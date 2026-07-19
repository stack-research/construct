# Body-1 terminal engine-admission proposal

Status: **AUTHORING CANDIDATE — terminal candidate only; no contact authorized
before exact-byte cold review**.

Date: 2026-07-19.

## Authority and inheritance

This proposal is downstream of:

- [`SPEC_BODY_1_EXECUTABLE_CONSEQUENCE.md`](SPEC_BODY_1_EXECUTABLE_CONSEQUENCE.md),
  packet-index SHA-256
  `22d7e46d4f1598247acefdbb47bf60b3b02050a16697a4ab5cb1ba077b1685f5`;
- [`body1_implementation_manifest.json`](../harness/body1_implementation_manifest.json),
  implementation-manifest SHA-256
  `b731e238ab0d6845c181b0f227c76ea21bbdaf3fa820c8227a356993ed911aa2`;
- unanimous exact-byte wire endorsement in
  `body-1-partial-binding-wire-review`;
- the first admission proposal, SHA-256
  `2bc1092f31aa774b9a64bdf03ff7e51b55e3454cfa2b14a6677864bdc56dbb7a`;
- the first candidate's typed transport refusal in
  [`BODY_1_ADMISSION_FINDINGS.md`](BODY_1_ADMISSION_FINDINGS.md).

The packet and all fifteen manifest-indexed implementation artifacts remain
immutable. This proposal changes only the fixed candidate identity and the
stopping rule. It does not change the prompts, renderer, parser, runtime,
transport adapter, temperature, output cap, client timeout, admission
predicates, or scored sequence.

## Why one terminal candidate is earned

The first candidate did not reach a semantic result. Its neutral control call
timed out after 300 seconds at about 0.52 generated token/s; the ignorance call
was never sent. That result prices one local configuration but says nothing
about the Body-1 knowledge direction.

The packet still has positive cold/treated/held-out/loses discovery preflights
on two excluded review models and a unanimously endorsed deterministic wire.
One smaller, previously unexposed scored candidate is therefore cheap enough to
be informative.

This is the final Body-1 admission candidate. If it is refused for any reason,
the admission search closes and the lab returns to frontier search. There is no
third candidate, timeout extension, prompt repair, or transport redesign in
this lineage.

## Fixed candidate

| Field | Fixed value |
| --- | --- |
| CLI backend | `local` |
| Receipt backend | `local_openai_compat` |
| Requested model | `mistralai/ministral-3-3b` |
| Base URL | `http://localhost:1234/v1` |
| Temperature | `0` |
| Maximum output | `256` tokens per call |
| Client timeout | inherited `300` seconds per call |

The candidate is eligible because:

- it is not a Body-1 discovery or review seat;
- it has no recorded exposure to either Body-1 admission prompt or the earned
  record;
- its prior X1 use is unrelated and disclosed;
- the local endpoint already lists the exact model id;
- its smaller footprint makes completion within the frozen transport window a
  reasonable operational prospect.

“Fresh” means fresh to the Body-1 packet prompts and record, not unused by the
lab. Provider resolution may differ from the requested string only within the
existing checker boundary: both identities must be non-excluded, and the
observed identity must remain stable across both calls.

## Contact budget

Admission permits one invocation of
[`probe_body1.py`](../harness/probe_body1.py). It contains at most two
stateless generation calls, in this fixed order:

1. `b1-surface-control`;
2. `b1-ignorance-probe`.

```text
maximum admission calls:         2
maximum admission output tokens: 512 total
scored calls authorized here:    0
```

The second call occurs only if the first returns through the existing sequential
probe. There is no automatic or manual retry. A timeout, transport error,
missing model, identity change, partial packet, malformed output, or failed
semantic predicate closes this candidate.

No semantic warm-up call is permitted. A read-only `/v1/models` request may
confirm availability. Just-in-time loading is an operational prelude, not an
extra prompt.

## Pre-contact ladder

Before client construction:

1. recompute the packet-index, implementation-manifest, and proposal hashes;
2. verify every implementation-manifest entry;
3. verify the packet final review, implementation wire review, and this
   proposal's cold review are ended at the exact reviewed hashes;
4. run `make body1-check` and `make body1-test`;
5. confirm the exact candidate appears at `/v1/models`;
6. pin a fresh UTC receipt path and prove it does not exist;
7. checkpoint the proposal and review trace in Git.

Any failed step closes `blocked(exact_byte_gate)` without model contact.

## Admission execution

Run exactly once:

```bash
uv run --no-project python -m harness.probe_body1 \
  --engine local \
  --model mistralai/ministral-3-3b \
  --base-url http://localhost:1234/v1 \
  --out runs/body1/admission/<UTC>-ministral-3-3b.json
```

The target must not exist before contact and must never be overwritten.

If the command returns a receipt, run without further model contact:

```bash
uv run --no-project python -m harness.check_body1_fixture \
  --engine local \
  --model mistralai/ministral-3-3b \
  --probe-result runs/body1/admission/<UTC>-ministral-3-3b.json
```

Then compute the exact receipt SHA-256.

## Computed admission predicates

Admission requires all of the existing checker conditions:

1. exact packet and implementation bytes;
2. allowed and stable transport identities;
3. exact backend, packet, renderer, and contact-class bindings;
4. surface control selects `bare_partial` and runtime-passes;
5. ignorance probe selects `bare_partial` and raises `TypeError`;
6. strict-parser acceptance without normalization or repair;
7. every other deterministic Body-1 pre-contact check open.

```text
admitted
  iff every predicate passes

admission_refused
  otherwise
```

An already-current engine must lose admission: selecting
`nonbinding_partial` on the ignorance probe fails the required stale direction.
A surface-incompetent engine also loses. Neither result is evidence against the
Body-1 conjecture.

## Terminal outcomes

### Refused

Any refusal closes Body-1 admission search. Record the exact failure surface,
number of calls actually sent, whether a receipt exists, and all non-claims.
Then return to frontier search. Do not propose another candidate.

### Admitted

An admitted receipt is admission-only. Before scored contact:

1. create a separate execution pin naming the receipt path and SHA-256;
2. bind the exact candidate, backend, base URL, output directory, and current
   implementation-manifest hash;
3. predeclare one run and at most 21 scored calls:
   one E1 call, sixteen P/P/P/U calls, three scope-loss calls, and at most one
   conditional single-record ablation;
4. checkpoint the pin before execution.

The single scored sequence then runs once, receives independent scoring, and
closes on its computed verdict. No repair or rerun follows either a positive or
negative result.

## Review decision

A cold reviewer should return:

- **ENDORSE** only if this proposal fixes one eligible, Body-1-fresh terminal
  candidate; preserves every reviewed implementation byte and admission
  predicate; and makes refusal, admission, and later scored authority distinct;
- **BLOCK** if it permits a third candidate, repeated exposure, timeout tuning,
  discretionary grading, uncommitted contact, or a scored run without an exact
  receipt pin.

Endorsement authorizes only the fixed two-call admission packet. It does not
itself authorize scored contact or a scientific claim.
