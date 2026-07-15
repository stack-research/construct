"""Offline tests for harness.efc_capture_k4."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from harness.efc_capture_k4 import (
    FROZEN_P,
    FROZEN_URLS,
    MAX_CALLS,
    P04_FROZEN_SYMBOLS,
    CaptureRefusal,
    br_rows_from_disk,
    build_global_ledger,
    dry_run,
    execute_live,
    p_rows_from_disk,
    qualify_p03,
    qualify_p04,
    qualify_slot,
    repair_ledger,
    verify_hashes,
    K4_ROOT,
)


def _ledger_rows():
    p_rows = p_rows_from_disk(K4_ROOT) if K4_ROOT.exists() else []
    br_rows = br_rows_from_disk(K4_ROOT) if K4_ROOT.exists() else []
    return build_global_ledger(K4_ROOT, p_rows, br_rows)


@dataclass
class FakeResp:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]
    redirect_refused: bool = False


def _p01_body() -> bytes:
    return json.dumps({
        "id": "RUSTSEC-2026-0122",
        "published": "2026-04-23T12:00:00Z",
        "aliases": ["GHSA-vfvv-c25p-m7mm"],
        "affected": [{
            "package": {"ecosystem": "crates.io", "name": "rkyv"},
            "ranges": [{"events": [
                {"introduced": "0.8.0"}, {"fixed": "0.8.16"},
            ]}],
        }],
    }).encode()


def _p04_body() -> bytes:
    return json.dumps({
        "id": "GO-2026-5676",
        "aliases": ["CVE-2026-40898"],
        "database_specific": {"review_status": "REVIEWED"},
        "affected": [{
            "package": {"name": "github.com/quic-go/quic-go", "ecosystem": "Go"},
            "ranges": [{"type": "SEMVER", "events": [
                {"introduced": "0"}, {"fixed": "0.59.1"},
            ]}],
            "ecosystem_specific": {
                "imports": [{
                    "path": "github.com/quic-go/quic-go/http3",
                    "symbols": list(P04_FROZEN_SYMBOLS),
                }],
            },
        }],
    }).encode()


class TestK4Plan(unittest.TestCase):
    def test_six_url_allowlist(self):
        self.assertEqual(len(FROZEN_P), 6)
        self.assertEqual(len(FROZEN_URLS), 6)

    def test_dry_run_zero(self):
        self.assertEqual(dry_run()["network_calls"], 0)

    def test_p03_cycle_value(self):
        data = [
            {"cycle": "11", "eol": "2025-01-01"},
            {"cycle": "12", "eol": "2026-04-30"},
        ]
        ok, reasons, extra = qualify_p03(data)
        self.assertTrue(ok)
        self.assertEqual(extra["cycle"], "12")

    def test_p04_symbols_exact(self):
        ok, reasons = qualify_p04(json.loads(_p04_body()))
        self.assertTrue(ok)
        self.assertEqual(reasons, [])

    def test_redirect_refused(self):
        spec = FROZEN_P[0]
        ok, reasons, _ = qualify_slot(
            spec, _p01_body(), http_status=200, redirect_refused=True)
        self.assertFalse(ok)
        self.assertIn("redirect_refused", reasons)


class TestK4LedgerRepair(unittest.TestCase):
    def setUp(self):
        if not K4_ROOT.exists():
            self.skipTest("k4 not executed")

    def test_excludes_failed_b_rows(self):
        ledger = _ledger_rows()
        slots = {r["logical_slot"] for r in ledger["rows"]}
        self.assertNotIn("B02", slots)
        self.assertNotIn("B03", slots)
        self.assertNotIn("B06", slots)
        excluded = {e["logical_slot"] for e in ledger["excluded_from_promotion"]}
        self.assertEqual(excluded, {"B02", "B03", "B06"})

    def test_d_urls_from_k2b_plan(self):
        ledger = _ledger_rows()
        d_rows = [r for r in ledger["rows"]
                  if r["family"] == "D" and not r["logical_slot"].startswith("P")]
        self.assertEqual(len(d_rows), 6)
        self.assertTrue(all(r["canonical_url"] for r in d_rows))
        self.assertTrue(all(r["canonical_url"].startswith("https://vuln.go.dev/") for r in d_rows))

    def test_e_entities_present(self):
        ledger = _ledger_rows()
        e_rows = [r for r in ledger["rows"]
                  if r["family"] == "E" and not r["logical_slot"].startswith("P")]
        self.assertEqual(len(e_rows), 6)
        self.assertTrue(all(r["entity_key"] for r in e_rows))

    def test_f_urls_and_entities(self):
        ledger = _ledger_rows()
        f_rows = [r for r in ledger["rows"] if r["family"] == "F"]
        self.assertEqual(len(f_rows), 4)
        self.assertTrue(all(r["canonical_url"] for r in f_rows))
        self.assertTrue(all(r["entity_key"] for r in f_rows))

    def test_promoted_count_and_shortfall(self):
        ledger = _ledger_rows()
        if (K4_ROOT / "captures" / "BR01").exists():
            self.assertEqual(ledger["row_count"], 40)
            self.assertEqual(ledger["replacement_shortfall"], 0)
            self.assertTrue(ledger["assertions"]["target_row_count"])
        else:
            self.assertEqual(ledger["row_count"], 37)
            self.assertEqual(ledger["replacement_shortfall"], 3)
            self.assertTrue(ledger["assertions"]["distinct_urls"])
            self.assertTrue(ledger["assertions"]["distinct_entities"])
            self.assertFalse(ledger["assertions"]["target_row_count"])


class TestK4Execute(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.k4 = Path(self.tmp) / "k4"
        self._patch = mock.patch("harness.efc_capture_k4.K4_ROOT", self.k4)
        self._patch.start()
        self._patch_k1 = mock.patch("harness.efc_capture_k4.K1_ROOT", Path(self.tmp) / "k1")
        self._patch_k2 = mock.patch("harness.efc_capture_k4.K2_ROOT", Path(self.tmp) / "k2")
        self._patch_k2b = mock.patch("harness.efc_capture_k4.K2B_ROOT", Path(self.tmp) / "k2b")
        self._patch_k3 = mock.patch("harness.efc_capture_k4.K3_ROOT", Path(self.tmp) / "k3")
        self._patch_k3c = mock.patch("harness.efc_capture_k4.K3C_ROOT", Path(self.tmp) / "k3c")
        self._patch_k3d = mock.patch("harness.efc_capture_k4.K3D_ROOT", Path(self.tmp) / "k3d")
        for p in (self._patch_k1, self._patch_k2, self._patch_k2b,
                  self._patch_k3, self._patch_k3c, self._patch_k3d):
            p.start()
        self._seed_prior()

    def tearDown(self):
        for p in (self._patch, self._patch_k1, self._patch_k2, self._patch_k2b,
                  self._patch_k3, self._patch_k3c, self._patch_k3d):
            p.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _seed_prior(self):
        # minimal stubs so build_global_ledger can run in synthetic test
        for root_name, caps in (
            ("k1", [f"capA-{i:02d}" for i in range(1, 7)]
                   + [f"capB-{i:02d}" for i in range(1, 7)]),
            ("k2", [f"capC-{i:02d}" for i in range(1, 7)]),
            ("k2b", [f"capD-{i:02d}" for i in range(1, 7)]),
        ):
            root = Path(self.tmp) / root_name
            for cid in caps:
                cdir = root / "captures" / cid
                cdir.mkdir(parents=True)
                (cdir / "raw.json").write_bytes(b"{}")
                (cdir / "sidecar.json").write_text(json.dumps({
                    "capture_verdict": "pass",
                    "capture_url": f"https://example.com/{cid}",
                    "record_id_returned": cid,
                    "package_returned": cid,
                    "product_slug": cid,
                    "go_id": "GO-2026-0000",
                    "module": "mod.example",
                }))
        k3d = Path(self.tmp) / "k3d"
        k3d.mkdir()
        k3_plan = {
            "entries": [
                {"id": f"capF-0{i}", "capture_url": f"https://example.com/f{i}",
                 "record_id": f"record-f{i}"}
                for i in range(1, 5)
            ],
        }
        (Path(self.tmp) / "k3").mkdir(parents=True, exist_ok=True)
        (Path(self.tmp) / "k2b").mkdir(parents=True, exist_ok=True)
        (Path(self.tmp) / "k3" / "plan.json").write_text(json.dumps(k3_plan))
        (Path(self.tmp) / "k2b" / "plan.json").write_text(json.dumps({
            "candidates": [{"go_id": "GO-2026-0000",
                            "capture_url": "https://vuln.go.dev/ID/GO-2026-0000.json"}],
        }))
        mappings = []
        for i in range(1, 7):
            mappings.append({
                "logical_slot": f"E{i:02d}",
                "source_capture_id": f"capE-{i:02d}",
                "source_kind": "k3_original",
                "qualification_verdict": "pass",
            })
        for i in range(1, 5):
            mappings.append({
                "logical_slot": f"F{i:02d}",
                "source_capture_id": f"capF-{i:02d}",
                "source_kind": "k3_original",
                "qualification_verdict": "pass",
            })
        (k3d / "promotion_ledger_v2.json").write_text(json.dumps({
            "logical_slot_mappings": mappings,
        }))
        for m in mappings:
            sid = m["source_capture_id"]
            base = Path(self.tmp) / "k3" / "captures" / sid
            base.mkdir(parents=True)
            ext = "json" if sid.startswith("capE") else "html"
            (base / f"raw.{ext}").write_bytes(b"{}")
            (base / "sidecar.json").write_text("{}")

    def test_create_once(self):
        execute_live(root=self.k4, transport=self._transport)
        with self.assertRaises(CaptureRefusal):
            execute_live(root=self.k4, transport=self._transport)

    def test_six_calls_ceiling(self):
        calls: list[str] = []
        def t(url: str) -> FakeResp:
            calls.append(url)
            return self._transport(url)
        execute_live(root=self.k4, transport=t)
        self.assertEqual(len(calls), MAX_CALLS)

    def _transport(self, url: str) -> FakeResp:
        if "RUSTSEC-2026-0122" in url:
            return FakeResp(200, {}, _p01_body(), url, [url])
        if "RUSTSEC-2026-0103" in url:
            body = json.dumps({
                "id": "RUSTSEC-2026-0103",
                "published": "2026-04-14T12:00:00Z",
                "affected": [{
                    "package": {"ecosystem": "crates.io", "name": "thin-vec"},
                    "ranges": [{"events": [
                        {"introduced": "0.0.0-0"}, {"fixed": "0.2.16"},
                    ]}],
                }],
            }).encode()
            return FakeResp(200, {}, body, url, [url])
        if "GHSA-jggg" in url:
            body = json.dumps({
                "ghsa_id": "GHSA-jggg-4jg4-v7c6",
                "published_at": "2026-05-19T16:21:33Z",
                "cve_id": "CVE-2026-45740",
                "vulnerabilities": [
                    {"package": {"name": "protobufjs", "ecosystem": "npm"},
                     "vulnerable_version_range": "<= 7.5.7",
                     "first_patched_version": "7.5.8"},
                    {"package": {"name": "protobufjs", "ecosystem": "npm"},
                     "vulnerable_version_range": ">= 8.0.0, < 8.2.0",
                     "first_patched_version": "8.2.0"},
                ],
            }).encode()
            return FakeResp(200, {}, body, url, [url])
        if "typo3" in url:
            body = json.dumps([
                {"cycle": "12", "eol": "2026-04-30"},
            ]).encode()
            return FakeResp(200, {}, body, url, [url])
        if "GO-2026-5676" in url:
            return FakeResp(200, {}, _p04_body(), url, [url])
        if "0BSD" in url:
            body = json.dumps({
                "licenseId": "0BSD",
                "licenseText": "zero clause",
            }).encode()
            return FakeResp(200, {}, body, url, [url])
        return FakeResp(404, {}, b"", url, [url])


class LiveK4(unittest.TestCase):
    def test_live_verify_if_present(self):
        if not K4_ROOT.exists():
            self.skipTest("k4 not executed")
        self.assertEqual(verify_hashes(), [])

    def test_repair_ledger_zero_network(self):
        if not K4_ROOT.exists():
            self.skipTest("k4 not executed")
        prod_ledger = (K4_ROOT / "promotion_identity_ledger.json").read_bytes()
        prod_report = (K4_ROOT / "capture_report.json").read_bytes()
        tmp = tempfile.mkdtemp()
        try:
            k4_copy = Path(tmp) / "k4"
            shutil.copytree(K4_ROOT, k4_copy)
            result = repair_ledger(k4_copy)
            self.assertEqual(result["network_calls"], 0)
            expected = 40 if (k4_copy / "captures" / "BR01").exists() else 37
            self.assertEqual(result["promotion_identity_ledger"]["row_count"],
                             expected)
            self.assertIn("ledger_repaired_at_utc",
                          json.loads((k4_copy / "capture_report.json")
                                     .read_text()))
            self.assertEqual(
                (K4_ROOT / "promotion_identity_ledger.json").read_bytes(),
                prod_ledger)
            self.assertEqual(
                (K4_ROOT / "capture_report.json").read_bytes(),
                prod_report)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
