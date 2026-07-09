"""Wire tests for the Phase-0 admission packet (pins P-A1'..P-A7, 2026-07-09).

Mock/scripted only — never an admission. Encodes the kimi/grok round:
the Bessel counterexample is a seeded regression (a pilot the population
closed form admits and the harness N-rule confounds must be REFUSED).
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from harness.engine import MockEngine
from harness.ledger import Ledger
from harness.run_prf_admission import admission_metrics, run_admission_packet
from harness.run_sbr import pilot_n_rule
from harness.sbr_util import sorted_surface_ids

from tests.fixtures.prf4_wire.build import DECOY_IDS, LEG_IDS, write_fixture


def _wire_fixture(**kw) -> Path:
    dst = Path(tempfile.mkdtemp()) / "prf-admission-wire"
    write_fixture(dst, **kw)
    return dst


def _handles(episode: dict) -> dict[str, str]:
    visible = sorted_surface_ids(episode["catalog"], episode["catalog_sort"])
    return {sid: f"R{visible.index(sid) + 1:02d}" for sid in visible}


def _episode_stub(leg_tokens: int = 100) -> dict:
    return {
        "dispositive_leg_ids": list(LEG_IDS),
        "catalog": {leg: {"text": " ".join(["w"] * leg_tokens),
                          "tokens": leg_tokens} for leg in LEG_IDS},
        "budgets": {"max_read_tokens": 700, "max_steps": 10,
                    "action_overhead_tokens": 20},
        "regime_s": {"n_max": 24, "ci_halfwidth_tokens": 100,
                     "dispersion_probe_k": 5},
    }


def _summary(read_ids: tuple, tokens: int, ok: bool) -> dict:
    return {"read_ids": read_ids, "read_tokens": tokens, "quality_ok": ok}


class TestPilotNRule(unittest.TestCase):
    """The shared N-rule code path — grok's break as seeded regressions."""

    def test_grok_counterexample_confounds(self):
        # k=5 corner: population variance 28,900 (green under the closed
        # form) but Bessel var_H = 36,125 -> n_required 28 > 24.
        var, n_req, unmet = pilot_n_rule([475, 475, 475, 475, 900], 100, 24)
        self.assertAlmostEqual(var, 36125.0)
        self.assertEqual(n_req, 28)
        self.assertTrue(unmet)

    def test_k6_corner_survives_exactly(self):
        var, n_req, unmet = pilot_n_rule([510, 510, 510, 510, 900], 100, 24)
        self.assertAlmostEqual(var, 30420.0)
        self.assertEqual(n_req, 24)
        self.assertFalse(unmet)

    def test_floor_at_two(self):
        var, n_req, unmet = pilot_n_rule([500, 500, 500, 500, 500], 100, 24)
        self.assertEqual((var, n_req, unmet), (0.0, 2, False))


class TestAdmissionMetrics(unittest.TestCase):
    """Pure predicate over synthetic pilots — each P-A leg exercised."""

    def test_admitted(self):
        ep = _episode_stub()
        route = tuple(DECOY_IDS) + tuple(LEG_IDS)
        pilots = [_summary(route, 510, True) for _ in range(5)]
        m = admission_metrics(ep, pilots, a_i=56)
        self.assertEqual(m["verdict"], "admitted")
        self.assertEqual(m["cold_pass_rate"], 1.0)
        self.assertEqual(m["mean_decoy_reads_on_successes"], 6.0)
        self.assertEqual(m["n_required"], 2)
        self.assertAlmostEqual(m["effect_size_est"], 510 - 356)

    def test_grok_corner_refused_end_to_end(self):
        # outer gate green (4/5), margin green (5 decoys), effect green —
        # and the harness estimator still refuses (n_required 28 > 24).
        ep = _episode_stub()
        route = tuple(DECOY_IDS[:5]) + tuple(LEG_IDS)
        pilots = [_summary(route, 475, True) for _ in range(4)]
        pilots.append(_summary(tuple(DECOY_IDS[:2]), 70, False))
        m = admission_metrics(ep, pilots, a_i=65)
        self.assertTrue(m["legs"]["outer_pass_rate"])
        self.assertTrue(m["legs"]["ineq1_decoy_reads"])
        self.assertTrue(m["legs"]["ineq3_effect_size"])
        self.assertFalse(m["legs"]["ineq2_n_required"])
        self.assertEqual(m["n_required"], 28)
        self.assertEqual(m["verdict"], "admission_refused")

    def test_marginal_when_only_outer_fails(self):
        # 3/5 passes reading expensively (near c_max) keeps var_H tiny:
        # inner inequalities pass, outer 0.6 < 0.8 -> marginal, not admitted.
        ep = _episode_stub()
        route = tuple(DECOY_IDS) + tuple(LEG_IDS)
        pilots = [_summary(route, 860, True) for _ in range(3)]
        pilots += [_summary(tuple(DECOY_IDS[:2]), 70, False)] * 2
        m = admission_metrics(ep, pilots, a_i=56)
        self.assertFalse(m["legs"]["outer_pass_rate"])
        self.assertTrue(m["legs"]["ineq1_decoy_reads"])
        self.assertTrue(m["legs"]["ineq2_n_required"])
        self.assertTrue(m["legs"]["ineq3_effect_size"])
        self.assertEqual(m["verdict"], "admission_marginal")

    def test_margin_dies_at_four_decoy_reads(self):
        ep = _episode_stub()
        route = tuple(DECOY_IDS[:4]) + tuple(LEG_IDS)
        pilots = [_summary(route, 440, True) for _ in range(5)]
        m = admission_metrics(ep, pilots, a_i=65)
        self.assertFalse(m["legs"]["ineq1_decoy_reads"])
        self.assertEqual(m["verdict"], "admission_refused")

    def test_denominator_is_all_k_draws(self):
        # P-A2: a refused/illegal draw (quality_ok=false, empty route)
        # stays in the denominator.
        ep = _episode_stub()
        route = tuple(DECOY_IDS) + tuple(LEG_IDS)
        pilots = [_summary(route, 510, True) for _ in range(4)]
        pilots.append(_summary((), 0, False))
        m = admission_metrics(ep, pilots, a_i=56)
        self.assertEqual(m["pilot_k"], 5)
        self.assertAlmostEqual(m["cold_pass_rate"], 0.8)
        # and the fail is priced at c_max in the vector (P-A7)
        self.assertEqual(m["pilot_cost_vector"][-1], 900)

    def test_all_fail_pilot_refused_without_success_stats(self):
        ep = _episode_stub()
        pilots = [_summary(tuple(DECOY_IDS[:2]), 70, False)] * 5
        m = admission_metrics(ep, pilots, a_i=56)
        self.assertEqual(m["verdict"], "admission_refused")
        self.assertIsNone(m["mean_decoy_reads_on_successes"])
        self.assertIsNone(m["success_cost_mean"])


class TestAdmissionPacketWire(unittest.TestCase):
    """End-to-end mock packet over the wire fixture."""

    def _run(self, fixture: Path, routes: list[list[str]], name: str) -> dict:
        ep = json.loads((fixture / "ep-baseline.json").read_text())
        handles = _handles(ep)
        sessions = [
            MockEngine(scripted_actions=[handles[s] for s in r]
                       + ["STOP"]).start_session()
            for r in routes]
        return run_admission_packet(
            fixture / "ep-baseline.json",
            scripted_factory=lambda i: sessions[i],
            ledger_path=fixture / f"{name}.jsonl")

    def test_wire_packet_admitted_shape(self):
        fixture = _wire_fixture()
        routes = [DECOY_IDS + LEG_IDS] * 5
        out = self._run(fixture, routes, "admit")
        packet = out["packet"]
        self.assertEqual(packet["verdict"], "admitted")
        self.assertTrue(packet["wire_test"])
        self.assertTrue(packet["resumable_routing_untested"])
        self.assertEqual(len(packet["pilot_cost_vector"]), 5)
        self.assertEqual(packet["pin_round"],
                         "fourth-family pins P-A1'..P-A7 (adopted 2026-07-09)")
        rows = [json.loads(l) for l in
                (fixture / "admit.jsonl").read_text().splitlines()]
        self.assertEqual(
            sum(1 for r in rows if r["kind"] == "admission_packet"), 1)
        # review F1/F2 (kimi/grok): the packet a_i must be the SAME quantity
        # the live scorer prices — the minted state_tokens (rendered fork on
        # v0.3/0.4), asserted against the ledger row, not a label
        minted = [r for r in rows if r["kind"] == "frontier_state_minted"]
        self.assertEqual(len(minted), 1)
        self.assertEqual(packet["a_i"], minted[0]["state_tokens"])
        from harness.mint_frontier_state import recompute_a_i
        from harness.sbr_util import artifact_render_tokens
        freeze = [r for r in rows if r["kind"] == "frontier_freeze"][0]
        self.assertEqual(
            packet["a_i"],
            recompute_a_i(freeze["canonical_state"],
                          packet["instrument_version"]))
        self.assertEqual(packet["a_i"],
                         artifact_render_tokens(freeze["canonical_state"]))
        # grok's next-second-way (discharge round): l_bar must be priced the
        # way the instrument prices reads — _tokens over surface TEXT
        from harness.run_sbr import _tokens
        ep = json.loads((fixture / "ep-baseline.json").read_text())
        expected_l_bar = sum(
            _tokens(ep["catalog"][leg]["text"])
            for leg in ep["dispositive_leg_ids"]) / 3
        self.assertEqual(packet["l_bar_canonical"], expected_l_bar)
        shutil.rmtree(fixture.parent)

    def test_real_engine_refused_without_probe_contract(self):
        # review F1 (codex/gemini): no fixture probe contract -> refuse the
        # real engine outright rather than probing the wrong world
        fixture = _wire_fixture()

        class FakeEngine:
            backend_name = "local"
            model = "fake/engine"
            temperature = 0.5
        out = run_admission_packet(
            fixture / "ep-baseline.json", engine=FakeEngine(),
            engine_label="fake/engine",
            ledger_path=fixture / "noprobe.jsonl")
        self.assertEqual(out["halted"], "admission_refused")
        self.assertEqual(out["reason"], "probe_contract_missing")
        shutil.rmtree(fixture.parent)

    def test_default_ledger_label_sanitized(self):
        # review (codex): slash-bearing model ids must not nest the default
        # ledger path outside flat runs/prf scans
        fixture = _wire_fixture()
        ep = json.loads((fixture / "ep-baseline.json").read_text())
        handles = _handles(ep)
        routes = [DECOY_IDS + LEG_IDS] * 5
        sessions = [MockEngine(scripted_actions=[handles[s] for s in r]
                               + ["STOP"]).start_session() for r in routes]
        out = run_admission_packet(
            fixture / "ep-baseline.json",
            scripted_factory=lambda i: sessions[i],
            engine_label="openai/gpt-oss-20b")
        ledger = Path(out["ledger"])
        try:
            self.assertEqual(ledger.parent.name, "prf")
            self.assertIn("admission-openai-gpt-oss-20b", ledger.name)
        finally:
            ledger.unlink(missing_ok=True)
        shutil.rmtree(fixture.parent)

    def test_wire_packet_refused_on_lazy_routes(self):
        # committed-record shape: routes that never assemble the triple
        fixture = _wire_fixture()
        routes = [["N29", "N31", "B01"], ["X31", "N29", "N31", "B01"],
                  ["B01", "B02"], DECOY_IDS[:3], DECOY_IDS[3:]]
        out = self._run(fixture, routes, "refuse")
        self.assertEqual(out["packet"]["verdict"], "admission_refused")
        self.assertEqual(out["packet"]["cold_pass_rate"], 0.0)
        shutil.rmtree(fixture.parent)

    def test_never_overwrites_a_ledger(self):
        fixture = _wire_fixture()
        routes = [DECOY_IDS + LEG_IDS] * 5
        self._run(fixture, routes, "once")
        with self.assertRaises(SystemExit):
            self._run(fixture, routes, "once")
        shutil.rmtree(fixture.parent)


if __name__ == "__main__":
    unittest.main()
