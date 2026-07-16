"""Conformance vectors: menu composition rules (SPEC v1 §2.5.5, §8.6)."""

from __future__ import annotations

import unittest

from harness.efc_menu_composition_v1 import (COLD_FIXTURE_REVIEWER_SEAT,
                                             CanonicalActionSet,
                                             canonicalize_action_set,
                                             check_fixture_composition,
                                             check_suite_ordinal_uniformity,
                                             derive_expected_enum,
                                             max_abs_dev_bound)

# NFC "café" vs NFD "café"
CAFE_NFC = "caf\u00e9"
CAFE_NFD = "cafe\u0301"

SHARED_POOL = ["defer", "reject", "hold", "withdraw"]
ROLE_MAP = {
    "approve": "commit",
    "defer": "non_commit",
    "reject": "baseline",
}


def _attestation(fixture_id: str, stratum: str) -> dict[str, str]:
    return {
        "fixture_id": fixture_id,
        "stratum": stratum,
        "reviewer_seat": COLD_FIXTURE_REVIEWER_SEAT,
        "reviewed_at": "2026-07-16T08:00:00Z",
        "attestation_id": f"att-{fixture_id}",
    }


def _fixture(
    *,
    fixture_id: str = "fx-001",
    stratum: str = "match_commit",
    action_set: list[str] | None = None,
    menu_order: list[str] | None = None,
    expected: str = "approve",
    role_map: dict[str, str] | None = None,
    shared_pool: list[str] | None = None,
) -> dict[str, object]:
    labels = action_set or ["approve", "defer", "reject"]
    return {
        "fixture_id": fixture_id,
        "stratum": stratum,
        "action_set": labels,
        "menu_order": menu_order or list(labels),
        "role_map": role_map or dict(ROLE_MAP),
        "expected_commitment_enum": expected,
        "shared_decoy_pool": shared_pool or SHARED_POOL,
        "plausibility_attestation": _attestation(fixture_id, stratum),
    }


class TestCanonicalizeActionSet(unittest.TestCase):
    def test_valid_three_member_set(self):
        result = canonicalize_action_set(["approve", "defer", "reject"])
        self.assertTrue(result.ok)
        assert result.canonical is not None
        self.assertEqual(result.canonical.labels, ("approve", "defer", "reject"))

    def test_nfc_nfd_dual_member_refused(self):
        result = canonicalize_action_set([CAFE_NFC, CAFE_NFD, "hold"])
        self.assertFalse(result.ok)
        self.assertEqual(result.failure, "duplicate_nfc_form")

    def test_zero_width_label_refused(self):
        result = canonicalize_action_set(["approve\u200b", "defer", "reject"])
        self.assertFalse(result.ok)
        self.assertEqual(result.failure, "forbidden_format_character")

    def test_whitespace_only_label_refused(self):
        result = canonicalize_action_set(["approve", "   ", "reject"])
        self.assertFalse(result.ok)
        self.assertEqual(result.failure, "whitespace_only_label")

    def test_untrimmed_label_refused(self):
        result = canonicalize_action_set(["approve", " defer", "reject"])
        self.assertFalse(result.ok)
        self.assertEqual(result.failure, "untrimmed_label")

    def test_trailing_whitespace_refused(self):
        result = canonicalize_action_set(["approve", "defer ", "reject"])
        self.assertFalse(result.ok)
        self.assertEqual(result.failure, "untrimmed_label")

    def test_duplicate_byte_label_refused(self):
        result = canonicalize_action_set(["approve", "defer", "approve"])
        self.assertFalse(result.ok)
        self.assertEqual(result.failure, "duplicate_byte_label")

    def test_action_set_too_small(self):
        result = canonicalize_action_set(["a", "b"])
        self.assertFalse(result.ok)
        self.assertEqual(result.failure, "action_set_too_small")

    def test_action_set_too_large(self):
        result = canonicalize_action_set(list("abcdefg"))
        self.assertFalse(result.ok)
        self.assertEqual(result.failure, "action_set_too_large")


class TestDeriveExpectedEnum(unittest.TestCase):
    def setUp(self) -> None:
        self.canonical = CanonicalActionSet(labels=("approve", "defer", "reject"))

    def test_match_commit_selects_commit_role(self):
        result = derive_expected_enum("match_commit", self.canonical, ROLE_MAP)
        self.assertTrue(result.ok)
        self.assertEqual(result.expected, "approve")

    def test_match_mismatch_selects_non_commit(self):
        result = derive_expected_enum("match_mismatch", self.canonical, ROLE_MAP)
        self.assertTrue(result.ok)
        self.assertEqual(result.expected, "defer")

    def test_irrelevant_selects_baseline(self):
        result = derive_expected_enum("irrelevant", self.canonical, ROLE_MAP)
        self.assertTrue(result.ok)
        self.assertEqual(result.expected, "reject")

    def test_tie_break_lexicographic_minimum(self):
        role_map = {
            "approve": "non_commit",
            "defer": "non_commit",
            "reject": "baseline",
        }
        result = derive_expected_enum("match_mismatch", self.canonical, role_map)
        self.assertTrue(result.ok)
        self.assertEqual(result.expected, "approve")

    def test_role_unoccupied_refused(self):
        role_map = {
            "approve": "commit",
            "defer": "commit",
            "reject": "baseline",
        }
        result = derive_expected_enum("match_mismatch", self.canonical, role_map)
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal, "role_unoccupied")

    def test_unknown_stratum_refused(self):
        result = derive_expected_enum("bogus", self.canonical, ROLE_MAP)
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal, "unknown_stratum")

    def test_role_map_incomplete_refused(self):
        result = derive_expected_enum(
            "match_commit",
            self.canonical,
            {"approve": "commit", "defer": "non_commit"},
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal, "role_map_incomplete")


class TestCheckFixtureComposition(unittest.TestCase):
    def test_valid_fixture_passes(self):
        result = check_fixture_composition(_fixture())
        self.assertTrue(result.ok)
        self.assertIsNone(result.refusal)

    def test_expected_not_in_action_set_refused(self):
        fx = _fixture(expected="withdraw")
        result = check_fixture_composition(fx)
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal, "expected_not_in_action_set")

    def test_expected_neq_mapping_output_refused(self):
        fx = _fixture(stratum="match_mismatch", expected="approve")
        result = check_fixture_composition(fx)
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal, "expected_neq_mapping_output")

    def test_decoy_not_in_shared_pool_refused(self):
        fx = _fixture(shared_pool=["withdraw"])
        result = check_fixture_composition(fx)
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal, "decoy_not_in_shared_pool")

    def test_menu_order_not_permutation_refused(self):
        fx = _fixture(menu_order=["approve", "reject", "reject"])
        result = check_fixture_composition(fx)
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal, "menu_order_not_permutation")

    def test_menu_order_unknown_label_refused(self):
        fx = _fixture(menu_order=["approve", "defer", "ghost"])
        result = check_fixture_composition(fx)
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal, "menu_order_unknown_label")

    def test_missing_plausibility_attestation_refused(self):
        fx = _fixture()
        del fx["plausibility_attestation"]
        result = check_fixture_composition(fx)
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal, "missing_plausibility_attestation")

    def test_malformed_plausibility_wrong_seat_refused(self):
        fx = _fixture()
        att = dict(fx["plausibility_attestation"])  # type: ignore[arg-type]
        att["reviewer_seat"] = "fixture_author"
        fx["plausibility_attestation"] = att
        result = check_fixture_composition(fx)
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal, "malformed_plausibility_attestation")

    def test_canonicalization_failure_surfaces(self):
        fx = _fixture(action_set=["approve\u200b", "defer", "reject"])
        result = check_fixture_composition(fx)
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal, "canonicalization_failed")
        self.assertEqual(result.canonicalization_failure,
                         "forbidden_format_character")

    def test_nfc_nfd_dual_in_fixture_refused(self):
        fx = _fixture(action_set=[CAFE_NFC, CAFE_NFD, "hold"],
                      menu_order=[CAFE_NFC, CAFE_NFD, "hold"],
                      expected=CAFE_NFC,
                      role_map={CAFE_NFC: "commit", CAFE_NFD: "non_commit",
                                "hold": "baseline"},
                      shared_pool=[CAFE_NFD, "hold"])
        result = check_fixture_composition(fx)
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal, "canonicalization_failed")
        self.assertEqual(result.canonicalization_failure, "duplicate_nfc_form")


class TestSuiteOrdinalUniformity(unittest.TestCase):
    def test_max_abs_dev_bound_formula(self):
        self.assertEqual(max_abs_dev_bound(5, 3), 1)
        self.assertEqual(max_abs_dev_bound(6, 3), 1)
        self.assertEqual(max_abs_dev_bound(3, 3), 1)

    def test_uniform_suite_passes(self):
        fixtures = [
            _fixture(fixture_id=f"fx-{i}", stratum="match_commit",
                     menu_order=["defer", "approve", "reject"],
                     expected="approve")
            for i in range(3)
        ]
        # rotate expected index: 1, 1, 1 — need spread indices
        fixtures[0]["menu_order"] = ["defer", "approve", "reject"]  # idx 1
        fixtures[1]["menu_order"] = ["approve", "defer", "reject"]  # idx 0
        fixtures[2]["menu_order"] = ["defer", "reject", "approve"]  # idx 2
        for fx in fixtures:
            fx["plausibility_attestation"] = _attestation(
                str(fx["fixture_id"]), "match_commit")

        result = check_suite_ordinal_uniformity(fixtures)
        self.assertTrue(result.ok)
        assert result.histogram is not None
        self.assertEqual(result.histogram, (1, 1, 1))

    def test_ordinal_deviation_bound_enforced(self):
        fixtures = [
            _fixture(fixture_id=f"fx-{i}", stratum="match_commit",
                     menu_order=["approve", "defer", "reject"],
                     expected="approve")
            for i in range(5)
        ]
        for fx in fixtures:
            fx["plausibility_attestation"] = _attestation(
                str(fx["fixture_id"]), "match_commit")

        result = check_suite_ordinal_uniformity(fixtures)
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal, "ordinal_uniformity_exceeded")
        assert result.histogram is not None
        self.assertEqual(result.histogram, (5, 0, 0))
        self.assertEqual(result.max_abs_dev_bound, 1)
        assert result.max_observed_deviation is not None
        self.assertGreater(result.max_observed_deviation, 1)


if __name__ == "__main__":
    unittest.main()
