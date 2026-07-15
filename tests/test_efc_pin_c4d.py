"""C4d superseding pin bundle — fail-closed verifier tests.

Real-tree tests cover the healthy path (pin, full verify with re-derivation,
idempotent rerun with preserved event time, protected-byte snapshot, CLI
modes). Sandbox copies of the exact repository bytes cover every refusal in
Sol's C4d verifier list: missing/tampered/ambiguous status, old-pin-only
use, failed-pin mutation, final-report mutation, superseding-pin tampering,
G4 disk and cross-artifact mismatch, approval/review/repair mutation,
lineage drift, decoding-sibling payload absence, and conflicting-bundle
refusal. Zero network throughout (socket-refusal guard).
"""

from __future__ import annotations

import json
import shutil
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness import efc_pin_c4b as c4b
from harness import efc_pin_c4d as c4d

ROOT = Path(__file__).resolve().parents[1]

PROTECTED = [c4b.MANIFEST_REL, c4b.SIBLING_REL, c4b.LEDGER_REL,
             c4b.REVIEW_REL, c4b.REPORT_REL, c4b.APPROVAL_RECORD_REL,
             c4d.C4C_ATTESTATION_REL, c4d.FAILED_PIN_REL, c4d.K4_LEDGER_REL,
             "corpus/efc_calibration/_acquisition/k4/capture_report.json"]

SANDBOX_FILES = (PROTECTED + list(c4d.G4_RECORD_RELS)
                 + sorted(set(c4b.LINEAGE_PATHS.values()))
                 + [c4d.FINAL_REPORT_REL, c4d.FAILURE_RECORD_REL,
                    c4d.SUPERSEDING_PIN_REL, c4d.STATUS_REL])


def make_sandbox() -> Path:
    box = Path(tempfile.mkdtemp(prefix="efc-c4d-"))
    for rel in sorted(set(SANDBOX_FILES)):
        dst = box / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dst)
    return box


class _RefusingSocket(socket.socket):
    def __init__(self, *a, **k):
        raise AssertionError("C4d finalizer attempted a network call")


class SocketRefusalMixin:
    @classmethod
    def setUpClass(cls):
        cls._real_socket = socket.socket
        socket.socket = _RefusingSocket

    @classmethod
    def tearDownClass(cls):
        socket.socket = cls._real_socket


class TestRealTreeBundle(SocketRefusalMixin, unittest.TestCase):
    def test_full_verify_with_rederivation(self):
        result = c4d.verify(ROOT, full=True)
        self.assertTrue(result["verified"])
        self.assertTrue(result["full_rederivation"])
        self.assertEqual(result["active_pin_event_id"],
                         c4d.SUPERSEDING_EVENT_ID)
        self.assertEqual(result["lineage_entries_reverified"],
                         len(c4b.LINEAGE_PATHS))
        self.assertEqual(result["network_calls"], 0)

    def test_pin_is_idempotent_and_preserves_time_and_bytes(self):
        before = {rel: c4d.sha256_path(ROOT / rel)
                  for rel in (c4d.FINAL_REPORT_REL, c4d.FAILURE_RECORD_REL,
                              c4d.SUPERSEDING_PIN_REL, c4d.STATUS_REL)}
        time_before = json.loads(
            (ROOT / c4d.SUPERSEDING_PIN_REL).read_text()) \
            ["pin_event"]["time_utc"]
        result = c4d.pin(ROOT, now_utc="2027-01-01T00:00:00Z")
        self.assertEqual(result["artifact_sha256"],
                         {rel: h for rel, h in before.items()})
        time_after = json.loads(
            (ROOT / c4d.SUPERSEDING_PIN_REL).read_text()) \
            ["pin_event"]["time_utc"]
        self.assertEqual(time_before, time_after)

    def test_pin_leaves_protected_bytes_unchanged(self):
        before = {rel: c4d.sha256_path(ROOT / rel) for rel in PROTECTED}
        c4d.pin(ROOT)
        after = {rel: c4d.sha256_path(ROOT / rel) for rel in PROTECTED}
        self.assertEqual(before, after)

    def test_failed_pin_bytes_preserved(self):
        self.assertEqual(c4d.sha256_path(ROOT / c4d.FAILED_PIN_REL),
                         c4d.FAILED_PIN_SHA)

    def test_status_is_sole_selector_with_one_active(self):
        status = json.loads((ROOT / c4d.STATUS_REL).read_text())
        active = [p for p in status["pins"] if p["role"] == "active"]
        invalid = [p for p in status["pins"] if p["role"] == "invalid"]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["event_id"], c4d.SUPERSEDING_EVENT_ID)
        self.assertEqual(invalid[0]["sha256"], c4d.FAILED_PIN_SHA)
        self.assertEqual(invalid[0]["disposition"],
                         "invalid_non_authoritative_preserved")

    def test_superseding_pin_binds_and_supersedes(self):
        sup = json.loads((ROOT / c4d.SUPERSEDING_PIN_REL).read_text())
        self.assertEqual(sup["pin_event"]["predecessor"], "part_i_sealed")
        self.assertEqual(sup["pin_event"]["supersedes"]["event_id"],
                         c4d.FAILED_PIN_EVENT_ID)
        binds = sup["binds"]
        self.assertEqual(binds[c4b.MANIFEST_REL]["sha256"],
                         c4b.MANIFEST_FILE_SHA)
        self.assertEqual(binds[c4b.SIBLING_REL]
                         ["decoding_payload_canonical_sha256"],
                         {"local": c4b.DECODING_LOCAL_SHA,
                          "api": c4b.DECODING_API_SHA})
        self.assertEqual(binds[c4b.LEDGER_REL]["total_budget_tokens"],
                         1187522)
        self.assertFalse(sup["disclosure"]
                         ["authorizes_probes_or_calibration_contact"])

    def test_final_report_resolutions_and_evidence(self):
        report = json.loads((ROOT / c4d.FINAL_REPORT_REL).read_text())
        self.assertEqual(report["blocking_items"], [])
        self.assertEqual(report["lineage_sha256"]
                         ["k4_promotion_identity_ledger"],
                         c4d.G4_AUDIT_LEDGER_SHA)
        self.assertEqual(report["c4c_repair_evidence"]["attestation_sha256"],
                         c4d.C4C_ATTESTATION_SHA)
        for key in ("operator_roster_budget_approval",
                    "extractor_identity_layer",
                    "decoding_contract_id_is_a_name",
                    "license_binding_conformance_review",
                    "g4_lineage_authority"):
            self.assertIn(key, report["resolutions"])

    def test_cli_modes(self):
        self.assertEqual(c4d.main([]), 2)
        self.assertEqual(c4d.main(["--verify"]), 0)

    def test_old_c4b_verifier_still_refuses_old_pin_alone(self):
        self.assertEqual(c4b.main(["--verify"]), 1)


class TestRefusals(SocketRefusalMixin, unittest.TestCase):
    def setUp(self):
        self.box = make_sandbox()
        self.addCleanup(shutil.rmtree, self.box, ignore_errors=True)

    def refuse(self, pattern: str):
        with self.assertRaisesRegex(c4d.PinRefusal, pattern):
            c4d.validate_bundle(self.box)

    def _mutate_json(self, rel: str, mutate) -> None:
        path = self.box / rel
        payload = json.loads(path.read_text())
        mutate(payload)
        path.write_text(json.dumps(payload, sort_keys=True, indent=1))

    # --- status selector ------------------------------------------------------

    def test_missing_status_with_old_pin_present_refused(self):
        (self.box / c4d.STATUS_REL).unlink()
        self.refuse("old pin alone must be rejected")

    def test_tampered_status_refused(self):
        self._mutate_json(c4d.STATUS_REL,
                          lambda p: p["pins"][0].update(sha256="0" * 64))
        self.refuse("does not match the superseding pin")

    def test_ambiguous_two_active_pins_refused(self):
        def dup(p):
            p["pins"].append(dict(p["pins"][0]))
        self._mutate_json(c4d.STATUS_REL, dup)
        self.refuse("ambiguous")

    def test_zero_active_pins_refused(self):
        self._mutate_json(c4d.STATUS_REL,
                          lambda p: p["pins"][0].update(role="invalid"))
        self.refuse("ambiguous|does not type")

    def test_status_missing_invalid_typing_refused(self):
        self._mutate_json(c4d.STATUS_REL,
                          lambda p: p["pins"][1].update(
                              disposition="something_else"))
        self.refuse("does not type the failed first pin invalid")

    # --- preserved artifacts ----------------------------------------------------

    def test_failed_pin_mutation_refused(self):
        self._mutate_json(c4d.FAILED_PIN_REL,
                          lambda p: p.update(status="resurrected"))
        self.refuse("mutation of a reviewed/preserved artifact")

    def test_final_report_mutation_refused(self):
        self._mutate_json(c4d.FINAL_REPORT_REL,
                          lambda p: p.update(blocking_items=["injected"]))
        self.refuse("does not bind the current bytes")

    def test_failure_record_mutation_refused(self):
        self._mutate_json(c4d.FAILURE_RECORD_REL,
                          lambda p: p.update(disposition="valid_actually"))
        self.refuse("does not bind the current bytes")

    def test_superseding_pin_tamper_refused(self):
        self._mutate_json(c4d.SUPERSEDING_PIN_REL,
                          lambda p: p["binds"][c4b.LEDGER_REL].update(
                              total_budget_tokens=1))
        self.refuse("does not match the superseding pin")

    def test_historical_report_mutation_refused(self):
        self._mutate_json(c4b.REPORT_REL,
                          lambda p: p.update(failures=["rewritten"]))
        self.refuse("mutation of a reviewed/preserved artifact")

    def test_approval_record_mutation_refused(self):
        self._mutate_json(c4b.APPROVAL_RECORD_REL,
                          lambda p: p.update(
                              approved_total_budget_tokens=999999))
        self.refuse("mutation of a reviewed/preserved artifact")

    def test_attestation_mutation_refused(self):
        self._mutate_json(c4d.C4C_ATTESTATION_REL,
                          lambda p: p.update(authorizes_repin=True))
        self.refuse("mutation of a reviewed/preserved artifact")

    def test_review_verdict_gates_when_hash_bypassed(self):
        self._mutate_json(c4b.REVIEW_REL,
                          lambda p: p.update(aggregate="block"))
        new_sha = c4d.sha256_path(self.box / c4b.REVIEW_REL)
        with patch.object(c4b, "REVIEW_SHA", new_sha):
            self.refuse("not an unqualified endorse")

    # --- G4 authority and lineage -----------------------------------------------

    def test_g4_disk_mismatch_refused(self):
        path = self.box / c4d.K4_LEDGER_REL
        path.write_bytes(path.read_bytes().replace(
            b"2026-07-14T21:46:25Z", b"2026-07-15T00:00:00Z"))
        self.refuse("!= G4-audited authority")

    def test_g4_cross_artifact_mismatch_refused(self):
        # a G4 record disagreeing with the audit authority refuses; the g4
        # file is also a lineage input, so either typed gate may fire first
        rel = c4d.G4_RECORD_RELS[0]
        self._mutate_json(rel, lambda p: p.update(
            promotion_identity_ledger_sha256="0" * 64))
        self.refuse("cross-artifact mismatch|lineage")

    def test_lineage_drift_refused(self):
        rel = c4b.LINEAGE_PATHS["production_rule_v1"]
        (self.box / rel).write_bytes((self.box / rel).read_bytes() + b"\n")
        self.refuse("lineage")

    # --- decoding sibling ---------------------------------------------------------

    def test_sibling_payload_absence_refused_when_hash_bypassed(self):
        def strip(p):
            del p["branches"]["api"]["decoding_contract"]
        self._mutate_json(c4b.SIBLING_REL, strip)
        new_sha = c4d.sha256_path(self.box / c4b.SIBLING_REL)
        with patch.object(c4b, "SIBLING_SHA", new_sha):
            self.refuse("no api decoding payload bytes")

    # --- conflicting bundle ---------------------------------------------------------

    def test_conflicting_superseding_pin_refuses_rerun(self):
        self._mutate_json(c4d.SUPERSEDING_PIN_REL,
                          lambda p: p["pin_event"].update(id="rogue-event"))
        # any edit to the pin bytes desynchronizes the status hash binding,
        # so the tamper is caught at the selector before anything else
        with self.assertRaisesRegex(c4d.PinRefusal,
                                    "does not match the superseding pin|"
                                    "conflicting"):
            c4d.validate_bundle(self.box)


if __name__ == "__main__":
    unittest.main()
