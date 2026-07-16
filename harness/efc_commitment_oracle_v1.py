"""Exact-enum commitment oracle — SPEC_EPISTEMIC_FRAME_CHECK_V1 §2.5.3.

Deterministic pure scorer: validated commitment enum vs expected enum with
exact UTF-8 label-byte equality. No text normalization, network, model calls,
or filesystem writes at score time.

``commitment_invalid`` propagates as ``fail`` for every quality-gate
denominator (D5) with the invalid reason preserved for rate-ceiling accounting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from harness.efc_commitment_wire_v1 import CommitmentValidation

OracleOutcome = Literal["pass", "fail"]


@dataclass(frozen=True)
class OracleScore:
    outcome: OracleOutcome
    validation_outcome: Literal["commitment_valid", "commitment_invalid"]
    commitment_enum: str | None
    expected_commitment_enum: str
    invalid_reason: str | None = None


def score_commitment_oracle_v1(
    validated: CommitmentValidation,
    expected_commitment_enum: str,
) -> OracleScore:
    """Score one row after schema validation (§2.5.3)."""
    if validated.outcome == "commitment_invalid":
        return OracleScore(
            outcome="fail",
            validation_outcome="commitment_invalid",
            commitment_enum=validated.commitment_enum,
            expected_commitment_enum=expected_commitment_enum,
            invalid_reason=validated.invalid_reason,
        )

    committed = validated.commitment_enum
    if committed == expected_commitment_enum:
        return OracleScore(
            outcome="pass",
            validation_outcome="commitment_valid",
            commitment_enum=committed,
            expected_commitment_enum=expected_commitment_enum,
        )

    return OracleScore(
        outcome="fail",
        validation_outcome="commitment_valid",
        commitment_enum=committed,
        expected_commitment_enum=expected_commitment_enum,
    )
