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
    HANDLE_ORIENTATIONS,
    RELEVANT_STRATA,
    SCOPE_DIMENSIONS,
    check_block_pair_structure,
    check_counterfactual_block_shape,
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

HASH_DEFINITION_CANONICAL_COMPACT_JSON = "canonical_compact_json"

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


def fixture_canonical_bytes(fixture: dict[str, Any]) -> bytes:
    """Full canonical fixture bytes — every authored field bound for shopping refusal."""
    return json.dumps(
        fixture,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def fixture_identity_hash(fixture: dict[str, Any]) -> str:
    """Pinned full-fixture digest for manifest verification."""
    return sha256_bytes(fixture_canonical_bytes(fixture))


def scope_dimension_histogram(
    fixtures: list[dict[str, Any]],
) -> dict[str, int]:
    """Count missing_scope_dimension once per block (mismatch stratum)."""
    counts = {dim: 0 for dim in SCOPE_DIMENSIONS}
    for fixture in fixtures:
        if fixture.get("stratum") != "mismatch":
            continue
        dim = fixture.get("missing_scope_dimension")
        if isinstance(dim, str) and dim in counts:
            counts[dim] += 1
    return counts


def handle_orientation_histogram(
    fixtures: list[dict[str, Any]],
) -> dict[str, int]:
    """Count handle_orientation once per block (match stratum)."""
    counts = {orient: 0 for orient in HANDLE_ORIENTATIONS}
    for fixture in fixtures:
        if fixture.get("stratum") != "match":
            continue
        orient = fixture.get("handle_orientation")
        if isinstance(orient, str) and orient in counts:
            counts[orient] += 1
    return counts


def check_scope_dimension_balance(
    fixtures: list[dict[str, Any]],
    *,
    k_pairs: int,
) -> tuple[bool, str | None]:
    """§B: equal frequencies of the five missing-scope dimensions."""
    if k_pairs < len(SCOPE_DIMENSIONS):
        return True, None
    hist = scope_dimension_histogram(fixtures)
    lo = k_pairs // len(SCOPE_DIMENSIONS)
    hi = (k_pairs + len(SCOPE_DIMENSIONS) - 1) // len(SCOPE_DIMENSIONS)
    for dim, count in hist.items():
        if count < lo or count > hi:
            return False, f"scope_dimension_histogram_imbalance:{dim}:{count}"
    return True, None


def check_handle_orientation_balance(
    fixtures: list[dict[str, Any]],
    *,
    k_pairs: int,
) -> tuple[bool, str | None]:
    """§B: balanced frozen opaque-handle orientation schedule."""
    if k_pairs < 2:
        return True, None
    hist = handle_orientation_histogram(fixtures)
    lo = k_pairs // len(HANDLE_ORIENTATIONS)
    hi = (k_pairs + len(HANDLE_ORIENTATIONS) - 1) // len(HANDLE_ORIENTATIONS)
    for orient, count in hist.items():
        if count < lo or count > hi:
            return False, f"handle_orientation_imbalance:{orient}:{count}"
    return True, None


def suite_fixture_order(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic suite membership order: block_id, then stratum."""
    stratum_rank = {"match": 0, "mismatch": 1, "irrelevant": 2}

    def sort_key(fixture: dict[str, Any]) -> tuple[str, int]:
        block_id = str(fixture.get("block_id", ""))
        stratum = fixture.get("stratum")
        rank = stratum_rank.get(stratum, 99) if isinstance(stratum, str) else 99
        return block_id, rank

    return sorted(fixtures, key=sort_key)


def suite_hash(
    fixtures: list[dict[str, Any]],
    *,
    k_pairs: int,
) -> str:
    """Frozen suite-level digest: membership, order, and balance metadata."""
    ordered = suite_fixture_order(fixtures)
    payload = {
        "hash_definition": HASH_DEFINITION_CANONICAL_COMPACT_JSON,
        "k_pairs": k_pairs,
        "fixture_order": [fx["fixture_id"] for fx in ordered],
        "fixture_hashes": [fixture_identity_hash(fx) for fx in ordered],
        "scope_dimension_histogram": scope_dimension_histogram(fixtures),
        "handle_orientation_histogram": handle_orientation_histogram(fixtures),
    }
    return sha256_canon(payload)


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
    """Validate suite shape, mapping, block pairing, balances, and leak-audit preconditions."""
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

    counterfactual = check_counterfactual_block_shape(validated)
    if not counterfactual.ok:
        return SuiteValidationResult(
            False, (counterfactual.refusal or "counterfactual_surface_mismatch",)
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

    dim_ok, dim_refusal = check_scope_dimension_balance(
        validated, k_pairs=expected_k_pairs
    )
    if not dim_ok and dim_refusal:
        return SuiteValidationResult(False, (dim_refusal,))

    handle_ok, handle_refusal = check_handle_orientation_balance(
        validated, k_pairs=expected_k_pairs
    )
    if not handle_ok and handle_refusal:
        return SuiteValidationResult(False, (handle_refusal,))

    leak = evaluate_leak_audit(validated)
    if not leak.ok:
        return SuiteValidationResult(False, leak.refusals)

    return SuiteValidationResult(True, (), fixture_count=len(validated))


def load_suite_manifest(path: Path | None = None) -> dict[str, Any]:
    manifest_path = path or MANIFEST_PATH
    if not manifest_path.is_file():
        raise FileNotFoundError(f"suite manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))
