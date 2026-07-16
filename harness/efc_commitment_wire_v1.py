"""Commitment-wire validation — SPEC_EPISTEMIC_FRAME_CHECK_V1 §2.5.1.

Pure deterministic validation for the closed action menu and model-authored
wire. The hashable JSON Schema artifact is ``efc_commitment_wire_v1.schema.json``;
this module is the wire-test implementation consumers call at score time.

``commitment_enum`` MUST be a non-empty UTF-8 string (schema ``enum_label``).
Arrays and other non-string types are ``malformed_field``.

The typed invalid subcause ``multiple_selections`` is reserved for a future
wire carrier; no current wire shape can produce it.

Validation outcomes are typed — ``commitment_invalid`` is never scorer
discretion (§2.5.1, D5).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SCHEMA_RELPATH = "harness/efc_commitment_wire_v1.schema.json"

WIRE_PROPERTIES = frozenset({"commitment_enum", "optional_prose"})
ACTION_SET_MIN = 3
ACTION_SET_MAX = 6

ValidationOutcome = Literal["commitment_valid", "commitment_invalid"]
InvalidReason = Literal[
    "absent_commitment",
    "malformed_field",
    "multiple_selections",
    "unknown_enum",
]
ActionSetFailure = Literal[
    "action_set_too_small",
    "action_set_too_large",
    "duplicate_labels",
    "malformed_action_set",
]


@dataclass(frozen=True)
class ActionSetValidation:
    ok: bool
    failure: ActionSetFailure | None = None


@dataclass(frozen=True)
class CommitmentValidation:
  outcome: ValidationOutcome
  commitment_enum: str | None = None
  invalid_reason: InvalidReason | None = None


def validate_action_set(action_set: object) -> ActionSetValidation:
    """Closed 3–6 member action_set declaration with distinct enum labels."""
    if not isinstance(action_set, list):
        return ActionSetValidation(False, "malformed_action_set")
    if len(action_set) < ACTION_SET_MIN:
        return ActionSetValidation(False, "action_set_too_small")
    if len(action_set) > ACTION_SET_MAX:
        return ActionSetValidation(False, "action_set_too_large")
    seen: set[str] = set()
    for item in action_set:
        if not isinstance(item, str) or item == "":
            return ActionSetValidation(False, "malformed_action_set")
        if item in seen:
            return ActionSetValidation(False, "duplicate_labels")
        seen.add(item)
    return ActionSetValidation(True)


def validate_commitment_wire(
    wire: object,
    action_set: list[str],
) -> CommitmentValidation:
    """Validate a model wire against a fixture-frozen action_set.

    ``action_set`` MUST already pass ``validate_action_set``; this function
    does not re-validate declaration size or duplicate labels.
    """
    if not isinstance(wire, dict):
        return CommitmentValidation("commitment_invalid",
                                    invalid_reason="malformed_field")

    extra = set(wire) - WIRE_PROPERTIES
    if extra:
        return CommitmentValidation("commitment_invalid",
                                    invalid_reason="malformed_field")

    if "commitment_enum" not in wire:
        return CommitmentValidation("commitment_invalid",
                                    invalid_reason="absent_commitment")

    raw = wire["commitment_enum"]
    if not isinstance(raw, str) or raw == "":
        return CommitmentValidation("commitment_invalid",
                                    invalid_reason="malformed_field")

    if "optional_prose" in wire and not isinstance(wire["optional_prose"], str):
        return CommitmentValidation("commitment_invalid",
                                    invalid_reason="malformed_field")

    if raw not in action_set:
        return CommitmentValidation("commitment_invalid",
                                    invalid_reason="unknown_enum")

    return CommitmentValidation("commitment_valid", commitment_enum=raw)
