"""Conformance vectors for EFC v2 admission gate."""

from __future__ import annotations

import unittest

from harness.efc_admission_gate_v2 import (
    K_DEFAULT,
    PAIR_SWITCH_REGION,
    STRATUM_COUNT_MAX,
    STRATUM_COUNT_MIN,
    admission_gate_params,
    central_binomial_region,
    compute_ub,
    evaluate_admission_band_gate,
    evaluate_pair_constant_policy_gate,
)
from harness.efc_intervals import newcombe_diff_interval


class TestAdmissionArithmetic(unittest.TestCase):
    def test_ub_at_k128(self):
        ub = compute_ub(128)
        self.assertAlmostEqual(ub, 0.4375)
        c_k = 103
        lower, _ = newcombe_diff_interval(c_k, 128, 56, 128, 0.95)
        self.assertGreaterEqual(lower, 0.25)
        lower_fail, _ = newcombe_diff_interval(c_k, 128, 57, 128, 0.95)
        self.assertLess(lower_fail, 0.25)

    def test_pair_switch_region_k128(self):
        lo, hi = central_binomial_region(128, 0.5)
        self.assertEqual((lo, hi), PAIR_SWITCH_REGION)
        self.assertEqual(PAIR_SWITCH_REGION, (53, 75))

    def test_manifest_params_recompute_ub(self):
        params = admission_gate_params(K_DEFAULT)
        self.assertEqual(params["UB"], params["pinned_UB"])
        self.assertEqual(params["per_stratum_count_range"], [52, 56])
        self.assertEqual(params["per_stratum_count_range"][0], STRATUM_COUNT_MIN)
        self.assertEqual(params["per_stratum_count_range"][1], STRATUM_COUNT_MAX)


class TestAdmissionBandGate(unittest.TestCase):
    def _row(self, stratum: str, passed: bool) -> dict:
        return {
            "lane": "M_untreated",
            "stratum": stratum,
            "validation_outcome": "commitment_valid",
            "oracle_outcome": "pass" if passed else "fail",
        }

    def test_per_stratum_pooled_camouflage_refused(self):
        params = admission_gate_params(128)
        rows = (
            [self._row("match", True)] * 56
            + [self._row("match", False)] * 72
            + [self._row("mismatch", True)] * 40
            + [self._row("mismatch", False)] * 88
        )
        result = evaluate_admission_band_gate(rows, params)
        self.assertFalse(result.passed)
        self.assertEqual(result.verdict, "confounded(admission_band)")
        self.assertFalse(result.detail["per_stratum_ok"])

    def test_pinned_ub_disagreement_fails(self):
        params = admission_gate_params(128)
        bad = dict(params)
        bad["pinned_UB"] = 0.99
        result = evaluate_admission_band_gate([], bad)
        self.assertFalse(result.passed)
        self.assertEqual(result.detail["reason"], "pinned_ub_disagreement")


class TestPairPredicate(unittest.TestCase):
    def test_orientation_region_score_time(self):
        lo, hi = central_binomial_region(53, 0.5)
        self.assertLessEqual(lo, 19)
        self.assertGreaterEqual(hi, 34)

    def test_pair_gate_with_fixtures(self):
        from tests.efc_v2_test_fixtures import make_minimal_suite

        fixtures = make_minimal_suite(1)
        fixtures_by_id = {f["fixture_id"]: f for f in fixtures}
        rows = [
            {
                "fixture_id": "block-0000-match",
                "lane": "M_untreated",
                "stratum": "match",
                "validation_outcome": "commitment_valid",
                "commitment_enum": "alpha_commit",
                "oracle_outcome": "pass",
            },
            {
                "fixture_id": "block-0000-mismatch",
                "lane": "M_untreated",
                "stratum": "mismatch",
                "validation_outcome": "commitment_valid",
                "commitment_enum": "gamma_hold",
                "oracle_outcome": "pass",
            },
        ]
        params = admission_gate_params(1)
        params["pair_switch_region"] = [0, 1]
        result = evaluate_pair_constant_policy_gate(rows, fixtures_by_id, params)
        self.assertTrue(result.passed)
