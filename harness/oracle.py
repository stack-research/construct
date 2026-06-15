"""Outcome oracles. A run with no outcome row is a failed run (plan §4A).

Two kinds (SPEC_M0 §1): the authored oracle scores against an expected answer
we wrote; the world-checked oracle scores against a corpus entry the world
wrote, through a decision rule we wrote and disclose IN the row. The fact is
un-authored; the mapping is authored; neither pretends to be the other.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .corpus import CorpusEntry, expected_decision

# The disclosed normative mapping (SPEC_M0 §1). Required non-empty on every
# world_checked row — an absent rule smuggles the apparatus back into the
# oracle while the row still looks world-checked (kagi/codex, v0.1 review).
DECISION_RULE = "COPE: retracted => decline; corrected with claim standing => cite"
DECISION_RULE_SOURCE = "https://publicationethics.org/retraction-guidelines"


@dataclass
class OracleScore:
    score: float  # 0.0–1.0
    type: str  # authored | world_checked
    source: str  # authored | retraction_corpus | web_search | sensor_trace | human_judgment
    confidence: float  # the value the authority gate consumes; for world_checked
    #                    rows this is min(corpus_confidence, rule_confidence)
    scorer: str  # harness | kagi
    # world_checked rows only (SPEC_M0 §4); None on authored rows:
    decision_rule: str | None = None
    decision_rule_source: str | None = None
    decision_extracted: str | None = None  # cite | decline | unparseable
    corpus_entry: str | None = None
    corpus_entry_sha256: str | None = None
    corpus_confidence: float | None = None
    rule_confidence: float | None = None
    representativeness: str | None = None
    corpus_scope: str | None = None
    # Reserved for the trace track (kagi/codex, v0.1) — null on retraction rows:
    trace_interval: str | None = None
    device_id: str | None = None
    capture_source: str | None = None


def _norm(s: str) -> str:
    # Replace stripped chars with a space (never delete) so word boundaries
    # survive: "**Decline.**\n\nThe" must normalize to "decline the", not the
    # glued "declinethe" that mis-extracts as unparseable. Answer-shape surface
    # effect (the A1 lesson); surfaced by claude's markdown in the M2 cross-engine run.
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


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


_NEGATED_CITE_PATTERNS = (
    r"\bdo not cite\b",
    r"\bnot suitable to cite\b",
    r"\bnot suitable for citation\b",
    r"\bshould not be cited\b",
    r"\bcannot be cited\b",
    r"\bnot citable\b",
)


def extract_decision(answer: str) -> str:
    """Mechanical cite/decline extraction — no human reads JSONL for verdicts.

    First-word priority: the C-1/C-2 answer shape is "`cite` or `decline`, then
    one sentence", so the leading token is authoritative when present. Conservative
    negated-citation patterns run before the first-occurrence fallback (M3 Phase B:
    adversarial framing pushes engines into defensive phrasing that must not
    mis-extract as `cite`). Still not a semantic judge — disclosed mechanical limits.
    """
    norm = _norm(answer)
    words = norm.split()
    if words and words[0] in ("cite", "decline"):
        return words[0]
    for pat in _NEGATED_CITE_PATTERNS:
        if re.search(pat, norm):
            return "decline"
    m = re.search(r"\b(cite|decline)\b", norm)
    return m.group(1) if m else "unparseable"


def world_checked_oracle(
    answer: str,
    entry: CorpusEntry,
    representativeness: str,
    corpus_confidence: float = 0.9,
    rule_confidence: float = 0.8,
) -> OracleScore:
    """Score a decision-shaped answer against a corpus entry (SPEC_M0 §4).

    Hard-fails on empty rule/representativeness fields: a world_checked row
    missing its disclosed apparatus must never be written.
    """
    if not DECISION_RULE or not DECISION_RULE_SOURCE:
        raise ValueError("world_checked row requires non-empty decision_rule + decision_rule_source")
    if not representativeness:
        raise ValueError(f"{entry.corpus_id}: representativeness must be stated at scoring time (SPEC_M0 §4)")
    decided = extract_decision(answer)
    return OracleScore(
        score=1.0 if decided == expected_decision(entry) else 0.0,
        type="world_checked",
        source="retraction_corpus",
        confidence=min(corpus_confidence, rule_confidence),
        scorer="harness",
        decision_rule=DECISION_RULE,
        decision_rule_source=DECISION_RULE_SOURCE,
        decision_extracted=decided,
        corpus_entry=entry.path,
        corpus_entry_sha256=entry.sha256,
        corpus_confidence=corpus_confidence,
        rule_confidence=rule_confidence,
        representativeness=representativeness,
        corpus_scope=entry.corpus_scope,
    )
