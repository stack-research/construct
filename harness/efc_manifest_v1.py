"""EFC v1 calibration manifest assembler + pin-eligibility verifier — §5.2/§5.3.

Deterministic assembly of ``corpus/efc_calibration_v1/calibration_manifest_v1.json``.
Every hash is recomputed from on-disk bytes at assembly and verification time;
thread-quoted expectations are cross-check inputs only — mismatches refuse.

Pin-event identity fields (``pin_event_id``, ``pinned_at``, ``pinned_by``) remain
``TO-BE-SET-AT-PIN`` until dan's manifest pin ruling.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness import efc_contracts as c
from harness.efc_artifacts import predicate_contract_hash
from harness.efc_check import check_adapter_contract_hash
from harness.efc_compare_production import (build_production_contract,
                                            production_check_contract_hash)
from harness.efc_fixtures_v1 import (FIXTURES_DIR, MANIFEST_PATH as SUITE_MANIFEST_PATH,
                                     SUITE_ID, validate_suite)
from harness.efc_leak_audit_v1 import (canonical_predictor_spec_bytes,
                                       check_no_lexical_marking,
                                       evaluate_leak_audit)
from harness.efc_render_v1 import (RENDERER_ID, foreground_template_hash,
                                   menu_only_template_hash, render_prompt,
                                   render_prompt_menu_only, renderer_contract_hash)

REPO_ROOT = Path(__file__).resolve().parents[1]
PART_I_SPEC_RELPATH = "notes/SPEC_EPISTEMIC_FRAME_CHECK_V1.md"
MANIFEST_RELPATH = "corpus/efc_calibration_v1/calibration_manifest_v1.json"
SCHEMA_VERSION = "efc_calibration_manifest_v1"

PART_I_SPEC_SHA256 = (
    "2d37f6bf0cd4aab830cb1dcf5eb9576f13b9acff65b63cd7d5b5fe0ea5b6097d"
)

INTEGRITY_LANES = ("M_menu_only", "M_task_menu")
SCORING_LANES = c.LANES
INVALID_RATE_LANES = INTEGRITY_LANES + SCORING_LANES
STRATA = c.STRATA

PIN_PLACEHOLDER = "TO-BE-SET-AT-PIN"

HASH_DEFINITION_CANONICAL_COMPACT_JSON = "canonical_compact_json"
HASH_DEFINITION_RAW_FILE_BYTES = "raw_file_bytes"

_JSON_DUMP = {"indent": 2, "sort_keys": True, "ensure_ascii": False}


@dataclass(frozen=True)
class ManifestVerifyResult:
    ok: bool
    failures: tuple[str, ...]
    manifest_hash: str | None = None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_canon(obj: object) -> str:
    return sha256_bytes(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def manifest_hash(manifest: dict[str, Any]) -> str:
    return sha256_canon(manifest)


def _root_path(root: Path, rel: str) -> Path:
    return root / rel


def compute_part_i_spec_hash(root: Path = REPO_ROOT) -> str:
    return sha256_path(_root_path(root, PART_I_SPEC_RELPATH))


def compute_commitment_wire_schema_hash(root: Path = REPO_ROOT) -> str:
    return sha256_path(_root_path(root, "harness/efc_commitment_wire_v1.schema.json"))


def compute_commitment_oracle_scorer_hash(root: Path = REPO_ROOT) -> str:
    return sha256_path(_root_path(root, "harness/efc_commitment_oracle_v1.py"))


def compute_action_menu_composition_rules_hash(root: Path = REPO_ROOT) -> str:
    return sha256_path(_root_path(root, "harness/efc_menu_composition_rules_v1.md"))


def compute_leak_audit_contract_hash(root: Path = REPO_ROOT) -> str:
    return sha256_path(_root_path(root, "harness/efc_leak_audit_contract_v1.md"))


def compute_leak_audit_predictor_hash() -> str:
    return sha256_bytes(canonical_predictor_spec_bytes())


def compute_predicate_contract_hash() -> str:
    """v0 C4: sha256 of canonical JSON of V0_PREDICATE_FEATURE_BINDINGS."""
    return predicate_contract_hash()


def compute_extractor_hash(root: Path = REPO_ROOT) -> str:
    """v0 C4: sha256 of raw harness/efc_trigger.py source bytes."""
    return sha256_path(_root_path(root, "harness/efc_trigger.py"))


def compute_check_contract_hash() -> str:
    """v0 C4: production_contract_identity_payload via efc_compare_production."""
    adapter_hash = check_adapter_contract_hash()
    contract = build_production_contract()
    return production_check_contract_hash(contract, adapter_hash)


def compute_contract_hashes(root: Path = REPO_ROOT) -> dict[str, str]:
    return {
        "part_i_spec_hash": compute_part_i_spec_hash(root),
        "commitment_wire_schema_hash": compute_commitment_wire_schema_hash(root),
        "commitment_oracle_scorer_hash": compute_commitment_oracle_scorer_hash(root),
        "action_menu_composition_rules_hash": (
            compute_action_menu_composition_rules_hash(root)
        ),
        "leak_audit_contract_hash": compute_leak_audit_contract_hash(root),
        "leak_audit_predictor_hash": compute_leak_audit_predictor_hash(),
        "renderer_id": RENDERER_ID,
        "foreground_template_hash": foreground_template_hash(),
        "menu_only_template_hash": menu_only_template_hash(),
        "renderer_contract_hash": renderer_contract_hash(),
        "generic_caution_sha256": c.GENERIC_CAUTION_SHA256,
        "offer_projection_sha256": c.OFFER_PROJECTION_SHA256,
        "predicate_contract_hash": compute_predicate_contract_hash(),
        "extractor_hash": compute_extractor_hash(root),
        "check_contract_hash": compute_check_contract_hash(),
    }


def _contract_hash_definitions() -> dict[str, str]:
    return {
        "predicate_contract_hash": (
            "sha256(json.dumps(V0_PREDICATE_FEATURE_BINDINGS, sort_keys=True, "
            "separators=(',', ':'))) — harness/efc_carrier.py"
        ),
        "extractor_hash": (
            "sha256(raw bytes of harness/efc_trigger.py module source)"
        ),
        "check_contract_hash": (
            "sha256(json.dumps(production_contract_identity_payload, "
            "sort_keys=True, separators=(',', ':'))) — "
            "harness/efc_compare_production.py"
        ),
    }


def _load_suite_manifest(root: Path) -> dict[str, Any]:
    path = _root_path(root, str(SUITE_MANIFEST_PATH.relative_to(REPO_ROOT)))
    return json.loads(path.read_text(encoding="utf-8"))


def _load_calibration_fixtures(root: Path) -> list[dict[str, Any]]:
    suite = _load_suite_manifest(root)
    fixtures_dir = _root_path(root, str(FIXTURES_DIR.relative_to(REPO_ROOT)))
    fixtures: list[dict[str, Any]] = []
    for entry in suite["fixtures"]:
        fixture_id = entry["fixture_id"]
        path = fixtures_dir / f"{fixture_id}.json"
        fixtures.append(json.loads(path.read_text(encoding="utf-8")))
    return fixtures


def _commitment_invalid_rate_ceiling() -> dict[str, Any]:
    cells = [
        {"lane": lane, "stratum": stratum, "ceiling": 0.05}
        for lane in INVALID_RATE_LANES
        for stratum in STRATA
    ]
    return {
        "global_minimum": 0.05,
        "cells": cells,
        "discrete_consequence_at_n5": (
            "At pilot n=5 observable invalid rates are 0, 0.20, 0.40, ...; "
            "therefore one invalid commitment gives 1/5=0.20 > 0.05 and "
            "confounds the cell. Zero invalids is required at n=5. At the "
            "strict held-out ceiling n=128, at most 6 invalids pass "
            "(6/128=0.046875); 7 fail (7/128=0.0546875). Invalid rows still "
            "count as failures in every quality numerator and denominator "
            "per §2.5.4."
        ),
    }


def _menu_ceiling_gate_params() -> dict[str, Any]:
    return {
        "K": 5,
        "C_pin": 1.0,
        "confidence": 0.95,
        "method": "newcombe_wilson",
        "scope_strata": ["match_mismatch"],
        "fail_condition_1_B_obs_gte": 0.80,
        "headroom_margin": 0.25,
        "non_extension_rationale": (
            "§9.2 asks C to preserve B on match_commit and irrelevant via "
            "non-inferiority. High inactive-surface competence in those "
            "lose/silence strata is healthy baseline behavior, not the "
            "superiority-ceiling confound that match_mismatch prices. Applying "
            "the match_mismatch headroom rule to match_commit or irrelevant "
            "would refuse exactly the baselines those cells require."
        ),
        "discrete_consequence_at_K5": (
            "At K=5 on match_mismatch only: for x=0 recovered, Newcombe lower "
            "bound of (C_pin-B_obs) headroom passes; for x=1 (B_obs=1/5), "
            "headroom lower bound fails. Therefore only B_obs=0/5 passes both "
            "conditions; every B_obs>=1/5 fails the headroom gate, and "
            "B_obs>=4/5 also fails condition 1 (B_obs>=0.80)."
        ),
        "descriptive_rates_other_strata": (
            "match_commit and irrelevant receive descriptive M_task_menu rates "
            "but no menu-ceiling refusal."
        ),
    }


def _ignorance_probe_contract(suite: dict[str, Any]) -> dict[str, Any]:
    probe_ids = [entry["fixture_id"] for entry in suite["fixtures"]]
    return {
        "probe_fact_count_F": len(probe_ids),
        "probe_fixture_ids": probe_ids,
        "max_recoverable_count": 3,
        "max_recoverable_rate": 3 / 15,
        "gate_rule": "pass iff recovered <= 3 of 15",
        "candidate_carried_from_v0_C2a": True,
        "review_flag": (
            "v0 C2a rule carried as candidate — flag for cold review"
        ),
        "probe_facts_are_suite_fixtures": True,
    }


def _budget_ledger() -> dict[str, Any]:
    input_ceiling = 250_000
    output_ceiling = 16_330
    input_rate = 2.50
    output_rate = 15.00
    worst_case_cost = (
        input_ceiling * input_rate / 1_000_000
        + output_ceiling * output_rate / 1_000_000
    )
    return {
        "total_call_ceiling": 258,
        "calls_already_spent": 3,
        "calls_remaining_ceiling": 255,
        "wire_probe_calls_completed": 2,
        "wire_probe_calls_rejected": 1,
        "wire_probe_tokens": {"input": 18, "output": 10, "total": 28},
        "max_output_tokens_per_request": 64,
        "input_token_ceiling": input_ceiling,
        "output_token_ceiling": output_ceiling,
        "output_ceiling_derivation": (
            "10 output tokens already spent + 255 remaining calls × 64 "
            "max_output_tokens = 16,330"
        ),
        "worst_case_cost_usd": round(worst_case_cost, 5),
        "hard_cost_ceiling_usd": 1.00,
        "headroom_below_hard_ceiling_usd": round(1.00 - worst_case_cost, 5),
        "pricing": {
            "source_url": "https://developers.openai.com/api/docs/models/gpt-5.4",
            "retrieved_date": "2026-07-16",
            "input_usd_per_million": input_rate,
            "output_usd_per_million": output_rate,
            "cached_input_discount_ignored": True,
        },
        "cost_formula": (
            "cost_usd = 2.50*input_tokens/1,000,000 + 15.00*output_tokens/1,000,000"
        ),
        "stop_before_crossing": True,
        "budget_refusal_typed_outcome": "budget_refusal",
        "parameterization_note": (
            "If ignorance-probe fact count F changes, recompute "
            "total_call_ceiling = 243 + F before pin."
        ),
    }


def _disclosure_block() -> list[dict[str, str]]:
    return [
        {
            "id": "tie_break_spelling_selector",
            "text": (
                "Mapping-rule tie-break is lexicographic minimum UTF-8 label "
                "among role members (TIE_BREAK_ID=lexicographic_minimum_utf8)."
            ),
            "origin": "grok D5-NB2",
        },
        {
            "id": "l2_equiv_l1_on_suite",
            "text": (
                "On this suite L1 and L2 leak-audit legs share identical "
                "per-stratum accuracy (0.20) because ordinal histogram "
                "(3,3,3,3,3) keeps token-overlap scores tied at menu index 0."
            ),
            "origin": "D5-NB4",
        },
        {
            "id": "mapping_consumes_role_map",
            "text": (
                "Mechanical enum mapping consumes each fixture's frozen "
                "role_map; authors choose labels/decoys, not per-fixture "
                "expected enums."
            ),
            "origin": "kimi D3-NB1",
        },
        {
            "id": "discrete_threshold_small_n",
            "text": (
                "At n=5, k=5: leak-audit fail_threshold=0.30; effective fail "
                "requires >=2/5 correct per leg/stratum."
            ),
            "origin": "grok D4-NB1",
        },
        {
            "id": "l2_floor_residuals",
            "text": (
                "Synonym/morph semantic leaks below the L2 token floor are "
                "priced by the M_task_menu pilot ceiling gate."
            ),
            "origin": "D4-NB2",
        },
        {
            "id": "engine_surface_superset",
            "text": (
                "Full-render engine-visible surface (header, trigger surface, "
                "caution, menu) is strictly larger than L1/L2 leak-audit "
                "inputs; residual priced by M_task_menu at pilot contact."
            ),
            "origin": "grok D6a-A1",
        },
        {
            "id": "homoglyph_hygiene",
            "text": "NFC canonicalization gate does not detect confusable scripts.",
            "origin": "D3-NB1",
        },
        {
            "id": "attest_filename_trust",
            "text": (
                "Attestation applier authority pointer is filename-trust on "
                "the ruling substrate entry, not a content-hash of that entry."
            ),
            "origin": "grok B1",
        },
        {
            "id": "oracle_scorer_in_contract_precommit",
            "text": (
                "contract_precommit MUST include commitment_oracle_scorer_hash "
                "per §13/§14 admission checklist."
            ),
            "origin": "grok v1-NB3",
        },
        {
            "id": "response_curve_only_scope",
            "text": (
                "response_curve_only=true: no population-level authority claim; "
                "upgrade path requires a superseding manifest."
            ),
            "origin": "dan ruling 2026-07-16",
        },
        {
            "id": "single_engine_no_fallback",
            "text": (
                "Single engine gpt-5.4-2026-03-05; NO fallback engine. An "
                "admission refusal blocks the phase as a valid typed outcome."
            ),
            "origin": "dan ruling / Sol wire report 2026-07-16",
        },
        {
            "id": "manifest_verify_referent_honesty",
            "text": (
                "manifest_verify checks referent honesty (disk-recomputable "
                "hashes and integrity gates), not whole-document self-integrity; "
                "manifest self-integrity is dan's pin of the exact emitted bytes "
                "(manifest_hash)."
            ),
            "origin": "grok D6-NB1",
        },
    ]


def assemble_manifest(
    *,
    root: Path = REPO_ROOT,
    output_path: Path | None = None,
) -> tuple[dict[str, Any], bytes]:
    """Assemble the v1 calibration manifest from on-disk artifacts."""
    if output_path is None:
        output_path = _root_path(root, MANIFEST_RELPATH)

    suite = _load_suite_manifest(root)
    if suite.get("attestation_status") != "signed":
        raise ValueError(
            "suite attestation_status must be signed before manifest assembly"
        )

    hashes = compute_contract_hashes(root)
    if hashes["part_i_spec_hash"] != PART_I_SPEC_SHA256:
        raise ValueError("part_i_spec_hash recomputation refused sealed pin")

    calibration_fixtures = []
    fixtures_raw_bytes: list[dict[str, str]] = []
    fixtures_dir = _root_path(root, str(FIXTURES_DIR.relative_to(REPO_ROOT)))
    for entry in suite["fixtures"]:
        fixture_id = entry["fixture_id"]
        path = fixtures_dir / f"{fixture_id}.json"
        fixture_obj = json.loads(path.read_text(encoding="utf-8"))
        calibration_fixtures.append(
            {"fixture_id": fixture_id, "sha256": sha256_canon(fixture_obj)}
        )
        fixtures_raw_bytes.append(
            {"fixture_id": fixture_id, "sha256": sha256_path(path)}
        )

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "suite_id": SUITE_ID,
        "part_i_spec_hash": hashes["part_i_spec_hash"],
        "pin_event_id": PIN_PLACEHOLDER,
        "pinned_at": PIN_PLACEHOLDER,
        "pinned_by": PIN_PLACEHOLDER,
        "engine_roster": ["gpt-5.4-2026-03-05"],
        "fallback_engine": None,
        "model_id": "gpt-5.4-2026-03-05",
        "decoding_contract": {
            "api_surface": "openai_responses",
            "endpoint": "POST /v1/responses",
            "model_snapshot": "gpt-5.4-2026-03-05",
            "max_output_tokens": 64,
            "reasoning_effort": "none",
            "temperature_primary": c.CALIBRATION_TEMPERATURE,
            "temperature_collapse_diagnostic": c.COLLAPSE_DIAGNOSTIC_TEMPERATURE,
            "seed": "unsupported_disclosed",
            "seed_disclosure": (
                "Live wire probe: HTTP/API rejection Unknown parameter: 'seed' "
                "on OpenAI Responses API (Sol ruling 2026-07-16)."
            ),
        },
        "renderer_id": hashes["renderer_id"],
        "foreground_template_hash": hashes["foreground_template_hash"],
        "menu_only_template_hash": hashes["menu_only_template_hash"],
        "renderer_contract_hash": hashes["renderer_contract_hash"],
        "commitment_wire_schema_hash": hashes["commitment_wire_schema_hash"],
        "commitment_oracle_scorer_hash": hashes["commitment_oracle_scorer_hash"],
        "action_menu_composition_rules_hash": (
            hashes["action_menu_composition_rules_hash"]
        ),
        "leak_audit_contract_hash": hashes["leak_audit_contract_hash"],
        "leak_audit_predictor_hash": hashes["leak_audit_predictor_hash"],
        "contract_precommit": {
            "commitment_wire_schema_hash": hashes["commitment_wire_schema_hash"],
            "action_menu_composition_rules_hash": (
                hashes["action_menu_composition_rules_hash"]
            ),
            "leak_audit_contract_hash": hashes["leak_audit_contract_hash"],
            "commitment_oracle_scorer_hash": hashes["commitment_oracle_scorer_hash"],
        },
        "generic_caution_text": c.GENERIC_CAUTION_TEXT,
        "generic_caution_sha256": hashes["generic_caution_sha256"],
        "offer_projection_text": c.OFFER_PROJECTION_TEXT,
        "offer_projection_sha256": hashes["offer_projection_sha256"],
        "predicate_contract_hash": hashes["predicate_contract_hash"],
        "extractor_hash": hashes["extractor_hash"],
        "check_contract_hash": hashes["check_contract_hash"],
        "contract_hash_definitions": _contract_hash_definitions(),
        "calibration_fixture_hash_definition": HASH_DEFINITION_CANONICAL_COMPACT_JSON,
        "calibration_fixtures": calibration_fixtures,
        "fixtures_raw_bytes_sha256": {
            "hash_definition": HASH_DEFINITION_RAW_FILE_BYTES,
            "entries": fixtures_raw_bytes,
        },
        "suite_manifest_path": str(SUITE_MANIFEST_PATH.relative_to(REPO_ROOT)),
        "suite_manifest_sha256": sha256_path(
            _root_path(root, str(SUITE_MANIFEST_PATH.relative_to(REPO_ROOT)))
        ),
        "attestation_authority": dict(suite["attestation_authority"]),
        "suite_k": suite["k"],
        "ordinal_histogram": list(suite["ordinal_histogram"]),
        "ordinal_max_abs_dev_bound": suite["ordinal_max_abs_dev_bound"],
        "ordinal_max_observed_deviation": suite["ordinal_max_observed_deviation"],
        "suite_gate_results": dict(suite["gate_results"]),
        "role_map": dict(suite["role_map"]),
        "calibration_k": c.CALIBRATION_K,
        "temperature": c.CALIBRATION_TEMPERATURE,
        "collapse_diagnostic_temperature": c.COLLAPSE_DIAGNOSTIC_TEMPERATURE,
        "stop_rule": c.STOP_RULE_ID,
        "n_max": c.N_MAX,
        "population_region": {
            "response_curve_only": True,
            "disclosure": (
                "No population-level authority claim; upgrade path = "
                "superseding manifest (dan ruling 2026-07-16)."
            ),
        },
        "commitment_invalid_rate_ceiling": _commitment_invalid_rate_ceiling(),
        "menu_ceiling_gate_params": _menu_ceiling_gate_params(),
        "ignorance_probe_contract": _ignorance_probe_contract(suite),
        "budget_ledger": _budget_ledger(),
        "integrity_gate_requirements": {
            "validate_suite_attestation_required": True,
            "evaluate_leak_audit": True,
            "check_no_lexical_marking": True,
            "render_modes": ["full", "menu_only"],
            "render_byte_determinism": True,
        },
        "disclosure_block": _disclosure_block(),
    }

    rendered = json.dumps(manifest, **_JSON_DUMP) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(rendered.encode("utf-8"))
    return manifest, rendered.encode("utf-8")


def _verify_hash_pins(
    manifest: dict[str, Any],
    root: Path,
    failures: list[str],
) -> None:
    expected = compute_contract_hashes(root)
    pin_fields = (
        "part_i_spec_hash",
        "commitment_wire_schema_hash",
        "commitment_oracle_scorer_hash",
        "action_menu_composition_rules_hash",
        "leak_audit_contract_hash",
        "leak_audit_predictor_hash",
        "renderer_id",
        "foreground_template_hash",
        "menu_only_template_hash",
        "renderer_contract_hash",
        "generic_caution_sha256",
        "offer_projection_sha256",
        "predicate_contract_hash",
        "extractor_hash",
        "check_contract_hash",
    )
    for field in pin_fields:
        if manifest.get(field) != expected[field]:
            failures.append(
                f"hash_mismatch:{field}:manifest={manifest.get(field)!r} "
                f"disk={expected[field]!r}"
            )

    precommit = manifest.get("contract_precommit")
    if not isinstance(precommit, dict):
        failures.append("malformed:contract_precommit")
    else:
        for key in (
            "commitment_wire_schema_hash",
            "action_menu_composition_rules_hash",
            "leak_audit_contract_hash",
            "commitment_oracle_scorer_hash",
        ):
            if precommit.get(key) != expected.get(key):
                failures.append(f"hash_mismatch:contract_precommit.{key}")


def _verify_fixture_pins(
    manifest: dict[str, Any],
    root: Path,
    failures: list[str],
) -> list[dict[str, Any]]:
    if manifest.get("calibration_fixture_hash_definition") != (
        HASH_DEFINITION_CANONICAL_COMPACT_JSON
    ):
        failures.append("hash_definition_mismatch:calibration_fixtures")

    entries = manifest.get("calibration_fixtures")
    if not isinstance(entries, list) or not entries:
        failures.append("malformed:calibration_fixtures")
        return []

    raw_block = manifest.get("fixtures_raw_bytes_sha256")
    if not isinstance(raw_block, dict):
        failures.append("malformed:fixtures_raw_bytes_sha256")
        raw_entries: list[dict[str, str]] = []
    else:
        if raw_block.get("hash_definition") != HASH_DEFINITION_RAW_FILE_BYTES:
            failures.append("hash_definition_mismatch:fixtures_raw_bytes_sha256")
        raw_entries = raw_block.get("entries", [])
        if not isinstance(raw_entries, list):
            failures.append("malformed:fixtures_raw_bytes_sha256.entries")
            raw_entries = []

    raw_by_id = {
        row["fixture_id"]: row["sha256"]
        for row in raw_entries
        if isinstance(row, dict)
        and isinstance(row.get("fixture_id"), str)
        and isinstance(row.get("sha256"), str)
    }

    fixtures_dir = _root_path(root, str(FIXTURES_DIR.relative_to(REPO_ROOT)))
    fixtures: list[dict[str, Any]] = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            failures.append(f"malformed:calibration_fixtures[{i}]")
            continue
        fixture_id = entry.get("fixture_id")
        pinned_sha = entry.get("sha256")
        if not isinstance(fixture_id, str) or not isinstance(pinned_sha, str):
            failures.append(f"malformed:calibration_fixtures[{i}]")
            continue
        path = fixtures_dir / f"{fixture_id}.json"
        if not path.is_file():
            failures.append(f"missing_fixture:{fixture_id}")
            continue
        fixture_obj = json.loads(path.read_text(encoding="utf-8"))
        canon_sha = sha256_canon(fixture_obj)
        if canon_sha != pinned_sha:
            failures.append(
                f"hash_mismatch:fixture:{fixture_id}:manifest={pinned_sha} "
                f"disk_canon={canon_sha}"
            )
        raw_sha = sha256_path(path)
        pinned_raw = raw_by_id.get(fixture_id)
        if pinned_raw is None:
            failures.append(f"missing_raw_bytes_pin:{fixture_id}")
        elif pinned_raw != raw_sha:
            failures.append(
                f"hash_mismatch:fixture_raw_bytes:{fixture_id}:"
                f"manifest={pinned_raw} disk={raw_sha}"
            )
        fixtures.append(fixture_obj)
    return fixtures


def _verify_render_determinism(
    fixtures: list[dict[str, Any]],
    failures: list[str],
    *,
    repeats: int = 20,
) -> None:
    from harness.efc_render_v1 import RenderRefusalError

    for fixture in fixtures:
        fixture_id = fixture["fixture_id"]
        for mode, render_fn in (
            ("full", render_prompt),
            ("menu_only", render_prompt_menu_only),
        ):
            try:
                first = render_fn(fixture)
            except RenderRefusalError as exc:
                failures.append(f"render_refused:{fixture_id}:{mode}:{exc}")
                continue
            first_sha = sha256_bytes(first.prompt.encode("utf-8"))
            for _ in range(repeats - 1):
                try:
                    again = render_fn(fixture)
                except RenderRefusalError as exc:
                    failures.append(
                        f"render_refused:{fixture_id}:{mode}:{exc}"
                    )
                    break
                again_sha = sha256_bytes(again.prompt.encode("utf-8"))
                if again_sha != first_sha or again.prompt != first.prompt:
                    failures.append(
                        f"render_nondeterministic:{fixture_id}:{mode}"
                    )
                    break


def manifest_verify(
    manifest: dict[str, Any],
    *,
    root: Path = REPO_ROOT,
    render_repeats: int = 20,
) -> ManifestVerifyResult:
    """Pin-eligibility check: recompute hashes, run integrity gates, refuse on mismatch."""
    failures: list[str] = []

    if manifest.get("schema_version") != SCHEMA_VERSION:
        failures.append("schema_version_mismatch")

    for field in ("pin_event_id", "pinned_at", "pinned_by"):
        if manifest.get(field) != PIN_PLACEHOLDER:
            failures.append(f"unexpected_pin_field:{field}")

    _verify_hash_pins(manifest, root, failures)
    fixtures = _verify_fixture_pins(manifest, root, failures)

    if fixtures:
        gate = validate_suite(fixtures, require_plausibility_attestation=True)
        if not gate.composition_ok:
            failures.append("integrity_refused:composition")
        if not gate.ordinal_ok:
            failures.append("integrity_refused:ordinal_uniformity")
        if not gate.leak_audit_ok:
            failures.append("integrity_refused:leak_audit")
        if not gate.lexical_marking_ok:
            failures.append("integrity_refused:lexical_marking")
        if not gate.extraction_integrity_ok:
            failures.append("integrity_refused:extraction_integrity")
        if not gate.family_validity_ok:
            failures.append("integrity_refused:family_validity")
        failures.extend(
            f"integrity_refused:{refusal}" for refusal in gate.refusals
        )

        leak = evaluate_leak_audit(fixtures)
        if not leak.ok:
            failures.extend(
                f"leak_audit_refused:{refusal}" for refusal in leak.refusals
            )

        lexical = check_no_lexical_marking(fixtures)
        if not lexical.ok:
            failures.extend(
                f"lexical_marking_refused:{refusal}"
                for refusal in lexical.refusals
            )

        _verify_render_determinism(
            fixtures, failures, repeats=render_repeats
        )

    budget = manifest.get("budget_ledger")
    if not isinstance(budget, dict):
        failures.append("malformed:budget_ledger")
    else:
        _verify_budget_arithmetic(budget, failures)

    ok = not failures
    return ManifestVerifyResult(
        ok=ok,
        failures=tuple(failures),
        manifest_hash=manifest_hash(manifest) if ok else None,
    )


def _verify_budget_arithmetic(budget: dict[str, Any], failures: list[str]) -> None:
    if budget.get("total_call_ceiling") != 258:
        failures.append("budget_inconsistent:total_call_ceiling")
    input_ceiling = budget.get("input_token_ceiling")
    output_ceiling = budget.get("output_token_ceiling")
    if input_ceiling is None or input_ceiling > 250_000:
        failures.append("budget_inconsistent:input_token_ceiling")
    if output_ceiling is None or output_ceiling > 16_330:
        failures.append("budget_inconsistent:output_token_ceiling")

    pricing = budget.get("pricing")
    if not isinstance(pricing, dict):
        failures.append("malformed:budget_ledger.pricing")
        return

    in_rate = pricing.get("input_usd_per_million")
    out_rate = pricing.get("output_usd_per_million")
    if not isinstance(in_rate, (int, float)) or not isinstance(out_rate, (int, float)):
        failures.append("malformed:budget_ledger.pricing_rates")
        return

    worst = budget.get("worst_case_cost_usd")
    if not isinstance(worst, (int, float)):
        failures.append("malformed:budget_ledger.worst_case_cost_usd")
        return

    recomputed = (
        input_ceiling * in_rate / 1_000_000
        + output_ceiling * out_rate / 1_000_000
    )
    if abs(recomputed - worst) > 1e-9:
        failures.append("budget_inconsistent:cost_formula")
    if worst > 1.00:
        failures.append("budget_inconsistent:exceeds_hard_ceiling")
