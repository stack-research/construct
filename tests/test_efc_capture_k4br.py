"""Offline tests for harness.efc_capture_k4br."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from harness.efc_capture_k4br import (
    FROZEN_BR,
    FROZEN_URLS,
    KIMI_DISCOVERY_ONLY_URLS,
    MAX_CALLS,
    CaptureRefusal,
    build_plan,
    dry_run,
    execute_live,
    qualify_br,
    qualify_br_slot,
    verify_hashes,
    K4_ROOT,
)


@dataclass
class FakeResp:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]
    redirect_refused: bool = False


def _br01_body() -> bytes:
    return json.dumps({
        "ghsa_id": "GHSA-hmw2-7cc7-3qxx",
        "type": "reviewed",
        "published_at": "2026-06-15T17:26:26Z",
        "cve_id": "CVE-2026-12143",
        "vulnerabilities": [
            {"package": {"ecosystem": "npm", "name": "form-data"},
             "vulnerable_version_range": "< 2.5.6",
             "first_patched_version": "2.5.6"},
            {"package": {"ecosystem": "npm", "name": "form-data"},
             "vulnerable_version_range": ">= 3.0.0, < 3.0.5",
             "first_patched_version": "3.0.5"},
            {"package": {"ecosystem": "npm", "name": "form-data"},
             "vulnerable_version_range": ">= 4.0.0, < 4.0.6",
             "first_patched_version": "4.0.6"},
        ],
    }).encode()


def _br02_body() -> bytes:
    return json.dumps({
        "ghsa_id": "GHSA-hm92-r4w5-c3mj",
        "type": "reviewed",
        "published_at": "2026-06-19T14:20:20Z",
        "cve_id": "CVE-2026-6734",
        "vulnerabilities": [
            {"package": {"ecosystem": "npm", "name": "undici"},
             "vulnerable_version_range": ">= 7.23.0, < 7.28.0",
             "first_patched_version": "7.28.0"},
            {"package": {"ecosystem": "npm", "name": "undici"},
             "vulnerable_version_range": ">= 8.0.0, < 8.2.0",
             "first_patched_version": "8.2.0"},
        ],
    }).encode()


def _br03_body() -> bytes:
    return json.dumps({
        "ghsa_id": "GHSA-xgmm-8j9v-c9wx",
        "type": "reviewed",
        "published_at": "2026-06-15T19:28:06Z",
        "cve_id": "CVE-2026-48526",
        "vulnerabilities": [
            {"package": {"ecosystem": "pip", "name": "pyjwt"},
             "vulnerable_version_range": "< 2.13.0",
             "first_patched_version": "2.13.0"},
        ],
    }).encode()


class TestK4BRPlan(unittest.TestCase):
    def test_three_url_allowlist(self):
        self.assertEqual(len(FROZEN_BR), 3)
        self.assertEqual(len(FROZEN_URLS), 3)
        self.assertTrue(KIMI_DISCOVERY_ONLY_URLS.isdisjoint(FROZEN_URLS))

    def test_dry_run_zero(self):
        if not K4_ROOT.exists():
            self.skipTest("k4 root missing")
        self.assertEqual(dry_run()["network_calls"], 0)

    def test_br01_exact_branches(self):
        ok, reasons = qualify_br(FROZEN_BR[0], json.loads(_br01_body()))
        self.assertTrue(ok)
        self.assertEqual(reasons, [])

    def test_branch_count_rejection(self):
        data = json.loads(_br01_body())
        data["vulnerabilities"] = data["vulnerabilities"][:2]
        ok, reasons = qualify_br(FROZEN_BR[0], data)
        self.assertFalse(ok)
        self.assertIn("branch_count_mismatch", reasons)

    def test_redirect_refused(self):
        ok, reasons = qualify_br_slot(
            FROZEN_BR[0], _br01_body(), http_status=200, redirect_refused=True)
        self.assertFalse(ok)
        self.assertIn("redirect_refused", reasons)


class TestK4BRExecute(unittest.TestCase):
    def setUp(self):
        if not K4_ROOT.exists():
            self.skipTest("k4 root missing")
        self.tmp = tempfile.mkdtemp()
        self.k4 = Path(self.tmp) / "k4"
        shutil.copytree(K4_ROOT, self.k4)
        for spec in FROZEN_BR:
            br_dir = self.k4 / "captures" / spec.slot
            if br_dir.exists():
                shutil.rmtree(br_dir)
        if (self.k4 / "br_plan.json").exists():
            (self.k4 / "br_plan.json").unlink()
        self._patch = mock.patch("harness.efc_capture_k4br.K4_ROOT", self.k4)
        self._patch.start()
        self._patch_k4 = mock.patch("harness.efc_capture_k4.K4_ROOT", self.k4)
        self._patch_k4.start()

    def tearDown(self):
        self._patch.stop()
        self._patch_k4.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_create_once(self):
        execute_live(root=self.k4, transport=self._transport)
        with self.assertRaises(CaptureRefusal):
            execute_live(root=self.k4, transport=self._transport)

    def test_three_calls_ceiling(self):
        calls: list[str] = []
        def t(url: str) -> FakeResp:
            calls.append(url)
            return self._transport(url)
        execute_live(root=self.k4, transport=t)
        self.assertEqual(len(calls), MAX_CALLS)

    def test_forty_row_ledger(self):
        result = execute_live(root=self.k4, transport=self._transport)
        ledger = result["promotion_identity_ledger"]
        self.assertEqual(ledger["row_count"], 40)
        self.assertTrue(ledger["assertions"]["target_row_count"])
        self.assertTrue(ledger["assertions"]["family_B"])
        excluded = {e["logical_slot"] for e in ledger["excluded_from_promotion"]}
        self.assertEqual(excluded, {"B02", "B03", "B06"})

    def _transport(self, url: str) -> FakeResp:
        if "GHSA-hmw2" in url:
            return FakeResp(200, {}, _br01_body(), url, [url])
        if "GHSA-hm92" in url:
            return FakeResp(200, {}, _br02_body(), url, [url])
        if "GHSA-xgmm" in url:
            return FakeResp(200, {}, _br03_body(), url, [url])
        return FakeResp(404, {}, b"", url, [url])


class LiveK4BR(unittest.TestCase):
    def test_live_verify_if_present(self):
        if not (K4_ROOT / "captures" / "BR01").exists():
            self.skipTest("BR not executed")
        self.assertEqual(verify_hashes(), [])

    def test_live_forty_rows_if_present(self):
        if not (K4_ROOT / "captures" / "BR01").exists():
            self.skipTest("BR not executed")
        ledger = json.loads(
            (K4_ROOT / "promotion_identity_ledger.json").read_text())
        self.assertEqual(ledger["row_count"], 40)
        self.assertTrue(ledger["assertions"]["all_qualifying"])


if __name__ == "__main__":
    unittest.main()
