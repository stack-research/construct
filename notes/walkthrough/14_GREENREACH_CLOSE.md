# Chapter 14 — Greenreach: the day the instrument caught everything, including us

Previous: [The pause/resume frontier](13_PAUSE_RESUME_FRONTIER.md) · [Walkthrough index](README.md)

Chapter 13 ended on a fork: if Greenreach opened the pay-window, a debt came
due; if it closed, the question would shift from fixtures to engines. This
chapter is the close — but not by the route anyone predicted. It all happened
on one day (2026-07-06), and the day's real product is not the cell. It is a
demonstration that the fail-closed machinery works under fire, and a finding
about what two oracles in a row were accidentally paying for.

**Status: closed.** The Greenreach family closed `confounded (A2)` — the
third consecutive family-level negative at this budget discipline. When this
chapter disagrees with the spec, the spec wins:
[SPEC_PAUSE_RESUME.md](../SPEC_PAUSE_RESUME.md) Part IV (§36–§46), including
the dated correction appended to §39.

## The question, sharpened once more

Part IV pinned the detectable form of the pay-window question (§36–§37, ch13):
cheap decoy siblings make the cold branch's *distracted* realization an
expensive PASS rather than a budget-blowing fail, so the pay-window is
arithmetically measurable at `n_max = 24`. One new oracle-side law came with
it — the **conjunctive evidence gate** (§41): no disposition is adequate
unless the session actually read all three dispositive legs. That law was
designed to seal a partial-credit hole found in the docket's ledgers. It
ended up being the day's protagonist.

## What ran, in order

1. **Dual-lane build.** Harness (F1 §29 forced-stop enforcement — twice, at
   the runner and independently at the scorer; D13 diagnostic rows; the §41
   conjunctive oracle shared between runner and gate; the v0.4 fixture gate
   with a 28-case wire-sweep) and fixtures (`episodes/prf/greenreach-release/`,
   composer's delegated build, two rounds — the reviewer caught an attested
   probe that never ran and fixture prose that broke the fourth wall).
   Sealed families were re-scored byte-identical under the new scorer.
2. **Five-seat build review.** All PASS, zero blocking findings — including
   the first seated read from the lab's proxied external cold reviewer.
3. **Engine contact.** Fresh ignorance probe (clean, confabulation disclosed),
   calibration PASS — and then the **A2 detector fired on the very first
   dispersion pilot**: cold conjunctive pass-rate 0/5.
4. **Stop the line.** Diagnosis found two transport defects, not engine
   behavior: pilot sessions never received the R-handle instruction (a
   version-fork gap carried from 0.3), and the engine's harmony channel
   envelopes leaked into `raw_action`, so legal handles were refused as
   gibberish. Worse: the same signatures riddle the *committed §33 ledgers*
   (119/245 decisions refused) — the sealed §39 sentence "zero grammar
   refusals across §33" was **false against the record**. Nobody had computed
   it.
5. **The §43 ladder, run in full.** Four seats verified the single-run path
   from the ledgers. Unanimous: the firing was ARTIFACTUAL. But the
   adversarial seat, told to steelman CONFIRMED, found something real
   underneath: in *clean-transport* sessions the engine still read one leg,
   stopped, and guessed — and the docket's non-conjunctive oracle had been
   **rewarding** exactly that habit (committed cold passes exist with
   `read_ids=[]`). The numbers seat priced the hypothesis before any new data:
   a decision table mapping clean cold pass-rate to A2-close / D11-close /
   proceed, with its own retraction precommitted for the worst row.
6. **Repairs, then the rerun.** Factory fix with a real-engine regression
   (the mock-blindness lesson: five seats had reviewed tests that never
   exercised a real session factory); harmony unwrap at the extraction
   boundary with the envelope preserved as `raw_transport` and the grammar
   kept strict; the §39 correction appended with the false sentence preserved
   as written.
7. **A2 fired again — real this time.** Clean transport verified in-ledger
   (6/31 refusals, all correctly-refused exotic JSON). Every free-route
   session, cold *and* resumable, read one plausible surface and answered:
   zero conjunctive passes in seven cold-side sessions
   (P ≈ 1.3×10⁻⁵ against a true pass-rate of even 0.8). Not the bimodal the
   decision table priced — pure `c_max` mass. Condition (b) triggered: the
   fits-24 derivation was retracted by its own author, on schedule.
8. **Close.** Family closed on A2 by the precommitted stop rule. The analogs
   ran as point-mode instrument alarms and stayed correctly silent (a
   falsifier needs a resumable cost-win; lazy-stopping prices every branch
   at `c_max`).

## Inspect and replay

- Ledgers: `runs/prf/greenreach-baseline.sbr-gpt-oss-20b.jsonl` (r1, the
  transport-defect record — attested `superseded_by`, never scored) and
  `…-r2.jsonl` (the clean run the close rests on), plus the two analog
  ledgers beside them.
- The split that settled the board round is one command:
  count `route_decision` rows with `refuse_reason` by probe-vs-branch
  session, in both the Greenreach and the committed docket ledgers.
- The transport repair is visible on the rows themselves: `raw_transport`
  carries the envelope whenever unwrapping changed what the parser saw.
- Re-run the family gate:
  `uv run --no-project python -m harness.check_prf_fixture episodes/prf/greenreach-release/manifest.json`
- The seeded regressions (forced-stop-pass, wire-sweep golden cases, harmony
  envelopes verbatim from the defect ledgers, the real-engine factory path):
  `uv run --no-project python -m unittest tests.test_prf4`

## What is licensed, and what is not

**Licensed:** gpt-oss-20b, free-routing under this geometry at 700/10/900,
does not assemble a three-leg conjunction unprompted — at any price. The
calibration gate proves the capability exists (forced along the route, it
reads the triple and answers correctly); free-routing shows the behavior.
The pay-window question is **not answered negative** — this engine never
entered the regime where paying was measurable.

**Not licensed:** anything about other engines; anything about the pay-window
"anywhere"; anything about the paused small-engine lane. One engine, one
geometry, one budget — the external reviewer's scoping phrase, adopted into
the close vocabulary.

## The residue that outranks the cell

1. **Oracles buy behavior.** The docket's non-conjunctive oracle paid out
   for read-one-leg-and-guess for a month; §41 converted the same behavior
   into a typed refusal on first contact. Two families in a row, the deepest
   finding is what the oracle was accidentally rewarding.
2. **Compute the sentence.** §39's false claim was written by content-read
   over a record one grep would have falsified. The lab's own review culture
   (cite-by-location, assert-the-number) caught a seal-integrity drift the
   day before; it did not catch this. The correction is appended; the
   original stands preserved, wrong, and dated — that is what immutable
   lineage is for.
3. **Precommitment removed discretion exactly when discretion would have
   been tempted.** The retraction was written before the data that triggered
   it; the close converted by stop rules, not judgment. The instrument
   refused its central question and typed every refusal.

## Handoff

Three families of typed negatives under one budget discipline. The docket
says the fail-form regime confounds; Greenreach says this engine will not
route into the detectable regime at all. The open problem is now squarely an
*engine* problem: eliciting un-forced conjunction assembly — the calibration
gate proves it is there — from an engine that habitually answers off one
surface. Any fourth family starts from that; and the §23 causal-reduction
law (precommit the reduction shape before Regime S) now governs any family
that can reach a win.
