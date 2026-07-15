"""Pre-pin artifact refresh and integration reporting — not production runtime."""

from __future__ import annotations

import json
from pathlib import Path

from harness.efc_compare_production import (REPO,
                                            build_production_contract,
                                            production_check_contract_hash,
                                            refresh_pinned_artifacts as _refresh_core)


def refresh_pinned_artifacts() -> dict[str, str]:
    from harness.efc_compare_inputs import write_structured_inputs

    return _refresh_core(write_structured_inputs=write_structured_inputs)


def build_integration_report(adapter_contract_sha256: str) -> dict:
    from harness.efc_check import check_adapter_contract_hash
    from harness.efc_compare_expectations import write_expectations
    from harness.efc_compare_production import (STRUCTURED_INPUTS_PATH,
                                                derivation_module_unreachable,
                                                interpret_structured_input,
                                                load_verified_structured_inputs,
                                                wire_lookup_unreachable)

    if adapter_contract_sha256 != check_adapter_contract_hash():
        raise ValueError("adapter contract hash mismatch")
    write_expectations()
    refresh = refresh_pinned_artifacts()
    contract = build_production_contract()
    candidate_hash = production_check_contract_hash(contract,
                                                    adapter_contract_sha256)
    structured = load_verified_structured_inputs(contract)
    outputs = []
    for row in structured["rows"]:
        outputs.append({
            "source_reference": row["source_reference"],
            "decision_scope_sha256": row["decision_scope_sha256"],
            "raw_sha256": row["raw_sha256"],
            "operation": row["operation"],
            "scope_matches": interpret_structured_input(row),
        })
    expectations_path = REPO / "corpus/efc_calibration/authoring_c2" / \
        "comparison_expectations_v1.json"
    expectations = json.loads(expectations_path.read_text())
    by_ref = {e["source_reference"]: e["expected_scope_matches"]
              for e in expectations["rows"]}
    agreements = sum(1 for o in outputs
                     if by_ref[o["source_reference"]] == o["scope_matches"])
    return {
        "schema_version": "efc-production-comparison-integration-v1",
        "status": "candidate_not_pinned",
        "production_rule_path": contract.rule_artifact_path,
        "rule_artifact_file_sha256": contract.rule_artifact_file_sha256,
        "rule_artifact_canonical_sha256": contract.rule_artifact_canonical_sha256,
        "interpreter_modules": list(contract.interpreter_modules),
        "interpreter_sha256": contract.interpreter_sha256,
        "conformance_vectors_path": contract.conformance_vectors_path,
        "conformance_vectors_sha256": contract.conformance_vectors_sha256,
        "structured_inputs_path": contract.structured_inputs_path,
        "structured_inputs_file_sha256": contract.structured_inputs_file_sha256,
        "structured_inputs_population_binding_sha256":
            contract.structured_inputs_population_binding_sha256,
        "structured_inputs_schema_version":
            contract.structured_inputs_schema_version,
        "structured_inputs_row_count": contract.structured_inputs_row_count,
        "adapter_contract_sha256": adapter_contract_sha256,
        "candidate_check_contract_hash": candidate_hash,
        "dispositive_row_count": len(outputs),
        "oracle_agreement_count": agreements,
        "wire_lookup_unreachable_from_production": wire_lookup_unreachable(),
        "derivation_module_unreachable_from_production":
            derivation_module_unreachable(),
        "license_binding_review_note": (
            "typed license atoms and population bindings require separate "
            "conformance review; not covered by Kimi C2a semantic review"),
        "outputs": outputs,
    }


def write_integration_artifact(path: Path | None = None) -> Path:
    from harness.efc_check import check_adapter_contract_hash

    path = path or (REPO / "corpus/efc_calibration/authoring_c2"
                    / "production_comparison_integration.json")
    report = build_integration_report(check_adapter_contract_hash())
    path.write_text(json.dumps(report, sort_keys=True, indent=1) + "\n")
    return path


if __name__ == "__main__":
    refresh = refresh_pinned_artifacts()
    out = write_integration_artifact()
    contract = build_production_contract()
    from harness.efc_check import check_adapter_contract_hash
    print(json.dumps({
        **refresh,
        "candidate_check_contract_hash": production_check_contract_hash(
            contract, check_adapter_contract_hash()),
        "integration_artifact": str(out.relative_to(REPO)),
    }, indent=2))
