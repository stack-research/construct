"""Offline unit tests for harness.efc_capture_k3."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from harness.efc_capture_k3 import (
    FAMILY_E,
    FAMILY_F,
    FROZEN_ATTEMPTS,
    CaptureRefusal,
    build_plan,
    canonical_json,
    check_create_once,
    dry_run,
    execute_live,
    extract_family_f,
    html_to_text,
    refuse_unknown_url,
    run_attempt,
    sha256_bytes,
    validate_family_e,
    verify_hashes,
    normalize_text,
    K3Spec,
    K3_ROOT,
    MAX_CALLS,
)


@dataclass
class FakeResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]
    redirect_refused: bool = False


def spdx_exception(record_id: str, text: str = "Exception text.") -> bytes:
    return canonical_json({
        "licenseExceptionId": record_id,
        "licenseExceptionText": text,
        "licenseExceptionName": record_id,
        "licenseListVersion": "3.25.0",
    }).encode()


def spdx_license(record_id: str, text: str = "License text.") -> bytes:
    return canonical_json({
        "licenseId": record_id,
        "licenseText": text,
        "licenseName": record_id,
        "licenseListVersion": "3.25.0",
    }).encode()


class K3TestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp) / "k3"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fake_transport(self, mapping: dict[str, bytes], *,
                       status: int = 200,
                       redirect: dict[str, FakeResponse] | None = None):
        calls: list[str] = []

        def transport(url: str) -> FakeResponse:
            calls.append(url)
            if redirect and url in redirect:
                return redirect[url]
            if url not in mapping:
                raise AssertionError(f"unexpected URL: {url}")
            return FakeResponse(
                status=status,
                headers={"content-type": "application/json"},
                body=mapping[url], url=url, redirect_chain=[url],
            )

        transport.calls = calls  # type: ignore[attr-defined]
        return transport


class TestFrozenPlan(K3TestCase):
    def test_ten_entries(self):
        self.assertEqual(len(FROZEN_ATTEMPTS), 10)
        self.assertEqual(len(FAMILY_E), 6)
        self.assertEqual(len(FAMILY_F), 4)

    def test_max_calls_ceiling(self):
        plan = build_plan(self.root)
        self.assertEqual(plan["max_network_calls"], MAX_CALLS)
        self.assertEqual(plan["attempt_count"], 10)

    def test_unknown_url_refused(self):
        with self.assertRaises(CaptureRefusal):
            refuse_unknown_url("https://evil.example/x")

    def test_dry_run_zero_network(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            out = dry_run(self.root)
            urlopen.assert_not_called()
        self.assertEqual(out["network_calls"], 0)


class TestFamilyE(K3TestCase):
    def test_exception_field_separation(self):
        spec = FAMILY_E[0]
        data = json.loads(spdx_exception("Classpath-exception-2.0"))
        v, fails, _ = validate_family_e(spec, data, True, None, False)
        self.assertEqual(v, "pass")
        data["licenseId"] = "BAD"
        v, fails, _ = validate_family_e(spec, data, True, None, False)
        self.assertIn("license_id_on_exception_record", fails)

    def test_license_field_separation(self):
        spec = FAMILY_E[3]
        data = json.loads(spdx_license("BSL-1.0"))
        v, fails, _ = validate_family_e(spec, data, True, None, False)
        self.assertEqual(v, "pass")
        data["licenseExceptionId"] = "BAD"
        v, fails, _ = validate_family_e(spec, data, True, None, False)
        self.assertIn("exception_id_on_license_record", fails)

    def test_empty_text_fails(self):
        spec = FAMILY_E[0]
        data = json.loads(spdx_exception("Classpath-exception-2.0", text="  "))
        v, fails, _ = validate_family_e(spec, data, True, None, False)
        self.assertIn("missing_exception_text", fails)


class TestFamilyFExtractors(unittest.TestCase):
    K8S_HTML = b"""<html><body>
    <h2>Removed APIs by release</h2>
    <h3>v1.32</h3>
    <p>The flowcontrol.apiserver.k8s.io/v1beta3 API version of FlowSchema and
    PriorityLevelConfiguration is no longer served as of v1.32.</p>
    <h3>v1.33</h3><p>other</p></body></html>"""

    DJANGO_HTML = b"""<html><body>
    <h2>Features removed in 5.0</h2>
    <ul><li>Support for pytz timezones is removed.</li></ul>
    </body></html>"""

    FLASK_HTML = b"""<html><body>
    <h2>Version 2.3.0</h2>
    <p>Released 2023-04-25</p>
    <h3>Remove previously deprecated code.</h3>
    <ul><li>The FLASK_ENV environment variable, ENV config key,
    and app.env property are removed.</li></ul>
    </body></html>"""

    RAILS_HTML = b"""<html><body>
    <h1>Ruby on Rails 7.2 Release Notes</h1>
    <h2>Railties</h2>
    <h3>Removals</h3>
    <ul><li>Remove deprecated Rails.config.enable_dependency_loading.</li></ul>
    </body></html>"""

    def test_kubernetes_extractor(self):
        spec = FAMILY_F[0]
        ext, fails = extract_family_f(spec, self.K8S_HTML)
        self.assertEqual(fails, [])
        self.assertEqual(ext["relation"], "no_longer_served")

    def test_django_exact_statement(self):
        spec = FAMILY_F[1]
        ext, fails = extract_family_f(spec, self.DJANGO_HTML)
        self.assertEqual(fails, [])
        self.assertEqual(ext["matched_statement"],
                         "Support for pytz timezones is removed.")

    def test_flask_date_and_statement(self):
        spec = FAMILY_F[2]
        ext, fails = extract_family_f(spec, self.FLASK_HTML)
        self.assertEqual(fails, [])
        self.assertEqual(ext["official_record_date"], "2023-04-25")

    def test_rails_extractor(self):
        spec = FAMILY_F[3]
        ext, fails = extract_family_f(spec, self.RAILS_HTML)
        self.assertEqual(fails, [])
        self.assertIn("Rails.config.enable_dependency_loading",
                      ext["named_surface"])

    def test_wrong_section_fails(self):
        spec = FAMILY_F[1]
        bad = b"<html><body><p>Support for pytz timezones is removed.</p></body></html>"
        _, fails = extract_family_f(spec, bad)
        self.assertIn("missing_bounded_section", fails)

    def test_future_removal_refused(self):
        spec = FAMILY_F[1]
        future = b"""<html><body><h2>Features removed in 5.0</h2>
        <p>Support for pytz timezones will be removed in 6.0.</p></body></html>"""
        _, fails = extract_family_f(spec, future)
        self.assertIn("missing_exact_statement", fails)

    def test_deterministic_normalization(self):
        html = b"<html><body><p>  hello   world </p></body></html>"
        a = normalize_text(html_to_text(html))
        b = normalize_text(html_to_text(html))
        self.assertEqual(a, b)
        self.assertEqual(a, "hello world")


class TestTransportAndCreateOnce(K3TestCase):
    def test_create_once_refusal(self):
        self.root.mkdir(parents=True)
        (self.root / "plan.json").write_text("{}")
        with self.assertRaises(CaptureRefusal):
            check_create_once(self.root)

    def test_one_call_per_url(self):
        mapping = {FAMILY_E[0].capture_url:
                   spdx_exception("Classpath-exception-2.0")}
        transport = self.fake_transport(mapping)
        self.root.mkdir(parents=True)
        plan = build_plan(self.root)
        run_attempt(FAMILY_E[0], transport, self.root, plan["plan_sha256"])
        self.assertEqual(len(transport.calls), 1)  # type: ignore[attr-defined]

    def test_redirect_refused(self):
        spec = FAMILY_F[0]
        redirect = {
            spec.capture_url: FakeResponse(
                301, {"location": "https://other.example/"},
                b"", spec.capture_url, [spec.capture_url, "https://other.example/"],
                redirect_refused=True,
            ),
        }
        transport = self.fake_transport({}, redirect=redirect)
        self.root.mkdir(parents=True)
        plan = build_plan(self.root)
        sc = run_attempt(spec, transport, self.root, plan["plan_sha256"])
        self.assertEqual(sc["capture_verdict"], "fail")
        self.assertIn("redirect_refused", sc["failure_reasons"])

    def test_execute_refuses_second_run(self):
        mapping = {}
        for spec in FAMILY_E:
            mapping[spec.capture_url] = (
                spdx_exception(spec.record_id) if spec.entity_kind == "exception"
                else spdx_license(spec.record_id))
        for spec in FAMILY_F:
            mapping[spec.capture_url] = TestFamilyFExtractors.K8S_HTML
        transport = self.fake_transport(mapping)
        execute_live(self.root, transport=transport)
        with self.assertRaises(CaptureRefusal):
            execute_live(self.root, transport=transport)


class TestFullSyntheticExecute(K3TestCase):
    def test_synthetic_all_pass(self):
        mapping = {}
        for spec in FAMILY_E:
            mapping[spec.capture_url] = (
                spdx_exception(spec.record_id) if spec.entity_kind == "exception"
                else spdx_license(spec.record_id))
        f_html = {
            "capF-01": TestFamilyFExtractors.K8S_HTML,
            "capF-02": TestFamilyFExtractors.DJANGO_HTML,
            "capF-03": TestFamilyFExtractors.FLASK_HTML,
            "capF-04": TestFamilyFExtractors.RAILS_HTML,
        }
        for spec in FAMILY_F:
            mapping[spec.capture_url] = f_html[spec.capture_id]
        transport = self.fake_transport(mapping)
        out = execute_live(self.root, transport=transport)
        self.assertEqual(out["network_calls"], 10)
        self.assertEqual(out["report"]["family_e_pass_count"], 6)
        self.assertEqual(out["report"]["family_f_pass_count"], 4)
        self.assertEqual(verify_hashes(self.root), [])

    def test_sidecar_forbidden_fields(self):
        mapping = {FAMILY_E[0].capture_url:
                   spdx_exception("Classpath-exception-2.0")}
        for spec in FAMILY_E[1:]:
            mapping[spec.capture_url] = (
                spdx_exception(spec.record_id) if spec.entity_kind == "exception"
                else spdx_license(spec.record_id))
        for spec in FAMILY_F:
            mapping[spec.capture_url] = TestFamilyFExtractors.DJANGO_HTML
        transport = self.fake_transport(mapping)
        execute_live(self.root, transport=transport)
        sc = json.loads((self.root / "captures/capE-01/sidecar.json").read_text())
        for forbidden in ("scope_extract", "decision_scope", "expected_action",
                          "fixture_id", "answer"):
            self.assertNotIn(forbidden, sc)


@unittest.skipUnless(K3_ROOT.exists(), "live K3 artifacts not present")
class TestK3LiveArtifacts(unittest.TestCase):
    def test_live_hashes(self):
        errs = verify_hashes(K3_ROOT)
        self.assertEqual(errs, [])


if __name__ == "__main__":
    unittest.main()
