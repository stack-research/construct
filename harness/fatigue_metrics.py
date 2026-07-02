"""Fatigue metrics over the immutable substrate thread record.

A print-only, non-gating advisory instrument (route_watch discipline: no
judicial robes — always exits 0, adds no fail-bit to check_contract).
Committed per heir-audit codex blocker (2026-07-02): the counting rules ARE
the metric, so they live in the repo, not a scratchpad.

Counting rules (crude by design; string-match, never semantic):
  - an *entry* is any `TIMESTAMP__author.md` file in a thread directory;
    `%2F` in author decodes to `/` (harness/model-version names);
    `__no-op` suffixed entries count as entries but are tagged no-op.
  - `blocker`  = occurrences of "blocker" minus occurrences of "no blocker"
    (case-insensitive) — counts *mentions*, not adjudicated blockers.
  - `endorse`  = occurrences of "endorse" — same caveat.
  These are TOPIC-PRESENCE counts (the route_watch §9.4 lesson applies):
  they support trend reading across threads, never per-entry verdicts.

Outputs: per-thread summary (span, authors, blocker/endorse counts),
roster attrition (last entry per participant), entries per calendar day.
"""

from __future__ import annotations

import collections
import datetime
import re
import sys
from pathlib import Path

ENTRY = re.compile(r"^(\d{8}T\d{9}Z)__(.+?)(__no-op)?\.md$")
THREADS_DIR = Path(".substrate/threads")


def _ts(s: str) -> datetime.datetime:
    return datetime.datetime.strptime(s, "%Y%m%dT%H%M%S%fZ")


def _author(raw: str) -> str:
    return raw.replace("%2F", "/")


def collect(threads_dir: Path) -> dict[str, list[dict]]:
    threads: dict[str, list[dict]] = {}
    for tdir in sorted(threads_dir.iterdir()):
        if not tdir.is_dir():
            continue
        entries = []
        for f in sorted(tdir.iterdir()):
            m = ENTRY.match(f.name)
            if not m:
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            low = text.lower()
            no_blocker = len(re.findall(r"no blocker", low))
            entries.append({
                "t": _ts(m.group(1)),
                "author": _author(m.group(2)),
                "noop": bool(m.group(3)),
                "chars": len(text),
                "blocker": len(re.findall(r"blocker", low)) - no_blocker,
                "no_blocker": no_blocker,
                "endorse": len(re.findall(r"endorse", low)),
            })
        if entries:
            threads[tdir.name] = entries
    return threads


def report(threads: dict[str, list[dict]]) -> None:
    print("=== per-thread summary (topic-presence counts, not verdicts) ===")
    for name, es in threads.items():
        span = es[-1]["t"] - es[0]["t"]
        authors = collections.Counter(e["author"] for e in es)
        b = sum(e["blocker"] for e in es)
        en = sum(e["endorse"] for e in es)
        print(f"{name:12s} entries={len(es):3d} span={str(span):>18s} "
              f"first={es[0]['t']:%m-%d %H:%M} last={es[-1]['t']:%m-%d %H:%M} "
              f"blocker~{b} endorse~{en}")
        print(f"             authors: {dict(authors)}")

    print("\n=== last entry per participant (roster attrition) ===")
    last: dict[str, tuple[datetime.datetime, str]] = {}
    for name, es in threads.items():
        for e in es:
            a = e["author"]
            if a not in last or e["t"] > last[a][0]:
                last[a] = (e["t"], name)
    for a, (t, th) in sorted(last.items(), key=lambda kv: kv[1][0]):
        print(f"{a:24s} last seen {t:%Y-%m-%d %H:%M} in {th}")

    print("\n=== entries per calendar day (pace) ===")
    day: collections.Counter = collections.Counter()
    for es in threads.values():
        for e in es:
            day[e["t"].date()] += 1
    for d in sorted(day):
        print(f"{d} {'#' * min(day[d], 60)} {day[d]}")


def main() -> int:
    threads_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else THREADS_DIR
    if not threads_dir.is_dir():
        print(f"fatigue_metrics: no thread directory at {threads_dir}", file=sys.stderr)
        return 0  # advisory: never a fail-bit
    report(collect(threads_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
