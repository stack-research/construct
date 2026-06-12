"""The ledger: append-only JSONL, written by the harness only.

The engine cannot steer what is recorded about it (plan §2.4). Row kinds:
  run_config — one per run; carries every fixture/backend disclosure
  offer / withholding — one per record per branch (plan §5)
  branch_run — per-branch cost side: latency, tokens, governance steps
  diff_outcome — per branch pair: divergence + oracle score + authority delta
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
