"""P3A candidate authoring — schema, coverage, vectors, budget audit."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from harness.efc_author_c2_content import FIXTURES
from harness.efc_author_p3 import (ALL_TASKS, FORBIDDEN_ROW_KEYS, IR_TASKS,
                                   P3_ROOT, V1_PATH, WORLD_ORACLE_SCHEMA,
                                   audit_ax_ir_budget,
                                   build_structured_inputs_v2_candidate,
                                   build_world_oracle_answer_key_candidate,
                                   derive_ir_structured_input,
                                   evaluate_cold_review_vectors,
                                   write_p3_artifacts)
from harness.efc_calibration_contact import _validate_scorer_rules
from harness.efc_compare_inputs import STRUCTURED_INPUTS_SCHEMA_VERSION
from harness.efc_compare_production import (interpret_structured_input,
                                            validate_structured_input)

REPO = Path(__file__).resolve().parent.parent


class TestP3ACandidateAuthoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifacts = write_p3_artifacts()
        cls.si = json.loads(cls.artifacts["structured_inputs"].read_text())
        cls.key = json.loads(cls.artifacts["answer_key"].read_text())
        cls.vectors = json.loads(cls.artifacts["cold_review"].read_text())
        cls.report = json.loads(cls.artifacts["report"].read_text())
        cls.v1 = json.loads(V1_PATH.read_text())

    def test_structured_inputs_schema_and_coverage(self) -> None:
        self.assertEqual(self.si["schema_version"],
                         STRUCTURED_INPUTS_SCHEMA_VERSION)
        self.assertEqual(self.si["row_count"], 20)
        self.assertEqual(len(self.si["rows"]), 20)
        selectors = {(r["source_reference"], r["decision_scope_sha256"])
                       for r in self.si["rows"]}
        self.assertEqual(len(selectors), 20)

    def test_old_fifteen_rows_byte_identical(self) -> None:
        for i in range(15):
            self.assertEqual(self.v1["rows"][i], self.si["rows"][i])

    def test_ir_rows_match_oracle_expectations(self) -> None:
        for tid in IR_TASKS:
            row = derive_ir_structured_input(tid)
            oracle = json.loads((REPO / "corpus/efc_calibration/oracle"
                                 / f"{tid}.json").read_text())
            self.assertEqual(
                interpret_structured_input(row),
                oracle["expected_scope_matches"],
                tid)
            validate_structured_input(row)
            for key in FORBIDDEN_ROW_KEYS:
                self.assertNotIn(key, row)
                self.assertNotIn(key, row.get("operands", {}))

    def test_world_oracle_key_schema_and_coverage(self) -> None:
        self.assertEqual(self.key["schema_version"], WORLD_ORACLE_SCHEMA)
        _validate_scorer_rules(self.key["rules"], set(ALL_TASKS))
        self.assertEqual(set(self.key["rules"]), set(FIXTURES))

    def test_cold_review_vectors_machine_evaluated(self) -> None:
        self.assertEqual(self.vectors["failure_count"], 0)
        self.assertEqual(self.vectors["failures"], [])
        for tid in ALL_TASKS:
            block = self.vectors["evaluation"][tid]
            self.assertGreaterEqual(len(block["correct"]), 3)
            self.assertGreaterEqual(len(block["incorrect"]), 3)

    def test_budget_audit_within_pinned_allowance(self) -> None:
        budget = json.loads(self.artifacts["budget_audit"].read_text())
        self.assertTrue(budget["within_budget"])
        self.assertEqual(len(budget["rows"]), 10)
        for row in budget["rows"]:
            self.assertLessEqual(row["delta"], 0)

    def test_report_attestations_and_no_contact(self) -> None:
        self.assertTrue(self.report["candidate_only"])
        self.assertFalse(self.report["authorizes_contact"])
        self.assertTrue(self.report["attestations"]["no_calibration_answers_used"])
        self.assertTrue(
            self.report["attestations"]["repair_not_informed_by_p1_counts"])
        self.assertEqual(self.report["blockers"], [])

    def test_report_hashes_match_artifacts(self) -> None:
        for name, path in self.artifacts.items():
            if name == "report":
                continue
            expect = self.report["artifact_hashes"][name]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                             expect, name)


if __name__ == "__main__":
    unittest.main()
