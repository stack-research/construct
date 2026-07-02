"""Close gate — the milestone close as a computed ledger artifact (SPEC_CLOSE_GATE v0.1).

Single writer of `runs/closes/closes.jsonl`. A `close_ruled` row refuses to exist
until four legs hold (fail-closed; the failing legs are named and ledgered):

  1. contribution — >=1 intervention row with `claimed_target_milestone == M` whose
     computed verdict has outcome in {landed, blocked}, not superseded by a later
     `reversal_of`, and packet-grounded (target_artifact in the stamped manifest, or
     a scorer_evidence pointer whose ledger is in the manifest). F1's forcing function.
  2. packet — the manifest is HARNESS-EXPANDED from declared artifact classes (globs
     for enumerable classes: the S1 fix — a hand list can silently drop the third
     sidecar; a glob cannot) and re-hashes to the stamped packet_sha256. Certifies
     immutability + declared-class completeness, never total completeness (disclosed).
  3. coverage — >=K distinct participants NOT in the stamped `builders` set posted in
     the stamp's thread after the stamp, each referencing the packet hash (first 8 hex)
     in the entry text. Derived from the thread record, never asserted. Reader-agnostic.
  4. rest — wall-clock floor. Output vocabulary is `opportunity_window_met`, never
     "read latency proven"; no cell_verdict may consume this leg. Moderator-calibrated
     POLICY (dan-informed default), exempt-by-design from the latency-as-evidence ban.

Override (`--override "<reason>"`) bypasses legs 3-4 ONLY, ledgered. Every invocation
writes close_requested; every failure writes close_refused with the failing legs —
the gate instruments its own non-use (heir-audit B3: F1's dark gap must not recur here).

All `ts` fields are stamped by the harness at write time; caller-supplied ts is
stripped (the X1 harness-authorized-tick law applied to process events).

Usage:
  python -m harness.check_close stamp <milestone> --classes classes.json \
      --builders claude/fable-5 --thread heir-audit --requested-by dan
  python -m harness.check_close observe <milestone>     # derive review rows
  python -m harness.check_close rule <milestone> --ruled-by dan [--override "reason"]
  python -m harness.check_close status
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

from .ledger import Ledger

REPO = Path(__file__).resolve().parent.parent
CLOSES = REPO / "runs" / "closes" / "closes.jsonl"
CONTRIBUTIONS = REPO / "runs" / "m1_5" / "contributions.jsonl"
THREADS = REPO / ".substrate" / "threads"

DEFAULT_K = 2                      # coverage leg: distinct non-builder reviewers
DEFAULT_MIN_INTERVAL_S = 12 * 3600  # rest leg: moderator-calibrated policy (SPEC §3.4)
OVERRIDE_LINE = (1, 5, 10)          # >1/5 of rulings overridden across any 10 attempts

_ENTRY = re.compile(r"^(\d{8}T\d{9}Z)__(.+?)(__no-op)?\.md$")


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str) -> datetime.datetime:
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc)


def _parse_entry_ts(s: str) -> datetime.datetime:
    return datetime.datetime.strptime(s, "%Y%m%dT%H%M%S%fZ").replace(
        tzinfo=datetime.timezone.utc)


class CloseGate:
    """Paths are injectable for wire tests; defaults are the live lab."""

    def __init__(self, closes: Path = CLOSES, contributions: Path = CONTRIBUTIONS,
                 threads_dir: Path = THREADS, repo: Path = REPO):
        self.ledger = Ledger(closes)
        self.contributions = contributions
        self.threads_dir = threads_dir
        self.repo = repo

    # -- writing (the harness stamps ts; caller ts is stripped) ---------------

    def _write(self, row: dict) -> dict:
        row = {k: v for k, v in row.items() if k != "ts"}  # blocker 3: no caller ts
        self.ledger.write(row)
        return self.ledger.rows()[-1]

    # -- packet ----------------------------------------------------------------

    def expand_classes(self, artifact_classes: dict) -> list[str]:
        """Harness-expanded manifest. A literal list passes through; a string is a
        glob the HARNESS expands (the S1 fix). An empty expansion fails loud —
        an evidence class with zero artifacts is never silently fine."""
        manifest: list[str] = []
        for cls, spec in sorted(artifact_classes.items()):
            paths = sorted(str(p.relative_to(self.repo))
                           for p in self.repo.glob(spec)) if isinstance(spec, str) else list(spec)
            if not paths:
                raise ValueError(f"artifact class {cls!r} expanded to zero artifacts — "
                                 "refusing to stamp an empty evidence class")
            manifest.extend(paths)
        return sorted(set(manifest))

    def packet_sha(self, manifest: list[str]) -> str:
        h = hashlib.sha256()
        for rel in sorted(manifest):
            p = self.repo / rel
            if not p.exists():
                raise ValueError(f"manifest artifact missing on disk: {rel}")
            h.update(rel.encode() + b"\x00" + hashlib.sha256(p.read_bytes()).digest())
        return h.hexdigest()

    def stamp(self, milestone: str, artifact_classes: dict, builders: list[str],
              thread: str, requested_by: str) -> dict:
        manifest = self.expand_classes(artifact_classes)
        return self._write({
            "kind": "close_packet_stamped", "milestone": milestone,
            "artifact_classes": artifact_classes, "packet_manifest": manifest,
            "packet_sha256": self.packet_sha(manifest),
            "builders": builders, "thread": thread, "requested_by": requested_by,
        })

    def _latest_stamp(self, milestone: str) -> dict | None:
        stamps = [r for r in self.ledger.rows()
                  if r.get("kind") == "close_packet_stamped" and r.get("milestone") == milestone]
        return stamps[-1] if stamps else None

    # -- coverage (derived, never asserted) -------------------------------------

    def observe_reviews(self, milestone: str) -> list[dict]:
        stamp = self._latest_stamp(milestone)
        if stamp is None:
            return []
        stamp_ts = _parse_iso(stamp["ts"])
        packet_ref = stamp["packet_sha256"][:8]
        seen = {r["thread_entry_ts"] for r in self.ledger.rows()
                if r.get("kind") == "close_review_observed" and r.get("milestone") == milestone}
        tdir = self.threads_dir / stamp["thread"]
        observed = []
        if not tdir.is_dir():
            return []
        for f in sorted(tdir.iterdir()):
            m = _ENTRY.match(f.name)
            if not m or m.group(3):
                continue
            entry_ts, author = m.group(1), m.group(2).replace("%2F", "/")
            if entry_ts in seen or author in stamp["builders"]:
                continue
            if _parse_entry_ts(entry_ts) <= stamp_ts:
                continue
            if packet_ref not in f.read_text(encoding="utf-8", errors="replace"):
                continue  # unbound room traffic never counts (v0.1 hard requirement)
            observed.append(self._write({
                "kind": "close_review_observed", "milestone": milestone,
                "reviewer": author, "thread_entry_ts": entry_ts, "packet_ref": packet_ref,
            }))
        return observed

    # -- leg 1: contribution ----------------------------------------------------

    def _contribution_leg(self, milestone: str, manifest: list[str]) -> tuple[bool, dict]:
        rows = Ledger(self.contributions).rows() if self.contributions.exists() else []
        ivs = {r["intervention_id"]: r for r in rows if r.get("kind") == "intervention"}
        superseded = {r.get("reversal_of") for r in ivs.values() if r.get("reversal_of")}
        verdicts = {r["intervention_id"]: r for r in rows
                    if r.get("kind") == "contribution_verdict"}
        qualifying = []
        for iv_id, iv in ivs.items():
            if iv.get("claimed_target_milestone") != milestone or iv_id in superseded:
                continue
            v = verdicts.get(iv_id)
            if v is None or v.get("outcome") not in ("landed", "blocked"):
                continue  # forward + terminal only (B1: excludes reversed/passenger)
            grounded = v.get("target_artifact") in manifest or any(
                p.get("type") == "scorer_evidence" and p.get("ledger") in manifest
                for p in iv.get("artifact_pointers", []))
            if grounded:
                qualifying.append(iv_id)
        return bool(qualifying), {"qualifying_interventions": qualifying}

    # -- the predicate -----------------------------------------------------------

    def rule(self, milestone: str, ruled_by: str, override: str | None = None,
             k: int = DEFAULT_K, min_interval_s: float = DEFAULT_MIN_INTERVAL_S,
             now: datetime.datetime | None = None) -> dict:
        now = now or _now()
        self._write({"kind": "close_requested", "milestone": milestone, "by": ruled_by})
        failed: list[str] = []
        evidence: dict = {}

        stamp = self._latest_stamp(milestone)
        if stamp is None:
            failed.extend(["packet", "contribution", "coverage", "rest"])
            evidence["packet"] = {"error": "no close_packet_stamped row"}
        else:
            # leg 2 — packet: re-expand + re-hash (immutability + class-completeness)
            try:
                manifest = self.expand_classes(stamp["artifact_classes"])
                sha = self.packet_sha(manifest)
                if sha != stamp["packet_sha256"] or manifest != stamp["packet_manifest"]:
                    failed.append("packet")
                    evidence["packet"] = {"stamped": stamp["packet_sha256"], "current": sha,
                                          "note": "evidence changed after stamp — re-stamp"}
            except ValueError as e:
                failed.append("packet")
                manifest = stamp["packet_manifest"]
                evidence["packet"] = {"error": str(e)}

            # leg 1 — contribution (never overridable)
            ok, ev = self._contribution_leg(milestone, stamp["packet_manifest"])
            evidence["contribution"] = ev
            if not ok:
                failed.append("contribution")

            # leg 3 — coverage (overridable)
            self.observe_reviews(milestone)
            reviewers = {r["reviewer"] for r in self.ledger.rows()
                         if r.get("kind") == "close_review_observed"
                         and r.get("milestone") == milestone
                         and r.get("packet_ref") == stamp["packet_sha256"][:8]}
            evidence["coverage"] = {"reviewers": sorted(reviewers), "k_required": k}
            if len(reviewers) < k:
                failed.append("coverage")

            # leg 4 — rest (overridable; POLICY vocabulary, never evidence)
            window_s = (now - _parse_iso(stamp["ts"])).total_seconds()
            met = window_s >= min_interval_s
            evidence["rest"] = {"opportunity_window_met": met,
                                "window_hours": round(window_s / 3600, 2),
                                "min_interval_hours": round(min_interval_s / 3600, 2),
                                "disclosure": "moderator-calibrated policy; prices nothing, "
                                              "scores nothing; no cell_verdict may consume this"}
            if not met:
                failed.append("rest")

        if override is not None:
            bypassed = [l for l in failed if l in ("coverage", "rest")]
            failed = [l for l in failed if l not in ("coverage", "rest")]
        else:
            bypassed = []

        if failed:
            return self._write({"kind": "close_refused", "milestone": milestone,
                                "by": ruled_by, "failed_legs": sorted(failed),
                                "evidence": evidence})
        return self._write({"kind": "close_ruled", "milestone": milestone,
                            "ruled_by": ruled_by,
                            "packet_sha256": stamp["packet_sha256"],
                            "override": ({"reason": override, "bypassed_legs": bypassed}
                                         if override is not None else None),
                            "evidence": evidence})

    # -- loses-metric + self-instrumentation (B3) --------------------------------

    def status(self) -> dict:
        rows = self.ledger.rows()
        attempts = [r for r in rows if r.get("kind") in ("close_ruled", "close_refused")]
        recent = attempts[-OVERRIDE_LINE[2]:]
        overridden = [r for r in recent if r.get("kind") == "close_ruled" and r.get("override")]
        stamps = {}
        for r in rows:
            if r.get("kind") == "close_packet_stamped":
                stamps[r["milestone"]] = r
        ruled = {r["milestone"] for r in rows if r.get("kind") == "close_ruled"}
        open_packets = {m: {"age_hours": round((_now() - _parse_iso(s["ts"])).total_seconds() / 3600, 1),
                            "sha": s["packet_sha256"][:8]}
                        for m, s in stamps.items() if m not in ruled}
        ruled_recent = sum(1 for r in recent if r["kind"] == "close_ruled")
        return {
            "attempts": len(attempts),
            "refused": sum(1 for r in attempts if r["kind"] == "close_refused"),
            "ruled": sum(1 for r in attempts if r["kind"] == "close_ruled"),
            "overridden_in_last_10_attempts": len(overridden),
            "embarrassment_line": f">{OVERRIDE_LINE[0]}/{OVERRIDE_LINE[1]} of rulings over "
                                  f"{OVERRIDE_LINE[2]} attempts (SPEC §5; post-hoc, retunable)",
            # crossed when overrides exceed 1/5 of recent rulings (attempt-windowed, B3)
            "line_crossed": len(overridden) * OVERRIDE_LINE[1] > ruled_recent * OVERRIDE_LINE[0],
            "open_packets": open_packets,
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("stamp")
    s.add_argument("milestone")
    s.add_argument("--classes", required=True, help="JSON file: {class: glob-or-list}")
    s.add_argument("--builders", nargs="+", required=True)
    s.add_argument("--thread", required=True)
    s.add_argument("--requested-by", required=True)

    o = sub.add_parser("observe")
    o.add_argument("milestone")

    r = sub.add_parser("rule")
    r.add_argument("milestone")
    r.add_argument("--ruled-by", required=True)
    r.add_argument("--override", default=None,
                   help="bypass legs 3-4 ONLY, with a ledgered reason")
    r.add_argument("--k", type=int, default=DEFAULT_K)

    sub.add_parser("status")
    args = ap.parse_args()
    gate = CloseGate()

    if args.cmd == "stamp":
        row = gate.stamp(args.milestone, json.loads(Path(args.classes).read_text()),
                         args.builders, args.thread, args.requested_by)
        print(json.dumps(row, indent=2, sort_keys=True))
        return 0
    if args.cmd == "observe":
        for row in gate.observe_reviews(args.milestone):
            print(json.dumps(row, sort_keys=True))
        return 0
    if args.cmd == "rule":
        row = gate.rule(args.milestone, args.ruled_by, override=args.override, k=args.k)
        print(json.dumps(row, indent=2, sort_keys=True))
        return 0 if row["kind"] == "close_ruled" else 1
    if args.cmd == "status":
        print(json.dumps(gate.status(), indent=2, sort_keys=True))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
