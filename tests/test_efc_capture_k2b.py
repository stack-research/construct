"""Offline tests for harness.efc_capture_k2b."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from harness.efc_capture_k2b import (
    FROZEN_CANDIDATES,
    FROZEN_URLS,
    MAX_CALLS,
    TARGET_D,
    CaptureRefusal,
    build_plan,
    dry_run,
    execute_live,
    qualify_candidate,
    verify_all,
    K2B_ROOT,
    FROZEN_CANDIDATES as CANDS,
)


@dataclass
class FakeResp:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]
    redirect_refused: bool = False


def _report_for(spec) -> dict:
    imports = [
        {"path": path, "symbols": list(syms)}
        for path, syms in spec.imports
    ]
    return {
        "id": spec.go_id,
        "published": "2026-01-01T00:00:00Z",
        "database_specific": {"review_status": "REVIEWED"},
        "affected": [{
            "package": {"ecosystem": "Go", "name": spec.module},
            "ranges": [{
                "type": "SEMVER",
                "events": [dict(e) for e in spec.range_events],
            }],
            "ecosystem_specific": {"imports": imports},
        }],
    }


class TestK2bPlan(unittest.TestCase):
    def test_eight_url_allowlist(self):
        plan = build_plan()
        self.assertEqual(len(plan["candidates"]), 8)
        urls = {c["capture_url"] for c in plan["candidates"]}
        self.assertEqual(urls, FROZEN_URLS)

    def test_dry_run_zero_network(self):
        self.assertEqual(dry_run()["network_calls"], 0)

    def test_exact_qualify_pass(self):
        spec = CANDS[0]
        ok, reasons, _ = qualify_candidate(
            spec, _report_for(spec), http_status=200,
            redirect_refused=False, selected_modules=set())
        self.assertTrue(ok)
        self.assertEqual(reasons, [])

    def test_review_fail(self):
        spec = CANDS[0]
        rep = _report_for(spec)
        rep["database_specific"]["review_status"] = "UNREVIEWED"
        ok, reasons, _ = qualify_candidate(
            spec, rep, http_status=200, redirect_refused=False,
            selected_modules=set())
        self.assertFalse(ok)
        self.assertIn("not_reviewed", reasons)

    def test_events_mismatch(self):
        spec = CANDS[0]
        rep = _report_for(spec)
        rep["affected"][0]["ranges"][0]["events"] = [{"introduced": "0"}]
        ok, reasons, _ = qualify_candidate(
            spec, rep, http_status=200, redirect_refused=False,
            selected_modules=set())
        self.assertFalse(ok)
        self.assertIn("range_events_mismatch", reasons)


class TestK2bExecute(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.k2b = Path(self.tmp) / "k2b"
        self.k2 = Path(self.tmp) / "k2"
        self._seed_k2()
        self._p_k2b = mock.patch("harness.efc_capture_k2b.K2B_ROOT", self.k2b)
        self._p_k2 = mock.patch("harness.efc_capture_k2b.K2_ROOT", self.k2)
        self._p_k2b.start()
        self._p_k2.start()

    def tearDown(self):
        self._p_k2b.stop()
        self._p_k2.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _seed_k2(self):
        self.k2.mkdir(parents=True)
        for i, cid in enumerate(
            ("capC-01", "capC-02", "capC-03", "capC-04", "capC-05", "capC-06"),
            start=1,
        ):
            cdir = self.k2 / "captures" / cid
            cdir.mkdir(parents=True)
            (cdir / "raw.json").write_bytes(b"{}")
            (cdir / "sidecar.json").write_text(json.dumps({
                "capture_verdict": "pass",
                "raw_sha256": "aa",
            }))
        sel = {
            "d_candidate_attempts": [
                {"candidate_id": "GO-2026-4273", "qualification_verdict": "fail"},
            ],
        }
        (self.k2 / "selection_ledger.json").write_text(json.dumps(sel))
        qual = self.k2 / "qualification" / "go_candidates" / "GO-2026-4273"
        qual.mkdir(parents=True)
        (qual / "raw.json").write_bytes(b"x")
        (qual / "sidecar.json").write_text("{}")

    def test_stop_at_six_passes(self):
        calls: list[str] = []

        def transport(url: str) -> FakeResp:
            calls.append(url)
            spec = next(s for s in CANDS if s.capture_url == url)
            return FakeResp(200, {}, json.dumps(_report_for(spec)).encode(),
                            url, [url])

        execute_live(root=self.k2b, transport=transport)
        self.assertEqual(len(calls), 6)

    def test_one_fail_contacts_seventh(self):
        calls: list[str] = []

        def transport(url: str) -> FakeResp:
            calls.append(url)
            spec = next(s for s in CANDS if s.capture_url == url)
            if spec.go_id == "GO-2026-4440":
                bad = _report_for(spec)
                bad["database_specific"]["review_status"] = "UNREVIEWED"
                body = json.dumps(bad).encode()
            else:
                body = json.dumps(_report_for(spec)).encode()
            return FakeResp(200, {}, body, url, [url])

        execute_live(root=self.k2b, transport=transport)
        self.assertEqual(len(calls), 7)

    def test_create_once(self):
        execute_live(root=self.k2b, transport=self._ok_transport)
        with self.assertRaises(CaptureRefusal):
            execute_live(root=self.k2b, transport=self._ok_transport)

    def _ok_transport(self, url: str) -> FakeResp:
        spec = next(s for s in CANDS if s.capture_url == url)
        return FakeResp(200, {}, json.dumps(_report_for(spec)).encode(),
                        url, [url])


class LiveK2b(unittest.TestCase):
    def test_live_verify_if_present(self):
        if not K2B_ROOT.exists():
            self.skipTest("k2b not executed")
        self.assertEqual(verify_all(), [])


if __name__ == "__main__":
    unittest.main()
