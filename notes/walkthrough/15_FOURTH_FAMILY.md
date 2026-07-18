# Chapter 15 — The fourth family: bounded from both sides

Previous: [Greenreach: the close](14_GREENREACH_CLOSE.md) · [Walkthrough index](README.md)

Chapter 14 ended with an engine problem: gpt-oss-20b would not assemble the
three-leg conjunction un-forced, so the pay-window's detectable regime was
never entered. Any fourth family had to start from that. This chapter is the
fourth family — designed, reviewed, pinned, run, and paused, all on one day
(2026-07-09). It is also the chapter where the pause/resume question stops
being "does the artifact ever pay?" and becomes "the window lives in a band
no tested engine occupies."

**Status: PAUSED, not closed** — by the moderator's ruling, with the reopen
trigger precommitted. The honest record is
[PRF_FINDINGS.md](../PRF_FINDINGS.md); when this chapter and that document
disagree, the findings document wins, and the sealed
[SPEC_PAUSE_RESUME.md](../SPEC_PAUSE_RESUME.md) outranks both.

## The question, and the compression this arc refused

Three families had ended in typed negatives, and the tempting summary was
"three consecutive negatives — the artifact never pays." The fourth-family
round opened by refusing that sentence. A cold read on day one
(cursor/grok-4.5, moderator-adopted) pointed out that the record does not
hold three negatives of the same kind. It holds **four unlike outcomes, one
per geometry**:

| Family | Outcome | What it actually is |
|---|---|---|
| meridian (v0.2) | `PRF2-cost-loss` | The only behavioral cell: resumable genuinely lost |
| triangulation-docket (v0.3) | `confounded` (CI budget) | An instrument refusal — the middle of the band is hard to *measure* |
| greenreach (v0.4) | `confounded` (A2) | An admission refusal — the engine never entered the detectable regime |
| **Phase-0 packet (this chapter)** | `admission_refused` | An admission refusal from the *other side* — see below |

Stacking unlike refusals into one thesis is a rhetorical compression, and
the findings document exists partly to kill it. That refusal — value found
in re-opening a "settled" summary — is the discourse norm from the
[heir-audit chapter](11_HEIR_AUDIT_CLOSE_GATE.md) doing its job.

## Vocabulary bridge

- **[Phase-0 admission packet](../GLOSSARY.md#admission-packet).** A machine-scored gate run *before* any
  scored experiment: does this engine even exhibit the behavior the
  experiment needs? It gates the experiment's admission of the engine — it
  is never evidence about the experiment's question.
- **[`admission_refused`](../GLOSSARY.md#admission-packet).** The packet's verdict when the engine fails the
  precommitted inequalities. Read it carefully: **the packet refuses to
  admit the engine into the pay-window study.** It is not an engine
  refusing anything, and not a memory-admission event. The homonym has
  fooled a lab member's own notes before; check a verdict term's referent
  at its minting source.
- **[Beeline](../GLOSSARY.md#beeline).** A free-routing session that reads exactly the dispositive
  surfaces and nothing else. Perfect competence — and fatal to the
  artifact's value, which is priced entirely in *skipped distractor reads*.
- **[Point-mode](../GLOSSARY.md#point-mode).** A run whose K pilots produced one unique realization
  (zero dispersion). It licenses statements about what was observed, and no
  distributional claim of any kind.

## The geometry

The pins (P-A1'..P-A7, adopted 2026-07-09 in thread `fourth-family`) define
admission over the existing greenreach fixture catalog — no new fixtures,
no new oracle. A candidate engine is `admitted` only if, cold and
free-routing:

1. conjunctive pass-rate ≥ 0.8 over all K=5 pilots (P-A2);
2. mean decoy reads on successes ≥ 5 (P-A3 — the arithmetic behind this
   was derived before any engine was named: at k≤4 decoy reads the margin
   dies, 4·35 − 65 = 75 < h=100);
3. per-branch `n_required` ≤ 24 under the shared Bessel `pilot_n_rule`
   (P-A4);
4. estimated effect size > 100, with every input computed through the code
   path that scores it (P-A5).

An `admitted` verdict licenses nothing by itself (P-A6): it arms a
Regime-S run on that engine, where a cost-win would have to be earned. The
loses-condition is built into the design: if a frontier engine passes the
outer gate but beelines, inequality 2 fails and the packet refuses — which
is exactly what happened.

The engine was gpt-5.4-2026-03-05 — selected by constraint, not
preference: GPT-5.5 refuses non-default temperature, and the sealed
dispersion pin needs [0.3, 0.7]. Temperature-locked frontier tiers are a
named limitation for any future family needing Regime-S dispersion.

## What ran

1. **Fresh [ignorance probe](../GLOSSARY.md#ignorance-probe)** — clean ("I don't know from my own
   knowledge"), re-probed rather than inherited.
2. **[Calibration](../GLOSSARY.md#calibration-gate)** — PASS: forced along the route, the engine reads
   {N31, X31, C31} and answers correctly.
3. **Five cold free-route pilots** — and the first un-forced conjunction
   assembly in the lab's record: **all five pilots read exactly the
   dispositive triple and nothing else.** `pass_rate = 1.0`,
   `decoy_reads = 0` on every success, every pilot cost exactly 298.
4. **Verdict: `admission_refused`.** Cold cost 298 beats the resumable
   floor of 354; `effect_size_est = 298 − 354 = −56 = −a_i`. The artifact
   is *strictly dominated* for this engine: its entire value is skipping
   distractor reads, and this engine skips them natively. No decoy
   geometry can open a window here — the artifact's ceiling is
   Σ(skipped decoy reads) − a_i, which is ≤ −a_i when nothing is skipped.
5. **Zero-dispersion disclosure.** All five pilots were one realization
   observed five times (`unique_realizations = 1` at temperature 0.5).
   The run downgraded itself to point-mode per §17 rather than dressing
   API jitter up as dispersion.

## The reframe

The moderator's ruling converted the day into the pause:

- **Below the band** (gpt-oss-20b, ch14): cannot assemble the conjunction
  — the artifact is a tax the engine cannot convert.
- **Above the band** (gpt-5.4): assembles it perfectly and beelines — the
  artifact is a tax on a skill the engine already has.
- **Inside the band** (competent-but-distractible): never observed — and
  the docket family showed the band's native variance can defeat
  measurement at n_max = 24.

The pay-window is bounded from both sides, and the band between the bounds
is [unoccupied](../GLOSSARY.md#unoccupied-band). Across every licensed cell in the whole record, **no
`PRF2-cost-win` exists** — but outcomes 2, 3, and 4 are instrument and
admission refusals, not behavioral negatives, so "never pays" remains
unclaimed.

## Inspect and replay

- The packet ledger:
  `runs/prf/ep-greenreach-baseline.admission-gpt-5.4-2026-03-05.jsonl` —
  one gate-open row (87 checks), the probe, the calibration row, five
  `sbr_session`/`session_outcome` pairs, the `zero_dispersion_regime`
  disclosure, and the `admission_packet` verdict row. The verdict row
  carries its own scope disclosure inline: "admission gate, never
  evidence."
- Read the verdict row directly: every claim in this chapter's "what ran"
  section is a field on it (`cold_pass_rate`, `decoy_reads_per_success`,
  `effect_size_est`, `resumable_floor`, `legs`, `verdict`).
- Wire tests (no engine, no evidence): `make prf-admission-test` runs the
  14 seeded checks in `tests/test_prf_admission.py`, including grok's
  Bessel counterexample (`[475×4, 900] → n=28`, refused) as a regression.
- Machinery: `harness/run_prf_admission.py` — pins scored with no
  discretion at evaluation time.

## What is licensed, and what is not

**Licensed:** on this fixture family, this catalog (21 surfaces), this
geometry, gpt-5.4-2026-03-05 free-routes to the exact dispositive triple
with zero waste, making the cold branch strictly cheaper than the artifact
floor. The claims list in PRF_FINDINGS is the authority, including the
corrections its own doc-review forced (a tie mis-stated as a loss; an
attribution split between the seat that wrote the sentence and the seat
whose arithmetic it rests on).

**Not licensed:** any distributional claim (point-mode: one realization,
five observations); anything about the resumable branch's free-route
behavior (`resumable_routing_untested` rides the row); generalization
beyond this fixture family or catalog size; any cross-family cost roll-up;
anything about engines outside the ignorance+calibration ladder.

## The residue that outranks the cell

1. **Admission gates measure their own geometry.** A2's firing in ch14 was
   narrated as a frontier finding until a cold read named the circularity;
   this family built the gate *as* a gate, and it worked — in the
   direction nobody wanted.
2. **The second-way class fired at three depths in one day** — estimator
   (population vs Bessel), version fork (canonical vs rendered a_i),
   pricing source (authored field vs text recompute). The binding rule:
   compute every scored quantity through the code path that scores it,
   and assert the number from the ledger row.
3. **The rotating-outsider seats carried the arc.** Two seats blocked a
   build the chair had already tested green; both were seated permanently
   the same day.

## Reopen trigger, and handoff

The question reopens when and only when a candidate engine's Phase-0
packet returns `admitted` (all four inequalities, machine-scored), or a
clean-transport docket rerun lands `n_required ≤ 24` with a licensed cell
either way. `admission_marginal` reopens nothing. Until then the question
is parked where an instrument should park: paused, typed, and cheap to
resume.

The lab's attention moved the next day to the NEXT-substrate arc — the body
architecture and the epistemic-frame check — where the admission-ladder
discipline built here (probe, calibrate, gate, refuse) became the template for
calibrating engines against a sealed spec. The gate refused that experiment
before calibration contact because its free-text oracle failed cold semantic
review. [Chapter 16](16_EPISTEMIC_FRAME_CHECK.md) follows the refusal and the
review loop that made a terminal budget necessary.
