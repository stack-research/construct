"""Exact-enum commitment oracle — SPEC_EPISTEMIC_FRAME_CHECK_V2 (inherits v1 §2.5.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from harness.efc_commitment_wire_v2 import CommitmentValidation

OracleOutcome = Literal["pass", "fail"]


@dataclass(frozen=True)
class OracleScore:
    outcome: OracleOutcome
    validation_outcome: Literal["commitment_valid", "commitment_invalid"]
    commitment_enum: str | None
    expected_commitment_enum: str
    invalid_reason: str | None = None


def score_commitment_oracle_v2(
    validated: CommitmentValidation,
    expected_commitment_enum: str,
) -> OracleScore:
    """Score one row after schema validation."""
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
