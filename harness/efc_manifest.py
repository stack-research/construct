"""Calibration-manifest machine check — SPEC_EPISTEMIC_FRAME_CHECK_V0 §5.2.

After Part I is sealed but before calibration contact, the calibration
manifest pins the roster, ids, hashes, probe contract, frozen texts, and the
§10.2 sampling constants. This module is the machine half of §5.2's check
("machine-checked and receives a bounded cold check for contract
conformance"): closed schema, pinned-value equality, format discipline, and a
forbidden-content scan. Semantic conformance (e.g. whether a probe fixture is
really disjoint) stays with the cold reviewer seat — machinery cannot certify
meaning, only structure.

The manifest may not contain held-out source or target outcomes (§5.2). The
machine layer enforces that as a closed key schema plus a forbidden-substring
scan over every nested key. Disjointness against held-out families is checked
when those manifests exist (§5.3 pins them only after admission).

The population region is OPTIONAL here: §12 requires it declared before
held-out contact, which is a deadline after admission (§5.3). If present it
is validated now and the §10.4 planner can include population contrasts in
the admission board; if absent, §14 item 6 blocks Part II until it lands.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from harness import efc_contracts as c
from harness.efc_planner import PlannerContractError, validate_prevalence_region

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9._/:+-]{1,128}$")
_DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}")

REQUIRED_FIELDS = (
    "part_i_spec_hash",
    "engine_roster",
    "model_id",
    "decoding_contract_id",
    "renderer_id",
    "foreground_template_hash",
    "calibration_fixtures",
    "world_oracles",
    "ignorance_probe_contract",
    "predicate_contract_hash",
    "extractor_hash",
    "check_contract_hash",
    "generic_caution_text",
    "generic_caution_sha256",
    "offer_projection_text",
    "offer_projection_sha256",
    "calibration_k",
    "temperature",
    "collapse_diagnostic_temperature",
    "stop_rule",
    "n_max",
    "total_budget_tokens",
)
OPTIONAL_FIELDS = ("population_region",)

# §5.2: no held-out source or target outcome material may ride the manifest.
FORBIDDEN_KEY_SUBSTRINGS = ("heldout", "held_out", "outcome",
                            "expected_action", "required_scope", "answer",
                            "target_fixture", "source_fixture")


@dataclass(frozen=True)
class ManifestCheckResult:
    ok: bool
    failures: tuple[str, ...]
    manifest_hash: str | None


def manifest_hash(manifest: dict) -> str:
    return hashlib.sha256(json.dumps(manifest, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")
                          ).hexdigest()


def _scan_forbidden_keys(node, path: str, failures: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            key_l = str(key).lower()
            for bad in FORBIDDEN_KEY_SUBSTRINGS:
                if bad in key_l:
                    failures.append(f"forbidden key {path}.{key}: manifests may "
                                    "not carry held-out outcome material (§5.2)")
            _scan_forbidden_keys(value, f"{path}.{key}", failures)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            _scan_forbidden_keys(item, f"{path}[{i}]", failures)


def check_calibration_manifest(manifest: dict) -> ManifestCheckResult:
    failures: list[str] = []

    unknown = set(manifest) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS)
    if unknown:
        failures.append(f"unknown manifest keys {sorted(unknown)}: the schema "
                        "is closed")
    missing = [f for f in REQUIRED_FIELDS if f not in manifest]
    if missing:
        failures.append(f"missing manifest keys {missing}")
        return ManifestCheckResult(False, tuple(failures), None)

    # --- seal identity -----------------------------------------------------
    if manifest["part_i_spec_hash"] != c.PART_I_SPEC_SHA256:
        failures.append("part_i_spec_hash does not match the sealed Part I")

    # --- frozen texts (§8.3/§8.4) -------------------------------------------
    if manifest["generic_caution_text"] != c.GENERIC_CAUTION_TEXT:
        failures.append("generic_caution_text differs from the sealed text")
    if manifest["generic_caution_sha256"] != c.GENERIC_CAUTION_SHA256:
        failures.append("generic_caution_sha256 differs from the sealed hash")
    if (c.sha256_utf8(str(manifest["generic_caution_text"]))
            != manifest["generic_caution_sha256"]):
        failures.append("generic_caution hash does not recompute from text")
    if manifest["offer_projection_text"] != c.OFFER_PROJECTION_TEXT:
        failures.append("offer_projection_text differs from the sealed template")
    if manifest["offer_projection_sha256"] != c.OFFER_PROJECTION_SHA256:
        failures.append("offer_projection_sha256 differs from the sealed hash")

    # --- §10.2 sampling constants -------------------------------------------
    if manifest["calibration_k"] != c.CALIBRATION_K:
        failures.append(f"calibration_k {manifest['calibration_k']!r} != "
                        f"{c.CALIBRATION_K}")
    if manifest["temperature"] != c.CALIBRATION_TEMPERATURE:
        failures.append(f"temperature {manifest['temperature']!r} != "
                        f"{c.CALIBRATION_TEMPERATURE}")
    if (manifest["collapse_diagnostic_temperature"]
            != c.COLLAPSE_DIAGNOSTIC_TEMPERATURE):
        failures.append("collapse_diagnostic_temperature != "
                        f"{c.COLLAPSE_DIAGNOSTIC_TEMPERATURE}")
    if manifest["stop_rule"] != c.STOP_RULE_ID:
        failures.append(f"stop_rule {manifest['stop_rule']!r} != {c.STOP_RULE_ID!r}")
    if manifest["n_max"] != c.N_MAX:
        failures.append(f"n_max {manifest['n_max']!r} != {c.N_MAX}")
    budget = manifest["total_budget_tokens"]
    if not isinstance(budget, int) or isinstance(budget, bool) or budget <= 0:
        failures.append("total_budget_tokens must be a positive integer "
                        "(§10.2: a separate hard pre-build disclosure)")

    # --- ids and hashes ------------------------------------------------------
    for name in ("model_id", "decoding_contract_id", "renderer_id"):
        value = manifest[name]
        if not isinstance(value, str) or not _ID.fullmatch(value):
            failures.append(f"{name} must be a compact identifier")
    for name in ("foreground_template_hash", "predicate_contract_hash",
                 "extractor_hash", "check_contract_hash"):
        value = manifest[name]
        if not isinstance(value, str) or not _HEX64.fullmatch(value):
            failures.append(f"{name} must be a sha256 hex digest")

    roster = manifest["engine_roster"]
    if (not isinstance(roster, list) or not roster
            or not all(isinstance(e, str) and _ID.fullmatch(e) for e in roster)):
        failures.append("engine_roster must be a non-empty list of compact ids")

    fixtures = manifest["calibration_fixtures"]
    if not isinstance(fixtures, list) or not fixtures:
        failures.append("calibration_fixtures must be a non-empty list")
    else:
        for i, entry in enumerate(fixtures):
            if (not isinstance(entry, dict)
                    or set(entry) != {"fixture_id", "sha256"}
                    or not _ID.fullmatch(str(entry.get("fixture_id", "")))
                    or not _HEX64.fullmatch(str(entry.get("sha256", "")))):
                failures.append(f"calibration_fixtures[{i}] must be "
                                "{fixture_id, sha256}")

    oracles = manifest["world_oracles"]
    if not isinstance(oracles, list) or not oracles:
        failures.append("world_oracles must be a non-empty list")
    else:
        for i, entry in enumerate(oracles):
            if (not isinstance(entry, dict)
                    or set(entry) != {"oracle_id", "timestamp", "sha256"}
                    or not _ID.fullmatch(str(entry.get("oracle_id", "")))
                    or not _HEX64.fullmatch(str(entry.get("sha256", "")))):
                failures.append(f"world_oracles[{i}] must be "
                                "{oracle_id, timestamp, sha256}")
            elif not _DATE_PREFIX.match(str(entry["timestamp"])):
                failures.append(f"world_oracles[{i}].timestamp must be a dated "
                                "record (YYYY-MM-DD...)")

    probe = manifest["ignorance_probe_contract"]
    if (not isinstance(probe, dict)
            or set(probe) != {"probe_fixture_ids", "max_recoverable_rate"}):
        failures.append("ignorance_probe_contract must be "
                        "{probe_fixture_ids, max_recoverable_rate}")
    else:
        ids = probe["probe_fixture_ids"]
        if (not isinstance(ids, list) or not ids
                or not all(isinstance(p, str) and _ID.fullmatch(p) for p in ids)):
            failures.append("probe_fixture_ids must be non-empty compact ids")
        rate = probe["max_recoverable_rate"]
        if not isinstance(rate, (int, float)) or isinstance(rate, bool) \
                or not (0.0 <= float(rate) < 1.0):
            failures.append("max_recoverable_rate must be in [0, 1)")

    # --- optional population region (§9.4/§12 deadline is pre-held-out) -----
    if "population_region" in manifest:
        region = manifest["population_region"]
        if region == {"response_curve_only": True}:
            pass  # typed non-license path (§9.4/§14.6)
        elif (isinstance(region, dict) and set(region) == {"vertices"}
                and isinstance(region["vertices"], list)):
            try:
                validate_prevalence_region(region["vertices"])
            except PlannerContractError as e:
                failures.append(f"population_region: {e}")
        else:
            failures.append("population_region must be {vertices: [...]} or "
                            "{response_curve_only: true}")

    _scan_forbidden_keys(manifest, "manifest", failures)

    if failures:
        return ManifestCheckResult(False, tuple(failures), None)
    return ManifestCheckResult(True, (), manifest_hash(manifest))
