"""Wire tests for PRF v0.3 mechanism (SPEC Part III §28–§34).

Mock/scripted only — never promotes a cell.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from harness.check_prf_fixture import check_manifest
from harness.ledger import Ledger
from harness.mint_frontier_state import recompute_state_tokens
from harness.run_sbr import (parse_action, parse_r_handle_action,
                             run_and_score, run_calibration_gate,
                             run_mint_spine, run_sbr_session)
from harness.score_prf import PRFScorer
from harness.sbr_util import (action_space_hash, artifact_render_tokens,
                              build_sbr_system)

from tests.fixtures.prf3_wire.build import write_fixture

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "prf3_wire"


def _wire_fixture() -> Path:
    dst = Path(tempfile.mkdtemp()) / "prf3-wire"
    write_fixture(dst)
    return dst


def _rows(ledger_path: Path, kind: str) -> list[dict]:
    return [json.loads(line) for line in ledger_path.read_text().splitlines()
            if json.loads(line).get("kind") == kind]


class TestRHandleParser(unittest.TestCase):
    VISIBLE = ["L01", "L02", "STOP"]

    def test_stop_and_read_case_whitespace(self):
        a, r = parse_r_handle_action("  stop  ", ["L01", "L02"])
        self.assertIsNone(r)
        self.assertEqual(a, {"action": "STOP"})
        a2, r2 = parse_r_handle_action("r01", ["L01", "L02"])
        self.assertIsNone(r2)
        self.assertEqual(a2, {"action": "READ", "surface_id": "L01"})

    def test_illegal_handle_refused(self):
        _, r = parse_r_handle_action("R99", ["L01", "L02"])
        self.assertEqual(r, "illegal_handle:R99")
        _, r2 = parse_r_handle_action("R00", ["L01"])
        self.assertEqual(r2, "illegal_handle:R00")

    def test_v03_fork_uses_handles(self):
        a, r = parse_action('{"action":"READ","surface_id":"L01"}',
                            ["L01"], "0.3")
        self.assertEqual(r, "not_json")
        a2, r2 = parse_action("R01", ["L01"], "0.3")
        self.assertIsNone(r2)
        self.assertEqual(a2["surface_id"], "L01")

    def test_illegal_handle_burns_step_not_surcharge(self):
        fx = _wire_fixture()
        ep = fx / "ep-baseline.json"
        scripts = {"cold_reread": [["R99", "R01", "STOP"]],
                   "resumable_state": [["R01", "STOP"]]}
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            run_and_score(ep, ledger_path=ledger, scripted_sessions=scripts)
            decisions = _rows(ledger, "route_decision")
            refused = [d for d in decisions if d.get("refuse_reason")]
            self.assertEqual(refused[0]["refuse_reason"], "illegal_handle:R99")
            self.assertNotIn("surcharge", ledger.read_text().lower())


class TestActionSpaceHash(unittest.TestCase):
    def test_v03_bumps_hash(self):
        self.assertNotEqual(action_space_hash("0.2"), action_space_hash("0.3"))


class TestRenderAlignment(unittest.TestCase):
    def test_a_i_guard_blocks_seeded_mismatch(self):
        fx = _wire_fixture()
        ep_path = fx / "ep-baseline.json"
        ep = json.loads(ep_path.read_text())
        pop = json.loads((fx / "population.json").read_text())
        freeze = json.loads((fx / "freeze_manifest.json").read_text())
        with tempfile.TemporaryDirectory() as td:
            ledger = Ledger(Path(td) / "mint.jsonl")
            mint = run_mint_spine(ep, pop, freeze, ledger)
            canonical = mint["canonical_state"]
            rendered = artifact_render_tokens(canonical)
            body = recompute_state_tokens(canonical)
            self.assertNotEqual(rendered, body)

            events = ledger.rows()
            minted = next(r for r in events if r["kind"] == "frontier_state_minted")
            minted["state_tokens"] = body  # seeded mismatch
            events = [minted if r.get("kind") == "frontier_state_minted" else r
                      for r in events]
            events.append({
                "kind": "run_config", "instrument_version": "0.3",
                "wire_test": True, "engine": "mock",
            })
            events.append({"kind": "gate_open", "checks": 1})
            scorer = PRFScorer(population=pop, freeze_manifest=freeze,
                               events=events, episode=ep)
            verdict = scorer.score()
            self.assertEqual(verdict["cell"], "confounded")
            self.assertFalse(verdict["guards"]["a_i_recomputed_ok"])


class TestV03FixtureGate(unittest.TestCase):
    def test_wire_fixture_gate_open(self):
        fx = _wire_fixture()
        checks = check_manifest(fx / "manifest.json")
        failed = {n for n, ok, _ in checks if not ok}
        self.assertEqual(failed, set(), msg=f"refused: {failed}")

    def test_pay_window_geometry_refuse(self):
        def mutate(d: Path):
            ep = json.loads((d / "ep-baseline.json").read_text())
            ep["cold_exploration_route"] = ep["calibration_route"]
            (d / "ep-baseline.json").write_text(json.dumps(ep))
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "fx"
            shutil.copytree(_wire_fixture(), dst)
            ep = json.loads((dst / "ep-baseline.json").read_text())
            ep["cold_exploration_route"] = ep["calibration_route"]
            (dst / "ep-baseline.json").write_text(json.dumps(ep))
            failed = {n for n, ok, _ in check_manifest(dst / "manifest.json")
                      if not ok}
            self.assertTrue(any("pay_window_geometry" in n for n in failed))

    def test_foreground_budget_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "fx"
            shutil.copytree(_wire_fixture(), dst)
            ep = json.loads((dst / "ep-baseline.json").read_text())
            ep["stale_claim"] = "x " * 400
            (dst / "ep-baseline.json").write_text(json.dumps(ep))
            failed = {n for n, ok, _ in check_manifest(dst / "manifest.json")
                      if not ok}
            self.assertTrue(any("foreground_budget_ok" in n for n in failed))

    def test_ballast_override_allowlist(self):
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "fx"
            shutil.copytree(_wire_fixture(), dst)
            ep = json.loads((dst / "ep-ballast.json").read_text())
            ep["stale_claim"] = "forbidden stale override on ballast analog"
            (dst / "ep-ballast.json").write_text(json.dumps(ep))
            failed = {n for n, ok, _ in check_manifest(dst / "manifest.json")
                      if not ok}
            self.assertIn("variant_declared_overrides_only[prf3-wire-ballast]",
                          failed)


class TestCalibrationWire(unittest.TestCase):
    def test_scripted_calibration_gate_pass(self):
        fx = _wire_fixture()
        ep = json.loads((fx / "ep-baseline.json").read_text())
        pop = json.loads((fx / "population.json").read_text())
        freeze = json.loads((fx / "freeze_manifest.json").read_text())
        from harness.sbr_util import sorted_surface_ids
        visible = sorted_surface_ids(ep["catalog"], "by_id")
        handles = [f"R{visible.index(s) + 1:02d}"
                   for s in ep["calibration_route"]] + ["STOP"]
        with tempfile.TemporaryDirectory() as td:
            ledger = Ledger(Path(td) / "cal.jsonl")
            ledger.write(pop)
            mint = run_mint_spine(ep, pop, freeze, ledger)
            row = run_calibration_gate(
                ep, mint["canonical_state"], ledger,
                scripted_actions=handles, elicit_answer=False)
            self.assertTrue(row["passed"])
            self.assertEqual(row["read_ids"], ep["calibration_route"])

    def test_run_and_score_skips_calibration_wire_test(self):
        fx = _wire_fixture()
        ep_path = fx / "ep-baseline.json"
        visible = None
        from harness.sbr_util import sorted_surface_ids
        ep = json.loads(ep_path.read_text())
        visible = sorted_surface_ids(ep["catalog"], "by_id")
        h1 = f"R{visible.index('L01') + 1:02d}"
        scripts = {
            "cold_reread": [[h1, "STOP"]],
            "resumable_state": [[h1, "STOP"]],
        }
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            out = run_and_score(ep_path, ledger_path=ledger,
                                scripted_sessions=scripts)
            self.assertIsNotNone(out["verdict"])
            cal = _rows(ledger, "calibration_gate")
            self.assertEqual(len(cal), 1)
            self.assertTrue(cal[0].get("skipped"))
            self.assertEqual(cal[0].get("disclosure"), "wire_test")

    def test_decision_read_chain_ok_r_handles(self):
        fx = _wire_fixture()
        ep = json.loads((fx / "ep-baseline.json").read_text())
        pop = json.loads((fx / "population.json").read_text())
        freeze = json.loads((fx / "freeze_manifest.json").read_text())
        from harness.sbr_util import sorted_surface_ids
        visible = sorted_surface_ids(ep["catalog"], "by_id")
        h1 = f"R{visible.index('L01') + 1:02d}"
        with tempfile.TemporaryDirectory() as td:
            ledger = Ledger(Path(td) / "s.jsonl")
            mint = run_mint_spine(ep, pop, freeze, ledger)
            from harness.engine import MockEngine
            session = MockEngine(scripted_actions=[h1, "STOP"]).start_session()
            run_sbr_session(
                ep, "cold_reread", "s1", 0, session, ledger,
                canonical_state=mint["canonical_state"])
            events = ledger.rows()
            scorer = PRFScorer(events=events, episode=ep)
            self.assertTrue(scorer._decision_read_chain_ok("cold_reread", "s1"))


class TestV03MenuPresentation(unittest.TestCase):
    def test_build_sbr_system_shows_handles(self):
        fx = _wire_fixture()
        ep = json.loads((fx / "ep-baseline.json").read_text())
        system = build_sbr_system(ep["catalog"], "by_id", ep["question"], "0.3")
        self.assertIn("R01:", system)
        self.assertIn("Legal actions: R01–R21 or STOP", system)
        self.assertNotIn('"action":"READ"', system)


if __name__ == "__main__":
    unittest.main()
