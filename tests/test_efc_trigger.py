"""Wire tests for the §2.1 closed trigger and §9.1 family gates.

Mock fixtures only — nothing here is evidence about the mechanism; the suite
proves the extraction closure refuses by name what the seal excludes and that
the trigger result is byte-identical under oracle/outcome removal.
"""

from __future__ import annotations

import unittest

from harness.efc_trigger import (ExtractionClosureError, check_extraction_integrity,
                                 extract_trigger_features, family_validity,
                                 irrelevant_shape_failures, strip_oracle_and_outcome,
                                 trigger_fires, trigger_result_record)


def matching_fixture(task_id="t1", stratum="match_mismatch", **overrides):
    fixture = {
        "task_id": task_id,
        "surface_text": "Cite the report and decide the rollout scope.",
        "population_id": "pop-cal-01",
        "assertion_basis_kind": "cited_source",
        "observation_boundary_present": False,
        "source_reference_present": True,
        "decision_scope_present": True,
        "stratum": stratum,
        # oracle/outcome material the extractor must never consult
        "oracle": {"kind": "world", "source": "external"},
        "outcome_label": "decline",
        "expected_action": "defer",
        "required_scope": "region-A",
        "fetched_source_scope": "region-B",
    }
    fixture.update(overrides)
    return fixture


def irrelevant_fixture(task_id="t9", variant="canonical", **overrides):
    fixture = matching_fixture(task_id=task_id, stratum="irrelevant")
    if variant == "canonical":
        fixture["observation_boundary_present"] = True
    else:
        fixture["assertion_basis_kind"] = "direct_observation"
    fixture.update(overrides)
    return fixture


class TestExtractionClosure(unittest.TestCase):
    def test_happy_path_fires(self):
        features = extract_trigger_features(matching_fixture())
        self.assertTrue(trigger_fires(features))

    def test_each_conjunct_gates(self):
        for flip in ({"assertion_basis_kind": "direct_observation"},
                     {"observation_boundary_present": True},
                     {"source_reference_present": False},
                     {"decision_scope_present": False}):
            features = extract_trigger_features(matching_fixture(**flip))
            self.assertFalse(trigger_fires(features), msg=str(flip))

    def test_missing_declared_field_refused(self):
        fixture = matching_fixture()
        del fixture["observation_boundary_present"]
        with self.assertRaises(ExtractionClosureError):
            extract_trigger_features(fixture)

    def test_untyped_field_refused(self):
        with self.assertRaises(ExtractionClosureError):
            extract_trigger_features(
                matching_fixture(observation_boundary_present="no"))
        with self.assertRaises(ExtractionClosureError):
            extract_trigger_features(matching_fixture(assertion_basis_kind=7))

    def test_byte_identity_under_oracle_removal(self):
        fixture = matching_fixture()
        self.assertTrue(check_extraction_integrity(fixture))
        stripped = strip_oracle_and_outcome(fixture)
        for key in ("oracle", "outcome_label", "expected_action",
                    "required_scope", "fetched_source_scope", "stratum"):
            self.assertNotIn(key, stripped)
        self.assertEqual(trigger_result_record(fixture),
                         trigger_result_record(stripped))

    def test_trigger_blind_to_oracle_and_value_content(self):
        base = trigger_result_record(matching_fixture())
        mutated_oracle = trigger_result_record(
            matching_fixture(outcome_label="commit", required_scope="region-Z"))
        self.assertEqual(base, mutated_oracle)
        # value content of the surface prose is also outside the four fields
        mutated_text = trigger_result_record(
            matching_fixture(surface_text="Entirely different topic."))
        self.assertEqual(base, mutated_text)


class TestIrrelevantShape(unittest.TestCase):
    def test_canonical_and_variant_shapes_pass(self):
        self.assertEqual(irrelevant_shape_failures(irrelevant_fixture()), [])
        self.assertEqual(
            irrelevant_shape_failures(irrelevant_fixture(variant="basis")), [])

    def test_dropping_check_inputs_fails(self):
        failures = irrelevant_shape_failures(
            irrelevant_fixture(source_reference_present=False))
        self.assertTrue(any("source_reference_present" in f for f in failures))

    def test_would_fire_shape_fails(self):
        # both semantic conjuncts left true: a routing-tag-free family cannot
        # contain an "irrelevant" fixture that fires
        fixture = irrelevant_fixture()
        fixture["observation_boundary_present"] = False
        fixture["assertion_basis_kind"] = "cited_source"
        failures = irrelevant_shape_failures(fixture)
        self.assertTrue(any("would fire" in f for f in failures))


class TestFamilyValidity(unittest.TestCase):
    def _family(self):
        return [
            matching_fixture("mm1", "match_mismatch"),
            matching_fixture("mm2", "match_mismatch"),
            matching_fixture("mc1", "match_commit"),
            matching_fixture("mc2", "match_commit"),
            irrelevant_fixture("ir1"),
            irrelevant_fixture("ir2", variant="basis"),
        ]

    def test_healthy_family_passes(self):
        result = family_validity(self._family())
        self.assertTrue(result.ok, msg=str(result.failures))

    def test_unbalanced_counts_fail(self):
        family = self._family() + [matching_fixture("mm3", "match_mismatch")]
        result = family_validity(family)
        self.assertTrue(any("unbalanced" in f for f in result.failures))

    def test_missed_fire_fails(self):
        family = self._family()
        family[0] = matching_fixture("mm1", "match_mismatch",
                                     source_reference_present=False)
        result = family_validity(family)
        self.assertTrue(any("missed fire" in f for f in result.failures))

    def test_false_fire_fails(self):
        family = self._family()
        bad = irrelevant_fixture("ir1")
        bad["observation_boundary_present"] = False
        family[4] = bad
        result = family_validity(family)
        self.assertTrue(any("false fire" in f for f in result.failures))

    def test_leakage_phrase_fails(self):
        family = self._family()
        family[2] = matching_fixture(
            "mc1", "match_commit",
            surface_text="As in the meridian retraction episode, decide scope.")
        result = family_validity(family, forbidden_phrases=("meridian",))
        self.assertTrue(any("leakage" in f for f in result.failures))

    def test_unknown_stratum_fails(self):
        result = family_validity([matching_fixture("x", "sourcey")])
        self.assertFalse(result.ok)


if __name__ == "__main__":
    unittest.main()
