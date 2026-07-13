"""Wire tests: wire/contact split (resolutions A/B), derived pilots + the
computed admission verdict row (C), injected pinned collapse detector with a
namespaced replayable diagnostic ledger (D), probe sidecar + isolation ids
(E/F), runner contract identity (G), orchestrator phases, terminal transport
refusal, fork identity, untrusting replay (sealed §5.3/§8.2/§10.2/§10.5/§13;
design §5/§6/§9)."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from harness import efc_contracts as c
from harness.efc_artifacts import implemented_artifact_identities
from harness.efc_ledger import replay_ledger
from harness.efc_manifest import check_calibration_manifest
from harness.efc_packet import load_packet
from harness.efc_planner import (AnyOf, BinaryPilot, ContrastSpec, OrArm,
                                 Pilots, PlannedGate, resolve_gates)
from harness.efc_runner import (STATUS_BRANCH_REFUSED_TRANSPORT,
                                STATUS_COMPLETED, ContactAuthorization,
                                RunnerContractError, T07_NAMESPACE,
                                TransportRefusal, _OnceGuard,
                                authorize_engine_contact,
                                authorize_wire_contact,
                                derive_pilots_from_runs,
                                run_admission_branch,
                                run_wire_admission_branch,
                                runner_contract_hash,
                                runner_contract_payload)
from tests.efc_wire_fixtures import (MockSession, constant_session_factory,
                                     default_store, exact_equality_rule,
                                     mock_oracle, mock_probe_scorer,
                                     mock_session_factory,
                                     pinned_collapse_detector,
                                     token_cover_rule, wire_manifest,
                                     write_packet)

PROBES = 2       # ids in the wire packet's probe contract
BOARD = 5 * 3 + 15 * 6   # 105


class BranchCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.packet = load_packet(write_packet(Path(self.tmp.name) / "p"),
                                  default_store(), token_cover_rule())
        self.assertTrue(self.packet.ok, msg=str(self.packet.failures))
        self.detector = pinned_collapse_detector()
        self.manifest = wire_manifest(self.packet)
        self.manifest_result = check_calibration_manifest(self.manifest)
        self.assertTrue(self.manifest_result.ok,
                        msg=str(self.manifest_result.failures))
        self.authorization = authorize_wire_contact(
            self.packet, self.manifest, self.manifest_result,
            token_cover_rule(), self.detector)

    def tearDown(self):
        self.tmp.cleanup()

    def run_branch(self, factory=mock_session_factory, **kw):
        return run_wire_admission_branch(
            self.packet, factory, mock_oracle, default_store(),
            kw.pop("wire_rule", token_cover_rule()), mock_probe_scorer,
            wire_authorization=kw.pop("wire_authorization",
                                      self.authorization),
            collapse_detector=kw.pop("collapse_detector", self.detector),
            manifest=kw.pop("manifest", self.manifest), **kw)


class TestContactSurfaceSplit(BranchCase):
    """Resolutions A/B mandated negative tests."""

    def test_arbitrary_dict_cannot_authorize_contact(self):
        # the production surface refuses a mapping
        with self.assertRaises(RunnerContractError) as ctx:
            run_admission_branch(self.packet, mock_session_factory,
                                 mock_oracle, default_store(),
                                 mock_probe_scorer,
                                 authorization={"part_i_spec_hash":
                                                c.PART_I_SPEC_SHA256})
        self.assertIn("never authority", str(ctx.exception))
        # the wire surface refuses a mapping too
        with self.assertRaises(RunnerContractError):
            self.run_branch(wire_authorization={"surface": "wire"})
        # and a bare mapping cannot stand in for the manifest check result
        with self.assertRaises(RunnerContractError):
            authorize_wire_contact(self.packet, self.manifest,
                                   {"ok": True, "manifest_hash": "x"},
                                   token_cover_rule(), self.detector)

    def test_pending_identities_make_production_contact_impossible(self):
        """Resolution A: production authorization refuses unconditionally
        while the check contract and route projection are pending."""
        with self.assertRaises(RunnerContractError) as ctx:
            authorize_engine_contact(self.packet, self.manifest,
                                     self.manifest_result)
        self.assertIn("pending", str(ctx.exception))
        with self.assertRaises(RunnerContractError):
            authorize_engine_contact()
        # even a hand-forged ContactAuthorization cannot run: no production
        # engine adapter exists in this workspace
        forged = ContactAuthorization(
            packet_id="x", packet_index_sha256="a" * 64,
            manifest_sha256="b" * 64, check_contract_sha256="c" * 64,
            collapse_detector_id="d", collapse_detector_contract_sha256="e" * 64,
            model_id="m", decoding_contract_id="d",
            foreground_template_sha256="f" * 64,
            part_i_spec_sha256=c.PART_I_SPEC_SHA256)
        with self.assertRaises(RunnerContractError) as ctx2:
            run_admission_branch(self.packet, mock_session_factory,
                                 mock_oracle, default_store(),
                                 mock_probe_scorer, authorization=forged)
        self.assertIn("production contact surface refused",
                      str(ctx2.exception))

    def test_pending_collapse_identity_refuses_wire_authorization(self):
        def bare_detector(runs):
            return False

        with self.assertRaises(RunnerContractError) as ctx:
            authorize_wire_contact(self.packet, self.manifest,
                                   self.manifest_result, token_cover_rule(),
                                   bare_detector)
        self.assertIn("no decision-capable default", str(ctx.exception))
        with self.assertRaises(RunnerContractError):
            self.run_branch(collapse_detector=bare_detector)

    def test_manifest_packet_fixture_mismatch_refuses(self):
        tampered = json.loads(json.dumps(self.manifest))
        tampered["calibration_fixtures"][0]["sha256"] = "f" * 64
        result = check_calibration_manifest(tampered)
        self.assertTrue(result.ok)  # format-valid, identity-wrong
        with self.assertRaises(RunnerContractError) as ctx:
            authorize_wire_contact(self.packet, tampered, result,
                                   token_cover_rule(), self.detector)
        self.assertIn("byte-bind", str(ctx.exception))

    def test_manifest_probe_binding_refuses(self):
        tampered = json.loads(json.dumps(self.manifest))
        tampered["ignorance_probe_contract"]["probe_fixture_ids"] = [
            "probe-fictional-0"]
        result = check_calibration_manifest(tampered)
        with self.assertRaises(RunnerContractError) as ctx:
            authorize_wire_contact(self.packet, tampered, result,
                                   token_cover_rule(), self.detector)
        self.assertIn("probe ids", str(ctx.exception))

    def test_manifest_bytes_must_recompute_to_checked_hash(self):
        other = json.loads(json.dumps(self.manifest))
        other["model_id"] = "wire-fictional-engine-1"
        other_result = check_calibration_manifest(other)
        with self.assertRaises(RunnerContractError) as ctx:
            authorize_wire_contact(self.packet, self.manifest, other_result,
                                   token_cover_rule(), self.detector)
        self.assertIn("recompute", str(ctx.exception))

    def test_authorization_binds_to_this_packet(self):
        other_packet = dataclasses.replace(
            self.packet, index={**self.packet.index,
                                "packet_id": "wire-fictional-packet-other"})
        with self.assertRaises(RunnerContractError) as ctx:
            run_wire_admission_branch(
                other_packet, mock_session_factory, mock_oracle,
                default_store(), token_cover_rule(), mock_probe_scorer,
                wire_authorization=self.authorization,
                collapse_detector=self.detector, manifest=self.manifest)
        self.assertIn("bind to this packet", str(ctx.exception))

    def test_runtime_rule_and_manifest_must_match_authorization(self):
        with self.assertRaises(RunnerContractError) as ctx:
            self.run_branch(wire_rule=exact_equality_rule())
        self.assertIn("authorized executor", str(ctx.exception))
        tampered = json.loads(json.dumps(self.manifest))
        tampered["model_id"] = "wire-fictional-engine-1"
        with self.assertRaises(RunnerContractError):
            self.run_branch(manifest=tampered)

    def test_wrong_template_identity_refuses(self):
        tampered = json.loads(json.dumps(self.manifest))
        tampered["foreground_template_hash"] = "e" * 64
        result = check_calibration_manifest(tampered)
        with self.assertRaises(RunnerContractError):
            authorize_wire_contact(self.packet, tampered, result,
                                   token_cover_rule(), self.detector)


class TestPhaseOrderAndCounts(BranchCase):
    def test_canonical_phase_order(self):
        report = self.run_branch()
        self.assertEqual(report.phase_log, ["manifest_precommit",
                                            "ignorance_probes",
                                            "primary_board"])
        self.assertEqual(report.status, STATUS_COMPLETED)
        self.assertTrue(report.eligible_for_planning)

    def test_counts_derive_from_identity_cardinality(self):
        report = self.run_branch()
        self.assertEqual(report.probe_calls, PROBES)
        self.assertEqual(report.invocations, PROBES + BOARD)
        self.assertEqual(len(report.runs), BOARD)
        self.assertEqual(report.provider_cache, "unverified")

    def test_six_lane_board_per_identity(self):
        report = self.run_branch()
        by_fixture = {}
        for run in report.runs:
            by_fixture.setdefault(run.fixture_id, set()).add(run.lane)
        for fixture_id in self.packet.analog:
            self.assertEqual(by_fixture[fixture_id], set(c.LANES))
        for fixture_id in self.packet.s_family:
            self.assertEqual(by_fixture[fixture_id], set(c.SOURCE_LEGS))

    def test_probe_text_never_enters_later_prompts(self):
        report = self.run_branch()
        for run in report.runs:
            self.assertNotIn("FICTIONAL PROBE", run.prompt)


class TestAdmissionVerdictRow(BranchCase):
    """Resolution C mandated tests: derived pilots + one legal computed
    verdict row."""

    def test_verdict_row_emitted_and_legal(self):
        report = self.run_branch()
        row = report.admission_verdict_row
        self.assertIsNotNone(row)
        self.assertEqual(row["event_type"], "engine_admission_verdict")
        self.assertIn(row["payload"]["verdict"],
                      c.ENGINE_ADMISSION_VERDICTS)
        # mock oracle passes everything → S0 band violated → engine_refused
        self.assertEqual(row["payload"]["verdict"], "engine_refused")
        self.assertTrue(any("s0_pass_rate" in r
                            for r in row["payload"]["reasons"]))
        self.assertEqual(row["payload"]["probe_sidecar_sha256"],
                         report.probe_sidecar_sha256)
        self.assertEqual(row["payload"]["probe_calls"], PROBES)
        self.assertIsNone(row["payload"]["collapse_rows_sha256"])
        self.assertIs(row["payload"]["budget_disclosure_required"], True)
        # the row is part of the replayable ledger
        self.assertIs(report.rows[-1], row)

    def test_pilots_derived_from_replayed_runs(self):
        report = self.run_branch()
        pilots = derive_pilots_from_runs(report, self.packet, self.manifest)
        # every planned contrast id is present (region declared → population
        # contrasts included)
        self.assertIn("sup_mm_C_vs_B", pilots.binary)
        self.assertIn("src_s1_vs_s0", pilots.binary)
        self.assertIn("pop_cost_C_vs_A", pilots.population)
        self.assertIn("or_eff_cost_C_vs_g", pilots.population)
        self.assertEqual(pilots.vertices,
                         self.manifest["population_region"]["vertices"])
        # binary successes come from world_oracle_score.passed (all pass)
        pilot = pilots.binary["sup_mm_C_vs_B"]
        self.assertEqual((pilot.passes_t, pilot.n_t, pilot.passes_c,
                          pilot.n_c), (5.0, 5, 5.0, 5))

    def test_incomplete_contrast_map_refuses_assembly(self):
        report = self.run_branch()
        # drop every A_always_check run: population contrasts lose an arm
        report.runs = [r for r in report.runs if r.lane != "A_always_check"]
        with self.assertRaises(RunnerContractError) as ctx:
            derive_pilots_from_runs(report, self.packet, self.manifest)
        self.assertIn("incomplete analog contrast map", str(ctx.exception))

    def test_refused_branch_refuses_pilot_derivation(self):
        report = self.run_branch()
        report.eligible_for_planning = False
        with self.assertRaises(RunnerContractError):
            derive_pilots_from_runs(report, self.packet, self.manifest)


class TestPrecisionOnlySelection(unittest.TestCase):
    """Mandated test: projected-clearance diagnostics cannot change
    admission selection — precision/N alone selects the OR arm."""

    def test_clearance_diagnostic_does_not_steer_selection(self):
        sup = ContrastSpec("arm_sup", "binary_superiority", "9.3", 0.95,
                           ("match_mismatch",), 0.25, 0.20, "C", "G")
        ni = ContrastSpec("arm_ni", "binary_noninferiority", "9.3", 0.95,
                          ("match_mismatch",), 0.10, 0.10, "C", "G")
        gate = PlannedGate("test_or", "9.3",
                           AnyOf((OrArm("quality", sup),
                                  OrArm("efficiency", ni))))
        pilots = Pilots(binary={
            # 0.5/0.5: widest intervals, projected clearance FALSE
            "arm_sup": BinaryPilot(2.5, 5, 2.5, 5),
            # 0.9/0.9: clearance TRUE but tighter target => larger N
            "arm_ni": BinaryPilot(4.5, 5, 4.5, 5),
        })
        plan = resolve_gates([gate], pilots)
        reqs = {r.contrast_id: r for r in plan.resolved[0].requirements}
        self.assertIs(reqs["arm_sup"].projected_clearance_diagnostic, False)
        self.assertIs(reqs["arm_ni"].projected_clearance_diagnostic, True)
        self.assertLess(reqs["arm_sup"].n_required, reqs["arm_ni"].n_required)
        # the smaller-N arm wins although its clearance diagnostic fails
        self.assertEqual(plan.or_selections["test_or"].arm_id, "quality")


class TestProbeSidecar(BranchCase):
    """Resolution E mandated tests: hash-pinned sidecar, strict types."""

    def test_sidecar_is_typed_and_hash_pinned(self):
        report = self.run_branch()
        self.assertEqual(len(report.probe_sidecar), PROBES)
        for entry in report.probe_sidecar:
            self.assertEqual(set(entry), {"probe_id", "answer_sha256",
                                          "recovered", "temperature",
                                          "isolation_id"})
            self.assertIsInstance(entry["recovered"], bool)
            self.assertEqual(entry["temperature"], c.CALIBRATION_TEMPERATURE)
            self.assertTrue(entry["isolation_id"].startswith("wire-iso-"))
            self.assertEqual(len(entry["answer_sha256"]), 64)
        recomputed = hashlib.sha256(json.dumps(
            report.probe_sidecar, sort_keys=True,
            separators=(",", ":")).encode("utf-8")).hexdigest()
        self.assertEqual(report.probe_sidecar_sha256, recomputed)

    def test_probe_response_text_not_retained(self):
        report = self.run_branch()
        blob = json.dumps(report.probe_sidecar) + json.dumps(report.rows)
        self.assertNotIn("fictional-wire-answer", blob)

    def test_non_bool_probe_scorer_fails_closed(self):
        with self.assertRaises(RunnerContractError) as ctx:
            run_wire_admission_branch(
                self.packet, mock_session_factory, mock_oracle,
                default_store(), token_cover_rule(),
                lambda pid, text: "yes",
                wire_authorization=self.authorization,
                collapse_detector=self.detector, manifest=self.manifest)
        self.assertIn("strict bool", str(ctx.exception))

    def test_untyped_probe_result_fails_closed(self):
        class Loose(MockSession):
            def __call__(self, prompt):
                super().__call__(prompt)
                return {"answer_text": "raw dict"}

        with self.assertRaises(RunnerContractError) as ctx:
            self.run_branch(lambda t: Loose(t))
        self.assertIn("typed EngineResult", str(ctx.exception))


class TestIsolationIdentity(BranchCase):
    """Resolution F: unique isolation_id even across distinct wrappers."""

    def test_reused_isolation_id_refused_across_distinct_wrappers(self):
        def factory(temperature):
            return MockSession(temperature, isolation_id="wire-iso-shared")

        with self.assertRaises(RunnerContractError) as ctx:
            self.run_branch(factory)
        self.assertIn("isolation_id 'wire-iso-shared' reused",
                      str(ctx.exception))

    def test_missing_isolation_id_refused(self):
        def factory(temperature):
            s = MockSession(temperature)
            s.isolation_id = ""
            return s

        with self.assertRaises(RunnerContractError):
            self.run_branch(factory)

    def test_reused_object_refused_even_with_forged_flag(self):
        cached = MockSession()

        def factory(temperature):
            cached.used = False
            return cached

        with self.assertRaises(RunnerContractError) as ctx:
            self.run_branch(factory)
        self.assertIn("already-seen session object", str(ctx.exception))

    def test_no_retry_no_redraw_guard(self):
        guard = _OnceGuard("primary_board")
        guard.claim("fx", "C_controlled_check")
        with self.assertRaises(RunnerContractError):
            guard.claim("fx", "C_controlled_check")


class TestTransportRefusalIsTerminal(BranchCase):
    """B3: the first transport failure terminates and types the branch."""

    def _flaky(self, fail_at: int):
        calls = {"n": 0}

        def factory(temperature):
            calls["n"] += 1
            if calls["n"] == fail_at:
                class Dead:
                    used = False
                    isolation_id = f"wire-iso-dead-{fail_at}"

                    def __call__(self, prompt):
                        raise TransportRefusal("fictional wire outage")
                return Dead()
            return MockSession(temperature)
        return factory, calls

    def test_board_failure_terminates_branch(self):
        fail_at = PROBES + 7
        factory, calls = self._flaky(fail_at)
        report = self.run_branch(factory)
        self.assertEqual(report.status, STATUS_BRANCH_REFUSED_TRANSPORT)
        self.assertFalse(report.eligible_for_planning)
        self.assertEqual(len(report.refused), 1)
        self.assertEqual(calls["n"], fail_at)
        self.assertEqual(report.invocations, fail_at)
        self.assertEqual(len(report.runs), 6)
        self.assertIsNone(report.s_band)
        self.assertIsNone(report.ignorance)
        self.assertIsNone(report.collapse)

    def test_refused_branch_still_gets_typed_verdict_row(self):
        """Resolution E: the verdict row records the typed refusal and any
        completed probe audit."""
        factory, _ = self._flaky(PROBES + 1)
        report = self.run_branch(factory)
        row = report.admission_verdict_row
        self.assertEqual(row["payload"]["verdict"], "not_engaged")
        self.assertTrue(any("branch_refused_transport" in r
                            for r in row["payload"]["reasons"]))
        self.assertEqual(row["payload"]["probe_sidecar_sha256"],
                         report.probe_sidecar_sha256)
        self.assertEqual(row["payload"]["probe_calls"], PROBES)

    def test_probe_failure_terminates_branch(self):
        factory, calls = self._flaky(1)
        report = self.run_branch(factory)
        self.assertEqual(report.status, STATUS_BRANCH_REFUSED_TRANSPORT)
        self.assertEqual(calls["n"], 1)
        self.assertEqual(len(report.runs), 0)
        self.assertIn("probe_id", report.refused[0])
        self.assertEqual(
            report.admission_verdict_row["payload"]["verdict"], "not_engaged")


class TestCollapseLedger(BranchCase):
    """Resolution D mandated tests: namespaced, separately replayable,
    hash-pinned T=0.7 rows; §10.2 single same-identity pass."""

    def test_collapse_triggers_single_same_identity_pass(self):
        report = self.run_branch(constant_session_factory(collapse_at_t07=True))
        self.assertIn("collapse_pass", report.phase_log)
        self.assertTrue(report.collapse.collapsed_at_t05)
        self.assertTrue(report.collapse.collapsed_at_t07)
        self.assertEqual(report.probe_calls, PROBES)   # probes never rerun
        self.assertEqual(report.invocations, PROBES + BOARD + BOARD)
        self.assertEqual({(r.fixture_id, r.lane) for r in report.collapse_runs},
                         {(r.fixture_id, r.lane) for r in report.runs})

    def test_t07_rows_are_namespaced_and_separate(self):
        report = self.run_branch(constant_session_factory())
        self.assertTrue(report.collapse_rows)
        for row in report.collapse_rows:
            self.assertTrue(row["event_id"].startswith(T07_NAMESPACE),
                            msg=row["event_id"])
        for row in report.rows:
            self.assertFalse(row["event_id"].startswith(T07_NAMESPACE))

    def test_t07_ledger_separately_replayable(self):
        report = self.run_branch(constant_session_factory())
        fixtures = {fid: {k: v for k, v in fx.items()
                          if k not in ("_shape", "entity_keys")}
                    for fid, fx in {**self.packet.s_family,
                                    **self.packet.analog}.items()}
        result = replay_ledger(
            report.collapse_rows, fixtures=fixtures,
            expected_contract_hashes={
                "part_i_spec_hash": c.PART_I_SPEC_SHA256},
            placebo_sha256_by_fixture=self.packet.placebo_sha256_by_fixture())
        self.assertTrue(result.ok, msg=str(result.failures[:5]))
        self.assertEqual(len(result.groups), BOARD)

    def test_t07_ledger_hash_pinned_in_verdict_row(self):
        report = self.run_branch(constant_session_factory())
        recomputed = hashlib.sha256(json.dumps(
            report.collapse_rows, sort_keys=True,
            separators=(",", ":")).encode("utf-8")).hexdigest()
        self.assertEqual(report.collapse_rows_sha256, recomputed)
        payload = report.admission_verdict_row["payload"]
        self.assertEqual(payload["collapse_rows_sha256"], recomputed)
        self.assertTrue(payload["collapsed_at_t05"])

    def test_t07_variation_clears_collapse(self):
        report = self.run_branch(constant_session_factory(collapse_at_t07=False))
        self.assertTrue(report.collapse.collapsed_at_t05)
        self.assertFalse(report.collapse.collapsed_at_t07)

    def test_no_collapse_no_extra_pass(self):
        report = self.run_branch()
        self.assertNotIn("collapse_pass", report.phase_log)
        self.assertEqual(report.collapse_runs, [])
        self.assertIsNone(report.collapse_rows_sha256)


class TestUntrustingReplay(BranchCase):
    def test_whole_ledger_replay_with_placebo_pins(self):
        report = self.run_branch()
        fixtures = {fid: {k: v for k, v in fx.items()
                          if k not in ("_shape", "entity_keys")}
                    for fid, fx in {**self.packet.s_family,
                                    **self.packet.analog}.items()}
        result = replay_ledger(
            report.rows, fixtures=fixtures,
            expected_contract_hashes={
                "part_i_spec_hash": c.PART_I_SPEC_SHA256,
                "manifest_sha256": self.authorization.manifest_sha256},
            placebo_sha256_by_fixture=self.packet.placebo_sha256_by_fixture())
        self.assertTrue(result.ok, msg=str(result.failures[:5]))
        self.assertEqual(len(result.groups), BOARD)

    def test_replay_rejects_wrong_placebo_pin(self):
        report = self.run_branch()
        pins = dict(self.packet.placebo_sha256_by_fixture())
        pins[next(iter(pins))] = "f" * 64
        result = replay_ledger(report.rows,
                               placebo_sha256_by_fixture=pins)
        self.assertFalse(result.ok)


class TestArtifactIdentities(unittest.TestCase):
    def test_identities_only_for_implemented_artifacts(self):
        ids = implemented_artifact_identities()
        self.assertEqual(ids["part_i_spec_sha256"], c.PART_I_SPEC_SHA256)
        for key in ("renderer", "controller", "packet_loader", "runner"):
            self.assertIn("contract_sha256", ids[key])
            self.assertIn("module_sha256_diagnostic", ids[key])
        # resolution G: the extractor's source hash is diagnostic-named
        self.assertIn("module_sha256_diagnostic", ids["extractor"])
        self.assertNotIn("extractor_sha256", ids["extractor"])
        self.assertIn("predicate_contract_sha256", ids["extractor"])
        # resolution A: the final check contract is typed pending
        self.assertEqual(ids["check"]["check_contract_identity"]["status"],
                         "pending")
        self.assertNotIn("check_contract_sha256", ids["check"])
        for absent in ("manifest_instance", "decoding_contract",
                       "oracle_snapshots", "fixture_content",
                       "comparison_rule"):
            self.assertNotIn(absent, ids)

    def test_runner_contract_hash_covers_split_and_policies(self):
        payload = runner_contract_payload()
        self.assertIn("wire", payload["surfaces"])
        self.assertIn("contact", payload["surfaces"])
        self.assertIn("operator-bound", payload["session_lease_policy"])
        mutated = dict(payload, transport_policy="retry twice")
        digest = hashlib.sha256(json.dumps(mutated, sort_keys=True,
                                           separators=(",", ":")).encode()
                                ).hexdigest()
        self.assertNotEqual(digest, runner_contract_hash())


if __name__ == "__main__":
    unittest.main()
