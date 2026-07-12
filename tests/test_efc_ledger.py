"""Wire tests for §13 ledger replay, §2.3 event order, §10.1 cost recompute.

Mock rows only — replay machinery, never run evidence. The boundary pin:
a check completing after model_action is annotation and an order failure;
a logged cost claim that replay cannot reproduce fails closed.
"""

from __future__ import annotations

import hashlib
import unittest

from harness.efc_ledger import (LedgerContractError, make_row, recompute_cost,
                                replay_fixture_group, replay_ledger,
                                validate_event_row)
from harness.efc_trigger import trigger_result_record

FIXTURE = {
    "task_id": "fx1",
    "surface_text": "Cite the report and decide the rollout scope.",
    "population_id": "pop-1",
    "assertion_basis_kind": "cited_source",
    "observation_boundary_present": False,
    "source_reference_present": True,
    "decision_scope_present": True,
}
TRIGGER_SHA = hashlib.sha256(trigger_result_record(FIXTURE)).hexdigest()


def group(lane="C_controlled_check", *, silent=False, post_answer=False,
          decision_claim=None, read_tokens=100, out_tokens=64,
          governance=1, forced_mark=False, invert_score=False,
          duplicate_action=False, drop_completed=False):
    rows = [make_row("e1", "activation_evaluated", "fx1", lane, {
        "trigger_result_sha256": TRIGGER_SHA,
        "governance_steps": governance,
        "forced_inactive": forced_mark,
    })]
    if silent:
        rows.append(make_row("e2", "external_check_silent", "fx1", lane))
    else:
        rows.append(make_row("e2", "external_check_started", "fx1", lane))
        if not post_answer and not drop_completed:
            rows.append(make_row("e3", "external_check_completed", "fx1", lane, {
                "controller_source_read_tokens": read_tokens,
                "check_output_tokens": out_tokens,
            }))
    rows.append(make_row("e4", "model_action", "fx1", lane, {
        "model_prompt_tokens": 700, "model_completion_tokens": 150,
    }))
    if duplicate_action:
        rows.append(make_row("e4b", "model_action", "fx1", lane, {
            "model_prompt_tokens": 700, "model_completion_tokens": 150,
        }))
    if post_answer and not silent:
        rows.append(make_row("e3", "external_check_completed", "fx1", lane, {
            "controller_source_read_tokens": read_tokens,
            "check_output_tokens": out_tokens,
        }))
    commit = make_row("e5", "task_commit", "fx1", lane)
    score = make_row("e6", "world_oracle_score", "fx1", lane, {"pass": True})
    rows.extend([score, commit] if invert_score else [commit, score])
    controller_read = 0 if (silent or drop_completed) else read_tokens
    if decision_claim is None:
        decision_claim = 700 + 150 + controller_read
    rows.append(make_row("e7", "cost_recompute", "fx1", lane,
                         {"decision_tokens": decision_claim}))
    return rows


class TestRowClosure(unittest.TestCase):
    def test_unknown_event_type_refused(self):
        with self.assertRaises(LedgerContractError):
            make_row("x1", "model_thought", "fx1", "C_controlled_check")

    def test_group_rows_need_fixture_and_lane(self):
        with self.assertRaises(LedgerContractError):
            make_row("x1", "model_action")

    def test_bad_event_id_refused(self):
        with self.assertRaises(LedgerContractError):
            validate_event_row({"event_id": "spaces are prose",
                                "event_type": "model_action",
                                "fixture_id": "f", "lane": "l", "payload": {}})


class TestGroupReplay(unittest.TestCase):
    def test_healthy_check_group_passes(self):
        replay = replay_fixture_group(group(), fixture=FIXTURE)
        self.assertTrue(replay.ok, msg=str(replay.failures))
        self.assertEqual(replay.cost.decision_tokens, 950)
        self.assertEqual(replay.cost.check_invocations, 1)
        self.assertFalse(replay.post_answer_annotation)

    def test_healthy_silent_group_passes(self):
        replay = replay_fixture_group(group(silent=True), fixture=FIXTURE)
        self.assertTrue(replay.ok, msg=str(replay.failures))
        self.assertEqual(replay.cost.decision_tokens, 850)
        self.assertEqual(replay.cost.check_invocations, 0)

    def test_post_answer_completion_is_annotation_and_failure(self):
        replay = replay_fixture_group(group(post_answer=True), fixture=FIXTURE)
        self.assertFalse(replay.ok)
        self.assertTrue(replay.post_answer_annotation)
        self.assertTrue(any("win path" in f for f in replay.failures))

    def test_started_without_completed_is_hole(self):
        replay = replay_fixture_group(group(drop_completed=True,
                                            decision_claim=850))
        self.assertFalse(replay.ok)
        self.assertTrue(any("never completed" in f for f in replay.failures))

    def test_score_order_inversion_fails(self):
        replay = replay_fixture_group(group(invert_score=True))
        self.assertFalse(replay.ok)
        self.assertTrue(any("inversion" in f for f in replay.failures))

    def test_duplicate_model_action_fails(self):
        replay = replay_fixture_group(group(duplicate_action=True))
        self.assertFalse(replay.ok)
        self.assertTrue(any("duplicate model_action" in f
                            for f in replay.failures))

    def test_cost_claim_mismatch_fails_closed(self):
        replay = replay_fixture_group(group(decision_claim=123))
        self.assertFalse(replay.ok)
        self.assertFalse(replay.cost.matches_logged_claim)
        self.assertTrue(any("untrusted" in f for f in replay.failures))

    def test_trigger_recompute_mismatch_fails(self):
        mutated = dict(FIXTURE, observation_boundary_present=True)
        replay = replay_fixture_group(group(), fixture=mutated)
        self.assertFalse(replay.ok)
        self.assertTrue(any("recompute mismatch" in f for f in replay.failures))

    def test_ceilings_surface_as_violations(self):
        replay = replay_fixture_group(
            group(read_tokens=600, out_tokens=300, governance=3,
                  decision_claim=700 + 150 + 600))
        violations = " ".join(replay.cost.ceiling_violations)
        self.assertIn("controller_source_read_tokens 600", violations)
        self.assertIn("check_output_tokens 300", violations)
        self.assertIn("governance_steps 3", violations)

    def test_b_inactive_contract(self):
        ok_rows = group(lane="B_inactive", silent=True, forced_mark=True)
        replay = replay_fixture_group(ok_rows, fixture=FIXTURE,
                                      forced_inactive=True)
        self.assertTrue(replay.ok, msg=str(replay.failures))
        ran_check = group(lane="B_inactive", forced_mark=True)
        replay = replay_fixture_group(ran_check, forced_inactive=True)
        self.assertFalse(replay.ok)
        unmarked = group(lane="B_inactive", silent=True, forced_mark=False)
        replay = replay_fixture_group(unmarked, forced_inactive=True)
        self.assertFalse(replay.ok)
        self.assertTrue(any("forced_inactive" in f for f in replay.failures))


class TestLedgerReplay(unittest.TestCase):
    def _preamble(self):
        return [
            make_row("r1", "run_config", payload={"engine": "mock"}),
            make_row("r2", "contract_precommit",
                     payload={"part_i_spec_hash": "a" * 64}),
        ]

    def test_healthy_ledger(self):
        rows = self._preamble() + group()
        result = replay_ledger(rows, fixtures={"fx1": FIXTURE},
                               expected_contract_hashes={
                                   "part_i_spec_hash": "a" * 64})
        self.assertTrue(result.ok, msg=str(result.failures))
        self.assertEqual(len(result.groups), 1)

    def test_duplicate_event_identity_fails(self):
        rows = self._preamble() + group()
        rows.append(make_row("e1", "untrusted_nomination",
                             payload={"claim": "x"}))
        result = replay_ledger(rows)
        self.assertFalse(result.ok)
        self.assertTrue(any("duplicate event identity" in f
                            for f in result.failures))

    def test_precommit_after_rows_fails(self):
        rows = group() + self._preamble()
        result = replay_ledger(rows)
        self.assertFalse(result.ok)
        self.assertTrue(any("precommit precedes rows" in f
                            for f in result.failures))

    def test_contract_hash_mismatch_fails(self):
        rows = self._preamble() + group()
        result = replay_ledger(rows, expected_contract_hashes={
            "part_i_spec_hash": "f" * 64})
        self.assertFalse(result.ok)

    def test_missing_preamble_is_hole(self):
        result = replay_ledger(group())
        self.assertFalse(result.ok)
        self.assertTrue(any("no run_config" in f for f in result.failures))


if __name__ == "__main__":
    unittest.main()
