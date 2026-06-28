# Glossary

This file is a reader aid, not a second spec. When a definition here seems too
short, treat the linked rubric/spec as the authority.

Some entries use explicit HTML anchors (`<a id="..."></a>`) when GitHub's
auto-generated heading slugs collide or are awkward — link to those ids from
`AGENTS.md` and other repo files.

**Editors:** heading text, `<a id="">` anchor names, and definition meaning are
all link targets. Renaming a heading or anchor silently breaks callers; changing
a definition's meaning silently misleads readers who followed a link expecting a
specific concept. Search for `GLOSSARY.md#<name>` across the repo before touching
any entry; update all callers when renaming.

## Plain-language bridges

Reader-facing words in [README.md](../README.md) and their shop terms. When
README uses plain vocabulary, it links here; the linked entries below carry the
formal definitions.

### Indexed Notes

<a id="indexed-notes"></a>

Keeping records and letting retrieval decide what enters the prompt — similarity
and recency over an [append-only store](#append-only-store), without
[governance](#governance) filtering first. The naive lane is [L1](#l1); colloquially,
"remember everything you indexed."

### World-Picture

What the agent is allowed to believe and act on — the agent's picture of its
world, not chat UX memory about the human user. Shaped by [governance](#governance),
the [offer set](#offer-set), and [out-of-band metadata](#out-of-band-metadata).

### Explicit Memory

Memory that crosses the [offer boundary](#offer-boundary) for *this* answer —
which records compete to enter the prompt right now. The M-track governs this
layer synchronously, before generation.

### Implicit Memory

<a id="implicit-memory-substrate"></a>

Memory that shapes the agent between answers: what stays in the [hot store](#hot-store),
what moves to [cold lineage](#cold-lineage) without erasure, what the agent is
disposed to remember at all. The X-track tests this layer; see also
[three-guardrail stack](#three-guardrail-stack).

### Resident

A repo-native agent that lives on a governed store across real sessions (M2).
Forkable and audited — the lab tests governed memory, not a crowned continuous
self.

### Heir

The second instance in a session handoff (M1): it inherits
[ablation](#ablation_run)-filtered memory from the first rather than cold
re-reading the whole store.

### Earned Trust

Trust backed by consequence — [authority](#authority), lineage, and supersession
links carried as [out-of-band metadata](#out-of-band-metadata), not as prompt
text the model can be tricked into overriding.

### Asserted Trust

Trust declared at write time or on an unauthenticated channel — [trust](#trust)
metadata without earned [authority](#authority). A prior, not a proof.

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

<a id="w1-prime"></a>

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

## X-track terms (implicit-memory substrate)

The X-track runs parallel to the M-track: implicit memory shapes *the offerer*
between episodes, where the explicit offer boundary shapes *the answer*. These
terms appear in the X1/X2 specs, ledgers, and scorers. See
[ROADMAP.md](ROADMAP.md) (X-track) and
[SPEC_X2_PRUNE_TO_COLD_STORE.md](SPEC_X2_PRUNE_TO_COLD_STORE.md) for authority.

These terms descend from the two-plane vocabulary in the lab-1→lab-2 bridge
glossary, [notes/previous/review/glossary.md](previous/review/glossary.md)
(*"Forming vocabulary for lab two"*): the **lineage plane** (immutable,
replayable record of what happened — the audit floor) and the **cognitive
plane** (the mutable layer over it). The hot-store / cold-lineage split below is
construct's materialization-axis naming for that ancestry; read the bridge
glossary's *lineage plane* before taking "cold lineage" as a term that sprang
from nowhere.

### Hot Store

The materialized candidate universe `select_offers` ranks over for a branch
(passed as `inherited_record_ids`). Carrying it has a measured cost. Prune evicts
from it; rematerialize returns to it.

### Cold Lineage

The append-only, immutable record universe (`all_record_ids`). A pruned record
leaves the hot store but **survives in lineage**. There is **no erase-from-lineage
verb, by design** — see *Immutable-Lineage Invariant*. Inherits the bridge
glossary's **lineage plane** (lab-1→lab-2): immutable, replayable, the audit
floor. "Cold" marks the materialization axis — the [hot store](#hot-store)'s
counterpart — over a plane that is immutable by definition.

### Prune

Evict a record from the hot store (it stops being an offer candidate). The record
is not deleted — it moves to cold lineage, recoverable by rematerialization.

### Rematerialize

Return a cold record to the hot store under a ledgered, oracle-gated reason — the
recovery the offer boundary has no verb for. The two-plane split made concrete.

### Hot-Store Cost / `hot_tokens`

The deterministic, substrate-native burden of carrying the hot set: `hot_tokens`
(Σ token length, primary), `hot_record_count`, `materialized_bytes`. Never
wall-clock. Replayable purely from the prune/rematerialize rows.

### Cost at Matched Quality

X2's scoring axis (the scoring-axis law): the win is *lower hot-store cost with
answer quality held to a world-checked floor*, never a changed answer. Quality is
a floor and a loses-cell, never the win leg.

### Immutable-Lineage Invariant

Forgetting is **eviction to cold, never erasure**. Erasure-from-lineage is
forbidden — the security invariant the verification model rests on (cost-replay,
the air-gap refusals, R1–R5 all assume rows are unremovable); an erase verb would
let dissent, corrections, or tamper-evidence be silently removed. The prune
actuator allowlist is prune/rematerialize/hold only. *"Forget the cost, never
lose the record."*

### Three-Guardrail Stack

What binds the X-track (the X1 resolution + dissent pass): (1) **attribution law**
— a verdict must move what the invariant M-track projection cannot explain; (2)
**organ-placement law** — act where the synchronous offer gate structurally
cannot; (3) **scoring-axis law** — score on a metric the offer gate cannot move.

### `fixture_attestation` / `fixture_gate_result`

`fixture_attestation` is a *claim* row: the fixture is out-of-weights / fictional
(corpus identity pin + engine cutoffs). `fixture_gate_result` is the *computed*
outcome of the cost/state-dependence gate (manifest hash + the 15 check results,
`gate_open`). The scorer requires `gate_open: true` for every non-mock cell —
**attestation is not gate passage**. X2-LB engages on attestation + a
policy-independent grader + `gate_open`; for X2, out-of-weights means *important*
(the answer cannot be sourced from weights) — distinct from X1's offer-dependence.

### X2-win / X2-overprune / X2-quality-erosion / X2-LB / X2-U1

The prune-to-cold-store cells. **X2-win**: C matches A's quality every episode and
is cheaper, attribution clean (fork identity + lineage integrity + cost replays
from rows). **X2-overprune** (loses): B prunes a record it cannot recover and the
answer falls — the verdict names the record. **X2-quality-erosion** (loses): C
cheaper but below A's quality floor → the cost win is refused. <a id="x2-lb"></a>**X2-LB**: the
*important* admission for the cost axis — attested fictional/out-of-weights +
policy-independent grader + a computed gate pass; a synthetic fixture can pass it.
<a id="x2-u1"></a>**X2-U1**: the un-authored / **world-grounded** close-gate (M0 vocabulary) — a
synthetic/fictional fixture is `not_engaged` (important ≠ world-grounded); it
engages only on a real external corpus.

### Temperature / Landauer Oracle (X1, retired)

X1's use-driven salience (`relevance × trust × authority × temperature` at the
offer boundary) under a world-checking oracle. The *instrument* shipped; the
*organ* (synchronous eligibility-temperature) was **retired** — it was explicit
governance with a dial, not the implicit substrate (`notes/X1_FINDINGS.md`).
