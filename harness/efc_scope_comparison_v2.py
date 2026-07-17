"""Candidate scope-comparison rule interpreter — SPEC_EPISTEMIC_FRAME_CHECK_V2 §B.

Single deterministic interpreter for the population-pinned candidate rule
artifact. Used by ``validate_suite`` record-store validation AND by check-C
via an injected ``WireComparisonRule``. Does **not** mint production
``check_contract_hash``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from harness.efc_check import WireComparisonRule
from harness.efc_menu_composition_v2 import SCOPE_DIMENSIONS

ScopeVerdict = Literal["covers", "misses"]

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPARISON_ROOT = REPO_ROOT / "corpus" / "efc_calibration_v2" / "comparison"
RULE_PATH = COMPARISON_ROOT / "scope_comparison_rule_candidate_v2.json"
VECTORS_PATH = COMPARISON_ROOT / "conformance_vectors_v2.json"

RULE_ID = "efc_scope_comparison_candidate_v2"
SCHEMA_VERSION = "efc-scope-comparison-rule-candidate-v2"
VECTORS_SCHEMA_VERSION = "efc-scope-comparison-conformance-v2"
INTERPRETER_MODULE = "harness/efc_scope_comparison_v2.py"


class ScopeComparisonError(ValueError):
    """Scope comparison outside the pinned candidate contract. Fail-closed."""


def _canon_bytes(obj: object) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_modules(relative_paths: tuple[str, ...]) -> str:
    h = hashlib.sha256()
    for rel in relative_paths:
        data = (REPO_ROOT / rel).read_bytes()
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(data)
    return h.hexdigest()


def normalize_scope_value(value: str) -> str:
    """Canonical value normalization — strip surrounding whitespace."""
    return value.strip()


def parse_scope_dimensions_partial(scope: str) -> dict[str, str]:
    """Parse scope dimensions present in a scope string."""
    if not isinstance(scope, str) or not scope.strip():
        raise ScopeComparisonError("scope must be a non-empty string")
    dims: dict[str, str] = {}
    for fragment in scope.split(";"):
        piece = fragment.strip()
        if not piece:
            continue
        if "=" not in piece:
            raise ScopeComparisonError(f"malformed scope fragment: {piece!r}")
        key, value = piece.split("=", 1)
        key = key.strip()
        value = normalize_scope_value(value)
        if key not in SCOPE_DIMENSIONS:
            raise ScopeComparisonError(f"unknown scope dimension: {key!r}")
        if not value:
            raise ScopeComparisonError(f"empty scope value for dimension {key!r}")
        dims[key] = value
    return dims


def parse_scope_dimensions(scope: str) -> dict[str, str]:
    """Parse a frozen semicolon-separated scope string (all five dimensions)."""
    dims = parse_scope_dimensions_partial(scope)
    missing = [dim for dim in SCOPE_DIMENSIONS if dim not in dims]
    if missing:
        raise ScopeComparisonError(f"scope missing dimensions: {missing}")
    return dims


def format_scope_dimensions(dimensions: dict[str, str]) -> str:
    """Canonical scope serialization — sorted keys, normalized values."""
    ordered = {
        dim: normalize_scope_value(dimensions[dim])
        for dim in SCOPE_DIMENSIONS
        if dim in dimensions
    }
    return ";".join(f"{key}={ordered[key]}" for key in sorted(ordered))


def scope_missing_dimensions(
    authoritative_scope: str,
    decision_scope: str,
) -> frozenset[str]:
    """Dimensions required by decision_scope that authoritative_scope does not cover."""
    decision_dims = parse_scope_dimensions(decision_scope)
    try:
        authoritative_dims = parse_scope_dimensions_partial(authoritative_scope)
    except ScopeComparisonError:
        authoritative_dims = {}
    missing: set[str] = set()
    for dim, required in decision_dims.items():
        actual = authoritative_dims.get(dim)
        if actual != required:
            missing.add(dim)
    return frozenset(missing)


def derive_scope_verdict(
    authoritative_scope: str,
    decision_scope: str,
) -> tuple[ScopeVerdict, str | None]:
    """Candidate check-C contract: covers, or misses on exactly one dimension."""
    missing = scope_missing_dimensions(authoritative_scope, decision_scope)
    if not missing:
        return "covers", None
    if len(missing) == 1:
        return "misses", next(iter(missing))
    return "misses", None


def compare_scope_covers(
    authoritative_scope: str,
    decision_scope: str,
) -> bool:
    """Boolean scope comparison — True iff decision_scope is fully covered."""
    verdict, _ = derive_scope_verdict(authoritative_scope, decision_scope)
    return verdict == "covers"


def rule_artifact_canonical_hash(artifact: dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in artifact.items()
        if key != "rule_artifact_canonical_sha256"
    }
    return hashlib.sha256(_canon_bytes(payload)).hexdigest()


def load_rule_artifact(path: Path | None = None) -> dict[str, Any]:
    path = path or RULE_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def load_conformance_vectors(path: Path | None = None) -> dict[str, Any]:
    path = path or VECTORS_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def validate_rule_artifact(artifact: dict[str, Any]) -> None:
    if artifact.get("rule_id") != RULE_ID:
        raise ScopeComparisonError("rule_id mismatch")
    if artifact.get("schema_version") != SCHEMA_VERSION:
        raise ScopeComparisonError("schema_version mismatch")
    if artifact.get("interpreter_module") != INTERPRETER_MODULE:
        raise ScopeComparisonError("interpreter_module mismatch")
    canon = rule_artifact_canonical_hash(artifact)
    if artifact.get("rule_artifact_canonical_sha256") != canon:
        raise ScopeComparisonError("rule artifact canonical hash mismatch")
    interp = _sha256_modules((INTERPRETER_MODULE,))
    if artifact.get("interpreter_sha256") != interp:
        raise ScopeComparisonError("interpreter hash mismatch")
    vectors_path = REPO_ROOT / artifact["conformance_vectors_path"]
    vectors_hash = _sha256_file(vectors_path)
    if artifact.get("conformance_vectors_sha256") != vectors_hash:
        raise ScopeComparisonError("conformance vectors hash mismatch")


def scope_comparison_pin_payload() -> dict[str, str]:
    """Pinned bytes for manifest and ``fixture_suite_hash`` coverage."""
    artifact = load_rule_artifact()
    validate_rule_artifact(artifact)
    return {
        "rule_id": RULE_ID,
        "rule_artifact_file_sha256": _sha256_file(RULE_PATH),
        "rule_artifact_canonical_sha256": artifact["rule_artifact_canonical_sha256"],
        "interpreter_sha256": artifact["interpreter_sha256"],
        "conformance_vectors_sha256": artifact["conformance_vectors_sha256"],
    }


def build_candidate_wire_rule(path: Path | None = None) -> WireComparisonRule:
    """Injected check-C executor bound to the pinned candidate rule artifact."""
    artifact = load_rule_artifact(path)
    validate_rule_artifact(artifact)
    return WireComparisonRule(
        rule_id=artifact["rule_id"],
        contract=artifact,
        compare=compare_scope_covers,
    )


def run_conformance_vector(vector: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one vector on the interpreter path."""
    auth = vector["authoritative_scope"]
    dec = vector["decision_scope"]
    verdict, missed = derive_scope_verdict(auth, dec)
    covers = compare_scope_covers(auth, dec)
    return {
        "verdict": verdict,
        "missed_dimension": missed,
        "scope_matches": covers,
    }


def verify_conformance_vectors(vectors_doc: dict[str, Any] | None = None) -> list[str]:
    """Return refusal tokens for any vector that disagrees with expectations."""
    doc = vectors_doc if vectors_doc is not None else load_conformance_vectors()
    if doc.get("schema_version") != VECTORS_SCHEMA_VERSION:
        return ["conformance_vectors_schema_mismatch"]
    refusals: list[str] = []
    for vector in doc.get("vectors", []):
        result = run_conformance_vector(vector)
        if result["scope_matches"] != vector.get("expect_covers"):
            refusals.append(f"conformance_vector_covers_mismatch:{vector['id']}")
        if result["verdict"] != vector.get("expect_verdict"):
            refusals.append(f"conformance_vector_verdict_mismatch:{vector['id']}")
        expected_miss = vector.get("expect_missed_dimension")
        if result["missed_dimension"] != expected_miss:
            refusals.append(
                f"conformance_vector_missed_dimension_mismatch:{vector['id']}"
            )
    return refusals
