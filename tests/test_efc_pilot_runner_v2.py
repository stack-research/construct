"""Conformance vectors for EFC v2 pilot runner."""

from __future__ import annotations

import json
import socket
import tempfile
import unittest
from pathlib import Path

from harness.efc_commitment_wire_v2 import validate_commitment_wire
from harness.efc_manifest_v2 import (
    CAP2048_MAX_OUTPUT_TOKENS_PER_REQUEST,
    CAP2048_OPENING_CALLS,
    EARLY_OUTPUT_CENSORING_OUTCOME,
    assemble_manifest,
    manifest_hash,
    sha256_path,
)
from harness.efc_pilot_runner_v2 import (
    BudgetRefusal,
    BudgetState,
    CensoringMockTransport,
    FailingTransport,
    LiveTransport,
    MockTransport,
    PIN_EVENT_ID,
    PilotRunnerRefusal,
    TransportResult,
    adapt_responses_to_chat_completions,
    build_request_body,
    check_budget_actual,
    check_budget_guard,
    check_early_censor_refusal,
    extract_chat_completion_text,
    load_budget_state,
    main,
    matches_early_censor_predicates,
    parse_commitment_wire_text,
    request_hash,
    run_admission_pilot,
    strip_think_blocks,
    verify_pin_sidecar,
    verify_pinned_engine_available,
)
from tests.efc_v2_test_fixtures import make_minimal_suite

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_RELPATH = "corpus/efc_calibration_v2/calibration_manifest.json"


def _current_manifest_hashes(root: Path) -> tuple[dict, str, str]:
    manifest_path = root / MANIFEST_RELPATH
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return manifest, sha256_path(manifest_path), manifest_hash(manifest)


def _write_superseding_pin_sidecar(
    handle,
    root: Path,
    *,
    pin_event_id: str,
    manifest_relpath: str | None = None,
) -> None:
    manifest_relpath = manifest_relpath or MANIFEST_RELPATH
    manifest_path = root / manifest_relpath
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_sha = sha256_path(manifest_path)
    canonical = manifest_hash(manifest)
    json.dump(
        {
            "manifest_file_sha256_raw": raw_sha,
            "manifest_hash_canonical": canonical,
            "manifest_path": manifest_relpath,
            "pin_event_id": pin_event_id,
            "pinned_at": "2026-07-17T13:38:51Z",
            "pinned_by": "test",
        },
        handle,
    )


def _write_temp_assembled_manifest(root: Path) -> tuple[Path, str]:
    manifest = _manifest_with_fork(root)
    temp_manifest = tempfile.NamedTemporaryFile(
        "w",
        dir=root,
        suffix=".json",
        delete=False,
    )
    json.dump(manifest, temp_manifest, indent=2, sort_keys=True)
    temp_manifest.flush()
    temp_manifest.close()
    path = Path(temp_manifest.name)
    return path, path.relative_to(root).as_posix()


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
    manifest = assemble_manifest(root, engine="qwen/qwen3.5-9b", effort="high")
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
        self.assertEqual(adapted["reasoning_effort"], "high")
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
            self.assertEqual(posted["reasoning_effort"], "high")
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

    def test_think_only_content_returns_empty_text_not_parse_failure(self):
        manifest = _manifest_with_fork(ROOT)
        body = build_request_body(manifest, "wire prompt")

        def http_post(_url: str, _posted: dict, _api_key):
            return {
                "http_status": 200,
                "data": {
                    "choices": [
                        {
                            "message": {
                                "content": "<think>only</think>"
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 1},
                },
            }

        transport = LiveTransport(http_post_fn=http_post)
        result = transport.call(
            body,
            type("Ctx", (), {"fixture_id": "f", "lane": "M_untreated"})(),
        )
        self.assertEqual(result.text, "")


class TestThinkOnlyCommitmentInvalid(unittest.TestCase):
    def test_think_only_ledger_is_commitment_invalid_not_transport_refusal(self):
        manifest = _manifest_with_fork(ROOT)
        fixtures = make_minimal_suite(1)

        def http_post(_url: str, _posted: dict, _api_key):
            return {
                "http_status": 200,
                "data": {
                    "choices": [
                        {
                            "message": {
                                "content": "<think>x</think>"
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 2},
                },
            }

        transport = LiveTransport(http_post_fn=http_post)
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "pilot.jsonl"
            result = run_admission_pilot(
                root=ROOT,
                transport=transport,
                manifest=manifest,
                fixtures=fixtures,
                ledger_path=ledger,
            )
            self.assertNotEqual(result["status"], "transport_refusal")
            row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["validation_outcome"], "commitment_invalid")
            self.assertEqual(row["call_outcome"], "completed")
            self.assertGreaterEqual(row["wall_time_ms"], 0.0)


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


class TestEarlyCensorRefusal(unittest.TestCase):
    def test_predicate_matches_length_capped_empty_envelope(self):
        raw = {
            "choices": [{"finish_reason": "length", "message": {"content": ""}}],
        }
        self.assertTrue(
            matches_early_censor_predicates(
                raw=raw,
                text="",
                output_tokens=2047,
                max_output_tokens=2048,
                tolerance=1,
            )
        )

    def test_predicate_rejects_nonempty_content(self):
        raw = {
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {"content": '{"commitment_enum":"x"}'},
                }
            ],
        }
        self.assertFalse(
            matches_early_censor_predicates(
                raw=raw,
                text='{"commitment_enum":"x"}',
                output_tokens=2047,
                max_output_tokens=2048,
                tolerance=1,
            )
        )

    def test_early_censor_refusal_after_eight_censored_envelopes(self):
        manifest = _manifest_with_fork(ROOT)
        fixtures = make_minimal_suite(2)
        transport = CensoringMockTransport(
            max_output_tokens=CAP2048_MAX_OUTPUT_TOKENS_PER_REQUEST,
        )
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "pilot.jsonl"
            result = run_admission_pilot(
                root=ROOT,
                transport=transport,
                manifest=manifest,
                fixtures=fixtures,
                ledger_path=ledger,
            )
            self.assertEqual(result["status"], EARLY_OUTPUT_CENSORING_OUTCOME)
            self.assertEqual(result["stop_reason"], "early_output_censoring")
            self.assertEqual(result["call_count"], 8)
            self.assertEqual(transport.call_count, 8)

    def test_nonmatching_empty_stop_disarms_early_censor_sol_counterprobe(self):
        """Call 1 = empty finish_reason=stop; calls 2-9 = censor => no refusal."""
        manifest = _manifest_with_fork(ROOT)
        fixtures = make_minimal_suite(2)

        class CounterprobeTransport:
            def __init__(self):
                self.call_count = 0
                self._censor = CensoringMockTransport(
                    max_output_tokens=CAP2048_MAX_OUTPUT_TOKENS_PER_REQUEST,
                )

            def call(self, request_body, context):
                self.call_count += 1
                if self.call_count == 1:
                    raw = {
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {"content": ""},
                            }
                        ],
                        "usage": {"prompt_tokens": 10, "completion_tokens": 0},
                    }
                    return TransportResult(
                        raw=raw,
                        text="",
                        input_tokens=10,
                        output_tokens=0,
                        tool_calls_present=False,
                    )
                return self._censor.call(request_body, context)

        transport = CounterprobeTransport()
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "pilot.jsonl"
            result = run_admission_pilot(
                root=ROOT,
                transport=transport,
                manifest=manifest,
                fixtures=fixtures,
                ledger_path=ledger,
            )
            self.assertNotEqual(result["status"], EARLY_OUTPUT_CENSORING_OUTCOME)
            self.assertGreater(result["call_count"], 8)

    def test_content_response_disables_early_censor(self):
        manifest = _manifest_with_fork(ROOT)
        fixtures = make_minimal_suite(2)

        class MixedTransport:
            def __init__(self):
                self.call_count = 0

            def call(self, request_body, context):
                self.call_count += 1
                if self.call_count == 3:
                    text = json.dumps({"commitment_enum": "alpha_commit"})
                    raw = {
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {"content": text},
                            }
                        ],
                        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                    }
                    return TransportResult(
                        raw=raw,
                        text=text,
                        input_tokens=10,
                        output_tokens=5,
                        tool_calls_present=False,
                    )
                return CensoringMockTransport(
                    max_output_tokens=CAP2048_MAX_OUTPUT_TOKENS_PER_REQUEST,
                ).call(request_body, context)

        transport = MixedTransport()
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "pilot.jsonl"
            result = run_admission_pilot(
                root=ROOT,
                transport=transport,
                manifest=manifest,
                fixtures=fixtures,
                ledger_path=ledger,
            )
            self.assertNotEqual(result["status"], EARLY_OUTPUT_CENSORING_OUTCOME)
            self.assertGreater(result["call_count"], 8)

    def test_check_early_censor_refusal_unit(self):
        manifest = _manifest_with_fork(ROOT)
        early = manifest["early_censor_refusal"]
        self.assertEqual(
            check_early_censor_refusal(
                manifest=manifest,
                envelope_attempts=8,
                censor_matches=8,
                early=early,
            ),
            EARLY_OUTPUT_CENSORING_OUTCOME,
        )
        self.assertIsNone(
            check_early_censor_refusal(
                manifest=manifest,
                envelope_attempts=8,
                censor_matches=7,
                early=early,
            )
        )


class TestCap2048BudgetLedger(unittest.TestCase):
    def test_load_budget_state_zero_dollar_pricing(self):
        manifest = _manifest_with_fork(ROOT)
        state = load_budget_state(manifest)
        self.assertEqual(
            state.max_output_tokens_per_request,
            CAP2048_MAX_OUTPUT_TOKENS_PER_REQUEST,
        )
        self.assertEqual(state.hard_cost_ceiling_usd, 0.0)
        self.assertEqual(state.input_usd_per_million, 0.0)
        self.assertEqual(state.output_usd_per_million, 0.0)
        self.assertEqual(state.calls_spent, CAP2048_OPENING_CALLS)

    def test_build_request_body_uses_cap2048(self):
        manifest = _manifest_with_fork(ROOT)
        body = build_request_body(manifest, "prompt")
        self.assertEqual(body["max_output_tokens"], CAP2048_MAX_OUTPUT_TOKENS_PER_REQUEST)


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
            self.assertIn("wall_time_ms", first)

    def test_transport_refusal_halts_and_accounts_budget(self):
        manifest = _manifest_with_fork(ROOT)
        fixtures = make_minimal_suite(1)
        transport = FailingTransport(
            detail="simulated_http_429",
            http_status=429,
            input_tokens=7,
            output_tokens=2,
        )
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "pilot.jsonl"
            result = run_admission_pilot(
                root=ROOT,
                transport=transport,
                manifest=manifest,
                fixtures=fixtures,
                ledger_path=ledger,
            )
            self.assertEqual(result["status"], "transport_refusal")
            row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["call_outcome"], "transport_rejected")
            self.assertEqual(row["usage"], {"input_tokens": 7, "output_tokens": 2})
            self.assertEqual(
                row["budget_state"]["calls_spent"],
                manifest["budget_ledger"]["calls_already_spent"] + 1,
            )
            self.assertIn("wall_time_ms", row)

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


class TestLivePinAuthorization(SocketRefusalMixin, unittest.TestCase):
    def _licensed_pin_sidecar_argv(self) -> tuple[list[str], Path, Path]:
        manifest_path, rel_manifest = _write_temp_assembled_manifest(ROOT)
        self.addCleanup(manifest_path.unlink, missing_ok=True)
        temp_pin = tempfile.NamedTemporaryFile(
            "w",
            dir=ROOT,
            suffix=".json",
            delete=False,
        )
        pin_path = Path(temp_pin.name)
        _write_superseding_pin_sidecar(
            temp_pin,
            ROOT,
            pin_event_id=PIN_EVENT_ID,
            manifest_relpath=rel_manifest,
        )
        temp_pin.flush()
        temp_pin.close()
        self.addCleanup(pin_path.unlink, missing_ok=True)
        rel_pin = pin_path.relative_to(ROOT).as_posix()
        return (
            ["--manifest", rel_manifest, "--pin-sidecar", rel_pin],
            pin_path,
            manifest_path,
        )

    def test_wrong_pin_event_id_cli_refuses(self):
        pin_argv, _, _ = self._licensed_pin_sidecar_argv()
        self.assertEqual(
            main(
                [
                    "--live",
                    *pin_argv,
                    "--pin-event-id",
                    "wrong-pin-id",
                ]
            ),
            2,
        )

    def test_unlicensed_pin_event_id_cli_refuses(self):
        pin_argv, _, _ = self._licensed_pin_sidecar_argv()
        self.assertEqual(
            main(
                [
                    "--live",
                    *pin_argv,
                    "--pin-event-id",
                    "efc-v2-manifest-pin-forged0000000000",
                ]
            ),
            2,
        )

    def test_forged_sidecar_event_id_cannot_self_authorize(self):
        manifest, _, _ = _current_manifest_hashes(ROOT)
        temp_pin = tempfile.NamedTemporaryFile(
            "w",
            dir=ROOT,
            suffix=".json",
            delete=False,
        )
        pin_path = Path(temp_pin.name)
        try:
            _write_superseding_pin_sidecar(
                temp_pin,
                ROOT,
                pin_event_id="efc-v2-manifest-pin-forged0000000000",
            )
            temp_pin.flush()
            rel_pin = pin_path.relative_to(ROOT).as_posix()
            ok, reason = verify_pin_sidecar(
                ROOT,
                manifest,
                manifest_relpath=MANIFEST_RELPATH,
                pin_sidecar_relpath=rel_pin,
                licensed_pin_event_id=PIN_EVENT_ID,
            )
            self.assertFalse(ok)
            self.assertEqual(reason, "pin_event_id_not_licensed")
        finally:
            temp_pin.close()
            pin_path.unlink(missing_ok=True)
