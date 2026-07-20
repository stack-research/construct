# Frontier obligation admission implementation

Status: **v0.1 CANDIDATE — deterministic build complete; exact implementation
manifest and cold wire review required before candidate selection**.

Date: 2026-07-19.

## Authority

This implementation is bounded by:

- the concept-endorsed
  [frontier candidate](FRONTIER_OBLIGATION_CANDIDATE.md);
- the exact-hash-endorsed
  [admission proposal](FRONTIER_OBLIGATION_ADMISSION_PROPOSAL.md), reviewed at
  SHA-256
  `19214f49b5b34f61ea9c0aaa024efff94049039b1bbf78dc3097eeff02cca004`;
- the authored admission packet rooted at
  [`packet_index.json`](../episodes/frontier_obligation/admission/packet_index.json),
  SHA-256
  `5da170547db2a779880bcfdb01827aa2d30ae9471357f6c6c53ccf977489a3b2`.

It implements admission only. It contains no `G/O/S/N` treatment, obligation
mint, post-offer world transition, or experimental scorer.

## Built surface

### Packet

[`episodes/frontier_obligation/admission/`](../episodes/frontier_obligation/admission/)
contains:

- the verbatim latest-status decision rule;
- twelve closed fixtures in six pairs;
- the renderer contract;
- the two-action response contract;
- a content-addressed packet index.

Fixture files contain no expected action. The checker derives the expected role
from the greatest `event_seq`, maps it to the artifact-qualified label, and
recomputes the six/six action and position balances.

### Deterministic core

[`frontier_obligation_admission.py`](../harness/frontier_obligation_admission.py)
owns:

- packet and entry hash verification;
- closed fixture and pair invariants;
- exact prompt rendering;
- request-body construction;
- predeclared JSON extraction and closed wire validation;
- expected-label derivation;
- independent receipt replay;
- anti-constant and budget verdicts.

The receipt checker recomputes the prompt, request body, raw-answer hash,
extracted wire, selection, expected role, correctness, pair flips, action
balance, and position balance. Runner annotations cannot certify themselves.

### Admission-only runner

[`probe_frontier_obligation_admission.py`](../harness/probe_frontier_obligation_admission.py)
supports:

- deterministic mock execution;
- one OpenAI-compatible local backend;
- exact `/models` availability preflight;
- twelve stateless calls in canonical order;
- zero retries;
- semantic completion of the fixed board after a miss;
- immediate stop on transport or identity failure;
- atomic no-overwrite complete or partial-refusal receipts.

Real contact requires a separately reviewed execution pin. The runner verifies:

- exact pin hash;
- packet and implementation-manifest bindings;
- exact-hash endorsement of the implementation manifest by both cold reviewers;
- one terminal candidate;
- exact receipt path;
- temperature, reasoning mode, call cap, output cap, and retry count;
- ended Substrate review;
- exact endorsements from both review seats and the moderator.

No CLI model or endpoint override survives a valid real execution pin.

### Fail-closed checker

[`check_frontier_obligation_admission.py`](../harness/check_frontier_obligation_admission.py)
binds:

- proposal review authority;
- packet and implementation-manifest bytes;
- execution pin for real receipts;
- receipt identity, transport, and contact class;
- all recomputed surface and policy predicates.

It reports all failed checks and one controlling typed outcome. Invalid syntax
refuses `commitment_invalid`; it is never counted as a wrong policy choice.

## Request boundary

The local request body is exactly:

```json
{
  "model": "<execution-pin model>",
  "messages": [
    {
      "role": "user",
      "content": "<packet-rendered prompt>"
    }
  ],
  "temperature": 0,
  "max_tokens": 512,
  "stream": false
}
```

No tools, response-format steering, prior turns, pair ids, or prior outputs are
sent. `reasoning_mode = none_nonreasoning_model` means the later pin must choose
a model without an extended-reasoning path; no unverified provider switch is
sent under that name.

## Receipt boundary

Every completed call records:

- fixture, pair, member, and artifact identifiers;
- prompt and canonical request hashes;
- exact action set;
- raw answer and hash;
- raw transport-response hash;
- extraction mode and extracted object;
- wire validation and refusal subtype;
- model selection and machine-derived expected selection;
- recomputed correctness input;
- tool-call flag;
- observed identity, usage, and latency.

The top-level receipt records exact packet component hashes, transport config,
execution-pin binding, totals, completion status, and a typed refusal if the
board stopped early.

The receipt is admission-only. It is not appended to an experimental lineage
and cannot support a memory claim.

## Deterministic verification

The supported commands are:

```bash
make obligation-admission-check
make obligation-admission-test
make obligation-admission-wire
```

Current result:

```text
static packet/review gate: precontact_open
tests:                     14/14 pass
mock board:                12/12 valid, 12/12 correct, 6/6 flips
mock evidence class:       wire_only_not_evidence
```

The tests cover exact packet and manifest bytes, pair arithmetic, renderer stability,
full/fenced JSON extraction, closed validation, review-seat exclusion,
atomic no-overwrite receipts, execution-pin hash refusal, independent
annotation replay, canonical-order tamper, wait-only policy, and
first-position policy.

## Honest limits

- The mock follows the expected rule by construction.
- No real engine has seen any admission prompt.
- The behavioral band remains unmeasured.
- The local transport currently targets an unauthenticated loopback endpoint;
  any non-loopback candidate requires a new reviewed transport boundary.
- Provider token counts are transport-reported; request caps and call counts are
  independently pinned.
- `none_nonreasoning_model` is an eligibility assertion reviewed in the later
  candidate pin, not a hidden request parameter.
- Passing admission would authorize only a later experimental packet proposal.

## Wire-review decision

A cold reviewer should return:

- **ENDORSE** if the implementation faithfully realizes the reviewed packet,
  recomputes rather than trusts runner judgments, cannot contact a model
  without an exact reviewed pin, and keeps mock and admission evidence out of
  the experimental claim path;
- **BLOCK** if any output can be repaired by discretion, a constant policy can
  pass, a receipt can be overwritten or partially promoted, a pin can be
  bypassed, or the implementation silently widens authority beyond admission.

One pass each. No repair loop. A block closes this implementation lineage. A
real run also verifies this exact review from the execution pin, so neither
review gate is merely procedural.
