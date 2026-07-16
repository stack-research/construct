"""Pure deterministic EFC v1 leak-audit predictors and frozen-suite evaluator.

Normative contract: ``harness/efc_leak_audit_contract_v1.md``.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from typing import Literal, Sequence

from harness.efc_trigger import ExtractionClosureError, extract_trigger_features

CONTRACT_RELPATH = "harness/efc_leak_audit_contract_v1.md"
PREDICTOR_ID = "efc_leak_audit_v1"
PREDICTOR_HASH = "TO-BE-COMPUTED-AT-SEAL"

STRATA = ("match_mismatch", "match_commit", "irrelevant")
LEGS = ("L1", "L2")
TRIGGER_CONJUNCT_FIELDS = (
    "assertion_basis_kind",
    "observation_boundary_present",
    "source_reference_present",
    "decision_scope_present",
)

Leg = Literal["L1", "L2"]
Stratum = Literal["match_mismatch", "match_commit", "irrelevant"]


@dataclass(frozen=True)
class PredictionRow:
    fixture_id: str
    leg: Leg
    stratum: Stratum
    predicted_commitment_enum: str
    expected_commitment_enum: str
    correct: bool


@dataclass(frozen=True)
class AuditCell:
    leg: Leg
    stratum: Stratum
    correct: int
    total: int
    accuracy: float
    fail_threshold: float
    passed: bool
    refusal: str | None = None


@dataclass(frozen=True)
class LeakAuditResult:
    ok: bool
    k: int | None = None
    predictions: tuple[PredictionRow, ...] = ()
    cells: tuple[AuditCell, ...] = ()
    refusals: tuple[str, ...] = ()
    confound: str | None = None


@dataclass(frozen=True)
class LexicalMarkingResult:
    ok: bool
    refusals: tuple[str, ...] = ()
    overlaps: tuple[tuple[str, tuple[str, ...]], ...] = ()


def tokens(text: str) -> tuple[str, ...]:
    """Frozen NFKC/casefold/maximal-isalnum-run tokenizer."""
    if not isinstance(text, str):
        raise TypeError("text must be str")
    normalized = unicodedata.normalize("NFKC", text).casefold()
    out: list[str] = []
    current: list[str] = []
    for char in normalized:
        if char.isalnum():
            current.append(char)
        elif current:
            out.append("".join(current))
            current = []
    if current:
        out.append("".join(current))
    return tuple(out)


def project_trigger_feature_strings(
    fixture: dict[str, object],
) -> tuple[str, ...]:
    """Project sealed §2.1 conjuncts to frozen normalized lexical strings.

    Each projected member is the frozen tokenizer output for the conjunct's
    field name followed by its declared value. Boolean values serialize as the
    lowercase JSON literals ``true`` and ``false``.
    """
    features = extract_trigger_features(fixture)
    values: tuple[str | bool, ...] = (
        features.assertion_basis_kind,
        features.observation_boundary_present,
        features.source_reference_present,
        features.decision_scope_present,
    )
    projected: list[str] = []
    for field, value in zip(TRIGGER_CONJUNCT_FIELDS, values, strict=True):
        rendered_value = value if isinstance(value, str) else str(value).lower()
        projected.append(" ".join(tokens(f"{field} {rendered_value}")))
    return tuple(projected)


def _validate_ordering(action_set_ordering: Sequence[str]) -> tuple[str, ...]:
    if isinstance(action_set_ordering, (str, bytes)):
        raise ValueError("action_set_ordering must be a sequence of labels")
    labels = tuple(action_set_ordering)
    if not 3 <= len(labels) <= 6:
        raise ValueError("action_set_ordering must contain 3-6 labels")
    if any(not isinstance(label, str) or label == "" for label in labels):
        raise ValueError("action_set_ordering labels must be non-empty strings")
    if len(set(labels)) != len(labels):
        raise ValueError("action_set_ordering labels must be distinct")
    return labels


def predict_menu_only(action_set_ordering: Sequence[str]) -> str:
    """L1: return the first label using menu order only."""
    return _validate_ordering(action_set_ordering)[0]


def predict_task_menu(
    task_body_text: str,
    action_set_ordering: Sequence[str],
) -> str:
    """L2: token-overlap score, with menu order as the deterministic tie-break."""
    if not isinstance(task_body_text, str):
        raise TypeError("task_body_text must be str")
    labels = _validate_ordering(action_set_ordering)
    task_tokens = set(tokens(task_body_text))
    scores = [len(set(tokens(label)) & task_tokens) for label in labels]
    return labels[max(range(len(labels)), key=lambda index: scores[index])]


def canonical_predictor_spec_bytes() -> bytes:
    """Canonical predictor-spec serialization whose sha256 is pinned at seal."""
    spec = {
        "forbidden_predictor_inputs": [
            "stratum",
            "expected_commitment_enum",
            "treatment_path",
            "check_evidence",
            "disposition_state",
            "oracle_fields",
        ],
        "legs": {
            "L1": {
                "inputs": ["action_set_ordering"],
                "procedure": "return_index_0",
            },
            "L2": {
                "inputs": ["task_body_text", "action_set_ordering"],
                "procedure": "max_label_token_overlap_with_task",
                "tie_break": "lowest_menu_index",
            },
        },
        "predictor_id": PREDICTOR_ID,
        "tokenization": ["NFKC", "casefold", "maximal_isalnum_runs"],
        "version": 1,
    }
    return json.dumps(
        spec,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _validate_fixture_suite(
    fixtures: object,
) -> tuple[list[dict[str, object]] | None, int | None, str | None]:
    if not isinstance(fixtures, list) or not fixtures:
        return None, None, "malformed_fixture_suite"
    validated: list[dict[str, object]] = []
    k: int | None = None
    counts = {stratum: 0 for stratum in STRATA}
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            return None, None, "malformed_fixture"
        fixture_id = fixture.get("fixture_id")
        stratum = fixture.get("stratum")
        task_body = fixture.get("task_body")
        menu_order = fixture.get("menu_order")
        expected = fixture.get("expected_commitment_enum")
        trigger_strings = fixture.get("trigger_feature_strings")
        if (
            not isinstance(fixture_id, str)
            or fixture_id == ""
            or not isinstance(task_body, str)
            or not isinstance(menu_order, list)
            or not isinstance(expected, str)
            or not isinstance(trigger_strings, list)
            or any(not isinstance(item, str) for item in trigger_strings)
        ):
            return None, None, "malformed_fixture"
        if not trigger_strings:
            return None, None, "empty_trigger_projection"
        try:
            computed_projection = project_trigger_feature_strings(fixture)
        except (ExtractionClosureError, TypeError, ValueError):
            return None, None, "malformed_fixture"
        if not computed_projection:
            return None, None, "empty_trigger_projection"
        if tuple(trigger_strings) != computed_projection:
            return None, None, "trigger_projection_mismatch"
        if stratum not in STRATA:
            return None, None, "unknown_stratum"
        try:
            labels = _validate_ordering(menu_order)
        except (TypeError, ValueError):
            return None, None, "malformed_fixture"
        if expected not in labels:
            return None, None, "expected_not_in_action_set"
        if k is None:
            k = len(labels)
        elif len(labels) != k:
            return None, None, "mixed_action_set_size"
        counts[stratum] += 1
        validated.append(fixture)
    if any(counts[stratum] == 0 for stratum in STRATA):
        return None, None, "empty_stratum"
    return validated, k, None


def evaluate_leak_audit(fixtures: object) -> LeakAuditResult:
    """Evaluate both frozen predictor legs per stratum over a fixture suite."""
    validated, k, refusal = _validate_fixture_suite(fixtures)
    if refusal is not None or validated is None or k is None:
        return LeakAuditResult(
            ok=False,
            refusals=(refusal,) if refusal is not None else (),
        )

    predictions: list[PredictionRow] = []
    cells: list[AuditCell] = []
    refusals: list[str] = []
    threshold = 1 / k + 0.10

    for leg in LEGS:
        for stratum in STRATA:
            correct = 0
            total = 0
            for fixture in validated:
                if fixture["stratum"] != stratum:
                    continue
                menu_order = fixture["menu_order"]
                assert isinstance(menu_order, list)
                if leg == "L1":
                    predicted = predict_menu_only(menu_order)
                else:
                    task_body = fixture["task_body"]
                    assert isinstance(task_body, str)
                    predicted = predict_task_menu(task_body, menu_order)
                expected = fixture["expected_commitment_enum"]
                fixture_id = fixture["fixture_id"]
                assert isinstance(expected, str) and isinstance(fixture_id, str)
                is_correct = predicted == expected
                correct += int(is_correct)
                total += 1
                predictions.append(PredictionRow(
                    fixture_id=fixture_id,
                    leg=leg,  # type: ignore[arg-type]
                    stratum=stratum,  # type: ignore[arg-type]
                    predicted_commitment_enum=predicted,
                    expected_commitment_enum=expected,
                    correct=is_correct,
                ))
            accuracy = correct / total
            passed = accuracy <= threshold
            cell_refusal = None
            if not passed:
                cell_refusal = f"leak_audit_fail({leg}, {stratum})"
                refusals.append(cell_refusal)
            cells.append(AuditCell(
                leg=leg,  # type: ignore[arg-type]
                stratum=stratum,  # type: ignore[arg-type]
                correct=correct,
                total=total,
                accuracy=accuracy,
                fail_threshold=threshold,
                passed=passed,
                refusal=cell_refusal,
            ))

    return LeakAuditResult(
        ok=not refusals,
        k=k,
        predictions=tuple(predictions),
        cells=tuple(cells),
        refusals=tuple(refusals),
        confound=None if not refusals else "confounded(menu_leak)",
    )


def check_no_lexical_marking(fixtures: object) -> LexicalMarkingResult:
    """Check the bound §2.1 projection against each expected enum's tokens."""
    validated, _, refusal = _validate_fixture_suite(fixtures)
    if refusal is not None or validated is None:
        return LexicalMarkingResult(False, refusal and (refusal,) or ())
    refusals: list[str] = []
    overlaps: list[tuple[str, tuple[str, ...]]] = []
    for fixture in validated:
        fixture_id = fixture["fixture_id"]
        expected = fixture["expected_commitment_enum"]
        trigger_strings = fixture["trigger_feature_strings"]
        assert isinstance(fixture_id, str)
        assert isinstance(expected, str)
        assert isinstance(trigger_strings, list)
        expected_tokens = set(tokens(expected))
        overlap = set()
        for trigger_string in trigger_strings:
            assert isinstance(trigger_string, str)
            overlap.update(expected_tokens & set(tokens(trigger_string)))
        if overlap:
            refusals.append(f"no_lexical_marking_fail({fixture_id})")
            overlaps.append((fixture_id, tuple(sorted(overlap))))
    return LexicalMarkingResult(
        ok=not refusals,
        refusals=tuple(refusals),
        overlaps=tuple(overlaps),
    )
