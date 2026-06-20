"""Hot-store / cold-lineage split: the X-track's first off-boundary organ (SPEC_X2).

The **hot store** is the materialized candidate universe `select_offers` ranks over
(passed as a branch's `inherited_record_ids`); the `RecordStore`/episode is the
**cold lineage** — append-only, immutable. **Prune** evicts a record_id from the
hot set (it stops being a candidate); the record survives in lineage. **Rematerialize**
returns a cold record to the hot set under a ledgered, oracle-gated reason.

**There is no erase-from-lineage verb — by design.** The actuator allowlist is
prune/rematerialize/hold only and `all_record_ids` (the lineage) is never reduced;
forgetting is eviction, never erasure. An erase verb would be an attack vector —
silent removal of dissent, corrections, or tamper-evidence — and is the one act the
substrate refuses; cost-replay and the air-gap refusals all assume the rows cannot
be removed.

Carrying the hot set has a **cost** (`hot_tokens` primary) the offer boundary cannot
reduce — it withholds but keeps everything hot, and it cannot erase (Landauer). X2 is
scored on **cost at matched quality** (the scoring-axis law): the win is lower carry
cost with answer quality held to a world-checked floor, never a changed answer —
because withheld-hot, pruned, and cold-in-lineage are identical *answer inputs*
(codex's observational equivalence; the X1 lesson).

Wall II (lifted from X1's TemperatureStore): the actuator applies only what a
pre-action `prune_projection` authorizes, via an allowlist signature — never a
provenance blob, and it reads no post-answer self-claim. The sidecar is a cache;
the `prune`/`rematerialize` rows are the source of truth (replay rebuilds the hot set).
"""

from __future__ import annotations

import json
from pathlib import Path

# Wall II — allowlist, not a forbidden-list (the X1 codex/cursor/gemma lesson).
ALLOWED_PROJECTION_KEYS = frozenset({
    "recommendation", "authorized_basis", "projection_ref", "world_check_ref",
})
ALLOWED_BASIS_KEYS = frozenset({
    "mode", "disuse", "world_check_id", "needed_by", "recall_load_bearing",
})
FORBIDDEN_BASIS_FIELDS = frozenset({
    "agent_claimed_usage", "agent_claimed_load_bearing",
    "resident_self_label", "answer", "answer_narration",
})
_RECOMMENDATIONS = frozenset({"prune", "rematerialize", "hold"})


class ProjectionViolation(Exception):
    """Wall II breach at write time: the actuator was asked to move a record the
    pre-action prune_projection did not authorize, or on a forbidden basis.
    score_prune.py recomputes the same entailment from the logged rows."""


def _validate_projection(projection: dict) -> None:
    extra = set(projection) - ALLOWED_PROJECTION_KEYS
    if extra:
        raise ProjectionViolation(f"projection carries non-allowlisted keys: {sorted(extra)}")
    if projection.get("recommendation") not in _RECOMMENDATIONS:
        raise ProjectionViolation(f"unknown recommendation: {projection.get('recommendation')!r}")
    basis = projection.get("authorized_basis", {})
    if not isinstance(basis, dict):
        raise ProjectionViolation("authorized_basis must be a dict of allowlisted keys")
    forbidden = (set(basis) & FORBIDDEN_BASIS_FIELDS) | (set(basis) - ALLOWED_BASIS_KEYS)
    if forbidden:
        raise ProjectionViolation(
            f"authorized_basis touches non-allowlisted/forbidden fields: {sorted(forbidden)}"
        )


class HotStore:
    """Per-branch hot set: the record_ids currently materialized. Read by the runner
    and passed to select_offers as `inherited_record_ids`. Mutated only through
    apply() under a validated projection; the sidecar mirrors the hot set but the
    ledger's prune/rematerialize rows are authoritative for replay."""

    def __init__(self, path: Path, seed_ids: frozenset | set | None = None):
        self.path = Path(path)
        if self.path.exists():
            self._hot: set[str] = set(json.loads(self.path.read_text()))
        else:
            self._hot = set(seed_ids or ())
            self._flush()

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(sorted(self._hot), indent=2))

    def get_hot(self) -> frozenset:
        return frozenset(self._hot)

    def apply(self, record_id: str, projection: dict) -> dict:
        """Apply the projection-entailed op. Allowlist signature: a validated
        projection only — never a provenance blob. prune evicts to cold, rematerialize
        returns to hot, hold is a no-op. Raises ProjectionViolation on a malformed
        or forbidden basis. Returns the prune/rematerialize row for the ledger."""
        _validate_projection(projection)
        rec = projection["recommendation"]
        before = record_id in self._hot
        if rec == "prune":
            self._hot.discard(record_id)
        elif rec == "rematerialize":
            self._hot.add(record_id)
        # hold: no-op
        after = record_id in self._hot
        self._flush()
        return {
            "record_id": record_id,
            "op": rec,
            "in_hot_before": before,
            "in_hot_after": after,
            "prune_projection_ref": projection.get("projection_ref"),
            "world_check_ref": projection.get("world_check_ref"),
        }

    def cost(self, records: list) -> dict:
        """Deterministic, substrate-native hot-store burden for the current hot set.
        hot_tokens is the primary metric (what must be carried/attended). Never
        wall-clock (the latency-as-governance trap)."""
        hot = [r for r in records if r.record_id in self._hot]
        return {
            "hot_record_count": len(hot),
            "hot_tokens": sum(len(r.text.split()) for r in hot),
            "materialized_bytes": sum(len(r.text.encode("utf-8")) for r in hot),
        }
