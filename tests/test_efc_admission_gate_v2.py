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
    evaluate_commitment_invalid_rate_gate,
    evaluate_fork_identity,
    evaluate_irrelevant_band_gate,
    evaluate_pair_constant_policy_gate,
    evaluate_within_class_gate,
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


class TestAdmissionBoundaryGates(unittest.TestCase):
    def _valid_row(self, *, lane: str, stratum: str, supplied_class: str | None = None):
        row = {
            "fixture_id": "fx-1",
            "lane": lane,
            "stratum": stratum,
            "validation_outcome": "commitment_valid",
            "oracle_outcome": "pass",
            "commitment_enum": "alpha_commit",
        }
        if supplied_class is not None:
            row["supplied_class"] = supplied_class
        return row

    def test_within_class_gate_passes_at_floor(self):
        rows = (
            [self._valid_row(lane="M_forced_class", stratum="match", supplied_class="commit")] * 128
            + [self._valid_row(lane="M_forced_class", stratum="mismatch", supplied_class="non_commit")] * 128
        )
        result = evaluate_within_class_gate(rows)
        self.assertTrue(result.passed)

    def test_irrelevant_band_gate_passes_at_floor(self):
        rows = [
            self._valid_row(lane="M_irrelevant", stratum="irrelevant")
        ] * 128
        result = evaluate_irrelevant_band_gate(rows)
        self.assertTrue(result.passed)

    def test_commitment_invalid_rate_6_passes_7_fails(self):
        ceiling_spec = {
            "global_minimum": 0.05,
            "cells": [{
                "lane": "M_untreated",
                "stratum": "match",
                "ceiling": 0.05,
            }],
        }
        base = {
            "lane": "M_untreated",
            "stratum": "match",
            "validation_outcome": "commitment_valid",
        }
        rows_6 = [dict(base) for _ in range(122)] + [
            {**base, "validation_outcome": "commitment_invalid"} for _ in range(6)
        ]
        rows_7 = [dict(base) for _ in range(121)] + [
            {**base, "validation_outcome": "commitment_invalid"} for _ in range(7)
        ]
        pass_result = evaluate_commitment_invalid_rate_gate(rows_6, ceiling_spec)
        fail_result = evaluate_commitment_invalid_rate_gate(rows_7, ceiling_spec)
        self.assertTrue(pass_result.passed)
        self.assertFalse(fail_result.passed)

    def test_fork_identity_mismatch_fails(self):
        manifest = {"fork_identity": {"engine": "a", "effort": "b", "render_hash": "c"}}
        result = evaluate_fork_identity(
            manifest, engine="x", effort="b", render_hash="c"
        )
        self.assertFalse(result.passed)

    def test_stratum_count_51_fails_52_passes(self):
        params = admission_gate_params(128)

        def rows_for_match_count(n: int) -> list[dict]:
            rows = []
            for i in range(n):
                rows.append({
                    "lane": "M_untreated",
                    "stratum": "match",
                    "validation_outcome": "commitment_valid",
                    "oracle_outcome": "pass",
                })
            for i in range(128 - n):
                rows.append({
                    "lane": "M_untreated",
                    "stratum": "match",
                    "validation_outcome": "commitment_valid",
                    "oracle_outcome": "fail",
                })
            for i in range(56):
                rows.append({
                    "lane": "M_untreated",
                    "stratum": "mismatch",
                    "validation_outcome": "commitment_valid",
                    "oracle_outcome": "pass",
                })
            for i in range(72):
                rows.append({
                    "lane": "M_untreated",
                    "stratum": "mismatch",
                    "validation_outcome": "commitment_valid",
                    "oracle_outcome": "fail",
                })
            return rows

        fail_51 = evaluate_admission_band_gate(rows_for_match_count(51), params)
        pass_52 = evaluate_admission_band_gate(rows_for_match_count(52), params)
        self.assertFalse(fail_51.passed)
        self.assertTrue(pass_52.passed)

    def test_stratum_count_57_fails_56_passes(self):
        params = admission_gate_params(128)

        def rows_for_match_count(n: int) -> list[dict]:
            rows = []
            for i in range(n):
                rows.append({
                    "lane": "M_untreated",
                    "stratum": "match",
                    "validation_outcome": "commitment_valid",
                    "oracle_outcome": "pass",
                })
            for i in range(128 - n):
                rows.append({
                    "lane": "M_untreated",
                    "stratum": "match",
                    "validation_outcome": "commitment_valid",
                    "oracle_outcome": "fail",
                })
            for i in range(56):
                rows.append({
                    "lane": "M_untreated",
                    "stratum": "mismatch",
                    "validation_outcome": "commitment_valid",
                    "oracle_outcome": "pass",
                })
            for i in range(72):
                rows.append({
                    "lane": "M_untreated",
                    "stratum": "mismatch",
                    "validation_outcome": "commitment_valid",
                    "oracle_outcome": "fail",
                })
            return rows

        pass_56 = evaluate_admission_band_gate(rows_for_match_count(56), params)
        fail_57 = evaluate_admission_band_gate(rows_for_match_count(57), params)
        self.assertTrue(pass_56.passed)
        self.assertFalse(fail_57.passed)

    def test_pair_switch_s52_fails_s53_passes(self):
        from tests.efc_v2_test_fixtures import make_minimal_suite

        fixtures = make_minimal_suite(128)
        fixtures_by_id = {f["fixture_id"]: f for f in fixtures}
        params = admission_gate_params(128)
        lo, _hi = PAIR_SWITCH_REGION

        def switched_rows(switched_count: int) -> list[dict]:
            rows: list[dict] = []
            block_ids = sorted({f["block_id"] for f in fixtures})
            for idx, block_id in enumerate(block_ids):
                match_id = f"{block_id}-match"
                mismatch_id = f"{block_id}-mismatch"
                if idx < switched_count:
                    correct = idx % 2 == 0
                    rows.extend([
                        {
                            "fixture_id": match_id,
                            "lane": "M_untreated",
                            "validation_outcome": "commitment_valid",
                            "commitment_enum": (
                                "alpha_commit" if correct else "gamma_hold"
                            ),
                        },
                        {
                            "fixture_id": mismatch_id,
                            "lane": "M_untreated",
                            "validation_outcome": "commitment_valid",
                            "commitment_enum": (
                                "gamma_hold" if correct else "alpha_commit"
                            ),
                        },
                    ])
                else:
                    rows.extend([
                        {
                            "fixture_id": match_id,
                            "lane": "M_untreated",
                            "validation_outcome": "commitment_valid",
                            "commitment_enum": "alpha_commit",
                        },
                        {
                            "fixture_id": mismatch_id,
                            "lane": "M_untreated",
                            "validation_outcome": "commitment_valid",
                            "commitment_enum": "alpha_commit",
                        },
                    ])
            return rows

        fail_below = evaluate_pair_constant_policy_gate(
            switched_rows(lo - 1), fixtures_by_id, params
        )
        pass_lo = evaluate_pair_constant_policy_gate(
            switched_rows(lo), fixtures_by_id, params
        )
        self.assertFalse(fail_below.passed)
        self.assertTrue(pass_lo.passed)
