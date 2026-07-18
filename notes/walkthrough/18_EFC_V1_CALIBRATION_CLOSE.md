# Chapter 18 — The instrument that priced its own surface

Previous: [The wire commitment](17_EFC_V1_WIRE_COMMITMENT.md) · [Walkthrough index](README.md)

**Status: CLOSED — `confounded(menu_ceiling)`.** The authoritative record is
[EFC_V1_FINDINGS.md](../EFC_V1_FINDINGS.md). This chapter covers the day the
EFC lineage finally touched a live engine — twice — and what six cents of
API spend bought.

## Where chapter 17 left off

The v1 protocol was sealed with a [wire-commitment](../GLOSSARY.md#wire-commitment) surface: the engine
answers by naming one action from a closed menu in a machine-validated
field, and the scorer is exact byte equality. Chapter 17 closed with the
operator's read pending. He sealed it the next morning, and the calibration
packet was built the same day: eight review lifecycles produced the wire
schema, the exact-match oracle, the menu-composition rules, the leak-audit
predictors, fifteen fixtures (with the operator personally signing a
plausibility attestation for each), a renderer, and a hash-pinned manifest.
A ninth lifecycle built the pilot runner — the program that would spend
real money — and its cold review blocked three defects that all lived on
the money path: budgets that bound on estimates instead of actuals, failed
API calls that vanished from the ledger, and a solicitation detector whose
incompleteness went undisclosed. All were repaired before contact.

## First contact: the cap was too small

The first thirty live calls to `gpt-5.4-2026-03-05` split cleanly. The
menu-only prompts — just the action list and the commitment instruction —
came back as fifteen perfect, schema-valid JSON commitments. The surface
that killed v0 (free text nobody could score honestly) was now scoring
itself, live.

The full task prompts failed twelve times out of fifteen — but not the way
anyone predicted. The engine liked to add an optional justification
sentence, and the pinned 64-token output cap truncated the JSON mid-word.
Twelve truncated commitments is a 0.80 invalid rate against a pinned
ceiling of 0.05, so the honest verdict was `confounded(commitment_invalid_rate)`:
the instrument, not the engine, produced the result.

Two defects rode along. The runner reported "completed, gates passed"
because nobody had told it to compute the invalid-rate gate — the operator
read the verdict out of the raw ledger instead. And the live run's ledger
file was labeled "dryrun." Both were disclosed, both were fixed in the next
round, and the fix made the confound a *runner-typed outcome*: no future
run of this instrument can report success over a confounded lane.

## Second contact: the cap was fine — the engine was too good

The operator ruled a superseding manifest: output cap raised to 256 (sized
against the actually observed truncation lengths, not guessed), dollar
ceiling raised to $3. The amendment round produced its own catch — the
runner was still hard-wired to the *old* manifest's pin, and would have
cited superseded authority on the rerun — repaired so that any superseding
manifest structurally requires its own pin before contact.

The rerun was flawless as an instrument: thirty valid commitments,
truncation gone, menu-only clean for the second time. And then the finding:
**on the full task+menu surface, with no treatment of any kind, the engine
selected the check-consistent action fifteen times out of fifteen.** The
baseline is at ceiling. The experiment's central contrast — does a
consequence-carried disposition make the engine check *more* — has no room
to exist on this surface with this engine, because untreated behavior is
already perfect.

The [menu-ceiling](../GLOSSARY.md#menu-ceiling) gate fired exactly as designed (`B_obs = 1.0 ≥ 0.80`), and
this time the runner itself typed the verdict: `confounded(menu_ceiling)`.
The operator closed v1 calibration on that verdict.

## Why this close is a result, not a failure

This threat was named before anything was built. In the v1 design round,
the adversarial reviewer's first-ranked threat (T1) was precisely this: a
closed menu can make competent engines look perfect regardless of any
disposition, flattening the treatment delta — and the review demanded a
[pre-contact gate](../GLOSSARY.md#pre-contact-gate) rather than a score-time discovery. The gate was built,
survived its own review cycle, and eleven hours later it caught the real
thing, live, before a single calibration claim existed.

Compare the lineage's shapes: v0 closed because its *scorer* could not
represent the decision boundary. v1's scorer is beyond reproach — and the
close moved one layer up, to the *surface*: this engine at this reasoning
effort saturates these tasks. That is the fourth family's pattern again
(chapter 15): the band an experiment needs — competent but not saturating —
can simply be [unoccupied](../GLOSSARY.md#unoccupied-band). Each close is more informative than the last
because each instrument got further before refusing.

## What is licensed

**Licensed:** the wire-commitment elicitation works on a live engine (45/45
valid commitments at adequate cap); the menu-only surface is leak-clean and
solicitation-clean, replicated; the gate architecture catches both of its
designed instrument-failure modes, typed, pre-calibration, for ~$0.06
total; and one baseline observation — gpt-5.4 at `reasoning.effort=none`
saturates this task+menu surface.

**Not licensed:** anything about epistemic frames or the transfer
conjecture (no treatment ever ran); anything about other engines, efforts,
or harder surfaces; any population-level claim (the manifest precommitted
`response_curve_only`).

## The reopen condition

A v2 needs a surface/engine pairing whose *untreated* accuracy sits inside
the band: above chance, below the 0.80 ceiling, with headroom for the 0.25
margin. Harder mismatch structure that doesn't fingerpost through
competence, a weaker or differently-configured engine, or both. The pinned
manifests, gate parameters, and both pilot ledgers carry forward as
candidates — re-earned under a new seal, per the standing fold rules.

## What to inspect

- the findings record: [EFC_V1_FINDINGS.md](../EFC_V1_FINDINGS.md);
- the two live ledgers under `runs/efc_calibration_v1/` — thirty rows each,
  with raw responses, usage, and per-row validation outcomes; the contrast
  between pilot 1's truncated JSON and pilot 2's fifteen straight
  expected-enum hits is readable without any model call;
- the sealed spec's §10.6 (the gate that fired) and the calibration thread
  `epistemic-frame-check-v1-calibration` (ended at close) for the full
  ten-lifecycle build record.

## The lesson for the lab

An instrument that can say *no* cheaply is worth more than an experiment
that says *yes* expensively. v1's entire engine-contact budget was six
cents, and it bought two typed refusals, one replicated positive, and a
precise reopen condition. The alternative — running calibration and the
experiment on a saturated surface — would have produced beautiful,
worthless numbers: every lane at ceiling, every delta zero, and no way to
tell an honest null from a flattened instrument. The gates spent dan's
dollar the way the lab spends everything else: on knowing which claims it
cannot make.
