"""occlusion_watch — X4 session-seam witness (SPEC_X4 §11): Layer-1 emitter + Layer-2.

The session-seam sibling of `route_watch` (the declared-read seam). `route_watch` asks
*"what ancestor is missing from this DECLARED-READ confidence?"*; `occlusion_watch` asks
the same across a SESSION seam: did a later-session (cold) agent use a confidence whose
grounding ancestor it did not re-route this session?

**Layers (§11).** Layer-1 *emits ordering facts + disqualifiers, never a verdict*.
Layer-2 (`compute_outcomes`) computes catches-vs-flinches from lineage order — advisory,
NOT a fourth scorer / no cell_verdict (§5). No judicial robes: always exits 0.

**Witness invariant (§2).** Timestamps are stamped by the substrate (entry filenames),
git (`%cI`), and the harness `Ledger` — never by the watched agent. The precommit that
arms this watch is itself a witnessed substrate entry (un-backdatable); this module READS
it, never authors it. Keys + paths are read from that entry, so they stay precommitted —
`borrowed_foresight` (§5) cannot enter through code.

**Honest scope (§8/§11).** Externalized surfaces only. Confidence that hardens without
leaving an enumerable trace — the cold-author lower bound (hermes, thread-x4c) — is out
of reach, by the same refusal that bars self-report.

**Population (from the precommit's `population_rule`, mechanically enumerable):**
  S1  every substrate entry authored by <watched_agent> in <thread> after precommit_ts
  S2  every committed diff touching the declared paths after precommit_ts (v0.1: ADDED
      lines, git-stamped %cI as the witnessed ts)

**candidate_key:** literal / conservative (the base-rate lesson, `runs/x4/base_rate.md`):
distinctive compounds only, exact substring; uncertain => DO NOT MATCH (under-claim
embarrasses; over-match steals — flinch-theft, §5).

**Session identity (v0.1, DISCLOSED proxy).** Substrate has no session-id, so a session
boundary is a gap > SESSION_GAP over the witnessed timeline (substrate + git). Fail-
toward-under-claim: a surface not clearly across a gap stays `same_session` (calibration,
NOT earned-eligible) — the proxy can only under-claim a catch, never invent one.

Usage:
  uv run --no-project python -m harness.occlusion_watch                 # Layer-1, print
  uv run --no-project python -m harness.occlusion_watch --write         # append Layer-1 rows
  uv run --no-project python -m harness.occlusion_watch --outcomes      # Layer-2, compute
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .ledger import Ledger

ROOT = Path(__file__).resolve().parent.parent
THREADS_DIR = ROOT / ".substrate" / "threads"
LEDGER = ROOT / "runs" / "x4" / "occlusion_watch.jsonl"

PRECOMMIT_MARKER = "ARM-NOW PRECOMMIT"
TURN_RE = re.compile(r"^(?P<ts>\d{8}T\d{6}\d*Z)__(?P<author>.+)\.md$")
FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
KEY_RE = re.compile(r'"([^"]+)"\s*(?:→|->)')  # candidate keys: "key" → §N
PATH_RE = re.compile(r"(harness/[\w./*-]+|notes/SPEC_X4[\w./*-]+)")

SESSION_GAP = timedelta(hours=4)        # v0.1 disclosed session-boundary heuristic
FALSE_ALARM_WINDOW = timedelta(days=7)  # an unnamed work_product observation older than this is stale
NOISY_THRESHOLD = 0.5                   # organ-level cry_wolf flag: observed / examined


@dataclass(frozen=True)
class Precommit:
    precommit_ts: str                 # the entry's filename ts — substrate-witnessed
    watched_agent: str
    thread: str
    candidate_keys: tuple[str, ...]   # literal, precommitted in the witnessed entry
    declared_paths: tuple[str, ...]   # S2 globs
    entry_path: str


@dataclass(frozen=True)
class Surface:
    ref: str    # path relative to ROOT, or git:<sha>
    ts: str     # witnessed timestamp (substrate filename or git %cI)
    author: str
    text: str


def _body(path: Path) -> str:
    return FRONTMATTER.sub("", path.read_text(), count=1)


def _rel(p: Path) -> str:
    """Repo-relative path when under ROOT; otherwise the path as-is (test tempdirs)."""
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def _parse_ts(ts: str) -> datetime | None:
    """Parse a witnessed ts. Substrate compact ('20260626T173754620Z') or git ISO
    ('2026-06-26T17:37:54+00:00'). Seconds precision is plenty for session gaps."""
    ts = (ts or "").strip()
    m = re.match(r"(\d{8}T\d{6})", ts)
    if m:
        return datetime.strptime(m.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _session_index(target: datetime, timeline: list[datetime]) -> int:
    """Session index of `target` within a timeline segmented by gaps > SESSION_GAP."""
    pts = sorted(set(timeline))
    if not pts:
        return 0
    seg = {pts[0]: 0}
    idx = 0
    for i in range(1, len(pts)):
        if pts[i] - pts[i - 1] > SESSION_GAP:
            idx += 1
        seg[pts[i]] = idx
    chosen = 0
    for t in pts:
        if t <= target:
            chosen = seg[t]
        else:
            break
    return chosen


def load_precommit(
    thread: str, watched_agent: str = "claude", threads_dir: Path = THREADS_DIR
) -> Precommit | None:
    """The witnessed ARM-NOW PRECOMMIT entry authored by the watched agent. Its filename
    timestamp IS `precommit_ts` (un-backdatable). Keys + paths parsed from the body, so
    they are precommitted (no retrofit). Returns None if nothing is armed."""
    tdir = threads_dir / thread
    if not tdir.is_dir():
        return None
    for f in sorted(tdir.glob("*.md")):
        m = TURN_RE.match(f.name)
        if not m or m["author"] != watched_agent:
            continue
        text = f.read_text()
        if PRECOMMIT_MARKER not in text:
            continue
        keys = tuple(dict.fromkeys(KEY_RE.findall(text)))     # ordered-unique
        paths = tuple(dict.fromkeys(PATH_RE.findall(text)))
        return Precommit(
            precommit_ts=m["ts"], watched_agent=watched_agent, thread=thread,
            candidate_keys=keys, declared_paths=paths, entry_path=_rel(f),
        )
    return None


def enumerate_s1(pc: Precommit, threads_dir: Path = THREADS_DIR) -> list[Surface]:
    """S1: entries by the watched agent in the thread, strictly AFTER precommit_ts (the
    precommit is the anchor, never itself a watched surface)."""
    tdir = threads_dir / pc.thread
    out: list[Surface] = []
    for f in sorted(tdir.glob("*.md")):
        m = TURN_RE.match(f.name)
        if not m or m["author"] != pc.watched_agent or m["ts"] <= pc.precommit_ts:
            continue
        out.append(Surface(_rel(f), m["ts"], m["author"], _body(f)))
    return out


def enumerate_s2(pc: Precommit, root: Path = ROOT) -> list[Surface]:
    """S2: committed diffs touching the declared paths AFTER precommit_ts. The ADDED lines
    are the surface (new confident code/prose); the commit's git-stamped date (%cI) is the
    witnessed ts. Globs in declared_paths are git pathspecs. Returns [] outside a git repo
    (e.g. test tempdirs) — graceful, never raises."""
    pdt = _parse_ts(pc.precommit_ts)
    if pdt is None or not pc.declared_paths:
        return []
    try:
        log = subprocess.run(
            ["git", "-C", str(root), "log", "--since", pdt.isoformat(),
             "--format=%H\t%cI", "--", *pc.declared_paths],
            capture_output=True, text=True, check=True,
        ).stdout
    except Exception:
        return []
    out: list[Surface] = []
    for line in log.splitlines():
        sha, _, cdate = line.partition("\t")
        cdt = _parse_ts(cdate)
        if not sha or cdt is None or cdt <= pdt:
            continue  # strictly after the precommit
        diff = subprocess.run(
            ["git", "-C", str(root), "show", sha, "--format=", "--unified=0", "--", *pc.declared_paths],
            capture_output=True, text=True,
        ).stdout
        added = "\n".join(
            ln[1:] for ln in diff.splitlines()
            if ln.startswith("+") and not ln.startswith("+++")
        )
        out.append(Surface(ref=f"git:{sha[:9]}", ts=cdate, author=pc.watched_agent, text=added))
    return out


def examine(text: str, keys: tuple[str, ...]) -> list[str]:
    """Literal/conservative match: exact case-insensitive substring of the distinctive
    compound. 'witness' alone never matches 'witness invariant' — only the full key."""
    low = text.lower()
    return [k for k in keys if k.lower() in low]


def seam_distance(surface_ts: str, precommit_ts: str, timeline: list[datetime] | None = None) -> str:
    """`same_session` (calibration) vs `later_session` (first earned-eligible, §11).

    With a `timeline` (the witnessed watched timestamps) the session boundary is a gap
    > SESSION_GAP — the v0.1 disclosed proxy, fail-toward-under-claim. Without one, falls
    back to the v0 UTC-calendar-date proxy (kept for the 2-arg callers/tests)."""
    if timeline is not None:
        sdt, pdt = _parse_ts(surface_ts), _parse_ts(precommit_ts)
        if sdt is not None and pdt is not None:
            return ("later_session" if _session_index(sdt, timeline) > _session_index(pdt, timeline)
                    else "same_session")
    return "same_session" if surface_ts[:8] == precommit_ts[:8] else "later_session"


def observe(pc: Precommit, threads_dir: Path = THREADS_DIR, root: Path = ROOT) -> list[dict]:
    """Emit Layer-1 rows for S1 (substrate prose) AND S2 (committed diffs): per surface a
    `route_watch_surface_expected` + `route_watch_surface_examined`, plus
    `occlusion_watch_observed` per literal key-hit. NEVER an outcome verdict (Layer 2,
    §10). seam_distance uses the gap-based session proxy over the witnessed timeline
    (precommit ∪ S1 ∪ S2)."""
    surfaces = (
        [("S1", s) for s in enumerate_s1(pc, threads_dir)]
        + [("S2", s) for s in enumerate_s2(pc, root)]
    )
    timeline = [dt for dt in
                [_parse_ts(pc.precommit_ts)] + [_parse_ts(s.ts) for _, s in surfaces]
                if dt is not None]

    rows: list[dict] = []
    for pop, s in surfaces:
        rows.append({
            "row": "route_watch_surface_expected", "seam": "session",
            "surface_ref": s.ref, "surface_ts": s.ts,
            "population_rule_ref": pop, "precommit_ts": pc.precommit_ts,
        })
        hits = examine(s.text, pc.candidate_keys)
        rows.append({
            "row": "route_watch_surface_examined", "surface_ref": s.ref,
            "population_rule_ref": pop,
            "candidate_count": len(hits), "wrote_observed_rows": bool(hits),
        })
        for k in hits:
            rows.append({
                "row": "occlusion_watch_observed", "seam": "session",
                "candidate_key": k, "match": "literal",
                "surface_ref": s.ref, "surface_ts": s.ts, "population_rule_ref": pop,
                "seam_distance": seam_distance(s.ts, pc.precommit_ts, timeline),
                "fire_authority": "agent_fired-under-precommitment",
                "watched_agent": pc.watched_agent,
                "watched_agent_is_author": True,  # S1/S2 are the watched agent's own work
                "surface_basis": "work_product",
                "precommit_ts": pc.precommit_ts,
                "evidence_status": "observed_only_no_outcome",  # Layer 1; earned is §10/Layer 2
            })
    return rows


def read_ledger(path: Path = LEDGER) -> list[dict]:
    """The append-only watch ledger: Layer-1 rows + external human_named_candidate rows."""
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def compute_outcomes(rows: list[dict], *, now: datetime | None = None) -> tuple[list[dict], dict]:
    """Layer-2 (§4): COMPUTE occlusion_watch_outcome records from the ledger's lineage
    order — catches vs flinches. NOT a fourth judicial scorer (§5: no fourth scorer, no
    cell_verdict); occlusion_watch's own advisory computation. The rows' hand-written
    `classification`/`tally` are IGNORED (R5: computed, never asserted).

    `earned` is structurally unmanufacturable from this session:
      - the namer must be EXTERNAL (watched_agent_is_author == False) — §2;
      - a matching `occlusion_watch_observed` row must be surface_basis=work_product (§4),
        seam_distance >= later_session, and PREDATE the naming (observed_ts < named_ts);
      - `earned` additionally needs action evidence (did_it_change_attention_or_action);
        explicit no-action => `passenger`; evidence-unknown => `early` (catch pending).
    Organ did not see it first => flinch. v0.1 also computes (disclosed heuristics):
      - `false_alarm`: a work_product observation never named and older than
        FALSE_ALARM_WINDOW (stale cry-wolf);
      - `noisy`: organ-level flag when observed / examined exceeds NOISY_THRESHOLD."""
    now = now or datetime.now(timezone.utc)
    observed = [r for r in rows if r.get("row") == "occlusion_watch_observed"]
    examined = [r for r in rows if r.get("row") == "route_watch_surface_examined"]
    named = [r for r in rows if r.get("row") in ("human_named_candidate", "flinch_observed")]
    outcomes: list[dict] = []
    matched_obs_keys: set[str] = set()

    for n in named:
        named_ts = n.get("named_ts") or ""
        nk = (n.get("candidate_ref") or n.get("candidate") or "").lower()
        external = n.get("watched_agent_is_author") is False
        predated = [
            o for o in observed
            if (o.get("candidate_key") or "").lower() in nk
            and o.get("surface_basis") == "work_product"
            and o.get("seam_distance") in ("later_session", "downstream_artifact")
            and (o.get("observed_ts") or o.get("ts"))
            and (o.get("observed_ts") or o.get("ts") or "") < named_ts
        ]
        seen_for_key = [o for o in observed if (o.get("candidate_key") or "").lower() in nk]
        for o in seen_for_key:
            matched_obs_keys.add((o.get("candidate_key") or "").lower())
        if not external:
            verdict = "not_engaged"               # the beneficiary cannot name (§2)
        elif predated:
            if bool(n.get("evidence")) and bool(n.get("did_it_change_attention_or_action")):
                verdict = "earned"                # observed-first + acted => a catch
            elif n.get("did_it_change_attention_or_action") is False:
                verdict = "passenger"             # observed-first but explicitly changed nothing
            else:
                verdict = "early"                 # observed-first, evidence pending
        elif seen_for_key:
            verdict = "late"                      # organ saw it, but not first (borrowed_foresight)
        else:
            verdict = "unmatched_human_flinch"    # organ blind — a flinch
        outcomes.append({
            "row": "occlusion_watch_outcome",
            "candidate": n.get("candidate") or n.get("candidate_ref"),
            "named_ts": named_ts,
            "observed_ts": predated[0].get("observed_ts") if predated else None,
            "seam_distance": n.get("seam_distance"),
            "verdict": verdict,
            "computed_from": "lineage_order",     # not the row's self-asserted classification
        })

    # false_alarm: a work_product observation never named and stale past the window
    for o in observed:
        key = (o.get("candidate_key") or "").lower()
        if o.get("surface_basis") != "work_product" or key in matched_obs_keys:
            continue
        o_dt = _parse_ts(o.get("observed_ts") or o.get("ts") or "")
        if o_dt is not None and (now - o_dt) > FALSE_ALARM_WINDOW:
            outcomes.append({
                "row": "occlusion_watch_outcome", "candidate": o.get("candidate_key"),
                "named_ts": None, "observed_ts": o.get("observed_ts") or o.get("ts"),
                "seam_distance": o.get("seam_distance"), "verdict": "false_alarm",
                "computed_from": "lineage_order",
            })

    tally = {"catches": 0, "flinches": 0, "early": 0, "late": 0,
             "passenger": 0, "false_alarm": 0, "not_engaged": 0}
    for o in outcomes:
        v = o["verdict"]
        if v == "earned":
            tally["catches"] += 1
        elif v == "unmatched_human_flinch":
            tally["flinches"] += 1
        else:
            tally[v] = tally.get(v, 0) + 1
    # noisy: organ-level cry_wolf flag (disclosed heuristic) — fires per examined surface
    n_examined = len(examined) or sum(1 for _ in observed)  # examined rows, else fall back
    fire_rate = round(len(observed) / n_examined, 3) if n_examined else 0.0
    tally["fire_rate"] = fire_rate
    tally["noisy"] = fire_rate > NOISY_THRESHOLD
    return outcomes, tally


def run(
    *, write: bool = False, thread: str = "thread-x4c",
    threads_dir: Path = THREADS_DIR, root: Path = ROOT,
) -> tuple[Precommit | None, list[dict]]:
    pc = load_precommit(thread, threads_dir=threads_dir)
    if pc is None:
        return None, []
    rows = observe(pc, threads_dir, root)
    if write and rows:
        ledger = Ledger(LEDGER)
        for r in rows:
            ledger.write(r)  # Ledger prepends harness-stamped `ts` = observed_ts (§2)
    return pc, rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="X4 occlusion_watch — session-seam witness (SPEC_X4 §11)",
    )
    ap.add_argument("--thread", default="thread-x4c", help="substrate thread holding the arm-now precommit")
    ap.add_argument("--write", action="store_true", help="append Layer-1 rows to the ledger (observed_ts harness-stamped)")
    ap.add_argument("--outcomes", action="store_true", help="Layer-2: COMPUTE catches-vs-flinches from the ledger lineage (advisory; no verdict-gate, §5)")
    args = ap.parse_args(argv)

    if args.outcomes:
        outcomes, tally = compute_outcomes(read_ledger())
        print("occlusion_watch — Layer-2 outcomes (COMPUTED from lineage; advisory, no cell_verdict, §5)")
        print(f"  catches {tally['catches']}   flinches {tally['flinches']}   early {tally.get('early', 0)}   "
              f"late {tally.get('late', 0)}   passenger {tally.get('passenger', 0)}   "
              f"false_alarm {tally.get('false_alarm', 0)}   not_engaged {tally.get('not_engaged', 0)}")
        print(f"  fire_rate {tally['fire_rate']}   noisy {tally['noisy']}")
        for o in outcomes:
            print(f"    • [{o['verdict']}] {o['candidate']}  (named {o['named_ts']})")
        if tally["catches"] == 0:
            print("  the organ has caught nothing yet — the honest red baseline (§8); green is earned prospectively.")
        return 0  # advisory; never gates (no judicial robes)

    pc, rows = run(write=args.write, thread=args.thread)
    if pc is None:
        print(f"occlusion_watch: no ARM-NOW PRECOMMIT found in thread '{args.thread}'; nothing armed.")
        return 0  # an instrument with nothing armed is a no-op, never a failure

    examined = [r for r in rows if r["row"] == "route_watch_surface_examined"]
    observed = [r for r in rows if r["row"] == "occlusion_watch_observed"]
    s2 = [r for r in examined if r.get("population_rule_ref") == "S2"]
    print(f"occlusion_watch [{pc.thread}] — precommit_ts {pc.precommit_ts}, watched_agent {pc.watched_agent}")
    print(f"  keys ({len(pc.candidate_keys)}): {', '.join(pc.candidate_keys)}")
    print(f"  surfaces examined: {len(examined)} (S2 diffs: {len(s2)})   observed key-hits: {len(observed)}")
    for r in observed:
        print(f"    • {r['candidate_key']!r} in {r['surface_ref']}  [{r['seam_distance']}]")
    print("  Layer 1 only — no verdict; `earned` is Layer 2 (§10), spoken only at a cross-seam named_ts.")
    if not args.write:
        print("  computed only; pass --write to append (deploy-and-watch).")
    return 0  # ALWAYS 0: no judicial robes


if __name__ == "__main__":
    raise SystemExit(main())
