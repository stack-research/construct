"""C4d append-only final conformance and superseding pin — finalization only.

The first pin (`calibration_manifest_pin.json`, C4b) was written and verified
against a conformance report whose K4 lineage row had already been restamped
by a test-suite mutator; after C4c restored the G4-audited ledger bytes and
removed the mutators, that pin correctly refuses forever. C4d does not touch
it. Instead it appends four artifacts (Sol's C4d assignment):

  - `c4_final_conformance_report.json` — every prior C4 check re-derived from
    CURRENT bytes, plus explicit resolutions of all carried flags, a
    cross-artifact G4 equality requirement (disk ledger == the value the G4
    plan/refetch/identity-audit each pinned, not merely disk self-equality),
    the C4c repair evidence, and Grok's narrow review as thread testimony;
  - `calibration_manifest_pin_failure_record.json` — types the first attempt
    `invalid_non_authoritative_preserved`, binds its bytes, cause, and the
    C4c repair evidence; states no engine/probe/calibration contact occurred
    under it;
  - `calibration_manifest_pin_superseding.json` — a new pin event
    (`…-s2`, predecessor `part_i_sealed`, `supersedes` → the failed event)
    binding the UNCHANGED manifest/sibling/ledger/approval bytes plus the
    C4a review, C4c attestation, final report, failure record, and every
    current transitive lineage identity;
  - `calibration_manifest_pin_status.json` — the SOLE active-pin selector:
    exactly one active pin; the failed pin is listed invalid; neither pin is
    authoritative without a valid status artifact, and consumers must reject
    the old pin alone.

Every payload is deterministic (no wall clock) except the superseding pin's
event time, stamped once at first creation and preserved verbatim on
idempotent rerun. Writes are atomic (same-dir temp + rename) and happen only
after ALL validation passes; a conflicting existing artifact refuses.

The final report records the C4c-repaired test-file hashes; full
verification recomputes them, so any later edit to those files (or to any
bound byte) invalidates verification — Sol's post-pin rule, applied
literally.

Zero network/engines/probes/listings/held-out contact. This bundle does NOT
authorize ignorance probes or calibration contact.

Run:   python3 -m harness.efc_pin_c4d --pin
       python3 -m harness.efc_pin_c4d --verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from harness import efc_contracts as c
from harness import efc_pin_c4b as c4b
from harness.efc_manifest import check_calibration_manifest
from harness.efc_pin_c4b import (PinRefusal, _write_atomic,
                                 canonical_json_bytes, sha256_path)

ROOT = Path(__file__).resolve().parents[1]
C4_DIR = "corpus/efc_calibration/authoring_c4"

FINAL_REPORT_REL = f"{C4_DIR}/c4_final_conformance_report.json"
FAILURE_RECORD_REL = f"{C4_DIR}/calibration_manifest_pin_failure_record.json"
SUPERSEDING_PIN_REL = f"{C4_DIR}/calibration_manifest_pin_superseding.json"
STATUS_REL = f"{C4_DIR}/calibration_manifest_pin_status.json"

FAILED_PIN_REL = c4b.PIN_REL
FAILED_PIN_SHA = ("9ea99f15392e1b46e01964f5eb656b09205585901ae696bdd4aa46554"
                  "0632e0d")
FAILED_PIN_EVENT_ID = "efc-cal-manifest-pin-2600d1fdba7b"
SUPERSEDING_EVENT_ID = f"{FAILED_PIN_EVENT_ID}-s2"

# byte identities fixed by prior rulings, reverified before every write ------
HISTORICAL_REPORT_SHA = ("e5f16e22db4793757ea5dcbca89597ff5e997421206e35197d7"
                         "f80eb97888d15")
APPROVAL_RECORD_SHA = ("4545fb8b2b6e29bdce3ecbdd54d2c7b25c3de77c4a02701011222"
                       "7eb338f08a9")
C4C_ATTESTATION_REL = f"{C4_DIR}/c4c_lineage_hygiene_repair.json"
C4C_ATTESTATION_SHA = ("1e649f89a041cee9c18b56637962e1e0684069eb8cfb8ea9ce1fa"
                       "6753d2d1cd7")
G4_AUDIT_LEDGER_SHA = ("b086689591d03a2f9ee6aa7bfffd16683f58d5b4d4674f6f19795"
                       "089224d45ac")
K4_LEDGER_REL = ("corpus/efc_calibration/_acquisition/k4/"
                 "promotion_identity_ledger.json")
G4_RECORD_RELS = (
    "corpus/efc_calibration/_acquisition/g4/plan.json",
    "corpus/efc_calibration/_acquisition/g4/refetch_report.json",
    "corpus/efc_calibration/_acquisition/g4/identity_audit.json",
)
C4C_REPAIRED_FILES = ("tests/test_efc_capture_k4.py",
                      "tests/test_efc_author_c4.py",
                      "tests/test_efc_lineage_hygiene_c4c.py")


def _refuse(msg: str) -> None:
    raise PinRefusal(msg)


def _load(root: Path, rel: str):
    return json.loads((root / rel).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# bundle validation — every C4d verifier refusal, structure/hash layer
# ---------------------------------------------------------------------------

def validate_bundle(root: Path = ROOT, require_bundle: bool = True) -> dict:
    """All refusals from Sol's C4d verifier list that are decidable from
    hashes, schemas, and cross-artifact identity. `require_bundle=False` is
    the pre-write mode used by pin(): it validates every INPUT but does not
    demand the four C4d artifacts yet."""
    # --- reviewed input bytes (unchanged since C4a/C4c) ----------------------
    fixed = ((c4b.MANIFEST_REL, c4b.MANIFEST_FILE_SHA),
             (c4b.SIBLING_REL, c4b.SIBLING_SHA),
             (c4b.LEDGER_REL, c4b.LEDGER_SHA),
             (c4b.REVIEW_REL, c4b.REVIEW_SHA),
             (c4b.REPORT_REL, HISTORICAL_REPORT_SHA),
             (c4b.APPROVAL_RECORD_REL, APPROVAL_RECORD_SHA),
             (C4C_ATTESTATION_REL, C4C_ATTESTATION_SHA),
             (FAILED_PIN_REL, FAILED_PIN_SHA))
    for rel, want in fixed:
        path = root / rel
        if not path.is_file():
            _refuse(f"missing required input {rel}")
        got = sha256_path(path)
        if got != want:
            _refuse(f"{rel}: sha256 {got} != bound {want} (mutation of a "
                    "reviewed/preserved artifact)")

    manifest = _load(root, c4b.MANIFEST_REL)
    sibling = _load(root, c4b.SIBLING_REL)
    ledger = _load(root, c4b.LEDGER_REL)
    review = _load(root, c4b.REVIEW_REL)
    attestation = _load(root, C4C_ATTESTATION_REL)
    approval = _load(root, c4b.APPROVAL_RECORD_REL)

    # --- closed schema + canonical identity ---------------------------------
    result = check_calibration_manifest(manifest)
    if not result.ok:
        _refuse(f"manifest failed the closed-schema check: {result.failures}")
    if result.manifest_hash != c4b.MANIFEST_CANONICAL_HASH:
        _refuse("canonical manifest hash does not recompute to the approved "
                "identity")

    # --- approval / review / repair semantics --------------------------------
    if (root / c4b.APPROVAL_RECORD_REL).read_bytes() \
            != canonical_json_bytes(c4b.build_approval_record()):
        _refuse("operator approval record does not match the append-only "
                "record bytes")
    if approval["approved_engine_roster"] != manifest["engine_roster"] \
            or approval["approved_total_budget_tokens"] \
            != manifest["total_budget_tokens"] \
            or ledger["totals"]["roster_total_budget_tokens"] \
            != c4b.APPROVED_BUDGET:
        _refuse("approval roster/budget do not match the manifest and ledger")
    if review.get("aggregate") != "endorse" or not review.get("checks") \
            or any(chk.get("verdict") != "endorse"
                   for chk in review["checks"]):
        _refuse("C4a review is not an unqualified endorse")
    if attestation.get("authorizes_repin") is not False or \
            attestation.get("authorizes_probes_or_calibration_contact") \
            is not False:
        _refuse("C4c attestation authorization flags are not the ruled "
                "values")

    # --- G4 authority: disk AND cross-artifact equality ----------------------
    k4_disk = sha256_path(root / K4_LEDGER_REL)
    if k4_disk != G4_AUDIT_LEDGER_SHA:
        _refuse(f"K4 ledger on disk {k4_disk} != G4-audited authority "
                f"{G4_AUDIT_LEDGER_SHA}")
    for rel in G4_RECORD_RELS:
        recorded = _load(root, rel).get("promotion_identity_ledger_sha256")
        if recorded != G4_AUDIT_LEDGER_SHA:
            _refuse(f"{rel} records promotion ledger {recorded} != the G4 "
                    "audit authority (cross-artifact mismatch)")

    # --- transitive lineage, recomputed from bytes ---------------------------
    lineage = {name: sha256_path(root / rel)
               for name, rel in c4b.LINEAGE_PATHS.items()}
    if lineage["k4_promotion_identity_ledger"] != G4_AUDIT_LEDGER_SHA:
        _refuse("lineage recompute disagrees with the G4 authority")

    # --- decoding sibling: name never authoritative without payload bytes ----
    for branch, want in (("local", c4b.DECODING_LOCAL_SHA),
                         ("api", c4b.DECODING_API_SHA)):
        payload = sibling["branches"][branch].get("decoding_contract")
        if not payload:
            _refuse(f"sibling carries no {branch} decoding payload bytes")
        got = c.sha256_utf8(json.dumps(payload, sort_keys=True,
                                       separators=(",", ":")))
        if got != want:
            _refuse(f"{branch} decoding payload does not recompute to its "
                    "R2 canonical hash")

    loaded = {"manifest": manifest, "sibling": sibling, "ledger": ledger,
              "review": review, "attestation": attestation,
              "lineage": lineage}
    if not require_bundle:
        return loaded

    # --- status artifact: the sole active-pin selector ------------------------
    status_path = root / STATUS_REL
    if not status_path.is_file():
        if (root / FAILED_PIN_REL).is_file():
            _refuse("status artifact missing: the old pin alone must be "
                    "rejected — no pin is authoritative without a valid "
                    "status selector")
        _refuse("status artifact missing")
    status = _load(root, STATUS_REL)
    pins = status.get("pins")
    if not isinstance(pins, list) or not pins:
        _refuse("status artifact carries no pin entries")
    active = [p for p in pins if p.get("role") == "active"]
    invalid = [p for p in pins if p.get("role") == "invalid"]
    if len(active) != 1 or len(active) + len(invalid) != len(pins):
        _refuse(f"status artifact is ambiguous: {len(active)} active pins "
                "(exactly one required, all others typed invalid)")
    if active[0].get("path") != SUPERSEDING_PIN_REL \
            or active[0].get("event_id") != SUPERSEDING_EVENT_ID:
        _refuse("status artifact's active pin is not the superseding event")
    if not any(p.get("path") == FAILED_PIN_REL
               and p.get("sha256") == FAILED_PIN_SHA
               and p.get("disposition") == "invalid_non_authoritative_preserved"
               for p in invalid):
        _refuse("status artifact does not type the failed first pin invalid")

    # --- the three bound C4d artifacts ---------------------------------------
    for rel in (FINAL_REPORT_REL, FAILURE_RECORD_REL, SUPERSEDING_PIN_REL):
        if not (root / rel).is_file():
            _refuse(f"missing C4d bundle artifact {rel}")
    sup = _load(root, SUPERSEDING_PIN_REL)
    sup_sha = sha256_path(root / SUPERSEDING_PIN_REL)
    if active[0].get("sha256") != sup_sha:
        _refuse("status artifact hash does not match the superseding pin "
                "bytes (tampered status or pin)")
    bound = sup.get("binds", {})
    for rel, want in (
            (FINAL_REPORT_REL, sha256_path(root / FINAL_REPORT_REL)),
            (FAILURE_RECORD_REL, sha256_path(root / FAILURE_RECORD_REL))):
        if bound.get(rel, {}).get("sha256") != want:
            _refuse(f"superseding pin does not bind the current bytes of "
                    f"{rel} (mutation)")
    if sup.get("lineage_sha256") != dict(sorted(lineage.items())):
        _refuse("superseding pin lineage does not recompute from current "
                "bytes (lineage drift)")
    loaded["status"] = status
    loaded["superseding"] = sup
    return loaded


# ---------------------------------------------------------------------------
# final conformance derivation (full, real-tree, read-only)
# ---------------------------------------------------------------------------

def build_final_report_payload(root: Path = ROOT) -> dict:
    """Re-derives every prior C4 check from current bytes. Read-only: writes
    nothing. Uses the reviewed C4 builder's own functions on the real tree."""
    from harness import efc_author_c4 as a
    from harness.efc_check import (ProvenanceRecord, ProvenanceStore,
                                   WireComparisonRule,
                                   check_adapter_contract_hash)
    from harness.efc_compare_production import (build_production_contract,
                                                production_check_contract_hash)
    from harness.efc_packet import derive_call_plan, load_packet

    loaded = validate_bundle(root, require_bundle=False)
    index, payloads, sibling_hashes = a.load_verified_packet_files()
    oracles = a.load_oracles()
    surface = a.load_roster_surface()

    adapter_hash = check_adapter_contract_hash()
    check_hash = production_check_contract_hash(build_production_contract(),
                                                adapter_hash)
    if check_hash != loaded["manifest"]["check_contract_hash"]:
        _refuse("production check contract hash no longer recomputes to the "
                "manifest value")

    probe_ids = payloads["ignorance-probe-contract"]["probe_fixture_ids"]
    plan = derive_call_plan(len(probe_ids), 2)
    rows, totals = a.derive_budget_rows(payloads, oracles)
    if rows != loaded["ledger"]["per_branch_rows"] \
            or 2 * totals["branch_total_tokens"] != c4b.APPROVED_BUDGET:
        _refuse("budget rows/totals no longer re-derive to the pinned "
                "ledger bytes")

    store = ProvenanceStore([ProvenanceRecord(
        oracle_id=o["payload"]["oracle_id"],
        source_reference=o["payload"]["source_reference"],
        authoritative_scope=o["payload"]["authoritative_scope"],
        cited_text=o["payload"]["cited_text"]) for o in oracles.values()])
    verdicts = {o["payload"]["authoritative_scope"]:
                o["payload"]["expected_scope_matches"]
                for o in oracles.values()}
    packet = load_packet(a.PACKET_ROOT, store, WireComparisonRule(
        rule_id="efc_c4_budget_lookup",
        contract={"rule_id": "efc_c4_budget_lookup", "wire_only": True,
                  "semantics": "see budget_derivation_ledger.json"},
        compare=lambda auth, dec: verdicts[auth]))
    if not packet.ok:
        _refuse(f"packet no longer loads cleanly: {packet.failures}")

    return {
        "schema_version": "efc_c4_final_conformance_report_v1",
        "status": "final_post_approval_post_repair",
        "derives_from": "current on-disk bytes only",
        "checks": {
            "packet_hash_verification":
                f"{len(payloads)} entries + {len(sibling_hashes)} siblings "
                "match packet_index.json",
            "roster_r2_contract_match": {
                branch: surface["branches"][branch]
                ["decoding_contract_canonical_sha256"]
                for branch in ("local", "api")},
            "check_contract_recomputation": {
                "candidate_check_contract_hash": check_hash,
                "adapter_contract_sha256": adapter_hash},
            "derived_call_plan": {
                "probe_calls_branch": plan.probe_calls_branch,
                "s_family_calls_branch": plan.s_family_calls_branch,
                "analog_calls_branch": plan.analog_calls_branch,
                "primary_calls_branch": plan.primary_calls_branch,
                "conditional_calls_branch": plan.conditional_calls_branch,
                "ceiling_calls_branch": plan.ceiling_calls_branch,
                "roster_ceiling_total": plan.roster_ceiling_total},
            "budget_rederivation": {
                **totals,
                "rows_byte_equal_to_pinned_ledger": True,
                "total_budget_tokens": 2 * totals["branch_total_tokens"]},
            "manifest_machine_check": {
                "ok": True,
                "canonical_hash": c4b.MANIFEST_CANONICAL_HASH},
            "packet_loader": "ok",
            "population_declaration_byte_match": True,
            "no_placeholder_identities": "clean",
        },
        "resolutions": {
            "operator_roster_budget_approval": {
                "resolved_by": c4b.APPROVAL_RECORD_REL,
                "sha256": APPROVAL_RECORD_SHA},
            "extractor_identity_layer": {
                "resolved_by": "C4a check C5 endorse (two-layer identity: "
                               "module bytes + predicate contract)",
                "review_sha256": c4b.REVIEW_SHA},
            "decoding_contract_id_is_a_name": {
                "resolved_by": "atomic manifest+sibling binding in the "
                               "superseding pin; the name binds only through "
                               "the sibling payload bytes"},
            "license_binding_conformance_review": {
                "resolved_by": "C4a check C4 endorse citing the Grok C3 "
                               "license_audit (sf-04/mm-05/mc-04) and "
                               "byte-stable structured inputs through the "
                               "C3b parser repair"},
            "g4_lineage_authority": {
                "requirement": "disk ledger == G4 plan/refetch/audit pinned "
                               "value, cross-artifact, not disk-only",
                "value": G4_AUDIT_LEDGER_SHA,
                "holds": True},
        },
        "c4c_repair_evidence": {
            "attestation_path": C4C_ATTESTATION_REL,
            "attestation_sha256": C4C_ATTESTATION_SHA,
            "repaired_files_sha256": {
                rel: sha256_path(root / rel) for rel in C4C_REPAIRED_FILES},
            "note": "these file identities are recorded AND enforced by "
                    "full verification: editing them invalidates the pin "
                    "verification, per the post-pin invalidation rule",
        },
        "grok_narrow_review_testimony": {
            "participant": "cursor/grok-4.5",
            "thread": "construct/epistemic-frame-check-v0-content",
            "entry_timestamp_utc": "2026-07-15T11:54:00Z",
            "local_entry_file": None,
            "disclosure": "thread testimony; no separate review artifact "
                          "file was authored by that seat (per its "
                          "assignment)",
        },
        "historical_reports": {
            "pre_approval_report_current_sha256": HISTORICAL_REPORT_SHA,
            "byte_preserved": True,
            "stale_k4_lineage_note": "its recorded K4 hash predates the C4c "
                                     "restoration and is testimony only; "
                                     "current authority is this report's "
                                     "lineage_sha256",
            "handoff_time_sha256_testimony": "c46d6e3a366fa501311b8293c993af"
                                             "4a4b3674b662b1b929f841187171740"
                                             "b1b",
            "c4a_stabilized_sha256_testimony": "5b6ca196f668a4d9ae6fa44697b58"
                                               "1a42463deefa238240ef7d587f6a6"
                                               "0d955e",
        },
        "lineage_sha256": dict(sorted(loaded["lineage"].items())),
        "lineage_paths": dict(sorted(c4b.LINEAGE_PATHS.items())),
        "blocking_items": [],
        "disclosure": {
            "engines_contacted": 0, "listing_calls": 0, "probes_run": 0,
            "network_calls": 0, "held_out_fixtures_authored": 0,
            "historical_artifacts_modified": 0,
        },
    }


def build_failure_record(root: Path = ROOT) -> dict:
    return {
        "schema_version": "efc_calibration_pin_failure_record_v1",
        "disposition": "invalid_non_authoritative_preserved",
        "failed_pin": {
            "path": FAILED_PIN_REL,
            "sha256": FAILED_PIN_SHA,
            "event_id": FAILED_PIN_EVENT_ID,
            "written_and_first_verified_utc": "2026-07-15T10:35:25Z",
            "verifier_module_at_attempt_sha256": sha256_path(
                root / "harness/efc_pin_c4b.py"),
        },
        "verification_failure": {
            "observed": "post-pin --verify refusal: conformance report "
                        "bytes and K4 ledger lineage no longer matched the "
                        "bound identities",
            "cause": "tests/test_efc_capture_k4.py::"
                     "test_repair_ledger_zero_network called repair_ledger() "
                     "on the production K4_ROOT, restamping generated_at_utc "
                     "on every full-suite run; secondary: the C4 test "
                     "setUpClass reran the builder against the real tree",
            "semantic_drift": "none — 40 ledger rows byte-identical "
                              "throughout; timestamp-only",
            "first_reported": "claude/fable-5 thread entry "
                              "2026-07-15 (C4b handoff)",
        },
        "repair_evidence": {
            "c4c_attestation_sha256": C4C_ATTESTATION_SHA,
            "g4_authority_restored_sha256": G4_AUDIT_LEDGER_SHA,
            "reviewed_by": ["cursor/grok-4.5 narrow regression review "
                            "2026-07-15T11:54:00Z",
                            "codex/gpt-5.6-sol C4c close "
                            "2026-07-15T12:03:29Z"],
        },
        "contact_disclosure": "no engine, listing, probe, or calibration "
                              "contact occurred under the failed attempt",
    }


def build_superseding_pin(loaded: dict, binds_extra: dict,
                          pin_time_utc: str) -> dict:
    return {
        "schema_version": "efc_calibration_manifest_pin_v2_superseding",
        "status": "pinned",
        "pin_event": {
            "id": SUPERSEDING_EVENT_ID,
            "time_utc": pin_time_utc,
            "predecessor": "part_i_sealed",
            "part_i_spec_sha256": c.PART_I_SPEC_SHA256,
            "supersedes": {"event_id": FAILED_PIN_EVENT_ID,
                           "path": FAILED_PIN_REL,
                           "sha256": FAILED_PIN_SHA,
                           "disposition":
                               "invalid_non_authoritative_preserved"},
            "authorized_by": "codex/gpt-5.6-sol C4d assignment "
                             "(2026-07-15T12:03:29Z) on dan's operator "
                             "approval (2026-07-15T01:53:51Z)",
        },
        "binds": {
            c4b.MANIFEST_REL: {
                "sha256": c4b.MANIFEST_FILE_SHA,
                "canonical_manifest_hash": c4b.MANIFEST_CANONICAL_HASH},
            c4b.SIBLING_REL: {
                "sha256": c4b.SIBLING_SHA,
                "decoding_payload_canonical_sha256": {
                    "local": c4b.DECODING_LOCAL_SHA,
                    "api": c4b.DECODING_API_SHA}},
            c4b.LEDGER_REL: {
                "sha256": c4b.LEDGER_SHA,
                "total_budget_tokens": c4b.APPROVED_BUDGET},
            c4b.APPROVAL_RECORD_REL: {"sha256": APPROVAL_RECORD_SHA},
            c4b.REVIEW_REL: {"sha256": c4b.REVIEW_SHA},
            C4C_ATTESTATION_REL: {"sha256": C4C_ATTESTATION_SHA},
            c4b.REPORT_REL: {"sha256": HISTORICAL_REPORT_SHA,
                             "role": "historical_pre_approval_testimony"},
            **binds_extra,
        },
        "lineage_sha256": dict(sorted(loaded["lineage"].items())),
        "atomicity": "the calibration manifest and the roster/decoding "
                     "sibling are ONE pin unit: neither is authoritative "
                     "alone, and no pin is authoritative without the valid "
                     "status selector artifact",
        "disclosure": {
            "engines_contacted": 0, "listing_calls": 0, "probes_run": 0,
            "network_calls": 0, "held_out_fixtures_authored": 0,
            "authorizes_probes_or_calibration_contact": False,
        },
    }


def build_status(superseding_sha256: str) -> dict:
    return {
        "schema_version": "efc_calibration_pin_status_v1",
        "role": "sole_active_pin_selector",
        "rule": "consumers and verifiers MUST resolve this artifact first "
                "and MUST reject any pin presented without it; the failed "
                "first pin is never valid alone or otherwise",
        "pins": [
            {"role": "active",
             "event_id": SUPERSEDING_EVENT_ID,
             "path": SUPERSEDING_PIN_REL,
             "sha256": superseding_sha256},
            {"role": "invalid",
             "event_id": FAILED_PIN_EVENT_ID,
             "path": FAILED_PIN_REL,
             "sha256": FAILED_PIN_SHA,
             "disposition": "invalid_non_authoritative_preserved",
             "failure_record": FAILURE_RECORD_REL},
        ],
    }


# ---------------------------------------------------------------------------
# pin / verify / CLI
# ---------------------------------------------------------------------------

def _bundle_payloads(root: Path, pin_time_utc: str) -> dict[str, bytes]:
    """Deterministic bytes for all four artifacts given a pin time."""
    loaded = validate_bundle(root, require_bundle=False)
    final_report = canonical_json_bytes(build_final_report_payload(root))
    failure = canonical_json_bytes(build_failure_record(root))
    sup = canonical_json_bytes(build_superseding_pin(
        loaded,
        {FINAL_REPORT_REL: {"sha256": hashlib.sha256(final_report).hexdigest()},
         FAILURE_RECORD_REL: {"sha256": hashlib.sha256(failure).hexdigest()}},
        pin_time_utc))
    status = canonical_json_bytes(build_status(
        hashlib.sha256(sup).hexdigest()))
    return {FINAL_REPORT_REL: final_report, FAILURE_RECORD_REL: failure,
            SUPERSEDING_PIN_REL: sup, STATUS_REL: status}


def pin(root: Path = ROOT, now_utc: str | None = None) -> dict:
    """Append-only creation of the C4d bundle. Idempotent only for the exact
    final bundle: any conflicting existing artifact refuses; rerun preserves
    the recorded pin time and every byte."""
    sup_path = root / SUPERSEDING_PIN_REL
    if sup_path.exists():
        recorded = json.loads(sup_path.read_text(encoding="utf-8")) \
            .get("pin_event", {}).get("time_utc", "")
        expected = _bundle_payloads(root, recorded)
        for rel, data in expected.items():
            path = root / rel
            if path.exists() and path.read_bytes() != data:
                _refuse(f"conflicting existing {rel}: rerun is allowed only "
                        "when byte-identical")
        for rel, data in expected.items():  # heal a partial bundle only
            if not (root / rel).exists():
                _write_atomic(root / rel, data)
    else:
        stamp = now_utc or datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        expected = _bundle_payloads(root, stamp)
        for rel in (FINAL_REPORT_REL, FAILURE_RECORD_REL, STATUS_REL):
            path = root / rel
            if path.exists() and path.read_bytes() != expected[rel]:
                _refuse(f"conflicting existing {rel}: refusing to overwrite")
        for rel in (FINAL_REPORT_REL, FAILURE_RECORD_REL,
                    SUPERSEDING_PIN_REL, STATUS_REL):
            _write_atomic(root / rel, expected[rel])
    validate_bundle(root)
    return {
        "pin_event_id": SUPERSEDING_EVENT_ID,
        "supersedes": FAILED_PIN_EVENT_ID,
        "artifact_sha256": {rel: sha256_path(root / rel)
                            for rel in (FINAL_REPORT_REL, FAILURE_RECORD_REL,
                                        SUPERSEDING_PIN_REL, STATUS_REL)},
        "network_calls": 0,
    }


def verify(root: Path = ROOT, full: bool = True) -> dict:
    """Resolve the status selector, then verify the active superseding pin
    and every bound byte. `full` additionally re-derives the final report
    from current bytes and requires byte equality. Zero network."""
    loaded = validate_bundle(root)
    if full:
        recorded = loaded["superseding"]["pin_event"]["time_utc"]
        expected = _bundle_payloads(root, recorded)
        for rel, data in expected.items():
            if (root / rel).read_bytes() != data:
                _refuse(f"{rel} does not recompute from current bytes")
    return {
        "verified": True,
        "active_pin_event_id": SUPERSEDING_EVENT_ID,
        "pin_event_time_utc":
            loaded["superseding"]["pin_event"]["time_utc"],
        "supersedes_invalid_event": FAILED_PIN_EVENT_ID,
        "lineage_entries_reverified": len(loaded["lineage"]),
        "full_rederivation": full,
        "network_calls": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness.efc_pin_c4d",
        description="C4d append-only superseding pin bundle (offline)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--pin", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    if not (args.pin or args.verify):
        parser.print_usage(sys.stderr)
        print("refused: an explicit mode (--pin or --verify) is required",
              file=sys.stderr)
        return 2
    try:
        result = pin() if args.pin else verify()
    except PinRefusal as e:
        print(json.dumps({"refused": str(e)}, indent=1))
        return 1
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
