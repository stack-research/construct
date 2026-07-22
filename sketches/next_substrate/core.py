"""Body Core v0.3: structural lineage verification with explicit projection.

This module is provisional runtime engineering, not a harness instrument or a
product schema. Its cognitive-policy-neutral kernel supplies deliberately small
structural facilities:

1. a tamper-evident lineage envelope;
2. fail-closed validation of ordering, authority, references, scopes, and
   retention;
3. explicit delegation of semantic replay to a selected projector.

The kernel retains a provisional structural vocabulary: writer-role authority
and the ``invocation_started`` / ``encounter_observed`` scope anchors. It is not
ontology-free. Lifecycle, placement, warrant, and metabolic interpretation live
in ``policy.py`` and cannot be selected silently.

Every event remains ``wire_integration_only``. Nothing here licenses a memory
mechanism or turns authored behavior into scientific evidence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, Iterable, Mapping, Protocol, TypeVar


CORE_SCHEMA_VERSION = "body-core-v0.2"
EVIDENCE_CLASS = "wire_integration_only"
GENESIS_HASH = "0" * 64

WRITER_AUTHORITIES: dict[str, frozenset[str]] = {
    "runtime": frozenset({"administration", "system_record"}),
    "observer": frozenset({"external_observation", "external_consequence"}),
    "controller": frozenset({"controller_transition", "wire_diagnostic"}),
    "model": frozenset({"model_proposal"}),
}


class ReplayRefusal(ValueError):
    """Raised when lineage cannot safely be replayed or projected."""


@dataclass(frozen=True)
class Writer:
    writer_id: str
    role: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.writer_id, "role": self.role}


ProjectedView = TypeVar("ProjectedView")


class Projector(Protocol[ProjectedView]):
    """Semantic projector selected explicitly by a lineage consumer."""

    projector_id: str

    def project(
        self, rows: tuple[dict[str, Any], ...]
    ) -> tuple[ProjectedView, tuple[str, ...]]:
        """Derive a view and verify projector-owned cache claims."""
        ...


@dataclass(frozen=True)
class ReplayResult(Generic[ProjectedView]):
    rows: tuple[dict[str, Any], ...]
    views: ProjectedView
    verified_view_claim_ids: tuple[str, ...]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _event_hash(row_without_hash: Mapping[str, Any]) -> str:
    return canonical_digest(row_without_hash)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReplayRefusal(message)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_retention(retention: Any, payload: Any, event_id: str) -> None:
    require(isinstance(retention, dict), f"{event_id}: retention must be an object")
    mode = retention.get("mode")
    require(
        mode in {"inline", "reference", "redacted"},
        f"{event_id}: invalid retention mode {mode!r}",
    )
    if mode == "inline":
        require(
            isinstance(payload, dict),
            f"{event_id}: inline payload must be an object",
        )
        return
    require(payload == {}, f"{event_id}: {mode} event must not retain inline payload")
    require(
        _is_sha256(retention.get("digest")),
        f"{event_id}: {mode} event requires a lowercase SHA-256 digest",
    )
    if mode == "reference":
        require(
            isinstance(retention.get("external_ref"), str)
            and retention["external_ref"],
            f"{event_id}: reference event requires external_ref",
        )
    else:
        require(
            isinstance(retention.get("reason"), str) and retention["reason"],
            f"{event_id}: redacted event requires a reason",
        )


def validate_lineage(rows: Iterable[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Validate structural vocabulary, envelope integrity, and references."""
    validated: list[dict[str, Any]] = []
    known_ids: set[str] = set()
    invocation_ids: set[str] = set()
    encounter_ids: set[str] = set()
    previous_hash = GENESIS_HASH

    for expected_index, row in enumerate(rows, start=1):
        require(
            isinstance(row, dict),
            f"row {expected_index}: event must be an object",
        )
        event_id = row.get("event_id")
        expected_id = f"ev-{expected_index:06d}"
        require(
            event_id == expected_id,
            f"row {expected_index}: expected {expected_id}, got {event_id!r}",
        )
        require(
            row.get("event_index") == expected_index,
            f"{event_id}: non-contiguous event_index",
        )
        require(
            row.get("schema_version") == CORE_SCHEMA_VERSION,
            f"{event_id}: unsupported schema_version",
        )
        require(
            row.get("evidence_class") == EVIDENCE_CLASS,
            f"{event_id}: unsupported evidence_class",
        )
        require(
            isinstance(row.get("kind"), str) and row["kind"],
            f"{event_id}: kind is required",
        )
        require(
            row.get("previous_event_hash") == previous_hash,
            f"{event_id}: previous_event_hash mismatch",
        )
        claimed_hash = row.get("event_hash")
        unsigned = {key: value for key, value in row.items() if key != "event_hash"}
        require(
            claimed_hash == _event_hash(unsigned),
            f"{event_id}: event_hash mismatch",
        )

        writer = row.get("writer")
        require(isinstance(writer, dict), f"{event_id}: writer must be an object")
        writer_id = writer.get("id")
        role = writer.get("role")
        require(
            isinstance(writer_id, str) and writer_id,
            f"{event_id}: writer id is required",
        )
        require(role in WRITER_AUTHORITIES, f"{event_id}: unknown writer role {role!r}")
        authority = row.get("authority")
        require(
            authority in WRITER_AUTHORITIES[role],
            f"{event_id}: role {role!r} cannot exercise {authority!r}",
        )

        parents = row.get("causal_parent_ids")
        warrants = row.get("warrant_event_ids")
        require(
            isinstance(parents, list),
            f"{event_id}: causal_parent_ids must be a list",
        )
        require(
            isinstance(warrants, list),
            f"{event_id}: warrant_event_ids must be a list",
        )
        for field_name, references in (
            ("causal_parent_ids", parents),
            ("warrant_event_ids", warrants),
        ):
            require(
                len(references) == len(set(references)),
                f"{event_id}: duplicate {field_name}",
            )
            dangling = [
                reference for reference in references if reference not in known_ids
            ]
            require(
                not dangling,
                f"{event_id}: dangling {field_name}: {dangling}",
            )

        scope = row.get("scope")
        require(isinstance(scope, dict), f"{event_id}: scope must be an object")
        invocation_id = scope.get("invocation_id")
        encounter_id = scope.get("encounter_id")
        if invocation_id is not None:
            require(
                invocation_id in invocation_ids,
                f"{event_id}: unknown invocation scope {invocation_id}",
            )
        if encounter_id is not None:
            require(
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


def replay(
    rows: Iterable[dict[str, Any]],
    *,
    projector: Projector[ProjectedView],
) -> ReplayResult[ProjectedView]:
    """Validate lineage, then delegate semantic replay to an explicit projector."""
    validated = validate_lineage(rows)
    views, verified_claims = projector.project(validated)
    return ReplayResult(
        rows=validated,
        views=views,
        verified_view_claim_ids=verified_claims,
    )


class LineageStore:
    """Append-only lineage with optional, explicitly bound semantic projection."""

    def __init__(
        self,
        path: Path,
        *,
        projector: Projector[Any] | None = None,
    ):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.projector = projector

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
        """Return kernel-validated rows without certifying a semantic view."""
        return list(validate_lineage(self.raw_rows()))

    def _selected_projector(
        self, projector: Projector[Any] | None = None
    ) -> Projector[Any]:
        selected = projector or self.projector
        if selected is None:
            raise ReplayRefusal(
                "explicit projector required for cognitive replay or view claims"
            )
        return selected

    def replay(
        self, *, projector: Projector[ProjectedView] | None = None
    ) -> ReplayResult[ProjectedView]:
        selected = self._selected_projector(projector)
        return replay(self.raw_rows(), projector=selected)

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
        projector: Projector[Any] | None = None,
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
        candidate = [*rows, row]
        selected = projector or self.projector
        if selected is None:
            validate_lineage(candidate)
        else:
            replay(candidate, projector=selected)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return row

    def append_view_claim(
        self,
        *,
        writer: Writer,
        projector: Projector[Any] | None = None,
    ) -> dict[str, Any]:
        selected = self._selected_projector(projector)
        views = replay(self.raw_rows(), projector=selected).views
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
            projector=selected,
        )
