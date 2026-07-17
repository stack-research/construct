"""Conformance vectors for EFC v2 fixture validators."""

from __future__ import annotations

import unittest

from harness.efc_fixtures_v2 import (
    EXPECTED_FIXTURE_COUNT,
    K_PAIRS,
    fixture_identity_hash,
    validate_suite,
)
from tests.efc_v2_test_fixtures import make_minimal_suite


class TestFixturesV2(unittest.TestCase):
    def test_minimal_suite_validates(self):
        result = validate_suite(make_minimal_suite(2), expected_k_pairs=2)
        self.assertTrue(result.ok, result.refusals)

    def test_expected_fixture_count_constant(self):
        self.assertEqual(EXPECTED_FIXTURE_COUNT, K_PAIRS * 3)

    def test_fixture_identity_hash_stable(self):
        fixture = make_minimal_suite(1)[0]
        h1 = fixture_identity_hash(fixture)
        h2 = fixture_identity_hash(fixture)
        self.assertEqual(h1, h2)
