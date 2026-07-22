"""Explicit provisional cognitive-state projection for Body Core v0.3.

This module preserves the exact Body Core v0.2 lifecycle, binary placement,
warrant-health, automatic-suspension, and metabolic fold. The profile is
selected explicitly by callers; it is useful authored policy under wire test,
not mechanism-neutral law or scientific evidence.

The profile deliberately preserves two historical properties during the split:

* every validated lineage row advances the canonical replay cursor even when
  its kind does not mutate policy state;
* event kind is not generically bound to writer authority. Runtime and adapter
  route constraints remain client policy rather than refactor-time Core law.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .core import canonical_digest, require


POLICY_PROFILE_ID = "body-core-v0.2-provisional-policy"

STATE_TRANSITIONS: dict[str, frozenset[str]] = {
    "probationary": frozenset({"active", "suspended", "retired"}),
    "active": frozenset({"suspended", "retired"}),
    "suspended": frozenset({"probationary", "active", "retired"}),
    "retired": frozenset(),
}

POLICY_MUTATING_EVENT_KINDS = frozenset(
    {
        "state_item_admitted",
        "state_item_transition",
        "placement_changed",
        "provenance_revision",
        "metabolic_event",
    }
)


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
    """The exact canonical view produced by the provisional v0.2 policy."""

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
        return canonical_digest(self.canonical())


def _derive_views(rows: Iterable[dict[str, Any]]) -> BodyViews:
    """Fold already-validated rows through the exact v0.2 policy."""
    validated = tuple(rows)
    views = BodyViews()

    for row in validated:
        kind = row["kind"]
        payload = row["payload"]
        event_id = row["event_id"]

        if kind == "state_item_admitted":
            item_id = payload.get("item_id")
            require(
                isinstance(item_id, str) and item_id,
                f"{event_id}: state_item_admitted requires item_id",
            )
            require(
                item_id not in views.state_items,
                f"{event_id}: duplicate state item {item_id}",
            )
            status = payload.get("status", "probationary")
            placement = payload.get("placement", "hot")
            item_kind = payload.get("item_kind", "unspecified")
            detail = payload.get("detail", {})
            require(
                status in STATE_TRANSITIONS,
                f"{event_id}: invalid state status {status!r}",
            )
            require(
                placement in {"hot", "cold"},
                f"{event_id}: invalid placement {placement!r}",
            )
            require(
                isinstance(item_kind, str) and item_kind,
                f"{event_id}: state item requires item_kind",
            )
            require(
                isinstance(detail, dict),
                f"{event_id}: state item detail must be an object",
            )
            warrants = list(row["warrant_event_ids"])
            require(warrants, f"{event_id}: admitted state requires a warrant")
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
                require(
                    not unhealthy,
                    f"{event_id}: cannot admit active state with unhealthy warrants {unhealthy}",
                )

        elif kind == "state_item_transition":
            item_id = payload.get("item_id")
            require(
                item_id in views.state_items,
                f"{event_id}: unknown state item {item_id!r}",
            )
            item = views.state_items[item_id]
            from_status = payload.get("from_status")
            to_status = payload.get("to_status")
            require(
                from_status == item.status,
                f"{event_id}: claimed from_status {from_status!r} != materialized {item.status!r}",
            )
            require(
                to_status in STATE_TRANSITIONS[item.status],
                f"{event_id}: illegal state transition {item.status!r} -> {to_status!r}",
            )
            if to_status in {"probationary", "active"}:
                unhealthy = [
                    warrant
                    for warrant in item.warrant_event_ids
                    if views.warrant_health.get(warrant) != "current"
                ]
                require(
                    not unhealthy,
                    f"{event_id}: cannot reactivate state with unhealthy warrants {unhealthy}",
                )
            item.status = to_status

        elif kind == "placement_changed":
            item_id = payload.get("item_id")
            require(
                item_id in views.state_items,
                f"{event_id}: unknown state item {item_id!r}",
            )
            item = views.state_items[item_id]
            from_placement = payload.get("from_placement")
            to_placement = payload.get("to_placement")
            require(
                from_placement == item.placement,
                f"{event_id}: claimed placement {from_placement!r} != {item.placement!r}",
            )
            require(
                to_placement in {"hot", "cold"} and to_placement != item.placement,
                f"{event_id}: invalid placement transition",
            )
            item.placement = to_placement

        elif kind == "provenance_revision":
            target = payload.get("target_event_id")
            health = payload.get("health")
            require(
                target
                in {prior["event_id"] for prior in validated[: row["event_index"] - 1]},
                f"{event_id}: provenance target does not precede revision",
            )
            require(
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
            require(
                item_id in views.state_items,
                f"{event_id}: metabolic event for unknown item",
            )
            metric = payload.get("metric")
            units = payload.get("units")
            require(
                isinstance(metric, str) and metric,
                f"{event_id}: metabolic metric required",
            )
            require(
                isinstance(units, int) and not isinstance(units, bool) and units >= 0,
                f"{event_id}: metabolic units must be a non-negative integer",
            )
            totals = views.reported_metabolic_totals.setdefault(item_id, {})
            totals[metric] = totals.get(metric, 0) + units

        # Cursor arithmetic is a lineage fact carried by the projection. Every
        # validated row advances it, including client rows the policy does not own.
        views.event_count = row["event_index"]
        views.through_event_id = event_id

    return views


@dataclass(frozen=True)
class V02PolicyProjector:
    """Exact projector for the historical Body Core v0.2 policy fold."""

    projector_id: str = POLICY_PROFILE_ID

    def project(
        self, rows: tuple[dict[str, Any], ...]
    ) -> tuple[BodyViews, tuple[str, ...]]:
        verified_claims: list[str] = []
        for offset, row in enumerate(rows):
            if row["kind"] != "materialized_view_claim":
                continue
            payload = row["payload"]
            prefix_views = _derive_views(rows[:offset])
            require(
                payload.get("through_event_id") == prefix_views.through_event_id,
                f"{row['event_id']}: materialized view through_event_id mismatch",
            )
            require(
                payload.get("view_digest") == prefix_views.digest(),
                f"{row['event_id']}: materialized view digest mismatch",
            )
            verified_claims.append(row["event_id"])
        return _derive_views(rows), tuple(verified_claims)


V02_POLICY_PROJECTOR = V02PolicyProjector()
