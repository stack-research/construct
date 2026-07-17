"""Conformance vectors for EFC v2 pilot runner."""

from __future__ import annotations

import json
import socket
import tempfile
import unittest
from pathlib import Path

from harness.efc_commitment_wire_v2 import validate_commitment_wire
from harness.efc_manifest_v2 import assemble_manifest
from harness.efc_pilot_runner_v2 import (
    BudgetRefusal,
    BudgetState,
    FailingTransport,
    LiveTransport,
    MockTransport,
    PilotRunnerRefusal,
    TransportRefusal,
    adapt_responses_to_chat_completions,
    build_request_body,
    check_budget_actual,
    check_budget_guard,
    extract_chat_completion_text,
    parse_commitment_wire_text,
    request_hash,
    run_admission_pilot,
    strip_think_blocks,
    verify_pinned_engine_available,
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


def _manifest_with_fork(root: Path) -> dict:
    manifest = assemble_manifest(root)
    manifest["fork_identity"] = {
        "engine": "qwen/qwen3.5-9b",
        "effort": "high",
        "render_hash": manifest["contract_hashes"]["foreground_template_hash"],
    }
    return manifest


class TestForkIdentityBinding(unittest.TestCase):
    def test_build_request_body_binds_fork_identity(self):
        manifest = _manifest_with_fork(ROOT)
        body = build_request_body(manifest, "prompt text")
        self.assertEqual(body["model"], "qwen/qwen3.5-9b")
        self.assertEqual(body["reasoning"], {"effort": "high"})
        self.assertEqual(body["input"], [{"role": "user", "content": "prompt text"}])

    def test_missing_engine_refuses_construction(self):
        manifest = assemble_manifest(ROOT)
        manifest["fork_identity"] = {"effort": "high", "render_hash": "x"}
        with self.assertRaises(PilotRunnerRefusal) as ctx:
            build_request_body(manifest, "prompt")
        self.assertEqual(ctx.exception.reason, "construction_refused")


class TestModelListRefusal(unittest.TestCase):
    def test_pinned_engine_missing_from_model_list(self):
        manifest = _manifest_with_fork(ROOT)

        def http_get(_url: str) -> dict:
            return {
                "http_status": 200,
                "data": {"data": [{"id": "other/model"}]},
                "error": None,
            }

        with self.assertRaises(PilotRunnerRefusal) as ctx:
            verify_pinned_engine_available(manifest, http_get=http_get)
        self.assertEqual(ctx.exception.detail, "pinned_engine_not_in_model_list")

    def test_pinned_engine_present_passes(self):
        manifest = _manifest_with_fork(ROOT)

        def http_get(_url: str) -> dict:
            return {
                "http_status": 200,
                "data": {"data": [{"id": "qwen/qwen3.5-9b"}]},
                "error": None,
            }

        verify_pinned_engine_available(manifest, http_get=http_get)


class TestThinkStripParse(unittest.TestCase):
    def test_strip_think_blocks(self):
        raw = (
            '<think>hidden</think>'
            '{"commitment_enum": "alpha_commit"}'
        )
        self.assertEqual(
            strip_think_blocks(raw),
            '{"commitment_enum": "alpha_commit"}',
        )

    def test_extract_ignores_reasoning_content(self):
        data = {
            "choices": [
                {
                    "message": {
                        "reasoning_content": "internal chain",
                        "content": '{"commitment_enum": "beta_commit"}',
                    }
                }
            ]
        }
        self.assertEqual(
            extract_chat_completion_text(data),
            '{"commitment_enum": "beta_commit"}',
        )

    def test_stripped_unparseable_is_commitment_invalid(self):
        text = strip_think_blocks(
            "<think>x</think>not-json"
        )
        wire = parse_commitment_wire_text(text)
        validated = validate_commitment_wire(
            wire, ["alpha_commit", "beta_commit", "gamma_hold", "delta_hold"]
        )
        self.assertEqual(validated.outcome, "commitment_invalid")


class TestAdapterMapping(unittest.TestCase):
    def test_responses_to_chat_completions_mapping(self):
        manifest = _manifest_with_fork(ROOT)
        body = build_request_body(manifest, "wire prompt")
        adapted = adapt_responses_to_chat_completions(body)
        self.assertEqual(adapted["messages"], body["input"])
        self.assertEqual(adapted["max_tokens"], body["max_output_tokens"])
        self.assertEqual(adapted["model"], body["model"])
        self.assertNotIn("input", adapted)
        self.assertNotIn("max_output_tokens", adapted)

    def test_request_hash_unchanged_over_canonical_body(self):
        manifest = _manifest_with_fork(ROOT)
        body = build_request_body(manifest, "wire prompt")
        canonical_hash = request_hash(body)
        adapt_responses_to_chat_completions(body)
        self.assertEqual(request_hash(body), canonical_hash)

    def test_live_transport_adapter_and_usage_mapping(self):
        manifest = _manifest_with_fork(ROOT)
        body = build_request_body(manifest, "wire prompt")

        def http_post(url: str, posted: dict, api_key):
            self.assertTrue(url.endswith("/chat/completions"))
            self.assertIsNone(api_key)
            self.assertEqual(posted["messages"], body["input"])
            self.assertEqual(posted["max_tokens"], body["max_output_tokens"])
            return {
                "http_status": 200,
                "data": {
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    '<think>t</think>'
                                    '{"commitment_enum": "alpha_commit"}'
                                )
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 12, "completion_tokens": 4},
                },
            }

        transport = LiveTransport(http_post_fn=http_post)
        result = transport.call(
            body,
            type("Ctx", (), {"fixture_id": "f", "lane": "M_untreated"})(),
        )
        self.assertEqual(result.input_tokens, 12)
        self.assertEqual(result.output_tokens, 4)
        self.assertEqual(
            result.text, '{"commitment_enum": "alpha_commit"}',
        )


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
        manifest = _manifest_with_fork(ROOT)
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
            first = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(first["request_body"]["model"], "qwen/qwen3.5-9b")

    def test_transport_refusal_halts(self):
        manifest = _manifest_with_fork(ROOT)
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
        manifest = _manifest_with_fork(ROOT)
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
