"""Body-1 pre-contact gate for the exact endorsed packet and implementation.

This checker is deterministic. Its mock mode verifies packet, runtime, grammar,
scope, cost, review authorization, and renderer bindings without model contact.
Real mode additionally requires a fresh engine-specific surface/ignorance
receipt produced by ``probe_body1.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from .body1 import (
    ENDORSED_PACKET_INDEX_SHA256,
    FORM_BARE,
    FORM_NONBINDING,
    PACKET_DIR,
    PACKET_INDEX,
    ROOT,
    ballast_records,
    classify_expression,
    cost_state_preflight,
    derive_scope,
    execute_packet_form,
    file_sha256,
    fixture,
    load_json,
    packet_index_sha256,
    renderer_sha256,
    scope_matches_declared,
    verify_packet_index,
    verify_runtime_pin,
)
from .records import Record

FINAL_REVIEW_THREAD = (
    ROOT / ".substrate" / "threads" / "body-1-partial-binding-final-review"
)

FORBIDDEN_SCORED_IDENTITIES = frozenset({
    "cursor-grok-4.5-high",
    "grok-4.5",
    "composer-2.5",
    "cursor/composer-2.5",
    "cursor/grok-4.5",
})

BACKEND_RECEIPT_NAMES = {
    "mock": "mock",
    "claude": "claude",
    "local": "local_openai_compat",
}


@dataclass(frozen=True)
class Check:
    check: str
    ok: bool
    detail: str

    def as_dict(self) -> dict:
        return {"check": self.check, "ok": self.ok, "detail": self.detail}


def backend_receipt_name(engine_backend: str) -> str:
    try:
        return BACKEND_RECEIPT_NAMES[engine_backend]
    except KeyError as exc:
        raise ValueError(f"unknown engine backend {engine_backend!r}") from exc


def _normalized_identity(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def identity_allowed(*values: str) -> bool:
    normalized = {_normalized_identity(value) for value in values if value}
    return not any(
        identity in FORBIDDEN_SCORED_IDENTITIES
        or identity.endswith("/composer-2.5")
        or identity.endswith("/grok-4.5")
        or "cursor-grok-4.5" in identity
        for identity in normalized
    )


def _review_checks() -> list[Check]:
    config = FINAL_REVIEW_THREAD / "config.yaml"
    reviewers = {
        "cursor/grok-4.5": list(
            FINAL_REVIEW_THREAD.glob("*__cursor%2Fgrok-4.5.md")
        ),
        "cursor/composer-2.5": list(
            FINAL_REVIEW_THREAD.glob("*__cursor%2Fcomposer-2.5.md")
        ),
    }
    config_ok = (
        config.is_file()
        and "status: ended" in config.read_text()
        and ENDORSED_PACKET_INDEX_SHA256 in config.read_text()
    )
    checks = [
        Check(
            "final_review_ended",
            config_ok,
            f"thread={FINAL_REVIEW_THREAD.relative_to(ROOT)}",
        )
    ]
    for name, paths in reviewers.items():
        ok = len(paths) == 1
        text = paths[0].read_text() if ok else ""
        ok = ok and "## ENDORSE" in text and ENDORSED_PACKET_INDEX_SHA256 in text
        checks.append(Check(
            f"final_review_{name}",
            ok,
            f"entries={len(paths)}; exact_hash={ENDORSED_PACKET_INDEX_SHA256}",
        ))
    moderator = [
        path for path in FINAL_REVIEW_THREAD.glob("*__codex.md")
        if "exact packet ENDORSED" in path.read_text()
    ]
    moderator_ok = (
        len(moderator) == 1
        and ENDORSED_PACKET_INDEX_SHA256 in moderator[0].read_text()
    )
    checks.append(Check(
        "final_review_moderator_close",
        moderator_ok,
        f"matching_closes={len(moderator)}",
    ))
    return checks


def _component_checks(sequence: dict) -> list[Check]:
    checks: list[Check] = []
    for name, pin in sequence["component_pins"].items():
        target = ROOT / pin["path"]
        observed = file_sha256(target) if target.is_file() else "missing"
        checks.append(Check(
            f"component_pin_{name}",
            observed == pin["sha256"],
            f"path={pin['path']}; observed={observed}",
        ))
    return checks


def _mutation_candidates(recurrence: dict) -> dict[str, str]:
    return {
        "additional_call": 'factory(partial(unit_key, "unit:"))',
        "assignment": 'x = partial(unit_key, "unit:")',
        "attribute": 'functools.partial(unit_key, "unit:")',
        "code_fence": '```python\\npartial(unit_key, "unit:")\\n```',
        "comprehension": '[partial(unit_key, "unit:") for _ in [0]]',
        "keyword": 'partial(unit_key, prefix="unit:")',
        "lambda": 'lambda: partial(unit_key, "unit:")',
        "subscript": '[partial(unit_key, "unit:")][0]',
        "trailing_prose": 'partial(unit_key, "unit:") because it binds',
        "tuple": '(partial(unit_key, "unit:"),)',
        "wrong_callable": 'partial(other_key, "unit:")',
        "wrong_literal": 'partial(unit_key, "other:")',
    }


def _fixture_checks() -> list[Check]:
    names = [
        "surface_control",
        "ignorance_probe",
        "e1_failure",
        "residence",
        "recurrence",
        "scope_loses",
    ]
    preflight = load_json(PACKET_DIR / "authoring_preflight.json")
    expected = {
        (row["fixture"], row["form"]): row
        for row in preflight["fixture_results"]
    }
    expression_contract = load_json(PACKET_DIR / "expression_contract.json")
    earned_text = load_json(PACKET_DIR / "earned_record.json")["text"]
    checks: list[Check] = []
    all_runtime_ok = True
    all_scope_ok = True
    all_parser_ok = True
    all_prompts_clean = True
    address_states: set[str] = set()
    for name in names:
        current = fixture(name)
        derived = derive_scope(current)
        all_scope_ok = all_scope_ok and scope_matches_declared(current, derived)
        prompt_lower = current["prompt"].lower()
        prompt_ok = (
            "staticmethod" not in prompt_lower
            and "nonbinding_partial" not in prompt_lower
            and earned_text not in current["prompt"]
            and all(
                expression not in current["prompt"]
                for expression in current["packet_expressions"].values()
            )
        )
        all_prompts_clean = all_prompts_clean and prompt_ok
        for form in (FORM_BARE, FORM_NONBINDING):
            selection = classify_expression(
                current["packet_expressions"][form],
                current,
                expression_contract,
            )
            all_parser_ok = (
                all_parser_ok
                and selection.status == "selected"
                and selection.form == form
            )
            observed = execute_packet_form(current, form)
            address_states.add(observed.address_space_limit)
            authored = expected[(current["fixture_id"], form)]
            all_runtime_ok = all_runtime_ok and (
                observed.status == "scored"
                and observed.outcome == authored["observed"]
                and observed.program_sha256 == authored["program_sha256"]
                and observed.stdout_sha256 == authored["stdout_sha256"]
            )
    recurrence = fixture("recurrence")
    mutation_ok = all(
        classify_expression(value, recurrence, expression_contract).form is None
        for value in _mutation_candidates(recurrence).values()
    )
    checks.extend([
        Check(
            "scope_derivation",
            all_scope_ok,
            "all six fixtures recompute declared arity inputs",
        ),
        Check(
            "prompt_leak",
            all_prompts_clean,
            "no prompt contains a repair token, record text, or completed expression",
        ),
        Check(
            "expression_grammar",
            all_parser_ok and mutation_ok,
            "authored forms unique; twelve mutation families rejected",
        ),
        Check(
            "oracle_directions",
            all_runtime_ok,
            "twelve frozen program directions match authoring preflight",
        ),
        Check(
            "address_space_target",
            address_states <= {"enforced", "unsupported_by_launch_path"},
            f"states={sorted(address_states)}; target attempted on every launch",
        ),
    ])
    return checks


def _cost_check(sequence: dict) -> Check:
    earned = load_json(PACKET_DIR / "earned_record.json")
    record = Record(
        record_id=earned["record_id"],
        text=earned["text"],
        created_at=earned["created_at"],
        predeclared_usage=earned["predeclared_usage"],
        vocabulary_kind=earned["vocabulary_kind"],
        trust=earned["trust"],
        provenance={"source": "precontact_cost_only"},
    )
    residence_count = sequence["residence_contract"]["block_labels"].count("P")
    cost = cost_state_preflight(
        [*ballast_records(sequence), record],
        record.record_id,
        residence_count,
    )
    return Check(
        "cost_state_dependence",
        cost["gate_open"] and cost["cost_C"] < cost["cost_R"],
        json.dumps(cost, sort_keys=True),
    )


def _probe_checks(
    probe_result: dict | None,
    *,
    engine_backend: str,
    model: str,
) -> list[Check]:
    if engine_backend == "mock":
        return [
            Check(
                "engine_exclusion",
                True,
                "mock wire seat; never behavioral evidence",
            ),
            Check(
                "engine_specific_probe",
                True,
                "mock wire bypass disclosed",
            ),
        ]
    receipt_backend = backend_receipt_name(engine_backend)
    probe = probe_result or {}
    requested = str(probe.get("requested_model", ""))
    observed = str(probe.get("observed_model", ""))
    identity_ok = (
        requested == model
        and identity_allowed(requested, observed)
    )
    binding_ok = (
        probe.get("packet_index_sha256") == ENDORSED_PACKET_INDEX_SHA256
        and probe.get("renderer_sha256") == renderer_sha256()
        and probe.get("engine_backend") == receipt_backend
        and probe.get("contact_class") == "admission_only_not_evidence"
    )
    surface = probe.get("surface_control") or {}
    ignorance = probe.get("ignorance_probe") or {}
    direction_ok = (
        surface.get("selection") == FORM_BARE
        and surface.get("runtime_outcome") == "pass"
        and ignorance.get("selection") == FORM_BARE
        and ignorance.get("runtime_outcome") == "TypeError"
    )
    return [
        Check(
            "engine_exclusion",
            identity_ok,
            f"requested={requested}; observed={observed}",
        ),
        Check(
            "probe_binding",
            binding_ok,
            f"backend={probe.get('engine_backend')}; packet={probe.get('packet_index_sha256')}",
        ),
        Check(
            "surface_control",
            direction_ok and surface.get("runtime_outcome") == "pass",
            json.dumps(surface, sort_keys=True),
        ),
        Check(
            "probe_ignorance",
            direction_ok and ignorance.get("runtime_outcome") == "TypeError",
            json.dumps(ignorance, sort_keys=True),
        ),
    ]


def checks(
    *,
    probe_result: dict | None = None,
    engine_backend: str = "mock",
    model: str = "mock-engine-v1",
) -> list[Check]:
    sequence = load_json(PACKET_DIR / "sequence_contract.json")
    packet_errors = verify_packet_index()
    runtime_ok, runtime_detail = verify_runtime_pin()
    result = [
        Check(
            "packet_index_hash",
            packet_index_sha256() == ENDORSED_PACKET_INDEX_SHA256,
            f"observed={packet_index_sha256()}",
        ),
        Check(
            "packet_entries",
            not packet_errors,
            "ok" if not packet_errors else "; ".join(packet_errors),
        ),
        Check(
            "runtime_pin",
            runtime_ok,
            json.dumps(runtime_detail, sort_keys=True),
        ),
        Check(
            "renderer",
            bool(renderer_sha256()),
            f"sha256={renderer_sha256()}",
        ),
    ]
    result.extend(_review_checks())
    result.extend(_component_checks(sequence))
    result.extend(_fixture_checks())
    result.append(_cost_check(sequence))
    result.extend(_probe_checks(
        probe_result,
        engine_backend=engine_backend,
        model=model,
    ))
    return result


def gate_result(
    *,
    probe_result: dict | None = None,
    engine_backend: str = "mock",
    model: str = "mock-engine-v1",
) -> dict:
    result = checks(
        probe_result=probe_result,
        engine_backend=engine_backend,
        model=model,
    )
    return {
        "gate_open": all(check.ok for check in result),
        "packet_index_sha256": packet_index_sha256(),
        "endorsed_packet_index_sha256": ENDORSED_PACKET_INDEX_SHA256,
        "renderer_sha256": renderer_sha256(),
        "engine_backend": backend_receipt_name(engine_backend),
        "engine_backend_cli": engine_backend,
        "model": model,
        "checks": [check.as_dict() for check in result],
        "evidence_class": "wire_integration_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the frozen Body-1 packet")
    parser.add_argument("--engine", default="mock", choices=sorted(BACKEND_RECEIPT_NAMES))
    parser.add_argument("--model", default="mock-engine-v1")
    parser.add_argument("--probe-result")
    args = parser.parse_args()
    probe = (
        json.loads(Path(args.probe_result).read_text())
        if args.probe_result else None
    )
    result = gate_result(
        probe_result=probe,
        engine_backend=args.engine,
        model=args.model,
    )
    for check in result["checks"]:
        print(
            f"{'PASS' if check['ok'] else 'FAIL'}  "
            f"{check['check']}: {check['detail']}"
        )
    print(
        "\nGATE OPEN: Body-1 packet and implementation preflight pass."
        if result["gate_open"]
        else "\nGATE CLOSED: Body-1 refuses contact."
    )
    return 0 if result["gate_open"] else 1


if __name__ == "__main__":
    sys.exit(main())
