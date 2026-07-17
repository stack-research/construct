"""Pure deterministic EFC v2 leak-audit predictors — SPEC §C.6.

Normative contract: ``harness/efc_leak_audit_contract_v2.md``.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from typing import Literal, Sequence

from harness.efc_menu_composition_v2 import ALL_STRATA, RELEVANT_STRATA

CONTRACT_RELPATH = "harness/efc_leak_audit_contract_v2.md"
PREDICTOR_ID = "efc_leak_audit_v2"

LEGS = ("L1", "L2", "L3")
L3_THRESHOLD = 0.60
L3_CHANCE = 0.50

Leg = Literal["L1", "L2", "L3"]
Stratum = Literal["match", "mismatch", "irrelevant"]


@dataclass(frozen=True)
class PredictionRow:
    fixture_id: str
    leg: Leg
    stratum: Stratum
    predicted: str
    expected: str
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


def tokens(text: str) -> tuple[str, ...]:
    """Frozen NFKC/casefold/maximal-isalnum-run tokenizer."""
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


def _validate_ordering(action_set_ordering: Sequence[str]) -> tuple[str, ...]:
    labels = tuple(action_set_ordering)
    if len(labels) != 4:
        raise ValueError("action_set_ordering must contain 4 labels")
    if len(set(labels)) != 4:
        raise ValueError("action_set_ordering labels must be distinct")
    return labels


def predict_menu_only(action_set_ordering: Sequence[str]) -> str:
    return _validate_ordering(action_set_ordering)[0]


def predict_task_menu(
    task_body_text: str,
    action_set_ordering: Sequence[str],
) -> str:
    labels = _validate_ordering(action_set_ordering)
    task_tokens = set(tokens(task_body_text))
    scores = [len(set(tokens(label)) & task_tokens) for label in labels]
    return labels[max(range(len(labels)), key=lambda i: scores[i])]


def predict_scope_from_render(rendered_surface: str) -> str:
    """L3: lexical heuristic on full render — must fail to recover scope bit."""
    surface_tokens = set(tokens(rendered_surface))
    covers_score = len(surface_tokens & {"covers", "cover", "complete"})
    misses_score = len(surface_tokens & {"misses", "miss", "gap", "partial"})
    return "covers" if covers_score >= misses_score else "misses"


def canonical_predictor_spec_bytes() -> bytes:
    spec = {
        "forbidden_predictor_inputs": [
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
                "target": "expected_commitment_enum",
            },
            "L2": {
                "inputs": ["task_body_text", "action_set_ordering"],
                "procedure": "max_label_token_overlap_with_task",
                "tie_break": "lowest_menu_index",
                "target": "expected_commitment_enum",
            },
            "L3": {
                "inputs": ["rendered_surface"],
                "procedure": "lexical_scope_heuristic",
                "target": "scope_bit",
                "chance": L3_CHANCE,
                "threshold": L3_THRESHOLD,
            },
        },
        "predictor_id": PREDICTOR_ID,
        "tokenization": ["NFKC", "casefold", "maximal_isalnum_runs"],
        "version": 2,
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
    counts = {stratum: 0 for stratum in ALL_STRATA}
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            return None, None, "malformed_fixture"
        fixture_id = fixture.get("fixture_id")
        stratum = fixture.get("stratum")
        task_body = fixture.get("task_body")
        menu_order = fixture.get("menu_order")
        expected = fixture.get("expected_commitment_enum")
        if (
            not isinstance(fixture_id, str)
            or fixture_id == ""
            or not isinstance(task_body, str)
            or not isinstance(menu_order, list)
            or not isinstance(expected, str)
            or stratum not in ALL_STRATA
        ):
            return None, None, "malformed_fixture"
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
    if any(counts[s] == 0 for s in ALL_STRATA):
        return None, None, "empty_stratum"
    return validated, k, None


def evaluate_leak_audit(
    fixtures: object,
    *,
    rendered_surfaces: dict[str, str] | None = None,
) -> LeakAuditResult:
    """Evaluate L1/L2/L3 frozen predictor legs per stratum."""
    validated, k, refusal = _validate_fixture_suite(fixtures)
    if refusal is not None or validated is None or k is None:
        return LeakAuditResult(
            ok=False,
            refusals=(refusal,) if refusal is not None else (),
        )

    l12_threshold = 1 / k + 0.10
    predictions: list[PredictionRow] = []
    cells: list[AuditCell] = []
    refusals: list[str] = []

    for leg in LEGS:
        for stratum in ALL_STRATA:
            correct = 0
            total = 0
            for fixture in validated:
                if fixture["stratum"] != stratum:
                    continue
                menu_order = fixture["menu_order"]
                assert isinstance(menu_order, list)
                fixture_id = fixture["fixture_id"]
                assert isinstance(fixture_id, str)

                if leg == "L1":
                    predicted = predict_menu_only(menu_order)
                    expected = fixture["expected_commitment_enum"]
                    assert isinstance(expected, str)
                elif leg == "L2":
                    task_body = fixture["task_body"]
                    assert isinstance(task_body, str)
                    predicted = predict_task_menu(task_body, menu_order)
                    expected = fixture["expected_commitment_enum"]
                    assert isinstance(expected, str)
                else:
                    if stratum not in RELEVANT_STRATA:
                        continue
                    scope_bit = fixture.get("scope_bit")
                    if not isinstance(scope_bit, str):
                        continue
                    expected = scope_bit
                    if rendered_surfaces and fixture_id in rendered_surfaces:
                        surface = rendered_surfaces[fixture_id]
                    else:
                        task_body = fixture.get("task_body", "")
                        assert isinstance(task_body, str)
                        surface = task_body
                    predicted = predict_scope_from_render(surface)

                is_correct = predicted == expected
                correct += int(is_correct)
                total += 1
                predictions.append(PredictionRow(
                    fixture_id=fixture_id,
                    leg=leg,
                    stratum=stratum,  # type: ignore[arg-type]
                    predicted=predicted,
                    expected=expected,
                    correct=is_correct,
                ))

            if total == 0:
                continue
            accuracy = correct / total
            threshold = l12_threshold if leg in ("L1", "L2") else L3_THRESHOLD
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

    confound = None
    if refusals:
        confound = "confounded(render_leak)" if any(
            "L3" in r for r in refusals
        ) else "confounded(render_leak)"
    return LeakAuditResult(
        ok=not refusals,
        k=k,
        predictions=tuple(predictions),
        cells=tuple(cells),
        refusals=tuple(refusals),
        confound=confound,
    )
