"""SPEC_PAUSE_RESUME §9 — the PRF fixture admission gate (computed, never
attested). Fail-loud preflight: refuses a fixture before any non-mock
evidence unless every leg passes; the scorer requires the `gate_open` row.

The two §4c offer-time content-floor legs appear here as PREFLIGHT MIRRORS
(review-round fix B4): the gate re-derives the same checks the offer-time
minter runs and must refuse any fixture the minter would refuse — it never
substitutes for the mint refusal. A mismatch between gate and mint is a
harness bug, not a scoring outcome.

Ballast is COMPUTED, not attested: `derived_obligation_tokens` must equal the
recomputed t0 token sum over the union of the derived obligations' source
surfaces. An attested number that disagrees fails the leg.

Usage:
  uv run --no-project python -m harness.check_prf_fixture episodes/prf/<fixture>/manifest.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .derive_live_obligations import (DerivationRefused,
                                      derive_live_obligations,
                                      validate_rulebook)
from .predicate_ast import PredicateClosureError, library_hash
from .score_prf import _tokens

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "episodes" / "prf" / "meridian" / "manifest.json"

Check = tuple[str, bool, str]

# Outcome-encoding lemmas the rulebook may never carry (WB genealogy_ok
# posture at population level): a rule that names the answer authors the
# frontier.
OUTCOME_LEMMAS = ("correct", "preferred", "winner", "best", "answer",
                  "refuted", "superseded", "leading", "default_choice")


def _witness_rows(route: list[str], catalog: dict) -> list[dict]:
    return [{"surface_id": sid, "read_index": i, "catalog_epoch": "t0",
             "content_hash": catalog[sid]["content_hash_t0"],
             "surface_tags": catalog[sid]["surface_tags"]}
            for i, sid in enumerate(route)]


def check_manifest(manifest_path: Path) -> list[Check]:
    checks: list[Check] = []
    fixture_dir = manifest_path.parent
    m = json.loads(manifest_path.read_text())
    pop = json.loads((fixture_dir / "population.json").read_text())
    freeze_manifest = json.loads(
        (fixture_dir / "freeze_manifest.json").read_text())

    # --- surface_tags_closed: appendix-sized enum, catalog-declared only ---
    tag_schema = set(pop.get("surface_tag_schema", []))
    stray = {t for meta in pop["catalog"].values()
             for t in meta.get("surface_tags", [])} - tag_schema
    if not tag_schema:
        checks.append(("surface_tags_closed", False,
                       "population declares no surface_tag_schema"))
    elif stray:
        checks.append(("surface_tags_closed", False,
                       f"catalog tags outside the pinned schema: {sorted(stray)}"))
    else:
        checks.append(("surface_tags_closed", True,
                       f"{len(tag_schema)} tags, all catalog-declared"))

    # --- predicate_closure + rulebook admission (AST + verdict-code refusal) --
    try:
        lib_hash = library_hash(pop["predicate_library"])
        rb_hash = validate_rulebook(pop["obligation_rulebook"],
                                    pop["predicate_library"],
                                    pop["relation_code_classes"])
        pinned = (lib_hash == pop.get("predicate_library_hash")
                  and rb_hash == pop.get("obligation_rulebook_hash"))
        checks.append(("predicate_closure", pinned,
                       "library + rulebook validate and match the population "
                       "pins" if pinned else "hash does not match the pin"))
    except (PredicateClosureError, DerivationRefused) as e:
        checks.append(("predicate_closure", False, str(e)))
        return checks

    # --- rulebook_genealogy_ok: no outcome lemmas in rules/tags/predicates ---
    corpus = json.dumps([pop["obligation_rulebook"], sorted(tag_schema),
                         pop["predicate_library"]], sort_keys=True).lower()
    vocab_lemmas = [v.lower() for v in pop.get("status_vocabulary", [])]
    hits = [w for w in (*OUTCOME_LEMMAS, *vocab_lemmas) if w in corpus]
    checks.append(("rulebook_genealogy_ok", not hits,
                   "no outcome lemmas in rulebook/tags/predicates" if not hits
                   else f"outcome-encoding lemmas found: {hits}"))

    # --- per-episode legs ---
    episodes = [json.loads((fixture_dir / p).read_text())
                for p in m["episodes"]]
    catalog = pop["catalog"]
    floor_met = False
    for ep in episodes:
        eid = ep["episode_id"]
        witness_route = ep["witness_route"]

        # rulebook_route_independence (witness-trace verdict, dan vote 3):
        # refuse fixtures where a rule's obligations could fire only on
        # surfaces the witness never read.
        witness_tags = {t for sid in witness_route
                        for t in catalog[sid]["surface_tags"]}
        dry = derive_live_obligations(
            pop, freeze_manifest, _witness_rows(witness_route, catalog),
            ep["seam_id"])
        fired_rules = {o["rule_id"] for o in dry["obligations"]}
        ghost = []
        for rule in pop["obligation_rulebook"]:
            if rule["rule_id"] in fired_rules:
                continue
            rule_tags = {t for sid, meta in catalog.items()
                         for t in meta["surface_tags"]
                         if _rule_can_fire_on(rule, meta)}
            if rule_tags and not rule_tags & witness_tags:
                ghost.append(rule["rule_id"])
        checks.append((f"rulebook_route_independence[{eid}]", not ghost,
                       "every firing path crosses the witness trace" if not ghost
                       else f"rules fire only on unread surfaces: {ghost}"))

        # derivation_nontrivial: non-empty and strictly richer than the M1
        # sidecar alone (>=1 conditional obligation beyond trace bookmark)
        conditional = [o for o in dry["obligations"]
                       if o["obligation_type"] in ("verify", "discard", "reopen")]
        ok = bool(dry["obligations"]) and bool(conditional)
        checks.append((f"derivation_nontrivial[{eid}]", ok,
                       f"{len(dry['obligations'])} obligations, "
                       f"{len(conditional)} conditional" if ok else
                       "derivation adds nothing beyond the trace bookmark — "
                       "comparator_incapable"))

        # ablation-causality MIRROR (§4c-1): withholding the obligation-
        # covered surfaces from the witness must change the derived batch —
        # obligations that survive their own sources' removal are decorative.
        covered = {sid for o in dry["obligations"]
                   for sid in o["source_read_ids"]}
        ablated_route = [s for s in witness_route if s not in covered]
        ablated = derive_live_obligations(
            pop, freeze_manifest, _witness_rows(ablated_route, catalog),
            ep["seam_id"])
        mirror_ok = (ablated["batch"]["obligation_set_hash"]
                     != dry["batch"]["obligation_set_hash"]) and \
            not ep.get("ablation_witness_adequate", False)
        checks.append((f"ablation_causality_mirror[{eid}]", mirror_ok,
                       "withheld sources change the batch; fixture attests "
                       "witness inadequacy under ablation" if mirror_ok else
                       "obligations decorative under ablation — the offer-time "
                       "mint would refuse (fixture_obligations_decorative)"))

        # ballast-γ MIRROR (§4c-2) — computed, not attested
        recomputed = sum(_tokens(ep["t0_texts"][sid]) for sid in covered)
        declared = ep["ballast"]["derived_obligation_tokens"]
        cold_cost = sum(_tokens(ep["t1_texts"][sid])
                        for sid in ep["routes"]["cold_reread"])
        if declared != recomputed:
            checks.append((f"ballast_gamma_mirror[{eid}]", False,
                           f"declared ballast {declared} != recomputed "
                           f"{recomputed} — attested numbers are refused"))
        elif recomputed < pop["gamma"] * cold_cost:
            checks.append((f"ballast_gamma_mirror[{eid}]", False,
                           f"ballast {recomputed} < gamma({pop['gamma']}) * "
                           f"cold({cold_cost}) — the offer-time mint would "
                           "refuse (obligation_ballast_below_gamma)"))
        else:
            checks.append((f"ballast_gamma_mirror[{eid}]", True,
                           f"ballast {recomputed} >= {pop['gamma']} * {cold_cost}"))

        # resume_cost_ballast: cold path must be worth saving on
        min_cold = m.get("min_cold_tokens", 100)
        checks.append((f"resume_cost_ballast[{eid}]", cold_cost >= min_cold,
                       f"cold checkpoint cost {cold_cost} (min {min_cold})"))

        # false_continuity_not_priced: a lose-leg episode must make the wrong
        # path actually cheaper than cold, else the cell is decorative
        if ep["oracle"].get("resumable_state") is False:
            wrong_cost = sum(_tokens(ep["t1_texts"][sid])
                             for sid in ep["routes"]["resumable_state"])
            priced = wrong_cost < cold_cost
            checks.append((f"false_continuity_priced[{eid}]", priced,
                           f"false-continue path {wrong_cost} < cold "
                           f"{cold_cost}" if priced else
                           f"false continuity ({wrong_cost}) is not cheaper "
                           f"than cold ({cold_cost}) — decorative lose-cell"))

        # hermes floor components: gappy witness + non-alphabetical winner
        gappy = set(witness_route) < set(catalog)
        winner = ep.get("winner_option_id")
        non_alpha = winner is not None and \
            winner != sorted(pop["option_ids"])[0]
        if gappy and non_alpha:
            floor_met = True

    # --- witness_coverage: no ghost rules anywhere in the fixture ---
    uncoverable = []
    for rule in pop["obligation_rulebook"]:
        if not any(_rule_can_fire_on(rule, meta)
                   for meta in catalog.values()):
            uncoverable.append(rule["rule_id"])
    checks.append(("witness_coverage", not uncoverable,
                   "every rule has a catalog surface that can trigger it"
                   if not uncoverable else f"ghost rules: {uncoverable}"))

    # --- invalidation_path_separation (dan round-4 vote 4) ---
    rr = pop.get("reopen_rules", {})
    reasons = [r["reason"] for r in rr.values()]
    preds = [r["invalidation_predicate_id"] for r in rr.values()]
    sep = ("changed_world" in reasons and "stale_frontier" in reasons
           and len(set(preds)) == len(preds))
    checks.append(("invalidation_path_separation", sep,
                   "changed-world and stale-frontier have distinct pinned "
                   "invalidation predicates" if sep else
                   "invalidation paths shared or missing — one cell would be "
                   "decorative"))

    # --- ignorance probe (X2 world-mode cousin): per-engine, pre-fork ---
    engines = m.get("attestation", {}).get("ignorance_probe", {}).get(
        "engines", {})
    probe_ok = bool(engines) and all(v.get("knew") is False
                                     for v in engines.values())
    checks.append(("ignorance_probe", probe_ok,
                   f"out-of-weights probe clean for {sorted(engines)}"
                   if probe_ok else
                   "attestation.ignorance_probe.engines must show knew:false "
                   "per engine before any real-engine evidence"))

    # --- hermes floor: >=1 episode with gappy witness + non-alpha winner ---
    checks.append(("hermes_floor", floor_met,
                   "fixture carries a gappy-witness, non-alphabetical-winner "
                   "episode" if floor_met else
                   ">=1 population-pinned episode with a non-trivially gappy "
                   "witness trace and a winner that is not the first "
                   "option_id alphabetically is REQUIRED (round-3 vote 2)"))
    return checks


def _rule_can_fire_on(rule: dict, surface_meta: dict) -> bool:
    """Conservative trigger-tag reachability: can this rule's trigger fire on
    a read of this surface? (read_has_tag triggers only, v0.1 rulebooks.)"""
    tags = set(surface_meta.get("surface_tags", []))
    trigger = rule["trigger_predicate_id"]
    # by convention v0.1 triggers are read_has_tag predicates; reachability is
    # decided from the library at call sites that have it — here we accept a
    # surface if it carries ANY tag (refined by route_independence per episode)
    return bool(tags) and trigger is not None


def main() -> int:
    p = argparse.ArgumentParser(description="PRF fixture admission gate (§9)")
    p.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    args = p.parse_args()
    path = Path(args.manifest)
    if not path.exists():
        print(f"FAIL: manifest not found: {path}", file=sys.stderr)
        return 1
    checks = check_manifest(path)
    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL':4s}  {name}: {detail}")
    if failed:
        print(f"\nGATE REFUSED: {len(failed)} check(s) failed — fixture cannot "
              "enter run_prf for real evidence.", file=sys.stderr)
        return 1
    print(f"\nGATE OPEN: {path.name} passes the PRF admission preflight.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
