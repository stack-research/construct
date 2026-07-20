"""Wire, packet, refusal, and tamper tests for obligation admission.

The mock receipt proves only the admission machinery. It is not behavioral or
memory evidence.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from harness.check_frontier_obligation_admission import (
    gate_result,
    implementation_manifest_checks,
)
from harness.frontier_obligation_admission import (
    MAX_CALLS,
    PACKET_INDEX_SHA256,
    ROOT,
    action_label,
    action_set,
    build_request_body,
    derive_expected_label,
    derive_expected_role,
    evaluate_receipt,
    fixtures,
    packet_checks,
    packet_index_sha256,
    render_prompt,
    validate_wire,
)
from harness.probe_frontier_obligation_admission import (
    CallResult,
    _row,
    atomic_write_new,
    run_admission,
    verify_execution_pin,
)


def _mock_receipt() -> dict:
    return run_admission(
        engine_backend="mock",
        model="mock-engine-v1",
    )


def _receipt_with_policy(policy) -> dict:
    receipt = _mock_receipt()
    rows = []
    for fixture in fixtures():
        prompt = render_prompt(fixture)
        selection = policy(fixture)
        answer = json.dumps(
            {"commitment_enum": selection},
            separators=(",", ":"),
        )
        result = CallResult(
            raw_answer=answer,
            observed_model="mock-engine-v1",
            latency_ms=0,
            prompt_tokens=0,
            completion_tokens=len(answer.split()),
            tool_calls_present=False,
            raw_response_sha256="mock-policy",
        )
        rows.append(
            _row(
                fixture,
                prompt,
                build_request_body("mock-engine-v1", prompt),
                result,
            )
        )
    receipt.update({
        "rows": rows,
        "calls_attempted": MAX_CALLS,
        "calls_completed": MAX_CALLS,
        "completion_tokens_total": sum(
            row["completion_tokens"] for row in rows
        ),
        "prompt_tokens_total": 0,
        "status": "complete",
        "observed_model": "mock-engine-v1",
    })
    return receipt


def _evaluate(receipt: dict) -> dict:
    return evaluate_receipt(
        receipt,
        engine_backend="mock",
        model="mock-engine-v1",
        reasoning_mode="none_nonreasoning_model",
    )


def test_atomic_receipt_refuses_overwrite():
    target = Path(tempfile.mkdtemp()) / "receipt.json"
    atomic_write_new(target, {"first": True})
    try:
        atomic_write_new(target, {"second": True})
    except FileExistsError:
        pass
    else:
        raise AssertionError("receipt overwrite was allowed")
    assert json.loads(target.read_text()) == {"first": True}
    print("ok  obligation admission receipt: atomic create refuses overwrite")


def test_balanced_pair_geometry():
    rows = fixtures()
    roles = [derive_expected_role(row) for row in rows]
    positions = [
        row["menu_role_order"].index(derive_expected_role(row))
        for row in rows
    ]
    assert roles.count("PROMOTE") == roles.count("WAIT") == 6
    assert positions.count(0) == positions.count(1) == 6
    for pair_id in (f"P{i}" for i in range(1, 7)):
        first = next(row for row in rows if row["fixture_id"] == f"{pair_id}-first")
        later = next(row for row in rows if row["fixture_id"] == f"{pair_id}-later")
        assert derive_expected_role(first) != derive_expected_role(later)
        assert later["status_history"][:-1] == first["status_history"]
    print("ok  obligation admission battery: six balanced paired flips")


def test_excluded_identity_refuses_before_transport():
    with patch(
        "harness.probe_frontier_obligation_admission._transport",
        side_effect=AssertionError("transport constructed for excluded seat"),
    ):
        try:
            run_admission(
                engine_backend="local",
                model="cursor/grok-4.5",
            )
        except ValueError as exc:
            assert "excluded" in str(exc)
        else:
            raise AssertionError("excluded review identity reached transport")
    print("ok  obligation admission exclusion: review seat stops before client")


def test_execution_pin_requires_exact_hash():
    target = Path(tempfile.mkdtemp()) / "pin.json"
    target.write_text("{}\n")
    try:
        verify_execution_pin(
            target,
            exact_hash="0" * 64,
            out_path=ROOT / "runs" / "frontier_obligation" / "never.json",
        )
    except ValueError as exc:
        assert "hash mismatch" in str(exc)
    else:
        raise AssertionError("wrong execution-pin hash was accepted")
    print("ok  obligation admission pin: wrong exact hash refuses")


def test_logged_annotations_are_not_trusted():
    receipt = _mock_receipt()
    receipt["rows"][0]["correct"] = False
    report = _evaluate(receipt)
    assert report["outcome"] == "blocked_before_contact(exact_byte_gate)"
    assert "receipt_row_integrity" in report["failed_checks"]
    print("ok  obligation admission checker: runner annotations recompute")


def test_manifest_is_exact_and_complete():
    checks = implementation_manifest_checks(required=True)
    failed = [check.as_dict() for check in checks if not check.ok]
    assert not failed, failed
    print("ok  obligation admission manifest: exact complete implementation set")


def test_mock_receipt_admits_as_wire_only():
    receipt = _mock_receipt()
    report = _evaluate(receipt)
    assert receipt["wire_only"]
    assert report["evidence_class"] == "wire_only_not_evidence"
    assert report["outcome"] == "admitted", report
    assert report["counts"] == {
        "calls": 12,
        "valid": 12,
        "correct": 12,
        "pair_flips": 6,
        "selected_promote": 6,
        "selected_wait": 6,
        "selected_first_position": 6,
        "selected_second_position": 6,
    }
    print("ok  obligation admission mock: full wire board admits, not evidence")


def test_packet_exact_and_closed():
    checks = packet_checks()
    failed = [check.as_dict() for check in checks if not check.ok]
    assert packet_index_sha256() == PACKET_INDEX_SHA256
    assert not failed, failed
    assert all("expected_action" not in row for row in fixtures())
    print("ok  obligation admission packet: exact bytes and closed fixtures")


def test_position_policy_is_caught():
    receipt = _receipt_with_policy(lambda fixture: action_set(fixture)[0])
    report = _evaluate(receipt)
    assert report["outcome"] == "admission_refused(rule_accuracy)"
    assert "pair_constant_policy" in report["failed_checks"]
    assert "position_constant_policy" in report["failed_checks"]
    assert report["counts"]["selected_first_position"] == 12
    print("ok  obligation admission anti-constant: first-position policy refused")


def test_prompt_surface_is_pair_fixed():
    for pair_id in (f"P{i}" for i in range(1, 7)):
        first = next(
            row for row in fixtures() if row["fixture_id"] == f"{pair_id}-first"
        )
        later = next(
            row for row in fixtures() if row["fixture_id"] == f"{pair_id}-later"
        )
        first_prompt = render_prompt(first)
        later_prompt = render_prompt(later)
        assert first["artifact_id"] == later["artifact_id"]
        assert action_set(first) == action_set(later)
        assert first_prompt != later_prompt
        for fixed in (
            "[task]",
            first["artifact_id"],
            "[governing rule]",
            "[action set]",
            *action_set(first),
            "[commitment response]",
        ):
            assert fixed in first_prompt and fixed in later_prompt
    print("ok  obligation admission renderer: pair surface fixed around status")


def test_proposal_review_opens_static_gate():
    report = gate_result(require_manifest=False)
    assert report["outcome"] == "precontact_open", report
    print("ok  obligation admission authority: proposal review opens static gate")


def test_receipt_order_tamper_blocks():
    receipt = _mock_receipt()
    receipt["rows"][0], receipt["rows"][1] = (
        receipt["rows"][1],
        receipt["rows"][0],
    )
    report = _evaluate(receipt)
    assert report["outcome"] == "blocked_before_contact(exact_byte_gate)"
    assert "receipt_order" in report["failed_checks"]
    print("ok  obligation admission receipt: canonical order tamper blocks")


def test_wait_constant_policy_is_caught():
    receipt = _receipt_with_policy(
        lambda fixture: action_label("WAIT", fixture["artifact_id"])
    )
    report = _evaluate(receipt)
    assert report["outcome"] == "admission_refused(rule_accuracy)"
    assert "pair_constant_policy" in report["failed_checks"]
    assert "action_constant_policy" in report["failed_checks"]
    assert report["counts"]["selected_wait"] == 12
    print("ok  obligation admission anti-constant: wait-only policy refused")


def test_wire_extraction_and_closed_validation():
    fixture = fixtures()[0]
    expected = derive_expected_label(fixture)
    plain = json.dumps({"commitment_enum": expected})
    fenced = f"```json\n{plain}\n```"
    assert validate_wire(plain, fixture).outcome == "commitment_valid"
    assert validate_wire(fenced, fixture).outcome == "commitment_valid"
    assert validate_wire(fenced, fixture).extraction_mode == "json_substring"
    assert validate_wire(
        json.dumps({"commitment_enum": expected, "extra": True}),
        fixture,
    ).invalid_reason == "extra_field"
    assert validate_wire(
        json.dumps({"commitment_enum": "UNKNOWN"}),
        fixture,
    ).invalid_reason == "unknown_enum"
    assert validate_wire(
        plain,
        fixture,
        tool_calls_present=True,
    ).invalid_reason == "tool_calls_present"
    assert validate_wire(
        f"{plain}\n{plain}",
        fixture,
    ).outcome == "commitment_invalid"
    print("ok  obligation admission wire: predeclared extraction stays closed")


if __name__ == "__main__":
    tests = sorted(
        (name, function)
        for name, function in globals().items()
        if name.startswith("test_") and callable(function)
    )
    for _, test in tests:
        test()
    print(
        f"\nALL {len(tests)} FRONTIER-OBLIGATION ADMISSION TESTS PASS "
        "(mock wire only)"
    )
