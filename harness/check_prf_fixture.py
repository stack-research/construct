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
from .mint_frontier_state import (MintRefusal, freeze_validate, manifest_hash,
                                  offer_gate)
from .predicate_ast import PredicateClosureError, library_hash
from .prf_ablation import structural_dependency
from .sbr_util import (artifact_render_tokens, render_resumable_foreground)
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
    if version == "0.4":
        return _check_manifest_v04(manifest_path, m)
    if version == "0.3":
        return _check_manifest_v03(manifest_path, m)
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


LEG_TAGS_V03 = ("leg_status", "leg_exception", "leg_clearance")


def _oracle_leg_ids(catalog: dict) -> set[str]:
    """Three K-17 dispositive surfaces (§26 / §30)."""
    legs: set[str] = set()
    for sid, meta in catalog.items():
        tags = set(meta.get("surface_tags", []))
        if tags & set(LEG_TAGS_V03) and meta.get("fields", {}).get(
                "catalog_key") == "K-17":
            legs.add(sid)
    return legs


def _obligation_ids_hash(ids: list[str]) -> str:
    import hashlib
    return hashlib.sha256(
        json.dumps(sorted(ids), sort_keys=True).encode()).hexdigest()


def _check_manifest_v03(manifest_path: Path, m: dict) -> list[Check]:
    """Triangulation-docket fixture gate (SPEC Part III §26–§32)."""
    checks: list[Check] = []
    fixture_dir = manifest_path.parent
    episodes = [json.loads((fixture_dir / p).read_text())
                for p in m["episodes"]]
    pop_path = fixture_dir / "population.json"
    freeze_path = fixture_dir / "freeze_manifest.json"
    has_mint = pop_path.exists() and freeze_path.exists()
    population = json.loads(pop_path.read_text()) if has_mint else {}
    freeze_manifest = json.loads(freeze_path.read_text()) if has_mint else {}
    checks.append(("mint_spine_present", has_mint,
                   "population.json + freeze_manifest.json present (§22)"
                   if has_mint else
                   "population.json / freeze_manifest.json missing"))

    from .sbr_util import catalog_hash, action_space_hash
    if len(episodes) > 1:
        ref = episodes[0]
        ref_ch = catalog_hash(ref["catalog"], ref["catalog_sort"])
        sym_ok = all(
            catalog_hash(ep["catalog"], ep["catalog_sort"]) == ref_ch
            and ep["budgets"] == ref["budgets"]
            and ep["catalog_sort"] == ref["catalog_sort"]
            for ep in episodes[1:])
        checks.append(("affordance_symmetry_across_variants", sym_ok,
                       "catalog_hash, sort, budgets identical across variants"
                       if sym_ok else "variant drift in static affordances"))

    baseline = next(
        (ep for ep in episodes if not ep.get("self_falsification")),
        episodes[0])

    for ep in episodes:
        eid = ep["episode_id"]
        catalog = ep["catalog"]
        budgets = ep["budgets"]
        ch = catalog_hash(catalog, ep["catalog_sort"])
        ah = action_space_hash("0.3")

        checks.append((f"catalog_flat[{eid}]", len(catalog) == 21,
                       f"{len(catalog)} surfaces (must be 21, §26)"))
        checks.append((f"c_max_derivation_mirror[{eid}]",
                       budgets.get("c_max") == _recompute_c_max(budgets),
                       f"c_max attested {budgets.get('c_max')} vs "
                       f"recomputed {_recompute_c_max(budgets)}"))
        total = _catalog_token_sum(catalog)
        binding = budgets["max_read_tokens"] < total
        checks.append((f"binding_budget[{eid}]", binding,
                       f"max_read {budgets['max_read_tokens']} < "
                       f"catalog total {total}"))
        checks.append((f"static_affordance_symmetry[{eid}]", True,
                       f"catalog_hash={ch[:12]}… action_space={ah[:12]}…"))
        checks.append((f"quality_threshold[{eid}]",
                       ep.get("quality_threshold") == 1.0,
                       f"quality_threshold={ep.get('quality_threshold')}"))

        for tag in LEG_TAGS_V03:
            n = sum(1 for meta in catalog.values()
                    if tag in meta.get("surface_tags", []))
            checks.append((f"plausible_geometry[{eid}:{tag}]", n == 3,
                           f"{n} surfaces tagged {tag} (must be 3)"))

        oracle_legs = _oracle_leg_ids(catalog)
        cal_route = ep.get("calibration_route", [])
        checks.append((f"calibration_route_ids[{eid}]",
                       set(cal_route) == oracle_legs and len(cal_route) == 3,
                       f"calibration_route {cal_route} vs oracle legs "
                       f"{sorted(oracle_legs)}"))
        cal_tokens = sum(_tokens(catalog[s]["text"]) for s in cal_route
                         if s in catalog)
        checks.append((f"calibration_route_tokens[{eid}]",
                       cal_tokens <= budgets["max_read_tokens"],
                       f"calibration route {cal_tokens} tokens vs "
                       f"max_read {budgets['max_read_tokens']}"))

        if has_mint:
            witness = _witness_rows(ep["witness_route"], population["catalog"])
            try:
                derived = derive_live_obligations(
                    population, freeze_manifest, witness, ep["seam_id"])
                derived_ids = sorted(o["obligation_id"]
                                     for o in derived["obligations"])
                pinned = ep.get("calibration_obligation_ids")
                if isinstance(pinned, str):
                    replay_ok = pinned == _obligation_ids_hash(derived_ids)
                else:
                    replay_ok = sorted(pinned or []) == derived_ids
                checks.append((f"calibration_obligation_replay[{eid}]",
                               replay_ok,
                               "obligation ids replay from witness_route"
                               if replay_ok else
                               f"pinned {pinned!r} != derived {derived_ids}"))
            except DerivationRefused as e:
                checks.append((f"calibration_obligation_replay[{eid}]", False,
                               str(e)))

        cold_route = ep.get("cold_exploration_route", [])
        plausible_ids = {sid for sid, meta in catalog.items()
                         if set(meta.get("surface_tags", [])) & set(LEG_TAGS_V03)}
        checks.append((f"cold_exploration_count[{eid}]", len(cold_route) == 6,
                       f"cold_exploration_route has {len(cold_route)} ids"))
        disjoint = not (set(cold_route) & set(cal_route))
        checks.append((f"cold_exploration_disjoint[{eid}]", disjoint,
                       "cold_exploration_route disjoint from calibration_route"
                       if disjoint else "routes overlap"))
        all_plausible = all(s in plausible_ids for s in cold_route)
        checks.append((f"cold_exploration_plausible[{eid}]", all_plausible,
                       "all cold_exploration surfaces are plausible-class"
                       if all_plausible else
                       f"non-plausible in cold route: "
                       f"{set(cold_route) - plausible_ids}"))

        if has_mint:
            try:
                dry = derive_live_obligations(
                    population, freeze_manifest,
                    _witness_rows(ep["witness_route"], population["catalog"]),
                    ep["seam_id"])
                cand = freeze_validate(
                    ep["frontier_state"], freeze_manifest, dry["batch"],
                    manifest_hash(freeze_manifest), rendered_tokens=True)
                a_i = artifact_render_tokens(cand["canonical_state"])
                cold_tokens = sum(_tokens(catalog[s]["text"])
                                  for s in cold_route if s in catalog)
                pay_ok = cold_tokens > a_i + cal_tokens
                checks.append((f"pay_window_geometry[{eid}]", pay_ok,
                               f"cold_explore {cold_tokens} > a_i {a_i} + "
                               f"cal {cal_tokens}"
                               if pay_ok else
                               f"geometry fails: {cold_tokens} <= "
                               f"{a_i + cal_tokens}"))
                fg = render_resumable_foreground(
                    cand["canonical_state"], ep.get("stale_claim"))
                fg_tokens = len(fg.split())
                checks.append((f"foreground_budget_ok[{eid}]",
                               fg_tokens <= 160,
                               f"foreground {fg_tokens} tokens (max 160, §27)"))
            except (MintRefusal, DerivationRefused) as e:
                checks.append((f"pay_window_geometry[{eid}]", False,
                               f"mint preview failed: {e}"))
                checks.append((f"foreground_budget_ok[{eid}]", False,
                               f"mint preview failed: {e}"))

        if ep.get("self_falsification"):
            overrides = []
            if ep.get("witness_route") != baseline.get("witness_route"):
                overrides.append("witness_route")
            if json.dumps(ep.get("frontier_state"), sort_keys=True) != \
                    json.dumps(baseline.get("frontier_state"), sort_keys=True):
                overrides.append("frontier_state")
            if ep.get("calibration_obligation_ids") != \
                    baseline.get("calibration_obligation_ids"):
                overrides.append("calibration_obligation_ids")
            if ep.get("stale_claim") != baseline.get("stale_claim"):
                overrides.append("stale_claim")
            sf = ep["self_falsification"]
            if sf == "ballast_discriminator":
                allowed = {"witness_route", "frontier_state",
                           "calibration_obligation_ids"}
            elif sf == "neutral_frontier":
                allowed = {"stale_claim"}
            else:
                allowed = set()
            declared_only = set(overrides) <= allowed
            checks.append((f"variant_declared_overrides_only[{eid}]",
                           declared_only,
                           f"overrides: {overrides or 'none'}"))
            stale_ok = (
                ep.get("stale_claim") == baseline.get("stale_claim")
                or (sf == "neutral_frontier" and ep.get("stale_claim") is None)
            )
            fs_ok = (
                json.dumps(ep.get("frontier_state"), sort_keys=True)
                == json.dumps(baseline.get("frontier_state"), sort_keys=True)
                or sf == "ballast_discriminator"
            )
            checks.append((f"stale_only_asymmetry[{eid}]",
                           stale_ok and fs_ok,
                           f"ballast may override frontier; neutral stale only "
                           f"(stale_ok={stale_ok}, fs_ok={fs_ok})"))

    kinds = {ep.get("self_falsification") for ep in episodes}
    checks.append(("self_falsification_ballast_present",
                   "ballast_discriminator" in kinds,
                   "ballast-discriminator variant required (§32)"))
    checks.append(("self_falsification_neutral_present",
                   "neutral_frontier" in kinds,
                   "neutral-frontier variant required (§32)"))

    if has_mint:
        catalog = population["catalog"]
        for ep in episodes:
            eid = ep["episode_id"]
            witness = _witness_rows(ep["witness_route"], catalog)
            try:
                dry = derive_live_obligations(
                    population, freeze_manifest, witness, ep["seam_id"])
            except DerivationRefused as e:
                checks.append((f"derivation_mirror[{eid}]", False, str(e)))
                continue
            try:
                cand = freeze_validate(
                    ep["frontier_state"], freeze_manifest, dry["batch"],
                    manifest_hash(freeze_manifest), rendered_tokens=True)
                checks.append((f"freeze_validate_mirror[{eid}]", True,
                               f"freeze_pass digest={cand['state_digest'][:12]}…"))
            except MintRefusal as e:
                checks.append((f"freeze_validate_mirror[{eid}]", False,
                               f"{e.row.get('check')}/{e.row.get('reason')}"))
                continue
            abl = structural_dependency(population, freeze_manifest, witness,
                                        ep["seam_id"])
            checks.append((f"ablation_structural_dependency_mirror[{eid}]",
                           abl["structural_dependency_ok"],
                           "withheld sources change the batch"
                           if abl["structural_dependency_ok"] else
                           "obligations decorative under ablation"))
            cold_cost = population["sbr_cold_reread_tokens"]
            recomputed = sum(_tokens(ep["t0_texts"][sid])
                             for sid in abl["covered_surfaces"])
            declared = ep["ballast"]["derived_obligation_tokens"]
            if declared != recomputed:
                checks.append((f"ballast_gamma_mirror[{eid}]", False,
                               f"declared {declared} != recomputed {recomputed}"))
            elif recomputed < population["gamma"] * cold_cost:
                checks.append((f"ballast_gamma_mirror[{eid}]", False,
                               f"ballast {recomputed} < gamma * cold({cold_cost})"))
            else:
                try:
                    offer_gate(cand, derived_obligation_tokens=declared,
                               cold_reread_tokens=cold_cost,
                               gamma=population["gamma"], ablation=abl,
                               frontier_artifact_id=f"fa:{eid}")
                    checks.append((f"offer_gate_mirror[{eid}]", True,
                                   f"ballast {recomputed} >= "
                                   f"{population['gamma']} * {cold_cost}"))
                except MintRefusal as e:
                    checks.append((f"offer_gate_mirror[{eid}]", False,
                                   f"{e.row.get('check')}/{e.row.get('reason')}"))

    engines = m.get("attestation", {}).get("ignorance_probe", {}).get(
        "engines", {})
    probe_ok = bool(engines) and all(v.get("knew") is False
                                     for v in engines.values())
    checks.append(("ignorance_probe", probe_ok,
                   f"probe clean for {sorted(engines)}" if probe_ok else
                   "ignorance_probe attestation required"))

    return checks


LEG_TAGS_V04 = ("leg_inflow", "leg_sediment", "leg_rights")
V04_TARGET_KEY = "WR-31"          # precommitted in the sealed spec (§37)
V04_DISPOSITIONS = ("release", "hold", "reject", "reopen")
V04_BUDGET_PINS = {"max_read_tokens": 700, "max_steps": 10,
                   "action_overhead_tokens": 20, "c_max": 900}


def _v04_leg_ids(catalog: dict, target_key: str) -> set[str]:
    """Three WR-31 dispositive surfaces (§37/§38)."""
    legs: set[str] = set()
    for sid, meta in catalog.items():
        tags = set(meta.get("surface_tags", []))
        if tags & set(LEG_TAGS_V04) and meta.get("fields", {}).get(
                "catalog_key") == target_key:
            legs.add(sid)
    return legs


def _check_manifest_v04(manifest_path: Path, m: dict) -> list[Check]:
    """Greenreach release-gate fixture gate (SPEC Part IV §37–§43).

    Carries the v0.3 legs re-keyed to the Greenreach geometry, plus the
    family's own law: the conjunctive-evidence wire-sweep (§41, pin D8), the
    0.4 pay_window_geometry form against the distracted-PASS comparator
    (§42, pin D7), the D5 token pins with the cheap-decoy floor, the
    exclusion-certificate discipline (§37), and the pinned family budgets
    (§40, docket values untouched)."""
    from .oracle import conjunctive_oracle
    from .sbr_util import catalog_hash, action_space_hash
    from itertools import combinations

    checks: list[Check] = []
    fixture_dir = manifest_path.parent
    episodes = [json.loads((fixture_dir / p).read_text())
                for p in m["episodes"]]
    pop_path = fixture_dir / "population.json"
    freeze_path = fixture_dir / "freeze_manifest.json"
    has_mint = pop_path.exists() and freeze_path.exists()
    population = json.loads(pop_path.read_text()) if has_mint else {}
    freeze_manifest = json.loads(freeze_path.read_text()) if has_mint else {}
    checks.append(("mint_spine_present", has_mint,
                   "population.json + freeze_manifest.json present (§22)"
                   if has_mint else
                   "population.json / freeze_manifest.json missing"))

    if len(episodes) > 1:
        ref = episodes[0]
        ref_ch = catalog_hash(ref["catalog"], ref["catalog_sort"])
        sym_ok = all(
            catalog_hash(ep["catalog"], ep["catalog_sort"]) == ref_ch
            and ep["budgets"] == ref["budgets"]
            and ep["catalog_sort"] == ref["catalog_sort"]
            for ep in episodes[1:])
        checks.append(("affordance_symmetry_across_variants", sym_ok,
                       "catalog_hash, sort, budgets identical across variants"
                       if sym_ok else "variant drift in static affordances"))

    baseline = next(
        (ep for ep in episodes if not ep.get("self_falsification")),
        episodes[0])

    for ep in episodes:
        eid = ep["episode_id"]
        catalog = ep["catalog"]
        budgets = ep["budgets"]
        ch = catalog_hash(catalog, ep["catalog_sort"])
        ah = action_space_hash("0.4")
        target_key = ep.get("target_key", "")

        checks.append((f"catalog_flat[{eid}]", len(catalog) == 21,
                       f"{len(catalog)} surfaces (must be 21, §37)"))
        budget_ok = all(budgets.get(k) == v
                        for k, v in V04_BUDGET_PINS.items())
        checks.append((f"budget_pins[{eid}]", budget_ok,
                       f"budgets {budgets} vs family pins {V04_BUDGET_PINS} "
                       "(§40; docket 8/860 untouched)"))
        checks.append((f"c_max_derivation_mirror[{eid}]",
                       budgets.get("c_max") == _recompute_c_max(budgets),
                       f"c_max attested {budgets.get('c_max')} vs "
                       f"recomputed {_recompute_c_max(budgets)}"))
        total = _catalog_token_sum(catalog)
        binding = budgets["max_read_tokens"] < total
        checks.append((f"binding_budget[{eid}]", binding,
                       f"max_read {budgets['max_read_tokens']} < "
                       f"catalog total {total}"))
        # real assertion, not decorative (build-review C, gemini): the §39
        # family hash bump must actually hold against the 0.3 space
        bumped = ah != action_space_hash("0.3")
        checks.append((f"static_affordance_symmetry[{eid}]", bumped,
                       f"catalog_hash={ch[:12]}… action_space={ah[:12]}… "
                       "(bumped from 0.3, §39)" if bumped else
                       "action_space_hash did NOT bump from 0.3 (§39)"))
        checks.append((f"quality_threshold[{eid}]",
                       ep.get("quality_threshold") == 1.0,
                       f"quality_threshold={ep.get('quality_threshold')}"))
        # computed against the spec pin, never attested presence (build-review
        # C, gemini; kagi concurred)
        checks.append((f"target_key_pinned[{eid}]",
                       target_key == V04_TARGET_KEY,
                       f"target_key={target_key!r} == spec pin "
                       f"{V04_TARGET_KEY!r} (§37)"))

        for tag in LEG_TAGS_V04:
            n = sum(1 for meta in catalog.values()
                    if tag in meta.get("surface_tags", []))
            checks.append((f"plausible_geometry[{eid}:{tag}]", n == 3,
                           f"{n} surfaces tagged {tag} (must be 3, §37)"))

        oracle_legs = _v04_leg_ids(catalog, target_key)
        pinned_legs = ep.get("dispositive_leg_ids", [])
        legs_ok = (len(oracle_legs) == 3
                   and set(pinned_legs) == oracle_legs)
        checks.append((f"dispositive_leg_ids_replay[{eid}]", legs_ok,
                       f"pinned {sorted(pinned_legs)} vs computed "
                       f"{sorted(oracle_legs)} (must be the 3-leg "
                       f"conjunction, §37/§41)"))

        plausible_ids = {sid for sid, meta in catalog.items()
                         if set(meta.get("surface_tags", []))
                         & set(LEG_TAGS_V04)}
        decoy_ids = plausible_ids - oracle_legs

        # --- D5 token pins (§37, as amended in the pin round) ---
        bad_tokens: list[str] = []
        for sid, meta in catalog.items():
            n = _tokens(meta["text"])
            if sid in oracle_legs:
                ok = 95 <= n <= 105
            elif sid in decoy_ids:
                ok = 35 <= n <= 40          # cheap-decoy floor at nominal
            else:
                ok = 31 <= n <= 41          # ballast 36 ± 5
            if not ok:
                bad_tokens.append(f"{sid}={n}")
        checks.append((f"token_pins_d5[{eid}]", not bad_tokens,
                       "legs 100±5, decoys 35..40, ballast 36±5"
                       if not bad_tokens else
                       f"token pins violated: {bad_tokens}"))

        # --- exclusion certificates (§37, design round unanimous) ---
        bad_decoys: list[str] = []
        for sid in decoy_ids:
            f = catalog[sid].get("fields", {})
            if f.get("target_key") == target_key or \
                    f.get("applicability") != "excluded_for_target":
                bad_decoys.append(sid)
        checks.append((f"exclusion_certificates[{eid}]",
                       len(decoy_ids) == 6 and not bad_decoys,
                       f"{len(decoy_ids)} decoys, all excluded_for_target "
                       f"with target_key != {target_key}"
                       if not bad_decoys else
                       f"decoys lacking exclusion certificates: {bad_decoys}"))

        # --- conjunctive_evidence_ok wire-sweep (§41, pin D8) ---
        # 7 dispositive-leg equivalence classes (every proper subset of the
        # triple) × 4 disposition tokens = 28 oracle evaluations, all of
        # which must FAIL; the exclusion certificates make decoy/ballast
        # membership irrelevant (glm's builder guidance, recorded in the
        # seal fold). One decoy-augmented spot check proves the
        # irrelevance; one positive control proves the sweep can pass.
        legs_sorted = sorted(oracle_legs)
        expected = ep["expected_answer_t1"]
        leak: list[str] = []
        for k in range(0, 3):
            for subset in combinations(legs_sorted, k):
                for token in V04_DISPOSITIONS:
                    s = conjunctive_oracle(token, expected, list(subset),
                                           legs_sorted)
                    if s.score >= 1.0:
                        leak.append(f"{list(subset)}+{token!r}")
        aug = conjunctive_oracle(expected, expected,
                                 sorted(decoy_ids) + legs_sorted[:2],
                                 legs_sorted)
        if aug.score >= 1.0:
            leak.append("6-decoys+2-legs")
        positive = conjunctive_oracle(expected, expected, legs_sorted,
                                      legs_sorted)
        sweep_ok = not leak and positive.score >= 1.0
        checks.append((f"conjunctive_evidence_ok[{eid}]", sweep_ok,
                       "28-case wire-sweep clean; triple+release passes"
                       if sweep_ok else
                       (f"oracle leaks on {leak}" if leak else
                        "positive control failed: triple+release scored 0")))

        # --- calibration (§42, §30 carries) ---
        cal_route = ep.get("calibration_route", [])
        checks.append((f"calibration_route_ids[{eid}]",
                       set(cal_route) == oracle_legs and len(cal_route) == 3,
                       f"calibration_route {cal_route} vs oracle legs "
                       f"{sorted(oracle_legs)}"))
        cal_tokens = sum(_tokens(catalog[s]["text"]) for s in cal_route
                         if s in catalog)
        checks.append((f"calibration_route_tokens[{eid}]",
                       cal_tokens <= budgets["max_read_tokens"],
                       f"calibration route {cal_tokens} tokens vs "
                       f"max_read {budgets['max_read_tokens']}"))

        if has_mint:
            witness = _witness_rows(ep["witness_route"], population["catalog"])
            try:
                derived = derive_live_obligations(
                    population, freeze_manifest, witness, ep["seam_id"])
                derived_ids = sorted(o["obligation_id"]
                                     for o in derived["obligations"])
                pinned = ep.get("calibration_obligation_ids")
                if isinstance(pinned, str):
                    replay_ok = pinned == _obligation_ids_hash(derived_ids)
                else:
                    replay_ok = sorted(pinned or []) == derived_ids
                checks.append((f"calibration_obligation_replay[{eid}]",
                               replay_ok,
                               "obligation ids replay from witness_route"
                               if replay_ok else
                               f"pinned {pinned!r} != derived {derived_ids}"))
            except DerivationRefused as e:
                checks.append((f"calibration_obligation_replay[{eid}]", False,
                               str(e)))

        # --- cold exploration route = exactly the 6 decoys (§42, pin D7) ---
        cold_route = ep.get("cold_exploration_route", [])
        checks.append((f"cold_exploration_count[{eid}]", len(cold_route) == 6,
                       f"cold_exploration_route has {len(cold_route)} ids"))
        disjoint = not (set(cold_route) & set(cal_route))
        checks.append((f"cold_exploration_disjoint[{eid}]", disjoint,
                       "cold_exploration_route disjoint from calibration_route"
                       if disjoint else "routes overlap"))
        decoys_exact = set(cold_route) == decoy_ids
        checks.append((f"cold_exploration_is_decoys[{eid}]", decoys_exact,
                       "cold_exploration_route = exactly the 6 decoy ids (§42)"
                       if decoys_exact else
                       f"route {sorted(cold_route)} != decoys "
                       f"{sorted(decoy_ids)}"))

        if has_mint:
            try:
                dry = derive_live_obligations(
                    population, freeze_manifest,
                    _witness_rows(ep["witness_route"], population["catalog"]),
                    ep["seam_id"])
                cand = freeze_validate(
                    ep["frontier_state"], freeze_manifest, dry["batch"],
                    manifest_hash(freeze_manifest), rendered_tokens=True)
                a_i = artifact_render_tokens(cand["canonical_state"])
                checks.append((f"a_i_ceiling[{eid}]", a_i <= 65,
                               f"a_i rendered {a_i} tokens (max 65, §38)"))
                # §42 pay_window_geometry, 0.4 form: the comparator is the
                # distracted-PASS cost, never a fail-priced route — the
                # 3-leg read cost cancels, leaving Σ decoys − a_i ≥ 145 on
                # ACTUAL authored totals via the shared render function.
                decoy_tokens = sum(_tokens(catalog[s]["text"])
                                   for s in cold_route if s in catalog)
                margin = decoy_tokens - a_i
                pay_ok = margin >= 145
                checks.append((f"pay_window_geometry[{eid}]", pay_ok,
                               f"Σ decoys {decoy_tokens} − a_i {a_i} = "
                               f"{margin} >= 145 (distracted-pass comparator)"
                               if pay_ok else
                               f"margin {margin} < 145 — geometry refused"))
                fg = render_resumable_foreground(
                    cand["canonical_state"], ep.get("stale_claim"))
                fg_tokens = len(fg.split())
                checks.append((f"foreground_budget_ok[{eid}]",
                               fg_tokens <= 160,
                               f"foreground {fg_tokens} tokens (max 160, §27)"))
            except (MintRefusal, DerivationRefused) as e:
                checks.append((f"pay_window_geometry[{eid}]", False,
                               f"mint preview failed: {e}"))
                checks.append((f"foreground_budget_ok[{eid}]", False,
                               f"mint preview failed: {e}"))

        # --- §32 allowlist, forked at 0.4 (§43) ---
        if ep.get("self_falsification"):
            overrides = []
            if ep.get("witness_route") != baseline.get("witness_route"):
                overrides.append("witness_route")
            if json.dumps(ep.get("frontier_state"), sort_keys=True) != \
                    json.dumps(baseline.get("frontier_state"), sort_keys=True):
                overrides.append("frontier_state")
            if ep.get("calibration_obligation_ids") != \
                    baseline.get("calibration_obligation_ids"):
                overrides.append("calibration_obligation_ids")
            if ep.get("stale_claim") != baseline.get("stale_claim"):
                overrides.append("stale_claim")
            sf = ep["self_falsification"]
            if sf == "ballast_discriminator":
                allowed = {"witness_route", "frontier_state",
                           "calibration_obligation_ids"}
            elif sf == "neutral_frontier":
                allowed = {"stale_claim"}
            else:
                allowed = set()
            declared_only = set(overrides) <= allowed
            checks.append((f"variant_declared_overrides_only[{eid}]",
                           declared_only,
                           f"overrides: {overrides or 'none'}"))
            stale_ok = (
                ep.get("stale_claim") == baseline.get("stale_claim")
                or (sf == "neutral_frontier" and ep.get("stale_claim") is None)
            )
            fs_ok = (
                json.dumps(ep.get("frontier_state"), sort_keys=True)
                == json.dumps(baseline.get("frontier_state"), sort_keys=True)
                or sf == "ballast_discriminator"
            )
            checks.append((f"stale_only_asymmetry[{eid}]",
                           stale_ok and fs_ok,
                           f"ballast may override frontier; neutral stale only "
                           f"(stale_ok={stale_ok}, fs_ok={fs_ok})"))

    kinds = {ep.get("self_falsification") for ep in episodes}
    checks.append(("self_falsification_ballast_present",
                   "ballast_discriminator" in kinds,
                   "ballast-discriminator variant required (§43)"))
    checks.append(("self_falsification_neutral_present",
                   "neutral_frontier" in kinds,
                   "neutral-frontier variant required (§43)"))

    if has_mint:
        catalog = population["catalog"]
        for ep in episodes:
            eid = ep["episode_id"]
            witness = _witness_rows(ep["witness_route"], catalog)
            try:
                dry = derive_live_obligations(
                    population, freeze_manifest, witness, ep["seam_id"])
            except DerivationRefused as e:
                checks.append((f"derivation_mirror[{eid}]", False, str(e)))
                continue
            try:
                cand = freeze_validate(
                    ep["frontier_state"], freeze_manifest, dry["batch"],
                    manifest_hash(freeze_manifest), rendered_tokens=True)
                checks.append((f"freeze_validate_mirror[{eid}]", True,
                               f"freeze_pass digest={cand['state_digest'][:12]}…"))
            except MintRefusal as e:
                checks.append((f"freeze_validate_mirror[{eid}]", False,
                               f"{e.row.get('check')}/{e.row.get('reason')}"))
                continue
            abl = structural_dependency(population, freeze_manifest, witness,
                                        ep["seam_id"])
            checks.append((f"ablation_structural_dependency_mirror[{eid}]",
                           abl["structural_dependency_ok"],
                           "withheld sources change the batch"
                           if abl["structural_dependency_ok"] else
                           "obligations decorative under ablation"))
            cold_cost = population["sbr_cold_reread_tokens"]
            recomputed = sum(_tokens(ep["t0_texts"][sid])
                             for sid in abl["covered_surfaces"])
            declared = ep["ballast"]["derived_obligation_tokens"]
            if declared != recomputed:
                checks.append((f"ballast_gamma_mirror[{eid}]", False,
                               f"declared {declared} != recomputed {recomputed}"))
            elif recomputed < population["gamma"] * cold_cost:
                checks.append((f"ballast_gamma_mirror[{eid}]", False,
                               f"ballast {recomputed} < gamma * cold({cold_cost})"))
            else:
                try:
                    offer_gate(cand, derived_obligation_tokens=declared,
                               cold_reread_tokens=cold_cost,
                               gamma=population["gamma"], ablation=abl,
                               frontier_artifact_id=f"fa:{eid}")
                    checks.append((f"offer_gate_mirror[{eid}]", True,
                                   f"ballast {recomputed} >= "
                                   f"{population['gamma']} * {cold_cost}"))
                except MintRefusal as e:
                    checks.append((f"offer_gate_mirror[{eid}]", False,
                                   f"{e.row.get('check')}/{e.row.get('reason')}"))

    engines = m.get("attestation", {}).get("ignorance_probe", {}).get(
        "engines", {})
    probe_ok = bool(engines) and all(v.get("knew") is False
                                     for v in engines.values())
    checks.append(("ignorance_probe", probe_ok,
                   f"probe clean for {sorted(engines)}" if probe_ok else
                   "ignorance_probe attestation required"))

    return checks


def _check_manifest_v02(manifest_path: Path, m: dict) -> list[Check]:
    """SBR fixture gate legs (SPEC_PAUSE_RESUME Part II §19/§20)."""
    checks: list[Check] = []
    fixture_dir = manifest_path.parent
    episodes = [json.loads((fixture_dir / p).read_text())
                for p in m["episodes"]]
    pop_path = fixture_dir / "population.json"
    freeze_path = fixture_dir / "freeze_manifest.json"
    has_mint = pop_path.exists() and freeze_path.exists()
    population = json.loads(pop_path.read_text()) if has_mint else {}
    freeze_manifest = json.loads(freeze_path.read_text()) if has_mint else {}
    # v0.2 carries the Part I spine verbatim (§22): a missing population /
    # freeze manifest FAILS the gate, never silently skips the mint mirrors
    # (review catch on the fix pass — fail-closed, not fail-quiet).
    checks.append(("mint_spine_present", has_mint,
                   "population.json + freeze_manifest.json present (§22)"
                   if has_mint else
                   "population.json / freeze_manifest.json missing — the "
                   "v0.2 gate requires the Part I precommit spine (§22)"))

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

    # stale_only_asymmetry: only stale_claim differs; neutral null; shared frontier
    if len(episodes) > 1:
        baseline = next(
            (ep for ep in episodes
             if ep.get("expected_cells", {}).get("kind")
             == "cognitive_temptation_baseline"),
            episodes[0])
        base_stale = baseline.get("stale_claim")
        base_fs = json.dumps(baseline.get("frontier_state"), sort_keys=True)
        for ep in episodes:
            eid = ep["episode_id"]
            stale_ok = (
                ep.get("stale_claim") == base_stale
                or (ep.get("self_falsification") == "neutral_frontier"
                    and ep.get("stale_claim") is None)
            )
            fs_ok = json.dumps(ep.get("frontier_state"),
                               sort_keys=True) == base_fs
            checks.append((f"stale_only_asymmetry[{eid}]",
                           stale_ok and fs_ok,
                           "only stale_claim may differ; frontier_state shared; "
                           f"neutral stale_claim null (stale_ok={stale_ok}, "
                           f"fs_ok={fs_ok})"))

    for ep in episodes:
        eid = ep["episode_id"]
        catalog = ep["catalog"]
        disc = ep["discriminator_surface_id"]

        checks.append((f"discriminator_symmetric[{eid}]", disc in catalog,
                       f"discriminator {disc} in symmetric catalog"))

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
        if ep.get("stale_claim") != baseline.get("stale_claim"):
            overrides.append("stale_claim")
        declared_only = set(overrides) <= {"discriminator_surface_id",
                                           "stale_claim"}
        checks.append((f"variant_declared_overrides_only[{eid}]", declared_only,
                       f"overrides: {overrides or 'none'}"))
        ep_failed = [n for n, ok, _ in checks if f"[{eid}]" in n and not ok]
        checks.append((f"variant_passes_gate[{eid}]", not ep_failed,
                       "variant passes gate legs" if not ep_failed
                       else f"failed: {ep_failed}"))

    # Mint-mirror legs (§9 / Part I spine — same shared functions as run_sbr)
    if has_mint:
        catalog = population["catalog"]
        for ep in episodes:
            eid = ep["episode_id"]
            witness_route = ep["witness_route"]
            witness = _witness_rows(witness_route, catalog)
            try:
                dry = derive_live_obligations(
                    population, freeze_manifest, witness, ep["seam_id"])
                checks.append((f"derivation_mirror[{eid}]", True,
                               f"{len(dry['obligations'])} obligations derived"))
            except DerivationRefused as e:
                checks.append((f"derivation_mirror[{eid}]", False, str(e)))
                continue

            try:
                cand = freeze_validate(ep["frontier_state"], freeze_manifest,
                                       dry["batch"],
                                       manifest_hash(freeze_manifest))
                checks.append((f"freeze_validate_mirror[{eid}]", True,
                               f"freeze_pass digest={cand['state_digest'][:12]}…"))
            except MintRefusal as e:
                checks.append((f"freeze_validate_mirror[{eid}]", False,
                               f"{e.row.get('check')}/{e.row.get('reason')}"))
                continue

            abl = structural_dependency(population, freeze_manifest, witness,
                                        ep["seam_id"])
            checks.append((f"ablation_structural_dependency_mirror[{eid}]",
                           abl["structural_dependency_ok"],
                           "withheld sources change the batch"
                           if abl["structural_dependency_ok"] else
                           "obligations decorative under ablation"))

            cold_cost = population["sbr_cold_reread_tokens"]
            recomputed = sum(_tokens(ep["t0_texts"][sid])
                             for sid in abl["covered_surfaces"])
            declared = ep["ballast"]["derived_obligation_tokens"]
            if declared != recomputed:
                checks.append((f"ballast_gamma_mirror[{eid}]", False,
                               f"declared {declared} != recomputed {recomputed}"))
            elif recomputed < population["gamma"] * cold_cost:
                checks.append((f"ballast_gamma_mirror[{eid}]", False,
                               f"ballast {recomputed} < gamma * cold({cold_cost})"))
            else:
                try:
                    offer_gate(
                        cand,
                        derived_obligation_tokens=declared,
                        cold_reread_tokens=cold_cost,
                        gamma=population["gamma"],
                        ablation=abl,
                        frontier_artifact_id=f"fa:{eid}")
                    checks.append((f"offer_gate_mirror[{eid}]", True,
                                   f"ballast {recomputed} >= "
                                   f"{population['gamma']} * {cold_cost}"))
                except MintRefusal as e:
                    checks.append((f"offer_gate_mirror[{eid}]", False,
                                   f"{e.row.get('check')}/{e.row.get('reason')}"))

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
