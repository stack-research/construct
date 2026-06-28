"""SPEC_X1 mock-smoke + replay — the decay machinery as a pure function of select_offers.

Run:  uv run --no-project python -m tests.test_decay   (or: make x1-test)

Mock engine, so NOT evidence about a resident. The verdicts prove the MACHINERY:
the earned-reweighting offer flip (X1-win), soft-ablation isolating temperature
from the M-track gates, the projection invariant fail-closed, Wall II, and
ledger-deterministic replay. Real cross-engine evidence is the gated run (§8).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from harness.ledger import Ledger
from harness.run_x1 import BRANCH_A, BRANCH_B, BRANCH_C, run_x1_sequence
from harness.score_decay import _branch_from_config, _final_temperatures, score_decay
from harness.temperature import ProjectionViolation, T_FLOOR, TemperatureStore

ROOT = Path(__file__).resolve().parent.parent
EP = ROOT / "episodes" / "x1" / "reweight.json"


def _run(n: int = 6) -> Path:
    return run_x1_sequence([EP] * n, engine_backend="mock", runs_dir=Path(tempfile.mkdtemp()))


def _cells(led: Path) -> dict:
    return {v["cell"]: v for v in score_decay(led)}


def test_reweight_win():
    v = _cells(_run())
    w = v["X1-win"]
    assert w["verdict"] == "pass", w
    # C reweighted: the retracted finding cooled out, only the corrective record offered
    assert w["offers"][BRANCH_C] == ["fish-clock-retraction-heed"], w["offers"]
    assert "fish-clock-finding" in w["offers"][BRANCH_A]   # A never decays -> still offers it
    assert "fish-clock-finding" in w["offers"][BRANCH_B]   # B reheats it -> still offers it
    # soft-ablation: clamping the finding's temperature re-offers it -> temperature was important,
    # and the flip is confined to the cooled record (not an M-track gate under a heat map)
    assert w["soft_ablation"]["symdiff"] == ["fish-clock-finding"], w["soft_ablation"]
    assert w["soft_ablation"]["confined_to_non_neutral"]
    assert w["projection_invariant"]
    print("ok  X1-win: earned reweighting flips C's offer set; soft-ablation isolates temperature")


def test_un_authored_and_disclosure():
    v = _cells(_run())
    assert v["X1-U1"]["verdict"] == "pass" and v["X1-U1"]["oracle_source"] != "authored"
    assert any("mock" in d for d in v["X1-win"]["disclosures"])
    print("ok  X1-U1 world leg (rw-0001, source!=authored) + mock disclosed, not evidence")


def test_projection_invariant_fail_closed():
    led = _run()
    rows = Ledger(led).rows()
    meta = next(r for r in rows if r["kind"] == "x1_run_meta")
    rc = next(r for r in rows if r["kind"] == "run_config" and r["run_id"] == meta["probe_run_id"])
    cfgC = _branch_from_config(next(b for b in rc["branches"] if b["branch_id"] == BRANCH_C))
    # Drift branch C's authority off the others -> the static M-track projection must refuse the win.
    Path(cfgC.authority_path).write_text(json.dumps({"fish-clock-finding": 1.5}))
    assert _cells(led)["X1-win"]["verdict"] == "confounded_authority"
    print("ok  M-track projection fail-closed: drifted authority -> confounded_authority, never pass")


def test_replay_pure_function():
    led = _run()
    rows = Ledger(led).rows()
    meta = next(r for r in rows if r["kind"] == "x1_run_meta")
    # Rebuild C's temperature from temperature_delta rows ALONE == the sidecar cache.
    replayed = _final_temperatures(rows, BRANCH_C)
    sidecar = json.loads(Path(meta["temperature_paths"][BRANCH_C]).read_text())
    assert replayed == sidecar, (replayed, sidecar)
    print("ok  replay: TemperatureStore rebuilt from temperature_delta rows == sidecar (rows are truth)")


def test_wall_ii_allowlist():
    s = TemperatureStore(Path(tempfile.mkdtemp()) / "t.json")
    bad_inputs = [
        # a post-answer self-claim smuggled as the basis
        {"recommendation": "reheat", "magnitude": 0.2, "authorized_basis": {"agent_claimed_usage": "evidence"}},
        # a fat provenance blob (non-allowlisted projection key)
        {"recommendation": "reheat", "magnitude": 0.2, "authorized_basis": {"mode": "x"},
         "resident_self_label": "important"},
    ]
    for bad in bad_inputs:
        try:
            s.apply("r", bad)
            raise AssertionError("expected ProjectionViolation")
        except ProjectionViolation:
            pass
    print("ok  Wall II: forbidden basis / fat provenance blob both raise ProjectionViolation")


def test_floor_holds():
    rows = Ledger(_run()).rows()
    assert all(r["temp_after"] >= T_FLOOR - 1e-9 for r in rows if r["kind"] == "temperature_delta")
    print("ok  floor: no record cooled below T_FLOOR (erasure is deliberate, not arithmetic accident)")


def main() -> None:
    tests = [
        test_reweight_win,
        test_un_authored_and_disclosure,
        test_projection_invariant_fail_closed,
        test_replay_pure_function,
        test_wall_ii_allowlist,
        test_floor_holds,
    ]
    for t in tests:
        t()
    print(f"\nALL {len(tests)} DECAY TESTS PASS")
    print("DISCLOSED: mock engine — machinery wire, not evidence about a resident.")


if __name__ == "__main__":
    main()
