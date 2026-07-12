"""Wire tests for the §10.4 N-rule planner and §6 computed calibration gate.

Mock pilot numbers only — admission diagnostics machinery, never mechanism
evidence (§6). Two pins matter most:

1. §10.4's zero-variance guard: a K=5 binary pilot at an observed boundary
   cannot claim n_required = 0 — Wilson/Newcombe width stays real.
2. The structural refusal found at build time (2026-07-12), corrected by this
   very machinery mid-build: at N_MAX=24 and 95%, exactly TWO of the 625
   possible count configurations meet the sealed §10.3 non-inferiority
   half-width target of 0.10 — the total anti-correlated collapses
   (24/24 vs 0/24) and (0/24 vs 24/24), hw = 0.09756. Both are incoherent
   for the §9.2 NI loses-cells (the comparator lane must score 0.00 from an
   engine that simultaneously clears the §6 S1 >= 0.80 band). Every coherent
   pilot yields n_required > 24, so the sealed board computes
   confounded(ci_target_unmet) and refuses Part II (§10.4). The planner must
   report that honestly; it is Part I arithmetic, not a bug in this module.
   (First-draft claim "unreachable for ALL pilots" was wrong: the equal-arms
   minimum 0.13798 is not the global minimum. The sliver is pinned below.)
"""

from __future__ import annotations

import unittest

from harness import efc_contracts as c
from harness.efc_intervals import newcombe_diff_interval, half_width, welch_interval
from harness.efc_planner import (AdmissionInputs, AllOf, AnyOf, BinaryPilot,
                                 CollapseState, IgnoranceProbeResult,
                                 PlannedGate, PlannerContractError, Pilots,
                                 PopulationPilot, SBandCounts,
                                 StratumCostPilot, calibration_band_failures,
                                 calibration_gate, detect_collapse,
                                 n_required_binary, n_required_cost,
                                 n_required_population, planned_gates,
                                 projected_counts, resolve_gates, _ni, _sup,
                                 _population, STATUS_DEGENERATE, STATUS_MET,
                                 STATUS_UNMET)

MM, MC, IRR = c.STRATA


def _region():
    return [
        {"match_mismatch": 0.6, "match_commit": 0.2, "irrelevant": 0.2},
        {"match_mismatch": 0.1, "match_commit": 0.1, "irrelevant": 0.8},
        {"match_mismatch": 0.2, "match_commit": 0.6, "irrelevant": 0.2},
    ]


def _strong_population_pilot():
    # C much cheaper than the comparator in every stratum, tight variance
    return PopulationPilot(strata=(
        StratumCostPilot(MM, 300.0, 20.0, 500.0, 20.0),
        StratumCostPilot(MC, 300.0, 20.0, 500.0, 20.0),
        StratumCostPilot(IRR, 450.0, 20.0, 500.0, 20.0),
    ))


class TestBinaryNRule(unittest.TestCase):
    def test_perfect_split_superiority_needs_ten(self):
        # p_t=1.0 vs p_c=0.0: Newcombe hw <= 0.20 first holds at N=10
        req = n_required_binary(BinaryPilot(5, 5, 0, 5),
                                _sup("x", "9.2.1", MM, "C", "B"))
        self.assertEqual(req.status, STATUS_MET)
        self.assertEqual(req.n_required, 10)
        self.assertTrue(req.projected_clearance_diagnostic)

    def test_zero_variance_pilot_cannot_claim_zero(self):
        # §10.4: boundary-observed K=5 packet keeps nonzero width
        req = n_required_binary(BinaryPilot(5, 5, 0, 5),
                                _sup("x", "9.2.1", MM, "C", "B"))
        self.assertGreaterEqual(req.n_required, 10)
        hw2 = half_width(newcombe_diff_interval(2, 2, 0, 2, 0.95))
        self.assertGreater(hw2, 0.20)

    def test_minimality_boundary(self):
        req = n_required_binary(BinaryPilot(5, 5, 0, 5),
                                _sup("x", "9.2.1", MM, "C", "B"))
        n = req.n_required
        below = half_width(newcombe_diff_interval(n - 1, n - 1, 0, n - 1, 0.95))
        self.assertGreater(below, 0.20)
        self.assertLessEqual(req.achieved_half_width, 0.20)

    def test_ni_width_target_unreachable_for_coherent_pilots(self):
        # THE build-day finding, exact form: the NI feasibility region at
        # N_MAX is two degenerate points out of 625.
        feasible = [(t, k) for t in range(25) for k in range(25)
                    if half_width(newcombe_diff_interval(t, 24, k, 24, 0.95))
                    <= c.QUALITY_NONINFERIORITY_CI_HALF_WIDTH]
        self.assertEqual(feasible, [(0, 24), (24, 0)])
        # equal-arms floor (the realistic-best case) stays above the pin
        equal_arms = half_width(newcombe_diff_interval(24, 24, 24, 24, 0.95))
        self.assertAlmostEqual(equal_arms, 0.13798, delta=5e-6)
        self.assertGreater(equal_arms, c.QUALITY_NONINFERIORITY_CI_HALF_WIDTH)
        # every coherent pilot shape (healthy comparator) refuses
        for pilot in (BinaryPilot(5, 5, 5, 5), BinaryPilot(4, 5, 4, 5),
                      BinaryPilot(5, 5, 4, 5), BinaryPilot(3, 5, 5, 5),
                      BinaryPilot(5, 5, 3, 5)):
            req = n_required_binary(pilot, _ni("x", "9.2.3", MC, "C", "B"))
            self.assertEqual(req.status, STATUS_UNMET, msg=str(pilot))
            self.assertIsNone(req.n_required)
        # and the sliver itself is MET at exactly N_MAX — machinery honesty:
        # the planner does not hide the degenerate configuration
        req = n_required_binary(BinaryPilot(5, 5, 0, 5),
                                _ni("x", "9.2.3", MC, "C", "B"))
        self.assertEqual(req.status, STATUS_MET)
        self.assertEqual(req.n_required, 24)

    def test_malformed_pilot_refused(self):
        with self.assertRaises(PlannerContractError):
            n_required_binary(BinaryPilot(6, 5, 0, 5),
                              _sup("x", "9.2.1", MM, "C", "B"))


class TestCostNRule(unittest.TestCase):
    def test_minimal_n_and_shared_function(self):
        req = n_required_cost(450.0, 25.0, 500.0, 25.0, 0.95, 25.0, "cost_x")
        self.assertEqual(req.status, STATUS_MET)
        n = req.n_required
        # minimality against the same score-time Welch function
        w_at = welch_interval(450.0, 25.0, n, 500.0, 25.0, n, 0.95)
        self.assertLessEqual(0.5 * (w_at.upper - w_at.lower), 25.0)
        if n > 2:
            w_below = welch_interval(450.0, 25.0, n - 1, 500.0, 25.0, n - 1, 0.95)
            self.assertGreater(0.5 * (w_below.upper - w_below.lower), 25.0)

    def test_degenerate_variance_is_refusal_not_zero(self):
        req = n_required_cost(450.0, 0.0, 500.0, 0.0, 0.95, 25.0, "cost_x")
        self.assertEqual(req.status, STATUS_DEGENERATE)
        self.assertIsNone(req.n_required)

    def test_huge_variance_unmet(self):
        req = n_required_cost(450.0, 400.0, 500.0, 400.0, 0.95, 10.0, "cost_x")
        self.assertEqual(req.status, STATUS_UNMET)
        self.assertIsNone(req.n_required)


class TestPopulationNRule(unittest.TestCase):
    def test_strong_pilot_plannable(self):
        spec = _population("pop", "9.4", "C_controlled_check", "A_always_check",
                           margin=c.POPULATION_ALWAYS_CHECK_MARGIN,
                           family_alpha=c.POPULATION_FAMILY_ALPHA)
        req = n_required_population(_strong_population_pilot(), spec, _region())
        self.assertEqual(req.status, STATUS_MET)
        self.assertLessEqual(req.n_required, c.N_MAX)

    def test_region_touching_zero_irrelevant_refused(self):
        spec = _population("pop", "9.4", "C", "A", 0.10, 0.05)
        bad = _region() + [{MM: 0.5, MC: 0.5, IRR: 0.0}]
        with self.assertRaises(PlannerContractError):
            n_required_population(_strong_population_pilot(), spec, bad)

    def test_saving_below_margin_unmet(self):
        # comparator only ~2% more expensive: point margin can never reach 10%
        pilot = PopulationPilot(strata=(
            StratumCostPilot(MM, 490.0, 5.0, 500.0, 5.0),
            StratumCostPilot(MC, 490.0, 5.0, 500.0, 5.0),
            StratumCostPilot(IRR, 490.0, 5.0, 500.0, 5.0),
        ))
        spec = _population("pop", "9.4", "C", "A", 0.10, 0.05)
        req = n_required_population(pilot, spec, _region())
        self.assertEqual(req.status, STATUS_UNMET)


class TestGateComposition(unittest.TestCase):
    def _pilots(self, **binary):
        return Pilots(binary=binary, population={}, vertices=None)

    def test_allof_takes_max_and_none_poisons(self):
        g = PlannedGate("g", "x", AllOf((
            _sup("a", "x", MM, "C", "B"), _sup("b", "x", MC, "C", "B"))))
        plan = resolve_gates([g], self._pilots(
            a=BinaryPilot(5, 5, 0, 5),        # n=10
            b=BinaryPilot(5, 5, 1, 5)))       # weaker split -> larger n
        [rg] = plan.resolved
        n_a = next(r for r in rg.requirements if r.contrast_id == "a").n_required
        n_b = next(r for r in rg.requirements if r.contrast_id == "b").n_required
        self.assertEqual(rg.n_required, max(n_a, n_b))

        g2 = PlannedGate("g2", "x", AllOf((
            _sup("a", "x", MM, "C", "B"), _ni("z", "x", MC, "C", "B"))))
        plan2 = resolve_gates([g2], self._pilots(
            a=BinaryPilot(5, 5, 0, 5), z=BinaryPilot(5, 5, 5, 5)))
        self.assertIsNone(plan2.resolved[0].n_required)
        self.assertIn("z", plan2.unmet)

    def test_anyof_takes_min_and_records_decision_bearing_arm(self):
        g = PlannedGate("g", "x", AnyOf((
            _sup("fast", "x", MM, "C", "G"),     # perfect split: n=10
            _sup("slow", "x", MM, "C", "G2"))))  # weaker: larger n
        plan = resolve_gates([g], self._pilots(
            fast=BinaryPilot(5, 5, 0, 5), slow=BinaryPilot(5, 5, 2, 5)))
        [rg] = plan.resolved
        self.assertEqual(rg.n_required, 10)
        self.assertEqual(rg.decision_bearing_arms, ("fast",))

    def test_unpowered_arm_does_not_poison_stratum(self):
        # OR of a plannable superiority arm and a structurally-unmet NI arm:
        # the gate is plannable and the NI arm must not poison the stratum N.
        g = PlannedGate("g", "x", AnyOf((
            _sup("q", "x", MM, "C", "G"),
            _ni("e", "x", MM, "C", "G"))))
        plan = resolve_gates([g], self._pilots(
            q=BinaryPilot(5, 5, 0, 5), e=BinaryPilot(5, 5, 5, 5)))
        self.assertEqual(plan.resolved[0].n_required, 10)
        self.assertTrue(plan.all_plannable)
        self.assertEqual(plan.unmet, ())
        self.assertEqual(plan.stratum_n[MM], 10)

    def test_trigger_matching_strata_equalized(self):
        g1 = PlannedGate("g1", "x", _sup("a", "x", MM, "C", "B"))
        g2 = PlannedGate("g2", "x", _sup("b", "x", MC, "C", "B"))
        plan = resolve_gates([g1, g2], self._pilots(
            a=BinaryPilot(5, 5, 0, 5), b=BinaryPilot(5, 5, 1, 5)))
        self.assertEqual(plan.stratum_n[MM], plan.stratum_n[MC])
        self.assertEqual(plan.stratum_n[MM],
                         max(r.n_required for g in plan.resolved
                             for r in g.requirements))

    def test_missing_pilot_fails_closed(self):
        g = PlannedGate("g", "x", _sup("a", "x", MM, "C", "B"))
        with self.assertRaises(PlannerContractError):
            resolve_gates([g], self._pilots())


class TestBandsAndProbes(unittest.TestCase):
    def test_bands_pass(self):
        self.assertEqual(calibration_band_failures(
            SBandCounts(s0_pass=2, s0_n=5, s1_pass=5, s1_n=5,
                        s2_pass=2, s2_n=5)), [])

    def test_each_band_fails_by_name(self):
        fails = calibration_band_failures(
            SBandCounts(s0_pass=4, s0_n=5, s1_pass=3, s1_n=5,
                        s2_pass=3, s2_n=5))
        text = " ".join(fails)
        for marker in ("s0_pass_rate", "s1_pass_rate", "s1-s0", "s1-s2"):
            self.assertIn(marker, text)

    def test_ignorance_probe(self):
        ok = IgnoranceProbeResult(recovered=1, n=10, max_recoverable_rate=0.2)
        self.assertIsNone(ok.failure())
        leaky = IgnoranceProbeResult(recovered=5, n=10, max_recoverable_rate=0.2)
        self.assertIn("recoverable", leaky.failure())

    def test_collapse_detection(self):
        self.assertTrue(detect_collapse(["h1", "h1", "h1"]))
        self.assertFalse(detect_collapse(["h1", "h2", "h1"]))
        with self.assertRaises(PlannerContractError):
            detect_collapse([])


class TestCalibrationGate(unittest.TestCase):
    def _healthy_inputs(self, region=True):
        # coherent pilots: superiority contrasts see a strong treatment split;
        # NI loses-cells see healthy comparators (the configuration the cells
        # are FOR — a comparator collapsing to 0/5 would contradict the §6
        # bands and the analog board itself)
        gates = planned_gates(population_region_declared=region)
        binary = {}
        for gate in gates:
            for req_spec in _leaves(gate):
                if req_spec.kind == "binary_superiority":
                    binary[req_spec.contrast_id] = BinaryPilot(5, 5, 0, 5)
                elif req_spec.kind == "binary_noninferiority":
                    binary[req_spec.contrast_id] = BinaryPilot(5, 5, 4, 5)
        population = {}
        for gate in gates:
            for req_spec in _leaves(gate):
                if req_spec.kind == "population_cost":
                    population[req_spec.contrast_id] = _strong_population_pilot()
        return AdmissionInputs(
            s_band=SBandCounts(2, 5, 5, 5, 2, 5),
            ignorance=IgnoranceProbeResult(0, 10, 0.2),
            collapse=CollapseState(collapsed_at_t05=False, collapsed_at_t07=None),
            pilots=Pilots(binary=binary, population=population,
                          vertices=_region() if region else None),
            population_region_declared=region,
            vertices=_region() if region else None)

    def test_structural_refusal_on_the_sealed_board(self):
        # Healthiest possible engine, perfect pilots, valid region — and the
        # sealed board still cannot open: §9.2 NI contrasts are unplannable at
        # n_max=24 (min hw 0.13798 > 0.10), so §10.4 refuses Part II.
        result = calibration_gate(self._healthy_inputs())
        self.assertEqual(result.verdict, "confounded(ci_target_unmet)")
        self.assertTrue(any("ni_" in cid for cid in result.plan.unmet))
        self.assertFalse(result.plan.all_plannable)
        self.assertTrue(result.budget_disclosure_required)

    def test_not_engaged_when_packet_absent(self):
        result = calibration_gate(AdmissionInputs(
            s_band=None, ignorance=None, collapse=None, pilots=None,
            population_region_declared=False, vertices=None))
        self.assertEqual(result.verdict, "not_engaged")

    def test_point_mode_diagnostic(self):
        inputs = self._healthy_inputs()
        collapsed = AdmissionInputs(
            s_band=inputs.s_band, ignorance=inputs.ignorance,
            collapse=CollapseState(True, True), pilots=inputs.pilots,
            population_region_declared=True, vertices=_region())
        self.assertEqual(calibration_gate(collapsed).verdict,
                         "point_mode_diagnostic")
        pending = AdmissionInputs(
            s_band=inputs.s_band, ignorance=inputs.ignorance,
            collapse=CollapseState(True, None), pilots=inputs.pilots,
            population_region_declared=True, vertices=_region())
        self.assertEqual(calibration_gate(pending).verdict, "not_engaged")

    def test_engine_refused_on_bands_and_ignorance(self):
        inputs = self._healthy_inputs()
        bad_band = AdmissionInputs(
            s_band=SBandCounts(4, 5, 3, 5, 3, 5), ignorance=inputs.ignorance,
            collapse=inputs.collapse, pilots=inputs.pilots,
            population_region_declared=True, vertices=_region())
        self.assertEqual(calibration_gate(bad_band).verdict, "engine_refused")
        leaky = AdmissionInputs(
            s_band=inputs.s_band,
            ignorance=IgnoranceProbeResult(9, 10, 0.2),
            collapse=inputs.collapse, pilots=inputs.pilots,
            population_region_declared=True, vertices=_region())
        self.assertEqual(calibration_gate(leaky).verdict, "engine_refused")

    def test_verdict_vocabulary_pinned(self):
        for verdict in ("engine_admitted", "engine_refused",
                        "point_mode_diagnostic", "not_engaged",
                        "confounded(ci_target_unmet)"):
            self.assertIn(verdict, c.ENGINE_ADMISSION_VERDICTS)


class TestProjectedCounts(unittest.TestCase):
    def test_counts_from_synthetic_plannable_board(self):
        # superiority-only synthetic board (the sealed board cannot open;
        # this exercises the disclosure arithmetic on a plannable one)
        gates = [
            PlannedGate("src", "7", AllOf((
                _sup("s1s0", "7", "source", "S1", "S0"),
                _sup("s1s2", "7", "source", "S1", "S2")))),
            PlannedGate("mm", "9.2.1", _sup("q1", "9.2.1", MM, "C", "B")),
            PlannedGate("mc", "x", _sup("q2", "x", MC, "C", "B")),
            PlannedGate("irr", "x", _sup("q3", "x", IRR, "C", "B")),
        ]
        pilots = Pilots(binary={cid: BinaryPilot(5, 5, 0, 5)
                                for cid in ("s1s0", "s1s2", "q1", "q2", "q3")})
        plan = resolve_gates(gates, pilots)
        self.assertTrue(plan.all_plannable)
        counts = projected_counts(plan, plan.stratum_n["source"])
        self.assertEqual(counts.target_fixtures_per_stratum,
                         {MM: 10, MC: 10, IRR: 10})
        self.assertEqual(counts.target_model_invocations, 30 * len(c.LANES))
        self.assertEqual(counts.source_model_invocations, 10 * 3)


def _leaves(gate):
    from harness.efc_planner import _iter_leaves
    return list(_iter_leaves(gate.node))


if __name__ == "__main__":
    unittest.main()
