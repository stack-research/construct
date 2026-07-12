"""Typed disposition carrier, validity envelope, warrant health, mint authority
— SPEC_EPISTEMIC_FRAME_CHECK_V0 §3 (and the §11 revision table's
authorization half).

The lab licenses a derivation mechanism; the resident activates one instance
(§3). This module is the §14 wire form of that split: closed schemas whose
fields are ids, hashes, enums, and numbers — there is structurally no field
that can hold a lesson paragraph, model rationale, confidence, generalization
claim, hidden instruction, or outcome label (§3.1). String ids are
charset-checked so prose cannot ride an id field.

Mint authority is externally computed and fail-closed (§3.3). Model
nomination is accepted only as an untrusted audit record: it can never supply
trigger features, certify the causal story, activate the instance, or
override a refusal — the tests pin that a nomination flips nothing.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, fields

from harness import efc_contracts as c
from harness.efc_trigger import CITED_SOURCE, TRIGGER_FIELDS


class CarrierContractError(ValueError):
    """Carrier/envelope/revision outside the closed §3 schema. Fail-closed."""


_HEX64 = re.compile(r"^[0-9a-f]{64}$")
# ids and identifiers: compact, prose-hostile
_ID = re.compile(r"^[A-Za-z0-9._/:+-]{1,128}$")

# §2.1 predicate feature bindings, exact — the carrier owns the trigger
# fields and values, not a template id whose meaning lives in source code.
V0_PREDICATE_FEATURE_BINDINGS = {
    "assertion_basis_kind": CITED_SOURCE,
    "observation_boundary_present": False,
    "source_reference_present": True,
    "decision_scope_present": True,
}


@dataclass(frozen=True)
class ValidityEnvelope:
    """§3.2 — changing any field creates a new candidate license."""
    model_id: str
    renderer_id: str
    foreground_template_hash: str
    tool_contract_id: str
    decoding_contract_id: str
    controller_id: str
    predicate_contract_hash: str
    extractor_hash: str
    check_contract_hash: str
    engine_admission_packet_hash: str
    source_family_hash: str
    target_population_hash: str
    per_invocation_cost_ceiling: int


@dataclass(frozen=True)
class DispositionCarrier:
    """§3.1 — bounded structured state only."""
    mechanism_id: str
    mechanism_version: str
    predicate_contract_hash: str
    predicate_feature_bindings: dict
    extractor_hash: str
    check_id: str
    check_contract_hash: str
    warrant_event_ids: tuple[str, ...]
    warrant_result_hash: str
    validity_envelope: ValidityEnvelope
    status: str
    per_invocation_cost_ceiling: int
    revision_scope_rules_hash: str
    retirement_rules_hash: str


def _require_hex(name: str, value: str) -> None:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise CarrierContractError(f"{name} must be a sha256 hex digest")


def _require_id(name: str, value: str) -> None:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise CarrierContractError(
            f"{name} must be a compact identifier (got {value!r})")


def validate_envelope(env: ValidityEnvelope) -> None:
    for f in fields(ValidityEnvelope):
        value = getattr(env, f.name)
        if f.name == "per_invocation_cost_ceiling":
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise CarrierContractError(
                    "per_invocation_cost_ceiling must be a positive integer")
        elif f.name.endswith("_hash"):
            _require_hex(f.name, value)
        else:
            _require_id(f.name, value)


def envelope_hash(env: ValidityEnvelope) -> str:
    validate_envelope(env)
    return hashlib.sha256(json.dumps(asdict(env), sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")
                          ).hexdigest()


def validate_carrier(carrier: DispositionCarrier) -> None:
    if carrier.mechanism_id != c.MECHANISM_ID:
        raise CarrierContractError(f"mechanism_id {carrier.mechanism_id!r}")
    if carrier.mechanism_version != c.MECHANISM_VERSION:
        raise CarrierContractError(f"mechanism_version {carrier.mechanism_version!r}")
    if carrier.check_id != c.CHECK_ID:
        raise CarrierContractError(f"check_id {carrier.check_id!r} is not the "
                                   f"named v0 check {c.CHECK_ID!r}")
    if carrier.status != c.CARRIER_STATUS_EXPERIMENTAL:
        raise CarrierContractError(
            f"status {carrier.status!r}: v0 instances are "
            f"{c.CARRIER_STATUS_EXPERIMENTAL!r} and otherwise frozen (§8.1)")
    if carrier.predicate_feature_bindings != V0_PREDICATE_FEATURE_BINDINGS:
        raise CarrierContractError(
            "predicate_feature_bindings must be the exact §2.1 fields and "
            f"values {sorted(TRIGGER_FIELDS)}; template ids and free shapes "
            "are refused")
    if (not carrier.warrant_event_ids
            or not all(isinstance(e, str) and _ID.fullmatch(e)
                       for e in carrier.warrant_event_ids)):
        raise CarrierContractError("warrant_event_ids must be non-empty ids")
    for name in ("predicate_contract_hash", "extractor_hash",
                 "check_contract_hash", "warrant_result_hash",
                 "revision_scope_rules_hash", "retirement_rules_hash"):
        _require_hex(name, getattr(carrier, name))
    if (not isinstance(carrier.per_invocation_cost_ceiling, int)
            or isinstance(carrier.per_invocation_cost_ceiling, bool)
            or carrier.per_invocation_cost_ceiling <= 0):
        raise CarrierContractError("per_invocation_cost_ceiling must be positive")
    validate_envelope(carrier.validity_envelope)
    for shared in ("predicate_contract_hash", "extractor_hash",
                   "check_contract_hash"):
        if getattr(carrier, shared) != getattr(carrier.validity_envelope, shared):
            raise CarrierContractError(f"{shared} differs between carrier and "
                                       "envelope")
    if (carrier.per_invocation_cost_ceiling
            != carrier.validity_envelope.per_invocation_cost_ceiling):
        raise CarrierContractError(
            "per_invocation_cost_ceiling differs between carrier and envelope")


def carrier_hash(carrier: DispositionCarrier) -> str:
    """Canonical instance identity — the target of `resident_instance`
    revisions (§3.4/§11's "named instance")."""
    validate_carrier(carrier)
    payload = asdict(carrier)
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")
                          ).hexdigest()


# ---------------------------------------------------------------------------
# §3.4 typed revisions and warrant health.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TypedRevision:
    """Every revision carries exactly one typed scope (§3.4)."""
    revision_id: str
    scope: str          # one of c.REVISION_SCOPES
    applies_to: str     # id/hash the scope targets
    reason_code: str


def validate_revision(rev: TypedRevision) -> None:
    _require_id("revision_id", rev.revision_id)
    _require_id("reason_code", rev.reason_code)
    if rev.scope not in c.REVISION_SCOPES:
        raise CarrierContractError(
            f"revision scope {rev.scope!r} outside {c.REVISION_SCOPES}")
    if not isinstance(rev.applies_to, str) or not rev.applies_to:
        raise CarrierContractError("applies_to must be a non-empty id/hash")


@dataclass(frozen=True)
class WarrantHealth:
    eligible: bool
    suspended_by: str | None = None
    suspended_scope: str | None = None


def revision_applies(carrier: DispositionCarrier, rev: TypedRevision) -> bool:
    """Deterministic applicability per §11's revision table."""
    validate_revision(rev)
    if rev.scope == "source_provenance":
        return rev.applies_to in carrier.warrant_event_ids
    if rev.scope == "causal_derivation":
        return rev.applies_to == carrier.warrant_result_hash
    if rev.scope == "check_contract":
        return rev.applies_to == carrier.check_contract_hash
    if rev.scope == "resident_instance":
        return rev.applies_to == carrier_hash(carrier)
    raise CarrierContractError(f"unreachable scope {rev.scope!r}")


def warrant_health(carrier: DispositionCarrier,
                   revisions: list[TypedRevision]) -> WarrantHealth:
    """Minting and activation check warrant HEALTH, not existence (§3.4).
    An unrelated revision leaves the disposition eligible — over-broad
    suspension is the §11 governance-should-lose cell, so the machinery must
    not suspend on it."""
    validate_carrier(carrier)
    for rev in revisions:
        if revision_applies(carrier, rev):
            return WarrantHealth(eligible=False, suspended_by=rev.revision_id,
                                 suspended_scope=rev.scope)
    return WarrantHealth(eligible=True)


# ---------------------------------------------------------------------------
# §3.3 mint authority — externally computed, fail-closed.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SourceCausalVerdict:
    """The §7 held-out source-family verdict as consumed by the mint. The
    verdict itself is computed by the score-time §7 gates; the mint only
    requires it to exist, to have passed, and to be world-scored."""
    passed: bool
    world_oracle_source: str   # must not be "authored" (R1/§3.3)
    verdict_hash: str


@dataclass(frozen=True)
class NominationRecord:
    """§3.3: ledgered untrusted audit claim. Never an input to authority."""
    event_id: str
    claim_text_hash: str


@dataclass(frozen=True)
class MintInputs:
    carrier: DispositionCarrier
    source_verdict: SourceCausalVerdict | None
    provenance_live: bool
    revisions: tuple[TypedRevision, ...]
    engine_admission_verdict: str
    calibration_packet_hash: str
    expected_envelope: ValidityEnvelope
    minted_by: str
    nomination: NominationRecord | None = None


@dataclass(frozen=True)
class MintResult:
    minted: bool
    event_type: str            # disposition_minted | disposition_mint_refused
    refusal_reasons: tuple[str, ...]


def mint_disposition(inputs: MintInputs) -> MintResult:
    """All six §3.3 conditions, computed. A failed outcome cannot mint; a
    nomination cannot mint, certify, or override — it is not even read here
    beyond being carried to the ledger."""
    validate_carrier(inputs.carrier)
    reasons: list[str] = []
    verdict = inputs.source_verdict
    if verdict is None or not verdict.passed:
        reasons.append("no passing held-out source-family causal verdict (§7)")
    if verdict is not None and verdict.world_oracle_source == "authored":
        reasons.append("world oracle source is authored: retrieved is not true (R1)")
    if not inputs.provenance_live:
        reasons.append("provenance record not live at mint time")
    health = warrant_health(inputs.carrier, list(inputs.revisions))
    if not health.eligible:
        reasons.append(f"standing {health.suspended_scope} revision "
                       f"{health.suspended_by} applies to the warrant")
    if inputs.engine_admission_verdict != "engine_admitted":
        reasons.append(f"engine not admitted "
                       f"({inputs.engine_admission_verdict})")
    if (inputs.calibration_packet_hash
            != inputs.carrier.validity_envelope.engine_admission_packet_hash):
        reasons.append("admission packet is not the envelope-pinned disjoint "
                       "calibration packet")
    if envelope_hash(inputs.carrier.validity_envelope) != envelope_hash(
            inputs.expected_envelope):
        reasons.append("validity envelope mismatch: a result does not "
                       "transfer silently (§3.2)")
    if inputs.minted_by != "external_controller":
        reasons.append(f"minting must be external and deterministic, "
                       f"got {inputs.minted_by!r}")
    if reasons:
        return MintResult(False, "disposition_mint_refused", tuple(reasons))
    return MintResult(True, "disposition_minted", ())
