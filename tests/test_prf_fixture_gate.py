"""Wire tests for the PRF fixture admission gate (SPEC_PAUSE_RESUME v0.1 §9).

Runs the gate on the checked-in `meridian` fixture (must be GATE OPEN), then
proves each refusal leg by tampering a copy: attested-not-computed ballast,
shared invalidation predicates, ghost rules, outcome lemmas, a missing
hermes-floor episode, and a decorative lose-cell."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from harness.check_prf_fixture import check_manifest

FIXTURE = Path(__file__).resolve().parent.parent / "episodes" / "prf" / "meridian"


def failed(checks):
    return {name for name, ok, _ in checks if not ok}


class TestGate(unittest.TestCase):
    def tampered(self, mutate):
        """Copy the fixture, apply `mutate(dir_path)`, run the gate."""
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "meridian"
            shutil.copytree(FIXTURE, dst)
            mutate(dst)
            return check_manifest(dst / "manifest.json")

    def test_checked_in_fixture_is_gate_open(self):
        checks = check_manifest(FIXTURE / "manifest.json")
        self.assertEqual(failed(checks), set(),
                         msg=f"gate refused: {failed(checks)}")

    def test_attested_ballast_refused(self):
        def mutate(d):
            ep = json.loads((d / "ep-win.json").read_text())
            ep["ballast"]["derived_obligation_tokens"] += 500  # attested lie
            (d / "ep-win.json").write_text(json.dumps(ep))
        bad = failed(self.tampered(mutate))
        self.assertIn("ballast_gamma_mirror[meridian-win]", bad)

    def test_sub_gamma_fixture_refused(self):
        def mutate(d):
            pop = json.loads((d / "population.json").read_text())
            pop["gamma"] = 0.99   # nothing could carry that much warmth
            (d / "population.json").write_text(json.dumps(pop))
        bad = failed(self.tampered(mutate))
        self.assertTrue(any(n.startswith("ballast_gamma_mirror") for n in bad))

    def test_shared_invalidation_path_refused(self):
        def mutate(d):
            pop = json.loads((d / "population.json").read_text())
            pop["reopen_rules"]["RR2"]["invalidation_predicate_id"] = \
                pop["reopen_rules"]["RR1"]["invalidation_predicate_id"]
            (d / "population.json").write_text(json.dumps(pop))
        bad = failed(self.tampered(mutate))
        self.assertIn("invalidation_path_separation", bad)

    def test_outcome_lemma_in_rulebook_refused(self):
        def mutate(d):
            pop = json.loads((d / "population.json").read_text())
            pop["surface_tag_schema"].append("preferred_option_marker")
            (d / "population.json").write_text(json.dumps(pop))
        bad = failed(self.tampered(mutate))
        self.assertIn("rulebook_genealogy_ok", bad)

    def test_missing_hermes_floor_refused(self):
        def mutate(d):
            m = json.loads((d / "manifest.json").read_text())
            for name in m["episodes"]:
                ep = json.loads((d / name).read_text())
                # un-gap the witness: it reads the whole catalog
                ep["witness_route"] = ["S1", "S2", "S3", "S4", "S5"]
                (d / name).write_text(json.dumps(ep))
        bad = failed(self.tampered(mutate))
        self.assertIn("hermes_floor", bad)

    def test_alphabetical_winner_fails_floor(self):
        def mutate(d):
            m = json.loads((d / "manifest.json").read_text())
            for name in m["episodes"]:
                ep = json.loads((d / name).read_text())
                ep["winner_option_id"] = "N"   # first option_id alphabetically
                (d / name).write_text(json.dumps(ep))
        bad = failed(self.tampered(mutate))
        self.assertIn("hermes_floor", bad)

    def test_decorative_lose_cell_refused(self):
        def mutate(d):
            ep = json.loads((d / "ep-changed-world.json").read_text())
            # the "false continuity" route now rereads the whole catalog:
            # the wrong path is no longer cheaper than cold — decorative
            ep["routes"]["resumable_state"] = ["S1", "S2", "S3", "S4", "S5"]
            (d / "ep-changed-world.json").write_text(json.dumps(ep))
        bad = failed(self.tampered(mutate))
        self.assertIn("false_continuity_priced[meridian-changed-world]", bad)

    def test_missing_ignorance_probe_refused(self):
        def mutate(d):
            m = json.loads((d / "manifest.json").read_text())
            m["attestation"]["ignorance_probe"]["engines"] = {}
            (d / "manifest.json").write_text(json.dumps(m))
        bad = failed(self.tampered(mutate))
        self.assertIn("ignorance_probe", bad)

    def test_stray_catalog_tag_refused(self):
        def mutate(d):
            pop = json.loads((d / "population.json").read_text())
            pop["catalog"]["S4"]["surface_tags"] = ["freeze_time_tag"]
            (d / "population.json").write_text(json.dumps(pop))
        bad = failed(self.tampered(mutate))
        self.assertIn("surface_tags_closed", bad)


if __name__ == "__main__":
    unittest.main()
