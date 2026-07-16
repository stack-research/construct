"""Menu composition enforcement — SPEC_EPISTEMIC_FRAME_CHECK_V1 §2.5.5, §8.6.

Pure deterministic checks for ``canonical_action_set`` normalization, mechanical
``(stratum, canonical_action_set, role_map) → expected_commitment_enum`` mapping,
shared decoy pool membership, plausibility attestation shape, and frozen ordinal
permutation / suite uniformity.

The hashable normative contract is ``efc_menu_composition_rules_v1.md``; this module
is the wire-test implementation consumers call at manifest/fixture validation time.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Literal

from harness.efc_commitment_wire_v1 import ACTION_SET_MAX, ACTION_SET_MIN

RULES_RELPATH = "harness/efc_menu_composition_rules_v1.md"

COLD_FIXTURE_REVIEWER_SEAT = "cold_fixture_reviewer"
TIE_BREAK_ID = "lexicographic_minimum_utf8"

Stratum = Literal["match_mismatch", "match_commit", "irrelevant"]
LexiconRole = Literal["non_commit", "commit", "baseline"]

STRATUM_TO_ROLE: dict[Stratum, LexiconRole] = {
    "match_mismatch": "non_commit",
    "match_commit": "commit",
    "irrelevant": "baseline",
}

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
    "decoy_not_in_shared_pool",
    "missing_plausibility_attestation",
    "malformed_plausibility_attestation",
    "ordinal_uniformity_exceeded",
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


@dataclass(frozen=True)
class SuiteOrdinalCheck:
    ok: bool
    refusal: CompositionRefusal | None = None
    histogram: tuple[int, ...] | None = None
    max_abs_dev_bound: int | None = None
    max_observed_deviation: float | None = None


def _has_forbidden_format_char(label: str) -> bool:
    return any(unicodedata.category(ch) == "Cf" for ch in label)


def canonicalize_action_set(action_set: object) -> CanonicalizationResult:
    """NFC-gated normalization per ``efc_menu_composition_rules_v1.md`` §1."""
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


def derive_expected_enum(
    stratum: str,
    canonical_action_set: CanonicalActionSet,
    role_map: dict[str, LexiconRole],
) -> DeriveResult:
    """Mechanical mapping rule (§2.5.5) with lexicographic_minimum_utf8 tie-break."""
    if stratum not in STRATUM_TO_ROLE:
        return DeriveResult(False, refusal="unknown_stratum")

    required_role = STRATUM_TO_ROLE[stratum]  # type: ignore[index]
    labels = canonical_action_set.labels

    for label in labels:
        if label not in role_map:
            return DeriveResult(False, refusal="role_map_incomplete")
        if role_map[label] not in ("non_commit", "commit", "baseline"):
            return DeriveResult(False, refusal="role_map_invalid_role")

    for mapped_label in role_map:
        if mapped_label not in labels:
            return DeriveResult(False, refusal="role_map_unknown_label")

    candidates = [lb for lb in labels if role_map[lb] == required_role]
    if not candidates:
        return DeriveResult(False, refusal="role_unoccupied")

    return DeriveResult(True, expected=min(candidates))


def max_abs_dev_bound(n: int, k: int) -> int:
    """§5.2: max_abs_dev(n, k) = ceil(n / (2k))."""
    if n <= 0 or k <= 0:
        return 0
    return -(-n // (2 * k))


def check_suite_ordinal_uniformity(
    fixtures: list[dict[str, object]],
    *,
    require_plausibility_attestation: bool = True,
) -> SuiteOrdinalCheck:
    """Suite histogram L∞ uniformity (judgment #7)."""
    if not fixtures:
        return SuiteOrdinalCheck(True, histogram=(), max_abs_dev_bound=0,
                                 max_observed_deviation=0.0)

    k: int | None = None
    counts: list[int] = []

    for fixture in fixtures:
        comp = check_fixture_composition(
            fixture,
            require_plausibility_attestation=require_plausibility_attestation,
        )
        if not comp.ok:
            return SuiteOrdinalCheck(False, refusal=comp.refusal)

        action_set = fixture.get("action_set")
        menu_order = fixture.get("menu_order")
        expected = fixture.get("expected_commitment_enum")
        if not isinstance(action_set, list) or not isinstance(menu_order, list):
            return SuiteOrdinalCheck(False, refusal="malformed_fixture")
        if not isinstance(expected, str):
            return SuiteOrdinalCheck(False, refusal="malformed_fixture")

        canon = canonicalize_action_set(action_set)
        if not canon.ok or canon.canonical is None:
            return SuiteOrdinalCheck(False, refusal="canonicalization_failed")

        fixture_k = len(canon.canonical.labels)
        if k is None:
            k = fixture_k
            counts = [0] * k
        elif fixture_k != k:
            return SuiteOrdinalCheck(False, refusal="malformed_fixture")

        try:
            idx = list(menu_order).index(expected)
        except ValueError:
            return SuiteOrdinalCheck(False, refusal="menu_order_unknown_label")
        counts[idx] += 1

    assert k is not None
    n = len(fixtures)
    mu = n / k
    bound = max_abs_dev_bound(n, k)
    max_dev = max(abs(c - mu) for c in counts)
    if max_dev > bound:
        return SuiteOrdinalCheck(
            False,
            refusal="ordinal_uniformity_exceeded",
            histogram=tuple(counts),
            max_abs_dev_bound=bound,
            max_observed_deviation=max_dev,
        )
    return SuiteOrdinalCheck(
        True,
        histogram=tuple(counts),
        max_abs_dev_bound=bound,
        max_observed_deviation=max_dev,
    )


def _validate_plausibility_attestation(
    fixture: dict[str, object],
) -> CompositionCheck | None:
    att = fixture.get("plausibility_attestation")
    if att is None:
        return CompositionCheck(False, refusal="missing_plausibility_attestation")
    if not isinstance(att, dict):
        return CompositionCheck(False, refusal="malformed_plausibility_attestation")
    if set(att) != PLAUSIBILITY_ATTESTATION_KEYS:
        return CompositionCheck(False, refusal="malformed_plausibility_attestation")
    for key in PLAUSIBILITY_ATTESTATION_KEYS:
        if not isinstance(att[key], str) or att[key] == "":
            return CompositionCheck(False, refusal="malformed_plausibility_attestation")
    if att["reviewer_seat"] != COLD_FIXTURE_REVIEWER_SEAT:
        return CompositionCheck(False, refusal="malformed_plausibility_attestation")
    fixture_id = fixture.get("fixture_id")
    stratum = fixture.get("stratum")
    if not isinstance(fixture_id, str) or not isinstance(stratum, str):
        return CompositionCheck(False, refusal="malformed_fixture")
    if att["fixture_id"] != fixture_id or att["stratum"] != stratum:
        return CompositionCheck(False, refusal="malformed_plausibility_attestation")
    return None


def check_fixture_composition(
    fixture: dict[str, object],
    *,
    require_plausibility_attestation: bool = True,
) -> CompositionCheck:
    """Machine-checkable composition rules for one fixture."""
    required = {
        "fixture_id",
        "stratum",
        "action_set",
        "menu_order",
        "role_map",
        "expected_commitment_enum",
        "shared_decoy_pool",
    }
    if not isinstance(fixture, dict) or not required.issubset(fixture):
        return CompositionCheck(False, refusal="malformed_fixture")

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

    stratum = fixture["stratum"]
    if not isinstance(stratum, str):
        return CompositionCheck(False, refusal="malformed_fixture")

    role_map_raw = fixture["role_map"]
    if not isinstance(role_map_raw, dict):
        return CompositionCheck(False, refusal="malformed_fixture")
    role_map: dict[str, LexiconRole] = {}
    for key, val in role_map_raw.items():
        if not isinstance(key, str) or not isinstance(val, str):
            return CompositionCheck(False, refusal="malformed_fixture")
        role_map[key] = val  # type: ignore[assignment]

    derived = derive_expected_enum(stratum, canon.canonical, role_map)
    if not derived.ok:
        return CompositionCheck(False, refusal=derived.refusal)

    expected = fixture["expected_commitment_enum"]
    if not isinstance(expected, str):
        return CompositionCheck(False, refusal="malformed_fixture")

    if expected not in label_set:
        return CompositionCheck(False, refusal="expected_not_in_action_set")
    if expected != derived.expected:
        return CompositionCheck(False, refusal="expected_neq_mapping_output")

    shared_pool = fixture["shared_decoy_pool"]
    if not isinstance(shared_pool, list):
        return CompositionCheck(False, refusal="malformed_fixture")
    pool_set = set(shared_pool)
    for decoy in labels:
        if decoy != expected and decoy not in pool_set:
            return CompositionCheck(False, refusal="decoy_not_in_shared_pool")

    if require_plausibility_attestation:
        att_err = _validate_plausibility_attestation(fixture)
        if att_err is not None:
            return att_err

    return CompositionCheck(True)
