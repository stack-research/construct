"""Fail-closed checker for the frontier-obligation admission packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .frontier_obligation_admission import (
    Check,
    PROPOSAL_REVIEW_SHA256,
    ROOT,
    evaluate_receipt,
    file_sha256,
    packet_checks,
)
from .probe_frontier_obligation_admission import (
    IMPLEMENTATION_MANIFEST,
    atomic_write_new,
    verify_execution_pin,
)


PROPOSAL_REVIEW_THREAD = (
    ROOT / ".substrate" / "threads" / "frontier-obligation-admission-review"
)


def proposal_review_checks() -> list[Check]:
    config = PROPOSAL_REVIEW_THREAD / "config.yaml"
    config_text = config.read_text() if config.is_file() else ""
    checks = [
        Check(
            "proposal_review_ended",
            "status: ended" in config_text
            and PROPOSAL_REVIEW_SHA256 in config_text,
            f"thread={PROPOSAL_REVIEW_THREAD.relative_to(ROOT)}",
        )
    ]
    for participant in ("cursor%2Fgrok-4.5", "cursor%2Fcomposer-2.5"):
        entries = list(PROPOSAL_REVIEW_THREAD.glob(f"*__{participant}.md"))
        text = entries[0].read_text() if len(entries) == 1 else ""
        checks.append(Check(
            f"proposal_review_{participant}",
            len(entries) == 1
            and PROPOSAL_REVIEW_SHA256 in text
            and ("**ENDORSE**" in text or "## ENDORSE" in text),
            f"entries={len(entries)}",
        ))
    moderator = [
        path
        for path in PROPOSAL_REVIEW_THREAD.glob("*__codex.md")
        if "proposal gate **ENDORSED**" in path.read_text()
    ]
    checks.append(Check(
        "proposal_review_moderator_close",
        len(moderator) == 1 and PROPOSAL_REVIEW_SHA256 in moderator[0].read_text(),
        f"matching_closes={len(moderator)}",
    ))
    return checks


def implementation_manifest_checks(*, required: bool) -> list[Check]:
    if not IMPLEMENTATION_MANIFEST.is_file():
        return [
            Check(
                "implementation_manifest",
                not required,
                "not yet frozen" if not required else "missing",
            )
        ]
    manifest = json.loads(IMPLEMENTATION_MANIFEST.read_text())
    checks = [
        Check(
            "implementation_manifest_shape",
            isinstance(manifest, dict)
            and manifest.get("implementation_id")
            == "frontier-obligation-admission-implementation-v0.1"
            and manifest.get("packet_index_sha256")
            == "5da170547db2a779880bcfdb01827aa2d30ae9471357f6c6c53ccf977489a3b2"
            and manifest.get("proposal_review_sha256")
            == PROPOSAL_REVIEW_SHA256
            and manifest.get("evidence_class") == "wire_only_not_evidence"
            and manifest.get("mock_outcome") == "admitted"
            and manifest.get("mock_calls") == 12
            and manifest.get("tests_passed") == 14,
            f"path={IMPLEMENTATION_MANIFEST.relative_to(ROOT)}",
        )
    ]
    entries = manifest.get("entries") if isinstance(manifest, dict) else None
    if not isinstance(entries, list):
        return [*checks, Check("implementation_manifest_entries", False, "missing")]
    expected_paths = {
        "Makefile",
        "episodes/frontier_obligation/admission/decision_rule.txt",
        "episodes/frontier_obligation/admission/fixtures.json",
        "episodes/frontier_obligation/admission/packet_index.json",
        "episodes/frontier_obligation/admission/renderer_contract.json",
        "episodes/frontier_obligation/admission/response_contract.json",
        "harness/check_frontier_obligation_admission.py",
        "harness/frontier_obligation_admission.py",
        "harness/probe_frontier_obligation_admission.py",
        "notes/FRONTIER_OBLIGATION_IMPLEMENTATION_PROPOSAL.md",
        "runs/frontier_obligation/wire/admission-mock-v0.1.json",
        "tests/test_frontier_obligation_admission.py",
    }
    entry_paths = [
        str(entry.get("path"))
        for entry in entries
        if isinstance(entry, dict)
    ]
    checks.append(Check(
        "implementation_manifest_entry_set",
        set(entry_paths) == expected_paths
        and len(entry_paths) == len(expected_paths),
        f"entries={sorted(entry_paths)}",
    ))
    for entry in entries:
        if not isinstance(entry, dict):
            checks.append(Check("implementation_entry_shape", False, repr(entry)))
            continue
        relpath = Path(str(entry.get("path", "")))
        safe_path = (
            not relpath.is_absolute()
            and ".." not in relpath.parts
            and str(relpath) in expected_paths
        )
        target = ROOT / relpath if safe_path else ROOT / ".missing"
        observed = file_sha256(target) if target.is_file() else "missing"
        checks.append(Check(
            f"implementation_hash_{entry.get('path')}",
            safe_path and observed == entry.get("sha256"),
            f"observed={observed}",
        ))
    return checks


def gate_result(
    *,
    receipt: dict[str, Any] | None = None,
    engine_backend: str = "mock",
    model: str = "mock-engine-v1",
    reasoning_mode: str = "none_nonreasoning_model",
    base_url: str = "http://localhost:1234/v1",
    execution_pin_sha256: str | None = None,
    execution_pin_path: str | None = None,
    require_manifest: bool = False,
) -> dict[str, Any]:
    authority_checks = [
        *proposal_review_checks(),
        *implementation_manifest_checks(required=require_manifest),
    ]
    if receipt is None:
        static_checks = [*packet_checks(), *authority_checks]
        failed = [check.check for check in static_checks if not check.ok]
        return {
            "checker": "frontier_obligation_admission_v0.1",
            "evidence_class": "precontact_static_only",
            "outcome": (
                "precontact_open"
                if not failed
                else "blocked_before_contact(exact_byte_gate)"
            ),
            "failed_checks": failed,
            "checks": [check.as_dict() for check in static_checks],
        }
    evaluated = evaluate_receipt(
        receipt,
        engine_backend=engine_backend,
        model=model,
        reasoning_mode=reasoning_mode,
        base_url=base_url,
        execution_pin_sha256=execution_pin_sha256,
        execution_pin_path=execution_pin_path,
    )
    meta_failed = [check.check for check in authority_checks if not check.ok]
    all_checks = [
        *[check.as_dict() for check in authority_checks],
        *evaluated["checks"],
    ]
    failed = [*meta_failed, *evaluated["failed_checks"]]
    outcome = (
        "blocked_before_contact(exact_byte_gate)"
        if meta_failed
        else evaluated["outcome"]
    )
    return {
        **evaluated,
        "outcome": outcome,
        "failed_checks": list(dict.fromkeys(failed)),
        "checks": all_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check frontier-obligation admission packet or receipt"
    )
    parser.add_argument("--receipt")
    parser.add_argument("--engine", choices=["mock", "local"], default="mock")
    parser.add_argument("--model", default="mock-engine-v1")
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument("--reasoning-mode", default="none_nonreasoning_model")
    parser.add_argument("--execution-pin")
    parser.add_argument("--pin-sha256")
    parser.add_argument("--require-manifest", action="store_true")
    parser.add_argument("--write-report")
    args = parser.parse_args()
    try:
        receipt_path = Path(args.receipt).resolve() if args.receipt else None
        receipt = (
            json.loads(receipt_path.read_text()) if receipt_path else None
        )
        model = args.model
        base_url = args.base_url
        reasoning_mode = args.reasoning_mode
        pin_sha256 = None
        pin_relpath = None
        if args.engine == "local":
            if receipt_path is None:
                raise ValueError("local receipt checking requires --receipt")
            if not args.execution_pin or not args.pin_sha256:
                raise ValueError("local receipt checking requires the execution pin")
            pin_path = Path(args.execution_pin).resolve()
            if not pin_path.is_relative_to(ROOT):
                raise ValueError("execution pin must be inside the repository")
            pin = verify_execution_pin(
                pin_path,
                exact_hash=args.pin_sha256,
                out_path=receipt_path,
            )
            model = str(pin["model"])
            base_url = str(pin["base_url"])
            reasoning_mode = str(pin["reasoning_mode"])
            pin_sha256 = args.pin_sha256
            pin_relpath = str(pin_path.relative_to(ROOT))
        report = gate_result(
            receipt=receipt,
            engine_backend=args.engine,
            model=model,
            reasoning_mode=reasoning_mode,
            base_url=base_url,
            execution_pin_sha256=pin_sha256,
            execution_pin_path=pin_relpath,
            require_manifest=args.require_manifest,
        )
        if args.write_report:
            atomic_write_new(Path(args.write_report).resolve(), report)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["outcome"] in {"precontact_open", "admitted"} else 1


if __name__ == "__main__":
    sys.exit(main())
