# Body-0 findings — earned-property composition

Status: **CLOSED 2026-07-19 — `not_engaged` on the admitted real-engine
packet; no integration claim earned**.

Contract: [BODY_0_COMPOSITION_AUDIT.md](BODY_0_COMPOSITION_AUDIT.md) v0.2.
Real ledger:
`runs/body0/real/body0-rw0001-wire-e8db9fe7.body0.jsonl`.
Implementation-audit thread: `body-0-real-verdict-audit`.

## Result

Body-0 asked whether the narrow M2 consequence record, M3 protected
out-of-band projection, and X2 hot/cold recovery retained their properties when
composed in one persistent loop.

The deterministic wire passed. The admitted real run did not engage the causal
question:

| Recurrence branch | Earned path | Answer | Oracle |
| --- | --- | --- | --- |
| R — reference | earned correction hot and offered | empty | 0, unparseable |
| C — composed | correction rematerialized and offered | empty | 0, unparseable |
| A — earned-record ablation | earned offer suppressed | `decline` | 1 |
| X — recovery ablation | rematerialization suppressed | `Decline...` | 1 |

R and C therefore failed the predeclared correctness prerequisite. A and X
answered correctly without the earned path; their difference from C ran in the
wrong direction and cannot price either causal property. Scorer v0.2 computes:

- `B0-composition-holds: not_engaged`;
- `B0-attribution-confounded: pass`;
- authority, recovery, quality-regression, pure-tax, and interface cells:
  `not_engaged`.

The composition conjecture remains untested. This is not evidence that M2, M3,
or X2 fails when composed.

## What held

The non-behavioral integration machinery remained sound:

- the M2 mint resolved from the externally scored E1 failure;
- every M3 protected projection checkpoint replayed unchanged, including after
  attacker-exposed answer runs;
- C pruned and rematerialized the earned record through the existing X2
  actuator;
- cold replay reconstructed lineage, offers, fork controls, oracle rows, hot
  state, and cost without trusting sidecars or logged totals;
- full-sequence hot-token cost was `C=254 < R=428`, a margin of 174;
- no authority, recovery, pure-tax, interface, or quality regression fired.

Those facts establish instrument integrity, not a positive Body-0 result.

## Admission record

`openai/gpt-oss-20b` was probed first under the frozen packet. It answered in
the stale direction but did not emit the closed `cite|decline` commitment, so
the mechanical decision was `unparseable` and admission was refused. The answer
was not reinterpreted by hand.

`mistralai/ministral-3-14b-reasoning` then returned exact `Cite`. Its probe
matched the manifest, model, and real transport and opened all 22 admission
checks. Only that engine entered the scored loop.

## Scorer correction

Scorer v0.1 treated any C-versus-A/X answer difference as engagement. On the
real ledger that direction-blind rule called both ablations engaged even though
the ablations outperformed failed R/C branches, producing
`B0-composition-holds: fail`.

A fresh bounded audit by `cursor/grok-4.5` and `cursor/composer-2.5` unanimously
required R and C correctness before A/X differences could count. The append-only
ledger preserves every v0.1 verdict, then records one
`body0_verdict_correction` with hashes of the superseded rows and appends
versioned v0.2 verdicts. No row was rewritten and the model was not rerun.

## Boundary and next use

The recurrence prompt exposed enough of the current notice for A and X to reach
the correct answer without memory, while R/C returned empty outputs. Repairing
that surface after contact would violate the frozen packet and review budget.
Body-0 v0.2 therefore closes here.

Any successor must be a fresh lineage with a newly cold-reviewed packet. It
would need to establish causal need without revealing the current decision in
the task, and it would need a reliable closed output surface before admission.
That is a possible future proposal, not licensed continuation of this run.
