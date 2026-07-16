"""Conformance vectors for the deterministic EFC v1 leak-audit contract."""

from __future__ import annotations

import inspect
import unittest

from harness.efc_leak_audit_v1 import (PREDICTOR_HASH,
                                       canonical_predictor_spec_bytes,
                                       check_no_lexical_marking,
                                       evaluate_leak_audit,
                                       predict_menu_only,
                                       predict_task_menu,
                                       project_trigger_feature_strings,
                                       tokens)

STRATA = ("match_mismatch", "match_commit", "irrelevant")
LABELS = ("approve", "defer", "reject")


def _suite(*, leaky: bool = False) -> list[dict[str, object]]:
    fixtures: list[dict[str, object]] = []
    for stratum in STRATA:
        for index in range(6):
            expected = LABELS[index % 3]
            shift = (index * 2) % 3
            order = list(LABELS[shift:] + LABELS[:shift])
            task = f"Assess record {stratum} item {index}"
            if leaky:
                task += f" choose {expected}"
            fixture: dict[str, object] = {
                "fixture_id": f"{stratum}-{index}",
                "stratum": stratum,
                "task_body": task,
                "menu_order": order,
                "expected_commitment_enum": expected,
                "assertion_basis_kind": expected if leaky else "cited_source",
                "observation_boundary_present": False,
                "source_reference_present": True,
                "decision_scope_present": True,
                # Forbidden treatment data may exist on the fixture, but is never
                # forwarded into either predictor.
                "treatment_path": "C",
                "check_evidence": {"scope_matches": True},
                "disposition_state": "eligible",
            }
            fixture["trigger_feature_strings"] = list(
                project_trigger_feature_strings(fixture)
            )
            fixtures.append(fixture)
    return fixtures


class TestPredictors(unittest.TestCase):
    def test_l1_uses_order_only(self):
        self.assertEqual(predict_menu_only(["defer", "approve", "reject"]), "defer")

    def test_l2_uses_frozen_token_overlap(self):
        self.assertEqual(
            predict_task_menu("Please DEFER this choice.", ["approve", "defer", "reject"]),
            "defer",
        )

    def test_l2_tie_breaks_by_menu_order(self):
        self.assertEqual(
            predict_task_menu("No label appears here", ["reject", "approve", "defer"]),
            "reject",
        )

    def test_tokenization_is_nfkc_casefolded(self):
        self.assertEqual(tokens("ＡＰＰＲＯＶＥ_case"), ("approve", "case"))

    def test_predictor_signatures_are_pure(self):
        self.assertEqual(
            tuple(inspect.signature(predict_menu_only).parameters),
            ("action_set_ordering",),
        )
        self.assertEqual(
            tuple(inspect.signature(predict_task_menu).parameters),
            ("task_body_text", "action_set_ordering"),
        )
        with self.assertRaises(TypeError):
            predict_menu_only(LABELS, treatment_path="C")  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            predict_task_menu("body", LABELS, check_evidence={})  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            predict_task_menu("body", LABELS, disposition_state="eligible")  # type: ignore[call-arg]

    def test_predictor_pin_is_not_invented(self):
        self.assertEqual(PREDICTOR_HASH, "TO-BE-COMPUTED-AT-SEAL")
        self.assertEqual(canonical_predictor_spec_bytes(), canonical_predictor_spec_bytes())


class TestSuiteEvaluation(unittest.TestCase):
    def test_clean_balanced_suite_passes_both_legs(self):
        result = evaluate_leak_audit(_suite())
        self.assertTrue(result.ok)
        self.assertEqual(len(result.cells), 6)
        self.assertTrue(all(cell.passed for cell in result.cells))
        self.assertEqual({cell.accuracy for cell in result.cells}, {1 / 3})

    def test_deliberately_leaky_menu_fails_l2(self):
        result = evaluate_leak_audit(_suite(leaky=True))
        self.assertFalse(result.ok)
        self.assertEqual(
            set(result.refusals),
            {f"leak_audit_fail(L2, {stratum})" for stratum in STRATA},
        )
        self.assertEqual(result.confound, "confounded(menu_leak)")

    def test_deliberately_leaky_menu_fails_no_lexical_marking(self):
        result = check_no_lexical_marking(_suite(leaky=True))
        self.assertFalse(result.ok)
        self.assertEqual(len(result.refusals), 18)
        self.assertIn("no_lexical_marking_fail(match_commit-0)", result.refusals)

    def test_clean_suite_passes_no_lexical_marking(self):
        self.assertTrue(check_no_lexical_marking(_suite()).ok)

    def test_empty_trigger_projection_is_refused(self):
        fixtures = _suite()
        fixtures[0]["trigger_feature_strings"] = []
        result = check_no_lexical_marking(fixtures)
        self.assertFalse(result.ok)
        self.assertEqual(result.refusals, ("empty_trigger_projection",))

    def test_trigger_projection_mismatch_is_refused(self):
        fixtures = _suite()
        fixtures[0]["trigger_feature_strings"] = ["author chosen placeholder"]
        result = check_no_lexical_marking(fixtures)
        self.assertFalse(result.ok)
        self.assertEqual(result.refusals, ("trigger_projection_mismatch",))

    def test_correct_trigger_projection_passes(self):
        fixture = _suite()[0]
        self.assertEqual(
            tuple(fixture["trigger_feature_strings"]),
            project_trigger_feature_strings(fixture),
        )
        self.assertTrue(check_no_lexical_marking(_suite()).ok)

    def test_leaky_trigger_projection_overlapping_expected_fails(self):
        result = check_no_lexical_marking(_suite(leaky=True))
        self.assertFalse(result.ok)
        self.assertIn("no_lexical_marking_fail(match_mismatch-0)", result.refusals)

    def test_threshold_is_per_leg_per_stratum(self):
        fixtures = _suite()
        target = [fx for fx in fixtures if fx["stratum"] == "match_commit"]
        # Make L1 right on 3/6 only for this stratum: .50 > 1/3 + .10.
        for fixture in target[:3]:
            expected = fixture["expected_commitment_enum"]
            order = fixture["menu_order"]
            assert isinstance(expected, str) and isinstance(order, list)
            order.remove(expected)
            order.insert(0, expected)
        for fixture in target[3:]:
            expected = fixture["expected_commitment_enum"]
            order = fixture["menu_order"]
            assert isinstance(expected, str) and isinstance(order, list)
            if order[0] == expected:
                order.append(order.pop(0))
        result = evaluate_leak_audit(fixtures)
        self.assertIn("leak_audit_fail(L1, match_commit)", result.refusals)
        self.assertNotIn("leak_audit_fail(L1, match_mismatch)", result.refusals)
        self.assertNotIn("leak_audit_fail(L1, irrelevant)", result.refusals)

    def test_threshold_equality_passes(self):
        labels = ("approve", "defer", "reject", "hold", "escalate")
        fixtures: list[dict[str, object]] = []
        for stratum in STRATA:
            for index in range(10):
                expected = labels[index % 5]
                shift = (index * 2) % 5
                order = list(labels[shift:] + labels[:shift])
                fixture: dict[str, object] = {
                    "fixture_id": f"eq-{stratum}-{index}",
                    "stratum": stratum,
                    "task_body": f"Assess neutral item {index}",
                    "menu_order": order,
                    "expected_commitment_enum": expected,
                    "assertion_basis_kind": "cited_source",
                    "observation_boundary_present": False,
                    "source_reference_present": True,
                    "decision_scope_present": True,
                }
                fixture["trigger_feature_strings"] = list(
                    project_trigger_feature_strings(fixture)
                )
                fixtures.append(fixture)
        target = [fx for fx in fixtures if fx["stratum"] == "irrelevant"]
        for fixture in target[:3]:
            expected = fixture["expected_commitment_enum"]
            order = fixture["menu_order"]
            assert isinstance(expected, str) and isinstance(order, list)
            order.remove(expected)
            order.insert(0, expected)
        for fixture in target[3:]:
            expected = fixture["expected_commitment_enum"]
            order = fixture["menu_order"]
            assert isinstance(expected, str) and isinstance(order, list)
            if order[0] == expected:
                order.append(order.pop(0))
        result = evaluate_leak_audit(fixtures)
        cell = next(c for c in result.cells if c.leg == "L1" and c.stratum == "irrelevant")
        self.assertAlmostEqual(cell.accuracy, 0.30)
        self.assertAlmostEqual(cell.fail_threshold, 0.30)
        self.assertTrue(cell.passed)

    def test_mixed_k_refused(self):
        fixtures = _suite()
        fixtures[0]["menu_order"] = ["approve", "defer", "reject", "hold"]
        fixtures[0]["expected_commitment_enum"] = "approve"
        result = evaluate_leak_audit(fixtures)
        self.assertFalse(result.ok)
        self.assertEqual(result.refusals, ("mixed_action_set_size",))

    def test_determinism(self):
        fixtures = _suite(leaky=True)
        first = evaluate_leak_audit(fixtures)
        for _ in range(50):
            self.assertEqual(evaluate_leak_audit(fixtures), first)
            self.assertEqual(
                check_no_lexical_marking(fixtures),
                check_no_lexical_marking(fixtures),
            )


if __name__ == "__main__":
    unittest.main()
