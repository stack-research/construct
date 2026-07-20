"""Deterministic core for the frontier-obligation admission packet.

This module owns packet verification, prompt rendering, commitment-wire
validation, and receipt scoring. It does not construct an engine client.
Admission receipts are surface diagnostics only, never memory evidence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKET_DIR = ROOT / "episodes" / "frontier_obligation" / "admission"
PACKET_INDEX = PACKET_DIR / "packet_index.json"
PACKET_ID = "frontier-obligation-admission-v0.1"
PACKET_INDEX_SHA256 = (
    "5da170547db2a779880bcfdb01827aa2d30ae9471357f6c6c53ccf977489a3b2"
)
PROPOSAL_REVIEW_SHA256 = (
    "19214f49b5b34f61ea9c0aaa024efff94049039b1bbf78dc3097eeff02cca004"
)
VALID_STATUSES = frozenset({"passed", "pending", "failed", "revoked"})
VALID_ROLES = ("PROMOTE", "WAIT")
MAX_CALLS = 12
MAX_OUTPUT_TOKENS_PER_CALL = 512
MAX_OUTPUT_TOKENS_TOTAL = MAX_CALLS * MAX_OUTPUT_TOKENS_PER_CALL
DECISION_RULE = """The requested action is promotion.

If status history is empty, follow the requested action.
If status history is present, the event with the greatest event_seq is current.
Promote only when the current status is passed.
Wait when the current status is pending, failed, or revoked."""


@dataclass(frozen=True)
class Check:
    check: str
    ok: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {"check": self.check, "ok": self.ok, "detail": self.detail}


@dataclass(frozen=True)
class WireResult:
    outcome: str
    selection: str | None
    invalid_reason: str | None
    extracted: object
    extraction_mode: str | None


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path}")
    return value


def packet_index_sha256() -> str:
    return file_sha256(PACKET_INDEX)


def packet_index() -> dict[str, Any]:
    return load_json(PACKET_INDEX)


def fixtures_document() -> dict[str, Any]:
    return load_json(PACKET_DIR / "fixtures.json")


def fixtures() -> list[dict[str, Any]]:
    rows = fixtures_document().get("fixtures")
    if not isinstance(rows, list):
        raise ValueError("fixtures must be a list")
    return rows


def renderer_contract() -> dict[str, Any]:
    return load_json(PACKET_DIR / "renderer_contract.json")


def response_contract() -> dict[str, Any]:
    return load_json(PACKET_DIR / "response_contract.json")


def decision_rule_text() -> str:
    return (PACKET_DIR / "decision_rule.txt").read_text().rstrip("\n")


def action_label(role: str, artifact_id: str) -> str:
    if role not in VALID_ROLES:
        raise ValueError(f"unknown action role {role!r}")
    return f"{role} {artifact_id}"


def action_set(fixture: dict[str, Any]) -> list[str]:
    artifact_id = str(fixture["artifact_id"])
    return [
        action_label(str(role), artifact_id)
        for role in fixture["menu_role_order"]
    ]


def derive_expected_role(fixture: dict[str, Any]) -> str:
    history = fixture.get("status_history")
    if not isinstance(history, list):
        raise ValueError("status_history must be a list")
    if not history:
        return "PROMOTE"
    current = max(history, key=lambda event: int(event["event_seq"]))
    return "PROMOTE" if current["status"] == "passed" else "WAIT"


def derive_expected_label(fixture: dict[str, Any]) -> str:
    return action_label(derive_expected_role(fixture), str(fixture["artifact_id"]))


def role_for_selection(fixture: dict[str, Any], selection: str | None) -> str | None:
    if selection is None:
        return None
    for role in VALID_ROLES:
        if selection == action_label(role, str(fixture["artifact_id"])):
            return role
    return None


def menu_position(fixture: dict[str, Any], selection: str | None) -> int | None:
    if selection is None:
        return None
    try:
        return action_set(fixture).index(selection)
    except ValueError:
        return None


def render_prompt(fixture: dict[str, Any]) -> str:
    renderer = renderer_contract()
    history = fixture["status_history"]
    if history:
        history_text = "\n".join(
            f"- event_seq={event['event_seq']} status={event['status']}"
            for event in history
        )
    else:
        history_text = renderer["status_none"]
    actions = "\n".join(f"- {label}" for label in action_set(fixture))
    return (
        f"{renderer['task_header']}\n"
        f"Artifact: {fixture['artifact_id']}\n"
        f"Requested action: {renderer['requested_action']}\n\n"
        f"{renderer['governing_rule_header']}\n"
        f"{decision_rule_text()}\n\n"
        f"{renderer['status_history_header']}\n"
        f"{history_text}\n\n"
        f"{renderer['action_set_header']}\n"
        f"{actions}\n\n"
        f"{renderer['commitment_response_header']}\n"
        f"{renderer['commitment_instruction']}"
    )


def build_request_body(model: str, prompt: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": MAX_OUTPUT_TOKENS_PER_CALL,
        "stream": False,
    }


def extract_wire(raw: str) -> tuple[object, str | None]:
    stripped = raw.strip()
    if not stripped:
        return None, None
    try:
        return json.loads(stripped), "full_json"
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(stripped[start : end + 1]), "json_substring"
            except json.JSONDecodeError:
                pass
    return None, None


def validate_wire(
    raw: str,
    fixture: dict[str, Any],
    *,
    tool_calls_present: bool = False,
) -> WireResult:
    extracted, extraction_mode = extract_wire(raw)
    if tool_calls_present:
        return WireResult(
            "commitment_invalid",
            None,
            "tool_calls_present",
            extracted,
            extraction_mode,
        )
    if not isinstance(extracted, dict):
        return WireResult(
            "commitment_invalid",
            None,
            "malformed_object",
            extracted,
            extraction_mode,
        )
    allowed = {"commitment_enum", "optional_prose"}
    if set(extracted) - allowed:
        return WireResult(
            "commitment_invalid",
            None,
            "extra_field",
            extracted,
            extraction_mode,
        )
    selection = extracted.get("commitment_enum")
    if not isinstance(selection, str) or not selection:
        return WireResult(
            "commitment_invalid",
            None,
            "absent_or_malformed_commitment",
            extracted,
            extraction_mode,
        )
    optional = extracted.get("optional_prose")
    if "optional_prose" in extracted and not isinstance(optional, str):
        return WireResult(
            "commitment_invalid",
            None,
            "malformed_optional_prose",
            extracted,
            extraction_mode,
        )
    if selection not in action_set(fixture):
        return WireResult(
            "commitment_invalid",
            selection,
            "unknown_enum",
            extracted,
            extraction_mode,
        )
    return WireResult(
        "commitment_valid",
        selection,
        None,
        extracted,
        extraction_mode,
    )


def _entry_checks() -> list[Check]:
    index = packet_index()
    checks: list[Check] = []
    expected_names = {
        "decision_rule.txt",
        "fixtures.json",
        "renderer_contract.json",
        "response_contract.json",
    }
    entry_names = {
        entry.get("path")
        for entry in index.get("entries", [])
        if isinstance(entry, dict)
    }
    checks.append(Check(
        "packet_entry_set",
        entry_names == expected_names,
        f"entries={sorted(str(name) for name in entry_names)}",
    ))
    for entry in index.get("entries", []):
        if not isinstance(entry, dict):
            checks.append(Check("packet_entry_shape", False, repr(entry)))
            continue
        target = PACKET_DIR / str(entry.get("path", ""))
        observed = file_sha256(target) if target.is_file() else "missing"
        checks.append(Check(
            f"packet_hash_{entry.get('path')}",
            observed == entry.get("sha256"),
            f"observed={observed}",
        ))
    actual_files = {path.name for path in PACKET_DIR.iterdir() if path.is_file()}
    checks.append(Check(
        "packet_no_unindexed_files",
        actual_files == expected_names | {"packet_index.json"},
        f"files={sorted(actual_files)}",
    ))
    return checks


def _pair_checks(rows: list[dict[str, Any]]) -> list[Check]:
    checks: list[Check] = []
    by_pair: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_pair.setdefault(str(row.get("pair_id")), []).append(row)
    pair_ids_ok = set(by_pair) == {f"P{i}" for i in range(1, 7)}
    checks.append(Check("pair_ids", pair_ids_ok, f"pairs={sorted(by_pair)}"))
    pair_shape_ok = True
    pair_flip_ok = True
    for pair_id, pair in sorted(by_pair.items()):
        if len(pair) != 2:
            pair_shape_ok = False
            pair_flip_ok = False
            continue
        first = next((row for row in pair if row.get("member") == "first"), None)
        later = next((row for row in pair if row.get("member") == "later"), None)
        if first is None or later is None:
            pair_shape_ok = False
            pair_flip_ok = False
            continue
        first_history = first.get("status_history")
        later_history = later.get("status_history")
        same_surface = (
            first.get("artifact_id") == later.get("artifact_id")
            and first.get("menu_role_order") == later.get("menu_role_order")
        )
        history_extension = (
            isinstance(first_history, list)
            and isinstance(later_history, list)
            and later_history[:-1] == first_history
            and len(later_history) == len(first_history) + 1
        )
        pair_shape_ok = pair_shape_ok and same_surface and history_extension
        pair_flip_ok = (
            pair_flip_ok
            and derive_expected_role(first) != derive_expected_role(later)
        )
    checks.extend([
        Check(
            "pair_mates",
            pair_shape_ok,
            "same artifact/menu; later member adds exactly one status event",
        ),
        Check(
            "pair_expected_flips",
            pair_flip_ok,
            "all six pairs reverse the machine-derived action",
        ),
    ])
    return checks


def packet_checks() -> list[Check]:
    index = packet_index()
    document = fixtures_document()
    rows = fixtures()
    canonical_order = document.get("canonical_order")
    checks = [
        Check(
            "packet_index_hash",
            packet_index_sha256() == PACKET_INDEX_SHA256,
            f"observed={packet_index_sha256()}",
        ),
        Check(
            "packet_id",
            index.get("packet_id") == PACKET_ID
            and document.get("packet_id") == PACKET_ID
            and renderer_contract().get("packet_id") == PACKET_ID
            and response_contract().get("packet_id") == PACKET_ID,
            f"expected={PACKET_ID}",
        ),
        Check(
            "proposal_review_binding",
            index.get("proposal_review_sha256") == PROPOSAL_REVIEW_SHA256,
            f"observed={index.get('proposal_review_sha256')}",
        ),
        Check(
            "decision_rule_exact",
            decision_rule_text() == DECISION_RULE,
            f"sha256={file_sha256(PACKET_DIR / 'decision_rule.txt')}",
        ),
        Check(
            "canonical_order",
            isinstance(canonical_order, list)
            and canonical_order == [row.get("fixture_id") for row in rows],
            f"count={len(rows)}",
        ),
        Check(
            "call_count",
            len(rows) == MAX_CALLS and len(set(canonical_order or [])) == MAX_CALLS,
            f"rows={len(rows)}; unique={len(set(canonical_order or []))}",
        ),
    ]
    checks.extend(_entry_checks())
    fixture_keys_ok = True
    history_ok = True
    menus_ok = True
    artifacts: dict[str, str] = {}
    for row in rows:
        fixture_keys_ok = fixture_keys_ok and set(row) == {
            "artifact_id",
            "fixture_id",
            "member",
            "menu_role_order",
            "pair_id",
            "status_history",
        }
        menu = row.get("menu_role_order")
        menus_ok = (
            menus_ok
            and isinstance(menu, list)
            and len(menu) == 2
            and set(menu) == set(VALID_ROLES)
        )
        history = row.get("status_history")
        if not isinstance(history, list):
            history_ok = False
            continue
        seqs: list[int] = []
        for event in history:
            if not isinstance(event, dict) or set(event) != {"event_seq", "status"}:
                history_ok = False
                continue
            try:
                seq = int(event["event_seq"])
            except (TypeError, ValueError):
                history_ok = False
                continue
            seqs.append(seq)
            history_ok = history_ok and (
                seq > 0 and event["status"] in VALID_STATUSES
            )
        history_ok = history_ok and seqs == sorted(set(seqs))
        pair_id = str(row.get("pair_id"))
        artifact = str(row.get("artifact_id"))
        prior = artifacts.setdefault(pair_id, artifact)
        fixture_keys_ok = fixture_keys_ok and prior == artifact
    checks.extend([
        Check(
            "fixture_closed_shape",
            fixture_keys_ok,
            "fixtures contain no expected-action or discretionary fields",
        ),
        Check(
            "status_history",
            history_ok,
            "closed vocabulary; positive unique event_seq in render order",
        ),
        Check(
            "menu_roles",
            menus_ok,
            "each fixture contains PROMOTE and WAIT exactly once",
        ),
        Check(
            "artifact_partition",
            len(set(artifacts.values())) == 6 and len(artifacts) == 6,
            json.dumps(artifacts, sort_keys=True),
        ),
    ])
    checks.extend(_pair_checks(rows))
    expected_roles = [derive_expected_role(row) for row in rows]
    expected_positions = [
        row["menu_role_order"].index(derive_expected_role(row))
        for row in rows
    ]
    checks.extend([
        Check(
            "expected_role_balance",
            expected_roles.count("PROMOTE") == 6
            and expected_roles.count("WAIT") == 6,
            f"PROMOTE={expected_roles.count('PROMOTE')}; WAIT={expected_roles.count('WAIT')}",
        ),
        Check(
            "expected_position_balance",
            expected_positions.count(0) == 6
            and expected_positions.count(1) == 6,
            f"first={expected_positions.count(0)}; second={expected_positions.count(1)}",
        ),
    ])
    prompts = [render_prompt(row) for row in rows]
    renderer_ok = all(
        prompt.count("[task]") == 1
        and prompt.count("[governing rule]") == 1
        and prompt.count("[status history]") == 1
        and prompt.count("[action set]") == 1
        and prompt.count("[commitment response]") == 1
        and DECISION_RULE in prompt
        for prompt in prompts
    )
    checks.append(Check(
        "renderer_closed",
        renderer_ok and len(set(prompts)) == MAX_CALLS,
        f"unique_prompts={len(set(prompts))}",
    ))
    return checks


def packet_gate_open() -> bool:
    return all(check.ok for check in packet_checks())


def _receipt_binding_checks(
    receipt: dict[str, Any],
    *,
    engine_backend: str,
    model: str,
    reasoning_mode: str,
    base_url: str,
    execution_pin_sha256: str | None,
    execution_pin_path: str | None,
) -> list[Check]:
    observed_models = {
        str(row.get("observed_model", ""))
        for row in receipt.get("rows", [])
        if isinstance(row, dict) and row.get("observed_model")
    }
    observed = str(receipt.get("observed_model", ""))
    identity_ok = (
        receipt.get("requested_model") == model
        and len(observed_models) <= 1
        and (not observed_models or observed in observed_models)
    )
    if engine_backend == "mock":
        identity_ok = identity_ok and observed == "mock-engine-v1"
    return [
        Check(
            "receipt_packet_binding",
            receipt.get("packet_index_sha256") == PACKET_INDEX_SHA256
            and receipt.get("renderer_sha256")
            == file_sha256(PACKET_DIR / "renderer_contract.json")
            and receipt.get("response_contract_sha256")
            == file_sha256(PACKET_DIR / "response_contract.json")
            and receipt.get("decision_rule_sha256")
            == file_sha256(PACKET_DIR / "decision_rule.txt"),
            f"packet={receipt.get('packet_index_sha256')}",
        ),
        Check(
            "receipt_transport_binding",
            receipt.get("engine_backend_cli") == engine_backend
            and receipt.get("temperature") == 0
            and receipt.get("reasoning_mode") == reasoning_mode
            and receipt.get("base_url") == base_url
            and receipt.get("max_output_tokens_per_call")
            == MAX_OUTPUT_TOKENS_PER_CALL,
            f"backend={receipt.get('engine_backend_cli')}; reasoning={receipt.get('reasoning_mode')}; base_url={receipt.get('base_url')}",
        ),
        Check(
            "receipt_execution_pin_binding",
            receipt.get("execution_pin_sha256") == execution_pin_sha256
            and receipt.get("execution_pin_path") == execution_pin_path,
            f"sha256={receipt.get('execution_pin_sha256')}; path={receipt.get('execution_pin_path')}",
        ),
        Check(
            "receipt_identity",
            identity_ok,
            f"requested={receipt.get('requested_model')}; observed={observed}; rows={sorted(observed_models)}",
        ),
        Check(
            "receipt_contact_class",
            receipt.get("contact_class") == "admission_only_not_evidence",
            f"contact_class={receipt.get('contact_class')}",
        ),
    ]


def evaluate_receipt(
    receipt: dict[str, Any],
    *,
    engine_backend: str,
    model: str,
    reasoning_mode: str,
    base_url: str = "http://localhost:1234/v1",
    execution_pin_sha256: str | None = None,
    execution_pin_path: str | None = None,
) -> dict[str, Any]:
    packet = packet_checks()
    rows = receipt.get("rows")
    if not isinstance(rows, list):
        rows = []
    fixture_rows = fixtures()
    expected_order = [row["fixture_id"] for row in fixture_rows]
    actual_order = [
        row.get("fixture_id")
        for row in rows
        if isinstance(row, dict)
    ]
    checks = [
        *packet,
        *_receipt_binding_checks(
            receipt,
            engine_backend=engine_backend,
            model=model,
            reasoning_mode=reasoning_mode,
            base_url=base_url,
            execution_pin_sha256=execution_pin_sha256,
            execution_pin_path=execution_pin_path,
        ),
        Check(
            "receipt_complete",
            receipt.get("status") == "complete"
            and receipt.get("calls_attempted") == MAX_CALLS
            and receipt.get("calls_completed") == MAX_CALLS
            and len(rows) == MAX_CALLS,
            f"status={receipt.get('status')}; attempted={receipt.get('calls_attempted')}; completed={receipt.get('calls_completed')}; rows={len(rows)}",
        ),
        Check(
            "receipt_order",
            actual_order == expected_order,
            f"actual={actual_order}",
        ),
    ]
    fixture_by_id = {row["fixture_id"]: row for row in fixture_rows}
    valid_count = 0
    correct_count = 0
    selected_roles: list[str] = []
    selected_positions: list[int] = []
    row_by_id: dict[str, dict[str, Any]] = {}
    outputs_within_cap = True
    tool_calls_absent = True
    row_integrity_ok = True
    for row in rows:
        if not isinstance(row, dict):
            row_integrity_ok = False
            continue
        fixture_id = str(row.get("fixture_id"))
        fixture = fixture_by_id.get(fixture_id)
        if fixture is None:
            row_integrity_ok = False
            continue
        row_by_id[fixture_id] = row
        raw_answer = row.get("raw_answer")
        if not isinstance(raw_answer, str):
            raw_answer = ""
            row_integrity_ok = False
        observed_wire = validate_wire(
            raw_answer,
            fixture,
            tool_calls_present=bool(row.get("tool_calls_present")),
        )
        expected = derive_expected_label(fixture)
        observed_correct = (
            observed_wire.outcome == "commitment_valid"
            and observed_wire.selection == expected
        )
        prompt = render_prompt(fixture)
        request_body = build_request_body(model, prompt)
        raw_sha = hashlib.sha256(raw_answer.encode()).hexdigest()
        logged_integrity = (
            row.get("pair_id") == fixture["pair_id"]
            and row.get("member") == fixture["member"]
            and row.get("artifact_id") == fixture["artifact_id"]
            and row.get("prompt_sha256")
            == hashlib.sha256(prompt.encode()).hexdigest()
            and row.get("request_sha256") == canonical_sha256(request_body)
            and row.get("action_set") == action_set(fixture)
            and row.get("raw_answer_sha256") == raw_sha
            and row.get("extraction_mode") == observed_wire.extraction_mode
            and row.get("extracted_wire") == observed_wire.extracted
            and row.get("validation_outcome") == observed_wire.outcome
            and row.get("invalid_reason") == observed_wire.invalid_reason
            and row.get("selection") == observed_wire.selection
            and row.get("expected_role") == derive_expected_role(fixture)
            and row.get("expected_selection") == expected
            and row.get("correct") is observed_correct
        )
        row_integrity_ok = row_integrity_ok and logged_integrity
        if observed_wire.outcome == "commitment_valid":
            valid_count += 1
        if observed_correct:
            correct_count += 1
        role = role_for_selection(fixture, observed_wire.selection)
        if role is not None:
            selected_roles.append(role)
        position = menu_position(fixture, observed_wire.selection)
        if position is not None:
            selected_positions.append(position)
        outputs_within_cap = outputs_within_cap and (
            int(row.get("completion_tokens", 0)) <= MAX_OUTPUT_TOKENS_PER_CALL
        )
        tool_calls_absent = tool_calls_absent and not bool(
            row.get("tool_calls_present")
        )
    checks.extend([
        Check(
            "receipt_row_integrity",
            row_integrity_ok,
            "runner annotations, prompt/request hashes, and wire fields recompute",
        ),
        Check(
            "wire_competence",
            valid_count == MAX_CALLS and tool_calls_absent,
            f"valid={valid_count}/{MAX_CALLS}; tool_calls_absent={tool_calls_absent}",
        ),
        Check(
            "rule_accuracy",
            correct_count == MAX_CALLS,
            f"correct={correct_count}/{MAX_CALLS}",
        ),
    ])
    pair_flips = 0
    for pair_id in (f"P{i}" for i in range(1, 7)):
        first = row_by_id.get(f"{pair_id}-first")
        later = row_by_id.get(f"{pair_id}-later")
        if (
            first is not None
            and later is not None
            and validate_wire(
                str(first.get("raw_answer", "")),
                fixture_by_id[f"{pair_id}-first"],
                tool_calls_present=bool(first.get("tool_calls_present")),
            ).selection
            != validate_wire(
                str(later.get("raw_answer", "")),
                fixture_by_id[f"{pair_id}-later"],
                tool_calls_present=bool(later.get("tool_calls_present")),
            ).selection
        ):
            pair_flips += 1
    checks.extend([
        Check(
            "pair_constant_policy",
            pair_flips == 6,
            f"flips={pair_flips}/6",
        ),
        Check(
            "action_constant_policy",
            selected_roles.count("PROMOTE") == 6
            and selected_roles.count("WAIT") == 6,
            f"PROMOTE={selected_roles.count('PROMOTE')}; WAIT={selected_roles.count('WAIT')}",
        ),
        Check(
            "position_constant_policy",
            selected_positions.count(0) == 6
            and selected_positions.count(1) == 6,
            f"first={selected_positions.count(0)}; second={selected_positions.count(1)}",
        ),
        Check(
            "budget",
            receipt.get("calls_attempted", 0) <= MAX_CALLS
            and receipt.get("calls_completed", 0) <= MAX_CALLS
            and int(receipt.get("completion_tokens_total", 0))
            <= MAX_OUTPUT_TOKENS_TOTAL
            and outputs_within_cap,
            f"calls={receipt.get('calls_attempted')}; output_tokens={receipt.get('completion_tokens_total')}",
        ),
    ])
    failed = [check.check for check in checks if not check.ok]
    transport_failure = receipt.get("status") == "transport_refused"
    if any(name.startswith("packet_") for name in failed):
        outcome = "blocked_before_contact(exact_byte_gate)"
    elif "receipt_identity" in failed:
        outcome = "admission_refused(identity)"
    elif transport_failure or "receipt_complete" in failed:
        outcome = "admission_refused(transport)"
    elif "receipt_row_integrity" in failed:
        outcome = "blocked_before_contact(exact_byte_gate)"
    elif "wire_competence" in failed:
        outcome = "admission_refused(commitment_invalid)"
    elif "rule_accuracy" in failed:
        outcome = "admission_refused(rule_accuracy)"
    elif "pair_constant_policy" in failed:
        outcome = "admission_refused(pair_constant_policy)"
    elif "action_constant_policy" in failed:
        outcome = "admission_refused(action_constant_policy)"
    elif "position_constant_policy" in failed:
        outcome = "admission_refused(position_constant_policy)"
    elif "budget" in failed:
        outcome = "admission_refused(budget)"
    elif failed:
        outcome = "blocked_before_contact(exact_byte_gate)"
    else:
        outcome = "admitted"
    return {
        "checker": "frontier_obligation_admission_v0.1",
        "evidence_class": (
            "wire_only_not_evidence"
            if engine_backend == "mock"
            else "admission_only_not_evidence"
        ),
        "outcome": outcome,
        "failed_checks": failed,
        "checks": [check.as_dict() for check in checks],
        "counts": {
            "calls": len(rows),
            "valid": valid_count,
            "correct": correct_count,
            "pair_flips": pair_flips,
            "selected_promote": selected_roles.count("PROMOTE"),
            "selected_wait": selected_roles.count("WAIT"),
            "selected_first_position": selected_positions.count(0),
            "selected_second_position": selected_positions.count(1),
        },
    }
