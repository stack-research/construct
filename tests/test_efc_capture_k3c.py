"""Offline tests for harness.efc_capture_k3c."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from harness import efc_capture_k3 as k3
from harness.efc_capture_k3c import (
    CORRECTED_CAPTURES,
    CORRECTED_URLS,
    CaptureRefusal,
    build_capture_plan,
    build_promotion_ledger,
    build_reconciliation_plan,
    execute_capture,
    execute_reconciliation,
    extract_f03c_rst,
    normalize_rst,
    verify_all,
    K3_ROOT,
    RECON_ROOT,
    K3C_ROOT,
    MAX_CAPTURE_CALLS,
)


@dataclass
class FakeResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]
    redirect_refused: bool = False


SAMPLE_RST = b"""Version 2.3.0
-------------

Released 2023-04-25

- Remove previously deprecated code.

  - The ``FLASK_ENV`` environment variable, ``ENV`` config key, and ``app.env``
    property are removed.

Version 2.2.4
-------------

Released 2023-04-25
"""


class K3cTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.k3_root = Path(self.tmp) / "k3"
        self.k3c_root = Path(self.tmp) / "k3c"
        self._patch_roots()

    def tearDown(self):
        for name in ("_k3_patcher", "_k3c_patcher", "_k3c_root_patcher",
                     "_recon_patcher", "_cap_patcher"):
            p = getattr(self, name, None)
            if p:
                p.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _patch_roots(self):
        self._k3_patcher = mock.patch.object(k3, "K3_ROOT", self.k3_root)
        self._k3c_patcher = mock.patch("harness.efc_capture_k3c.K3_ROOT", self.k3_root)
        self._k3c_root_patcher = mock.patch("harness.efc_capture_k3c.K3C_ROOT", self.k3c_root)
        self._recon_patcher = mock.patch("harness.efc_capture_k3c.RECON_ROOT",
                                         self.k3c_root / "reconciliation")
        self._cap_patcher = mock.patch("harness.efc_capture_k3c.CAPTURE_ROOT",
                                       self.k3c_root / "captures")
        for p in (self._k3_patcher, self._k3c_patcher, self._k3c_root_patcher,
                  self._recon_patcher, self._cap_patcher):
            p.start()

    def _seed_k3_partial(self):
        """K3 tree with real F01/F04 HTML fixtures for reconciliation."""
        plan = {"plan_sha256": "abc", "schema_version": "x"}
        self.k3_root.mkdir(parents=True)
        (self.k3_root / "plan.json").write_text(json.dumps(plan))
        (self.k3_root / "capture_report.json").write_text("{}")

        def write_cap(spec, body: bytes, verdict: str, failures: list):
            cdir = self.k3_root / "captures" / spec.capture_id
            cdir.mkdir(parents=True)
            raw_name = spec.raw_name
            (cdir / raw_name).write_bytes(body)
            sc = {
                "capture_verdict": verdict,
                "failure_reasons": failures,
                "retrieved_at_utc": "2026-07-14T17:14:04Z",
                "raw_sha256": __import__("hashlib").sha256(body).hexdigest(),
                "plan_sha256": "abc",
            }
            (cdir / "sidecar.json").write_text(json.dumps(sc) + "\n")

        write_cap(k3.FAMILY_F[0], K8S_HTML, "fail", ["extractor_defect"])
        write_cap(k3.FAMILY_F[3], RAILS_HTML, "fail", ["extractor_defect"])
        write_cap(k3.FAMILY_F[1], DJANGO_HTML, "pass", [])
        write_cap(k3.FAMILY_F[2], b"<html/>", "fail", ["redirect_refused"])
        for spec in k3.FAMILY_E[:3]:
            body = json.dumps({
                "licenseExceptionId": spec.record_id,
                "licenseExceptionText": "exception text",
            }).encode()
            write_cap(spec, body, "pass", [])
        for spec in k3.FAMILY_E[3:]:
            body = b"404: Not Found"
            write_cap(spec, body, "fail", ["http_failure"])


# HTML fixtures (mirror tests.test_efc_capture_k3.TestFamilyFExtractors)
K8S_HTML = b"""<html><body>
    <h2>Removed APIs by release</h2>
    <h3>v1.32</h3>
    <p>The flowcontrol.apiserver.k8s.io/v1beta3 API version of FlowSchema and
    PriorityLevelConfiguration is no longer served as of v1.32.</p>
    </body></html>"""
DJANGO_HTML = b"""<html><body>
    <h2>Features removed in 5.0</h2>
    <ul><li>Support for pytz timezones is removed.</li></ul>
    </body></html>"""
RAILS_HTML = b"""<html><body>
    <h1>Ruby on Rails 7.2 Release Notes</h1>
    <h2>Railties</h2>
    <h3>Removals</h3>
    <ul><li>Remove deprecated Rails.config.enable_dependency_loading.</li></ul>
    </body></html>"""


class TestRstExtraction(unittest.TestCase):
    def test_flask_statement_and_date(self):
        ext, fails = extract_f03c_rst(SAMPLE_RST)
        self.assertEqual(fails, [])
        self.assertEqual(ext["framework_version"], "2.3.0")
        self.assertIn("FLASK_ENV", ext["matched_statement"] or "")

    def test_markup_normalization(self):
        norm = normalize_rst(SAMPLE_RST.decode())
        self.assertNotIn("``", norm)
        self.assertIn("FLASK_ENV", norm)


class TestReconciliation(K3cTestCase):
    def test_zero_network_reconcile(self):
        self._seed_k3_partial()
        with mock.patch("urllib.request.urlopen") as urlopen:
            out = execute_reconciliation()
            urlopen.assert_not_called()
        self.assertEqual(out["network_calls"], 0)
        sc = json.loads((self.k3c_root / "reconciliation/capF-01/sidecar.json").read_text())
        self.assertTrue(sc["derived_from_saved_raw"])
        self.assertEqual(sc["capture_time_verdict"], "fail")
        self.assertEqual(sc["reconciliation_verdict"], "pass")

    def test_immutable_k3_tree(self):
        self._seed_k3_partial()
        before = (self.k3_root / "captures/capF-01/raw.html").read_bytes()
        execute_reconciliation()
        after = (self.k3_root / "captures/capF-01/raw.html").read_bytes()
        self.assertEqual(before, after)

    def test_reconcile_create_once(self):
        self._seed_k3_partial()
        execute_reconciliation()
        with self.assertRaises(CaptureRefusal):
            execute_reconciliation()


class TestCorrectedCapture(K3cTestCase):
    def test_four_url_allowlist(self):
        self.assertEqual(len(CORRECTED_CAPTURES), 4)
        self.assertEqual(len(CORRECTED_URLS), 4)
        plan = build_capture_plan()
        self.assertEqual(plan["max_network_calls"], MAX_CAPTURE_CALLS)

    def test_capture_dry_run_zero_network(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            from harness.efc_capture_k3c import main
            main(["--capture-dry-run"])
            urlopen.assert_not_called()

    def test_synthetic_capture(self):
        self._seed_k3_partial()
        execute_reconciliation()
        mapping = {}
        for spec in CORRECTED_CAPTURES:
            if spec.family == "E":
                mapping[spec.capture_url] = json.dumps({
                    "licenseId": spec.record_id,
                    "licenseText": "License body",
                }).encode()
            else:
                mapping[spec.capture_url] = SAMPLE_RST

        def transport(url: str) -> FakeResponse:
            return FakeResponse(200, {"content-type": "application/json"},
                                mapping[url], url, [url])

        out = execute_capture(transport=transport)
        self.assertEqual(out["network_calls"], 4)
        sc = json.loads((self.k3c_root / "captures/capF-03c/sidecar.json").read_text())
        self.assertEqual(sc["capture_verdict"], "pass")


class TestPromotionLedger(K3cTestCase):
    def test_mapping_and_superseded(self):
        self._seed_k3_partial()
        execute_reconciliation()

        def transport(url: str) -> FakeResponse:
            spec = next(s for s in CORRECTED_CAPTURES if s.capture_url == url)
            if spec.family == "E":
                body = json.dumps({"licenseId": spec.record_id,
                                   "licenseText": "x"}).encode()
            else:
                body = SAMPLE_RST
            return FakeResponse(200, {}, body, url, [url])

        execute_capture(transport=transport)
        ledger = build_promotion_ledger()
        slots = {m["logical_slot"] for m in ledger["logical_slot_mappings"]}
        self.assertEqual(len(slots), 10)
        ineligible = {s["capture_id"] for s in ledger["superseded_ineligible"]}
        self.assertIn("capE-04", ineligible)
        self.assertFalse(any(
            s["promotion_eligible"] for s in ledger["superseded_ineligible"]))


@unittest.skipUnless(K3_ROOT.exists(), "live K3 tree required")
class TestLiveK3c(unittest.TestCase):
    def test_live_verify_if_present(self):
        if not (K3C_ROOT / "promotion_ledger.json").exists():
            return
        self.assertEqual(verify_all(), [])


if __name__ == "__main__":
    unittest.main()
