"""occlusion_watch — X4 session-seam witness, Layer-1 emitter (SPEC_X4 §11).

The session-seam sibling of `route_watch` (the declared-read seam). `route_watch` asks
*"what ancestor is missing from this DECLARED-READ confidence?"*; `occlusion_watch` asks
the same across a SESSION seam: did a later-session (cold) agent use a confidence whose
grounding ancestor it did not re-route this session?

**Layer-1 emitter ONLY (§11).** It emits ordering FACTS + disqualifiers, never an
outcome verdict. `earned` is Layer 2, deferred (§10) — spoken only when a cross-seam
external `named_ts` lands on a predated `work_product` row over a visible denominator.
No judicial robes: always exits 0, gates nothing.

**Witness invariant (§2).** Timestamps are stamped by the substrate (entry filenames)
and the harness `Ledger`, never by the watched agent — the beneficiary can neither set
nor backdate them. The precommit that arms this watch is itself a witnessed substrate
entry (un-backdatable); this module READS it, it does not author it. Reading the keys
and paths from that entry (not from a code constant) keeps them precommitted — a key
added to the source later would be `borrowed_foresight` (§5), and this module cannot
introduce one.

**Honest scope (§8/§11).** Externalized surfaces only. Confidence that hardens without
leaving an enumerable trace — the cold-author lower bound (hermes, thread-x4c) — is out
of reach, by the same refusal that bars self-report. This watch cannot catch what never
leaves a trace.

**Population (from the precommit's `population_rule`, mechanically enumerable):**
  S1  every substrate entry authored by <watched_agent> in <thread> after precommit_ts
  S2  every committed diff touching the declared paths after precommit_ts
v0 examines S1 (substrate prose); S2 surfaces are emitted as `scope_gap` (declared in
the denominator, examination deferred to v0.1) — the denominator stays external and is
never silently shrunk.

**candidate_key:** literal / conservative (the base-rate lesson, `runs/x4/base_rate.md`):
distinctive compounds only, exact substring; uncertain normalization => DO NOT MATCH
(under-claim embarrasses; over-match steals — flinch-theft, §5).

NOTE (v0 coupling, disclosed): `load_precommit` parses the precommit entry's prose
(keys as `"key" → §N`, the S2 path globs). Tuned to the arm-now entry format; a format
change means updating the parser, not the witness.

Usage:
  uv run --no-project python -m harness.occlusion_watch                 # compute, print
  uv run --no-project python -m harness.occlusion_watch --write         # append Layer-1 rows
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
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
    ref: str   # path relative to ROOT
    ts: str    # filename timestamp (witnessed)
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
            candidate_keys=keys, declared_paths=paths,
            entry_path=_rel(f),
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


def examine(text: str, keys: tuple[str, ...]) -> list[str]:
    """Literal/conservative match: exact case-insensitive substring of the distinctive
    compound. 'witness' alone never matches 'witness invariant' — only the full key."""
    low = text.lower()
    return [k for k in keys if k.lower() in low]


def seam_distance(surface_ts: str, precommit_ts: str) -> str:
    """v0 proxy (DISCLOSED): UTC calendar date vs the precommit's date. Same date =
    `same_session` (calibration, not earned-eligible); later date = `later_session` (the
    first earned-eligible seam, §11). A coarse session proxy — robust session identity is
    a v0.1 refinement; note it can only make a surface LESS earned-eligible, never more,
    so it fails toward under-claim."""
    return "same_session" if surface_ts[:8] == precommit_ts[:8] else "later_session"


def observe(pc: Precommit, threads_dir: Path = THREADS_DIR) -> list[dict]:
    """Emit Layer-1 rows: `route_watch_surface_expected` + `route_watch_surface_examined`
    (S1), `occlusion_watch_observed` (per literal key-hit), `scope_gap` (S2 — examination
    deferred, kept in the denominator). NEVER an outcome verdict (Layer 2, §10)."""
    rows: list[dict] = []
    for s in enumerate_s1(pc, threads_dir):
        rows.append({
            "row": "route_watch_surface_expected", "seam": "session",
            "surface_ref": s.ref, "surface_ts": s.ts,
            "population_rule_ref": "S1", "precommit_ts": pc.precommit_ts,
        })
        hits = examine(s.text, pc.candidate_keys)
        rows.append({
            "row": "route_watch_surface_examined", "surface_ref": s.ref,
            "candidate_count": len(hits), "wrote_observed_rows": bool(hits),
        })
        for k in hits:
            rows.append({
                "row": "occlusion_watch_observed", "seam": "session",
                "candidate_key": k, "match": "literal",
                "surface_ref": s.ref, "surface_ts": s.ts,
                "seam_distance": seam_distance(s.ts, pc.precommit_ts),
                "fire_authority": "agent_fired-under-precommitment",
                "watched_agent": pc.watched_agent,
                "watched_agent_is_author": True,  # S1 is the watched agent's own prose
                "surface_basis": "work_product",
                "precommit_ts": pc.precommit_ts,
                # Layer 1: NO verdict. `earned` is computed later vs an external named_ts.
                "evidence_status": "observed_only_no_outcome",
            })
    for p in pc.declared_paths:
        rows.append({
            "row": "scope_gap", "surface_ref": p, "population_rule_ref": "S2",
            "reason": "examination_deferred_v0_committed_diff",
            "precommit_ts": pc.precommit_ts,
        })
    return rows


def read_ledger(path: Path = LEDGER) -> list[dict]:
    """The append-only watch ledger: Layer-1 rows + external human_named_candidate rows."""
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def compute_outcomes(rows: list[dict]) -> tuple[list[dict], dict]:
    """Layer-2 (§4): COMPUTE occlusion_watch_outcome records from the ledger's lineage
    order — catches vs flinches. NOT a fourth judicial scorer (§5: no fourth scorer, no
    cell_verdict); occlusion_watch's own advisory computation. The rows' hand-written
    `classification`/`tally` are IGNORED (R5: computed, never asserted).

    `earned` is structurally unmanufacturable from this session:
      - the namer must be EXTERNAL (watched_agent_is_author == False) — §2;
      - a matching `occlusion_watch_observed` row must be surface_basis=work_product (§4),
        seam_distance >= later_session, and PREDATE the naming (observed_ts < named_ts);
      - `earned` additionally needs action evidence (did_it_change_attention_or_action);
        present-but-no-evidence => `early` (a catch pending evidence), never `earned`.
    Anything the organ did not see first is a flinch; same_pass is `not_engaged` upstream
    (the Layer-1 seam rule). passenger / false_alarm / noisy need an action-evidence +
    base-rate window and are deferred (disclosed under-claim, §8)."""
    observed = [r for r in rows if r.get("row") == "occlusion_watch_observed"]
    named = [r for r in rows if r.get("row") in ("human_named_candidate", "flinch_observed")]
    outcomes: list[dict] = []

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
        if not external:
            verdict = "not_engaged"               # the beneficiary cannot name (§2)
        elif predated:
            has_evidence = bool(n.get("evidence")) and bool(n.get("did_it_change_attention_or_action"))
            verdict = "earned" if has_evidence else "early"   # catch (w/ evidence) vs pending
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

    tally = {"catches": 0, "flinches": 0, "early": 0, "late": 0, "not_engaged": 0}
    for o in outcomes:
        v = o["verdict"]
        if v == "earned":
            tally["catches"] += 1
        elif v == "unmatched_human_flinch":
            tally["flinches"] += 1
        else:
            tally[v] = tally.get(v, 0) + 1
    return outcomes, tally


def run(
    *, write: bool = False, thread: str = "thread-x4c", threads_dir: Path = THREADS_DIR
) -> tuple[Precommit | None, list[dict]]:
    pc = load_precommit(thread, threads_dir=threads_dir)
    if pc is None:
        return None, []
    rows = observe(pc, threads_dir)
    if write and rows:
        ledger = Ledger(LEDGER)
        for r in rows:
            ledger.write(r)  # Ledger prepends harness-stamped `ts` = observed_ts (§2)
    return pc, rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="X4 occlusion_watch — session-seam Layer-1 emitter (SPEC_X4 §11)",
    )
    ap.add_argument("--thread", default="thread-x4c", help="substrate thread holding the arm-now precommit")
    ap.add_argument("--write", action="store_true", help="append Layer-1 rows to the ledger (observed_ts harness-stamped)")
    ap.add_argument("--outcomes", action="store_true", help="Layer-2: COMPUTE catches-vs-flinches from the ledger lineage (advisory; no verdict-gate, §5)")
    args = ap.parse_args(argv)

    if args.outcomes:
        outcomes, tally = compute_outcomes(read_ledger())
        print("occlusion_watch — Layer-2 outcomes (COMPUTED from lineage; advisory, no cell_verdict, §5)")
        print(f"  catches {tally['catches']}   flinches {tally['flinches']}   "
              f"early {tally.get('early', 0)}   late {tally.get('late', 0)}   not_engaged {tally.get('not_engaged', 0)}")
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
    gaps = [r for r in rows if r["row"] == "scope_gap"]
    print(f"occlusion_watch [{pc.thread}] — precommit_ts {pc.precommit_ts}, watched_agent {pc.watched_agent}")
    print(f"  keys ({len(pc.candidate_keys)}): {', '.join(pc.candidate_keys)}")
    print(f"  S1 examined: {len(examined)}   observed key-hits: {len(observed)}   S2 scope_gap: {len(gaps)}")
    for r in observed:
        print(f"    • {r['candidate_key']!r} in {r['surface_ref']}  [{r['seam_distance']}]")
    print("  Layer 1 only — no verdict; `earned` is Layer 2 (§10), spoken only at a cross-seam named_ts.")
    if not args.write:
        print("  computed only; pass --write to append (deploy-and-watch).")
    return 0  # ALWAYS 0: no judicial robes


if __name__ == "__main__":
    raise SystemExit(main())
