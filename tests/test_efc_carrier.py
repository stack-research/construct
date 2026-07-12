"""Wire tests for §3 carrier/envelope/warrant/mint machinery.

Mock structures only. The two authority pins that matter most: a nomination
can never flip a refusal (§3.3 / R5), and an unrelated revision never
suspends (§11's governance-should-lose cell).
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from harness.efc_carrier import (CarrierContractError, DispositionCarrier,
                                 MintInputs, MintResult, NominationRecord,
                                 SourceCausalVerdict, TypedRevision,
                                 V0_PREDICATE_FEATURE_BINDINGS, ValidityEnvelope,
                                 carrier_hash, envelope_hash, mint_disposition,
                                 revision_applies, validate_carrier,
                                 validate_revision, warrant_health)

H = "a" * 64
H2 = "b" * 64


def envelope(**overrides):
    env = ValidityEnvelope(
        model_id="engine-x-2026-05", renderer_id="renderer-v1",
        foreground_template_hash=H, tool_contract_id="tools-v0",
        decoding_contract_id="decode-t05", controller_id="controller-v0",
        predicate_contract_hash=H, extractor_hash=H, check_contract_hash=H,
        engine_admission_packet_hash=H, source_family_hash=H,
        target_population_hash=H, per_invocation_cost_ceiling=1024)
    return replace(env, **overrides) if overrides else env


def carrier(**overrides):
    car = DispositionCarrier(
        mechanism_id="epistemic_frame_check", mechanism_version="v0",
        predicate_contract_hash=H,
        predicate_feature_bindings=dict(V0_PREDICATE_FEATURE_BINDINGS),
        extractor_hash=H, check_id="scope_provenance_check_v0",
        check_contract_hash=H, warrant_event_ids=("evt-src-001", "evt-src-002"),
        warrant_result_hash=H2, validity_envelope=envelope(),
        status="experimental_probationary", per_invocation_cost_ceiling=1024,
        revision_scope_rules_hash=H, retirement_rules_hash=H)
    return replace(car, **overrides) if overrides else car


def mint_inputs(**overrides):
    inputs = MintInputs(
        carrier=carrier(),
        source_verdict=SourceCausalVerdict(True, "external_corpus", H),
        provenance_live=True, revisions=(),
        engine_admission_verdict="engine_admitted",
        calibration_packet_hash=H, expected_envelope=envelope(),
        minted_by="external_controller", nomination=None)
    return replace(inputs, **overrides) if overrides else inputs


class TestCarrierClosure(unittest.TestCase):
    def test_valid_carrier_passes(self):
        validate_carrier(carrier())

    def test_wrong_status_refused(self):
        with self.assertRaises(CarrierContractError):
            validate_carrier(carrier(status="licensed"))

    def test_template_id_bindings_refused(self):
        with self.assertRaises(CarrierContractError):
            validate_carrier(carrier(predicate_feature_bindings={"template": "T1"}))

    def test_prose_rider_in_bindings_refused(self):
        bindings = dict(V0_PREDICATE_FEATURE_BINDINGS)
        bindings["lesson"] = "always check scope on cited sources"
        with self.assertRaises(CarrierContractError):
            validate_carrier(carrier(predicate_feature_bindings=bindings))

    def test_prose_in_id_field_refused(self):
        from harness.efc_carrier import validate_envelope
        with self.assertRaises(CarrierContractError):
            validate_envelope(envelope(
                model_id="the model we liked most during review"))

    def test_bad_hash_refused(self):
        with self.assertRaises(CarrierContractError):
            validate_carrier(carrier(warrant_result_hash="not-a-hash"))

    def test_empty_warrant_refused(self):
        with self.assertRaises(CarrierContractError):
            validate_carrier(carrier(warrant_event_ids=()))

    def test_ceiling_must_match_envelope(self):
        with self.assertRaises(CarrierContractError):
            validate_carrier(carrier(per_invocation_cost_ceiling=999))

    def test_envelope_hash_changes_on_any_field(self):
        base = envelope_hash(envelope())
        for override in ({"model_id": "engine-y"},
                         {"renderer_id": "renderer-v2"},
                         {"decoding_contract_id": "decode-t07"},
                         {"target_population_hash": H2},
                         {"per_invocation_cost_ceiling": 512}):
            self.assertNotEqual(base, envelope_hash(envelope(**override)),
                                msg=str(override))


class TestWarrantHealth(unittest.TestCase):
    def test_each_scope_suspends_its_target(self):
        car = carrier()
        cases = [
            TypedRevision("rev1", "source_provenance", "evt-src-001", "retracted"),
            TypedRevision("rev2", "causal_derivation", H2, "rederived"),
            TypedRevision("rev3", "check_contract", H, "incompatible_v1"),
            TypedRevision("rev4", "resident_instance", carrier_hash(car), "manual"),
        ]
        for rev in cases:
            health = warrant_health(car, [rev])
            self.assertFalse(health.eligible, msg=rev.scope)
            self.assertEqual(health.suspended_by, rev.revision_id)

    def test_unrelated_revision_leaves_eligible(self):
        # §11 loses-cell: over-broad suspension is a governance loss
        unrelated = [
            TypedRevision("rev5", "source_provenance", "evt-other", "retracted"),
            TypedRevision("rev6", "causal_derivation", H, "other_warrant"),
            TypedRevision("rev7", "resident_instance", H2, "different_instance"),
        ]
        health = warrant_health(carrier(), unrelated)
        self.assertTrue(health.eligible)

    def test_untyped_scope_refused(self):
        with self.assertRaises(CarrierContractError):
            validate_revision(TypedRevision("rev", "everything", "x", "panic"))
        with self.assertRaises(CarrierContractError):
            revision_applies(carrier(),
                             TypedRevision("rev", "both_scopes", "x", "r"))


class TestMintAuthority(unittest.TestCase):
    def test_happy_path_mints(self):
        result = mint_disposition(mint_inputs())
        self.assertEqual(result, MintResult(True, "disposition_minted", ()))

    def test_failed_outcome_cannot_mint(self):
        result = mint_disposition(mint_inputs(
            source_verdict=SourceCausalVerdict(False, "external_corpus", H)))
        self.assertFalse(result.minted)
        self.assertEqual(result.event_type, "disposition_mint_refused")

    def test_authored_oracle_cannot_mint(self):
        result = mint_disposition(mint_inputs(
            source_verdict=SourceCausalVerdict(True, "authored", H)))
        self.assertFalse(result.minted)
        self.assertTrue(any("R1" in r for r in result.refusal_reasons))

    def test_dead_provenance_and_standing_revision_refuse(self):
        self.assertFalse(mint_disposition(mint_inputs(provenance_live=False)).minted)
        rev = TypedRevision("rev1", "source_provenance", "evt-src-002", "retracted")
        result = mint_disposition(mint_inputs(revisions=(rev,)))
        self.assertFalse(result.minted)
        self.assertTrue(any("rev1" in r for r in result.refusal_reasons))

    def test_unadmitted_engine_and_wrong_packet_refuse(self):
        self.assertFalse(mint_disposition(mint_inputs(
            engine_admission_verdict="engine_refused")).minted)
        self.assertFalse(mint_disposition(mint_inputs(
            calibration_packet_hash=H2)).minted)

    def test_envelope_mismatch_refuses(self):
        result = mint_disposition(mint_inputs(
            expected_envelope=envelope(model_id="engine-y")))
        self.assertFalse(result.minted)
        self.assertTrue(any("transfer" in r for r in result.refusal_reasons))

    def test_internal_minter_refused(self):
        result = mint_disposition(mint_inputs(minted_by="model_self_report"))
        self.assertFalse(result.minted)

    def test_nomination_cannot_flip_any_refusal(self):
        # R5/§3.3: run every refusal case again WITH an enthusiastic
        # nomination attached; nothing may change
        nomination = NominationRecord("evt-nom-1", H)
        refusal_cases = [
            mint_inputs(source_verdict=None),
            mint_inputs(provenance_live=False),
            mint_inputs(engine_admission_verdict="point_mode_diagnostic"),
            mint_inputs(minted_by="model_self_report"),
        ]
        for case in refusal_cases:
            bare = mint_disposition(case)
            with_nom = mint_disposition(replace(case, nomination=nomination))
            self.assertFalse(with_nom.minted)
            self.assertEqual(bare.refusal_reasons, with_nom.refusal_reasons)

    def test_nomination_alone_never_mints(self):
        result = mint_disposition(mint_inputs(
            source_verdict=None, nomination=NominationRecord("evt-nom-2", H)))
        self.assertFalse(result.minted)


if __name__ == "__main__":
    unittest.main()
