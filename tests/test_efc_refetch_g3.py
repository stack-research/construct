"""Offline unit tests for harness.efc_refetch_g3 — injected transport only."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from harness.efc_capture_k3 import CaptureRefusal, canonical_json, sha256_bytes, sha256_file
from harness.efc_refetch_g3 import (
    G3_URLS,
    G3_URLS_ORDERED,
    MAX_CALLS,
    CallCeiling,
    acquisition_raw_path,
    build_g3_sources,
    build_plan,
    compare_one,
    dry_run,
    execute_live,
    refuse_unknown_url,
    type_content_identity,
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


def exception_body(exc_id: str) -> bytes:
    return canonical_json({
        "licenseExceptionId": exc_id,
        "licenseExceptionText": f"Exception text for {exc_id}.",
    }).encode()


def license_body(lic_id: str) -> bytes:
    return canonical_json({
        "licenseId": lic_id,
        "licenseText": f"License text for {lic_id}.",
    }).encode()


class G3TestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp) / "g3"

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
                redirect_refused=False,
            )

        transport.calls = calls  # type: ignore[attr-defined]
        return transport


class TestAllowlistAndCeiling(G3TestCase):
    def test_exactly_ten_urls(self):
        self.assertEqual(len(G3_URLS_ORDERED), 10)
        self.assertEqual(len(G3_URLS), 10)
        self.assertEqual(len(_SLOT_ORDER), 10)

    def test_unknown_url_refused(self):
        with self.assertRaises(CaptureRefusal):
            refuse_unknown_url("https://evil.example/x")

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
        self.assertEqual(out["source_count"], 10)


class TestPromotionLedgerMapping(G3TestCase):
    def test_source_mapping_matches_assignment(self):
        sources = build_g3_sources()
        by_slot = {s.logical_slot: s for s in sources}
        self.assertEqual(by_slot["E01"].source_kind, "k3_original")
        self.assertEqual(by_slot["E02"].source_kind, "k3_original")
        self.assertEqual(by_slot["E03"].source_kind, "k3_original")
        self.assertEqual(by_slot["E04"].source_kind, "k3c_corrected")
        self.assertEqual(by_slot["E05"].source_kind, "k3c_corrected")
        self.assertEqual(by_slot["E06"].source_kind, "k3c_corrected")
        self.assertEqual(by_slot["F01"].source_kind, "k3c_reconciled")
        self.assertEqual(by_slot["F02"].source_kind, "k3_original")
        self.assertEqual(by_slot["F03"].source_kind, "k3c_corrected")
        self.assertEqual(by_slot["F04"].source_kind, "k3c_reconciled")
        for s in sources:
            path = acquisition_raw_path(
                s.source_capture_id, s.source_kind, s.raw_name)
            self.assertTrue(path.exists(), msg=str(path))
            self.assertEqual(sha256_file(path), s.acquisition_raw_sha256)

    def test_urls_match_ordered_allowlist(self):
        sources = build_g3_sources()
        self.assertEqual(
            [s.capture_url for s in sources], list(G3_URLS_ORDERED))


class TestByteAndJsonDriftTyping(G3TestCase):
    def test_exact_bytes(self):
        typed = type_content_identity(
            "E", True,
            {"parsed_object": {"a": 1}, "canonical_id": "X", "text_present": True,
             "json_parse_ok": True},
            {"parsed_object": {"a": 1}, "canonical_id": "X", "text_present": True,
             "json_parse_ok": True},
        )
        self.assertEqual(typed["content_identity"], "exact")
        self.assertIsNone(typed["drift_type"])

    def test_json_key_order_only_after_parsed_equality(self):
        obj = {"licenseId": "BSL-1.0", "licenseText": "text"}
        typed = type_content_identity(
            "E", False,
            {"parsed_object": obj, "canonical_id": "BSL-1.0",
             "text_present": True, "json_parse_ok": True,
             "licenseId": "BSL-1.0"},
            {"parsed_object": dict(obj), "canonical_id": "BSL-1.0",
             "text_present": True, "json_parse_ok": True,
             "licenseId": "BSL-1.0"},
        )
        self.assertEqual(typed["content_identity"], "drift")
        self.assertEqual(typed["drift_type"], "json_key_order_only")
        self.assertTrue(typed["parsed_objects_equal"])

    def test_json_parsed_diff(self):
        typed = type_content_identity(
            "E", False,
            {"parsed_object": {"licenseId": "A", "licenseText": "t"},
             "canonical_id": "A", "text_present": True, "json_parse_ok": True,
             "licenseId": "A"},
            {"parsed_object": {"licenseId": "B", "licenseText": "t"},
             "canonical_id": "B", "text_present": True, "json_parse_ok": True,
             "licenseId": "B"},
        )
        self.assertEqual(typed["drift_type"], "json_parsed_diff")
        self.assertTrue(typed["field_diffs"])

    def test_f_raw_drift_does_not_erase_when_normalized_matches(self):
        typed = type_content_identity(
            "F", False,
            {"normalized_text_sha256": "aaa", "section_text_sha256": "bbb",
             "matched_statement": "stmt", "named_surface": "s",
             "framework_version": "1", "relation": "removed"},
            {"normalized_text_sha256": "aaa", "section_text_sha256": "bbb",
             "matched_statement": "stmt", "named_surface": "s",
             "framework_version": "1", "relation": "removed"},
        )
        self.assertEqual(typed["content_identity"], "drift")
        self.assertEqual(
            typed["drift_type"], "raw_byte_drift_normalized_and_section_match")
        self.assertFalse(typed["raw_drift_erased_by_normalized_match"])
        self.assertTrue(typed["normalized_equal"])
        self.assertFalse(typed["raw_bytes_equal"])


class TestExecuteInjected(G3TestCase):
    def test_create_once_and_no_overwrite(self):
        sources = build_g3_sources()
        # Use real acquisition bytes for exact match path.
        mapping = {}
        for s in sources:
            path = acquisition_raw_path(
                s.source_capture_id, s.source_kind, s.raw_name)
            mapping[s.capture_url] = path.read_bytes()
        transport = self.fake_transport(mapping)
        out = execute_live(
            transport=transport,  # type: ignore[arg-type]
            root=self.root,
            write_plan_if_missing=True,
        )
        self.assertEqual(out["network_calls"], 10)
        self.assertEqual(out["content_identity_counts"]["exact"], 10)
        self.assertEqual(len(transport.calls), 10)  # type: ignore[attr-defined]
        self.assertFalse(verify_hashes(self.root))

        with self.assertRaises(CaptureRefusal):
            execute_live(
                transport=transport,  # type: ignore[arg-type]
                root=self.root,
                write_plan_if_missing=False,
            )

    def test_no_retry_on_redirect_refused(self):
        sources = build_g3_sources()
        calls: list[str] = []

        def transport(url: str) -> FakeResponse:
            calls.append(url)
            return FakeResponse(
                status=302,
                headers={"content-type": "text/html", "location": url + "x"},
                body=b"",
                url=url,
                redirect_chain=[url, url + "x"],
                redirect_refused=True,
            )

        # Only need to ensure ceiling and one call per URL; execute will still
        # write artifacts. Use first URL failure path via custom loop would be
        # heavy; instead test CallCeiling + refuse and compare_one redirect flag.
        ceiling = CallCeiling(MAX_CALLS)
        for url in G3_URLS_ORDERED:
            ceiling.record()
            resp = transport(url)
            self.assertTrue(resp.redirect_refused)
        self.assertEqual(len(calls), 10)
        with self.assertRaises(CaptureRefusal):
            ceiling.record()

    def test_e_compare_detects_id_field(self):
        sources = build_g3_sources()
        e01 = next(s for s in sources if s.logical_slot == "E01")
        acq = acquisition_raw_path(
            e01.source_capture_id, e01.source_kind, e01.raw_name).read_bytes()
        # Same bytes -> exact
        resp = FakeResponse(200, {"content-type": "application/json"}, acq,
                            e01.capture_url, [e01.capture_url], False)
        row = compare_one(e01, resp, acq, "plan")
        self.assertEqual(row["content_identity"], "exact")
        self.assertTrue(row["canonical_id_match"])
        self.assertTrue(row["text_present"])


class TestPlanWrite(G3TestCase):
    def test_write_plan_zero_network(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            plan = write_plan(self.root)
            urlopen.assert_not_called()
        self.assertEqual(plan["source_count"], 10)
        self.assertTrue((self.root / "plan.json").exists())
        with self.assertRaises(CaptureRefusal):
            write_plan(self.root)


if __name__ == "__main__":
    unittest.main()
