"""Conformance vectors: commitment wire + enum oracle (SPEC v1 §2.5.1/§2.5.3)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from harness.efc_commitment_oracle_v1 import score_commitment_oracle_v1
from harness.efc_commitment_wire_v1 import (SCHEMA_RELPATH,
                                            validate_action_set,
                                            validate_commitment_wire)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / SCHEMA_RELPATH

ACTION_SET = ["approve", "defer", "reject"]


class TestActionSetDeclaration(unittest.TestCase):
    def test_valid_three_member_set(self):
        result = validate_action_set(ACTION_SET)
        self.assertTrue(result.ok)
        self.assertIsNone(result.failure)

    def test_two_members_too_small(self):
        result = validate_action_set(["a", "b"])
        self.assertFalse(result.ok)
        self.assertEqual(result.failure, "action_set_too_small")

    def test_seven_members_too_large(self):
        result = validate_action_set(list("abcdefg"))
        self.assertFalse(result.ok)
        self.assertEqual(result.failure, "action_set_too_large")

    def test_duplicate_labels_rejected(self):
        result = validate_action_set(["approve", "defer", "approve"])
        self.assertFalse(result.ok)
        self.assertEqual(result.failure, "duplicate_labels")

    def test_malformed_action_set_non_list(self):
        result = validate_action_set("approve")
        self.assertFalse(result.ok)
        self.assertEqual(result.failure, "malformed_action_set")


class TestCommitmentWireValidation(unittest.TestCase):
    def test_valid_single_commitment(self):
        wire = {"commitment_enum": "defer"}
        result = validate_commitment_wire(wire, ACTION_SET)
        self.assertEqual(result.outcome, "commitment_valid")
        self.assertEqual(result.commitment_enum, "defer")
        self.assertIsNone(result.invalid_reason)

    def test_valid_with_optional_prose(self):
        wire = {"commitment_enum": "approve", "optional_prose": "scope covers"}
        result = validate_commitment_wire(wire, ACTION_SET)
        self.assertEqual(result.outcome, "commitment_valid")
        self.assertEqual(result.commitment_enum, "approve")

    def test_absent_commitment(self):
        result = validate_commitment_wire({}, ACTION_SET)
        self.assertEqual(result.outcome, "commitment_invalid")
        self.assertEqual(result.invalid_reason, "absent_commitment")

    def test_malformed_field_wrong_type(self):
        result = validate_commitment_wire({"commitment_enum": 42}, ACTION_SET)
        self.assertEqual(result.outcome, "commitment_invalid")
        self.assertEqual(result.invalid_reason, "malformed_field")

    def test_malformed_optional_prose_type(self):
        wire = {"commitment_enum": "defer", "optional_prose": 1}
        result = validate_commitment_wire(wire, ACTION_SET)
        self.assertEqual(result.outcome, "commitment_invalid")
        self.assertEqual(result.invalid_reason, "malformed_field")

    def test_malformed_field_multi_element_array(self):
        wire = {"commitment_enum": ["approve", "defer"]}
        result = validate_commitment_wire(wire, ACTION_SET)
        self.assertEqual(result.outcome, "commitment_invalid")
        self.assertEqual(result.invalid_reason, "malformed_field")

    def test_malformed_field_singleton_array(self):
        wire = {"commitment_enum": ["defer"]}
        result = validate_commitment_wire(wire, ACTION_SET)
        self.assertEqual(result.outcome, "commitment_invalid")
        self.assertEqual(result.invalid_reason, "malformed_field")

    def test_malformed_field_empty_array(self):
        wire = {"commitment_enum": []}
        result = validate_commitment_wire(wire, ACTION_SET)
        self.assertEqual(result.outcome, "commitment_invalid")
        self.assertEqual(result.invalid_reason, "malformed_field")

    def test_malformed_field_bool(self):
        result = validate_commitment_wire({"commitment_enum": True}, ACTION_SET)
        self.assertEqual(result.outcome, "commitment_invalid")
        self.assertEqual(result.invalid_reason, "malformed_field")

    def test_malformed_field_null(self):
        result = validate_commitment_wire({"commitment_enum": None}, ACTION_SET)
        self.assertEqual(result.outcome, "commitment_invalid")
        self.assertEqual(result.invalid_reason, "malformed_field")

    def test_malformed_field_nested_object(self):
        wire = {"commitment_enum": {"label": "defer"}}
        result = validate_commitment_wire(wire, ACTION_SET)
        self.assertEqual(result.outcome, "commitment_invalid")
        self.assertEqual(result.invalid_reason, "malformed_field")

    def test_unknown_enum_not_in_action_set(self):
        wire = {"commitment_enum": "withdraw"}
        result = validate_commitment_wire(wire, ACTION_SET)
        self.assertEqual(result.outcome, "commitment_invalid")
        self.assertEqual(result.invalid_reason, "unknown_enum")

    def test_schema_closure_extra_field_rejected(self):
        wire = {"commitment_enum": "defer", "rationale": "hidden"}
        result = validate_commitment_wire(wire, ACTION_SET)
        self.assertEqual(result.outcome, "commitment_invalid")
        self.assertEqual(result.invalid_reason, "malformed_field")

    def test_exact_match_case_sensitive(self):
        wire = {"commitment_enum": "Defer"}
        result = validate_commitment_wire(wire, ACTION_SET)
        self.assertEqual(result.outcome, "commitment_invalid")
        self.assertEqual(result.invalid_reason, "unknown_enum")


class TestCommitmentOracle(unittest.TestCase):
    def test_pass_on_exact_enum_match(self):
        validated = validate_commitment_wire({"commitment_enum": "defer"},
                                             ACTION_SET)
        score = score_commitment_oracle_v1(validated, "defer")
        self.assertEqual(score.outcome, "pass")
        self.assertEqual(score.validation_outcome, "commitment_valid")

    def test_fail_on_enum_mismatch(self):
        validated = validate_commitment_wire({"commitment_enum": "defer"},
                                             ACTION_SET)
        score = score_commitment_oracle_v1(validated, "approve")
        self.assertEqual(score.outcome, "fail")
        self.assertEqual(score.validation_outcome, "commitment_valid")
        self.assertIsNone(score.invalid_reason)

    def test_invalid_counts_as_fail_with_reason_preserved(self):
        validated = validate_commitment_wire({}, ACTION_SET)
        score = score_commitment_oracle_v1(validated, "defer")
        self.assertEqual(score.outcome, "fail")
        self.assertEqual(score.validation_outcome, "commitment_invalid")
        self.assertEqual(score.invalid_reason, "absent_commitment")

    def test_oracle_case_sensitive_no_normalization(self):
        validated = validate_commitment_wire({"commitment_enum": "defer"},
                                             ACTION_SET)
        score = score_commitment_oracle_v1(validated, "Defer")
        self.assertEqual(score.outcome, "fail")
        self.assertEqual(score.validation_outcome, "commitment_valid")


class TestSchemaArtifact(unittest.TestCase):
    def test_schema_loads_and_closes_wire(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        wire = schema["$defs"]["commitment_wire"]
        self.assertFalse(wire["additionalProperties"])
        self.assertEqual(set(wire["required"]), {"commitment_enum"})
        self.assertEqual(set(wire["properties"]), {"commitment_enum",
                                                  "optional_prose"})

    def test_action_set_bounds_in_schema(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        action_set = schema["$defs"]["action_set"]
        self.assertEqual(action_set["minItems"], 3)
        self.assertEqual(action_set["maxItems"], 6)

    def test_action_set_unique_items_in_schema(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        action_set = schema["$defs"]["action_set"]
        self.assertTrue(action_set["uniqueItems"])


if __name__ == "__main__":
    unittest.main()
