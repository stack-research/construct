"""Offline tests for harness.efc_capture_k3d."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from harness import efc_capture_k3 as k3
from harness.efc_capture_k3c import CaptureRefusal
from harness.efc_capture_k3d import (
    AUTHORITATIVE_CAPTURE_IMPL,
    ERRONEOUS_CAPTURE_IMPL_LABEL,
    K3C_RECON_IMPL,
    K3D_ROOT,
    build_identity_attestation,
    build_identity_plan,
    build_promotion_ledger_v2,
    execute,
    tree_digest,
    verify_all,
    verify_lineage,
)


class K3dTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.k3_root = Path(self.tmp) / "k3"
        self.k3c_root = Path(self.tmp) / "k3c"
        self.k3d_root = Path(self.tmp) / "k3d"
        self._patch_roots()

    def tearDown(self):
        for name in ("_k3", "_k3c", "_k3d", "_repo", "_k3c_mod_k3", "_k3c_mod_k3c"):
            p = getattr(self, name, None)
            if p:
                p.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _patch_roots(self):
        self._k3 = mock.patch("harness.efc_capture_k3d.K3_ROOT", self.k3_root)
        self._k3c = mock.patch("harness.efc_capture_k3d.K3C_ROOT", self.k3c_root)
        self._k3d = mock.patch("harness.efc_capture_k3d.K3D_ROOT", self.k3d_root)
        self._repo = mock.patch("harness.efc_capture_k3d.REPO", Path(self.tmp))
        self._k3c_mod_k3 = mock.patch(
            "harness.efc_capture_k3c.K3_ROOT", self.k3_root)
        self._k3c_mod_k3c = mock.patch(
            "harness.efc_capture_k3c.K3C_ROOT", self.k3c_root)
        for p in (self._k3, self._k3c, self._k3d, self._repo,
                  self._k3c_mod_k3, self._k3c_mod_k3c):
            p.start()

    def _seed_minimal_trees(self):
        """Minimal K3/K3c fixtures with the lineage mismatch pattern."""
        self.k3_root.mkdir(parents=True)
        self.k3c_root.mkdir(parents=True)
        plan = {
            "plan_sha256": "6456e6fe6c1badbbcdd27fa9a849398f62815869565dc30299f7d7215541e19e",
            "implementation_module_sha256": AUTHORITATIVE_CAPTURE_IMPL,
        }
        (self.k3_root / "plan.json").write_text(json.dumps(plan))

        for cid in ("capF-01", "capF-04"):
            cdir = self.k3_root / "captures" / cid
            cdir.mkdir(parents=True)
            (cdir / "raw.html").write_bytes(b"<html>raw</html>")
            sidecar = {
                "capture_verdict": "fail",
                "raw_sha256": "aa" * 32,
                "implementation_module_sha256": AUTHORITATIVE_CAPTURE_IMPL,
            }
            (cdir / "sidecar.json").write_text(json.dumps(sidecar))

        recon = self.k3c_root / "reconciliation"
        recon.mkdir(parents=True)
        recon_plan = {
            "k3_implementation_module_sha256": ERRONEOUS_CAPTURE_IMPL_LABEL,
            "reconciliation_module_sha256": K3C_RECON_IMPL,
        }
        (recon / "plan.json").write_text(json.dumps(recon_plan))
        for cid in ("capF-01", "capF-04"):
            rdir = recon / cid
            rdir.mkdir()
            (rdir / "extract.json").write_text("{}")
            (rdir / "normalized.txt").write_text("norm")
            (rdir / "section.txt").write_text("sec")
            rsc = {
                "k3_implementation_module_sha256": ERRONEOUS_CAPTURE_IMPL_LABEL,
                "reconciliation_module_sha256": K3C_RECON_IMPL,
                "reconciliation_verdict": "pass",
            }
            (rdir / "sidecar.json").write_text(json.dumps(rsc))

        ledger = {
            "k3_closed": True,
            "logical_slot_mappings": [
                {"logical_slot": s, "promotion_eligible": True,
                 "artifact_hashes": {"raw_sha256": "bb" * 32,
                                     "sidecar_sha256": "cc" * 32}}
                for s in (
                    "E01", "E02", "E03", "E04", "E05", "E06",
                    "F01", "F02", "F03", "F04",
                )
            ],
            "superseded_ineligible": [],
        }
        (self.k3c_root / "promotion_ledger.json").write_text(json.dumps(ledger))

    def test_plan_records_authoritative_hash(self):
        self._seed_minimal_trees()
        plan = build_identity_plan()
        self.assertEqual(
            plan["authoritative_capture_implementation_module_sha256"],
            AUTHORITATIVE_CAPTURE_IMPL,
        )
        self.assertEqual(plan["network_calls"], 0)

    def test_attestation_records_mismatch(self):
        self._seed_minimal_trees()
        plan = build_identity_plan()
        att = build_identity_attestation(plan)
        self.assertEqual(att["finding"],
                         "post_fix_k3_hash_mislabeled_as_capture_implementation_hash")
        self.assertEqual(
            att["erroneous_k3c_artifacts"]["reconciliation_plan"]["erroneous_value"],
            ERRONEOUS_CAPTURE_IMPL_LABEL,
        )
        self.assertTrue(att["no_byte_changes"])

    def test_verify_lineage_fails_on_false_capture_hash(self):
        self._seed_minimal_trees()
        plan = build_identity_plan()
        att = build_identity_attestation(plan)
        ledger = build_promotion_ledger_v2(att)
        # corrupt ledger to use erroneous hash as authoritative
        ledger["logical_slot_mappings"][6]["identity_lineage"][
            "authoritative_capture_implementation_module_sha256"] = (
            ERRONEOUS_CAPTURE_IMPL_LABEL)
        errs = verify_lineage(att, ledger)
        self.assertTrue(any("capture impl wrong" in e for e in errs))

    def test_verify_lineage_fails_when_recon_equals_capture(self):
        self._seed_minimal_trees()
        plan = build_identity_plan()
        att = build_identity_attestation(plan)
        ledger = build_promotion_ledger_v2(att)
        for m in ledger["logical_slot_mappings"]:
            if m["logical_slot"] == "F01":
                m["identity_lineage"][
                    "reconciliation_implementation_module_sha256"] = (
                    AUTHORITATIVE_CAPTURE_IMPL)
        errs = verify_lineage(att, ledger)
        self.assertTrue(any("confuses recon" in e for e in errs))

    def test_k3c_closure_without_attestation_fails(self):
        self._seed_minimal_trees()
        plan = build_identity_plan()
        att = build_identity_attestation(plan)
        ledger = build_promotion_ledger_v2(att)
        ledger.pop("identity_attestation_sha256")
        errs = verify_lineage(att, ledger)
        self.assertTrue(errs)

    def test_execute_create_once(self):
        self._seed_minimal_trees()
        with mock.patch(
            "harness.efc_capture_k3d.verify_trees_unchanged", return_value=[]
        ):
            execute()
            with self.assertRaises(CaptureRefusal):
                execute()

    def test_zero_network_execute(self):
        self._seed_minimal_trees()
        with mock.patch(
            "harness.efc_capture_k3d.verify_trees_unchanged", return_value=[]
        ), mock.patch("urllib.request.urlopen") as urlopen:
            result = execute()
            urlopen.assert_not_called()
        self.assertEqual(result["network_calls"], 0)


class LiveK3d(unittest.TestCase):
    def test_live_verify_if_present(self):
        if not K3D_ROOT.exists():
            self.skipTest("k3d not executed")
        errs = verify_all()
        self.assertEqual(errs, [])


if __name__ == "__main__":
    unittest.main()
