"""C4 offline manifest-budget derivation — conformance tests.

Runs the C4 builder once (offline, idempotent) and then verifies every
assignment-level property from the written artifacts alone: closed schema,
roster/R2 match, exact call-plan and 450-call ceiling derivation, budget
recomputation with no check-output double count, population byte match,
placeholder absence, and candidate (not pinned) status.
"""

from __future__ import annotations

import json
import shutil
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from harness import efc_author_c4 as c4
from harness import efc_contracts as c
from harness.efc_manifest import (check_calibration_manifest,
                                  population_choice_canonical)
from harness.efc_packet import derive_call_plan

ROOT = Path(__file__).resolve().parents[1]
C4_ROOT = ROOT / "corpus/efc_calibration/authoring_c4"


def _load(name: str):
    return json.loads((C4_ROOT / name).read_text(encoding="utf-8"))


class TestC4Derivation(unittest.TestCase):
    manifest: dict
    ledger: dict
    pin: dict
    report: dict

    @classmethod
    def setUpClass(cls):
        cls.manifest = _load("C4_candidate_calibration_manifest.json")
        cls.ledger = _load("budget_derivation_ledger.json")
        cls.pin = _load("roster_decoding_pin_candidate.json")
        cls.report = _load("c4_conformance_report.json")

    # ---- schema and identity -------------------------------------------------

    def test_manifest_machine_check_passes_closed_schema(self):
        result = check_calibration_manifest(self.manifest)
        self.assertTrue(result.ok, result.failures)

    def test_roster_matches_r2_close_ruling(self):
        self.assertEqual(self.manifest["engine_roster"],
                         ["openai/gpt-oss-20b", "gpt-5.4-2026-03-05"])
        self.assertEqual(self.manifest["model_id"], "gpt-5.4-2026-03-05")

    def test_decoding_pin_sibling_binds_r2_hashes(self):
        self.assertEqual(
            self.pin["branches"]["local"]
                ["decoding_contract_canonical_sha256"],
            "b36dfdc49ff83e0d52610580e8a9b00a62ed85d7b5d30e7c498c210a03f3bcd0")
        self.assertEqual(
            self.pin["branches"]["api"]
                ["decoding_contract_canonical_sha256"],
            "7fdb78bc5c78db47fe9ad16b0ee567c9e27ae3b76040a965342552f27fd42da0")
        self.assertEqual(self.pin["decoding_contract_id"],
                         self.manifest["decoding_contract_id"])
        self.assertEqual(self.pin["status"], "candidate_not_pinned")
        for branch in ("local", "api"):
            contract = self.pin["branches"][branch]["decoding_contract"]
            recomputed = c.sha256_utf8(json.dumps(
                contract, sort_keys=True, separators=(",", ":")))
            self.assertEqual(recomputed, self.pin["branches"][branch]
                             ["decoding_contract_canonical_sha256"])
            self.assertEqual(contract["output_ceiling"], 2048)

    def test_check_contract_hash_is_the_reviewed_candidate(self):
        self.assertEqual(
            self.manifest["check_contract_hash"],
            "af370e93a021436771dd805b384139c59be592bda677d2675eb1904ea5bfa79b")

    def test_no_placeholder_or_synthetic_identities(self):
        blob = json.dumps(self.manifest, sort_keys=True)
        for marker in ("PENDING", "PLACEHOLDER", "synthetic"):
            self.assertNotIn(marker, blob)
        for name in ("predicate_contract_hash", "extractor_hash",
                     "check_contract_hash(resolution A)"):
            self.assertNotIn(c.sha256_utf8(f"PENDING-PLACEHOLDER:{name}"),
                             blob)

    # ---- call plan and budget --------------------------------------------------

    def test_exact_call_plan_derivation(self):
        plan = derive_call_plan(
            len(self.manifest["ignorance_probe_contract"]
                ["probe_fixture_ids"]),
            len(self.manifest["engine_roster"]))
        self.assertEqual(plan.probe_calls_branch, 15)
        self.assertEqual(plan.s_family_calls_branch, 15)
        self.assertEqual(plan.analog_calls_branch, 90)
        self.assertEqual(plan.primary_calls_branch, 120)
        self.assertEqual(plan.conditional_calls_branch, 105)
        self.assertEqual(plan.ceiling_calls_branch, 225)
        self.assertEqual(plan.roster_ceiling_total, 450)

    def test_budget_recomputes_exactly_from_ledger_rows(self):
        rows = self.ledger["per_branch_rows"]
        self.assertEqual(len(rows), 225)
        for row in rows:
            self.assertEqual(
                row["per_call_total"],
                row["prompt_tokens"] + 2048 + 512,
                f"{row['call_id']}: double count or missing term")
            self.assertEqual(row["completion_request_ceiling"], 2048)
            self.assertEqual(row["controller_source_read_bound"],
                             c.MAX_CONTROLLER_SOURCE_READ_TOKENS)
        branch_total = sum(r["per_call_total"] for r in rows)
        self.assertEqual(branch_total,
                         self.ledger["totals"]["branch_total_tokens"])
        self.assertEqual(2 * branch_total,
                         self.manifest["total_budget_tokens"])
        self.assertEqual(2 * branch_total, self.ledger["totals"]
                         ["roster_total_budget_tokens"])

    def test_budget_row_categories_match_plan(self):
        rows = self.ledger["per_branch_rows"]
        by = lambda cat: [r for r in rows if r["category"] == cat]
        self.assertEqual(len(by("probe")), 15)
        self.assertEqual(len(by("s_family")), 15)
        self.assertEqual(len(by("analog")), 90)
        self.assertEqual(len(by("conditional_s_family")), 15)
        self.assertEqual(len(by("conditional_analog")), 90)

    def test_probes_never_conditional(self):
        for row in self.ledger["per_branch_rows"]:
            if row["category"] == "probe":
                self.assertFalse(row["conditional"])
                self.assertEqual(row["temperature"],
                                 c.CALIBRATION_TEMPERATURE)

    def test_conditional_rows_reuse_primary_prompt_bounds(self):
        rows = self.ledger["per_branch_rows"]
        primary = {(r["fixture_id"], r["lane"]): r["prompt_tokens"]
                   for r in rows if not r["conditional"]
                   and r["category"] != "probe"}
        for row in rows:
            if row["conditional"]:
                self.assertEqual(
                    row["prompt_tokens"],
                    primary[(row["fixture_id"], row["lane"])])
                self.assertEqual(row["temperature"],
                                 c.COLLAPSE_DIAGNOSTIC_TEMPERATURE)

    # ---- population and lineage -------------------------------------------------

    def test_population_declaration_byte_match(self):
        declaration = json.loads(
            (ROOT / "corpus/efc_calibration/authoring_c2/"
                    "population_intent_declaration.json").read_text())
        self.assertEqual(
            population_choice_canonical(self.manifest["population_region"]),
            population_choice_canonical(declaration["population_region"]))
        self.assertEqual(
            c.sha256_utf8(population_choice_canonical(
                self.manifest["population_region"]).decode("utf-8")),
            declaration["canonical_serialization_sha256"])

    def test_fixture_and_oracle_hashes_bind_actual_files(self):
        index = json.loads((ROOT / "episodes/efc_calibration/"
                            "packet_index.json").read_text())
        indexed = {e["id"]: e["sha256"] for e in index["entries"]
                   if e["role"] in ("s_family", "analog")}
        listed = {f["fixture_id"]: f["sha256"]
                  for f in self.manifest["calibration_fixtures"]}
        self.assertEqual(indexed, listed)
        for row in self.manifest["world_oracles"]:
            task_id = row["oracle_id"].removeprefix("efc-cal-oracle-")
            path = (ROOT / "corpus/efc_calibration/oracle"
                    / f"{task_id}.json")
            self.assertEqual(c4.sha256_path(path), row["sha256"])

    def test_report_has_open_blocker_and_candidate_status(self):
        self.assertEqual(self.report["disclosure"]["network_calls"], 0)
        self.assertEqual(self.report["disclosure"]["manifest_status"],
                         "candidate_not_pinned")
        blocking = [b for b in self.report["blockers"] if b["blocking"]]
        self.assertEqual([b["id"] for b in blocking],
                         ["operator_roster_budget_approval"])
        self.assertEqual(self.report["failures"], [])

    def test_builder_is_idempotent(self):
        tmp = tempfile.mkdtemp()
        try:
            c4_copy = Path(tmp) / "authoring_c4"
            shutil.copytree(C4_ROOT, c4_copy)
            prod_hashes = {p.name: c4.sha256_path(p)
                           for p in C4_ROOT.glob("*.json")}

            real_socket = socket.socket

            def _refuse(*a, **k):
                raise AssertionError("C4 builder attempted a network call")

            socket.socket = _refuse
            try:
                with mock.patch.object(c4, "C4_ROOT", c4_copy):
                    self.assertEqual(c4.main(), 0)
                    after_first = {p.name: c4.sha256_path(p)
                                   for p in c4_copy.glob("*.json")}
                    self.assertEqual(c4.main(), 0)
                    after_second = {p.name: c4.sha256_path(p)
                                    for p in c4_copy.glob("*.json")}
            finally:
                socket.socket = real_socket

            self.assertEqual(after_first, after_second)
            after_prod = {p.name: c4.sha256_path(p)
                          for p in C4_ROOT.glob("*.json")}
            self.assertEqual(prod_hashes, after_prod)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
