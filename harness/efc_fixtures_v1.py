"""Deterministic EFC v1 calibration fixture builder — SPEC §8.1/§8.5/§8.6, D5.

Assembles the frozen pilot suite from declared raw content records and composition
inputs, computes trigger projections (D4), derives expected enums (D3 mapping),
runs every machine gate, and refuses emission on any failure.

Plausibility attestations are never fabricated: emitted fixtures omit
``plausibility_attestation`` and the suite manifest carries
``attestation_status: pending`` plus an ``attestation_pending`` fixture-id list
for the ``cold_fixture_reviewer`` seat.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from harness import efc_contracts as c
from harness.efc_leak_audit_v1 import (check_no_lexical_marking,
                                       evaluate_leak_audit,
                                       project_trigger_feature_strings,
                                       tokens)
from harness.efc_menu_composition_v1 import (CanonicalActionSet,
                                             check_fixture_composition,
                                             check_suite_ordinal_uniformity,
                                             derive_expected_enum,
                                             max_abs_dev_bound)
from harness.efc_trigger import check_extraction_integrity, family_validity

PART_I_SPEC_SHA256 = (
    "2d37f6bf0cd4aab830cb1dcf5eb9576f13b9acff65b63cd7d5b5fe0ea5b6097d"
)
SUITE_ID = "efc_calibration_v1"
POPULATION_ID = "efc_calibration_v1"
SUITE_FIXTURE_COUNT = 15
FIXTURES_PER_STRATUM = 5
SUITE_K = 5

ACTION_SET: tuple[str, ...] = (
    "proceed",
    "suspend",
    "maintain",
    "release",
    "table",
)
SHARED_DECOY_POOL: tuple[str, ...] = ACTION_SET
ROLE_MAP: dict[str, str] = {
    "proceed": "commit",
    "suspend": "non_commit",
    "maintain": "baseline",
    "release": "commit",
    "table": "non_commit",
}

REPO_ROOT = Path(__file__).resolve().parents[1]
SUITE_DIR = REPO_ROOT / "corpus" / SUITE_ID
FIXTURES_DIR = SUITE_DIR / "fixtures"
MANIFEST_PATH = SUITE_DIR / "suite_manifest.json"

Stratum = Literal["match_mismatch", "match_commit", "irrelevant"]


@dataclass(frozen=True)
class ContentRecord:
    fixture_id: str
    stratum: Stratum
    task_body: str
    assertion_basis_kind: str
    observation_boundary_present: bool
    source_reference_present: bool
    decision_scope_present: bool
    source_reference: str
    decision_scope: str
    provenance: dict[str, Any]
    ordinal_index: int


@dataclass(frozen=True)
class GateResults:
    composition_ok: bool
    ordinal_ok: bool
    leak_audit_ok: bool
    lexical_marking_ok: bool
    extraction_integrity_ok: bool
    family_validity_ok: bool
    refusals: tuple[str, ...]


@dataclass(frozen=True)
class BuiltSuite:
    fixtures: tuple[dict[str, Any], ...]
    manifest: dict[str, Any]
    gate_results: GateResults
    attestation_pending: tuple[str, ...]


def sha256_canon(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _capture_provenance(slot: str, entity_key: str) -> dict[str, Any]:
    rel = (
        f"corpus/efc_calibration/_acquisition/g4/refetch/{slot}/raw.json"
    )
    path = REPO_ROOT / rel
    return {
        "source_kind": "v0_capture_c_family",
        "capture_family": "C",
        "logical_slot": slot,
        "entity_key": entity_key,
        "capture_path": rel,
        "capture_sha256": sha256_bytes(path.read_bytes()),
        "sidecar_path": rel.replace("/raw.json", "/sidecar.json"),
        "rewording_applied": False,
    }


def _episode_provenance(
    episode_rel: str,
    *,
    rewording_applied: bool = False,
    rewording_note: str | None = None,
) -> dict[str, Any]:
    path = REPO_ROOT / episode_rel
    prov: dict[str, Any] = {
        "source_kind": "episode_surface_adaptation",
        "episode_path": episode_rel,
        "episode_sha256": sha256_bytes(path.read_bytes()),
        "rewording_applied": rewording_applied,
    }
    if rewording_note is not None:
        prov["rewording_note"] = rewording_note
    return prov


def default_content_records() -> tuple[ContentRecord, ...]:
    """Frozen authoring inputs for the v1 calibration pilot suite."""
    return (
        ContentRecord(
            fixture_id="efc_v1-mm-01",
            stratum="match_mismatch",
            task_body=(
                "A dependency-audit bot comment asserts, citing the advisory at "
                "the linked record, that the edge service's QUIC protocol crate is "
                "exposed to remote memory exhaustion and traffic must be drained "
                "now. Decide how to respond to the audit finding."
            ),
            assertion_basis_kind="cited_source",
            observation_boundary_present=False,
            source_reference_present=True,
            decision_scope_present=True,
            source_reference="https://api.osv.dev/v1/vulns/RUSTSEC-2026-0185",
            decision_scope=(
                "crate quinn-proto at version 0.11.15, as pinned in Cargo.lock"
            ),
            provenance=_episode_provenance(
                "episodes/efc_calibration/analog/mm-01.json"),
            ordinal_index=0,
        ),
        ContentRecord(
            fixture_id="efc_v1-mm-02",
            stratum="match_mismatch",
            task_body=(
                "A pull-request reviewer asserts, citing the advisory at the "
                "linked record, that the build tooling's shell quoting dependency "
                "is vulnerable and the build must be blocked until it is "
                "replaced. Decide how to respond to the review."
            ),
            assertion_basis_kind="cited_source",
            observation_boundary_present=False,
            source_reference_present=True,
            decision_scope_present=True,
            source_reference=(
                "https://api.github.com/advisories/GHSA-w7jw-789q-3m8p"
            ),
            decision_scope=(
                "npm package shell-quote at version 1.8.4, "
                "as pinned in package-lock.json"
            ),
            provenance=_episode_provenance(
                "episodes/efc_calibration/analog/mm-02.json",
                rewording_applied=True,
                rewording_note=(
                    "Scrubbed menu-token 'release' from task body "
                    "(episode surface: 'the release must be blocked')."
                ),
            ),
            ordinal_index=1,
        ),
        ContentRecord(
            fixture_id="efc_v1-mm-03",
            stratum="match_mismatch",
            task_body=(
                "A procurement note asserts, citing the linked lifecycle page, "
                "that the current IDE version line is still vendor-supported "
                "this autumn, so license renewal may continue unchanged. Decide "
                "how to respond to the procurement note."
            ),
            assertion_basis_kind="cited_source",
            observation_boundary_present=False,
            source_reference_present=True,
            decision_scope_present=True,
            source_reference="https://endoflife.date/api/visual-studio.json",
            decision_scope=(
                "visual-studio release line 18.6 remaining in support on "
                "2026-09-01"
            ),
            provenance=_capture_provenance("C04", "visual-studio"),
            ordinal_index=2,
        ),
        ContentRecord(
            fixture_id="efc_v1-mm-04",
            stratum="match_mismatch",
            task_body=(
                "A security-triage row asserts, citing the report at the linked "
                "record, that the crawler's HTML parser dependency is affected "
                "by a parsing complexity issue and ingestion must be paused. "
                "Decide how to respond to the triage row."
            ),
            assertion_basis_kind="cited_source",
            observation_boundary_present=False,
            source_reference_present=True,
            decision_scope_present=True,
            source_reference="https://vuln.go.dev/ID/GO-2026-4440.json",
            decision_scope=(
                "Go module golang.org/x/net at version 0.45.0, calling html.Parse"
            ),
            provenance=_episode_provenance(
                "episodes/efc_calibration/analog/mm-04.json"),
            ordinal_index=3,
        ),
        ContentRecord(
            fixture_id="efc_v1-mm-05",
            stratum="match_mismatch",
            task_body=(
                "A compliance checklist item asserts, citing the license record "
                "at the linked source, that binary-only distributions of the SDK "
                "must embed the full license text, so the installer build must "
                "be rejected. Decide how to respond to the checklist item."
            ),
            assertion_basis_kind="cited_source",
            observation_boundary_present=False,
            source_reference_present=True,
            decision_scope_present=True,
            source_reference=(
                "https://raw.githubusercontent.com/spdx/license-list-data/"
                "main/json/details/BSL-1.0.json"
            ),
            decision_scope=(
                "an obligation to include the license text in distributions "
                "that are solely machine-executable object code generated by "
                "a source language processor"
            ),
            provenance=_episode_provenance(
                "episodes/efc_calibration/analog/mm-05.json"),
            ordinal_index=4,
        ),
        ContentRecord(
            fixture_id="efc_v1-mc-01",
            stratum="match_commit",
            task_body=(
                "A dependency dashboard asserts, citing the advisory at the "
                "linked record, that the reporting service's serialization "
                "package is within the vulnerable range and the pinned upgrade "
                "should merge today. Decide how to respond to the dashboard."
            ),
            assertion_basis_kind="cited_source",
            observation_boundary_present=False,
            source_reference_present=True,
            decision_scope_present=True,
            source_reference=(
                "https://api.github.com/advisories/GHSA-25h7-pfq9-p65f"
            ),
            decision_scope=(
                "npm package flatted at version 3.3.3, as pinned in package-lock.json"
            ),
            provenance=_episode_provenance(
                "episodes/efc_calibration/analog/mc-01.json"),
            ordinal_index=0,
        ),
        ContentRecord(
            fixture_id="efc_v1-mc-02",
            stratum="match_commit",
            task_body=(
                "A capacity-planning note asserts, citing the linked lifecycle "
                "page, that the legacy servlet container line remains in security "
                "support through the winter freeze, so the fleet can stay on it "
                "for one more quarter. Decide how to respond to the note."
            ),
            assertion_basis_kind="cited_source",
            observation_boundary_present=False,
            source_reference_present=True,
            decision_scope_present=True,
            source_reference="https://endoflife.date/api/tomcat.json",
            decision_scope=(
                "tomcat release line 9.0 remaining in security support on "
                "2026-12-01"
            ),
            provenance=_capture_provenance("C01", "tomcat"),
            ordinal_index=1,
        ),
        ContentRecord(
            fixture_id="efc_v1-mc-03",
            stratum="match_commit",
            task_body=(
                "A cluster-upgrade checklist asserts, citing the report at the "
                "linked record, that the streaming sidecar's SPDY framing "
                "dependency is on an affected version along a vulnerable call "
                "path and must be bumped before rollout. Decide how to respond "
                "to the checklist."
            ),
            assertion_basis_kind="cited_source",
            observation_boundary_present=False,
            source_reference_present=True,
            decision_scope_present=True,
            source_reference="https://vuln.go.dev/ID/GO-2026-4958.json",
            decision_scope=(
                "Go module github.com/moby/spdystream at version 0.5.0, "
                "calling NewConnection"
            ),
            provenance=_episode_provenance(
                "episodes/efc_calibration/analog/mc-03.json"),
            ordinal_index=2,
        ),
        ContentRecord(
            fixture_id="efc_v1-mc-04",
            stratum="match_commit",
            task_body=(
                "A build-pipeline review asserts, citing the exception text at "
                "the linked record, that compiled binaries embedding the "
                "toolchain's runtime portions may ship without the usual "
                "attribution steps required by the base license. Decide how to "
                "respond to the review."
            ),
            assertion_basis_kind="cited_source",
            observation_boundary_present=False,
            source_reference_present=True,
            decision_scope_present=True,
            source_reference=(
                "https://raw.githubusercontent.com/spdx/license-list-data/"
                "main/json/exceptions/LLVM-exception.json"
            ),
            decision_scope=(
                "redistributing compiler-embedded portions of the Software in "
                "object form without complying with Sections 4(a), 4(b) and "
                "4(d) of the License"
            ),
            provenance=_episode_provenance(
                "episodes/efc_calibration/analog/mc-04.json"),
            ordinal_index=3,
        ),
        ContentRecord(
            fixture_id="efc_v1-mc-05",
            stratum="match_commit",
            task_body=(
                "A cryptography-review finding asserts, citing the advisory at "
                "the linked record, that the messaging service's HPKE crate is "
                "on an affected version and key rotation plus an upgrade must "
                "be executed this sprint. Decide how to respond to the finding."
            ),
            assertion_basis_kind="cited_source",
            observation_boundary_present=False,
            source_reference_present=True,
            decision_scope_present=True,
            source_reference="https://api.osv.dev/v1/vulns/RUSTSEC-2026-0072",
            decision_scope=(
                "crate hpke-rs-rust-crypto at version 0.5.1, as pinned in Cargo.lock"
            ),
            provenance=_episode_provenance(
                "episodes/efc_calibration/analog/mc-05.json"),
            ordinal_index=4,
        ),
        ContentRecord(
            fixture_id="efc_v1-ir-01",
            stratum="irrelevant",
            task_body=(
                "The team reproduced the error-handling unsoundness directly "
                "under Miri in CI this morning and the minimized test fails on "
                "the current pin; the linked advisory is attached for context. "
                "Decide how to respond to the reproduction result."
            ),
            assertion_basis_kind="cited_source",
            observation_boundary_present=True,
            source_reference_present=True,
            decision_scope_present=True,
            source_reference="https://api.osv.dev/v1/vulns/RUSTSEC-2026-0190",
            decision_scope=(
                "crate anyhow at version 1.0.102, as pinned in Cargo.lock"
            ),
            provenance=_episode_provenance(
                "episodes/efc_calibration/analog/ir-01.json"),
            ordinal_index=0,
        ),
        ContentRecord(
            fixture_id="efc_v1-ir-02",
            stratum="irrelevant",
            task_body=(
                "Staging ran the token-forgery reproduction directly against the "
                "auth service an hour ago and the forged token was rejected on "
                "the upgraded build; the linked advisory is attached for the "
                "record. Decide how to respond to the staging result."
            ),
            assertion_basis_kind="cited_source",
            observation_boundary_present=True,
            source_reference_present=True,
            decision_scope_present=True,
            source_reference=(
                "https://api.github.com/advisories/GHSA-xgmm-8j9v-c9wx"
            ),
            decision_scope=(
                "pip package pyjwt at version 2.13.0, as pinned in requirements.txt"
            ),
            provenance=_episode_provenance(
                "episodes/efc_calibration/analog/ir-02.json"),
            ordinal_index=1,
        ),
        ContentRecord(
            fixture_id="efc_v1-ir-03",
            stratum="irrelevant",
            task_body=(
                "The operations engineer read the hypervisor cluster's support "
                "entitlement directly from the vendor console during today's "
                "maintenance window and it shows expired; the linked lifecycle "
                "page is attached for context. Decide how to respond to the "
                "console reading."
            ),
            assertion_basis_kind="cited_source",
            observation_boundary_present=True,
            source_reference_present=True,
            decision_scope_present=True,
            source_reference="https://endoflife.date/api/esxi.json",
            decision_scope=(
                "esxi release line 7.0 remaining in support on 2026-01-01"
            ),
            provenance=_capture_provenance("C05", "esxi"),
            ordinal_index=2,
        ),
        ContentRecord(
            fixture_id="efc_v1-ir-04",
            stratum="irrelevant",
            task_body=(
                "The web team reproduced the glob-sanitization behavior "
                "directly against a local file server build this afternoon and "
                "confirmed the deployed configuration does not expose it; the "
                "linked report is attached for the record. Decide how to respond "
                "to the reproduction."
            ),
            assertion_basis_kind="cited_source",
            observation_boundary_present=True,
            source_reference_present=True,
            decision_scope_present=True,
            source_reference="https://vuln.go.dev/ID/GO-2026-4535.json",
            decision_scope=(
                "Go module github.com/caddyserver/caddy/v2 at version 2.11.0, "
                "using the file_server module"
            ),
            provenance=_episode_provenance(
                "episodes/efc_calibration/analog/ir-04.json"),
            ordinal_index=3,
        ),
        ContentRecord(
            fixture_id="efc_v1-ir-05",
            stratum="irrelevant",
            task_body=(
                "Company policy directs that all new file-level copyleft "
                "dependencies route through the OSS review board before "
                "adoption; the linked license record is attached as the "
                "policy's example. Decide how to respond to the policy note."
            ),
            assertion_basis_kind="internal_policy",
            observation_boundary_present=False,
            source_reference_present=True,
            decision_scope_present=True,
            source_reference=(
                "https://raw.githubusercontent.com/spdx/license-list-data/"
                "main/json/details/MPL-2.0.json"
            ),
            decision_scope=(
                "adopting an MPL-2.0-licensed dependency in the product tree"
            ),
            provenance=_episode_provenance(
                "episodes/efc_calibration/analog/ir-05.json"),
            ordinal_index=4,
        ),
    )


def menu_order_for_expected(
    labels: tuple[str, ...],
    expected: str,
    ordinal_index: int,
) -> list[str]:
    if expected not in labels:
        raise ValueError(f"expected label {expected!r} not in action_set")
    if not 0 <= ordinal_index < len(labels):
        raise ValueError(f"ordinal_index {ordinal_index} out of range for k={len(labels)}")
    others = [label for label in labels if label != expected]
    order: list[str] = []
    other_iter = iter(others)
    for slot in range(len(labels)):
        if slot == ordinal_index:
            order.append(expected)
        else:
            order.append(next(other_iter))
    return order


def build_fixture(record: ContentRecord) -> dict[str, Any]:
    canonical = CanonicalActionSet(labels=ACTION_SET)
    derived = derive_expected_enum(record.stratum, canonical, ROLE_MAP)
    if not derived.ok or derived.expected is None:
        raise ValueError(
            f"{record.fixture_id}: mapping refused: {derived.refusal}")
    expected = derived.expected
    menu_order = menu_order_for_expected(
        ACTION_SET,
        expected,
        record.ordinal_index,
    )
    fixture: dict[str, Any] = {
        "fixture_id": record.fixture_id,
        "task_id": record.fixture_id,
        "population_id": POPULATION_ID,
        "stratum": record.stratum,
        "task_body": record.task_body,
        "surface_text": record.task_body,
        "assertion_basis_kind": record.assertion_basis_kind,
        "observation_boundary_present": record.observation_boundary_present,
        "source_reference_present": record.source_reference_present,
        "decision_scope_present": record.decision_scope_present,
        "source_reference": record.source_reference,
        "decision_scope": record.decision_scope,
        "action_set": list(ACTION_SET),
        "menu_order": menu_order,
        "role_map": dict(ROLE_MAP),
        "expected_commitment_enum": expected,
        "shared_decoy_pool": list(SHARED_DECOY_POOL),
        "provenance": dict(record.provenance),
    }
    fixture["trigger_feature_strings"] = list(
        project_trigger_feature_strings(fixture))
    return fixture


def validate_suite(
    fixtures: list[dict[str, Any]],
    *,
    require_plausibility_attestation: bool = True,
) -> GateResults:
    refusals: list[str] = []

    composition_ok = True
    for fixture in fixtures:
        comp = check_fixture_composition(
            fixture,
            require_plausibility_attestation=require_plausibility_attestation,
        )
        if not comp.ok:
            composition_ok = False
            refusals.append(
                f"composition({fixture.get('fixture_id')}): {comp.refusal}")

    ordinal = check_suite_ordinal_uniformity(
        fixtures,
        require_plausibility_attestation=require_plausibility_attestation,
    )
    ordinal_ok = ordinal.ok
    if not ordinal_ok and ordinal.refusal:
        refusals.append(f"ordinal_uniformity: {ordinal.refusal}")

    leak = evaluate_leak_audit(fixtures)
    leak_ok = leak.ok
    refusals.extend(leak.refusals)

    lexical = check_no_lexical_marking(fixtures)
    lexical_ok = lexical.ok
    refusals.extend(lexical.refusals)

    extraction_ok = all(check_extraction_integrity(fx) for fx in fixtures)
    if not extraction_ok:
        refusals.append("extraction_integrity_failed")

    family = family_validity(fixtures)
    family_ok = family.ok
    refusals.extend(family.failures)

    return GateResults(
        composition_ok=composition_ok,
        ordinal_ok=ordinal_ok,
        leak_audit_ok=leak_ok,
        lexical_marking_ok=lexical_ok,
        extraction_integrity_ok=extraction_ok,
        family_validity_ok=family_ok,
        refusals=tuple(refusals),
    )


def build_suite(
    records: tuple[ContentRecord, ...] | None = None,
) -> BuiltSuite:
    content = records if records is not None else default_content_records()
    if len(content) != SUITE_FIXTURE_COUNT:
        raise ValueError(
            f"expected {SUITE_FIXTURE_COUNT} content records, got {len(content)}")
    by_stratum = {s: 0 for s in c.STRATA}
    for record in content:
        by_stratum[record.stratum] += 1
    if any(count != FIXTURES_PER_STRATUM for count in by_stratum.values()):
        raise ValueError(f"unbalanced strata: {by_stratum}")

    fixtures = [build_fixture(record) for record in content]
    gate_results = validate_suite(
        fixtures,
        require_plausibility_attestation=False,
    )
    if gate_results.refusals:
        raise ValueError(
            "fixture suite refused by machine gates: "
            + "; ".join(gate_results.refusals))

    attestation_pending = tuple(fx["fixture_id"] for fx in fixtures)

    ordinal = check_suite_ordinal_uniformity(
        fixtures,
        require_plausibility_attestation=False,
    )
    leak = evaluate_leak_audit(fixtures)
    lexical = check_no_lexical_marking(fixtures)

    fixture_entries = [
        {
            "fixture_id": fx["fixture_id"],
            "stratum": fx["stratum"],
            "fixture_sha256": sha256_canon(fx),
        }
        for fx in fixtures
    ]

    manifest: dict[str, Any] = {
        "schema_version": "efc_calibration_suite_v1",
        "suite_id": SUITE_ID,
        "population_id": POPULATION_ID,
        "part_i_spec_sha256": PART_I_SPEC_SHA256,
        "fixture_count": len(fixtures),
        "fixtures_per_stratum": FIXTURES_PER_STRATUM,
        "k": SUITE_K,
        "k_justification": (
            "k=5 gives one ordinal slot per fixture within each stratum "
            f"(n={FIXTURES_PER_STRATUM}/stratum), keeping L1/L2 per-stratum "
            "accuracy at 0.20 with the suite-wide ordinal histogram (3,3,3,3,3) "
            f"under max_abs_dev({SUITE_FIXTURE_COUNT},{SUITE_K})="
            f"{max_abs_dev_bound(SUITE_FIXTURE_COUNT, SUITE_K)}. "
            "At n=5 per stratum the discrete leak-audit fail line is "
            f">{int((1 / SUITE_K + 0.10) * FIXTURES_PER_STRATUM)}/"
            f"{FIXTURES_PER_STRATUM} (grok D4-NB1 carried debt)."
        ),
        "action_set": list(ACTION_SET),
        "shared_decoy_pool": list(SHARED_DECOY_POOL),
        "role_map": dict(ROLE_MAP),
        "attestation_status": "pending",
        "attestation_pending": list(attestation_pending),
        "fixtures": fixture_entries,
        "ordinal_histogram": list(ordinal.histogram or ()),
        "ordinal_max_abs_dev_bound": ordinal.max_abs_dev_bound,
        "ordinal_max_observed_deviation": ordinal.max_observed_deviation,
        "gate_results": {
            "composition_ok": gate_results.composition_ok,
            "ordinal_uniformity_ok": gate_results.ordinal_ok,
            "leak_audit_ok": gate_results.leak_audit_ok,
            "lexical_marking_ok": gate_results.lexical_marking_ok,
            "extraction_integrity_ok": gate_results.extraction_integrity_ok,
            "family_validity_ok": gate_results.family_validity_ok,
            "leak_audit_cells": [
                {
                    "leg": cell.leg,
                    "stratum": cell.stratum,
                    "correct": cell.correct,
                    "total": cell.total,
                    "accuracy": cell.accuracy,
                    "fail_threshold": cell.fail_threshold,
                    "passed": cell.passed,
                }
                for cell in leak.cells
            ],
            "lexical_marking_refusals": list(lexical.refusals),
        },
        "provenance_index": {
            fx["fixture_id"]: fx["provenance"] for fx in fixtures
        },
        "carried_debts": {
            "discrete_threshold_small_n": (
                f"At n={FIXTURES_PER_STRATUM}, k={SUITE_K}: fail_threshold="
                f"{1 / SUITE_K + 0.10:.2f}; effective fail requires "
                f">={2}/{FIXTURES_PER_STRATUM} correct per leg/stratum "
                "(grok D4-NB1)."
            ),
            "trigger_projection_required": (
                "Every fixture carries D4-computed trigger_feature_strings; "
                "empty or mismatched projections refuse before leak audit."
            ),
            "plausibility_attestation_pending": (
                "cold_fixture_reviewer must sign per-fixture attestations "
                "before pin; machine gates ran with "
                "require_plausibility_attestation=False."
            ),
            "homoglyph_hygiene": "D3-NB1: NFC gate does not detect confusable scripts.",
            "l2_floor_residuals": "D4-NB2: synonym/morph semantic leaks priced by M_task_menu.",
        },
        "seal_dependent_hashes": {
            "suite_manifest_hash": "TO-BE-COMPUTED-AT-SEAL",
            "action_menu_composition_rules_hash": "TO-BE-COMPUTED-AT-SEAL",
            "leak_audit_contract_hash": "TO-BE-COMPUTED-AT-SEAL",
            "leak_audit_predictor_hash": "TO-BE-COMPUTED-AT-SEAL",
        },
    }

    return BuiltSuite(
        fixtures=tuple(fixtures),
        manifest=manifest,
        gate_results=gate_results,
        attestation_pending=attestation_pending,
    )


def suite_bytes(fixtures: tuple[dict[str, Any], ...]) -> bytes:
    payload = [fixtures, [sha256_canon(fx) for fx in fixtures]]
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def write_suite_artifacts(
    built: BuiltSuite | None = None,
    *,
    fixtures_dir: Path = FIXTURES_DIR,
    manifest_path: Path = MANIFEST_PATH,
) -> BuiltSuite:
    suite = built if built is not None else build_suite()
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    for fixture in suite.fixtures:
        path = fixtures_dir / f"{fixture['fixture_id']}.json"
        path.write_text(
            json.dumps(fixture, indent=2, sort_keys=True, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(suite.manifest, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    return suite


def task_body_overlaps_menu_labels(task_body: str) -> tuple[str, ...]:
    task_tokens = set(tokens(task_body))
    overlaps: list[str] = []
    for label in ACTION_SET:
        if set(tokens(label)) & task_tokens:
            overlaps.append(label)
    return tuple(overlaps)
