"""Offline validation and CLI tests for R2 decoding-surface artifact."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from harness.efc_roster_r2 import (API_MODEL, LOCAL_MODEL, OUT_PATH,
                                   PINNED_ARTIFACT_SHA256, WIRE_PROMPT,
                                   load_and_validate_r2_artifact,
                                   validate_r2_artifact)

REPO = Path(__file__).resolve().parent.parent
MODULE = "harness.efc_roster_r2"


def _artifact_sha256() -> str:
    return hashlib.sha256(OUT_PATH.read_bytes()).hexdigest()


class TestDecodingSurfaceR2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._baseline_artifact_sha = _artifact_sha256()

    def tearDown(self):
        self.assertEqual(_artifact_sha256(), self._baseline_artifact_sha)

    def test_artifact_passes_validator(self):
        artifact = load_and_validate_r2_artifact()
        self.assertEqual(artifact["disclosure"]["inference_calls"], 4)
        self.assertEqual(artifact["branches"]["local"]["verdict"], "pass")
        self.assertEqual(artifact["branches"]["api"]["verdict"], "pass")
        self.assertEqual(artifact["frozen_wire_prompt"], WIRE_PROMPT)
        self.assertEqual(_artifact_sha256(), PINNED_ARTIFACT_SHA256)

    def test_validator_rejects_wrong_model(self):
        artifact = json.loads(OUT_PATH.read_text())
        bad = copy.deepcopy(artifact)
        bad["calls"][0]["request_body_sanitized"]["model"] = "evil/model"
        with self.assertRaises(ValueError):
            validate_r2_artifact(bad)

    def test_validator_rejects_wrong_temperature(self):
        artifact = json.loads(OUT_PATH.read_text())
        bad = copy.deepcopy(artifact)
        bad["calls"][1]["requested_temperature"] = 0.9
        with self.assertRaises(ValueError):
            validate_r2_artifact(bad)

    def test_validator_rejects_wrong_prompt_hash(self):
        artifact = json.loads(OUT_PATH.read_text())
        bad = copy.deepcopy(artifact)
        bad["frozen_wire_prompt_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_r2_artifact(bad)

    def test_validator_rejects_wrong_contract_hash(self):
        artifact = json.loads(OUT_PATH.read_text())
        bad = copy.deepcopy(artifact)
        bad["branches"]["local"]["decoding_contract_canonical_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_r2_artifact(bad)

    def test_validator_rejects_extra_call(self):
        artifact = json.loads(OUT_PATH.read_text())
        bad = copy.deepcopy(artifact)
        bad["calls"].append(copy.deepcopy(bad["calls"][0]))
        bad["disclosure"]["inference_calls"] = 5
        with self.assertRaises(ValueError):
            validate_r2_artifact(bad)

    def test_validator_rejects_missing_response_id(self):
        artifact = json.loads(OUT_PATH.read_text())
        bad = copy.deepcopy(artifact)
        bad["calls"][2]["response_id"] = None
        with self.assertRaises(ValueError):
            validate_r2_artifact(bad)

    def test_validator_rejects_api_tools(self):
        artifact = json.loads(OUT_PATH.read_text())
        bad = copy.deepcopy(artifact)
        bad["calls"][2]["request_body_sanitized"]["tools"] = []
        with self.assertRaises(ValueError):
            validate_r2_artifact(bad)

    def test_contract_models_match_roster(self):
        artifact = load_and_validate_r2_artifact()
        self.assertEqual(artifact["branches"]["local"]["contract"]["model_id"],
                         LOCAL_MODEL)
        self.assertEqual(artifact["branches"]["api"]["contract"]["model_id"],
                         API_MODEL)


class TestDecodingSurfaceR2Cli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._baseline_artifact_sha = _artifact_sha256()

    def tearDown(self):
        self.assertEqual(_artifact_sha256(), self._baseline_artifact_sha)

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", MODULE, *args],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_verify_cli_succeeds_zero_network(self):
        proc = self._run("--verify")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["artifact_sha256"], PINNED_ARTIFACT_SHA256)
        self.assertEqual(payload["network_calls"], 0)

    def test_no_args_refuses_without_network(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("specify --verify or --execute", proc.stderr)

    def test_execute_refuses_when_artifact_exists(self):
        proc = self._run("--execute")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("refusing to overwrite", proc.stderr + proc.stdout)

    def test_verify_fails_on_mutated_copy(self):
        artifact = json.loads(OUT_PATH.read_text())
        bad = copy.deepcopy(artifact)
        bad["calls"][0]["request_body_sanitized"]["max_tokens"] = 1024
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps(bad, sort_keys=True, indent=1) + "\n")
            # validator reads default path; patch via env not supported — call
            # validate directly for mutation, and verify CLI on default artifact
            with self.assertRaises(ValueError):
                validate_r2_artifact(bad)
        proc = self._run("--verify")
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
