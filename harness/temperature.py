"""Temperature sidecar: record_id -> salience, the sibling of authority (SPEC_X1).

Temperature is an out-of-band multiplier on eligibility, exactly like authority
([authority.py]): 1.0 is neutral, clamped to [T_FLOOR, T_MAX]. The floor is > 0
on purpose — cooling *relaxes toward a cold floor, never to zero*. A cooled
record stays cold-but-present and recoverable; dropping it out of the hot store
entirely (below the floor) is the deliberate, prune-planned *erasure* act of X2+,
never an arithmetic accident (the same doctrine authority.py states for
suppression). Authority is earned by consequence; temperature is earned by use,
adjudicated by the world.

The second law, in code: **cooling is free** (relaxation toward the floor, the
default direction) and **reheating must be paid** (the Landauer oracle, in branch
C). The actuator does not decide heat — it *applies what a pre-action
thermal_projection authorized* (Wall II). Its input is an allowlist of scalars
and refs, never a free-form provenance blob: an observer that could hand the
actuator a post-answer self-claim ("this still matters to me") would reopen the
closed-loop drift the air gap exists to refuse. The demon pays by being logged
before it moves heat.
"""

from __future__ import annotations

import json
from pathlib import Path

NEUTRAL = 1.0
T_FLOOR, T_MAX = 0.1, 2.0  # mirror AuthorityStore's clamp: no record silently zeroed
# Asymmetric by design (disclosed calibration, SPEC_X1): a world-WRONG recall is
# clawed harder than a record is merely cooled by disuse, so a record the world
# keeps faulting cools *out* of eligibility before a merely-unused one — which is
# what lets the corrective record become load-bearing and earn its heat (the
# earned-reweighting phase transition). Reheat is paid; cooling is free.
REHEAT = 0.2       # paid reheat: a load-bearing, world-correct recall
CLAW = 0.4         # clawed-back: a load-bearing, world-WRONG recall (cools hardest)
RELAXATION = 0.1   # free disuse cooling per tick (gentlest; the default direction)

# Wall II — the actuator's input is an allowlist, not a forbidden-list (codex/cursor/gemma).
ALLOWED_PROJECTION_KEYS = frozenset({
    "recommendation", "magnitude", "authorized_basis",
    "projection_ref", "landauer_decision_ref",
})
ALLOWED_BASIS_KEYS = frozenset({
    "recall_load_bearing", "mode", "landauer_decision_id", "disuse_tick",
})
# Post-answer self-report the actuator must never read as authority for heat.
FORBIDDEN_BASIS_FIELDS = frozenset({
    "agent_claimed_usage", "agent_claimed_load_bearing",
    "resident_self_label", "answer", "answer_narration",
})

_RECOMMENDATION_SIGN = {"reheat": +1.0, "cool": -1.0, "hold": 0.0}


class ProjectionViolation(Exception):
    """Wall II breach at write time: the actuator was asked to move heat the
    pre-action thermal_projection did not authorize, or on a forbidden basis.
    score_decay.py recomputes the same entailment from the logged rows; this is
    the runtime half of that check (defense in depth)."""


def entailed_delta(recommendation: str, magnitude: float) -> float:
    """The heat a projection authorizes, derived only from allowlisted fields.
    Pure: read by run_x1 to apply and by score_decay to verify — they must agree."""
    if recommendation not in _RECOMMENDATION_SIGN:
        raise ProjectionViolation(f"unknown recommendation: {recommendation!r}")
    return _RECOMMENDATION_SIGN[recommendation] * magnitude


def _validate_projection(projection: dict) -> None:
    extra = set(projection) - ALLOWED_PROJECTION_KEYS
    if extra:
        raise ProjectionViolation(f"projection carries non-allowlisted keys: {sorted(extra)}")
    basis = projection.get("authorized_basis", {})
    if not isinstance(basis, dict):
        raise ProjectionViolation("authorized_basis must be a dict of allowlisted keys")
    forbidden = (set(basis) & FORBIDDEN_BASIS_FIELDS) | (set(basis) - ALLOWED_BASIS_KEYS)
    if forbidden:
        raise ProjectionViolation(
            f"authorized_basis touches non-allowlisted/forbidden fields: {sorted(forbidden)}"
        )


class TemperatureStore:
    """record_id -> earned salience, read by the X1 eligibility factor.

    Written only through apply(), which moves exactly the heat the projection
    entails. The sidecar file is a *cache*; the source of truth is the ordered
    temperature_delta rows in the ledger (replay rebuilds this store from them)."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._data: dict[str, float] = {}
        if self.path.exists():
            self._data = json.loads(self.path.read_text())

    def get(self, record_id: str) -> float:
        return self._data.get(record_id, NEUTRAL)

    def apply(self, record_id: str, projection: dict) -> dict:
        """Apply the projection-entailed heat. Allowlist signature: a validated
        projection dict only — never a free-form provenance object. Raises
        ProjectionViolation if the projection is malformed or rests on a
        forbidden basis. Clamps to [T_FLOOR, T_MAX]. Returns the temperature_delta
        row for the ledger (carrying both refs so the scorer can re-derive)."""
        _validate_projection(projection)
        delta = entailed_delta(projection["recommendation"], projection["magnitude"])
        before = self.get(record_id)
        after = max(T_FLOOR, min(T_MAX, before + delta))
        self._data[record_id] = after
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, sort_keys=True))
        return {
            "record_id": record_id,
            "delta": delta,
            "temp_before": before,
            "temp_after": after,
            "thermal_projection_ref": projection.get("projection_ref"),
            "landauer_decision_ref": projection.get("landauer_decision_ref"),
        }
