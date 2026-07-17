"""Conformance vectors for EFC v2 commitment wire."""

from __future__ import annotations

import unittest

from harness.efc_commitment_wire_v2 import (
    ACTION_SET_MAX,
    ACTION_SET_MIN,
    validate_action_set,
    validate_commitment_wire,
)


class TestCommitmentWireV2(unittest.TestCase):
    def test_four_action_menu_only(self):
        self.assertEqual(ACTION_SET_MIN, 4)
        self.assertEqual(ACTION_SET_MAX, 4)
        ok = validate_action_set(["a", "b", "c", "d"])
        self.assertTrue(ok.ok)
        bad = validate_action_set(["a", "b", "c"])
        self.assertFalse(bad.ok)

    def test_exact_enum_validation(self):
        action_set = ["proceed", "hold", "defer", "close"]
        wire = {"commitment_enum": "proceed"}
        result = validate_commitment_wire(wire, action_set)
        self.assertEqual(result.outcome, "commitment_valid")
