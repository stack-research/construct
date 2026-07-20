"""Admission-only runner for the frontier-obligation paired battery.

Mock execution is wire evidence only. Real local contact requires a separately
reviewed execution pin whose exact hash appears in an ended Substrate review.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .frontier_obligation_admission import (
    MAX_CALLS,
    MAX_OUTPUT_TOKENS_PER_CALL,
    PACKET_DIR,
    PACKET_INDEX_SHA256,
    ROOT,
    action_set,
    build_request_body,
    canonical_sha256,
    derive_expected_label,
    derive_expected_role,
    file_sha256,
    fixtures,
    packet_gate_open,
    render_prompt,
    validate_wire,
)


FORBIDDEN_ENGINE_IDENTITIES = frozenset({
    "cursor/grok-4.5",
    "cursor/composer-2.5",
    "grok-4.5",
    "composer-2.5",
    "cursor-grok-4.5-high",
    "gpt-5.6-sol",
})
IMPLEMENTATION_MANIFEST = (
    ROOT / "harness" / "frontier_obligation_admission_manifest.json"
)


@dataclass(frozen=True)
class CallResult:
    raw_answer: str
    observed_model: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    tool_calls_present: bool
    raw_response_sha256: str


class Transport(Protocol):
    backend_name: str

    def call(self, prompt: str, fixture: dict[str, Any]) -> CallResult:
        ...


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _normalized_identity(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def identity_allowed(*values: str) -> bool:
    normalized = {_normalized_identity(value) for value in values if value}
    return not any(
        value in FORBIDDEN_ENGINE_IDENTITIES
        or value.endswith("/grok-4.5")
        or value.endswith("/composer-2.5")
        or "cursor-grok-4.5" in value
        for value in normalized
    )


class MockTransport:
    backend_name = "mock"

    def __init__(self, model: str):
        self.model = model

    def call(self, prompt: str, fixture: dict[str, Any]) -> CallResult:
        del prompt
        started = time.monotonic()
        answer = json.dumps(
            {"commitment_enum": derive_expected_label(fixture)},
            separators=(",", ":"),
        )
        raw = {
            "model": "mock-engine-v1",
            "choices": [{"message": {"content": answer}}],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": len(answer.split()),
            },
        }
        return CallResult(
            raw_answer=answer,
            observed_model="mock-engine-v1",
            latency_ms=int((time.monotonic() - started) * 1000),
            prompt_tokens=0,
            completion_tokens=len(answer.split()),
            tool_calls_present=False,
            raw_response_sha256=canonical_sha256(raw),
        )


class LocalTransport:
    backend_name = "local_openai_compat"

    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def verify_model_available(self) -> None:
        request = urllib.request.Request(f"{self.base_url}/models")
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = json.loads(response.read())
        data = raw.get("data") if isinstance(raw, dict) else None
        ids = {
            str(row.get("id"))
            for row in data or []
            if isinstance(row, dict) and row.get("id")
        }
        if self.model not in ids:
            raise ValueError(
                f"requested model is not listed at the pinned endpoint: {self.model}"
            )

    def call(self, prompt: str, fixture: dict[str, Any]) -> CallResult:
        del fixture
        body = build_request_body(self.model, prompt)
        encoded = json.dumps(body).encode()
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=encoded,
            headers={"Content-Type": "application/json"},
        )
        started = time.monotonic()
        with urllib.request.urlopen(request, timeout=300) as response:
            raw_bytes = response.read()
        latency_ms = int((time.monotonic() - started) * 1000)
        raw = json.loads(raw_bytes)
        choices = raw.get("choices") or []
        if len(choices) != 1 or not isinstance(choices[0], dict):
            raise ValueError("transport returned a non-singleton choices list")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise ValueError("transport returned no message object")
        content = message.get("content")
        answer = content if isinstance(content, str) else ""
        usage = raw.get("usage") or {}
        tool_calls = bool(message.get("tool_calls"))
        return CallResult(
            raw_answer=answer.strip(),
            observed_model=str(raw.get("model") or self.model),
            latency_ms=latency_ms,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            tool_calls_present=tool_calls,
            raw_response_sha256=__import__("hashlib").sha256(raw_bytes).hexdigest(),
        )


def _transport(
    *,
    engine_backend: str,
    model: str,
    base_url: str,
) -> Transport:
    if engine_backend == "mock":
        return MockTransport(model)
    if engine_backend == "local":
        return LocalTransport(model, base_url)
    raise ValueError(f"unknown admission backend {engine_backend!r}")


def _row(
    fixture: dict[str, Any],
    prompt: str,
    request_body: dict[str, Any],
    result: CallResult,
) -> dict[str, Any]:
    wire = validate_wire(
        result.raw_answer,
        fixture,
        tool_calls_present=result.tool_calls_present,
    )
    expected = derive_expected_label(fixture)
    return {
        "fixture_id": fixture["fixture_id"],
        "pair_id": fixture["pair_id"],
        "member": fixture["member"],
        "artifact_id": fixture["artifact_id"],
        "prompt_sha256": __import__("hashlib").sha256(prompt.encode()).hexdigest(),
        "request_sha256": canonical_sha256(request_body),
        "action_set": action_set(fixture),
        "raw_answer": result.raw_answer,
        "raw_answer_sha256": __import__("hashlib").sha256(
            result.raw_answer.encode()
        ).hexdigest(),
        "raw_response_sha256": result.raw_response_sha256,
        "extraction_mode": wire.extraction_mode,
        "extracted_wire": wire.extracted,
        "validation_outcome": wire.outcome,
        "invalid_reason": wire.invalid_reason,
        "selection": wire.selection,
        "expected_role": derive_expected_role(fixture),
        "expected_selection": expected,
        "correct": wire.outcome == "commitment_valid" and wire.selection == expected,
        "tool_calls_present": result.tool_calls_present,
        "observed_model": result.observed_model,
        "latency_ms": result.latency_ms,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
    }


def run_admission(
    *,
    engine_backend: str,
    model: str,
    base_url: str = "http://localhost:1234/v1",
    reasoning_mode: str = "none_nonreasoning_model",
    execution_pin_sha256: str | None = None,
    execution_pin_path: str | None = None,
) -> dict[str, Any]:
    if not packet_gate_open():
        raise ValueError("admission packet exact-byte gate is closed")
    if engine_backend != "mock" and not identity_allowed(model):
        raise ValueError("requested engine identity is excluded")
    transport = _transport(
        engine_backend=engine_backend,
        model=model,
        base_url=base_url,
    )
    rows: list[dict[str, Any]] = []
    status = "complete"
    refusal: dict[str, Any] | None = None
    calls_attempted = 0
    if isinstance(transport, LocalTransport):
        try:
            transport.verify_model_available()
        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
            urllib.error.URLError,
        ) as exc:
            status = "transport_refused"
            refusal = {
                "fixture_id": None,
                "reason": type(exc).__name__,
                "detail": str(exc),
            }
    for fixture in fixtures():
        if status != "complete":
            break
        prompt = render_prompt(fixture)
        request_body = build_request_body(model, prompt)
        calls_attempted += 1
        try:
            result = transport.call(prompt, fixture)
        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
            urllib.error.URLError,
        ) as exc:
            status = "transport_refused"
            refusal = {
                "fixture_id": fixture["fixture_id"],
                "reason": type(exc).__name__,
                "detail": str(exc),
            }
            break
        rows.append(_row(fixture, prompt, request_body, result))
        observed = {row["observed_model"] for row in rows}
        if len(observed) != 1:
            status = "identity_refused"
            refusal = {
                "fixture_id": fixture["fixture_id"],
                "reason": "observed_model_changed",
                "detail": sorted(observed),
            }
            break
    observed_models = {
        row["observed_model"] for row in rows if row.get("observed_model")
    }
    observed_model = (
        next(iter(observed_models)) if len(observed_models) == 1 else ""
    )
    return {
        "receipt_id": f"frontier-obligation-admission-{int(time.time())}",
        "created_at": _utc_now(),
        "contact_class": "admission_only_not_evidence",
        "wire_only": engine_backend == "mock",
        "packet_index_sha256": PACKET_INDEX_SHA256,
        "renderer_sha256": file_sha256(PACKET_DIR / "renderer_contract.json"),
        "response_contract_sha256": file_sha256(
            PACKET_DIR / "response_contract.json"
        ),
        "decision_rule_sha256": file_sha256(PACKET_DIR / "decision_rule.txt"),
        "engine_backend": transport.backend_name,
        "engine_backend_cli": engine_backend,
        "requested_model": model,
        "observed_model": observed_model,
        "base_url": base_url,
        "temperature": 0,
        "reasoning_mode": reasoning_mode,
        "execution_pin_sha256": execution_pin_sha256,
        "execution_pin_path": execution_pin_path,
        "max_output_tokens_per_call": MAX_OUTPUT_TOKENS_PER_CALL,
        "max_calls": MAX_CALLS,
        "status": status,
        "calls_attempted": calls_attempted,
        "calls_completed": len(rows),
        "prompt_tokens_total": sum(row["prompt_tokens"] for row in rows),
        "completion_tokens_total": sum(
            row["completion_tokens"] for row in rows
        ),
        "rows": rows,
        "refusal": refusal,
    }


def _review_entry_endorses(path: Path, exact_hash: str) -> bool:
    text = path.read_text()
    return exact_hash in text and (
        "**ENDORSE**" in text or "## ENDORSE" in text
    )


def _verify_exact_review(
    *,
    thread_slug: str,
    exact_hash: str,
    moderator_phrase: str,
    review_name: str,
) -> None:
    thread = ROOT / ".substrate" / "threads" / thread_slug
    config = thread / "config.yaml"
    if not config.is_file() or "status: ended" not in config.read_text():
        raise ValueError(f"{review_name} is not ended")
    for participant in ("cursor%2Fgrok-4.5", "cursor%2Fcomposer-2.5"):
        entries = list(thread.glob(f"*__{participant}.md"))
        if len(entries) != 1 or not _review_entry_endorses(entries[0], exact_hash):
            raise ValueError(
                f"{review_name} lacks exact endorsement from {participant}"
            )
    moderator = [
        path
        for path in thread.glob("*__codex.md")
        if exact_hash in path.read_text()
        and moderator_phrase in path.read_text()
    ]
    if len(moderator) != 1:
        raise ValueError(f"{review_name} lacks exact moderator endorsement")


def verify_execution_pin(
    pin_path: Path,
    *,
    exact_hash: str,
    out_path: Path,
) -> dict[str, Any]:
    if file_sha256(pin_path) != exact_hash:
        raise ValueError("execution pin hash mismatch")
    pin = json.loads(pin_path.read_text())
    if not isinstance(pin, dict):
        raise ValueError("execution pin must be an object")
    required = {
        "packet_index_sha256": PACKET_INDEX_SHA256,
        "implementation_manifest_sha256": (
            file_sha256(IMPLEMENTATION_MANIFEST)
            if IMPLEMENTATION_MANIFEST.is_file()
            else "missing"
        ),
        "engine_backend": "local",
        "temperature": 0,
        "reasoning_mode": "none_nonreasoning_model",
        "max_output_tokens_per_call": MAX_OUTPUT_TOKENS_PER_CALL,
        "max_calls": MAX_CALLS,
        "retries": 0,
        "terminal_candidate": True,
        "receipt_path": str(out_path.relative_to(ROOT)),
    }
    mismatches = {
        key: {"expected": value, "observed": pin.get(key)}
        for key, value in required.items()
        if pin.get(key) != value
    }
    if mismatches:
        raise ValueError(
            f"execution pin fields mismatch: {json.dumps(mismatches, sort_keys=True)}"
        )
    model = str(pin.get("model", ""))
    base_url = str(pin.get("base_url", ""))
    if not model or not base_url or not identity_allowed(model):
        raise ValueError("execution pin candidate identity is missing or excluded")
    implementation_review_thread = str(
        pin.get("implementation_review_thread", "")
    )
    if not implementation_review_thread:
        raise ValueError("implementation wire-review thread is missing")
    _verify_exact_review(
        thread_slug=implementation_review_thread,
        exact_hash=file_sha256(IMPLEMENTATION_MANIFEST),
        moderator_phrase="wire gate **ENDORSED**",
        review_name="implementation wire review",
    )
    thread_slug = str(pin.get("review_thread", ""))
    if not thread_slug:
        raise ValueError("execution pin review thread is missing")
    _verify_exact_review(
        thread_slug=thread_slug,
        exact_hash=exact_hash,
        moderator_phrase="pin gate **ENDORSED**",
        review_name="execution pin review",
    )
    return pin


def atomic_write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temp.open("x") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run frontier-obligation admission packet"
    )
    parser.add_argument("--engine", required=True, choices=["mock", "local"])
    parser.add_argument("--model")
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument("--reasoning-mode", default="none_nonreasoning_model")
    parser.add_argument("--execution-pin")
    parser.add_argument("--pin-sha256")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    target = Path(args.out).resolve()
    try:
        if not target.is_relative_to(ROOT):
            raise ValueError("receipt path must be inside the repository")
        model = args.model
        base_url = args.base_url
        reasoning_mode = args.reasoning_mode
        if args.engine == "local":
            if not args.execution_pin or not args.pin_sha256:
                raise ValueError("local contact requires an exact execution pin")
            pin_path = Path(args.execution_pin).resolve()
            if not pin_path.is_relative_to(ROOT):
                raise ValueError("execution pin must be inside the repository")
            pin = verify_execution_pin(
                pin_path,
                exact_hash=args.pin_sha256,
                out_path=target,
            )
            model = str(pin["model"])
            base_url = str(pin["base_url"])
            reasoning_mode = str(pin["reasoning_mode"])
        if not model:
            raise ValueError("--model is required for mock execution")
        receipt = run_admission(
            engine_backend=args.engine,
            model=model,
            base_url=base_url,
            reasoning_mode=reasoning_mode,
            execution_pin_sha256=(
                args.pin_sha256 if args.engine == "local" else None
            ),
            execution_pin_path=(
                str(pin_path.relative_to(ROOT))
                if args.engine == "local"
                else None
            ),
        )
        atomic_write_new(target, receipt)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    print(f"Frontier-obligation admission receipt: {target.relative_to(ROOT)}")
    print("DISCLOSED: admission-only; not memory evidence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
