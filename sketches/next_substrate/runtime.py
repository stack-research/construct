"""Disk-backed walking skeleton for the NEXT substrate body.

This is deliberately not a harness instrument and not a product schema. It
demonstrates composition across invocation seams using authored deterministic
behavior. Every row is marked ``wire_integration_only``; no output licenses a
memory claim.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol


EVIDENCE_CLASS = "wire_integration_only"
LICENSE_STATUS = "stubbed_not_earned"
TEMPLATE_ID = "epistemic_frame_check_v0_stub"
CHECK_ID = "fetch_provenance_and_require_scope_match_stub"


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


class LineageStore:
    """Minimal append-only JSONL store with deterministic event ordering."""

    _RESERVED = frozenset({"event_id", "event_index", "kind", "evidence_class"})

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text().splitlines()
            if line.strip()
        ]

    def append(self, kind: str, **payload: Any) -> dict[str, Any]:
        overlap = self._RESERVED.intersection(payload)
        if overlap:
            raise ValueError(f"reserved lineage fields: {sorted(overlap)}")
        rows = self.rows()
        event_index = rows[-1]["event_index"] + 1 if rows else 1
        row = {
            "event_id": f"ev-{event_index:04d}",
            "event_index": event_index,
            "kind": kind,
            "evidence_class": EVIDENCE_CLASS,
            **payload,
        }
        with self.path.open("a") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
        return row


def materialize(rows: list[dict[str, Any]]) -> BodyState:
    """Rebuild the governed cognitive materialization from lineage."""
    state = BodyState()
    for row in rows:
        kind = row.get("kind")
        if kind == "disposition_instance_activated":
            disposition = DispositionState(
                disposition_id=row["disposition_id"],
                template_id=row["template_id"],
                status=row.get("status", "probationary"),
                validity_envelope=dict(row["validity_envelope"]),
                warrant_event_ids=list(row["warrant_event_ids"]),
            )
            state.dispositions[disposition.disposition_id] = disposition
        elif kind == "metabolic_event":
            disposition = state.dispositions.get(row["disposition_id"])
            if disposition is not None:
                event = row["metabolic_kind"]
                disposition.metabolic_counts[event] = (
                    disposition.metabolic_counts.get(event, 0) + 1
                )
        elif kind == "provenance_revision":
            target = row["target_event_id"]
            for disposition in state.dispositions.values():
                if target in disposition.warrant_event_ids:
                    disposition.status = "suspended"
        elif kind == "disposition_suspended":
            disposition = state.dispositions.get(row["disposition_id"])
            if disposition is not None:
                disposition.status = "suspended"
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
        if not self.lineage.rows():
            self.lineage.append(
                "sketch_started",
                claim_boundary=(
                    "composition demonstrator only; authored behavior; "
                    "never memory evidence"
                ),
                mechanism_license=LICENSE_STATUS,
            )

    def state(self) -> BodyState:
        return materialize(self.lineage.rows())

    def wake(self, task: Task) -> WakeResult:
        """Run one invocation through activation, action boundary, and outcome."""
        invocation = self.lineage.append(
            "invocation_started",
            task_id=task.task_id,
            environment=asdict(self.environment),
        )
        self.lineage.append(
            "encounter_observed",
            invocation_id=invocation["event_id"],
            task=asdict(task),
        )

        state = self.state()
        self.lineage.append(
            "activation_field_built",
            invocation_id=invocation["event_id"],
            offered_memory=[],
            note="ordinary offer phase complete; controller checks follow",
        )
        self.lineage.append(
            "action_boundary_entered",
            invocation_id=invocation["event_id"],
            placement="post_offer_pre_commit",
        )

        fired: list[str] = []
        evidence: list[dict[str, Any]] = []
        for disposition in state.dispositions.values():
            if disposition.status != "probationary":
                continue
            if disposition.template_id != TEMPLATE_ID:
                continue
            if not _validity_matches(disposition, self.environment):
                continue
            matched = _trigger_matches(task)
            self.lineage.append(
                "disposition_trigger_evaluated",
                invocation_id=invocation["event_id"],
                disposition_id=disposition.disposition_id,
                matched=matched,
            )
            if not matched:
                continue
            fired.append(disposition.disposition_id)
            check_evidence = _run_check(task)
            evidence.append(check_evidence)
            self.lineage.append(
                "controller_check_executed",
                invocation_id=invocation["event_id"],
                disposition_id=disposition.disposition_id,
                controller_steps=1,
                evidence=check_evidence,
            )

        action = self.model.act(task, evidence)
        self.lineage.append(
            "model_action",
            invocation_id=invocation["event_id"],
            action=action,
            writer="model_port",
        )
        consequence = self.lineage.append(
            "consequence_observed",
            invocation_id=invocation["event_id"],
            oracle="deterministic_demo_oracle",
            score=_score(task, action),
            writer="external_observer_stub",
        )
        for disposition_id in fired:
            self.lineage.append(
                "metabolic_event",
                disposition_id=disposition_id,
                invocation_id=invocation["event_id"],
                metabolic_kind="check_executed",
                controller_steps=1,
            )
        self.lineage.append(
            "invocation_completed",
            invocation_id=invocation["event_id"],
            score=consequence["score"],
        )
        return WakeResult(
            task_id=task.task_id,
            action=action,
            score=consequence["score"],
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
        if any(float(rows[w].get("score", 1.0)) >= 1.0 for w in warrant_event_ids):
            raise ValueError("stub failure dispositions require a scored failure")
        if disposition_id in self.state().dispositions:
            raise ValueError(f"disposition already exists: {disposition_id}")
        return self.lineage.append(
            "disposition_instance_activated",
            disposition_id=disposition_id,
            template_id=TEMPLATE_ID,
            check_id=CHECK_ID,
            license_status=LICENSE_STATUS,
            minted_by="external_controller_stub",
            status="probationary",
            validity_envelope=asdict(self.environment),
            warrant_event_ids=warrant_event_ids,
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
            disposition_id=disposition_id,
            task_id=task.task_id,
            treated_score=treated.score,
            counterfactual_score=counterfactual_score,
            effect=effect,
            warning="authored deterministic probe; not a licensed causal result",
        )
        self.lineage.append(
            "metabolic_event",
            disposition_id=disposition_id,
            invocation_id=None,
            metabolic_kind=effect,
            controller_steps=0,
            source_event_id=row["event_id"],
        )
        return row

    def revise_warrant(self, *, warrant_event_id: str, reason: str) -> list[str]:
        """External provenance-health sweep: suspend every dependent disposition."""
        rows = {row["event_id"]: row for row in self.lineage.rows()}
        if warrant_event_id not in rows:
            raise ValueError(f"unknown warrant event {warrant_event_id}")
        state_before_revision = self.state()
        revision = self.lineage.append(
            "provenance_revision",
            target_event_id=warrant_event_id,
            reason=reason,
            writer="external_provenance_sweep_stub",
        )
        suspended: list[str] = []
        for disposition in state_before_revision.dispositions.values():
            if disposition.status == "suspended":
                continue
            if warrant_event_id not in disposition.warrant_event_ids:
                continue
            self.lineage.append(
                "disposition_suspended",
                disposition_id=disposition.disposition_id,
                reason="stale_warrant",
                provenance_revision_id=revision["event_id"],
            )
            suspended.append(disposition.disposition_id)
        return suspended
