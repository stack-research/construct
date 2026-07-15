"""Offline unit tests for harness.efc_refetch_g4 — injected transport only."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from harness.efc_capture_k4 import CaptureRefusal, canonical_json, sha256_file
from harness.efc_capture_k4br import KIMI_DISCOVERY_ONLY_URLS
from harness.efc_refetch_g4 import (
    EXCLUDED_B_URLS,
    MAX_CALLS,
    CallCeiling,
    assert_allowlist_exclusions,
    build_g4_sources,
    build_identity_audit,
    build_plan,
    compare_one,
    derive_allowlist,
    dry_run,
    execute_live,
    load_ledger,
    positive_requalification,
    refuse_unknown_url,
    type_identity,
    verify_hashes,
    write_plan,
    _qualify_osv_a,
    _qualify_ghsa_b,
)


@dataclass
class FakeResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]
    redirect_refused: bool = False


class G4TestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp) / "g4"

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


class TestAllowlistDerivation(G4TestCase):
    def test_exactly_forty_from_promoted_rows(self):
        sources = build_g4_sources()
        ordered, allowlist = derive_allowlist()
        self.assertEqual(len(sources), 40)
        self.assertEqual(len(ordered), 40)
        self.assertEqual(len(allowlist), 40)
        self.assertEqual(MAX_CALLS, 40)
        self.assertEqual(
            [s.capture_url for s in sources], list(ordered))

    def test_excluded_b_urls_not_in_allowlist(self):
        _, allowlist = derive_allowlist()
        for url in EXCLUDED_B_URLS:
            self.assertNotIn(url, allowlist)
        for url in KIMI_DISCOVERY_ONLY_URLS:
            self.assertNotIn(url, allowlist)

    def test_excluded_url_refused(self):
        _, allowlist = derive_allowlist()
        with self.assertRaises(CaptureRefusal):
            refuse_unknown_url(next(iter(EXCLUDED_B_URLS)), allowlist)
        with self.assertRaises(CaptureRefusal):
            refuse_unknown_url(next(iter(KIMI_DISCOVERY_ONLY_URLS)), allowlist)

    def test_assert_allowlist_exclusions_raises(self):
        with self.assertRaises(CaptureRefusal):
            assert_allowlist_exclusions(
                list(derive_allowlist()[0]) + [next(iter(EXCLUDED_B_URLS))])

    def test_acquisition_hashes_match_ledger(self):
        ledger = load_ledger()
        for row, spec in zip(ledger["rows"], build_g4_sources()):
            self.assertEqual(row["logical_slot"], spec.logical_slot)
            self.assertTrue(spec.acquisition_raw_path.exists())
            self.assertEqual(
                sha256_file(spec.acquisition_raw_path),
                spec.acquisition_raw_sha256)

    def test_dry_run_zero_network(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            out = dry_run()
            urlopen.assert_not_called()
        self.assertEqual(out["network_calls"], 0)
        self.assertEqual(out["source_count"], 40)


class TestCallCeilingAndOrder(G4TestCase):
    def test_call_ceiling(self):
        c = CallCeiling(2)
        c.record()
        c.record()
        with self.assertRaises(CaptureRefusal):
            c.record()

    def test_execute_call_order_and_ceiling(self):
        sources = build_g4_sources()
        mapping = {
            s.capture_url: s.acquisition_raw_path.read_bytes()
            for s in sources
        }
        transport = self.fake_transport(mapping)
        out = execute_live(
            transport=transport,  # type: ignore[arg-type]
            root=self.root,
        )
        self.assertEqual(out["network_calls"], 40)
        self.assertEqual(len(transport.calls), 40)  # type: ignore[attr-defined]
        self.assertEqual(transport.calls, [s.capture_url for s in sources])  # type: ignore[attr-defined]

    def test_zero_retry_create_once(self):
        sources = build_g4_sources()
        mapping = {s.capture_url: s.acquisition_raw_path.read_bytes() for s in sources}
        transport = self.fake_transport(mapping)
        execute_live(transport=transport, root=self.root)  # type: ignore[arg-type]
        with self.assertRaises(CaptureRefusal):
            execute_live(transport=transport, root=self.root)  # type: ignore[arg-type]


class TestIdentityVsRequalification(G4TestCase):
    def test_byte_drift_independent_of_qualification(self):
        sources = build_g4_sources()
        spec = next(s for s in sources if s.logical_slot == "A01")
        acq = spec.acquisition_raw_path.read_bytes()
        drifted = acq + b" "
        resp = FakeResponse(200, {}, drifted, spec.capture_url, [spec.capture_url])
        row = compare_one(spec, resp, acq, "plan", set())
        self.assertEqual(row["content_identity"], "drift")
        self.assertFalse(row["raw_bytes_equal"])
        # Drifted JSON may still requalify if parse succeeds on drifted body — often fails.
        # Force qualification path on valid acquisition parse separately:
        resp2 = FakeResponse(200, {}, acq, spec.capture_url, [spec.capture_url])
        row2 = compare_one(spec, resp2, acq, "plan", set())
        self.assertEqual(row2["content_identity"], "exact")
        self.assertTrue(row2["positive_requalification_pass"])

    def test_predicate_pass_does_not_mask_drift(self):
        sources = build_g4_sources()
        spec = next(s for s in sources if s.logical_slot == "C01")
        acq = spec.acquisition_raw_path.read_bytes()
        drifted = acq[:-1] + (b"}" if acq[-1:] != b"}" else b"]")
        resp = FakeResponse(200, {}, drifted, spec.capture_url, [spec.capture_url])
        row = compare_one(spec, resp, acq, "plan", set())
        self.assertEqual(row["content_identity"], "drift")
        self.assertNotEqual(row["content_identity"], "exact")

    def test_type_identity_exact(self):
        t = type_identity(True)
        self.assertEqual(t["content_identity"], "exact")


class TestFamilyValidators(G4TestCase):
    def test_osv_a_negative_near_miss(self):
        sources = build_g4_sources()
        spec = next(s for s in sources if s.logical_slot == "A01")
        data = json.loads(spec.acquisition_raw_path.read_text())
        data["id"] = "RUSTSEC-2099-0001"
        ok, reasons = _qualify_osv_a(spec, data, 200, False)
        self.assertFalse(ok)
        self.assertIn("id_mismatch", reasons)

    def test_ghsa_b_negative_near_miss(self):
        sources = build_g4_sources()
        spec = next(s for s in sources if s.logical_slot == "B01")
        data = json.loads(spec.acquisition_raw_path.read_bytes())
        data["published_at"] = "2025-01-01T00:00:00Z"
        ok, reasons = _qualify_ghsa_b(spec, data, 200, False)
        self.assertFalse(ok)
        self.assertIn("published_at_not_2026", reasons)

    def test_p01_positive_on_acquisition(self):
        sources = build_g4_sources()
        spec = next(s for s in sources if s.logical_slot == "P01")
        body = spec.acquisition_raw_path.read_bytes()
        resp = FakeResponse(200, {}, body, spec.capture_url, [spec.capture_url])
        ok, reasons, _ = positive_requalification(spec, body, resp, set())
        self.assertTrue(ok, msg=reasons)

    def test_redirect_refused_fails_requalification(self):
        sources = build_g4_sources()
        spec = next(s for s in sources if s.logical_slot == "D01")
        body = spec.acquisition_raw_path.read_bytes()
        resp = FakeResponse(
            302, {"location": spec.capture_url + "x"}, b"",
            spec.capture_url, [spec.capture_url, spec.capture_url + "x"],
            redirect_refused=True)
        ok, reasons, _ = positive_requalification(spec, body, resp, set())
        self.assertFalse(ok)
        self.assertTrue(
            "redirect_refused" in reasons or "http_not_200" in reasons)


class TestIdentityAudit(G4TestCase):
    def test_fresh_global_collision_detection(self):
        sources = build_g4_sources()
        mapping = {s.capture_url: s.acquisition_raw_path.read_bytes() for s in sources}
        transport = self.fake_transport(mapping)
        execute_live(transport=transport, root=self.root)  # type: ignore[arg-type]
        report = json.loads((self.root / "refetch_report.json").read_text())
        plan = json.loads((self.root / "plan.json").read_text())
        audit = build_identity_audit(report["rows"], plan)
        self.assertTrue(audit["assertions"]["distinct_record_ids"])
        self.assertTrue(audit["assertions"]["distinct_urls"])
        self.assertTrue(audit["assertions"]["distinct_entities"])
        self.assertTrue(audit["assertions"]["no_alias_cross_row_duplicates"])
        self.assertTrue(audit["assertions"]["person_name_screen_clear"])
        self.assertEqual(audit["family_counts"]["A"], 8)
        self.assertEqual(audit["family_counts"]["B"], 7)

    def test_collision_detection_flags_duplicate(self):
        rows = [
            {"logical_slot": "A01", "family": "A", "record_id": "X", "entity_key": "a",
             "capture_url": "https://example.com/1", "alias_extraction": {"aliases": []},
             "content_identity": "exact", "positive_requalification_pass": True},
            {"logical_slot": "A02", "family": "A", "record_id": "X", "entity_key": "b",
             "capture_url": "https://example.com/2", "alias_extraction": {"aliases": []},
             "content_identity": "exact", "positive_requalification_pass": True},
        ]
        plan = {"plan_sha256": "x", "promotion_identity_ledger_sha256": "y"}
        audit = build_identity_audit(rows, plan)
        self.assertFalse(audit["assertions"]["distinct_record_ids"])


class TestPlanAndHashes(G4TestCase):
    def test_write_plan_create_once(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            plan = write_plan(self.root)
            urlopen.assert_not_called()
        self.assertEqual(plan["source_count"], 40)
        self.assertTrue(plan["allowlist_assertions"]["excluded_slots_absent"])
        with self.assertRaises(CaptureRefusal):
            write_plan(self.root)

    def test_verify_hashes_after_execute(self):
        sources = build_g4_sources()
        mapping = {s.capture_url: s.acquisition_raw_path.read_bytes() for s in sources}
        transport = self.fake_transport(mapping)
        execute_live(transport=transport, root=self.root)  # type: ignore[arg-type]
        self.assertFalse(verify_hashes(self.root))

    def test_build_plan_has_ledger_sha(self):
        plan = build_plan()
        self.assertEqual(len(plan["entries"]), 40)
        self.assertIn("promotion_identity_ledger_sha256", plan)
        self.assertIn("plan_sha256", plan)


class TestExecuteSummary(G4TestCase):
    def test_full_execute_exact_match(self):
        sources = build_g4_sources()
        mapping = {s.capture_url: s.acquisition_raw_path.read_bytes() for s in sources}
        transport = self.fake_transport(mapping)
        out = execute_live(transport=transport, root=self.root)  # type: ignore[arg-type]
        self.assertEqual(out["content_identity_counts"]["exact"], 40)
        self.assertEqual(out["positive_requalification_counts"]["pass"], 40)
        self.assertTrue(all(a for a in out["identity_assertions"].values()))


if __name__ == "__main__":
    unittest.main()
