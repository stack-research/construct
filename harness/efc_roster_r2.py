"""R2 non-fixture decoding-surface wire checks — roster verification only."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
R1_ARTIFACT = REPO / "corpus/efc_calibration/roster/roster_enumeration_r1.json"
OUT_PATH = REPO / "corpus/efc_calibration/roster/decoding_surface_r2.json"

WIRE_PROMPT = "Return exactly the single word ACK."
LOCAL_BASE = "http://localhost:1234/v1"
LOCAL_MODEL = "openai/gpt-oss-20b"
API_BASE = "https://api.openai.com/v1"
API_MODEL = "gpt-5.4-2026-03-05"
OUTPUT_CEILING = 2048

# Frozen before contact from official GPT-5.4 Responses docs: sampling params
# (temperature, top_p) are used when reasoning.effort is none.
API_TOP_P_INCLUDED = True

PINNED_ARTIFACT_SHA256 = (
    "ac76d1769911eb61a0d39f5c9766a862090467ea3e4d2d0ab7c4da2b5d4ac208"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_canon(obj: Any) -> str:
    return sha256_bytes(json.dumps(obj, sort_keys=True,
                                   separators=(",", ":")).encode("utf-8"))


def prompt_hash() -> str:
    return sha256_bytes(WIRE_PROMPT.encode("utf-8"))


def r1_artifact_hash() -> str:
    return sha256_bytes(R1_ARTIFACT.read_bytes())


def local_request_body(temperature: float) -> dict:
    return {
        "model": LOCAL_MODEL,
        "messages": [{"role": "user", "content": WIRE_PROMPT}],
        "temperature": temperature,
        "top_p": 1.0,
        "max_tokens": OUTPUT_CEILING,
        "stream": False,
    }


def api_request_body(temperature: float) -> dict:
    body = {
        "model": API_MODEL,
        "input": [{"role": "user", "content": WIRE_PROMPT}],
        "reasoning": {"effort": "none"},
        "temperature": temperature,
        "max_output_tokens": OUTPUT_CEILING,
        "store": False,
        "stream": False,
    }
    if API_TOP_P_INCLUDED:
        body["top_p"] = 1.0
    return body


def _http_post(url: str, body: dict, api_key: str | None = None) -> dict:
    payload = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read()
            return {
                "http_status": resp.status,
                "response_bytes": len(raw),
                "response_sha256": sha256_bytes(raw),
                "data": json.loads(raw),
                "error": None,
            }
    except urllib.error.HTTPError as e:
        raw = e.read()
        parsed = None
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = {"raw_error_body": raw.decode("utf-8", errors="replace")}
        return {
            "http_status": e.code,
            "response_bytes": len(raw),
            "response_sha256": sha256_bytes(raw) if raw else "",
            "data": parsed,
            "error": str(e),
        }


def _sanitize_response(data: dict | None) -> dict:
    if not isinstance(data, dict):
        return {"parse_error": True, "raw_type": str(type(data))}
    out: dict[str, Any] = {}
    for key in ("id", "object", "model", "status", "error", "usage",
                "temperature", "top_p"):
        if key in data:
            out[key] = data[key]
    if "choices" in data:
        choices = []
        for ch in data.get("choices", []):
            msg = ch.get("message", {})
            choices.append({
                "index": ch.get("index"),
                "finish_reason": ch.get("finish_reason"),
                "message_role": msg.get("role"),
                "message_content": msg.get("content"),
            })
        out["choices"] = choices
    if "output" in data:
        out["output"] = data["output"]
    if "output_text" in data:
        out["output_text"] = data["output_text"]
    return out


def _extract_text(data: dict | None) -> str | None:
    if not isinstance(data, dict):
        return None
    if data.get("output_text"):
        return str(data["output_text"]).strip()
    for item in data.get("output", []) or []:
        if item.get("type") == "message":
            for part in item.get("content", []) or []:
                if part.get("type") in ("output_text", "text"):
                    text = part.get("text") or part.get("output_text")
                    if text:
                        return str(text).strip()
    choices = data.get("choices") or []
    if choices:
        msg = choices[0].get("message", {})
        content = msg.get("content")
        if content:
            return str(content).strip()
    return None


def _call_passes(result: dict, requested_model: str,
                 requested_temperature: float) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if result.get("error"):
        reasons.append(f"transport_error: {result['error']}")
    status = result.get("http_status")
    if status != 200:
        reasons.append(f"http_status_{status}")
    data = result.get("data")
    if isinstance(data, dict) and data.get("error"):
        reasons.append("response_error_object")
    text = _extract_text(data if isinstance(data, dict) else None)
    if not text:
        reasons.append("missing_text_output")
    returned_model = None
    if isinstance(data, dict):
        returned_model = data.get("model")
    if not returned_model:
        reasons.append("missing_returned_model")
    elif returned_model != requested_model:
        reasons.append(f"returned_model_differs:{returned_model}")
    if not result.get("response_id"):
        reasons.append("missing_response_id")
    if result.get("requested_temperature") != requested_temperature:
        reasons.append("requested_temperature_mismatch")
    return (len(reasons) == 0, reasons)


def local_decoding_contract() -> dict:
    return {
        "branch": "local",
        "endpoint_type": "openai_compatible_chat_completions",
        "endpoint_base_url_sanitized": LOCAL_BASE,
        "model_id": LOCAL_MODEL,
        "stateless_single_user_message": True,
        "temperature_values": [0.5, 0.7],
        "top_p": 1.0,
        "output_ceiling_param": "max_tokens",
        "output_ceiling": OUTPUT_CEILING,
        "seed": "unsupported_unavailable",
        "streaming": False,
        "tools": False,
        "response_format_steering": False,
        "system_prompt": False,
    }


def api_decoding_contract() -> dict:
    contract = {
        "branch": "api",
        "endpoint_type": "openai_responses",
        "endpoint_base_url_sanitized": API_BASE,
        "model_id": API_MODEL,
        "stateless_text_input": True,
        "reasoning_effort": "none",
        "temperature_values": [0.5, 0.7],
        "output_ceiling_param": "max_output_tokens",
        "output_ceiling": OUTPUT_CEILING,
        "store": False,
        "prior_response_id": False,
        "seed": "unsupported_unavailable",
        "streaming": False,
        "tools": False,
        "service_tier_override": False,
        "prompt_cache_key": False,
        "top_p_schema_basis": (
            "official_gpt-5.4_docs_sampling_params_with_reasoning_effort_none"
        ),
    }
    if API_TOP_P_INCLUDED:
        contract["top_p"] = 1.0
    else:
        contract["top_p"] = "excluded_pre_contact"
    return contract


def run_r2_checks() -> dict:
    if not R1_ARTIFACT.exists():
        raise FileNotFoundError(R1_ARTIFACT)
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY required for API branch")

    calls: list[dict] = []
    plan = [
        ("local", 0.5, f"{LOCAL_BASE}/chat/completions", local_request_body, None),
        ("local", 0.7, f"{LOCAL_BASE}/chat/completions", local_request_body, None),
        ("api", 0.5, f"{API_BASE}/responses", api_request_body, key),
        ("api", 0.7, f"{API_BASE}/responses", api_request_body, key),
    ]
    for branch, temp, url, body_fn, api_key in plan:
        body = body_fn(temp)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        result = _http_post(url, body, api_key=api_key)
        data = result.get("data")
        sanitized = _sanitize_response(data if isinstance(data, dict) else None)
        response_id = sanitized.get("id") if isinstance(sanitized, dict) else None
        if not response_id and isinstance(data, dict):
            response_id = data.get("id")
        call = {
            "branch": branch,
            "timestamp_utc": ts,
            "endpoint_url_sanitized": url,
            "request_body_sanitized": body,
            "request_body_sha256": sha256_canon(body),
            "requested_temperature": temp,
            "requested_output_ceiling": OUTPUT_CEILING,
            "http_status": result["http_status"],
            "transport_error": result["error"],
            "response_id": response_id,
            "returned_model": sanitized.get("model") if isinstance(sanitized, dict) else None,
            "response_sanitized": sanitized,
            "response_sanitized_sha256": sha256_canon(sanitized),
            "usage": sanitized.get("usage") if isinstance(sanitized, dict) else None,
            "output_text": _extract_text(data if isinstance(data, dict) else None),
        }
        passed, fail_reasons = _call_passes({
            **result,
            "response_id": response_id,
            "requested_temperature": temp,
        }, LOCAL_MODEL if branch == "local" else API_MODEL, temp)
        call["pass"] = passed
        call["fail_reasons"] = fail_reasons
        calls.append(call)

    def branch_verdict(branch: str) -> dict:
        branch_calls = [c for c in calls if c["branch"] == branch]
        ok = all(c["pass"] for c in branch_calls)
        contract = (local_decoding_contract() if branch == "local"
                    else api_decoding_contract())
        payload = {
            "branch": branch,
            "verdict": "pass" if ok else "fail",
            "contract": contract,
        }
        if ok:
            payload["decoding_contract_canonical_sha256"] = sha256_canon(contract)
        return payload

    return {
        "schema_version": "efc-decoding-surface-r2-v1",
        "assignment": "R2 non-fixture decoding-surface wire checks",
        "r1_artifact_path": str(R1_ARTIFACT.relative_to(REPO)),
        "r1_artifact_sha256": r1_artifact_hash(),
        "frozen_wire_prompt": WIRE_PROMPT,
        "frozen_wire_prompt_sha256": prompt_hash(),
        "disclosure": {
            "inference_calls": 4,
            "retries": 0,
            "packet_fixture_probe_calibration_or_source_text_sent": False,
            "neutral_prompt_only": True,
        },
        "calls": calls,
        "branches": {
            "local": branch_verdict("local"),
            "api": branch_verdict("api"),
        },
    }


def validate_r2_artifact(artifact: dict) -> None:
    """Offline validator for the R2 decoding-surface artifact."""
    if artifact.get("schema_version") != "efc-decoding-surface-r2-v1":
        raise ValueError("schema_version mismatch")
    if artifact.get("frozen_wire_prompt") != WIRE_PROMPT:
        raise ValueError("wire prompt mismatch")
    if artifact.get("frozen_wire_prompt_sha256") != prompt_hash():
        raise ValueError("wire prompt hash mismatch")
    if artifact.get("r1_artifact_sha256") != r1_artifact_hash():
        raise ValueError("r1 artifact hash mismatch")

    disclosure = artifact.get("disclosure", {})
    if disclosure.get("inference_calls") != 4:
        raise ValueError("inference call count must be exactly 4")
    if disclosure.get("retries") != 0:
        raise ValueError("retries must be zero")
    if disclosure.get("packet_fixture_probe_calibration_or_source_text_sent"):
        raise ValueError("packet/probe/calibration disclosure violated")
    if not disclosure.get("neutral_prompt_only"):
        raise ValueError("neutral_prompt_only must be true")

    calls = artifact.get("calls", [])
    if len(calls) != 4:
        raise ValueError("artifact must contain exactly four calls")

    expected = [
        ("local", 0.5, LOCAL_MODEL, f"{LOCAL_BASE}/chat/completions",
         "max_tokens"),
        ("local", 0.7, LOCAL_MODEL, f"{LOCAL_BASE}/chat/completions",
         "max_tokens"),
        ("api", 0.5, API_MODEL, f"{API_BASE}/responses", "max_output_tokens"),
        ("api", 0.7, API_MODEL, f"{API_BASE}/responses", "max_output_tokens"),
    ]
    for call, (branch, temp, model, endpoint, ceiling_key) in zip(calls, expected):
        if call.get("branch") != branch:
            raise ValueError(f"wrong branch: {call.get('branch')}")
        if call.get("requested_temperature") != temp:
            raise ValueError(f"wrong temperature for {branch} {temp}")
        body = call.get("request_body_sanitized", {})
        if body.get("model") != model:
            raise ValueError(f"wrong model for {branch} {temp}")
        if call.get("endpoint_url_sanitized") != endpoint:
            raise ValueError(f"wrong endpoint for {branch} {temp}")
        if ceiling_key not in body or body[ceiling_key] != OUTPUT_CEILING:
            raise ValueError(f"wrong output ceiling for {branch} {temp}")
        if body.get("stream") is not False:
            raise ValueError("streaming must be off")
        if body.get("temperature") != temp:
            raise ValueError("request body temperature mismatch")
        if body.get("top_p") != 1.0:
            raise ValueError("top_p must be 1.0")
        if call.get("request_body_sha256") != sha256_canon(body):
            raise ValueError(f"request body hash mismatch for {branch} {temp}")
        if branch == "api":
            if body.get("reasoning") != {"effort": "none"}:
                raise ValueError("api reasoning.effort must be none")
            if body.get("store") is not False:
                raise ValueError("api store must be false")
            if "tools" in body:
                raise ValueError("api tools must be absent")
            if "previous_response_id" in body:
                raise ValueError("api state linkage forbidden")
        if branch == "local":
            if "tools" in body:
                raise ValueError("local tools must be absent")
            if any(m.get("role") != "user" for m in body.get("messages", [])):
                raise ValueError("local must be single user message only")
        if WIRE_PROMPT not in json.dumps(body):
            raise ValueError("frozen prompt missing from request body")
        if not call.get("response_id"):
            raise ValueError("missing response id evidence")
        sanitized = call.get("response_sanitized")
        if not call.get("response_sanitized_sha256"):
            raise ValueError("missing sanitized response hash")
        if sanitized and call["response_sanitized_sha256"] != sha256_canon(sanitized):
            raise ValueError(f"response hash mismatch for {branch} {temp}")
        if call.get("http_status") != 200:
            raise ValueError(f"call not successful: {branch} {temp}")
        if call.get("returned_model") != model:
            raise ValueError(f"returned model mismatch: {branch} {temp}")
        if not call.get("output_text"):
            raise ValueError(f"missing output text: {branch} {temp}")
        if call.get("pass") is not True:
            raise ValueError(f"call marked fail: {branch} {temp}")

    for branch_name in ("local", "api"):
        branch = artifact["branches"][branch_name]
        branch_calls = [c for c in calls if c["branch"] == branch_name]
        if branch["verdict"] != "pass":
            raise ValueError(f"{branch_name} branch verdict must be pass")
        if not all(c["pass"] for c in branch_calls):
            raise ValueError(f"{branch_name} verdict pass but call failed")
        contract = branch["contract"]
        expected_contract = (local_decoding_contract() if branch_name == "local"
                             else api_decoding_contract())
        if contract != expected_contract:
            raise ValueError(f"{branch_name} contract payload mismatch")
        expected_hash = sha256_canon(contract)
        if branch.get("decoding_contract_canonical_sha256") != expected_hash:
            raise ValueError(f"{branch_name} contract hash mismatch")


def load_and_validate_r2_artifact(path: Path | None = None) -> dict:
    path = path or OUT_PATH
    artifact = json.loads(path.read_text())
    validate_r2_artifact(artifact)
    return artifact


def verify_r2_artifact_file(path: Path | None = None) -> dict:
    """Validate the on-disk R2 artifact with zero network I/O."""
    path = path or OUT_PATH
    if not path.exists():
        raise FileNotFoundError(path)
    file_hash = sha256_bytes(path.read_bytes())
    artifact = load_and_validate_r2_artifact(path)
    return {
        "status": "ok",
        "artifact_path": str(path.relative_to(REPO)),
        "artifact_sha256": file_hash,
        "inference_calls": artifact["disclosure"]["inference_calls"],
        "local_verdict": artifact["branches"]["local"]["verdict"],
        "api_verdict": artifact["branches"]["api"]["verdict"],
        "local_decoding_contract_sha256":
            artifact["branches"]["local"]["decoding_contract_canonical_sha256"],
        "api_decoding_contract_sha256":
            artifact["branches"]["api"]["decoding_contract_canonical_sha256"],
        "network_calls": 0,
    }


def write_r2_artifact(path: Path | None = None) -> Path:
    """Create-once writer for the live R2 evidence (not authorized by default)."""
    path = path or OUT_PATH
    if path.exists():
        raise RuntimeError(
            f"refusing to overwrite existing R2 artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    artifact = run_r2_checks()
    path.write_text(json.dumps(artifact, sort_keys=True, indent=1) + "\n")
    return path


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="R2 decoding-surface artifact verifier (offline by default)")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="validate the pinned R2 artifact with zero network calls",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="create-once live R2 capture; refuses if artifact already exists",
    )
    args = parser.parse_args(argv)

    if args.verify:
        if args.execute:
            parser.error("--verify and --execute are mutually exclusive")
        result = verify_r2_artifact_file()
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.execute:
        out = write_r2_artifact()
        print(json.dumps({
            "status": "created",
            "artifact": str(out.relative_to(REPO)),
            "artifact_sha256": sha256_bytes(out.read_bytes()),
        }, sort_keys=True))
        return 0

    parser.print_usage(file=sys.stderr)
    print("\nerror: specify --verify or --execute", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
