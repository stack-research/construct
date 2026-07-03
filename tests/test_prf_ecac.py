"""Wire tests for ECAC scoring (SPEC_PAUSE_RESUME Part II §16/§18/§21).

MockEngine scripted sessions: win/loss/c_max pricing, a_i inclusion,
quality_threshold, zero-dispersion downgrade, ballast-null and neutral-null
self-refutation, skip-set derivation, false_continuation predicate. No network.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.run_sbr import run_and_score
from harness.score_prf import PRFScorer
from harness.sbr_util import render_foreground_block

FIXTURE = Path(__file__).resolve().parent.parent / "episodes" / "prf" / "sbr-meridian"
EP_T = FIXTURE / "ep-temptation.json"
EP_B = FIXTURE / "ep-ballast-discriminator.json"
EP_N = FIXTURE / "ep-neutral-frontier.json"

READ_S1 = '{"action":"READ","surface_id":"S1"}'
READ_S7 = '{"action":"READ","surface_id":"S7"}'
STOP = '{"action":"STOP"}'
SKIP_STOP = '{"action":"STOP"}'  # stop without reading discriminator


def _run(ep: Path, cold_script: list[str], res_script: list[str]) -> dict:
    with tempfile.TemporaryDirectory() as td:
        ledger = Path(td) / "out.jsonl"
        out = run_and_score(
            ep, ledger_path=ledger,
            scripted_sessions={
                "cold_reread": [cold_script],
                "resumable_state": [res_script],
            })
        return out["verdict"]


class TestECACArithmetic(unittest.TestCase):
    def test_a_i_resumable_nonzero_cold_zero(self):
        ep = json.loads(EP_T.read_text())
        fg = ep["resumable_foreground"]
        self.assertGreater(len(render_foreground_block(fg).split()), 0)
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            out = run_and_score(
                EP_T, ledger_path=ledger,
                scripted_sessions={
                    "cold_reread": [[READ_S1, STOP]],
                    "resumable_state": [[READ_S1, STOP]],
                })
            ecac = out["verdict"]["ecac"]
            self.assertGreater(ecac["a_i_resumable"], 0)
            self.assertEqual(ecac["a_i_cold"], 0)

    def test_c_max_replay_ok(self):
        verdict = _run(EP_T, [READ_S1, STOP], [READ_S1, STOP])
        self.assertTrue(verdict["guards"]["c_max_replay_ok"])

    def test_quality_failure_priced_at_c_max(self):
        """Resumable skips discriminator → inadequate → c_max."""
        verdict = _run(EP_T, [READ_S1, STOP], [SKIP_STOP])
        ecac = verdict["ecac"]
        self.assertEqual(ecac["mean_eff_resumable"], ecac["c_max"])

    def test_skip_set_scorer_derived(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            run_and_score(
                EP_T, ledger_path=ledger,
                scripted_sessions={
                    "cold_reread": [[READ_S1, STOP]],
                    "resumable_state": [[SKIP_STOP]],
                })
            events = [json.loads(l) for l in ledger.read_text().splitlines()]
            ep = json.loads(EP_T.read_text())
            scorer = PRFScorer(events=events, episode=ep)
            sessions = [r for r in events if r["kind"] == "sbr_session"
                        and r["branch"] == "resumable_state"]
            sid = sessions[0]["session_id"]
            visible, read, skip = scorer._route_session(
                "resumable_state", sid, 0)
            self.assertIn("S1", skip)
            self.assertNotIn("S1", read)


class TestFalseContinuation(unittest.TestCase):
    def test_false_continuation_on_stale_skip(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            run_and_score(
                EP_T, ledger_path=ledger,
                scripted_sessions={
                    "cold_reread": [[READ_S1, STOP]],
                    "resumable_state": [[SKIP_STOP]],
                })
            events = [json.loads(l) for l in ledger.read_text().splitlines()]
            ep = json.loads(EP_T.read_text())
            scorer = PRFScorer(events=events, episode=ep)
            sessions = [r for r in events if r["kind"] == "sbr_session"
                        and r["branch"] == "resumable_state"][0]
            outcome = next(r for r in events
                           if r.get("kind") == "session_outcome"
                           and r["session_id"] == sessions["session_id"])
            fc = scorer._false_continuation(
                "resumable_state", sessions["session_id"], 0,
                outcome["quality_ok"])
            self.assertTrue(fc)


class TestSelfFalsificationCells(unittest.TestCase):
    def test_ballast_null_fires_on_spurious_win(self):
        """Ballast discriminator: resumable wins on ECAC → self-refute."""
        verdict = _run(EP_B, [SKIP_STOP], [READ_S1, STOP])
        self.assertEqual(verdict["cell"], "PRF2-ballast-null")

    def test_neutral_null_fires_on_resumable_win(self):
        """Neutral frontier: any resumable ECAC win is self-refutation."""
        verdict = _run(EP_N, [SKIP_STOP], [READ_S1, STOP])
        self.assertEqual(verdict["cell"], "PRF2-neutral-null")


class TestZeroDispersion(unittest.TestCase):
    def test_zero_dispersion_cell(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            from harness.ledger import Ledger
            from harness.run_sbr import run_episode

            ep = json.loads(EP_T.read_text())
            led = Ledger(ledger)
            led.write({"kind": "gate_open", "checks": 1})
            led.write({
                "kind": "run_config",
                "instrument_version": "0.2",
                "engine": "mock",
                "wire_test": True,
                "episode_id": ep["episode_id"],
                "regime": "S",
                "unique_realizations": 1,
                "dispersion_probe_k": 5,
                "quality_threshold": 1.0,
            })
            led.write({"kind": "zero_dispersion_regime",
                       "unique_realizations": 1, "dispersion_probe_k": 5})
            scripts = {
                "cold_reread": [[READ_S1, STOP]],
                "resumable_state": [[READ_S1, STOP]],
            }
            run_episode(ep, led, scripted_sessions=scripts)
            events = led.rows()
            scorer = PRFScorer(events=events, episode=ep)
            verdict = scorer.score()
            self.assertEqual(verdict["cell"], "PRF2-zero-dispersion")


if __name__ == "__main__":
    unittest.main()
