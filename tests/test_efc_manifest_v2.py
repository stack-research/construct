"""Conformance vectors for EFC v2 manifest."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.efc_admission_gate_v2 import PART_I_SPEC_SHA256, compute_ub
from harness.efc_manifest_v2 import (
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
        pins = recomputed
        self.assertIn("scope_comparison_rule_artifact_sha256", pins)
        self.assertIn("scope_comparison_interpreter_sha256", pins)
        self.assertIn("scope_comparison_conformance_vectors_sha256", pins)

    def test_derived_ub_in_manifest_params(self):
        manifest = assemble_manifest(REPO_ROOT)
        params = manifest["admission_gate_params"]
        self.assertAlmostEqual(float(params["UB"]), compute_ub(128))
        self.assertEqual(params["pinned_UB"], params["UB"])

    def test_manifest_verify_without_corpus(self):
        manifest = assemble_manifest(REPO_ROOT)
        result = manifest_verify(REPO_ROOT, manifest)
        self.assertTrue(result.ok, result.failures)

    def test_pin_eligibility_refuses_missing_suite_hash(self):
        manifest = assemble_manifest(REPO_ROOT)
        result = manifest_verify(REPO_ROOT, manifest, require_suite_hash=True)
        self.assertFalse(result.ok)
        self.assertIn("fixture_suite_hash_missing", result.failures)

    def test_load_pinned_manifest_requires_suite_hash(self):
        manifest = assemble_manifest(REPO_ROOT)
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
