"""Wire tests for the PRF closed predicate AST (SPEC_PAUSE_RESUME v0.1 §5).

Mock structures only — nothing here is evidence about resumability; the suite
proves the closure refuses by name what the spec excludes (unknown fields and
operators, numeric valuation, free shapes) and that a validated library hashes
canonically."""

from __future__ import annotations

import unittest

from harness.predicate_ast import (PredicateClosureError, evaluate,
                                   library_hash, validate)


def V(node):
    validate(node)
    return node


class TestClosureRefusals(unittest.TestCase):
    def test_unknown_operator_refused(self):
        with self.assertRaises(PredicateClosureError):
            validate({"op": "regex", "field": "surface_id", "value": ".*"})

    def test_unknown_field_refused(self):
        with self.assertRaises(PredicateClosureError):
            validate({"op": "eq", "field": "answer_text", "value": "x"})

    def test_branch_route_field_refused(self):
        with self.assertRaises(PredicateClosureError):
            validate({"op": "eq", "field": "branch", "value": "resumable_state"})

    def test_numeric_valuation_refused(self):
        # scores/weights/counts are the answer-axis smuggling shape
        with self.assertRaises(PredicateClosureError):
            validate({"op": "eq", "field": "read_index", "value": 3})

    def test_extra_keys_refused(self):
        with self.assertRaises(PredicateClosureError):
            validate({"op": "eq", "field": "surface_id", "value": "S1",
                      "note": "prose rider"})

    def test_empty_in_refused(self):
        with self.assertRaises(PredicateClosureError):
            validate({"op": "in", "field": "surface_tag", "values": []})

    def test_single_arm_and_refused(self):
        with self.assertRaises(PredicateClosureError):
            validate({"op": "and", "args": [
                {"op": "exists", "field": "surface_id"}]})

    def test_nested_violation_refused(self):
        with self.assertRaises(PredicateClosureError):
            validate({"op": "and", "args": [
                {"op": "exists", "field": "surface_id"},
                {"op": "eq", "field": "model_tag", "value": "x"}]})

    def test_bad_library_never_hashes(self):
        with self.assertRaises(PredicateClosureError):
            library_hash({"P1": {"op": "regex", "field": "surface_id",
                                 "value": ".*"}})


class TestEvaluation(unittest.TestCase):
    def test_eq_and_absence(self):
        node = V({"op": "eq", "field": "surface_tag", "value": "moved"})
        self.assertTrue(evaluate(node, {"surface_tag": "moved"}))
        self.assertFalse(evaluate(node, {}))

    def test_neq_requires_presence(self):
        node = V({"op": "neq", "field": "option_status", "value": "live"})
        self.assertFalse(evaluate(node, {}))          # absent is not "different"
        self.assertTrue(evaluate(node, {"option_status": "blocked"}))

    def test_changed_needs_both_hashes(self):
        node = V({"op": "changed"})
        self.assertTrue(evaluate(node, {"surface_hash_t0": "a",
                                        "surface_hash_t1": "b"}))
        self.assertFalse(evaluate(node, {"surface_hash_t0": "a",
                                         "surface_hash_t1": "a"}))
        self.assertFalse(evaluate(node, {"surface_hash_t0": "a"}))

    def test_read_has_tag_witness_context(self):
        node = V({"op": "read_has_tag", "tag": "missing_evidence_for_option"})
        self.assertTrue(evaluate(node, {"surface_tags":
                                        ["missing_evidence_for_option"]}))
        self.assertFalse(evaluate(node, {"surface_tags": []}))
        self.assertFalse(evaluate(node, {}))

    def test_boolean_composition(self):
        node = V({"op": "and", "args": [
            {"op": "eq", "field": "catalog_epoch", "value": "t1"},
            {"op": "not", "arg": {"op": "eq", "field": "world_leg",
                                  "value": "noise"}}]})
        self.assertTrue(evaluate(node, {"catalog_epoch": "t1",
                                        "world_leg": "moved"}))
        self.assertFalse(evaluate(node, {"catalog_epoch": "t1",
                                         "world_leg": "noise"}))

    def test_library_hash_stable_and_order_free(self):
        lib_a = {"P1": {"op": "changed"},
                 "P2": {"op": "eq", "field": "surface_tag", "value": "x"}}
        lib_b = dict(reversed(list(lib_a.items())))
        self.assertEqual(library_hash(lib_a), library_hash(lib_b))


if __name__ == "__main__":
    unittest.main()
