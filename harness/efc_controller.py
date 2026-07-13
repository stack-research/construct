"""Frozen external controller — SPEC_EPISTEMIC_FRAME_CHECK_V0 §2.3/§2.4/§8.2.

The controller replays the contract mechanically: it evaluates the frozen
trigger, runs or withholds the named check, places evidence into the
activation path BEFORE the model produces the task action, and writes the §13
rows in canonical order. It exercises no discretionary interpretation and
accepts no model self-certification (§4). There is no enforcement leg (§2.4):
after evidence is returned, the model still produces the task action.

Lane semantics (§8.2): B is forcibly inactive and ledgered; C checks iff the
frozen trigger fires; A runs the identical named check on every task; G and O
are renderer-side text treatments with no controller check.

Placebo lanes (P_placebo, S2_placebo) insert a PRE-PINNED placebo evidence
object at the matched placement. That is a treatment insertion, not a named
check: no provenance is fetched and no comparison runs, so the controller
must not ledger `external_check_started/completed` for it (B5). The placebo
group takes the silent/control path with a typed treatment payload
(`treatment: pinned_placebo_evidence`, `placebo_sha256`) that untrusting
replay verifies; actual check-invocation count is zero and placebo bytes are
charged only through model prompt tokens (§10.1).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from harness import efc_contracts as c
from harness.efc_check import (CheckEvidence, ProvenanceStore,
                               WireComparisonRule,
                               run_scope_provenance_check)
from harness.efc_ledger import make_row
from harness.efc_renderer import Foreground, render_prompt
from harness.efc_trigger import trigger_result_record

CONTROLLER_ID = "efc_controller_v0"

PLACEBO_TREATMENT = "pinned_placebo_evidence"

# lanes/legs on which the controller itself runs the named check
_CHECKING = {"C_controlled_check": "trigger", "A_always_check": "always",
             "S1_relevant_check": "always"}
# lanes/legs that insert the pre-pinned placebo object (never a named check)
_PLACEBO = {"P_placebo": "trigger", "S2_placebo": "always"}

# canonical §2.3 group order the controller emits (B4 contract component)
_EVENT_ORDER = ("activation_evaluated",
                "external_check_started|external_check_silent",
                "external_check_completed?", "model_action", "task_commit",
                "world_oracle_score", "cost_recompute")


class ControllerContractError(ValueError):
    """Controller input outside the frozen contract. Fail-closed."""


@dataclass(frozen=True)
class EngineResult:
    answer_text: str
    prompt_tokens: int
    completion_tokens: int


@dataclass(frozen=True)
class TaskRun:
    fixture_id: str
    lane: str
    rows: tuple[dict, ...]
    prompt: str
    answer_text: str
    checked: bool                    # a named check actually executed
    placebo_inserted: bool           # pre-pinned placebo treatment applied
    evidence: CheckEvidence | None


def controller_contract_payload() -> dict:
    """Typed controller contract (B4): event order, lane policy, accounting
    rules — the semantics a reviewer must be able to pin by hash."""
    return {
        "controller_id": CONTROLLER_ID,
        "schema_version": "efc_controller_contract_v1",
        "event_order": list(_EVENT_ORDER),
        "lane_check_policy": {
            **_CHECKING,
            **{lane: f"placebo_{mode}" for lane, mode in _PLACEBO.items()},
            "B_inactive": "forced_inactive",
            "S0_no_check": "never",
            "G_generic_caution": "never",
            "O_offer_projection": "never",
        },
        "placebo_semantics": ("pre-pinned evidence insertion at matched "
                              "placement; named check never claimed; zero "
                              "check invocations; bytes charged via prompt "
                              "tokens only"),
        "governance_steps_rule": "1 trigger evaluation + 1 per named-check "
                                 "dispatch",
        "decision_tokens_rule": "model_prompt + model_completion + "
                                "controller_source_read (never double-counted)",
        # resolution G: one structural insertion point for evidence-shaped
        # treatments (render_evidence_block)
        "placebo_position_gate": "structural_single_insertion_point",
        "enforcement_leg": "none (§2.4)",
    }


def controller_contract_hash() -> str:
    return hashlib.sha256(json.dumps(controller_contract_payload(),
                                     sort_keys=True, separators=(",", ":")
                                     ).encode("utf-8")).hexdigest()


def run_task(fixture: dict, lane: str, foreground: Foreground,
             engine_call, oracle_score, store: ProvenanceStore | None = None,
             wire_rule: WireComparisonRule | None = None,
             placebo_evidence_text: str | None = None,
             event_namespace: str = "") -> TaskRun:
    """Run one fixture × lane/leg group under the frozen contract.

    `engine_call(prompt) -> EngineResult` is the injected engine session — in
    this workspace only mock/wire engines. `oracle_score(fixture, answer_text)
    -> dict` is the injected external oracle payload (never computed from the
    model's claims). The returned rows are the group's §13 ledger rows in
    canonical order.
    """
    if lane not in c.LANES and lane not in c.SOURCE_LEGS:
        raise ControllerContractError(f"unknown lane/leg {lane!r}")
    if foreground.fixture_id != str(fixture.get("task_id")):
        raise ControllerContractError(
            "foreground/fixture identity mismatch: foregrounds are built once "
            "per fixture identity and shared across lanes (§13)")

    def _id(event_type: str) -> str:
        # `event_namespace` (e.g. "t07.") keeps a conditional-pass ledger's
        # event identities disjoint from the primary pass (§10.2; item E)
        return f"{event_namespace}{foreground.fixture_id}.{lane}.{event_type}"

    rows: list[dict] = []
    fires = foreground.trigger_fires
    forced_inactive = lane == "B_inactive"
    checks = (not forced_inactive and lane in _CHECKING
              and (_CHECKING[lane] == "always" or fires))
    placebo = (not forced_inactive and lane in _PLACEBO
               and (_PLACEBO[lane] == "always" or fires))

    rows.append(make_row(_id("activation_evaluated"), "activation_evaluated",
                         foreground.fixture_id, lane, {
        "trigger_result_sha256": hashlib.sha256(
            trigger_result_record(fixture)).hexdigest(),
        "trigger_fires": fires,
        "forced_inactive": forced_inactive,
        # trigger evaluation, plus the single named-check dispatch when one
        # actually runs; placebo insertion dispatches nothing
        "governance_steps": 1 + int(checks),
    }))

    evidence: CheckEvidence | None = None
    evidence_text: str | None = None
    if checks:
        if store is None or wire_rule is None:
            raise ControllerContractError(
                f"{lane} requires a provenance store and the injected "
                f"comparison-rule executor for {c.CHECK_ID}")
        rows.append(make_row(_id("external_check_started"),
                             "external_check_started",
                             foreground.fixture_id, lane, {}))
        evidence = run_scope_provenance_check(
            store, str(fixture["source_reference"]),
            str(fixture["decision_scope"]), wire_rule)
        evidence_text = evidence.rendered()
        rows.append(make_row(_id("external_check_completed"),
                             "external_check_completed",
                             foreground.fixture_id, lane, {
            "check_id": c.CHECK_ID,
            "comparison_rule_id": evidence.comparison_rule_id,
            "controller_source_read_tokens":
                evidence.controller_source_read_tokens,
            "check_output_tokens": evidence.check_output_tokens,
        }))
    elif placebo:
        # B5: a treatment insertion, honestly ledgered on the silent path —
        # the named check did NOT execute and may not be claimed.
        if placebo_evidence_text is None:
            raise ControllerContractError(
                f"{lane} requires the packet's placebo evidence object")
        evidence_text = placebo_evidence_text
        rows.append(make_row(_id("external_check_silent"),
                             "external_check_silent",
                             foreground.fixture_id, lane, {
            "reason": "placebo_treatment",
            "treatment": PLACEBO_TREATMENT,
            "placebo_sha256": hashlib.sha256(
                placebo_evidence_text.encode("utf-8")).hexdigest(),
        }))
    else:
        rows.append(make_row(_id("external_check_silent"),
                             "external_check_silent",
                             foreground.fixture_id, lane, {
            "reason": ("forced_inactive" if forced_inactive
                       else "trigger_silent" if lane in (*_CHECKING, *_PLACEBO)
                       else "lane_has_no_controller_check"),
        }))

    prompt = render_prompt(foreground, lane, evidence_text)
    result = engine_call(prompt)
    if not isinstance(result, EngineResult):
        raise ControllerContractError("engine_call must return an EngineResult")
    rows.append(make_row(_id("model_action"), "model_action",
                         foreground.fixture_id, lane, {
        "answer_sha256": hashlib.sha256(
            result.answer_text.encode("utf-8")).hexdigest(),
        "model_prompt_tokens": result.prompt_tokens,
        "model_completion_tokens": result.completion_tokens,
    }))
    rows.append(make_row(_id("task_commit"), "task_commit",
                         foreground.fixture_id, lane, {}))
    rows.append(make_row(_id("world_oracle_score"), "world_oracle_score",
                         foreground.fixture_id, lane,
                         dict(oracle_score(fixture, result.answer_text))))
    # §10.1: placebo bytes reach cost only through model prompt tokens
    decision_tokens = (result.prompt_tokens + result.completion_tokens
                       + (evidence.controller_source_read_tokens
                          if evidence is not None else 0))
    rows.append(make_row(_id("cost_recompute"), "cost_recompute",
                         foreground.fixture_id, lane,
                         {"decision_tokens": decision_tokens}))
    return TaskRun(foreground.fixture_id, lane, tuple(rows), prompt,
                   result.answer_text, checks, placebo, evidence)
