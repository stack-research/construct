"""World-fact corpus loader for X2-U1 world-grounded fixtures.

Sibling to fictional_corpus.py, but the facts are REAL and externally verifiable
(`source != authored`): a status the world settled, pinned to a citable source URL.
Backs `world_fact_oracle` (source `web_verified`) so the X2-U1 close engages on an
out-of-weights *world* corpus — not the lab-authored Helix (which is X2-LB only).

Out-of-weights here is earned by obscurity + recency (and proven per-engine by the
pre-run ignorance probe recorded in the manifest attestation), never by construction.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FIELDS = (
    "corpus_id", "fictional", "domain", "facts", "source_url",
    "selection_method", "verified_by", "verified_at", "corpus_scope",
)


@dataclass(frozen=True)
class WorldFactCorpusEntry:
    corpus_id: str
    domain: str
    facts: dict[str, str]
    source_url: str  # the citable provenance for the disclosed decision rule
    selection_method: str
    verified_by: str
    verified_at: str
    corpus_scope: str
    path: str
    sha256: str


def load_world_fact_entry(path: str | Path) -> WorldFactCorpusEntry:
    p = (ROOT / path) if not Path(path).is_absolute() else Path(path)
    raw = p.read_bytes()
    d = json.loads(raw)
    problems = [f for f in REQUIRED_FIELDS if f not in d or d[f] in ("", None, [])]
    # The whole point of this loader vs the fictional one: the facts are REAL.
    if d.get("fictional") is not False:
        problems.append("fictional must be false (this is a world-grounded corpus; use fictional_corpus for synthetic)")
    if not isinstance(d.get("facts"), dict) or not d["facts"]:
        problems.append("facts must be a non-empty dict")
    if problems:
        raise ValueError(f"{p.name}: world-fact corpus entry invalid: {problems}")
    return WorldFactCorpusEntry(
        corpus_id=d["corpus_id"],
        domain=d["domain"],
        facts=dict(d["facts"]),
        source_url=d["source_url"],
        selection_method=d["selection_method"],
        verified_by=d["verified_by"],
        verified_at=d["verified_at"],
        corpus_scope=d["corpus_scope"],
        path=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),
        sha256=hashlib.sha256(raw).hexdigest(),
    )
