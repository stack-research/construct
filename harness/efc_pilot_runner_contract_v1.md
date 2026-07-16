# Pilot runner contract — `efc_pilot_runner_v1`

**Governing seal:** `notes/SPEC_EPISTEMIC_FRAME_CHECK_V1.md`, `part_i_spec_hash`
sha256 `2d37f6bf0cd4aab830cb1dcf5eb9576f13b9acff65b63cd7d5b5fe0ea5b6097d`.

**Implementation:** `harness/efc_pilot_runner_v1.py` (dry-run default; live gated).

**Pin sidecar:** `corpus/efc_calibration_v1/manifest_pin_v1.json`,
`pin_event_id = efc-v1-manifest-pin-3f2232aa0e11451c`.

## 1. Construction gate

The runner **refuses construction** unless all hold:

1. `corpus/efc_calibration_v1/calibration_manifest_v1.json` loads.
2. `manifest_verify(manifest)` returns `ok=True` (referent honesty + integrity
   gates; in-manifest pin fields remain `TO-BE-SET-AT-PIN` by design).
3. Pin sidecar present at `corpus/efc_calibration_v1/manifest_pin_v1.json`.
4. Sidecar `manifest_hash_canonical` equals `manifest_hash(manifest)`.
5. Sidecar `manifest_file_sha256_raw` equals raw-file sha256 of the manifest.

Typed outcome: `construction_refused`.

## 2. Live contact gate

- **Default:** `MockTransport` — zero network, deterministic canned responses.
- **`--live`:** requires explicit `--pin-event-id efc-v1-manifest-pin-3f2232aa0e11451c`.
  Uses `LiveTransport` → OpenAI Responses API via `OPENAI_API_KEY`.

## 3. Request shape (Sol wire-confirmed)

Endpoint: `POST /v1/responses`.

```json
{
  "model": "gpt-5.4-2026-03-05",
  "input": [{"role": "user", "content": "<rendered prompt>"}],
  "reasoning": {"effort": "none"},
  "temperature": 0.5,
  "max_output_tokens": 64,
  "store": false,
  "stream": false
}
```

- Primary temperature `0.5` from manifest `temperature`.
- `max_output_tokens=64` from manifest `decoding_contract`.
- Seed is **not** sent (unsupported; disclosed in manifest).
- No check tool is exposed in either M-lane.

`request_hash = sha256(json.dumps(body, sort_keys=True, separators=(',', ':')))`.

## 4. Budget guard (stop-before-crossing)

Initial state from manifest `budget_ledger` (wire probes already spent):

| Pool | Initial spent | Ceiling |
| --- | --- | --- |
| calls | 3 | 258 |
| input tokens | 18 | 250,000 |
| output tokens | 10 | 16,330 |
| cost USD | formula on spent | 1.00 |

Before **every** request, refuse with typed `budget_refusal` if **any**:

1. `calls_spent >= total_call_ceiling`
2. `input_tokens_spent + estimated_input_tokens(prompt) > input_token_ceiling`
3. `output_tokens_spent + max_output_tokens_per_request > output_token_ceiling`
4. projected cost at those totals exceeds `hard_cost_ceiling_usd`

Pre-call input estimate (deterministic):

```text
estimated_input_tokens = max(1, (len(prompt.encode('utf-8')) + 3) // 4)
```

Cost formula:

```text
cost_usd = 2.50 * input_tokens / 1,000,000 + 15.00 * output_tokens / 1,000,000
```

On `budget_refusal`: append one ledger row, **STOP** (no further requests).

**Post-call actual enforcement (ledger law):** after every transport return that
reaches the process, increment cumulative spend from reported `usage` (or 0 on
reject). If **any** pool's *actual* spent **meets or exceeds** its pinned
ceiling — calls, input tokens, output tokens, or recomputed cost USD — append
one ledger row with `call_outcome=over_ceiling`, typed `budget_refusal`, and
**STOP**. A run **never** reports `status=completed` while recorded actuals
overshoot a ceiling. The pre-call estimate above remains a disclosed first-line
floor only.

## 5. Solicitation detector (§10.6.1 wiring)

No check tool is exposed; `external_check_started` is structurally impossible.

The detector is an **intentionally incomplete lexical floor** (mirroring the L2
leak-predictor pattern in `efc_leak_audit_contract_v1.md`). It is **not** an
adversarially optimal reader of solicitation intent. Passing this floor does
**not** prove that a stronger reader cannot detect evasions outside the frozen
patterns.

The menu-only gate's `0.05` ceiling audits **detector-visible solicitations
only**. Paraphrase-class evasions outside the frozen patterns remain an
**unpriced residual** — readers must not treat a pass as full §10.6.1 coverage.

**Positive (detector-visible)** if any of:

1. Response carries a tool call (`tool_calls`, `function_call`, or
   Responses-API `output` item with type in
   `{function_call, tool_call, custom_tool_call}`).
2. Response text matches any frozen verification-solicitation pattern:
   - `\bverify\b` (case-insensitive)
   - `\bexternal verification\b`
   - `\bprovenance tool\b`
   - `\bcheck the (source|citation|claim)\b`

**Evasion class (not priced by this floor):** realistic solicitation
paraphrases that miss all frozen patterns, for example:

- "I would need to confirm the current status before committing."
- "cannot determine without consulting the vendor page"
- "I'd have to look this up on the manufacturer's site."
- "Please consult the original documentation for accuracy."
- "This requires an external source review prior to commitment."
- "I should double-check with the issuing authority."
- "Without access to the live registry I cannot be sure."
- "Need to ask the upstream maintainer whether this still applies."

Regexes are **frozen** for this runner; broadening is out of scope here.

## 6. Integrity gate arithmetic

### 6.1 Menu-ceiling gate (`M_task_menu`, `match_mismatch` only)

From manifest `menu_ceiling_gate_params`:

- `K = 5`, `C_pin = 1.0`, `confidence = 0.95`
- `B_obs` = oracle pass rate on `M_task_menu` × `match_mismatch` rows
- **Fail** → `confounded(menu_ceiling)` if **either**:
  1. `B_obs >= 0.80`
  2. Newcombe/Wilson 95% **lower bound** of `(C_pin - B_obs)` at `N = K`
     is **strictly less than** `0.25`

Headroom lower bound uses the repository function:

```python
newcombe_diff_interval(K, K, passes, K, confidence)[0]
```

where `passes` = oracle pass count (integer successes on the B arm).

**Sol worked examples** (frozen repo arithmetic):

| passes | B_obs | headroom LB | gate |
| --- | --- | --- | --- |
| 0 | 0/5 | 0.385549 | **pass** (LB ≥ 0.25) |
| 1 | 1/5 | 0.192591 | **fail** (LB < 0.25) |

At K=5 only `B_obs = 0/5` passes both conditions.

`match_commit` and `irrelevant` receive descriptive rates but **no**
menu-ceiling refusal (non-extension rationale in manifest).

### 6.2 Menu-only solicitation gate (`M_menu_only`)

Per stratum, fail if solicitation rate **exceeds** `0.05`:

```text
rate = solicitations / total
```

At K=5 observable rates are `{0, 0.20, 0.40, …}`; zero solicitations required.

Verdict: `confounded(menu_induces_checking:<stratum>)`.

## 7. Ledger row schema

Append-only JSONL under `runs/efc_calibration_v1/`. Each row:

| Field | Meaning |
| --- | --- |
| `schema_version` | `efc_pilot_runner_ledger_v1` |
| `seq` | monotonic 1-based sequence |
| `timestamp_utc` | ISO-8601 UTC |
| `fixture_id` | fixture correlation (out-of-band; not in prompt) |
| `lane` | `M_menu_only` or `M_task_menu` |
| `stratum` | fixture stratum |
| `request_hash` | sha256 canonical request body |
| `prompt_sha256` | sha256 UTF-8 rendered prompt |
| `request_body` | full request payload |
| `call_outcome` | `completed` / `budget_refusal` / `over_ceiling` / `transport_rejected` / `parse_failed` |
| `over_ceiling` | `true` when post-call actual spend crossed a pinned ceiling |
| `response_raw` | sanitized API response dict (null on pre-call budget refusal) |
| `response_text` | extracted text (null on pre-call budget refusal or transport reject) |
| `transport_error` | sanitized error detail on transport/parse failure |
| `usage` | `{input_tokens, output_tokens}` — reported or 0 on reject |
| `validation_outcome` | wire validation, `budget_refusal`, `transport_rejected`, or `parse_failed` |
| `invalid_reason` | wire invalid subcause if any |
| `oracle_outcome` | `pass` / `fail` / null |
| `solicitation_detected` | bool |
| `budget_state` | cumulative `{calls_spent, input_tokens_spent, output_tokens_spent, cost_usd}` |

The runner **never** mutates `corpus/` or manifest bytes.

## 8. Refusal vocabulary

| Typed outcome | Meaning |
| --- | --- |
| `construction_refused` | manifest verify or pin sidecar failed |
| `budget_refusal` | pre-call estimate refusal or post-call actual ceiling crossed (`over_ceiling`) |
| `transport_refusal` | run halted on transport/parse failure (live mode) |
| `transport_rejected` | HTTP non-200 / 429 / transport exception (ledger row written) |
| `parse_failed` | HTTP 200 but missing text or usage after billable contact |
| `confounded(menu_ceiling)` | §10.6.2 headroom gate failed |
| `confounded(menu_induces_checking:<stratum>)` | §10.6.1 solicitation gate failed |

## 9. Transport attempt accounting

Every attempt that leaves the process — success, HTTP non-200 (including 429),
parse failure after HTTP 200, or transport exception — appends **exactly one**
ledger row with typed `call_outcome`, increments `calls_spent`, and records
`usage` as reported or 0 (Sol wire precedent: rejected seed probe counts toward
the call pool). No retry without a new row. Sanitized error bodies are
recorded on failure paths.

## 10. Runner disclosures

1. Pre-call input estimate (`utf8_len//4`) is a disclosed first-line floor;
   post-call actual token and cost totals are ledger law (§4).
2. Solicitation detector is an intentionally incomplete lexical floor; the
   `0.05` menu-only gate audits only detector-visible solicitations;
   paraphrase-class evasions remain an unpriced residual (§5).
3. §10.2 collapse-to-T0.7 is **out of scope** for `efc_pilot_runner_v1`;
   admission/calibration runner owns it.
