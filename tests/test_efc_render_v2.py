"""Conformance vectors for EFC v2 renderer."""

from __future__ import annotations

import unittest

from harness.efc_render_v2 import render_for_lane, render_forced_class, render_prompt
from tests.efc_v2_test_fixtures import make_minimal_suite


class TestRenderV2(unittest.TestCase):
    def test_untreated_render_deterministic(self):
        fixture = make_minimal_suite(1)[0]
        a = render_prompt(fixture)
        b = render_prompt(fixture)
        self.assertEqual(a.prompt, b.prompt)
        self.assertEqual(a.sha256, b.sha256)

    def test_forced_class_render_includes_supplied_class(self):
        fixture = make_minimal_suite(1)[0]
        rendered = render_forced_class(fixture, supplied_class="commit")
        self.assertIn("commit", rendered.prompt)
        self.assertIn("alpha_commit", rendered.prompt)

    def test_render_for_lane_irrelevant(self):
        fixture = make_minimal_suite(1)[2]
        rendered = render_for_lane(fixture, "M_irrelevant")
        self.assertIn("[action set]", rendered.prompt)
