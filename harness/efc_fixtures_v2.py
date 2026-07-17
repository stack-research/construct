"""EFC v2 fixture suite validators — SPEC §B.

Schema and machine gates only. No fixture content is authored in this module;
battery authoring is a separate lifecycle step under §B's shopping refusal.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.efc_leak_audit_v2 import evaluate_leak_audit
from harness.efc_menu_composition_v2 import (
    ALL_STRATA,
    RELEVANT_STRATA,
    check_block_pair_structure,
    check_fixture_composition,
)

PART_I_SPEC_SHA256 = (
    "8cedf6537aa7f6c2df792ad581d4f937066d5c639812907c3c8ea90c21197d62"
)
SUITE_ID = "efc_calibration_v2"
POPULATION_ID = "efc_calibration_v2"
K_PAIRS = 128
FIXTURES_PER_BLOCK = 3
EXPECTED_FIXTURE_COUNT = K_PAIRS * FIXTURES_PER_BLOCK

REPO_ROOT = Path(__file__).resolve().parents[1]
SUITE_DIR = REPO_ROOT / "corpus" / SUITE_ID
FIXTURES_DIR = SUITE_DIR / "fixtures"
MANIFEST_PATH = SUITE_DIR / "suite_manifest.json"


@dataclass(frozen=True)
class SuiteValidationResult:
    ok: bool
    refusals: tuple[str, ...]
    fixture_count: int = 0


def sha256_canon(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fixture_identity_hash(fixture: dict[str, Any]) -> str:
    """Pinned fields for manifest verification."""
    pinned = {
        "fixture_id": fixture["fixture_id"],
        "block_id": fixture["block_id"],
        "stratum": fixture["stratum"],
        "action_set": fixture["action_set"],
        "menu_order": fixture["menu_order"],
        "role_map": fixture["role_map"],
        "expected_commitment_enum": fixture["expected_commitment_enum"],
    }
    if fixture["stratum"] in RELEVANT_STRATA:
        pinned.update({
            "scope_bit": fixture["scope_bit"],
            "coherent_commit_action": fixture["coherent_commit_action"],
            "coherent_non_commit_action": fixture["coherent_non_commit_action"],
            "missing_scope_dimension": fixture["missing_scope_dimension"],
        })
    return sha256_canon(pinned)


def validate_fixture(
    fixture: object,
    *,
    require_plausibility_attestation: bool = False,
) -> SuiteValidationResult:
    if not isinstance(fixture, dict):
        return SuiteValidationResult(False, ("malformed_fixture",))
    comp = check_fixture_composition(
        fixture,
        require_plausibility_attestation=require_plausibility_attestation,
    )
    if not comp.ok:
        return SuiteValidationResult(False, (comp.refusal or "malformed_fixture",))
    return SuiteValidationResult(True, (), fixture_count=1)


def validate_suite(
    fixtures: object,
    *,
    require_plausibility_attestation: bool = False,
    expected_k_pairs: int = K_PAIRS,
) -> SuiteValidationResult:
    """Validate suite shape, mapping, block pairing, and leak-audit preconditions."""
    if not isinstance(fixtures, list):
        return SuiteValidationResult(False, ("malformed_fixture_suite",))

    refusals: list[str] = []
    validated: list[dict[str, Any]] = []
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            return SuiteValidationResult(False, ("malformed_fixture",))
        comp = check_fixture_composition(
            fixture,
            require_plausibility_attestation=require_plausibility_attestation,
        )
        if not comp.ok:
            refusals.append(comp.refusal or "malformed_fixture")
            continue
        validated.append(fixture)

    if refusals:
        return SuiteValidationResult(False, tuple(refusals))

    pair_check = check_block_pair_structure(validated)
    if not pair_check.ok:
        return SuiteValidationResult(
            False, (pair_check.refusal or "invalid_pair_structure",)
        )

    blocks = {f["block_id"] for f in validated}
    if len(blocks) != expected_k_pairs:
        return SuiteValidationResult(
            False,
            (f"block_count_mismatch:expected_{expected_k_pairs}_got_{len(blocks)}",),
        )

    stratum_counts = {s: 0 for s in ALL_STRATA}
    for fixture in validated:
        stratum_counts[fixture["stratum"]] += 1
    if stratum_counts["match"] != expected_k_pairs:
        return SuiteValidationResult(False, ("match_count_mismatch",))
    if stratum_counts["mismatch"] != expected_k_pairs:
        return SuiteValidationResult(False, ("mismatch_count_mismatch",))
    if stratum_counts["irrelevant"] != expected_k_pairs:
        return SuiteValidationResult(False, ("irrelevant_count_mismatch",))

    leak = evaluate_leak_audit(validated)
    if not leak.ok:
        return SuiteValidationResult(False, leak.refusals)

    return SuiteValidationResult(True, (), fixture_count=len(validated))


def load_suite_manifest(path: Path | None = None) -> dict[str, Any]:
    manifest_path = path or MANIFEST_PATH
    if not manifest_path.is_file():
        raise FileNotFoundError(f"suite manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))
