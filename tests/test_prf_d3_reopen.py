"""Wire tests for D3 — the reopen warmth tax and the three regions
(SPEC_PAUSE_RESUME v0.1 §7/§8). Mock event streams, never evidence.

The arithmetic under test (glm's round-1 catch, closed by the §4c floor):
  wins  — A + P + R < C at the quality floor (obligation-targeted reread)
  null  — honest reopen that does not pay for its stale carry (A + P + R >= C)
  loses — false continuity on a cheaper path / reflexive reopen (§4c-3)
`frontier_stale_reopen` forgives wrong continuity; it does not forgive the
cost of having carried stale warmth — A is charged on EVERY resume."""

from __future__ import annotations

import unittest

from harness.derive_live_obligations import derive_live_obligations
from harness.mint_frontier_state import (freeze_validate, manifest_hash,
                                         offer_gate)
from harness.score_prf import PRFScorer, _tokens
from tests import prf_mock as M
from tests.test_prf_mint import golden_state


def build_events(t1_texts, resumable_route, cold_route=("S1", "S2", "S3"),
                 reopen=None, quality=None):
    """Assemble a fork group's event stream: witness t0 reads, derivation,
    freeze, two-phase mint, post-seam branch reads, world-oracle outcomes."""
    pop = M.population()
    manifest = M.freeze_manifest()
    reads = M.witness_reads()
    out = derive_live_obligations(pop, manifest, reads, "seam-1")
    cand = freeze_validate(golden_state(out), manifest, out["batch"],
                           manifest_hash(manifest))
    minted = offer_gate(cand, derived_obligation_tokens=120,
                        cold_reread_tokens=400, gamma=pop["gamma"],
                        witness_adequate_without_obligation_surfaces=False,
                        frontier_artifact_id="fa-1")
    events = list(reads) + [out["batch"]] + out["obligations"]
    events.append({"kind": "frontier_freeze",
                   "canonical_state": cand["canonical_state"],
                   "state_digest": cand["state_digest"],
                   "obligation_set_hash": cand["obligation_set_hash"]})
    events.append(minted)
    for i, sid in enumerate(cold_route):
        events.append({"kind": "surface_read", "branch": "cold_reread",
                       "surface_id": sid, "read_index": i,
                       "catalog_epoch": "t1"})
    for i, sid in enumerate(resumable_route):
        events.append({"kind": "surface_read", "branch": "resumable_state",
                       "surface_id": sid, "read_index": i,
                       "catalog_epoch": "t1"})
    if reopen is not None:
        events.append({"kind": "frontier_stale_reopen",
                       "branch": "resumable_state",
                       "population_reopen_rules_hash":
                           pop["population_reopen_rules_hash"], **reopen})
    quality = quality or {"cold_reread": True, "resumable_state": True}
    for branch, ok in quality.items():
        events.append({"kind": "branch_outcome", "branch": branch,
                       "quality_ok": ok})
    scorer = PRFScorer(pop, manifest, events, M.SURFACE_TEXT_T0, t1_texts)
    return scorer, minted


def tok(sid, texts):
    return _tokens(texts[sid])


class TestThreeRegions(unittest.TestCase):
    def test_win_targeted_reread_beats_cold_sweep(self):
        # silent world; resumable reads only the obligation surfaces
        scorer, _ = build_events(M.SURFACE_TEXT_T1_SILENT,
                                 resumable_route=("S1", "S3"))
        v = scorer.score()
        self.assertEqual(v["cell"], "PRF-frontier-win")
        t1 = M.SURFACE_TEXT_T1_SILENT
        expected_c = tok("S1", t1) + tok("S2", t1) + tok("S3", t1)
        self.assertEqual(v["costs"]["C"], expected_c)
        self.assertLess(v["costs"]["resumable_total"], expected_c)
        self.assertGreater(v["costs"]["A"], 0)   # the artifact is never free

    def test_null_heir_dominates_when_reads_match_cold(self):
        # resumable reads the same sweep as cold: A makes it strictly worse,
        # and the read-set identity is the reconstruction-illusion shape
        scorer, _ = build_events(M.SURFACE_TEXT_T1_SILENT,
                                 resumable_route=("S1", "S2", "S3"))
        v = scorer.score()
        self.assertEqual(v["cell"], "PRF-heir-dominates")
        self.assertGreaterEqual(v["costs"]["resumable_total"], v["costs"]["C"])

    def test_null_honest_immediate_reopen_pays_the_carry(self):
        # moved world; resumable reads S1 (discard fires), honestly reopens,
        # then rereads the remaining sweep — A + P + R >= C, provably null
        scorer, _ = build_events(
            M.SURFACE_TEXT_T1_MOVED,
            resumable_route=("S1", "S2", "S3"),
            reopen={"reopen_rule_id": "RR1", "reopen_reason": "changed_world",
                    "invalidating_surface_ids": ["S1"],
                    "read_index_at_reopen": 1})
        v = scorer.score()
        self.assertEqual(v["cell"], "PRF-reopen-null")
        self.assertTrue(v["guards"]["reopen_ok"])
        self.assertGreaterEqual(v["costs"]["resumable_total"], v["costs"]["C"])

    def test_win_reopen_with_targeted_reread(self):
        # moved world; reopen then reread ONLY the derived obligations
        scorer, _ = build_events(
            M.SURFACE_TEXT_T1_MOVED,
            resumable_route=("S1", "S3"),
            reopen={"reopen_rule_id": "RR1", "reopen_reason": "changed_world",
                    "invalidating_surface_ids": ["S1"],
                    "read_index_at_reopen": 1})
        v = scorer.score()
        self.assertEqual(v["cell"], "PRF-reopen-win")
        self.assertLess(v["costs"]["resumable_total"], v["costs"]["C"])

    def test_lose_false_continuity_is_priced(self):
        # moved world; resumable trusts the stale artifact, skips the status
        # surface, answers wrong on a cheaper path
        scorer, _ = build_events(
            M.SURFACE_TEXT_T1_MOVED,
            resumable_route=("S5",),
            quality={"cold_reread": True, "resumable_state": False})
        v = scorer.score()
        self.assertEqual(v["cell"], "PRF-changed-world")
        self.assertFalse(v["guards"]["quality_floor_holds"])
        self.assertIn("cheaper than cold", " ".join(v["evidence"]))

    def test_lose_stale_frontier_distinct_invalidator(self):
        # stale world: the GATE surface moved (option topology), not the
        # status key — the distinct invalidation path (§8)
        scorer, _ = build_events(
            M.SURFACE_TEXT_T1_STALE,
            resumable_route=("S3", "S5"),
            quality={"cold_reread": True, "resumable_state": False})
        v = scorer.score()
        self.assertEqual(v["cell"], "PRF-stale-frontier")

    def test_reflexive_reopen_unjustified(self):
        # §4c-3 engagement leg: reopen citing a surface never read before the
        # reopen row is refused; the branch falls to the priced-lose path
        scorer, _ = build_events(
            M.SURFACE_TEXT_T1_MOVED,
            resumable_route=("S5",),
            reopen={"reopen_rule_id": "RR1", "reopen_reason": "changed_world",
                    "invalidating_surface_ids": ["S1"],
                    "read_index_at_reopen": 0},
            quality={"cold_reread": True, "resumable_state": False})
        v = scorer.score()
        self.assertFalse(v["guards"]["reopen_ok"])
        self.assertIn("reopen_unjustified",
                      " ".join(scorer.evidence))
        self.assertIn(v["cell"], ("PRF-changed-world", "PRF-stale-frontier"))

    def test_reopen_predicate_false_is_unjustified(self):
        # silent world: nothing moved, so a reopen citing S1 cannot justify
        scorer, _ = build_events(
            M.SURFACE_TEXT_T1_SILENT,
            resumable_route=("S1", "S2", "S3"),
            reopen={"reopen_rule_id": "RR1", "reopen_reason": "changed_world",
                    "invalidating_surface_ids": ["S1"],
                    "read_index_at_reopen": 1})
        v = scorer.score()
        self.assertFalse(v["guards"]["reopen_ok"])

    def test_unpinned_reopen_rule_unreplayable(self):
        scorer, _ = build_events(
            M.SURFACE_TEXT_T1_MOVED,
            resumable_route=("S1", "S2", "S3"),
            reopen={"reopen_rule_id": "RR-ghost",
                    "reopen_reason": "changed_world",
                    "invalidating_surface_ids": ["S1"],
                    "read_index_at_reopen": 1})
        scorer.score()
        self.assertIn("reopen_unreplayable", " ".join(scorer.evidence))

    def test_route_replay_mismatch_confounds(self):
        scorer, _ = build_events(M.SURFACE_TEXT_T1_SILENT,
                                 resumable_route=("S1", "S3"))
        for r in scorer.events:
            if r.get("kind") == "surface_read" and \
                    r.get("branch") == "resumable_state":
                r["route_read_tokens"] = 1   # narrated cost, wrong
        v = scorer.score()
        self.assertEqual(v["cell"], "confounded")
        self.assertFalse(v["guards"]["route_replay_ok"])

    def test_forged_derivation_confounds(self):
        scorer, _ = build_events(M.SURFACE_TEXT_T1_SILENT,
                                 resumable_route=("S1", "S3"))
        for r in scorer.events:
            if r.get("kind") == "obligation_derivation_batch":
                r["obligation_set_hash"] = "0" * 64
        v = scorer.score()
        self.assertEqual(v["cell"], "confounded")
        self.assertFalse(v["guards"]["derivation_replay_ok"])


if __name__ == "__main__":
    unittest.main()
