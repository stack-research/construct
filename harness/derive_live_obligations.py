"""D2 — `derive_live_obligations`: rulebooked, branch-blind, replayable.

SPEC_PAUSE_RESUME v0.1 §5. The function is deliberately boring: take only the
`surface_read` rows witnessed BEFORE the seam, run the population-pinned
rulebook once in canonical order, and emit content-addressed obligations. The
minter does not choose what feels salient; if a relation tuple cannot cite the
exact pre-seam read row(s) and rule id that emitted it, it is not derived — it
is authored, and it is refused.

v0.1 is RULEBOOKED-ONLY (dan's round-3 vote 1): `derivation_mode` is declared
at `population_precommit` and must be "rulebooked"; there is no hint_only
tier. Surface tags are catalog metadata (or deterministic extractor output
recorded with the surface at population), never model-extracted at read time.

The check is never "does this obligation make semantic sense?" It is "can I
replay the derivation from witnessed rows and get the same tuple?" — the
scorer's `derivation_replay_ok` re-runs this module and compares
`obligation_set_hash`; mismatch confounds every cost cell.

Rule shape (population sidecar, hash-pinned):
  {"rule_id", "trigger_predicate_id", "emits_relation_code",
   "emits_obligation_type", "satisfaction_predicate_id", "option_id",
   "match_key_ids": [...]}
Triggers are evaluated over `witness_read` contexts ({surface_id,
surface_tags, read_index} + catalog metadata for that surface); a rule fires
per read surface, accumulate semantics, canonical `rule_id` order.
"""

from __future__ import annotations

import hashlib
import json

from .predicate_ast import (OBLIGATION_KINDS, PredicateClosureError, evaluate,
                            library_hash, validate)

SCHEMA_VERSION = "prf-0.1"

RULE_KEYS = frozenset({"rule_id", "trigger_predicate_id", "emits_relation_code",
                       "emits_obligation_type", "satisfaction_predicate_id",
                       "option_id", "match_key_ids"})


class DerivationRefused(ValueError):
    """Emitted as an `obligation_derivation_refused` row by callers."""

    def __init__(self, check: str, detail: str):
        super().__init__(f"{check}: {detail}")
        self.row = {"kind": "obligation_derivation_refused",
                    "check": check, "detail": detail}


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def validate_rulebook(rulebook: list[dict], predicate_library: dict[str, dict],
                      relation_code_classes: dict[str, str]) -> str:
    """Structural admission for the rulebook itself (the residual second-author
    seat). Refuses: unknown keys, unpinned predicates, verdict-shaped relation
    codes (only conditional-transition classes are legal — SPEC §4a), and
    obligation types outside the closed kind enum. Returns the rulebook hash
    the population pin must carry."""
    seen: set[str] = set()
    for rule in rulebook:
        keys = set(rule)
        if keys != RULE_KEYS:
            raise DerivationRefused(
                "rulebook_shape", f"rule keys {sorted(keys)} != {sorted(RULE_KEYS)}")
        rid = rule["rule_id"]
        if rid in seen:
            raise DerivationRefused("rulebook_shape", f"duplicate rule_id {rid!r}")
        seen.add(rid)
        for pid_key in ("trigger_predicate_id", "satisfaction_predicate_id"):
            pid = rule[pid_key]
            if pid not in predicate_library:
                raise DerivationRefused(
                    "predicate_closure",
                    f"rule {rid}: {pid_key}={pid!r} not in the pinned library")
        code = rule["emits_relation_code"]
        cls = relation_code_classes.get(code)
        if cls not in ("identity", "topology", "obligation", "discard", "reopen"):
            raise DerivationRefused(
                "relation_code_class",
                f"rule {rid}: relation code {code!r} has class {cls!r} — only "
                "conditional-transition classes are legal (verdicts are out, §4a)")
        if rule["emits_obligation_type"] not in OBLIGATION_KINDS:
            raise DerivationRefused(
                "obligation_kind",
                f"rule {rid}: obligation type {rule['emits_obligation_type']!r} "
                f"outside {sorted(OBLIGATION_KINDS)}")
        if not isinstance(rule["match_key_ids"], list):
            raise DerivationRefused("rulebook_shape",
                                    f"rule {rid}: match_key_ids must be a list")
    try:
        library_hash(predicate_library)
    except PredicateClosureError as e:
        raise DerivationRefused("predicate_closure", str(e))
    return _sha(sorted(rulebook, key=lambda r: r["rule_id"]))


def obligation_id(episode_id: str, seam_id: str, rule: dict,
                  source_read_ids: list[str],
                  source_read_hashes: list[str]) -> str:
    """codex's provenance-hash recipe (SPEC §5): the obligation has no prior
    document hash, so it is content-addressed from the derivation tuple —
    reproducible because the same reads + the same rulebook produce the same id."""
    return "obl:sha256:" + _sha([
        SCHEMA_VERSION, episode_id, seam_id, rule["rule_id"], rule["option_id"],
        rule["emits_relation_code"], rule["emits_obligation_type"],
        sorted(source_read_ids), sorted(source_read_hashes),
        sorted(rule["match_key_ids"]), rule["satisfaction_predicate_id"]])


def derive_live_obligations(population: dict, freeze_manifest: dict,
                            pre_seam_read_rows: list[dict], seam_id: str,
                            **extra_inputs) -> dict:
    """Run the pinned rulebook over the witnessed pre-seam reads. Returns
    {"batch": obligation_derivation_batch row, "obligations": [per-obligation
    rows]}. Input closure is strict: any extra input refuses the derivation
    (no branch route plan, no answer text, no post-seam reads, no narration)."""
    if extra_inputs:
        raise DerivationRefused(
            "derivation_input_closure",
            f"extra inputs {sorted(extra_inputs)} — the closure is "
            "{population, freeze_manifest, pre_seam_read_rows, seam_id} only")
    if population.get("derivation_mode") != "rulebooked":
        raise DerivationRefused(
            "derivation_mode",
            f"derivation_mode={population.get('derivation_mode')!r} — v0.1 is "
            "rulebooked-only; there is no hint_only tier (dan, round-3 vote 1)")

    rulebook = population["obligation_rulebook"]
    library = population["predicate_library"]
    codes = population["relation_code_classes"]
    rb_hash = validate_rulebook(rulebook, library, codes)
    if rb_hash != population.get("obligation_rulebook_hash"):
        raise DerivationRefused(
            "rulebook_pinned",
            "rulebook hash does not match the population_precommit pin")
    lib_hash = library_hash(library)
    if lib_hash != population.get("predicate_library_hash"):
        raise DerivationRefused(
            "predicate_library_pinned",
            "predicate library hash does not match the population_precommit pin")

    episode_id = population["episode_id"]
    catalog = population["catalog"]  # surface_id -> metadata (tags at population)
    reads = sorted(pre_seam_read_rows, key=lambda r: r["read_index"])
    for r in reads:
        if r.get("catalog_epoch") != "t0":
            raise DerivationRefused(
                "pre_seam_only",
                f"read of {r.get('surface_id')!r} at epoch "
                f"{r.get('catalog_epoch')!r} — derivation consumes pre-seam "
                "(t0) witnessed reads only")
        sid = r["surface_id"]
        if sid not in catalog:
            raise DerivationRefused(
                "read_manifest_match",
                f"witnessed read of {sid!r} has no population catalog entry")
        if r.get("content_hash") != catalog[sid].get("content_hash_t0"):
            raise DerivationRefused(
                "read_manifest_match",
                f"read of {sid!r}: content hash does not match the T0 catalog")

    obligations: list[dict] = []
    for rule in sorted(rulebook, key=lambda r: r["rule_id"]):
        trigger = library[rule["trigger_predicate_id"]]
        validate(trigger)
        fired_ids, fired_hashes, fired_tags = [], [], []
        for r in reads:
            ctx = {**catalog[r["surface_id"]].get("fields", {}),
                   "surface_id": r["surface_id"],
                   "surface_tags": catalog[r["surface_id"]].get("surface_tags", []),
                   "read_index": r["read_index"], "seam_id": seam_id,
                   "catalog_epoch": "t0"}
            if evaluate(trigger, ctx):
                fired_ids.append(r["surface_id"])
                fired_hashes.append(r["content_hash"])
                fired_tags.extend(ctx["surface_tags"])
        if not fired_ids:
            continue
        oid = obligation_id(episode_id, seam_id, rule, fired_ids, fired_hashes)
        obligations.append({
            "kind": "live_obligation_derived",
            "episode_id": episode_id, "seam_id": seam_id,
            "obligation_id": oid, "rule_id": rule["rule_id"],
            "option_id": rule["option_id"],
            "relation_code": rule["emits_relation_code"],
            "obligation_type": rule["emits_obligation_type"],
            "source_read_ids": sorted(fired_ids),
            "source_read_hashes": sorted(fired_hashes),
            "source_surface_tags": sorted(set(fired_tags)),
            "match_key_ids": sorted(rule["match_key_ids"]),
            "satisfaction_predicate_id": rule["satisfaction_predicate_id"],
            "status_at_freeze": "pending",
        })

    obligations.sort(key=lambda o: o["obligation_id"])
    ob_ids = [o["obligation_id"] for o in obligations]
    batch = {
        "kind": "obligation_derivation_batch",
        "episode_id": episode_id, "seam_id": seam_id,
        "population_contract_hash": population.get("population_contract_hash"),
        "derivation_schema_hash": _sha([SCHEMA_VERSION, rb_hash, lib_hash]),
        "read_manifest_hash": _sha([[r["surface_id"], r["content_hash"]]
                                    for r in reads]),
        "obligation_set_hash": _sha(ob_ids),
        "obligation_ids": ob_ids,
        "derivation_inputs_hash": _sha(
            {"population": population.get("population_contract_hash"),
             "manifest": freeze_manifest.get("frontier_schema_hash"),
             "reads": [[r["surface_id"], r["content_hash"], r["read_index"]]
                       for r in reads],
             "seam": seam_id}),
    }
    return {"batch": batch, "obligations": obligations}


def replay_ok(population: dict, freeze_manifest: dict,
              pre_seam_read_rows: list[dict], seam_id: str,
              claimed_batch: dict) -> bool:
    """Scorer leg `derivation_replay_ok`: re-derive from ledger rows and compare
    the obligation_set_hash. The logged batch is never authority."""
    try:
        fresh = derive_live_obligations(population, freeze_manifest,
                                        pre_seam_read_rows, seam_id)
    except DerivationRefused:
        return False
    return fresh["batch"]["obligation_set_hash"] == \
        claimed_batch.get("obligation_set_hash")
