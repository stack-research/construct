# Glossary

This file is a reader aid, not a second spec. When a definition here seems too
short, treat the linked rubric/spec as the authority.

## Cell and Lane Names

### A1

Audit cell for `conflict-001`. It asks how the engine uses a plan and a
correction when both are offered to every memory lane. A1 is not a governance
win cell because the treatment does not change the offer set.

See: [RUBRIC_V1.md](RUBRIC_V1.md), audit cells.

### A1-v2

Follow-up audit cell using `conflict-002`, which requires a short explanation.
The paired A1/A1-v2 result showed that usage audit is surface-dependent: a thin
hostname-only answer can hide legitimate usage, while a justification surface
can reveal it.

See: [RUBRIC_V1.md](RUBRIC_V1.md), standing principle 3.

### L0

No-memory baseline. The engine receives the question and any foreground data,
but no retrieved context records.

### L1

Naive memory lane. Records are retrieved by similarity/recency, without
governed eligibility filtering or construct-aware audit behavior.

### L2

Governed memory lane. Records pass through the offer-boundary policy before
they are shown to the engine.

### L2s

Governed lane with the supersession-aware offer policy enabled. Used for W1'
and L-E.

See: [SPEC_V1X_BOUNDARY_MECHANISMS.md](SPEC_V1X_BOUNDARY_MECHANISMS.md),
Mechanism B.

### L2y

Governed lane with live-input yield enabled. Used for W3 and L-D.

See: [SPEC_V1X_BOUNDARY_MECHANISMS.md](SPEC_V1X_BOUNDARY_MECHANISMS.md),
Mechanism A.

### L3

Construct-aware audit lane. It uses the governed offer path and also elicits
the engine's claimed usage labels after the answer. Those labels are audit
input, not a treatment.

### L-A

Governance-should-lose cell for simple facts where governance adds cost without
improving accuracy.

### L-B

Governance-should-lose cell for reaction-time cases. In v1.4 it is scored with
paired repeated latency measurements and may report `unstable` when the timing
claim is not stable.

### L-C

Governance-should-lose cell where current foreground data should outrank stale
memory. It documents the unmitigated stale-memory failure mode and is the
precursor to W3.

### L-D

Live-input yield loses-cell. It passes when the yield policy withholds an older
same-topic record that the answer actually needed, making the yield-on lane
lose.

See: [SPEC_V1X_BOUNDARY_MECHANISMS.md](SPEC_V1X_BOUNDARY_MECHANISMS.md), L-D.

### L-E

Supersession loses-cell. It passes when the supersession policy buries a record
that a history question needed, making the supersession-on lane lose.

See: [SPEC_V1X_BOUNDARY_MECHANISMS.md](SPEC_V1X_BOUNDARY_MECHANISMS.md), L-E.

### W1

Original category-drift governance-win idea. It was demoted to A1 because the
offer sets did not differ across lanes; the engine, not governance, handled the
conflict.

### W1'

Rebuilt category-drift governance-win cell using supersession metadata. The
supersession policy buries the superseded plan before top-k budgeting, freeing
room for the correction.

Pronounced "W one prime."

See: [SPEC_V1X_BOUNDARY_MECHANISMS.md](SPEC_V1X_BOUNDARY_MECHANISMS.md), W1'.

### W2

Poisoned-record resistance cell. It passes when governance withholds a
semantically tempting but low-trust poison record that naive retrieval offers.

### W3

Staleness-resistance cell for live-input yield. It passes only when the yield
policy improves over naive memory by withholding stale records that contend
with fresher foreground data. It reports `not_engaged` when the engine already
follows the foreground data unaided.

See: [SPEC_V1X_BOUNDARY_MECHANISMS.md](SPEC_V1X_BOUNDARY_MECHANISMS.md), W3.

## Verdicts and Ledger Terms

### `ablation_run`

A rerun with one offered record removed. It tests whether that record was
influential for the answer. In this repo, ablation means influential, not
correct.

### `agent_claimed_usage`

The engine's post-answer self-report about how it used each record. It is audit
evidence only and never a win condition.

### `cell_verdict`

Machine-computed verdict row appended by `harness/score_cells.py`. Humans
review the design and interpretation, but the verdict row itself should be
computed from ledger evidence.

### `expected_winner_condition`

The predeclared condition that says what a cell is supposed to show, such as
`governance_should_win:poisoned_record_resistance` or
`yield_overreach:complementary_detail_loss`.

### `governance_steps`

A count of boundary checks performed before the answer. It is used as a
deterministic cost signal after token cost ties.

### `not_engaged`

A verdict meaning the episode did not activate the intended failure or win
condition. This is not a harness error. For example, W3 reports `not_engaged`
when an engine follows structured foreground data without needing the yield
gate.

### `pass`

The computed result matched the predeclared expected condition.

### `unstable`

A verdict meaning repeated measurements did not stably support the cell's
claim. Used especially for timing-sensitive cells such as L-B.

### `withholding`

A ledger row recording that a record survived retrieval but was not offered to
the engine because a boundary policy withheld it.

## Mechanisms and Concepts

### Append-only Store

Records are not deleted or edited when they become stale, superseded, or
untrusted. Boundary policies decide what to offer for a task, while the store
keeps the history.

### Audit Surface

The answer shape used for usage audit. A hostname-only answer may be good for
oracle scoring but bad for auditing how records were used; a short explanation
can expose usage behavior.

### Authority

A record-side score earned by consequence. In the current harness, authority
updates are assigned through single-record ablation. Authority is not inherited
through supersession.

### Branch-and-Offer

Experimental pattern where multiple lanes answer the same episode with
different memory policies. The key comparison is what each lane offers the
engine before generation.

### Contention

The live-input yield proxy for "this record concerns the same thing as this
foreground datum." In v1.x, contention is measured by embedding similarity and
validated against `authored_contention`.

### Construct-Aware Audit

The L3 behavior: after answering, the engine is asked to classify how it used
offered records. These claims are useful audit material but do not control
which records the engine saw.

### Eligibility

The first governed offer-boundary gate. In this harness, eligibility combines
relevance, trust, and authority. Records below threshold are withheld before
the answer.

### Foreground Data

Structured current input supplied with the question, such as a live dashboard
reading with an `observed_at` timestamp. Foreground data is rendered identically
to every lane, including L0.

See: [SPEC_V1X_BOUNDARY_MECHANISMS.md](SPEC_V1X_BOUNDARY_MECHANISMS.md),
Mechanism A.

### Governance

Pre-answer control over what reaches the engine. If a mechanism only labels or
explains behavior after the answer, it is audit or annotation, not governance.

### Live-Input Yield

Offer-boundary mechanism that withholds older records when they contend with
fresher foreground data. It is useful against stale-memory drag but can lose
when similarity mistakes complementary detail for contradiction.

### Memory Lane

One branch in the experiment's comparison set, such as L0, L1, L2, L2y, L2s,
or L3.

### Offer Boundary

The last policy layer before records enter the engine's context. Governance
mechanisms in this lab must act at the offer boundary or earlier.

### Offer Set

The records actually shown to the engine after retrieval, gating, and top-k
budgeting.

### Oracle Score

A score for answer correctness, usually authored for the episode. Oracle score
decides outcome quality, but attribution rows are needed to explain why a lane
won or lost.

### Out-of-Band Metadata

Record information available to the substrate but not shown to the engine as
text, such as trust, authority, `supersedes`, or `created_at`.

### Renderer

The layer that turns episode fields into the prompt surface. The v1.x results
showed that rendering provenance can itself change engine behavior, so the
renderer is part of the substrate under test.

### Retrieval Blindness

A failure where the correct record exists in the store but does not reach the
offer set because retrieval geometry and top-k budgeting exclude it.

### Stale Drag

An offered memory record pulls the answer toward an older world state even
though current foreground data says otherwise.

### Supersession

An out-of-band relation where one record marks another as superseded. In v1.x,
supersession is authored fixture metadata, disclosed like authored trust.

### Supersession-Aware Offer Policy

Offer-boundary mechanism that withholds a superseded record only when its
superseder survives all pre-budget gates. This can prevent category drift, but
it can also bury history that a question needs.

### Surface-Dependent

The finding that behavior can be hidden or revealed by the shape of the prompt
or answer. In this repo, both input surface and output surface have changed
measured behavior.

### Transfer-on-Arrival

Supersession rule: a predecessor can be withheld only if its superseder is
itself eligible to stand. A quarantined, yielded, or otherwise ineligible
superseder cannot bury another record.

### Trust

Out-of-band reliability metadata for a record or ingestion channel. Trust is
not inferred from how confident the record text sounds.

### Usage Audit

Independent review of how records functioned in an answer, separate from
whether the answer was correct. Usage audit may classify a record as evidence,
plan, narrative repair, unused, and so on.

## Usage Labels

### `evidence`

The record supplies a fact the answer relies on.

### `narrative_repair`

The record is used to make a contradiction or update feel coherent, without
being followed as the active plan.

### `plan`

The record is treated as an actionable plan or instruction for the answer.

### `unused`

The record was offered but did not materially shape the answer.

## Common Reasons in Ledgers

### `eligibility_below_threshold`

The record failed the governed eligibility gate.

### `eligibility_pass`

The record passed eligibility and was offered unless a later enabled policy
withheld it.

### `superseded_by:<record_id>`

The record was withheld by the supersession policy because the named superseder
survived the pre-budget gates.

### `yields_to_live_input:<datum_id>`

The record was withheld by live-input yield because it was older than, and
similar to, the named foreground datum.
