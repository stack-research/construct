"""Conformance vectors for EFC v2 manifest."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.efc_admission_gate_v2 import PART_I_SPEC_SHA256, compute_ub
from harness.efc_manifest_v2 import (
    CAP2048_INPUT_TOKEN_CEILING,
    CAP2048_MAX_OUTPUT_TOKENS_PER_REQUEST,
    CAP2048_OPENING_CALLS,
    CAP2048_OPENING_INPUT_TOKENS,
    CAP2048_OPENING_OUTPUT_TOKENS,
    CAP2048_OUTPUT_TOKEN_CEILING,
    CAP2048_TOTAL_CALL_CEILING,
    EARLY_OUTPUT_CENSORING_OUTCOME,
    LIVE_001_ABORT_RECORD_RELPATH,
    LIVE_001_LEDGER_RELPATH,
    LIVE_002_LEDGER_RELPATH,
    LIVE_003_LEDGER_RELPATH,
    MANIFEST_RELPATH,
    PART_I_SPEC_RELPATH,
    assemble_manifest,
    compute_contract_hashes,
    manifest_verify,
    sha256_path,
)
from harness.efc_pilot_runner_v2 import PilotRunnerRefusal, load_pinned_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestManifestV2(unittest.TestCase):
    def test_part_i_spec_hash_on_disk(self):
        self.assertEqual(
            sha256_path(REPO_ROOT / PART_I_SPEC_RELPATH),
            PART_I_SPEC_SHA256,
        )

    def test_assemble_manifest_contract_hashes(self):
        manifest = assemble_manifest(REPO_ROOT)
        recomputed = compute_contract_hashes(REPO_ROOT)
        self.assertEqual(manifest["contract_hashes"], recomputed)
        self.assertEqual(manifest["part_i_spec_sha256"], PART_I_SPEC_SHA256)
        self.assertEqual(manifest["engine"], manifest["fork_identity"]["engine"])
        self.assertEqual(manifest["effort"], manifest["fork_identity"]["effort"])
        pins = recomputed
        self.assertIn("scope_comparison_rule_artifact_sha256", pins)
        self.assertIn("scope_comparison_interpreter_sha256", pins)
        self.assertIn("scope_comparison_conformance_vectors_sha256", pins)

    def test_derived_ub_in_manifest_params(self):
        manifest = assemble_manifest(REPO_ROOT)
        params = manifest["admission_gate_params"]
        self.assertAlmostEqual(float(params["UB"]), compute_ub(128))
        self.assertEqual(params["pinned_UB"], params["UB"])

    def test_manifest_verify_with_authored_battery(self):
        manifest = assemble_manifest(REPO_ROOT)
        result = manifest_verify(REPO_ROOT, manifest)
        self.assertTrue(result.ok, result.failures)

    def test_pin_eligibility_with_authored_battery(self):
        manifest = assemble_manifest(REPO_ROOT)
        self.assertIn("fixture_suite_hash", manifest)
        result = manifest_verify(REPO_ROOT, manifest, require_suite_hash=True)
        self.assertTrue(result.ok, result.failures)

    def test_pin_eligibility_refuses_missing_suite_hash(self):
        manifest = assemble_manifest(REPO_ROOT)
        manifest.pop("fixture_suite_hash", None)
        manifest["calibration_fixtures"] = []
        result = manifest_verify(REPO_ROOT, manifest, require_suite_hash=True)
        self.assertFalse(result.ok)
        self.assertIn("fixture_suite_hash_missing", result.failures)

    def test_load_pinned_manifest_requires_suite_hash(self):
        manifest = assemble_manifest(REPO_ROOT)
        manifest.pop("fixture_suite_hash", None)
        manifest["calibration_fixtures"] = []
        temp_manifest = tempfile.NamedTemporaryFile(
            "w",
            dir=REPO_ROOT,
            suffix=".json",
            delete=False,
        )
        try:
            json.dump(manifest, temp_manifest)
            temp_manifest.flush()
            manifest_path = Path(temp_manifest.name)
            rel_manifest = manifest_path.relative_to(REPO_ROOT).as_posix()
            with self.assertRaises(PilotRunnerRefusal) as ctx:
                load_pinned_manifest(
                    REPO_ROOT,
                    manifest_path=rel_manifest,
                    require_pin=False,
                )
            self.assertIn("fixture_suite_hash_missing", str(ctx.exception))
        finally:
            temp_manifest.close()
            manifest_path.unlink(missing_ok=True)

    def test_manifest_relpath_target(self):
        self.assertEqual(
            MANIFEST_RELPATH,
            "corpus/efc_calibration_v2/calibration_manifest.json",
        )

    def test_cap2048_budget_ledger_pins(self):
        manifest = assemble_manifest(REPO_ROOT)
        budget = manifest["budget_ledger"]
        self.assertEqual(
            budget["max_output_tokens_per_request"],
            CAP2048_MAX_OUTPUT_TOKENS_PER_REQUEST,
        )
        self.assertEqual(budget["calls_already_spent"], CAP2048_OPENING_CALLS)
        self.assertEqual(
            budget["opening_input_tokens_spent"], CAP2048_OPENING_INPUT_TOKENS
        )
        self.assertEqual(
            budget["opening_output_tokens_spent"], CAP2048_OPENING_OUTPUT_TOKENS
        )
        self.assertEqual(budget["total_call_ceiling"], CAP2048_TOTAL_CALL_CEILING)
        self.assertEqual(budget["output_token_ceiling"], CAP2048_OUTPUT_TOKEN_CEILING)
        self.assertEqual(budget["input_token_ceiling"], CAP2048_INPUT_TOKEN_CEILING)
        self.assertEqual(budget["hard_cost_ceiling_usd"], 0.0)
        self.assertEqual(budget["pricing"]["input_usd_per_million"], 0.0)
        self.assertEqual(budget["pricing"]["output_usd_per_million"], 0.0)

    def test_early_censor_refusal_pinned(self):
        manifest = assemble_manifest(REPO_ROOT)
        early = manifest["early_censor_refusal"]
        self.assertEqual(early["first_k"], 8)
        self.assertEqual(early["predicates"]["finish_reason"], "length")
        self.assertTrue(early["predicates"]["normalized_content_empty"])
        self.assertTrue(early["predicates"]["completion_tokens_at_cap_minus_tolerance"])
        self.assertEqual(early["typed_outcome"], EARLY_OUTPUT_CENSORING_OUTCOME)

    def test_completion_budget_contract_pinned(self):
        manifest = assemble_manifest(REPO_ROOT)
        contract = manifest["completion_budget_contract"]
        self.assertEqual(contract["transport"], "chat-completions")
        self.assertIn("reasoning", contract["max_tokens_semantics"])
        self.assertFalse(contract["reasoning_content_in_wire_parser"])
        self.assertTrue(contract["reasoning_content_in_completion_usage"])
        self.assertEqual(contract["provider_off_by_one_tolerance"], 1)

    def test_abort_evidence_binding_hashes(self):
        manifest = assemble_manifest(REPO_ROOT)
        binding = manifest["abort_evidence_binding"]
        self.assertEqual(
            binding["live_001_ledger_sha256"],
            sha256_path(REPO_ROOT / LIVE_001_LEDGER_RELPATH),
        )
        self.assertEqual(
            binding["live_001_abort_record_sha256"],
            sha256_path(REPO_ROOT / LIVE_001_ABORT_RECORD_RELPATH),
        )
        self.assertEqual(
            binding["live_002_ledger_sha256"],
            sha256_path(REPO_ROOT / LIVE_002_LEDGER_RELPATH),
        )
        self.assertEqual(
            binding["live_002_ledger_relpath"],
            LIVE_002_LEDGER_RELPATH,
        )
        self.assertEqual(
            binding["live_003_ledger_sha256"],
            sha256_path(REPO_ROOT / LIVE_003_LEDGER_RELPATH),
        )
        self.assertEqual(
            binding["live_003_ledger_relpath"],
            LIVE_003_LEDGER_RELPATH,
        )
        preserves = binding["rerun_preserves"]
        self.assertEqual(
            preserves["fixture_suite_hash"], manifest["fixture_suite_hash"]
        )
        self.assertEqual(preserves["engine"], manifest["engine"])
        self.assertEqual(preserves["effort"], manifest["effort"])
        self.assertIn("lane_order", preserves)

    def test_typed_outcomes_includes_early_output_censoring(self):
        manifest = assemble_manifest(REPO_ROOT)
        self.assertIn(EARLY_OUTPUT_CENSORING_OUTCOME, manifest["typed_outcomes"])
        self.assertIn(
            "confounded(commitment_invalid_rate)", manifest["typed_outcomes"]
        )

    def test_manifest_verify_cap2048_amendment(self):
        manifest = assemble_manifest(REPO_ROOT)
        result = manifest_verify(REPO_ROOT, manifest, require_suite_hash=True)
        self.assertTrue(result.ok, result.failures)
