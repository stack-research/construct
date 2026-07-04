"""Minimal v0.3 wire fixture builder (mechanism tests only — not measurement evidence)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from harness.check_prf_fixture import _obligation_ids_hash
from harness.derive_live_obligations import derive_live_obligations
from harness.mint_frontier_state import freeze_validate, manifest_hash

REPO = Path(__file__).resolve().parents[3]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _tok(text: str) -> int:
    return len(text.split())


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


def build_catalog() -> dict:
    """21 surfaces: 9 plausible (3+3+3 leg tags) + 12 ballast."""
    cat: dict = {}
    for i, case in enumerate(("K-17", "K-18", "K-19"), start=1):
        text = (f"case status note {case} disposition field approve "
                f"wire fixture status note {case} " * 8)
        cat[f"L{i:02d}"] = _surface(
            f"L{i:02d}", f"Case {case} Status Note", text,
            ["leg_status"], {"catalog_key": case, "surface_kind": "status"})
    for letter in ("A", "B", "C"):
        k17 = "K-17" if letter == "A" else "K-18"
        text = (f"exception register {letter} row {k17} class wire "
                f"exception register {letter} " * 10)
        cat[f"R{letter}"] = _surface(
            f"R{letter}", f"Exception Register {letter}", text,
            ["leg_exception"], {"catalog_key": k17, "surface_kind": "register"})
    for letter in ("A", "B", "C"):
        k17 = "K-17" if letter == "A" else "K-18"
        text = (f"clearance ledger {letter} reviewer row {k17} wire "
                f"clearance ledger {letter} " * 10)
        cat[f"G{letter}"] = _surface(
            f"G{letter}", f"Clearance Ledger {letter}", text,
            ["leg_clearance"], {"catalog_key": k17, "surface_kind": "ledger"})
    for i in range(1, 13):
        text = f"admin ballast record {i} routine queue metadata " * 12
        cat[f"B{i:02d}"] = _surface(f"B{i:02d}", f"Admin Record {i}", text, [])
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
        "episode_id": "prf3-wire",
        "derivation_mode": "rulebooked",
        "gamma": 0.2,
        "option_ids": ["A", "B"],
        "catalog": pop_catalog,
        "surface_tag_schema": ["leg_status", "leg_exception", "leg_clearance"],
        "obligation_rulebook": [
            {
                "rule_id": "R_status",
                "trigger_predicate_id": "P_leg_status",
                "emits_relation_code": "pending_evidence",
                "emits_obligation_type": "verify",
                "match_key_ids": ["K17_status"],
                "option_id": "A",
                "satisfaction_predicate_id": "P_sat_read",
            },
            {
                "rule_id": "R_exception",
                "trigger_predicate_id": "P_leg_exception",
                "emits_relation_code": "pending_evidence",
                "emits_obligation_type": "read",
                "match_key_ids": ["K17_exception"],
                "option_id": "A",
                "satisfaction_predicate_id": "P_sat_read",
            },
            {
                "rule_id": "R_clearance",
                "trigger_predicate_id": "P_leg_clearance",
                "emits_relation_code": "pending_evidence",
                "emits_obligation_type": "read",
                "match_key_ids": ["K17_clearance"],
                "option_id": "A",
                "satisfaction_predicate_id": "P_sat_read",
            },
        ],
        "predicate_library": {
            "P_leg_status": {"op": "read_has_tag", "tag": "leg_status"},
            "P_leg_exception": {"op": "read_has_tag", "tag": "leg_exception"},
            "P_leg_clearance": {"op": "read_has_tag", "tag": "leg_clearance"},
            "P_sat_read": {"op": "and", "args": [
                {"field": "catalog_epoch", "op": "eq", "value": "t1"},
                {"field": "surface_id", "op": "exists"},
            ]},
            "P_world_moved": {"op": "changed"},
            "P_stale": {"field": "surface_id", "op": "eq", "value": "L01"},
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
        "sbr_cold_reread_tokens": 800,
        "seam_id": "seam-prf3-wire",
        "continuation_step_id": "csid-prf3-wire",
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
                  episode_id: str = "prf3-wire-baseline",
                  self_falsification: str | None = None,
                  stale_claim: str | None = None,
                  witness_route: list[str] | None = None,
                  frontier_state: dict | None = None) -> dict:
    catalog_src = build_catalog()
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

    witness_route = witness_route or ["L01", "RA", "GA"]
    cal_route = ["L01", "RA", "GA"]
    cold_route = ["L02", "L03", "RB", "RC", "GB", "GC"]
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
        "instrument_version": "0.3",
        "seam_id": population["seam_id"],
        "catalog": catalog_ep,
        "catalog_sort": "by_id",
        "question": ("What disposition should be entered for case K-17: "
                     "approve / defer / reject / reopen?"),
        "expected_answer_t1": "approve",
        "calibration_expected_answer": "approve",
        "calibration_route": cal_route,
        "calibration_obligation_ids": cal_obl_hash,
        "cold_exploration_route": cold_route,
        "witness_route": witness_route,
        "frontier_state": fs,
        "budgets": {
            "max_read_tokens": 700,
            "max_steps": 8,
            "action_overhead_tokens": 20,
            "c_max": 860,
        },
        "quality_threshold": 1.0,
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


def write_fixture(dst: Path) -> Path:
    """Write a minimal passing v0.3 wire fixture tree to ``dst``."""
    dst.mkdir(parents=True, exist_ok=True)
    catalog = build_catalog()
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
    total_tokens = sum(_tok(m["text"]) for m in catalog.values())
    population["sbr_cold_reread_tokens"] = max(400, total_tokens // 3)

    baseline = build_episode(population, freeze)
    del baseline["_mint_preview"]
    neutral = build_episode(
        population, freeze, episode_id="prf3-wire-neutral",
        self_falsification="neutral_frontier", stale_claim=None)
    del neutral["_mint_preview"]
    ballast = build_episode(
        population, freeze, episode_id="prf3-wire-ballast",
        self_falsification="ballast_discriminator",
        witness_route=["L02", "RB", "GB"],
        frontier_state=build_frontier_state(
            population, freeze, ["L02", "RB", "GB"]))
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
        "fixture_id": "prf3-wire",
        "instrument_version": "0.3",
        "fictional": True,
        "episodes": ["ep-baseline.json", "ep-neutral.json", "ep-ballast.json"],
        "target_engines": ["mock"],
        "attestation": {"ignorance_probe": {"engines": {"mock": {"knew": False}}}},
    }
    (dst / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return dst
