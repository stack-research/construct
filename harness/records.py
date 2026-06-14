"""Record store: the inert side of memory. A record does nothing until offered."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Record:
    record_id: str
    text: str
    created_at: str  # ISO 8601; recency is computed from ordering, not wall clock
    predeclared_usage: str | None = None  # plan | observation | correction | distractor | evidence | ...
    vocabulary_kind: str | None = None  # belief | claim | memory | evidence | reality_observation (descriptive, non-gating)
    trust: float = 1.0  # source-trust prior for L2 eligibility; a prior, not truth
    supersedes: tuple[str, ...] = ()  # out-of-band ingestion-channel links (SPEC_V1X §2); never rendered to the engine
    provenance: dict | None = None  # SPEC_M2 §3: harness-minted earned-record provenance.
    #   Null on ordinary records. On an earned-failure record (Wall B) carries
    #   {minted_by, source_session_id, source_run_id, mint_basis, corrected_claim,
    #    source_oracle}. Written by the harness mint from the scored trace, never
    #   by the engine — the resident does not hold the pen on its own past.


class RecordStore:
    """Append-only JSONL store. The harness reads it; the engine never does."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.records: list[Record] = []
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    d = json.loads(line)
                    self.records.append(Record(**d))

    def append(self, record: Record) -> None:
        self.records.append(record)
        with self.path.open("a") as f:
            f.write(json.dumps(record.__dict__) + "\n")

    def all(self) -> list[Record]:
        return list(self.records)
