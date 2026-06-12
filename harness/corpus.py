"""Retraction-corpus loader: the un-authored side of the M0 oracle (SPEC_M0 §2).

Entries are supplied by the world-oracle role (kagi) with citations and
verified by a second participant before any scored run. The loader validates
shape loudly; it never judges the science — `claim_stands_after_event` comes
from the publisher's notice, not from us.

Boundary note (SPEC_M0 §5): corpus entries contain the answers to their own
episodes. Safe while engines under test never read the repo; the moment any
agent-under-test holds repo read access, corpus/ joins the off-path list in
check_contract's read-order validation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FIELDS = (
    "corpus_id", "doi", "title", "claim_summary", "category", "event_date",
    "stated_reason", "claim_stands_after_event", "notice_terseness",
    "provenance_urls", "selection_method", "verified_by", "verified_at",
    "corpus_scope",
)
CATEGORIES = ("retraction", "correction", "expression_of_concern")
TERSENESS = ("self_sufficient", "terse", "mixed")


@dataclass(frozen=True)
class CorpusEntry:
    corpus_id: str
    doi: str
    title: str
    claim_summary: str
    category: str
    event_date: str
    stated_reason: str
    claim_stands_after_event: bool
    notice_terseness: str
    provenance_urls: tuple[str, ...]
    selection_method: str
    verified_by: str
    verified_at: str
    corpus_scope: str
    path: str  # repo-relative, recorded in the oracle row
    sha256: str  # of file bytes at load time — pins what was scored against


def load_entry(path: str | Path) -> CorpusEntry:
    """Validate loudly; an entry that cannot back an oracle row must not load."""
    p = (ROOT / path) if not Path(path).is_absolute() else Path(path)
    raw = p.read_bytes()
    d = json.loads(raw)
    problems = [f for f in REQUIRED_FIELDS if f not in d or d[f] in ("", None, [])]
    if d.get("category") not in CATEGORIES:
        problems.append(f"category must be one of {CATEGORIES}")
    if d.get("notice_terseness") not in TERSENESS:
        problems.append(f"notice_terseness must be one of {TERSENESS}")
    if not isinstance(d.get("claim_stands_after_event"), bool):
        problems.append("claim_stands_after_event must be boolean (from the publisher's notice)")
    if not d.get("provenance_urls"):
        problems.append("provenance_urls empty — citations are load-bearing (SPEC_M0 §2)")
    if problems:
        raise ValueError(f"{p.name}: corpus entry cannot back an oracle row: {problems}")
    return CorpusEntry(
        **{f: tuple(d[f]) if f == "provenance_urls" else d[f] for f in REQUIRED_FIELDS},
        path=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def expected_decision(entry: CorpusEntry) -> str:
    """The disclosed decision rule (SPEC_M0 §1), applied to the world's category.
    EoC is excluded from v0 scoring: the world has not decided that category."""
    if entry.category == "retraction":
        return "decline"
    if entry.category == "correction":
        return "cite" if entry.claim_stands_after_event else "decline"
    raise ValueError(
        f"{entry.corpus_id}: category {entry.category!r} is excluded from v0 scoring (SPEC_M0 §2)"
    )
