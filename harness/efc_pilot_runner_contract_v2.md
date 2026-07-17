# EFC v2 pilot runner contract

Status: v2 lineage. Dry-run (MockTransport) is the default; **live engine contact**
is licensed only via explicit `--live` + matching `--pin-event-id` against the
pinned sidecar. Unlicensed contact remains structurally refused.

## Lanes

| Lane | Purpose |
| --- | --- |
| `M_untreated` | Untreated relevant items for §C admission band and pair predicates |
| `M_forced_class` | Dual-scoring: each relevant item scored under commit and non_commit |
| `M_irrelevant` | Irrelevant stratum untreated floor |

Pinned suite contact: 384 `M_untreated` + 512 `M_forced_class` (2×256 dual) +
irrelevant floor rows; ledger under `runs/efc_calibration_v2/`.

## Live contact gate

- **Default:** `MockTransport` — zero network, deterministic canned responses.
- **`--live`:** requires `--pin-event-id efc-v2-manifest-pin-8a4686b8d81e3828`.
  Uses `LiveTransport` → LM Studio OpenAI-compatible chat-completions at
  `http://localhost:1234/v1` (no API key).
- Before live contact: `GET /v1/models` must list the pinned
  `fork_identity.engine` (`qwen/qwen3.5-9b`); otherwise `construction_refused`.
- Canonical request body is Responses-shaped (ledger `request_hash` binds it).
  `LiveTransport` adapts internally to chat-completions (`input`→`messages`,
  `max_output_tokens`→`max_tokens`; usage `prompt_tokens`/`completion_tokens`
  → input/output).
- Think-block stripping: final message `content` only (not `reasoning_content`);
  strip `<think>…</think>` before wire JSON parse.
  Stripped-but-unparseable output is `commitment_invalid`, not headroom.

## Fork identity binding

`build_request_body` binds `model` from `fork_identity.engine` and
`reasoning.effort` from `fork_identity.effort` (not `decoding_contract`).

## Ledger

Append-only `efc_pilot_runner_ledger_v2` rows. Budget guards inherited from v1
pattern. Pin-sidecar lifecycle inherited from v1 pattern.

## Typed outcomes

Runner vocabulary extends v1 with §D admission types via
`evaluate_admission_gate` (sealed module; runner reports, gate decides).
