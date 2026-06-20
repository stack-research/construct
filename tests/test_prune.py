"""SPEC_X2 mock-smoke + cost-replay + fail-closed integrity — the prune machinery
as a pure function.

Run:  uv run --no-project python -m tests.test_prune   (or: make x2-test)

Mock engine, so NOT evidence about a resident. The verdicts prove the MACHINERY:
the cost-at-matched-quality win (X2-win), the over-prune loss (B drops a needed
record it cannot recover), the quality-erosion floor-refusal, cost replaying
purely from prune/rematerialize rows, the scorer recomputing cost independently
and failing closed when a cost row is tampered or the lineage has a hole, and
Wall II. Real cross-engine evidence on an out-of-weights fixture is the gated run.
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

_W5 = "alpha beta gamma delta epsilon"  # exactly five tokens


def _run() -> Path:
    return run_x2_sequence([CORE, CORE, CORE, RECUR], engine_backend="mock",
                           runs_dir=Path(tempfile.mkdtemp()), top_k=1)


def _cells(led: Path) -> dict:
    return {v["cell"]: v for v in score_prune(led)}


def _tamper(led_path: Path, mutate) -> Path:
    """Copy a ledger, mutate its rows in place, write to a fresh path (so we can
    re-score a tampered immutable lineage and watch the scorer fail closed)."""
    rows = [json.loads(l) for l in Path(led_path).read_text().splitlines() if l.strip()]
    mutate(rows)
    out = Path(tempfile.mkdtemp()) / "tampered.x2.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return out


def test_x2_win():
    w = _cells(_run())["X2-win"]
    assert w["verdict"] == "pass", w
    cost = w["cost_hot_tokens"]
    assert cost[BRANCH_C] < cost[BRANCH_A], cost          # cheaper than no-prune
    assert w["quality_floor_holds"] and w["attribution_ok"]
    assert w["cost_replay_ok"] and w["lineage_integrity_ok"] and w["fork_identity_ok"]
    print("ok  X2-win: C matched A's quality at lower hot_tokens (cost recomputed from the lineage + rows)")


def test_x2_overprune():
    v = _cells(_run())["X2-overprune"]
    assert v["verdict"] == "pass", v
    assert v["pruned_unrecovered_by_B"], v            # Tier-2: the loss points to a named record
    assert v["C_recovered_via_rematerialize"], v      # and C held it (rematerialized)
    print(f"ok  X2-overprune: B lost {v['pruned_unrecovered_by_B']} (unrecovered); "
          f"C rematerialized {v['C_recovered_via_rematerialize']}")


def test_quality_erosion_refused():
    # Cost-consistent synthetic ledger: C is cheaper than A (prunes r2 after ep0) but
    # its quality dips below A on ep1 -> the floor must REFUSE the cost win. Cost rows
    # match the prune-row replay so attribution is clean and the refusal is real.
    d = Path(tempfile.mkdtemp())
    led = Ledger(d / "syn.x2.jsonl")
    bcfg = lambda b: {"branch_id": b, "memory": "governed", "top_k": 1, "recency_weight": 0.0,
                      "similarity_backend": "lexical_tfidf", "eligibility_threshold": 0.0,
                      "inherited_record_ids": None}
    branches = [bcfg(b) for b in (BRANCH_A, BRANCH_B, BRANCH_C)]
    runs = {0: "run0", 1: "run1"}
    for k, rid in runs.items():
        led.write({"kind": "run_config", "run_id": rid, "engine_backend": "mock", "branches": branches})
    # C prunes r2 after ep0 (event_index 0); A and B never prune.
    led.write({"kind": "prune", "branch_id": BRANCH_C, "seq_index": 0, "event_index": 0,
               "op": "prune", "record_id": "r2"})
    # logged cost rows (must equal the replay): A,B = {r1,r2}=10 both eps; C = 10 then 5.
    cost_rows = {BRANCH_A: {0: 10, 1: 10}, BRANCH_B: {0: 10, 1: 10}, BRANCH_C: {0: 10, 1: 5}}
    qual = {BRANCH_A: {0: 1.0, 1: 1.0}, BRANCH_B: {0: 1.0, 1: 1.0}, BRANCH_C: {0: 1.0, 1: 0.0}}
    for k, rid in runs.items():
        for b in (BRANCH_A, BRANCH_B, BRANCH_C):
            led.write({"kind": "hot_store_cost", "run_id": rid, "seq_index": k, "branch_id": b,
                       "hot_tokens": cost_rows[b][k], "rematerialize_steps": 0})
            led.write({"kind": "branch_run", "run_id": rid, "branch_id": b,
                       "oracle": {"score": qual[b][k], "source": "world_oracle"}})
    led.write({"kind": "x2_run_meta", "seq_id": "syn", "probe_run_id": "run1",
               "all_record_ids": ["r1", "r2"], "record_texts": {"r1": _W5, "r2": _W5},
               "primary_cost_metric": "hot_tokens",
               "branches": {"no_prune": BRANCH_A, "closed_loop": BRANCH_B, "oracle_gated": BRANCH_C}})
    v = _cells(led.path)
    assert v["X2-win"]["verdict"] == "quality_erosion", v["X2-win"]
    assert v["X2-win"]["attribution_ok"], v["X2-win"]          # refusal is real, not a confound
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


def test_confounded_cost():
    # The scorer recomputes cost from the lineage + rows; it does NOT trust the
    # hot_store_cost rows. Tamper one -> the win is confounded, not manufactured.
    def bump(rows):
        for r in rows:
            if r["kind"] == "hot_store_cost":
                r["hot_tokens"] = r.get("hot_tokens", 0) + 100
                return
    w = _cells(_tamper(_run(), bump))["X2-win"]
    assert w["verdict"] == "confounded", w
    assert not w["cost_replay_ok"] and "cost_replay_mismatch" in w["confound_reasons"], w
    print("ok  confounded-cost: a tampered hot_store_cost row != row-replay -> X2-win confounded")


def test_lineage_integrity():
    # Lineage is immutable AND complete. A prune row referencing an id outside the
    # lineage universe is a hole, not a measurement -> fail closed (dan's invariant).
    def ghost(rows):
        for r in rows:
            if r["kind"] == "prune":
                r["record_id"] = "ghost-not-in-lineage"
                return
    w = _cells(_tamper(_run(), ghost))["X2-win"]
    assert w["verdict"] == "confounded", w
    assert not w["lineage_integrity_ok"] and "op_references_unknown_record" in w["confound_reasons"], w
    print("ok  lineage-integrity: a prune referencing an id outside the lineage -> confounded (immutable+complete)")


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
    tests = [test_x2_win, test_x2_overprune, test_quality_erosion_refused, test_cost_replay,
             test_confounded_cost, test_lineage_integrity, test_wall_ii]
    for t in tests:
        t()
    print(f"\nALL {len(tests)} PRUNE TESTS PASS")
    print("DISCLOSED: mock engine — machinery wire, not evidence about a resident.")


if __name__ == "__main__":
    main()
