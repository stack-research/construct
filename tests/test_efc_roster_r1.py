"""Offline validation for R1 roster enumeration artifact."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "corpus/efc_calibration/roster/roster_enumeration_r1.json"


class TestRosterEnumerationR1(unittest.TestCase):
    def test_artifact_schema_and_local_exact_id(self):
        data = json.loads(ARTIFACT.read_text())
        self.assertEqual(data["schema_version"], "efc-roster-enumeration-r1-v1")
        disclosure = data["call_disclosure"]
        self.assertEqual(disclosure["listing_calls"], 2)
        self.assertEqual(disclosure["inference_calls"], 0)
        self.assertEqual(disclosure["retries"], 0)
        self.assertFalse(disclosure["packet_fixture_probe_or_task_text_sent"])

        local = data["local_branch"]
        self.assertEqual(local["endpoint_base_url_sanitized"],
                         "http://localhost:1234/v1")
        self.assertTrue(local["accepted_model_id_present_exact"])
        self.assertEqual(local["accepted_model_id"], "openai/gpt-oss-20b")
        self.assertFalse(local["inference_performed"])

        api = data["api_branch"]
        self.assertEqual(api["endpoint_base_url_sanitized"],
                         "https://api.openai.com/v1")
        self.assertEqual(api["request"]["authorization"], "Bearer [REDACTED]")
        self.assertFalse(api["inference_performed"])
        self.assertGreaterEqual(len(api["nomination_set"]), 1)
        ranks = [n["rank"] for n in api["nomination_set"]]
        self.assertEqual(ranks, list(range(1, len(ranks) + 1)))
        for nom in api["nomination_set"]:
            self.assertTrue(nom["claude_family_excluded"])
            self.assertIn("temperature_0_5", nom["parameter_support"])
            self.assertEqual(nom["parameter_support"]["temperature_0_5"],
                             "official_contract_pending")


if __name__ == "__main__":
    unittest.main()
