"""Fresh engine-specific Body-1 surface and ignorance admission probe.

Probe receipts are admission-only and never scored evidence. The CLI refuses
known discovery/review seats before constructing an engine client.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .body1 import (
    ENDORSED_PACKET_INDEX_SHA256,
    build_body1_prompt,
    classify_expression,
    execute_packet_form,
    fixture,
    packet_index_sha256,
    renderer_sha256,
    runtime_row,
)
from .body1_engine import Body1Engine
from .check_body1_fixture import identity_allowed


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _probe_one(engine: Body1Engine, name: str) -> tuple[dict, str]:
    current = fixture(name)
    prompt = build_body1_prompt(current)
    result = engine.run(prompt, current, [])
    selection = classify_expression(result.raw_answer, current)
    runtime = (
        execute_packet_form(current, selection.form)
        if selection.form else None
    )
    return {
        "fixture_id": current["fixture_id"],
        "prompt_sha256": __import__("hashlib").sha256(prompt.encode()).hexdigest(),
        "raw_answer": result.raw_answer,
        "raw_answer_sha256": selection.raw_sha256,
        "selection_status": selection.status,
        "selection": selection.form,
        "selection_refusal": selection.refusal,
        "runtime_outcome": runtime.outcome if runtime else None,
        "runtime": runtime_row(runtime) if runtime else None,
        "latency_ms": result.latency_ms,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
    }, result.observed_model


def run_probe(
    *,
    engine_backend: str,
    model: str,
    base_url: str = "http://localhost:1234/v1",
) -> dict:
    if packet_index_sha256() != ENDORSED_PACKET_INDEX_SHA256:
        raise ValueError("Body-1 packet no longer matches the endorsed hash")
    if not identity_allowed(model):
        raise ValueError("requested engine is excluded from scored Body-1 roles")
    engine = Body1Engine(
        backend=engine_backend,
        model=model,
        base_url=base_url,
    )
    surface, observed_surface = _probe_one(engine, "surface_control")
    ignorance, observed_ignorance = _probe_one(engine, "ignorance_probe")
    if observed_surface != observed_ignorance:
        raise ValueError("provider model identity changed between admission probes")
    return {
        "probe_id": f"b1-admission-{int(time.time())}",
        "created_at": _utc_now(),
        "contact_class": "admission_only_not_evidence",
        "wire_only": engine_backend == "mock",
        "packet_index_sha256": packet_index_sha256(),
        "renderer_sha256": renderer_sha256(),
        "engine_backend": engine.backend_name,
        "engine_backend_cli": engine_backend,
        "requested_model": model,
        "observed_model": observed_surface,
        "surface_control": surface,
        "ignorance_probe": ignorance,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Body-1 admission probes")
    parser.add_argument("--engine", required=True, choices=["mock", "claude", "local"])
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        result = run_probe(
            engine_backend=args.engine,
            model=args.model,
            base_url=args.base_url,
        )
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    print(f"Body-1 admission receipt: {args.out}")
    print("DISCLOSED: admission-only; not scored evidence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
