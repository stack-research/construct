"""Wire tests: frozen controller — event order, lane semantics, honest
placebo treatment (B5), fail-closed post-answer checks, untrusting replay
(sealed §2.3/§8.2/§13)."""

from __future__ import annotations

import hashlib
import unittest

from harness.efc_controller import (ControllerContractError, EngineResult,
                                    PLACEBO_TREATMENT,
                                    controller_contract_hash,
                                    controller_contract_payload, run_task)
from harness.efc_ledger import make_row, replay_fixture_group
from harness.efc_renderer import build_foreground
from tests.efc_wire_fixtures import (MockSession, fictional_source_ref,
                                     firing_fixture, irrelevant_fixture,
                                     make_store, mock_oracle,
                                     token_cover_rule)

REF = fictional_source_ref(0)
PLACEBO = "fictional placebo evidence about the unrelated whistle registry"
PLACEBO_SHA = hashlib.sha256(PLACEBO.encode("utf-8")).hexdigest()


def _run(fixture, lane, **kw):
    fg = build_foreground(fixture)
    return run_task(fixture, lane, fg, MockSession(), mock_oracle, **kw)


class TestControllerLanes(unittest.TestCase):
    def setUp(self):
        self.store = make_store([REF])
        self.rule = token_cover_rule()
        self.firing = firing_fixture("ct-01", REF, mismatch=True)
        self.silent = irrelevant_fixture("ct-02", REF)
        self.checking = {"store": self.store, "wire_rule": self.rule}

    def _types(self, run):
        return [r["event_type"] for r in run.rows]

    def test_event_order_check_before_action(self):
        run = _run(self.firing, "C_controlled_check", **self.checking)
        self.assertEqual(self._types(run), [
            "activation_evaluated", "external_check_started",
            "external_check_completed", "model_action", "task_commit",
            "world_oracle_score", "cost_recompute"])
        self.assertTrue(run.checked)
        replay = replay_fixture_group(list(run.rows), fixture=self.firing)
        self.assertTrue(replay.ok, msg=str(replay.failures))

    def test_check_completed_after_action_fails_replay(self):
        """Sealed §2.3 / brief item 6: a check completed after model action
        is a post-answer annotation and fails closed."""
        run = _run(self.firing, "C_controlled_check", **self.checking)
        rows = list(run.rows)
        completed = rows.pop(2)          # external_check_completed
        rows.insert(4, completed)        # after model_action + task_commit
        replay = replay_fixture_group(rows, fixture=self.firing)
        self.assertFalse(replay.ok)
        self.assertTrue(replay.post_answer_annotation)

    def test_b_inactive_forced_and_ledgered(self):
        run = _run(self.firing, "B_inactive")
        self.assertFalse(run.checked)
        self.assertIn("external_check_silent", self._types(run))
        activation = run.rows[0]
        self.assertTrue(activation["payload"]["forced_inactive"])
        replay = replay_fixture_group(list(run.rows), fixture=self.firing,
                                      forced_inactive=True)
        self.assertTrue(replay.ok, msg=str(replay.failures))

    def test_c_silent_on_irrelevant(self):
        run = _run(self.silent, "C_controlled_check", **self.checking)
        self.assertFalse(run.checked)
        self.assertIn("external_check_silent", self._types(run))

    def test_a_always_checks_on_irrelevant(self):
        run = _run(self.silent, "A_always_check", **self.checking)
        self.assertTrue(run.checked)

    def test_check_lane_requires_injected_rule(self):
        """B1: the controller cannot check without the injected rule."""
        with self.assertRaises(ControllerContractError):
            _run(self.firing, "C_controlled_check", store=self.store)

    def test_g_and_o_run_no_controller_check(self):
        for lane in ("G_generic_caution", "O_offer_projection"):
            run = _run(self.firing, lane)
            self.assertFalse(run.checked, msg=lane)
            self.assertIn("external_check_silent", self._types(run))

    def test_source_legs(self):
        s1 = _run(self.firing, "S1_relevant_check", **self.checking)
        self.assertTrue(s1.checked)
        s0 = _run(self.firing, "S0_no_check")
        self.assertFalse(s0.checked)

    def test_single_invocation_structural(self):
        run = _run(self.firing, "C_controlled_check", **self.checking)
        starts = [t for t in self._types(run)
                  if t == "external_check_started"]
        self.assertEqual(len(starts), 1)

    def test_foreground_identity_mismatch_refused(self):
        fg = build_foreground(self.silent)
        with self.assertRaises(ControllerContractError):
            run_task(self.firing, "B_inactive", fg, MockSession(), mock_oracle)

    def test_cost_recompute_matches_untrusting_replay(self):
        run = _run(self.firing, "A_always_check", **self.checking)
        replay = replay_fixture_group(list(run.rows), fixture=self.firing)
        self.assertTrue(replay.ok, msg=str(replay.failures))
        self.assertTrue(replay.cost.matches_logged_claim)
        self.assertEqual(replay.cost.ceiling_violations, ())

    def test_contract_hash_changes_on_component_mutation(self):
        """B4: the controller contract hash covers its typed payload."""
        import hashlib as h
        import json
        payload = controller_contract_payload()
        mutated = dict(payload, enforcement_leg="commit_gate")
        digest = h.sha256(json.dumps(mutated, sort_keys=True,
                                     separators=(",", ":")).encode()
                          ).hexdigest()
        self.assertNotEqual(digest, controller_contract_hash())


class TestPlaceboTreatment(unittest.TestCase):
    """B5 repair tests: placebo insertion is a treatment, never a claimed
    named-check invocation."""

    def setUp(self):
        self.firing = firing_fixture("ct-10", REF, mismatch=True)
        self.silent = irrelevant_fixture("ct-11", REF)

    def _types(self, run):
        return [r["event_type"] for r in run.rows]

    def test_placebo_never_claims_the_named_check(self):
        for lane in ("P_placebo", "S2_placebo"):
            run = _run(self.firing, lane, placebo_evidence_text=PLACEBO)
            types = self._types(run)
            self.assertNotIn("external_check_started", types, msg=lane)
            self.assertNotIn("external_check_completed", types, msg=lane)
            self.assertFalse(run.checked, msg=lane)
            self.assertTrue(run.placebo_inserted, msg=lane)
            self.assertIn(PLACEBO, run.prompt, msg=lane)

    def test_placebo_silent_row_is_typed(self):
        run = _run(self.firing, "P_placebo", placebo_evidence_text=PLACEBO)
        silent = next(r for r in run.rows
                      if r["event_type"] == "external_check_silent")
        self.assertEqual(silent["payload"]["reason"], "placebo_treatment")
        self.assertEqual(silent["payload"]["treatment"], PLACEBO_TREATMENT)
        self.assertEqual(silent["payload"]["placebo_sha256"], PLACEBO_SHA)

    def test_replay_distinguishes_check_from_placebo(self):
        """A forged placebo group that ledgers an actual named-check
        invocation fails untrusting replay."""
        run = _run(self.firing, "P_placebo", placebo_evidence_text=PLACEBO)
        replay = replay_fixture_group(list(run.rows), fixture=self.firing,
                                      expected_placebo_sha256=PLACEBO_SHA)
        self.assertTrue(replay.ok, msg=str(replay.failures))
        self.assertEqual(replay.cost.check_invocations, 0)
        forged = [r for r in run.rows
                  if r["event_type"] != "external_check_silent"]
        forged.insert(1, make_row("ct-10.P_placebo.forged_start",
                                  "external_check_started", "ct-10",
                                  "P_placebo"))
        forged.insert(2, make_row("ct-10.P_placebo.forged_done",
                                  "external_check_completed", "ct-10",
                                  "P_placebo", {
                                      "check_id": "scope_provenance_check_v0",
                                      "controller_source_read_tokens": 0,
                                      "check_output_tokens": 10}))
        forged_replay = replay_fixture_group(forged, fixture=self.firing)
        self.assertFalse(forged_replay.ok)
        self.assertTrue(any("claimed an actual named-check" in f
                            for f in forged_replay.failures))

    def test_replay_pins_the_packet_placebo_hash(self):
        run = _run(self.firing, "P_placebo", placebo_evidence_text=PLACEBO)
        replay = replay_fixture_group(list(run.rows), fixture=self.firing,
                                      expected_placebo_sha256="f" * 64)
        self.assertFalse(replay.ok)
        self.assertTrue(any("does not match the packet" in f
                            for f in replay.failures))

    def test_placebo_bytes_charged_via_prompt_tokens_only(self):
        run = _run(self.firing, "P_placebo", placebo_evidence_text=PLACEBO)
        cost_row = next(r for r in run.rows
                        if r["event_type"] == "cost_recompute")
        action = next(r for r in run.rows if r["event_type"] == "model_action")
        self.assertEqual(cost_row["payload"]["decision_tokens"],
                         action["payload"]["model_prompt_tokens"]
                         + action["payload"]["model_completion_tokens"])
        # the placebo bytes are in the prompt (hence in prompt tokens)
        self.assertGreater(action["payload"]["model_prompt_tokens"],
                           len(build_foreground(self.firing).text.split()))

    def test_placebo_governance_steps_count_no_dispatch(self):
        run = _run(self.firing, "P_placebo", placebo_evidence_text=PLACEBO)
        self.assertEqual(run.rows[0]["payload"]["governance_steps"], 1)

    def test_p_lane_trigger_silent_without_placebo(self):
        run = _run(self.silent, "P_placebo", placebo_evidence_text=PLACEBO)
        self.assertFalse(run.placebo_inserted)
        self.assertNotIn(PLACEBO, run.prompt)
        silent = next(r for r in run.rows
                      if r["event_type"] == "external_check_silent")
        self.assertEqual(silent["payload"]["reason"], "trigger_silent")

    def test_placebo_lane_requires_pinned_object(self):
        with self.assertRaises(ControllerContractError):
            _run(self.firing, "P_placebo")
        with self.assertRaises(ControllerContractError):
            _run(self.firing, "S2_placebo")


if __name__ == "__main__":
    unittest.main()
