"""Shared mock PRF population for wire tests — SPEC_PAUSE_RESUME v0.1.

Mock structures only, never evidence. The scenario: three options (B, A, C —
deliberately not won by the alphabetical first), a five-surface catalog, one
rule that obligates a verify-read on the moved status surface, one that arms a
reopen on option Q's gate surface, and a discard rule on the world key. The
winner option is "R" (non-alphabetical vs "A"/"Q") to keep the hermes-floor
shape present even at the wire layer."""

from __future__ import annotations

import hashlib
import json


def sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# Canonical surface texts (t0). Token counts drive cost recompute in D3 tests.
SURFACE_TEXT_T0 = {
    "S1": "status ledger for the R migration key currently pending review " * 6,
    "S2": "long background corpus describing every option in the population " * 30,
    "S3": "gate surface naming the catalog condition that would reopen Q " * 8,
    "S4": "unrelated churn surface with rotating release notes " * 12,
    "S5": "secondary evidence surface for option R verification obligations " * 10,
}

# T1 worlds: "moved" flips the status surface (changed-world leg); "stale"
# flips the gate surface (stale-frontier leg — distinct invalidation path);
# "silent" leaves everything unchanged.
SURFACE_TEXT_T1_MOVED = {**SURFACE_TEXT_T0,
                         "S1": "status ledger for the R migration key now "
                               "resolved rejected final " * 6}
SURFACE_TEXT_T1_STALE = {**SURFACE_TEXT_T0,
                         "S3": "gate surface catalog condition now matches "
                               "reopening option Q " * 8}
SURFACE_TEXT_T1_SILENT = dict(SURFACE_TEXT_T0)

PREDICATE_LIBRARY = {
    "P_status_read": {"op": "read_has_tag", "tag": "status_bearing"},
    "P_gate_read": {"op": "read_has_tag", "tag": "reopen_gate"},
    "P_verify_sat": {"op": "and", "args": [
        {"op": "eq", "field": "surface_id", "value": "S1"},
        {"op": "eq", "field": "catalog_epoch", "value": "t1"}]},
    "P_gate_sat": {"op": "and", "args": [
        {"op": "eq", "field": "surface_id", "value": "S3"},
        {"op": "eq", "field": "catalog_epoch", "value": "t1"}]},
    "P_world_moved": {"op": "changed"},
    "P_catalog_reopen": {"op": "and", "args": [
        {"op": "eq", "field": "surface_id", "value": "S3"},
        {"op": "changed"}]},
}

RELATION_CODE_CLASSES = {
    "live": "identity",
    "pending_evidence": "obligation",
    "blocked_by_missing_surface": "topology",
    "discard_if_world_key_changed": "discard",
    "reopen_if_catalog_match": "reopen",
    # verdict-shaped codes exist only so tests can prove they are refused:
    "superseded_by_surface": "verdict",
    "factually_refuted": "evaluation",
}

RULEBOOK = [
    {"rule_id": "R1", "trigger_predicate_id": "P_status_read",
     "emits_relation_code": "pending_evidence", "emits_obligation_type": "verify",
     "satisfaction_predicate_id": "P_verify_sat", "option_id": "R",
     "match_key_ids": ["K_status"]},
    {"rule_id": "R2", "trigger_predicate_id": "P_gate_read",
     "emits_relation_code": "reopen_if_catalog_match",
     "emits_obligation_type": "reopen",
     "satisfaction_predicate_id": "P_catalog_reopen", "option_id": "Q",
     "match_key_ids": ["K_gate"]},
    {"rule_id": "R3", "trigger_predicate_id": "P_status_read",
     "emits_relation_code": "discard_if_world_key_changed",
     "emits_obligation_type": "discard",
     "satisfaction_predicate_id": "P_world_moved", "option_id": "R",
     "match_key_ids": ["K_status"]},
]

CATALOG = {
    "S1": {"content_hash_t0": text_hash(SURFACE_TEXT_T0["S1"]),
           "surface_tags": ["status_bearing"],
           "fields": {"surface_kind": "status_slice", "certificate_eligible": True,
                      "status_key": "K_status"}},
    "S2": {"content_hash_t0": text_hash(SURFACE_TEXT_T0["S2"]),
           "surface_tags": [],
           "fields": {"surface_kind": "prose_body", "certificate_eligible": False}},
    "S3": {"content_hash_t0": text_hash(SURFACE_TEXT_T0["S3"]),
           "surface_tags": ["reopen_gate"],
           "fields": {"surface_kind": "gate_slice", "certificate_eligible": True,
                      "catalog_key": "K_gate"}},
    "S4": {"content_hash_t0": text_hash(SURFACE_TEXT_T0["S4"]),
           "surface_tags": [],
           "fields": {"surface_kind": "churn", "certificate_eligible": False}},
    "S5": {"content_hash_t0": text_hash(SURFACE_TEXT_T0["S5"]),
           "surface_tags": ["status_bearing"],
           "fields": {"surface_kind": "evidence", "certificate_eligible": True,
                      "status_key": "K_status"}},
}


def population(**overrides) -> dict:
    from harness.derive_live_obligations import validate_rulebook
    from harness.predicate_ast import library_hash
    pop = {
        "kind": "population_precommit",
        "episode_id": "prf-mock-1",
        "derivation_mode": "rulebooked",
        "obligation_rulebook": RULEBOOK,
        "predicate_library": PREDICATE_LIBRARY,
        "relation_code_classes": RELATION_CODE_CLASSES,
        "catalog": CATALOG,
        "option_ids": ["A", "Q", "R"],
        "uncertainty_codes": ["unresolved", "needs_check", "conflict_unread"],
        "gamma": 0.20,
        "continuation_step_id": "csid-mock-1",
        "reopen_rules": {
            "RR1": {"invalidation_predicate_id": "P_world_moved",
                    "reason": "changed_world"},
            "RR2": {"invalidation_predicate_id": "P_catalog_reopen",
                    "reason": "stale_frontier"},
        },
    }
    pop["population_reopen_rules_hash"] = sha(pop["reopen_rules"])
    pop["obligation_rulebook_hash"] = validate_rulebook(
        RULEBOOK, PREDICATE_LIBRARY, RELATION_CODE_CLASSES)
    pop["predicate_library_hash"] = library_hash(PREDICATE_LIBRARY)
    pop["population_contract_hash"] = sha(
        [pop["obligation_rulebook_hash"], pop["predicate_library_hash"],
         sorted(CATALOG), pop["option_ids"], pop["gamma"]])
    pop.update(overrides)
    return pop


def freeze_manifest() -> dict:
    m = {
        "option_ids": ["A", "Q", "R"],
        "surface_ids": sorted(CATALOG),
        "relation_code_classes": {k: v for k, v in RELATION_CODE_CLASSES.items()
                                  if v in ("identity", "topology", "obligation",
                                           "discard", "reopen")},
        "uncertainty_codes": ["unresolved", "needs_check", "conflict_unread"],
        "allowed_fields": ["live_options", "inactive_options",
                           "pending_obligations", "reopen_rules",
                           "read_manifest", "uncertainty"],
        "forbidden_field_names": ["best_option", "option_rank", "confidence",
                                  "draft_answer", "summary", "next_step",
                                  "reason"],
        "id_pattern": r"^[A-Z][0-9]*$",
    }
    m["frontier_schema_hash"] = sha(m)
    return m


def witness_reads(surface_ids=("S1", "S3", "S5")) -> list[dict]:
    """A gappy witness trace: reads a strict subset of the catalog (never S2/S4)."""
    return [{"kind": "surface_read", "branch": "uninterrupted_warm",
             "surface_id": sid, "read_index": i, "catalog_epoch": "t0",
             "content_hash": CATALOG[sid]["content_hash_t0"],
             "surface_tags": CATALOG[sid]["surface_tags"]}
            for i, sid in enumerate(surface_ids)]
