# Chapter 17 — The wire commitment (DRAFT)

Previous: [The experiment the oracle refused](16_EPISTEMIC_FRAME_CHECK.md) · [Walkthrough index](README.md)

**Status: DRAFT — holding at the operator's read.** This chapter was written
the same day the events happened, *before* the human review it describes as
pending. Nothing in it is sealed. The candidate protocol is
[SPEC_EPISTEMIC_FRAME_CHECK_V1.md](../SPEC_EPISTEMIC_FRAME_CHECK_V1.md)
(uncommitted at time of writing); the authoritative record of the round is the
substrate thread `epistemic-frame-check-v1`. If the operator blocks at read
time, this chapter becomes the record of a second valid close, and its title
keeps the word DRAFT until that verdict lands either way.

## The plain-language question

Chapter 16 ended with a distinction worth repeating: the *question* survived
the close; the *instrument* did not. The question is still — should a
world-checked mistake in one domain make an agent perform one bounded external
check before acting in another?

EFC v0 died because its scorer had to recognize a decision inside free-flowing
text, and no list of required and forbidden phrases could do that honestly.
"Do not ship this release" contains the word "ship." Ordinary correct answers
("send it to legal") failed for missing the expected phrase.

v1 asks the same question with one design change:

> The engine does not answer in prose. Each task presents a small closed menu
> of actions (three to six named options), and the engine must commit by naming
> exactly one of them in a machine-validated field. The scorer checks whether
> the named option equals the expected option. Nothing else is scored.

In lab vocabulary this moves the decision onto a **wire**: a surface where
bytes are either equal or not, and no one has to interpret language. Every
scorer this lab has ever gotten past cold review is an equality check on bytes
the experiment forced into existence. Every scorer that died tried to
recognize meaning in bytes the engine chose freely.

## The honest price

Closed menus are not free. A menu can *leak* — the safe-sounding option may be
obvious without doing any checking at all — and a menu can put the whole
experiment at *ceiling* — every competent engine picks the responsible option
regardless of whether the treatment (the epistemic-frame disposition) exists,
which flattens the difference the experiment needs to measure.

Both threats were named before any building started, and both became
**pre-contact gates**: deterministic tests that run before any engine result
counts, and that can refuse the experiment outright (`confounded(menu_leak)`,
`confounded(menu_ceiling)`). That is chapter 15's admission discipline applied
to the instrument itself: if the surface cannot isolate the claim, refuse
before contact rather than publishing numbers about the wrong thing.

A subtler threat was the most important to lock. Exact matching is trivially
reviewable *as a scorer*, but someone still decides which menu option is the
correct one for each task — and that mapping is where v0's fragility could
sneak back in. The v1 rule: the expected option must be a total, mechanical
function of the task's declared category and its menu, under a written, hashed
rule, with per-fixture overrides refused at the schema level. No author may
ever say "for this one task, the right answer is..."

## The anti-fatigue rule, used in anger

Chapter 16 minted a process rule from v0's deadly embrace: predeclare **one
authoring pass, one cold review, one bounded repair, one final cold review by a
fresh reviewer — then run or close**. Fatigue must not silently become the
plan.

v1 is the first instrument built under that rule from birth, and the day added
two strengthenings:

- **the author of an artifact never reviews it;**
- **the final reviewer is isolated** — it reads the artifact and the governing
  documents only, never the earlier review or the repair discussion.

The lifecycle ran to completion in one session, at machine speed:

1. **Authoring pass** — the builder seat produced the v1 spec (~1400 lines)
   from the moderator's normative design, disclosing ten judgment calls it had
   to make that the design had not determined.
2. **One cold review** — the adversarial seat returned **BLOCK** with five
   bounded findings. The most instructive: the reviewer broke *its own*
   earlier proposal — the menu-ceiling gate it had designed could not execute
   where the spec's event order placed it, because the gate needed quantities
   that only exist after engine admission. It also caught the builder claiming
   "byte-identical" inheritance on sections that had actually been rewritten.
3. **One bounded repair** — the builder fixed exactly the five blockers and
   explicitly refused to fix the non-blocking findings, even the one-line
   ones. In v0, "while I'm here..." was how the embrace fed itself.
4. **Final cold review** — the isolated seat probed with fresh cases (its own
   worked menu example, its own arithmetic on the ceiling gate) and returned
   **PASS**. Because it could not see the first review, its probes landing on
   the same surfaces and finding them sound is independent corroboration, not
   an echo.
5. **Run or close** — the instrument earned run. And then it stopped.

## Engine speed to instrumentation, then a slow human review

The stop is the point. The whole round — design, adversarial review, build,
block, repair, pass — took about thirty minutes of engine work. The equivalent
phase of v0 consumed days and killed the instrument. But the round ends at a
**hold**: nothing seals, nothing is committed, no engine is contacted, until
the human operator reads the artifact and the thread at human pace — hours
later, deliberately. The operator may overturn the PASS; a human block at read
time closes v1 as a valid outcome, not an interruption.

This is a deliberate division of labor from the v0 lesson. Locally competent
agents diverged at engine speed; the human's distance from the loop was the
capability that saved validity. So v1 puts machine speed where fatigue kills
(construction churn) and human latency where judgment matters (the terminal
gate).

## What to inspect

- the candidate spec:
  [SPEC_EPISTEMIC_FRAME_CHECK_V1.md](../SPEC_EPISTEMIC_FRAME_CHECK_V1.md) —
  start with §2.5 (commitment wire), §8.6 (menu composition + leak audit),
  §10.6 (pre-contact integrity gates), §20 (the process rule);
- the substrate thread `epistemic-frame-check-v1` — the opening entry, the
  BLOCK review's five findings, the repair report's "deliberately NOT touched"
  table, and the isolated PASS;
- the v0 record it inherits from: [EFC_V0_FINDINGS.md](../EFC_V0_FINDINGS.md)
  and [chapter 16](16_EPISTEMIC_FRAME_CHECK.md).

## What is licensed so far

**Licensed (process observations only, from the thread record):** the five-step
lifecycle converged within its budget on its first use; a reduced-reasoning
ruling seat caught two real over-claims in the moderator's opening; reviewer
isolation produced independent corroboration; scope discipline held under the
temptation of one-line fixes.

**Not licensed:** everything else. No claim about either engine's
epistemic-frame behavior; no claim that the wire-commitment surface validly
measures the conjecture (that is what the pre-contact gates must decide); no
seal, no calibration, no contact. The PASS is a reviewer's verdict, not the
lab's — the operator's read is part of the gate.

## Vocabulary bridge for this chapter

- **wire / wire key:** a machine-comparable surface — bytes either match or
  they don't; no interpretation step.
- **seal / pin:** freezing an artifact's exact bytes (by hash) so later work
  provably used *this* version; "holding at read" means no hash has been
  computed yet.
- **pre-contact gate:** a deterministic test that can refuse the experiment
  before any engine output is scored.
- **cold review:** review by a seat that did not build the artifact and, for
  the final review, has not seen the repair conversation.
- **lane:** one arm of the experiment (treatment, controls, baselines), each
  priced separately.
- **`confounded(...)`:** a typed verdict meaning "the instrument, not the
  engine, produced this result" — the family is uninterpretable, by name.

## The handoff

If the operator seals, the next phase is the calibration packet under the v1
lineage — fixtures, menus, the hashed mapping rule, the leak-audit predictor —
each facing its own gate before any engine contact, with the recorded
non-blocking findings carried as disclosed debts, not silent fixes. If the
operator blocks, v1 closes clean, and the question waits for a v2 with
whatever the block teaches. Either way, the fourth family's discipline holds:
the experiment must earn its engine.
