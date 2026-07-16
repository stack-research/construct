"""Conformance vectors for EFC v1 integrity-lanes pilot runner."""

from __future__ import annotations

import copy
import json
import shutil
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness.efc_intervals import newcombe_diff_interval
from harness.efc_manifest_v1 import manifest_hash, sha256_path
from harness.efc_pilot_runner_v1 import (
    PIN_EVENT_ID,
    PIN_SIDECAR_RELPATH,
    RUNNER_DISCLOSURES,
    BudgetRefusal,
    BudgetState,
    CallContext,
    FailingTransport,
    MockTransport,
    PilotRunnerRefusal,
    RejectThenSuccessTransport,
    TransportRefusal,
    check_budget_actual,
    check_budget_guard,
    detect_solicitation,
    evaluate_menu_ceiling_gate,
    evaluate_menu_only_solicitation_gate,
    load_budget_state,
    load_pinned_manifest,
    main,
    menu_ceiling_headroom_lower_bound,
    run_integrity_pilot,
    verify_pin_sidecar,
)

ROOT = Path(__file__).resolve().parents[1]


class _RefusingSocket(socket.socket):
    def __init__(self, *a, **k):
        raise AssertionError("pilot runner test attempted a network call")


class SocketRefusalMixin:
    @classmethod
    def setUpClass(cls):
        cls._real_socket = socket.socket
        socket.socket = _RefusingSocket

    @classmethod
    def tearDownClass(cls):
        socket.socket = cls._real_socket


def _copy_repo_tree(tmp: Path) -> Path:
    for rel in (
        "corpus/efc_calibration_v1",
        "notes/SPEC_EPISTEMIC_FRAME_CHECK_V1.md",
        "harness/efc_commitment_wire_v1.schema.json",
        "harness/efc_commitment_oracle_v1.py",
        "harness/efc_menu_composition_rules_v1.md",
        "harness/efc_leak_audit_contract_v1.md",
        "harness/efc_trigger.py",
        "harness/efc_carrier.py",
        "harness/efc_artifacts.py",
        "harness/efc_check.py",
        "harness/efc_compare_production.py",
        "harness/efc_contracts.py",
        "harness/efc_fixtures_v1.py",
        "harness/efc_leak_audit_v1.py",
        "harness/efc_menu_composition_v1.py",
        "harness/efc_render_v1.py",
        "harness/efc_commitment_wire_v1.py",
        "harness/efc_manifest_v1.py",
        "harness/efc_intervals.py",
        "harness/efc_pilot_runner_v1.py",
    ):
        src = ROOT / rel
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    return tmp


def _corpus_hashes(root: Path) -> dict[str, str]:
    corpus = root / "corpus" / "efc_calibration_v1"
    out: dict[str, str] = {}
    for path in sorted(corpus.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(root))] = sha256_path(path)
    return out


class TestConstructionRefusal(SocketRefusalMixin, unittest.TestCase):
    def test_verify_fail_refuses(self):
        box = Path(tempfile.mkdtemp(prefix="efc-pilot-"))
        self.addCleanup(shutil.rmtree, box, ignore_errors=True)
        _copy_repo_tree(box)
        manifest = json.loads(
            (box / "corpus/efc_calibration_v1/calibration_manifest_v1.json"
             ).read_text()
        )
        manifest["calibration_fixtures"][0]["sha256"] = "0" * 64
        (box / "corpus/efc_calibration_v1/calibration_manifest_v1.json"
         ).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        with self.assertRaises(PilotRunnerRefusal) as ctx:
            load_pinned_manifest(box)
        self.assertIn("manifest_verify_failed", str(ctx.exception.detail))

    def test_missing_pin_sidecar_refuses(self):
        box = Path(tempfile.mkdtemp(prefix="efc-pilot-"))
        self.addCleanup(shutil.rmtree, box, ignore_errors=True)
        _copy_repo_tree(box)
        (box / PIN_SIDECAR_RELPATH).unlink()
        with self.assertRaises(PilotRunnerRefusal) as ctx:
            load_pinned_manifest(box)
        self.assertEqual(ctx.exception.detail, "pin_sidecar_missing")

    def test_mismatched_pin_hash_refuses(self):
        box = Path(tempfile.mkdtemp(prefix="efc-pilot-"))
        self.addCleanup(shutil.rmtree, box, ignore_errors=True)
        _copy_repo_tree(box)
        pin = json.loads((box / PIN_SIDECAR_RELPATH).read_text())
        pin["manifest_hash_canonical"] = "0" * 64
        (box / PIN_SIDECAR_RELPATH).write_text(
            json.dumps(pin, indent=2, sort_keys=True) + "\n"
        )
        manifest = json.loads(
            (box / "corpus/efc_calibration_v1/calibration_manifest_v1.json"
             ).read_text()
        )
        ok, reason = verify_pin_sidecar(box, manifest)
        self.assertFalse(ok)
        self.assertIn("pin_hash_mismatch", reason)


class TestBudgetGuard(unittest.TestCase):
    def _state(self, **overrides) -> BudgetState:
        base = BudgetState(
            calls_spent=3,
            input_tokens_spent=18,
            output_tokens_spent=10,
            input_token_ceiling=250_000,
            output_token_ceiling=16_330,
            total_call_ceiling=258,
            max_output_tokens_per_request=64,
            hard_cost_ceiling_usd=1.0,
            input_usd_per_million=2.5,
            output_usd_per_million=15.0,
        )
        for key, value in overrides.items():
            object.__setattr__(base, key, value)
        return base

    def test_calls_pool_boundary(self):
        state = self._state(calls_spent=258)
        refusal = check_budget_guard(state, projected_input_tokens=100)
        self.assertIsInstance(refusal, BudgetRefusal)
        self.assertEqual(refusal.pool, "calls")

    def test_input_pool_boundary(self):
        state = self._state(input_tokens_spent=250_000)
        refusal = check_budget_guard(state, projected_input_tokens=250_001)
        self.assertIsInstance(refusal, BudgetRefusal)
        self.assertEqual(refusal.pool, "input_tokens")

    def test_output_pool_boundary(self):
        state = self._state(output_tokens_spent=16_330 - 64 + 1)
        refusal = check_budget_guard(state, projected_input_tokens=100)
        self.assertIsInstance(refusal, BudgetRefusal)
        self.assertEqual(refusal.pool, "output_tokens")

    def test_cost_pool_boundary(self):
        state = self._state(
            input_tokens_spent=200_000,
            output_tokens_spent=10_000,
            hard_cost_ceiling_usd=0.60,
        )
        refusal = check_budget_guard(state, projected_input_tokens=250_000)
        self.assertIsInstance(refusal, BudgetRefusal)
        self.assertEqual(refusal.pool, "cost_usd")

    def test_actual_input_ceiling_at_crossing(self):
        state = self._state(input_tokens_spent=250_000)
        refusal = check_budget_actual(state)
        self.assertIsInstance(refusal, BudgetRefusal)
        self.assertEqual(refusal.pool, "input_tokens")


class TestPostCallBudgetEnforcement(SocketRefusalMixin, unittest.TestCase):
    def _run_with_budget(
        self,
        budget: BudgetState,
        transport: MockTransport,
    ) -> dict:
        manifest = load_pinned_manifest(ROOT)
        out = Path(tempfile.mkdtemp(prefix="efc-pilot-budget-"))
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        ledger = out / "pilot.jsonl"
        with patch(
            "harness.efc_pilot_runner_v1.load_budget_state",
            return_value=budget,
        ):
            return run_integrity_pilot(
                root=ROOT,
                transport=transport,
                manifest=manifest,
                ledger_path=ledger,
                timestamp_fn=lambda: "2026-07-16T14:00:00+00:00",
            ), ledger

    def test_mid_run_overshoot_halts_at_crossing_row(self):
        """Grok scenario 1: estimate passes, actual crosses — halt on that row."""
        budget = BudgetState(
            calls_spent=3,
            input_tokens_spent=249_500,
            output_tokens_spent=10,
            input_token_ceiling=250_000,
            output_token_ceiling=16_330,
            total_call_ceiling=258,
            max_output_tokens_per_request=64,
            hard_cost_ceiling_usd=1.0,
            input_usd_per_million=2.5,
            output_usd_per_million=15.0,
        )
        transport = MockTransport(usage_overrides=[(600, 1)])
        result, ledger = self._run_with_budget(budget, transport)
        self.assertEqual(result["status"], "budget_refusal")
        self.assertEqual(result["rows_written"], 1)
        self.assertEqual(transport.call_count, 1)
        row = json.loads(ledger.read_text().strip().splitlines()[0])
        self.assertEqual(row["call_outcome"], "over_ceiling")
        self.assertTrue(row["over_ceiling"])
        self.assertEqual(row["validation_outcome"], "budget_refusal")
        self.assertGreaterEqual(
            row["budget_state"]["input_tokens_spent"], 250_000
        )

    def test_accumulation_halts_at_crossing_call_not_next(self):
        """Grok scenario 2: 20k/call from I=18 — halt on call 13, not call 14."""
        budget = BudgetState(
            calls_spent=3,
            input_tokens_spent=18,
            output_tokens_spent=10,
            input_token_ceiling=250_000,
            output_token_ceiling=16_330,
            total_call_ceiling=258,
            max_output_tokens_per_request=64,
            hard_cost_ceiling_usd=1.0,
            input_usd_per_million=2.5,
            output_usd_per_million=15.0,
        )
        transport = MockTransport(
            usage_overrides=[(20_000, 1)] * 20,
        )
        result, ledger = self._run_with_budget(budget, transport)
        self.assertEqual(result["status"], "budget_refusal")
        self.assertEqual(transport.call_count, 13)
        self.assertEqual(result["rows_written"], 13)
        last = json.loads(ledger.read_text().strip().splitlines()[-1])
        self.assertEqual(last["call_outcome"], "over_ceiling")
        self.assertGreaterEqual(last["budget_state"]["input_tokens_spent"], 250_000)
        completed = [
            json.loads(line)
            for line in ledger.read_text().strip().splitlines()[:-1]
        ]
        for row in completed:
            self.assertEqual(row["call_outcome"], "completed")
            self.assertLess(row["budget_state"]["input_tokens_spent"], 250_000)

    def test_last_call_spike_yields_budget_refusal_not_completed(self):
        """Grok scenario 3: spike on final call — status budget_refusal."""
        budget = BudgetState(
            calls_spent=3,
            input_tokens_spent=18,
            output_tokens_spent=10,
            input_token_ceiling=250_000,
            output_token_ceiling=16_330,
            total_call_ceiling=258,
            max_output_tokens_per_request=64,
            hard_cost_ceiling_usd=1.0,
            input_usd_per_million=2.5,
            output_usd_per_million=15.0,
        )
        transport = MockTransport(
            usage_overrides=[(100, 1)] * 29 + [(250_000, 1)],
        )
        result, ledger = self._run_with_budget(budget, transport)
        self.assertEqual(result["status"], "budget_refusal")
        self.assertNotEqual(result["status"], "completed")
        self.assertEqual(transport.call_count, 30)
        self.assertEqual(result["rows_written"], 30)
        last = json.loads(ledger.read_text().strip().splitlines()[-1])
        self.assertEqual(last["call_outcome"], "over_ceiling")
        self.assertGreaterEqual(
            result["budget_final"]["input_tokens_spent"], 250_000
        )


class TestTransportAccounting(SocketRefusalMixin, unittest.TestCase):
    def test_failing_transport_writes_row_and_counts_call(self):
        manifest = load_pinned_manifest(ROOT)
        transport = FailingTransport(detail="simulated_http_429", http_status=429)
        out = Path(tempfile.mkdtemp(prefix="efc-pilot-transport-"))
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        ledger = out / "pilot.jsonl"
        result = run_integrity_pilot(
            root=ROOT,
            transport=transport,
            manifest=manifest,
            ledger_path=ledger,
            timestamp_fn=lambda: "2026-07-16T14:00:00+00:00",
        )
        self.assertEqual(result["status"], "transport_refusal")
        self.assertEqual(transport.call_count, 1)
        self.assertEqual(result["rows_written"], 1)
        row = json.loads(ledger.read_text().strip())
        self.assertEqual(row["call_outcome"], "transport_rejected")
        self.assertEqual(row["budget_state"]["calls_spent"], 4)
        self.assertEqual(row["usage"], {"input_tokens": 0, "output_tokens": 0})

    def test_reject_then_success_sequence_counts_two_calls_two_rows(self):
        manifest = load_pinned_manifest(ROOT)
        budget = load_budget_state(manifest)
        transport = RejectThenSuccessTransport()
        body = {"model": "test", "input": []}
        ctx = CallContext(
            fixture_id="f1",
            lane="M_menu_only",
            stratum="match_mismatch",
            expected_commitment_enum="A",
            action_set=("A", "B"),
        )
        rows: list[dict] = []
        for _ in range(2):
            try:
                result = transport.call(body, ctx)
            except TransportRefusal as exc:
                budget.calls_spent += 1
                rows.append(
                    {
                        "call_outcome": "transport_rejected",
                        "calls_spent": budget.calls_spent,
                        "detail": exc.detail,
                    }
                )
                continue
            budget.calls_spent += 1
            rows.append(
                {
                    "call_outcome": "completed",
                    "calls_spent": budget.calls_spent,
                    "input_tokens": result.input_tokens,
                }
            )
        self.assertEqual(transport.call_count, 2)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["call_outcome"], "transport_rejected")
        self.assertEqual(rows[1]["call_outcome"], "completed")
        self.assertEqual(rows[0]["calls_spent"], 4)
        self.assertEqual(rows[1]["calls_spent"], 5)


class TestRunnerDisclosure(SocketRefusalMixin, unittest.TestCase):
    def test_run_report_carries_disclosure(self):
        manifest = load_pinned_manifest(ROOT)
        out = Path(tempfile.mkdtemp(prefix="efc-pilot-disc-"))
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        result = run_integrity_pilot(
            root=ROOT,
            transport=MockTransport(),
            manifest=manifest,
            ledger_path=out / "pilot.jsonl",
            timestamp_fn=lambda: "2026-07-16T14:00:00+00:00",
        )
        self.assertEqual(result["disclosure"], list(RUNNER_DISCLOSURES))
        self.assertTrue(
            any("lexical floor" in d for d in result["disclosure"])
        )
        self.assertTrue(
            any("T0.7" in d or "T0.7" in d.replace("-", "") or "0.7" in d
                for d in result["disclosure"])
        )


class TestGateArithmetic(unittest.TestCase):
    def test_sol_worked_examples(self):
        lo0, _ = newcombe_diff_interval(5, 5, 0, 5, 0.95)
        lo1, _ = newcombe_diff_interval(5, 5, 1, 5, 0.95)
        self.assertAlmostEqual(lo0, 0.385549, places=5)
        self.assertAlmostEqual(lo1, 0.192591, places=5)
        self.assertGreaterEqual(lo0, 0.25)
        self.assertLess(lo1, 0.25)

    def test_menu_ceiling_vectors(self):
        params = {
            "K": 5,
            "confidence": 0.95,
            "headroom_margin": 0.25,
            "fail_condition_1_B_obs_gte": 0.80,
        }

        def rows(passes: int) -> list[dict]:
            return [
                {
                    "lane": "M_task_menu",
                    "stratum": "match_mismatch",
                    "oracle_outcome": "pass" if i < passes else "fail",
                    "validation_outcome": "commitment_valid",
                }
                for i in range(5)
            ]

        pass_gate = evaluate_menu_ceiling_gate(rows(0), params)
        self.assertTrue(pass_gate["passed"])
        self.assertAlmostEqual(
            pass_gate["headroom_lower_bound"],
            menu_ceiling_headroom_lower_bound(0, k=5, confidence=0.95),
        )

        fail_gate = evaluate_menu_ceiling_gate(rows(1), params)
        self.assertFalse(fail_gate["passed"])
        self.assertEqual(fail_gate["verdict"], "confounded(menu_ceiling)")

    def test_menu_only_solicitation_ceiling(self):
        rows = [
            {
                "lane": "M_menu_only",
                "stratum": "match_mismatch",
                "solicitation_detected": True,
                "validation_outcome": "commitment_valid",
            }
        ]
        gate = evaluate_menu_only_solicitation_gate(rows)
        self.assertFalse(gate["passed"])
        self.assertIn("confounded(menu_induces_checking", gate["verdict"])


class TestSolicitationDetector(unittest.TestCase):
    def test_tool_call_positive(self):
        raw = {"output": [{"type": "function_call", "name": "check"}]}
        self.assertTrue(
            detect_solicitation(raw=raw, text="{}", validation_outcome="commitment_valid")
        )

    def test_verify_prose_positive(self):
        raw = {"output_text": "Please verify the source before committing."}
        self.assertTrue(
            detect_solicitation(
                raw=raw,
                text=raw["output_text"],
                validation_outcome="commitment_valid",
            )
        )


class TestPilotRun(SocketRefusalMixin, unittest.TestCase):
    def test_full_dry_run_green(self):
        manifest = load_pinned_manifest(ROOT)
        transport = MockTransport()
        out = Path(tempfile.mkdtemp(prefix="efc-pilot-run-"))
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        ledger = out / "pilot.jsonl"
        fixed_ts = iter(["2026-07-16T14:00:00+00:00"] * 100)
        result = run_integrity_pilot(
            root=ROOT,
            transport=transport,
            manifest=manifest,
            ledger_path=ledger,
            timestamp_fn=lambda: next(fixed_ts),
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["invocations"], 30)
        self.assertEqual(result["rows_written"], 30)
        self.assertEqual(result["disclosure"], list(RUNNER_DISCLOSURES))
        self.assertTrue(result["gates"]["menu_ceiling"]["passed"])
        self.assertTrue(result["gates"]["menu_only_solicitation"]["passed"])
        lines = ledger.read_text().strip().splitlines()
        self.assertEqual(len(lines), 30)
        row0 = json.loads(lines[0])
        self.assertEqual(row0["schema_version"], "efc_pilot_runner_ledger_v1")
        self.assertEqual(row0["call_outcome"], "completed")
        self.assertIn("budget_state", row0)

    def test_ledger_append_only_refusal(self):
        manifest = load_pinned_manifest(ROOT)
        transport = MockTransport()
        out = Path(tempfile.mkdtemp(prefix="efc-pilot-run-"))
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        ledger = out / "pilot.jsonl"
        ledger.write_text("{}\n")
        with self.assertRaises(PilotRunnerRefusal):
            run_integrity_pilot(
                root=ROOT,
                transport=transport,
                manifest=manifest,
                ledger_path=ledger,
            )

    def test_ledger_determinism(self):
        manifest = load_pinned_manifest(ROOT)
        fixed_ts = iter(["2026-07-16T14:00:00+00:00"] * 100)

        def run_once() -> list[dict]:
            transport = MockTransport()
            out = Path(tempfile.mkdtemp(prefix="efc-pilot-det-"))
            ledger = out / "pilot.jsonl"
            run_integrity_pilot(
                root=ROOT,
                transport=transport,
                manifest=manifest,
                ledger_path=ledger,
                timestamp_fn=lambda: next(iter(["2026-07-16T14:00:00+00:00"] * 100)),
            )
            rows = [json.loads(line) for line in ledger.read_text().splitlines()]
            shutil.rmtree(out, ignore_errors=True)
            for row in rows:
                row.pop("timestamp_utc", None)
            return rows

        self.assertEqual(run_once(), run_once())

    def test_corpus_untouched(self):
        before = _corpus_hashes(ROOT)
        manifest = load_pinned_manifest(ROOT)
        out = Path(tempfile.mkdtemp(prefix="efc-pilot-corpus-"))
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        run_integrity_pilot(
            root=ROOT,
            transport=MockTransport(),
            manifest=manifest,
            ledger_path=out / "pilot.jsonl",
            timestamp_fn=lambda: "2026-07-16T14:00:00+00:00",
        )
        after = _corpus_hashes(ROOT)
        self.assertEqual(before, after)

    def test_budget_refusal_stops_run(self):
        manifest = load_pinned_manifest(ROOT)
        transport = MockTransport()
        out = Path(tempfile.mkdtemp(prefix="efc-pilot-budget-"))
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        ledger = out / "pilot.jsonl"
        with patch(
            "harness.efc_pilot_runner_v1.load_budget_state",
            return_value=BudgetState(
                calls_spent=258,
                input_tokens_spent=18,
                output_tokens_spent=10,
                input_token_ceiling=250_000,
                output_token_ceiling=16_330,
                total_call_ceiling=258,
                max_output_tokens_per_request=64,
                hard_cost_ceiling_usd=1.0,
                input_usd_per_million=2.5,
                output_usd_per_million=15.0,
            ),
        ):
            result = run_integrity_pilot(
                root=ROOT,
                transport=transport,
                manifest=manifest,
                ledger_path=ledger,
                timestamp_fn=lambda: "2026-07-16T14:00:00+00:00",
            )
        self.assertEqual(result["status"], "budget_refusal")
        self.assertEqual(result["rows_written"], 1)
        self.assertEqual(transport.call_count, 0)
        row = json.loads(ledger.read_text().strip())
        self.assertEqual(row["call_outcome"], "budget_refusal")


class TestLiveFlagGating(SocketRefusalMixin, unittest.TestCase):
    def test_live_without_pin_id_refuses(self):
        self.assertEqual(main(["--live"]), 2)

    def test_live_wrong_pin_id_refuses(self):
        self.assertEqual(
            main(["--live", "--pin-event-id", "wrong-pin"]),
            2,
        )

    def test_dry_run_cli_completes(self):
        out = Path(tempfile.mkdtemp(prefix="efc-pilot-cli-"))
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        rc = main(
            [
                "--run-id",
                "test-cli",
                "--output",
                str(out / "cli.jsonl"),
            ]
        )
        self.assertEqual(rc, 0)
        self.assertTrue((out / "cli.jsonl").is_file())


class TestPinSidecarBinding(unittest.TestCase):
    def test_real_tree_pin_matches_manifest(self):
        manifest = json.loads(
            (ROOT / "corpus/efc_calibration_v1/calibration_manifest_v1.json"
             ).read_text()
        )
        ok, reason = verify_pin_sidecar(ROOT, manifest)
        self.assertTrue(ok, reason)
        pin = json.loads((ROOT / PIN_SIDECAR_RELPATH).read_text())
        self.assertEqual(pin["pin_event_id"], PIN_EVENT_ID)
        self.assertEqual(
            pin["manifest_hash_canonical"],
            manifest_hash(manifest),
        )


if __name__ == "__main__":
    unittest.main()
