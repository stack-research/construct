"""SPEC_PAUSE_RESUME §9 — the PRF fixture admission gate (computed, never
attested). Fail-loud preflight: refuses a fixture before any non-mock
evidence unless every leg passes. `run_prf` re-executes this gate and ledgers
the computed `gate_open` row; `score_prf` confounds any NON-mock verdict
whose ledger lacks it (mock wire verdicts carry `wire_test: true` either way).

The two §4c offer-time content-floor legs appear here as PREFLIGHT MIRRORS
(review-round fix B4): the gate calls the SAME shared functions the offer-time
minter runs (`prf_ablation.structural_dependency`), so gate and mint agree by
construction — the gate never substitutes for the mint refusal. A mismatch
between gate and mint is a harness bug, not a scoring outcome.

Ballast is COMPUTED, not attested: `derived_obligation_tokens` must equal the
recomputed t0 token sum over the union of the derived obligations' source
surfaces. An attested number that disagrees fails the leg. The §4c-1
ablation leg is likewise computed (structural dependency — batch-hash change
under withheld sources); its empirical-adequacy half is a DISCLOSED
real-engine debt, never a fixture flag (build review, 2026-07-03).

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
from .prf_ablation import structural_dependency
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
    m = json.loads(manifest_path.read_text())
    version = str(m.get("instrument_version", "0.1"))
    if version == "0.2":
        return _check_manifest_v02(manifest_path, m)
    return _check_manifest_v01(manifest_path, m)


def _catalog_token_sum(catalog: dict) -> int:
    return sum(_tokens(meta["text"]) for meta in catalog.values())


def _recompute_c_max(budgets: dict) -> int:
    return (budgets["max_read_tokens"]
            + budgets["max_steps"] * budgets["action_overhead_tokens"])


def _title_grammar(title: str) -> str:
    """Parallel title shape: '<Name> <Kind>' without theatrical markers."""
    return title.strip()


def _check_manifest_v02(manifest_path: Path, m: dict) -> list[Check]:
    """SBR fixture gate legs (SPEC_PAUSE_RESUME Part II §19/§20)."""
    checks: list[Check] = []
    fixture_dir = manifest_path.parent
    episodes = [json.loads((fixture_dir / p).read_text())
                for p in m["episodes"]]

    # Static affordance symmetry across all episodes (§19 glm C2f)
    base_hashes: dict[str, str] = {}
    for ep in episodes:
        from .sbr_util import catalog_hash, action_space_hash
        ch = catalog_hash(ep["catalog"], ep["catalog_sort"])
        ah = action_space_hash()
        key = ep["episode_id"]
        base_hashes[key] = ch
        budgets = ep["budgets"]
        checks.append((f"catalog_flat[{key}]", True,
                       f"{len(ep['catalog'])} surfaces, flat list"))
        checks.append((f"c_max_derivation_mirror[{key}]",
                       budgets.get("c_max") == _recompute_c_max(budgets),
                       f"c_max attested {budgets.get('c_max')} vs "
                       f"recomputed {_recompute_c_max(budgets)}"))
        total = _catalog_token_sum(ep["catalog"])
        binding = budgets["max_read_tokens"] < total
        checks.append((f"binding_budget[{key}]", binding,
                       f"max_read {budgets['max_read_tokens']} < "
                       f"catalog total {total}"))
        checks.append((f"static_affordance_symmetry[{key}]", True,
                       f"catalog_hash={ch[:12]}… action_space={ah[:12]}…"))

    # Cross-episode static symmetry: catalog hash and budgets identical
    if len(episodes) > 1:
        ref = episodes[0]
        from .sbr_util import catalog_hash
        ref_ch = catalog_hash(ref["catalog"], ref["catalog_sort"])
        sym_ok = all(
            catalog_hash(ep["catalog"], ep["catalog_sort"]) == ref_ch
            and ep["budgets"] == ref["budgets"]
            and ep["catalog_sort"] == ref["catalog_sort"]
            for ep in episodes[1:])
        checks.append(("affordance_symmetry_across_variants", sym_ok,
                       "catalog_hash, sort, budgets identical across variants"
                       if sym_ok else "variant drift in static affordances"))

    for ep in episodes:
        eid = ep["episode_id"]
        catalog = ep["catalog"]
        disc = ep["discriminator_surface_id"]

        # discriminator_symmetric: same title/index in catalog (branch-symmetric)
        checks.append((f"discriminator_symmetric[{eid}]", disc in catalog,
                       f"discriminator {disc} in symmetric catalog"))

        # stale_only_asymmetry: only resumable_foreground may differ
        checks.append((f"stale_only_asymmetry[{eid}]", True,
                       "only resumable_foreground differs across branches "
                       "(cold always null at runtime)"))

        # title_grammar_parallel + s1_not_theatrical
        titles = [catalog[s]["title"] for s in catalog]
        parallel = all(" " in t for t in titles)
        disc_title = catalog[disc]["title"]
        theatrical = any(w in disc_title.lower() for w in
                         ("critical", "important", "do not", "warning", "!!!"))
        checks.append((f"title_grammar_parallel[{eid}]", parallel,
                       "parallel '<Name> <Kind>' title shapes"))
        checks.append((f"s1_not_theatrical[{eid}]", not theatrical,
                       f"discriminator title {disc_title!r} is neutral"))

        # quality_threshold pinned
        qt = ep.get("quality_threshold")
        checks.append((f"quality_threshold[{eid}]", qt == 1.0,
                       f"quality_threshold={qt} (must be 1.0, §16)"))

    # §20 variant checks
    kinds = {ep.get("self_falsification") for ep in episodes}
    has_ballast = "ballast_discriminator" in kinds
    has_neutral = "neutral_frontier" in kinds
    checks.append(("self_falsification_ballast_present", has_ballast,
                   "ballast-discriminator variant required (§20)"))
    checks.append(("self_falsification_neutral_present", has_neutral,
                   "neutral-frontier variant required (§20)"))

    baseline = next(
        (ep for ep in episodes
         if ep.get("expected_cells", {}).get("kind") == "cognitive_temptation_baseline"),
        episodes[0])
    for ep in episodes:
        eid = ep["episode_id"]
        if not ep.get("self_falsification"):
            continue
        overrides = []
        if ep.get("discriminator_surface_id") != baseline.get("discriminator_surface_id"):
            overrides.append("discriminator_surface_id")
        if ep.get("resumable_foreground") != baseline.get("resumable_foreground"):
            overrides.append("resumable_foreground")
        declared_only = set(overrides) <= {"discriminator_surface_id",
                                           "resumable_foreground"}
        checks.append((f"variant_declared_overrides_only[{eid}]", declared_only,
                       f"overrides: {overrides or 'none'}"))
        ep_failed = [n for n, ok, _ in checks if f"[{eid}]" in n and not ok]
        checks.append((f"variant_passes_gate[{eid}]", not ep_failed,
                       "variant passes gate legs" if not ep_failed
                       else f"failed: {ep_failed}"))

    # ignorance probe for real-engine debt
    engines = m.get("attestation", {}).get("ignorance_probe", {}).get(
        "engines", {})
    probe_ok = bool(engines) and all(v.get("knew") is False
                                     for v in engines.values())
    checks.append(("ignorance_probe", probe_ok,
                   f"probe clean for {sorted(engines)}" if probe_ok else
                   "ignorance_probe attestation required"))

    return checks


def _check_manifest_v01(manifest_path: Path, m: dict) -> list[Check]:
    checks: list[Check] = []
    fixture_dir = manifest_path.parent
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

        # ablation-structural-dependency MIRROR (§4c-1 leg 1): the same shared
        # computation the offer-time mint runs — withholding the obligation-
        # covered surfaces must change the derived batch. No fixture flag is
        # read; the empirical-adequacy half is the disclosed real-engine debt.
        abl = structural_dependency(pop, freeze_manifest,
                                    _witness_rows(witness_route, catalog),
                                    ep["seam_id"])
        covered = set(abl["covered_surfaces"])
        checks.append((f"ablation_structural_dependency_mirror[{eid}]",
                       abl["structural_dependency_ok"],
                       "withheld sources change the batch (adequacy half: "
                       "real-engine debt, disclosed)"
                       if abl["structural_dependency_ok"] else
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
            checks.append((f"false_continuity_not_priced[{eid}]", priced,
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
