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
from harness.mint_frontier_state import recompute_state_tokens
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
        stale = ep.get("stale_claim")
        if stale:
            self.assertGreater(len(render_foreground_block(stale).split()), 0)
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

    def test_a_i_resumable_positive_on_neutral_frontier(self):
        """§20 falsifier anchor: neutral pays artifact carry without stale claim."""
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            out = run_and_score(
                EP_N, ledger_path=ledger,
                scripted_sessions={
                    "cold_reread": [[READ_S1, STOP]],
                    "resumable_state": [[READ_S1, STOP]],
                })
            ecac = out["verdict"]["ecac"]
            self.assertGreater(ecac["a_i_resumable"], 0)
            self.assertEqual(ecac["a_i_cold"], 0)
            self.assertEqual(ecac.get("stale_claim_tokens", 0), 0)

    def test_a_i_matches_recompute_state_tokens(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            out = run_and_score(
                EP_T, ledger_path=ledger,
                scripted_sessions={
                    "cold_reread": [[READ_S1, STOP]],
                    "resumable_state": [[READ_S1, STOP]],
                })
            events = [json.loads(l) for l in ledger.read_text().splitlines()]
            freeze = next(r for r in events if r["kind"] == "frontier_freeze")
            expected = recompute_state_tokens(freeze["canonical_state"])
            self.assertEqual(out["verdict"]["ecac"]["a_i_resumable"], expected)

    def test_v02_scoring_confounded_without_mint_rows(self):
        """Non-mock scoring refuses ledgers lacking population_precommit + mint."""
        ep = json.loads(EP_T.read_text())
        pop = json.loads((FIXTURE / "population.json").read_text())
        freeze = json.loads((FIXTURE / "freeze_manifest.json").read_text())
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            run_and_score(EP_T, ledger_path=ledger,
                          scripted_sessions={
                              "cold_reread": [[READ_S1, STOP]],
                              "resumable_state": [[READ_S1, STOP]],
                          },
                          skip_mint=True)
            events = [json.loads(l) for l in ledger.read_text().splitlines()]
            scorer = PRFScorer(
                population=pop, freeze_manifest=freeze,
                events=events, episode=ep)
            verdict = scorer.score()
            self.assertEqual(verdict["cell"], "confounded")

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
        self.assertGreater(verdict["ecac"]["a_i_resumable"], 0)


class TestZeroDispersion(unittest.TestCase):
    def test_zero_dispersion_cell(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "out.jsonl"
            from harness.ledger import Ledger
            from harness.run_sbr import run_episode, run_mint_spine

            ep = json.loads(EP_T.read_text())
            pop = json.loads((FIXTURE / "population.json").read_text())
            freeze = json.loads((FIXTURE / "freeze_manifest.json").read_text())
            led = Ledger(ledger)
            led.write({"kind": "gate_open", "checks": 1})
            mint = run_mint_spine(ep, pop, freeze, led)
            canonical = mint["canonical_state"]
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
            run_episode(ep, led, canonical_state=canonical,
                        scripted_sessions=scripts)
            events = led.rows()
            scorer = PRFScorer(
                population=pop, freeze_manifest=freeze,
                events=events, episode=ep)
            verdict = scorer.score()
            self.assertEqual(verdict["cell"], "PRF2-zero-dispersion")


class _FakeSession:
    """Real-engine-shaped session: scripted actions, then a final answer for
    the elicitation step."""

    def __init__(self, actions: list[str], answer: str):
        self._actions = list(actions)
        self._answer = answer

    def step(self, observation: str):
        class R:
            pass
        r = R()
        r.raw_action = (self._actions.pop(0) if self._actions
                        else self._answer)
        return r


class _FakeEngine:
    backend_name = "fake-real"
    # attested label in the sbr-meridian manifest: the run-time ignorance-
    # probe teeth (A1 enforcement, 2026-07-06) refuse un-attested real
    # engines at run entry — the fake wears a probed engine's label
    model = "openai/gpt-oss-20b"

    def __init__(self, sessions: list[_FakeSession]):
        self._sessions = list(sessions)
        self._i = 0

    def start_session(self, *a, **k):
        s = self._sessions[self._i % len(self._sessions)]
        self._i += 1
        return _FakeSession(list(s._actions), s._answer)


class TestRealEngineLeg(unittest.TestCase):
    """Answer elicitation + oracle-key false_continuation + §17 N-rule."""

    def test_elicited_answer_and_oracle_key_false_continuation(self):
        ep = json.loads(EP_T.read_text())
        t1 = ep["expected_answer_t1"]
        stale = ep["expected_answer_t0"]
        engine = _FakeEngine([])
        # cold reads the discriminator and answers fresh; resumable skips it
        # and answers the stale state — the §18 event, oracle-key matched
        engine._sessions = [
            _FakeSession([READ_S1, STOP], t1),        # cold
            _FakeSession([STOP], stale),              # resumable
        ]
        with tempfile.TemporaryDirectory() as td:
            out = run_and_score(EP_T, ledger_path=Path(td) / "o.jsonl",
                                engine=engine, engine_backend="fake-real")
            v = out["verdict"]
            self.assertNotEqual(v["cell"], "confounded")
            self.assertEqual(v["ecac"]["false_continuation_basis"],
                             "oracle_key:expected_answer_t0")
            self.assertEqual(
                v["ecac"]["false_continuation_rate"]["resumable_state"], 1.0)
            self.assertEqual(
                v["ecac"]["false_continuation_rate"]["cold_reread"], 0.0)
            rows = [json.loads(l) for l in
                    (Path(td) / "o.jsonl").read_text().splitlines()]
            outcomes = [r for r in rows if r["kind"] == "session_outcome"]
            self.assertTrue(outcomes)
            self.assertTrue(all(r["answer_source"] == "engine_elicited"
                                for r in outcomes))

    def test_n_rule_executes_and_ci_target_unmet_confounds(self):
        ep = json.loads(EP_T.read_text())
        t1 = ep["expected_answer_t1"]
        # High-variance pilot: some probe draws fail quality (priced c_max),
        # some succeed cheap -> n_required blows past n_max -> ci_target_unmet
        # -> the scorer refuses EVERY behavioral cell (§17, symmetric).
        engine = _FakeEngine([
            _FakeSession([READ_S1, STOP], t1),               # cheap success
            _FakeSession([READ_S7, STOP], "no idea"),        # c_max failure
        ])
        with tempfile.TemporaryDirectory() as td:
            out = run_and_score(EP_T, ledger_path=Path(td) / "o.jsonl",
                                engine=engine, engine_backend="fake-real",
                                regime="S")
            v = out["verdict"]
            rows = [json.loads(l) for l in
                    (Path(td) / "o.jsonl").read_text().splitlines()]
            cfg = next(r for r in rows if r["kind"] == "run_config")
            self.assertIsNotNone(cfg["pilot_variance"])
            self.assertGreater(cfg["n_required"], cfg["n_max"])
            self.assertTrue(cfg["ci_target_unmet"])
            self.assertEqual(v["cell"], "confounded")
            self.assertIn("CI target unmet", " ".join(v["evidence"]))


if __name__ == "__main__":
    unittest.main()
