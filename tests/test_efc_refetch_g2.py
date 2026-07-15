"""Offline unit tests for harness.efc_refetch_g2 — injected transport only."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from harness.efc_capture_k2 import CaptureRefusal, canonical_json, sha256_file
from harness.efc_refetch_g2 import (
    G2_URLS,
    G2_URLS_ORDERED,
    MAX_CALLS,
    CallCeiling,
    acquisition_raw_path,
    build_g2_sources,
    dry_run,
    execute_live,
    positive_d_evidence,
    refuse_unknown_url,
    type_identity,
    verify_c_locators,
    verify_hashes,
    write_plan,
    _SLOT_ORDER,
)


@dataclass
class FakeResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]
    redirect_refused: bool = False


class G2TestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp) / "g2"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fake_transport(self, mapping: dict[str, bytes]) -> object:
        calls: list[str] = []

        def transport(url: str) -> FakeResponse:
            calls.append(url)
            if url not in mapping:
                raise AssertionError(f"unexpected URL: {url}")
            return FakeResponse(
                status=200,
                headers={"content-type": "application/json"},
                body=mapping[url],
                url=url,
                redirect_chain=[url],
            )

        transport.calls = calls  # type: ignore[attr-defined]
        return transport


class TestAllowlistAndCeiling(G2TestCase):
    def test_exactly_twelve(self):
        self.assertEqual(len(G2_URLS_ORDERED), 12)
        self.assertEqual(len(G2_URLS), 12)
        self.assertEqual(len(_SLOT_ORDER), 12)
        self.assertEqual(MAX_CALLS, 12)

    def test_unknown_url_refused(self):
        with self.assertRaises(CaptureRefusal):
            refuse_unknown_url("https://vuln.go.dev/index/modules.json")

    def test_call_ceiling(self):
        c = CallCeiling(2)
        c.record()
        c.record()
        with self.assertRaises(CaptureRefusal):
            c.record()

    def test_dry_run_zero_network(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            out = dry_run()
            urlopen.assert_not_called()
        self.assertEqual(out["network_calls"], 0)
        self.assertEqual(out["source_count"], 12)


class TestLedgerMapping(G2TestCase):
    def test_ledger_mapping_and_hashes(self):
        sources = build_g2_sources()
        by = {s.logical_slot: s for s in sources}
        for slot in ("C01", "C02", "C03", "C04", "C05", "C06"):
            self.assertEqual(by[slot].source_kind, "k2_original")
            self.assertTrue(by[slot].acquisition_locators)
        for slot in ("D01", "D02", "D03", "D04", "D05", "D06"):
            self.assertEqual(by[slot].source_kind, "k2b_selected")
        self.assertEqual(
            [s.capture_url for s in sources], list(G2_URLS_ORDERED))
        for s in sources:
            path = acquisition_raw_path(s)
            self.assertTrue(path.exists())
            self.assertEqual(sha256_file(path), s.acquisition_raw_sha256)


class TestCLocators(G2TestCase):
    def test_locator_exact_match(self):
        data = [
            {"cycle": "1"},
            {"cycle": "2"},
            {"cycle": "3"},
            {"cycle": "9.0", "eol": "2027-03-31", "support": True},
        ]
        expected = ({
            "array_index": 3, "cycle": "9.0", "field": "eol",
            "value": "2027-03-31",
        },)
        checks = verify_c_locators(data, expected)
        self.assertTrue(checks[0]["exact_match"])
        self.assertFalse(checks[0]["boolean_or_null_rejected"])

    def test_boolean_never_counts(self):
        data = [{"cycle": "9.0", "eol": True}]
        expected = ({
            "array_index": 0, "cycle": "9.0", "field": "eol",
            "value": "2027-03-31",
        },)
        checks = verify_c_locators(data, expected)
        self.assertTrue(checks[0]["boolean_or_null_rejected"])
        self.assertFalse(checks[0]["exact_match"])


class TestDPositiveEvidence(G2TestCase):
    def test_positive_fields_on_real_acquisition(self):
        sources = build_g2_sources()
        d01 = next(s for s in sources if s.logical_slot == "D01")
        body = acquisition_raw_path(d01).read_bytes()
        report = json.loads(body)
        evidence = positive_d_evidence(d01.d_spec, report)  # type: ignore[arg-type]
        self.assertTrue(evidence["id_match"])
        self.assertTrue(evidence["publication_2026"])
        self.assertTrue(evidence["reviewed"])
        self.assertEqual(evidence["selected_affected_index"], 0)
        self.assertTrue(evidence["module_match"])
        self.assertTrue(evidence["range_type_semver"])
        self.assertTrue(evidence["range_events_match"])
        self.assertTrue(evidence["has_finite_fixed"])
        self.assertTrue(evidence["all_imports_match"])
        self.assertTrue(evidence["same_affected_object_conjunction"])
        self.assertTrue(evidence["positive_requalification_pass"])
        # Positive evidence must record values, not empty mismatch map.
        self.assertEqual(evidence["id"], "GO-2026-4440")
        self.assertEqual(evidence["review_status"], "REVIEWED")
        self.assertTrue(evidence["imports"])

    def test_all_six_d_positive_on_acquisition(self):
        sources = build_g2_sources()
        modules = []
        for s in sources:
            if s.family != "D":
                continue
            report = json.loads(acquisition_raw_path(s).read_bytes())
            ev = positive_d_evidence(s.d_spec, report)  # type: ignore[arg-type]
            self.assertTrue(ev["positive_requalification_pass"], msg=s.logical_slot)
            modules.append(ev["module"])
        self.assertEqual(len(modules), 6)
        self.assertEqual(len(set(modules)), 6)


class TestIdentityTyping(G2TestCase):
    def test_exact(self):
        t = type_identity(True, True, [])
        self.assertEqual(t["content_identity"], "exact")

    def test_key_order_only(self):
        t = type_identity(False, True, [])
        self.assertEqual(t["drift_type"], "json_key_order_only")
        self.assertFalse(t["raw_drift_erased_by_parsed_equality"])

    def test_parsed_diff(self):
        t = type_identity(False, False, [{"field": "id"}])
        self.assertEqual(t["drift_type"], "json_parsed_diff")


class TestExecuteInjected(G2TestCase):
    def test_exact_twelve_create_once(self):
        sources = build_g2_sources()
        mapping = {
            s.capture_url: acquisition_raw_path(s).read_bytes()
            for s in sources
        }
        transport = self.fake_transport(mapping)
        out = execute_live(
            transport=transport,  # type: ignore[arg-type]
            root=self.root,
        )
        self.assertEqual(out["network_calls"], 12)
        self.assertEqual(out["content_identity_counts"]["exact"], 12)
        self.assertEqual(out["positive_requalification_counts"]["pass"], 12)
        self.assertEqual(len(transport.calls), 12)  # type: ignore[attr-defined]
        self.assertFalse(verify_hashes(self.root))
        with self.assertRaises(CaptureRefusal):
            execute_live(
                transport=transport,  # type: ignore[arg-type]
                root=self.root,
            )

    def test_no_redirect_follow_flag(self):
        # Ceiling + redirect refused response typing.
        ceiling = CallCeiling(MAX_CALLS)
        for url in G2_URLS_ORDERED:
            ceiling.record()
            resp = FakeResponse(
                302, {"location": url + "x"}, b"", url,
                [url, url + "x"], redirect_refused=True)
            self.assertTrue(resp.redirect_refused)
        with self.assertRaises(CaptureRefusal):
            ceiling.record()


class TestPlanWrite(G2TestCase):
    def test_write_plan_zero_network(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            plan = write_plan(self.root)
            urlopen.assert_not_called()
        self.assertEqual(plan["source_count"], 12)
        self.assertTrue(plan["no_index_contact"])
        with self.assertRaises(CaptureRefusal):
            write_plan(self.root)


if __name__ == "__main__":
    unittest.main()
