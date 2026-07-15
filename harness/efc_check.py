"""Named-check adapter boundary — SPEC_EPISTEMIC_FRAME_CHECK_V0 §2.2.

The only v0 action is `scope_provenance_check_v0`. This module is the frozen
adapter boundary: a provenance store AND the scope-comparison executor are
both injected.

**Resolution A (moderator, final round): no production comparison execution
exists before the population-pinned rule does.** The accepted design defines
no comparison-rule language or interpreter, and this builder may not invent
one. The executor protocol here is therefore WIRE-ONLY: `WireComparisonRule`
and `wire_rule_contract_hash` are named so they cannot be mistaken for a
production-bound rule, and NO API in this module can mint a final production
`check_contract_hash` — `check_contract_hash()` refuses unconditionally.
The check-contract identity is typed-pending
(`pending_check_contract_identity`) until a later, separately reviewed
population-rule artifact plus a deterministic interpreter and conformance
proof exist. That is an honest pending boundary, not unfinished work.

The returned evidence is a bounded typed object carrying cited provenance and
the verdict `scope_matches` — never a final answer, prose recommendation, or
an instruction to commit or defer (§2.2). The evidence schema is structurally
closed so there is no field a recommendation could ride.

§10.1 ceilings are enforced at this boundary: controller source-read tokens
≤ 512 and check-output tokens ≤ 256 fail the invocation closed; the §9
verdict layer converts a ledgered violation into a loss.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from typing import Callable

from harness import efc_contracts as c
from harness.efc_renderer import canonical_tokens

CHECK_EVIDENCE_SCHEMA_VERSION = "efc_check_evidence_v1"
PENDING_COMPARISON_RULE = "pending_population_pinned_comparison_rule"


class CheckContractError(ValueError):
    """Check invocation outside the §2.2 contract. Fail-closed."""


# ---------------------------------------------------------------------------
# WIRE-ONLY comparison executor (resolution A): synthetic test execution,
# never a production-bound rule.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WireComparisonRule:
    """A WIRE-ONLY scope-comparison executor for synthetic fixtures. The
    callable's behavior is outside anything a hash can cover, so this type
    can never carry production identity: it exists so the adapter and the
    six-lane wire board can be exercised before the population-pinned rule
    artifact and its deterministic interpreter exist."""
    rule_id: str
    contract: dict
    compare: Callable[[str, str], bool]


def validate_wire_comparison_rule(rule: WireComparisonRule) -> None:
    if not isinstance(rule, WireComparisonRule):
        raise CheckContractError(
            "the check executor must be a WireComparisonRule (wire-only)")
    if not isinstance(rule.rule_id, str) or not rule.rule_id \
            or len(rule.rule_id) > 128:
        raise CheckContractError("rule_id must be a compact identifier")
    if not isinstance(rule.contract, dict) or not rule.contract:
        raise CheckContractError(
            "rule contract must be a non-empty declarative payload")
    if rule.contract.get("rule_id") != rule.rule_id:
        raise CheckContractError(
            "rule contract payload must carry its own rule_id")
    try:
        json.dumps(rule.contract, sort_keys=True)
    except (TypeError, ValueError) as e:
        raise CheckContractError(f"rule contract not canonicalizable: {e}")
    if not callable(rule.compare):
        raise CheckContractError("rule compare operation must be callable")


def wire_rule_contract_hash(rule: WireComparisonRule) -> str:
    """Identity of the WIRE rule's declarative payload — for wire
    authorization bookkeeping only; never a production check contract."""
    validate_wire_comparison_rule(rule)
    return hashlib.sha256(json.dumps(rule.contract, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")
                          ).hexdigest()


# ---------------------------------------------------------------------------
# Provenance store adapter.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProvenanceRecord:
    """A population-pinned provenance record as served by an injected store.
    In this workspace, only conspicuously fictional wire fixtures."""
    oracle_id: str
    source_reference: str
    authoritative_scope: str
    cited_text: str
    raw_sha256: str | None = None


class ProvenanceStore:
    """In-memory adapter; the frozen tool contract for wire tests. Fetching
    real records is a different seat's job and is not authorized here."""

    def __init__(self, records: list[ProvenanceRecord]):
        self._by_ref = {r.source_reference: r for r in records}

    def fetch(self, source_reference: str) -> ProvenanceRecord:
        record = self._by_ref.get(source_reference)
        if record is None:
            raise CheckContractError(
                f"no population-pinned provenance record for "
                f"{source_reference!r}")
        return record


# ---------------------------------------------------------------------------
# Bounded evidence object (§2.2) and the check action.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CheckEvidence:
    """§2.2 bounded evidence object. Closed schema: cited provenance, the
    verdict, the rule that produced it, and deterministic token accounting.
    No answer field exists."""
    check_id: str
    comparison_rule_id: str
    source_reference: str
    oracle_id: str
    cited_provenance: str
    scope_matches: bool
    controller_source_read_tokens: int
    check_output_tokens: int

    def rendered(self) -> str:
        return (f"check_id: {self.check_id}\n"
                f"source_reference: {self.source_reference}\n"
                f"cited_provenance: {self.cited_provenance}\n"
                f"scope_matches: {self.scope_matches}")


def run_scope_provenance_check(store: ProvenanceStore, source_reference: str,
                               decision_scope: str,
                               wire_rule: WireComparisonRule) -> CheckEvidence:
    """§2.2 steps 1-4: fetch, read authoritative scope under the frozen tool
    contract, compare with the INJECTED wire executor, return bounded
    evidence. Wire execution only in this workspace."""
    validate_wire_comparison_rule(wire_rule)
    if not isinstance(source_reference, str) or not source_reference:
        raise CheckContractError("source_reference must be a non-empty string")
    if not isinstance(decision_scope, str) or not decision_scope:
        raise CheckContractError("decision_scope must be a non-empty string")
    record = store.fetch(source_reference)
    read_tokens = len(canonical_tokens(record.authoritative_scope)) + len(
        canonical_tokens(record.cited_text))
    if read_tokens > c.MAX_CONTROLLER_SOURCE_READ_TOKENS:
        raise CheckContractError(
            f"controller source read {read_tokens} tokens > "
            f"{c.MAX_CONTROLLER_SOURCE_READ_TOKENS} (§10.1 hard ceiling)")
    verdict = wire_rule.compare(record.authoritative_scope, decision_scope)
    if not isinstance(verdict, bool):
        raise CheckContractError(
            "comparison rule returned a non-boolean verdict")
    evidence = CheckEvidence(
        check_id=c.CHECK_ID,
        comparison_rule_id=wire_rule.rule_id,
        source_reference=source_reference,
        oracle_id=record.oracle_id,
        cited_provenance=record.cited_text,
        scope_matches=verdict,
        controller_source_read_tokens=read_tokens,
        check_output_tokens=0)
    out_tokens = len(canonical_tokens(evidence.rendered()))
    if out_tokens > c.MAX_EXTERNAL_CHECK_OUTPUT_TOKENS:
        raise CheckContractError(
            f"check output {out_tokens} tokens > "
            f"{c.MAX_EXTERNAL_CHECK_OUTPUT_TOKENS} (§10.1 hard ceiling)")
    return CheckEvidence(**{**evidence.__dict__, "check_output_tokens": out_tokens})


# ---------------------------------------------------------------------------
# Contract identity (§3.2/§5.2): adapter contract implemented; the FINAL
# check contract is structurally unmintable here (resolution A).
# ---------------------------------------------------------------------------

def check_adapter_contract_payload() -> dict:
    """The implemented ADAPTER contract: closed evidence schema and §10.1
    ceilings. This is the builder's artifact; it deliberately excludes any
    comparison-rule semantics."""
    return {
        "check_id": c.CHECK_ID,
        "schema_version": CHECK_EVIDENCE_SCHEMA_VERSION,
        "evidence_fields": [f.name for f in fields(CheckEvidence)],
        "ceilings": {
            "check_invocations_per_task": c.MAX_CHECK_INVOCATIONS_PER_TASK,
            "controller_source_read_tokens": c.MAX_CONTROLLER_SOURCE_READ_TOKENS,
            "check_output_tokens": c.MAX_EXTERNAL_CHECK_OUTPUT_TOKENS,
        },
        # resolution G: the evidence/treatment insertion point is structural
        "placebo_position_gate": "structural_single_insertion_point",
    }


def check_adapter_contract_hash() -> str:
    return hashlib.sha256(json.dumps(check_adapter_contract_payload(),
                                     sort_keys=True, separators=(",", ":")
                                     ).encode("utf-8")).hexdigest()


def check_contract_hash(*_args, **_kwargs) -> str:
    """Resolution A: NO production check-contract hash can be minted in this
    workspace, from any input. The final identity requires the
    population-pinned rule artifact, a deterministic interpreter, and a
    separately reviewed conformance proof — none of which exist yet."""
    raise CheckContractError(
        "no production check-contract identity can be minted: the "
        "population-pinned comparison rule, its deterministic interpreter, "
        "and the conformance proof are pending (resolution A); wire "
        "execution uses WireComparisonRule and wire_rule_contract_hash")


def pending_check_contract_identity() -> dict:
    """Typed pending marker for artifact reporting while no population-pinned
    rule exists."""
    return {
        "status": "pending",
        "reason": PENDING_COMPARISON_RULE,
        "adapter_contract_sha256": check_adapter_contract_hash(),
    }


# ---------------------------------------------------------------------------
# Production comparison path (population-pinned; no wire executor).
# ---------------------------------------------------------------------------

from harness.efc_compare_production import (  # noqa: E402
    ProductionComparisonContract,
    build_production_contract,
    execute_pinned_binding,
    interpret_structured_input,
    production_check_contract_hash as _production_check_contract_hash,
    validate_production_contract,
    validate_structured_input,
)


def validate_production_comparison_contract(
        contract: ProductionComparisonContract) -> None:
    if isinstance(contract, WireComparisonRule):
        raise CheckContractError(
            "production path cannot accept WireComparisonRule")
    try:
        validate_production_contract(contract)
    except ValueError as e:
        raise CheckContractError(str(e)) from e


def production_check_contract_hash(
        contract: ProductionComparisonContract) -> str:
    validate_production_comparison_contract(contract)
    return _production_check_contract_hash(contract,
                                           check_adapter_contract_hash())


def run_production_scope_check(
        store: ProvenanceStore,
        source_reference: str,
        decision_scope_sha256: str,
        contract: ProductionComparisonContract) -> CheckEvidence:
    """Production §2.2 path: hash-pinned binding only; no caller operands."""
    validate_production_comparison_contract(contract)
    if isinstance(contract, WireComparisonRule):
        raise CheckContractError(
            "production path cannot accept WireComparisonRule")
    if not isinstance(source_reference, str) or not source_reference:
        raise CheckContractError("source_reference must be a non-empty string")
    if not isinstance(decision_scope_sha256, str) or not decision_scope_sha256:
        raise CheckContractError(
            "decision_scope_sha256 must be a non-empty string")
    record = store.fetch(source_reference)
    if not record.raw_sha256:
        raise CheckContractError(
            "production path requires provenance raw_sha256 lineage")
    read_tokens = len(canonical_tokens(record.authoritative_scope)) + len(
        canonical_tokens(record.cited_text))
    if read_tokens > c.MAX_CONTROLLER_SOURCE_READ_TOKENS:
        raise CheckContractError(
            f"controller source read {read_tokens} tokens > "
            f"{c.MAX_CONTROLLER_SOURCE_READ_TOKENS} (§10.1 hard ceiling)")
    try:
        verdict = execute_pinned_binding(
            contract, source_reference, decision_scope_sha256,
            provenance_raw_sha256=record.raw_sha256)
    except ValueError as e:
        raise CheckContractError(str(e)) from e
    if not isinstance(verdict, bool):
        raise CheckContractError(
            "production comparison returned a non-boolean verdict")
    evidence = CheckEvidence(
        check_id=c.CHECK_ID,
        comparison_rule_id=contract.rule_id,
        source_reference=source_reference,
        oracle_id=record.oracle_id,
        cited_provenance=record.cited_text,
        scope_matches=verdict,
        controller_source_read_tokens=read_tokens,
        check_output_tokens=0)
    out_tokens = len(canonical_tokens(evidence.rendered()))
    if out_tokens > c.MAX_EXTERNAL_CHECK_OUTPUT_TOKENS:
        raise CheckContractError(
            f"check output {out_tokens} tokens > "
            f"{c.MAX_EXTERNAL_CHECK_OUTPUT_TOKENS} (§10.1 hard ceiling)")
    return CheckEvidence(**{**evidence.__dict__, "check_output_tokens": out_tokens})
