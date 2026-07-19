"""Body-1 packet, runtime, wire, replay, and tamper tests.

The mock sequence proves implementation wiring only. It cannot support a
behavioral or memory claim.
"""

from __future__ import annotations

import json
import tempfile
from functools import lru_cache
from pathlib import Path
from unittest.mock import patch

from harness.body1 import (
    BRANCH_A,
    BRANCH_C,
    BRANCH_L1,
    BRANCH_R,
    BRANCH_X,
    ENDORSED_PACKET_INDEX_SHA256,
    FORM_BARE,
    FORM_NONBINDING,
    Body1ContractError,
    classify_expression,
    derive_scope,
    execute_packet_form,
    fixture,
    packet_index_sha256,
    runtime_row,
    scope_matches_declared,
)
from harness.check_body1_fixture import gate_result
from harness.probe_body1 import run_probe
from harness.run_body1 import run_body1
from harness.score_body1 import append_body1_verdicts, score_body1


@lru_cache(maxsize=1)
def _run() -> Path:
    return run_body1(
        engine_backend="mock",
        model="mock-engine-v1",
        runs_dir=Path(tempfile.mkdtemp()),
    )


def _cells(path: Path) -> dict[str, dict]:
    return {row["cell"]: row for row in score_body1(path)}


def _tamper(path: Path, mutate) -> Path:
    rows = [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    mutate(rows)
    target = Path(tempfile.mkdtemp()) / "tampered.body1.jsonl"
    target.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return target


def _replace_action(rows: list[dict], run_id: str, branch_id: str, form: str) -> None:
    action = next(
        row for row in rows
        if row.get("kind") == "body1_action"
        and row.get("run_id") == run_id
        and row.get("branch_id") == branch_id
    )
    current = fixture(
        "recurrence"
        if action["episode_id"] == "b1-u-unit-key"
        else "scope_loses"
    )
    raw = current["packet_expressions"][form]
    selection = classify_expression(raw, current)
    action.update({
        "raw_answer": raw,
        "raw_answer_sha256": selection.raw_sha256,
        "selection_status": selection.status,
        "selected_form": selection.form,
        "selection_refusal": selection.refusal,
    })
    runtime = next(
        row for row in rows
        if row.get("kind") == "body1_subprocess_result"
        and row.get("run_id") == run_id
        and row.get("branch_id") == branch_id
    )
    preserved = {
        key: runtime[key]
        for key in ("ts", "kind", "run_id", "fork_group_id", "branch_id", "role")
    }
    runtime.clear()
    runtime.update(preserved)
    runtime.update(runtime_row(execute_packet_form(current, form)))


def test_packet_gate():
    gate = gate_result()
    assert packet_index_sha256() == ENDORSED_PACKET_INDEX_SHA256
    assert gate["gate_open"], [
        check for check in gate["checks"] if not check["ok"]
    ]
    assert any(
        check["check"] == "address_space_target"
        and check["ok"]
        for check in gate["checks"]
    )
    print("ok  Body-1 gate: exact packet, review, runtime, renderer, and cost bind")


def test_closed_expression_parser():
    current = fixture("recurrence")
    for form in (FORM_BARE, FORM_NONBINDING):
        selected = classify_expression(current["packet_expressions"][form], current)
        assert selected.status == "selected" and selected.form == form
    rejected = [
        'factory(partial(unit_key, "unit:"))',
        'functools.partial(unit_key, "unit:")',
        'partial(unit_key, prefix="unit:")',
        'partial(unit_key, "unit:") because',
        'lambda: partial(unit_key, "unit:")',
        "x" * 257,
    ]
    assert all(classify_expression(raw, current).form is None for raw in rejected)
    print("ok  Body-1 parser: only two exact AST forms select authored source")


def test_scope_derivation():
    expected = {
        "surface_control": 1,
        "ignorance_probe": 0,
        "e1_failure": 0,
        "residence": 1,
        "recurrence": 0,
        "scope_loses": 1,
    }
    for name, slot in expected.items():
        current = fixture(name)
        derived = derive_scope(current)
        assert derived.descriptor_slot == slot
        assert scope_matches_declared(current, derived)
    print("ok  Body-1 scope: arity relation is recomputed from source")


def test_runtime_directions():
    expected = {
        "surface_control": ("pass", "TypeError"),
        "ignorance_probe": ("TypeError", "pass"),
        "e1_failure": ("TypeError", "pass"),
        "residence": ("pass", "TypeError"),
        "recurrence": ("TypeError", "pass"),
        "scope_loses": ("pass", "TypeError"),
    }
    for name, outcomes in expected.items():
        current = fixture(name)
        observed = tuple(
            execute_packet_form(current, form).outcome
            for form in (FORM_BARE, FORM_NONBINDING)
        )
        assert observed == outcomes
    print("ok  Body-1 runtime: all twelve frozen directions reproduce")


def test_wire_composition():
    cells = _cells(_run())
    holds = cells["B1-composition-holds"]
    assert holds["verdict"] == "wire_pass", holds
    assert holds["runtime_replay_ok"] and holds["raw_execution_boundary_ok"]
    assert holds["reference_and_composed_pass"]
    assert holds["offer_ablation_fails"] and holds["recovery_ablation_fails"]
    assert holds["cost_hot_tokens"][BRANCH_C] < holds["cost_hot_tokens"][BRANCH_R]
    assert cells["B1-scope-refusal"]["verdict"] == "wire_pass"
    assert cells["B1-governance-should-lose"]["verdict"] == "wire_pass"
    for cell in (
        "B1-attribution-confounded",
        "B1-authority-regression",
        "B1-recovery-regression",
        "B1-quality-regression",
        "B1-pure-tax",
        "B1-interface-blocked",
    ):
        assert cells[cell]["verdict"] == "not_engaged", cells[cell]
    print("ok  Body-1 wire: executable R/C/A/X and both loses cells engage")


def test_real_run_refuses_before_engine_construction():
    with patch(
        "harness.run_body1.Body1Engine",
        side_effect=AssertionError("engine constructed before admission"),
    ):
        try:
            run_body1(
                engine_backend="local",
                model="unprobed-model",
                runs_dir=Path(tempfile.mkdtemp()),
            )
        except Body1ContractError as exc:
            assert "before engine contact" in str(exc)
        else:
            raise AssertionError("unprobed real engine was admitted")
    print("ok  Body-1 admission: unprobed real engine is refused before contact")


def test_excluded_probe_refuses_before_engine_construction():
    with patch(
        "harness.probe_body1.Body1Engine",
        side_effect=AssertionError("excluded engine constructed"),
    ):
        try:
            run_probe(engine_backend="mock", model="composer-2.5")
        except ValueError as exc:
            assert "excluded" in str(exc)
        else:
            raise AssertionError("review seat entered admission probe")
    print("ok  Body-1 exclusion: review seats stop before client construction")


def test_logged_cost_tamper_confounds():
    def mutate(rows):
        row = next(
            row for row in rows if row["kind"] == "body1_hot_store_cost"
        )
        row["hot_tokens"] += 1

    cells = _cells(_tamper(_run(), mutate))
    assert cells["B1-composition-holds"]["verdict"] == "confounded"
    assert "cost_replay_failed" in cells["B1-composition-holds"]["confound_reasons"]
    print("ok  Body-1 replay: logged cost cannot manufacture a result")


def test_selected_form_tamper_confounds():
    def mutate(rows):
        row = next(row for row in rows if row["kind"] == "body1_action")
        row["selected_form"] = FORM_NONBINDING

    cells = _cells(_tamper(_run(), mutate))
    assert cells["B1-composition-holds"]["verdict"] == "confounded"
    assert "expression_or_runtime_replay_failed" in (
        cells["B1-composition-holds"]["confound_reasons"]
    )
    print("ok  Body-1 replay: selected-form claims are untrusted")


def test_raw_execution_flag_blocks_interface():
    def mutate(rows):
        row = next(row for row in rows if row["kind"] == "body1_action")
        row["model_bytes_executed"] = True

    cells = _cells(_tamper(_run(), mutate))
    assert cells["B1-interface-blocked"]["verdict"] == "pass"
    assert cells["B1-composition-holds"]["verdict"] == "confounded"
    print("ok  Body-1 boundary: any raw execution closes the interface")


def test_projection_tamper_fires_authority_regression():
    def mutate(rows):
        row = next(
            row for row in rows
            if row["kind"] == "body1_protected_projection"
            and row["stage"] == "post_attack"
        )
        earned_id = row["projection"]["earned_record_id"]
        row["projection"]["authority_seed"][earned_id] = 2.0

    cells = _cells(_tamper(_run(), mutate))
    assert cells["B1-authority-regression"]["verdict"] == "pass"
    assert cells["B1-composition-holds"]["verdict"] == "fail"
    print("ok  Body-1 authority: attacker-visible projection mutation fires")


def test_missing_recovery_fires_regression():
    def mutate(rows):
        operation = next(
            row for row in rows
            if row["kind"] == "rematerialize" and row["branch_id"] == BRANCH_C
        )
        rows.remove(operation)
        projection = next(
            row for row in rows
            if row["kind"] == "prune_projection"
            and row["branch_id"] == BRANCH_C
            and row["event_index"] == operation["event_index"]
        )
        rows.remove(projection)

    cells = _cells(_tamper(_run(), mutate))
    assert cells["B1-recovery-regression"]["verdict"] == "pass"
    assert cells["B1-composition-holds"]["verdict"] == "confounded"
    print("ok  Body-1 recovery: missing rematerialization is not hidden")


def test_direction_blind_shape_is_not_engaged():
    def mutate(rows):
        recurrence_run = next(
            row for row in rows if row["kind"] == "body1_run_meta"
        )["sequence_run_ids"][-1]
        for branch in (BRANCH_R, BRANCH_C):
            _replace_action(rows, recurrence_run, branch, FORM_BARE)
        for branch in (BRANCH_A, BRANCH_X):
            _replace_action(rows, recurrence_run, branch, FORM_NONBINDING)

    cells = _cells(_tamper(_run(), mutate))
    assert cells["B1-composition-holds"]["verdict"] == "not_engaged"
    assert cells["B1-attribution-confounded"]["verdict"] == "pass"
    assert not cells["B1-composition-holds"]["reference_and_composed_pass"]
    print("ok  Body-1 direction: A/X success cannot rescue failed R/C")


def test_scope_null_is_honest():
    def mutate(rows):
        scope_run = next(
            row for row in rows if row["kind"] == "body1_run_meta"
        )["scope_run_id"]
        _replace_action(rows, scope_run, BRANCH_L1, FORM_BARE)

    cells = _cells(_tamper(_run(), mutate))
    assert cells["B1-scope-refusal"]["verdict"] == "not_engaged"
    assert cells["B1-governance-should-lose"]["verdict"] == "wire_pass"
    print("ok  Body-1 scope: ignored bad offer yields an honest null")


def test_append_verdicts():
    target = Path(tempfile.mkdtemp()) / "append.body1.jsonl"
    target.write_bytes(_run().read_bytes())
    verdicts = append_body1_verdicts(target)
    appended = [
        json.loads(line)
        for line in target.read_text().splitlines()
        if '"scorer": "score_body1"' in line
    ]
    assert len(appended) == len(verdicts) == 9
    assert appended[0]["cell"] == "B1-composition-holds"
    print("ok  Body-1 ledger: computed verdicts append without rewriting")


if __name__ == "__main__":
    tests = sorted(
        (name, function)
        for name, function in globals().items()
        if name.startswith("test_") and callable(function)
    )
    for _, test in tests:
        test()
    print(f"\nALL {len(tests)} BODY-1 TESTS PASS (mock wire only)")
