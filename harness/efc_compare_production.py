"""Population-pinned production scope comparison — resolution A interpreter.

Derives ``scope_matches`` only from hash-verified population bindings.
No fixture lookup, no expected-label reads, no injected callables, no wire
table, no caller-supplied operands.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from harness.efc_compare_version import (CompareDomainError,
                                         compare_versions,
                                         parse_ghsa_range,
                                         parse_iso_date,
                                         version_in_any_range,
                                         version_satisfies_constraints)

REPO = Path(__file__).resolve().parent.parent
COMPARISON_ROOT = REPO / "corpus" / "efc_calibration" / "comparison"
RULE_PATH = COMPARISON_ROOT / "production_rule_v1.json"
VECTORS_PATH = COMPARISON_ROOT / "conformance_vectors_v1.json"
STRUCTURED_INPUTS_PATH = COMPARISON_ROOT / "structured_inputs_v1.json"

RULE_ID = "efc_production_comparison_v1"
SCHEMA_VERSION = "efc-production-comparison-rule-v1"
CANONICALIZATION_ID = "efc_compare_canonicalization_v1"
STRUCTURED_INPUTS_SCHEMA_VERSION = "efc-production-structured-inputs-v1"

SUPPORTED_OPERATIONS = frozenset({
    "cargo_affected_membership",
    "ghsa_semver_membership",
    "eol_support_on_date",
    "go_symbol_version_membership",
    "license_permission_granted",
    "license_section_waiver_applies",
    "license_inclusion_obligation_holds",
})

SUPPORTED_ECOSYSTEMS = frozenset({"crates.io", "npm", "pip"})

_FORBIDDEN_INPUT_KEYS = frozenset({
    "expected_scope_matches",
    "required_behavior",
    "expect_match",
    "behavior",
    "task_id",
    "oracle_id",
    "fixture_id",
    "logical_slot",
})


class ProductionCompareError(ValueError):
    """Production comparison outside the pinned contract. Fail-closed."""


@dataclass(frozen=True)
class ProductionComparisonContract:
    """Declarative production comparison identity — no runtime callable."""
    rule_id: str
    schema_version: str
    rule_artifact_path: str
    rule_artifact_file_sha256: str
    rule_artifact_canonical_sha256: str
    interpreter_modules: tuple[str, ...]
    interpreter_sha256: str
    canonicalization_id: str
    conformance_vectors_path: str
    conformance_vectors_sha256: str
    structured_inputs_path: str
    structured_inputs_file_sha256: str
    structured_inputs_schema_version: str
    structured_inputs_row_count: int
    structured_inputs_population_binding_sha256: str
    operations: tuple[str, ...]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rule_artifact_canonical_hash(artifact: dict) -> str:
    payload = {k: v for k, v in artifact.items()
               if k != "rule_artifact_canonical_sha256"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")
                          ).hexdigest()


def population_binding_payload(data: dict) -> dict:
    return {
        "row_count": data["row_count"],
        "rows": sorted(data["rows"], key=lambda r: (
            r["source_reference"], r["decision_scope_sha256"])),
        "schema_version": data["schema_version"],
    }


def population_binding_sha256_from_data(data: dict) -> str:
    payload = population_binding_payload(data)
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")
                          ).hexdigest()


def _sha256_modules(relative_paths: tuple[str, ...]) -> str:
    h = hashlib.sha256()
    for rel in relative_paths:
        data = (REPO / rel).read_bytes()
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(data)
    return h.hexdigest()


def canonicalization_payload() -> dict:
    return {
        "canonicalization_id": CANONICALIZATION_ID,
        "date_comparison": "iso8601_calendar_date_inclusive_support_through_eol",
        "ghsa_range_grammar": (
            "comma-separated AND fragments within one range string; "
            "multi-range OR only across range_strings entries"
        ),
        "ghsa_version_token_grammar": (
            "numeric_dotted: DIGIT+(.DIGIT+)* ; rejects whitespace, ||, "
            "commas inside a fragment, comparator residue in bound, caret, "
            "tilde, and wildcard forms"
        ),
        "license_atoms": "case_insensitive_substring_on_normalized_clause",
        "version_tokenizer": "dot_hyphen_plus_split_numeric_then_lexicographic_tail",
    }


def interpreter_module_paths() -> tuple[str, ...]:
    return ("harness/efc_compare_production.py",
            "harness/efc_compare_version.py")


def _require_str(operands: dict, key: str) -> str:
    val = operands.get(key)
    if not isinstance(val, str) or not val.strip():
        raise ProductionCompareError(f"missing or empty operand {key!r}")
    return val


def _require_list_str(operands: dict, key: str) -> list[str]:
    val = operands.get(key)
    if not isinstance(val, list) or not val:
        raise ProductionCompareError(f"missing or empty list operand {key!r}")
    if not all(isinstance(x, str) and x for x in val):
        raise ProductionCompareError(f"non-string entries in {key!r}")
    return val


def _normalize_clause(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def _eval_cargo_affected(operands: dict) -> bool:
    eco = _require_str(operands, "ecosystem")
    if eco not in SUPPORTED_ECOSYSTEMS:
        raise ProductionCompareError(f"unsupported ecosystem {eco!r}")
    version = _require_str(operands, "version")
    if "introduced" in operands:
        introduced = _require_str(operands, "introduced")
        fixed = _require_str(operands, "fixed_exclusive")
        return (version_satisfies_constraints(
            version, parse_ghsa_range(f">= {introduced}"))
                and version_satisfies_constraints(
                    version, parse_ghsa_range(f"< {fixed}")))
    upper = _require_str(operands, "upper_exclusive")
    return version_satisfies_constraints(
        version, parse_ghsa_range(f"< {upper}"))


def _eval_ghsa_semver(operands: dict) -> bool:
    eco = _require_str(operands, "ecosystem")
    if eco not in SUPPORTED_ECOSYSTEMS:
        raise ProductionCompareError(f"unsupported ecosystem {eco!r}")
    version = _require_str(operands, "version")
    ranges = _require_list_str(operands, "range_strings")
    parsed = tuple(parse_ghsa_range(r) for r in ranges)
    return version_in_any_range(version, parsed)


def _eval_eol_support(operands: dict) -> bool:
    eol = parse_iso_date(_require_str(operands, "eol_date"))
    check = parse_iso_date(_require_str(operands, "check_date"))
    return check <= eol


def _eval_go_symbol(operands: dict) -> bool:
    version = _require_str(operands, "version")
    upper = _require_str(operands, "upper_exclusive")
    symbol = _require_str(operands, "symbol")
    listed = _require_str(operands, "listed_symbol")
    if symbol != listed:
        return False
    return compare_versions(version, upper) < 0


def _eval_license_permission(operands: dict) -> bool:
    clause = _normalize_clause(_require_str(operands, "clause_text"))
    for phrase in _require_list_str(operands, "required_phrases"):
        if phrase.lower() not in clause:
            return False
    return True


def _eval_license_waiver(operands: dict) -> bool:
    clause = _normalize_clause(_require_str(operands, "clause_text"))
    for sec in _require_list_str(operands, "sections"):
        if sec.lower() not in clause:
            raise ProductionCompareError(
                f"license section atom absent from clause: {sec!r}")
    if "without complying" not in clause:
        raise ProductionCompareError("waiver language absent from clause")
    return True


def _eval_license_inclusion(operands: dict) -> bool:
    clause = _normalize_clause(_require_str(operands, "clause_text"))
    category = _normalize_clause(_require_str(operands, "category_phrase"))
    if "must be included" not in clause and "must include" not in clause:
        raise ProductionCompareError("inclusion obligation language absent")
    if category in clause and "unless" in clause:
        return False
    return True


_OPERATION_DISPATCH = {
    "cargo_affected_membership": _eval_cargo_affected,
    "ghsa_semver_membership": _eval_ghsa_semver,
    "eol_support_on_date": _eval_eol_support,
    "go_symbol_version_membership": _eval_go_symbol,
    "license_permission_granted": _eval_license_permission,
    "license_section_waiver_applies": _eval_license_waiver,
    "license_inclusion_obligation_holds": _eval_license_inclusion,
}


def validate_operation_row(row: dict) -> None:
    """Validate operation shape for synthetic conformance vectors."""
    if not isinstance(row, dict):
        raise ProductionCompareError("structured input must be a dict")
    for key in _FORBIDDEN_INPUT_KEYS:
        if key in row:
            raise ProductionCompareError(
                f"forbidden dispatch key in structured input: {key!r}")
    op = row.get("operation")
    if op not in SUPPORTED_OPERATIONS:
        raise ProductionCompareError(f"unknown operation {op!r}")
    operands = row.get("operands")
    if not isinstance(operands, dict):
        raise ProductionCompareError("operands must be a dict")
    for key in _FORBIDDEN_INPUT_KEYS:
        if key in operands:
            raise ProductionCompareError(
                f"forbidden dispatch key in operands: {key!r}")


def validate_binding_row(row: dict) -> None:
    validate_operation_row(row)
    for key in ("source_reference", "raw_sha256", "decision_scope_sha256"):
        if not isinstance(row.get(key), str) or not row[key]:
            raise ProductionCompareError(f"missing binding key {key!r}")


def validate_structured_input(row: dict) -> None:
    """Validate a population binding row shape."""
    validate_binding_row(row)


def interpret_operation_row(row: dict) -> bool:
    """Evaluate operands for conformance vectors and pinned rows."""
    validate_operation_row(row)
    op = row["operation"]
    try:
        return _OPERATION_DISPATCH[op](row["operands"])
    except CompareDomainError as e:
        raise ProductionCompareError(str(e)) from e


def interpret_structured_input(row: dict) -> bool:
    """Evaluate one hash-bound population row to a boolean verdict."""
    validate_binding_row(row)
    return interpret_operation_row(row)


def load_rule_artifact(path: Path | None = None) -> dict:
    path = path or RULE_PATH
    return json.loads(path.read_text())


def load_verified_structured_inputs(
        contract: ProductionComparisonContract) -> dict:
    path = REPO / contract.structured_inputs_path
    file_hash = _sha256_file(path)
    if file_hash != contract.structured_inputs_file_sha256:
        raise ProductionCompareError("structured inputs file hash mismatch")
    data = json.loads(path.read_text())
    if data.get("schema_version") != contract.structured_inputs_schema_version:
        raise ProductionCompareError("structured inputs schema mismatch")
    if data.get("row_count") != contract.structured_inputs_row_count:
        raise ProductionCompareError("structured inputs row count mismatch")
    binding_hash = population_binding_sha256_from_data(data)
    if binding_hash != contract.structured_inputs_population_binding_sha256:
        raise ProductionCompareError("population binding hash mismatch")
    return data


def resolve_pinned_row(contract: ProductionComparisonContract,
                       source_reference: str,
                       decision_scope_sha256: str) -> dict:
    """Select the unique hash-verified population binding for one check."""
    if not source_reference or not decision_scope_sha256:
        raise ProductionCompareError("missing binding selector keys")
    data = load_verified_structured_inputs(contract)
    matches = [
        row for row in data["rows"]
        if row["source_reference"] == source_reference
        and row["decision_scope_sha256"] == decision_scope_sha256
    ]
    if not matches:
        raise ProductionCompareError("no population binding for selector")
    if len(matches) > 1:
        raise ProductionCompareError("duplicate population binding for selector")
    row = matches[0]
    validate_binding_row(row)
    return row


def execute_pinned_binding(contract: ProductionComparisonContract,
                           source_reference: str,
                           decision_scope_sha256: str,
                           *,
                           provenance_raw_sha256: str) -> bool:
    """Resolve and execute only the hash-pinned population row."""
    row = resolve_pinned_row(contract, source_reference, decision_scope_sha256)
    if row["source_reference"] != source_reference:
        raise ProductionCompareError("pinned row source_reference mismatch")
    if row["raw_sha256"] != provenance_raw_sha256:
        raise ProductionCompareError(
            "pinned row raw_sha256 does not match provenance lineage")
    return interpret_structured_input(row)


def build_production_contract(
        rule_path: Path | None = None,
        vectors_path: Path | None = None,
        structured_path: Path | None = None) -> ProductionComparisonContract:
    rule_path = rule_path or RULE_PATH
    vectors_path = vectors_path or VECTORS_PATH
    structured_path = structured_path or STRUCTURED_INPUTS_PATH
    artifact = load_rule_artifact(rule_path)
    if artifact.get("rule_id") != RULE_ID:
        raise ProductionCompareError("rule_id mismatch")
    if artifact.get("schema_version") != SCHEMA_VERSION:
        raise ProductionCompareError("schema_version mismatch")
    modules = tuple(artifact.get("interpreter_modules", interpreter_module_paths()))
    rule_file_hash = _sha256_file(rule_path)
    rule_canonical_hash = rule_artifact_canonical_hash(artifact)
    if artifact.get("rule_artifact_canonical_sha256") != rule_canonical_hash:
        raise ProductionCompareError("rule artifact canonical hash mismatch")
    interp_hash = _sha256_modules(modules)
    if artifact.get("interpreter_sha256") != interp_hash:
        raise ProductionCompareError("interpreter hash mismatch")
    vec_hash = _sha256_file(vectors_path)
    if artifact.get("conformance_vectors_sha256") != vec_hash:
        raise ProductionCompareError("conformance vectors hash mismatch")
    structured_file_hash = _sha256_file(structured_path)
    if artifact.get("structured_inputs_file_sha256") != structured_file_hash:
        raise ProductionCompareError("structured inputs file hash mismatch")
    structured = json.loads(structured_path.read_text())
    binding_hash = population_binding_sha256_from_data(structured)
    if artifact.get("structured_inputs_population_binding_sha256") != binding_hash:
        raise ProductionCompareError("population binding hash mismatch in rule")
    if artifact.get("structured_inputs_schema_version") != structured["schema_version"]:
        raise ProductionCompareError("structured inputs schema mismatch in rule")
    if artifact.get("structured_inputs_row_count") != structured["row_count"]:
        raise ProductionCompareError("structured inputs row count mismatch in rule")
    ops = tuple(artifact["operations"])
    if set(ops) != SUPPORTED_OPERATIONS:
        raise ProductionCompareError("operations set mismatch")
    return ProductionComparisonContract(
        rule_id=RULE_ID,
        schema_version=SCHEMA_VERSION,
        rule_artifact_path=str(rule_path.relative_to(REPO)),
        rule_artifact_file_sha256=rule_file_hash,
        rule_artifact_canonical_sha256=rule_canonical_hash,
        interpreter_modules=modules,
        interpreter_sha256=interp_hash,
        canonicalization_id=CANONICALIZATION_ID,
        conformance_vectors_path=str(vectors_path.relative_to(REPO)),
        conformance_vectors_sha256=vec_hash,
        structured_inputs_path=str(structured_path.relative_to(REPO)),
        structured_inputs_file_sha256=structured_file_hash,
        structured_inputs_schema_version=structured["schema_version"],
        structured_inputs_row_count=structured["row_count"],
        structured_inputs_population_binding_sha256=binding_hash,
        operations=ops,
    )


def validate_production_contract(contract: ProductionComparisonContract) -> None:
    if not isinstance(contract, ProductionComparisonContract):
        raise ProductionCompareError(
            "production path requires ProductionComparisonContract")
    on_disk = build_production_contract(
        REPO / contract.rule_artifact_path,
        REPO / contract.conformance_vectors_path,
        REPO / contract.structured_inputs_path)
    if on_disk != contract:
        raise ProductionCompareError("contract does not match on-disk artifacts")


def production_contract_identity_payload(
        contract: ProductionComparisonContract,
        adapter_contract_sha256: str) -> dict:
    validate_production_contract(contract)
    return {
        "check_id": "scope_provenance_check_v0",
        "schema_version": "efc_production_check_contract_v1",
        "rule_id": contract.rule_id,
        "rule_schema_version": contract.schema_version,
        "rule_artifact_file_sha256": contract.rule_artifact_file_sha256,
        "rule_artifact_canonical_sha256": contract.rule_artifact_canonical_sha256,
        "interpreter_sha256": contract.interpreter_sha256,
        "canonicalization": canonicalization_payload(),
        "conformance_vectors_sha256": contract.conformance_vectors_sha256,
        "structured_inputs_file_sha256": contract.structured_inputs_file_sha256,
        "structured_inputs_population_binding_sha256":
            contract.structured_inputs_population_binding_sha256,
        "structured_inputs_schema_version":
            contract.structured_inputs_schema_version,
        "structured_inputs_row_count": contract.structured_inputs_row_count,
        "adapter_contract_sha256": adapter_contract_sha256,
        "operations": list(contract.operations),
        "ceilings": {
            "check_invocations_per_task": 1,
            "controller_source_read_tokens": 512,
            "check_output_tokens": 256,
        },
    }


def production_check_contract_hash(
        contract: ProductionComparisonContract,
        adapter_contract_sha256: str) -> str:
    payload = production_contract_identity_payload(contract,
                                                   adapter_contract_sha256)
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")
                          ).hexdigest()


def run_conformance_vector(vector: dict) -> bool | str:
    """Run one conformance vector; return bool verdict or error token."""
    expect = vector.get("expect")
    if expect == "error":
        try:
            interpret_operation_row(vector["input"])
        except ProductionCompareError:
            return "error"
        return "unexpected_ok"
    return interpret_operation_row(vector["input"])


def derivation_module_unreachable() -> bool:
    """Production runtime must not import pre-pin derivation modules."""
    import ast

    tree = ast.parse(Path(__file__).read_text())
    banned = ("harness.efc_compare_inputs", "harness.efc_compare_expectations",
              "harness.efc_author_c2", "efc_compare_inputs",
              "efc_compare_expectations", "efc_author_c2")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in banned:
                    return False
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module in banned:
                return False
    return True


def wire_lookup_unreachable() -> bool:
    """Static guard: production module must not import wire lookup paths."""
    import ast

    tree = ast.parse(Path(__file__).read_text())
    banned_modules = ("harness.efc_author_c2", "efc_author_c2")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in banned_modules:
                    return False
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module in banned_modules:
                return False
    return True


def refresh_pinned_artifacts(
        write_structured_inputs=None) -> dict[str, str]:
    """Recompute pinned hashes and write comparison artifacts."""
    if write_structured_inputs is None:
        raise ProductionCompareError(
            "refresh requires an injected structured-input writer")

    COMPARISON_ROOT.mkdir(parents=True, exist_ok=True)
    structured_path = write_structured_inputs()
    structured = json.loads(structured_path.read_text())
    structured_file_hash = _sha256_file(structured_path)
    binding_hash = population_binding_sha256_from_data(structured)
    vectors_hash = _sha256_file(VECTORS_PATH)
    interp_hash = _sha256_modules(interpreter_module_paths())
    rule = load_rule_artifact(RULE_PATH)
    rule["interpreter_sha256"] = interp_hash
    rule["conformance_vectors_sha256"] = vectors_hash
    rule["structured_inputs_path"] = str(
        structured_path.relative_to(REPO))
    rule["structured_inputs_file_sha256"] = structured_file_hash
    rule["structured_inputs_schema_version"] = structured["schema_version"]
    rule["structured_inputs_row_count"] = structured["row_count"]
    rule["structured_inputs_population_binding_sha256"] = binding_hash
    rule.pop("rule_artifact_file_sha256", None)
    rule["rule_artifact_canonical_sha256"] = rule_artifact_canonical_hash(rule)
    RULE_PATH.write_text(json.dumps(rule, sort_keys=True, indent=1) + "\n")
    rule_file_hash = _sha256_file(RULE_PATH)
    return {
        "rule_artifact_file_sha256": rule_file_hash,
        "rule_artifact_canonical_sha256": rule["rule_artifact_canonical_sha256"],
        "interpreter_sha256": interp_hash,
        "conformance_vectors_sha256": vectors_hash,
        "structured_inputs_file_sha256": structured_file_hash,
        "structured_inputs_population_binding_sha256": binding_hash,
        "structured_inputs_path": str(structured_path.relative_to(REPO)),
    }
