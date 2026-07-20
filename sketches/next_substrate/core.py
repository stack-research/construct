"""Body Core v0.2: a small integrity kernel plus a provisional policy profile.

This module is provisional runtime engineering, not a harness instrument or a
product schema. Its integrity kernel supplies three deliberately small
facilities:

1. a tamper-evident lineage envelope;
2. fail-closed, untrusting replay;
3. independently recomputable materialized views.

The lifecycle table, binary hot/cold placement, three-value warrant health, and
automatic suspension on invalidation are a provisional policy profile layered
on that kernel. They are useful defaults under test, not mechanism-neutral law.

Every event remains ``wire_integration_only``. Nothing here licenses a memory
mechanism or turns authored behavior into scientific evidence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping


CORE_SCHEMA_VERSION = "body-core-v0.2"
EVIDENCE_CLASS = "wire_integration_only"
GENESIS_HASH = "0" * 64
POLICY_PROFILE_ID = "body-core-v0.2-provisional-policy"

WRITER_AUTHORITIES: dict[str, frozenset[str]] = {
    "runtime": frozenset({"administration", "system_record"}),
    "observer": frozenset({"external_observation", "external_consequence"}),
    "controller": frozenset({"controller_transition", "wire_diagnostic"}),
    "model": frozenset({"model_proposal"}),
}

STATE_TRANSITIONS: dict[str, frozenset[str]] = {
    "probationary": frozenset({"active", "suspended", "retired"}),
    "active": frozenset({"suspended", "retired"}),
    "suspended": frozenset({"probationary", "active", "retired"}),
    "retired": frozenset(),
}


class ReplayRefusal(ValueError):
    """Raised when lineage cannot safely be replayed."""


@dataclass(frozen=True)
class Writer:
    writer_id: str
    role: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.writer_id, "role": self.role}


@dataclass
class MaterializedItem:
    item_id: str
    item_kind: str
    status: str
    placement: str
    warrant_event_ids: list[str]
    detail: dict[str, Any]


@dataclass
class BodyViews:
    """Views derived only from validated lineage rows."""

    policy_profile_id: str = POLICY_PROFILE_ID
    state_items: dict[str, MaterializedItem] = field(default_factory=dict)
    warrant_health: dict[str, str] = field(default_factory=dict)
    dependents_by_warrant: dict[str, list[str]] = field(default_factory=dict)
    reported_metabolic_totals: dict[str, dict[str, int]] = field(default_factory=dict)
    event_count: int = 0
    through_event_id: str | None = None

    def canonical(self) -> dict[str, Any]:
        return {
            "policy_profile_id": self.policy_profile_id,
            "state_items": {
                item_id: {
                    "item_kind": item.item_kind,
                    "status": item.status,
                    "placement": item.placement,
                    "warrant_event_ids": sorted(item.warrant_event_ids),
                    "detail": item.detail,
                }
                for item_id, item in sorted(self.state_items.items())
            },
            "warrant_health": dict(sorted(self.warrant_health.items())),
            "dependents_by_warrant": {
                warrant: sorted(dependents)
                for warrant, dependents in sorted(self.dependents_by_warrant.items())
            },
            "reported_metabolic_totals": {
                item_id: dict(sorted(totals.items()))
                for item_id, totals in sorted(self.reported_metabolic_totals.items())
            },
            "event_count": self.event_count,
            "through_event_id": self.through_event_id,
        }

    def digest(self) -> str:
        return _digest(self.canonical())


@dataclass(frozen=True)
class ReplayResult:
    rows: tuple[dict[str, Any], ...]
    views: BodyViews
    verified_view_claim_ids: tuple[str, ...]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _event_hash(row_without_hash: Mapping[str, Any]) -> str:
    return _digest(row_without_hash)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReplayRefusal(message)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_retention(retention: Any, payload: Any, event_id: str) -> None:
    _require(
        isinstance(retention, dict),
        f"{event_id}: retention must be an object",
    )
    mode = retention.get("mode")
    _require(
        mode in {"inline", "reference", "redacted"},
        f"{event_id}: invalid retention mode {mode!r}",
    )
    if mode == "inline":
        _require(
            isinstance(payload, dict),
            f"{event_id}: inline payload must be an object",
        )
        return
    _require(payload == {}, f"{event_id}: {mode} event must not retain inline payload")
    _require(
        _is_sha256(retention.get("digest")),
        f"{event_id}: {mode} event requires a lowercase SHA-256 digest",
    )
    if mode == "reference":
        _require(
            isinstance(retention.get("external_ref"), str)
            and retention["external_ref"],
            f"{event_id}: reference event requires external_ref",
        )
    else:
        _require(
            isinstance(retention.get("reason"), str) and retention["reason"],
            f"{event_id}: redacted event requires a reason",
        )


def validate_lineage(rows: Iterable[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Validate envelope integrity, authority, ordering, and backward references."""
    validated: list[dict[str, Any]] = []
    known_ids: set[str] = set()
    invocation_ids: set[str] = set()
    encounter_ids: set[str] = set()
    previous_hash = GENESIS_HASH

    for expected_index, row in enumerate(rows, start=1):
        _require(
            isinstance(row, dict),
            f"row {expected_index}: event must be an object",
        )
        event_id = row.get("event_id")
        expected_id = f"ev-{expected_index:06d}"
        _require(
            event_id == expected_id,
            f"row {expected_index}: expected {expected_id}, got {event_id!r}",
        )
        _require(
            row.get("event_index") == expected_index,
            f"{event_id}: non-contiguous event_index",
        )
        _require(
            row.get("schema_version") == CORE_SCHEMA_VERSION,
            f"{event_id}: unsupported schema_version",
        )
        _require(
            row.get("evidence_class") == EVIDENCE_CLASS,
            f"{event_id}: unsupported evidence_class",
        )
        _require(
            isinstance(row.get("kind"), str) and row["kind"],
            f"{event_id}: kind is required",
        )
        _require(
            row.get("previous_event_hash") == previous_hash,
            f"{event_id}: previous_event_hash mismatch",
        )
        claimed_hash = row.get("event_hash")
        unsigned = {key: value for key, value in row.items() if key != "event_hash"}
        _require(
            claimed_hash == _event_hash(unsigned),
            f"{event_id}: event_hash mismatch",
        )

        writer = row.get("writer")
        _require(isinstance(writer, dict), f"{event_id}: writer must be an object")
        writer_id = writer.get("id")
        role = writer.get("role")
        _require(
            isinstance(writer_id, str) and writer_id,
            f"{event_id}: writer id is required",
        )
        _require(
            role in WRITER_AUTHORITIES,
            f"{event_id}: unknown writer role {role!r}",
        )
        authority = row.get("authority")
        _require(
            authority in WRITER_AUTHORITIES[role],
            f"{event_id}: role {role!r} cannot exercise {authority!r}",
        )

        parents = row.get("causal_parent_ids")
        warrants = row.get("warrant_event_ids")
        _require(
            isinstance(parents, list),
            f"{event_id}: causal_parent_ids must be a list",
        )
        _require(
            isinstance(warrants, list),
            f"{event_id}: warrant_event_ids must be a list",
        )
        for field_name, references in (
            ("causal_parent_ids", parents),
            ("warrant_event_ids", warrants),
        ):
            _require(
                len(references) == len(set(references)),
                f"{event_id}: duplicate {field_name}",
            )
            dangling = [
                reference for reference in references if reference not in known_ids
            ]
            _require(
                not dangling,
                f"{event_id}: dangling {field_name}: {dangling}",
            )

        scope = row.get("scope")
        _require(isinstance(scope, dict), f"{event_id}: scope must be an object")
        invocation_id = scope.get("invocation_id")
        encounter_id = scope.get("encounter_id")
        if invocation_id is not None:
            _require(
                invocation_id in invocation_ids,
                f"{event_id}: unknown invocation scope {invocation_id}",
            )
        if encounter_id is not None:
            _require(
                encounter_id in encounter_ids,
                f"{event_id}: unknown encounter scope {encounter_id}",
            )

        payload = row.get("payload")
        _validate_retention(row.get("retention"), payload, event_id)

        known_ids.add(event_id)
        if row["kind"] == "invocation_started":
            invocation_ids.add(event_id)
        if row["kind"] == "encounter_observed":
            encounter_ids.add(event_id)
        previous_hash = claimed_hash
        validated.append(row)

    return tuple(validated)


def derive_views(rows: Iterable[dict[str, Any]]) -> BodyViews:
    """Recompute state, placement, warrant health, dependencies, and metabolism."""
    validated = validate_lineage(rows)
    views = BodyViews()

    for row in validated:
        kind = row["kind"]
        payload = row["payload"]
        event_id = row["event_id"]

        if kind == "state_item_admitted":
            item_id = payload.get("item_id")
            _require(
                isinstance(item_id, str) and item_id,
                f"{event_id}: state_item_admitted requires item_id",
            )
            _require(
                item_id not in views.state_items,
                f"{event_id}: duplicate state item {item_id}",
            )
            status = payload.get("status", "probationary")
            placement = payload.get("placement", "hot")
            item_kind = payload.get("item_kind", "unspecified")
            detail = payload.get("detail", {})
            _require(
                status in STATE_TRANSITIONS,
                f"{event_id}: invalid state status {status!r}",
            )
            _require(
                placement in {"hot", "cold"},
                f"{event_id}: invalid placement {placement!r}",
            )
            _require(
                isinstance(item_kind, str) and item_kind,
                f"{event_id}: state item requires item_kind",
            )
            _require(
                isinstance(detail, dict),
                f"{event_id}: state item detail must be an object",
            )
            warrants = list(row["warrant_event_ids"])
            _require(warrants, f"{event_id}: admitted state requires a warrant")
            item = MaterializedItem(
                item_id=item_id,
                item_kind=item_kind,
                status=status,
                placement=placement,
                warrant_event_ids=warrants,
                detail=dict(detail),
            )
            views.state_items[item_id] = item
            for warrant in warrants:
                views.warrant_health.setdefault(warrant, "current")
                views.dependents_by_warrant.setdefault(warrant, []).append(item_id)
            if status in {"probationary", "active"}:
                unhealthy = [
                    warrant
                    for warrant in warrants
                    if views.warrant_health[warrant] != "current"
                ]
                _require(
                    not unhealthy,
                    f"{event_id}: cannot admit active state with unhealthy warrants {unhealthy}",
                )

        elif kind == "state_item_transition":
            item_id = payload.get("item_id")
            _require(
                item_id in views.state_items,
                f"{event_id}: unknown state item {item_id!r}",
            )
            item = views.state_items[item_id]
            from_status = payload.get("from_status")
            to_status = payload.get("to_status")
            _require(
                from_status == item.status,
                f"{event_id}: claimed from_status {from_status!r} != materialized {item.status!r}",
            )
            _require(
                to_status in STATE_TRANSITIONS[item.status],
                f"{event_id}: illegal state transition {item.status!r} -> {to_status!r}",
            )
            if to_status in {"probationary", "active"}:
                unhealthy = [
                    warrant
                    for warrant in item.warrant_event_ids
                    if views.warrant_health.get(warrant) != "current"
                ]
                _require(
                    not unhealthy,
                    f"{event_id}: cannot reactivate state with unhealthy warrants {unhealthy}",
                )
            item.status = to_status

        elif kind == "placement_changed":
            item_id = payload.get("item_id")
            _require(
                item_id in views.state_items,
                f"{event_id}: unknown state item {item_id!r}",
            )
            item = views.state_items[item_id]
            from_placement = payload.get("from_placement")
            to_placement = payload.get("to_placement")
            _require(
                from_placement == item.placement,
                f"{event_id}: claimed placement {from_placement!r} != {item.placement!r}",
            )
            _require(
                to_placement in {"hot", "cold"} and to_placement != item.placement,
                f"{event_id}: invalid placement transition",
            )
            item.placement = to_placement

        elif kind == "provenance_revision":
            target = payload.get("target_event_id")
            health = payload.get("health")
            _require(
                target
                in {prior["event_id"] for prior in validated[: row["event_index"] - 1]},
                f"{event_id}: provenance target does not precede revision",
            )
            _require(
                health in {"current", "disputed", "invalid"},
                f"{event_id}: invalid warrant health {health!r}",
            )
            views.warrant_health[target] = health
            if health == "invalid":
                for item_id in views.dependents_by_warrant.get(target, []):
                    item = views.state_items[item_id]
                    if item.status != "retired":
                        item.status = "suspended"

        elif kind == "metabolic_event":
            item_id = payload.get("item_id")
            _require(
                item_id in views.state_items,
                f"{event_id}: metabolic event for unknown item",
            )
            metric = payload.get("metric")
            units = payload.get("units")
            _require(
                isinstance(metric, str) and metric,
                f"{event_id}: metabolic metric required",
            )
            _require(
                isinstance(units, int) and not isinstance(units, bool) and units >= 0,
                f"{event_id}: metabolic units must be a non-negative integer",
            )
            totals = views.reported_metabolic_totals.setdefault(item_id, {})
            totals[metric] = totals.get(metric, 0) + units

        views.event_count = row["event_index"]
        views.through_event_id = event_id

    return views


def replay(rows: Iterable[dict[str, Any]]) -> ReplayResult:
    """Validate lineage and independently verify every materialized-view claim."""
    validated = validate_lineage(rows)
    verified_claims: list[str] = []
    for offset, row in enumerate(validated):
        if row["kind"] != "materialized_view_claim":
            continue
        payload = row["payload"]
        prefix_views = derive_views(validated[:offset])
        _require(
            payload.get("through_event_id") == prefix_views.through_event_id,
            f"{row['event_id']}: materialized view through_event_id mismatch",
        )
        _require(
            payload.get("view_digest") == prefix_views.digest(),
            f"{row['event_id']}: materialized view digest mismatch",
        )
        verified_claims.append(row["event_id"])
    return ReplayResult(
        rows=validated,
        views=derive_views(validated),
        verified_view_claim_ids=tuple(verified_claims),
    )


class LineageStore:
    """Append-only disk lineage whose rows are validated before use or append."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def raw_rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line_number, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                raise ReplayRefusal(
                    f"line {line_number}: blank lines are not permitted"
                )
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ReplayRefusal(
                    f"line {line_number}: invalid JSON: {exc.msg}"
                ) from exc
            rows.append(row)
        return rows

    def rows(self) -> list[dict[str, Any]]:
        return list(validate_lineage(self.raw_rows()))

    def replay(self) -> ReplayResult:
        return replay(self.raw_rows())

    def append(
        self,
        kind: str,
        *,
        writer: Writer,
        authority: str,
        payload: Mapping[str, Any] | None = None,
        causal_parent_ids: Iterable[str] = (),
        warrant_event_ids: Iterable[str] = (),
        invocation_id: str | None = None,
        encounter_id: str | None = None,
        retention: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        rows = self.rows()
        event_index = len(rows) + 1
        previous_hash = rows[-1]["event_hash"] if rows else GENESIS_HASH
        row: dict[str, Any] = {
            "schema_version": CORE_SCHEMA_VERSION,
            "event_id": f"ev-{event_index:06d}",
            "event_index": event_index,
            "kind": kind,
            "evidence_class": EVIDENCE_CLASS,
            "writer": writer.as_dict(),
            "authority": authority,
            "causal_parent_ids": list(causal_parent_ids),
            "warrant_event_ids": list(warrant_event_ids),
            "scope": {
                "invocation_id": invocation_id,
                "encounter_id": encounter_id,
            },
            "retention": dict(retention or {"mode": "inline"}),
            "payload": dict(payload or {}),
            "previous_event_hash": previous_hash,
        }
        row["event_hash"] = _event_hash(row)
        replay([*rows, row])
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return row

    def append_view_claim(self, *, writer: Writer) -> dict[str, Any]:
        views = derive_views(self.rows())
        return self.append(
            "materialized_view_claim",
            writer=writer,
            authority="system_record",
            causal_parent_ids=(
                [views.through_event_id] if views.through_event_id else []
            ),
            payload={
                "through_event_id": views.through_event_id,
                "view_digest": views.digest(),
                "claim_boundary": "cache claim only; replay remains authoritative",
            },
        )
