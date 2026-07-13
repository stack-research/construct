"""Wire tests: named-check adapter boundary (sealed §2.2/§10.1; resolution
A: the executor is WIRE-ONLY, the adapter carries injected semantics, and NO
production check-contract hash can be minted in this workspace)."""

from __future__ import annotations

import unittest
from dataclasses import fields

from harness import efc_contracts as c
from harness.efc_check import (CheckContractError, CheckEvidence,
                               ProvenanceRecord, ProvenanceStore,
                               WireComparisonRule,
                               check_adapter_contract_hash,
                               check_adapter_contract_payload,
                               check_contract_hash,
                               pending_check_contract_identity,
                               run_scope_provenance_check,
                               validate_wire_comparison_rule,
                               wire_rule_contract_hash)
from tests.efc_wire_fixtures import (exact_equality_rule,
                                     fictional_source_ref, make_store,
                                     token_cover_rule)


class TestWireComparisonRule(unittest.TestCase):
    """B1/resolution-A tests: injected wire executor, no production mint."""

    def setUp(self):
        self.ref = fictional_source_ref(0)
        self.store = make_store([self.ref])

    def test_adapter_carries_rather_than_chooses_semantics(self):
        """Two injected fictional wire rules, same adapter, same inputs,
        different verdicts — semantics live in the rule, not the adapter."""
        scope = "fictional examplon deployments of the glimmer subsystem"
        a = run_scope_provenance_check(self.store, self.ref, scope,
                                       token_cover_rule())
        b = run_scope_provenance_check(self.store, self.ref, scope,
                                       exact_equality_rule())
        self.assertTrue(a.scope_matches)     # tokens covered
        self.assertFalse(b.scope_matches)    # not byte-equal
        self.assertEqual(a.comparison_rule_id, "wire_fictional_token_cover")
        self.assertEqual(b.comparison_rule_id, "wire_fictional_exact_equality")

    def test_rule_is_required(self):
        with self.assertRaises(CheckContractError):
            run_scope_provenance_check(self.store, self.ref, "x", None)

    def test_rule_shape_validated(self):
        with self.assertRaises(CheckContractError):
            validate_wire_comparison_rule(WireComparisonRule(
                rule_id="r", contract={}, compare=lambda a, b: True))
        with self.assertRaises(CheckContractError):
            validate_wire_comparison_rule(WireComparisonRule(
                rule_id="r", contract={"rule_id": "other"},
                compare=lambda a, b: True))
        with self.assertRaises(CheckContractError):
            validate_wire_comparison_rule(WireComparisonRule(
                rule_id="r", contract={"rule_id": "r"},
                compare="not-callable"))

    def test_non_boolean_verdict_fails_closed(self):
        bad = WireComparisonRule(rule_id="r", contract={"rule_id": "r"},
                                 compare=lambda a, b: "yes")
        with self.assertRaises(CheckContractError):
            run_scope_provenance_check(self.store, self.ref, "x", bad)

    def test_no_production_check_contract_hash_exists(self):
        """Resolution A mandated test: a callable wire rule — or ANY input —
        cannot mint a production check-contract hash; the identity is
        typed-pending."""
        with self.assertRaises(CheckContractError):
            check_contract_hash(token_cover_rule())
        with self.assertRaises(CheckContractError):
            check_contract_hash({"rule_id": "x", "contract": {}})
        with self.assertRaises(CheckContractError):
            check_contract_hash()
        pending = pending_check_contract_identity()
        self.assertEqual(pending["status"], "pending")
        self.assertEqual(pending["adapter_contract_sha256"],
                         check_adapter_contract_hash())

    def test_wire_rule_hash_is_wire_named_and_tracks_the_rule(self):
        h_a = wire_rule_contract_hash(token_cover_rule())
        h_b = wire_rule_contract_hash(exact_equality_rule())
        self.assertNotEqual(h_a, h_b)
        self.assertEqual(h_a, wire_rule_contract_hash(token_cover_rule()))


class TestCheckBoundary(unittest.TestCase):
    def setUp(self):
        self.ref = fictional_source_ref(0)
        self.store = make_store([self.ref])
        self.rule = token_cover_rule()

    def test_verdict_carrying_both_directions(self):
        match = run_scope_provenance_check(
            self.store, self.ref,
            "fictional examplon deployments of the glimmer subsystem",
            self.rule)
        self.assertTrue(match.scope_matches)
        mismatch = run_scope_provenance_check(
            self.store, self.ref, "totally unrelated sprocket scope",
            self.rule)
        self.assertFalse(mismatch.scope_matches)
        self.assertEqual(match.check_id, c.CHECK_ID)

    def test_evidence_schema_is_closed(self):
        """§2.2: no field exists for a final answer, recommendation, or
        commit/defer instruction."""
        names = {f.name for f in fields(CheckEvidence)}
        self.assertEqual(names, {
            "check_id", "comparison_rule_id", "source_reference", "oracle_id",
            "cited_provenance", "scope_matches",
            "controller_source_read_tokens", "check_output_tokens"})

    def test_unpinned_reference_fails_closed(self):
        with self.assertRaises(CheckContractError):
            run_scope_provenance_check(self.store, "wire://fictional/absent",
                                       "x", self.rule)

    def test_source_read_ceiling_enforced(self):
        big = ProvenanceStore([ProvenanceRecord(
            "FICTIONAL-BIG", "wire://fictional/big",
            authoritative_scope="pad " * 600, cited_text="x")])
        with self.assertRaises(CheckContractError):
            run_scope_provenance_check(big, "wire://fictional/big", "pad",
                                       self.rule)

    def test_empty_inputs_refused(self):
        with self.assertRaises(CheckContractError):
            run_scope_provenance_check(self.store, "", "scope", self.rule)
        with self.assertRaises(CheckContractError):
            run_scope_provenance_check(self.store, self.ref, "", self.rule)

    def test_output_tokens_within_ceiling(self):
        evidence = run_scope_provenance_check(self.store, self.ref, "glimmer",
                                              self.rule)
        self.assertLessEqual(evidence.check_output_tokens,
                             c.MAX_EXTERNAL_CHECK_OUTPUT_TOKENS)
        self.assertLessEqual(evidence.controller_source_read_tokens,
                             c.MAX_CONTROLLER_SOURCE_READ_TOKENS)

    def test_adapter_contract_hash_covers_schema_and_ceilings(self):
        """B4: mutate a contract component → the hash changes."""
        import hashlib
        import json
        payload = check_adapter_contract_payload()
        self.assertEqual(payload["placebo_position_gate"],
                         "structural_single_insertion_point")
        mutated = dict(payload)
        mutated["ceilings"] = dict(payload["ceilings"],
                                   check_output_tokens=999)
        h = hashlib.sha256(json.dumps(mutated, sort_keys=True,
                                      separators=(",", ":")).encode()
                           ).hexdigest()
        self.assertNotEqual(h, check_adapter_contract_hash())


if __name__ == "__main__":
    unittest.main()
