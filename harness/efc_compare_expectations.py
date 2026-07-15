"""Test-layer oracle expectations for production conformance — never read by interpreter."""

from __future__ import annotations

import json
from pathlib import Path

from harness.efc_compare_inputs import DISPOSITIVE_TASKS, ORACLE_ROOT

REPO = Path(__file__).resolve().parent.parent
EXPECTATIONS_PATH = REPO / "corpus/efc_calibration/authoring_c2" / \
    "comparison_expectations_v1.json"


def build_expectations() -> dict:
    rows = []
    for task_id in DISPOSITIVE_TASKS:
        oracle = json.loads((ORACLE_ROOT / f"{task_id}.json").read_text())
        rows.append({
            "task_id": task_id,
            "source_reference": oracle["source_reference"],
            "expected_scope_matches": oracle["expected_scope_matches"],
        })
    return {
        "schema_version": "efc-comparison-expectations-v1",
        "note": ("test-layer only; production interpreter must not read this"),
        "row_count": len(rows),
        "rows": rows,
    }


def write_expectations(path: Path | None = None) -> Path:
    path = path or EXPECTATIONS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_expectations(), sort_keys=True, indent=1)
                    + "\n")
    return path
