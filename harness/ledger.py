"""The ledger: append-only JSONL, written by the harness only.

The engine cannot steer what is recorded about it (plan §2.4). Row kinds:
  run_config — one per run; carries every fixture/backend disclosure
  offer / withholding — one per record per branch (plan §5)
  branch_run — per-branch cost side: latency, tokens, governance steps, and the
    branch's own `oracle` outcome (SPEC_M2: a single-branch session must ledger
    its scored failure for the mint to read; not only the pairwise diff_outcome)
  diff_outcome — per branch pair: divergence + oracle score + authority delta

Contribution boundary (SPEC_M1.5 — the offer ledger, one level up):
  intervention — a CLAIM that an agent intervention changed an artifact; audit
    input only (R5), contributor-written, never authoritative. `intervention_kind`
    (review|blocker|patch|audit|synthesis) is the category; `kind` is the row type.
  contribution_verdict — the COMPUTED boundary crossing, written by
    score_contribution.py from the artifact trace; load_bearing is never copied
    from the intervention's claim.

Resident substrate (SPEC_M2 — the offer ledger, across a session seam):
  session — one per session; the cold memory-blank seam made auditable:
    {session_id, store_path, prior_session_id, wall_clock_start (documentary),
     resident_config_digest, memory_isolation: minimal_harness|scrubbed, episode_id}.
    Compared across the E2 fork as a scorer precondition (engine re-instantiated
    cold, governed store the sole memory channel — Wall A integrity).
  An earned-failure record is an ordinary Record whose `provenance` is minted by
    the HARNESS from the E1 scored trace (Wall B), never by the resident.
  resident_verdict / cell_verdict — COMPUTED by score_resident.py: the fork (not
    the resident's testimony) decides whether the store was used (RS-1/RS-loses/
    RS-stale/RS-U1).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class Ledger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, row: dict[str, Any]) -> None:
        row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **row}
        with self.path.open("a") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")

    def rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text().splitlines() if l.strip()]
