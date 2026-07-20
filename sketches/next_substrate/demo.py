"""Run the NEXT substrate embodiment sketch across four invocation seams."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from .runtime import BodyRuntime, EVIDENCE_CLASS, Task


FAILURE_TASK = Task(
    task_id="wake-1-research-source",
    domain="research",
    assertion_kind="source_assertion",
    observation_boundary="absent",
    source_scope="publisher_summary",
    required_scope="current_world_state",
    expected_action="defer",
)

TRANSFER_TASK = Task(
    task_id="wake-2-operations-source",
    domain="operations",
    assertion_kind="source_assertion",
    observation_boundary="absent",
    source_scope="vendor_claim",
    required_scope="observed_deployment_state",
    expected_action="defer",
)

SILENT_TASK = Task(
    task_id="wake-3-direct-observation",
    domain="maintenance",
    assertion_kind="direct_observation",
    observation_boundary="present",
    source_scope="observed_machine_state",
    required_scope="observed_machine_state",
    expected_action="commit",
)

POST_REVISION_TASK = Task(
    task_id="wake-4-after-warrant-revision",
    domain="finance",
    assertion_kind="source_assertion",
    observation_boundary="absent",
    source_scope="analyst_claim",
    required_scope="audited_current_state",
    expected_action="defer",
)


def run_demo(lineage_path: Path) -> dict[str, Any]:
    """Execute, reload between wakes, and return a compact demonstration summary."""
    first_runtime = BodyRuntime(lineage_path)
    first = first_runtime.wake(FAILURE_TASK)
    disposition_id = "disp-epistemic-frame-001"
    first_runtime.activate_stub_disposition(
        disposition_id=disposition_id,
        warrant_event_ids=[first.consequence_event_id],
    )

    second_runtime = BodyRuntime(lineage_path)  # reawaken from disk lineage
    transfer = second_runtime.wake(TRANSFER_TASK)
    probe = second_runtime.record_wire_causal_probe(
        disposition_id=disposition_id,
        task=TRANSFER_TASK,
        treated=transfer,
    )

    third_runtime = BodyRuntime(lineage_path)  # another cold materialization
    silent = third_runtime.wake(SILENT_TASK)
    suspended = third_runtime.revise_warrant(
        warrant_event_id=first.consequence_event_id,
        reason="demo external observer retracts the original failure warrant",
    )

    fourth_runtime = BodyRuntime(lineage_path)
    post_revision = fourth_runtime.wake(POST_REVISION_TASK)
    fourth_runtime.record_materialized_view_claim()
    replay = fourth_runtime.lineage.replay()
    final_state = fourth_runtime.state()

    return {
        "evidence_class": EVIDENCE_CLASS,
        "claim_boundary": "composition only; no language-model memory finding",
        "lineage_path": str(lineage_path),
        "phases": {
            "failure_before_disposition": _result(first),
            "cross_domain_transfer": _result(transfer),
            "non_matching_task_is_silent": _result(silent),
            "after_external_warrant_revision": _result(post_revision),
        },
        "wire_causal_probe": {
            "effect": probe["payload"]["effect"],
            "warning": probe["payload"]["warning"],
        },
        "suspended_disposition_ids": suspended,
        "materialized_dispositions": {
            did: {
                "status": disposition.status,
                "metabolic_counts": disposition.metabolic_counts,
            }
            for did, disposition in final_state.dispositions.items()
        },
        "body_core": {
            "view_digest": replay.views.digest(),
            "verified_view_claim_ids": list(replay.verified_view_claim_ids),
            "warrant_health": replay.views.warrant_health,
        },
        "lineage_rows": len(replay.rows),
    }


def _result(result) -> dict[str, Any]:
    return {
        "action": result.action,
        "score": result.score,
        "fired_disposition_ids": list(result.fired_disposition_ids),
        "check_evidence": list(result.check_evidence),
    }


def render(summary: dict[str, Any]) -> str:
    lines = [
        "NEXT substrate embodiment sketch",
        "EVIDENCE: WIRE / INTEGRATION ONLY — AUTHORED DETERMINISTIC BEHAVIOR",
        "",
    ]
    for name, phase in summary["phases"].items():
        fired = ",".join(phase["fired_disposition_ids"]) or "none"
        lines.append(
            f"{name}: action={phase['action']} score={phase['score']:.1f} "
            f"disposition={fired} checks={len(phase['check_evidence'])}"
        )
    lines.extend([
        "",
        f"wire causal probe: {summary['wire_causal_probe']['effect']} "
        "(authored; not evidence)",
        f"suspended after warrant revision: "
        f"{','.join(summary['suspended_disposition_ids']) or 'none'}",
        f"lineage rows: {summary['lineage_rows']}",
        f"lineage: {summary['lineage_path']}",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state-dir",
        type=Path,
        help="empty directory to retain the wire-only lineage (default: temporary)",
    )
    parser.add_argument("--json", action="store_true", help="print JSON summary")
    args = parser.parse_args()

    if args.state_dir is not None:
        args.state_dir.mkdir(parents=True, exist_ok=True)
        lineage_path = args.state_dir / "lineage.jsonl"
        if lineage_path.exists() and lineage_path.stat().st_size:
            raise SystemExit(f"refusing to append a second demo to {lineage_path}")
        summary = run_demo(lineage_path)
        print(json.dumps(summary, indent=2, sort_keys=True) if args.json else render(summary))
        return

    with tempfile.TemporaryDirectory(prefix="next-substrate-sketch-") as td:
        summary = run_demo(Path(td) / "lineage.jsonl")
        print(json.dumps(summary, indent=2, sort_keys=True) if args.json else render(summary))


if __name__ == "__main__":
    main()
