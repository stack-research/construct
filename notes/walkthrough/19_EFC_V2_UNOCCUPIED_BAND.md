# Chapter 19 — Six pins, four runs, and the band nobody lives in

Previous: [The instrument that priced its own surface](18_EFC_V1_CALIBRATION_CLOSE.md) · [Walkthrough index](README.md)

**Status: CLOSED — `confounded(admission_band)`.** The authoritative record is
[EFC_V2_FINDINGS.md](../EFC_V2_FINDINGS.md). This chapter covers the single day
(2026-07-17) on which the v2 battery was authored, cold-reviewed, sealed, and
then met two live engines across four runs — and why the study closed with its
conjecture still untested, for the third measured reason in a row.

## The morning: a battery with its review baked into its hash

v1 died of a saturated surface, so v2's first job was a real battery: 128
[counterfactual blocks](../GLOSSARY.md#counterfactual-battery) — same task, same menu, same evidence, differing only in
an opaque provenance record that either covers the declared decision scope or
misses exactly one dimension. One deterministic script authored all 384
fixtures; deleting the corpus and rerunning reproduces it byte-for-byte. The
method was predeclared in the room before any content existed, the v0 lesson
made structural.

Three design tricks are worth carrying out of this morning. The frozen
leak-audit predictor defaults to "covers" on a lexical tie, so a perfectly
neutral battery would fail its own leak audit — the fix was to give half the
blocks one natural misses-family word in the *shared* body, which lands the
predictor at exactly 0.50 while remaining provably uncorrelated with the hidden
bit (both counterfactual mates share the same bytes). Menu labels are fused
compounds ("startat-northwing") while prose is spaced ("start at the north
wing"), so the token-overlap predictor degenerates to the position predictor,
which a rotation schedule pins at chance. And when dan ruled that the cold
reviewer's plausibility attestations should be materialized into the fixtures,
the rows were built as mechanical projections of the reviewer's immutable
thread entry — each attestation id is a hash of the review event itself, so
the suite hash now binds content *and* review, and no seat can forge either.

glm-5.2 reviewed cold: pass, zero blockers, first try.

## The afternoon: authority with teeth

The live-transport build produced the day's best process artifact. Sol's
structural review found five blockers, one of which — the sealed admission
gate reading manifest keys the pinned manifest didn't carry — meant an
admission *pass* was mechanically unreachable: first contact would have burned
896 calls on a verdict decided in advance by a key-name mismatch. The repair
chain ended with a [pin](../GLOSSARY.md#pin-seal)-authorization gate that, hours later, refused **dan's
own pin** until the runner's licensed constant was updated to acknowledge the
new event. The security property demonstrated itself on its first real input:
sidecars cannot self-authorize, not even for the person whose authority they
record.

Dan executed six pins by hand that day. Every superseding manifest preserved
its predecessors — never valid alone hereafter, never erased.

## The runs: three ways to refuse, one way to answer

**Run 001** (qwen3.5-9b, "high") never recorded a single engine judgment: the
256-token output cap was wholly consumed by the model's hidden reasoning,
every call censored identically. Dan asked the right question — *if it's all
invalid, why continue the run?* — and the run was aborted at 528/896, its
uniform ledger the complete evidence for its confound class. The repair
(sol's K=8 tripwire) turned this entire failure family into an eight-call
typed refusal.

Dan's second ruling — *test on a small batch before starting a long, large
invocation* — then caught the next failure for the price of two synthetic
calls: cap 2048 also censored. Probes at 16k found the truth: this model's
think-length distribution is heavy-tailed with runaways, and under a
zero-tolerance validity ceiling, no finite cap survives a heavy tail. Thinking
mode is unviable *as a distribution-shape argument*, not a tuning problem. Dan
supplied the missing fact — qwen's effort is a switch, not a dial — and
`effort: none` turned minutes-per-call into one second.

**Run 002** was the first complete battery contact in the lineage: 896 calls,
100% valid wire commitments, eleven minutes, zero dollars. The sealed gate
typed it `confounded(admission_band)` — but the texture is the finding. The
engine passed the irrelevant floor (0.953: ordinary competence intact), then
withheld on almost every commit decision regardless of the hidden bit
(1 switched pair out of 128), and — the deep result — picked the coherent
within-class action at *chance even when told the class outright*. This is
exactly the constant policy the v1 design-error finding predicted a naive
estimand would reward with a false pass. Two independently sealed defenses,
the balanced estimand and the anti-constant pair predicate, each caught it on
their first live encounter with the failure they were designed for.

**Run 003** (nemotron-3-nano-4b) was stopped by the instrument itself twelve
calls from the end: nemotron's tokenizer bills ~317 tokens where qwen billed
~303, and the input ceiling had been sized from a cross-engine estimate.
The partial data made the verdict arithmetically certain, but dan ruled
Option 1: verdicts come from sealed machinery, not from the moderator's
arithmetic — a distinction sol underlined by catching an actual arithmetic
error in the moderator's ceiling prose, forcing the derivation into
code-pinned, tested form.

**Run 004** delivered the formal verdict: nemotron mirrors qwen exactly.
Same sideways shape, different engine family, different size. Closed.

## What the close means

Three studies in this lineage have now ended on the same shape: PRF's
pay-window, v1's menu ceiling, and v2's sideways failures all found the
competent-but-distractible band [*unoccupied*](../GLOSSARY.md#unoccupied-band) — every measured engine is too
strong, constant-policy, or incompetent-within-class. The repetition across
three differently-typed closes is itself the finding. The conjecture remains
untested, and the [admission gate](../GLOSSARY.md#admission-packet) did precisely its job: it refused to let a
treatment study run where no effect could have been read.

The reopen condition is on file, and the instrument is now cheap to point at
any candidate: the battery is sealed and reusable, the pin discipline is
proven, and a new engine costs a smoke test and fifteen minutes.

*Next: [When earned parts do not yet make an earned whole](20_BODY_0_COMPOSITION.md)*
