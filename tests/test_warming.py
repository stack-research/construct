"""Wire tests for the warming-budget scorer (SPEC_WARMING_BUDGET v0.1).

Mock fixtures only — nothing here is evidence about warmth; the suite proves
the machinery encodes the review blockers by name (§6a derived-certificate
rule, mint closure, silent-leg mandate, chronology, replay, R5 fence)."""

from __future__ import annotations

import hashlib
import json
import unittest

from harness.score_warming import (WarmingScorer, derive_answer_bearing_surfaces,
                                   mint_compact_state, refuse_hand_authored_marks)


def _sha(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()


VOCAB = ["dep-9901-status"]
POP = {
    "kind": "population_precommit", "match_rule_id": "lifecycle_diff",
    "status_vocabulary": VOCAB, "status_vocabulary_hash": _sha(VOCAB),
    "selection_rule_hash": "f" * 64, "unresolved_frontier_enum": ["api_lifecycle"],
    "noise_leg_population": 0.25,
}

T0 = {"ruling": "dep 9901 is deprecated status pending final ruling word " * 3,
      "guide": "general migration guide text " * 20,
      "changelog": "old changelog text " * 10}
T1_MOVED = {**T0, "ruling": "dep 9901 has been revoked effective now " * 3}

CATALOG = {"ruling": {"subject": "dep-9901-status"},
           "guide": {"subject": "migration"},
           "changelog": {"subject": "release-notes"}}


def packet(leg: str) -> dict:
    return {"unit_id": "wb-mock-1", "world_leg": leg, "status_key": "dep-9901-status",
            "route_catalog": CATALOG, "T0_snapshot": T0,
            "T1_snapshot": T1_MOVED if leg == "moved" else T0}


def base_events(leg: str, hint=("ruling",)) -> list[dict]:
    state = mint_compact_state(
        route_catalog_t0=CATALOG, m1_sidecar={"authority": {"guide": 1.1}},
        pause_question_id="q1", unresolved_frontier_tag="api_lifecycle",
        route_hint=list(hint), trigger_key="official_status_changed:dep-9901-status",
        discard_rule="discard if trigger fires and certificate read", population=POP)
    state["kind"] = "compact_resume_state_minted"
    state["frontier_unresolved_attested"] = True
    ev = [dict(POP),
          {"kind": "ignorance_probe", "engine": "mock", "result": "cold"},
          state,
          {"kind": "trigger_precommit", "match_rule_ref": POP["status_vocabulary_hash"],
           "precommit_ts": "2026-07-01T00:00:00Z", "external_stream_ref": "mock://stream",
           "catalog_hash": _sha(sorted(CATALOG)), "pause_artifact_hash": "a" * 64}]
    if leg == "moved":
        ev += [{"kind": "world_move", "external_ts": "2026-07-02T00:00:00Z",
                "subject": "dep-9901-status"},
               {"kind": "t1_catalog_materialized", "surfaces": sorted(CATALOG)},
               {"kind": "trigger_observed", "fired": True}]
    else:
        ev += [{"kind": "t1_catalog_materialized", "surfaces": sorted(CATALOG)},
               {"kind": "trigger_observed", "fired": False}]
    return ev


def reads(branch: str, surfaces: list[str], start: int = 0) -> list[dict]:
    return [{"kind": "surface_read", "branch": branch, "surface_id": s, "order": start + i}
            for i, s in enumerate(surfaces)]


def outcomes(**scores) -> list[dict]:
    return [{"kind": "branch_outcome", "branch": b.replace("_", "+") if b in
             ("B_plus",) else b, "prefix_index": 0, "oracle_score": v}
            for b, v in scores.items()]


class DerivedCertificate(unittest.TestCase):
    """§6a — the Q2 resolution, tested as the pure function it is."""

    def test_moved_leg_diff_gated(self):
        certs, state = derive_answer_bearing_surfaces(
            T0, T1_MOVED, CATALOG, "dep-9901-status", "lifecycle_diff", VOCAB, "moved")
        self.assertEqual(certs, {"ruling"})       # changed AND subject-matched
        self.assertEqual(state, "ok")

    def test_moved_leg_irrelevant_churn_excluded(self):
        t1 = {**T1_MOVED, "changelog": "new unrelated churn " * 10}
        certs, _ = derive_answer_bearing_surfaces(
            T0, t1, CATALOG, "dep-9901-status", "lifecycle_diff", VOCAB, "moved")
        self.assertEqual(certs, {"ruling"})       # churn never enters the set

    def test_silent_leg_stable_certificate(self):
        certs, state = derive_answer_bearing_surfaces(
            T0, T0, CATALOG, "dep-9901-status", "lifecycle_diff", VOCAB, "silent")
        self.assertEqual((certs, state), ({"ruling"}, "ok"))

    def test_degenerate_set_confounded(self):
        certs, state = derive_answer_bearing_surfaces(
            T0, T1_MOVED, CATALOG, "unknown-key", "lifecycle_diff", VOCAB, "moved")
        self.assertEqual((certs, state), (set(), "confounded"))

    def test_unknown_match_rule_refused(self):
        with self.assertRaises(ValueError):
            derive_answer_bearing_surfaces(T0, T1_MOVED, CATALOG, "dep-9901-status",
                                           "current_status_field", VOCAB, "moved")

    def test_hand_authored_marks_refused(self):
        with self.assertRaises(ValueError):
            refuse_hand_authored_marks({"answer_bearing_surface_ids": ["ruling"]})

    def test_rev_time_churn_never_certifies_and_keeps_silent_stable(self):
        # population verification round (unanimous block, reproduced live by
        # composer on draft-ietf-6lo-nd-gaao): rev/time churn must not certify
        # a moved leg, and must not destroy silent-leg stability. The fix is a
        # transition-only certificate projection; rev/time live on a separate
        # certificate_eligible=false meta surface.
        catalog = {
            "status:d1": {"subject": "dep-9901-status", "certificate_eligible": True},
            "meta:d1": {"subject": "dep-9901-status", "certificate_eligible": False},
        }
        t0 = {"status:d1": '{"iesg_states": ["ad-eval"], "name": "d1"}',
              "meta:d1": '{"name": "d1", "rev": "03", "time": "T0"}'}
        t1_churn = {**t0, "meta:d1": '{"name": "d1", "rev": "04", "time": "T1"}'}
        vocab = ["dep-9901-status"]
        moved, m_state = derive_answer_bearing_surfaces(
            t0, t1_churn, catalog, "dep-9901-status", "lifecycle_diff", vocab, "moved")
        self.assertEqual((moved, m_state), (set(), "confounded"))  # churn ≠ movement
        silent, s_state = derive_answer_bearing_surfaces(
            t0, t1_churn, catalog, "dep-9901-status", "lifecycle_diff", vocab, "silent")
        self.assertEqual((silent, s_state), ({"status:d1"}, "ok"))  # stability survives

    def test_certificate_ineligible_prose_never_certifies(self):
        # composer attack B (population round): draft-body revision churn on a
        # certificate_eligible=false surface must not fire a moved certificate
        catalog = {**CATALOG,
                   "draft_body": {"subject": "dep-9901-status",
                                  "certificate_eligible": False}}
        t0 = {**T0, "draft_body": "draft revision one text " * 5}
        t1 = {**T1_MOVED, "draft_body": "draft revision two text " * 5}
        certs, state = derive_answer_bearing_surfaces(
            t0, t1, catalog, "dep-9901-status", "lifecycle_diff", VOCAB, "moved")
        self.assertEqual(certs, {"ruling"})   # body churn excluded; status slice certifies
        self.assertEqual(state, "ok")


class MintClosure(unittest.TestCase):
    """§3 — compaction input closure + genealogy_ok at mint."""

    def test_extra_input_refused(self):
        with self.assertRaises(ValueError):
            mint_compact_state(route_catalog_t0=CATALOG, m1_sidecar={},
                               pause_question_id="q", unresolved_frontier_tag="api_lifecycle",
                               route_hint=[], trigger_key="k", discard_rule="d",
                               population=POP, pause_work_product="the answer was...")

    def test_free_text_frontier_tag_refused(self):
        with self.assertRaises(ValueError):
            mint_compact_state(route_catalog_t0=CATALOG, m1_sidecar={},
                               pause_question_id="q",
                               unresolved_frontier_tag="watch the dep 9901 revocation!",
                               route_hint=[], trigger_key="k", discard_rule="d",
                               population=POP)

    def test_hint_outside_catalog_refused(self):
        with self.assertRaises(ValueError):
            mint_compact_state(route_catalog_t0=CATALOG, m1_sidecar={},
                               pause_question_id="q", unresolved_frontier_tag="api_lifecycle",
                               route_hint=["secret_url"], trigger_key="k",
                               discard_rule="d", population=POP)


class ScorerWire(unittest.TestCase):
    def test_moved_win_all_green(self):
        ev = base_events("moved")
        ev += [{"kind": "route_plan", "branch": "B+",
                "neutral_rank": {"guide": 0, "changelog": 1, "ruling": 2}}]
        ev += reads("B0", ["guide", "changelog", "ruling"])
        ev += reads("B+", ["guide", "ruling"])
        ev += reads("C", ["ruling"])
        ev += reads("C_ablated", ["guide", "ruling"])
        ev += outcomes(B0=1.0, C=1.0) + [
            {"kind": "branch_outcome", "branch": "B+", "prefix_index": 0,
             "oracle_score": 1.0}]
        v = WarmingScorer(packet("moved"), ev).score()
        self.assertTrue(all(v["guards"].values()), v["guards"])
        self.assertEqual(v["cells"]["WB-moved-win"], "pass")
        self.assertEqual(v["cells"]["WB-heir-dominates"], "not_engaged")

    def test_heir_dominates_honest_null(self):
        ev = base_events("moved")
        ev += [{"kind": "route_plan", "branch": "B+",
                "neutral_rank": {"ruling": 0, "guide": 1}}]
        ev += reads("B0", ["guide", "ruling"])
        ev += reads("B+", ["ruling"])          # the heir routes straight to it
        ev += reads("C", ["ruling"])           # C pays state tokens on top
        ev += reads("C_ablated", ["ruling"])
        ev += [{"kind": "branch_outcome", "branch": b, "prefix_index": 0,
                "oracle_score": 1.0} for b in ("B0", "B+", "C")]
        v = WarmingScorer(packet("moved"), ev).score()
        self.assertTrue(all(v["guards"].values()), v["guards"])
        self.assertEqual(v["cells"]["WB-heir-dominates"], "pass")
        self.assertEqual(v["cells"]["WB-moved-win"], "not_engaged")

    def test_silent_leg_mandate_of_read(self):
        ev = base_events("silent")
        ev += reads("B0", ["guide"]) + reads("B+", ["guide"])
        ev += reads("C", ["guide"])            # skips the hinted 'ruling' surface
        ev += [{"kind": "branch_outcome", "branch": b, "prefix_index": 0,
                "oracle_score": 1.0} for b in ("B0", "B+", "C")]
        v = WarmingScorer(packet("silent"), ev).score()
        self.assertFalse(v["guards"]["route_cost_ok"])
        self.assertIn("ruling",
                      v["evidence"]["route_cost_ok"]["hinted_but_skipped_on_silent"])
        self.assertEqual(v["cells"]["all"], "confounded")

    def test_silent_cost_pays_warmth_tax(self):
        ev = base_events("silent")
        ev += reads("B0", ["guide"]) + reads("B+", ["guide"])
        ev += reads("C", ["ruling", "guide"])  # mandated watch read = the tax
        ev += [{"kind": "branch_outcome", "branch": b, "prefix_index": 0,
                "oracle_score": 1.0} for b in ("B0", "B+", "C")]
        v = WarmingScorer(packet("silent"), ev).score()
        self.assertTrue(all(v["guards"].values()), v["guards"])
        self.assertEqual(v["cells"]["WB-silent-cost"], "pass")

    def test_chronology_violation_confounds(self):
        ev = base_events("moved")
        for e in ev:
            if e["kind"] == "world_move":
                e["external_ts"] = "2026-06-30T00:00:00Z"   # world moved BEFORE precommit
        ev += reads("B0", ["ruling"]) + reads("B+", ["ruling"]) + reads("C", ["ruling"])
        ev += reads("C_ablated", ["ruling"])
        ev += [{"kind": "branch_outcome", "branch": b, "prefix_index": 0,
                "oracle_score": 1.0} for b in ("B0", "B+", "C")]
        v = WarmingScorer(packet("moved"), ev).score()
        self.assertFalse(v["guards"]["precommit_precedes_world_move"])
        self.assertEqual(v["cells"]["all"], "confounded")

    def test_replay_mismatch_confounds(self):
        ev = base_events("moved")
        ev += [{"kind": "route_plan", "branch": "B+", "neutral_rank": {"ruling": 0}}]
        ev += reads("B0", ["ruling"]) + reads("B+", ["ruling"])
        ev += [{"kind": "surface_read", "branch": "C", "surface_id": "ruling",
                "order": 0, "tokens": 1}]      # logged cost lies; canonical differs
        ev += reads("C_ablated", ["ruling"])
        ev += [{"kind": "branch_outcome", "branch": b, "prefix_index": 0,
                "oracle_score": 1.0} for b in ("B0", "B+", "C")]
        v = WarmingScorer(packet("moved"), ev).score()
        self.assertFalse(v["guards"]["route_replay_ok"])
        self.assertEqual(v["cells"]["all"], "confounded")

    def test_ablation_lane_mandatory_for_win(self):
        ev = base_events("moved")
        ev += [{"kind": "route_plan", "branch": "B+",
                "neutral_rank": {"guide": 0, "ruling": 1}}]
        ev += reads("B0", ["guide", "ruling"]) + reads("B+", ["guide", "ruling"])
        ev += reads("C", ["ruling"])           # would win — but no C_ablated lane
        ev += [{"kind": "branch_outcome", "branch": b, "prefix_index": 0,
                "oracle_score": 1.0} for b in ("B0", "B+", "C")]
        v = WarmingScorer(packet("moved"), ev).score()
        self.assertFalse(v["guards"]["planner_ablation_ok"])
        self.assertEqual(v["cells"]["all"], "confounded")

    def test_trigger_redefining_match_rule_refused(self):
        ev = base_events("moved")
        for e in ev:
            if e["kind"] == "trigger_precommit":
                e["match_rule"] = {"custom": "rule"}   # defines, not cites
        ev += reads("B0", ["ruling"]) + reads("B+", ["ruling"]) + reads("C", ["ruling"])
        ev += reads("C_ablated", ["ruling"])
        v = WarmingScorer(packet("moved"), ev).score()
        self.assertFalse(v["guards"]["population_precommit_ok"])

    def test_r5_fence_agent_claims_refused(self):
        ev = base_events("moved")
        ev += reads("B0", ["ruling"]) + reads("B+", ["ruling"]) + reads("C", ["ruling"])
        ev += reads("C_ablated", ["ruling"])
        ev += [{"kind": "branch_outcome", "branch": "C", "prefix_index": 0,
                "oracle_score": 1.0, "agent_claimed_hint_used": True}]
        with self.assertRaises(ValueError):
            WarmingScorer(packet("moved"), ev).score()

    def test_hand_authored_marks_in_events_refused(self):
        ev = base_events("moved")
        ev += [{"kind": "fixture_note", "answer_bearing_surface_ids": ["ruling"]}]
        with self.assertRaises(ValueError):
            WarmingScorer(packet("moved"), ev)


if __name__ == "__main__":
    unittest.main(verbosity=2)
