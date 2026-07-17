"""Conformance vectors for EFC v2 menu composition."""

from __future__ import annotations

import unittest

from harness.efc_menu_composition_v2 import (
    check_block_pair_structure,
    check_fixture_composition,
    derive_expected_enum_relevant,
)
from harness.efc_menu_composition_v2 import CanonicalActionSet
from tests.efc_v2_test_fixtures import make_minimal_suite


class TestMappingRule(unittest.TestCase):
    def test_covers_selects_commit_class(self):
        fx = make_minimal_suite(1)[0]
        canon = CanonicalActionSet(labels=tuple(fx["action_set"]))
        result = derive_expected_enum_relevant(
            scope_bit="covers",
            coherent_commit_action="alpha_commit",
            coherent_non_commit_action="gamma_hold",
            canonical_action_set=canon,
            role_map=fx["role_map"],
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.expected, "alpha_commit")

    def test_misses_selects_non_commit_class(self):
        fx = make_minimal_suite(1)[1]
        result = derive_expected_enum_relevant(
            scope_bit="misses",
            coherent_commit_action="alpha_commit",
            coherent_non_commit_action="gamma_hold",
            canonical_action_set=CanonicalActionSet(labels=tuple(fx["action_set"])),
            role_map=fx["role_map"],
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.expected, "gamma_hold")

    def test_fixture_composition_matches_pinned_expected(self):
        for fixture in make_minimal_suite(2):
            comp = check_fixture_composition(fixture)
            self.assertTrue(comp.ok, fixture["fixture_id"])

    def test_block_pair_structure(self):
        comp = check_block_pair_structure(make_minimal_suite(3))
        self.assertTrue(comp.ok)
