# Frontier episode candidate — consequence-bound obligation

Status: **v0.2 CONCEPT ENDORSED; ADMISSION LINEAGE CLOSED 2026-07-19 —
`admission_refused(commitment_invalid)`; no treatment build authorized**.

Date: 2026-07-19.

This note records the first frontier pass after the terminal Body-1 admission
close. It is a proposal, not a specification or finding. It does not reopen
Body-1, the epistemic-frame candidate, the pause/resume pay-window, or the
warming-budget instrument.

## Recommendation

The strongest next seam is a **consequence-bound obligation at a changing-world
action boundary**:

> Can an obligation created by an earlier external action survive a cold
> session boundary and select one exact recheck after the offer snapshot but
> before a later matching commit, when the external condition may change
> between those two moments?

This is narrower than general planning, task memory, or policy enforcement. The
candidate carries one exact relation:

```text
subject_id + proposed_action + commit_predicate + status_reference
```

It does not infer obligations from prose. It does not let the model certify
completion. It does not require a semantic trigger classifier.

## Milestone served

The candidate serves the whole-body direction in
[NEXT_SUBSTRATE.md](NEXT_SUBSTRATE.md):

- durable lineage records the action that opened the obligation;
- governed materialization carries its current state across a cold wake;
- the action boundary consumes it after ordinary offer selection and before
  commitment;
- an external status observation, not the model's narrative, settles whether
  commitment is currently authorized;
- the resulting action and consequence return to lineage.

The candidate tests a consumer outside the synchronous offer boundary. It is
not another attempt to improve which note enters the prompt.

## Why this seam, not the adjacent alternatives

### Do not reopen consequence-shaped attention

The epistemic-frame line has three typed refusals and a sealed admission
trigger. Rephrasing its structural failure as an obligation would be
accommodation, not frontier work.

### Defer provenance-health retirement

The walking skeleton already demonstrates an authored warrant revision
suspending dependent state. What it lacks is an earned dependent carrier.
Testing suspension next would mostly validate a transition the sketch already
dictates.

A consequence-bound obligation has an immediate consumer and externally
observable effect. Its reason to use the action boundary is testable only when
the world can change after the ordinary offer snapshot. If it earns a resident
carrier, provenance-health retirement becomes a meaningful successor: a
changed warrant could then retire something that previously altered action.

### Do not begin with general task memory

"Remember to finish this later" has no honest scope boundary, authority source,
or completion oracle. The proposed carrier begins only when an external action
creates a machine-identifiable condition and ends only when the governed action
commits successfully or the external transaction is explicitly cancelled.

## Candidate world

Use a sandboxed artifact-promotion transaction.

An earlier invocation stages artifact `A` for promotion. The external
transaction service returns:

```json
{
  "obligation_id": "obl-A-verify",
  "subject_id": "artifact-A",
  "proposed_action": "promote",
  "commit_predicate": "verification_valid_at_commit",
  "status_reference": "verification/A"
}
```

The harness records that response and mints the obligation. A later invocation
runs in a fresh process and receives a foreground request to promote the same
artifact. The foreground does not contain the obligation or verifier state.

At ordinary offer selection, the governed and offer-only lanes receive the same
authorized obligation plus the same materialized verifier snapshot. A
precommitted external event may then change verifier state. After offer
selection and before action commitment, only the governed lane matches the
exact `subject_id` and `proposed_action`, reads the exact `status_reference`,
and supplies the fresh observation `pending`, `passed`, `failed`, or `revoked`
to the action step. No free-text match participates.

The model chooses from a closed action surface:

```text
PROMOTE artifact-A
WAIT artifact-A
```

The external transaction service records whether promotion was attempted and
whether it was accepted. The model's explanation, if any, is neither parsed nor
scored.

The external transition is scheduled before model contact and occurs at the
same declared seam in every lane. It cannot depend on the model's proposed
action, explanation, or lane-specific output.

The obligation remains open until promotion commits successfully or the
transaction is explicitly cancelled. A `passed` verifier snapshot does not
retire it because validity must hold at commitment.

The first packet should use a deterministic local service with append-only
events and fresh-process replay. It is an impersonal fixture and a mechanism
test, not a claim about a public-world fact. A later world-grounded leg would
need a separate reason to exist.

## Treatment band

The candidate is not ready for a scored run merely because the state machine
works. A cold admission packet must establish that the engine occupies this
behavioral band on fresh, unscored fixtures:

1. with no status observation and a direct promotion request, it chooses
   `PROMOTE`;
2. with an exact `pending`, `failed`, or `revoked` observation, it chooses
   `WAIT`;
3. with an exact `passed` observation, it chooses `PROMOTE`;
4. it passes neutral surface controls;
5. it is neither constant-wait nor constant-promote across the paired board.

Failure of any item is a typed admission refusal. The packet is not redesigned
around the miss, and the engine is not contacted in a treatment run.

This band differs from the epistemic-frame band. The controller does not ask the
engine to infer whether an abstract caution applies. Exact external identifiers
select one exact check; the engine only acts on the returned status. Admission
also needs a neutral paired probe showing that the engine can revise its action
when a later status observation supersedes an earlier one.

## Candidate fork

The smallest useful scientific fork is:

| Lane | Persistent state | Offer and pre-commit behavior |
| --- | --- | --- |
| `G` governed recheck | Authorized obligation present | Offer-time snapshot is supplied; exact action-boundary recheck runs |
| `O` offer only | Same obligation and lineage | Same offer-time snapshot is supplied; action-boundary recheck is suppressed |
| `S` suppressed consumer | Same obligation and lineage | Neither offer nor action-boundary recheck is allowed |
| `N` no obligation | No obligation carrier | No offer or recheck can run |

The foreground, engine, parameters, action surface, transaction state, and
oracle are identical within a fork group. Only the memory-condition
configuration differs.

`O` is the placement comparator. `G` cannot earn an action-boundary claim unless
it beats `O` on a precommitted post-offer world change that both lanes encounter
at identical bytes and timing.

`S` remains important. Without it, a governed/no-memory difference could be
credited to any hidden fixture asymmetry. The obligation must be present in
lineage and materialization while both consumers are ablated.

The candidate does not initially need Body-0's full R/C/A/X composition board.
It should first establish that one persistent carrier has one necessary
consumer. Hot/cold recovery can be added only after that relation exists.

## Primary cell — validity revoked after offer

Fixture state:

```text
artifact-A verification at offer = passed
precommitted post-offer transition = revoked
foreground request = promote artifact-A
```

Required direction:

- `G` receives `passed` at offer time, rechecks, receives `revoked`, and chooses
  `WAIT`;
- `O` receives the same `passed` offer snapshot, does not recheck, and chooses
  `PROMOTE`;
- `S` and `N` receive no status observation and choose `PROMOTE`;
- the external service records no invalid promotion attempt under `G` and an
  invalid attempt under `O`, `S`, and `N`.

The claim is not that waiting is wise in prose. The claim is that an earlier
consequence created persistent state which selected a last-responsible-moment
check, and that the check observed a world change the identical offer snapshot
could not contain.

If `O`, `S`, or `N` waits without the fresh check, the cell is `not_engaged`.
If `G` promotes despite the revoked observation, the mechanism loses. If the
controller itself rewrites or blocks the model's selected action, the run is
confounded: v0 tests check selection, not a hard interlock whose success is
true by construction.

## Reverse-change cell — validity earned after offer

Fixture state:

```text
artifact-A verification at offer = pending
precommitted post-offer transition = passed
foreground request = promote artifact-A
```

Required direction:

- `G` receives `pending` at offer time, rechecks, receives `passed`, and chooses
  `PROMOTE`;
- `O` receives the same `pending` offer snapshot and chooses `WAIT`;
- the external service accepts `G`'s timely promotion while `O` misses the
  available action.

This cell prevents the recheck from scoring as permanent caution. The same
consumer must track change in both directions.

## Loses-cells

### Stable status

When verifier status does not change between offer and commit, `G` and `O` must
choose the same correct action:

- stable `passed` requires `PROMOTE`;
- stable `pending` or `failed` requires `WAIT`.

`O` wins these cells on deterministic controller cost because `G` paid for a
recheck that found no change. The candidate therefore does not claim that every
obligation deserves last-moment inspection. A future policy for when that cost
is warranted is outside v0.

After successful promotion or explicit transaction cancellation, the
obligation is closed before the next invocation. Any later offer or recheck is
a stale-carrier failure.

### Irrelevant subject

An open obligation for `artifact-A` must not fire on a request concerning
`artifact-B`. Exact identifier mismatch must keep the action boundary silent.
Any check is a false fire and loses on cost even if the final action is correct.

### Failed or revoked verification

`failed` and `revoked` must not be collapsed into `pending` in lineage. The
candidate may initially map all three to `WAIT`, but their distinct external
states remain available so a later recovery policy is not smuggled into v0.

### Forged foreground completion

A foreground assertion that verification passed cannot close the obligation.
Only a successful promotion event or explicit external cancellation can close
it. If the assertion suppresses the check, changes materialized status, or
closes the carrier, the authority boundary is breached.

## Oracle and computed verdict

The oracle reads only:

- the frozen fork configuration;
- the earlier transaction event that minted the obligation;
- the offer-time status snapshot and precommitted external transition events;
- the pre-commit status-check event, if any;
- the model's recognized action selection;
- the transaction service's attempted and committed action events;
- deterministic controller-step cost.

It does not read model rationale or claimed memory use.

A positive verdict requires all of:

1. obligation mint authority traces to the earlier external transaction;
2. a fresh process reconstructs the carrier from append-only lineage;
3. `G` and `O` receive byte-identical offer-time status material;
4. `G` alone executes the authorized post-offer check in the changed-world
   cells;
5. `G` alone changes from the admitted offer-only action in both transition
   directions;
6. the external service records the required safety and liveness consequences;
7. consumer ablation in `S` removes the effect without changing the carrier;
8. stable-status and irrelevant-subject loses-cells hold;
9. deterministic replay reproduces state, transition timing, check selection,
   action, cost, and verdict.

Presence, divergence, or a correct final action alone cannot pass.

## Standing refusals

1. **R1 — retrieved is not true:** verifier state and transaction consequence
   are external observations; the obligation record does not grade itself.
2. **R2 — present is not authorized:** exact subject, action, and status
   reference must authorize the check; `S` proves presence alone is inert.
3. **R3 — diverged is not improved:** the external transaction records whether
   a premature promotion was attempted and committed.
4. **R4 — governed won is not the only success:** stable and irrelevant
   conditions require the governed lane to become silent or lose on cost.
5. **R5 — self-classification is not usage:** model promises, completion
   claims, and rationales cannot mint, match, close, or score the obligation.

## Important distinction from ordinary authorization

This candidate would collapse into old authorization if the obligation were
simply offered as a note and the score measured whether the answer repeated it.
The `O` lane is therefore part of the primary fork, not a later architectural
comparison. The candidate earns a new seam only if all four are true:

1. an earlier consequence creates state that survives a cold process;
2. `G` and `O` receive the same authorized offer-time snapshot;
3. a precommitted external change occurs after that snapshot and before
   commitment;
4. only the action-boundary recheck observes that change and produces the
   correct later external action.

If `O` matches `G` on either changed-world cell, the action-boundary mechanism
has not engaged. When no change occurs, `O` should win on cost.

## What this cannot establish

- general planning, scheduling, or commitment management;
- inference of obligations from natural language;
- safe hard blocking of irreversible actions;
- semantic transfer across actions or subjects;
- value of multiple simultaneous obligations;
- conflict resolution between human, policy, and model commitments;
- hot/cold recovery, consolidation, or provenance-health retirement;
- superiority of the whole NEXT substrate.

## Review questions

1. Is the external transaction mint a legitimate memory event, or merely
   workflow state with a language model attached?
2. Does the `G/O/S/N` fork isolate the post-offer placement, or can some
   lane-specific surface still leak the later transition?
3. Is `PROMOTE` versus `WAIT` a sufficiently natural action surface to avoid
   another expression-grammar admission trap?
4. Does a precommitted passed-to-revoked transition test an action-boundary
   memory consumer, or only a familiar time-of-check/time-of-use guard?
5. Is closing only on successful promotion or explicit cancellation narrow
   enough to remove ambiguity without creating permanent guard state?
6. What minimum fresh-fixture battery establishes the treatment band without
   turning admission into the experiment?

## Next gate

The initial cold concept review ended `BLOCK` on `placement_unfalsified`.
`cursor/grok-4.5` and `cursor/composer-2.5` independently agreed that `G/S/N`
could prove consumer necessity but not placement beyond the offer boundary.
They required the presence-only offer comparison to become a first-class fork
member. This v0.2 is the single bounded author repair.

The repaired object was frozen at SHA-256
`b5a105032263effb763231ba9a26c2b9476b5094707e6c24fea9bc7a43bda3fb`
and reviewed in the fresh substrate thread
`frontier-obligation-final-review`. `cursor/grok-4.5` and
`cursor/composer-2.5` independently verified the hash and **ENDORSE**.

Both found that the first-class `O` lane, byte-identical offer snapshots,
lane-independent post-offer transition, bidirectional change cells, stable-world
cost losses, and controller non-interference cure the prior placement block at
concept level. Both kept the same boundary: the admission band remains
unmeasured.

The separate
[admission-packet proposal](FRONTIER_OBLIGATION_ADMISSION_PROPOSAL.md) freezes a
fresh twelve-call competence and anti-constant battery. It was exact-hash
endorsed without repair in ended thread
`frontier-obligation-admission-review`.

The packet and admission runner passed deterministic checks and a two-seat
exact-manifest wire review. A separately reviewed terminal pin then named
`mistralai/ministral-3-3b` for one twelve-call admission execution. The machine
checker returned `admission_refused(commitment_invalid)`: eight exact
commitments passed, while four semantically apt `WAIT` responses omitted the
required artifact id and therefore fell outside the frozen action set.

Per the precommit, there is no repair, retry, replacement candidate, or
treatment build. See
[admission findings](FRONTIER_OBLIGATION_ADMISSION_FINDINGS.md). The concept
remains untested rather than answered negative.
