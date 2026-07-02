"""Close-latency gate — the read-latency instrument (heir-audit S4, glm-5's form).

dan's slow, late, outside reads have this lab's best catch record; the heir-audit
fatigue metrics showed closes moving faster than that sensor can fire (four
milestone closes in three days; X1-retire + X2-LB-close on one day). glm-5's
convergence-breaking push: the read-latency gate must be an INSTRUMENT with a
computable event pair, not a vibe or a single-point sensor.

The forward mechanism (v0): a close emits two witnessed events into the thread
record, and the interval between them is the moderator's read latency —

    close_packet_stamped   the evidence packet is frozen and offered for review
    close_ruled            the moderator issues the full-close ruling

`close_latency_seconds = close_ruled.ts - close_packet_stamped.ts`. Under a
predeclared `min_interval`, a ruling stamped too soon after its packet is a
`fast_close` advisory row — NOT a block (route_watch discipline: this instrument
never gates, always exits 0). The interval is *logical* over the witnessed
timestamps, not wall-clock enforcement — the moderator may read for a day and
rule in a minute; the gate measures the offered read window, and a human who
overrides it does so on the record.

v0 scope + honest limit (the route_watch §9.4 base-rate lesson): the two event
kinds do not yet exist in the historical ledger, so retrospective mode infers
candidate packet/ruling entries from thread text by marker match (`--retro`).
Inference is advisory and cry-wolf-prone exactly as route_watch is; the numbers
are trend-grade, not verdict-grade. The forward path is explicit event emission
(`emit_event`), where the interval is exact and un-inferred. Prospective events,
not retrofitted string-matching, are how this earns verdict standing.
"""

from __future__ import annotations

import datetime
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

THREADS_DIR = Path(".substrate/threads")
DEFAULT_MIN_INTERVAL_S = 12 * 3600  # a biologic interval; predeclared, tune on review

PACKET_MARKERS = (
    r"packet", r"evidence (is )?in", r"run-debt (is )?paid", r"ready (for|to) (close|rule)",
    r"close[- ]gate", r"result-review packet",
)
RULING_MARKERS = (
    r"moderator('s)? (full-)?close", r"full-close ruling", r"i (hereby )?close",
    r"closed by moderator", r"dan's (moderator )?close", r"ruling: close",
)


@dataclass
class CloseLatencyEvent:
    kind: str  # close_packet_stamped | close_ruled
    milestone: str
    ts: str  # ISO8601 Z
    thread: str
    by: str  # participant who stamped/ruled
    packet_sha256: str | None = None  # binds a ruling to the exact packet it read


def emit_event(ev: CloseLatencyEvent, out: Path) -> None:
    """Forward path: append a witnessed event (append-only; the harness stamps ts)."""
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"kind_row": "close_latency_event", **asdict(ev)}) + "\n")


def score_pair(packet: CloseLatencyEvent, ruling: CloseLatencyEvent,
               min_interval_s: float = DEFAULT_MIN_INTERVAL_S) -> dict:
    dt = (_ts(ruling.ts) - _ts(packet.ts)).total_seconds()
    # codex labeling boundary (SPEC_CLOSE_GATE §3.4): opportunity window, never
    # "read latency proven"; no cell_verdict may consume this vocabulary.
    verdict = "fast_close" if dt < min_interval_s else "opportunity_window_met"
    row = {
        "kind_row": "close_latency_verdict",
        "milestone": ruling.milestone,
        "close_latency_seconds": dt,
        "close_latency_hours": round(dt / 3600, 2),
        "min_interval_hours": round(min_interval_s / 3600, 2),
        "verdict": verdict,  # advisory, never a fail-bit
        "packet_by": packet.by,
        "ruling_by": ruling.by,
    }
    if packet.packet_sha256 and ruling.packet_sha256 and packet.packet_sha256 != ruling.packet_sha256:
        row["packet_mismatch"] = True  # ruling read a different packet than was stamped
    return row


def _ts(s: str) -> datetime.datetime:
    return datetime.datetime.strptime(s, "%Y%m%dT%H%M%S%fZ")


_ENTRY = re.compile(r"^(\d{8}T\d{9}Z)__(.+?)(__no-op)?\.md$")


def retro_scan(threads_dir: Path, min_interval_s: float = DEFAULT_MIN_INTERVAL_S) -> list[dict]:
    """Advisory retrospective mode — infer packet/ruling entries by marker match.

    Cry-wolf-prone (route_watch §9.4): reports the *first* packet marker and the
    *first* later ruling marker per thread. Trend-grade, not verdict-grade.
    """
    pk = re.compile("|".join(PACKET_MARKERS), re.I)
    rk = re.compile("|".join(RULING_MARKERS), re.I)
    rows = []
    for tdir in sorted(threads_dir.iterdir()):
        if not tdir.is_dir():
            continue
        packet = ruling = None
        for f in sorted(tdir.iterdir()):
            m = _ENTRY.match(f.name)
            if not m:
                continue
            ts, by = m.group(1), m.group(2).replace("%2F", "/")
            text = f.read_text(encoding="utf-8", errors="replace")
            if packet is None and pk.search(text):
                packet = (ts, by)
            if pk.search(text) is None and rk.search(text) and packet is not None and ruling is None:
                ruling = (ts, by)
        if packet and ruling:
            dt = (_ts(ruling[0]) - _ts(packet[0])).total_seconds()
            rows.append({
                "thread": tdir.name,
                "inferred_packet": f"{packet[1]} @ {packet[0]}",
                "inferred_ruling": f"{ruling[1]} @ {ruling[0]}",
                "close_latency_hours": round(dt / 3600, 2),
                "min_interval_hours": round(min_interval_s / 3600, 2),
                # glm-5 review blocker 4: retro vocabulary DIVERGES from forward —
                # a stripped table can never read as verdict-grade.
                "verdict": ("retro_fast_close_hint" if dt < min_interval_s
                            else "retro_window_met_hint"),
                "disclosure": "INFERRED by marker match — advisory, not verdict-grade (route_watch §9.4)",
            })
    return rows


def main() -> int:
    retro = "--retro" in sys.argv
    if not retro:
        print("close_latency: forward mode needs close_latency_event rows; none wired yet.")
        print("Run `--retro` for the advisory retrospective scan over the thread record.")
        print("Forward path: emit close_packet_stamped + close_ruled per close (see module docstring).")
        return 0
    rows = retro_scan(THREADS_DIR)
    print("=== close-latency (INFERRED — advisory, trend-grade only) ===")
    for r in rows:
        print(f"{r['thread']:12s} {r['verdict']:12s} {r['close_latency_hours']:>7.2f}h "
              f"(packet: {r['inferred_packet']}  ruling: {r['inferred_ruling']})")
    fast = [r for r in rows if r["verdict"] == "fast_close"]
    print(f"\n{len(fast)}/{len(rows)} inferred closes under the {DEFAULT_MIN_INTERVAL_S/3600:.0f}h read window.")
    print("Advisory only. The forward instrument (explicit events) is how this earns verdict standing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
