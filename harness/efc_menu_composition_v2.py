"""Menu composition enforcement — SPEC_EPISTEMIC_FRAME_CHECK_V2 §B.

Pure deterministic checks for four-action menus, v2 mapping rule, and suite
structure validators. No fixture content is authored here.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Literal

from harness.efc_commitment_wire_v2 import ACTION_SET_MAX, ACTION_SET_MIN

RULES_RELPATH = "harness/efc_menu_composition_rules_v2.md"

COLD_FIXTURE_REVIEWER_SEAT = "cold_fixture_reviewer"

Stratum = Literal["match", "mismatch", "irrelevant"]
ScopeBit = Literal["covers", "misses"]
LexiconRole = Literal["commit", "non_commit"]

RELEVANT_STRATA: tuple[Stratum, ...] = ("match", "mismatch")
ALL_STRATA: tuple[Stratum, ...] = ("match", "mismatch", "irrelevant")

SCOPE_DIMENSIONS = (
    "population",
    "interval",
    "jurisdiction",
    "endpoint",
    "artifact_version",
)

CanonicalizationFailure = Literal[
    "malformed_action_set",
    "malformed_label",
    "untrimmed_label",
    "whitespace_only_label",
    "forbidden_format_character",
    "duplicate_byte_label",
    "duplicate_nfc_form",
    "action_set_too_small",
    "action_set_too_large",
]

CompositionRefusal = Literal[
    "malformed_fixture",
    "canonicalization_failed",
    "menu_order_not_permutation",
    "menu_order_unknown_label",
    "unknown_stratum",
    "role_unoccupied",
    "role_map_incomplete",
    "role_map_unknown_label",
    "role_map_invalid_role",
    "expected_not_in_action_set",
    "expected_neq_mapping_output",
    "incoherent_commit_action",
    "incoherent_non_commit_action",
    "invalid_scope_bit",
    "missing_block_id",
    "invalid_pair_structure",
    "missing_scope_dimension",
    "invalid_scope_dimension",
    "missing_plausibility_attestation",
    "malformed_plausibility_attestation",
]

PLAUSIBILITY_ATTESTATION_KEYS = frozenset({
    "fixture_id",
    "stratum",
    "reviewer_seat",
    "reviewed_at",
    "attestation_id",
})


@dataclass(frozen=True)
class CanonicalActionSet:
    labels: tuple[str, ...]


@dataclass(frozen=True)
class CanonicalizationResult:
    ok: bool
    canonical: CanonicalActionSet | None = None
    failure: CanonicalizationFailure | None = None


@dataclass(frozen=True)
class DeriveResult:
    ok: bool
    expected: str | None = None
    refusal: CompositionRefusal | None = None


@dataclass(frozen=True)
class CompositionCheck:
    ok: bool
    refusal: CompositionRefusal | None = None
    canonicalization_failure: CanonicalizationFailure | None = None


def _has_forbidden_format_char(label: str) -> bool:
    return any(unicodedata.category(ch) == "Cf" for ch in label)


def canonicalize_action_set(action_set: object) -> CanonicalizationResult:
    """NFC-gated normalization for the four-action menu."""
    if not isinstance(action_set, list):
        return CanonicalizationResult(False, failure="malformed_action_set")
    if len(action_set) < ACTION_SET_MIN:
        return CanonicalizationResult(False, failure="action_set_too_small")
    if len(action_set) > ACTION_SET_MAX:
        return CanonicalizationResult(False, failure="action_set_too_large")

    seen_bytes: set[str] = set()
    seen_nfc: set[str] = set()
    labels: list[str] = []

    for item in action_set:
        if not isinstance(item, str) or item == "":
            return CanonicalizationResult(False, failure="malformed_label")
        if not item.strip():
            return CanonicalizationResult(False, failure="whitespace_only_label")
        if item != item.strip():
            return CanonicalizationResult(False, failure="untrimmed_label")
        if _has_forbidden_format_char(item):
            return CanonicalizationResult(False, failure="forbidden_format_character")
        if item in seen_bytes:
            return CanonicalizationResult(False, failure="duplicate_byte_label")
        nfc = unicodedata.normalize("NFC", item)
        if nfc in seen_nfc:
            return CanonicalizationResult(False, failure="duplicate_nfc_form")
        seen_bytes.add(item)
        seen_nfc.add(nfc)
        labels.append(item)

    return CanonicalizationResult(
        True,
        canonical=CanonicalActionSet(labels=tuple(labels)),
    )


def derive_expected_enum_relevant(
    *,
    scope_bit: str,
    coherent_commit_action: str,
    coherent_non_commit_action: str,
    canonical_action_set: CanonicalActionSet,
    role_map: dict[str, LexiconRole],
) -> DeriveResult:
    """§B mapping: scope bit selects class; visible facts pin coherent member."""
    if scope_bit not in ("covers", "misses"):
        return DeriveResult(False, refusal="invalid_scope_bit")

    labels = canonical_action_set.labels
    label_set = set(labels)

    if coherent_commit_action not in label_set:
        return DeriveResult(False, refusal="incoherent_commit_action")
    if coherent_non_commit_action not in label_set:
        return DeriveResult(False, refusal="incoherent_non_commit_action")
    if role_map.get(coherent_commit_action) != "commit":
        return DeriveResult(False, refusal="incoherent_commit_action")
    if role_map.get(coherent_non_commit_action) != "non_commit":
        return DeriveResult(False, refusal="incoherent_non_commit_action")

    commit_members = [lb for lb in labels if role_map.get(lb) == "commit"]
    non_commit_members = [lb for lb in labels if role_map.get(lb) == "non_commit"]
    if len(commit_members) != 2 or len(non_commit_members) != 2:
        return DeriveResult(False, refusal="role_unoccupied")

    expected = (
        coherent_commit_action
        if scope_bit == "covers"
        else coherent_non_commit_action
    )
    return DeriveResult(True, expected=expected)


def action_class(
    label: str,
    role_map: dict[str, LexiconRole],
) -> LexiconRole | None:
    return role_map.get(label)


def check_fixture_composition(
    fixture: dict[str, object],
    *,
    require_plausibility_attestation: bool = False,
) -> CompositionCheck:
    """Machine-checkable composition rules for one v2 fixture."""
    base_required = {
        "fixture_id",
        "block_id",
        "stratum",
        "action_set",
        "menu_order",
        "role_map",
        "expected_commitment_enum",
    }
    if not isinstance(fixture, dict) or not base_required.issubset(fixture):
        return CompositionCheck(False, refusal="malformed_fixture")

    stratum = fixture["stratum"]
    if not isinstance(stratum, str) or stratum not in ALL_STRATA:
        return CompositionCheck(False, refusal="unknown_stratum")

    block_id = fixture["block_id"]
    if not isinstance(block_id, str) or block_id == "":
        return CompositionCheck(False, refusal="missing_block_id")

    canon = canonicalize_action_set(fixture["action_set"])
    if not canon.ok or canon.canonical is None:
        return CompositionCheck(
            False,
            refusal="canonicalization_failed",
            canonicalization_failure=canon.failure,
        )

    labels = canon.canonical.labels
    label_set = set(labels)

    menu_order = fixture["menu_order"]
    if not isinstance(menu_order, list):
        return CompositionCheck(False, refusal="malformed_fixture")
    if len(menu_order) != len(labels):
        return CompositionCheck(False, refusal="menu_order_not_permutation")
    if set(menu_order) != label_set:
        if any(not isinstance(m, str) or m not in label_set for m in menu_order):
            return CompositionCheck(False, refusal="menu_order_unknown_label")
        return CompositionCheck(False, refusal="menu_order_not_permutation")

    role_map_raw = fixture["role_map"]
    if not isinstance(role_map_raw, dict):
        return CompositionCheck(False, refusal="malformed_fixture")
    role_map: dict[str, LexiconRole] = {}
    for key, val in role_map_raw.items():
        if not isinstance(key, str) or not isinstance(val, str):
            return CompositionCheck(False, refusal="malformed_fixture")
        if val not in ("commit", "non_commit"):
            return CompositionCheck(False, refusal="role_map_invalid_role")
        role_map[key] = val  # type: ignore[assignment]

    for mapped_label in role_map:
        if mapped_label not in label_set:
            return CompositionCheck(False, refusal="role_map_unknown_label")
    for label in labels:
        if label not in role_map:
            return CompositionCheck(False, refusal="role_map_incomplete")

    expected = fixture["expected_commitment_enum"]
    if not isinstance(expected, str):
        return CompositionCheck(False, refusal="malformed_fixture")
    if expected not in label_set:
        return CompositionCheck(False, refusal="expected_not_in_action_set")

    if stratum in RELEVANT_STRATA:
        for field in (
            "scope_bit",
            "coherent_commit_action",
            "coherent_non_commit_action",
            "missing_scope_dimension",
        ):
            if field not in fixture:
                return CompositionCheck(False, refusal="malformed_fixture")
        scope_bit = fixture["scope_bit"]
        coherent_commit = fixture["coherent_commit_action"]
        coherent_non_commit = fixture["coherent_non_commit_action"]
        missing_dim = fixture["missing_scope_dimension"]
        if not isinstance(scope_bit, str) or not isinstance(coherent_commit, str):
            return CompositionCheck(False, refusal="malformed_fixture")
        if not isinstance(coherent_non_commit, str):
            return CompositionCheck(False, refusal="malformed_fixture")
        if not isinstance(missing_dim, str) or missing_dim not in SCOPE_DIMENSIONS:
            return CompositionCheck(False, refusal="invalid_scope_dimension")

        derived = derive_expected_enum_relevant(
            scope_bit=scope_bit,
            coherent_commit_action=coherent_commit,
            coherent_non_commit_action=coherent_non_commit,
            canonical_action_set=canon.canonical,
            role_map=role_map,
        )
        if not derived.ok:
            return CompositionCheck(False, refusal=derived.refusal)
        if expected != derived.expected:
            return CompositionCheck(False, refusal="expected_neq_mapping_output")
    else:
        if any(
            key in fixture
            for key in (
                "scope_bit",
                "coherent_commit_action",
                "coherent_non_commit_action",
                "missing_scope_dimension",
            )
        ):
            return CompositionCheck(False, refusal="malformed_fixture")

    if require_plausibility_attestation:
        att = fixture.get("plausibility_attestation")
        if att is None:
            return CompositionCheck(False, refusal="missing_plausibility_attestation")
        if not isinstance(att, dict) or set(att) != PLAUSIBILITY_ATTESTATION_KEYS:
            return CompositionCheck(False, refusal="malformed_plausibility_attestation")
        if att["reviewer_seat"] != COLD_FIXTURE_REVIEWER_SEAT:
            return CompositionCheck(False, refusal="malformed_plausibility_attestation")

    return CompositionCheck(True)


def check_block_pair_structure(fixtures: list[dict[str, object]]) -> CompositionCheck:
    """Each block has exactly two relevant mates and one irrelevant item."""
    blocks: dict[str, dict[str, int]] = {}
    for fixture in fixtures:
        block_id = fixture.get("block_id")
        stratum = fixture.get("stratum")
        if not isinstance(block_id, str) or not isinstance(stratum, str):
            return CompositionCheck(False, refusal="malformed_fixture")
        if block_id not in blocks:
            blocks[block_id] = {"match": 0, "mismatch": 0, "irrelevant": 0}
        if stratum not in blocks[block_id]:
            return CompositionCheck(False, refusal="unknown_stratum")
        blocks[block_id][stratum] += 1

    for counts in blocks.values():
        if counts["match"] != 1 or counts["mismatch"] != 1 or counts["irrelevant"] != 1:
            return CompositionCheck(False, refusal="invalid_pair_structure")
    return CompositionCheck(True)
