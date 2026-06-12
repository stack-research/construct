"""oracle_reinterpretation rows (SPEC_M0 §4): a retroactive reading of a scored
outcome is a different epistemic act, not an amendment. The new row references
the original by line hash and never rewrites it — the original verdict stays
true-as-scored under the corpus state then in force (the L-A precedent,
applied to the world: the retraction was itself retracted, the correction was
upgraded, the corpus entry was found wanting).

Usage:
  uv run --no-project python -m harness.reinterpret LEDGER.jsonl \
      --original-sha256 <sha of the original JSONL line> \
      --reading "<the new interpretation>" \
      --basis "<what changed in the world or the corpus>" \
      --agent <who is reinterpreting>
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from .ledger import Ledger


def find_row_line(ledger_path: Path, sha: str) -> str | None:
    for line in ledger_path.read_text().splitlines():
        if line.strip() and hashlib.sha256(line.encode()).hexdigest() == sha:
            return line
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ledger", type=Path)
    ap.add_argument("--original-sha256", required=True)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--basis", required=True)
    ap.add_argument("--agent", required=True)
    args = ap.parse_args(argv)

    if find_row_line(args.ledger, args.original_sha256) is None:
        print(f"FAIL: no row in {args.ledger} hashes to {args.original_sha256[:12]}… — "
              "a reinterpretation must point at a real original")
        return 1
    Ledger(args.ledger).write({
        "kind": "oracle_reinterpretation",
        "original_row_sha256": args.original_sha256,
        "reading": args.reading,
        "basis": args.basis,
        "agent": args.agent,
    })
    print(f"oracle_reinterpretation appended to {args.ledger} (original {args.original_sha256[:12]}… untouched)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
