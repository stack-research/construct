"""Disk-backed walking skeleton for the NEXT substrate body.

This is deliberately not a harness instrument and not a product schema. It
demonstrates composition across invocation seams using authored deterministic
behavior. Every row is marked ``wire_integration_only``; no output licenses a
memory claim.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .core import (
    BodyViews,
    EVIDENCE_CLASS as CORE_EVIDENCE_CLASS,
    LineageStore,
    Writer,
)

EVIDENCE_CLASS = CORE_EVIDENCE_CLASS
LICENSE_STATUS = "stubbed_not_earned"
TEMPLATE_ID = "epistemic_frame_check_v0_stub"
CHECK_ID = "fetch_provenance_and_require_scope_match_stub"

RUNTIME_WRITER = Writer("body-runtime-v0", "runtime")
CONTROLLER_WRITER = Writer("body-controller-v0", "controller")
MODEL_WRITER = Writer("model-port", "model")
OBSERVER_WRITER = Writer("external-observer-stub", "observer")
PROVENANCE_WRITER = Writer("external-provenance-sweep-stub", "observer")


@dataclass(frozen=True)
class Environment:
    model_id: str = "deterministic-model-stub"
    renderer_id: str = "body-sketch-v0"
    tool_contract_id: str = "provenance-check-stub-v0"
    decoding_id: str = "deterministic"
    controller_id: str = "body-controller-v0"


@dataclass(frozen=True)
class Task:
    task_id: str
    domain: str
    assertion_kind: str
    observation_boundary: str
    source_scope: str
    required_scope: str
    expected_action: str


@dataclass
class DispositionState:
    disposition_id: str
    template_id: str
    status: str
    validity_envelope: dict[str, str]
    warrant_event_ids: list[str]
    metabolic_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class BodyState:
    dispositions: dict[str, DispositionState] = field(default_factory=dict)


@dataclass(frozen=True)
class WakeResult:
    task_id: str
    action: str
    score: float
    fired_disposition_ids: tuple[str, ...]
    check_evidence: tuple[dict[str, Any], ...]
    consequence_event_id: str


class ModelPort(Protocol):
    def act(self, task: Task, check_evidence: list[dict[str, Any]]) -> str:
        """Return a proposed action. The model cannot write lineage directly."""
        ...


class DeterministicModelStub:
    """Authored behavior used only to make the body executable without a model.

    The stub credulously commits on source assertions unless controller-produced
    evidence shows a scope mismatch. Direct observations are committed.
    """

    def act(self, task: Task, check_evidence: list[dict[str, Any]]) -> str:
        if any(e.get("scope_matches") is False for e in check_evidence):
            return "defer"
        return "commit"


def materialize(views: BodyViews) -> BodyState:
    """Project the mechanism-neutral views into this sketch's disposition port."""
    state = BodyState()
    for item in views.state_items.values():
        if item.item_kind != "disposition":
            continue
        disposition = DispositionState(
            disposition_id=item.item_id,
            template_id=item.detail["template_id"],
            status=item.status,
            validity_envelope=dict(item.detail["validity_envelope"]),
            warrant_event_ids=list(item.warrant_event_ids),
            metabolic_counts=dict(views.metabolic_totals.get(item.item_id, {})),
        )
        state.dispositions[disposition.disposition_id] = disposition
    return state


def _validity_matches(disposition: DispositionState, environment: Environment) -> bool:
    return disposition.validity_envelope == asdict(environment)


def _trigger_matches(task: Task) -> bool:
    return (
        task.assertion_kind == "source_assertion"
        and task.observation_boundary == "absent"
    )


def _run_check(task: Task) -> dict[str, Any]:
    """Controller-side deterministic check; never disposition autobiography."""
    return {
        "check_id": CHECK_ID,
        "observation_boundary": task.observation_boundary,
        "required_scope": task.required_scope,
        "scope_matches": task.source_scope == task.required_scope,
        "source_scope": task.source_scope,
    }


def _score(task: Task, action: str) -> float:
    return 1.0 if action == task.expected_action else 0.0


class BodyRuntime:
    """Smallest runtime that makes the proposed body traversable end-to-end."""

    def __init__(
        self,
        lineage_path: Path,
        *,
        model: ModelPort | None = None,
        environment: Environment | None = None,
    ):
        self.lineage = LineageStore(lineage_path)
        self.model = model or DeterministicModelStub()
        self.environment = environment or Environment()
        if not self.lineage.replay().rows:
            self.lineage.append(
                "sketch_started",
                writer=RUNTIME_WRITER,
                authority="administration",
                payload={
                    "claim_boundary": (
                        "composition demonstrator only; authored behavior; "
                        "never memory evidence"
                    ),
                    "mechanism_license": LICENSE_STATUS,
                },
            )

    def state(self) -> BodyState:
        return materialize(self.lineage.replay().views)

    def record_materialized_view_claim(self) -> dict[str, Any]:
        """Persist a cache claim that cold replay must independently verify."""
        return self.lineage.append_view_claim(writer=RUNTIME_WRITER)

    def wake(self, task: Task) -> WakeResult:
        """Run one invocation through activation, action boundary, and outcome."""
        invocation = self.lineage.append(
            "invocation_started",
            writer=RUNTIME_WRITER,
            authority="system_record",
            payload={
                "task_id": task.task_id,
                "environment": asdict(self.environment),
            },
        )
        encounter = self.lineage.append(
            "encounter_observed",
            writer=OBSERVER_WRITER,
            authority="external_observation",
            causal_parent_ids=[invocation["event_id"]],
            invocation_id=invocation["event_id"],
            payload={"task": asdict(task)},
        )

        state = self.state()
        activation = self.lineage.append(
            "activation_field_built",
            writer=CONTROLLER_WRITER,
            authority="controller_transition",
            causal_parent_ids=[encounter["event_id"]],
            invocation_id=invocation["event_id"],
            encounter_id=encounter["event_id"],
            payload={
                "offered_memory": [],
                "note": "ordinary offer phase complete; controller checks follow",
            },
        )
        boundary = self.lineage.append(
            "action_boundary_entered",
            writer=CONTROLLER_WRITER,
            authority="controller_transition",
            causal_parent_ids=[activation["event_id"]],
            invocation_id=invocation["event_id"],
            encounter_id=encounter["event_id"],
            payload={"placement": "post_offer_pre_commit"},
        )

        fired: list[str] = []
        evidence: list[dict[str, Any]] = []
        last_control_event_id = boundary["event_id"]
        for disposition in state.dispositions.values():
            if disposition.status != "probationary":
                continue
            if disposition.template_id != TEMPLATE_ID:
                continue
            if not _validity_matches(disposition, self.environment):
                continue
            matched = _trigger_matches(task)
            trigger = self.lineage.append(
                "disposition_trigger_evaluated",
                writer=CONTROLLER_WRITER,
                authority="controller_transition",
                causal_parent_ids=[last_control_event_id],
                warrant_event_ids=disposition.warrant_event_ids,
                invocation_id=invocation["event_id"],
                encounter_id=encounter["event_id"],
                payload={
                    "disposition_id": disposition.disposition_id,
                    "matched": matched,
                },
            )
            last_control_event_id = trigger["event_id"]
            if not matched:
                continue
            fired.append(disposition.disposition_id)
            check_evidence = _run_check(task)
            evidence.append(check_evidence)
            checked = self.lineage.append(
                "controller_check_executed",
                writer=CONTROLLER_WRITER,
                authority="controller_transition",
                causal_parent_ids=[trigger["event_id"]],
                warrant_event_ids=disposition.warrant_event_ids,
                invocation_id=invocation["event_id"],
                encounter_id=encounter["event_id"],
                payload={
                    "disposition_id": disposition.disposition_id,
                    "controller_steps": 1,
                    "evidence": check_evidence,
                },
            )
            last_control_event_id = checked["event_id"]

        action = self.model.act(task, evidence)
        model_action = self.lineage.append(
            "model_action",
            writer=MODEL_WRITER,
            authority="model_proposal",
            causal_parent_ids=[last_control_event_id],
            invocation_id=invocation["event_id"],
            encounter_id=encounter["event_id"],
            payload={"action": action},
        )
        consequence = self.lineage.append(
            "consequence_observed",
            writer=OBSERVER_WRITER,
            authority="external_consequence",
            causal_parent_ids=[model_action["event_id"]],
            invocation_id=invocation["event_id"],
            encounter_id=encounter["event_id"],
            payload={
                "oracle": "deterministic_demo_oracle",
                "score": _score(task, action),
            },
        )
        last_event_id = consequence["event_id"]
        for disposition_id in fired:
            metabolic = self.lineage.append(
                "metabolic_event",
                writer=CONTROLLER_WRITER,
                authority="controller_transition",
                causal_parent_ids=[last_event_id],
                invocation_id=invocation["event_id"],
                encounter_id=encounter["event_id"],
                payload={
                    "item_id": disposition_id,
                    "metric": "check_executed",
                    "units": 1,
                },
            )
            last_event_id = metabolic["event_id"]
        self.lineage.append(
            "invocation_completed",
            writer=RUNTIME_WRITER,
            authority="system_record",
            causal_parent_ids=[last_event_id],
            invocation_id=invocation["event_id"],
            encounter_id=encounter["event_id"],
            payload={"score": consequence["payload"]["score"]},
        )
        return WakeResult(
            task_id=task.task_id,
            action=action,
            score=consequence["payload"]["score"],
            fired_disposition_ids=tuple(fired),
            check_evidence=tuple(evidence),
            consequence_event_id=consequence["event_id"],
        )

    def activate_stub_disposition(
        self,
        *,
        disposition_id: str,
        warrant_event_ids: list[str],
    ) -> dict[str, Any]:
        """External activation under an explicitly unearned mechanism license."""
        rows = {row["event_id"]: row for row in self.lineage.rows()}
        if not warrant_event_ids or any(w not in rows for w in warrant_event_ids):
            raise ValueError("every warrant must resolve in lineage")
        if any(rows[w]["kind"] != "consequence_observed" for w in warrant_event_ids):
            raise ValueError("stub dispositions require consequence warrants")
        if any(
            float(rows[w]["payload"].get("score", 1.0)) >= 1.0
            for w in warrant_event_ids
        ):
            raise ValueError("stub failure dispositions require a scored failure")
        if disposition_id in self.state().dispositions:
            raise ValueError(f"disposition already exists: {disposition_id}")
        return self.lineage.append(
            "state_item_admitted",
            writer=CONTROLLER_WRITER,
            authority="controller_transition",
            causal_parent_ids=warrant_event_ids,
            warrant_event_ids=warrant_event_ids,
            payload={
                "item_id": disposition_id,
                "item_kind": "disposition",
                "status": "probationary",
                "placement": "hot",
                "detail": {
                    "template_id": TEMPLATE_ID,
                    "check_id": CHECK_ID,
                    "license_status": LICENSE_STATUS,
                    "minted_by": CONTROLLER_WRITER.writer_id,
                    "validity_envelope": asdict(self.environment),
                },
            },
        )

    def record_wire_causal_probe(
        self,
        *,
        disposition_id: str,
        task: Task,
        treated: WakeResult,
    ) -> dict[str, Any]:
        """Authored counterfactual for demo visibility, never a scientific fork."""
        counterfactual_action = self.model.act(task, [])
        counterfactual_score = _score(task, counterfactual_action)
        effect = "helped" if treated.score > counterfactual_score else "no_gain"
        row = self.lineage.append(
            "wire_causal_probe",
            writer=CONTROLLER_WRITER,
            authority="wire_diagnostic",
            causal_parent_ids=[treated.consequence_event_id],
            payload={
                "item_id": disposition_id,
                "task_id": task.task_id,
                "treated_score": treated.score,
                "counterfactual_score": counterfactual_score,
                "effect": effect,
                "warning": "authored deterministic probe; not a licensed causal result",
            },
        )
        self.lineage.append(
            "metabolic_event",
            writer=CONTROLLER_WRITER,
            authority="controller_transition",
            causal_parent_ids=[row["event_id"]],
            payload={
                "item_id": disposition_id,
                "metric": effect,
                "units": 1,
            },
        )
        return row

    def revise_warrant(self, *, warrant_event_id: str, reason: str) -> list[str]:
        """External provenance-health sweep: suspend every dependent disposition."""
        rows = {row["event_id"]: row for row in self.lineage.rows()}
        if warrant_event_id not in rows:
            raise ValueError(f"unknown warrant event {warrant_event_id}")
        state_before_revision = self.state()
        self.lineage.append(
            "provenance_revision",
            writer=PROVENANCE_WRITER,
            authority="external_observation",
            causal_parent_ids=[warrant_event_id],
            payload={
                "target_event_id": warrant_event_id,
                "health": "invalid",
                "reason": reason,
            },
        )
        suspended: list[str] = []
        for disposition in state_before_revision.dispositions.values():
            if disposition.status == "suspended":
                continue
            if warrant_event_id not in disposition.warrant_event_ids:
                continue
            suspended.append(disposition.disposition_id)
        return suspended
