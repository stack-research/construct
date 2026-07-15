"""C4c production-tree immutability regression — zero network.

Snapshots the G4-audited K4 ledger and reviewed C4/C4a inputs, runs the
historical production-tree mutators in their temp-root sandboxes, and proves
the production corpus bytes are unchanged.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from harness import efc_author_c4 as c4
from harness.efc_capture_k4 import K4_ROOT, repair_ledger

ROOT = Path(__file__).resolve().parents[1]
C4_ROOT = ROOT / "corpus/efc_calibration/authoring_c4"

G4_LEDGER_SHA = (
    "b086689591d03a2f9ee6aa7bfffd16683f58d5b4d4674f6f19795089224d45ac"
)

PROTECTED_REL_PATHS = (
    "corpus/efc_calibration/_acquisition/k4/promotion_identity_ledger.json",
    "corpus/efc_calibration/_acquisition/k4/capture_report.json",
    "corpus/efc_calibration/authoring_c4/C4_candidate_calibration_manifest.json",
    "corpus/efc_calibration/authoring_c4/roster_decoding_pin_candidate.json",
    "corpus/efc_calibration/authoring_c4/budget_derivation_ledger.json",
    "corpus/efc_calibration/authoring_c4/operator_approval_record.json",
    "corpus/efc_calibration/authoring_c4/c4_conformance_report.json",
    "corpus/efc_calibration/authoring_c4/final_manifest_review_composer.json",
    "corpus/efc_calibration/authoring_c4/calibration_manifest_pin.json",
)


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot() -> dict[str, str]:
    return {rel: _sha256_path(ROOT / rel) for rel in PROTECTED_REL_PATHS}


class TestProductionTreeImmutability(unittest.TestCase):
    def test_g4_ledger_authority_on_disk(self):
        ledger = ROOT / PROTECTED_REL_PATHS[0]
        self.assertTrue(ledger.exists(), "k4 promotion ledger missing")
        self.assertEqual(_sha256_path(ledger), G4_LEDGER_SHA)

    def test_mutators_leave_production_bytes_unchanged(self):
        before = _snapshot()
        self.assertEqual(before[PROTECTED_REL_PATHS[0]], G4_LEDGER_SHA)

        if not K4_ROOT.exists():
            self.skipTest("k4 not executed")

        prod_ledger = (K4_ROOT / "promotion_identity_ledger.json").read_bytes()
        prod_report = (K4_ROOT / "capture_report.json").read_bytes()
        tmp_k4 = tempfile.mkdtemp()
        try:
            k4_copy = Path(tmp_k4) / "k4"
            shutil.copytree(K4_ROOT, k4_copy)
            repair_ledger(k4_copy)
            self.assertEqual(
                (K4_ROOT / "promotion_identity_ledger.json").read_bytes(),
                prod_ledger)
            self.assertEqual(
                (K4_ROOT / "capture_report.json").read_bytes(),
                prod_report)
        finally:
            shutil.rmtree(tmp_k4, ignore_errors=True)

        tmp_c4 = tempfile.mkdtemp()
        try:
            c4_copy = Path(tmp_c4) / "authoring_c4"
            shutil.copytree(C4_ROOT, c4_copy)
            real_socket = socket.socket

            def _refuse(*a, **k):
                raise AssertionError("C4 builder attempted a network call")

            socket.socket = _refuse
            try:
                with mock.patch.object(c4, "C4_ROOT", c4_copy):
                    self.assertEqual(c4.main(), 0)
                    after_first = {p.name: c4.sha256_path(p)
                                   for p in c4_copy.glob("*.json")}
                    self.assertEqual(c4.main(), 0)
                    after_second = {p.name: c4.sha256_path(p)
                                    for p in c4_copy.glob("*.json")}
            finally:
                socket.socket = real_socket
            self.assertEqual(after_first, after_second)
        finally:
            shutil.rmtree(tmp_c4, ignore_errors=True)

        after = _snapshot()
        self.assertEqual(before, after)

    def test_focused_mutator_tests_leave_production_unchanged(self):
        before = _snapshot()
        modules = (
            "tests.test_efc_capture_k4.LiveK4.test_repair_ledger_zero_network",
            "tests.test_efc_author_c4.TestC4Derivation.test_builder_is_idempotent",
        )
        for target in modules:
            proc = subprocess.run(
                [sys.executable, "-m", "unittest", target, "-v"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                proc.returncode, 0,
                f"{target} failed:\n{proc.stdout}\n{proc.stderr}")
        after = _snapshot()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
