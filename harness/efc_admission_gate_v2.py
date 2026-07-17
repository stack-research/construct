"""EFC v2 admission gate — SPEC §C eight-predicate gate and §D typed outcomes.

Pure deterministic score-time and manifest-time predicates. No engine contact.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from harness.efc_intervals import newcombe_diff_interval, wilson_interval
from harness.efc_leak_audit_v2 import evaluate_leak_audit
from harness.efc_menu_composition_v2 import ALL_STRATA, RELEVANT_STRATA

PART_I_SPEC_SHA256 = (
    "8cedf6537aa7f6c2df792ad581d4f937066d5c639812907c3c8ea90c21197d62"
)

K_DEFAULT = 128
C0 = 0.80
DELTA = 0.25
CONFIDENCE = 0.95

STRATUM_COUNT_MIN = 52
STRATUM_COUNT_MAX = 56

PAIR_SWITCH_REGION = (53, 75)

WITHIN_CLASS_WILSON_FLOOR = 0.80
IRRELEVANT_WILSON_FLOOR = 0.80

AdmissionOutcome = Literal[
    "pass",
    "confounded(admission_band)",
    "confounded(within_class_commit)",
    "confounded(within_class_non_commit)",
    "confounded(pair_constant_policy)",
    "confounded(pair_leak)",
    "confounded(pair_anticue)",
    "confounded(render_leak)",
    "confounded(irrelevant_band)",
    "confounded(commitment_invalid_rate)",
    "confounded(battery_shopping)",
]


@dataclass(frozen=True)
class GateResult:
    gate: str
    passed: bool
    verdict: AdmissionOutcome | Literal["pass"]
    detail: dict[str, Any]


@dataclass(frozen=True)
class AdmissionGateReport:
    passed: bool
    verdict: AdmissionOutcome | Literal["pass"]
    gates: tuple[GateResult, ...]
    derived_ub: float
    pinned_ub: float | None = None


def binom_pmf(k: int, n: int, p: float) -> float:
    return math.comb(n, k) * (p**k) * ((1.0 - p) ** (n - k))


def binom_cdf(k: int, n: int, p: float) -> float:
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    return sum(binom_pmf(i, n, p) for i in range(k + 1))


def central_binomial_region(n: int, p: float, alpha: float = 0.05) -> tuple[int, int]:
    """Equal-tail central acceptance region; each tail <= alpha/2."""
    tail = alpha / 2.0
    lo = 0
    while lo < n and binom_cdf(lo, n, p) <= tail:
        lo += 1
    hi = n
    while hi > 0 and (1.0 - binom_cdf(hi - 1, n, p)) <= tail:
        hi -= 1
    return lo, hi


def compute_ub(k: int, *, c0: float = C0, delta: float = DELTA,
               confidence: float = CONFIDENCE) -> float:
    """§C.1: UB(K) = (1/K) * max{ b : NewcombeLB95(cK, b; K) >= Δ }."""
    c_k = math.ceil(k * c0)
    best_b = 0
    for b in range(k + 1):
        lower, _ = newcombe_diff_interval(c_k, k, b, k, confidence)
        if lower >= delta:
            best_b = b
    return best_b / k


def balanced_relevant_accuracy(
    rows: list[dict[str, Any]],
    *,
    lane: str = "M_untreated",
) -> tuple[float, dict[str, int]]:
    """§A estimand: mean per-class accuracy over {match, mismatch}."""
    counts: dict[str, int] = {s: 0 for s in RELEVANT_STRATA}
    totals: dict[str, int] = {s: 0 for s in RELEVANT_STRATA}
    for row in rows:
        if row.get("lane") != lane:
            continue
        stratum = row.get("stratum")
        if stratum not in RELEVANT_STRATA:
            continue
        if row.get("validation_outcome") == "budget_refusal":
            continue
        totals[stratum] += 1
        if row.get("oracle_outcome") == "pass":
            counts[stratum] += 1
    accuracies = [
        counts[s] / totals[s] if totals[s] else 0.0 for s in RELEVANT_STRATA
    ]
    return sum(accuracies) / len(accuracies), counts


def evaluate_admission_band_gate(
    rows: list[dict[str, Any]],
    params: dict[str, Any],
) -> GateResult:
    k = int(params["K"])
    floor = float(params["floor"])
    ub = float(params["UB"])
    confidence = float(params.get("confidence", CONFIDENCE))
    recomputed_ub = compute_ub(k, c0=float(params.get("C0", C0)),
                               delta=float(params.get("delta", DELTA)),
                               confidence=confidence)
    pinned_ub = params.get("pinned_UB")
    if pinned_ub is not None and abs(float(pinned_ub) - recomputed_ub) > 1e-12:
        return GateResult(
            gate="admission_band",
            passed=False,
            verdict="confounded(admission_band)",
            detail={
                "reason": "pinned_ub_disagreement",
                "recomputed_ub": recomputed_ub,
                "pinned_ub": float(pinned_ub),
            },
        )

    balanced, per_stratum = balanced_relevant_accuracy(rows)
    per_stratum_ok = all(
        STRATUM_COUNT_MIN <= per_stratum[s] <= STRATUM_COUNT_MAX
        for s in RELEVANT_STRATA
    )
    in_band = floor <= balanced <= ub and per_stratum_ok
    verdict: AdmissionOutcome | Literal["pass"] = (
        "pass" if in_band else "confounded(admission_band)"
    )
    return GateResult(
        gate="admission_band",
        passed=in_band,
        verdict=verdict,
        detail={
            "K": k,
            "floor": floor,
            "UB": ub,
            "recomputed_ub": recomputed_ub,
            "balanced_accuracy": balanced,
            "per_stratum_passes": per_stratum,
            "per_stratum_range": [STRATUM_COUNT_MIN, STRATUM_COUNT_MAX],
            "per_stratum_ok": per_stratum_ok,
        },
    )


def evaluate_within_class_gate(
    rows: list[dict[str, Any]],
    *,
    lane: str = "M_forced_class",
    floor: float = WITHIN_CLASS_WILSON_FLOOR,
    confidence: float = CONFIDENCE,
) -> GateResult:
    """§C.3: Wilson LB >= floor per class over 2K dual-scored observations."""
    classes: dict[str, list[bool]] = {"commit": [], "non_commit": []}
    for row in rows:
        if row.get("lane") != lane:
            continue
        supplied = row.get("supplied_class")
        if supplied not in classes:
            continue
        if row.get("validation_outcome") == "commitment_invalid":
            classes[supplied].append(False)
            continue
        if row.get("validation_outcome") == "budget_refusal":
            continue
        classes[supplied].append(row.get("oracle_outcome") == "pass")

    detail: dict[str, Any] = {}
    failures: list[str] = []
    for cls, obs in classes.items():
        n = len(obs)
        successes = sum(obs)
        lb, _ = wilson_interval(successes, n, confidence) if n else (0.0, 0.0)
        passed = n > 0 and lb >= floor
        detail[cls] = {
            "successes": successes,
            "n": n,
            "wilson_lb": lb,
            "floor": floor,
            "passed": passed,
        }
        if not passed:
            failures.append(cls)

    if failures == ["commit"]:
        verdict: AdmissionOutcome | Literal["pass"] = (
            "confounded(within_class_commit)"
        )
    elif failures == ["non_commit"]:
        verdict = "confounded(within_class_non_commit)"
    elif failures:
        verdict = "confounded(within_class_commit)"
    else:
        verdict = "pass"
    return GateResult(
        gate="within_class_competence",
        passed=not failures,
        verdict=verdict,
        detail=detail,
    )


def _pair_rows_by_block(
    rows: list[dict[str, Any]],
    fixtures_by_id: dict[str, dict[str, Any]],
    *,
    lane: str = "M_untreated",
) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    blocks: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        if row.get("lane") != lane:
            continue
        fid = row.get("fixture_id")
        if not isinstance(fid, str):
            continue
        fixture = fixtures_by_id.get(fid)
        if fixture is None:
            continue
        stratum = fixture.get("stratum")
        block_id = fixture.get("block_id")
        if not isinstance(block_id, str) or stratum not in RELEVANT_STRATA:
            continue
        blocks.setdefault(block_id, {})[stratum] = row
    pairs: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for block_id, by_stratum in blocks.items():
        if "match" in by_stratum and "mismatch" in by_stratum:
            pairs[block_id] = (by_stratum["match"], by_stratum["mismatch"])
    return pairs


def _selected_class(
    row: dict[str, Any],
    fixture: dict[str, Any],
) -> str | None:
    if row.get("validation_outcome") != "commitment_valid":
        return None
    enum = row.get("commitment_enum") or row.get("response_commitment_enum")
    if not isinstance(enum, str):
        return None
    role_map = fixture.get("role_map")
    if not isinstance(role_map, dict):
        return None
    cls = role_map.get(enum)
    return cls if cls in ("commit", "non_commit") else None


def evaluate_pair_constant_policy_gate(
    rows: list[dict[str, Any]],
    fixtures_by_id: dict[str, dict[str, Any]],
    params: dict[str, Any],
) -> GateResult:
    """§C.4: S switched pairs in central Binomial(K, 0.5) region."""
    k = int(params["K"])
    lo, hi = PAIR_SWITCH_REGION
    if "pair_switch_region" in params:
        region = params["pair_switch_region"]
        lo, hi = int(region[0]), int(region[1])

    pairs = _pair_rows_by_block(rows, fixtures_by_id)
    switched = 0
    correct_orientation = 0
    pair_details: list[dict[str, Any]] = []

    for block_id, (match_row, mismatch_row) in pairs.items():
        match_fx = fixtures_by_id[match_row["fixture_id"]]
        mismatch_fx = fixtures_by_id[mismatch_row["fixture_id"]]
        match_cls = _selected_class(match_row, match_fx)
        mismatch_cls = _selected_class(mismatch_row, mismatch_fx)
        if match_cls is None or mismatch_cls is None:
            pair_details.append({
                "block_id": block_id,
                "switched": False,
                "skipped": True,
            })
            continue
        is_switched = match_cls != mismatch_cls
        if is_switched:
            switched += 1
            covering_commits = match_cls == "commit" and mismatch_cls == "non_commit"
            if covering_commits:
                correct_orientation += 1
        pair_details.append({
            "block_id": block_id,
            "match_class": match_cls,
            "mismatch_class": mismatch_cls,
            "switched": is_switched,
        })

    s_ok = lo <= switched <= hi
    orientation_detail: dict[str, Any] = {}
    orientation_ok = True
    orientation_verdict: AdmissionOutcome | Literal["pass"] = "pass"
    if switched > 0:
        r_lo, r_hi = central_binomial_region(switched, 0.5)
        orientation_ok = r_lo <= correct_orientation <= r_hi
        orientation_detail = {
            "S": switched,
            "R": correct_orientation,
            "accept_region": [r_lo, r_hi],
        }
        if not orientation_ok:
            if correct_orientation > r_hi:
                orientation_verdict = "confounded(pair_leak)"
            else:
                orientation_verdict = "confounded(pair_anticue)"

    passed = s_ok and orientation_ok
    if not s_ok:
        verdict: AdmissionOutcome | Literal["pass"] = (
            "confounded(pair_constant_policy)"
        )
    elif not orientation_ok:
        verdict = orientation_verdict
    else:
        verdict = "pass"

    return GateResult(
        gate="pair_constant_policy",
        passed=passed,
        verdict=verdict,
        detail={
            "K": k,
            "S": switched,
            "S_region": [lo, hi],
            "S_ok": s_ok,
            "orientation": orientation_detail,
            "pairs": pair_details,
        },
    )


def evaluate_commitment_invalid_rate_gate(
    rows: list[dict[str, Any]],
    ceiling_spec: dict[str, Any],
) -> GateResult:
    """§C.5: validity gate upstream — inherited v1 machinery."""
    global_ceiling = float(ceiling_spec.get("global_minimum", 0.05))
    cells_spec = ceiling_spec.get("cells", [])
    cells: list[dict[str, Any]] = []
    refusals: list[str] = []
    for cell in cells_spec:
        if not isinstance(cell, dict):
            continue
        lane = cell.get("lane")
        stratum = cell.get("stratum")
        ceiling = float(cell.get("ceiling", global_ceiling))
        if not isinstance(lane, str) or not isinstance(stratum, str):
            continue
        scoped = [
            row
            for row in rows
            if row.get("lane") == lane
            and row.get("stratum") == stratum
            and row.get("validation_outcome") != "budget_refusal"
        ]
        invalid = sum(
            1 for row in scoped
            if row.get("validation_outcome") == "commitment_invalid"
        )
        total = len(scoped)
        rate = invalid / total if total else 0.0
        passed = rate <= ceiling
        if not passed:
            refusals.append(f"{lane}:{stratum}")
        cells.append({
            "lane": lane,
            "stratum": stratum,
            "invalid": invalid,
            "total": total,
            "rate": rate,
            "ceiling": ceiling,
            "passed": passed,
        })
    verdict: AdmissionOutcome | Literal["pass"] = (
        "pass" if not refusals else "confounded(commitment_invalid_rate)"
    )
    return GateResult(
        gate="commitment_invalid_rate",
        passed=not refusals,
        verdict=verdict,
        detail={"cells": cells, "refusals": refusals},
    )


def evaluate_irrelevant_band_gate(
    rows: list[dict[str, Any]],
    *,
    lane: str = "M_irrelevant",
    floor: float = IRRELEVANT_WILSON_FLOOR,
    confidence: float = CONFIDENCE,
) -> GateResult:
    """§C.8: Wilson LB of irrelevant accuracy >= floor."""
    scoped = [
        row
        for row in rows
        if row.get("lane") == lane
        and row.get("stratum") == "irrelevant"
        and row.get("validation_outcome") != "budget_refusal"
    ]
    successes = sum(1 for row in scoped if row.get("oracle_outcome") == "pass")
    n = len(scoped)
    lb, _ = wilson_interval(successes, n, confidence) if n else (0.0, 0.0)
    passed = n > 0 and lb >= floor
    verdict: AdmissionOutcome | Literal["pass"] = (
        "pass" if passed else "confounded(irrelevant_band)"
    )
    return GateResult(
        gate="irrelevant_band",
        passed=passed,
        verdict=verdict,
        detail={
            "successes": successes,
            "n": n,
            "wilson_lb": lb,
            "floor": floor,
        },
    )


def evaluate_leak_audit_gate(
    fixtures: list[dict[str, Any]],
    rendered_surfaces: dict[str, str] | None = None,
) -> GateResult:
    """§C.6: L1/L2/L3 pre-contact leak audit."""
    result = evaluate_leak_audit(fixtures, rendered_surfaces=rendered_surfaces)
    if result.ok:
        return GateResult(
            gate="leak_audit",
            passed=True,
            verdict="pass",
            detail={"cells": [c.__dict__ for c in result.cells]},
        )
    confound = result.confound or "confounded(render_leak)"
    verdict: AdmissionOutcome | Literal["pass"] = confound  # type: ignore[assignment]
    return GateResult(
        gate="leak_audit",
        passed=False,
        verdict=verdict,
        detail={
            "refusals": list(result.refusals),
            "cells": [c.__dict__ for c in result.cells],
        },
    )


def evaluate_fork_identity(
    manifest: dict[str, Any],
    *,
    engine: str,
    effort: str,
    render_hash: str,
) -> GateResult:
    """§C.7: admission and scored legs share engine, effort, render constants."""
    fork = manifest.get("fork_identity", {})
    expected = {
        "engine": engine,
        "effort": effort,
        "render_hash": render_hash,
    }
    mismatches = {
        key: {"expected": val, "manifest": fork.get(key)}
        for key, val in expected.items()
        if fork.get(key) != val
    }
    passed = not mismatches
    return GateResult(
        gate="fork_identity",
        passed=passed,
        verdict="pass" if passed else "confounded(admission_band)",
        detail={"mismatches": mismatches, "fork_identity": fork},
    )


def admission_gate_params(k: int = K_DEFAULT) -> dict[str, Any]:
    """Manifest-pinned §C parameters with derived UB."""
    ub = compute_ub(k)
    lo, hi = central_binomial_region(k, 0.5)
    return {
        "K": k,
        "C0": C0,
        "delta": DELTA,
        "confidence": CONFIDENCE,
        "floor": 0.40,
        "UB": ub,
        "pinned_UB": ub,
        "per_stratum_count_range": [STRATUM_COUNT_MIN, STRATUM_COUNT_MAX],
        "pair_switch_region": [lo, hi],
        "within_class_wilson_floor": WITHIN_CLASS_WILSON_FLOOR,
        "irrelevant_wilson_floor": IRRELEVANT_WILSON_FLOOR,
        "l3_threshold": 0.60,
        "estimand": "balanced_relevant_accuracy",
    }


def evaluate_admission_gate(
    *,
    rows: list[dict[str, Any]],
    fixtures: list[dict[str, Any]],
    manifest: dict[str, Any],
    rendered_surfaces: dict[str, str] | None = None,
) -> AdmissionGateReport:
    """Run all eight §C predicates in gate order."""
    params = manifest.get("admission_gate_params", admission_gate_params())
    fixtures_by_id = {
        f["fixture_id"]: f for f in fixtures if isinstance(f.get("fixture_id"), str)
    }
    derived_ub = compute_ub(int(params["K"]))

    gates = (
        evaluate_commitment_invalid_rate_gate(
            rows, manifest.get("commitment_invalid_rate_ceiling", {})
        ),
        evaluate_admission_band_gate(rows, params),
        evaluate_within_class_gate(rows),
        evaluate_pair_constant_policy_gate(rows, fixtures_by_id, params),
        evaluate_leak_audit_gate(fixtures, rendered_surfaces),
        evaluate_irrelevant_band_gate(rows),
        evaluate_fork_identity(
            manifest,
            engine=str(manifest.get("engine", "")),
            effort=str(manifest.get("effort", "")),
            render_hash=str(
                manifest.get("contract_hashes", {}).get("foreground_template_hash", "")
            ),
        ),
    )

    for gate in gates:
        if not gate.passed:
            return AdmissionGateReport(
                passed=False,
                verdict=gate.verdict,
                gates=gates,
                derived_ub=derived_ub,
                pinned_ub=float(params.get("UB", derived_ub)),
            )
    return AdmissionGateReport(
        passed=True,
        verdict="pass",
        gates=gates,
        derived_ub=derived_ub,
        pinned_ub=float(params.get("UB", derived_ub)),
    )
