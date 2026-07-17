"""Conformance vectors for EFC v2 pilot runner."""

from __future__ import annotations

import importlib
import inspect
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness.efc_manifest_v2 import assemble_manifest
from harness.efc_pilot_runner_v2 import (
    BudgetRefusal,
    BudgetState,
    FailingTransport,
    MockTransport,
    PilotRunnerRefusal,
    TransportRefusal,
    check_budget_actual,
    check_budget_guard,
    run_admission_pilot,
)
from tests.efc_v2_test_fixtures import make_minimal_suite

ROOT = Path(__file__).resolve().parents[1]


class _RefusingSocket(socket.socket):
    def __init__(self, *a, **k):
        raise AssertionError("v2 pilot runner attempted a network call")


class SocketRefusalMixin:
    @classmethod
    def setUpClass(cls):
        cls._real_socket = socket.socket
        socket.socket = _RefusingSocket

    @classmethod
    def tearDownClass(cls):
        socket.socket = cls._real_socket


class TestNoLiveTransport(SocketRefusalMixin, unittest.TestCase):
    def test_module_has_no_live_transport(self):
        mod = importlib.import_module("harness.efc_pilot_runner_v2")
        self.assertFalse(hasattr(mod, "LiveTransport"))

    def test_no_live_cli_flag(self):
        import harness.efc_pilot_runner_v2 as runner

        source = inspect.getsource(runner.main)
        self.assertNotIn('add_argument("--live"', source)
        self.assertNotIn("efc_roster", inspect.getsource(runner))


class TestBudgetGuards(unittest.TestCase):
    def test_guard_refuses_at_call_ceiling(self):
        state = BudgetState(
            calls_spent=10,
            input_tokens_spent=0,
            output_tokens_spent=0,
            input_token_ceiling=100,
            output_token_ceiling=100,
            total_call_ceiling=10,
            max_output_tokens_per_request=32,
            hard_cost_ceiling_usd=1.0,
            input_usd_per_million=1.0,
            output_usd_per_million=1.0,
        )
        refusal = check_budget_guard(state, projected_input_tokens=1)
        self.assertIsInstance(refusal, BudgetRefusal)

    def test_actual_refuses_over_cost(self):
        state = BudgetState(
            calls_spent=1,
            input_tokens_spent=1_000_000,
            output_tokens_spent=0,
            input_token_ceiling=2_000_000,
            output_token_ceiling=2_000_000,
            total_call_ceiling=100,
            max_output_tokens_per_request=256,
            hard_cost_ceiling_usd=1.0,
            input_usd_per_million=2.0,
            output_usd_per_million=0.0,
        )
        refusal = check_budget_actual(state)
        self.assertIsNotNone(refusal)


class TestAdmissionPilot(SocketRefusalMixin, unittest.TestCase):
    def test_dryrun_writes_ledger(self):
        manifest = assemble_manifest(ROOT)
        manifest["fork_identity"] = {
            "engine": "mock",
            "effort": "high",
            "render_hash": manifest["contract_hashes"]["foreground_template_hash"],
        }
        fixtures = make_minimal_suite(1)
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "pilot.jsonl"
            result = run_admission_pilot(
                root=ROOT,
                transport=MockTransport(),
                manifest=manifest,
                fixtures=fixtures,
                ledger_path=ledger,
            )
            self.assertTrue(ledger.is_file())
            self.assertGreater(result["call_count"], 0)

    def test_transport_refusal_halts(self):
        manifest = assemble_manifest(ROOT)
        fixtures = make_minimal_suite(1)
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "pilot.jsonl"
            result = run_admission_pilot(
                root=ROOT,
                transport=FailingTransport(),
                manifest=manifest,
                fixtures=fixtures,
                ledger_path=ledger,
            )
            self.assertEqual(result["status"], "transport_refusal")

    def test_append_only_ledger_refusal(self):
        manifest = assemble_manifest(ROOT)
        fixtures = make_minimal_suite(1)
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "pilot.jsonl"
            ledger.write_text("{}\n")
            with self.assertRaises(PilotRunnerRefusal):
                run_admission_pilot(
                    root=ROOT,
                    transport=MockTransport(),
                    manifest=manifest,
                    fixtures=fixtures,
                    ledger_path=ledger,
                )
