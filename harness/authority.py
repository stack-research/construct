"""Authority sidecar: record_id -> earned authority, read by L2 eligibility.

Written only from oracle-scored outcomes, gated by oracle confidence
(plan §5: a doubtful oracle can describe but cannot govern). Authority is a
multiplier on eligibility: 1.0 is neutral, clamped to [0.1, 2.0] so no record
can earn unbounded influence or be silently zeroed (suppression must be a
policy decision with a ledger reason, not an arithmetic accident).
"""

from __future__ import annotations

import json
from pathlib import Path

CLAMP_MIN, CLAMP_MAX = 0.1, 2.0
ORACLE_CONFIDENCE_THRESHOLD = 0.7


class AuthorityStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._data: dict[str, float] = {}
        if self.path.exists():
            self._data = json.loads(self.path.read_text())

    def get(self, record_id: str) -> float:
        return self._data.get(record_id, 1.0)

    def apply(self, record_id: str, delta: float, oracle_confidence: float) -> dict:
        """Returns the authority_update dict for the ledger. Applies only if the gate passes."""
        frozen = oracle_confidence < ORACLE_CONFIDENCE_THRESHOLD
        update = {
            "record_id": record_id,
            "delta": delta,
            "frozen": frozen,
            "authority_before": self.get(record_id),
        }
        if not frozen:
            self._data[record_id] = max(CLAMP_MIN, min(CLAMP_MAX, self.get(record_id) + delta))
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, indent=2, sort_keys=True))
        update["authority_after"] = self.get(record_id)
        return update
