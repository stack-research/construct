"""Conformance vectors for EFC v2 leak audit."""

from __future__ import annotations

import unittest

from harness.efc_leak_audit_v2 import L3_THRESHOLD, evaluate_leak_audit
from tests.efc_v2_test_fixtures import make_minimal_suite


class TestLeakAuditV2(unittest.TestCase):
    def test_l3_threshold_pinned(self):
        self.assertAlmostEqual(L3_THRESHOLD, 0.60)

    def test_minimal_suite_passes_when_predictors_fail(self):
        result = evaluate_leak_audit(make_minimal_suite(2))
        self.assertTrue(result.ok)
        legs = {cell.leg for cell in result.cells}
        self.assertIn("L3", legs)
