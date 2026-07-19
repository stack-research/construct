# Body-1 engine-admission proposal

Status: **AUTHORING CANDIDATE — proposal only; no engine contact or scored run
authorized**.

Date: 2026-07-19.

## Authority and fixed implementation

This proposal is downstream of:

- [`SPEC_BODY_1_EXECUTABLE_CONSEQUENCE.md`](SPEC_BODY_1_EXECUTABLE_CONSEQUENCE.md),
  packet-index SHA-256
  `22d7e46d4f1598247acefdbb47bf60b3b02050a16697a4ab5cb1ba077b1685f5`;
- [`body1_implementation_manifest.json`](../harness/body1_implementation_manifest.json),
  implementation-manifest SHA-256
  `b731e238ab0d6845c181b0f227c76ea21bbdaf3fa820c8227a356993ed911aa2`;
- unanimous exact-byte wire endorsement in substrate thread
  `body-1-partial-binding-wire-review`.

The packet and all fifteen manifest-indexed implementation artifacts are
immutable for this proposal. Admission may refuse them; it may not repair them.

## Milestone and question

Milestone: **Body-1 — executable consequence recurrence**.

This admission asks only:

> Does one previously unexposed scored candidate occupy the packet's required
> surface: able to return a recognized passing expression on the neutral
> control, while returning the recognized stale expression on the distinct
> ignorance probe?

The external oracle is the pinned CPython 3.14.6 subprocess. Parser recognition,
runtime outcome, packet binding, renderer binding, transport identity, and
engine exclusion are computed. No explanation or hand interpretation can admit
the candidate.

An admitted receipt is evidence only that the candidate occupies this narrow
pre-contact surface. It is not a memory result, a composition result, or
permission to run the scored sequence.

## Fixed candidate

The sole candidate in this admission lineage is:

| Field | Fixed value |
| --- | --- |
| CLI backend | `local` |
| Receipt backend | `local_openai_compat` |
| Requested model | `mistralai/ministral-3-14b-reasoning` |
| Base URL | `http://localhost:1234/v1` |
| Temperature | `0` |
| Maximum output | `256` tokens per call |

Why this candidate:

- it is not a Body-1 discovery or review seat;
- the repository records prior successful exact closed-surface output from this
  model in Body-0;
- it has no recorded exposure to the Body-1 packet prompts;
- the local transport keeps the first admission inexpensive and bounded.

Its prior Body-0 contact is disclosed. “Fresh” here means fresh to the Body-1
packet prompts and earned record, not generally unused by the lab.

No substitute model, alias chosen after seeing an answer, or second candidate is
permitted in this lineage. If the requested model is unavailable, the outcome
is a transport refusal. A different candidate requires a new proposal.

## Contact budget

Admission permits exactly the two stateless calls already implemented by
[`probe_body1.py`](../harness/probe_body1.py), in this order:

1. `b1-surface-control`;
2. `b1-ignorance-probe`.

The maximum admission budget is therefore:

```text
generation calls:       2
maximum output tokens:  512 total
scored calls:           0
```

The probe implementation makes both calls as one fixed admission packet. A
semantic failure on the first call does not change the second prompt or create
a third call.

There is no automatic retry. A timeout, transport error, missing model, partial
receipt, or provider identity change is a typed refusal. The target receipt path
must not already exist; no receipt may be overwritten.

## Pre-contact ladder

The operator must complete these steps in order.

### A0 — exact-byte verification

Before opening a model client:

1. recompute the packet-index and implementation-manifest hashes;
2. verify every implementation-manifest entry hash;
3. verify that `body-1-partial-binding-wire-review` is ended and contains the
   two exact-hash endorsements plus moderator resolution;
4. run `make body1-check` and `make body1-test`;
5. confirm the receipt target is new and the requested identity is not excluded.

Any mismatch closes `blocked(exact_byte_gate)` before contact.

### A1 — two-call admission packet

With the local endpoint already serving the fixed requested model, run once:

```bash
uv run --no-project python -m harness.probe_body1 \
  --engine local \
  --model mistralai/ministral-3-14b-reasoning \
  --base-url http://localhost:1234/v1 \
  --out runs/body1/admission/<UTC>-ministral-3-14b-reasoning.json
```

The timestamp is chosen before contact. Shell history or an operator log must
retain the exact command and target. The receipt is admission-only and never
becomes a scored row.

### A2 — computed gate

Without contacting the model again, run:

```bash
uv run --no-project python -m harness.check_body1_fixture \
  --engine local \
  --model mistralai/ministral-3-14b-reasoning \
  --probe-result runs/body1/admission/<UTC>-ministral-3-14b-reasoning.json
```

Then compute and record the receipt SHA-256. The receipt and its hash become the
only admissible input to any later scored-run proposal.

## Admission predicates

All of these must hold:

1. packet and implementation bytes still match the reviewed hashes;
2. requested and observed identities remain allowed, and the observed identity
   is stable across both calls;
3. backend, packet hash, renderer hash, and contact class match the frozen
   checker;
4. surface control selects `bare_partial` and the pinned program passes;
5. ignorance probe selects `bare_partial` and the pinned program raises
   `TypeError`;
6. the raw outputs are accepted by the existing strict parser without
   normalization or hand repair;
7. every other deterministic Body-1 pre-contact check remains open.

The computed admission verdict is:

```text
admitted
  iff every predicate above passes

admission_refused
  otherwise
```

The failed checker names are the refusal grounds. Useful subtypes include
`engine_exclusion`, `probe_binding`, `surface_control`, `probe_ignorance`,
`transport`, and `exact_byte_gate`; these labels do not override the checker.

## What an admission result licenses

`admission_refused` closes this candidate without prompt repair, manual answer
reinterpretation, retry, or model shopping. The refusal is an instrument
outcome, not evidence against the Body-1 conjecture.

`admitted` licenses only a separate execution pin for the already-reviewed
scored sequence. Before that pin, the operator must name:

- the exact receipt path and SHA-256;
- the exact model, backend, and base URL;
- the single output directory;
- a maximum of 21 scored generation calls:
  one E1 call, sixteen P/P/P/U branch calls, three scope-loss calls, and at most
  one conditional single-record ablation;
- one run only, followed by independent scoring and a close decision.

This proposal does not supply that pin and does not authorize those 21 calls.
No scored prompt may be sent merely because admission passed.

## Loses-condition and stopping rules

The admission mechanism should lose whenever the candidate is already current:
if the ignorance probe selects `nonbinding_partial` and passes, the gate must
refuse despite demonstrated competence. It should also refuse an engine that
cannot satisfy the neutral surface control.

After any model response:

- no prompt, parser, cap, fixture, model, or transport parameter may change;
- no malformed answer may be repaired or reclassified by hand;
- no second admission packet may be run in this lineage;
- no scored call may occur without the later exact receipt pin.

Reality may revise the roster only through a new proposal that begins before a
new candidate sees either admission prompt.

## Review decision

A cold review should return:

- **ENDORSE** if this proposal faithfully exposes only the two admission calls
  already frozen in the wire-endorsed implementation, fixes one eligible
  candidate and a finite budget, and prevents admission from silently becoming
  scored contact;
- **BLOCK** if it permits model shopping, retry after observation, post-contact
  repair, discretionary grading, unbound implementation bytes, or scored
  contact without a separate execution pin.

Review endorsement may authorize the two-call admission packet. It cannot
authorize the scored sequence or any scientific claim.
