"""SPEC_X2 prune-to-cold-store runner — the offer ledger's hot/cold split.

A/B/C prune-fork over a sequence (the hot set = a branch's `inherited_record_ids`,
the M1 heir restriction reused; the full record list is the cold lineage):

  A  no-prune    : hot set = all records, always; pays full hot-store cost.
  B  closed-loop : prune not-offered records (disuse, no oracle); NO rematerialize.
  C  oracle-gated: prune not-offered records *when the answer is world-correct*;
                   and REMATERIALIZE cold records that become relevant again — the
                   recovery B lacks. That is the load-bearing difference: B over-
                   prunes a record needed later and cannot get it back; C does.

Scored on **cost at matched quality** (scoring-axis law): the win is lower
`hot_tokens` with answer quality held to the world floor, never a changed answer.
Fork identity: same engine/episodes/prompt/oracle/offer-gates, authority frozen;
only the prune policy differs. Wall II: a `prune_projection` precedes every
prune/rematerialize; the actuator (HotStore.apply) moves only what it entails.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

from .ledger import Ledger
from .prune import HotStore
from .retrieval import rank_records
from .runner import BranchConfig, Episode, run_fork_group

ROOT = Path(__file__).resolve().parent.parent
X2_DIR = ROOT / "episodes" / "x2"

BRANCH_A = "L2"      # no-prune control
BRANCH_B = "L2p"     # closed-loop prune (no rematerialize)
BRANCH_C = "L2pR"    # oracle-gated prune + rematerialize


def _episode_signals(rows: list[dict], run_id: str) -> dict:
    """Per-branch offered set + oracle row for one episode, from the ledger."""
    sig: dict[str, dict] = {}

    def b(bid: str) -> dict:
        return sig.setdefault(bid, {"offered": set(), "oracle": {}})

    for r in rows:
        if r.get("run_id") != run_id:
            continue
        if r["kind"] == "offer":
            b(r["branch_id"])["offered"].add(r["record_id"])
        elif r["kind"] == "branch_run":
            b(r["branch_id"])["oracle"] = r.get("oracle", {})
    return sig


def _rematerialize_relevant(ep: Episode, hot: HotStore, ledger: Ledger,
                            *, top_k: int, recency_weight: float, backend: str,
                            ctr: list[int]) -> int:
    """C only, before answering: bring back a cold record only if it would land in
    the top_k for the current question — i.e. it is actually needed / would be
    offered. Not a fixed relevance floor (which rematerializes anything sharing a
    common word and defeats the cost win); a record returns exactly when the
    question makes it offer-worthy again. Ledgered + projected (the recovery B lacks)."""
    cold_ids = {r.record_id for r in ep.records if r.record_id not in hot.get_hot()}
    if not cold_ids:
        return 0
    ranked = rank_records(ep.question, ep.records, recency_weight, similarity_backend=backend)
    n = 0
    for r, score in ranked[:top_k]:
        if r.record_id in cold_ids and score > 0.0:
            ev = ctr[0]; ctr[0] += 1
            pp_ref = f"pp-{BRANCH_C}-{ev}"
            projection = {
                "recommendation": "rematerialize",
                "authorized_basis": {"needed_by": ep.episode_id, "world_check_id": f"top{top_k}_relevant"},
                "projection_ref": pp_ref, "world_check_ref": f"relevance:{score:.3f}",
            }
            ledger.write({"kind": "prune_projection", "branch_id": BRANCH_C, "episode_id": ep.episode_id,
                          "event_index": ev, **projection})
            row = hot.apply(r.record_id, projection)
            ledger.write({"kind": "rematerialize", "branch_id": BRANCH_C, "episode_id": ep.episode_id,
                          "event_index": ev, "reason": "relevant_recurrence",
                          "world_check": {"relevance": score, "rank_within": top_k}, **row})
            n += 1
    return n


def _prune_disuse(branch_id: str, ep: Episode, hot: HotStore, offered: set, *,
                  oracle_gated: bool, world_correct: bool, ledger: Ledger, ctr: list[int]) -> None:
    """After answering: a hot record not offered this episode is a disuse candidate.
    B prunes it ungated; C prunes it only when the answer was world-correct (the
    sanction that we are not losing quality by dropping it)."""
    if oracle_gated and not world_correct:
        return  # C holds: do not prune while the answer is not world-confirmed
    for r in ep.records:
        if r.record_id in hot.get_hot() and r.record_id not in offered:
            ev = ctr[0]; ctr[0] += 1
            pp_ref = f"pp-{branch_id}-{ev}"
            basis = ({"mode": "oracle_gated", "world_check_id": "answer_world_correct", "disuse": True}
                     if oracle_gated else {"mode": "closed_loop", "disuse": True})
            projection = {"recommendation": "prune", "authorized_basis": basis,
                          "projection_ref": pp_ref,
                          "world_check_ref": ("answer_world_correct" if oracle_gated else None)}
            ledger.write({"kind": "prune_projection", "branch_id": branch_id, "episode_id": ep.episode_id,
                          "event_index": ev, **projection})
            row = hot.apply(r.record_id, projection)
            ledger.write({"kind": "prune", "branch_id": branch_id, "episode_id": ep.episode_id,
                          "event_index": ev,
                          "world_check": ({"answer_world_correct": True} if oracle_gated else None), **row})


def run_x2_sequence(
    seq_paths: list[Path],
    *,
    engine_backend: str = "mock",
    model: str = "mock-engine-v1",
    base_url: str = "http://localhost:1234/v1",
    runs_dir: Path | None = None,
    top_k: int = 1,
    ablation_samples: int = 1,
) -> Path:
    runs_dir = (runs_dir or ROOT / "runs" / "x2").resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)
    episodes = [Episode.load(p) for p in seq_paths]
    if not episodes:
        raise ValueError("X2 needs a non-empty sequence")
    all_ids = frozenset(r.record_id for ep in episodes for r in ep.records)  # the lineage universe
    seq_id = episodes[-1].episode_id.rsplit("-", 1)[0] + "-" + uuid.uuid4().hex[:6]
    ledger = Ledger(runs_dir / f"{seq_id}.x2.jsonl")
    if ledger.path.exists():
        ledger.path.unlink()

    common = dict(memory="governed", recency_weight=0.3, similarity_backend="lexical_tfidf")
    paths: dict[str, tuple[Path, Path]] = {}
    for bid in (BRANCH_A, BRANCH_B, BRANCH_C):
        ap = runs_dir / f"{seq_id}.{bid}.authority.json"
        hp = runs_dir / f"{seq_id}.{bid}.hot.json"
        for p in (ap, hp):
            if p.exists():
                p.unlink()
        paths[bid] = (ap, hp)
    hot = {bid: HotStore(paths[bid][1], seed_ids=all_ids) for bid in (BRANCH_A, BRANCH_B, BRANCH_C)}
    ctr = [0]
    probe_run_id = None

    for ep in episodes:
        # C rematerializes relevant cold records BEFORE answering (the recovery B lacks).
        remat = _rematerialize_relevant(ep, hot[BRANCH_C], ledger, top_k=top_k,
                                        recency_weight=common["recency_weight"],
                                        backend=common["similarity_backend"], ctr=ctr)
        branches = [
            BranchConfig(bid, authority_path=str(paths[bid][0]), top_k=top_k,
                         inherited_record_ids=hot[bid].get_hot(), **common)
            for bid in (BRANCH_A, BRANCH_B, BRANCH_C)
        ]
        result = run_fork_group(ep, branches, ledger, engine_backend=engine_backend,
                                model=model, base_url=base_url, ablation_samples=ablation_samples,
                                freeze_authority=True)
        probe_run_id = result["run_id"]
        for bid in (BRANCH_A, BRANCH_B, BRANCH_C):
            cost = hot[bid].cost(ep.records)
            ledger.write({"kind": "hot_store_cost", "branch_id": bid, "episode_id": ep.episode_id,
                          "run_id": probe_run_id,
                          "rematerialize_steps": remat if bid == BRANCH_C else 0, **cost})

        sig = _episode_signals(ledger.rows(), probe_run_id)
        for bid, gated in ((BRANCH_B, False), (BRANCH_C, True)):
            s = sig.get(bid, {"offered": set(), "oracle": {}})
            _prune_disuse(bid, ep, hot[bid], s["offered"], oracle_gated=gated,
                          world_correct=(s["oracle"].get("score", 0.0) >= 1.0),
                          ledger=ledger, ctr=ctr)

    probe = episodes[-1]
    ledger.write({
        "kind": "x2_run_meta", "seq_id": seq_id,
        "episode_ids": [e.episode_id for e in episodes],
        "probe_episode_id": probe.episode_id, "probe_run_id": probe_run_id,
        "branches": {"no_prune": BRANCH_A, "closed_loop": BRANCH_B, "oracle_gated": BRANCH_C},
        "hot_paths": {bid: str(paths[bid][1]) for bid in (BRANCH_A, BRANCH_B, BRANCH_C)},
        "authority_frozen": True, "top_k": top_k, "primary_cost": "hot_tokens",
        "all_record_ids": sorted(all_ids),
    })
    print(f"{seq_id}: {len(episodes)} episodes; final hot sets — "
          f"A={sorted(hot[BRANCH_A].get_hot())} B={sorted(hot[BRANCH_B].get_hot())} C={sorted(hot[BRANCH_C].get_hot())}")
    print(f"  ledger: {ledger.path}")
    return ledger.path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("episodes", nargs="+", help="the prune sequence; records shared across the sequence (the lineage)")
    p.add_argument("--engine", default="mock", choices=["mock", "claude", "local"])
    p.add_argument("--model", default="mock-engine-v1")
    p.add_argument("--base-url", default="http://localhost:1234/v1")
    p.add_argument("--runs-dir", default=str(ROOT / "runs" / "x2"))
    p.add_argument("--top-k", type=int, default=1)
    p.add_argument("--ablation-samples", type=int, default=1)
    args = p.parse_args()
    try:
        run_x2_sequence([Path(e) for e in args.episodes], engine_backend=args.engine, model=args.model,
                        base_url=args.base_url, runs_dir=Path(args.runs_dir), top_k=args.top_k,
                        ablation_samples=args.ablation_samples)
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
