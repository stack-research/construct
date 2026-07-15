"""Offline tests for harness.efc_capture_k2."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from harness.efc_capture_k2 import (
    CANDIDATE_CEILING,
    FAMILY_C,
    CaptureRefusal,
    build_plan,
    derive_candidate_plan,
    dry_run,
    execute_live,
    qualify_go_candidate,
    validate_family_c,
    verify_hashes,
    K2_ROOT,
)


@dataclass
class FakeResp:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]


TOMCAT_JSON = json.dumps([
    {"cycle": "8.5", "eol": "2024-03-31"},
    {"cycle": "9.0", "eol": "2027-03-31", "support": False},
]).encode()

MODULES_JSON = json.dumps([
    {"path": "example.com/a", "vulns": [
        {"id": "GO-2026-0001", "fixed": "1.0.1"},
    ]},
    {"path": "example.com/b", "vulns": [
        {"id": "GO-2026-0002", "fixed": "2.0.0"},
    ]},
    {"path": "stdlib", "vulns": [
        {"id": "GO-2026-0003", "fixed": "1.0.0"},
    ]},
    {"path": "lru", "vulns": [
        {"id": "GO-2026-0004", "fixed": "1.0.0"},
    ]},
    {"path": "example.com/c", "vulns": [
        {"id": "GO-2026-0005", "fixed": "1.0.0"},
    ]},
]).encode()

VULNS_JSON = json.dumps([
    {"id": "GO-2026-0001"},
    {"id": "GO-2026-0002"},
    {"id": "GO-2026-0003"},
    {"id": "GO-2026-0004"},
    {"id": "GO-2026-0005"},
]).encode()


def _go_report(goid: str, module: str, *, intro_only: bool = False,
                 symbols: bool = True, reviewed: str = "REVIEWED") -> bytes:
    events = [{"introduced": "0"}]
    if not intro_only:
        events.append({"fixed": "1.0.0"})
    imports = [{"path": f"{module}/pkg", "symbols": ["Fn"]}] if symbols else []
    body = {
        "id": goid,
        "published": "2026-01-15T00:00:00Z",
        "database_specific": {"review_status": reviewed},
        "affected": [{
            "package": {"name": module, "ecosystem": "Go"},
            "ranges": [{"type": "SEMVER", "events": events}],
            "ecosystem_specific": {"imports": imports},
        }],
    }
    return json.dumps(body).encode()


class TestK2Plan(unittest.TestCase):
    def test_dry_run_zero_network(self):
        out = dry_run()
        self.assertEqual(out["network_calls"], 0)
        self.assertEqual(len(out["plan"]["phase_c"]), 6)

    def test_c_boolean_date_refused(self):
        data = json.dumps([{"cycle": "1.0", "eol": True}]).encode()
        v, matches, fails = validate_family_c(
            data, FAMILY_C[0], FAMILY_C[0].capture_url)
        self.assertEqual(v, "fail")
        self.assertEqual(matches, [])

    def test_c_iso_match(self):
        v, matches, _ = validate_family_c(
            TOMCAT_JSON, FAMILY_C[0], FAMILY_C[0].capture_url)
        self.assertEqual(v, "pass")
        self.assertTrue(any(m["value"] == "2027-03-31" for m in matches))

    def test_candidate_derivation(self):
        plan = derive_candidate_plan(
            MODULES_JSON, VULNS_JSON,
            {"modules": "aa", "vulns": "bb"},
        )
        ids = [c["id"] for c in plan["candidates"]]
        self.assertEqual(ids, ["GO-2026-0001", "GO-2026-0002", "GO-2026-0005"])
        self.assertNotIn("GO-2026-0003", ids)
        self.assertNotIn("GO-2026-0004", ids)

    def test_go_qualify_introduced_only_fails(self):
        ok, reasons, _ = qualify_go_candidate(
            json.loads(_go_report("GO-2026-0001", "example.com/a",
                                  intro_only=True)),
            "GO-2026-0001", ["example.com/a"], set())
        self.assertFalse(ok)
        self.assertIn("no_finite_range", reasons)

    def test_go_qualify_pass(self):
        ok, reasons, summary = qualify_go_candidate(
            json.loads(_go_report("GO-2026-0001", "example.com/a")),
            "GO-2026-0001", ["example.com/a"], set())
        self.assertTrue(ok)
        self.assertEqual(reasons, [])
        self.assertEqual(summary["module"], "example.com/a")

    def test_module_collision_rejects(self):
        ok, reasons, _ = qualify_go_candidate(
            json.loads(_go_report("GO-2026-0002", "example.com/b")),
            "GO-2026-0002", ["example.com/b"], {"example.com/b"})
        self.assertFalse(ok)
        self.assertIn("module_collision", reasons)


class TestK2Execute(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp) / "k2"
        self._patcher = mock.patch("harness.efc_capture_k2.K2_ROOT", self.root)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_create_once_refusal(self):
        self.root.mkdir(parents=True)
        (self.root / "plan.json").write_text("{}")
        with self.assertRaises(CaptureRefusal):
            execute_live(root=self.root, transport=self._transport)

    def test_synthetic_execute_stops_at_six(self):
        result = execute_live(root=self.root, transport=self._transport_many)
        self.assertLessEqual(result["network_calls"], 6 + 3 + CANDIDATE_CEILING)
        self.assertTrue((self.root / "candidate_plan.json").exists())
        with self.assertRaises(CaptureRefusal):
            execute_live(root=self.root, transport=self._transport)

    def _transport(self, url: str) -> FakeResp:
        if "tomcat" in url:
            return FakeResp(200, {}, TOMCAT_JSON, url, [url])
        if url.endswith("modules.json"):
            return FakeResp(200, {}, MODULES_JSON, url, [url])
        if url.endswith("vulns.json"):
            return FakeResp(200, {}, VULNS_JSON, url, [url])
        if url.endswith("db.json"):
            return FakeResp(200, {}, b"{}", url, [url])
        return FakeResp(404, {}, b"", url, [url])

    def _transport_many(self, url: str) -> FakeResp:
        base = self._transport(url)
        if "/ID/" in url:
            goid = url.rsplit("/", 1)[-1].replace(".json", "")
            mod = {
                "GO-2026-0001": "example.com/a",
                "GO-2026-0002": "example.com/b",
                "GO-2026-0005": "example.com/c",
            }.get(goid, "example.com/z")
            return FakeResp(200, {}, _go_report(goid, mod), url, [url])
        return base


class LiveK2(unittest.TestCase):
    def test_live_verify_if_present(self):
        if not K2_ROOT.exists():
            self.skipTest("k2 not executed")
        self.assertEqual(verify_hashes(), [])


if __name__ == "__main__":
    unittest.main()
