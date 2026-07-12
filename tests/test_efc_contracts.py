"""Seal-drift tripwires for harness/efc_contracts.py (SPEC_EFC §5.1/§8.3/§8.4).

Re-derives the pinned texts and the sealed file hash from the sealed document
itself: if either the spec file or the contracts module drifts, this suite
fails before any machinery can consume a stale pin.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from harness import efc_contracts as c

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = REPO_ROOT / c.PART_I_SPEC_RELPATH


def _extract_blockquote(section_heading: str) -> str:
    """Return the first blockquote after a heading, unwrapped to one line."""
    lines = SPEC_PATH.read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith(section_heading))
    quote: list[str] = []
    for ln in lines[start + 1:]:
        if ln.startswith("> "):
            quote.append(ln[2:])
        elif quote:
            break
    return " ".join(quote)


class TestSeal(unittest.TestCase):
    def test_sealed_file_hash_matches_pin(self):
        # canonical hash recorded in `epistemic-frame-check-v0-review`
        self.assertEqual(c.sha256_file(SPEC_PATH), c.PART_I_SPEC_SHA256)

    def test_generic_caution_text_matches_sealed_spec(self):
        self.assertEqual(_extract_blockquote("### 8.3 Frozen generic caution"),
                         c.GENERIC_CAUTION_TEXT)
        self.assertEqual(c.sha256_utf8(c.GENERIC_CAUTION_TEXT),
                         c.GENERIC_CAUTION_SHA256)

    def test_offer_projection_text_matches_sealed_spec(self):
        self.assertEqual(_extract_blockquote("### 8.4 Offer projection"),
                         c.OFFER_PROJECTION_TEXT)
        self.assertEqual(c.sha256_utf8(c.OFFER_PROJECTION_TEXT),
                         c.OFFER_PROJECTION_SHA256)

    def test_caution_names_no_trigger_machinery(self):
        # §8.3: may not name predicate fields, template ids, the disposition,
        # nomination language, or the check id
        for forbidden in ("assertion_basis_kind", "observation_boundary_present",
                          "source_reference_present", "decision_scope_present",
                          c.CHECK_ID, "disposition", "nominat"):
            self.assertNotIn(forbidden, c.GENERIC_CAUTION_TEXT)


class TestPinValues(unittest.TestCase):
    def test_effects_are_the_sealed_numbers(self):
        # §10.3 block, transcribed
        self.assertEqual(c.QUALITY_SUPERIORITY_MARGIN, 0.25)
        self.assertEqual(c.QUALITY_SUPERIORITY_CI_HALF_WIDTH, 0.20)
        self.assertEqual(c.QUALITY_NONINFERIORITY_MARGIN, 0.10)
        self.assertEqual(c.QUALITY_NONINFERIORITY_CI_HALF_WIDTH, 0.10)
        self.assertEqual(c.COST_EFFICIENCY_MARGIN, 0.10)
        self.assertEqual(c.COST_EFFICIENCY_CI_HALF_WIDTH, 0.05)
        self.assertEqual(c.POPULATION_ALWAYS_CHECK_MARGIN, 0.10)
        # §10.3 v0.2 explicit population precision pin (§18 amendment)
        self.assertEqual(c.POPULATION_COST_CI_HALF_WIDTH, 0.05)

    def test_ceilings_are_the_sealed_numbers(self):
        self.assertEqual(c.MAX_CHECK_INVOCATIONS_PER_TASK, 1)
        self.assertEqual(c.MAX_CONTROLLER_SOURCE_READ_TOKENS, 512)
        self.assertEqual(c.MAX_EXTERNAL_CHECK_OUTPUT_TOKENS, 256)
        self.assertEqual(c.MAX_GOVERNANCE_STEPS_PER_TASK, 2)
        self.assertEqual(c.MAX_INCREMENTAL_TOKENS_PER_ADDED_CORRECT, 1024)

    def test_sampling_contract(self):
        self.assertEqual(c.CALIBRATION_K, 5)
        self.assertEqual(c.CALIBRATION_TEMPERATURE, 0.5)
        self.assertEqual(c.COLLAPSE_DIAGNOSTIC_TEMPERATURE, 0.7)
        # v0.2 §18 amendment: bounded feasibility ceiling (v0.1's 24 admitted
        # no coherent configuration)
        self.assertEqual((c.N_ENUM_MIN, c.N_MAX), (2, 128))

    def test_vocabularies_closed(self):
        self.assertEqual(len(c.LANES), 6)
        self.assertEqual(len(c.SOURCE_LEGS), 3)
        self.assertEqual(len(c.STRATA), 3)
        self.assertEqual(len(c.REVISION_SCOPES), 4)
        self.assertEqual(set(c.TRIGGER_MATCHING_STRATA) | {"irrelevant"},
                         set(c.STRATA))
        # §13 row list + the one explicitly-untrusted §3.3 nomination row
        self.assertEqual(len(c.EVENT_TYPES), 18)


if __name__ == "__main__":
    unittest.main()
