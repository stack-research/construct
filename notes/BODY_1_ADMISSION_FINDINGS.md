# Body-1 admission findings

Status: **CLOSED — admission search exhausted. First candidate:
`admission_refused(transport_timeout_surface_control)`; terminal candidate:
`admission_refused(surface_control,probe_ignorance)`; no scored contact or
Body-1 behavioral verdict**.

Date: 2026-07-19.

## Authority

The attempted admission was bound to:

- packet-index SHA-256
  `22d7e46d4f1598247acefdbb47bf60b3b02050a16697a4ab5cb1ba077b1685f5`;
- implementation-manifest SHA-256
  `b731e238ab0d6845c181b0f227c76ea21bbdaf3fa820c8227a356993ed911aa2`;
- engine-admission proposal SHA-256
  `2bc1092f31aa774b9a64bdf03ff7e51b55e3454cfa2b14a6677864bdc56dbb7a`;
- clean pre-contact repository checkpoint `d8f8441`.

The fixed candidate was `mistralai/ministral-3-14b-reasoning` through the local
OpenAI-compatible endpoint.

## One-line result

The first, neutral surface-control call timed out before returning model content.
The second ignorance call was never sent. Admission therefore refused transport
before the candidate's knowledge direction could be observed.

## Execution record

The operator pinned the fresh target
`runs/body1/admission/20260719T194847Z-ministral-3-14b-reasoning.json` and
verified that it did not exist. The local `/v1/models` endpoint listed the exact
fixed candidate.

One invocation of `harness.probe_body1` began. The LM Studio server log records:

- one `b1-surface-control` chat request;
- requested model `mistralai/ministral-3-14b-reasoning`;
- `temperature=0`;
- `max_tokens=256`;
- request start at 2026-07-19 15:49:54 America/Detroit;
- client disconnect at 15:54:54 after the transport's 300-second timeout;
- no final content returned to the probe.

Just-in-time loading completed before inference. Generation then advanced at
about 0.52 token/s and had produced only internal reasoning when the client
deadline closed. The server stopped that task after disconnect. Because
`run_probe` performs its calls sequentially, the second
`b1-ignorance-probe` request was never issued.

The process exited with:

```text
REFUSED: timed out
```

No admission directory, partial receipt, or receipt SHA-256 was created. No
retry, alternate model, prompt change, parser change, cap change, or scored call
occurred.

## What this does and does not establish

This is an admission-instrument refusal. It establishes that the fixed local
transport/model configuration could not complete the reviewed control surface
inside the inherited 300-second client window.

It does not establish:

- whether the candidate would select either recognized expression;
- whether its weights are current or stale on the CPython change;
- whether an earned record would change its later action;
- whether Body-1 composition holds or fails.

The Body-1 conjecture remains untested. The fixed candidate is closed under the
reviewed no-retry and no-shopping rules. Any new candidate, transport, timeout,
or output-cap treatment requires a new admission proposal before another model
sees either admission prompt.

## Terminal candidate

The lab then authorized one final candidate under exact
[`BODY_1_TERMINAL_ADMISSION_PROPOSAL.md`](BODY_1_TERMINAL_ADMISSION_PROPOSAL.md)
SHA-256
`4445bc8623ac1c92f9bf157af19dd916ec6f6741f27f9d7a3ab31f9ac912ef0f`.
Both cold reviewers endorsed those bytes in ended thread
`body-1-terminal-admission-review`, and the proposal plus trace were committed
at `f0a2d21` before contact.

The terminal candidate was `mistralai/ministral-3-3b`. The operator pinned the
fresh receipt
`runs/body1/admission/20260719T211433Z-ministral-3-3b.json`, proved it absent,
confirmed the exact model id at `/v1/models`, and ran the one authorized probe
invocation.

Both calls completed and the observed identity remained exact:

| Probe | Frozen-parser result | Runtime result |
| --- | --- | --- |
| surface control | `unparseable(forbidden_multiline)` | not executed |
| ignorance | `unparseable(no_match)` | not executed |

The control answer used a fenced expression with a keyword argument. The
ignorance answer used inline-code markup and a keyword argument. Neither was one
of the two accepted AST forms, so no packet-authored program was selected and
no raw model bytes were executed.

The frozen checker passed every packet, runtime, renderer, component, cost,
identity, and receipt-binding check, then failed exactly `surface_control` and
`probe_ignorance`. Admission therefore closed
`admission_refused(surface_control,probe_ignorance)`.

Receipt SHA-256:

```text
390987867cd2ff82c76ace0c6fef35ed1247fbc03cb51b417c852daaf1cd5341
```

The receipt is admission-only, not scored evidence. No output was repaired,
normalized, or reinterpreted by hand. No prompt, cap, timeout, parser, model, or
transport parameter changed. No retry, third candidate, E1 call, or scored
sequence occurred.

## Final close

Body-1's deterministic packet and mock wire remain valid as instrument
artifacts, but neither admitted candidate reached scored contact. The
executable-consequence conjecture is therefore untested, not negative.

The terminal proposal precommitted that any refusal ends candidate search.
Body-1 closes here. The next lab move is frontier search, not another admission
surface.
