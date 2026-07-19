# Body-1 admission findings

Status: **CLOSED `admission_refused(transport_timeout_surface_control)` —
fixed candidate exhausted its one reviewed packet; no receipt and no scored
contact**.

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
