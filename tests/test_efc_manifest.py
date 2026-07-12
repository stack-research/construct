"""Wire tests for the §5.2 calibration-manifest machine check.

Mock manifests only. The check is structural: pinned equality, closed schema,
forbidden-content scan. Semantic disjointness stays with the cold seat.
"""

from __future__ import annotations

import unittest

from harness import efc_contracts as c
from harness.efc_manifest import check_calibration_manifest, manifest_hash

H = "c" * 64


def healthy_manifest(**overrides):
    manifest = {
        "part_i_spec_hash": c.PART_I_SPEC_SHA256,
        "engine_roster": ["engine-x-2026-05"],
        "model_id": "engine-x-2026-05",
        "decoding_contract_id": "decode-t05-frozen",
        "renderer_id": "renderer-v1",
        "foreground_template_hash": H,
        "calibration_fixtures": [{"fixture_id": "cal-001", "sha256": H},
                                 {"fixture_id": "cal-002", "sha256": H}],
        "world_oracles": [{"oracle_id": "corpus-w1",
                           "timestamp": "2026-07-12T00:00:00Z",
                           "sha256": H}],
        "ignorance_probe_contract": {"probe_fixture_ids": ["probe-01"],
                                     "max_recoverable_rate": 0.2},
        "predicate_contract_hash": H,
        "extractor_hash": H,
        "check_contract_hash": H,
        "generic_caution_text": c.GENERIC_CAUTION_TEXT,
        "generic_caution_sha256": c.GENERIC_CAUTION_SHA256,
        "offer_projection_text": c.OFFER_PROJECTION_TEXT,
        "offer_projection_sha256": c.OFFER_PROJECTION_SHA256,
        "calibration_k": c.CALIBRATION_K,
        "temperature": c.CALIBRATION_TEMPERATURE,
        "collapse_diagnostic_temperature": c.COLLAPSE_DIAGNOSTIC_TEMPERATURE,
        "stop_rule": c.STOP_RULE_ID,
        "n_max": c.N_MAX,
        "total_budget_tokens": 2_000_000,
    }
    manifest.update(overrides)
    return manifest


class TestManifestCheck(unittest.TestCase):
    def test_healthy_manifest_passes_with_stable_hash(self):
        result = check_calibration_manifest(healthy_manifest())
        self.assertTrue(result.ok, msg=str(result.failures))
        self.assertEqual(result.manifest_hash,
                         manifest_hash(healthy_manifest()))

    def test_wrong_seal_hash_fails(self):
        result = check_calibration_manifest(healthy_manifest(
            part_i_spec_hash="f" * 64))
        self.assertIn("sealed Part I", " ".join(result.failures))

    def test_tampered_caution_text_fails(self):
        result = check_calibration_manifest(healthy_manifest(
            generic_caution_text=c.GENERIC_CAUTION_TEXT.replace(
                "provenance tool", "provenance tool carefully")))
        self.assertFalse(result.ok)
        # both the equality pin and the recompute cross-check fire
        text = " ".join(result.failures)
        self.assertIn("differs from the sealed text", text)
        self.assertIn("does not recompute", text)

    def test_sampling_constants_pinned(self):
        for override in ({"calibration_k": 6}, {"temperature": 0.7},
                         {"n_max": 25}, {"stop_rule": "run_until_happy"},
                         {"total_budget_tokens": 0}):
            result = check_calibration_manifest(healthy_manifest(**override))
            self.assertFalse(result.ok, msg=str(override))

    def test_unknown_key_fails_closed(self):
        result = check_calibration_manifest(healthy_manifest(
            reviewer_notes="looks fine"))
        self.assertIn("closed", " ".join(result.failures))

    def test_forbidden_key_scan_fires_on_nested_outcome(self):
        bad = healthy_manifest()
        bad["calibration_fixtures"] = [
            {"fixture_id": "cal-001", "sha256": H,
             "outcome_label": "decline"}]
        result = check_calibration_manifest(bad)
        self.assertFalse(result.ok)
        text = " ".join(result.failures)
        self.assertIn("forbidden key", text)

    def test_roster_and_fixture_shapes(self):
        self.assertFalse(check_calibration_manifest(
            healthy_manifest(engine_roster=[])).ok)
        self.assertFalse(check_calibration_manifest(
            healthy_manifest(calibration_fixtures=[{"fixture_id": "x"}])).ok)
        self.assertFalse(check_calibration_manifest(healthy_manifest(
            world_oracles=[{"oracle_id": "w", "timestamp": "sometime",
                            "sha256": H}])).ok)

    def test_ignorance_contract_rate_domain(self):
        self.assertFalse(check_calibration_manifest(healthy_manifest(
            ignorance_probe_contract={"probe_fixture_ids": ["p"],
                                      "max_recoverable_rate": 1.0})).ok)

    def test_population_region_paths(self):
        ok_curve = check_calibration_manifest(healthy_manifest(
            population_region={"response_curve_only": True}))
        self.assertTrue(ok_curve.ok, msg=str(ok_curve.failures))
        ok_region = check_calibration_manifest(healthy_manifest(
            population_region={"vertices": [
                {"match_mismatch": 0.6, "match_commit": 0.2, "irrelevant": 0.2},
                {"match_mismatch": 0.1, "match_commit": 0.1, "irrelevant": 0.8},
            ]}))
        self.assertTrue(ok_region.ok, msg=str(ok_region.failures))
        bad_region = check_calibration_manifest(healthy_manifest(
            population_region={"vertices": [
                {"match_mismatch": 0.5, "match_commit": 0.5, "irrelevant": 0.0},
            ]}))
        self.assertFalse(bad_region.ok)
        self.assertIn("p_irrelevant", " ".join(bad_region.failures))

    def test_missing_key_reported(self):
        manifest = healthy_manifest()
        del manifest["stop_rule"]
        result = check_calibration_manifest(manifest)
        self.assertFalse(result.ok)
        self.assertIn("missing manifest keys", " ".join(result.failures))


if __name__ == "__main__":
    unittest.main()
