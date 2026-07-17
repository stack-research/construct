# EFC v2 Findings — Part I contact stage (2026-07-17)

**Status: CLOSED `confounded(admission_band)` — dan's standing (d) ruling; dan seals.**

One day, one lineage: the v2 battery was authored, cold-reviewed, attestation-bound,
and pinned in the morning; by evening it had met two live engines across four runs
under six dan-executed pins. This file is the typed record. Thread:
`epistemic-frame-check-v2` (build stage folded earlier the same day; see
`EFC_V1_FINDINGS.md` for the inherited admission requirement).

## The question

EFC v2 inherits v1's admission requirement: before any treatment leg may run, an
engine's *untreated* balanced relevant accuracy on the frozen battery must land in
the declared band **[0.40, 0.4375]** (K=128; Newcombe-derived UB) with the
competence floors passing — competent enough to be worth treating, fallible enough
on the hidden scope bit to leave measurable headroom. v1 closed
`confounded(menu_ceiling)` because gpt-5.4 saturated the surface (B_obs = 1.0).
v2's contact stage asked: does a small local engine occupy the band?

## The battery (sealed before any contact)

- K=128 counterfactual blocks × 3 fixtures = 384, authored by one deterministic
  script (`harness/efc_author_battery_v2.py`, commit `9ce5b4c`) — 8 plain domains
  × 16 variants; delete the corpus, rerun, byte-identical.
- Leak audit by frozen predictors: L1/L2 pinned at 0.25 per stratum (vs 0.35
  threshold) via menu rotation and label/body token disjointness; L3 at exactly
  0.50/0.50 via the half-tilt discipline (mates share bytes, so the L3 predictor
  provably cannot correlate with the scope bit).
- glm-5.2 (max) cold review: **PASS, zero blockers** — all six §B
  forbidden-headroom sources verified absent.
- Plausibility attestations materialized per dan's ruling as mechanical
  projections of the reviewer's immutable PASS entry (commit `2d1c3f1`; glm
  ENDORSE) — `fixture_suite_hash ca4f173b…` binds content + review together.

## The runs

| Run | Fork | Outcome | What it taught |
| --- | --- | --- | --- |
| 001 | qwen3.5-9b / "high" | `confounded(commitment_invalid_rate)`, aborted 528/896 by dan's ruling | cap 256 wholly consumed by reasoning; uniform censoring; zero engine judgment recorded; battery uncontaminated |
| 002 | qwen3.5-9b / none | `confounded(admission_band)` + `within_class_commit` + `pair_constant_policy`, 896/896 wire-valid, ~11 min | fails **sideways**: irrelevant floor PASS 0.953; constant-withhold (S=0; match 0.086 / mismatch 0.883; balanced 0.4844 > UB); forced-class at chance |
| 003 | nemotron-3-nano-4b / none | `budget_refusal(input_token_ceiling)` at 883/896, all valid | tokenizer variance (317 vs 303 tok/call) exhausted the estimate-based ceiling; honest instrument stop |
| 004 | nemotron-3-nano-4b / none, measured-rate ceiling | `confounded(admission_band)` + `within_class_commit` + `pair_constant_policy`, 896/896 wire-valid | the formal verdict: same sideways shape as run 002, second engine |

## Named findings

1. **The §A redesign earned its seal on first live contact.** Run 002's engine
   adopted near-universal withholding — exactly the constant policy the v1
   design-error finding predicted a mismatch-only estimand would reward with a
   false pass. Two independently sealed defenses caught it independently: the
   balanced estimand (0.4844 > UB) and the anti-constant pair predicate (S = 0
   against a 53–75 acceptance region).
2. **Within-class incompetence is the small-engine failure mode, not weakness.**
   Both no-think forks passed the irrelevant floor (0.93–0.95, ordinary
   competence) yet selected the coherent within-class member at *chance* even
   when the class was supplied outright. The §C.3 dual-scored forced-class gate
   isolated this cleanly from the scope-bit question.
3. **Thinking-mode is unviable under a zero-tolerance validity ceiling —
   a distribution-shape argument.** Measured think-lengths on trivial synthetic
   items: 6.5k–7.8k tokens with one 16k+ runaway. With zero tolerance for
   invalid commitments, a single censored call types the run; no finite cap
   survives a heavy tail at n=896. The instrument refuses reasoning engines on
   local hardware as a class, and says so honestly.
4. **Cap arithmetic must be per-engine-class; token estimates are per-tokenizer.**
   v1's cap-64 JSON truncation, run 001's cap-256 reasoning censoring, and run
   003's tokenizer-rate ceiling breach are one confound family: output ceilings
   interact with everything the engine emits, and input estimates are floors,
   not cross-engine bounds. The repair trajectory (K=8 early-censor tripwire;
   measured-rate ceilings via code-pinned formulas) turned the whole family into
   cheap typed refusals.
5. **The unoccupied band, third sighting.** PRF's pay-window, v1's menu ceiling,
   and v2's sideways failures all land the same shape: the
   competent-but-distractible band the conjecture needs is unoccupied by every
   engine measured so far — too strong, too weak-in-class, or constant-policy.
   The repetition across three differently-typed studies is now itself a named
   finding: the band may be genuinely narrow in the current model landscape.
6. **Process: the review economy caught the moderator twice.** Sol's B4 (sealed
   gate read manifest keys the pinned manifest lacked — admission pass
   mechanically unreachable) would have wasted first contact; sol's arithmetic
   catch (a prose increment matching no formula) forced the ceiling derivation
   into testable code. Dan's two in-conversation rulings (abort the doomed run;
   smoke-test before long invocations) each changed the instrument the same day.

## Instrument demonstrations now on record

- Wire-commitment elicitation: clean across three engines live (v1 gpt-5.4,
  qwen-9b-nothink, nemotron-4b-nothink) — 100% valid on every completed no-think run.
- The B1 pin gate refused dan's own pin until the licensed constant acknowledged
  the new event — sidecars cannot self-authorize, demonstrated on real input.
- Six dan-executed pins in one day; every verdict typed by sealed machinery;
  zero sealed-byte drift; battery never contaminated (run 001's censoring
  recorded zero engine judgment; runs 002–004 are post-seal contact under pin).

## Verdict (run 004 — sealed gate report, complete battery)

`nvidia/nemotron-3-nano-4b` / none, 896/896 calls, **100% wire-valid**, typed
**`confounded(admission_band)`**, with `within_class_commit` and
`pair_constant_policy` failing on the same report; `commitment_invalid_rate`,
`leak_audit`, `irrelevant_band`, and `fork_identity` all pass.

Numbers: irrelevant **119/128 = 0.930** (floor PASS); match **44/128 = 0.344**
vs mismatch **72/128 = 0.562** (balanced **0.453 > UB 0.4375**); switched pairs
**S = 1** (needs 53–75); forced-class **128/256 / 120/256 — chance both ways**.
The same sideways failure as qwen-9b, in a different engine family at a
different size: mostly-withhold on commit decisions, chance-level within-class
selection, ordinary competence intact. Run 003's overdetermined preview
(883-call partial) is confirmed exactly by the formal verdict.

## Close

**CLOSED `confounded(admission_band)` per dan's standing ruling ("one more,
then close and write it up"), 2026-07-17.** Two engines formally typed, one
instrument-refusal family named and armored, zero sealed-byte drift across six
pins, the conjecture untested for a measured reason — the admission gate did
its job: it refused to let a treatment study run where no effect could have
been read. Reopen condition carries forward from v1: an engine whose untreated
B_obs sits inside [0.40, 0.4375] with floors passing, fresh fork pin, same
sealed battery (`fixture_suite_hash ca4f173b…`). The battery, harness, and pin
discipline are reusable as-is; candidate engines should smoke-test at ~30
calls' cost before any full run.
