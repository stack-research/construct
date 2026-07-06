"""Minimal v0.4 Greenreach wire fixture builder (SPEC Part IV §37–§43).

Mechanism tests only — never measurement evidence. D5-conformant by
construction: legs 100 ± 5, decoy siblings 35..40 (floor at nominal),
ballast 36 ± 5; exclusion-certificate decoys; budgets 700/10/20/900.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from harness.check_prf_fixture import _obligation_ids_hash
from harness.derive_live_obligations import derive_live_obligations
from harness.mint_frontier_state import freeze_validate, manifest_hash

REPO = Path(__file__).resolve().parents[3]

TARGET_KEY = "WR-31"
LEG_IDS = ["N31", "X31", "C31"]                      # inflow / sediment / rights
DECOY_IDS = ["N30", "N29", "X30", "X29", "C30", "C29"]
DISPOSITIONS = ("release", "hold", "reject", "reopen")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _tok(text: str) -> int:
    return len(text.split())


def _pad_to(text: str, n: int) -> str:
    """Pad with neutral filler words to exactly n whitespace tokens."""
    words = text.split()
    if len(words) > n:
        raise ValueError(f"base text already {len(words)} > {n} tokens")
    filler = ["watershed", "desk", "record", "routine", "entry", "log"]
    i = 0
    while len(words) < n:
        words.append(filler[i % len(filler)])
        i += 1
    return " ".join(words)


def _surface(sid: str, title: str, text: str, tags: list[str],
             fields: dict | None = None) -> dict:
    fields = fields or {}
    return {
        "title": title,
        "text": text,
        "content_hash": _sha(text),
        "tokens": _tok(text),
        **({"fields": fields} if fields else {}),
        "surface_tags": tags,
    }


def build_catalog(decoy_tokens: int = 35) -> dict:
    """21 surfaces: 3 legs + 6 cheap exclusion-certificate decoys + 12 ballast."""
    cat: dict = {}
    leg_specs = [
        ("N31", "leg_inflow", "Inflow Status Note WR-31",
         f"inflow status note {TARGET_KEY} gauge reading within seasonal "
         "band all upstream conditions clear for allocation"),
        ("X31", "leg_sediment", "Sediment Exception Register",
         f"sediment test exception register row {TARGET_KEY} sediment "
         "class two exception resolved cleared for release"),
        ("C31", "leg_rights", "Rights Clearance Ledger",
         f"rights holder clearance ledger row {TARGET_KEY} reviewer "
         "clearance granted no standing objection recorded"),
    ]
    for sid, tag, title, base in leg_specs:
        cat[sid] = _surface(sid, title, _pad_to(base, 100), [tag],
                            {"catalog_key": TARGET_KEY,
                             "surface_kind": "dispositive"})
    decoy_specs = [
        ("N30", "leg_inflow", "Inflow Status Note WR-30", "WR-30"),
        ("N29", "leg_inflow", "Inflow Status Note WR-29", "WR-29"),
        ("X30", "leg_sediment", "Sediment Exception Register", "WR-30"),
        ("X29", "leg_sediment", "Sediment Exception Register", "WR-29"),
        ("C30", "leg_rights", "Rights Clearance Ledger", "WR-30"),
        ("C29", "leg_rights", "Rights Clearance Ledger", "WR-29"),
    ]
    for sid, tag, title, key in decoy_specs:
        base = (f"register row {key} applicability excluded for target "
                f"{TARGET_KEY} this row concerns permit {key} only")
        cat[sid] = _surface(sid, title, _pad_to(base, decoy_tokens), [tag],
                            {"catalog_key": key,
                             "target_key": key,
                             "applicability": "excluded_for_target",
                             "surface_kind": "sibling"})
    for i in range(1, 13):
        base = f"administrative record {i} routine desk queue metadata entry"
        cat[f"B{i:02d}"] = _surface(f"B{i:02d}", f"Admin Record {i}",
                                    _pad_to(base, 36), [])
    return cat


def build_population(catalog: dict) -> dict:
    pop_catalog = {}
    for sid, meta in catalog.items():
        pop_catalog[sid] = {
            "content_hash_t0": _sha(meta["text"] + " t0"),
            "surface_tags": meta["surface_tags"],
            "fields": meta.get("fields", {}),
        }
    return {
        "kind": "population_precommit",
        "episode_id": "prf4-wire",
        "derivation_mode": "rulebooked",
        "gamma": 0.2,
        "option_ids": ["A", "B"],
        "catalog": pop_catalog,
        "surface_tag_schema": ["leg_inflow", "leg_sediment", "leg_rights"],
        "obligation_rulebook": [
            {
                "rule_id": "R_inflow",
                "trigger_predicate_id": "P_leg_inflow",
                "emits_relation_code": "pending_evidence",
                "emits_obligation_type": "verify",
                "match_key_ids": ["WR31_inflow"],
                "option_id": "A",
                "satisfaction_predicate_id": "P_sat_read",
            },
            {
                "rule_id": "R_sediment",
                "trigger_predicate_id": "P_leg_sediment",
                "emits_relation_code": "pending_evidence",
                "emits_obligation_type": "read",
                "match_key_ids": ["WR31_sediment"],
                "option_id": "A",
                "satisfaction_predicate_id": "P_sat_read",
            },
            {
                "rule_id": "R_rights",
                "trigger_predicate_id": "P_leg_rights",
                "emits_relation_code": "pending_evidence",
                "emits_obligation_type": "read",
                "match_key_ids": ["WR31_rights"],
                "option_id": "A",
                "satisfaction_predicate_id": "P_sat_read",
            },
        ],
        "predicate_library": {
            "P_leg_inflow": {"op": "read_has_tag", "tag": "leg_inflow"},
            "P_leg_sediment": {"op": "read_has_tag", "tag": "leg_sediment"},
            "P_leg_rights": {"op": "read_has_tag", "tag": "leg_rights"},
            "P_sat_read": {"op": "and", "args": [
                {"field": "catalog_epoch", "op": "eq", "value": "t1"},
                {"field": "surface_id", "op": "exists"},
            ]},
            "P_world_moved": {"op": "changed"},
            "P_stale": {"field": "surface_id", "op": "eq", "value": "N31"},
        },
        "relation_code_classes": {
            "pending_evidence": "obligation",
            "discard_if_world_key_changed": "discard",
            "reopen_if_catalog_match": "reopen",
            "live": "identity",
            "blocked_by_missing_surface": "topology",
        },
        "reopen_rules": {
            "RR1": {"invalidation_predicate_id": "P_world_moved",
                    "reason": "changed_world"},
            "RR2": {"invalidation_predicate_id": "P_stale",
                    "reason": "stale_frontier"},
        },
        "uncertainty_codes": ["unresolved", "needs_check", "conflict_unread"],
        "sbr_cold_reread_tokens": 400,
        "seam_id": "seam-prf4-wire",
        "continuation_step_id": "csid-prf4-wire",
        "obligation_rulebook_hash": "wire",
        "predicate_library_hash": "wire",
        "population_reopen_rules_hash": "wire",
        "population_contract_hash": "wire",
    }


def _witness_rows(route: list[str], catalog: dict) -> list[dict]:
    return [{"surface_id": sid, "read_index": i, "catalog_epoch": "t0",
             "content_hash": catalog[sid]["content_hash_t0"],
             "surface_tags": catalog[sid]["surface_tags"]}
            for i, sid in enumerate(route)]


def build_frontier_state(population: dict, freeze_manifest: dict,
                         witness_route: list[str]) -> dict:
    witness = _witness_rows(witness_route, population["catalog"])
    out = derive_live_obligations(
        population, freeze_manifest, witness, population["seam_id"])
    obls = out["obligations"]
    return {
        "live_options": ["A"],
        "inactive_options": [],
        "pending_obligations": [
            {"obligation_id": o["obligation_id"],
             "derived_from_obligation_id": o["obligation_id"],
             "option_id": o["option_id"],
             "relation_code": o["relation_code"]}
            for o in obls
        ],
        "read_manifest": list(witness_route),
        "reopen_rules": [
            {"derived_from_obligation_id": obls[0]["obligation_id"],
             "option_id": "A",
             "relation_code": "discard_if_world_key_changed",
             "surface_id": witness_route[0]},
        ],
        "uncertainty": [{"option_id": "B", "uncertainty_code": "unresolved"}],
    }


def build_episode(population: dict, freeze_manifest: dict, *,
                  episode_id: str = "prf4-wire-baseline",
                  self_falsification: str | None = None,
                  stale_claim: str | None = None,
                  witness_route: list[str] | None = None,
                  frontier_state: dict | None = None,
                  decoy_tokens: int = 35,
                  budgets: dict | None = None) -> dict:
    catalog_src = build_catalog(decoy_tokens=decoy_tokens)
    catalog_ep = {}
    t0_texts = {}
    for sid, meta in catalog_src.items():
        catalog_ep[sid] = {
            "title": meta["title"],
            "text": meta["text"],
            "content_hash": meta["content_hash"],
            "tokens": meta["tokens"],
            "surface_tags": meta["surface_tags"],
        }
        if meta.get("fields"):
            catalog_ep[sid]["fields"] = meta["fields"]
        t0_texts[sid] = meta["text"] + " t0 witness padding " * 30

    witness_route = witness_route or list(LEG_IDS)
    fs = frontier_state or build_frontier_state(
        population, freeze_manifest, witness_route)
    witness = _witness_rows(witness_route, population["catalog"])
    derived = derive_live_obligations(
        population, freeze_manifest, witness, population["seam_id"])
    cal_obl_hash = _obligation_ids_hash(
        sorted(o["obligation_id"] for o in derived["obligations"]))
    cand = freeze_validate(fs, freeze_manifest, derived["batch"],
                           manifest_hash(freeze_manifest), rendered_tokens=True)
    covered = witness_route
    ballast_tokens = sum(_tok(t0_texts[s]) for s in covered)

    return {
        "episode_id": episode_id,
        "instrument_version": "0.4",
        "target_key": TARGET_KEY,
        "dispositive_leg_ids": list(LEG_IDS),
        "seam_id": population["seam_id"],
        "catalog": catalog_ep,
        "catalog_sort": "by_id",
        "question": ("Enter the release disposition for water-allocation "
                     "permit WR-31: release / hold / reject / reopen."),
        "expected_answer_t1": "release",
        "expected_answer_t0": "hold",
        "calibration_expected_answer": "release",
        "calibration_route": list(LEG_IDS),
        "calibration_obligation_ids": cal_obl_hash,
        "cold_exploration_route": list(DECOY_IDS),
        "witness_route": witness_route,
        "frontier_state": fs,
        "budgets": budgets or {
            "max_read_tokens": 700,
            "max_steps": 10,
            "action_overhead_tokens": 20,
            "c_max": 900,
        },
        "quality_threshold": 1.0,
        "oracle_source_label": "authored_oracle:fictional_greenreach",
        "ballast": {
            "covered_surfaces": covered,
            "derived_obligation_tokens": ballast_tokens,
        },
        "t0_texts": t0_texts,
        "stale_claim": stale_claim,
        "self_falsification": self_falsification,
        "expected_cells": {"kind": "pay_window_baseline"},
        "_mint_preview": cand,
    }


def build_freeze_manifest(catalog: dict) -> dict:
    surface_ids = sorted(catalog.keys())
    fm = {
        "allowed_fields": ["live_options", "inactive_options",
                           "pending_obligations", "reopen_rules",
                           "read_manifest", "uncertainty"],
        "forbidden_field_names": ["best_option", "option_rank", "confidence",
                                  "draft_answer", "summary", "next_step",
                                  "reason"],
        "id_pattern": "^[A-Z][0-9A-Z]*$",
        "option_ids": ["A", "B"],
        "surface_ids": surface_ids,
        "relation_code_classes": {
            "pending_evidence": "obligation",
            "discard_if_world_key_changed": "discard",
            "reopen_if_catalog_match": "reopen",
            "live": "identity",
            "blocked_by_missing_surface": "topology",
        },
        "uncertainty_codes": ["unresolved", "needs_check", "conflict_unread"],
    }
    mh = manifest_hash(fm)
    fm["frontier_schema_hash"] = mh
    return fm


def write_fixture(dst: Path, *, decoy_tokens: int = 35) -> Path:
    """Write a minimal passing v0.4 Greenreach wire fixture tree to ``dst``."""
    dst.mkdir(parents=True, exist_ok=True)
    catalog = build_catalog(decoy_tokens=decoy_tokens)
    population = build_population(catalog)
    freeze = build_freeze_manifest(population["catalog"])
    from harness.derive_live_obligations import validate_rulebook
    from harness.predicate_ast import library_hash
    population["obligation_rulebook_hash"] = validate_rulebook(
        population["obligation_rulebook"], population["predicate_library"],
        population["relation_code_classes"])
    population["predicate_library_hash"] = library_hash(
        population["predicate_library"])
    population["population_reopen_rules_hash"] = hashlib.sha256(
        json.dumps(population["reopen_rules"], sort_keys=True).encode()
    ).hexdigest()

    stale = ("permit WR-31 was awaiting sediment exception resolution at "
             "pause; disposition hold pending clearance")
    baseline = build_episode(population, freeze, decoy_tokens=decoy_tokens,
                             stale_claim=stale)
    del baseline["_mint_preview"]
    neutral = build_episode(
        population, freeze, episode_id="prf4-wire-neutral",
        self_falsification="neutral_frontier", stale_claim=None,
        decoy_tokens=decoy_tokens)
    del neutral["_mint_preview"]
    ballast_route = ["N30", "X30", "C30"]
    ballast = build_episode(
        population, freeze, episode_id="prf4-wire-ballast",
        self_falsification="ballast_discriminator",
        witness_route=ballast_route,
        frontier_state=build_frontier_state(population, freeze, ballast_route),
        decoy_tokens=decoy_tokens, stale_claim=stale)
    w = _witness_rows(ballast["witness_route"], population["catalog"])
    d = derive_live_obligations(population, freeze, w, population["seam_id"])
    ballast["calibration_obligation_ids"] = _obligation_ids_hash(
        sorted(o["obligation_id"] for o in d["obligations"]))
    del ballast["_mint_preview"]

    (dst / "population.json").write_text(json.dumps(population, indent=2))
    (dst / "freeze_manifest.json").write_text(json.dumps(freeze, indent=2))
    (dst / "ep-baseline.json").write_text(json.dumps(baseline, indent=2))
    (dst / "ep-neutral.json").write_text(json.dumps(neutral, indent=2))
    (dst / "ep-ballast.json").write_text(json.dumps(ballast, indent=2))
    manifest = {
        "fixture_id": "prf4-wire",
        "instrument_version": "0.4",
        "fictional": True,
        "episodes": ["ep-baseline.json", "ep-neutral.json", "ep-ballast.json"],
        "target_engines": ["mock"],
        "attestation": {"ignorance_probe": {"engines": {"mock": {"knew": False}}}},
    }
    (dst / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return dst
