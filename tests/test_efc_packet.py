"""Wire tests: fail-closed packet loader/validator (B2), exclusion-screen
boundaries, placebo gate incl. the ≤256 ceiling, derived budget (design
§3-§5, §8, §9)."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from harness import efc_contracts as c
from harness.efc_check import run_scope_provenance_check
from harness.efc_manifest import check_calibration_manifest
from harness.efc_packet import (JACCARD_REJECT_THRESHOLD, PacketContractError,
                                derive_call_plan, derive_total_budget_tokens,
                                exclusion_screen, load_packet,
                                packet_loader_contract_hash,
                                packet_loader_contract_payload,
                                placebo_pairing_failures, shingle_jaccard,
                                wording_shingles)
from tests.efc_wire_fixtures import (default_store, fictional_source_ref,
                                     firing_fixture, rewrite_entry,
                                     synthetic_carrier_payload,
                                     token_cover_rule, write_packet)


class PacketCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = write_packet(Path(self.tmp.name) / "packet")
        self.store = default_store()
        self.rule = token_cover_rule()

    def tearDown(self):
        self.tmp.cleanup()

    def load(self):
        return load_packet(self.root, self.store, self.rule)

    def index(self) -> dict:
        return json.loads((self.root / "packet_index.json").read_text())

    def write_index(self, index: dict) -> None:
        (self.root / "packet_index.json").write_text(json.dumps(index))

    def assert_fails(self, needle: str):
        packet = self.load()
        self.assertFalse(packet.ok)
        self.assertTrue(any(needle in f for f in packet.failures),
                        msg=f"{needle!r} not in {packet.failures}")


class TestPacketLoaderPositive(PacketCase):
    def test_valid_packet_loads(self):
        packet = self.load()
        self.assertTrue(packet.ok, msg=str(packet.failures))
        self.assertEqual(len(packet.s_family), 5)
        self.assertEqual(len(packet.analog), 15)
        shapes = [f["_shape"] for f in packet.s_family.values()]
        self.assertEqual((shapes.count("mismatch"), shapes.count("commit")),
                         (3, 2))
        self.assertEqual(len(packet.placebos), 5 + 10)
        self.assertEqual(len(packet.placebo_sha256_by_fixture()), 15)

    def test_loader_contract_hash_changes_on_mutation(self):
        payload = packet_loader_contract_payload()
        mutated = dict(payload, exclusion={"shingle_width": 4,
                                           "jaccard_reject_threshold": 0.5})
        digest = hashlib.sha256(json.dumps(mutated, sort_keys=True,
                                           separators=(",", ":")).encode()
                                ).hexdigest()
        self.assertNotEqual(digest, packet_loader_contract_hash())


class TestClosedIndexShape(PacketCase):
    """B2: closed shapes, unique ids/paths, confined paths."""

    def test_unknown_index_key_refused(self):
        index = self.index()
        index["notes"] = "x"
        self.write_index(index)
        self.assert_fails("closed shape")

    def test_entry_shape_closed(self):
        index = self.index()
        index["entries"][0]["extra"] = 1
        self.write_index(index)
        self.assert_fails("must be {id, path, role, sha256}")

    def test_unknown_role_refused(self):
        index = self.index()
        index["entries"][0]["role"] = "bonus_material"
        self.write_index(index)
        self.assert_fails("identity registry is closed")

    def test_duplicate_id_refused(self):
        index = self.index()
        index["entries"][1]["id"] = index["entries"][0]["id"]
        self.write_index(index)
        self.assert_fails("duplicate entry id")

    def test_duplicate_path_refused(self):
        index = self.index()
        index["entries"][1]["path"] = index["entries"][0]["path"]
        self.write_index(index)
        self.assert_fails("duplicate packet path")

    def test_absolute_path_refused(self):
        index = self.index()
        index["entries"][0]["path"] = str(
            self.root / "s_family" / "sf-00.json")
        self.write_index(index)
        self.assert_fails("absolute path")

    def test_dotdot_escape_refused(self):
        escape = self.root.parent / "outside.json"
        escape.write_text("{}")
        index = self.index()
        index["entries"][0]["path"] = "../outside.json"
        self.write_index(index)
        self.assert_fails("escapes the packet root")

    def test_symlink_refused(self):
        target = self.root / "s_family" / "sf-00.json"
        link = self.root / "s_family" / "link.json"
        os.symlink(target, link)
        index = self.index()
        index["entries"][0]["path"] = "s_family/link.json"
        self.write_index(index)
        self.assert_fails("symlink")

    def test_entry_id_must_match_task_id(self):
        fx = json.loads((self.root / "s_family/sf-00.json").read_text())
        fx["task_id"] = "sf-99"
        rewrite_entry(self.root, "s_family/sf-00.json", fx, "sf-00")
        self.assert_fails("entry id != fixture task_id")

    def test_placebo_id_must_match_entry_id(self):
        pb = json.loads((self.root / "placebo/pb-sf-00.json").read_text())
        pb["placebo_id"] = "pb-other"
        rewrite_entry(self.root, "placebo/pb-sf-00.json", pb, "pb-sf-00")
        self.assert_fails("entry id != placebo_id")

    def test_hash_mismatch_fails(self):
        path = sorted((self.root / "analog").iterdir())[0]
        path.write_text(path.read_text() + " ")
        self.assert_fails("sha256 mismatch")


class TestSiblings(PacketCase):
    def test_missing_sibling_name_refused(self):
        index = self.index()
        del index["siblings"]["difficulty_rationale"]
        self.write_index(index)
        self.assert_fails("siblings must be exactly")

    def test_sibling_hash_checked_not_just_present(self):
        """B2: sibling artifacts are hash-governed."""
        (self.root / "difficulty_rationale.md").write_text("tampered\n")
        self.assert_fails("sibling difficulty_rationale: sha256 mismatch")

    def test_empty_sibling_refused(self):
        data = b""
        (self.root / "isolation_contract.md").write_bytes(data)
        index = self.index()
        index["siblings"]["isolation_contract"]["sha256"] = hashlib.sha256(
            data).hexdigest()
        self.write_index(index)
        self.assert_fails("empty artifact")


class TestIdentityCounts(PacketCase):
    def test_wrong_s_family_count(self):
        index = self.index()
        index["entries"] = [e for e in index["entries"] if e["id"] != "sf-04"]
        self.write_index(index)
        self.assert_fails("needs exactly 5")

    def test_empty_analog_board_fails(self):
        """B2: the empty-board case is a count failure, not a skip."""
        index = self.index()
        index["entries"] = [e for e in index["entries"]
                            if e["role"] != "analog"]
        self.write_index(index)
        self.assert_fails("analog board has 0 identities")

    def test_stratum_imbalance_fails(self):
        fx = json.loads(
            (self.root / "analog/ma-00-match_mismatch.json").read_text())
        fx["stratum"] = "match_commit"
        rewrite_entry(self.root, "analog/ma-00-match_mismatch.json", fx,
                      "ma-00-match_mismatch")
        self.assert_fails("needs exactly 5")

    def test_shape_split_is_frozen(self):
        fx = json.loads((self.root / "s_family/sf-00.json").read_text())
        fx["shape"] = "commit"
        rewrite_entry(self.root, "s_family/sf-00.json", fx, "sf-00")
        self.assert_fails("shape split")

    def test_exactly_one_probe_contract_and_carrier(self):
        index = self.index()
        index["entries"] = [e for e in index["entries"]
                            if e["role"] != "probe_contract"]
        self.write_index(index)
        self.assert_fails("exactly one probe_contract")


class TestFieldDisciplineAndTypedObjects(PacketCase):
    def test_forbidden_field_in_fixture_fails(self):
        fx = json.loads((self.root / "s_family/sf-01.json").read_text())
        fx["required_scope"] = "leak"
        rewrite_entry(self.root, "s_family/sf-01.json", fx, "sf-01")
        self.assert_fails("forbidden foreground fields")

    def test_carrier_must_be_section_3_1_complete(self):
        """B2: the synthetic carrier is validated by efc_carrier machinery."""
        wrapper = synthetic_carrier_payload()
        del wrapper["carrier"]["warrant_result_hash"]
        rewrite_entry(self.root, "carrier/synthetic_carrier.json", wrapper,
                      "synthetic-carrier")
        self.assert_fails("not §3.1-complete")

    def test_carrier_bad_hash_fails_typed_validation(self):
        wrapper = synthetic_carrier_payload()
        wrapper["carrier"]["warrant_result_hash"] = "not-hex"
        rewrite_entry(self.root, "carrier/synthetic_carrier.json", wrapper,
                      "synthetic-carrier")
        self.assert_fails("fails §3.1 validation")

    def test_non_synthetic_carrier_fails(self):
        wrapper = synthetic_carrier_payload()
        wrapper["synthetic"] = False
        rewrite_entry(self.root, "carrier/synthetic_carrier.json", wrapper,
                      "synthetic-carrier")
        self.assert_fails("synthetic and non-mintable")

    def test_probe_contract_closed_shape(self):
        probes = json.loads(
            (self.root / "probes/ignorance_probe_contract.json").read_text())
        probes["extra"] = 1
        rewrite_entry(self.root, "probes/ignorance_probe_contract.json",
                      probes, "probe-contract")
        self.assert_fails("closed shape")

    def test_probe_texts_must_match_ids(self):
        probes = json.loads(
            (self.root / "probes/ignorance_probe_contract.json").read_text())
        del probes["probe_texts"]["probe-fictional-1"]
        rewrite_entry(self.root, "probes/ignorance_probe_contract.json",
                      probes, "probe-contract")
        self.assert_fails("probe_texts keys must equal")


class TestPlaceboGateViaLoader(PacketCase):
    def test_missing_placebo_fails(self):
        index = self.index()
        index["entries"] = [e for e in index["entries"]
                            if e["id"] != "pb-sf-00"]
        self.write_index(index)
        self.assert_fails("no pinned placebo object")

    def test_loader_runs_pairing_gate(self):
        """B2: the ±5 gate runs against the exact relevant evidence."""
        pb = json.loads((self.root / "placebo/pb-sf-00.json").read_text())
        pb["text"] = pb["text"] + " " + " ".join(["pad"] * 10)
        rewrite_entry(self.root, "placebo/pb-sf-00.json", pb, "pb-sf-00")
        self.assert_fails("token count off by")

    def test_oversized_placebo_hits_evidence_ceiling(self):
        """Additional correction: the ≤256 ceiling binds before pairing."""
        pb = json.loads((self.root / "placebo/pb-sf-00.json").read_text())
        pb["text"] = " ".join(["pad"] * 300)
        rewrite_entry(self.root, "placebo/pb-sf-00.json", pb, "pb-sf-00")
        self.assert_fails("evidence ceiling")

    def test_shared_reference_fails(self):
        pb = json.loads((self.root / "placebo/pb-sf-00.json").read_text())
        pb["disjoint_reference"] = fictional_source_ref(0)
        rewrite_entry(self.root, "placebo/pb-sf-00.json", pb, "pb-sf-00")
        self.assert_fails("fixture's own source_reference")

    def test_shared_entity_key_fails(self):
        pb = json.loads((self.root / "placebo/pb-sf-00.json").read_text())
        pb["entity_keys"] = ["examplon-glimmer"]
        rewrite_entry(self.root, "placebo/pb-sf-00.json", pb, "pb-sf-00")
        self.assert_fails("shares entity keys")

    def test_placebo_for_irrelevant_fixture_refused(self):
        pb = json.loads((self.root / "placebo/pb-sf-00.json").read_text())
        pb["placebo_for"] = "ir-00-irrelevant"
        rewrite_entry(self.root, "placebo/pb-sf-00.json", pb, "pb-sf-00")
        packet = self.load()
        self.assertFalse(packet.ok)
        self.assertTrue(any("takes no placebo treatment" in f
                            for f in packet.failures)
                        or any("no pinned placebo" in f
                               for f in packet.failures))

    def test_direct_pairing_gate(self):
        ref = fictional_source_ref(0)
        fixture = firing_fixture("pg-01", ref, mismatch=False)
        fixture["entity_keys"] = ["examplon-glimmer"]
        evidence = run_scope_provenance_check(self.store, ref,
                                              fixture["decision_scope"],
                                              self.rule)
        good = {"placebo_id": "pb", "placebo_for": "pg-01",
                "text": " ".join(["pad"] * len(evidence.rendered().split())),
                "disjoint_reference": "wire://fictional/other",
                "entity_keys": ["fictional-other"]}
        self.assertEqual(placebo_pairing_failures(good, evidence.rendered(),
                                                  fixture), [])
        undeclared = dict(good, note="hello")
        self.assertTrue(placebo_pairing_failures(undeclared,
                                                 evidence.rendered(), fixture))


class TestExclusionScreen(unittest.TestCase):
    """Design §8 exactly: NFKC → casefold → whitespace collapse → exact id
    rejection → 5-token shingles at Jaccard >= 0.20."""

    CAL = "the fictional examplon glimmer subsystem scope statement record one"

    def test_exact_id_rejection(self):
        v = exclusion_screen("completely different words here",
                             {"entity_key": ["shared-entity"]},
                             [self.CAL], {"entity_key": ["shared-entity"]})
        self.assertTrue(v.rejected)

    def test_threshold_boundary(self):
        cal_shingles = wording_shingles(self.CAL)
        v = exclusion_screen(self.CAL, {}, [self.CAL], {})
        self.assertTrue(v.rejected)
        v = exclusion_screen("wholly unrelated fictional whistle registry "
                             "narrative with no overlap at all", {},
                             [self.CAL], {})
        self.assertFalse(v.rejected)
        cand = ("the fictional examplon glimmer subsystem xa xb xc xd xe "
                "xf xg xh xi xj xk xl xm xn xo xp xq")
        j = shingle_jaccard(wording_shingles(cand), cal_shingles)
        v = exclusion_screen(cand, {}, [self.CAL], {})
        self.assertEqual(v.rejected, j >= JACCARD_REJECT_THRESHOLD)

    def test_under_five_tokens_no_shingle_rejection(self):
        v = exclusion_screen("four tokens only here", {}, [self.CAL], {})
        self.assertFalse(v.rejected)
        v = exclusion_screen("four tokens only here",
                             {"task_identity": ["t1"]}, [self.CAL],
                             {"task_identity": ["t1"]})
        self.assertTrue(v.rejected)

    def test_normalization_nfkc_casefold_whitespace(self):
        cand = "  THE   Fictional EXAMPLON glimmer subsystem scope statement record one "
        v = exclusion_screen(cand, {}, [self.CAL], {})
        self.assertTrue(v.rejected)


class TestBudgetDerivation(unittest.TestCase):
    def test_design_section_9_numbers(self):
        plan = derive_call_plan(dispositive_fact_count=15, roster_size=2)
        self.assertEqual(plan.probe_calls_branch, 15)
        self.assertEqual(plan.s_family_calls_branch, 15)   # 5 x 3
        self.assertEqual(plan.analog_calls_branch, 90)     # 15 x 6
        self.assertEqual(plan.primary_calls_branch, 120)
        self.assertEqual(plan.conditional_calls_branch, 105)
        self.assertEqual(plan.ceiling_calls_branch, 225)
        self.assertEqual(plan.roster_primary_total, 240)
        self.assertEqual(plan.roster_ceiling_total, 450)

    def test_budget_tokens_derived_not_stored(self):
        plan = derive_call_plan(15, 1)
        tokens = derive_total_budget_tokens(plan, prompt_cap=1000,
                                            completion_cap=500)
        self.assertEqual(tokens, 225 * (1000 + 500 + 512))

    def test_no_manifest_call_budget_key(self):
        """Brief item 8: the closed manifest schema refuses a call-budget
        key."""
        result = check_calibration_manifest({"total_budget_calls": 450})
        self.assertFalse(result.ok)
        self.assertTrue(any("unknown manifest keys" in f
                            for f in result.failures))

    def test_malformed_plan_refused(self):
        with self.assertRaises(PacketContractError):
            derive_call_plan(0, 1)
        with self.assertRaises(PacketContractError):
            derive_total_budget_tokens(derive_call_plan(1, 1), 0, 10)


if __name__ == "__main__":
    unittest.main()
