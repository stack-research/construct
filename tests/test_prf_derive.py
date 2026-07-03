"""Wire tests for D2 `derive_live_obligations` (SPEC_PAUSE_RESUME v0.1 §5).

Mock fixtures only. Proves: content-addressed reproducibility (same reads +
same rulebook -> same ids), replay as the authority, strict input closure,
rulebooked-only mode, verdict-code refusal at rulebook admission, and the
pre-seam/read-manifest discipline."""

from __future__ import annotations

import unittest

from harness.derive_live_obligations import (DerivationRefused,
                                             derive_live_obligations,
                                             replay_ok, validate_rulebook)
from tests import prf_mock as M


class TestDerivation(unittest.TestCase):
    def setUp(self):
        self.pop = M.population()
        self.manifest = M.freeze_manifest()
        self.reads = M.witness_reads()

    def derive(self, **kw):
        return derive_live_obligations(self.pop, self.manifest, self.reads,
                                       "seam-1", **kw)

    def test_rules_fire_on_witnessed_tags_only(self):
        out = self.derive()
        by_rule = {o["rule_id"] for o in out["obligations"]}
        self.assertEqual(by_rule, {"R1", "R2", "R3"})
        r1 = next(o for o in out["obligations"] if o["rule_id"] == "R1")
        # fired on S1+S5 (status_bearing, witnessed), never S2/S4 (unread)
        self.assertEqual(r1["source_read_ids"], ["S1", "S5"])
        self.assertEqual(r1["status_at_freeze"], "pending")

    def test_content_addressed_reproducible(self):
        a = self.derive()
        b = self.derive()
        self.assertEqual(a["batch"]["obligation_set_hash"],
                         b["batch"]["obligation_set_hash"])
        self.assertEqual([o["obligation_id"] for o in a["obligations"]],
                         [o["obligation_id"] for o in b["obligations"]])

    def test_different_reads_different_ids(self):
        narrower = derive_live_obligations(
            self.pop, self.manifest, M.witness_reads(("S1",)), "seam-1")
        full = self.derive()
        self.assertNotEqual(narrower["batch"]["obligation_set_hash"],
                            full["batch"]["obligation_set_hash"])

    def test_replay_is_authority(self):
        out = self.derive()
        self.assertTrue(replay_ok(self.pop, self.manifest, self.reads,
                                  "seam-1", out["batch"]))
        forged = dict(out["batch"], obligation_set_hash="0" * 64)
        self.assertFalse(replay_ok(self.pop, self.manifest, self.reads,
                                   "seam-1", forged))

    def test_input_closure_refuses_extras(self):
        with self.assertRaises(DerivationRefused) as cm:
            self.derive(pause_work_product="the answer is R")
        self.assertEqual(cm.exception.row["check"], "derivation_input_closure")

    def test_rulebooked_only(self):
        self.pop["derivation_mode"] = "hint_only"
        with self.assertRaises(DerivationRefused) as cm:
            self.derive()
        self.assertEqual(cm.exception.row["check"], "derivation_mode")

    def test_post_seam_read_refused(self):
        rows = M.witness_reads()
        rows[0] = dict(rows[0], catalog_epoch="t1")
        with self.assertRaises(DerivationRefused) as cm:
            derive_live_obligations(self.pop, self.manifest, rows, "seam-1")
        self.assertEqual(cm.exception.row["check"], "pre_seam_only")

    def test_tampered_read_hash_refused(self):
        rows = M.witness_reads()
        rows[0] = dict(rows[0], content_hash="f" * 64)
        with self.assertRaises(DerivationRefused) as cm:
            derive_live_obligations(self.pop, self.manifest, rows, "seam-1")
        self.assertEqual(cm.exception.row["check"], "read_manifest_match")

    def test_unpinned_rulebook_refused(self):
        self.pop["obligation_rulebook_hash"] = "0" * 64
        with self.assertRaises(DerivationRefused) as cm:
            self.derive()
        self.assertEqual(cm.exception.row["check"], "rulebook_pinned")


class TestRulebookAdmission(unittest.TestCase):
    def test_verdict_code_refused(self):
        # superseded_by_surface is a defeat claim fixed at freeze — out (§4a)
        bad = [dict(M.RULEBOOK[0], rule_id="RX",
                    emits_relation_code="superseded_by_surface")]
        with self.assertRaises(DerivationRefused) as cm:
            validate_rulebook(bad, M.PREDICATE_LIBRARY, M.RELATION_CODE_CLASSES)
        self.assertEqual(cm.exception.row["check"], "relation_code_class")

    def test_evaluation_code_refused(self):
        bad = [dict(M.RULEBOOK[0], rule_id="RX",
                    emits_relation_code="factually_refuted")]
        with self.assertRaises(DerivationRefused):
            validate_rulebook(bad, M.PREDICATE_LIBRARY, M.RELATION_CODE_CLASSES)

    def test_unpinned_predicate_refused(self):
        bad = [dict(M.RULEBOOK[0], trigger_predicate_id="P_ghost")]
        with self.assertRaises(DerivationRefused) as cm:
            validate_rulebook(bad, M.PREDICATE_LIBRARY, M.RELATION_CODE_CLASSES)
        self.assertEqual(cm.exception.row["check"], "predicate_closure")

    def test_extra_rule_key_refused(self):
        bad = [dict(M.RULEBOOK[0], rationale="R is probably right")]
        with self.assertRaises(DerivationRefused) as cm:
            validate_rulebook(bad, M.PREDICATE_LIBRARY, M.RELATION_CODE_CLASSES)
        self.assertEqual(cm.exception.row["check"], "rulebook_shape")


if __name__ == "__main__":
    unittest.main()
