"""Wire tests for the non-evidentiary NEXT substrate walking skeleton.

Run:
  UV_CACHE_DIR=/private/tmp/uv-cache uv run --no-project \
    python -m tests.test_next_substrate_sketch
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from sketches.next_substrate.demo import run_demo
from sketches.next_substrate.runtime import BodyRuntime, EVIDENCE_CLASS, Task


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def test_full_demo_traverses_the_body():
    with TemporaryDirectory() as td:
        lineage = Path(td) / "lineage.jsonl"
        summary = run_demo(lineage)
        phases = summary["phases"]

        assert summary["evidence_class"] == EVIDENCE_CLASS
        assert phases["failure_before_disposition"]["score"] == 0.0
        assert phases["cross_domain_transfer"]["score"] == 1.0
        assert phases["cross_domain_transfer"]["fired_disposition_ids"]
        assert phases["non_matching_task_is_silent"]["score"] == 1.0
        assert phases["non_matching_task_is_silent"]["fired_disposition_ids"] == []
        assert phases["after_external_warrant_revision"]["score"] == 0.0
        assert phases["after_external_warrant_revision"]["fired_disposition_ids"] == []
        assert summary["suspended_disposition_ids"] == ["disp-epistemic-frame-001"]
        print("ok  demo: failure -> transfer -> silence -> external suspension")


def test_lineage_is_append_only_and_replayable():
    with TemporaryDirectory() as td:
        lineage = Path(td) / "lineage.jsonl"
        summary = run_demo(lineage)
        rows = _rows(lineage)

        assert [row["event_index"] for row in rows] == list(range(1, len(rows) + 1))
        assert [row["event_id"] for row in rows] == [
            f"ev-{i:04d}" for i in range(1, len(rows) + 1)
        ]
        assert all(row["evidence_class"] == EVIDENCE_CLASS for row in rows)
        assert summary["lineage_rows"] == len(rows)

        reloaded = BodyRuntime(lineage).state()
        disposition = reloaded.dispositions["disp-epistemic-frame-001"]
        assert disposition.status == "suspended"
        assert disposition.metabolic_counts == {"check_executed": 1, "helped": 1}
        print("ok  lineage: ordered append + cold replay rebuilds final state")


def test_required_check_is_on_the_action_boundary():
    with TemporaryDirectory() as td:
        lineage = Path(td) / "lineage.jsonl"
        run_demo(lineage)
        rows = _rows(lineage)
        start = next(
            row for row in rows
            if row["kind"] == "invocation_started"
            and row["task_id"] == "wake-2-operations-source"
        )
        kinds = [
            row["kind"] for row in rows
            if row.get("invocation_id") == start["event_id"]
        ]

        assert kinds.index("activation_field_built") < kinds.index("action_boundary_entered")
        assert kinds.index("action_boundary_entered") < kinds.index("controller_check_executed")
        assert kinds.index("controller_check_executed") < kinds.index("model_action")
        print("ok  placement: offer phase -> action boundary -> check -> model action")


def test_model_failure_cannot_activate_a_disposition_without_external_warrant():
    task = Task(
        task_id="unwarranted",
        domain="test",
        assertion_kind="source_assertion",
        observation_boundary="absent",
        source_scope="claim",
        required_scope="world",
        expected_action="defer",
    )
    with TemporaryDirectory() as td:
        runtime = BodyRuntime(Path(td) / "lineage.jsonl")
        runtime.wake(task)
        try:
            runtime.activate_stub_disposition(
                disposition_id="bad",
                warrant_event_ids=["ev-does-not-exist"],
            )
        except ValueError as exc:
            assert "resolve in lineage" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("unresolved warrant activated a disposition")
        print("ok  authority: unresolved model-side claim cannot activate state")


def test_successful_outcome_cannot_warrant_a_failure_disposition():
    task = Task(
        task_id="successful",
        domain="test",
        assertion_kind="direct_observation",
        observation_boundary="present",
        source_scope="observed",
        required_scope="observed",
        expected_action="commit",
    )
    with TemporaryDirectory() as td:
        runtime = BodyRuntime(Path(td) / "lineage.jsonl")
        result = runtime.wake(task)
        assert result.score == 1.0
        try:
            runtime.activate_stub_disposition(
                disposition_id="bad-success-scar",
                warrant_event_ids=[result.consequence_event_id],
            )
        except ValueError as exc:
            assert "scored failure" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("successful outcome minted a failure disposition")
        print("ok  authority: successful outcome cannot warrant a failure scar")


def test_provenance_revision_suspends_on_replay_even_before_projection_row():
    task = Task(
        task_id="failure-for-revision",
        domain="test",
        assertion_kind="source_assertion",
        observation_boundary="absent",
        source_scope="claim",
        required_scope="world",
        expected_action="defer",
    )
    with TemporaryDirectory() as td:
        runtime = BodyRuntime(Path(td) / "lineage.jsonl")
        result = runtime.wake(task)
        runtime.activate_stub_disposition(
            disposition_id="revision-target",
            warrant_event_ids=[result.consequence_event_id],
        )
        runtime.lineage.append(
            "provenance_revision",
            target_event_id=result.consequence_event_id,
            reason="simulated interruption before projection row",
            writer="external_provenance_sweep_stub",
        )

        reloaded = BodyRuntime(runtime.lineage.path).state()
        assert reloaded.dispositions["revision-target"].status == "suspended"
        print("ok  provenance: revision event fails safe on cold replay")


if __name__ == "__main__":
    tests = sorted(
        (name, fn)
        for name, fn in globals().items()
        if name.startswith("test_") and callable(fn)
    )
    for _, fn in tests:
        fn()
    print(f"\nALL {len(tests)} NEXT SUBSTRATE SKETCH TESTS PASS")
