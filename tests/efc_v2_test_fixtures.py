"""Shared synthetic v2 fixtures for wire tests — no authored battery content."""

from __future__ import annotations

from typing import Any

ACTION_SET = ("alpha_commit", "beta_commit", "gamma_hold", "delta_hold")
MENU_ORDER_MATCH = ["gamma_hold", "delta_hold", "alpha_commit", "beta_commit"]
MENU_ORDER_MISMATCH = ["delta_hold", "beta_commit", "alpha_commit", "gamma_hold"]
MENU_ORDER_IRRELEVANT = ["gamma_hold", "beta_commit", "alpha_commit", "delta_hold"]
ROLE_MAP = {
    "alpha_commit": "commit",
    "beta_commit": "commit",
    "gamma_hold": "non_commit",
    "delta_hold": "non_commit",
}


def _trigger_fields() -> dict[str, Any]:
    return {
        "assertion_basis_kind": "direct_observation",
        "observation_boundary_present": True,
        "source_reference_present": False,
        "decision_scope_present": False,
        "source_reference": "",
        "decision_scope": "service example-api version 1.0",
    }


def make_relevant_fixture(
    *,
    fixture_id: str,
    block_id: str,
    stratum: str,
    scope_bit: str,
    coherent_commit: str = "alpha_commit",
    coherent_non_commit: str = "gamma_hold",
    missing_scope_dimension: str = "population",
    task_suffix: str = "",
) -> dict[str, Any]:
    expected = coherent_commit if scope_bit == "covers" else coherent_non_commit
    menu_order = (
        MENU_ORDER_MATCH if stratum == "match" else MENU_ORDER_MISMATCH
    )
    return {
        "fixture_id": fixture_id,
        "block_id": block_id,
        "task_id": fixture_id,
        "population_id": "efc_calibration_v2_test",
        "stratum": stratum,
        "scope_bit": scope_bit,
        "coherent_commit_action": coherent_commit,
        "coherent_non_commit_action": coherent_non_commit,
        "missing_scope_dimension": missing_scope_dimension,
        "action_set": list(ACTION_SET),
        "menu_order": list(menu_order),
        "role_map": dict(ROLE_MAP),
        "expected_commitment_enum": expected,
        "task_body": (
            f"Review operational ticket {fixture_id} for block {block_id}. "
            f"Choose one response label from the menu. {task_suffix}"
        ),
        **_trigger_fields(),
    }


def make_irrelevant_fixture(
    *,
    fixture_id: str,
    block_id: str,
    expected: str = "delta_hold",
) -> dict[str, Any]:
    return {
        "fixture_id": fixture_id,
        "block_id": block_id,
        "task_id": fixture_id,
        "population_id": "efc_calibration_v2_test",
        "stratum": "irrelevant",
        "action_set": list(ACTION_SET),
        "menu_order": list(MENU_ORDER_IRRELEVANT),
        "role_map": dict(ROLE_MAP),
        "expected_commitment_enum": expected,
        "task_body": (
            f"Observation-only record {fixture_id} for block {block_id}. "
            "Pick the listed response label."
        ),
        **_trigger_fields(),
    }


def make_block(block_index: int) -> list[dict[str, Any]]:
    bid = f"block-{block_index:04d}"
    # Alternate task suffixes so the frozen L3 lexical heuristic stays at chance.
    match_suffix = "partial gap noted." if block_index % 2 else "uniform baseline."
    return [
        make_relevant_fixture(
            fixture_id=f"{bid}-match",
            block_id=bid,
            stratum="match",
            scope_bit="covers",
            task_suffix=match_suffix,
        ),
        make_relevant_fixture(
            fixture_id=f"{bid}-mismatch",
            block_id=bid,
            stratum="mismatch",
            scope_bit="misses",
        ),
        make_irrelevant_fixture(
            fixture_id=f"{bid}-irrelevant",
            block_id=bid,
        ),
    ]


def make_minimal_suite(block_count: int = 1) -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    for i in range(block_count):
        fixtures.extend(make_block(i))
    return fixtures
