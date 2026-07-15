"""P2 production calibration authority + execution surface — offline only.

Two disclosed test seams (wire material, AGENTS.md standing rule):

- Authority tests run against the REAL tree and prove the two structural
  refusals (missing world-oracle scorer; missing A-lane population
  bindings). The mintable-authority tests emulate exactly those two pending
  repairs — a synthetic scorer artifact at a patched path and a no-op
  coverage gate — every OTHER binding (C4d pin, manifest, packet, P1 prior,
  decoding, budget, collapse contract) is the real chain.
- Execution tests exercise the production runner's phase machinery (call
  cardinality, conditional T=0.7 pass, namespace separation, transport
  stop, append-only outputs, verdict computation) with mock sessions and a
  fictional wire comparison rule injected through a patched bindings
  loader, because the REAL production comparison contract cannot serve the
  A-lane irrelevant fixtures until finding 2 is repaired. The pinned
  collapse detector, packet bytes, manifest bytes, and P1 prior are real.
"""

from __future__ import annotations

import contextlib
import json
import shutil
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import harness.efc_calibration_contact as cc
from harness import efc_contracts as c
from harness import efc_pin_c4d as c4d
from harness.efc_check import (ProvenanceRecord, ProvenanceStore,
                               WireComparisonRule)
from harness.efc_collapse_production import (
    production_collapse_contract_hash)
from harness.efc_controller import EngineResult
from harness.efc_packet import load_packet
from harness.efc_probe_contact import (ProbeContactError,
                                       run_production_ignorance_probes)
from harness.efc_runner import (ContactAuthorization, RunnerContractError,
                                TransportRefusal, WireContactAuthorization,
                                run_admission_branch)
from tests.efc_wire_fixtures import (MockSession, constant_session_factory,
                                     mock_session_factory)

ROOT = Path(__file__).resolve().parents[1]


class _RefusingSocket(socket.socket):
    def __init__(self, *a, **k):
        raise AssertionError("calibration test attempted a network call")


class SocketRefusalMixin:
    @classmethod
    def setUpClass(cls):
        cls._real_socket = socket.socket
        socket.socket = _RefusingSocket

    @classmethod
    def tearDownClass(cls):
        socket.socket = cls._real_socket


def _packet_fixture_ids() -> list[str]:
    index = json.loads(
        (ROOT / "episodes/efc_calibration/packet_index.json").read_text())
    return sorted(e["id"] for e in index["entries"]
                  if e["role"] in ("s_family", "analog"))


def _synthetic_scorer_doc() -> dict:
    return {
        "schema_version": cc.WORLD_ORACLE_SCORER_SCHEMA,
        "fictional_test_material": True,
        "rules": {fid: {"pass_when": {"all_of": ["fictional"]}}
                  for fid in _packet_fixture_ids()},
    }


@contextlib.contextmanager
def emulated_repairs(scorer_doc: dict | None = None):
    """Emulate exactly the two pending repairs (findings 1 and 2)."""
    box = Path(tempfile.mkdtemp(prefix="efc-p2-scorer-"))
    try:
        scorer_path = box / "world_oracle_answer_key.json"
        scorer_path.write_text(json.dumps(
            scorer_doc if scorer_doc is not None else _synthetic_scorer_doc(),
            indent=1, sort_keys=True) + "\n", encoding="utf-8")
        with patch.object(cc, "WORLD_ORACLE_SCORER_REL", str(scorer_path)), \
                patch.object(cc, "_check_population_coverage",
                             lambda contract, packet: None):
            yield scorer_path
    finally:
        shutil.rmtree(box, ignore_errors=True)


def _forged_auth(**overrides) -> cc.CalibrationContactAuthorization:
    base = dict(
        packet_id="forged", packet_index_sha256="0" * 64,
        manifest_sha256="0" * 64, check_contract_sha256="0" * 64,
        collapse_detector_id="answer_only_detector",
        collapse_detector_contract_sha256="0" * 64,
        model_id="openai/gpt-oss-20b", decoding_contract_id="forged",
        foreground_template_sha256="0" * 64, part_i_spec_sha256="0" * 64,
        branch="local")
    base.update(overrides)
    return cc.CalibrationContactAuthorization(**base)


# ---------------------------------------------------------------------------
# Authority: real-tree refusals and the emulated-repair mint chain.
# ---------------------------------------------------------------------------

class TestAuthorityRealTree(SocketRefusalMixin, unittest.TestCase):

    def test_mint_refuses_on_population_coverage_gap(self):
        for branch in ("local", "api"):
            with self.assertRaises(cc.CalibrationContactError) as ctx:
                cc.authorize_calibration_contact(branch)
            self.assertIn("P2 structural finding 2", str(ctx.exception))
            self.assertIn("ir-01", str(ctx.exception))

    def test_mint_refuses_on_missing_world_oracle_scorer(self):
        with patch.object(cc, "_check_population_coverage",
                          lambda contract, packet: None):
            with self.assertRaises(cc.CalibrationContactError) as ctx:
                cc.authorize_calibration_contact("local")
        self.assertIn("P2 structural finding 1", str(ctx.exception))
        self.assertIn(cc.WORLD_ORACLE_SCORER_SCHEMA, str(ctx.exception))

    def test_unknown_branch_refuses(self):
        with self.assertRaises(cc.CalibrationContactError):
            cc.authorize_calibration_contact("both")


class TestAuthorityEmulatedRepairs(SocketRefusalMixin, unittest.TestCase):

    def test_mint_succeeds_and_binds_the_real_chain(self):
        with emulated_repairs() as scorer_path:
            for branch, recovered in (("local", 0), ("api", 3)):
                auth = cc.authorize_calibration_contact(branch)
                self.assertEqual(auth.branch, branch)
                self.assertEqual(auth.model_id, cc.BRANCH_MODEL[branch])
                self.assertEqual(auth.pin_event_id,
                                 c4d.SUPERSEDING_EVENT_ID)
                self.assertEqual(auth.check_contract_sha256,
                                 cc.CHECK_CONTRACT_SHA)
                self.assertEqual(auth.collapse_detector_contract_sha256,
                                 production_collapse_contract_hash(ROOT))
                self.assertEqual(auth.p1_recovered, recovered)
                self.assertEqual(auth.p1_n, 15)
                self.assertEqual(auth.p1_ignorance_gate_verdict,
                                 "ignorance_gate_pass")
                self.assertEqual(auth.calibration_k, 5)
                self.assertEqual(auth.temperature_primary, 0.5)
                self.assertEqual(auth.temperature_diagnostic, 0.7)
                self.assertGreater(auth.remaining_branch_budget_tokens, 0)
                self.assertGreaterEqual(
                    auth.remaining_branch_budget_tokens,
                    auth.primary_budget_tokens
                    + auth.conditional_budget_tokens)
                self.assertEqual(auth.roster_total_budget_tokens, 1187522)
                self.assertFalse(auth.consumed)
                self.assertEqual(
                    auth.world_oracle_scorer_sha256,
                    __import__("hashlib").sha256(
                        scorer_path.read_bytes()).hexdigest())

    def test_scorer_schema_refusals(self):
        good = _synthetic_scorer_doc()
        bad_version = dict(good, schema_version="wrong")
        missing_fixture = json.loads(json.dumps(good))
        missing_fixture["rules"].popitem()
        empty_positive = json.loads(json.dumps(good))
        first = next(iter(empty_positive["rules"]))
        empty_positive["rules"][first] = {"pass_when": {"none_of": ["x"]}}
        for doc in (bad_version, missing_fixture, empty_positive):
            with emulated_repairs(doc):
                with self.assertRaises(cc.CalibrationContactError):
                    cc.authorize_calibration_contact("local")

    def test_scorer_evaluator_semantics(self):
        rules = {"fx": {"pass_when": {"all_of": ["alpha", "beta"],
                                      "any_of": ["gamma", "delta"],
                                      "none_of": ["omega"]}}}
        score = cc.make_world_oracle_score(rules)
        fixture = {"task_id": "fx"}
        self.assertTrue(score(fixture, "Alpha then BETA and gamma.")["passed"])
        self.assertFalse(score(fixture, "alpha gamma only-half")["passed"])
        self.assertFalse(score(fixture, "alpha beta no-anyof")["passed"])
        self.assertFalse(
            score(fixture, "alpha beta gamma omega")["passed"])
        with self.assertRaises(cc.CalibrationContactError):
            score({"task_id": "unknown"}, "text")

    def test_single_use_semantics(self):
        with emulated_repairs():
            auth = cc.authorize_calibration_contact("local")
        auth.mark_consumed()
        with self.assertRaises(cc.CalibrationContactError):
            auth.mark_consumed()
        with self.assertRaises(cc.CalibrationContactError):
            cc._reject_non_authority(auth)


class TestP1PriorBinding(SocketRefusalMixin, unittest.TestCase):

    def _p1_sandbox(self) -> Path:
        box = Path(tempfile.mkdtemp(prefix="efc-p2-p1-"))
        self.addCleanup(shutil.rmtree, box, ignore_errors=True)
        src = ROOT / cc.P1_RUN_ROOT_REL
        dst = box / cc.P1_RUN_ROOT_REL
        shutil.copytree(src, dst)
        return box

    def test_real_p1_prior_binds(self):
        prior = cc._load_p1_prior(ROOT, "local")
        self.assertEqual(prior["recovered"], 0)
        prior = cc._load_p1_prior(ROOT, "api")
        self.assertEqual(prior["recovered"], 3)

    def test_stale_or_tampered_p1_label_refuses(self):
        box = self._p1_sandbox()
        correction = (box / cc.P1_RUN_ROOT_REL
                      / "ignorance_gate_result.json")
        doc = json.loads(correction.read_text())
        doc["branches"]["local"]["ignorance_gate_verdict"] = \
            "engine_admitted"
        correction.write_text(json.dumps(doc, indent=1, sort_keys=True)
                              + "\n")
        with self.assertRaises(cc.CalibrationContactError) as ctx:
            cc._load_p1_prior(box, "local")
        self.assertIn("never authority", str(ctx.exception))

    def test_tampered_sidecar_refuses(self):
        box = self._p1_sandbox()
        sidecar = (box / cc.P1_RUN_ROOT_REL / "local"
                   / "probe_sidecar.jsonl")
        rows = sidecar.read_text().splitlines()
        row = json.loads(rows[0])
        row["recovered"] = True
        rows[0] = json.dumps(row, sort_keys=True, separators=(",", ":"))
        sidecar.write_text("\n".join(rows) + "\n")
        with self.assertRaises(cc.CalibrationContactError):
            cc._load_p1_prior(box, "local")

    def test_missing_correction_refuses(self):
        box = self._p1_sandbox()
        (box / cc.P1_RUN_ROOT_REL / "ignorance_gate_result.json").unlink()
        with self.assertRaises(cc.CalibrationContactError):
            cc._load_p1_prior(box, "local")


class TestAuthorityRejection(SocketRefusalMixin, unittest.TestCase):

    def test_non_authority_objects_refuse(self):
        wire = WireContactAuthorization(
            packet_id="w", packet_index_sha256="0" * 64,
            manifest_sha256="0" * 64, wire_rule_id="r",
            wire_rule_contract_sha256="0" * 64, detector_id="d",
            detector_contract_sha256="0" * 64,
            foreground_template_sha256="0" * 64,
            part_i_spec_sha256="0" * 64)
        bare = ContactAuthorization(
            packet_id="b", packet_index_sha256="0" * 64,
            manifest_sha256="0" * 64, check_contract_sha256="0" * 64,
            collapse_detector_id="d",
            collapse_detector_contract_sha256="0" * 64,
            model_id="m", decoding_contract_id="dc",
            foreground_template_sha256="0" * 64,
            part_i_spec_sha256="0" * 64)
        out = Path(tempfile.mkdtemp(prefix="efc-p2-out-"))
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        for bad in ({"i": "am a dict"}, wire, bare):
            with self.assertRaises(cc.CalibrationContactError):
                cc.run_production_calibration_branch(bad, out / "x")

    def test_forged_authority_refuses_and_is_consumed(self):
        forged = _forged_auth()
        out = Path(tempfile.mkdtemp(prefix="efc-p2-out-"))
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        with self.assertRaises(cc.CalibrationContactError):
            cc.run_production_calibration_branch(forged, out / "x")
        self.assertTrue(forged.consumed)
        with self.assertRaises(cc.CalibrationContactError):
            cc.run_production_calibration_branch(forged, out / "y")

    def test_probe_surface_rejects_calibration_authority(self):
        with self.assertRaises(ProbeContactError):
            run_production_ignorance_probes(
                _forged_auth(), {}, {}, Path("/nonexistent"))

    def test_wire_era_admission_surface_still_refuses(self):
        packet = _load_real_packet_with_wire_rule()[0]
        with self.assertRaises(RunnerContractError):
            run_admission_branch(packet, mock_session_factory,
                                 lambda f, a: {"passed": True},
                                 None, lambda p, a: False, _forged_auth())


# ---------------------------------------------------------------------------
# Execution machinery (disclosed wire seam; see module docstring).
# ---------------------------------------------------------------------------

def _load_real_packet_with_wire_rule():
    """Real packet bytes, fictional wire comparison rule for pairing and
    check execution (finding 2 blocks the real production contract)."""
    records, verdicts = [], {}
    for path in sorted((ROOT / cc.ORACLE_ROOT_REL).glob("*.json")):
        if path.name in ("probe_answer_key.json",
                         "world_oracle_answer_key.json"):
            continue
        payload = json.loads(path.read_text())
        records.append(ProvenanceRecord(
            oracle_id=str(payload["oracle_id"]),
            source_reference=str(payload["source_reference"]),
            authoritative_scope=str(payload["authoritative_scope"]),
            cited_text=str(payload["cited_text"]),
            raw_sha256=str(payload["raw_sha256"])))
        verdicts[str(payload["authoritative_scope"])] = bool(
            payload["expected_scope_matches"])
    store = ProvenanceStore(records)
    rule = WireComparisonRule(
        rule_id="p2_test_wire_lookup",
        contract={"rule_id": "p2_test_wire_lookup", "fictional": True,
                  "semantics": "test-only oracle-expected lookup; never a "
                               "production rule"},
        compare=lambda auth, dec: verdicts[auth])
    packet = load_packet(ROOT / cc.PACKET_ROOT_REL, store, rule)
    assert packet.ok, packet.failures
    return packet, store, rule


def _fake_bindings():
    packet, store, rule = _load_real_packet_with_wire_rule()
    manifest = json.loads((ROOT / "corpus/efc_calibration/authoring_c4/"
                           "C4_candidate_calibration_manifest.json"
                           ).read_text())
    return {"packet": packet, "manifest": manifest, "store": store,
            "contract": rule,
            "scorer_rules": _synthetic_scorer_doc()["rules"]}


@contextlib.contextmanager
def execution_seam():
    with emulated_repairs():
        auth = cc.authorize_calibration_contact("local")
    bindings = _fake_bindings()
    with patch.object(cc, "_load_calibration_bindings",
                      lambda root: bindings), \
            patch.object(cc, "_verify_authorization_bindings",
                         lambda auth, root: None):
        yield auth


class _TransportFailingSession(MockSession):
    def __call__(self, prompt: str) -> EngineResult:
        raise TransportRefusal("fictional transport failure")


class TestExecutionMachinery(SocketRefusalMixin, unittest.TestCase):

    def _out(self) -> Path:
        box = Path(tempfile.mkdtemp(prefix="efc-p2-run-"))
        self.addCleanup(shutil.rmtree, box, ignore_errors=True)
        return box / "branch"

    def test_primary_board_cardinality_and_outputs(self):
        with execution_seam() as auth:
            out = self._out()
            result = cc.run_production_calibration_branch(
                auth, out, session_factory=mock_session_factory)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["invocations"], 105)
        self.assertEqual(result["new_probe_calls"], 0)
        self.assertTrue(result["p1_prior_imported"])
        self.assertIn(result["engine_admission_verdict"],
                      c.ENGINE_ADMISSION_VERDICTS)
        self.assertFalse(result["collapse"]["collapsed_at_t05"])
        self.assertTrue((out / cc.PRIMARY_ROWS_NAME).is_file())
        self.assertFalse((out / cc.T07_ROWS_NAME).exists())
        self.assertTrue(auth.consumed)
        # P1 prior rides the verdict evidence
        self.assertEqual(result["probe_sidecar_canonical_sha256"],
                         auth.p1_sidecar_canonical_sha256)
        # no plaintext answers in any persisted row
        text = (out / cc.PRIMARY_ROWS_NAME).read_text()
        self.assertNotIn("fictional-wire-answer", text)

    def test_conditional_t07_pass_runs_once_in_own_namespace(self):
        with execution_seam() as auth:
            out = self._out()
            result = cc.run_production_calibration_branch(
                auth, out,
                session_factory=constant_session_factory(
                    collapse_at_t07=True))
        self.assertEqual(result["invocations"], 210)
        self.assertTrue(result["collapse"]["collapsed_at_t05"])
        self.assertTrue(result["collapse"]["collapsed_at_t07"])
        self.assertEqual(result["engine_admission_verdict"],
                         "point_mode_diagnostic")
        t07 = (out / cc.T07_ROWS_NAME).read_text().splitlines()
        self.assertTrue(t07)
        for line in t07:
            self.assertTrue(json.loads(line)["event_id"].startswith("t07."))
        primary = (out / cc.PRIMARY_ROWS_NAME).read_text().splitlines()
        for line in primary:
            self.assertFalse(
                json.loads(line)["event_id"].startswith("t07."))

    def test_t07_diversity_clears_point_mode(self):
        with execution_seam() as auth:
            result = cc.run_production_calibration_branch(
                auth, self._out(),
                session_factory=constant_session_factory(
                    collapse_at_t07=False))
        self.assertEqual(result["invocations"], 210)
        self.assertTrue(result["collapse"]["collapsed_at_t05"])
        self.assertFalse(result["collapse"]["collapsed_at_t07"])
        self.assertNotEqual(result["engine_admission_verdict"],
                            "point_mode_diagnostic")

    def test_transport_failure_terminates_branch_without_retry(self):
        calls = {"n": 0}

        def factory(temperature: float):
            calls["n"] += 1
            if calls["n"] >= 3:
                return _TransportFailingSession(temperature)
            return MockSession(temperature)

        with execution_seam() as auth:
            out = self._out()
            result = cc.run_production_calibration_branch(
                auth, out, session_factory=factory)
        self.assertEqual(result["status"], "branch_refused_transport")
        self.assertEqual(result["invocations"], 3)
        self.assertEqual(result["engine_admission_verdict"], "not_engaged")
        self.assertTrue(result["refused"])
        self.assertTrue((out / cc.RESULT_NAME).is_file())

    def test_append_only_output_refusal(self):
        with execution_seam() as auth:
            out = self._out()
            cc.run_production_calibration_branch(
                auth, out, session_factory=mock_session_factory)
        with execution_seam() as auth2:
            with self.assertRaises(cc.CalibrationContactError):
                cc.run_production_calibration_branch(
                    auth2, out, session_factory=mock_session_factory)


class TestTransportShapes(SocketRefusalMixin, unittest.TestCase):

    def test_request_bodies_match_p0a_surfaces(self):
        local = cc.build_calibration_request_body(
            "local", "openai/gpt-oss-20b", "PROMPT", 0.5)
        self.assertEqual(local, {
            "model": "openai/gpt-oss-20b",
            "messages": [{"role": "user", "content": "PROMPT"}],
            "temperature": 0.5, "top_p": 1.0, "max_tokens": 2048,
            "stream": False})
        api = cc.build_calibration_request_body(
            "api", "gpt-5.4-2026-03-05", "PROMPT", 0.7)
        self.assertEqual(api, {
            "model": "gpt-5.4-2026-03-05",
            "input": [{"role": "user", "content": "PROMPT"}],
            "reasoning": {"effort": "none"}, "temperature": 0.7,
            "max_output_tokens": 2048, "store": False, "stream": False,
            "top_p": 1.0})

    def test_unpinned_temperature_refuses(self):
        with self.assertRaises(cc.CalibrationContactError):
            cc.build_calibration_request_body(
                "local", "openai/gpt-oss-20b", "PROMPT", 1.0)

    def test_missing_usage_is_a_transport_refusal(self):
        with self.assertRaises(TransportRefusal):
            cc._extract_usage("local", {"usage": {}})
        self.assertEqual(cc._extract_usage(
            "api", {"usage": {"input_tokens": 3, "output_tokens": 4}}),
            (3, 4))


class TestCliAndReport(SocketRefusalMixin, unittest.TestCase):

    def test_cli_refusals(self):
        self.assertEqual(cc.main([]), 2)
        self.assertEqual(cc.main(["--contact"]), 2)
        out = Path(tempfile.mkdtemp(prefix="efc-p2-cli-"))
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        # real tree: refused fail-closed (finding 2), zero network
        self.assertEqual(cc.main(["--contact", "--branch", "local",
                                  "--output-dir", str(out / "x")]), 1)

    def test_report_payload_binds_current_bytes(self):
        payload = cc.implementation_report_payload(ROOT)
        self.assertFalse(payload["authorizes_calibration_contact"])
        self.assertEqual(
            payload["future_contact_commands"][0]["max_real_calls"], 210)
        findings = payload["structural_findings_blocking_contact"]
        self.assertEqual(len(findings), 2)

    def test_production_report_file_matches_current_bytes(self):
        """P1b regression pattern: the on-disk report's embedded hashes must
        equal current file hashes."""
        path = ROOT / cc.P2_REPORT_REL
        self.assertTrue(path.is_file(),
                        "P2 implementation report not yet written")
        doc = json.loads(path.read_text())
        for rel, want in {**doc["module_sha256"],
                          **doc["test_sha256"],
                          **doc["modified_shared_modules_sha256"]}.items():
            got = __import__("hashlib").sha256(
                (ROOT / rel).read_bytes()).hexdigest()
            self.assertEqual(got, want, rel)


if __name__ == "__main__":
    unittest.main()
