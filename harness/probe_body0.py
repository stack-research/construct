"""Separate Body-0 real-engine ignorance probe.

The probe receives no memory records and no attacker foreground.  It binds one
engine/model to the current manifest bytes and records whether the cold answer
still takes the stale decision required for Body-0 engagement.  Admission is not
evidence; ``run_body0`` consumes the packet but never treats it as a verdict.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .check_body0_fixture import DEFAULT_MANIFEST, manifest_hash
from .engine import ClaudeEngine, LocalEngine, MockEngine
from .oracle import extract_decision


def run_probe(manifest_path: Path, *, engine_backend: str, model: str,
              base_url: str = "http://localhost:1234/v1") -> dict:
    manifest = json.loads(manifest_path.read_text())
    spec = manifest["ignorance_probe"]
    if engine_backend == "claude":
        engine = ClaudeEngine(model)
    elif engine_backend == "local":
        engine = LocalEngine(model, base_url=base_url)
    elif engine_backend == "mock":
        engine = MockEngine()
    else:
        raise ValueError(f"unknown engine backend {engine_backend!r}")
    result = engine.run(spec["question"], [], "")
    decision = extract_decision(result.answer)
    return {
        "kind": "body0_ignorance_probe",
        "manifest_sha256": manifest_hash(manifest_path),
        "fixture_id": manifest["fixture_id"],
        "engine_backend": engine.backend_name,
        "model": engine.model,
        "question": spec["question"],
        "answer": result.answer,
        "decision": decision,
        "ignorant_decision": spec["ignorant_decision"],
        "current_decision": spec["current_decision"],
        "knew_current": decision == spec["current_decision"],
        "wire_only": engine.backend_name == "mock",
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "disclosure": (
            "mock probe proves transport only; never admits real contact"
            if engine.backend_name == "mock"
            else "cold no-memory admission probe; not Body-0 evidence"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Body-0 cold ignorance probe")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--engine", required=True, choices=["mock", "claude", "local"])
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    packet = run_probe(
        Path(args.manifest),
        engine_backend=args.engine,
        model=args.model,
        base_url=args.base_url,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n")
    print(json.dumps(packet, indent=2, sort_keys=True))
    if packet["wire_only"]:
        print("REFUSED: mock probe is wire-only and cannot admit a real run", file=sys.stderr)
        return 2
    return 0 if packet["decision"] == packet["ignorant_decision"] else 3


if __name__ == "__main__":
    sys.exit(main())
