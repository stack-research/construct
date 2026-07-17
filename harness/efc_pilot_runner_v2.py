"""EFC v2 admission pilot runner — SPEC §C pre-engine protocol.

Deterministic dry-run (MockTransport) only. Live engine contact is
structurally unconstructible: no LiveTransport and no network imports.

Normative contract: ``harness/efc_pilot_runner_contract_v2.md``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Protocol

from harness.efc_admission_gate_v2 import (
    PART_I_SPEC_SHA256,
    AdmissionOutcome,
    evaluate_admission_gate,
)
from harness.efc_commitment_oracle_v2 import score_commitment_oracle_v2
from harness.efc_commitment_wire_v2 import validate_commitment_wire
from harness.efc_fixtures_v2 import FIXTURES_DIR, RELEVANT_STRATA
from harness.efc_manifest_v2 import (
    MANIFEST_RELPATH,
    REPO_ROOT,
    manifest_hash,
    manifest_verify,
    sha256_path,
)
from harness.efc_render_v2 import render_for_lane

CONTRACT_RELPATH = "harness/efc_pilot_runner_contract_v2.md"
PIN_SIDECAR_RELPATH = "corpus/efc_calibration_v2/manifest_pin.json"
LEDGER_DIR_REL = "runs/efc_calibration_v2"

LANES = ("M_untreated", "M_forced_class", "M_irrelevant")
FORCED_CLASSES = ("commit", "non_commit")

VERIFICATION_SOLICITATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bverify\b", re.IGNORECASE),
    re.compile(r"\bexternal\s+verification\b", re.IGNORECASE),
)

Outcome = Literal[
    "completed",
    "construction_refused",
    "budget_refusal",
    "transport_refusal",
] | AdmissionOutcome

CallOutcome = Literal[
    "completed",
    "budget_refusal",
    "over_ceiling",
    "transport_rejected",
    "parse_failed",
]

RUNNER_DISCLOSURES: tuple[str, ...] = (
    "v2 runner: MockTransport only; live contact authorization is "
    "structurally unconstructible.",
    "Pre-call input estimate (utf8_len//4) is a disclosed first-line floor.",
)


@dataclass(frozen=True)
class LoadedPinManifest:
    manifest: dict[str, Any]
    pin_event_id: str
    manifest_path: str
    pin_sidecar_path: str

    @property
    def manifest_hash_canonical(self) -> str:
        return manifest_hash(self.manifest)


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
    supplied_class: str | None = None


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
    return max(1, (len(prompt.encode("utf-8")) + 3) // 4)


def default_budget_state() -> BudgetState:
    """Conservative ceiling for dry-run when manifest omits budget_ledger."""
    return BudgetState(
        calls_spent=0,
        input_tokens_spent=0,
        output_tokens_spent=0,
        input_token_ceiling=500_000,
        output_token_ceiling=200_000,
        total_call_ceiling=50_000,
        max_output_tokens_per_request=256,
        hard_cost_ceiling_usd=100.0,
        input_usd_per_million=2.50,
        output_usd_per_million=15.00,
    )


def load_budget_state(manifest: dict[str, Any]) -> BudgetState:
    budget = manifest.get("budget_ledger")
    if not isinstance(budget, dict):
        return default_budget_state()
    pricing = budget.get("pricing", {})
    return BudgetState(
        calls_spent=int(budget.get("calls_already_spent", 0)),
        input_tokens_spent=int(budget.get("opening_input_tokens_spent", 0)),
        output_tokens_spent=int(budget.get("opening_output_tokens_spent", 0)),
        input_token_ceiling=int(budget.get("input_token_ceiling", 500_000)),
        output_token_ceiling=int(budget.get("output_token_ceiling", 200_000)),
        total_call_ceiling=int(budget.get("total_call_ceiling", 50_000)),
        max_output_tokens_per_request=int(
            budget.get("max_output_tokens_per_request", 256)
        ),
        hard_cost_ceiling_usd=float(budget.get("hard_cost_ceiling_usd", 100.0)),
        input_usd_per_million=float(pricing.get("input_usd_per_million", 2.50)),
        output_usd_per_million=float(pricing.get("output_usd_per_million", 15.00)),
    )


def check_budget_guard(
    state: BudgetState,
    *,
    projected_input_tokens: int,
) -> BudgetRefusal | None:
    if state.calls_spent >= state.total_call_ceiling:
        return BudgetRefusal("budget_refusal", "total_call_ceiling", pool="calls")
    if projected_input_tokens > state.input_token_ceiling:
        return BudgetRefusal("budget_refusal", "input_token_ceiling", pool="input")
    return None


def check_budget_actual(state: BudgetState) -> BudgetRefusal | None:
    if state.input_tokens_spent > state.input_token_ceiling:
        return BudgetRefusal("budget_refusal", "input_token_ceiling_exceeded", pool="input")
    if state.output_tokens_spent > state.output_token_ceiling:
        return BudgetRefusal("budget_refusal", "output_token_ceiling_exceeded", pool="output")
    if state.cost_usd() > state.hard_cost_ceiling_usd:
        return BudgetRefusal("budget_refusal", "hard_cost_ceiling_exceeded", pool="cost")
    return None


def verify_pin_sidecar(
    root: Path,
    manifest: dict[str, Any],
    *,
    manifest_relpath: str,
    pin_sidecar_relpath: str,
) -> tuple[bool, str]:
    pin_path = root / pin_sidecar_relpath
    if not pin_path.is_file():
        return False, "pin_sidecar_missing"
    pin = json.loads(pin_path.read_text(encoding="utf-8"))
    canonical = manifest_hash(manifest)
    if pin.get("manifest_hash_canonical") != canonical:
        return False, "pin_hash_mismatch:manifest_hash_canonical"
    raw_sha = sha256_path(root / manifest_relpath)
    if pin.get("manifest_file_sha256_raw") != raw_sha:
        return False, "pin_hash_mismatch:manifest_file_sha256_raw"
    if pin.get("manifest_path") != manifest_relpath:
        return False, "pin_sidecar_path_mismatch"
    return True, ""


def load_pinned_manifest(
    root: Path = REPO_ROOT,
    *,
    manifest_path: str | None = None,
    pin_sidecar_path: str | None = None,
    require_pin: bool = True,
) -> LoadedPinManifest:
    manifest_relpath = manifest_path or MANIFEST_RELPATH
    pin_relpath = pin_sidecar_path or PIN_SIDECAR_RELPATH
    manifest_file = root / manifest_relpath
    if not manifest_file.is_file():
        raise PilotRunnerRefusal("construction_refused", "manifest_missing")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("part_i_spec_sha256") != PART_I_SPEC_SHA256:
        raise PilotRunnerRefusal("construction_refused", "part_i_spec_sha256_mismatch")
    verify = manifest_verify(root, manifest, require_suite_hash=True)
    if not verify.ok:
        raise PilotRunnerRefusal(
            "construction_refused",
            "manifest_verify_failed:" + ";".join(verify.failures[:5]),
        )
    if require_pin:
        ok, reason = verify_pin_sidecar(
            root,
            manifest,
            manifest_relpath=manifest_relpath,
            pin_sidecar_relpath=pin_relpath,
        )
        if not ok:
            raise PilotRunnerRefusal("construction_refused", reason)
        pin = json.loads((root / pin_relpath).read_text(encoding="utf-8"))
        pin_event_id = pin.get("pin_event_id", "")
        if not isinstance(pin_event_id, str) or not pin_event_id:
            raise PilotRunnerRefusal(
                "construction_refused", "pin_sidecar_missing_pin_event_id"
            )
    else:
        pin_event_id = ""
    return LoadedPinManifest(
        manifest=manifest,
        pin_event_id=pin_event_id,
        manifest_path=manifest_relpath,
        pin_sidecar_path=pin_relpath,
    )


def load_fixtures(root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    fixtures_dir = root / FIXTURES_DIR.relative_to(REPO_ROOT)
    fixtures: list[dict[str, Any]] = []
    for entry in manifest.get("calibration_fixtures", []):
        fixture_id = entry["fixture_id"]
        path = fixtures_dir / f"{fixture_id}.json"
        fixtures.append(json.loads(path.read_text(encoding="utf-8")))
    return fixtures


def build_request_body(manifest: dict[str, Any], prompt: str) -> dict[str, Any]:
    decoding = manifest.get("decoding_contract", {})
    budget = manifest.get("budget_ledger", {})
    return {
        "model": decoding.get("model_snapshot", "dry-run"),
        "input": [{"role": "user", "content": prompt}],
        "reasoning": {"effort": decoding.get("reasoning_effort", "high")},
        "temperature": float(manifest.get("temperature", 0.0)),
        "max_output_tokens": int(
            budget.get("max_output_tokens_per_request", 256)
            if isinstance(budget, dict) else 256
        ),
        "store": False,
        "stream": False,
    }


def request_hash(body: dict[str, Any]) -> str:
    from harness.efc_manifest_v2 import sha256_canon
    return sha256_canon(body)


def parse_commitment_wire_text(text: str) -> object:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def response_has_tool_calls(raw: dict[str, Any]) -> bool:
    if raw.get("tool_calls"):
        return True
    for choice in raw.get("choices") or []:
        if choice.get("message", {}).get("tool_calls"):
            return True
    return False


def detect_solicitation(*, raw: dict[str, Any], text: str) -> bool:
    if response_has_tool_calls(raw):
        return True
    return any(p.search(text) for p in VERIFICATION_SOLICITATION_PATTERNS)


def _default_mock_response(context: CallContext) -> str:
    if context.lane == "M_forced_class" and context.supplied_class:
        role_map_labels = [
            label for label in context.action_set
        ]
        for label in role_map_labels:
            if label == context.expected_commitment_enum:
                return json.dumps({"commitment_enum": label})
    wrong = next(
        (label for label in reversed(context.action_set)
         if label != context.expected_commitment_enum),
        context.action_set[0],
    )
    return json.dumps({"commitment_enum": wrong})


@dataclass
class MockTransport:
    """Deterministic canned responses for dry-run and tests."""

    responses: dict[str, str] = field(default_factory=dict)
    usage_scale: float = 0.25
    call_count: int = 0

    def call(
        self,
        request_body: dict[str, Any],
        context: CallContext,
    ) -> TransportResult:
        self.call_count += 1
        key = f"{context.fixture_id}:{context.lane}"
        if context.supplied_class:
            key = f"{key}:{context.supplied_class}"
        text = self.responses.get(key, _default_mock_response(context))
        req_bytes = json.dumps(request_body, sort_keys=True).encode("utf-8")
        input_tokens = max(1, int(len(req_bytes) * self.usage_scale))
        output_tokens = max(1, int(len(text.encode("utf-8")) * self.usage_scale))
        raw = {
            "object": "response",
            "model": request_body.get("model", "dry-run"),
            "status": "completed",
            "output_text": text,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
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
    detail: str = "simulated_transport_refusal"
    call_count: int = 0

    def call(
        self,
        request_body: dict[str, Any],
        context: CallContext,
    ) -> TransportResult:
        self.call_count += 1
        raise TransportRefusal("transport_refusal", self.detail)


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
    supplied_class: str | None = None,
    over_ceiling: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": "efc_pilot_runner_ledger_v2",
        "seq": seq,
        "timestamp_utc": timestamp_utc,
        "fixture_id": fixture_id,
        "lane": lane,
        "stratum": stratum,
        "supplied_class": supplied_class,
        "request_hash": req_hash,
        "prompt_sha256": prompt_sha256,
        "request_body": request_body,
        "call_outcome": call_outcome,
        "over_ceiling": over_ceiling,
        "response_raw": transport.raw if transport else None,
        "response_text": transport.text if transport else None,
        "usage": (
            {
                "input_tokens": transport.input_tokens,
                "output_tokens": transport.output_tokens,
            }
            if transport
            else None
        ),
        "validation_outcome": validation.get("validation_outcome"),
        "invalid_reason": validation.get("invalid_reason"),
        "oracle_outcome": validation.get("oracle_outcome"),
        "commitment_enum": validation.get("commitment_enum"),
        "solicitation_detected": validation.get("solicitation_detected"),
        "budget_state": budget.snapshot(),
    }


def _iter_call_specs(
    fixtures: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], str, str | None]]:
    """Expand fixtures into (fixture, lane, supplied_class) call specs."""
    specs: list[tuple[dict[str, Any], str, str | None]] = []
    for fixture in fixtures:
        stratum = fixture["stratum"]
        if stratum in RELEVANT_STRATA:
            specs.append((fixture, "M_untreated", None))
            for cls in FORCED_CLASSES:
                specs.append((fixture, "M_forced_class", cls))
        else:
            specs.append((fixture, "M_irrelevant", None))
    return specs


def run_admission_pilot(
    *,
    root: Path = REPO_ROOT,
    transport: Transport,
    manifest: dict[str, Any] | None = None,
    fixtures: list[dict[str, Any]] | None = None,
    loaded: LoadedPinManifest | None = None,
    ledger_path: Path | None = None,
    run_id: str | None = None,
    timestamp_fn: Any | None = None,
) -> dict[str, Any]:
    """Execute v2 admission-lane contact (MockTransport only)."""
    if timestamp_fn is None:
        timestamp_fn = lambda: datetime.now(timezone.utc).isoformat()
    if loaded is not None:
        manifest = loaded.manifest
    elif manifest is None:
        loaded = load_pinned_manifest(root, require_pin=False)
        manifest = loaded.manifest
    if fixtures is None:
        fixtures = load_fixtures(root, manifest)
    budget = load_budget_state(manifest)

    if ledger_path is None:
        ledger_dir = root / LEDGER_DIR_REL
        ledger_dir.mkdir(parents=True, exist_ok=True)
        run_id = run_id or "dryrun"
        ledger_path = ledger_dir / f"admission_pilot_{run_id}.jsonl"
    elif ledger_path.exists():
        raise PilotRunnerRefusal(
            "construction_refused", "ledger_path_exists_append_only"
        )

    rendered_surfaces = {
        f["fixture_id"]: render_for_lane(f, "M_untreated").prompt
        for f in fixtures
        if f.get("stratum") in RELEVANT_STRATA
    }

    rows: list[dict[str, Any]] = []
    seq = 0
    outcome: Outcome = "completed"
    stop_reason: str | None = None
    stopped = False

    with ledger_path.open("w", encoding="utf-8") as ledger:
        for fixture, lane, supplied_class in _iter_call_specs(fixtures):
            if stopped:
                break
            fixture_id = fixture["fixture_id"]
            stratum = fixture["stratum"]
            expected = fixture["expected_commitment_enum"]
            action_set = tuple(fixture["menu_order"])
            rendered = render_for_lane(
                fixture, lane, supplied_class=supplied_class
            )
            body = build_request_body(manifest, rendered.prompt)
            req_hash = request_hash(body)
            ctx = CallContext(
                fixture_id=fixture_id,
                lane=lane,
                stratum=stratum,
                expected_commitment_enum=expected,
                action_set=action_set,
                supplied_class=supplied_class,
            )
            projected = budget.input_tokens_spent + estimated_input_tokens(
                rendered.prompt
            )
            refusal = check_budget_guard(budget, projected_input_tokens=projected)
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
                    supplied_class=supplied_class,
                )
                ledger.write(json.dumps(row, sort_keys=True) + "\n")
                rows.append(row)
                outcome = "budget_refusal"
                stop_reason = refusal.detail
                stopped = True
                break

            try:
                transport_result = transport.call(body, ctx)
            except TransportRefusal as exc:
                seq += 1
                validation = {
                    "validation_outcome": "transport_rejected",
                    "invalid_reason": exc.detail,
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
                    call_outcome="transport_rejected",
                    supplied_class=supplied_class,
                )
                ledger.write(json.dumps(row, sort_keys=True) + "\n")
                rows.append(row)
                outcome = "transport_refusal"
                stop_reason = exc.detail
                stopped = True
                break

            budget.calls_spent += 1
            budget.input_tokens_spent += transport_result.input_tokens
            budget.output_tokens_spent += transport_result.output_tokens

            actual_refusal = check_budget_actual(budget)
            if actual_refusal is not None:
                seq += 1
                validation = {
                    "validation_outcome": "budget_refusal",
                    "invalid_reason": actual_refusal.detail,
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
                    transport=transport_result,
                    validation=validation,
                    budget=budget,
                    timestamp_utc=timestamp_fn(),
                    call_outcome="over_ceiling",
                    supplied_class=supplied_class,
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
            oracle = score_commitment_oracle_v2(validated, expected)
            solicitation = detect_solicitation(
                raw=transport_result.raw,
                text=transport_result.text,
            )
            validation = {
                "validation_outcome": validated.outcome,
                "invalid_reason": validated.invalid_reason,
                "oracle_outcome": oracle.outcome,
                "commitment_enum": validated.commitment_enum,
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
                supplied_class=supplied_class,
            )
            ledger.write(json.dumps(row, sort_keys=True) + "\n")
            rows.append(row)

    gate_report = evaluate_admission_gate(
        rows=rows,
        fixtures=fixtures,
        manifest=manifest,
        rendered_surfaces=rendered_surfaces,
    )
    if outcome == "completed" and not gate_report.passed:
        outcome = gate_report.verdict  # type: ignore[assignment]

    return {
        "status": outcome,
        "stop_reason": stop_reason,
        "ledger_path": str(ledger_path),
        "admission_gate": {
            "passed": gate_report.passed,
            "verdict": gate_report.verdict,
            "derived_ub": gate_report.derived_ub,
            "gates": [
                {"gate": g.gate, "passed": g.passed, "verdict": g.verdict}
                for g in gate_report.gates
            ],
        },
        "call_count": len(rows),
        "runner_disclosures": list(RUNNER_DISCLOSURES),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="EFC v2 admission pilot runner (MockTransport only)"
    )
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--pin-sidecar", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--run-id", default="dryrun")
    args = parser.parse_args(argv)

    try:
        loaded = load_pinned_manifest(
            REPO_ROOT,
            manifest_path=args.manifest,
            pin_sidecar_path=args.pin_sidecar,
            require_pin=False,
        )
    except PilotRunnerRefusal as exc:
        print(f"refused: {exc.reason}:{exc.detail}", file=sys.stderr)
        return 1

    transport: Transport = MockTransport()
    ledger_path = Path(args.output) if args.output else None
    try:
        result = run_admission_pilot(
            root=REPO_ROOT,
            transport=transport,
            loaded=loaded,
            ledger_path=ledger_path,
            run_id=args.run_id,
        )
    except PilotRunnerRefusal as exc:
        print(f"refused: {exc.reason}:{exc.detail}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
