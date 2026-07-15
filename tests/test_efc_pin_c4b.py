"""C4b failed-pin module — permanent fail-closed supersession coverage.

The C4b finalizer wrote the first pin against a conformance report whose K4
lineage had been restamped by a test-suite mutator (repaired in C4c). Its
constants deliberately bind those now-superseded identities, so the module
must refuse FOREVER — on verify, on pin, everywhere — while the failed pin
bytes stay preserved and the C4d status selector types the attempt invalid.
These tests convert the former healthy-path expectations into that
supersession contract (Sol C4d: failure-path coverage, not skips).
Zero network throughout.
"""

from __future__ import annotations

import json
import shutil
import socket
import tempfile
import unittest
from pathlib import Path

from harness import efc_pin_c4b as c4b
from harness import efc_pin_c4d as c4d

ROOT = Path(__file__).resolve().parents[1]


class _RefusingSocket(socket.socket):
    def __init__(self, *a, **k):
        raise AssertionError("C4b module attempted a network call")


class TestFailedPinSupersession(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._real_socket = socket.socket
        socket.socket = _RefusingSocket

    @classmethod
    def tearDownClass(cls):
        socket.socket = cls._real_socket

    # --- the failed attempt is preserved, typed, and never authoritative -----

    def test_failed_pin_bytes_preserved_exactly(self):
        self.assertEqual(c4b.sha256_path(ROOT / c4b.PIN_REL),
                         c4d.FAILED_PIN_SHA)

    def test_c4b_verify_refuses_forever_on_current_tree(self):
        """The stale conformance-report constant makes the old verifier
        fail closed permanently — the supersession invariant."""
        with self.assertRaises(c4b.PinRefusal) as ctx:
            c4b.verify(ROOT)
        self.assertIn(c4b.REPORT_SHA_STABILIZED, str(ctx.exception))

    def test_c4b_pin_refuses_and_writes_nothing(self):
        before = {p.name: c4b.sha256_path(p)
                  for p in (ROOT / c4b.C4_DIR).glob("*.json")}
        with self.assertRaises(c4b.PinRefusal):
            c4b.pin(ROOT)
        after = {p.name: c4b.sha256_path(p)
                 for p in (ROOT / c4b.C4_DIR).glob("*.json")}
        self.assertEqual(before, after)

    def test_c4b_cli_verify_exits_1(self):
        self.assertEqual(c4b.main(["--verify"]), 1)

    def test_c4b_cli_no_arg_refuses(self):
        self.assertEqual(c4b.main([]), 2)

    def test_status_selector_types_this_attempt_invalid(self):
        status = json.loads((ROOT / c4d.STATUS_REL).read_text())
        row = next(p for p in status["pins"]
                   if p["path"] == c4b.PIN_REL)
        self.assertEqual(row["role"], "invalid")
        self.assertEqual(row["sha256"], c4d.FAILED_PIN_SHA)
        self.assertEqual(row["disposition"],
                         "invalid_non_authoritative_preserved")

    def test_failure_record_binds_this_attempt(self):
        record = json.loads((ROOT / c4d.FAILURE_RECORD_REL).read_text())
        self.assertEqual(record["failed_pin"]["sha256"], c4d.FAILED_PIN_SHA)
        self.assertEqual(record["failed_pin"]["event_id"],
                         c4d.FAILED_PIN_EVENT_ID)
        self.assertEqual(record["disposition"],
                         "invalid_non_authoritative_preserved")
        self.assertIn("no engine, listing, probe, or calibration contact",
                      record["contact_disclosure"])

    # --- approval record remains the append-only C4b deliverable --------------

    def test_approval_record_still_matches_builder(self):
        self.assertEqual(
            (ROOT / c4b.APPROVAL_RECORD_REL).read_bytes(),
            c4b.canonical_json_bytes(c4b.build_approval_record()))

    # --- refusal mechanics still work in isolation (sandboxed) -----------------

    def test_refusal_reports_first_mismatching_input(self):
        box = Path(tempfile.mkdtemp(prefix="efc-c4b-hist-"))
        self.addCleanup(shutil.rmtree, box, ignore_errors=True)
        for rel in (c4b.MANIFEST_REL, c4b.SIBLING_REL, c4b.LEDGER_REL,
                    c4b.REPORT_REL, c4b.REVIEW_REL):
            dst = box / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dst)
        (box / c4b.MANIFEST_REL).write_bytes(
            (box / c4b.MANIFEST_REL).read_bytes() + b"\n")
        with self.assertRaisesRegex(c4b.PinRefusal, "sha256 .* != reviewed"):
            c4b.validate_inputs(box)


if __name__ == "__main__":
    unittest.main()
