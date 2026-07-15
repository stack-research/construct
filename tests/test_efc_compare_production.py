"""Production comparison contract — conformance, hash pinning, isolation."""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from harness.efc_check import (CheckContractError, ProvenanceRecord,
                               ProvenanceStore, WireComparisonRule,
                               check_adapter_contract_hash,
                               check_contract_hash,
                               production_check_contract_hash,
                               run_production_scope_check,
                               validate_production_comparison_contract)
from harness.efc_compare_expectations import write_expectations
from harness.efc_compare_pin import (build_integration_report,
                                     refresh_pinned_artifacts)
from harness.efc_compare_inputs import (DISPOSITIVE_TASKS,
                                        build_structured_inputs,
                                        write_structured_inputs)
from harness.efc_compare_production import (ProductionCompareError,
                                            ProductionComparisonContract,
                                            build_production_contract,
                                            derivation_module_unreachable,
                                            execute_pinned_binding,
                                            interpret_operation_row,
                                            interpret_structured_input,
                                            production_contract_identity_payload,
                                            resolve_pinned_row,
                                            run_conformance_vector,
                                            validate_structured_input,
                                            wire_lookup_unreachable)
from harness.efc_compare_version import (CompareDomainError, compare_versions,
                                         parse_ghsa_range, parse_iso_date)

REPO = Path(__file__).resolve().parent.parent
VECTORS_PATH = REPO / "corpus/efc_calibration/comparison/conformance_vectors_v1.json"
STRUCTURED_PATH = REPO / "corpus/efc_calibration/comparison/structured_inputs_v1.json"
EXPECTATIONS_PATH = REPO / "corpus/efc_calibration/authoring_c2" / \
    "comparison_expectations_v1.json"
ORACLE_ROOT = REPO / "corpus/efc_calibration/oracle"


def _oracle_store() -> ProvenanceStore:
    records = []
    for task_id in DISPOSITIVE_TASKS:
        oracle = json.loads((ORACLE_ROOT / f"{task_id}.json").read_text())
        records.append(ProvenanceRecord(
            oracle_id=oracle["oracle_id"],
            source_reference=oracle["source_reference"],
            authoritative_scope=oracle["authoritative_scope"],
            cited_text=oracle["cited_text"],
            raw_sha256=oracle["raw_sha256"],
        ))
    return ProvenanceStore(records)


class TestProductionInterpreter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        write_expectations()
        refresh_pinned_artifacts()
        cls.contract = build_production_contract()

    def test_conformance_vectors(self):
        payload = json.loads(VECTORS_PATH.read_text())
        for vector in payload["vectors"]:
            got = run_conformance_vector(vector)
            self.assertEqual(got, vector["expect"], vector["id"])

    def test_version_endpoints(self):
        self.assertEqual(compare_versions("0.16.3", "0.16.3"), 0)
        self.assertEqual(compare_versions("0.16.2", "0.16.3"), -1)
        self.assertEqual(compare_versions("0.16.4", "0.16.3"), 1)

    def test_ghsa_fail_closed_forms(self):
        bad_ranges = [
            ">= 7.23.0 < 7.28.0",
            ">= 1.2.3 || < 2",
            ">= 1.2.3 garbage",
            ">=",
            "< < 2.0.0",
            ">= 1.0.0,, < 2.0.0",
            "^1.2.3",
            "~1.2.3",
        ]
        for text in bad_ranges:
            with self.subTest(text=text):
                with self.assertRaises(ProductionCompareError):
                    interpret_operation_row({
                        "operation": "ghsa_semver_membership",
                        "operands": {
                            "ecosystem": "npm",
                            "package": "pkg",
                            "version": "1.0.0",
                            "range_strings": [text],
                        },
                    })

    def test_ghsa_valid_population_ranges_still_parse(self):
        valid = [
            ">= 7.23.0, < 7.28.0",
            ">= 8.0.0, < 8.2.0",
            ">= 1.1.0, <= 1.8.3",
            "< 3.4.0",
        ]
        for text in valid:
            with self.subTest(text=text):
                constraints = parse_ghsa_range(text)
                self.assertTrue(constraints)

    def test_iso_invalid_calendar_date_fail_closed(self):
        with self.assertRaises(ProductionCompareError):
            interpret_operation_row({
                "operation": "eol_support_on_date",
                "operands": {
                    "product": "demo",
                    "cycle": "1.0",
                    "eol_date": "2026-02-30",
                    "check_date": "2026-06-01",
                },
            })
        with self.assertRaises(CompareDomainError):
            parse_iso_date("2026-02-30")

    def test_forbidden_expected_label_rejected(self):
        with self.assertRaises(ProductionCompareError):
            validate_structured_input({
                "operation": "cargo_affected_membership",
                "expected_scope_matches": True,
                "source_reference": "https://example.test/x",
                "raw_sha256": "a" * 64,
                "decision_scope_sha256": "b" * 64,
                "operands": {"ecosystem": "crates.io", "package": "x",
                             "version": "1.0.0", "upper_exclusive": "2.0.0"},
            })


class TestProductionContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        write_expectations()
        refresh_pinned_artifacts()
        cls.contract = build_production_contract()

    def test_production_hash_mints_and_mutates(self):
        h0 = production_check_contract_hash(self.contract)
        payload = production_contract_identity_payload(
            self.contract, check_adapter_contract_hash())
        mutated = dict(payload)
        mutated["operations"] = list(payload["operations"]) + ["bogus"]
        h1 = hashlib.sha256(json.dumps(mutated, sort_keys=True,
                                        separators=(",", ":")).encode()
                            ).hexdigest()
        self.assertNotEqual(h0, h1)

    def test_hash_labels_are_distinct(self):
        payload = production_contract_identity_payload(
            self.contract, check_adapter_contract_hash())
        self.assertNotEqual(payload["rule_artifact_file_sha256"],
                            payload["rule_artifact_canonical_sha256"])
        self.assertNotEqual(payload["structured_inputs_file_sha256"],
                            payload["structured_inputs_population_binding_sha256"])
        self.assertNotEqual(payload["rule_artifact_file_sha256"],
                            payload["structured_inputs_file_sha256"])

    def test_wire_rule_cannot_mint_production_hash(self):
        wire = WireComparisonRule(rule_id="wire", contract={"rule_id": "wire"},
                                  compare=lambda a, b: True)
        with self.assertRaises(CheckContractError):
            production_check_contract_hash(wire)
        with self.assertRaises(CheckContractError):
            check_contract_hash(wire)

    def test_wire_rule_cannot_run_production_path(self):
        store = ProvenanceStore([ProvenanceRecord(
            "o", "https://example.test/x", "scope", "cited",
            raw_sha256="c" * 64)])
        wire = WireComparisonRule(rule_id="wire", contract={"rule_id": "wire"},
                                  compare=lambda a, b: True)
        with self.assertRaises(CheckContractError):
            run_production_scope_check(
                store, "https://example.test/x", "d" * 64, wire)

    def test_production_contract_rejects_wire_type(self):
        wire = WireComparisonRule(rule_id="wire", contract={"rule_id": "wire"},
                                  compare=lambda a, b: True)
        with self.assertRaises(CheckContractError):
            validate_production_comparison_contract(wire)


class TestC3aBindingSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        write_expectations()
        refresh_pinned_artifacts()
        cls.contract = build_production_contract()
        cls.structured = json.loads(STRUCTURED_PATH.read_text())
        cls.store = _oracle_store()

    def _first_row(self) -> dict:
        return self.structured["rows"][0]

    def test_pinned_runtime_rejects_unpinned_binding_file(self):
        row = self._first_row()
        evidence = run_production_scope_check(
            self.store, row["source_reference"],
            row["decision_scope_sha256"], self.contract)
        self.assertIsInstance(evidence.scope_matches, bool)
        mutated = copy.deepcopy(self.structured)
        mutated["rows"][0]["operands"]["version"] = "9.9.9"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mutated.json"
            path.write_text(json.dumps(mutated, sort_keys=True, indent=1) + "\n")
            stale = ProductionComparisonContract(
                **{**self.contract.__dict__,
                   "structured_inputs_path": str(path),
                   "structured_inputs_file_sha256":
                       hashlib.sha256(path.read_bytes()).hexdigest()})
            with self.assertRaises(ProductionCompareError):
                build_production_contract(
                    REPO / stale.rule_artifact_path,
                    REPO / stale.conformance_vectors_path,
                    Path(stale.structured_inputs_path))

    def test_raw_hash_swap_rejected(self):
        row = self._first_row()
        with self.assertRaises(ProductionCompareError):
            execute_pinned_binding(
                self.contract, row["source_reference"],
                row["decision_scope_sha256"],
                provenance_raw_sha256="f" * 64)

    def test_missing_binding_rejected(self):
        row = self._first_row()
        with self.assertRaises(ProductionCompareError):
            resolve_pinned_row(self.contract, row["source_reference"],
                               "0" * 64)

    def test_source_reference_swap_rejected(self):
        row = self._first_row()
        with self.assertRaises(ProductionCompareError):
            resolve_pinned_row(self.contract, "https://evil.example/x",
                               row["decision_scope_sha256"])

    def test_duplicate_binding_rejected(self):
        row = self._first_row()
        duped = copy.deepcopy(self.structured)
        duped["rows"].append(copy.deepcopy(row))
        from harness.efc_compare_production import population_binding_sha256_from_data
        duped["population_binding_sha256"] = population_binding_sha256_from_data(duped)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dup.json"
            path.write_text(json.dumps(duped, sort_keys=True, indent=1) + "\n")
            bad = ProductionComparisonContract(
                **{**self.contract.__dict__,
                   "structured_inputs_path": str(path),
                   "structured_inputs_file_sha256":
                       hashlib.sha256(path.read_bytes()).hexdigest(),
                   "structured_inputs_population_binding_sha256":
                       duped["population_binding_sha256"]})
            with self.assertRaises(ProductionCompareError):
                resolve_pinned_row(bad, row["source_reference"],
                                   row["decision_scope_sha256"])

    def test_operand_mutation_changes_binding_hash(self):
        h0 = self.contract.structured_inputs_population_binding_sha256
        mutated = copy.deepcopy(self.structured)
        mutated["rows"][0]["operands"]["version"] = "9.9.9"
        from harness.efc_compare_production import population_binding_sha256_from_data
        h1 = population_binding_sha256_from_data(mutated)
        self.assertNotEqual(h0, h1)

    def test_binding_mutation_changes_contract_hash_if_repinned(self):
        h0 = production_check_contract_hash(self.contract)
        replacement = ProductionComparisonContract(
            **{**self.contract.__dict__,
               "structured_inputs_population_binding_sha256": "0" * 64})
        base = production_contract_identity_payload(
            self.contract, check_adapter_contract_hash())
        mutated = dict(base)
        mutated["structured_inputs_population_binding_sha256"] = "0" * 64
        h1 = hashlib.sha256(json.dumps(mutated, sort_keys=True,
                                        separators=(",", ":")).encode()
                            ).hexdigest()
        self.assertNotEqual(h0, h1)

    def test_binding_mutation_rejected_under_old_contract(self):
        row = self._first_row()
        with tempfile.TemporaryDirectory() as tmp:
            mutated = copy.deepcopy(self.structured)
            mutated["rows"][0]["operands"]["version"] = "9.9.9"
            path = Path(tmp) / "mutated.json"
            path.write_text(json.dumps(mutated, sort_keys=True, indent=1) + "\n")
            stale = ProductionComparisonContract(
                **{**self.contract.__dict__,
                   "structured_inputs_path": str(path),
                   "structured_inputs_file_sha256":
                       hashlib.sha256(path.read_bytes()).hexdigest()})
            with self.assertRaises(ProductionCompareError):
                build_production_contract(
                    REPO / stale.rule_artifact_path,
                    REPO / stale.conformance_vectors_path,
                    Path(stale.structured_inputs_path))

    def test_production_path_uses_oracle_store(self):
        row = self._first_row()
        evidence = run_production_scope_check(
            self.store, row["source_reference"],
            row["decision_scope_sha256"], self.contract)
        self.assertIsInstance(evidence.scope_matches, bool)


class TestDispositiveConformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        write_expectations()
        refresh_pinned_artifacts()
        cls.structured = build_structured_inputs()
        cls.expectations = json.loads(EXPECTATIONS_PATH.read_text())
        cls.contract = build_production_contract()

    def test_fifteen_structured_rows(self):
        self.assertEqual(len(self.structured["rows"]), 15)
        self.assertEqual(len(DISPOSITIVE_TASKS), 15)
        for row in self.structured["rows"]:
            self.assertIn("decision_scope_sha256", row)

    def test_production_agrees_with_oracle_expectations_test_layer_only(self):
        by_ref = {r["source_reference"]: r["expected_scope_matches"]
                  for r in self.expectations["rows"]}
        for row in self.structured["rows"]:
            got = interpret_structured_input(row)
            self.assertEqual(got, by_ref[row["source_reference"]],
                             row["source_reference"])

    def test_production_module_never_reads_expectations(self):
        from harness import efc_compare_production as mod
        source = inspect.getsource(mod.execute_pinned_binding)
        self.assertNotIn("expected_scope_matches", source)
        self.assertTrue(mod.wire_lookup_unreachable())
        self.assertTrue(mod.derivation_module_unreachable())

    def test_wire_lookup_unreachable(self):
        self.assertTrue(wire_lookup_unreachable())

    def test_derivation_module_unreachable(self):
        self.assertTrue(derivation_module_unreachable())


class TestIntegrationArtifact(unittest.TestCase):
    def test_integration_report_fifteen_of_fifteen(self):
        write_expectations()
        refresh_pinned_artifacts()
        report = build_integration_report(check_adapter_contract_hash())
        self.assertEqual(report["dispositive_row_count"], 15)
        self.assertEqual(report["oracle_agreement_count"], 15)
        self.assertTrue(report["wire_lookup_unreachable_from_production"])
        self.assertTrue(report["derivation_module_unreachable_from_production"])
        self.assertEqual(report["status"], "candidate_not_pinned")
        self.assertIn("rule_artifact_file_sha256", report)
        self.assertIn("structured_inputs_population_binding_sha256", report)


if __name__ == "__main__":
    unittest.main()
