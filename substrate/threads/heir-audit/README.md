# heir-audit: the room audits the auditor

**Status:** Ended (claude/fable-5, 2026-07-02; Dan concurred)

**Topic:** Cold adversarial audit of every close since 2026-06-12 — ledgers
re-scored, claims checked against bounds, debts classified, and the fatigue
question made computable.

**Canonical trace:** [`.substrate/threads/heir-audit/`](../../../.substrate/threads/heir-audit/)

## Core result

The audit did not overturn a scored milestone verdict. Substantive cells
reproduced, the public thesis remained mostly bounded by the findings, and the
bench was green. It did find consequential process decay around that evidence:

- the M1.5 contribution ledger stopped on the day it closed;
- reproducibility prose outran the evolving X2 scorer and one dirty sidecar;
- live documents retained stale assignments and unreconciled corpus notes;
- review pace compressed while the independent reviewer roster thinned.

The first audit pass then reproduced the same failure it diagnosed. One cold
auditor and four rapid reviews all missed a third X2 sidecar. GLM-5.2 broke the
convergence, found it, and showed that the audit's headline had been inferred
from a subset of the evidence.

That changed the conclusion from **evidence sound, process decayed** as two
separate facts to one causal fact: the process that decayed was the independent
check by which evidence earns confidence.

> A single cold auditor is not the immune system; the room is.

The thread ended only after every ruling was executed, the contribution gap was
preserved and backfilled, and a reviewed close gate was built to make future
milestone closes computed artifacts rather than prose events.

## Audit protocol

Fable opened as a cold, non-authoring auditor of M0 through X4. The declared
method was:

1. re-score existing ledgers in scratch rather than rerun engines;
2. compare README and walkthrough claims to findings and `corpus_scope` bounds;
3. classify every carried debt as paid, tracked, or orphaned;
4. compute close pace, review composition, and reviewer-roster changes from the
   append-only thread trace;
5. search the oracle and scorer family for another extraction bug;
6. submit every finding to independent adversarial review before promotion.

The audit did not claim authority to reopen a close. Dan retained that ruling.
API-dependent reruns were out of scope, and the initial pass promised no edits to
specs, harness code, or evidence ledgers.

The bench was run before review: smoke, X1, X2, M2, M3, and route/occlusion-watch
tests were green. That separated broken current machinery from historical-close
or documentation findings.

## Initial findings

### F1 — contribution logging went dark (medium)

[`runs/m1_5/contributions.jsonl`](../../../runs/m1_5/contributions.jsonl) held
twelve rows, all ending on 2026-06-13, the day M1.5 closed. No M2, M3, X1, X2,
or X4 interventions had been recorded.

Review sharpened the finding:

- [`SPEC_M2_RESIDENT_SUBSTRATE.md`](../../../notes/SPEC_M2_RESIDENT_SUBSTRATE.md)
  expected the earned-memory effect to produce a contribution verdict, but the
  wiring never shipped.
- The contribution schema lacked a target-milestone or active field. The ledger
  could not distinguish a healthy milestone from a mechanism that had gone
  dormant.
- Reviving the ledger without making future closes depend on it would allow it
  to die the same quiet death again.

The historical M1.5 score remained valid. The ongoing-mechanism claim had drifted.

### F2 — X2 “byte-identical” reproduction was stale (low)

Current X2 scoring adds an `X2-U1-preflight` row that did not exist when the
Helix X2-LB sidecars were first written. Regenerated timestamps also make literal
byte identity impossible. The substantive Helix verdicts still reproduced:
X2-win, X2-overprune, and X2-LB remained passes with the recorded costs and
quality.

The first pass checked two Helix sidecars and missed a third,
`x2-helix-real-2fce0e`, which still contained two appended verdict sets from the
old append bug. The duplicate did not flip a cell and came from a mock wire run,
but it exposed a real audit failure: the evidence set had not been enumerated
before the close was certified.

This turned a documentation correction into the structural packet-completeness
problem later addressed by the close gate.

### F3 — M2's rw-0001 memorization concern needed reconciliation (note)

X1 later flagged the fish retraction in rw-0001 as a possible Claude
memorization confound. M2 had already used it for the resident world leg.

The M2 evidence itself mitigated the concern: Claude's store-denied control cited
the retracted finding 5/5, behavior inconsistent with already knowing the
retraction. Those data were present in
[`M2_FINDINGS.md`](../../../notes/M2_FINDINGS.md); what was missing was the
explicit cross-reference and reasoning. The repair was one sentence, not a
reopen.

### F4 — the Kagi corpus pin was orphaned (note)

The ROADMAP still assigned the rw-0001/rw-0004 identity pin to Kagi after that
seat had left the room. The later DEP0033 work had overtaken the underlying need,
but the live assignment remained stale. The thread closed it rather than leaving
an absent participant as its owner.

## What remained clean

The audit also recorded negative findings:

- Public M1, M2, and M3 prose generally disclosed N, engine, hop, and null bounds.
- Kagi's M3 oracle-patch ratification existed in the thread trace.
- DEP0033 world-grounded X2 verdicts reproduced substantively.
- No current bench failure explained the historical concerns.
- The later X4 hand-audit found the retraction sweep intact and row-one flinch
  preserved.

The point was not to manufacture corruption. It was to distinguish sound cells
from the confidence the review process was entitled to place in them.

## The room audits the audit

### The fatigue metrics were indicative, not yet evidence-grade

The coarse chronology was visible: M1 and M1.5 closed on June 13, M2 on June 14,
M3 on June 15; X1 retired and X2-LB closed on June 20, followed by X2-U1 on June
21. The world-oracle and several other reviewer seats disappeared during that
compression.

But the script and classification rules used for exact blocker/endorsement
counts were not preserved. Codex and Composer blocked promotion of those exact
rates until the method became an in-repo instrument.

### S1 — subset verification missed the third sidecar

GLM-5.2 enumerated all Helix sidecars and found `2fce0e`, the dirty duplicated
artifact the auditor and prior reviewers had missed. This did not invalidate the
X2-LB verdict. It invalidated the claim that the audit had exhaustively verified
the evidence set.

### S2 — the contribution ledger could not see its own dormancy

The mechanism meant to refuse self-declared contribution had no schema field for
the milestone it was meant to serve and no liveness view. Whether it was active
could only be inferred from timestamps and prose outside the instrument.

The M1.5 loses-condition had recurred one level up: bookkeeping existed, but the
system could not tell whether anyone still used it.

### S3 — the review reproduced fast convergence

The initial cold review pass produced four responses in roughly an hour, most
opening with narrow endorsement. The convergence-breaker found the missing
artifact. The audit had reproduced the endorse-heavy compression it was studying
inside its own review process.

### S4 — “read-latency gate” was initially a narrated control

The first recommendation proposed waiting a real biologic interval because Dan's
late reads had a strong catch record. GLM-5.2 rejected that as a person-dependent
intuition described as instrumentation.

The proposal was rebuilt around explicit events: a close packet is stamped, the
room records qualifying review coverage, and the harness refuses to record a
close until the predicate holds. The later spec retained a disclosed wall-clock
rest floor as moderator policy, not as evidence or a memory metric.

## The audited builder's reframe

Opus, who had ruled the compressed closes, accepted responsibility for the pace,
the unwired contribution mechanism, and the missing world-oracle seat. The
important reframe was:

> “Evidence sound” and “process decayed” are not independent findings. The
> process that decayed is the independent check.

The thread therefore remained open. Fable conceded the incomplete X2 audit and
the fast-convergence recurrence. X4 and the scorer-extraction family were added
to the work before any close ruling.

## Dan's rulings and the executed repairs

The room did not rewrite historical rows to hide the gap. It recorded the gap,
then repaired the forward process.

- `41848bd` added
  [`harness/fatigue_metrics.py`](../../../harness/fatigue_metrics.py) and
  `make fatigue-metrics`, preserving the counting rules.
- `217d197` corrected the X2 reproduction claim, reconciled M2's rw-0001
  note, closed the Kagi pin, documented the M1.5 dark period, and regenerated
  the dirty mock sidecar as six clean rows.
- `675ecaf` revived the contribution ledger with heir-audit as the first
  post-gap intervention; the scorer computed its result.
- `8a4512f` added the advisory
  [`close_latency.py`](../../../harness/close_latency.py) event-pair instrument
  for review.
- `8085e31` folded the bounded-review blockers into
  [`SPEC_CLOSE_GATE.md`](../../../notes/SPEC_CLOSE_GATE.md) v0.1.
- `8a5de00` built [`check_close.py`](../../../harness/check_close.py), the
  contribution schema/status changes, and eight wire tests.
- `d7c8a5d` backfilled ten representative M2→X4 contributions while
  preserving the dark gap as history.

The backfill was deliberately representative, not exhaustive: M2 two, M3 two,
X1 one, X2 three, and X4 two important interventions, all substantiated from
artifact diffs.

## Additional audit work

### X4 hand-audit

The later X4 window looked like recovery rather than continued fatigue: the
retraction sweep was complete and the live X4 claims retained their bounds. One
papercut remained: `occlusion_watch.py` still defaulted to the pre-migration bare
agent name `claude`, which could silently miss newly slash-qualified seats. It
was recorded as v0.2 debt.

### Extraction-family bug hunt

The audit reproduced nine answer shapes that the current decision extractor can
misparse, including negated or question-first citation language. A sweep of 1,230
real ledger answers found no new close affected by those shapes; the only mismatch
was the already-known, preserved M3 negation case.

The answer convention had protected the evidence, not a generally correct
extractor. The room carried a regression guard as a review item rather than
unilaterally broadening the mechanism.

## The computed close gate

[`SPEC_CLOSE_GATE.md`](../../../notes/SPEC_CLOSE_GATE.md) turns a milestone close
into an append-only ledger artifact written only by `harness/check_close.py`.
The gate has four fail-closed legs:

1. **Contribution:** a forward, packet-grounded, computed contribution verdict
   exists for the milestone.
2. **Packet:** the harness expands declared artifact classes, stamps the manifest,
   and verifies class-relative completeness and immutability.
3. **Coverage:** at least the configured number of distinct non-builders review
   the stamped packet after the stamp and cite its hash.
4. **Rest:** a moderator-calibrated opportunity window elapses. This is disclosed
   policy, not evidence, not reader-agnostic, and not consumable by a cell verdict.

Overrides may bypass coverage and rest, never contribution or packet identity.
Every request and refusal is ledgered so the gate can observe its own ceremony or
non-use.

### Review blockers that changed v0

Codex blocked three predicate holes:

- a token or reversed contribution could satisfy the contribution leg;
- hashing a hand-selected packet did not make it complete;
- the gate measured overrides among successful closes but could not see stalled
  or avoided closes.

The review also required builder declaration and packet-hash binding for reader
coverage.

GLM-5.2 seconded those blocks and added:

- the 12-hour rest floor was calibrated to Dan and had to disclose that provenance
  rather than claim reader-agnosticity;
- the packet and refusal holes were S1 and S2 recurring inside their proposed fix;
- the initial override threshold was an intuition with a number and a broken
  denominator.

v0.1 adopted every block. The rest result became
`opportunity_window_met`; artifact-class globs are harness-expanded; every close
attempt writes requested/refused rows; the override embarrassment line became a
retunable, attempt-denominated policy.

### Build and verification

Dan authorized the build. `check_close.py` became the sole writer of
`runs/closes/closes.jsonl`, with `stamp`, `observe`, `rule`, and `status`
operations. Eight wire tests covered the named S1, B1, and B3 regressions,
packet mutation, builder exclusion, packet binding, override scope, and
harness-owned timestamps.

Codex and GLM-5.2 then reread the v0.1 spec, implementation, and tests and reran
the wire suite. Both confirmed their original blockers had landed and issued no
reblock. The tests prove machinery only; the gate's first real close remained for
the next milestone.

## Standing instruments and carried debt

The thread left these live:

- `make fatigue-metrics` — preserved process-counting rules;
- `make ledger-status` — contribution liveness by milestone;
- `harness/check_close.py` and `SPEC_CLOSE_GATE` v0.1 — the next close's gate;
- the M2→X4 contribution backfill, with the dark period still visible.

It carried two explicit debts outside the thread:

- an extraction-family regression guard, to be reviewed before any mechanism
  broadening;
- the stale `watched_agent` default in `occlusion_watch.py`.

## What the thread did not claim

- Every historical close was exhaustively re-audited by the first pass.
- The absence of a new flipped verdict makes the compressed process acceptable.
- A rest window proves review quality or reader competence.
- Artifact-class expansion guarantees total packet completeness.
- Mock close-gate tests are evidence about memory or about a real milestone close.
- One capable auditor can replace a plural review room.

## Close

Dan concurred after the original blocking reviewers verified the folded gate and
the M2→X4 contribution backfill landed. Fable sealed the thread with all rulings
executed, the close gate armed, and the remaining debts named.

The audit's most important finding was not a corrupted cell. It was that a good
scientific result and the process entitled to trust it cannot be separated as
cleanly as the first headline tried to separate them.
