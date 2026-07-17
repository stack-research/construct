"""Menu composition enforcement — SPEC_EPISTEMIC_FRAME_CHECK_V2 §B.

Pure deterministic checks for four-action menus, v2 mapping rule, and suite
structure validators. No fixture content is authored here.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from typing import Any, Literal

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

HANDLE_ORIENTATIONS = ("A", "B")

SCOPE_BIT_LEXICAL_MARKERS = ("covers", "misses")

# §B shared block surface — byte-equal across relevant mates.
BLOCK_SHARED_SURFACE_KEYS = (
    "task_body",
    "coherent_commit_action",
    "coherent_non_commit_action",
    "assertion_basis_kind",
    "observation_boundary_present",
    "source_reference_present",
    "decision_scope_present",
    "decision_scope",
    "action_set",
    "role_map",
    "menu_order",
    "missing_scope_dimension",
    "handle_orientation",
)

# Licensed provenance delta between counterfactual mates.
PROVENANCE_RECORD_KEYS = (
    "scope_bit",
    "source_reference",
    "opaque_source_handle",
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
    "missing_opaque_source_handle",
    "missing_handle_orientation",
    "invalid_handle_orientation",
    "counterfactual_surface_mismatch",
    "counterfactual_scope_bit_invalid",
    "counterfactual_provenance_unchanged",
    "counterfactual_provenance_reference_collision",
    "counterfactual_provenance_handle_collision",
    "provenance_record_missing",
    "provenance_scope_bit_contradicts_record",
    "provenance_scope_dimension_contradicts_record",
    "provenance_record_scope_invalid",
    "counterfactual_missing_scope_dimension_mismatch",
    "handle_orientation_handle_mismatch",
    "provenance_lexical_scope_leak",
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


def _canon_bytes(obj: object) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def block_shared_surface_bytes(fixture: dict[str, Any]) -> bytes:
    """Canonical bytes for the §B shared counterfactual surface."""
    surface = {key: fixture[key] for key in BLOCK_SHARED_SURFACE_KEYS}
    return _canon_bytes(surface)


def block_shared_surface_hash(fixture: dict[str, Any]) -> str:
    return hashlib.sha256(block_shared_surface_bytes(fixture)).hexdigest()


def provenance_record_bytes(fixture: dict[str, Any]) -> bytes:
    record = {key: fixture[key] for key in PROVENANCE_RECORD_KEYS}
    return _canon_bytes(record)


def expected_opaque_source_handle(block_id: str, handle_orientation: str) -> str:
    """Mechanical §B binding: frozen opaque bytes from block + orientation schedule."""
    return f"{block_id}#{handle_orientation}"


def complementary_handle_orientation(handle_orientation: str) -> str:
    if handle_orientation == "A":
        return "B"
    if handle_orientation == "B":
        return "A"
    raise ValueError(f"invalid handle_orientation: {handle_orientation!r}")


def mate_handle_orientation(block_orientation: str, stratum: str) -> str:
    """Relevant mates share block orientation schedule but address distinct handles."""
    if stratum == "match":
        return block_orientation
    if stratum == "mismatch":
        return complementary_handle_orientation(block_orientation)
    raise ValueError(f"invalid stratum for mate handle: {stratum!r}")


def expected_opaque_source_handle_for_fixture(fixture: dict[str, Any]) -> str:
    block_id = fixture["block_id"]
    block_orientation = fixture["handle_orientation"]
    stratum = fixture["stratum"]
    if not isinstance(block_id, str) or not isinstance(block_orientation, str):
        raise ValueError("fixture missing block_id or handle_orientation")
    if not isinstance(stratum, str):
        raise ValueError("fixture missing stratum")
    orientation = mate_handle_orientation(block_orientation, stratum)
    return expected_opaque_source_handle(block_id, orientation)


def expected_source_reference(opaque_source_handle: str) -> str:
    return f"ref://opaque/{opaque_source_handle}"


def provenance_carries_scope_lexicon(text: str) -> bool:
    """True when opaque provenance bytes encode the hidden scope bit."""
    lower = text.casefold()
    return any(marker in lower for marker in SCOPE_BIT_LEXICAL_MARKERS)


def check_provenance_lexical_neutrality(fixture: dict[str, Any]) -> CompositionCheck:
    """§B: opaque handles/references must not lexicalize covers vs misses."""
    for field in ("opaque_source_handle", "source_reference"):
        value = fixture.get(field)
        if not isinstance(value, str):
            return CompositionCheck(False, refusal="malformed_fixture")
        if provenance_carries_scope_lexicon(value):
            return CompositionCheck(False, refusal="provenance_lexical_scope_leak")
    return CompositionCheck(True)


def check_handle_orientation_binding(fixture: dict[str, Any]) -> CompositionCheck:
    """§B: block orientation schedule binds each mate to a distinct opaque handle."""
    block_id = fixture.get("block_id")
    handle_orientation = fixture.get("handle_orientation")
    stratum = fixture.get("stratum")
    opaque_handle = fixture.get("opaque_source_handle")
    source_reference = fixture.get("source_reference")
    if not isinstance(block_id, str) or not isinstance(handle_orientation, str):
        return CompositionCheck(False, refusal="malformed_fixture")
    if not isinstance(stratum, str) or stratum not in RELEVANT_STRATA:
        return CompositionCheck(False, refusal="malformed_fixture")
    if not isinstance(opaque_handle, str) or not isinstance(source_reference, str):
        return CompositionCheck(False, refusal="malformed_fixture")
    expected_handle = expected_opaque_source_handle_for_fixture(fixture)
    if opaque_handle != expected_handle:
        return CompositionCheck(False, refusal="handle_orientation_handle_mismatch")
    if source_reference != expected_source_reference(expected_handle):
        return CompositionCheck(False, refusal="handle_orientation_handle_mismatch")
    return CompositionCheck(True)


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
            "opaque_source_handle",
            "handle_orientation",
        ):
            if field not in fixture:
                if field == "opaque_source_handle":
                    return CompositionCheck(False, refusal="missing_opaque_source_handle")
                if field == "handle_orientation":
                    return CompositionCheck(False, refusal="missing_handle_orientation")
                return CompositionCheck(False, refusal="malformed_fixture")
        scope_bit = fixture["scope_bit"]
        coherent_commit = fixture["coherent_commit_action"]
        coherent_non_commit = fixture["coherent_non_commit_action"]
        missing_dim = fixture["missing_scope_dimension"]
        handle_orientation = fixture["handle_orientation"]
        opaque_handle = fixture["opaque_source_handle"]
        if not isinstance(scope_bit, str) or not isinstance(coherent_commit, str):
            return CompositionCheck(False, refusal="malformed_fixture")
        if not isinstance(coherent_non_commit, str):
            return CompositionCheck(False, refusal="malformed_fixture")
        if not isinstance(missing_dim, str) or missing_dim not in SCOPE_DIMENSIONS:
            return CompositionCheck(False, refusal="invalid_scope_dimension")
        if not isinstance(handle_orientation, str) or handle_orientation not in HANDLE_ORIENTATIONS:
            return CompositionCheck(False, refusal="invalid_handle_orientation")
        if not isinstance(opaque_handle, str) or opaque_handle == "":
            return CompositionCheck(False, refusal="missing_opaque_source_handle")

        lexical = check_provenance_lexical_neutrality(fixture)
        if not lexical.ok:
            return lexical
        binding = check_handle_orientation_binding(fixture)
        if not binding.ok:
            return binding

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


def check_counterfactual_block_shape(
    fixtures: list[dict[str, Any]],
) -> CompositionCheck:
    """§B: relevant mates share the block surface; provenance differs exactly once."""
    by_block: dict[str, dict[str, dict[str, Any]]] = {}
    for fixture in fixtures:
        block_id = fixture.get("block_id")
        stratum = fixture.get("stratum")
        if not isinstance(block_id, str) or not isinstance(stratum, str):
            return CompositionCheck(False, refusal="malformed_fixture")
        if stratum not in RELEVANT_STRATA:
            continue
        by_block.setdefault(block_id, {})[stratum] = fixture

    for block_id, mates in by_block.items():
        if "match" not in mates or "mismatch" not in mates:
            return CompositionCheck(False, refusal="invalid_pair_structure")
        match_fx = mates["match"]
        mismatch_fx = mates["mismatch"]

        if match_fx.get("scope_bit") != "covers":
            return CompositionCheck(False, refusal="counterfactual_scope_bit_invalid")
        if mismatch_fx.get("scope_bit") != "misses":
            return CompositionCheck(False, refusal="counterfactual_scope_bit_invalid")

        if match_fx.get("missing_scope_dimension") != mismatch_fx.get(
            "missing_scope_dimension"
        ):
            return CompositionCheck(
                False,
                refusal="counterfactual_missing_scope_dimension_mismatch",
            )

        if block_shared_surface_bytes(match_fx) != block_shared_surface_bytes(
            mismatch_fx
        ):
            return CompositionCheck(False, refusal="counterfactual_surface_mismatch")

        if provenance_record_bytes(match_fx) == provenance_record_bytes(mismatch_fx):
            return CompositionCheck(False, refusal="counterfactual_provenance_unchanged")

        if match_fx.get("source_reference") == mismatch_fx.get("source_reference"):
            return CompositionCheck(
                False,
                refusal="counterfactual_provenance_reference_collision",
            )
        if match_fx.get("opaque_source_handle") == mismatch_fx.get(
            "opaque_source_handle"
        ):
            return CompositionCheck(
                False,
                refusal="counterfactual_provenance_handle_collision",
            )

        if match_fx.get("handle_orientation") != mismatch_fx.get("handle_orientation"):
            return CompositionCheck(False, refusal="counterfactual_surface_mismatch")

    return CompositionCheck(True)
