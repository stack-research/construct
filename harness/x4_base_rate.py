"""x4_base_rate — SPEC_X4 §9.4 / §10 #5: the cry-wolf base-rate admission gate.

Measure how often `route_watch` FIRES on real work-product prose. This is the gate
that stands BEFORE any standing watch on live turns (§9.4): a high fire-rate is the
`cry_wolf` loses-condition (§5) measured before it can embarrass a live watch — which
is exactly what an admission gate is for. It is NOT a catch and NOT evidence the organ
works (that is earned only prospectively, §0/§7); it is the instrument's false-alarm
profile, computed.

Reuses `route_watch.cold_candidates` UNCHANGED — this measures the shipped instrument,
it does not reimplement the relation.

Population (pre-declared, enumerable, uncurated — §11 population_rule): every substrate
thread turn file `.substrate/threads/<thread>/<ts>__<author>.md` (READMEs excluded;
no-op turns do not exist on disk here). File boundaries the foreground cannot curate.
`scope_gap` counts any named surface we could not read, keeping the denominator external.

Routes measured:
  cold       read_order = []                the bridge glossary is absent — the
                                            realistic cold-start state and the ONLY
                                            state where the relation can fire. The
                                            result is invariant across any cold route
                                            (the relation gates solely on whether the
                                            bridge glossary is routed), so this is the
                                            base rate, not one route's quirk.
  warm       read_order=[BRIDGE_GLOSSARY]   control: the ancestor is routed, so the
                                            relation MUST go silent — validates it is
                                            not simply always-on.
  distinctive  LAB1_EPISTEMIC, cold         the distinctive-terms-only profile
                                            (runs/x4/option3-ceiling.md): expected
                                            near-zero — distinctiveness trades cry-wolf
                                            for under-claim.

It also splits each cold fire into compound-name match (e.g. "lineage plane") vs
bare-root match (e.g. "lineage"), because the relation's `in_use = name OR root` means
the bare root fires on construct's everyday vocabulary — the suspected cry-wolf driver.

Representativeness (disclosed, M0 corpus_scope rule): the corpus is lab-review prose
whose authors were generally WARM (in-thread, holding the lineage context). So a fire
here is almost always a false positive — this measures the cry-wolf rate directly, an
UPPER bound on usable signal. It is also topic-skewed: lineage-heavy threads (x4*) fire
far more than M-track threads; the per-thread breakdown discloses the skew.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from .route_watch import (
    ACTIVE_GLOSSARY,
    BRIDGE_GLOSSARY,
    LAB1_EPISTEMIC,
    ROOT,
    active_headwords,
    ancestor_term_set,
    cold_candidates,
)

THREADS_DIR = ROOT / ".substrate" / "threads"
OUT = ROOT / "runs" / "x4" / "base_rate.json"
TURN_RE = re.compile(r"^(?P<ts>\d{8}T\d{6}\d*Z)__(?P<author>.+)\.md$")
FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)


def population() -> list[Path]:
    """Every turn file across all threads — enumerable, uncurated (READMEs out)."""
    files: list[Path] = []
    for thread_dir in sorted(p for p in THREADS_DIR.iterdir() if p.is_dir()):
        for f in sorted(thread_dir.glob("*.md")):
            if f.name != "README.md" and TURN_RE.match(f.name):
                files.append(f)
    return files


def surface_of(path: Path) -> str:
    """The prose body, frontmatter stripped (the metadata is not the agent's prose)."""
    return FRONTMATTER.sub("", path.read_text(), count=1)


def _fire(surface: str, read_order: list[str], active_hw, terms) -> list[dict]:
    return cold_candidates(
        read_order, surface, active_hw, terms,
        ancestor_source=BRIDGE_GLOSSARY, route_trigger=None,
        surface_label="x4_base_rate", surface_basis="work_product",
    )


def measure() -> dict:
    bridge_text = (ROOT / BRIDGE_GLOSSARY).read_text()
    active_text = (ROOT / ACTIVE_GLOSSARY).read_text()
    terms = ancestor_term_set(bridge_text)
    active_hw = active_headwords(active_text)

    files = population()
    surfaces: list[tuple[Path, str]] = []
    scope_gap: list[dict] = []
    for f in files:
        try:
            surfaces.append((f, surface_of(f)))
        except OSError as e:  # a named surface we could not read — external denominator
            scope_gap.append({"path": str(f.relative_to(ROOT)), "reason": repr(e)})

    n = len(surfaces)
    per_thread: dict[str, dict] = defaultdict(lambda: {"n": 0, "fired": 0})
    term_fires: Counter = Counter()
    term_kind: dict[str, Counter] = defaultdict(Counter)  # term -> {name, root}
    per_surface: list[dict] = []
    cold_fired = 0
    name_match_fired = 0

    for f, surface in surfaces:
        thread = f.parent.name
        rows = _fire(surface, [], active_hw, terms)
        per_thread[thread]["n"] += 1
        fired = bool(rows)
        surface_low = surface.lower()
        kinds: dict[str, str] = {}
        for r in rows:
            name = r["candidate"]
            term_fires[name] += 1
            mk = "name" if name.lower() in surface_low else "root"
            term_kind[name][mk] += 1
            kinds[name] = mk
        if fired:
            cold_fired += 1
            per_thread[thread]["fired"] += 1
            if any(mk == "name" for mk in kinds.values()):
                name_match_fired += 1
        per_surface.append({
            "path": str(f.relative_to(ROOT)),
            "thread": thread,
            "author": TURN_RE.match(f.name)["author"],
            "fired": fired,
            "n_candidates": len(rows),
            "candidates": kinds,
            "top": rows[0]["candidate"] if rows else None,
            "top_confidence": rows[0]["cold_confidence"] if rows else None,
        })

    # warm control: routing the ancestor must silence the relation
    warm_fired = sum(1 for _, s in surfaces if _fire(s, [BRIDGE_GLOSSARY], active_hw, terms))
    # distinctive profile (cold): distinctiveness should trade cry-wolf for under-claim
    distinct_fired = sum(
        1 for _, s in surfaces
        if cold_candidates(
            [], s, set(), list(LAB1_EPISTEMIC.terms),
            ancestor_source=LAB1_EPISTEMIC.ancestor_source, route_trigger=None,
            surface_label="x4_base_rate:distinctive", surface_basis="work_product",
        )
    )

    def rate(k: int) -> float:
        return round(k / n, 3) if n else 0.0

    return {
        "spec": "SPEC_X4 §9.4 / §10 #5 — cry-wolf base rate (admission gate)",
        "instrument": "harness.route_watch.cold_candidates (unchanged)",
        "not_a_catch": "false-alarm profile of the instrument; not evidence the organ works (§0/§7)",
        "population_rule": "every .substrate/threads/<thread>/<ts>__<author>.md (READMEs excluded; no no-op files on disk)",
        "population": len(files),
        "examined": n,
        "scope_gap": scope_gap,
        "warm_authors_caveat": (
            "corpus authors were generally in-thread (warm), so a fire is ~a false "
            "positive: this is the cry-wolf rate directly / an upper bound on usable signal"
        ),
        "routes": {
            "cold": {
                "read_order": [],
                "note": "bridge glossary absent — invariant across any cold route",
                "fired": cold_fired,
                "fire_rate": rate(cold_fired),
            },
            "warm_control": {
                "read_order": [BRIDGE_GLOSSARY],
                "note": "ancestor routed — must be ~0 (relation is not always-on)",
                "fired": warm_fired,
                "fire_rate": rate(warm_fired),
            },
            "distinctive_profile_cold": {
                "profile": LAB1_EPISTEMIC.name,
                "note": "distinctive terms only (runs/x4/option3-ceiling.md) — under-claim end",
                "fired": distinct_fired,
                "fire_rate": rate(distinct_fired),
            },
        },
        "name_match_only": {
            "note": "cold fires with >=1 compound-name match (the rate if bare-root match were dropped)",
            "fired": name_match_fired,
            "fire_rate": rate(name_match_fired),
        },
        "per_thread": {
            t: {**v, "fire_rate": round(v["fired"] / v["n"], 3)}
            for t, v in sorted(per_thread.items())
        },
        "per_term": {
            name: {
                "fired_on": term_fires[name],
                "name_match": term_kind[name]["name"],
                "root_only": term_kind[name]["root"],
            }
            for name in sorted(term_fires, key=lambda k: -term_fires[k])
        },
        "per_surface": per_surface,
    }


def main() -> int:
    result = measure()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")

    r = result
    print(f"x4 base rate — {r['examined']}/{r['population']} surfaces examined "
          f"({len(r['scope_gap'])} scope_gap)\n")
    for name, route in r["routes"].items():
        print(f"  {name:24s} fire_rate {route['fire_rate']:.3f}  ({route['fired']}/{r['examined']})")
    nm = r["name_match_only"]
    print(f"  {'cold, name-match only':24s} fire_rate {nm['fire_rate']:.3f}  ({nm['fired']}/{r['examined']})")
    print("\n  per-thread fire_rate (cold):")
    for t, v in r["per_thread"].items():
        print(f"    {t:14s} {v['fire_rate']:.3f}  ({v['fired']}/{v['n']})")
    print("\n  per-term (cold) — fired_on / name / root-only:")
    for name, v in r["per_term"].items():
        print(f"    {name:24s} {v['fired_on']:4d}  name={v['name_match']:<4d} root_only={v['root_only']}")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
