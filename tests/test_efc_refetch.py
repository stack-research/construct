"""Offline unit tests for harness.efc_refetch — injected transport only."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from harness.efc_capture import CaptureRefusal, canonical_json, sha256_bytes, sha256_file
from harness.efc_refetch import (
    G1_IDS,
    G1_SOURCES,
    G1_URLS,
    extract_identity_fields,
    field_level_diff,
    dry_run,
    execute_live,
    refuse_unknown_url,
    verify_identity_against_expected,
    verify_refetch_hashes,
)


@dataclass
class FakeResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]


def osv_body(record_id: str, package: str, *, pub: str = "2026-01-15T00:00:00Z",
             fixed: str = "1.0.0") -> bytes:
    payload = {
        "id": record_id,
        "published": pub,
        "modified": "2026-02-01T00:00:00Z",
        "affected": [{
            "package": {"ecosystem": "crates.io", "name": package},
            "ranges": [{"type": "SEMVER", "events": [
                {"introduced": "0"}, {"fixed": fixed},
            ]}],
        }],
    }
    return canonical_json(payload).encode()


def github_body(ghsa_id: str, package: str, ecosystem: str, vrange: str,
                *, pub: str = "2026-03-01T00:00:00Z") -> bytes:
    payload = {
        "ghsa_id": ghsa_id,
        "published_at": pub,
        "updated_at": "2026-03-02T00:00:00Z",
        "vulnerabilities": [{
            "package": {"ecosystem": ecosystem, "name": package},
            "vulnerable_version_range": vrange,
        }],
    }
    return canonical_json(payload).encode()


class RefetchTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.k1 = Path(self.tmp) / "k1"
        self.captures = self.k1 / "captures"
        self.refetch = self.k1 / "refetch"
        self.captures.mkdir(parents=True)
        self.refetch.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_fixture_k1(self, bodies: dict[str, bytes]) -> None:
        raw_sha = {}
        sidecar_sha = {}
        for spec in G1_SOURCES:
            body = bodies[spec.capture_id]
            cdir = self.captures / spec.capture_id
            cdir.mkdir(parents=True)
            raw_path = cdir / "raw.json"
            raw_path.write_bytes(body)
            sc = {
                "capture_id": spec.capture_id,
                "raw_sha256": sha256_bytes(body),
                "record_id_expected": spec.record_id_expected,
                "package_expected": spec.package_expected,
                "ecosystem_expected": spec.ecosystem_expected,
            }
            sc_path = cdir / "sidecar.json"
            sc_path.write_text(canonical_json(sc) + "\n")
            raw_sha[spec.capture_id] = sha256_bytes(body)
            sidecar_sha[spec.capture_id] = sha256_file(sc_path)

        plan = {"schema_version": "test-plan", "attempt_count": 12}
        plan_path = self.k1 / "plan.json"
        plan_path.write_text(canonical_json(plan) + "\n")
        plan_sha = sha256_file(plan_path)

        report = {"schema_version": "test-report"}
        report_path = self.k1 / "capture_report.json"
        report_path.write_text(canonical_json(report) + "\n")
        report_sha = sha256_file(report_path)

        amendment = {
            "schema_version": "efc-k1-normalization-amendment-v1",
            "ecosystem_mapping": {
                "closed": True,
                "PyPI": "pypi_registry",
                "pip": "pypi_registry",
                "npm": "npm",
            },
            "pinned_original_artifacts": {
                "plan_sha256": plan_sha,
                "capture_report_sha256": report_sha,
                "raw_sha256": raw_sha,
                "capture_sidecar_sha256": sidecar_sha,
            },
        }
        (self.k1 / "normalization_amendment.json").write_text(
            canonical_json(amendment) + "\n")
        reconciled = {
            "schema_version": "efc-k1-capture-report-reconciled-v1",
            "plan_sha256": plan_sha,
        }
        (self.k1 / "capture_report.reconciled.json").write_text(
            canonical_json(reconciled) + "\n")

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


class TestG1Plan(RefetchTestCase):
    def test_exactly_twelve_sources(self):
        self.assertEqual(len(G1_SOURCES), 12)
        self.assertEqual(len(G1_IDS), 12)
        self.assertEqual(len(G1_URLS), 12)
        self.assertEqual(list(G1_IDS), [s.capture_id for s in G1_SOURCES])

    def test_unknown_url_refused(self):
        with self.assertRaises(CaptureRefusal):
            refuse_unknown_url("https://evil.example/vuln")

    def test_dry_run_zero_network_against_repo(self):
        # Uses real K1 artifacts; no network.
        out = dry_run()
        self.assertEqual(out["network_calls"], 0)
        self.assertEqual(out["source_count"], 12)


class TestIdentityAndDrift(RefetchTestCase):
    def test_pypi_pip_ecosystem_match(self):
        spec = next(s for s in G1_SOURCES if s.capture_id == "capB-02")
        fields = extract_identity_fields(
            github_body(spec.record_id_expected, spec.package_expected, "pip",
                        "<= 0.63.0"),
            spec.capture_url,
        )
        notes = verify_identity_against_expected(spec, fields)
        self.assertNotIn("ecosystem_mismatch", notes)
        self.assertEqual(fields["ecosystem_normalized"], "pypi_registry")

    def test_field_level_diff_bounded(self):
        url = "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0002"
        a = extract_identity_fields(
            osv_body("RUSTSEC-2026-0002", "lru", fixed="1.0.0"), url)
        b = extract_identity_fields(
            osv_body("RUSTSEC-2026-0002", "lru", fixed="1.0.1"), url)
        diffs = field_level_diff(a, b)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0]["field"], "affected_range_fields")


class TestExecuteInjected(RefetchTestCase):
    def _bodies_exact(self) -> dict[str, bytes]:
        bodies: dict[str, bytes] = {}
        for spec in G1_SOURCES:
            if spec.capture_url.startswith("https://api.github.com/"):
                eco = "pip" if spec.ecosystem_expected == "PyPI" else spec.ecosystem_expected
                bodies[spec.capture_id] = github_body(
                    spec.record_id_expected, spec.package_expected, eco, "<= 1.2.3")
            else:
                bodies[spec.capture_id] = osv_body(
                    spec.record_id_expected, spec.package_expected)
        return bodies

    def test_exact_identity_twelve(self):
        bodies = self._bodies_exact()
        self._write_fixture_k1(bodies)
        mapping = {s.capture_url: bodies[s.capture_id] for s in G1_SOURCES}
        transport = self.fake_transport(mapping)
        out = execute_live(
            transport=transport,  # type: ignore[arg-type]
            refetch_root=self.refetch,
            k1_root=self.k1,
            report_path=self.k1 / "refetch_report.json",
            captures_root=self.captures,
        )
        self.assertEqual(out["network_calls"], 12)
        self.assertEqual(out["content_identity_counts"]["exact"], 12)
        self.assertEqual(out["content_identity_counts"]["drift"], 0)
        self.assertEqual(len(transport.calls), 12)  # type: ignore[attr-defined]
        self.assertFalse(verify_refetch_hashes(self.refetch))

    def test_drift_preserves_both_hashes(self):
        bodies = self._bodies_exact()
        self._write_fixture_k1(bodies)
        drifted = dict(bodies)
        # Change only range field for one OSV record.
        spec = G1_SOURCES[0]
        drifted[spec.capture_id] = osv_body(
            spec.record_id_expected, spec.package_expected, fixed="9.9.9")
        mapping = {s.capture_url: drifted[s.capture_id] for s in G1_SOURCES}
        transport = self.fake_transport(mapping)
        out = execute_live(
            transport=transport,  # type: ignore[arg-type]
            refetch_root=self.refetch,
            k1_root=self.k1,
            report_path=self.k1 / "refetch_report.json",
            captures_root=self.captures,
        )
        self.assertEqual(out["content_identity_counts"]["exact"], 11)
        self.assertEqual(out["content_identity_counts"]["drift"], 1)
        row = next(r for r in out["rows"] if r["capture_id"] == spec.capture_id)
        self.assertEqual(row["content_identity"], "drift")
        self.assertNotEqual(row["original_raw_sha256"], row["refetch_raw_sha256"])
        self.assertTrue(row["field_diffs"])
        self.assertEqual(row["field_diffs"][0]["field"], "affected_range_fields")

    def test_create_once_refusal(self):
        bodies = self._bodies_exact()
        self._write_fixture_k1(bodies)
        mapping = {s.capture_url: bodies[s.capture_id] for s in G1_SOURCES}
        transport = self.fake_transport(mapping)
        execute_live(
            transport=transport,  # type: ignore[attr-defined]
            refetch_root=self.refetch,
            k1_root=self.k1,
            report_path=self.k1 / "refetch_report.json",
            captures_root=self.captures,
        )
        with self.assertRaises(CaptureRefusal):
            execute_live(
                transport=transport,  # type: ignore[arg-type]
                refetch_root=self.refetch,
                k1_root=self.k1,
                report_path=self.k1 / "refetch_report.json",
                captures_root=self.captures,
            )


if __name__ == "__main__":
    unittest.main()
