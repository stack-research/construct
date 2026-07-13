"""Wire tests: frozen renderer — fork identity, forbidden foreground fields,
frozen lane treatments, declarative template identity (sealed §8.2-§8.4/§13;
design §4.3; B4)."""

from __future__ import annotations

import unittest

from harness import efc_contracts as c
from harness.efc_renderer import (FOREGROUND_TEMPLATE_BYTES,
                                  PLACEBO_POSITION_GATE,
                                  RendererContractError, build_foreground,
                                  canonical_tokens, foreground_template,
                                  foreground_template_hash,
                                  render_evidence_block, render_prompt,
                                  renderer_contract_hash,
                                  renderer_contract_payload)
from tests.efc_wire_fixtures import (fictional_source_ref, firing_fixture,
                                     irrelevant_fixture)


class TestForeground(unittest.TestCase):
    def test_deterministic_once_per_identity(self):
        fx = firing_fixture("wt-01", fictional_source_ref(0), mismatch=True)
        a, b = build_foreground(fx), build_foreground(dict(fx))
        self.assertEqual(a.sha256, b.sha256)
        self.assertTrue(a.trigger_fires)

    def test_forbidden_foreground_fields_refused(self):
        for bad in ("required_scope", "expected_action", "outcome_label",
                    "oracle_answer", "fetched_source_scope"):
            fx = firing_fixture("wt-02", fictional_source_ref(0), True)
            fx[bad] = "leak"
            with self.assertRaises(RendererContractError):
                build_foreground(fx)

    def test_undeclared_field_refused(self):
        fx = firing_fixture("wt-03", fictional_source_ref(0), True)
        fx["routing_tag"] = "match"  # the §17-rejected content-free tag
        with self.assertRaises(RendererContractError):
            build_foreground(fx)


class TestTemplateIdentity(unittest.TestCase):
    """B4 repair tests: the template is declarative data; its hash covers the
    exact structural bytes, and rendering is driven by the data."""

    def test_template_hash_is_of_the_canonical_bytes(self):
        import hashlib
        self.assertEqual(foreground_template_hash(),
                         hashlib.sha256(FOREGROUND_TEMPLATE_BYTES).hexdigest())
        self.assertEqual(foreground_template_hash(),
                         foreground_template_hash(foreground_template()))
        mutated = dict(foreground_template(), line_joiner=" | ")
        self.assertNotEqual(foreground_template_hash(mutated),
                            foreground_template_hash())

    def test_rendering_is_driven_by_template_data(self):
        fx = firing_fixture("wt-04", fictional_source_ref(0), True)
        default = build_foreground(fx)
        mutated = dict(foreground_template(),
                       declared_line_format="{field} == {value}")
        changed = build_foreground(fx, template=mutated)
        self.assertNotEqual(default.text, changed.text)
        self.assertIn("source_reference ==", changed.text)

    def test_renderer_contract_hash_changes_on_component_mutation(self):
        import hashlib
        import json
        payload = renderer_contract_payload()
        mutated = dict(payload, render_fields=payload["render_fields"][:-1])
        h = hashlib.sha256(json.dumps(mutated, sort_keys=True,
                                      separators=(",", ":")).encode()
                           ).hexdigest()
        self.assertNotEqual(h, renderer_contract_hash())

    def test_canonical_template_is_copy_on_read(self):
        """Resolution G mandated behavior: the canonical identity is the
        immutable bytes; every read is a fresh copy, so mutating what you
        were handed changes NOTHING behind the stable hash."""
        before = foreground_template_hash()
        leaked = foreground_template()
        leaked["evidence_header"] = "[forged]"
        leaked["declared_field_order"].append("required_scope")
        self.assertNotEqual(foreground_template(), leaked)
        self.assertEqual(foreground_template_hash(), before)
        self.assertEqual(foreground_template()["evidence_header"],
                         "[external check evidence]")

    def test_mutated_alias_cannot_ride_a_stale_hash_at_render(self):
        """Item G mandated test: a foreground built under the canonical
        template refuses to render under a mutated alias — behavior cannot
        change while the recorded template hash stays stable."""
        fx = firing_fixture("wt-05", fictional_source_ref(0), True)
        fg = build_foreground(fx)
        self.assertEqual(fg.template_sha256, foreground_template_hash())
        alias = foreground_template()
        alias["evidence_header"] = "[forged evidence header]"
        with self.assertRaises(RendererContractError) as ctx:
            render_prompt(fg, "C_controlled_check", "evidence",
                          template=alias)
        self.assertIn("template identity mismatch", str(ctx.exception))
        # and the alias cannot claim the canonical hash: it recomputes
        self.assertNotEqual(foreground_template_hash(alias),
                            foreground_template_hash())

    def test_contract_payload_carries_frozen_text_hashes(self):
        payload = renderer_contract_payload()
        self.assertEqual(payload["generic_caution_sha256"],
                         c.GENERIC_CAUTION_SHA256)
        self.assertEqual(payload["template"], foreground_template())
        self.assertEqual(payload["placebo_position_gate"],
                         PLACEBO_POSITION_GATE)


class TestLaneTreatments(unittest.TestCase):
    def setUp(self):
        self.fg = build_foreground(
            firing_fixture("wt-10", fictional_source_ref(0), True))

    def test_fork_identity_shared_prefix(self):
        """Every lane's prompt begins with the identical foreground bytes;
        only the declared treatment differs (§13)."""
        prompts = {
            "B_inactive": render_prompt(self.fg, "B_inactive"),
            "C_controlled_check": render_prompt(self.fg, "C_controlled_check",
                                                "fictional evidence"),
            "G_generic_caution": render_prompt(self.fg, "G_generic_caution"),
            "O_offer_projection": render_prompt(self.fg, "O_offer_projection"),
        }
        for lane, prompt in prompts.items():
            self.assertTrue(prompt.startswith(self.fg.text), msg=lane)
        self.assertEqual(prompts["B_inactive"], self.fg.text)

    def test_frozen_texts_inserted_verbatim(self):
        self.assertIn(c.GENERIC_CAUTION_TEXT,
                      render_prompt(self.fg, "G_generic_caution"))
        self.assertIn(c.OFFER_PROJECTION_TEXT,
                      render_prompt(self.fg, "O_offer_projection"))

    def test_offer_projection_silent_when_trigger_silent(self):
        fg = build_foreground(
            irrelevant_fixture("wt-11", fictional_source_ref(1)))
        self.assertFalse(fg.trigger_fires)
        self.assertEqual(render_prompt(fg, "O_offer_projection"), fg.text)

    def test_no_check_lanes_refuse_evidence(self):
        for lane in ("B_inactive", "G_generic_caution", "O_offer_projection",
                     "S0_no_check"):
            with self.assertRaises(RendererContractError):
                render_prompt(self.fg, lane, "evidence")

    def test_always_check_requires_evidence(self):
        with self.assertRaises(RendererContractError):
            render_prompt(self.fg, "A_always_check")

    def test_unknown_lane_refused(self):
        with self.assertRaises(RendererContractError):
            render_prompt(self.fg, "Z_new_lane")

    def test_canonical_tokens(self):
        self.assertEqual(canonical_tokens("  a  b\nc "), ["a", "b", "c"])

    def test_relevant_and_placebo_share_one_insertion_point(self):
        """Resolution G mandated test: relevant evidence and placebo
        evidence go through the identical insertion function at the
        identical structural position (`placebo_position_gate`)."""
        s1 = render_prompt(self.fg, "S1_relevant_check", "RELEVANT-BLOB")
        s2 = render_prompt(self.fg, "S2_placebo", "PLACEBO-BLOB")
        self.assertEqual(s1.replace("RELEVANT-BLOB", "X"),
                         s2.replace("PLACEBO-BLOB", "X"))
        for prompt, blob in ((s1, "RELEVANT-BLOB"), (s2, "PLACEBO-BLOB")):
            self.assertEqual(prompt.count("[external check evidence]"), 1)
            self.assertTrue(prompt.endswith(render_evidence_block(blob)))


if __name__ == "__main__":
    unittest.main()
