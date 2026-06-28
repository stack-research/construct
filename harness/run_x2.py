"""SPEC_X2 prune-to-cold-store runner — the offer ledger's hot/cold split.

A/B/C prune-fork over a sequence (the hot set = a branch's `inherited_record_ids`,
the M1 heir restriction reused; the full record list is the cold lineage):

  A  no-prune    : hot set = all records, always; pays full hot-store cost.
  B  closed-loop : prune not-offered records (disuse, no oracle); NO rematerialize.
  C  oracle-gated: prune not-offered records *when the answer is world-correct*;
                   and REMATERIALIZE cold records that become relevant again — the
                   recovery B lacks. That is the important difference: B over-
                   prunes a record needed later and cannot get it back; C does.

Scored on **cost at matched quality** (scoring-axis law): the win is lower
`hot_tokens` with answer quality held to the world floor, never a changed answer.
Fork identity: same engine/episodes/prompt/oracle/offer-gates, authority frozen;
only the prune policy differs. Wall II: a `prune_projection` precedes every
prune/rematerialize; the actuator (HotStore.apply) moves only what it entails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
                            *, seq_index: int, top_k: int, recency_weight: float,
                            backend: str, ctr: list[int]) -> int:
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
                          "seq_index": seq_index, "event_index": ev, **projection})
            row = hot.apply(r.record_id, projection)
            ledger.write({"kind": "rematerialize", "branch_id": BRANCH_C, "episode_id": ep.episode_id,
                          "seq_index": seq_index, "event_index": ev, "reason": "relevant_recurrence",
                          "world_check": {"relevance": score, "rank_within": top_k}, **row})
            n += 1
    return n


def _prune_disuse(branch_id: str, ep: Episode, hot: HotStore, offered: set, *,
                  seq_index: int, oracle_gated: bool, world_correct: bool,
                  ledger: Ledger, ctr: list[int]) -> None:
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
                          "seq_index": seq_index, "event_index": ev, **projection})
            row = hot.apply(r.record_id, projection)
            ledger.write({"kind": "prune", "branch_id": branch_id, "episode_id": ep.episode_id,
                          "seq_index": seq_index, "event_index": ev,
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
    fixture_attestation: dict | None = None,
    manifest: dict | None = None,
    gate_result: dict | None = None,
    blocks: list[str] | None = None,
    recency_weight: float = 0.3,
) -> Path:
    runs_dir = (runs_dir or ROOT / "runs" / "x2").resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)
    episodes = [Episode.load(p) for p in seq_paths]
    if not episodes:
        raise ValueError("X2 needs a non-empty sequence")
    # Block labels (thread-7): P = predictable recurrence, U = unpredictable re-need.
    # One label per episode (by seq_index); absent -> a flat, block-unaware sequence.
    if blocks is not None and len(blocks) != len(episodes):
        raise ValueError(f"blocks length {len(blocks)} != sequence length {len(episodes)}")
    all_ids = frozenset(r.record_id for ep in episodes for r in ep.records)  # the lineage universe
    fixture_id = (manifest or {}).get("fixture_id", episodes[-1].episode_id.rsplit("-", 1)[0])
    seq_id = f"{fixture_id}-{uuid.uuid4().hex[:6]}"
    ledger = Ledger(runs_dir / f"{seq_id}.x2.jsonl")
    if ledger.path.exists():
        ledger.path.unlink()

    # recency_weight is fork-constant (same A/B/C); a same-subject temporal-reversal
    # corpus sets it 0.0 so the QUESTION, not recency, selects the record (manifest-configurable).
    common = dict(memory="governed", recency_weight=recency_weight, similarity_backend="lexical_tfidf")
    paths: dict[str, tuple[Path, Path]] = {}
    for bid in (BRANCH_A, BRANCH_B, BRANCH_C):
        ap = runs_dir / f"{seq_id}.{bid}.authority.json"
        hp = runs_dir / f"{seq_id}.{bid}.hot.json"
        for p in (ap, hp):
            if p.exists():
                p.unlink()
        paths[bid] = (ap, hp)
    hot = {bid: HotStore(paths[bid][1], seed_ids=all_ids) for bid in (BRANCH_A, BRANCH_B, BRANCH_C)}
    # The lineage universe: one immutable Record per id. The cost denominator is the
    # standing hot burden over the whole lineage, never the per-episode file — so the
    # scorer can replay cost independently (codex/cursor Tier-1).
    lineage_records = list({r.record_id: r for ep in episodes for r in ep.records}.values())
    record_texts = {r.record_id: r.text for r in lineage_records}
    ctr = [0]
    probe_run_id = None

    for seq_index, ep in enumerate(episodes):
        # C rematerializes relevant cold records BEFORE answering (the recovery B lacks).
        remat = _rematerialize_relevant(ep, hot[BRANCH_C], ledger, seq_index=seq_index, top_k=top_k,
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
        # Cost snapshot: after C's pre-answer rematerialize, before this episode's prune.
        # Over the full lineage (not ep.records) so cost replays from the row-trail.
        for bid in (BRANCH_A, BRANCH_B, BRANCH_C):
            cost = hot[bid].cost(lineage_records)
            ledger.write({"kind": "hot_store_cost", "branch_id": bid, "episode_id": ep.episode_id,
                          "run_id": probe_run_id, "seq_index": seq_index,
                          "rematerialize_steps": remat if bid == BRANCH_C else 0, **cost})

        sig = _episode_signals(ledger.rows(), probe_run_id)
        for bid, gated in ((BRANCH_B, False), (BRANCH_C, True)):
            s = sig.get(bid, {"offered": set(), "oracle": {}})
            _prune_disuse(bid, ep, hot[bid], s["offered"], seq_index=seq_index, oracle_gated=gated,
                          world_correct=(s["oracle"].get("score", 0.0) >= 1.0),
                          ledger=ledger, ctr=ctr)

    if gate_result is not None:
        # The COMPUTED gate outcome (manifest hash + the check results), not the
        # attestation claim. score_prune requires gate_open for any non-mock cell —
        # attestation is a claim, gate passage is computed.
        ledger.write({"kind": "fixture_gate_result", **gate_result})
    if fixture_attestation is not None:
        ledger.write({"kind": "fixture_attestation", **fixture_attestation})

    probe = episodes[-1]
    ledger.write({
        "kind": "x2_run_meta", "seq_id": seq_id,
        "fixture_id": fixture_id if manifest else None,
        "episode_ids": [e.episode_id for e in episodes],
        "probe_episode_id": probe.episode_id, "probe_run_id": probe_run_id,
        "branches": {"no_prune": BRANCH_A, "closed_loop": BRANCH_B, "oracle_gated": BRANCH_C},
        "hot_paths": {bid: str(paths[bid][1]) for bid in (BRANCH_A, BRANCH_B, BRANCH_C)},
        "authority_frozen": True, "top_k": top_k,
        "primary_cost_metric": (manifest or {}).get("primary_cost_metric", "hot_tokens"),
        "all_record_ids": sorted(all_ids), "record_texts": record_texts,
        "block_labels": list(blocks) if blocks else [None] * len(episodes),
    })
    print(f"{seq_id}: {len(episodes)} episodes; final hot sets — "
          f"A={sorted(hot[BRANCH_A].get_hot())} B={sorted(hot[BRANCH_B].get_hot())} C={sorted(hot[BRANCH_C].get_hot())}")
    print(f"  ledger: {ledger.path}")
    return ledger.path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("episodes", nargs="*", help="the prune sequence (or omit with --manifest)")
    p.add_argument("--manifest", help="X2 fixture manifest (episodes/x2/real/manifest.json)")
    p.add_argument("--engine", default="mock", choices=["mock", "claude", "local"])
    p.add_argument("--model", default="mock-engine-v1")
    p.add_argument("--base-url", default="http://localhost:1234/v1")
    p.add_argument("--runs-dir", default=str(ROOT / "runs" / "x2"))
    p.add_argument("--top-k", type=int, default=None)
    p.add_argument("--ablation-samples", type=int, default=1)
    p.add_argument("--skip-gate", action="store_true", help="wire/mock only — do not run admission gate")
    args = p.parse_args()
    # --skip-gate is wire/mock only: a non-mock (evidence) run may not skip the gate.
    if args.skip_gate and args.engine != "mock":
        print("REFUSED: --skip-gate is wire/mock only; a non-mock run must pass the gate",
              file=sys.stderr)
        return 1
    manifest = None
    seq_paths: list[Path]
    gate_result = None
    if args.manifest:
        manifest = json.loads(Path(args.manifest).read_text())
        seq_paths = [ROOT / p for p in manifest["sequence"]]
        if not args.skip_gate:
            from .check_x2_fixture import check_manifest
            checks = check_manifest(Path(args.manifest))
            gate_result = {
                "manifest_hash": hashlib.sha256(Path(args.manifest).read_bytes()).hexdigest()[:16],
                "gate_open": all(ok for _, ok, _ in checks),
                "n_checks": len(checks), "n_passed": sum(1 for _, ok, _ in checks if ok),
                "checks": [{"check": n, "ok": ok, "detail": d} for n, ok, d in checks],
            }
            if not gate_result["gate_open"] and args.engine != "mock":
                print(f"GATE REFUSED: {[n for n, ok, _ in checks if not ok]}", file=sys.stderr)
                return 1
    elif args.episodes:
        seq_paths = [Path(e) for e in args.episodes]
    else:
        print("provide episodes or --manifest", file=sys.stderr)
        return 1
    top_k = args.top_k if args.top_k is not None else (manifest or {}).get("top_k", 1)
    attestation = None
    if manifest:
        att = manifest.get("attestation", {})
        attestation = {
            "fixture_id": manifest.get("fixture_id"),
            "fictional": manifest.get("fictional"),
            "out_of_weights": manifest.get("out_of_weights"),
            "corpus_entry": manifest.get("corpus_entry"),
            "attested_by": att.get("attested_by"),
            "attested_at": att.get("attested_at"),
            "corpus_identity_pin": att.get("corpus_identity_pin"),
            "engine_cutoffs_disclosed": att.get("engine_cutoffs_disclosed"),
        }
    try:
        run_x2_sequence(seq_paths, engine_backend=args.engine, model=args.model,
                        base_url=args.base_url, runs_dir=Path(args.runs_dir), top_k=top_k,
                        ablation_samples=args.ablation_samples, manifest=manifest,
                        fixture_attestation=attestation, gate_result=gate_result,
                        blocks=(manifest or {}).get("blocks"),
                        recency_weight=(manifest or {}).get("recency_weight", 0.3))
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
