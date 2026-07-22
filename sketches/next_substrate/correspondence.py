"""Shared source-binding checks for Body Core wire adapters.

Adapters decide which state receipts they authorize and what those receipts
mean.  This helper checks only the repeated transport invariant: every selected
receipt affecting adapter-materialized state must point back to one carried
source event, name that event as a causal parent, and repeat its declared source
coordinates exactly.

The helper is Core-adjacent rather than part of the integrity kernel.  Source
row kinds and coordinates belong to adapters, not to Body Core's generic event
envelope or provisional policy profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .core import ReplayRefusal


@dataclass(frozen=True)
class SourceBindingIndex:
    """Validated receipts grouped by the carried source event they bind."""

    source_events: dict[str, dict[str, Any]]
    receipts: tuple[dict[str, Any], ...]
    receipts_by_source: dict[str, tuple[dict[str, Any], ...]]


def index_bound_state_receipts(
    rows: Iterable[dict[str, Any]],
    *,
    source_event_kind: str,
    receipt_event_kinds: Iterable[str],
    affected_item_ids: Iterable[str],
    coordinate_fields: Iterable[str],
    context: str,
) -> SourceBindingIndex:
    """Validate selected state receipts without choosing adapter policy.

    Callers supply the receipt kinds their adapter authorizes.  Other
    state-affecting kinds remain the caller's responsibility, which keeps a
    valid source binding from granting policy permission by itself.
    """

    row_list = tuple(rows)
    receipt_kinds = frozenset(receipt_event_kinds)
    item_ids = frozenset(affected_item_ids)
    coordinates = tuple(coordinate_fields)
    source_events = {
        row["event_id"]: row for row in row_list if row["kind"] == source_event_kind
    }
    receipts: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = {}

    for row in row_list:
        if row["kind"] not in receipt_kinds:
            continue
        payload = row["payload"]
        if payload.get("item_id") not in item_ids:
            continue

        source_event_id = payload.get("source_event_id")
        if not isinstance(source_event_id, str) or not source_event_id:
            raise ReplayRefusal(
                f"{row['event_id']}: {context} {row['kind']} lacks source_event_id"
            )
        source = source_events.get(source_event_id)
        if source is None:
            raise ReplayRefusal(
                f"{row['event_id']}: {context} source_event_id {source_event_id!r} "
                f"is not a {source_event_kind} event"
            )
        if source_event_id not in row["causal_parent_ids"]:
            raise ReplayRefusal(
                f"{row['event_id']}: {context} source_event_id must be a causal parent"
            )
        for field in coordinates:
            if (
                field not in payload
                or field not in source["payload"]
                or payload[field] != source["payload"][field]
            ):
                raise ReplayRefusal(
                    f"{row['event_id']}: {context} source coordinate {field!r} "
                    "disagrees with carried source"
                )

        receipts.append(row)
        grouped.setdefault(source_event_id, []).append(row)

    return SourceBindingIndex(
        source_events=source_events,
        receipts=tuple(receipts),
        receipts_by_source={
            source_event_id: tuple(bound)
            for source_event_id, bound in grouped.items()
        },
    )
