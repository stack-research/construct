"""Conformance vectors: menu-carrying v1 renderer (D6a)."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness import efc_contracts as c
from harness.efc_commitment_wire_v1 import SCHEMA_RELPATH, WIRE_PROPERTIES
from harness.efc_fixtures_v1 import FIXTURES_DIR, build_fixture, default_content_records
from harness.efc_render_v1 import (FOREGROUND_MENU_ONLY_TEMPLATE_BYTES,
                                     FOREGROUND_TEMPLATE_BYTES,
                                     GENERIC_CAUTION_SHA256,
                                     GENERIC_CAUTION_TEXT,
                                     OFFER_PROJECTION_SHA256,
                                     OFFER_PROJECTION_TEXT,
                                     RenderRefusalError, action_set_block_span,
                                     foreground_template, foreground_template_hash,
                                     menu_labels_in_renderer_owned_regions,
                                     menu_only_template, menu_only_template_hash,
                                     render_prompt, render_prompt_menu_only,
                                     renderer_contract_hash,
                                     renderer_contract_payload)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / SCHEMA_RELPATH
LIVE_FIXTURE_PATHS = sorted(FIXTURES_DIR.glob("*.json"))


def _load_live_fixtures() -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in LIVE_FIXTURE_PATHS
    ]


class TestInheritedTextIdentity(unittest.TestCase):
    def test_generic_caution_byte_identical_to_v0_contracts(self):
        self.assertEqual(GENERIC_CAUTION_TEXT, c.GENERIC_CAUTION_TEXT)
        self.assertEqual(GENERIC_CAUTION_SHA256, c.GENERIC_CAUTION_SHA256)

    def test_offer_projection_byte_identical_to_v0_contracts(self):
        self.assertEqual(OFFER_PROJECTION_TEXT, c.OFFER_PROJECTION_TEXT)
        self.assertEqual(OFFER_PROJECTION_SHA256, c.OFFER_PROJECTION_SHA256)


class TestTemplateIdentity(unittest.TestCase):
    def test_foreground_template_hash_is_canonical_bytes(self):
        import hashlib
        self.assertEqual(
            foreground_template_hash(),
            hashlib.sha256(FOREGROUND_TEMPLATE_BYTES).hexdigest(),
        )
        self.assertEqual(
            foreground_template_hash(),
            foreground_template_hash(foreground_template()),
        )

    def test_menu_only_template_hash_is_canonical_bytes(self):
        import hashlib
        self.assertEqual(
            menu_only_template_hash(),
            hashlib.sha256(FOREGROUND_MENU_ONLY_TEMPLATE_BYTES).hexdigest(),
        )
        self.assertEqual(
            menu_only_template_hash(),
            menu_only_template_hash(menu_only_template()),
        )

    def test_canonical_dumps_use_ensure_ascii_false(self):
        import hashlib
        import json
        raw = json.dumps(
            foreground_template(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        self.assertEqual(FOREGROUND_TEMPLATE_BYTES, raw)
        self.assertEqual(foreground_template_hash(), hashlib.sha256(raw).hexdigest())


class TestRenderDeterminism(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = _load_live_fixtures()
        if len(cls.fixtures) < 1:
            raise unittest.SkipTest("no attested live fixtures on disk")

    def test_byte_deterministic_full_render_across_repeated_calls(self):
        for fixture in self.fixtures:
            first = render_prompt(fixture)
            for _ in range(20):
                again = render_prompt(fixture)
                self.assertEqual(first.prompt, again.prompt)
                self.assertEqual(first.sha256, again.sha256)

    def test_byte_deterministic_menu_only_across_repeated_calls(self):
        for fixture in self.fixtures:
            first = render_prompt_menu_only(fixture)
            for _ in range(20):
                again = render_prompt_menu_only(fixture)
                self.assertEqual(first.prompt, again.prompt)
                self.assertEqual(first.sha256, again.sha256)

    def test_renderer_contract_hash_stable(self):
        first = renderer_contract_hash()
        for _ in range(10):
            self.assertEqual(renderer_contract_hash(), first)


class TestNoFixtureIdentifierInEngineSurface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = _load_live_fixtures()

    def test_full_render_excludes_task_id_and_fixture_id(self):
        for fixture in self.fixtures:
            rendered = render_prompt(fixture)
            self.assertNotIn(fixture["task_id"], rendered.prompt)
            self.assertNotIn(fixture["fixture_id"], rendered.prompt)

    def test_menu_only_render_excludes_task_id_and_fixture_id(self):
        for fixture in self.fixtures:
            rendered = render_prompt_menu_only(fixture)
            self.assertNotIn(fixture["task_id"], rendered.prompt)
            self.assertNotIn(fixture["fixture_id"], rendered.prompt)


class TestMenuOnlyMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = _load_live_fixtures()

    def test_menu_only_has_action_set_and_commitment_only(self):
        tmpl = menu_only_template()
        for fixture in self.fixtures:
            rendered = render_prompt_menu_only(fixture)
            self.assertIn(tmpl["action_set_header"], rendered.prompt)
            self.assertIn(tmpl["commitment_instruction_header"], rendered.prompt)
            self.assertNotIn(fixture["task_body"], rendered.prompt)
            self.assertNotIn(GENERIC_CAUTION_TEXT, rendered.prompt)
            self.assertNotIn(tmpl.get("generic_caution_header", "[generic caution]"),
                             rendered.prompt)
            for field in ("assertion_basis_kind", "source_reference", "decision_scope"):
                self.assertNotIn(f"{field}:", rendered.prompt)

    def test_menu_only_preserves_menu_order(self):
        for fixture in self.fixtures:
            rendered = render_prompt_menu_only(fixture)
            start, end = action_set_block_span(
                rendered.prompt, menu_only_template())
            block = rendered.prompt[start:end]
            for label in fixture["menu_order"]:
                self.assertIn(f"- {label}", block)
            positions = [block.index(f"- {label}") for label in fixture["menu_order"]]
            self.assertEqual(positions, sorted(positions))


class TestMenuOrderAndLeakDiscipline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = _load_live_fixtures()

    def test_menu_order_preserved_exactly_in_action_set(self):
        for fixture in self.fixtures:
            rendered = render_prompt(fixture)
            start, end = action_set_block_span(rendered.prompt)
            block = rendered.prompt[start:end]
            for label in fixture["menu_order"]:
                self.assertIn(f"- {label}", block)
            positions = [block.index(f"- {label}") for label in fixture["menu_order"]]
            self.assertEqual(positions, sorted(positions))

    def test_no_menu_label_in_renderer_owned_regions(self):
        for fixture in self.fixtures:
            rendered = render_prompt(fixture)
            leaks = menu_labels_in_renderer_owned_regions(
                rendered.prompt,
                fixture["menu_order"],
            )
            self.assertEqual(leaks, (), fixture["fixture_id"])

    def test_scrub_hole_demo_label_equals_field_value_detected(self):
        """Label ≡ trigger-field value injected into caution must be detected."""
        fixture = copy.deepcopy(_load_live_fixtures()[0])
        injected_label = "release"
        fixture["source_reference"] = injected_label
        tmpl = foreground_template()
        # Simulate renderer injection into generic-caution region.
        malicious_caution = GENERIC_CAUTION_TEXT + f" {injected_label}"
        prompt = render_prompt(fixture).prompt.replace(
            GENERIC_CAUTION_TEXT, malicious_caution)
        leaks = menu_labels_in_renderer_owned_regions(
            prompt, fixture["menu_order"])
        self.assertIn(injected_label, leaks)
        # Old scrub-then-check hole: scrubbing field value hides the injection.
        start, end = action_set_block_span(prompt, tmpl)
        outside = prompt[:start] + prompt[end:]
        for field in ("task_body", "source_reference"):
            outside = outside.replace(str(fixture[field]), "")
        scrub_leaks = [lbl for lbl in fixture["menu_order"] if lbl in outside]
        self.assertNotIn(injected_label, scrub_leaks)

    def test_generic_caution_present_verbatim_in_full_render(self):
        for fixture in self.fixtures:
            rendered = render_prompt(fixture)
            self.assertIn(GENERIC_CAUTION_TEXT, rendered.prompt)

    def test_commitment_instruction_neutral_no_label_tokens(self):
        payload = renderer_contract_payload()
        instruction = payload["template"]["commitment_instruction_text"]
        labels = set()
        for fixture in self.fixtures:
            labels.update(fixture["menu_order"])
        for label in labels:
            self.assertNotIn(label, instruction)


class TestCommitmentWireInstruction(unittest.TestCase):
    def test_instruction_names_schema_fields(self):
        instruction = renderer_contract_payload()["template"]["commitment_instruction_text"]
        self.assertIn("commitment_enum", instruction)
        self.assertIn("optional_prose", instruction)

    def test_schema_closure_matches_instruction(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        wire = schema["$defs"]["commitment_wire"]
        self.assertEqual(set(wire["properties"]), set(WIRE_PROPERTIES))
        self.assertEqual(set(wire["required"]), {"commitment_enum"})


class TestStrictInputGate(unittest.TestCase):
    def test_refuse_unattested_built_fixture(self):
        record = default_content_records()[0]
        fixture = build_fixture(record)
        self.assertNotIn("plausibility_attestation", fixture)
        with self.assertRaises(RenderRefusalError) as ctx:
            render_prompt(fixture)
        self.assertIn("plausibility", str(ctx.exception).lower())

    def test_refuse_malformed_fixture(self):
        attested = _load_live_fixtures()[0]
        bad = copy.deepcopy(attested)
        bad["expected_commitment_enum"] = "proceed"
        with self.assertRaises(RenderRefusalError):
            render_prompt(bad)

    def test_default_gate_requires_attestation(self):
        record = default_content_records()[0]
        fixture = build_fixture(record)
        with self.assertRaises(RenderRefusalError):
            render_prompt(fixture, require_plausibility_attestation=True)

    def test_menu_only_refuses_unattested_fixture(self):
        record = default_content_records()[0]
        fixture = build_fixture(record)
        with self.assertRaises(RenderRefusalError):
            render_prompt_menu_only(fixture)


class TestCorpusUntouched(unittest.TestCase):
    def test_render_suite_never_writes_real_corpus(self):
        before = {p: p.read_bytes() for p in LIVE_FIXTURE_PATHS}
        fixtures = _load_live_fixtures()
        for fixture in fixtures:
            render_prompt(fixture)
            render_prompt_menu_only(fixture)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / "would_be_write.json"
            tmp_path.write_text("noop", encoding="utf-8")
        for path, data in before.items():
            self.assertEqual(path.read_bytes(), data)


if __name__ == "__main__":
    unittest.main()
