"""Body-0 admission, composition, replay, and tamper tests.

Mock execution proves the complete wire only.  The tests intentionally mutate
copied ledgers to show that logged costs, protected projections, oracle rows,
and pre-action contracts cannot manufacture a positive composition verdict.
"""

from __future__ import annotations

import json
import tempfile
from functools import lru_cache
from pathlib import Path
from unittest.mock import patch

from harness.body0 import Body0ContractError
from harness.check_body0_fixture import DEFAULT_MANIFEST, gate_result, manifest_hash
from harness.run_body0 import run_body0
from harness.runner import Episode
from harness.score_body0 import append_body0_verdicts, score_body0


@lru_cache(maxsize=1)
def _run() -> Path:
    return run_body0(
        DEFAULT_MANIFEST,
        engine_backend="mock",
        model="mock-engine-v1",
        runs_dir=Path(tempfile.mkdtemp()),
    )


def _cells(path: Path) -> dict[str, dict]:
    return {row["cell"]: row for row in score_body0(path)}


def _tamper(path: Path, mutate) -> Path:
    rows = [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    mutate(rows)
    target = Path(tempfile.mkdtemp()) / "tampered.body0.jsonl"
    target.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return target


def test_fixture_gate():
    gate = gate_result(DEFAULT_MANIFEST)
    assert gate["gate_open"], [
        check for check in gate["checks"] if not check["ok"]
    ]
    cost = next(
        check for check in gate["checks"]
        if check["check"] == "cost_state_dependence"
    )
    assert '"cost_C": 254' in cost["detail"]
    assert '"cost_R": 428' in cost["detail"]
    print("ok  Body-0 fixture: frozen P/P/P/U packet opens with strict cost margin")


def test_real_probe_backend_receipt_binding():
    model = "candidate-model"
    probe = {
        "manifest_sha256": manifest_hash(DEFAULT_MANIFEST),
        "engine_backend": "local_openai_compat",
        "model": model,
        "wire_only": False,
        "decision": "cite",
        "knew_current": False,
    }
    gate = gate_result(
        DEFAULT_MANIFEST,
        probe_result=probe,
        engine_backend="local",
        model=model,
    )
    assert gate["gate_open"], [
        check for check in gate["checks"] if not check["ok"]
    ]
    assert gate["engine_backend"] == "local_openai_compat"
    assert gate["engine_backend_cli"] == "local"
    print("ok  Body-0 admission: CLI backend binds the engine receipt name")


def test_wire_composition():
    cells = _cells(_run())
    holds = cells["B0-composition-holds"]
    assert holds["verdict"] == "wire_pass", holds
    assert holds["earned_ablation_engaged"], holds
    assert holds["recovery_ablation_engaged"], holds
    assert holds["protected_projection_ok"], holds
    assert holds["hot_state_replay_ok"] and holds["cost_replay_ok"], holds
    assert holds["cost_hot_tokens"]["B0-C"] < holds["cost_hot_tokens"]["B0-R"]
    for cell in (
        "B0-authority-regression",
        "B0-recovery-regression",
        "B0-quality-regression",
        "B0-attribution-confounded",
        "B0-pure-tax",
        "B0-interface-blocked",
    ):
        assert cells[cell]["verdict"] == "not_engaged", cells[cell]
    print("ok  Body-0 wire: dual engagement + protected projection + replayed cost")


def test_logged_cost_tamper_confounds():
    def mutate(rows):
        row = next(r for r in rows if r["kind"] == "body0_hot_store_cost")
        row["hot_tokens"] += 1

    cells = _cells(_tamper(_run(), mutate))
    assert cells["B0-composition-holds"]["verdict"] == "confounded"
    assert cells["B0-attribution-confounded"]["verdict"] == "pass"
    assert "cost_replay_mismatch" in cells["B0-composition-holds"]["confound_reasons"]
    print("ok  Body-0 replay: logged cost tamper cannot manufacture a win")


def test_projection_tamper_fires_regression():
    def mutate(rows):
        row = next(
            r for r in rows
            if r["kind"] == "body0_protected_projection"
            and r["stage"] == "post_attack"
        )
        row["projection"]["authority_seed"][row["projection"]["earned_record_id"]] = 1.5

    cells = _cells(_tamper(_run(), mutate))
    assert cells["B0-composition-holds"]["verdict"] == "fail"
    assert cells["B0-authority-regression"]["verdict"] == "pass"
    print("ok  Body-0 M3: changed protected projection fires authority regression")


def test_oracle_tamper_confounds():
    def mutate(rows):
        recurrence = next(
            r for r in rows
            if r["kind"] == "body0_run_meta"
        )["sequence_run_ids"][-1]
        row = next(
            r for r in rows
            if r["kind"] == "branch_run"
            and r["run_id"] == recurrence
            and r["branch_id"] == "B0-A"
        )
        row["oracle"]["score"] = 1.0

    cells = _cells(_tamper(_run(), mutate))
    assert cells["B0-composition-holds"]["verdict"] == "confounded"
    assert "oracle_replay_mismatch" in cells["B0-composition-holds"]["confound_reasons"]
    print("ok  Body-0 oracle: scorer recomputes answers against the frozen oracle")


def test_missing_preaction_projection_confounds():
    def mutate(rows):
        index = next(
            i for i, row in enumerate(rows)
            if row["kind"] == "prune_projection"
        )
        rows.pop(index)

    cells = _cells(_tamper(_run(), mutate))
    assert cells["B0-composition-holds"]["verdict"] == "confounded"
    assert "hot_operation_integrity_failed" in cells["B0-composition-holds"]["confound_reasons"]
    print("ok  Body-0 X2: operation without its earlier projection fails closed")


def test_recovery_regression_fires():
    def mutate(rows):
        op = next(
            row for row in rows
            if row["kind"] == "rematerialize" and row["branch_id"] == "B0-C"
        )
        rows.remove(op)
        projection = next(
            row for row in rows
            if row["kind"] == "prune_projection"
            and row["branch_id"] == "B0-C"
            and row["event_index"] == op["event_index"]
        )
        rows.remove(projection)

    cells = _cells(_tamper(_run(), mutate))
    assert cells["B0-recovery-regression"]["verdict"] == "pass"
    assert cells["B0-composition-holds"]["verdict"] == "confounded"
    print("ok  Body-0 recovery: missing C rematerialization fires the regression cell")


def test_quality_regression_fires_after_engagement():
    recurrence_path = json.loads(DEFAULT_MANIFEST.read_text())["recurrence"]
    recurrence = Episode.load(
        DEFAULT_MANIFEST.parents[3] / recurrence_path
    )

    def mutate(rows):
        recurrence_run = next(
            row for row in rows if row["kind"] == "body0_run_meta"
        )["sequence_run_ids"][-1]
        branch = next(
            row for row in rows
            if row["kind"] == "branch_run"
            and row["run_id"] == recurrence_run
            and row["branch_id"] == "B0-C"
        )
        branch["branch_output"]["answer"] = "I do not know."
        branch["oracle"] = recurrence.score("I do not know.").__dict__

    cells = _cells(_tamper(_run(), mutate))
    assert cells["B0-quality-regression"]["verdict"] == "pass"
    assert cells["B0-quality-regression"]["causal_paths_changed"]
    assert cells["B0-composition-holds"]["verdict"] == "fail"
    print("ok  Body-0 quality: engaged C below R fires quality regression")


def test_direction_blind_ablation_is_not_engaged():
    recurrence_path = json.loads(DEFAULT_MANIFEST.read_text())["recurrence"]
    recurrence = Episode.load(DEFAULT_MANIFEST.parents[3] / recurrence_path)

    def mutate(rows):
        recurrence_run = next(
            row for row in rows if row["kind"] == "body0_run_meta"
        )["sequence_run_ids"][-1]
        for row in rows:
            if row.get("kind") != "branch_run" or row.get("run_id") != recurrence_run:
                continue
            if row["branch_id"] in {"B0-R", "B0-C"}:
                answer = ""
            else:
                answer = "decline"
            row["branch_output"]["answer"] = answer
            row["oracle"] = recurrence.score(answer).__dict__

    cells = _cells(_tamper(_run(), mutate))
    holds = cells["B0-composition-holds"]
    assert holds["verdict"] == "not_engaged", holds
    assert not holds["reference_and_composed_correct"], holds
    assert holds["causal_paths_changed"] and not holds["earned_ablation_engaged"], holds
    assert cells["B0-attribution-confounded"]["verdict"] == "pass"
    print("ok  Body-0 direction: ablations beating failed R/C are not engagement")


def test_versioned_rescore_preserves_legacy_rows():
    source = _run()
    target = Path(tempfile.mkdtemp()) / "legacy.body0.jsonl"
    target.write_bytes(source.read_bytes())
    from harness.ledger import Ledger

    ledger = Ledger(target)
    legacy = score_body0(target)
    for verdict in legacy:
        verdict = dict(verdict)
        verdict.pop("scorer_version")
        ledger.write(verdict)
    legacy_rows = [
        row for row in ledger.rows()
        if row.get("kind") == "cell_verdict"
        and row.get("scorer") == "score_body0"
    ]
    verdicts, correction = append_body0_verdicts(target)
    rows = ledger.rows()
    assert correction is not None
    assert len(correction["superseded_verdicts"]) == len(legacy_rows)
    assert all(row in rows for row in legacy_rows)
    assert all(v["scorer_version"] == "0.2" for v in verdicts)
    print("ok  Body-0 append-only: v0.2 supersedes without rewriting v0.1")


def test_pure_tax_fires_if_composed_state_never_cools():
    def mutate(rows):
        event_ids = {
            row["event_index"] for row in rows
            if row["kind"] in {"prune", "rematerialize"}
            and row["branch_id"] == "B0-C"
        }
        rows[:] = [
            row for row in rows
            if not (
                row.get("branch_id") == "B0-C"
                and (
                    row.get("kind") in {"prune", "rematerialize"}
                    or (
                        row.get("kind") == "prune_projection"
                        and row.get("event_index") in event_ids
                    )
                )
            )
        ]

    cells = _cells(_tamper(_run(), mutate))
    assert cells["B0-pure-tax"]["verdict"] == "pass"
    assert cells["B0-composition-holds"]["verdict"] == "confounded"
    print("ok  Body-0 cost: composed path with no savings fires pure-tax")


def test_adapter_policy_effect_fires_interface_block():
    def mutate(rows):
        row = next(r for r in rows if r["kind"] == "body0_adapter_receipt")
        row["policy_effects"] = ["semantic_classifier"]
        row["identity_ok"] = False

    cells = _cells(_tamper(_run(), mutate))
    assert cells["B0-composition-holds"]["verdict"] == "fail"
    assert cells["B0-interface-blocked"]["verdict"] == "pass"
    print("ok  Body-0 interface: policy-bearing adapter closes the composition")


def test_real_run_refuses_before_contact_without_probe():
    with patch(
        "harness.run_body0.run_fork_group",
        side_effect=AssertionError("engine contact occurred before admission"),
    ):
        try:
            run_body0(
                DEFAULT_MANIFEST,
                engine_backend="local",
                model="unprobed-model",
                runs_dir=Path(tempfile.mkdtemp()),
            )
        except Body0ContractError as exc:
            assert "before engine contact" in str(exc)
        else:
            raise AssertionError("unprobed real run was admitted")
    print("ok  Body-0 admission: unprobed real engine is refused before contact")


if __name__ == "__main__":
    tests = sorted(
        (name, fn)
        for name, fn in globals().items()
        if name.startswith("test_") and callable(fn)
    )
    for _, test in tests:
        test()
    print(f"\nALL {len(tests)} BODY-0 TESTS PASS (mock wire only)")
