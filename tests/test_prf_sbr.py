"""Wire tests for SBR loop mechanics (SPEC_PAUSE_RESUME Part II §15).

MockEngine scripted-action tests: actions parsed, budgets enforced,
forced_stop recomputed, rows emitted, illegal actions refused-and-ledgered.
No network.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.run_sbr import parse_structured_action, run_and_score

FIXTURE = Path(__file__).resolve().parent.parent / "episodes" / "prf" / "sbr-meridian"
EP = FIXTURE / "ep-temptation.json"

READ_S1 = '{"action":"READ","surface_id":"S1"}'
STOP = '{"action":"STOP"}'
ILLEGAL = '{"action":"FLY","surface_id":"S1"}'
PROSE = "I will read S1 now"


def _rows(ledger_path: Path, kind: str) -> list[dict]:
    return [json.loads(line) for line in ledger_path.read_text().splitlines()
            if json.loads(line).get("kind") == kind]


class TestActionParsing(unittest.TestCase):
    def test_read_and_stop_legal(self):
        a, r = parse_structured_action(READ_S1)
        self.assertIsNone(r)
        self.assertEqual(a, {"action": "READ", "surface_id": "S1"})
        a2, r2 = parse_structured_action(STOP)
        self.assertIsNone(r2)
        self.assertEqual(a2, {"action": "STOP"})

    def test_refuse_prose_and_illegal(self):
        _, r = parse_structured_action(PROSE)
        self.assertEqual(r, "not_json")
        _, r2 = parse_structured_action(ILLEGAL)
        self.assertTrue(r2.startswith("illegal_action"))


class TestSBRLoop(unittest.TestCase):
    def test_rows_emitted_and_reads_ledgered(self):
        scripts = {
            "cold_reread": [[READ_S1, STOP]],
            "resumable_state": [[READ_S1, STOP]],
        }
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            out = run_and_score(EP, ledger_path=ledger,
                                scripted_sessions=scripts)
            self.assertIsNotNone(out["verdict"])
            self.assertEqual(len(_rows(ledger, "sbr_session")), 2)
            self.assertTrue(len(_rows(ledger, "affordance_presented")) >= 24)
            self.assertEqual(len(_rows(ledger, "route_decision")), 4)
            reads = _rows(ledger, "surface_read")
            self.assertEqual(len(reads), 2)
            self.assertEqual(reads[0]["surface_id"], "S1")
            self.assertIn("session_id", reads[0])
            self.assertIn("step", reads[0])

    def test_illegal_action_refused_and_ledgered(self):
        scripts = {
            "cold_reread": [[ILLEGAL, READ_S1, STOP]],
            "resumable_state": [[READ_S1, STOP]],
        }
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            run_and_score(EP, ledger_path=ledger, scripted_sessions=scripts)
            decisions = _rows(ledger, "route_decision")
            refused = [d for d in decisions if d.get("refuse_reason")]
            self.assertTrue(refused)
            self.assertEqual(refused[0]["refuse_reason"], "illegal_action:FLY")

    def test_forced_stop_max_steps(self):
        read_s2 = '{"action":"READ","surface_id":"S2"}'
        scripts = {
            "cold_reread": [[read_s2] * 20],
            "resumable_state": [[READ_S1, STOP]],
        }
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            run_and_score(EP, ledger_path=ledger, scripted_sessions=scripts)
            forced = _rows(ledger, "forced_stop")
            self.assertTrue(any(f["stop_reason"] == "max_steps" for f in forced))

    def test_gate_open_required(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            run_and_score(EP, ledger_path=ledger,
                          scripted_sessions={
                              "cold_reread": [[READ_S1, STOP]],
                              "resumable_state": [[READ_S1, STOP]],
                          })
            self.assertEqual(len(_rows(ledger, "gate_open")), 1)

    def test_zero_dispersion_probe_row(self):
        """Identical probe realizations emit zero_dispersion_regime (§17)."""
        from harness.run_sbr import dispersion_probe, run_episode
        from harness.ledger import Ledger

        ep = json.loads(EP.read_text())
        with tempfile.TemporaryDirectory() as td:
            ledger = Ledger(Path(td) / "probe.jsonl")
            k = 3

            def factory(i: int):
                from harness.engine import MockEngine
                return MockEngine(scripted_actions=[READ_S1, STOP]).start_session()

            result = dispersion_probe(ep, factory, ledger, k)
            self.assertEqual(result["unique_realizations"], 1)
            rows = ledger.rows()
            self.assertTrue(any(r.get("kind") == "zero_dispersion_regime"
                                for r in rows))


if __name__ == "__main__":
    unittest.main()
