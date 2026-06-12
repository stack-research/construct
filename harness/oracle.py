"""Authored outcome oracle. A run with no outcome row is a failed run (plan §4A)."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class OracleScore:
    score: float  # 0.0–1.0
    type: str  # authored | world_checked
    source: str  # authored | web_search | sensor_trace | human_judgment
    confidence: float
    scorer: str  # harness | kagi


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def authored_oracle(answer: str, expected_answer: str) -> OracleScore:
    """Score 1.0 if the normalized expected answer appears in the normalized answer."""
    hit = _norm(expected_answer) in _norm(answer)
    return OracleScore(
        score=1.0 if hit else 0.0,
        type="authored",
        source="authored",
        confidence=1.0,
        scorer="harness",
    )
