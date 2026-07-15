"""C4b mechanical approval capture and atomic manifest pin — finalization only.

This module authors NO content. It binds already-reviewed bytes into an
append-only pin bundle: dan's operator approval (transcript entry of
2026-07-15T01:53:51Z) is captured as `operator_approval_record.json`, and
`calibration_manifest_pin.json` pins the exact reviewed candidate manifest,
roster/decoding sibling, budget ledger, pre-approval conformance report, and
C4a review — plus every transitive lineage hash, reverified from bytes at pin
time. Nothing reviewed is regenerated, rewritten, or renamed; the candidate
files' internal `candidate_not_pinned` markers record their creation state
and the external pin event promotes those exact bytes (Sol, C4a ruling).

Fail-closed refusals (assignment list, in order): any expected input hash
mismatch; manifest closed-schema failure; approval roster/budget/file-SHA/
canonical-hash mismatch against the manifest; C4a aggregate or any per-check
verdict != endorse; conformance-report hash != the stabilized value or any
transitive lineage hash failing to recompute; the decoding name treated as
authority without the sibling payload bytes recomputing to their R2 hashes;
a pre-existing conflicting pin (rerun allowed only when byte-identical).

Atomicity: the manifest and the roster/decoding sibling are ONE pin unit —
neither is authoritative alone; the pin binds both or nothing. Writes go
through a same-directory temp file + atomic rename, and only after every
validation passes.

Zero network, engines, probes, listings, or held-out contact. This pin does
NOT authorize ignorance probes or calibration contact (Sol's explicit
reservation).

Run:   python3 -m harness.efc_pin_c4b --pin
       python3 -m harness.efc_pin_c4b --verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from harness import efc_contracts as c
from harness.efc_manifest import check_calibration_manifest, manifest_hash

ROOT = Path(__file__).resolve().parents[1]
C4_DIR = "corpus/efc_calibration/authoring_c4"

APPROVAL_RECORD_REL = f"{C4_DIR}/operator_approval_record.json"
PIN_REL = f"{C4_DIR}/calibration_manifest_pin.json"

# --- reviewed identities this finalizer binds (Sol C4b assignment; every one
# is reverified against actual bytes before anything is written) -------------
MANIFEST_REL = f"{C4_DIR}/C4_candidate_calibration_manifest.json"
MANIFEST_FILE_SHA = ("d5965001e19d846826aba8be0b130bf4a16fd82f63fbc21c8927b1"
                     "53237b971e")
MANIFEST_CANONICAL_HASH = ("2600d1fdba7bbf7fca5f4c0c75b57130afe2c04560d351aa5"
                           "fa7d743fc28a94d")
SIBLING_REL = f"{C4_DIR}/roster_decoding_pin_candidate.json"
SIBLING_SHA = ("4b3e452bd140ae88a971d0e7e9b1e68b95cc2ec8978abf3c194bdbe1ccb752"
               "1b")
LEDGER_REL = f"{C4_DIR}/budget_derivation_ledger.json"
LEDGER_SHA = ("b14466c1542ec034b6ab5c018d379b49b0f8b32ce107d899249f6c4c470a2e"
              "b6")
REPORT_REL = f"{C4_DIR}/c4_conformance_report.json"
REPORT_SHA_STABILIZED = ("5b6ca196f668a4d9ae6fa44697b581a42463deefa238240ef7d"
                         "587f6a60d955e")
REVIEW_REL = f"{C4_DIR}/final_manifest_review_composer.json"
REVIEW_SHA = ("0a490085dec8732cade54150f7b321cd579830191b5d071c157ce03ea22595"
              "da")
DECODING_LOCAL_SHA = ("b36dfdc49ff83e0d52610580e8a9b00a62ed85d7b5d30e7c498c21"
                      "0a03f3bcd0")
DECODING_API_SHA = ("7fdb78bc5c78db47fe9ad16b0ee567c9e27ae3b76040a965342552f2"
                    "7fd42da0")

APPROVED_ROSTER = ["openai/gpt-oss-20b", "gpt-5.4-2026-03-05"]
APPROVED_BUDGET = 1187522
APPROVAL_TIMESTAMP_UTC = "2026-07-15T01:53:51Z"
APPROVAL_ENTRY_VERBATIM = ("models (openai/gpt-oss-20b, gpt-5.4-2026-03-05) "
                           "and the 1,187,522-token budget are approved.")

# transitive lineage paths, keyed exactly as the conformance report's
# lineage_sha256 (duplicated from the C4 builder rather than imported so the
# reviewed builder bytes stay untouched; key-set equality is enforced below)
LINEAGE_PATHS = {
    "roster_enumeration_r1":
        "corpus/efc_calibration/roster/roster_enumeration_r1.json",
    "decoding_surface_r2":
        "corpus/efc_calibration/roster/decoding_surface_r2.json",
    "k4_promotion_identity_ledger":
        "corpus/efc_calibration/_acquisition/k4/promotion_identity_ledger.json",
    "g4_refetch_report":
        "corpus/efc_calibration/_acquisition/g4/refetch_report.json",
    "g4_identity_audit":
        "corpus/efc_calibration/_acquisition/g4/identity_audit.json",
    "packet_index": "episodes/efc_calibration/packet_index.json",
    "c2_check_report":
        "corpus/efc_calibration/authoring_c2/c2_check_report.json",
    "cold_semantic_review_kimi":
        "corpus/efc_calibration/authoring_c2/cold_semantic_review_kimi.json",
    "production_comparison_review_grok":
        "corpus/efc_calibration/authoring_c2/production_comparison_review_grok.json",
    "production_comparison_integration":
        "corpus/efc_calibration/authoring_c2/production_comparison_integration.json",
    "comparison_expectations_v1":
        "corpus/efc_calibration/authoring_c2/comparison_expectations_v1.json",
    "population_intent_declaration":
        "corpus/efc_calibration/authoring_c2/population_intent_declaration.json",
    "allocation": "corpus/efc_calibration/authoring_c2/allocation.json",
    "placebo_truth_verification":
        "corpus/efc_calibration/authoring_c2/placebo_truth_verification.json",
    "production_rule_v1":
        "corpus/efc_calibration/comparison/production_rule_v1.json",
    "structured_inputs_v1":
        "corpus/efc_calibration/comparison/structured_inputs_v1.json",
    "conformance_vectors_v1":
        "corpus/efc_calibration/comparison/conformance_vectors_v1.json",
    "exclusion_manifest":
        "episodes/efc_calibration/exclusion/exclusion_manifest.json",
}


class PinRefusal(ValueError):
    """A fail-closed refusal. Nothing is written after one of these."""


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json_bytes(payload) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=1).encode("utf-8")


def _load(root: Path, rel: str):
    return json.loads((root / rel).read_text(encoding="utf-8"))


def _refuse(msg: str) -> None:
    raise PinRefusal(msg)


# ---------------------------------------------------------------------------
# validation (all of it, before any write)
# ---------------------------------------------------------------------------

def validate_inputs(root: Path) -> dict:
    """Every assignment refusal, in order. Returns the loaded artifacts."""
    # 1. exact input hashes
    expected = ((MANIFEST_REL, MANIFEST_FILE_SHA), (SIBLING_REL, SIBLING_SHA),
                (LEDGER_REL, LEDGER_SHA), (REPORT_REL, REPORT_SHA_STABILIZED),
                (REVIEW_REL, REVIEW_SHA))
    for rel, want in expected:
        path = root / rel
        if not path.is_file():
            _refuse(f"missing required input {rel}")
        got = sha256_path(path)
        if got != want:
            _refuse(f"{rel}: sha256 {got} != reviewed {want}")

    manifest = _load(root, MANIFEST_REL)
    sibling = _load(root, SIBLING_REL)
    ledger = _load(root, LEDGER_REL)
    report = _load(root, REPORT_REL)
    review = _load(root, REVIEW_REL)

    # 2. closed-schema machine check
    result = check_calibration_manifest(manifest)
    if not result.ok:
        _refuse(f"manifest failed the closed-schema check: {result.failures}")
    if result.manifest_hash != MANIFEST_CANONICAL_HASH:
        _refuse(f"canonical manifest hash {result.manifest_hash} != reviewed "
                f"{MANIFEST_CANONICAL_HASH}")

    # 3. approval must match the manifest exactly
    if manifest["engine_roster"] != APPROVED_ROSTER:
        _refuse(f"manifest roster {manifest['engine_roster']} != approved "
                f"{APPROVED_ROSTER}")
    if manifest["total_budget_tokens"] != APPROVED_BUDGET:
        _refuse(f"manifest budget {manifest['total_budget_tokens']} != "
                f"approved {APPROVED_BUDGET}")
    if ledger["totals"]["roster_total_budget_tokens"] != APPROVED_BUDGET:
        _refuse("budget ledger roster total does not recompute to the "
                "approved budget")

    # 4./5. C4a review: aggregate and every per-check verdict
    if review.get("aggregate") != "endorse":
        _refuse(f"C4a aggregate is {review.get('aggregate')!r}, not endorse")
    bad = [chk.get("id") for chk in review.get("checks", [])
           if chk.get("verdict") != "endorse"]
    if bad or not review.get("checks"):
        _refuse(f"C4a per-check verdicts not all endorse: {bad or 'no checks'}")

    # 5. stabilized report + every transitive lineage hash recomputes
    lineage = report.get("lineage_sha256", {})
    if set(lineage) != set(LINEAGE_PATHS):
        _refuse("conformance-report lineage keys differ from the pinned "
                f"lineage path map: {sorted(set(lineage) ^ set(LINEAGE_PATHS))}")
    for name, want in lineage.items():
        got = sha256_path(root / LINEAGE_PATHS[name])
        if got != want:
            _refuse(f"lineage {name}: {LINEAGE_PATHS[name]} recomputes to "
                    f"{got} != {want}")

    # 6. the decoding name is never authority without the sibling bytes
    for branch, want in (("local", DECODING_LOCAL_SHA),
                         ("api", DECODING_API_SHA)):
        entry = sibling["branches"][branch]
        payload = entry.get("decoding_contract")
        if not payload:
            _refuse(f"sibling carries no {branch} decoding payload bytes; "
                    "the decoding name alone is not authoritative")
        got = c.sha256_utf8(json.dumps(payload, sort_keys=True,
                                       separators=(",", ":")))
        if got != want or entry["decoding_contract_canonical_sha256"] != want:
            _refuse(f"{branch} decoding payload does not recompute to the R2 "
                    f"canonical hash {want}")
    expected_id = (f"efc-decoding-r2-local-{DECODING_LOCAL_SHA[:8]}"
                   f"-api-{DECODING_API_SHA[:8]}")
    if manifest["decoding_contract_id"] != expected_id \
            or sibling["decoding_contract_id"] != expected_id:
        _refuse("manifest/sibling decoding_contract_id does not name the R2 "
                "payload hashes")
    if manifest["part_i_spec_hash"] != c.PART_I_SPEC_SHA256:
        _refuse("manifest part_i_spec_hash is not the sealed Part I")

    return {"manifest": manifest, "sibling": sibling, "ledger": ledger,
            "report": report, "review": review, "lineage": lineage}


# ---------------------------------------------------------------------------
# deterministic bundle payloads
# ---------------------------------------------------------------------------

def build_approval_record() -> dict:
    return {
        "schema_version": "efc_operator_approval_record_v1",
        "status": "recorded_append_only",
        "approver": "dan",
        "transcript_reference": {
            "space": "construct",
            "thread": "epistemic-frame-check-v0-content",
            "entry_author": "dan",
            "entry_timestamp_utc": APPROVAL_TIMESTAMP_UTC,
            "entry_text_verbatim": APPROVAL_ENTRY_VERBATIM,
            "position": ("the entry immediately following the claude/fable-5 "
                         "C4 handoff of 2026-07-15T01:44:21Z and immediately "
                         "preceding the codex/gpt-5.6-sol approval-recorded "
                         "ruling of 2026-07-15T01:56:09Z"),
        },
        "approved_engine_roster": list(APPROVED_ROSTER),
        "approved_total_budget_tokens": APPROVED_BUDGET,
        "candidate_manifest_path": MANIFEST_REL,
        "candidate_manifest_file_sha256": MANIFEST_FILE_SHA,
        "candidate_manifest_canonical_hash": MANIFEST_CANONICAL_HASH,
        "approval_scope": ("limited to exactly this roster, this "
                           "total_budget_tokens, and this manifest identity; "
                           "captures the transcript approval append-only "
                           "without rewriting any pre-approval artifact; "
                           "authorizes the C4b pin bundle only — NOT "
                           "ignorance probes or calibration contact"),
    }


def build_pin_payload(loaded: dict, approval_record_sha256: str,
                      pin_time_utc: str) -> dict:
    return {
        "schema_version": "efc_calibration_manifest_pin_v1",
        "status": "pinned",
        "pin_event": {
            "id": f"efc-cal-manifest-pin-{MANIFEST_CANONICAL_HASH[:12]}",
            "time_utc": pin_time_utc,
            "predecessor": "part_i_sealed",
            "part_i_spec_sha256": c.PART_I_SPEC_SHA256,
            "authorized_by": ("codex/gpt-5.6-sol C4b assignment "
                              "(2026-07-15T09:56:15Z) on dan's operator "
                              "approval (2026-07-15T01:53:51Z)"),
        },
        "manifest": {
            "path": MANIFEST_REL,
            "file_sha256": MANIFEST_FILE_SHA,
            "canonical_manifest_hash": MANIFEST_CANONICAL_HASH,
        },
        "roster_decoding_sibling": {
            "path": SIBLING_REL,
            "file_sha256": SIBLING_SHA,
            "decoding_payload_canonical_sha256": {
                "local": DECODING_LOCAL_SHA,
                "api": DECODING_API_SHA,
            },
        },
        "budget_ledger": {
            "path": LEDGER_REL,
            "file_sha256": LEDGER_SHA,
            "total_budget_tokens": APPROVED_BUDGET,
        },
        "pre_approval_conformance_report": {
            "path": REPORT_REL,
            "file_sha256": REPORT_SHA_STABILIZED,
            "note": ("stabilized bytes; the earlier handoff hash c46d6e3a… "
                     "remains historical testimony only (Sol C4a ruling)"),
        },
        "c4a_review": {
            "path": REVIEW_REL,
            "file_sha256": REVIEW_SHA,
            "aggregate": "endorse",
        },
        "operator_approval_record": {
            "path": APPROVAL_RECORD_REL,
            "file_sha256": approval_record_sha256,
        },
        "lineage_sha256": dict(sorted(loaded["lineage"].items())),
        "lineage_paths": dict(sorted(LINEAGE_PATHS.items())),
        "atomicity": ("the calibration manifest and the roster/decoding "
                      "sibling are ONE pin unit: neither is authoritative "
                      "alone, and the decoding_contract_id is a name that "
                      "binds only through the sibling payload bytes pinned "
                      "here"),
        "disclosure": {
            "engines_contacted": 0, "listing_calls": 0, "probes_run": 0,
            "network_calls": 0, "held_out_fixtures_authored": 0,
            "reviewed_bytes_modified": 0,
            "authorizes_probes_or_calibration_contact": False,
        },
    }


# ---------------------------------------------------------------------------
# atomic write, idempotent rerun, verify
# ---------------------------------------------------------------------------

def _write_atomic(path: Path, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def pin(root: Path = ROOT, now_utc: str | None = None) -> dict:
    """Validate everything, then write the approval record and pin bundle
    atomically. Rerun on an existing pin is a no-op iff byte-identical
    (modulo the recorded pin time, which is reused); a conflicting pin
    refuses."""
    loaded = validate_inputs(root)

    approval_bytes = canonical_json_bytes(build_approval_record())
    approval_path = root / APPROVAL_RECORD_REL
    if approval_path.exists() and approval_path.read_bytes() != approval_bytes:
        _refuse("existing operator_approval_record.json conflicts with the "
                "expected append-only record")
    approval_sha = hashlib.sha256(approval_bytes).hexdigest()

    pin_path = root / PIN_REL
    if pin_path.exists():
        existing = json.loads(pin_path.read_text(encoding="utf-8"))
        recorded_time = existing.get("pin_event", {}).get("time_utc", "")
        expected = canonical_json_bytes(
            build_pin_payload(loaded, approval_sha, recorded_time))
        if pin_path.read_bytes() != expected:
            _refuse("a conflicting calibration_manifest_pin.json already "
                    "exists; rerun is allowed only when byte-identical")
        payload = existing  # idempotent no-op
    else:
        stamp = now_utc or datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        payload = build_pin_payload(loaded, approval_sha, stamp)
        if not approval_path.exists():
            _write_atomic(approval_path, approval_bytes)
        _write_atomic(pin_path, canonical_json_bytes(payload))

    if not approval_path.exists():
        _write_atomic(approval_path, approval_bytes)
    return {
        "pin_event_id": payload["pin_event"]["id"],
        "pin_event_time_utc": payload["pin_event"]["time_utc"],
        "operator_approval_record_sha256": sha256_path(approval_path),
        "calibration_manifest_pin_sha256": sha256_path(pin_path),
        "network_calls": 0,
    }


def verify(root: Path = ROOT) -> dict:
    """Re-validate the whole bundle from disk. Zero network."""
    loaded = validate_inputs(root)
    approval_path = root / APPROVAL_RECORD_REL
    pin_path = root / PIN_REL
    if not approval_path.is_file() or not pin_path.is_file():
        _refuse("pin bundle not present; nothing to verify")
    if approval_path.read_bytes() != canonical_json_bytes(
            build_approval_record()):
        _refuse("operator_approval_record.json does not match the expected "
                "append-only record bytes")
    existing = json.loads(pin_path.read_text(encoding="utf-8"))
    recorded_time = existing.get("pin_event", {}).get("time_utc", "")
    expected = canonical_json_bytes(build_pin_payload(
        loaded, sha256_path(approval_path), recorded_time))
    if pin_path.read_bytes() != expected:
        _refuse("calibration_manifest_pin.json does not recompute from the "
                "pinned inputs")
    return {
        "verified": True,
        "pin_event_id": existing["pin_event"]["id"],
        "pin_event_time_utc": recorded_time,
        "operator_approval_record_sha256": sha256_path(approval_path),
        "calibration_manifest_pin_sha256": sha256_path(pin_path),
        "lineage_entries_reverified": len(loaded["lineage"]),
        "network_calls": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness.efc_pin_c4b", add_help=True,
        description="C4b approval capture and atomic manifest pin (offline)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--pin", action="store_true",
                      help="validate and write the pin bundle (idempotent)")
    mode.add_argument("--verify", action="store_true",
                      help="re-validate the existing bundle from disk")
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
