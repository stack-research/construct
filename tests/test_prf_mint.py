"""Wire tests for the D1 mint (SPEC_PAUSE_RESUME v0.1 §4) — golden
allowed/refused frontier states (codex's round-2 JSON pairs) + the two-phase
mint discipline from the review-round fix (A+B+C).

Mock fixtures only, never evidence."""

from __future__ import annotations

import unittest

from harness.derive_live_obligations import derive_live_obligations
from harness.mint_frontier_state import (MintRefusal, freeze_validate,
                                         manifest_hash, offer_gate,
                                         recompute_state_tokens)
from tests import prf_mock as M


def setup_batch():
    pop = M.population()
    manifest = M.freeze_manifest()
    out = derive_live_obligations(pop, manifest, M.witness_reads(), "seam-1")
    return pop, manifest, out


def golden_state(batch) -> dict:
    """The allowed shape: skeleton of attention, every relation tuple citing
    its derived obligation."""
    ob = {o["rule_id"]: o for o in batch["obligations"]}
    return {
        "live_options": ["R", "A"],
        "inactive_options": [
            {"option_id": "Q", "relation_code": "reopen_if_catalog_match",
             "surface_id": "S3",
             "derived_from_obligation_id": ob["R2"]["obligation_id"]}],
        "pending_obligations": [
            {"obligation_id": ob["R1"]["obligation_id"], "option_id": "R",
             "relation_code": "pending_evidence",
             "derived_from_obligation_id": ob["R1"]["obligation_id"]}],
        "reopen_rules": [
            {"option_id": "R", "relation_code": "discard_if_world_key_changed",
             "surface_id": "S1",
             "derived_from_obligation_id": ob["R3"]["obligation_id"]}],
        "read_manifest": ["S1", "S3", "S5"],
        "uncertainty": [{"option_id": "A", "uncertainty_code": "unresolved"}],
    }


class TestFreezePhase(unittest.TestCase):
    def setUp(self):
        self.pop, self.manifest, out = setup_batch()
        self.batch, self.obs = out["batch"], out["obligations"]
        self.pin = manifest_hash(self.manifest)

    def validate(self, state):
        return freeze_validate(state, self.manifest, self.batch, self.pin)

    def check_refused(self, state, check, reason=None):
        with self.assertRaises(MintRefusal) as cm:
            self.validate(state)
        self.assertEqual(cm.exception.row["check"], check)
        if reason:
            self.assertEqual(cm.exception.row["reason"], reason)
        return cm.exception.row

    def test_golden_allowed_state_passes_freeze(self):
        cand = self.validate(golden_state({"batch": self.batch,
                                           "obligations": self.obs}))
        self.assertEqual(cand["phase"], "freeze_pass")
        self.assertEqual(cand["obligation_set_hash"],
                         self.batch["obligation_set_hash"])

    def test_freeze_pass_is_not_minted(self):
        cand = self.validate(golden_state({"batch": self.batch,
                                           "obligations": self.obs}))
        self.assertNotEqual(cand.get("kind"), "frontier_state_minted")

    # --- codex's refused goldens ---
    def test_best_option_refused(self):
        s = golden_state({"batch": self.batch, "obligations": self.obs})
        s["best_option"] = "R"
        self.check_refused(s, "field_allowlist", "work_product_field")

    def test_option_rank_refused(self):
        s = golden_state({"batch": self.batch, "obligations": self.obs})
        s["option_rank"] = ["R", "A", "Q"]
        self.check_refused(s, "field_allowlist", "work_product_field")

    def test_confidence_refused(self):
        s = golden_state({"batch": self.batch, "obligations": self.obs})
        s["confidence"] = {"R": 0.72}
        self.check_refused(s, "field_allowlist", "work_product_field")

    def test_draft_answer_refused(self):
        s = golden_state({"batch": self.batch, "obligations": self.obs})
        s["draft_answer"] = "the user should choose R"
        self.check_refused(s, "field_allowlist", "work_product_field")

    def test_prose_token_refused(self):
        s = golden_state({"batch": self.batch, "obligations": self.obs})
        s["uncertainty"] = [{"option_id": "A",
                             "uncertainty_code": "R is probably correct"}]
        self.check_refused(s, "vocab_closure", "work_product_field")

    def test_verdict_relation_code_refused(self):
        s = golden_state({"batch": self.batch, "obligations": self.obs})
        s["inactive_options"][0]["relation_code"] = "superseded_by_surface"
        row = self.check_refused(s, "vocab_closure")
        # superseded_by_surface was dropped from the manifest enum entirely
        self.assertIn("superseded_by_surface", row["detail"])

    def test_numeric_value_refused(self):
        s = golden_state({"batch": self.batch, "obligations": self.obs})
        s["read_manifest"] = ["S1", 3]
        self.check_refused(s, "no_scalar_valuation", "work_product_field")

    def test_free_reason_key_refused(self):
        s = golden_state({"batch": self.batch, "obligations": self.obs})
        s["inactive_options"][0]["reason"] = "S3 defeats Q"
        self.check_refused(s, "gate_relation_shape")

    def test_authored_tuple_without_provenance_refused(self):
        s = golden_state({"batch": self.batch, "obligations": self.obs})
        del s["inactive_options"][0]["derived_from_obligation_id"]
        self.check_refused(s, "gate_relation_shape", "work_product_field")

    def test_foreign_provenance_refused(self):
        s = golden_state({"batch": self.batch, "obligations": self.obs})
        s["inactive_options"][0]["derived_from_obligation_id"] = \
            "obl:sha256:" + "0" * 64
        self.check_refused(s, "vocab_closure", "out_of_vocab_token")

    def test_partition_conflict_refused(self):
        s = golden_state({"batch": self.batch, "obligations": self.obs})
        s["live_options"] = ["R", "Q"]   # Q is also inactive
        self.check_refused(s, "partition_consistency", "work_product_field")

    def test_unknown_surface_refused(self):
        s = golden_state({"batch": self.batch, "obligations": self.obs})
        s["read_manifest"] = ["S1", "S9"]
        self.check_refused(s, "vocab_closure", "out_of_vocab_token")

    def test_input_closure_refused(self):
        with self.assertRaises(MintRefusal) as cm:
            freeze_validate(golden_state({"batch": self.batch,
                                          "obligations": self.obs}),
                            self.manifest, self.batch, self.pin,
                            pause_work_product="notes")
        self.assertEqual(cm.exception.row["check"], "input_closure")

    def test_unpinned_schema_refused(self):
        with self.assertRaises(MintRefusal) as cm:
            freeze_validate(golden_state({"batch": self.batch,
                                          "obligations": self.obs}),
                            self.manifest, self.batch, "0" * 64)
        self.assertEqual(cm.exception.row["check"], "schema_pinned")

    def test_state_content_void_refused_at_freeze(self):
        empty_batch = dict(self.batch, obligation_ids=[])
        with self.assertRaises(MintRefusal) as cm:
            freeze_validate({"live_options": ["R"], "read_manifest": ["S1"]},
                            self.manifest, empty_batch, self.pin)
        self.assertEqual(cm.exception.row["reason"], "state_content_void")

    def test_canonicalization_kills_order(self):
        s1 = golden_state({"batch": self.batch, "obligations": self.obs})
        s2 = golden_state({"batch": self.batch, "obligations": self.obs})
        s2["live_options"] = list(reversed(s2["live_options"]))
        c1, c2 = self.validate(s1), self.validate(s2)
        self.assertEqual(c1["state_digest"], c2["state_digest"])


class TestOfferPhase(unittest.TestCase):
    """§4c two-phase mint: minted row only at offer time; content-floor
    failures are mint refusals with the voted reasons."""

    def setUp(self):
        self.pop, self.manifest, out = setup_batch()
        self.batch, self.obs = out["batch"], out["obligations"]
        self.cand = freeze_validate(
            golden_state({"batch": self.batch, "obligations": self.obs}),
            self.manifest, self.batch, manifest_hash(self.manifest))

    def test_mint_only_after_both_phases(self):
        row = offer_gate(self.cand, derived_obligation_tokens=120,
                         cold_reread_tokens=400, gamma=0.20,
                         witness_adequate_without_obligation_surfaces=False,
                         frontier_artifact_id="fa-1")
        self.assertEqual(row["kind"], "frontier_state_minted")
        self.assertEqual(row["state_digest"], self.cand["state_digest"])

    def test_decorative_obligations_refused_at_offer(self):
        with self.assertRaises(MintRefusal) as cm:
            offer_gate(self.cand, 120, 400, 0.20,
                       witness_adequate_without_obligation_surfaces=True,
                       frontier_artifact_id="fa-1")
        self.assertEqual(cm.exception.row["reason"],
                         "fixture_obligations_decorative")
        self.assertEqual(cm.exception.row["kind"], "frontier_mint_refused")

    def test_sub_gamma_ballast_refused_at_offer(self):
        with self.assertRaises(MintRefusal) as cm:
            offer_gate(self.cand, derived_obligation_tokens=10,
                       cold_reread_tokens=400, gamma=0.20,
                       witness_adequate_without_obligation_surfaces=False,
                       frontier_artifact_id="fa-1")
        self.assertEqual(cm.exception.row["reason"],
                         "obligation_ballast_below_gamma")

    def test_offer_gate_requires_freeze_candidate(self):
        with self.assertRaises(MintRefusal) as cm:
            offer_gate({"state_digest": "x"}, 120, 400, 0.20, False, "fa-1")
        self.assertEqual(cm.exception.row["check"], "two_phase_order")

    def test_artifact_tokens_recompute_matches(self):
        self.assertEqual(recompute_state_tokens(self.cand["canonical_state"]),
                         self.cand["state_tokens"])


if __name__ == "__main__":
    unittest.main()
