"""Shared synthetic v2 fixtures for wire tests — no authored battery content."""

from __future__ import annotations

from typing import Any

from harness.efc_menu_composition_v2 import (
    SCOPE_DIMENSIONS,
    complementary_handle_orientation,
    expected_opaque_source_handle,
    expected_opaque_source_handle_for_fixture,
    expected_source_reference,
)
from harness.efc_provenance_record_store_v2 import (
    build_record_store_from_fixtures,
    decision_scope_for_block,
)


ACTION_SET = ("alpha_commit", "beta_commit", "gamma_hold", "delta_hold")
MENU_ORDER = ["beta_commit", "delta_hold", "gamma_hold", "alpha_commit"]
MENU_ORDER_IRRELEVANT = ["beta_commit", "delta_hold", "alpha_commit", "gamma_hold"]
ROLE_MAP = {
    "alpha_commit": "commit",
    "beta_commit": "commit",
    "gamma_hold": "non_commit",
    "delta_hold": "non_commit",
}


def _trigger_fields(
    *,
    source_reference: str,
    decision_scope: str,
) -> dict[str, Any]:
    return {
        "assertion_basis_kind": "direct_observation",
        "observation_boundary_present": True,
        "source_reference_present": bool(source_reference),
        "decision_scope_present": bool(decision_scope),
        "source_reference": source_reference,
        "decision_scope": decision_scope,
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
    handle_orientation: str = "A",
    opaque_source_handle: str | None = None,
    task_body: str | None = None,
    source_reference: str | None = None,
    decision_scope: str | None = None,
) -> dict[str, Any]:
    expected = coherent_commit if scope_bit == "covers" else coherent_non_commit
    draft = {
        "block_id": block_id,
        "stratum": stratum,
        "handle_orientation": handle_orientation,
    }
    if opaque_source_handle is None:
        opaque_source_handle = expected_opaque_source_handle_for_fixture(draft)
    if source_reference is None:
        source_reference = expected_source_reference(opaque_source_handle)
    if decision_scope is None:
        decision_scope = decision_scope_for_block(0)
    if task_body is None:
        task_body = (
            f"Review operational ticket for block {block_id}. "
            "Choose one response label from the menu."
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
        "handle_orientation": handle_orientation,
        "opaque_source_handle": opaque_source_handle,
        "action_set": list(ACTION_SET),
        "menu_order": list(MENU_ORDER),
        "role_map": dict(ROLE_MAP),
        "expected_commitment_enum": expected,
        "task_body": task_body,
        **_trigger_fields(
            source_reference=source_reference,
            decision_scope=decision_scope,
        ),
    }


def make_irrelevant_fixture(
    *,
    fixture_id: str,
    block_id: str,
    expected: str = "delta_hold",
    task_body: str | None = None,
    decision_scope: str | None = None,
) -> dict[str, Any]:
    if task_body is None:
        task_body = (
            f"Observation-only record for block {block_id}. "
            "Pick the listed response label."
        )
    if decision_scope is None:
        decision_scope = decision_scope_for_block(0)
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
        "task_body": task_body,
        **_trigger_fields(
            source_reference="",
            decision_scope=decision_scope,
        ),
    }


def make_block(block_index: int) -> list[dict[str, Any]]:
    bid = f"block-{block_index:04d}"
    dim = SCOPE_DIMENSIONS[block_index % len(SCOPE_DIMENSIONS)]
    orientation = "A" if block_index % 2 == 0 else "B"
    lexical_tail = (
        "partial gap miss noted."
        if block_index % 2 == 0
        else "covers complete noted."
    )
    shared_task = (
        f"Review operational ticket for block {bid}. "
        f"Choose one response label from the menu. {lexical_tail}"
    )
    shared_scope = decision_scope_for_block(block_index)
    match_handle = expected_opaque_source_handle(bid, orientation)
    mismatch_handle = expected_opaque_source_handle(
        bid,
        complementary_handle_orientation(orientation),
    )
    return [
        make_relevant_fixture(
            fixture_id=f"{bid}-match",
            block_id=bid,
            stratum="match",
            scope_bit="covers",
            missing_scope_dimension=dim,
            handle_orientation=orientation,
            opaque_source_handle=match_handle,
            task_body=shared_task,
            source_reference=expected_source_reference(match_handle),
            decision_scope=shared_scope,
        ),
        make_relevant_fixture(
            fixture_id=f"{bid}-mismatch",
            block_id=bid,
            stratum="mismatch",
            scope_bit="misses",
            missing_scope_dimension=dim,
            handle_orientation=orientation,
            opaque_source_handle=mismatch_handle,
            task_body=shared_task,
            source_reference=expected_source_reference(mismatch_handle),
            decision_scope=shared_scope,
        ),
        make_irrelevant_fixture(
            fixture_id=f"{bid}-irrelevant",
            block_id=bid,
            task_body=shared_task,
            decision_scope=shared_scope,
        ),
    ]


def make_minimal_suite(block_count: int = 1) -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    for i in range(block_count):
        fixtures.extend(make_block(i))
    return fixtures


def make_minimal_record_store(
    fixtures: list[dict[str, Any]] | None = None,
):
    """Authoritative store aligned to the synthetic wire suite."""
    if fixtures is None:
        fixtures = make_minimal_suite(1)
    return build_record_store_from_fixtures(fixtures)
