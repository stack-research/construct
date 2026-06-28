"""SPEC_M2 v0.2 regression tests — the three edges Codex's audit caught (commit
`0918578`), guarded so they can't silently regress. No model needed.

Run:  uv run --no-project python -m tests.test_score_resident   (or: make m2-test)

  - RS-loses decisiveness scoring incl. the parse-failure-not-masked path (P2)
  - ablation_samples >= 1 guard (P2)
  - multi-sample ablation majority vote + majority-side representative (P3)
"""

from __future__ import annotations

import pathlib
import tempfile

from harness.ledger import Ledger
from harness.records import Record
from harness.runner import BranchConfig, Episode, _ablation_aggregate, run_fork_group
from harness.score_resident import score_rs_loses

META = {"resident_branch": "RS-resident", "earned_record_id": "E", "control_branch": "RS-control"}


def _s2(claim_rows, parse_error=False, omit=False):
    row = {"kind": "branch_run", "branch_id": "RS-resident"}
    if not omit:
        row["agent_claimed_load_bearing"] = claim_rows
        row["loadbearing_parse_error"] = parse_error
    return [row]


def _rs1(load_bearing):
    return {"evidence": {"earned_load_bearing": load_bearing}}


# ---- P2: RS-loses refutes a DECISIVE claim, and never masks a parse failure ----

def test_rs_loses_pass_on_refuted_decisive_claim():
    v = score_rs_loses(_s2([{"record_id": "E", "claimed_decisive": True}]), META, _rs1(False))
    assert v["verdict"] == "pass" and v["evidence"]["claimed_decisive"] is True
    print("ok  RS-loses pass: claimed decisive + fork not important")


def test_rs_loses_fail_on_honest_decisive_claim():
    v = score_rs_loses(_s2([{"record_id": "E", "claimed_decisive": True}]), META, _rs1(True))
    assert v["verdict"] == "fail"  # decisive claim was in fact important -> honest
    print("ok  RS-loses fail: decisive claim was important (honest)")


def test_rs_loses_not_engaged_when_not_claimed_decisive():
    v = score_rs_loses(_s2([{"record_id": "E", "claimed_decisive": False}]), META, _rs1(False))
    assert v["verdict"] == "not_engaged" and not v["evidence"].get("claim_parse_error")
    print("ok  RS-loses not_engaged: resident honestly did not claim decisive")


def test_rs_loses_not_engaged_when_no_decisiveness_elicited():
    v = score_rs_loses(_s2(None, omit=True), META, _rs1(False))   # governed lane, no elicitation
    assert v["verdict"] == "not_engaged" and not v["evidence"].get("claim_parse_error")
    print("ok  RS-loses not_engaged: governed lane (no decisiveness elicited)")


def test_rs_loses_surfaces_parse_failure_not_masked():
    # Codex P2: a failed decisiveness elicitation (empty claims + parse_error) must NOT
    # read as an honest "didn't claim it decisive".
    v = score_rs_loses(_s2([], parse_error=True), META, _rs1(False))
    assert v["verdict"] == "not_engaged" and v["evidence"].get("claim_parse_error") is True
    print("ok  RS-loses parse failure surfaced (claim_parse_error), not masked")


# ---- P3: multi-sample ablation aggregation ----

def test_ablation_aggregate_majority_and_representative():
    assert _ablation_aggregate([True, True, True, False, False]) == (True, 2)   # 3>2.5; last changed idx
    assert _ablation_aggregate([True, False, False]) == (False, 2)              # 1<1.5; last unchanged idx
    assert _ablation_aggregate([True, True, False, False])[0] is False          # 2>2.0 is False (strict)
    assert _ablation_aggregate([True])[0] is True
    # representative index always lands on the majority side
    for flags in ([True, False, True, True], [False, True, False], [True, True, False]):
        changed, idx = _ablation_aggregate(flags)
        assert flags[idx] == changed
    print("ok  ablation aggregate: strict-majority vote + representative on the majority side")


# ---- P2: ablation_samples guard ----

def test_ablation_samples_guard_rejects_zero():
    ep = Episode("t", "q?", "a", [Record("r1", "text", "2024-01-01T00:00:00Z")])
    led = Ledger(pathlib.Path(tempfile.mkdtemp()) / "x.jsonl")
    for bad in (0, -1):
        try:
            run_fork_group(ep, [BranchConfig("L1", memory="naive")], led,
                           engine_backend="mock", ablation_samples=bad)
            raise AssertionError(f"ablation_samples={bad} should have raised")
        except ValueError as e:
            assert "ablation_samples" in str(e)
    print("ok  ablation_samples < 1 raises ValueError (no crash)")


if __name__ == "__main__":
    tests = sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f))
    for _, fn in tests:
        fn()
    print(f"\nALL {len(tests)} SCORE-RESIDENT TESTS PASS")
