"""SPEC_X1 decay-dynamics runner — the offer ledger under use-driven temperature.

A/B/C decay-fork over a recall sequence (the rw-0001 chain):

  A  no-decay (control)  : decay off; temperature pinned at 1.0 (today's L2)
  B  closed-loop         : reheat-on-recall (ungated) + cool-on-disuse
  C  oracle-gated        : reheat is a CLAIM the Landauer oracle pays/claws against
                           the world-checked answer outcome (R1/R5 in the thermal layer)

Fork identity held: same engine/episodes/prompt/oracle; AUTHORITY READ-ONLY
(freeze_authority) so temperature is the only moving record-side factor — a later
C-vs-A/B offer gap cannot be authority drift (codex/cursor block, SPEC_X1 §2).

Two harness-authorized logical clocks (kagi — never wall-clock, never resident-emitted):
  - recall event  : a record offered AND important (ablation) raises a reheat
                    claim, adjudicated at answer-scoring time.
  - disuse tick   : at each episode boundary every present-but-not-recalled record
                    cools toward the floor (the free direction).

Wall II: the observer writes a thermal_projection BEFORE every temperature_delta;
the actuator (TemperatureStore.apply) moves only the heat the projection entails.
The demon pays by being logged before it moves heat.

Usage:
  python -m harness.run_x1 episodes/x1/use-1.json ... episodes/x1/probe.json \
      --engine local --model openai/gpt-oss-20b
  (the LAST episode in the sequence is the probe the scorer reads)
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

from .ledger import Ledger
from .runner import BranchConfig, Episode, run_fork_group
from .temperature import CLAW, REHEAT, RELAXATION, TemperatureStore

ROOT = Path(__file__).resolve().parent.parent
X1_DIR = ROOT / "episodes" / "x1"

BRANCH_A = "L2"     # no-decay control
BRANCH_B = "L2t"    # closed-loop decay (temperature, no oracle)
BRANCH_C = "L2tL"   # oracle-gated decay (temperature + Landauer)


def _episode_signals(rows: list[dict], run_id: str) -> dict:
    """Per-branch signals from one episode's run, read from the ledger (never
    narration): offered ids, the ablation important map, the candidate set,
    and the branch's oracle row. The fork decides; the resident does not."""
    sig: dict[str, dict] = {}

    def b(bid: str) -> dict:
        return sig.setdefault(bid, {"offered": set(), "candidates": set(),
                                    "load_bearing": {}, "oracle": {}})

    for r in rows:
        if r.get("run_id") != run_id:
            continue
        k = r["kind"]
        if k == "offer":
            d = b(r["branch_id"]); d["offered"].add(r["record_id"]); d["candidates"].add(r["record_id"])
        elif k == "withholding":
            b(r["branch_id"])["candidates"].add(r["record_id"])
        elif k == "ablation_run":
            b(r["branch_id"])["load_bearing"][r["ablated_record_id"]] = bool(r["outcome_changed"])
        elif k == "branch_run":
            b(r["branch_id"])["oracle"] = r.get("oracle", {})
    return sig


def _observe(branch_id: str, ep: Episode, sig_b: dict, temp_store: TemperatureStore,
             ledger: Ledger, run_id: str, *, landauer_oracle: bool, ctr: list[int]) -> None:
    """Wall II observer for one branch over one episode. Recall (offered +
    important) raises a reheat claim: B applies it ungated (closed loop), C
    adjudicates pay/claw against the world-checked answer outcome. Everything else
    present that episode cools by disuse (the free direction). The actuator only
    ever applies the projection-entailed heat."""
    offered, lb, oracle = sig_b["offered"], sig_b["load_bearing"], sig_b["oracle"]
    oracle_score = oracle.get("score", 0.0)
    for r in ep.records:
        rid = r.record_id
        recalled = rid in offered and lb.get(rid, False)
        ev = ctr[0]; ctr[0] += 1
        ld_ref = None
        if recalled:
            ledger.write({"kind": "thermal_event", "event_index": ev, "event_kind": "recall",
                          "trigger_run_id": run_id, "record_id": rid, "episode_id": ep.episode_id,
                          "branch_id": branch_id, "tick_authority": "harness"})
            if landauer_oracle:
                # The Landauer oracle: reheat is paid only when the recall was
                # important AND world-correct; a important WRONG recall is
                # clawed back. The world leg is the branch's own world-checked
                # answer outcome — no second judge.
                decision = "pay" if oracle_score >= 1.0 else "claw_back"
                rec, mag = ("reheat", REHEAT) if decision == "pay" else ("cool", CLAW)
                ld_ref = f"ld-{branch_id}-{ev}"
                ledger.write({"kind": "landauer_decision", "landauer_decision_id": ld_ref,
                              "thermal_event_index": ev, "branch_id": branch_id,
                              "decision": decision, "recall_load_bearing": True,
                              "world_check": {"oracle_source": oracle.get("source"),
                                              "score": oracle_score,
                                              "corpus_entry": oracle.get("corpus_entry")},
                              "magnitude": mag})
                basis = {"mode": "oracle_gated", "landauer_decision_id": ld_ref,
                         "recall_load_bearing": True}
            else:
                rec, mag = "reheat", REHEAT
                basis = {"mode": "closed_loop", "recall_load_bearing": True}
        else:
            ledger.write({"kind": "thermal_event", "event_index": ev, "event_kind": "disuse_tick",
                          "trigger_run_id": run_id, "record_id": rid, "episode_id": ep.episode_id,
                          "branch_id": branch_id, "tick_authority": "harness"})
            rec, mag = "cool", RELAXATION
            basis = {"disuse_tick": True}

        tp_ref = f"tp-{branch_id}-{ev}"
        projection = {"recommendation": rec, "magnitude": mag, "authorized_basis": basis,
                      "projection_ref": tp_ref, "landauer_decision_ref": ld_ref}
        ledger.write({"kind": "thermal_projection", "branch_id": branch_id,
                      "episode_id": ep.episode_id, "event_index": ev, **projection})
        delta_row = temp_store.apply(rid, projection)  # raises ProjectionViolation if unentailed
        ledger.write({"kind": "temperature_delta", "branch_id": branch_id,
                      "episode_id": ep.episode_id, "event_index": ev, **delta_row})


def run_x1_sequence(
    seq_paths: list[Path],
    *,
    engine_backend: str = "mock",
    model: str = "mock-engine-v1",
    base_url: str = "http://localhost:1234/v1",
    runs_dir: Path | None = None,
    ablation_samples: int = 1,
) -> Path:
    runs_dir = (runs_dir or ROOT / "runs" / "x1").resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)
    episodes = [Episode.load(p) for p in seq_paths]
    if not episodes:
        raise ValueError("X1 needs a non-empty recall sequence (last episode = probe)")
    seq_id = episodes[-1].episode_id.rsplit("-", 1)[0] + "-" + uuid.uuid4().hex[:6]
    ledger = Ledger(runs_dir / f"{seq_id}.x1.jsonl")
    if ledger.path.exists():
        ledger.path.unlink()

    common = dict(memory="governed", recency_weight=0.3, similarity_backend="lexical_tfidf")
    paths: dict[str, tuple[Path, Path]] = {}
    for bid in (BRANCH_A, BRANCH_B, BRANCH_C):
        ap = runs_dir / f"{seq_id}.{bid}.authority.json"
        tp = runs_dir / f"{seq_id}.{bid}.temperature.json"
        for p in (ap, tp):
            if p.exists():
                p.unlink()
        paths[bid] = (ap, tp)

    def branches(top_k: int) -> list[BranchConfig]:
        # top_k covers all candidates: eligibility×temperature withholds the cold
        # record, never the budget (SPEC_X1 — the finding "cools below threshold").
        return [
            BranchConfig(BRANCH_A, authority_path=str(paths[BRANCH_A][0]), top_k=top_k,
                         decay_dynamics=False, **common),
            BranchConfig(BRANCH_B, authority_path=str(paths[BRANCH_B][0]), top_k=top_k,
                         decay_dynamics=True, landauer_oracle=False,
                         temperature_path=str(paths[BRANCH_B][1]), **common),
            BranchConfig(BRANCH_C, authority_path=str(paths[BRANCH_C][0]), top_k=top_k,
                         decay_dynamics=True, landauer_oracle=True,
                         temperature_path=str(paths[BRANCH_C][1]), **common),
        ]

    temp_stores = {BRANCH_B: TemperatureStore(paths[BRANCH_B][1]),
                   BRANCH_C: TemperatureStore(paths[BRANCH_C][1])}
    ctr = [0]
    probe_run_id = None
    for ep in episodes:
        result = run_fork_group(
            ep, branches(len(ep.records)), ledger,
            engine_backend=engine_backend, model=model, base_url=base_url,
            ablation_samples=ablation_samples, freeze_authority=True,
        )
        probe_run_id = result["run_id"]  # last episode wins = the probe
        sig = _episode_signals(ledger.rows(), probe_run_id)
        empty = {"offered": set(), "candidates": set(), "load_bearing": {}, "oracle": {}}
        for bid, store in temp_stores.items():
            _observe(bid, ep, sig.get(bid, empty), store, ledger, probe_run_id,
                     landauer_oracle=(bid == BRANCH_C), ctr=ctr)

    probe = episodes[-1]
    ledger.write({
        "kind": "x1_run_meta", "seq_id": seq_id,
        "episode_ids": [e.episode_id for e in episodes],
        "probe_episode_id": probe.episode_id, "probe_run_id": probe_run_id,
        "probe_episode_path": str(seq_paths[-1]),
        "branches": {"no_decay": BRANCH_A, "closed_loop": BRANCH_B, "oracle_gated": BRANCH_C},
        "temperature_paths": {bid: str(paths[bid][1]) for bid in (BRANCH_B, BRANCH_C)},
        "authority_frozen": True,
        "target_record_ids": sorted(r.record_id for r in probe.records),
    })
    finals = {bid: temp_stores[bid]._data for bid in (BRANCH_B, BRANCH_C)}
    print(f"{seq_id}: {len(episodes)} episodes, probe={probe.episode_id} run={probe_run_id}")
    print(f"  final temperatures  B={finals[BRANCH_B]}")
    print(f"                      C={finals[BRANCH_C]}")
    print(f"  ledger: {ledger.path}")
    return ledger.path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("episodes", nargs="+", help="recall sequence; the LAST episode is the probe")
    p.add_argument("--engine", default="mock", choices=["mock", "claude", "local"])
    p.add_argument("--model", default="mock-engine-v1")
    p.add_argument("--base-url", default="http://localhost:1234/v1")
    p.add_argument("--runs-dir", default=str(ROOT / "runs" / "x1"))
    p.add_argument("--ablation-samples", type=int, default=1)
    args = p.parse_args()
    try:
        run_x1_sequence(
            [Path(e) for e in args.episodes],
            engine_backend=args.engine, model=args.model, base_url=args.base_url,
            runs_dir=Path(args.runs_dir), ablation_samples=args.ablation_samples,
        )
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
