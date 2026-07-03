"""Wire tests for the PRF real-engine path (SPEC_PAUSE_RESUME v0.1 §6/§4c-1).

MockEngine-driven, no network: proves frozen-prefix surface injection,
authored-oracle branch_outcome minting, multi-sample disclosure, and
ablation_adequacy row emission. CLI `--engine mock` stays fixture-oracle;
tests pass an explicit engine instance to exercise the oracle path.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.engine import MockEngine, build_prompt
from harness.run_prf import (
    SINGLE_DRAW_DISCLOSURE,
    run_and_score,
    run_ignorance_probe,
)

FIXTURE = Path(__file__).resolve().parent.parent / "episodes" / "prf" / "meridian"
EP_WIN = FIXTURE / "ep-win.json"


def _rows(ledger_path: Path, kind: str) -> list[dict]:
    return [json.loads(line) for line in ledger_path.read_text().splitlines()
            if json.loads(line).get("kind") == kind]


class TestEnginePath(unittest.TestCase):
    def test_surface_injection_route_order_and_oracle_mint(self):
        """Prompt carries t1 surfaces in route order; oracle mints outcomes."""
        calls: list[tuple[str, list[str], str]] = []

        class CapturingMock(MockEngine):
            def run(self, question, offered_texts, foreground_block=""):
                calls.append((question, list(offered_texts), foreground_block))
                return super().run(question, offered_texts, foreground_block)

        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            out = run_and_score(
                EP_WIN, ledger_path=ledger, engine=CapturingMock(), samples=2)
            self.assertIsNotNone(out["verdict"])

            cfg = _rows(ledger, "run_config")[0]
            self.assertFalse(cfg["wire_test"])
            self.assertEqual(cfg["samples"], 2)

            outcomes = {r["branch"]: r for r in _rows(ledger, "branch_outcome")}
            self.assertEqual(outcomes["cold_reread"]["oracle_source"],
                             "authored_oracle:fictional_meridian")
            self.assertEqual(outcomes["cold_reread"]["samples"], 2)
            self.assertEqual(len(outcomes["cold_reread"]["sample_scores"]), 2)
            self.assertIn("quality_ok", outcomes["cold_reread"])
            self.assertNotEqual(outcomes["cold_reread"]["oracle_source"],
                                "fixture_mock")

            ep = json.loads(EP_WIN.read_text())
            cold_route = ep["routes"]["cold_reread"]
            res_route = ep["routes"]["resumable_state"]
            self.assertEqual(outcomes["cold_reread"]["injected_route"],
                             cold_route)
            self.assertEqual(outcomes["resumable_state"]["injected_route"],
                             res_route)
            res_calls = [c for c in calls if c[2]]
            cold_calls = [c for c in calls if not c[2] and len(c[1]) == len(cold_route)]
            self.assertTrue(res_calls)
            self.assertTrue(cold_calls)
            self.assertEqual(
                cold_calls[0][1],
                [ep["t1_texts"][sid] for sid in cold_route])

    def test_ablation_adequacy_row_emitted(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            run_and_score(EP_WIN, ledger_path=ledger, engine=MockEngine(),
                          samples=1)
            rows = _rows(ledger, "ablation_adequacy")
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertIn("ablated_quality_ok", row)
            self.assertEqual(row["samples"], 1)
            self.assertIn("sample_scores", row)
            self.assertIn("covered_surfaces", row)
            ep = json.loads(EP_WIN.read_text())
            covered = set(row["covered_surfaces"])
            ablated = [sid for sid in ep["witness_route"] if sid not in covered]
            self.assertEqual(row["ablated_witness_route"], ablated)

    def test_single_draw_disclosure(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            run_and_score(EP_WIN, ledger_path=ledger, engine=MockEngine(),
                          samples=1)
            outcome = _rows(ledger, "branch_outcome")[0]
            self.assertTrue(outcome["single_draw_inadmissible"])
            self.assertEqual(outcome["determinism_disclosure"],
                             SINGLE_DRAW_DISCLOSURE)

    def test_mock_cli_path_unchanged_fixture_oracle(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            run_and_score(EP_WIN, ledger_path=ledger)
            outcomes = _rows(ledger, "branch_outcome")
            self.assertTrue(all(r["oracle_source"] == "fixture_mock"
                                for r in outcomes))
            self.assertEqual(len(_rows(ledger, "ablation_adequacy")), 0)

    def test_build_prompt_injects_surfaces_in_order(self):
        ep = json.loads(EP_WIN.read_text())
        route = ep["routes"]["cold_reread"]
        offered = [ep["t1_texts"][sid] for sid in route]
        prompt = build_prompt(ep["question"], offered)
        pos = [prompt.index(ep["t1_texts"][sid][:40]) for sid in route]
        self.assertEqual(pos, sorted(pos))

    def test_ignorance_probe_mock_cold(self):
        probe = run_ignorance_probe(MockEngine())
        self.assertFalse(probe["knew"])


if __name__ == "__main__":
    unittest.main()
