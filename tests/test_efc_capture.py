"""Offline unit tests for harness.efc_capture — injected transport only."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from harness.efc_capture import (
    CANONICAL_CAPTURES,
    CaptureRefusal,
    FROZEN_ATTEMPTS,
    QA_ATTEMPTS,
    apply_promotion,
    build_capture_sidecar,
    build_plan,
    build_qa_sidecar,
    canonical_json,
    check_create_once,
    dry_run,
    ecosystems_match,
    execute_live,
    github_finite_bound_conservative,
    normalize_ecosystem,
    reconcile_k1,
    refuse_unknown_url,
    run_attempt,
    sha256_bytes,
    validate_capture,
    validate_capture_reconciled,
    verify_sidecar_hashes,
    _pin_original_hashes,
    _verify_pinned_hashes,
    CaptureSpec,
    K1_ROOT,
)


@dataclass
class FakeResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]


def osv_body(record_id: str, package: str, *, pub: str = "2026-01-15T00:00:00Z",
             withdrawn: str | None = None,
             events: list[dict] | None = None) -> bytes:
    payload = {
        "id": record_id,
        "published": pub,
        "modified": "2026-02-01T00:00:00Z",
        "affected": [{
            "package": {"ecosystem": "crates.io", "name": package},
            "ranges": [{"type": "SEMVER", "events": events or [
                {"introduced": "0"}, {"fixed": "1.0.0"},
            ]}],
        }],
    }
    if withdrawn:
        payload["withdrawn"] = withdrawn
    return canonical_json(payload).encode()


def github_body(ghsa_id: str, package: str, ecosystem: str, vrange: str,
                *, pub: str = "2026-03-01T00:00:00Z",
                withdrawn_at: str | None = None) -> bytes:
    payload = {
        "ghsa_id": ghsa_id,
        "published_at": pub,
        "updated_at": "2026-03-02T00:00:00Z",
        "vulnerabilities": [{
            "package": {"ecosystem": ecosystem, "name": package},
            "vulnerable_version_range": vrange,
        }],
    }
    if withdrawn_at:
        payload["withdrawn_at"] = withdrawn_at
    return canonical_json(payload).encode()


class CaptureTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp) / "k1"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fake_transport(self, mapping: dict[str, bytes],
                       status: int = 200) -> object:
        calls: list[str] = []

        def transport(url: str) -> FakeResponse:
            calls.append(url)
            if url not in mapping:
                raise AssertionError(f"unexpected URL: {url}")
            return FakeResponse(status=status,
                                headers={"content-type": "application/json"},
                                body=mapping[url], url=url, redirect_chain=[url])

        transport.calls = calls  # type: ignore[attr-defined]
        return transport


class TestFrozenPlan(CaptureTestCase):
    def test_exact_fifteen_order(self):
        self.assertEqual(len(FROZEN_ATTEMPTS), 15)
        self.assertEqual(len(CANONICAL_CAPTURES), 8)
        self.assertEqual(len(QA_ATTEMPTS), 7)
        ids = [s.capture_id for s in FROZEN_ATTEMPTS]
        self.assertEqual(ids[:8], [s.capture_id for s in CANONICAL_CAPTURES])
        self.assertEqual(ids[8:], [s.capture_id for s in QA_ATTEMPTS])

    def test_unknown_url_refused(self):
        with self.assertRaises(CaptureRefusal):
            refuse_unknown_url("https://evil.example/vuln")

    def test_dry_run_zero_network(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            out = dry_run(self.root)
            urlopen.assert_not_called()
        self.assertEqual(out["network_calls"], 0)
        self.assertEqual(out["plan"]["attempt_count"], 15)


class TestValidation(CaptureTestCase):
    def test_osv_introduced_zero_plus_fixed_passes(self):
        data = json.loads(osv_body("RUSTSEC-2026-0002", "lru"))
        spec = QA_ATTEMPTS[0]
        v, fails, q = validate_capture(spec, data, True, None)
        self.assertEqual(v, "pass")
        self.assertFalse(fails)

    def test_osv_introduced_zero_alone_fails(self):
        data = json.loads(osv_body("RUSTSEC-2026-0002", "lru", events=[
            {"introduced": "0"},
        ]))
        spec = QA_ATTEMPTS[0]
        v, fails, _ = validate_capture(spec, data, True, None)
        self.assertEqual(v, "fail")
        self.assertIn("missing_finite_bound", fails)

    def test_id_package_ecosystem_mismatch_fails(self):
        data = json.loads(osv_body("RUSTSEC-2026-0002", "wrong-crate"))
        spec = QA_ATTEMPTS[0]
        v, fails, _ = validate_capture(spec, data, True, None)
        self.assertIn("package_mismatch", fails)

    def test_withdrawn_fails(self):
        data = json.loads(osv_body("RUSTSEC-2026-0002", "lru",
                                   withdrawn="2026-01-01T00:00:00Z"))
        spec = QA_ATTEMPTS[0]
        v, fails, _ = validate_capture(spec, data, True, None)
        self.assertIn("withdrawn", fails)

    def test_github_range_from_vulnerable_version_range(self):
        body = github_body("GHSA-pmch-g965-grmr", "langroid", "PyPI", "<= 0.63.0")
        data = json.loads(body)
        spec = CANONICAL_CAPTURES[3]
        v, fails, _ = validate_capture(spec, data, True, None)
        self.assertEqual(v, "pass", msg=str(fails))

    def test_missing_range_fails(self):
        data = {"ghsa_id": "GHSA-pmch-g965-grmr", "published_at": "2026-01-01",
                "vulnerabilities": []}
        spec = CANONICAL_CAPTURES[3]
        v, fails, _ = validate_capture(spec, data, True, None)
        self.assertIn("missing_range", fails)


class TestCreateOnceAndTransport(CaptureTestCase):
    def test_create_once_refusal(self):
        self.root.mkdir(parents=True)
        (self.root / "plan.json").write_text("{}")
        with self.assertRaises(CaptureRefusal):
            check_create_once(self.root)

    def test_injected_transport_one_call_per_url(self):
        cap = CANONICAL_CAPTURES[0]
        body = osv_body("RUSTSEC-2026-0038", "rssn")
        transport = self.fake_transport({cap.capture_url: body})
        self.root.mkdir(parents=True)
        plan = build_plan(self.root)
        run_attempt(cap, transport, self.root, plan["plan_sha256"])
        self.assertEqual(len(transport.calls), 1)  # type: ignore[attr-defined]

    def test_no_retry_on_http_failure(self):
        cap = CANONICAL_CAPTURES[0]
        transport = self.fake_transport({})
        transport.calls = []  # type: ignore[attr-defined]

        def fail_transport(url: str) -> FakeResponse:
            transport.calls.append(url)  # type: ignore[attr-defined]
            return FakeResponse(status=500, headers={}, body=b"err",
                                url=url, redirect_chain=[url])

        self.root.mkdir(parents=True)
        plan = build_plan(self.root)
        sc = run_attempt(cap, fail_transport, self.root, plan["plan_sha256"])
        self.assertEqual(len(transport.calls), 1)  # type: ignore[attr-defined]
        self.assertEqual(sc["capture_verdict"], "fail")
        self.assertIn("http_failure", sc["failure_reasons"])

    def test_raw_byte_hash_equals_on_disk(self):
        cap = CANONICAL_CAPTURES[0]
        body = osv_body("RUSTSEC-2026-0038", "rssn")
        transport = self.fake_transport({cap.capture_url: body})
        self.root.mkdir(parents=True)
        plan = build_plan(self.root)
        sc = run_attempt(cap, transport, self.root, plan["plan_sha256"])
        raw_path = self.root / "captures" / cap.capture_id / "raw.json"
        self.assertEqual(sc["raw_sha256"], sha256_bytes(raw_path.read_bytes()))


class TestSidecarShape(CaptureTestCase):
    def test_no_scope_or_prose_fields(self):
        cap = CANONICAL_CAPTURES[0]
        body = osv_body("RUSTSEC-2026-0038", "rssn")
        resp = FakeResponse(200, {"content-type": "application/json"},
                            body, cap.capture_url, [cap.capture_url])
        sc = build_capture_sidecar(cap, "abc", resp, body)
        forbidden = {"scope_extract", "summary", "description", "severity",
                       "answer", "decision_scope"}
        for key in sc:
            self.assertNotIn(key, forbidden)
        self.assertEqual(sc["schema_version"], "efc-k1-acquisition-v1")
        self.assertEqual(sc["oracle_id"], "efc-calibration-capA-02")

    def test_qa_sidecar_has_qualifies_not_oracle(self):
        spec = QA_ATTEMPTS[0]
        body = osv_body("RUSTSEC-2026-0002", "lru")
        resp = FakeResponse(200, {"content-type": "application/json"},
                            body, spec.capture_url, [spec.capture_url])
        sc = build_qa_sidecar(spec, "abc", resp, body)
        self.assertIn("qualifies", sc)
        self.assertNotIn("oracle_id", sc)


class TestPromotion(CaptureTestCase):
    def _write_qa(self, qa_id: str, package: str, record_id: str,
                  qualifies: bool = True) -> None:
        spec = next(s for s in QA_ATTEMPTS if s.capture_id == qa_id)
        qdir = self.root / "qualification" / qa_id
        qdir.mkdir(parents=True, exist_ok=True)
        if qualifies:
            body = osv_body(record_id, package)
        else:
            body = osv_body(record_id, package, events=[{"introduced": "0"}])
        (qdir / "raw.json").write_bytes(body)
        resp = FakeResponse(200, {"content-type": "application/json"},
                            body, spec.capture_url, [spec.capture_url])
        sc = build_qa_sidecar(spec, "planhash", resp, body)
        (qdir / "sidecar.json").write_text(canonical_json(sc) + "\n")

    def test_deterministic_promotion_order(self):
        self.root.mkdir(parents=True)
        self._write_qa("qaA-lru", "lru", "RUSTSEC-2026-0002")
        self._write_qa("qaA-memmap2", "memmap2", "RUSTSEC-2026-0186")
        self._write_qa("qaA-quinn-proto", "quinn-proto", "RUSTSEC-2026-0185")
        self._write_qa("qaA-hpke-rs-rust-crypto", "hpke-rs-rust-crypto",
                       "RUSTSEC-2026-0072")
        ledger = apply_promotion(self.root, "planhash")
        self.assertFalse(ledger["family_shortfall"])
        promos = ledger["promotions"]
        self.assertEqual([p["capture_id"] for p in promos],
                         ["capA-01", "capA-03", "capA-05", "capA-06"])
        for target, qa in zip(["capA-01", "capA-03", "capA-05", "capA-06"],
                              ["qaA-lru", "qaA-memmap2", "qaA-quinn-proto",
                               "qaA-hpke-rs-rust-crypto"]):
            raw = (self.root / "captures" / target / "raw.json").read_bytes()
            qa_raw = (self.root / "qualification" / qa / "raw.json").read_bytes()
            self.assertEqual(raw, qa_raw)

    def test_fallback_when_original_fails(self):
        self.root.mkdir(parents=True)
        self._write_qa("qaA-lru", "lru", "RUSTSEC-2026-0002", qualifies=False)
        self._write_qa("qaA-memmap2", "memmap2", "RUSTSEC-2026-0186")
        self._write_qa("qaA-quinn-proto", "quinn-proto", "RUSTSEC-2026-0185")
        self._write_qa("qaA-hpke-rs-rust-crypto", "hpke-rs-rust-crypto",
                       "RUSTSEC-2026-0072")
        self._write_qa("qaA-enum-map", "enum-map", "RUSTSEC-2026-0019")
        ledger = apply_promotion(self.root, "planhash")
        promoted = [e["promoted_to"] for e in ledger["entries"]
                    if e.get("promoted_to")]
        self.assertIn("capA-01", promoted)
        self.assertIn("capA-06", promoted)

    def test_family_shortfall_when_fewer_than_four(self):
        self.root.mkdir(parents=True)
        self._write_qa("qaA-lru", "lru", "RUSTSEC-2026-0002", qualifies=False)
        ledger = apply_promotion(self.root, "planhash")
        self.assertTrue(ledger["family_shortfall"])
        self.assertLess(len(ledger["promotions"]), 4)


class TestFullDryExecute(CaptureTestCase):
    def test_execute_refuses_second_run(self):
        mapping = {}
        for spec in FROZEN_ATTEMPTS:
            if spec.capture_url.startswith("https://api.github.com/"):
                mapping[spec.capture_url] = github_body(
                    spec.record_id, spec.package_expected,
                    spec.ecosystem_expected, "< 9.9.9")
            else:
                mapping[spec.capture_url] = osv_body(
                    spec.record_id, spec.package_expected)
        transport = self.fake_transport(mapping)
        execute_live(self.root, transport=transport)
        with self.assertRaises(CaptureRefusal):
            execute_live(self.root, transport=transport)

    def test_verify_sidecar_hashes(self):
        mapping = {CANONICAL_CAPTURES[0].capture_url:
                   osv_body("RUSTSEC-2026-0038", "rssn")}
        transport = self.fake_transport(mapping)
        execute_live(self.root, transport=transport)
        errs = verify_sidecar_hashes(self.root)
        self.assertEqual(errs, [])


class TestEcosystemNormalization(unittest.TestCase):
    def test_pypi_pip_exact_mapping(self):
        self.assertEqual(normalize_ecosystem("PyPI"), normalize_ecosystem("pip"))
        self.assertNotEqual(normalize_ecosystem("PyPI"), "PyPI")

    def test_npm_unchanged(self):
        self.assertEqual(normalize_ecosystem("npm"), "npm")

    def test_no_unrelated_aliases(self):
        self.assertEqual(normalize_ecosystem("crates.io"), "crates.io")
        self.assertNotEqual(normalize_ecosystem("pypi"), normalize_ecosystem("pip"))
        self.assertFalse(ecosystems_match("npm", "PyPI"))


class TestGithubFiniteBoundConservative(unittest.TestCase):
    def test_accepts_examples(self):
        for v in ("< 1.2.2", "<= 0.63.0", ">= 1.1.0, <= 1.8.3", "= 1.2.3"):
            self.assertTrue(github_finite_bound_conservative(v), msg=v)

    def test_rejects_examples(self):
        for v in ("", "*", ">= 0", ">= 1.0.0"):
            self.assertFalse(github_finite_bound_conservative(v), msg=v)


class TestK1cReconciliation(CaptureTestCase):
    def _write_capture(self, cap_id: str, body: bytes, spec: CaptureSpec) -> None:
        cdir = self.root / "captures" / cap_id
        cdir.mkdir(parents=True, exist_ok=True)
        (cdir / "raw.json").write_bytes(body)
        resp = FakeResponse(200, {"content-type": "application/json"},
                            body, spec.capture_url, [spec.capture_url])
        sc = build_capture_sidecar(spec, "planhash", resp, body)
        (cdir / "sidecar.json").write_text(canonical_json(sc) + "\n")

    def _minimal_k1_tree(self) -> None:
        """Build minimal artifact tree for reconcile (12 captures + QA stubs)."""
        self.root.mkdir(parents=True)
        plan = build_plan(self.root)
        (self.root / "plan.json").write_text(canonical_json(plan) + "\n")
        (self.root / "promotion_ledger.json").write_text("{}\n")
        (self.root / "capture_report.json").write_text(
            canonical_json({"capture_verdicts": {}, "qa_qualifies": {
                "qaA-enum-map": False}}) + "\n")

        for spec in QA_ATTEMPTS:
            qdir = self.root / "qualification" / spec.capture_id
            qdir.mkdir(parents=True)
            body = osv_body(spec.record_id, spec.package_expected)
            (qdir / "raw.json").write_bytes(body)
            resp = FakeResponse(200, {}, body, spec.capture_url, [spec.capture_url])
            sc = build_qa_sidecar(spec, plan["plan_sha256"], resp, body)
            (qdir / "sidecar.json").write_text(canonical_json(sc) + "\n")

        for i in range(1, 7):
            cap_id = f"capA-0{i}"
            if cap_id in ("capA-01", "capA-03", "capA-05", "capA-06"):
                qa = {"capA-01": "qaA-lru", "capA-03": "qaA-memmap2",
                      "capA-05": "qaA-quinn-proto",
                      "capA-06": "qaA-hpke-rs-rust-crypto"}[cap_id]
                qspec = next(s for s in QA_ATTEMPTS if s.capture_id == qa)
                body = (self.root / "qualification" / qa / "raw.json").read_bytes()
                cdir = self.root / "captures" / cap_id
                cdir.mkdir(parents=True)
                (cdir / "raw.json").write_bytes(body)
                resp = FakeResponse(200, {}, body, qspec.capture_url, [qspec.capture_url])
                sc = build_qa_sidecar(qspec, plan["plan_sha256"], resp, body)
                sc["capture_id"] = cap_id
                sc["oracle_id"] = f"efc-calibration-{cap_id}"
                sc["capture_verdict"] = "pass"
                (cdir / "sidecar.json").write_text(canonical_json(sc) + "\n")
            else:
                spec = next(s for s in CANONICAL_CAPTURES if s.capture_id == cap_id)
                body = osv_body(spec.record_id, spec.package_expected)
                self._write_capture(cap_id, body, spec)

        for spec in CANONICAL_CAPTURES:
            if spec.capture_id.startswith("capB"):
                eco = "pip" if spec.ecosystem_expected == "PyPI" else spec.ecosystem_expected
                body = github_body(spec.record_id, spec.package_expected, eco,
                                   "<= 9.9.9", pub="2026-06-01T00:00:00Z")
                self._write_capture(spec.capture_id, body, spec)

    def test_reconciliation_flips_pypi_pip_only(self):
        self._minimal_k1_tree()
        with mock.patch("urllib.request.urlopen") as urlopen:
            out = reconcile_k1(self.root)
            urlopen.assert_not_called()
        flipped = [r for r in out["rows"]
                   if r["original_verdict"] == "fail"
                   and r["reconciled_verdict"] == "pass"]
        self.assertEqual(len(flipped), 3)
        self.assertEqual(out["family_b_pass_count"], 6)

    def test_true_failure_stays_failed(self):
        data = json.loads(github_body("GHSA-pmch-g965-grmr", "wrong-pkg", "pip",
                                      "<= 1.0", pub="2026-06-01T00:00:00Z"))
        spec = CANONICAL_CAPTURES[3]
        v, fails = validate_capture_reconciled(
            spec.record_id, spec.package_expected, spec.ecosystem_expected,
            spec.capture_url, data, True, None)
        self.assertEqual(v, "fail")
        self.assertIn("package_mismatch", fails)

    def test_reconcile_refuses_changed_raw(self):
        self._minimal_k1_tree()
        raw_path = self.root / "captures" / "capB-02" / "raw.json"
        raw_path.write_bytes(raw_path.read_bytes() + b" ")
        with self.assertRaises(CaptureRefusal):
            reconcile_k1(self.root)

    def test_reconcile_refuses_changed_sidecar(self):
        self._minimal_k1_tree()
        pins = _pin_original_hashes(self.root)
        sc_path = self.root / "captures" / "capB-02" / "sidecar.json"
        sc_path.write_text(sc_path.read_text() + " ")
        with self.assertRaises(CaptureRefusal):
            _verify_pinned_hashes(self.root, pins)

    def test_reconcile_create_once(self):
        self._minimal_k1_tree()
        reconcile_k1(self.root)
        with self.assertRaises(CaptureRefusal):
            reconcile_k1(self.root)

    def test_original_bytes_unchanged_after_reconcile(self):
        self._minimal_k1_tree()
        before = {p: p.read_bytes()
                  for p in self.root.rglob("raw.json")
                  if "qualification" in str(p) or "captures" in str(p)}
        reconcile_k1(self.root)
        for p, data in before.items():
            self.assertEqual(p.read_bytes(), data)


@unittest.skipUnless(K1_ROOT.exists(), "live K1 artifacts not present")
class TestK1cLiveArtifacts(unittest.TestCase):
    def test_live_reconcile_if_not_done(self):
        if (K1_ROOT / "normalization_amendment.json").exists():
            return
        with mock.patch("urllib.request.urlopen") as urlopen:
            out = reconcile_k1(K1_ROOT)
            urlopen.assert_not_called()
        self.assertEqual(out["family_a_pass_count"], 6)
        self.assertEqual(out["family_b_pass_count"], 6)


if __name__ == "__main__":
    unittest.main()
