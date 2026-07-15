"""P0 production ignorance-probe surface — offline wire tests only."""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import shutil
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness import efc_pin_c4b as c4b
from harness import efc_pin_c4d as c4d
from harness.efc_controller import EngineResult
from harness.efc_probe_contact import (
    BRANCH_API,
    BRANCH_LOCAL,
    P1_RUN_ROOT_REL,
    PROBE_COUNT,
    PROBE_TEMPERATURE,
    ProbeBranchResult,
    ProbeContactAuthorization,
    ProbeContactError,
    ProductionProbeTransport,
    VERDICT_ENGINE_REFUSED,
    VERDICT_IGNORANCE_GATE_PASS,
    VERDICT_NOT_ENGAGED,
    authorize_probe_contact,
    build_ignorance_gate_correction,
    build_probe_request_body,
    implementation_report_payload,
    main,
    p1a_correction_report_payload,
    run_production_ignorance_probes,
    score_probe_answer,
    sha256_canon,
    write_ignorance_gate_correction,
    write_implementation_report,
    write_p1a_correction_report,
)
from harness.efc_runner import (ContactAuthorization, RunnerContractError,
                                TransportRefusal, WireContactAuthorization,
                                run_admission_branch)
from tests.efc_wire_fixtures import (default_store, mock_oracle,
                                     mock_probe_scorer, mock_session_factory)

ROOT = Path(__file__).resolve().parents[1]


class _RefusingSocket(socket.socket):
    def __init__(self, *a, **k):
        raise AssertionError("probe-contact test attempted a network call")


class SocketRefusalMixin:
    @classmethod
    def setUpClass(cls):
        cls._real_socket = socket.socket
        socket.socket = _RefusingSocket

    @classmethod
    def tearDownClass(cls):
        socket.socket = cls._real_socket


def _bindings():
    from harness.efc_probe_contact import _load_probe_bindings
    return _load_probe_bindings(ROOT)


@dataclasses.dataclass
class FakeLease:
    isolation_id: str
    used: bool = False


class FakeTransport:
    def __init__(self, answers: dict[str, str] | None = None,
                 fail_at: str | None = None):
        self._answers = answers or {}
        self._fail_at = fail_at
        self._n = 0
        self.bodies: list[dict] = []
        self.leases: list[FakeLease] = []

    def fresh_lease(self, temperature: float) -> FakeLease:
        self._n += 1
        lease = FakeLease(isolation_id=f"fake-{self._n}")
        self.leases.append(lease)
        return lease

    def invoke(self, lease: FakeLease, request_body: dict) -> str:
        lease.used = True
        self.bodies.append(copy.deepcopy(request_body))
        probe_text = None
        if "messages" in request_body:
            probe_text = request_body["messages"][0]["content"]
        elif "input" in request_body:
            probe_text = request_body["input"][0]["content"]
        for probe_id, text in self._bindings_texts().items():
            if text == probe_text:
                if self._fail_at == probe_id:
                    raise TransportRefusal(f"injected failure at {probe_id}")
                return self._answers.get(probe_id, "unknown answer")
        return "unknown answer"

    def _bindings_texts(self) -> dict[str, str]:
        return _bindings()["probe_texts"]


class TestAuthorize(SocketRefusalMixin, unittest.TestCase):
    def test_authorize_local_and_api(self):
        for branch in (BRANCH_LOCAL, BRANCH_API):
            auth = authorize_probe_contact(branch, ROOT)
            self.assertFalse(auth.consumed)
            self.assertEqual(auth.pin_event_id, c4d.SUPERSEDING_EVENT_ID)
            self.assertEqual(len(auth.probe_fixture_ids), PROBE_COUNT)

    def test_dict_wire_and_admission_authority_refused(self):
        for bad in ({}, WireContactAuthorization(
                packet_id="x", packet_index_sha256="a" * 64,
                manifest_sha256="b" * 64, wire_rule_id="w",
                wire_rule_contract_sha256="c" * 64,
                detector_id="d", detector_contract_sha256="e" * 64,
                foreground_template_sha256="f" * 64,
                part_i_spec_sha256="g" * 64),
                    ContactAuthorization(
                        packet_id="x", packet_index_sha256="a" * 64,
                        manifest_sha256="b" * 64,
                        check_contract_sha256="c" * 64,
                        collapse_detector_id="d",
                        collapse_detector_contract_sha256="e" * 64,
                        model_id="m", decoding_contract_id="d",
                        foreground_template_sha256="f" * 64,
                        part_i_spec_sha256="g" * 64)):
            with self.subTest(type=type(bad).__name__):
                with self.assertRaises(ProbeContactError):
                    run_production_ignorance_probes(
                        bad, {}, {}, Path(tempfile.mkdtemp()))

    def test_forged_authorization_refused(self):
        good = authorize_probe_contact(BRANCH_LOCAL, ROOT)
        forged = dataclasses.replace(good, manifest_file_sha256="f" * 64)
        loaded = _bindings()
        with self.assertRaises(ProbeContactError):
            run_production_ignorance_probes(
                forged, loaded["probe_texts"], loaded["answer_key"],
                Path(tempfile.mkdtemp()), transport=FakeTransport())

    def test_reused_authorization_refused(self):
        auth = authorize_probe_contact(BRANCH_LOCAL, ROOT)
        loaded = _bindings()
        out = Path(tempfile.mkdtemp())
        transport = FakeTransport()
        run_production_ignorance_probes(
            auth, loaded["probe_texts"], loaded["answer_key"], out,
            transport=transport)
        with self.assertRaises(ProbeContactError):
            run_production_ignorance_probes(
                auth, loaded["probe_texts"], loaded["answer_key"], out,
                transport=transport)

    def test_admission_surface_rejects_probe_authority(self):
        from harness.efc_packet import load_packet
        from tests.efc_wire_fixtures import token_cover_rule, write_packet
        tmp = Path(tempfile.mkdtemp())
        packet = load_packet(write_packet(tmp / "p"), default_store(),
                             token_cover_rule())
        auth = authorize_probe_contact(BRANCH_LOCAL, ROOT)
        with self.assertRaises(RunnerContractError):
            run_admission_branch(packet, mock_session_factory, mock_oracle,
                                 default_store(), mock_probe_scorer,
                                 authorization=auth)


class TestPinAndBranchTamper(SocketRefusalMixin, unittest.TestCase):
    def test_pin_verify_required(self):
        with patch("harness.efc_probe_contact.c4d.verify",
                   side_effect=c4d.PinRefusal("tampered pin")):
            with self.assertRaises(c4d.PinRefusal):
                authorize_probe_contact(BRANCH_LOCAL, ROOT)

    def test_unknown_branch_refused(self):
        with self.assertRaises(ProbeContactError):
            authorize_probe_contact("bogus", ROOT)


class TestProbeExecution(SocketRefusalMixin, unittest.TestCase):
    def setUp(self):
        self.loaded = _bindings()
        self.auth = authorize_probe_contact(BRANCH_LOCAL, ROOT)
        self.tmp = Path(tempfile.mkdtemp())

    def _answers(self, recovered_ids: set[str]) -> dict[str, str]:
        answers = {}
        for pid in self.loaded["probe_fixture_ids"]:
            tokens = self.loaded["answer_key"][pid]["must_contain"]
            if pid in recovered_ids:
                answers[pid] = " ".join(tokens)
            else:
                answers[pid] = "i do not know"
        return answers

    def test_three_recovered_passes(self):
        recovered = set(self.loaded["probe_fixture_ids"][:3])
        result = run_production_ignorance_probes(
            self.auth, self.loaded["probe_texts"],
            self.loaded["answer_key"], self.tmp,
            transport=FakeTransport(self._answers(recovered)))
        self.assertTrue(result.gate_pass)
        self.assertEqual(result.ignorance_gate_verdict, VERDICT_IGNORANCE_GATE_PASS)
        self.assertEqual(result.recovered_count, 3)
        self.assertEqual(result.n, 15)

    def test_four_recovered_refuses(self):
        recovered = set(self.loaded["probe_fixture_ids"][:4])
        result = run_production_ignorance_probes(
            self.auth, self.loaded["probe_texts"],
            self.loaded["answer_key"], self.tmp,
            transport=FakeTransport(self._answers(recovered)))
        self.assertFalse(result.gate_pass)
        self.assertEqual(result.ignorance_gate_verdict, VERDICT_ENGINE_REFUSED)
        self.assertEqual(result.recovered_count, 4)

    def test_probe_only_never_emits_engine_admitted(self):
        cases = [
            set(),
            set(self.loaded["probe_fixture_ids"][:3]),
            set(self.loaded["probe_fixture_ids"][:4]),
        ]
        for recovered in cases:
            auth = authorize_probe_contact(BRANCH_LOCAL, ROOT)
            out = Path(tempfile.mkdtemp())
            result = run_production_ignorance_probes(
                auth, self.loaded["probe_texts"],
                self.loaded["answer_key"], out,
                transport=FakeTransport(self._answers(recovered)))
            self.assertNotEqual(result.ignorance_gate_verdict, "engine_admitted")
            self.assertIn(result.ignorance_gate_verdict,
                          (VERDICT_IGNORANCE_GATE_PASS, VERDICT_ENGINE_REFUSED))
        fail_id = self.loaded["probe_fixture_ids"][1]
        auth = authorize_probe_contact(BRANCH_LOCAL, ROOT)
        out = Path(tempfile.mkdtemp())
        result = run_production_ignorance_probes(
            auth, self.loaded["probe_texts"],
            self.loaded["answer_key"], out,
            transport=FakeTransport(self._answers(set()), fail_at=fail_id))
        self.assertEqual(result.ignorance_gate_verdict, VERDICT_NOT_ENGAGED)
        self.assertNotEqual(result.ignorance_gate_verdict, "engine_admitted")

    def test_fifteen_fresh_leases(self):
        transport = FakeTransport(self._answers(set()))
        run_production_ignorance_probes(
            self.auth, self.loaded["probe_texts"],
            self.loaded["answer_key"], self.tmp, transport=transport)
        self.assertEqual(len(transport.leases), 15)
        self.assertEqual(len({l.isolation_id for l in transport.leases}), 15)
        self.assertTrue(all(l.used for l in transport.leases))

    def test_prompt_exactness_and_oracle_non_leakage(self):
        transport = FakeTransport(self._answers(set()))
        run_production_ignorance_probes(
            self.auth, self.loaded["probe_texts"],
            self.loaded["answer_key"], self.tmp, transport=transport)
        texts = self.loaded["probe_texts"]
        for body in transport.bodies:
            if "messages" in body:
                content = body["messages"][0]["content"]
                self.assertIn(content, texts.values())
                blob = json.dumps(body)
                for entry in self.loaded["answer_key"].values():
                    for token in entry["must_contain"]:
                        if token not in content:
                            self.assertNotIn(entry["fact"], blob)

    def test_sidecar_excludes_plaintext(self):
        transport = FakeTransport(self._answers(
            {self.loaded["probe_fixture_ids"][0]}))
        run_production_ignorance_probes(
            self.auth, self.loaded["probe_texts"],
            self.loaded["answer_key"], self.tmp, transport=transport)
        sidecar = (self.tmp / "probe_sidecar.jsonl").read_text()
        first = self.loaded["probe_fixture_ids"][0]
        answer = " ".join(self.loaded["answer_key"][first]["must_contain"])
        self.assertNotIn(answer, sidecar)
        self.assertIn("answer_sha256", sidecar)

    def test_transport_failure_no_retry(self):
        fail_id = self.loaded["probe_fixture_ids"][2]
        transport = FakeTransport(self._answers(set()), fail_at=fail_id)
        result = run_production_ignorance_probes(
            self.auth, self.loaded["probe_texts"],
            self.loaded["answer_key"], self.tmp, transport=transport)
        self.assertEqual(result.status, "branch_refused_transport")
        self.assertEqual(result.ignorance_gate_verdict, VERDICT_NOT_ENGAGED)
        self.assertEqual(result.probe_calls, 3)
        self.assertEqual(len(transport.bodies), 3)

    def test_conflicting_output_refused(self):
        transport = FakeTransport(self._answers(set()))
        run_production_ignorance_probes(
            self.auth, self.loaded["probe_texts"],
            self.loaded["answer_key"], self.tmp, transport=transport)
        auth2 = authorize_probe_contact(BRANCH_LOCAL, ROOT)
        with self.assertRaises(ProbeContactError):
            run_production_ignorance_probes(
                auth2, self.loaded["probe_texts"],
                self.loaded["answer_key"], self.tmp, transport=transport)

    def test_exact_local_request_body_shape(self):
        pid = self.loaded["probe_fixture_ids"][0]
        text = self.loaded["probe_texts"][pid]
        sibling = json.loads(
            (ROOT / c4b.SIBLING_REL).read_text(encoding="utf-8"))
        contract = sibling["branches"][BRANCH_LOCAL]["decoding_contract"]
        body = build_probe_request_body(
            BRANCH_LOCAL, self.auth.model_id, text, contract)
        self.assertEqual(body["temperature"], PROBE_TEMPERATURE)
        self.assertEqual(body["top_p"], 1.0)
        self.assertEqual(body["max_tokens"], 2048)
        self.assertEqual(body["messages"], [{"role": "user", "content": text}])
        self.assertNotIn("system", json.dumps(body))


class TestScoring(unittest.TestCase):
    def test_normalized_token_containment(self):
        key = {"p": {"must_contain": ["3.4.0", "2027-03-31"]}}
        self.assertTrue(score_probe_answer("p", "  version 3.4.0 on 2027-03-31 ",
                                           key))
        self.assertFalse(score_probe_answer("p", "3.4", key))


class TestExecutionBinding(SocketRefusalMixin, unittest.TestCase):
    """P0a execute-time probe-text and answer-key identity enforcement."""

    def setUp(self):
        self.loaded = _bindings()
        self.auth = authorize_probe_contact(BRANCH_LOCAL, ROOT)
        self.tmp = Path(tempfile.mkdtemp())

    def test_tampered_probe_text_refused_before_lease(self):
        texts = copy.deepcopy(self.loaded["probe_texts"])
        first = self.loaded["probe_fixture_ids"][0]
        texts[first] = "TAMPERED PROBE TEXT — NOT THE PINNED BYTES"
        transport = FakeTransport()
        with self.assertRaises(ProbeContactError):
            run_production_ignorance_probes(
                self.auth, texts, self.loaded["answer_key"], self.tmp,
                transport=transport)
        self.assertEqual(len(transport.leases), 0)
        self.assertEqual(len(transport.bodies), 0)
        self.assertFalse((self.tmp / "probe_sidecar.jsonl").exists())

    def test_forged_answer_key_refused_before_lease(self):
        forged = {
            pid: {"must_contain": ["___never___"]}
            for pid in self.loaded["probe_fixture_ids"]
        }
        transport = FakeTransport()
        with self.assertRaises(ProbeContactError):
            run_production_ignorance_probes(
                self.auth, self.loaded["probe_texts"], forged, self.tmp,
                transport=transport)
        self.assertEqual(len(transport.leases), 0)
        self.assertFalse((self.tmp / "probe_sidecar.jsonl").exists())

    def test_extra_probe_text_key_refused(self):
        texts = copy.deepcopy(self.loaded["probe_texts"])
        texts["extra-probe-id"] = "unexpected"
        with self.assertRaises(ProbeContactError):
            run_production_ignorance_probes(
                self.auth, texts, self.loaded["answer_key"], self.tmp,
                transport=FakeTransport())

    def test_missing_probe_text_key_refused(self):
        texts = copy.deepcopy(self.loaded["probe_texts"])
        del texts[self.loaded["probe_fixture_ids"][-1]]
        with self.assertRaises(ProbeContactError):
            run_production_ignorance_probes(
                self.auth, texts, self.loaded["answer_key"], self.tmp,
                transport=FakeTransport())

    def test_extra_answer_key_entry_refused(self):
        key = copy.deepcopy(self.loaded["answer_key"])
        key["extra-probe-id"] = {"must_contain": ["x"]}
        with self.assertRaises(ProbeContactError):
            run_production_ignorance_probes(
                self.auth, self.loaded["probe_texts"], key, self.tmp,
                transport=FakeTransport())

    def test_missing_answer_key_entry_refused(self):
        key = copy.deepcopy(self.loaded["answer_key"])
        del key[self.loaded["probe_fixture_ids"][-1]]
        with self.assertRaises(ProbeContactError):
            run_production_ignorance_probes(
                self.auth, self.loaded["probe_texts"], key, self.tmp,
                transport=FakeTransport())

    def test_malformed_answer_key_scoring_refused(self):
        key = copy.deepcopy(self.loaded["answer_key"])
        pid = self.loaded["probe_fixture_ids"][0]
        key[pid] = {"must_contain": []}
        with self.assertRaises(ProbeContactError):
            run_production_ignorance_probes(
                self.auth, self.loaded["probe_texts"], key, self.tmp,
                transport=FakeTransport())

    def test_binding_refusal_consumes_authorization(self):
        texts = copy.deepcopy(self.loaded["probe_texts"])
        texts[self.loaded["probe_fixture_ids"][0]] = "tampered"
        with self.assertRaises(ProbeContactError):
            run_production_ignorance_probes(
                self.auth, texts, self.loaded["answer_key"], self.tmp,
                transport=FakeTransport())
        with self.assertRaises(ProbeContactError):
            run_production_ignorance_probes(
                self.auth, self.loaded["probe_texts"],
                self.loaded["answer_key"], Path(tempfile.mkdtemp()),
                transport=FakeTransport())

    def test_happy_path_unchanged(self):
        transport = FakeTransport()
        result = run_production_ignorance_probes(
            self.auth, self.loaded["probe_texts"],
            self.loaded["answer_key"], self.tmp, transport=transport)
        self.assertEqual(result.probe_calls, 15)
        self.assertEqual(len(transport.leases), 15)


class TestP1aIgnoranceGateCorrection(SocketRefusalMixin, unittest.TestCase):
    P1_ORIGINAL_HASHES = {
        "local/probe_sidecar.jsonl":
            "db172a40163199b271e8b9b88c3867756b7c548ccc5aa0218437089084c04821",
        "local/probe_branch_result.json":
            "ac215d830a83e9f031b5daad51e2822cd329a693d13b946ea4a145a1f1a09c7d",
        "api/probe_sidecar.jsonl":
            "e4c6f8630acebc5f3727bcecc33fa91f292078d97fe6aaa6e27fdbdfaa19609a",
        "api/probe_branch_result.json":
            "a0fb96ec4f094c202bbfde28667e4076227e18c87a0f2e28d3bdd1c917612367",
    }

    def test_build_correction_from_p1_runs(self):
        run_root = ROOT / P1_RUN_ROOT_REL
        if not (run_root / "local" / "probe_sidecar.jsonl").is_file():
            self.skipTest("P1 run artifacts not present locally")
        payload = build_ignorance_gate_correction(ROOT, run_root)
        self.assertEqual(payload["active_pin_event_id"],
                         "efc-cal-manifest-pin-2600d1fdba7b-s2")
        self.assertFalse(payload["authorizes_calibration_contact"])
        self.assertEqual(payload["additional_real_calls"], 0)
        self.assertEqual(payload["branches"]["local"]["recovered_count"], 0)
        self.assertEqual(payload["branches"]["api"]["recovered_count"], 3)
        self.assertEqual(payload["branches"]["local"]["ignorance_gate_verdict"],
                         VERDICT_IGNORANCE_GATE_PASS)
        self.assertEqual(payload["branches"]["api"]["ignorance_gate_verdict"],
                         VERDICT_IGNORANCE_GATE_PASS)
        self.assertEqual(payload["branches"]["local"]["engine_admission_status"],
                         "engine_admission_pending")
        for rel, expected in self.P1_ORIGINAL_HASHES.items():
            path = run_root / rel
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, expected)

    def test_write_correction_preserves_original_run_files(self):
        run_root = ROOT / P1_RUN_ROOT_REL
        if not (run_root / "local" / "probe_sidecar.jsonl").is_file():
            self.skipTest("P1 run artifacts not present locally")
        before = {
            rel: (run_root / rel).read_bytes()
            for rel in self.P1_ORIGINAL_HASHES
        }
        tmp = Path(tempfile.mkdtemp())
        copy_root = tmp / "p1"
        shutil.copytree(
            run_root, copy_root,
            ignore=lambda _d, names: [n for n in names
                                      if n == "ignorance_gate_result.json"])
        write_ignorance_gate_correction(ROOT, copy_root)
        for rel, content in before.items():
            self.assertEqual((run_root / rel).read_bytes(), content)
        result_path = copy_root / "ignorance_gate_result.json"
        self.assertTrue(result_path.is_file())
        doc = json.loads(result_path.read_text(encoding="utf-8"))
        self.assertEqual(doc["branches"]["local"]["recovered_count"], 0)
        self.assertEqual(doc["branches"]["api"]["recovered_count"], 3)

    def test_p1a_report_preserves_p0a_report(self):
        p0_path = ROOT / "corpus/efc_calibration/authoring_c4/p0_probe_contact_implementation_report.json"
        before = p0_path.read_bytes()
        tmp = Path(tempfile.mkdtemp())
        with patch("harness.efc_probe_contact.P1A_REPORT_REL",
                   str(Path(tmp) / "p1a_report.json")):
            payload = write_p1a_correction_report(ROOT)
        self.assertTrue(payload["prior_p0a_report_preserved"])
        self.assertEqual(payload["forbidden_probe_verdict"], "engine_admitted")
        self.assertEqual(p0_path.read_bytes(), before)

    def test_p1a_report_embedded_hashes_match_current_files(self):
        report_path = (ROOT / "corpus/efc_calibration/authoring_c4/"
                       "p1a_ignorance_gate_correction_report.json")
        module_path = ROOT / "harness/efc_probe_contact.py"
        test_path = ROOT / "tests/test_efc_probe_contact.py"
        doc = json.loads(report_path.read_text(encoding="utf-8"))
        module_hash = hashlib.sha256(module_path.read_bytes()).hexdigest()
        test_hash = hashlib.sha256(test_path.read_bytes()).hexdigest()
        self.assertEqual(doc["module_sha256"], module_hash)
        self.assertEqual(doc["test_sha256"], test_hash)
        expected = p1a_correction_report_payload(ROOT)
        self.assertEqual(doc["module_sha256"], expected["module_sha256"])
        self.assertEqual(doc["test_sha256"], expected["test_sha256"])
    def test_write_report_zero_calls(self):
        report_path = ROOT / "corpus/efc_calibration/authoring_c4/p0_probe_contact_implementation_report.json"
        before = report_path.read_bytes()
        tmp = Path(tempfile.mkdtemp())
        try:
            payload = implementation_report_payload(ROOT)
            (tmp / "report.json").write_text(
                json.dumps(payload, indent=1, sort_keys=True) + "\n",
                encoding="utf-8")
            self.assertEqual(payload["disclosure"]["real_inference_calls"], 0)
            self.assertEqual(payload["disclosure"]["network_calls"], 0)
            self.assertEqual(sum(c["max_real_calls"]
                                 for c in payload["future_contact_commands"]), 30)
        finally:
            self.assertEqual(report_path.read_bytes(), before)

    def test_cli_no_arg_refuses(self):
        self.assertEqual(main([]), 2)

    def test_cli_write_report(self):
        with patch("harness.efc_probe_contact.write_implementation_report") as mock_write:
            mock_write.return_value = {
                "disclosure": {"real_inference_calls": 0, "network_calls": 0},
                "future_contact_commands": [{"max_real_calls": 15},
                                            {"max_real_calls": 15}],
            }
            self.assertEqual(main(["--write-report"]), 0)
            mock_write.assert_called_once()


class TestBudgetAndBranchIsolation(SocketRefusalMixin, unittest.TestCase):
    def test_probe_budget_positive(self):
        auth = authorize_probe_contact(BRANCH_LOCAL, ROOT)
        self.assertGreater(auth.probe_budget_tokens, 0)
        self.assertGreaterEqual(auth.roster_total_budget_tokens,
                                auth.probe_budget_tokens)

    def test_branch_isolation(self):
        local = authorize_probe_contact(BRANCH_LOCAL, ROOT)
        api = authorize_probe_contact(BRANCH_API, ROOT)
        self.assertNotEqual(local.decoding_contract_sha256,
                            api.decoding_contract_sha256)
        self.assertNotEqual(local.model_id, api.model_id)


if __name__ == "__main__":
    unittest.main()
