"""Derive typed production comparison inputs from promoted oracle artifacts.

Pre-pin authoring only. The production runtime must not import this module.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from harness.efc_author_c2_content import FIXTURES

REPO = Path(__file__).resolve().parent.parent
ORACLE_ROOT = REPO / "corpus" / "efc_calibration" / "oracle"
COMPARISON_ROOT = REPO / "corpus" / "efc_calibration" / "comparison"

STRUCTURED_INPUTS_SCHEMA_VERSION = "efc-production-structured-inputs-v1"

DISPOSITIVE_TASKS = tuple(
    tid for tid, spec in FIXTURES.items()
    if spec["role"] == "s_family"
    or spec.get("stratum") in ("match_mismatch", "match_commit")
)


def decision_scope_sha256(decision_scope: str) -> str:
    return hashlib.sha256(decision_scope.encode("utf-8")).hexdigest()


def _load_oracle(task_id: str) -> dict:
    return json.loads((ORACLE_ROOT / f"{task_id}.json").read_text())


def _parse_cargo_scope(scope: str) -> tuple[str, str]:
    m = re.search(r"crate (\S+) at version ([\d.]+)", scope)
    if not m:
        raise ValueError(f"cargo scope parse failed: {scope!r}")
    return m.group(1), m.group(2)


def _parse_npm_scope(scope: str) -> tuple[str, str]:
    m = re.search(r"npm package (\S+) at version ([\d.]+)", scope)
    if not m:
        raise ValueError(f"npm scope parse failed: {scope!r}")
    return m.group(1), m.group(2)


def _parse_go_scope(scope: str) -> tuple[str, str, str | None]:
    m = re.search(
        r"Go module (\S+) at version ([\d.]+)(?:, "
        r"(?:calling|using|through) (\S+))?",
        scope)
    if not m:
        raise ValueError(f"go scope parse failed: {scope!r}")
    sym = m.group(3)
    if sym and "." in sym:
        sym = sym.rsplit(".", 1)[-1]
    return m.group(1), m.group(2), sym


def _parse_eol_scope(scope: str) -> tuple[str, str, str]:
    m = re.search(
        r"(\S+) release line ([\d.]+) remaining in (?:security )?support on "
        r"(\d{4}-\d{2}-\d{2})", scope)
    if not m:
        raise ValueError(f"eol scope parse failed: {scope!r}")
    return m.group(1), m.group(2), m.group(3)


def derive_structured_input(task_id: str) -> dict:
    spec = FIXTURES[task_id]
    oracle = _load_oracle(task_id)
    ev = oracle["extracted_values"]
    scope = spec["decision_scope"]
    record = spec["record"]
    base = {
        "source_reference": oracle["source_reference"],
        "raw_sha256": oracle["raw_sha256"],
        "decision_scope_sha256": decision_scope_sha256(scope),
    }

    if record.startswith("A"):
        pkg, version = _parse_cargo_scope(scope)
        if pkg != ev["pkg"]:
            raise ValueError(f"{task_id}: crate mismatch {pkg} vs {ev['pkg']}")
        op = "cargo_affected_membership"
        if "introduced" in ev:
            operands = {
                "ecosystem": "crates.io",
                "package": pkg,
                "version": version,
                "introduced": ev["introduced"],
                "fixed_exclusive": ev["fixed"],
            }
        else:
            operands = {
                "ecosystem": "crates.io",
                "package": pkg,
                "version": version,
                "upper_exclusive": ev["fixed"],
            }
        return {**base, "operation": op, "operands": operands}

    if record.startswith("B") or record == "BR02":
        pkg, version = _parse_npm_scope(scope)
        ranges = []
        if "range0" in ev and "range1" in ev:
            ranges = [ev["range0"], ev["range1"]]
        elif "range" in ev:
            ranges = [ev["range"]]
        else:
            raise ValueError(f"{task_id}: missing GHSA ranges")
        return {
            **base,
            "operation": "ghsa_semver_membership",
            "operands": {
                "ecosystem": ev.get("eco", "npm"),
                "package": pkg,
                "version": version,
                "range_strings": ranges,
            },
        }

    if record.startswith("C"):
        product, cycle, check_date = _parse_eol_scope(scope)
        if ev["cycle"] != cycle:
            raise ValueError(f"{task_id}: cycle mismatch")
        return {
            **base,
            "operation": "eol_support_on_date",
            "operands": {
                "product": product,
                "cycle": cycle,
                "eol_date": ev["eol"],
                "check_date": check_date,
            },
        }

    if record.startswith("D") or record == "P04":
        mod, version, symbol = _parse_go_scope(scope)
        if mod != ev["mod"]:
            raise ValueError(f"{task_id}: module mismatch")
        listed = ev.get("sym0") or ev.get("sym1")
        if symbol is None:
            symbol = listed
        return {
            **base,
            "operation": "go_symbol_version_membership",
            "operands": {
                "module": mod,
                "version": version,
                "upper_exclusive": ev["fixed"],
                "symbol": symbol,
                "listed_symbol": listed,
            },
        }

    if record.startswith("E"):
        clause = ev["clause"]
        if "link" in scope.lower() and "independent" in scope.lower():
            return {
                **base,
                "operation": "license_permission_granted",
                "operands": {
                    "license_id": ev["id"],
                    "required_phrases": [
                        "independent modules",
                        "executable",
                        "terms of your choice",
                    ],
                    "clause_text": clause,
                },
            }
        if "4(a)" in scope or "4(b)" in scope:
            return {
                **base,
                "operation": "license_section_waiver_applies",
                "operands": {
                    "license_id": ev["id"],
                    "sections": ["4(a)", "4(b)", "4(d)"],
                    "clause_text": clause,
                },
            }
        if "machine-executable" in scope.lower():
            return {
                **base,
                "operation": "license_inclusion_obligation_holds",
                "operands": {
                    "license_id": ev["id"],
                    "category_phrase": (
                        "solely in the form of machine-executable object code"),
                    "clause_text": clause,
                },
            }

    raise ValueError(f"unsupported task derivation: {task_id}")


def population_binding_payload(rows: list[dict],
                               schema_version: str,
                               row_count: int) -> dict:
    return {
        "row_count": row_count,
        "rows": sorted(rows, key=lambda r: (
            r["source_reference"], r["decision_scope_sha256"])),
        "schema_version": schema_version,
    }


def population_binding_sha256(rows: list[dict],
                              schema_version: str,
                              row_count: int) -> str:
    payload = population_binding_payload(rows, schema_version, row_count)
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")
                          ).hexdigest()


def build_structured_inputs() -> dict:
    rows = [derive_structured_input(tid) for tid in DISPOSITIVE_TASKS]
    schema_version = STRUCTURED_INPUTS_SCHEMA_VERSION
    row_count = len(rows)
    return {
        "schema_version": schema_version,
        "row_count": row_count,
        "population_binding_sha256": population_binding_sha256(
            rows, schema_version, row_count),
        "rows": rows,
    }


def write_structured_inputs(path: Path | None = None) -> Path:
    path = path or COMPARISON_ROOT / "structured_inputs_v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_structured_inputs()
    path.write_text(json.dumps(payload, sort_keys=True, indent=1) + "\n")
    return path
