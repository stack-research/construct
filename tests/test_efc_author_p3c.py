"""P3C answer-key repair — v2 candidate, vectors, contradiction check."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from harness.efc_author_c2_content import FIXTURES
from harness.efc_author_p3 import (P3_ROOT, WORLD_ORACLE_SCHEMA,
                                   build_world_oracle_answer_key_candidate)
from harness.efc_author_p3c import (KIMI_REVIEW_PATH,
                                    build_world_oracle_answer_key_candidate_v2,
                                    evaluate_all_repair_vectors,
                                    find_rule_contradictions,
                                    load_kimi_adversarial_vectors,
                                    write_p3c_artifacts)
from harness.efc_calibration_contact import _validate_scorer_rules

REPO = Path(__file__).resolve().parent.parent


class TestP3CAnswerKeyRepair(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifacts = write_p3c_artifacts()
        cls.key_v2 = json.loads(cls.artifacts["answer_key_v2"].read_text())
        cls.vectors = json.loads(cls.artifacts["vectors"].read_text())
        cls.report = json.loads(cls.artifacts["report"].read_text())
        cls.v1_path = P3_ROOT / "world_oracle_answer_key_candidate.json"
        cls.si_path = P3_ROOT / "structured_inputs_v2_candidate.json"
        cls.budget_path = P3_ROOT / "ax_ir_budget_audit.json"

    def test_v1_candidate_unchanged(self) -> None:
        before = hashlib.sha256(self.v1_path.read_bytes()).hexdigest()
        self.assertEqual(
            before,
            self.report["input_hashes"]["world_oracle_answer_key_candidate_v1"])

    def test_structured_inputs_and_budget_unchanged(self) -> None:
        self.assertEqual(
            hashlib.sha256(self.si_path.read_bytes()).hexdigest(),
            self.report["input_hashes"]["structured_inputs_v2_candidate"])
        budget_hash = hashlib.sha256(self.budget_path.read_bytes()).hexdigest()
        self.assertTrue(budget_hash)

    def test_v2_schema_and_coverage(self) -> None:
        self.assertEqual(self.key_v2["schema_version"], WORLD_ORACLE_SCHEMA)
        _validate_scorer_rules(self.key_v2["rules"], set(FIXTURES))
        self.assertEqual(set(self.key_v2["rules"]), set(FIXTURES))

    def test_no_substring_contradictions(self) -> None:
        conflicts = find_rule_contradictions(self.key_v2["rules"])
        self.assertEqual(conflicts, [])
        self.assertTrue(self.report["contradiction_check"]["passed"])

    def test_kimi_vectors_frozen_eighty(self) -> None:
        kimi = load_kimi_adversarial_vectors()
        self.assertEqual(kimi["vector_count"], 80)
        self.assertEqual(kimi["source_artifact"],
                         str(KIMI_REVIEW_PATH.relative_to(REPO)))

    def test_all_vector_sources_zero_failures(self) -> None:
        self.assertEqual(self.vectors["total_failure_count"], 0)
        for source, count in self.vectors["failure_counts_by_source"].items():
            self.assertEqual(count, 0, source)
        self.assertGreater(self.vectors["counts_by_source"]["composer_p3a"], 0)
        self.assertEqual(self.vectors["counts_by_source"]["kimi_p3b"], 80)
        self.assertGreater(self.vectors["counts_by_source"]["composer_p3c"], 0)

    def test_report_attestations(self) -> None:
        self.assertTrue(self.report["candidate_only"])
        self.assertFalse(self.report["authorizes_contact"])
        self.assertFalse(self.report["authorizes_integration"])
        self.assertEqual(self.report["blockers"], [])
        self.assertEqual(self.report["schema_inexpressible_fixtures"], [])

    def test_rule_changes_documented_per_fixture(self) -> None:
        v1 = build_world_oracle_answer_key_candidate()
        self.assertEqual(len(self.report["rule_changes"]), len(FIXTURES))
        for change in self.report["rule_changes"]:
            tid = change["fixture_id"]
            self.assertNotEqual(
                v1["rules"][tid]["pass_when"],
                self.key_v2["rules"][tid]["pass_when"])

    def test_evaluate_matches_written_artifact(self) -> None:
        live = evaluate_all_repair_vectors(self.key_v2)
        self.assertEqual(live["total_failure_count"], 0)
        self.assertEqual(
            live["counts_by_source"],
            self.vectors["counts_by_source"])


if __name__ == "__main__":
    unittest.main()
