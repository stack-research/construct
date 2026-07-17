"""Conformance vectors for the v2 candidate scope-comparison rule."""

from __future__ import annotations

import unittest

from harness.efc_check import ProvenanceRecord, ProvenanceStore, run_scope_provenance_check
from harness.efc_scope_comparison_v2 import (
    RULE_PATH,
    build_candidate_wire_rule,
    compare_scope_covers,
    derive_scope_verdict,
    load_conformance_vectors,
    scope_comparison_pin_payload,
    verify_conformance_vectors,
)
from tests.efc_wire_fixtures import exact_equality_rule, token_cover_rule


class TestScopeComparisonConformance(unittest.TestCase):
    def test_pinned_artifact_loads(self):
        pins = scope_comparison_pin_payload()
        self.assertEqual(pins["rule_id"], "efc_scope_comparison_candidate_v2")
        self.assertTrue(pins["rule_artifact_file_sha256"])
        self.assertTrue(pins["interpreter_sha256"])
        self.assertTrue(pins["conformance_vectors_sha256"])

    def test_conformance_vectors_pass(self):
        refusals = verify_conformance_vectors()
        self.assertEqual(refusals, [], refusals)

    def test_order_permutation_covers_on_interpreter(self):
        vectors = load_conformance_vectors()["vectors"]
        probe = next(v for v in vectors if v["id"] == "order-permutation-covers")
        auth = probe["authoritative_scope"]
        dec = probe["decision_scope"]
        verdict, missed = derive_scope_verdict(auth, dec)
        self.assertEqual(verdict, "covers")
        self.assertIsNone(missed)
        self.assertTrue(compare_scope_covers(auth, dec))

    def test_wire_exemplars_disagree_on_order_permutation(self):
        vectors = load_conformance_vectors()["vectors"]
        probe = next(v for v in vectors if v["id"] == "order-permutation-covers")
        auth = probe["authoritative_scope"]
        dec = probe["decision_scope"]
        self.assertFalse(token_cover_rule().compare(auth, dec))
        self.assertFalse(exact_equality_rule().compare(auth, dec))

    def test_validator_and_check_path_agree_on_vectors(self):
        rule = build_candidate_wire_rule(RULE_PATH)
        vectors = load_conformance_vectors()["vectors"]
        for vector in vectors:
            auth = vector["authoritative_scope"]
            dec = vector["decision_scope"]
            ref = f"ref://conformance/{vector['id']}"
            store = ProvenanceStore([
                ProvenanceRecord(
                    oracle_id="ORACLE-CONFORMANCE",
                    source_reference=ref,
                    authoritative_scope=auth,
                    cited_text="conformance vector provenance",
                )
            ])
            verdict, missed = derive_scope_verdict(auth, dec)
            covers = compare_scope_covers(auth, dec)
            evidence = run_scope_provenance_check(store, ref, dec, rule)
            self.assertEqual(verdict, vector["expect_verdict"], vector["id"])
            self.assertEqual(missed, vector["expect_missed_dimension"], vector["id"])
            self.assertEqual(covers, vector["expect_covers"], vector["id"])
            self.assertEqual(evidence.scope_matches, vector["expect_covers"], vector["id"])
            self.assertEqual(evidence.comparison_rule_id, rule.rule_id)

    def test_suite_hash_binds_scope_comparison_pins(self):
        from harness.efc_fixtures_v2 import suite_hash
        from tests.efc_v2_test_fixtures import make_minimal_record_store, make_minimal_suite

        suite = make_minimal_suite(1)
        store = make_minimal_record_store(suite)
        h1 = suite_hash(suite, k_pairs=1, record_store=store)
        h2 = suite_hash(suite, k_pairs=1, record_store=store)
        self.assertEqual(h1, h2)
