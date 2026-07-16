"""Conformance vectors for the EFC v1 calibration fixture builder (D5)."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from harness.efc_leak_audit_v1 import (check_no_lexical_marking,
                                       evaluate_leak_audit,
                                       project_trigger_feature_strings)
from harness.efc_fixtures_v1 import (ACTION_SET, FIXTURES_DIR,
                                     MANIFEST_PATH, ROLE_MAP, SUITE_FIXTURE_COUNT,
                                     SUITE_K, build_fixture, build_suite,
                                     default_content_records,
                                     suite_bytes, task_body_overlaps_menu_labels,
                                     validate_suite, write_suite_artifacts)
from harness.efc_menu_composition_v1 import (check_fixture_composition,
                                             check_suite_ordinal_uniformity)

ROOT = Path(__file__).resolve().parents[1]


class TestFixtureBuilder(unittest.TestCase):
  def test_default_suite_builds_and_all_gates_green(self):
    built = build_suite()
    self.assertEqual(len(built.fixtures), SUITE_FIXTURE_COUNT)
    self.assertEqual(len(built.attestation_pending), SUITE_FIXTURE_COUNT)
    self.assertTrue(built.gate_results.composition_ok)
    self.assertTrue(built.gate_results.ordinal_ok)
    self.assertTrue(built.gate_results.leak_audit_ok)
    self.assertTrue(built.gate_results.lexical_marking_ok)
    self.assertTrue(built.gate_results.extraction_integrity_ok)
    self.assertTrue(built.gate_results.family_validity_ok)
    self.assertFalse(built.gate_results.refusals)

  def test_attestation_never_fabricated(self):
    built = build_suite()
    self.assertEqual(built.manifest["attestation_status"], "pending")
    for fixture in built.fixtures:
      self.assertNotIn("plausibility_attestation", fixture)
    self.assertEqual(
      set(built.manifest["attestation_pending"]),
      {fx["fixture_id"] for fx in built.fixtures},
    )

  def test_builder_determinism_byte_identical_suite(self):
    first = suite_bytes(build_suite().fixtures)
    for _ in range(20):
      self.assertEqual(suite_bytes(build_suite().fixtures), first)

  def test_written_artifacts_match_builder(self):
    built = write_suite_artifacts()
    self.assertTrue(FIXTURES_DIR.is_dir())
    self.assertTrue(MANIFEST_PATH.is_file())
    for fixture in built.fixtures:
      path = FIXTURES_DIR / f"{fixture['fixture_id']}.json"
      self.assertTrue(path.is_file())
      on_disk = json.loads(path.read_text(encoding="utf-8"))
      self.assertEqual(on_disk, fixture)
      self.assertNotIn("plausibility_attestation", on_disk)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    self.assertEqual(manifest["k"], SUITE_K)
    self.assertEqual(manifest["attestation_status"], "pending")

  def test_k_choice_and_ordinal_histogram(self):
    built = build_suite()
    self.assertEqual(built.manifest["k"], 5)
    self.assertEqual(built.manifest["ordinal_histogram"], [3, 3, 3, 3, 3])
    self.assertEqual(built.manifest["ordinal_max_abs_dev_bound"], 2)

  def test_every_fixture_has_computed_projection(self):
    for fixture in build_suite().fixtures:
      self.assertEqual(
        fixture["trigger_feature_strings"],
        list(project_trigger_feature_strings(fixture)),
      )

  def test_task_bodies_do_not_overlap_menu_labels(self):
    for record in default_content_records():
      overlaps = task_body_overlaps_menu_labels(record.task_body)
      self.assertEqual(overlaps, (), record.fixture_id)

  def test_refuse_leaky_task_body(self):
    records = list(default_content_records())
    leaky_records = []
    for index in (0, 1):
      record = records[index]
      fixture = build_fixture(record)
      expected = fixture["expected_commitment_enum"]
      leaky_records.append(record.__class__(
        **{**record.__dict__,
           "task_body": record.task_body + f" choose {expected} now"}
      ))
    fixtures = [build_fixture(r) for r in leaky_records] + [
      build_fixture(r) for r in records[2:]
    ]
    gates = validate_suite(
      fixtures,
      require_plausibility_attestation=False,
    )
    self.assertFalse(gates.leak_audit_ok)

  def test_refuse_bad_projection(self):
    fixtures = list(build_suite().fixtures)
    fixtures[0] = dict(fixtures[0])
    fixtures[0]["trigger_feature_strings"] = ["author placeholder"]
    lexical = check_no_lexical_marking(fixtures)
    self.assertFalse(lexical.ok)
    self.assertIn("trigger_projection_mismatch", lexical.refusals)

  def test_refuse_ordinal_violation(self):
    records = list(default_content_records())
    records[0] = records[0].__class__(
      **{**records[0].__dict__, "ordinal_index": 0}
    )
    records[1] = records[1].__class__(
      **{**records[1].__dict__, "ordinal_index": 0}
    )
    records[2] = records[2].__class__(
      **{**records[2].__dict__, "ordinal_index": 0}
    )
    records[3] = records[3].__class__(
      **{**records[3].__dict__, "ordinal_index": 0}
    )
    records[4] = records[4].__class__(
      **{**records[4].__dict__, "ordinal_index": 0}
    )
    fixtures = [build_fixture(r) for r in records] + [
      build_fixture(r) for r in default_content_records()[5:]
    ]
    ordinal = check_suite_ordinal_uniformity(
      fixtures,
      require_plausibility_attestation=False,
    )
    self.assertFalse(ordinal.ok)
    self.assertEqual(ordinal.refusal, "ordinal_uniformity_exceeded")

  def test_full_attestation_required_for_pin_ready_composition(self):
    fixture = dict(build_suite().fixtures[0])
    without = check_fixture_composition(
      fixture,
      require_plausibility_attestation=False,
    )
    with_req = check_fixture_composition(fixture)
    self.assertTrue(without.ok)
    self.assertFalse(with_req.ok)
    self.assertEqual(with_req.refusal, "missing_plausibility_attestation")

  def test_validate_suite_defaults_require_attestation(self):
    fixtures = list(build_suite().fixtures)
    gates = validate_suite(fixtures)
    self.assertFalse(gates.composition_ok)
    self.assertIn("missing_plausibility_attestation", gates.refusals[0])

  def test_mm02_rewording_flagged_in_provenance(self):
    built = build_suite()
    mm02 = next(fx for fx in built.fixtures if fx["fixture_id"] == "efc_v1-mm-02")
    prov = mm02["provenance"]
    self.assertTrue(prov["rewording_applied"])
    self.assertIn("release", prov["rewording_note"])
    for fx in built.fixtures:
      if fx["fixture_id"] == "efc_v1-mm-02":
        continue
      self.assertFalse(fx["provenance"]["rewording_applied"])

  def test_provenance_index_covers_all_fixtures(self):
    built = build_suite()
    index = built.manifest["provenance_index"]
    self.assertEqual(len(index), SUITE_FIXTURE_COUNT)
    capture_count = sum(
      1 for entry in index.values()
      if entry["source_kind"] == "v0_capture_c_family"
    )
    episode_count = sum(
      1 for entry in index.values()
      if entry["source_kind"] == "episode_surface_adaptation"
    )
    self.assertEqual(capture_count, 3)
    self.assertEqual(episode_count, 12)

  def test_role_map_occupies_all_three_lexicon_roles(self):
    roles = set(ACTION_SET)
    mapped_roles = {ROLE_MAP[label] for label in roles}
    self.assertEqual(mapped_roles, {"commit", "non_commit", "baseline"})


if __name__ == "__main__":
  unittest.main()
