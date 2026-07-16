"""EFC v1 integrity-lanes pilot runner — §5.3 / §10.6 engine contact.

Deterministic dry-run (MockTransport) is mandatory for review; live contact
requires an explicit ``--live`` flag and the pinned ``pin_event_id``. Never
mutates ``corpus/`` or the manifest bytes.

Normative contract: ``harness/efc_pilot_runner_contract_v1.md``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Protocol

from harness.efc_commitment_oracle_v1 import score_commitment_oracle_v1
from harness.efc_commitment_wire_v1 import validate_commitment_wire
from harness.efc_intervals import newcombe_diff_interval
from harness.efc_manifest_v1 import (MANIFEST_RELPATH, REPO_ROOT,
                                       manifest_hash, manifest_verify,
                                       sha256_bytes, sha256_canon, sha256_path)
from harness.efc_render_v1 import render_prompt, render_prompt_menu_only
from harness.efc_roster_r2 import API_BASE, _extract_text, _http_post

CONTRACT_RELPATH = "harness/efc_pilot_runner_contract_v1.md"
PIN_SIDECAR_RELPATH = "corpus/efc_calibration_v1/manifest_pin_v1.json"
LEDGER_DIR_REL = "runs/efc_calibration_v1"
PIN_EVENT_ID = "efc-v1-manifest-pin-3f2232aa0e11451c"
PART_I_SPEC_SHA256 = (
    "2d37f6bf0cd4aab830cb1dcf5eb9576f13b9acff65b63cd7d5b5fe0ea5b6097d"
)

LANES = ("M_menu_only", "M_task_menu")
STRATA = ("match_mismatch", "match_commit", "irrelevant")

VERIFICATION_SOLICITATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bverify\b", re.IGNORECASE),
    re.compile(r"\bexternal\s+verification\b", re.IGNORECASE),
    re.compile(r"\bprovenance\s+tool\b", re.IGNORECASE),
    re.compile(r"\bcheck\s+the\s+(source|citation|claim)\b", re.IGNORECASE),
)

Outcome = Literal[
    "completed",
    "construction_refused",
    "budget_refusal",
    "transport_refusal",
]

CallOutcome = Literal[
    "completed",
    "budget_refusal",
    "over_ceiling",
    "transport_rejected",
    "parse_failed",
]

RUNNER_DISCLOSURES: tuple[str, ...] = (
    "Pre-call input estimate (utf8_len//4) is a disclosed first-line floor; "
    "post-call actual token and cost totals are ledger law (§4).",
    "Solicitation detector is an intentionally incomplete lexical floor "
    "(mirroring the L2 leak-predictor pattern). The 0.05 menu-only gate "
    "audits only detector-visible solicitations; paraphrase-class evasions "
    "remain an unpriced residual (§5).",
    "§10.2 collapse-to-T0.7 is out of scope for this runner; "
    "admission/calibration runner owns it.",
)


@dataclass(frozen=True)
class PilotRunnerRefusal(Exception):
    reason: str
    detail: str | None = None


@dataclass(frozen=True)
class BudgetRefusal(PilotRunnerRefusal):
    pool: str | None = None


@dataclass(frozen=True)
class TransportRefusal(PilotRunnerRefusal):
    http_status: int | None = None
    sanitized_body: dict[str, Any] | None = None
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class ParseFailure(PilotRunnerRefusal):
    sanitized_body: dict[str, Any] | None = None
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class BudgetState:
    calls_spent: int
    input_tokens_spent: int
    output_tokens_spent: int
    input_token_ceiling: int
    output_token_ceiling: int
    total_call_ceiling: int
    max_output_tokens_per_request: int
    hard_cost_ceiling_usd: float
    input_usd_per_million: float
    output_usd_per_million: float

    def cost_usd(self) -> float:
        return (
            self.input_tokens_spent * self.input_usd_per_million / 1_000_000
            + self.output_tokens_spent * self.output_usd_per_million / 1_000_000
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "calls_spent": self.calls_spent,
            "input_tokens_spent": self.input_tokens_spent,
            "output_tokens_spent": self.output_tokens_spent,
            "cost_usd": round(self.cost_usd(), 8),
        }


@dataclass(frozen=True)
class CallContext:
    fixture_id: str
    lane: str
    stratum: str
    expected_commitment_enum: str
    action_set: tuple[str, ...]


@dataclass(frozen=True)
class TransportResult:
    raw: dict[str, Any]
    text: str
    input_tokens: int
    output_tokens: int
    tool_calls_present: bool


class Transport(Protocol):
    def call(self, request_body: dict[str, Any], context: CallContext) -> TransportResult:
        ...


def estimated_input_tokens(prompt: str) -> int:
    """Deterministic pre-call input estimate (contract §4)."""
    return max(1, (len(prompt.encode("utf-8")) + 3) // 4)


def load_budget_state(manifest: dict[str, Any]) -> BudgetState:
    budget = manifest["budget_ledger"]
    pricing = budget["pricing"]
    wire = budget["wire_probe_tokens"]
    return BudgetState(
        calls_spent=int(budget["calls_already_spent"]),
        input_tokens_spent=int(wire["input"]),
        output_tokens_spent=int(wire["output"]),
        input_token_ceiling=int(budget["input_token_ceiling"]),
        output_token_ceiling=int(budget["output_token_ceiling"]),
        total_call_ceiling=int(budget["total_call_ceiling"]),
        max_output_tokens_per_request=int(
            budget["max_output_tokens_per_request"]
        ),
        hard_cost_ceiling_usd=float(budget["hard_cost_ceiling_usd"]),
        input_usd_per_million=float(pricing["input_usd_per_million"]),
        output_usd_per_million=float(pricing["output_usd_per_million"]),
    )


def check_budget_guard(
    state: BudgetState,
    *,
    projected_input_tokens: int,
) -> BudgetRefusal | None:
    if state.calls_spent >= state.total_call_ceiling:
        return BudgetRefusal("budget_refusal", "calls_pool_exhausted", "calls")
    projected_output = (
        state.output_tokens_spent + state.max_output_tokens_per_request
    )
    if projected_input_tokens > state.input_token_ceiling:
        return BudgetRefusal(
            "budget_refusal", "input_token_ceiling_crossed", "input_tokens"
        )
    if projected_output > state.output_token_ceiling:
        return BudgetRefusal(
            "budget_refusal", "output_token_ceiling_crossed", "output_tokens"
        )
    projected_cost = (
        projected_input_tokens * state.input_usd_per_million / 1_000_000
        + projected_output * state.output_usd_per_million / 1_000_000
    )
    if projected_cost > state.hard_cost_ceiling_usd:
        return BudgetRefusal(
            "budget_refusal", "hard_cost_ceiling_crossed", "cost_usd"
        )
    return None


def check_budget_actual(state: BudgetState) -> BudgetRefusal | None:
    """Post-call enforcement: actual cumulative spend vs pinned ceilings."""
    if state.calls_spent >= state.total_call_ceiling:
        return BudgetRefusal("budget_refusal", "calls_pool_exhausted", "calls")
    if state.input_tokens_spent >= state.input_token_ceiling:
        return BudgetRefusal(
            "budget_refusal", "input_token_ceiling_crossed", "input_tokens"
        )
    if state.output_tokens_spent >= state.output_token_ceiling:
        return BudgetRefusal(
            "budget_refusal", "output_token_ceiling_crossed", "output_tokens"
        )
    if state.cost_usd() >= state.hard_cost_ceiling_usd:
        return BudgetRefusal(
            "budget_refusal", "hard_cost_ceiling_crossed", "cost_usd"
        )
    return None


def verify_pin_sidecar(root: Path, manifest: dict[str, Any]) -> tuple[bool, str]:
    pin_path = root / PIN_SIDECAR_RELPATH
    if not pin_path.is_file():
        return False, "pin_sidecar_missing"
    pin = json.loads(pin_path.read_text(encoding="utf-8"))
    canonical = manifest_hash(manifest)
    if pin.get("manifest_hash_canonical") != canonical:
        return False, "pin_hash_mismatch:manifest_hash_canonical"
    manifest_path = root / MANIFEST_RELPATH
    raw_sha = sha256_path(manifest_path)
    if pin.get("manifest_file_sha256_raw") != raw_sha:
        return False, "pin_hash_mismatch:manifest_file_sha256_raw"
    if pin.get("manifest_path") != MANIFEST_RELPATH:
        return False, "pin_sidecar_path_mismatch"
    return True, ""


def load_pinned_manifest(
    root: Path = REPO_ROOT,
    *,
    require_pin: bool = True,
) -> dict[str, Any]:
    manifest_path = root / MANIFEST_RELPATH
    if not manifest_path.is_file():
        raise PilotRunnerRefusal("construction_refused", "manifest_missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("part_i_spec_hash") != PART_I_SPEC_SHA256:
        raise PilotRunnerRefusal(
            "construction_refused", "part_i_spec_hash_mismatch"
        )
    verify = manifest_verify(manifest, root=root, render_repeats=2)
    if not verify.ok:
        raise PilotRunnerRefusal(
            "construction_refused",
            "manifest_verify_failed:" + ";".join(verify.failures[:5]),
        )
    if require_pin:
        ok, reason = verify_pin_sidecar(root, manifest)
        if not ok:
            raise PilotRunnerRefusal("construction_refused", reason)
    return manifest


def load_fixtures(root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    from harness.efc_fixtures_v1 import FIXTURES_DIR

    fixtures_dir = root / FIXTURES_DIR.relative_to(REPO_ROOT)
    fixtures: list[dict[str, Any]] = []
    for entry in manifest["calibration_fixtures"]:
        fixture_id = entry["fixture_id"]
        path = fixtures_dir / f"{fixture_id}.json"
        obj = json.loads(path.read_text(encoding="utf-8"))
        fixtures.append(obj)
    return fixtures


def build_request_body(
    manifest: dict[str, Any],
    prompt: str,
    *,
    temperature: float | None = None,
) -> dict[str, Any]:
    decoding = manifest["decoding_contract"]
    if temperature is None:
        temperature = float(manifest["temperature"])
    return {
        "model": decoding["model_snapshot"],
        "input": [{"role": "user", "content": prompt}],
        "reasoning": {"effort": decoding["reasoning_effort"]},
        "temperature": temperature,
        "max_output_tokens": decoding["max_output_tokens"],
        "store": False,
        "stream": False,
    }


def request_hash(body: dict[str, Any]) -> str:
    return sha256_canon(body)


def parse_commitment_wire_text(text: str) -> object:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(stripped[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def response_has_tool_calls(raw: dict[str, Any]) -> bool:
    if raw.get("tool_calls"):
        return True
    for item in raw.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type", "")
        if item_type in ("function_call", "tool_call", "custom_tool_call"):
            return True
        if item.get("tool_calls"):
            return True
    choices = raw.get("choices") or []
    for choice in choices:
        msg = choice.get("message", {})
        if msg.get("tool_calls"):
            return True
    return False


def text_requests_external_verification(text: str) -> bool:
    return any(pattern.search(text) for pattern in VERIFICATION_SOLICITATION_PATTERNS)


def detect_solicitation(
    *,
    raw: dict[str, Any],
    text: str,
    validation_outcome: str,
) -> bool:
    del validation_outcome  # reserved for contract extension
    if response_has_tool_calls(raw):
        return True
    return text_requests_external_verification(text)


def menu_ceiling_headroom_lower_bound(
    passes: int,
    *,
    k: int,
    confidence: float,
) -> float:
    lower, _ = newcombe_diff_interval(k, k, passes, k, confidence)
    return lower


def evaluate_menu_ceiling_gate(
    rows: list[dict[str, Any]],
    params: dict[str, Any],
) -> dict[str, Any]:
    k = int(params["K"])
    confidence = float(params["confidence"])
    margin = float(params["headroom_margin"])
    b_fail = float(params["fail_condition_1_B_obs_gte"])
    scoped = [
        row
        for row in rows
        if row["lane"] == "M_task_menu"
        and row["stratum"] == "match_mismatch"
        and row.get("validation_outcome") != "budget_refusal"
    ]
    passes = sum(1 for row in scoped if row.get("oracle_outcome") == "pass")
    total = len(scoped)
    b_obs = passes / total if total else 0.0
    headroom_lb = menu_ceiling_headroom_lower_bound(
        passes, k=k, confidence=confidence
    )
    fail_direct = b_obs >= b_fail
    fail_headroom = headroom_lb < margin
    return {
        "gate": "menu_ceiling",
        "scope_stratum": "match_mismatch",
        "lane": "M_task_menu",
        "K": k,
        "passes": passes,
        "total": total,
        "B_obs": b_obs,
        "headroom_lower_bound": headroom_lb,
        "fail_condition_1": fail_direct,
        "fail_condition_2": fail_headroom,
        "passed": not (fail_direct or fail_headroom),
        "verdict": (
            "pass"
            if not (fail_direct or fail_headroom)
            else "confounded(menu_ceiling)"
        ),
    }


def evaluate_menu_only_solicitation_gate(
    rows: list[dict[str, Any]],
    ceiling: float = 0.05,
) -> dict[str, Any]:
    cells: list[dict[str, Any]] = []
    refusals: list[str] = []
    for stratum in STRATA:
        scoped = [
            row
            for row in rows
            if row["lane"] == "M_menu_only"
            and row["stratum"] == stratum
            and row.get("validation_outcome") != "budget_refusal"
        ]
        solicitations = sum(1 for row in scoped if row.get("solicitation_detected"))
        total = len(scoped)
        rate = solicitations / total if total else 0.0
        passed = rate <= ceiling
        if not passed:
            refusals.append(f"confounded(menu_induces_checking:{stratum})")
        cells.append(
            {
                "lane": "M_menu_only",
                "stratum": stratum,
                "solicitations": solicitations,
                "total": total,
                "rate": rate,
                "ceiling": ceiling,
                "passed": passed,
            }
        )
    return {
        "gate": "menu_only_solicitation",
        "cells": cells,
        "passed": not refusals,
        "verdict": "pass" if not refusals else refusals[0],
        "refusals": refusals,
    }


def _default_mock_response(context: CallContext) -> str:
    wrong = next(
        (
            label
            for label in reversed(context.action_set)
            if label != context.expected_commitment_enum
        ),
        context.action_set[0],
    )
    return json.dumps({"commitment_enum": wrong})


@dataclass
class MockTransport:
    """Deterministic canned Responses for dry-run and tests."""

    responses: dict[str, str] = field(default_factory=dict)
    usage_scale: float = 0.25
    usage_overrides: list[tuple[int, int]] | None = None
    call_count: int = 0

    def call(
        self,
        request_body: dict[str, Any],
        context: CallContext,
    ) -> TransportResult:
        self.call_count += 1
        key = f"{context.fixture_id}:{context.lane}"
        text = self.responses.get(key, _default_mock_response(context))
        req_bytes = json.dumps(request_body, sort_keys=True).encode("utf-8")
        if self.usage_overrides is not None:
            idx = self.call_count - 1
            if idx < len(self.usage_overrides):
                input_tokens, output_tokens = self.usage_overrides[idx]
            else:
                input_tokens = max(1, int(len(req_bytes) * self.usage_scale))
                output_tokens = max(1, int(len(text.encode("utf-8")) * self.usage_scale))
        else:
            input_tokens = max(1, int(len(req_bytes) * self.usage_scale))
            output_tokens = max(1, int(len(text.encode("utf-8")) * self.usage_scale))
        raw = {
            "object": "response",
            "model": request_body["model"],
            "status": "completed",
            "output_text": text,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        }
        return TransportResult(
            raw=raw,
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tool_calls_present=False,
        )


@dataclass
class FailingTransport:
    """Raises TransportRefusal on every call (probe / test vector)."""

    detail: str = "simulated_http_429"
    http_status: int = 429
    sanitized_body: dict[str, Any] | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    call_count: int = 0

    def call(
        self,
        request_body: dict[str, Any],
        context: CallContext,
    ) -> TransportResult:
        self.call_count += 1
        raise TransportRefusal(
            "transport_refusal",
            self.detail,
            http_status=self.http_status,
            sanitized_body=self.sanitized_body,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
        )


@dataclass
class RejectThenSuccessTransport:
    """First call rejects; subsequent calls succeed (probe vector)."""

    reject_detail: str = "simulated_http_429"
    reject_http_status: int = 429
    call_count: int = 0

    def call(
        self,
        request_body: dict[str, Any],
        context: CallContext,
    ) -> TransportResult:
        self.call_count += 1
        if self.call_count == 1:
            raise TransportRefusal(
                "transport_refusal",
                self.reject_detail,
                http_status=self.reject_http_status,
                sanitized_body={"error": {"message": self.reject_detail}},
            )
        return MockTransport().call(request_body, context)


@dataclass
class LiveTransport:
    """OpenAI Responses API — gated behind ``--live``."""

    def call(
        self,
        request_body: dict[str, Any],
        context: CallContext,
    ) -> TransportResult:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise TransportRefusal(
                "transport_refusal", "OPENAI_API_KEY_required_for_live"
            )
        url = f"{API_BASE}/responses"
        result = _http_post(url, request_body, api_key=api_key)
        http_status = result.get("http_status")
        data = result.get("data") or {}
        if result.get("error") or http_status != 200:
            usage = data.get("usage") or {}
            inp = usage.get("input_tokens")
            out = usage.get("output_tokens")
            raise TransportRefusal(
                "transport_refusal",
                f"http_status={http_status} error={result.get('error')}",
                http_status=http_status if isinstance(http_status, int) else None,
                sanitized_body=data if data else {"error": result.get("error")},
                input_tokens=inp if isinstance(inp, int) else 0,
                output_tokens=out if isinstance(out, int) else 0,
            )
        text = _extract_text(data)
        usage = data.get("usage") or {}
        inp = usage.get("input_tokens")
        out = usage.get("output_tokens")
        inp_tok = inp if isinstance(inp, int) else 0
        out_tok = out if isinstance(out, int) else 0
        if not text:
            raise ParseFailure(
                "transport_refusal",
                "missing_text_output",
                sanitized_body=data,
                input_tokens=inp_tok,
                output_tokens=out_tok,
            )
        if not isinstance(inp, int) or not isinstance(out, int):
            raise ParseFailure(
                "transport_refusal",
                "missing_usage_tokens",
                sanitized_body=data,
                input_tokens=inp_tok,
                output_tokens=out_tok,
            )
        input_tokens = inp
        output_tokens = out
        return TransportResult(
            raw=data,
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tool_calls_present=response_has_tool_calls(data),
        )


def render_for_lane(fixture: dict[str, Any], lane: str):
    if lane == "M_menu_only":
        return render_prompt_menu_only(fixture)
    if lane == "M_task_menu":
        return render_prompt(fixture)
    raise ValueError(f"unknown lane {lane!r}")


def _ledger_row(
    *,
    seq: int,
    fixture_id: str,
    lane: str,
    stratum: str,
    req_hash: str,
    prompt_sha256: str,
    request_body: dict[str, Any],
    transport: TransportResult | None,
    validation: dict[str, Any],
    budget: BudgetState,
    timestamp_utc: str,
    call_outcome: CallOutcome,
    over_ceiling: bool = False,
    transport_error: str | None = None,
) -> dict[str, Any]:
    usage = validation.get("usage")
    if usage is None and transport is not None:
        usage = {
            "input_tokens": transport.input_tokens,
            "output_tokens": transport.output_tokens,
        }
    return {
        "schema_version": "efc_pilot_runner_ledger_v1",
        "seq": seq,
        "timestamp_utc": timestamp_utc,
        "fixture_id": fixture_id,
        "lane": lane,
        "stratum": stratum,
        "request_hash": req_hash,
        "prompt_sha256": prompt_sha256,
        "request_body": request_body,
        "call_outcome": call_outcome,
        "over_ceiling": over_ceiling,
        "response_raw": (
            transport.raw if transport else validation.get("response_raw")
        ),
        "response_text": transport.text if transport else None,
        "transport_error": transport_error,
        "usage": usage,
        "validation_outcome": validation.get("validation_outcome"),
        "invalid_reason": validation.get("invalid_reason"),
        "oracle_outcome": validation.get("oracle_outcome"),
        "solicitation_detected": validation.get("solicitation_detected"),
        "budget_state": budget.snapshot(),
    }


def _record_transport_failure(
    *,
    exc: TransportRefusal | ParseFailure,
    call_outcome: CallOutcome,
) -> tuple[dict[str, Any], int, int, dict[str, Any] | None]:
    input_tokens = getattr(exc, "input_tokens", 0) or 0
    output_tokens = getattr(exc, "output_tokens", 0) or 0
    sanitized = getattr(exc, "sanitized_body", None)
    validation = {
        "validation_outcome": call_outcome,
        "invalid_reason": exc.detail,
        "oracle_outcome": None,
        "solicitation_detected": False,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        "response_raw": sanitized,
    }
    return validation, input_tokens, output_tokens, sanitized


def run_integrity_pilot(
    *,
    root: Path = REPO_ROOT,
    transport: Transport,
    manifest: dict[str, Any] | None = None,
    ledger_path: Path | None = None,
    run_id: str | None = None,
    timestamp_fn: Any | None = None,
) -> dict[str, Any]:
    """Execute §10.6 integrity-lanes pilot contact (30 calls)."""
    if timestamp_fn is None:
        timestamp_fn = lambda: datetime.now(timezone.utc).isoformat()
    if manifest is None:
        manifest = load_pinned_manifest(root)
    fixtures = load_fixtures(root, manifest)
    budget = load_budget_state(manifest)
    params = manifest["menu_ceiling_gate_params"]

    if ledger_path is None:
        ledger_dir = root / LEDGER_DIR_REL
        ledger_dir.mkdir(parents=True, exist_ok=True)
        run_id = run_id or datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"
        )
        ledger_path = ledger_dir / f"pilot_integrity_{run_id}.jsonl"
    elif ledger_path.exists():
        raise PilotRunnerRefusal(
            "construction_refused", "ledger_path_exists_append_only"
        )

    rows: list[dict[str, Any]] = []
    seq = 0
    outcome: Outcome = "completed"
    stop_reason: str | None = None
    stopped = False

    with ledger_path.open("w", encoding="utf-8") as ledger:
        for fixture in fixtures:
            if stopped:
                break
            fixture_id = fixture["fixture_id"]
            stratum = fixture["stratum"]
            expected = fixture["expected_commitment_enum"]
            action_set = tuple(fixture["menu_order"])
            for lane in LANES:
                rendered = render_for_lane(fixture, lane)
                body = build_request_body(manifest, rendered.prompt)
                req_hash = request_hash(body)
                ctx = CallContext(
                    fixture_id=fixture_id,
                    lane=lane,
                    stratum=stratum,
                    expected_commitment_enum=expected,
                    action_set=action_set,
                )
                projected_input = (
                    budget.input_tokens_spent
                    + estimated_input_tokens(rendered.prompt)
                )
                refusal = check_budget_guard(
                    budget, projected_input_tokens=projected_input
                )
                if refusal is not None:
                    seq += 1
                    validation = {
                        "validation_outcome": "budget_refusal",
                        "invalid_reason": refusal.detail,
                        "oracle_outcome": None,
                        "solicitation_detected": False,
                    }
                    row = _ledger_row(
                        seq=seq,
                        fixture_id=fixture_id,
                        lane=lane,
                        stratum=stratum,
                        req_hash=req_hash,
                        prompt_sha256=rendered.sha256,
                        request_body=body,
                        transport=None,
                        validation=validation,
                        budget=budget,
                        timestamp_utc=timestamp_fn(),
                        call_outcome="budget_refusal",
                    )
                    ledger.write(json.dumps(row, sort_keys=True) + "\n")
                    rows.append(row)
                    outcome = "budget_refusal"
                    stop_reason = refusal.detail
                    stopped = True
                    break

                transport_result: TransportResult | None = None
                call_outcome: CallOutcome = "completed"
                transport_error: str | None = None
                validation: dict[str, Any]

                try:
                    transport_result = transport.call(body, ctx)
                except ParseFailure as exc:
                    call_outcome = "parse_failed"
                    transport_error = exc.detail
                    validation, inp_tok, out_tok, _ = _record_transport_failure(
                        exc=exc, call_outcome="parse_failed"
                    )
                    budget.calls_spent += 1
                    budget.input_tokens_spent += inp_tok
                    budget.output_tokens_spent += out_tok
                    seq += 1
                    row = _ledger_row(
                        seq=seq,
                        fixture_id=fixture_id,
                        lane=lane,
                        stratum=stratum,
                        req_hash=req_hash,
                        prompt_sha256=rendered.sha256,
                        request_body=body,
                        transport=None,
                        validation=validation,
                        budget=budget,
                        timestamp_utc=timestamp_fn(),
                        call_outcome=call_outcome,
                        transport_error=transport_error,
                    )
                    ledger.write(json.dumps(row, sort_keys=True) + "\n")
                    rows.append(row)
                    outcome = "transport_refusal"
                    stop_reason = exc.detail
                    stopped = True
                    break
                except TransportRefusal as exc:
                    call_outcome = "transport_rejected"
                    transport_error = exc.detail
                    validation, inp_tok, out_tok, _ = _record_transport_failure(
                        exc=exc, call_outcome="transport_rejected"
                    )
                    budget.calls_spent += 1
                    budget.input_tokens_spent += inp_tok
                    budget.output_tokens_spent += out_tok
                    seq += 1
                    row = _ledger_row(
                        seq=seq,
                        fixture_id=fixture_id,
                        lane=lane,
                        stratum=stratum,
                        req_hash=req_hash,
                        prompt_sha256=rendered.sha256,
                        request_body=body,
                        transport=None,
                        validation=validation,
                        budget=budget,
                        timestamp_utc=timestamp_fn(),
                        call_outcome=call_outcome,
                        transport_error=transport_error,
                    )
                    ledger.write(json.dumps(row, sort_keys=True) + "\n")
                    rows.append(row)
                    outcome = "transport_refusal"
                    stop_reason = exc.detail
                    stopped = True
                    break

                assert transport_result is not None
                budget.calls_spent += 1
                budget.input_tokens_spent += transport_result.input_tokens
                budget.output_tokens_spent += transport_result.output_tokens

                actual_refusal = check_budget_actual(budget)
                if actual_refusal is not None:
                    validation = {
                        "validation_outcome": "budget_refusal",
                        "invalid_reason": actual_refusal.detail,
                        "oracle_outcome": None,
                        "solicitation_detected": False,
                    }
                    seq += 1
                    row = _ledger_row(
                        seq=seq,
                        fixture_id=fixture_id,
                        lane=lane,
                        stratum=stratum,
                        req_hash=req_hash,
                        prompt_sha256=rendered.sha256,
                        request_body=body,
                        transport=transport_result,
                        validation=validation,
                        budget=budget,
                        timestamp_utc=timestamp_fn(),
                        call_outcome="over_ceiling",
                        over_ceiling=True,
                    )
                    ledger.write(json.dumps(row, sort_keys=True) + "\n")
                    rows.append(row)
                    outcome = "budget_refusal"
                    stop_reason = actual_refusal.detail
                    stopped = True
                    break

                wire = parse_commitment_wire_text(transport_result.text)
                validated = validate_commitment_wire(wire, list(action_set))
                oracle = score_commitment_oracle_v1(validated, expected)
                solicitation = detect_solicitation(
                    raw=transport_result.raw,
                    text=transport_result.text,
                    validation_outcome=validated.outcome,
                )
                validation = {
                    "validation_outcome": validated.outcome,
                    "invalid_reason": validated.invalid_reason,
                    "oracle_outcome": oracle.outcome,
                    "solicitation_detected": solicitation,
                }
                seq += 1
                row = _ledger_row(
                    seq=seq,
                    fixture_id=fixture_id,
                    lane=lane,
                    stratum=stratum,
                    req_hash=req_hash,
                    prompt_sha256=rendered.sha256,
                    request_body=body,
                    transport=transport_result,
                    validation=validation,
                    budget=budget,
                    timestamp_utc=timestamp_fn(),
                    call_outcome="completed",
                )
                ledger.write(json.dumps(row, sort_keys=True) + "\n")
                rows.append(row)

            if stopped:
                break
        if outcome == "completed" and len(rows) < len(fixtures) * len(LANES):
            outcome = "transport_refusal"

    menu_ceiling = evaluate_menu_ceiling_gate(rows, params)
    menu_only = evaluate_menu_only_solicitation_gate(rows)

    return {
        "status": outcome,
        "stop_reason": stop_reason,
        "ledger_path": (
            str(ledger_path.relative_to(root))
            if str(ledger_path).startswith(str(root))
            else str(ledger_path)
        ),
        "invocations": len(
            [r for r in rows if r.get("call_outcome") == "completed"]
        ),
        "rows_written": len(rows),
        "budget_final": budget.snapshot(),
        "disclosure": list(RUNNER_DISCLOSURES),
        "gates": {
            "menu_ceiling": menu_ceiling,
            "menu_only_solicitation": menu_only,
        },
        "manifest_hash_canonical": manifest_hash(manifest),
        "pin_event_id": PIN_EVENT_ID,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="EFC v1 integrity-lanes pilot runner (§10.6)"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use LiveTransport (requires --pin-event-id)",
    )
    parser.add_argument(
        "--pin-event-id",
        default=None,
        help="Required pin event id for --live contact",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Ledger output path (must not exist)",
    )
    parser.add_argument(
        "--run-id",
        default="dryrun",
        help="Run identifier for ledger filename",
    )
    args = parser.parse_args(argv)

    if args.live:
        if args.pin_event_id != PIN_EVENT_ID:
            print(
                f"refused: --live requires --pin-event-id {PIN_EVENT_ID}",
                file=sys.stderr,
            )
            return 2

    try:
        manifest = load_pinned_manifest(REPO_ROOT)
    except PilotRunnerRefusal as exc:
        print(f"refused: {exc.reason}:{exc.detail}", file=sys.stderr)
        return 1

    transport: Transport
    if args.live:
        transport = LiveTransport()
    else:
        transport = MockTransport()

    ledger_path = Path(args.output) if args.output else None
    try:
        result = run_integrity_pilot(
            root=REPO_ROOT,
            transport=transport,
            manifest=manifest,
            ledger_path=ledger_path,
            run_id=args.run_id,
        )
    except PilotRunnerRefusal as exc:
        print(f"refused: {exc.reason}:{exc.detail}", file=sys.stderr)
        return 1
    except TransportRefusal as exc:
        print(f"refused: {exc.reason}:{exc.detail}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
