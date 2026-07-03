"""D1 — the frontier-state mint: 13-check structural validator + two-phase mint.

SPEC_PAUSE_RESUME v0.1 §4. The artifact's language is deliberately poor: a
skeleton of attention (which ids are live, which are blocked, what must be
reopened or discarded under precommitted rules), never a judgment about which
option is winning. If the next valid step requires knowing that, the resumed
engine must earn it by reading obligations after the seam.

Boundary (§0, load-bearing): this validator bounds OVERT leakage only —
scores, ranks, NL rationales, answer tokens, evaluative labels. Covert leakage
through structure (asymmetric id assignment, gate-shaped micro-conclusions) is
bounded-not-zero and priced downstream by D2 derivation honesty, the
continuation checkpoint, and the loses-cells. A restricted prompt template,
not an airtight seal.

TWO-PHASE MINT (§4c, review-round fix A+B+C — dan's round-4 vote 1):
  phase 1, freeze-time  — `freeze_validate`: the 13 structural checks +
    `state_content_void` (planned_obligation_count = 0). Passing phase 1 does
    NOT mint; it returns a candidate.
  phase 2, offer-time   — `offer_gate`: after `post_seam_catalog_materialized`,
    before any resumable-branch post-seam read. Ablation-proven causality and
    the token ballast ratio fire HERE (they need the post-seam catalog and
    cold's checkpoint cost, which do not exist at freeze). Failures emit
    `frontier_mint_refused`; the branch is never offered the artifact and
    never resumes. `frontier_state_minted` is authoritatively emitted only
    after BOTH phases pass — the minted and refused rows are mutually
    exclusive per fork.

All content-floor failures are mint refusals, never `gate_open` legs: an
honorary artifact can never enter the win path and be demoted later via
`comparator_incapable`.
"""

from __future__ import annotations

import hashlib
import json
import re

# The strict compaction-input closure (§4b check 2). Mirrors WB MINT_INPUTS.
MINT_INPUTS = frozenset({"route_reads_at_freeze", "m1_sidecar_at_freeze",
                         "freeze_manifest", "derive_live_obligations_id"})

# Per-field tuple key shapes (§4b check 12): schema-pinned, no free-text keys.
TUPLE_SHAPES = {
    "inactive_options": ({"option_id", "relation_code",
                          "derived_from_obligation_id"}, {"surface_id"}),
    "pending_obligations": ({"obligation_id", "option_id", "relation_code",
                             "derived_from_obligation_id"}, set()),
    "reopen_rules": ({"option_id", "relation_code", "surface_id",
                      "derived_from_obligation_id"}, set()),
    "uncertainty": ({"option_id", "uncertainty_code"}, set()),
}

_ORDER_WORDS = re.compile(r"rank|priority|score|weight|confidence", re.I)
_PROSE = re.compile(r"[a-z]{3,}\s+[a-z]{3,}", re.I)  # multi-word natural language


class MintRefusal(ValueError):
    """Carries the `frontier_mint_refused` ledger row. The branch never resumes."""

    def __init__(self, check: str, reason: str, detail: str, schema_hash: str = ""):
        super().__init__(f"{check}/{reason}: {detail}")
        self.row = {"kind": "frontier_mint_refused", "check": check,
                    "reason": reason, "detail": detail,
                    "frontier_schema_hash": schema_hash}


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def manifest_hash(manifest: dict) -> str:
    return _sha({k: v for k, v in manifest.items() if k != "frontier_schema_hash"})


def _canonical(state: dict) -> dict:
    """§4b check 9: every list is an unordered set — canonicalized sort-by-id
    before hashing so array order can never carry a ranking."""
    out = {}
    for field in sorted(state):
        v = state[field]
        if isinstance(v, list):
            if all(isinstance(x, str) for x in v):
                out[field] = sorted(v)
            else:
                out[field] = sorted(
                    v, key=lambda t: json.dumps(t, sort_keys=True))
        else:
            out[field] = v
    return out


def freeze_validate(frontier_state: dict, freeze_manifest: dict,
                    derivation_batch: dict, pinned_schema_hash: str,
                    **mint_inputs) -> dict:
    """Phase 1 (freeze-time). Runs the 13 structural checks + the
    `state_content_void` floor. Returns a NON-minted candidate
    {canonical_state, state_digest, state_tokens, obligation_set_hash,
    frontier_schema_hash} — `frontier_state_minted` is emitted only by
    `offer_gate` (§4c two-phase pin). Raises MintRefusal fail-closed."""
    schema_hash = freeze_manifest.get("frontier_schema_hash", "")

    def refuse(check: str, reason: str, detail: str):
        raise MintRefusal(check, reason, detail, schema_hash)

    # 1. schema_pinned
    if manifest_hash(freeze_manifest) != pinned_schema_hash or \
            schema_hash != pinned_schema_hash:
        refuse("schema_pinned", "schema_unpinned",
               "freeze_manifest hash does not match the population pin")
    # 2. input_closure
    extra = set(mint_inputs) - MINT_INPUTS
    if extra:
        refuse("input_closure", "work_product_field",
               f"mint called with non-closure inputs {sorted(extra)} — "
               f"permitted: {sorted(MINT_INPUTS)}")

    allowed_fields = set(freeze_manifest["allowed_fields"])
    forbidden = set(freeze_manifest["forbidden_field_names"])
    option_ids = set(freeze_manifest["option_ids"])
    surface_ids = set(freeze_manifest["surface_ids"])
    relation_classes = freeze_manifest["relation_code_classes"]
    uncertainty_codes = set(freeze_manifest["uncertainty_codes"])
    batch_ids = set(derivation_batch.get("obligation_ids", []))
    id_pattern = re.compile(freeze_manifest["id_pattern"])
    vocab = option_ids | surface_ids | set(relation_classes) | \
        uncertainty_codes | batch_ids

    # state_content_void (§4c, freeze-time leg): an artifact with zero derived
    # obligations is honorary — it never reaches the offer gate.
    if not batch_ids:
        refuse("state_content_void", "state_content_void",
               "planned_obligation_count = 0 — the artifact is honorary")

    # 3. field_allowlist
    for field in frontier_state:
        if field in forbidden:
            refuse("field_allowlist", "work_product_field",
                   f"forbidden field {field!r}")
        if field not in allowed_fields:
            refuse("field_allowlist", "out_of_vocab_token",
                   f"field {field!r} not in allowed_fields")
        if _ORDER_WORDS.search(field):
            refuse("no_total_order", "work_product_field",
                   f"field name {field!r} implies ordering/valuation")

    def walk(value, path: str):
        if isinstance(value, bool) or value is None:
            return
        if isinstance(value, (int, float)):
            # 8. no_scalar_valuation
            refuse("no_scalar_valuation", "work_product_field",
                   f"numeric value at {path} — scores/weights/probabilities "
                   "are refused")
        if isinstance(value, str):
            # 4+7. vocab_closure / no_natural_language
            if value not in vocab:
                reason = "out_of_vocab_token"
                if _PROSE.search(value):
                    reason = "work_product_field"
                refuse("vocab_closure", reason,
                       f"token {value!r} at {path} outside the closed "
                       "vocabularies")
            return
        if isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, f"{path}[{i}]")
            return
        if isinstance(value, dict):
            for k, v in value.items():
                if _ORDER_WORDS.search(k):
                    refuse("no_total_order", "work_product_field",
                           f"key {k!r} at {path} implies ordering/valuation")
                if k == "reason":
                    refuse("gate_relation_shape", "work_product_field",
                           f"free-text 'reason' key at {path}")
                walk(v, f"{path}.{k}")
            return
        refuse("vocab_closure", "out_of_vocab_token",
               f"unsupported value type at {path}")

    walk(frontier_state, "state")

    # 5. opaque_id_format — option ids match the pinned pattern and carry no prose
    for oid in option_ids & _all_strings(frontier_state):
        if not id_pattern.match(oid):
            refuse("opaque_id_format", "out_of_vocab_token",
                   f"option id {oid!r} fails the pinned opaque pattern")

    # 12. gate_relation_shape — tuple keys are schema-pinned
    for field, (allowed_keys, optional_keys) in TUPLE_SHAPES.items():
        for i, tup in enumerate(frontier_state.get(field, [])):
            if not isinstance(tup, dict):
                refuse("gate_relation_shape", "out_of_vocab_token",
                       f"{field}[{i}] must be a relation tuple")
            keys = set(tup)
            if not keys <= (allowed_keys | optional_keys) or \
                    not (allowed_keys - optional_keys) <= keys:
                refuse("gate_relation_shape", "work_product_field",
                       f"{field}[{i}] keys {sorted(keys)} violate the pinned "
                       f"shape {sorted(allowed_keys)}")

    # 6. relation_code_class — conditional-transition classes only (§4a)
    for field in ("inactive_options", "pending_obligations", "reopen_rules"):
        for tup in frontier_state.get(field, []):
            code = tup.get("relation_code")
            cls = relation_classes.get(code)
            if cls not in ("identity", "topology", "obligation", "discard",
                           "reopen"):
                refuse("relation_code_class", "work_product_field",
                       f"relation code {code!r} has class {cls!r} — verdicts "
                       "fixed at freeze are out (§4a)")

    # 10. partition_consistency
    live = set(frontier_state.get("live_options", []))
    inactive = {t["option_id"] for t in frontier_state.get("inactive_options", [])}
    both = live & inactive
    if both:
        refuse("partition_consistency", "work_product_field",
               f"options {sorted(both)} are both live and inactive")
    for oid in live | inactive:
        if oid not in option_ids:
            refuse("partition_consistency", "out_of_vocab_token",
                   f"option {oid!r} not in the manifest option_ids")

    # 11. ref_integrity
    for field in ("inactive_options", "reopen_rules"):
        for tup in frontier_state.get(field, []):
            sid = tup.get("surface_id")
            if sid is not None and sid not in surface_ids:
                refuse("ref_integrity", "out_of_vocab_token",
                       f"{field} references unknown surface {sid!r}")
    for sid in frontier_state.get("read_manifest", []):
        if sid not in surface_ids:
            refuse("ref_integrity", "out_of_vocab_token",
                   f"read_manifest references unknown surface {sid!r}")
    for tup in frontier_state.get("pending_obligations", []):
        if tup.get("obligation_id") not in batch_ids:
            refuse("ref_integrity", "out_of_vocab_token",
                   f"obligation {tup.get('obligation_id')!r} not in the "
                   "derivation batch")

    # D2 hook: relation_tuple_provenance — placement of ids was EARNED.
    for field in ("inactive_options", "pending_obligations", "reopen_rules"):
        for i, tup in enumerate(frontier_state.get(field, [])):
            if tup.get("derived_from_obligation_id") not in batch_ids:
                refuse("relation_tuple_provenance", "work_product_field",
                       f"{field}[{i}] does not cite a derived obligation — "
                       "authored placement is refused")

    # 13. canonical_hash
    canonical = _canonical(frontier_state)
    canonical_json = json.dumps(canonical, sort_keys=True)
    return {
        "canonical_state": canonical,
        "state_digest": hashlib.sha256(canonical_json.encode()).hexdigest(),
        "state_tokens": len(canonical_json.split()),
        "obligation_set_hash": derivation_batch.get("obligation_set_hash"),
        "frontier_schema_hash": schema_hash,
        "phase": "freeze_pass",   # NOT minted — §4c two-phase pin
    }


def _all_strings(value) -> set[str]:
    out: set[str] = set()
    if isinstance(value, str):
        out.add(value)
    elif isinstance(value, list):
        for v in value:
            out |= _all_strings(v)
    elif isinstance(value, dict):
        for v in value.values():
            out |= _all_strings(v)
    return out


def offer_gate(freeze_candidate: dict, derived_obligation_tokens: int,
               cold_reread_tokens: int, gamma: float,
               witness_adequate_without_obligation_surfaces: bool,
               frontier_artifact_id: str) -> dict:
    """Phase 2 (offer-time): after `post_seam_catalog_materialized`, before any
    resumable-branch post-seam read. The two replay-dependent content-floor
    legs fire here (§4c-1/§4c-2, review-round fix A+B). On pass, returns the
    authoritative `frontier_state_minted` row — the only place it is emitted."""
    if freeze_candidate.get("phase") != "freeze_pass":
        raise MintRefusal("two_phase_order", "work_product_field",
                          "offer_gate requires a freeze-phase candidate",
                          freeze_candidate.get("frontier_schema_hash", ""))
    schema_hash = freeze_candidate["frontier_schema_hash"]
    # §4c-1 ablation-proven causality: if a simulated witness path with the
    # obligation-covered surfaces withheld still reaches the continuation
    # checkpoint at adequate quality, the obligations are decorative.
    if witness_adequate_without_obligation_surfaces:
        raise MintRefusal("ablation_causality", "fixture_obligations_decorative",
                          "witness reached the checkpoint with obligation "
                          "surfaces withheld — the branch never resumes",
                          schema_hash)
    # §4c-2 token ballast ratio: carried warmth must be a material fraction of
    # what cold reread would pay. γ is population-pinned; re-pin = fixture-class
    # re-derivation, never calibration.
    if derived_obligation_tokens < gamma * cold_reread_tokens:
        raise MintRefusal("ballast_ratio", "obligation_ballast_below_gamma",
                          f"derived_obligation_tokens={derived_obligation_tokens} "
                          f"< gamma({gamma}) * cold({cold_reread_tokens}) — the "
                          "branch never resumes", schema_hash)
    return {
        "kind": "frontier_state_minted",
        "frontier_artifact_id": frontier_artifact_id,
        "state_digest": freeze_candidate["state_digest"],
        "state_tokens": freeze_candidate["state_tokens"],
        "obligation_set_hash": freeze_candidate["obligation_set_hash"],
        "frontier_schema_hash": schema_hash,
        "content_floor": {"gamma": gamma,
                          "derived_obligation_tokens": derived_obligation_tokens,
                          "cold_reread_tokens": cold_reread_tokens,
                          "ablation_causal": True},
    }


def recompute_state_tokens(canonical_state: dict) -> int:
    """Scorer-side: `frontier_artifact_tokens` (D3's A) is recomputed from the
    canonical state at `state_digest`; the logged `state_tokens` is audit-only."""
    return len(json.dumps(_canonical(canonical_state), sort_keys=True).split())
