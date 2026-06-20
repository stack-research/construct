"""SPEC_X2 mock-smoke + cost-replay — the prune machinery as a pure function.

Run:  uv run --no-project python -m tests.test_prune   (or: make x2-test)

Mock engine, so NOT evidence about a resident. The verdicts prove the MACHINERY:
the cost-at-matched-quality win (X2-win), the over-prune loss (B drops a needed
record it cannot recover), the quality-erosion floor-refusal, cost replaying
purely from prune/rematerialize rows, and Wall II. Real cross-engine evidence on
an out-of-weights fixture is the gated run (§7).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from harness.ledger import Ledger
from harness.prune import HotStore, ProjectionViolation
from harness.run_x2 import BRANCH_A, BRANCH_B, BRANCH_C, run_x2_sequence
from harness.score_prune import score_prune

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "episodes" / "x2" / "core.json"
RECUR = ROOT / "episodes" / "x2" / "recurrence.json"


def _run() -> Path:
    return run_x2_sequence([CORE, CORE, CORE, RECUR], engine_backend="mock",
                           runs_dir=Path(tempfile.mkdtemp()), top_k=1)


def _cells(led: Path) -> dict:
    return {v["cell"]: v for v in score_prune(led)}


def test_x2_win():
    w = _cells(_run())["X2-win"]
    assert w["verdict"] == "pass", w
    cost = w["cost_hot_tokens"]
    assert cost[BRANCH_C] < cost[BRANCH_A], cost          # cheaper than no-prune
    assert w["quality_floor_holds"] and w["attribution_ok"]
    print("ok  X2-win: C matched A's quality at lower hot_tokens (distractor pruned, backup rematerialized)")


def test_x2_overprune():
    assert _cells(_run())["X2-overprune"]["verdict"] == "pass"
    print("ok  X2-overprune: B pruned a needed record, could not recover -> quality fell while cheaper")


def test_quality_erosion_refused():
    # Synthetic ledger: C is cheaper than A but its quality dips below A on one
    # episode -> the floor must REFUSE the cost win (cheap memory bought by forgetting).
    d = Path(tempfile.mkdtemp())
    led = Ledger(d / "syn.x2.jsonl")
    branches = [{"branch_id": b, "memory": "governed", "top_k": 1, "recency_weight": 0.0,
                 "similarity_backend": "lexical_tfidf", "eligibility_threshold": 0.0,
                 "inherited_record_ids": None} for b in (BRANCH_A, BRANCH_B, BRANCH_C)]
    for i, rid in enumerate(("r1", "r2")):
        led.write({"kind": "run_config", "run_id": rid, "engine_backend": "mock", "branches": branches})
        for b, q, ht in ((BRANCH_A, 1.0, 50), (BRANCH_B, 1.0, 50),
                         (BRANCH_C, (0.0 if i == 1 else 1.0), 20)):
            led.write({"kind": "branch_run", "run_id": rid, "branch_id": b,
                       "oracle": {"score": q, "source": "authored"}})
            led.write({"kind": "hot_store_cost", "run_id": rid, "branch_id": b, "hot_tokens": ht})
    led.write({"kind": "x2_run_meta", "seq_id": "syn", "probe_run_id": "r2", "all_record_ids": ["x"],
               "branches": {"no_prune": BRANCH_A, "closed_loop": BRANCH_B, "oracle_gated": BRANCH_C}})
    v = _cells(led.path)
    assert v["X2-win"]["verdict"] == "quality_erosion", v["X2-win"]
    assert v["X2-quality-erosion"]["verdict"] == "pass", v["X2-quality-erosion"]
    print("ok  quality-erosion: C cheaper but below A's floor -> X2-win refused, floor-cell fires")


def test_cost_replay():
    led = _run()
    rows = Ledger(led).rows()
    meta = next(r for r in rows if r["kind"] == "x2_run_meta")
    all_ids = set(meta["all_record_ids"])
    for b in (BRANCH_A, BRANCH_B, BRANCH_C):
        hot = set(all_ids)  # seeded full, then evolved purely by the rows
        ops = sorted((r for r in rows if r["kind"] in ("prune", "rematerialize") and r["branch_id"] == b),
                     key=lambda r: r["event_index"])
        for r in ops:
            hot.discard(r["record_id"]) if r["op"] == "prune" else hot.add(r["record_id"])
        sidecar = set(json.loads(Path(meta["hot_paths"][b]).read_text()))
        assert hot == sidecar, (b, hot, sidecar)
    print("ok  cost-replay: hot set rebuilt from prune/rematerialize rows == sidecar (rows are truth)")


def test_wall_ii():
    h = HotStore(Path(tempfile.mkdtemp()) / "h.json", seed_ids={"r1"})
    for bad in ({"recommendation": "prune", "authorized_basis": {"agent_claimed_usage": "unused"}},
                {"recommendation": "prune", "authorized_basis": {"mode": "x"}, "resident_self_label": "drop"}):
        try:
            h.apply("r1", bad)
            raise AssertionError("expected ProjectionViolation")
        except ProjectionViolation:
            pass
    print("ok  Wall II: forbidden basis / fat provenance blob both raise ProjectionViolation")


def main() -> None:
    tests = [test_x2_win, test_x2_overprune, test_quality_erosion_refused, test_cost_replay, test_wall_ii]
    for t in tests:
        t()
    print(f"\nALL {len(tests)} PRUNE TESTS PASS")
    print("DISCLOSED: mock engine — machinery wire, not evidence about a resident.")


if __name__ == "__main__":
    main()
