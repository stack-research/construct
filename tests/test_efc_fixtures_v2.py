"""Conformance vectors for EFC v2 fixture validators."""

from __future__ import annotations

import copy
import unittest

from harness.efc_fixtures_v2 import (
    EXPECTED_FIXTURE_COUNT,
    K_PAIRS,
    fixture_identity_hash,
    suite_hash,
    validate_suite,
)
from harness.efc_menu_composition_v2 import (
    expected_opaque_source_handle_for_fixture,
    expected_source_reference,
)
from tests.efc_v2_test_fixtures import make_minimal_record_store, make_minimal_suite


def _validated_suite(block_count: int = 1, *, mutate=None):
    suite = make_minimal_suite(block_count)
    if mutate is not None:
        mutate(suite)
    store = make_minimal_record_store(suite)
    return suite, store


class TestFixturesV2(unittest.TestCase):
    def test_minimal_suite_validates(self):
        suite, store = _validated_suite(2)
        result = validate_suite(suite, expected_k_pairs=2, record_store=store)
        self.assertTrue(result.ok, result.refusals)

    def test_expected_fixture_count_constant(self):
        self.assertEqual(EXPECTED_FIXTURE_COUNT, K_PAIRS * 3)

    def test_fixture_identity_hash_stable(self):
        fixture = make_minimal_suite(1)[0]
        h1 = fixture_identity_hash(fixture)
        h2 = fixture_identity_hash(fixture)
        self.assertEqual(h1, h2)

    def test_fixture_hash_binds_task_body(self):
        fixtures = make_minimal_suite(1)
        original = fixture_identity_hash(fixtures[0])
        mutated = copy.deepcopy(fixtures[0])
        mutated["task_body"] = mutated["task_body"] + " SHOPPED"
        self.assertNotEqual(fixture_identity_hash(mutated), original)

    def test_fixture_hash_binds_source_reference(self):
        fixtures = make_minimal_suite(1)
        original = fixture_identity_hash(fixtures[0])
        mutated = copy.deepcopy(fixtures[0])
        mutated["source_reference"] = "ref://opaque/shopped-handle"
        self.assertNotEqual(fixture_identity_hash(mutated), original)

    def test_suite_hash_covers_membership_and_order(self):
        suite_a, store_a = _validated_suite(2)
        suite_b, store_b = _validated_suite(2)
        suite_b[0]["task_body"] = suite_b[0]["task_body"] + " variant"
        store_b = make_minimal_record_store(suite_b)
        h1 = suite_hash(suite_a, k_pairs=2, record_store=store_a)
        h2 = suite_hash(suite_b, k_pairs=2, record_store=store_b)
        self.assertNotEqual(h1, h2)

    def test_suite_hash_binds_input_order(self):
        suite, store = _validated_suite(2)
        reversed_suite = list(reversed(suite))
        h1 = suite_hash(suite, k_pairs=2, record_store=store)
        h2 = suite_hash(reversed_suite, k_pairs=2, record_store=store)
        self.assertNotEqual(h1, h2)

    def test_suite_hash_binds_record_store(self):
        suite, store = _validated_suite(1)
        h1 = suite_hash(suite, k_pairs=1, record_store=store)
        mutated_store = make_minimal_record_store(suite)
        record = mutated_store.records[0]
        swapped = type(record)(
            record_id=record.record_id,
            source_reference=record.source_reference,
            authoritative_scope=record.authoritative_scope + ";endpoint=api.other/v2",
        )
        from harness.efc_provenance_record_store_v2 import build_record_store

        alt_store = build_record_store([swapped, *mutated_store.records[1:]])
        h2 = suite_hash(suite, k_pairs=1, record_store=alt_store)
        self.assertNotEqual(h1, h2)


class TestMutationProbes(unittest.TestCase):
    """Sol structural-review mutation probes — must fail validation."""

    def _mutated_suite(self, **mutations):
        suite = make_minimal_suite(2)
        target = next(f for f in suite if f["fixture_id"] == "block-0000-match")
        for key, val in mutations.items():
            target[key] = val
        store = make_minimal_record_store(suite)
        return suite, store

    def test_mutated_task_body_fails(self):
        suite, store = self._mutated_suite(task_body="entirely different decision problem")
        result = validate_suite(suite, expected_k_pairs=2, record_store=store)
        self.assertFalse(result.ok)
        self.assertIn("counterfactual_surface_mismatch", result.refusals)

    def test_mutated_action_set_fails(self):
        suite, store = self._mutated_suite(
            action_set=["alpha_commit", "beta_commit", "gamma_hold", "epsilon_hold"],
            role_map={
                "alpha_commit": "commit",
                "beta_commit": "commit",
                "gamma_hold": "non_commit",
                "epsilon_hold": "non_commit",
            },
        )
        result = validate_suite(suite, expected_k_pairs=2, record_store=store)
        self.assertFalse(result.ok)

    def test_mutated_menu_order_fails(self):
        suite, store = self._mutated_suite(
            menu_order=["alpha_commit", "beta_commit", "gamma_hold", "delta_hold"]
        )
        result = validate_suite(suite, expected_k_pairs=2, record_store=store)
        self.assertFalse(result.ok)
        self.assertIn("counterfactual_surface_mismatch", result.refusals)

    def test_different_menu_order_across_mates_fails(self):
        suite = make_minimal_suite(1)
        mismatch = next(f for f in suite if f["stratum"] == "mismatch")
        mismatch["menu_order"] = list(reversed(mismatch["menu_order"]))
        store = make_minimal_record_store(suite)
        result = validate_suite(suite, expected_k_pairs=1, record_store=store)
        self.assertFalse(result.ok)
        self.assertIn("counterfactual_surface_mismatch", result.refusals)

    def test_scope_dimension_concentration_fails(self):
        suite = make_minimal_suite(5)
        for fx in suite:
            if fx["stratum"] == "mismatch":
                fx["missing_scope_dimension"] = "population"
            if fx["stratum"] == "match":
                fx["missing_scope_dimension"] = "population"
        store = make_minimal_record_store(suite)
        result = validate_suite(suite, expected_k_pairs=5, record_store=store)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("scope_dimension_histogram_imbalance" in r for r in result.refusals)
        )

    def test_handle_orientation_imbalance_fails(self):
        suite = make_minimal_suite(4)
        for fx in suite:
            if fx["stratum"] in ("match", "mismatch"):
                fx["handle_orientation"] = "A"
                handle = expected_opaque_source_handle_for_fixture(fx)
                fx["opaque_source_handle"] = handle
                fx["source_reference"] = expected_source_reference(handle)
        store = make_minimal_record_store(suite)
        result = validate_suite(suite, expected_k_pairs=4, record_store=store)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("handle_orientation_imbalance" in r for r in result.refusals)
        )

    def test_mutated_source_reference_only_fails(self):
        suite = make_minimal_suite(2)
        match = next(f for f in suite if f["fixture_id"] == "block-0000-match")
        match["source_reference"] = "ref://opaque/arbitrary-shopped-handle"
        store = make_minimal_record_store(suite)
        result = validate_suite(suite, expected_k_pairs=2, record_store=store)
        self.assertFalse(result.ok)
        self.assertTrue(
            any(
                r in result.refusals
                for r in (
                    "provenance_record_missing",
                    "handle_orientation_handle_mismatch",
                )
            )
        )

    def test_scope_bit_contradicting_fetched_record_fails(self):
        suite = make_minimal_suite(1)
        store = make_minimal_record_store(suite)
        mismatch = next(f for f in suite if f["stratum"] == "mismatch")
        mismatch["scope_bit"] = "covers"
        mismatch["expected_commitment_enum"] = mismatch["coherent_commit_action"]
        result = validate_suite(suite, expected_k_pairs=1, record_store=store)
        self.assertFalse(result.ok)
        self.assertIn("provenance_scope_bit_contradicts_record", result.refusals)

    def test_lexical_scope_bit_in_handles_fails(self):
        from harness.efc_menu_composition_v2 import check_fixture_composition

        suite = make_minimal_suite(1)
        match = next(f for f in suite if f["stratum"] == "match")
        match["opaque_source_handle"] = "handle-block-0000-covers"
        match["source_reference"] = "ref://opaque/handle-block-0000-covers"
        comp = check_fixture_composition(match)
        self.assertFalse(comp.ok)
        self.assertIn("provenance_lexical_scope_leak", comp.refusal)
