"""Wire tests for the §10.4 N-rule planner and §6 computed calibration gate.

Mock pilot numbers only — admission diagnostics machinery, never mechanism
evidence (§6). Two pins matter most:

1. §10.4's zero-variance guard: a K=5 binary pilot at an observed boundary
   cannot claim n_required = 0 — Wilson/Newcombe width stays real.
2. Finding 1 (2026-07-12, now the §18 v0.2 amendment record): under the v0.1
   ceiling of 24, exactly TWO of the 625 possible count configurations met
   the §10.3 non-inferiority half-width target of 0.10 — the total
   anti-correlated collapses (24/24 vs 0/24) and mirror, hw = 0.09756 — both
   incoherent with the §6 S1 >= 0.80 band, so the v0.1 board computed
   confounded(ci_target_unmet) for every coherent pilot. That historical
   arithmetic is pinned below with EXPLICIT N=24 enumeration, independent of
   the amended N_MAX (Sol's acceptance condition: history is not mutated
   into a ceiling test). The v0.2 ceiling of 128 opens the coherent corner
   (equal 0.80 rates -> N=124); the acceptance test asserts the full board,
   stratum table, and budget disclosure, not merely the verdict.
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

    def test_historical_v01_infeasibility_enumeration(self):
        # Finding 1, §18 amendment record — pinned at EXPLICIT N=24, fully
        # independent of the amended N_MAX. Do not mutate this history.
        feasible = [(t, k) for t in range(25) for k in range(25)
                    if half_width(newcombe_diff_interval(t, 24, k, 24, 0.95))
                    <= c.QUALITY_NONINFERIORITY_CI_HALF_WIDTH]
        self.assertEqual(feasible, [(0, 24), (24, 0)])
        # equal-arms floor (the realistic-best case) stays above the pin
        equal_arms = half_width(newcombe_diff_interval(24, 24, 24, 24, 0.95))
        self.assertAlmostEqual(equal_arms, 0.13798, delta=5e-6)
        self.assertGreater(equal_arms, c.QUALITY_NONINFERIORITY_CI_HALF_WIDTH)
        # the §18 equal-arms first-feasible N table
        for p, first_n in ((1.0, 35), (0.95, 54), (0.9, 77), (0.8, 124)):
            for n, expect_met in ((first_n - 1, False), (first_n, True)):
                hw = half_width(newcombe_diff_interval(p * n, n, p * n, n, 0.95))
                self.assertEqual(hw <= 0.10, expect_met, msg=f"p={p} N={n}")

    def test_ni_planning_under_v02_ceiling(self):
        # coherent NI pilots now plan inside the 128 ceiling (§18)
        for pilot, expected_n in ((BinaryPilot(4, 5, 4, 5), 124),
                                  (BinaryPilot(5, 5, 5, 5), 35)):
            req = n_required_binary(pilot, _ni("x", "9.2.3", MC, "C", "B"))
            self.assertEqual(req.status, STATUS_MET, msg=str(pilot))
            self.assertEqual(req.n_required, expected_n, msg=str(pilot))
        # the anti-correlated sliver still plans first at 24 — the planner
        # does not hide the degenerate configuration
        req = n_required_binary(BinaryPilot(5, 5, 0, 5),
                                _ni("x", "9.2.3", MC, "C", "B"))
        self.assertEqual(req.n_required, 24)
        # and a genuinely low-rate configuration still refuses at 128
        req = n_required_binary(BinaryPilot(3, 5, 3, 5),
                                _ni("x", "9.2.3", MC, "C", "B"))
        self.assertEqual(req.status, STATUS_UNMET)

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
        self.assertTrue(req.projected_clearance_diagnostic)
        # §19 per-vertex diagnostics: one row per declared vertex, aggregate
        # derivable, and reconstructible from typed inputs
        self.assertEqual(len(req.vertex_diagnostics), len(_region()))
        self.assertEqual(req.projected_clearance_diagnostic,
                         all(d.margin_ok and d.positivity_ok
                             for d in req.vertex_diagnostics))
        from harness.efc_planner import population_vertex_diagnostics
        recomputed = population_vertex_diagnostics(
            _strong_population_pilot(), spec, _region(), req.n_required)
        self.assertEqual(recomputed, req.vertex_diagnostics)
        for d in req.vertex_diagnostics:
            self.assertLessEqual(d.precision_gap, d.precision_target)

    def test_region_touching_zero_irrelevant_refused(self):
        spec = _population("pop", "9.4", "C", "A", 0.10, 0.05)
        bad = _region() + [{MM: 0.5, MC: 0.5, IRR: 0.0}]
        with self.assertRaises(PlannerContractError):
            n_required_population(_strong_population_pilot(), spec, bad)

    def test_saving_below_margin_is_diagnostic_not_refusal(self):
        # §10.4 v0.2 three-layer split (Sol's Q2 ruling): a ~2% saving can
        # never clear the 10% margin, but margin clearance no longer decides
        # admission — precision does. Status is MET with a False diagnostic;
        # the margin remains a held-out §9.4 verdict condition.
        pilot = PopulationPilot(strata=(
            StratumCostPilot(MM, 490.0, 5.0, 500.0, 5.0),
            StratumCostPilot(MC, 490.0, 5.0, 500.0, 5.0),
            StratumCostPilot(IRR, 490.0, 5.0, 500.0, 5.0),
        ))
        spec = _population("pop", "9.4", "C", "A", 0.10, 0.05)
        req = n_required_population(pilot, spec, _region())
        self.assertEqual(req.status, STATUS_MET)
        self.assertFalse(req.projected_clearance_diagnostic)
        # §19 diagnostics say exactly WHICH condition failed at every vertex:
        # the 2% saving can never reach the 10% margin, and at the first
        # precision-admitted N the simultaneous lower bound (saving 10, gap up
        # to 25) may legitimately still cross zero — both facts visible per
        # vertex instead of collapsed into one bool
        for d in req.vertex_diagnostics:
            self.assertFalse(d.margin_ok)
            self.assertEqual(d.positivity_ok, d.lower_saving > 0.0)

    def test_wide_variance_population_precision_refuses(self):
        # precision (the only admission criterion) still refuses honestly
        pilot = PopulationPilot(strata=(
            StratumCostPilot(MM, 300.0, 400.0, 500.0, 400.0),
            StratumCostPilot(MC, 300.0, 400.0, 500.0, 400.0),
            StratumCostPilot(IRR, 450.0, 400.0, 500.0, 400.0),
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
            a=BinaryPilot(5, 5, 0, 5), z=BinaryPilot(3, 5, 3, 5)))
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
            q=BinaryPilot(5, 5, 0, 5), e=BinaryPilot(3, 5, 3, 5)))
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
        # NI loses-cells see EQUAL 0.80-rate arms — Sol's named acceptance
        # corner, the lowest coherent healthy-engine configuration implied by
        # the §6 S1 >= 0.80 band (§18)
        gates = planned_gates(population_region_declared=region)
        binary = {}
        for gate in gates:
            for req_spec in _leaves(gate):
                if req_spec.kind == "binary_superiority":
                    binary[req_spec.contrast_id] = BinaryPilot(5, 5, 0, 5)
                elif req_spec.kind == "binary_noninferiority":
                    binary[req_spec.contrast_id] = BinaryPilot(4, 5, 4, 5)
        population = {}
        for gate in gates:
            for req_spec in _leaves(gate):
                if req_spec.kind == "population_cost":
                    population[req_spec.contrast_id] = _strong_population_pilot()
        intent = (c.POPULATION_INTENT_REGION if region
                  else c.POPULATION_INTENT_RESPONSE_CURVE_ONLY)
        return AdmissionInputs(
            s_band=SBandCounts(2, 5, 5, 5, 2, 5),
            ignorance=IgnoranceProbeResult(0, 10, 0.2),
            collapse=CollapseState(collapsed_at_t05=False, collapsed_at_t07=None),
            pilots=Pilots(binary=binary, population=population,
                          vertices=_region() if region else None),
            population_intent=intent,
            vertices=_region() if region else None)

    def test_coherent_corner_admits_at_v02_ceiling(self):
        # §18 acceptance case (Sol's condition 4): equal 0.80-rate NI pilots,
        # healthy bands, valid region — the amended board opens with the full
        # stratum table and the budget disclosure, not merely the verdict.
        result = calibration_gate(self._healthy_inputs())
        self.assertEqual(result.verdict, "engine_admitted")
        self.assertTrue(result.plan.all_plannable)
        self.assertEqual(result.plan.unmet, ())
        self.assertEqual(result.plan.stratum_n["match_mismatch"], 124)
        self.assertEqual(result.plan.stratum_n["match_commit"], 124)
        self.assertEqual(result.plan.stratum_n["irrelevant"], 124)
        self.assertEqual(result.plan.stratum_n["source"], 10)
        self.assertEqual(result.counts.target_fixtures_per_stratum,
                         {MM: 124, MC: 124, IRR: 124})
        self.assertEqual(result.counts.target_model_invocations, 2232)
        self.assertEqual(result.counts.source_model_invocations, 30)
        self.assertTrue(result.budget_disclosure_required)
        self.assertEqual(result.license_path, c.POPULATION_INTENT_REGION)
        # §9.3 v0.3: decision-bearing arms are pinned in the plan, selected on
        # precision/N alone; only these can satisfy the OR at score time
        arms = result.plan.decision_bearing_arms
        self.assertEqual(arms["boundary_necessity_G_generic_caution"],
                         ("ni_mc_C_vs_g", "ni_irr_C_vs_g",
                          "or_quality_mm_C_vs_g"))
        self.assertEqual(arms["boundary_necessity_O_offer_projection"],
                         ("ni_mc_C_vs_o", "ni_irr_C_vs_o",
                          "or_quality_mm_C_vs_o"))
        self.assertNotIn("or_eff_ni_mm_C_vs_g",
                         arms["boundary_necessity_G_generic_caution"])

    def test_not_engaged_when_packet_absent(self):
        result = calibration_gate(AdmissionInputs(
            s_band=None, ignorance=None, collapse=None, pilots=None,
            population_intent=None, vertices=None))
        self.assertEqual(result.verdict, "not_engaged")

    def test_undeclared_population_intent_does_not_open_band(self):
        # §10.4 v0.3: a packet with no §5.2 intent is not license-seeking
        inputs = self._healthy_inputs()
        undeclared = AdmissionInputs(
            s_band=inputs.s_band, ignorance=inputs.ignorance,
            collapse=inputs.collapse, pilots=inputs.pilots,
            population_intent=None, vertices=None)
        result = calibration_gate(undeclared)
        self.assertEqual(result.verdict, "not_engaged")
        self.assertIn("population intent", " ".join(result.reasons))

    def test_response_curve_only_path(self):
        # §12/§10.4 v0.3: quality board fully sized, population leaves absent,
        # permanent non-license path recorded
        result = calibration_gate(self._healthy_inputs(region=False))
        self.assertEqual(result.verdict, "engine_admitted")
        self.assertEqual(result.license_path,
                         c.POPULATION_INTENT_RESPONSE_CURVE_ONLY)
        all_contrasts = [r.contrast_id for g in result.plan.resolved
                         for r in g.requirements]
        self.assertNotIn("pop_cost_C_vs_A", all_contrasts)
        self.assertFalse(any(cid.startswith("or_eff_") for cid in all_contrasts))
        # boundary-necessity quality alternatives still sized (§10.4 v0.3)
        self.assertIn("or_quality_mm_C_vs_g", all_contrasts)
        self.assertIn("or_quality_mm_C_vs_o", all_contrasts)

    def test_intent_contract_violations_fail_closed(self):
        inputs = self._healthy_inputs()
        with self.assertRaises(PlannerContractError):
            calibration_gate(AdmissionInputs(
                s_band=inputs.s_band, ignorance=inputs.ignorance,
                collapse=inputs.collapse, pilots=inputs.pilots,
                population_intent=c.POPULATION_INTENT_REGION, vertices=None))
        with self.assertRaises(PlannerContractError):
            calibration_gate(AdmissionInputs(
                s_band=inputs.s_band, ignorance=inputs.ignorance,
                collapse=inputs.collapse, pilots=inputs.pilots,
                population_intent=c.POPULATION_INTENT_RESPONSE_CURVE_ONLY,
                vertices=_region()))
        with self.assertRaises(PlannerContractError):
            calibration_gate(AdmissionInputs(
                s_band=inputs.s_band, ignorance=inputs.ignorance,
                collapse=inputs.collapse, pilots=inputs.pilots,
                population_intent="whatever_wins", vertices=_region()))

    def test_point_mode_diagnostic(self):
        inputs = self._healthy_inputs()
        collapsed = AdmissionInputs(
            s_band=inputs.s_band, ignorance=inputs.ignorance,
            collapse=CollapseState(True, True), pilots=inputs.pilots,
            population_intent=c.POPULATION_INTENT_REGION, vertices=_region())
        self.assertEqual(calibration_gate(collapsed).verdict,
                         "point_mode_diagnostic")
        pending = AdmissionInputs(
            s_band=inputs.s_band, ignorance=inputs.ignorance,
            collapse=CollapseState(True, None), pilots=inputs.pilots,
            population_intent=c.POPULATION_INTENT_REGION, vertices=_region())
        self.assertEqual(calibration_gate(pending).verdict, "not_engaged")

    def test_engine_refused_on_bands_and_ignorance(self):
        inputs = self._healthy_inputs()
        bad_band = AdmissionInputs(
            s_band=SBandCounts(4, 5, 3, 5, 3, 5), ignorance=inputs.ignorance,
            collapse=inputs.collapse, pilots=inputs.pilots,
            population_intent=c.POPULATION_INTENT_REGION, vertices=_region())
        self.assertEqual(calibration_gate(bad_band).verdict, "engine_refused")
        leaky = AdmissionInputs(
            s_band=inputs.s_band,
            ignorance=IgnoranceProbeResult(9, 10, 0.2),
            collapse=inputs.collapse, pilots=inputs.pilots,
            population_intent=c.POPULATION_INTENT_REGION, vertices=_region())
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
