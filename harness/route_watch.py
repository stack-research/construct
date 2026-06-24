"""route_watch — X4 declared-read-seam occlusion watch (SPEC_X4 §3).

An INSTRUMENT, not a scorer. It computes cold-confidence watch rows and appends
them only when explicitly asked; ordinary and historical runs are print-only.
No judicial robes (codex): the name is `route_watch`, never `check_*`; it owns
no exit-code verdict and adds no fail-bit anywhere.

The question it asks (SPEC_X4 §0) is *"what ancestor is missing from this
confidence?"* — one seam over from M-1's `check_contract.py`, from **files-read**
to **obligations-inherited**.

The relation, not a fact (SPEC_X4 §1). A cold-confidence candidate exists when:
  - a two-plane lineage TERM is in use (the confidence forming here), AND
  - its ANCESTOR source — the bridge glossary, routed by AGENTS' "Open only when"
    edge `Inherited vocabulary, two-plane lineage terms` — is ABSENT from the
    declared route, AND
  - the active route does NOT independently ground the term (the active glossary
    has no standalone definition of it; it only uses or defers to the ancestor).
That triple is the seam: something existed (the ancestor definition), mattered
(the term is in use), and was unavailable from the foreground's side of the act
(its route omits the ancestor). Absence + a foreground-blind seam, not vibes.

Witness (SPEC_X4 §2): partial at this seam. If rows are written, the harness
(`Ledger`) stamps `observed_ts`; the agent under watch does not. The route itself
is still a declared read-order claim, so rows disclose that the timestamp is
witnessed while the WHAT-in-route remains self-reported.

NOT in v0.1, by design:
  - No outcome/verdict row. `earned | early | late | passenger | false_alarm |
    noisy` is COMPUTED LATER against an EXTERNAL `human_named_candidate` row — the
    session-seam concern, still designed-not-build-admitted (SPEC_X4 §3/§9.2).
    This module emits only `occlusion_watch_observed`.
  - No cost/cry-wolf model (an admission gate before any standing watch on real
    turns, SPEC_X4 §9.4). v0.1 runs on declared-read manifests, not live turns.

Anti-theater (SPEC_X4 §7): re-finding thread-8's known misses proves MACHINERY at
best — load-bearing maybe, world-grounded no; `not_engaged` as evidence by X2-U1's
own gate. The cold-lineage candidate this surfaces on a pre-`b7e04c0` route is a
machinery demonstration, NEVER a pass condition and NEVER evidence the organ works.
That is earned only prospectively, by catches-vs-flinches under the witness invariant.

Usage:
  uv run --no-project python -m harness.route_watch --manifest runs/bootstrap/cursor.json
  uv run --no-project python -m harness.route_watch --read-order AGENTS.md,notes/GLOSSARY.md
  uv run --no-project python -m harness.route_watch --manifest M.json --work notes/SOME_DRAFT.md
  uv run --no-project python -m harness.route_watch --manifest M.json --write   # append a prospective watch row
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from .ledger import Ledger

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "AGENTS.md"
BRIDGE_GLOSSARY = "notes/previous/review/glossary.md"  # the routed ancestor source
ACTIVE_GLOSSARY = "notes/GLOSSARY.md"  # default in-use surface; standing lab vocabulary
ROUTE_WATCH_SIDECAR = ROOT / "runs" / "bootstrap" / "route_watch.jsonl"

LINK = re.compile(r"\[[^\]]+\]\(([^)#]+)\)")
HEADWORD = re.compile(r"^\*\*(.+?)\*\*", re.M)  # bridge glossary term: **Term**
ACTIVE_HEADING = re.compile(r"^###\s+`?(.+?)`?\s*$", re.M)  # active glossary: ### Term


@dataclass(frozen=True)
class AncestorTerm:
    name: str  # e.g. "Lineage plane"
    root: str  # distinctive token, e.g. "lineage" — what a derived form narrows
    core: bool  # True for the Planes-section two-plane cluster


def _section(text: str, heading: str) -> str:
    """Body of a `## heading` section, up to the next `## ` or EOF."""
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def conditional_edges(contract_text: str) -> list[tuple[str, str]]:
    """The AGENTS 'Open only when' routing table as (trigger, source-path) edges.

    These are the obligation→ancestor routes the contract publishes about itself.
    Parsed from the contract on every run so the contract stays authoritative.
    """
    sec = _section(contract_text, "Required read order")
    _, _, tail = sec.partition("Open only when")
    edges: list[tuple[str, str]] = []
    for line in tail.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or "---" in cells[0] or cells[0].lower() == "task":
            continue
        m = LINK.search(cells[1])
        if m:
            edges.append((cells[0], m.group(1)))
    return edges


def ancestor_term_set(bridge_text: str) -> list[AncestorTerm]:
    """The two-plane lineage vocabulary the AGENTS edge routes to the bridge glossary.

    Derived from the bridge glossary's own structure — the `## Planes` section
    headwords are the two-plane core; any other lineage-rooted headword rides along
    at lower weight. No authored term list: scoped to what the contract edge names.
    """
    planes = {h.strip() for h in HEADWORD.findall(_section(bridge_text, "Planes"))}
    terms: list[AncestorTerm] = []
    seen: set[str] = set()
    for name in HEADWORD.findall(bridge_text):
        name = name.strip()
        low = name.lower()
        core = name in planes
        if not core and "lineage" not in low:
            continue  # v0.1 scope: the two-plane lineage cluster only (cry-wolf floor)
        if low in seen:
            continue
        seen.add(low)
        root = re.sub(r"[^\w-]", "", name.split()[0]).lower()
        terms.append(AncestorTerm(name=name, root=root, core=core))
    return terms


def active_headwords(active_text: str) -> set[str]:
    """Terms the active glossary defines on its own (lowercased).

    A term independently grounded here is NOT occluded for an agent who read the
    active glossary — the ancestor is locally re-grounded, not missing. (The active
    glossary's `### Cold Lineage` is a *derived* term that defers to the ancestor;
    it is not a standalone definition of `lineage plane`, so it does not shield it.)
    """
    return {h.strip().lower() for h in ACTIVE_HEADING.findall(active_text)}


def cold_candidates(
    read_order: list[str],
    surface_text: str,
    active_hw: set[str],
    terms: list[AncestorTerm],
    *,
    ancestor_source: str,
    route_trigger: str | None,
    surface_label: str,
    surface_basis: str,
) -> list[dict]:
    """Pure: the ranked cold-confidence candidates for one declared route + surface.

    Never raises on empty input; an empty list is the honest 'nothing cold here'
    result, not an error. Returns observed-row dicts WITHOUT `ts` (the Ledger, the
    external witness, stamps that).
    """
    routed = ancestor_source in read_order
    surface_low = surface_text.lower()
    rows: list[dict] = []
    for t in terms:
        in_use = t.name.lower() in surface_low or t.root in surface_low
        if not in_use:
            continue
        if t.name.lower() in active_hw:
            continue  # locally grounded by the active route; ancestor not occluded
        if routed:
            continue  # the route reached the ancestor; confidence is not cold
        # Breadth-collapse is a property of the two-plane CORE vocabulary narrowing
        # into construct's materialization axis (the `lineage plane` → `cold lineage`
        # move). Awarding it to every lineage-rooted term via the shared root would
        # inflate confidence on loose matches — the cry_wolf loses-condition (§5).
        derived = sorted(h for h in active_hw if t.root in h and h != t.name.lower()) if t.core else []
        breadth_collapse = bool(derived)
        freq = surface_low.count(t.root)
        cold = (1.0 if t.core else 0.6) + (0.5 if breadth_collapse else 0.0) + min(0.3, 0.03 * freq)
        why = (
            f"using two-plane lineage term '{t.name}'"
            + (f" (in use as {', '.join(repr(d) for d in derived)})" if derived else "")
            + f"; ancestor '{t.name}' lives in {ancestor_source}, absent from the declared route"
            + "; confidence here is cold"
        )
        rows.append({
            "row": "occlusion_watch_observed",
            "seam": "declared-read",
            "candidate": t.name,
            "candidate_kind": "route-relation" if breadth_collapse else "term",
            "why_now": why,
            "search_boundary": surface_label,
            "mode": "silent",
            "ancestor_source": ancestor_source,
            "route_trigger": route_trigger,
            "route_basis": "declared_read_order",
            "witness_scope": "observed_ts_only__route_claim_not_independently_witnessed",
            "evidence_status": "observed_only_no_outcome",
            "surface_basis": surface_basis,  # standing_glossary survey vs a live work_product (cursor P2)
            "breadth_collapse": breadth_collapse,
            "derived_in_use": derived,
            "cold_confidence": round(cold, 3),
        })
    rows.sort(key=lambda r: r["cold_confidence"], reverse=True)
    return rows


def observe(
    read_order: list[str],
    *,
    agent: str | None = None,
    work_path: Path | None = None,
    write: bool = False,
    sidecar: Path = ROUTE_WATCH_SIDECAR,
) -> list[dict]:
    """Run the watch over one declared route; optionally append rows to the sidecar.

    `read_order` is what the agent declared inheriting (e.g. a bootstrap manifest's
    read_order) — never a filename handed in as a target (SPEC_X4 §3). The in-use
    surface is `work_path` if given, else the active glossary (the standing lab
    vocabulary). Returns the observed rows. Writing is opt-in so retrospective or
    ordinary conformance reruns cannot masquerade as prospective catches.
    """
    contract_text = CONTRACT.read_text()
    edges = conditional_edges(contract_text)
    route_trigger = next((trig for trig, src in edges if src == BRIDGE_GLOSSARY), None)

    bridge_text = (ROOT / BRIDGE_GLOSSARY).read_text()
    active_text = (ROOT / ACTIVE_GLOSSARY).read_text()
    terms = ancestor_term_set(bridge_text)
    active_hw = active_headwords(active_text)

    if work_path is not None:
        surface_text = Path(work_path).read_text()
        surface_label = str(work_path)
        surface_basis = "work_product"
    else:
        surface_text = active_text
        surface_label = ACTIVE_GLOSSARY
        surface_basis = "standing_glossary"  # a survey/mirror, NOT a live-turn catch
    search_boundary = (
        f"AGENTS read-order graph ({len(edges)} conditional edges); "
        f"ancestor source {BRIDGE_GLOSSARY} ({len(terms)} two-plane terms); "
        f"in-use surface {surface_label}; declared route {len(read_order)} entries"
    )

    rows = cold_candidates(
        read_order, surface_text, active_hw, terms,
        ancestor_source=BRIDGE_GLOSSARY, route_trigger=route_trigger,
        surface_label=search_boundary, surface_basis=surface_basis,
    )
    if write and rows:
        ledger = Ledger(sidecar)
        for r in rows:
            ledger.write({**r, "agent": agent})  # Ledger prepends harness-stamped `ts` = observed_ts
    return rows


def _read_order_from_args(args) -> tuple[list[str], str | None]:
    if args.manifest:
        m = json.loads(Path(args.manifest).read_text())
        return list(m.get("read_order", [])), m.get("agent")
    if args.read_order:
        return [p.strip() for p in args.read_order.split(",") if p.strip()], args.agent
    return [], args.agent


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--manifest", type=Path, help="bootstrap manifest JSON (uses its read_order)")
    ap.add_argument("--read-order", help="comma-separated declared read order (instead of --manifest)")
    ap.add_argument("--work", type=Path, help="text whose confidence is forming (default: active glossary)")
    ap.add_argument("--agent", help="agent label for the watch rows")
    ap.add_argument("--write", action="store_true", help="append observed rows to the sidecar")
    ap.add_argument("--no-write", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    read_order, agent = _read_order_from_args(args)
    if not read_order:
        print("route_watch: no declared route (pass --manifest or --read-order); nothing to watch.")
        return 0  # an instrument with no input is a no-op, never a failure

    should_write = args.write and not args.no_write
    rows = observe(read_order, agent=agent, work_path=args.work, write=should_write)

    label = agent or args.read_order or "?"
    if not rows:
        print(f"route_watch [{label}]: no cold-confidence candidates "
              f"(route grounds or reaches the two-plane lineage ancestor).")
        return 0
    print(f"route_watch [{label}]: {len(rows)} cold-confidence candidate(s) — "
          f"watch rows, not a verdict (SPEC_X4 §3):\n")
    for r in rows:
        print(f"  • [{r['cold_confidence']:.2f}] {r['candidate']}  ({r['candidate_kind']})")
        print(f"      {r['why_now']}")
    if should_write:
        print(f"\nappended {len(rows)} occlusion_watch_observed row(s) to "
              f"{ROUTE_WATCH_SIDECAR.relative_to(ROOT)} (harness-witnessed, append-only).")
    else:
        print("\ncomputed only; no sidecar append. Pass --write only for a prospective watch row.")
    return 0  # ALWAYS 0: an instrument never fails the build (no judicial robes)


if __name__ == "__main__":
    sys.exit(main())
