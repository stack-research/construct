"""Conformance vectors for EFC v1 calibration manifest assembly (D6)."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from harness.efc_fixtures_v1 import FIXTURES_DIR, MANIFEST_PATH as SUITE_MANIFEST_PATH
from harness.efc_manifest_v1 import (MANIFEST_RELPATH, MANIFEST_V2_RELPATH,
                                     PART_I_SPEC_SHA256, SUPERSEDES_PIN_EVENT_ID,
                                     SUPERSESSION_REASON, assemble_manifest,
                                     assemble_manifest_v2, compute_contract_hashes,
                                     compute_check_contract_hash,
                                     compute_extractor_hash,
                                     compute_predicate_contract_hash,
                                     manifest_hash, manifest_verify, sha256_canon,
                                     sha256_path)

REPO_ROOT = Path(__file__).resolve().parents[1]

# Thread-expected pins (cross-check only; assembler recomputes from disk).
# Origin: moderator D6 open entry 20260716T124219514Z + pin event 20260716T085823403Z
EXPECTED_PART_I_SPEC_HASH = (
    "2d37f6bf0cd4aab830cb1dcf5eb9576f13b9acff65b63cd7d5b5fe0ea5b6097d"
)  # notes/SPEC_EPISTEMIC_FRAME_CHECK_V1.md
EXPECTED_COMMITMENT_WIRE_SCHEMA_HASH = (
    "2492f6ea3f50177da3c034174444ca925eeeb9d552a1bd291cf6e56a650114f7"
)  # harness/efc_commitment_wire_v1.schema.json
EXPECTED_COMMITMENT_ORACLE_SCORER_HASH = (
    "e8d17029553693445873c2e3f9f517a777f8ac96fe3303df374c946165db7ef0"
)  # harness/efc_commitment_oracle_v1.py
EXPECTED_ACTION_MENU_COMPOSITION_RULES_HASH = (
    "085f7701408b633385d6383e3fc99230c1116fd4714a6199d724493e6e58d803"
)  # harness/efc_menu_composition_rules_v1.md
EXPECTED_LEAK_AUDIT_CONTRACT_HASH = (
    "1fd0626b892d619723a35cfdeb58fc927d2a8ed7dad081cd460c81fd3f53fbe9"
)  # harness/efc_leak_audit_contract_v1.md
EXPECTED_LEAK_AUDIT_PREDICTOR_HASH = (
    "f0fa52ce50427e94b0134d2d3cf2cb8ec58e499e193b8a2c2387d03187d6a7ed"
)  # canonical_predictor_spec_bytes()
EXPECTED_FOREGROUND_TEMPLATE_HASH = (
    "bda77e1a14d1e006a1e9dec0680535a297225d30af4ab8cda7073bea2b1d132b"
)  # harness/efc_render_v1.py post-D6a repair
EXPECTED_MENU_ONLY_TEMPLATE_HASH = (
    "80fb4d923789d18e575e160ce003511e233798f0ea5c0e4e72e0a88f24e33b9f"
)  # harness/efc_render_v1.py post-D6a repair
EXPECTED_RENDERER_CONTRACT_HASH = (
    "ff72d0456fb9188918aba852b91b39836931f4890dd59d873d707f04205efcbe"
)  # harness/efc_render_v1.py renderer_contract_payload
EXPECTED_PREDICATE_CONTRACT_HASH = (
    "f8c3f07439dfc634c88385b37ec33f6f2ac2df9cd22b4c1960e147d3d6c732ed"
)  # sha256_canon(V0_PREDICATE_FEATURE_BINDINGS) — v0 C4 / efc_artifacts.py
EXPECTED_EXTRACTOR_HASH = (
    "cfe9c05a1509568df4c2aa1cfeeae04b85ef5dc4c4b39ae6c6f2a1bfadd028ce"
)  # raw bytes harness/efc_trigger.py — v0 C4
EXPECTED_CHECK_CONTRACT_HASH = (
    "af370e93a021436771dd805b384139c59be592bda677d2675eb1904ea5bfa79b"
)  # production_check_contract_hash — v0 C4 / efc_compare_production.py

# Suite rows and calibration_fixtures[] both use sha256_canon of attested objects.
EXPECTED_FIXTURE_CANON_SHAS = {
    "efc_v1-mm-01": "09dc0fa783df9c6a52975ee12d309cf55a675c4952027e60d3b6ee83282f30e2",
    "efc_v1-mm-02": "8e8789925b9e85733b0dcb74b64fc187623d5a86833639378c3e447c8bec6ae6",
    "efc_v1-mm-03": "38342eba34abca95a0e7b5853d3d4bfba8b761bf503013f84479ff1edda631fc",
    "efc_v1-mm-04": "6127dedb07fcefbb8cf5089fed9047b2006b5b88f34a9b171f6e8fe8522dd96c",
    "efc_v1-mm-05": "2d4f116b6c5d5911471f12a4a186024f14292ae0bff2ae0dac766af222817fa4",
    "efc_v1-mc-01": "57344788acb91570715da751a707ab118c2deadf9bc072b382f543aac0b452ad",
    "efc_v1-mc-02": "1f751090df1d3af3ddfed971b35c0495ecdd770285560969283dfc0fb322b4e7",
    "efc_v1-mc-03": "136c7e87c5f853542f4cfb7322a088c79a7d02fb324e9a2b7309d3dde07a851c",
    "efc_v1-mc-04": "a6e7464d8a8739af1fc2f79caaa8b1b775517693087b710543917142ea184192",
    "efc_v1-mc-05": "ef0b160026f6c99d4513b834bb9d6c044ab40908618956d586a3340657df4d9e",
    "efc_v1-ir-01": "0d817ff73731ffbe974e76e4e1ed23f64af2cc5948108f8bdbaf05edf3b1a772",
    "efc_v1-ir-02": "a7d29f968e0bbb288405a10a94b9f85bea44cf63f63d08b18b274ce0cb0e2d01",
    "efc_v1-ir-03": "4aa7f7cde7c16d77a75c8e3b15ee561cd47a6fedd588e796521fbfec2ce56a4c",
    "efc_v1-ir-04": "8b64dcbdfe7bb3738e07601b173076c96c11625896f7b0c4df8c29029d8d6aa5",
    "efc_v1-ir-05": "12f0581dd1fb4d078a874ea4594063547d5f8248b0052af4b371e582f2cab140",
}

EXPECTED_FIXTURE_RAW_BYTES_SHAS = {
    # Named raw-file-bytes integrity pin (differs from canon by definition)
    "efc_v1-mm-01": "1929d1cc77c320e5c5ebf78fcd4b5994fd6e406d1601691bda8278a3f2929376",
    "efc_v1-mm-02": "3dcd9af4a6018b2039f24bbda7624e63f40c0c10c0e1beb4211303e4e034af13",
    "efc_v1-mm-03": "d4993f052d7ec811dc7537a7efeeb31330b5aba98778d052da76b5097623b293",
    "efc_v1-mm-04": "0336049d7468f6ac45f7e1bfd2ccca9f13e1afb2dd7eeb8ec96174fd1de87026",
    "efc_v1-mm-05": "aaf06ab2950fdebb6f99460572232de3489f2c0091acea1b6dc1e11419d52247",
    "efc_v1-mc-01": "2e985dddd36a5edf070702f08fb377bb4923644ca92684172b92f05d5ac49024",
    "efc_v1-mc-02": "e65c849b740283296d373af65c85bcd38a4bcdfc30f4a9712630673fea8a6263",
    "efc_v1-mc-03": "706a21a57981eee5878639986f17f8252db72b9c12d3f09adbcc66cd24afd2fe",
    "efc_v1-mc-04": "a001acd1d33ccfd17aed9006c304fef86e000fbd7d2a9d83d86797ef7aa34290",
    "efc_v1-mc-05": "0c0862032114709ddc06c52516a668a17e76767c6086dfb49411bef5bfcf97bf",
    "efc_v1-ir-01": "45100d09ea9b621993a419a3965f1c72451774a555d73444736f792f0102ec3c",
    "efc_v1-ir-02": "02f1b0acb9073d30b306f55cf7b1cb08c82f9e56ee196ffcfa7e087da3448b9b",
    "efc_v1-ir-03": "2ee351c8b92330adedf6bb3f067868cf1a70a85a668cc85c5f29d3458ea1acf8",
    "efc_v1-ir-04": "64be560bff05037e2f12d529235feeb5a856fc114bbe74b538060724fb73e1a4",
    "efc_v1-ir-05": "9b2508e88dfc7aa81793b1483bba2a3157fa1577d3d3b4cfac3275e01c67869f",
}


def _copy_corpus_tree(tmp: Path) -> Path:
    corpus_root = tmp / "corpus" / "efc_calibration_v1"
    shutil.copytree(
        REPO_ROOT / "corpus" / "efc_calibration_v1",
        corpus_root,
        dirs_exist_ok=True,
    )
    spec_dir = tmp / "notes"
    spec_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        REPO_ROOT / "notes" / "SPEC_EPISTEMIC_FRAME_CHECK_V1.md",
        spec_dir / "SPEC_EPISTEMIC_FRAME_CHECK_V1.md",
    )
    harness_dir = tmp / "harness"
    harness_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "efc_commitment_wire_v1.schema.json",
        "efc_commitment_oracle_v1.py",
        "efc_menu_composition_rules_v1.md",
        "efc_leak_audit_contract_v1.md",
        "efc_render_v1.py",
        "efc_render_contract_v1.md",
        "efc_contracts.py",
        "efc_fixtures_v1.py",
        "efc_leak_audit_v1.py",
        "efc_menu_composition_v1.py",
        "efc_commitment_wire_v1.py",
        "efc_trigger.py",
        "efc_carrier.py",
        "efc_artifacts.py",
        "efc_check.py",
        "efc_compare_production.py",
        "efc_compare_version.py",
    ):
        shutil.copy2(REPO_ROOT / "harness" / name, harness_dir / name)
    return tmp


class TestHashRecomputation(unittest.TestCase):
    def test_thread_expected_pins_match_disk(self):
        hashes = compute_contract_hashes(REPO_ROOT)
        self.assertEqual(hashes["part_i_spec_hash"], EXPECTED_PART_I_SPEC_HASH)
        self.assertEqual(hashes["part_i_spec_hash"], PART_I_SPEC_SHA256)
        self.assertEqual(
            hashes["commitment_wire_schema_hash"],
            EXPECTED_COMMITMENT_WIRE_SCHEMA_HASH,
        )
        self.assertEqual(
            hashes["commitment_oracle_scorer_hash"],
            EXPECTED_COMMITMENT_ORACLE_SCORER_HASH,
        )
        self.assertEqual(
            hashes["action_menu_composition_rules_hash"],
            EXPECTED_ACTION_MENU_COMPOSITION_RULES_HASH,
        )
        self.assertEqual(
            hashes["leak_audit_contract_hash"],
            EXPECTED_LEAK_AUDIT_CONTRACT_HASH,
        )
        self.assertEqual(
            hashes["leak_audit_predictor_hash"],
            EXPECTED_LEAK_AUDIT_PREDICTOR_HASH,
        )
        self.assertEqual(
            hashes["foreground_template_hash"],
            EXPECTED_FOREGROUND_TEMPLATE_HASH,
        )
        self.assertEqual(
            hashes["menu_only_template_hash"],
            EXPECTED_MENU_ONLY_TEMPLATE_HASH,
        )
        self.assertEqual(
            hashes["renderer_contract_hash"],
            EXPECTED_RENDERER_CONTRACT_HASH,
        )
        self.assertEqual(
            hashes["predicate_contract_hash"],
            EXPECTED_PREDICATE_CONTRACT_HASH,
        )
        self.assertEqual(
            hashes["extractor_hash"],
            EXPECTED_EXTRACTOR_HASH,
        )
        self.assertEqual(
            hashes["check_contract_hash"],
            EXPECTED_CHECK_CONTRACT_HASH,
        )
        self.assertEqual(
            compute_predicate_contract_hash(),
            EXPECTED_PREDICATE_CONTRACT_HASH,
        )
        self.assertEqual(
            compute_extractor_hash(REPO_ROOT),
            EXPECTED_EXTRACTOR_HASH,
        )
        self.assertEqual(
            compute_check_contract_hash(),
            EXPECTED_CHECK_CONTRACT_HASH,
        )

    def test_fixture_canon_shas_recompute_from_disk(self):
        for fixture_id, expected in EXPECTED_FIXTURE_CANON_SHAS.items():
            obj = json.loads(
                (FIXTURES_DIR / f"{fixture_id}.json").read_text(encoding="utf-8")
            )
            self.assertEqual(sha256_canon(obj), expected)

    def test_fixture_raw_bytes_shas_recompute_from_disk(self):
        for fixture_id, expected in EXPECTED_FIXTURE_RAW_BYTES_SHAS.items():
            disk = sha256_path(FIXTURES_DIR / f"{fixture_id}.json")
            self.assertEqual(disk, expected)

    def test_suite_manifest_fixture_rows_match_sha256_canon_of_attested_fixtures(self):
        """Suite rows are live sha256_canon pins, not stale pre-attestation residues."""
        suite = json.loads(SUITE_MANIFEST_PATH.read_text(encoding="utf-8"))
        for entry in suite["fixtures"]:
            fixture_id = entry["fixture_id"]
            obj = json.loads(
                (FIXTURES_DIR / f"{fixture_id}.json").read_text(encoding="utf-8")
            )
            canon = sha256_canon(obj)
            self.assertEqual(entry["fixture_sha256"], EXPECTED_FIXTURE_CANON_SHAS[fixture_id])
            self.assertEqual(entry["fixture_sha256"], canon)
            self.assertNotEqual(
                entry["fixture_sha256"],
                EXPECTED_FIXTURE_RAW_BYTES_SHAS[fixture_id],
            )


class TestManifestAssembly(unittest.TestCase):
    def test_assembly_is_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_corpus_tree(Path(tmp))
            out = root / "calibration_manifest_v1.json"
            _, first = assemble_manifest(root=root, output_path=out)
            _, second = assemble_manifest(root=root, output_path=out)
            self.assertEqual(first, second)

    def test_live_manifest_verify_passes(self):
        manifest_path = REPO_ROOT / MANIFEST_RELPATH
        if not manifest_path.is_file():
            assemble_manifest(root=REPO_ROOT)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        result = manifest_verify(manifest, root=REPO_ROOT, render_repeats=3)
        self.assertTrue(result.ok, result.failures)
        self.assertIsNotNone(result.manifest_hash)


class TestRefusalVectors(unittest.TestCase):
    def _assemble_in_temp(self, tmp: Path) -> dict:
        root = _copy_corpus_tree(tmp)
        out = root / "calibration_manifest_v1.json"
        manifest, _ = assemble_manifest(root=root, output_path=out)
        return manifest

    def test_tampered_fixture_byte_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_corpus_tree(Path(tmp))
            out = root / "calibration_manifest_v1.json"
            manifest, _ = assemble_manifest(root=root, output_path=out)
            fixture_path = (
                root / "corpus/efc_calibration_v1/fixtures/efc_v1-mm-01.json"
            )
            data = json.loads(fixture_path.read_text(encoding="utf-8"))
            data["task_body"] = data["task_body"] + " tamper"
            fixture_path.write_text(
                json.dumps(data, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            result = manifest_verify(manifest, root=root, render_repeats=1)
            self.assertFalse(result.ok)
            self.assertTrue(
                any("hash_mismatch:fixture:efc_v1-mm-01" in f for f in result.failures)
            )

    def test_missing_attestation_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_corpus_tree(Path(tmp))
            out = root / "calibration_manifest_v1.json"
            manifest, _ = assemble_manifest(root=root, output_path=out)
            fixture_path = (
                root / "corpus/efc_calibration_v1/fixtures/efc_v1-mm-01.json"
            )
            data = json.loads(fixture_path.read_text(encoding="utf-8"))
            data.pop("plausibility_attestation", None)
            fixture_path.write_text(
                json.dumps(data, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            result = manifest_verify(manifest, root=root, render_repeats=1)
            self.assertFalse(result.ok)
            self.assertTrue(
                any("integrity_refused" in f for f in result.failures)
            )

    def test_wrong_spec_hash_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._assemble_in_temp(Path(tmp))
            root = Path(tmp)
            manifest = copy.deepcopy(manifest)
            manifest["part_i_spec_hash"] = "0" * 64
            result = manifest_verify(manifest, root=root, render_repeats=1)
            self.assertFalse(result.ok)
            self.assertTrue(
                any(f.startswith("hash_mismatch:part_i_spec_hash") for f in result.failures)
            )

    def test_tampered_predicate_contract_hash_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._assemble_in_temp(Path(tmp))
            manifest = copy.deepcopy(manifest)
            manifest["predicate_contract_hash"] = "0" * 64
            result = manifest_verify(manifest, root=Path(tmp), render_repeats=1)
            self.assertFalse(result.ok)
            self.assertTrue(
                any(f.startswith("hash_mismatch:predicate_contract_hash") for f in result.failures)
            )

    def test_tampered_extractor_hash_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._assemble_in_temp(Path(tmp))
            manifest = copy.deepcopy(manifest)
            manifest["extractor_hash"] = "0" * 64
            result = manifest_verify(manifest, root=Path(tmp), render_repeats=1)
            self.assertFalse(result.ok)
            self.assertTrue(
                any(f.startswith("hash_mismatch:extractor_hash") for f in result.failures)
            )

    def test_tampered_check_contract_hash_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._assemble_in_temp(Path(tmp))
            manifest = copy.deepcopy(manifest)
            manifest["check_contract_hash"] = "0" * 64
            result = manifest_verify(manifest, root=Path(tmp), render_repeats=1)
            self.assertFalse(result.ok)
            self.assertTrue(
                any(f.startswith("hash_mismatch:check_contract_hash") for f in result.failures)
            )


class TestBudgetLedger(unittest.TestCase):
    def test_budget_fields_self_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = TestRefusalVectors()._assemble_in_temp(Path(tmp))
            budget = manifest["budget_ledger"]
            self.assertEqual(budget["total_call_ceiling"], 258)
            self.assertLessEqual(budget["input_token_ceiling"], 250_000)
            self.assertLessEqual(budget["output_token_ceiling"], 16_330)
            cost = (
                budget["input_token_ceiling"]
                * budget["pricing"]["input_usd_per_million"]
                / 1_000_000
                + budget["output_token_ceiling"]
                * budget["pricing"]["output_usd_per_million"]
                / 1_000_000
            )
            self.assertAlmostEqual(cost, budget["worst_case_cost_usd"])
            self.assertLessEqual(budget["worst_case_cost_usd"], 1.00)


class TestManifestV2Assembly(unittest.TestCase):
    SOL_V2_BUDGET_FIELDS = {
        "total_call_ceiling": 288,
        "calls_already_spent": 33,
        "calls_remaining_ceiling": 255,
        "wire_probe_calls_completed": 2,
        "wire_probe_calls_rejected": 1,
        "wire_probe_tokens": {"input": 18, "output": 10, "total": 28},
        "pilot_calls_spent": 30,
        "pilot_tokens": {"input": 4827, "output": 1078},
        "opening_input_tokens_spent": 4845,
        "opening_output_tokens_spent": 1088,
        "opening_cost_usd": 0.0284325,
        "max_output_tokens_per_request": 256,
        "input_token_ceiling": 250_000,
        "output_token_ceiling": 66_368,
        "output_ceiling_derivation": (
            "1,088 output tokens already spent + 255 remaining calls × 256 "
            "max_output_tokens = 66,368"
        ),
        "worst_case_cost_usd": 1.62052,
        "hard_cost_ceiling_usd": 3.00,
        "headroom_below_hard_ceiling_usd": 1.37948,
        "stop_before_crossing": True,
        "budget_refusal_typed_outcome": "budget_refusal",
    }

    def test_v2_assembly_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_corpus_tree(Path(tmp))
            out = root / "calibration_manifest_v2.json"
            _, first = assemble_manifest_v2(root=root, output_path=out)
            _, second = assemble_manifest_v2(root=root, output_path=out)
            self.assertEqual(first, second)

    def test_v2_supersedes_and_sol_table_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_corpus_tree(Path(tmp))
            out = root / "calibration_manifest_v2.json"
            manifest, _ = assemble_manifest_v2(root=root, output_path=out)
            self.assertEqual(manifest["supersedes"], SUPERSEDES_PIN_EVENT_ID)
            self.assertEqual(manifest["supersession_reason"], SUPERSESSION_REASON)
            self.assertEqual(manifest["decoding_contract"]["max_output_tokens"], 256)
            budget = manifest["budget_ledger"]
            for key, value in self.SOL_V2_BUDGET_FIELDS.items():
                self.assertEqual(budget[key], value, key)
            self.assertEqual(
                budget["pricing"]["input_usd_per_million"],
                2.50,
            )
            self.assertEqual(
                budget["pricing"]["output_usd_per_million"],
                15.00,
            )

    def test_v2_contract_pins_match_v1_assembly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_corpus_tree(Path(tmp))
            v1, _ = assemble_manifest(
                root=root,
                output_path=root / "calibration_manifest_v1.json",
            )
            v2, _ = assemble_manifest_v2(
                root=root,
                output_path=root / "calibration_manifest_v2.json",
            )
            pin_fields = (
                "part_i_spec_hash",
                "commitment_wire_schema_hash",
                "commitment_oracle_scorer_hash",
                "renderer_contract_hash",
                "foreground_template_hash",
                "menu_only_template_hash",
                "calibration_fixtures",
                "suite_manifest_sha256",
            )
            for field in pin_fields:
                self.assertEqual(v1[field], v2[field], field)

    def test_v2_manifest_verify_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_corpus_tree(Path(tmp))
            out = root / "calibration_manifest_v2.json"
            manifest, _ = assemble_manifest_v2(root=root, output_path=out)
            result = manifest_verify(manifest, root=root, render_repeats=2)
            self.assertTrue(result.ok, result.failures)
            self.assertIsNotNone(result.manifest_hash)

    def test_emit_live_repo_v2_manifest(self):
        """Emit corpus v2 artifact (new file; v1 bytes untouched)."""
        v1_before = (REPO_ROOT / MANIFEST_RELPATH).read_bytes()
        out = REPO_ROOT / MANIFEST_V2_RELPATH
        manifest, rendered = assemble_manifest_v2(root=REPO_ROOT, output_path=out)
        self.assertTrue(out.is_file())
        v1_after = (REPO_ROOT / MANIFEST_RELPATH).read_bytes()
        self.assertEqual(v1_before, v1_after)
        self.assertNotEqual(
            manifest_hash(manifest),
            manifest_hash(
                json.loads((REPO_ROOT / MANIFEST_RELPATH).read_text())
            ),
        )
        self._v2_canonical_hash = manifest_hash(manifest)
        self._v2_rendered = rendered


class TestCorpusUntouched(unittest.TestCase):
    def test_full_module_run_never_mutates_live_fixtures(self):
        before = {p: p.read_bytes() for p in sorted(FIXTURES_DIR.glob("*.json"))}
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_corpus_tree(Path(tmp))
            out = root / "calibration_manifest_v1.json"
            manifest, _ = assemble_manifest(root=root, output_path=out)
            result = manifest_verify(manifest, root=root, render_repeats=2)
            self.assertTrue(result.ok, result.failures)
        after = {p: p.read_bytes() for p in sorted(FIXTURES_DIR.glob("*.json"))}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
