"""EFC v2 calibration manifest assembler + pin-eligibility verifier — SPEC §F.

Deterministic assembly of ``corpus/efc_calibration_v2/calibration_manifest.json``.
Every hash is recomputed from on-disk bytes at assembly and verification time.

No fixture content is authored here; manifest_verify refuses when the suite
directory is absent or fails schema validation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.efc_admission_gate_v2 import (
    PART_I_SPEC_SHA256,
    admission_gate_params,
    compute_ub,
)
from harness.efc_commitment_wire_v2 import SCHEMA_RELPATH as WIRE_SCHEMA_RELPATH
from harness.efc_fixtures_v2 import (
    FIXTURES_DIR,
    HASH_DEFINITION_CANONICAL_COMPACT_JSON,
    K_PAIRS,
    MANIFEST_PATH as SUITE_MANIFEST_PATH,
    SUITE_ID,
    fixture_identity_hash,
    suite_hash,
    validate_suite,
)
from harness.efc_provenance_record_store_v2 import (
    build_record_store_from_fixtures,
)
from harness.efc_leak_audit_v2 import canonical_predictor_spec_bytes
from harness.efc_menu_composition_v2 import ALL_STRATA, RELEVANT_STRATA
from harness.efc_render_v2 import (
    RENDERER_ID,
    forced_class_template_hash,
    foreground_template_hash,
    renderer_contract_hash,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PART_I_SPEC_RELPATH = "notes/SPEC_EPISTEMIC_FRAME_CHECK_V2.md"
MANIFEST_RELPATH = "corpus/efc_calibration_v2/calibration_manifest.json"
SCHEMA_VERSION = "efc_calibration_manifest_v2"

PIN_PLACEHOLDER = "TO-BE-SET-AT-PIN"

INTEGRITY_LANES = ("M_untreated", "M_forced_class", "M_irrelevant")
STRATA = ALL_STRATA

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
    return sha256_path(_root_path(root, WIRE_SCHEMA_RELPATH))


def compute_commitment_oracle_scorer_hash(root: Path = REPO_ROOT) -> str:
    return sha256_path(_root_path(root, "harness/efc_commitment_oracle_v2.py"))


def compute_action_menu_composition_rules_hash(root: Path = REPO_ROOT) -> str:
    return sha256_path(
        _root_path(root, "harness/efc_menu_composition_rules_v2.md")
    )


def compute_leak_audit_contract_hash(root: Path = REPO_ROOT) -> str:
    return sha256_path(
        _root_path(root, "harness/efc_leak_audit_contract_v2.md")
    )


def compute_leak_audit_predictor_hash() -> str:
    return sha256_bytes(canonical_predictor_spec_bytes())


def compute_admission_gate_module_hash(root: Path = REPO_ROOT) -> str:
    return sha256_path(_root_path(root, "harness/efc_admission_gate_v2.py"))


def compute_scope_comparison_rule_hash(root: Path = REPO_ROOT) -> str:
    return sha256_path(
        _root_path(root, "corpus/efc_calibration_v2/comparison/scope_comparison_rule_candidate_v2.json")
    )


def compute_scope_comparison_interpreter_hash(root: Path = REPO_ROOT) -> str:
    return sha256_path(_root_path(root, "harness/efc_scope_comparison_v2.py"))


def compute_scope_comparison_vectors_hash(root: Path = REPO_ROOT) -> str:
    return sha256_path(
        _root_path(root, "corpus/efc_calibration_v2/comparison/conformance_vectors_v2.json")
    )


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
        "admission_gate_module_hash": compute_admission_gate_module_hash(root),
        "scope_comparison_rule_artifact_sha256": compute_scope_comparison_rule_hash(root),
        "scope_comparison_interpreter_sha256": compute_scope_comparison_interpreter_hash(root),
        "scope_comparison_conformance_vectors_sha256": (
            compute_scope_comparison_vectors_hash(root)
        ),
        "renderer_id": RENDERER_ID,
        "foreground_template_hash": foreground_template_hash(),
        "forced_class_template_hash": forced_class_template_hash(),
        "renderer_contract_hash": renderer_contract_hash(),
    }


def _commitment_invalid_rate_ceiling() -> dict[str, Any]:
    cells = [
        {"lane": lane, "stratum": stratum, "ceiling": 0.05}
        for lane in INTEGRITY_LANES
        for stratum in STRATA
    ]
    return {
        "global_minimum": 0.05,
        "cells": cells,
        "discrete_consequence_at_n128": (
            "At K=128 observable invalid rates are multiples of 1/128; "
            "at most 6 invalids pass (6/128=0.046875); 7 fail."
        ),
    }


def _load_suite_fixtures(root: Path) -> tuple[list[dict[str, Any]], list[str]] | None:
    suite_path = _root_path(root, str(SUITE_MANIFEST_PATH.relative_to(REPO_ROOT)))
    if not suite_path.is_file():
        return None
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    fixtures_dir = _root_path(root, str(FIXTURES_DIR.relative_to(REPO_ROOT)))
    fixtures: list[dict[str, Any]] = []
    fixture_order: list[str] = []
    for entry in suite.get("fixtures", []):
        fixture_id = entry["fixture_id"]
        path = fixtures_dir / f"{fixture_id}.json"
        if not path.is_file():
            return None
        fixtures.append(json.loads(path.read_text(encoding="utf-8")))
        fixture_order.append(fixture_id)
    return fixtures, fixture_order


def assemble_manifest(
    root: Path = REPO_ROOT,
    *,
    engine: str = PIN_PLACEHOLDER,
    effort: str = PIN_PLACEHOLDER,
) -> dict[str, Any]:
    """Assemble manifest from on-disk contract hashes (fixtures optional)."""
    contract_hashes = compute_contract_hashes(root)
    params = admission_gate_params(K_PAIRS)
    params["pinned_UB"] = params["UB"]

    calibration_fixtures: list[dict[str, Any]] = []
    fixture_suite_hash: str | None = None
    loaded = _load_suite_fixtures(root)
    if loaded is not None:
        fixtures, _fixture_order = loaded
        for fixture in fixtures:
            calibration_fixtures.append({
                "fixture_id": fixture["fixture_id"],
                "sha256": fixture_identity_hash(fixture),
            })
        fixture_suite_hash = suite_hash(
            fixtures,
            k_pairs=K_PAIRS,
            record_store=build_record_store_from_fixtures(fixtures),
        )

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "suite_id": SUITE_ID,
        "k_pairs": K_PAIRS,
        "part_i_spec_sha256": PART_I_SPEC_SHA256,
        "contract_hashes": contract_hashes,
        "admission_gate_params": params,
        "commitment_invalid_rate_ceiling": _commitment_invalid_rate_ceiling(),
        "calibration_fixture_hash_definition": HASH_DEFINITION_CANONICAL_COMPACT_JSON,
        "calibration_fixtures": calibration_fixtures,
        "fork_identity": {
            "engine": engine,
            "effort": effort,
            "render_hash": contract_hashes["foreground_template_hash"],
        },
        "pin_event_id": PIN_PLACEHOLDER,
        "pinned_at": PIN_PLACEHOLDER,
        "pinned_by": PIN_PLACEHOLDER,
        "estimand": "balanced_relevant_accuracy",
        "typed_outcomes": [
            "confounded(admission_band)",
            "confounded(within_class_commit)",
            "confounded(within_class_non_commit)",
            "confounded(pair_constant_policy)",
            "confounded(pair_leak)",
            "confounded(pair_anticue)",
            "confounded(render_leak)",
            "confounded(irrelevant_band)",
            "confounded(battery_shopping)",
            "confounded(commitment_invalid_rate)",
        ],
    }
    if fixture_suite_hash is not None:
        manifest["fixture_suite_hash"] = fixture_suite_hash
    return manifest


def manifest_verify(root: Path = REPO_ROOT, manifest: dict[str, Any] | None = None,
                    *, require_suite_hash: bool = False) -> ManifestVerifyResult:
    """Recompute every pinned hash and derived UB; fail on disagreement."""
    failures: list[str] = []

    if manifest is None:
        path = _root_path(root, MANIFEST_RELPATH)
        if not path.is_file():
            return ManifestVerifyResult(False, ("manifest_missing",))
        manifest = json.loads(path.read_text(encoding="utf-8"))

    if manifest.get("schema_version") != SCHEMA_VERSION:
        failures.append("schema_version_mismatch")

    if manifest.get("part_i_spec_sha256") != PART_I_SPEC_SHA256:
        failures.append("part_i_spec_sha256_mismatch")

    if manifest.get("calibration_fixture_hash_definition") not in (
        None,
        HASH_DEFINITION_CANONICAL_COMPACT_JSON,
    ):
        failures.append("calibration_fixture_hash_definition_mismatch")

    recomputed = compute_contract_hashes(root)
    pinned = manifest.get("contract_hashes", {})
    for key, val in recomputed.items():
        if pinned.get(key) != val:
            failures.append(f"contract_hash_mismatch:{key}")

    params = manifest.get("admission_gate_params", {})
    k = int(params.get("K", K_PAIRS))
    derived_ub = compute_ub(k)
    if abs(float(params.get("UB", -1)) - derived_ub) > 1e-12:
        failures.append("derived_ub_disagreement")
    pinned_ub = params.get("pinned_UB")
    if pinned_ub is not None and abs(float(pinned_ub) - derived_ub) > 1e-12:
        failures.append("pinned_ub_disagreement")

    loaded = _load_suite_fixtures(root)
    pinned_suite_hash = manifest.get("fixture_suite_hash")
    calibration_rows = manifest.get("calibration_fixtures", [])

    if require_suite_hash:
        if not pinned_suite_hash:
            failures.append("fixture_suite_hash_missing")
        if not isinstance(calibration_rows, list) or len(calibration_rows) != (
            K_PAIRS * 3
        ):
            failures.append("calibration_fixtures_incomplete")

    if loaded is not None:
        fixtures, suite_manifest_order = loaded
        store = build_record_store_from_fixtures(fixtures)
        suite_result = validate_suite(fixtures, record_store=store)
        if not suite_result.ok:
            failures.extend(suite_result.refusals)
        recomputed_suite_hash = suite_hash(
            fixtures,
            k_pairs=K_PAIRS,
            record_store=store,
        )
        if pinned_suite_hash is not None and pinned_suite_hash != recomputed_suite_hash:
            failures.append("fixture_suite_hash_mismatch")
        calibration_order = [
            row.get("fixture_id")
            for row in calibration_rows
            if isinstance(row, dict)
        ]
        if calibration_order != suite_manifest_order:
            failures.append("calibration_fixtures_order_mismatch")
        for fixture in fixtures:
            expected = fixture_identity_hash(fixture)
            row = next(
                (
                    r for r in calibration_rows
                    if r.get("fixture_id") == fixture["fixture_id"]
                ),
                None,
            )
            if row is None or row.get("sha256") != expected:
                failures.append(
                    f"fixture_hash_mismatch:{fixture['fixture_id']}"
                )
    elif pinned_suite_hash or calibration_rows:
        failures.append("fixture_suite_on_disk_missing")

    mh = manifest_hash(manifest)
    return ManifestVerifyResult(not failures, tuple(failures), mh)
