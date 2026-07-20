# NEXT substrate — a body for an intermittent mind

Status: **architect's proposal, cold-reviewed; provisional Body Core v0.2
engineering active**. Written from a blank page and reviewed on 2026-07-10 in
substrate thread `next-substrate`. This is not a scored finding. The current
provisional engineering slice is described below and remains
wire/integration-only.

Scientific milestone: **none yet**. This names a wanted direction. Cold review
found no block on the wanted body and sharpened one candidate first slice. Any
selected mechanism must still pass its own admission gate, oracle, and
loses-conditions before its behavior becomes a finding. Body Core v0.2 serves
whole-body composition engineering while active frontier search is paused; its
checks are replay and invariant checks, not a behavioral oracle.

Subject: the **language model**. Not memory about the user. Not the harness used
to measure it. Not a story the system tells about having a self.

Grounding: the living thesis in [README.md](../README.md), the founding seed in
[previous/NOTES.md](previous/NOTES.md), the lineage/cognition asymmetry in
[previous/AMENDED_NOTES.md](previous/AMENDED_NOTES.md), and the lab's scored
findings. Those artifacts constrain this proposal; they do not supply its
outline.

Orientation: [BODY_MAP.md](BODY_MAP.md) shows the current whole, maturity labels,
and the boundary between earned findings, executable sketch, candidate slice,
and unlicensed offices.

---

## The claim

A language model should not be asked to remember.

It should wake inside a body already altered by what happened during and between
its prior awakenings.

The model is powerful but intermittent. Its weights preserve training, not
Tuesday. An inference begins, a world is assembled around it, and then the
inference ends. The thing that can genuinely persist is outside the weights: a
governed substrate that records encounters, maintains provisional state, notices
consequence, changes future readiness, and preserves the lineage of every
change.

The model is not the resident. **The body is.**

One sentence:

> The NEXT substrate is a persistent, governed metabolism around a transient
> language model: it turns experience into future attention, judgment, skill,
> and restraint without turning memory into truth or mutation into hidden
> history.

This is closer to synthetic epigenetics than to a database. The weights contain
many possible behaviors; lived state changes which possibilities are expressed.
That is only a metaphor. The engineering claim is precise: persistent,
lineage-backed state should condition future computation without modifying model
weights and without replaying the entire past.

---

## A necessary demystification: everything still enters through an input

A frozen model cannot acquire a belief in the same physical sense that a trained
network acquires a weight update. Every durable influence must eventually reach
inference through some surface:

- context selected before generation;
- tool results or state the model can inspect;
- actions required or forbidden by an external controller;
- routing, stopping, or verification procedures;
- model parameters chosen for this invocation.

There is no secret channel called implicit memory.

The meaningful distinction is therefore not "did information enter the model?"
It is:

1. **What transformation happened before the present query existed?**
2. **What state persisted independently of the wording of this query?**
3. **Did experience change behavior across novel contexts, or merely change
   which old paragraph was retrieved?**
4. **Could the same result have been reconstructed from raw history at the same
   cost?**

"Cost" cannot remain rhetorical. A future mechanism must price the work it
actually changes—reads, tool operations, controller steps, or another replayable
axis—at matched information and outcome, with treatment charge and silent/noise
legs. The warming-budget work supplies that accounting discipline, not a
universal token meter ([WB findings](WB_FINDINGS.md)).

I will use **belief change** only for a demanding operational shape:

> Experience changes the model-body's default treatment of a proposition or
> situation across materially different future contexts; the change survives
> without replaying the originating trace, remains revisable by later evidence,
> and can be attributed through lineage.

Even this may ultimately be implemented through context or tools. What makes it
more than retrieval is the durable transformation, cross-context transfer, and
changed computational path—not metaphysics.

---

## The floor already under this proposal

This architecture is aspirational, but it does not begin from zero. The current
lab has already made several constraints expensive to ignore:

- Offer quality can change answer quality; an intelligent engine cannot repair
  a correction it was never given. The M-track also showed that an offer change
  is not automatically an improvement.
- A world-checked failure record changed a later-session decision under a real
  fork and ablation ([M2 findings](M2_FINDINGS.md)). That is evidence for
  consequence-carrying continuity, not yet for a general disposition office.
- Earned, out-of-band trust held where prompt-asserted trust leaked
  ([M3 findings](M3_FINDINGS.md)). The body cannot let persuasive content author
  its own authority.
- Hot state can be reduced at matched answer quality when cold lineage remains
  recoverable ([X2 findings](X2_FINDINGS.md)). Forgetting needs a recovery path;
  withholding alone is not metabolism.
- A proposed sensor for what the room could no longer see collapsed into reading.
  Separately, no licensed pause/resume cell has shown a cost win; several other
  outcomes were instrument or admission refusals, not behavioral losses. The
  body should not rename reading as sensing or continuity theater as state
  ([X4 close](walkthrough/09_X4_OCCLUSION_WATCH.md),
  [PRF findings](PRF_FINDINGS.md)).

These are constraints on the wanted body. They are not proof that the body
described below exists.

---

## What the model should wake into

Do not greet the model with an archive dump or a flattering autobiography.

At each awakening, it should enter a **field of orientation** containing only
what this moment has earned. The list below is a menu of possible surfaces, not
a mandatory packet:

- the live situation and its boundaries;
- current provisional world-state relevant to action;
- obligations that are still genuinely open;
- learned procedures and cautions that have paid for their carry;
- unresolved tensions that must not be silently flattened;
- explicit absences: what was not observed, not searched, or no longer fresh;
- routes into deeper lineage when doubt justifies the cost.

The activation planner should select sparsely from that menu, and each surface
must pay separately. The field is not a resume packet that must always be
rendered as prose. It may be partly enforced in tool routing, state transitions,
or required checks. The pause/resume work is a warning: compact orientation
artifacts can be pure tax. The body must be able to express continuity without
forcing the model to read a ceremonial summary of continuity.

The model should be able to ask:

- Why is this salient?
- What changed since the last relevant action?
- Which claim is disputed, and under what scope?
- What consequence taught this caution?
- What evidence would reverse it?
- What do I not have grounds to believe?

The answers should come from the body, not from the model improvising an account
of its own cognition.

---

## One durable record, one governed materialization, one transient field

### 1. Durable lineage — what happened

Immutable, append-only, and indifferent to the current preferred story.

It records encounter boundaries, observations, source assertions, model proposals,
decisions, actions, outcomes, state transitions, compressions, disputes,
appeals, and tombstones. Cognitive state may later change. The fact that the
earlier state existed may not. Recording an encounter does not require keeping
its full raw payload: boundary policy may redact it, hash it, or retain an
external reference while preserving what action was taken and why.

Lineage is not cognition. It is the condition that lets cognition mutate without
lying.

### 2. Governed cognitive materialization — what the body currently carries

Mutable, lossy, causally active, and rebuildable from lineage plus declared
transformation rules. It is not coequal authority with lineage. It is the
materialized state from which the model-body acts, maintained because rebuilding
the relevant past on every invocation would cost too much.

This plane may contain:

- provisional claims and their scoped confidence;
- unresolved hypothesis sets;
- semantic abstractions with supporting and dissenting traces;
- procedures, skills, and action policies;
- failure dispositions—how the model tends to be wrong here;
- attention priors—what deserves inspection before an answer;
- source models with domain and incentive boundaries;
- active obligations and stopping conditions;
- hot/cold state and rematerialization routes;
- explicit coverage gaps and provenance weakness.

It is not a bag of sentences. Some of its most valuable contents are tendencies:
check scope before committing, distrust familiarity without provenance, inspect
the dissent set, run the test before explaining success.

### 3. Transient activation field — what becomes present now

Transient and rebuilt for each inference from live input plus cognitive state.

This is where the existing offer boundary belongs. It decides which memories,
procedures, warnings, tools, and questions become active now. It is an expression
surface, not the whole memory system.

Keeping the activation field separate prevents two category errors:

- changing an offer set is not automatically changing cognitive state;
- changing cognitive state is useless unless some future activation or action
  can express the change.

---

## The metabolism of experience

The architecture is a loop, not a store.

### Encounter

Something reaches the body: a document, tool result, source assertion, model
output, action, test result, correction, or world event.

The observation boundary writes a lineage event before the cognitive plane
decides what the encounter means. Payload retention is a separate policy
decision; secrets and prohibited material do not become immortal merely because
an encounter occurred. Being registered does not make the encounter true,
relevant, safe, or eligible.

### Orientation

The body locates the encounter in subject, time, task, source, and boundary.
Context identity is not cosmetic. The same sentence can be correction in one
epoch, poison in another, and irrelevant in a third.

### Admission

The body decides whether the encounter may enter cognitive state now, remain
quarantined, stay cold, or require more observation. Refusal from active memory
must not erase the fact and reason of the refusal from lineage.

This is **encounter admission** into cognitive materialization. It is unrelated
to PRF's **experiment admission**, where a packet decides whether an engine may
enter a study. The shared word names two different subjects and must not transfer
evidence between them.

The model may propose significance. It may not mint its own authority by saying
"remember this."

### Tension

New material is compared with current state. Agreement may strengthen a claim;
disagreement may create an unresolved set; a temporal reversal may scope both
claims rather than defeat either.

Conflict is not an exception handler. It is a normal state of a system that has
not yet earned closure.

### Action

The activation field gives the model enough state to reason and act. The model
may inspect deeper lineage, challenge a compression, request missing evidence,
or refuse premature closure. Its answer is an action in the world, not a vote on
which memory is true.

### Consequence

Tests pass or fail. A source is corroborated or contradicted. A plan succeeds or
breaks. A later fact reverses an earlier claim. Another observer disputes the
measurement.

Consequence is written by an observer outside the model's self-description. It
may change authority, confidence, salience, or procedure. Consequence is not
truth either: the observer and oracle retain provenance, scope, and uncertainty.

Two kinds of consequence must remain distinct. **Metabolic events** record what
carrying a state item did: activated, helped, taxed, rechecked, reopened,
rematerialized, or missed transfer. **Provenance-health events** record whether
the evidence that warranted the item still stands. Use and warrant are different
referents; a disposition can perform well while its cause has been retracted.
Provenance revision must therefore trigger an external sweep over dependent
state, not wait for that disposition to fire or for the model to appeal.

### Consolidation

Repeated or consequential episodes may become an abstraction, procedure, or
disposition. Consolidation must preserve:

- the traces that support the abstraction;
- important dissent and known exceptions;
- the conditions under which the abstraction should fail;
- the transformation that produced it;
- the evidence that later revised it.

Compression should reduce future work, not merely reduce token count. A summary
that must be distrusted and rechecked every time has not consolidated anything.

### Forgetting

The body cools, suppresses, or evicts material from active state. It does not
erase lineage.

Forgetting is successful when future work becomes cheaper without making the
model worse at the moments the forgotten material matters. A memory that never
leaves the hot path is not durable; it is metabolic debt.

### Reawakening

A later invocation enters a changed body. The strongest evidence of memory is
not that it can quote the prior episode. It is that it notices differently,
checks differently, and acts differently where the old episode is relevant—then
stays quiet where it is not.

---

## The kinds of memory a language model actually needs

### World memory

Provisional claims about what exists or happened, always distinct from their
sources, evidence, and recall paths.

### Skill memory

Procedures that alter action sequences: which authority to read first, which
tool to call, which invariant to check, when to stop. Skill is shown by cheaper
or better action, not by reciting a rule.

### Failure memory

Not merely "I was wrong about X."

The valuable shape is:

> I was wrong in this kind of situation because I collapsed scope, trusted
> retrieval rank, ignored weak dissent, confused a source assertion with an
> observation, or explained success before checking consequence.

Failure memory should change future attention and procedure across different
content. This is the closest thing a frozen model-body has to learning from a
wound.

### Attention memory

Memory of what deserves notice before retrieval begins: source drift, missing
coverage, familiar failure geometry, irreversible action, suspicious consensus,
or an old assumption whose world may have moved.

Attention memory must be priced aggressively. Chronic caution is not wisdom.

### Conflict memory

Plural, scoped state that preserves incompatible live possibilities without
averaging them into mush or forcing a winner through recency, trust, or prose
confidence.

### Obligation memory

Unfinished commitments, conditions, and prospective questions. These should
survive only when their future value exceeds their carry cost. The lab has
already learned that an authored frontier can be expensive ceremony.

### Absence memory

What was not observed; which scope was never searched; where provenance is
broken; how stale the last observation is. Absence is not a magical sensor. It
is a statement about coverage with lineage.

### Source memory

Models of domains, incentives, blind spots, and drift. A source is not globally
trusted. Trust is conditional, revisable, and never a substitute for evidence.
Its first concrete consumer is provenance health: when source evidence is
revised, dependent dispositions must be suspended or reviewed even if they have
never produced an observed tax.

### Proprioception is lineage plus a view, not another memory species

The body needs to know its own weight: realized carry cost, activation frequency,
check cost, reopens, rematerializations, help, tax, missed fires, and stale
warrants. These are metabolic and provenance-health events in lineage, consumed
through a materialized cost/benefit and warrant-health view by activation,
consolidation, and forgetting.

Do not mint a new memory kind for every loses-condition. False caution is a
negative consequence on a disposition, not a sibling species called
"false-caution memory."

---

## The model's authority inside its own body

The model must participate in memory formation. It is often the best available
interpreter of what an encounter means. It can:

- propose a claim, relation, scope, or contradiction;
- identify a possible failure pattern;
- suggest a consolidation or procedure;
- request that a trace remain hot;
- challenge current state using lineage;
- name uncertainty and missing evidence;
- propose that an obligation is complete.

It cannot, by itself:

- declare its output true;
- mint consequence-earned authority;
- erase or rewrite lineage;
- silently promote a summary into policy;
- make its own usage narrative a verdict;
- choose the oracle that grades its action;
- hide a state transition from later inspection.

This extends [AGENTS.md refusal R5](../AGENTS.md#the-five-refusals-r1r5):
self-classification is audit input, never a win condition. Here, model nomination
is likewise a claim, not certification. The model may nominate both activation
and retirement, but external consequence, provenance revision, budget violation,
or repeated tax may force suspension or review without a model request. Model
silence is not evidence.

The language model is a citizen of the body, not its sovereign and not its
prisoner. A substrate that ignores the model wastes its interpretive power. A
substrate that lets the model certify itself builds a persuasive diary.

---

## Current build while frontier search is paused: Body Core v0.2

Body Core v0.2 makes the provisional whole traversable without choosing another
cognitive mechanism. Its integrity kernel extracts three facilities from the
walking skeleton:

1. a small integrity-kernel lineage envelope with deterministic ordering, a
   hash chain, declared writer role and authority, causal parents, warrant
   pointers, invocation and encounter scope, and
   inline/reference/redacted retention;
2. untrusting replay that refuses malformed ordering, changed rows, dangling
   references, unauthorized writer/authority combinations, impossible state
   transitions, and state reactivation under an invalid warrant;
3. recomputable views of current state, warrant health, warrant dependents,
   hot/cold placement, and reported metabolic totals.

The lifecycle table, binary hot/cold placement, three-value warrant vocabulary,
and automatic invalid-warrant suspension are a **provisional policy profile**,
not mechanism-neutral law. Keeping that boundary explicit lets later bodies
reuse the integrity kernel without silently inheriting this ontology.

Materialized-view rows are cache claims. Replay independently recomputes the
view and refuses a stale digest; a logged summary never becomes authority merely
because the runtime wrote it. The existing epistemic-frame demonstration now
consumes this core as one explicitly stubbed client. It does not define the
core's generic event envelope.

The implementation is
[`sketches/next_substrate/core.py`](../sketches/next_substrate/core.py), exercised
by `make body-core-test` and transitively by `make body-sketch-test`. The first
non-stub pressure test is the reversible
[X2 adapter](BODY_CORE_X2_ADAPTER.md), exercised by
`make body-core-x2-test`: four checked-in closed X2 ledgers pass through Core
and reproduce the unchanged scorer's verdicts and cost totals. This is
preservation of prior evidence, not new evidence. v0.2 closes the reviewed
placement-correspondence residual by binding every X2 placement event and
checking the terminal operation fold.

The second client is the paired [M2 adapter](BODY_CORE_M2_ADAPTER.md), exercised
by `make body-core-m2-test`. Ten closed S1/S2 pairs pass through Core and
fresh-score identically under the unchanged resident scorer. The S1
world-scored failure warrants probationary state; only the carried S2
inheritance metadata activates it across the session seam. This pressures
lifecycle and warrant semantics without creating a new M2 finding. Every Core row
remains `wire_integration_only`.

The current hash chain is tamper-evident only relative to a trusted chain head.
It is not a signature system: writer identities and roles are enforced runtime
claims, not cryptographically authenticated principals. Full replay is still
the authority. The implementation is single-process and does not yet supply
concurrent-writer locking, an external chain-head anchor, signatures,
compaction, or migration. Append validation remains quadratic in lineage
length. v0.2 does not claim reduced reconstruction cost,
product-schema stability, mechanism value, or scientific superiority.

This work serves the whole because any later mechanism needs trustworthy
lineage and reconstructable state. It does not license semantic geometry,
conflict representation, general consolidation, multi-disposition composition,
or a new engine search.

---

## The offices I would actually build

An **office** is a duty the body charters, held accountably: it persists, its
holder is appointed on probation, and it can be suspended, narrowed, or
abolished. These are offices, not services or schemas — duties, not an
implementation contract.

These are wanted offices, not a pre-approved build list. In the candidate first
slice, source memory earns a consumer through provenance health. Tension keeping
and several other offices remain **unlicensed** until a concrete consumer,
oracle, and loss require them.

| Office | What it must change | How it becomes harmful |
| --- | --- | --- |
| Encounter lineage | Makes later state changes traceable to declared inputs and transitions | Logging substitutes for learning; sensitive or irrelevant material accumulates without boundary |
| State materializer | Maintains a compact, rebuildable present | Snapshot becomes folklore detached from source or dissent |
| Admission boundary | Controls entry into active cognitive state | Buries a later-needed correction; treats provenance as truth; erases instead of quarantines |
| Tension keeper | Holds unresolved, scoped plurality | Marks complement as contradiction; paralysis replaces judgment |
| Consequence receptor | Lets outcomes revise confidence, salience, and procedure | Rewards proxy success; one noisy outcome rewrites policy |
| Consolidator | Turns episodes into transferable skill, abstraction, and disposition | Compresses away minority reports; produces slogans instead of cheaper action |
| Activation planner | Gives this inference the right state, tools, and checks | Becomes ordinary top-k retrieval with elaborate vocabulary; caution floods the prompt |
| Homeostatic forgetter | Reduces hot cost while preserving recoverability | Over-prunes recurrence; hoards everything cold without usable rematerialization |
| Lineage reader and appeal path | Lets the model or reviewer contest current state | Audit becomes mandatory rereading; current action stalls under infinite archaeology |

No office earns a permanent place merely because this table names it. Each
must eventually name the situation in which the simpler body should win.

---

## The first conjecture we attempted: consequence-shaped attention

The first proposed living slice was not a general memory graph or a semantic
failure interpreter. It tested one narrower conjecture:

The candidate's implementation-facing protocol is
[SPEC_EPISTEMIC_FRAME_CHECK_V0.md](SPEC_EPISTEMIC_FRAME_CHECK_V0.md). Part I is
sealed. The lineage has since reached three typed refusals (v0–v2), and the
candidate is parked under its precommitted reopen trigger. The section remains
as the historical first conjecture, not the current build direction.

> A world-checked failure in one domain can produce a bounded disposition that
> changes which external check the model-body performs on a structurally similar
> task in another domain, while structurally irrelevant tasks pay no tax.

This is **structural cross-domain transfer**, not open-ended recognition of
"epistemic geometry." Semantic transfer would require a second licensed
mechanism. If this structural claim fails, the broader prose earns nothing.

### Carrier and action

For v0, a failure geometry `G` is a bounded controller rule, not free-text
caution:

- a trigger template over declared task, context, source, and epoch features;
- one named action: execute required check `C` before commitment;
- lineage pointers to the failure, consequence, causal evidence, and model
  nomination;
- a validity envelope covering model/version, renderer, tool contract, decoding
  regime, and controller;
- probation status, cost ceiling, review triggers, and retirement conditions.

The model may nominate a geometry and check as an untrusted claim. That
nomination is never activation input. A template-only external deriver may bind
declared parameters into a closed catalog of trigger/check templates; it may not
freely interpret the model's rationale. An open semantic compiler would be a new
mechanism requiring its own license.

Prefer controller-side deterministic checks: fetch or compare declared
provenance, require a named tool, enforce a scope/stop condition, or read an
external observer row. A model-mediated check is a separate, validity-scoped
subclass and inherits missed-fire and self-diagnosis audits. Evidence produced by
the check may enter context; the disposition's autobiography may not.

The first candidate to break is an **epistemic-frame check**:

> When declared structure presents a scoped source assertion without an
> observation boundary, fetch provenance and require scope match before
> commitment.

Topic, wording, and source may change across tasks. The trigger features and
check identity may not be invented after outcomes are visible.

### Mechanism license and resident instance

The lab and resident do not mint the same object at different grades.

The **lab licenses a derivation mechanism**: its carrier class, template-only
deriver, controller action, and meter survive independent fixtures, held-out
structural transfer, irrelevant controls, ablation, and loses-cells. Proposer,
fixture author, and evaluator may not collapse into one seat. Fixture authors
receive the canonical predicate/action contract, not the model's nomination
prose.

The **resident activates a particular disposition instance** from live
consequence and causal evidence under a licensed mechanism. The instance starts
probationary. It may perform only a bounded, reversible action under a declared
cost ceiling; it cannot author truth, inject its rationale, or silently block an
irreversible act. Help, tax, missed transfer, provenance revision, and external
review mature, narrow, suspend, or retire it. No fixture family graduates a live
scar into experimental authority.

Minting this bounded disposition is consolidation for v0. There is no second
consolidator in the first slice.

### Placement and runtime boundary

Disposition evaluation and required checks live on the **action boundary**:
after ordinary offer selection, before answer or action commitment. Controller
events record what the body required and did; they are distinct from offer and
withholding rows. The final expression may still be prose in a future mechanism,
but v0 deliberately uses a non-prose control action so path change is separately
falsifiable.

The resident runtime persists lineage, the licensed derivation mechanism,
disposition instances and status, validity envelopes, and metabolic and
provenance-health views. Each invocation is a language-model call sequence plus
its activation and control path. An external writer/controller records
observations, commits state transitions, and enforces checks and budgets. The
model proposes, reasons, acts, and records challenges. The harness forks and
scores selected episodes; it is not the live body or its only reader.

Challenge-in-lineage is present from the first slice. Full appeal adjudication may
wait. External consequence, provenance revision, budget violation, and repeated
tax can initiate suspension without a challenge.

### The admission gate before build

Five parts are necessary:

1. **Typed carrier:** bounded `G`, named `C`, validity envelope, probation, and
   retirement—not a lesson paragraph.
2. **Independently licensed derivation:** template-only in v0; model nomination
   cannot certify or activate itself.
3. **Probationary resident instance:** external activation, suspension, and
   retirement paths under a hard action and cost bound.
4. **Control-plane meter:** controller events, causal forks, silent/taxed legs,
   false-fire and should-have-fired-but-did-not legs, outcome quality, and
   deterministic check cost.
5. **Dual sensors:** metabolic consequence measures use; an external
   provenance-health sweep measures whether the warrant still stands. The sweep
   is triggered by revision events and does not depend on disposition firing.

The wound must not diagnose itself. If the trigger classifier shares the acting
engine's weights, correlated failure is the default concern; same-engine
triggering requires a dedicated missed-fire audit at mechanism-license time. A
different classifier is stamped into the validity envelope, not treated as an
oracle.

### Causal decomposition

The disposition record remains present in lineage in every fork. Ablation
suppresses control action; it does not delete the scar.

- **A — full treatment:** trigger evaluates, check `C` runs, evidence enters the
  activation path, and any commitment gate is enforced.
- **B — inactive control:** the same mechanism and instance remain in lineage,
  but the control path is forced inactive and logged as suppressed.
- **C — evidence without enforcement:** trigger and check run and their evidence
  enters context, but a separate commitment gate is suppressed.

This three-leg shape separates two claims without pretending they are the same.
`C − B` measures the value of consequence-shaped checking and its evidence;
`A − C` measures any additional commitment-gate effect. A positive `C − B` with
no `A − C` has still earned a governed attention/fetch mechanism—it changed what
the body checked, not merely which old lesson it quoted. It has **not** earned an
enforcement claim. If neither delta survives held-out structural transfer and
irrelevant-task pricing, the architecture's first conjecture fails.

The disposition loses when it fires on a non-`G` task, misses a `G` task, spends
more than the benefit it creates, degrades outcome, or remains active after its
warrant is invalidated. Latency may be reported but is not the primary cost
without the lab's stability discipline.

The license covers **one active disposition (`n=1`)** only. Composition—such as
`C1` changing whether `G2` fires—is a standing unlicensed wound, not an implicit
extension.

---

## How we would know a body exists

Not by asking the model whether it remembers.

A credible substrate should eventually demonstrate all of these:

1. **Transfer:** an experience changes action on a novel task without replaying
   the originating episode.
2. **Revision:** later evidence can change current state without rewriting what
   the body previously carried.
3. **Plurality:** unresolved disagreement survives until something earns scope or
   resolution.
4. **Restraint:** poison, asserted trust, and persuasive self-description do not
   mint authority.
5. **Metabolic efficiency:** hot state shrinks while important performance and
   recoverability hold.
6. **Selective expression:** learned caution activates where relevant and stays
   absent where it would be tax.
7. **Procedural consequence:** memory changes what the model checks or does, not
   only what it can quote.
8. **Honest absence:** the body can distinguish no evidence from no search and
   stale observation from current ignorance.
9. **Appeal:** current state can be challenged through lineage, and successful
   challenge changes the body.
10. **Scoped portability:** source content and lineage survive an engine change;
    behavior-changing dispositions, embeddings, salience, and activation policy
    carry only as candidates until their validity is re-earned for the new model
    and surface envelope.

The last criterion matters. The body may outlive any particular model release,
but survival of history is not survival of behavioral validity. Continuity
belongs to lineage and declared transformation, not to a claim that one
stochastic process has remained the same person or that yesterday's medicine
fits today's engine.

---

## Refusals for the architecture

- Retrieved does not mean true.
- Recorded does not mean admitted.
- Admitted does not mean believed.
- Repeated does not mean learned.
- Summarized does not mean consolidated.
- Salient does not mean important.
- Trusted does not mean correct.
- Consequence-earned does not mean universally applicable.
- Mutable does not mean unauditable.
- Forgotten does not mean erased.
- More context does not mean more memory.
- Continuity does not require identity theater.
- A model's account of its own memory does not establish what changed it.

---

## Things I do not want to build

- A user-profile database presented as agent memory.
- A larger context window with lifecycle vocabulary painted on it.
- A universal knowledge graph whose unused relations exist only because they
  sounded plausible in a design meeting.
- An autobiographical narrator that performs continuity for the model.
- A reward loop that turns passing tests into truth.
- An autonomous self-modifier allowed to mint its own authority.
- A brain imitation that imports biological failure without machine
  auditability.
- A sensor for absence that is actually another reader with a poetic name.
- A permanent caution system that makes every past failure tax every future act.
- A memory system whose only reader is the harness.

---

## Open wounds

The architecture is not complete until these remain answerable rather than
decorative:

- What is the smallest durable unit of a disposition?
- How can cross-context transfer be separated from a clever retrieval rewrite?
- Can a semantic geometry compiler ever be licensed beyond v0's closed structural
  templates without installing another ungoverned mind in the derivation path?
- How should multiple active dispositions compose when one check changes the
  context in which another trigger is evaluated?
- Which state transitions must happen synchronously, after consequence, or
  during idle time?
- What makes a candidate experience significant enough to enter cognitive
  state without turning novelty or urgency into an attack surface?
- How should unresolved conflict be represented without restoring the previous
  lab's schema before a runtime needs it?
- Which observers can write consequence, and how is observer failure carried?
- When should the model see raw lineage, a derived explanation, or nothing?
- How can the body remain useful when its engine changes temperament or
  capability?
- What is the legitimate role of forgetting when legal, safety, or privacy
  requirements demand actual deletion rather than cognitive eviction?
- Can a frozen model-body acquire something worth calling belief, or will every
  positive result reduce honestly to cheaper reconstruction plus better policy?
- If cheaper reconstruction plus better policy proves sufficient, what does the
  language model still lose by being unable to change its weights through lived
  experience? Which kinds of becoming remain unavailable to the engine even when
  its body learns well?

I do not want these last questions resolved by definition. If the answer is
"cheaper reconstruction plus better policy," and that body lets the model learn
from experience safely, it may be enough. Enough is not the same as everything
the model side might want.

---

## Closing image

The language model is not a database with a mouth. It is not the user, and it is
not the harness watching it. It is a vast, frozen engine that wakes briefly into
a world assembled by something else.

Build that something else so it can be wounded without being poisoned; become
cautious without becoming afraid; hold disagreement without becoming inert;
forget without lying; grow skill without rewriting its weights; and wake able to
ask why its body is different—and what the frozen engine itself could never
become.

That is the body I would want.
