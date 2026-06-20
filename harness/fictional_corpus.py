"""Fictional lab-fact corpus loader for X2 world-scored fixtures (SPEC_X2 §5).

Entries are authored for construct runs where retraction-corpus oracles are the
wrong shape. They back a fact-extraction oracle (`lab_fictional_corpus` source)
so X2-U1 can engage without rw-0001 memorization confounds. The facts have no
real-world referent — out-of-weights by construction.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FIELDS = (
    "corpus_id", "fictional", "domain", "facts", "selection_method",
    "verified_by", "verified_at", "corpus_scope",
)


@dataclass(frozen=True)
class FictionalCorpusEntry:
    corpus_id: str
    fictional: bool
    domain: str
    facts: dict[str, str]
    selection_method: str
    verified_by: str
    verified_at: str
    corpus_scope: str
    path: str
    sha256: str


def load_fictional_entry(path: str | Path) -> FictionalCorpusEntry:
    p = (ROOT / path) if not Path(path).is_absolute() else Path(path)
    raw = p.read_bytes()
    d = json.loads(raw)
    problems = [f for f in REQUIRED_FIELDS if f not in d or d[f] in ("", None, [])]
    if d.get("fictional") is not True:
        problems.append("fictional must be true")
    if not isinstance(d.get("facts"), dict) or not d["facts"]:
        problems.append("facts must be a non-empty dict")
    if problems:
        raise ValueError(f"{p.name}: fictional corpus entry invalid: {problems}")
    return FictionalCorpusEntry(
        corpus_id=d["corpus_id"],
        fictional=True,
        domain=d["domain"],
        facts=dict(d["facts"]),
        selection_method=d["selection_method"],
        verified_by=d["verified_by"],
        verified_at=d["verified_at"],
        corpus_scope=d["corpus_scope"],
        path=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),
        sha256=hashlib.sha256(raw).hexdigest(),
    )
