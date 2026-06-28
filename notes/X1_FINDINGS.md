# X1 FINDINGS — Decay Dynamics (use-driven temperature under a Landauer oracle)

Status: **RESOLVED 2026-06-20 (dan's moderator ruling, thread-6): X1 instrument engineering-closed; synchronous eligibility-temperature retired as the X-track organ.** X1-win is a real-engine disclosed null across 3 models — the planned §8 close (X1-win *pass*) was not met, and *that is the finding*. **Next: an offer-dependence admission gate → a prune-to-cold-store spec only if the gate passes** (absence ≠ reweighting). Two guardrails now bind the X-track: attribution/scorer law (M-track-projection counterfactual) and organ-placement/milestone law (must do what the synchronous offer gate structurally cannot). Corpus note: rw-0001 is the *fish* retraction (not VICTOR/rw-0004); claude's ~Jan-2026 cutoff makes the mid-2025 retraction a live memorization confound, so the gate's fixture must be verifiably out-of-weights. entropy-os is a parts bin, not a dependency — decay lives in construct. Built dan+claude on branch `x1-decay-dynamics`; SPEC_X1 v0.1. Oracle: the Landauer oracle (M0's world oracle, rw-0001, coupled to a thermal actuator). `corpus_scope: single_chain rw-0001; one retraction; use-driven temp only; authority read-only`.

## The one-line result

**The instrument works and the machinery is proven (mock X1-win pass); but on all three real engines tested — gpt-oss-20b, claude-opus-4-8, and ministral-3-3b — the earned-reweighting win does not engage. Every model declines correctly whenever a retraction signal is in the offer set, so there is no credulity gap for temperature to close, and reweighting is redundant with plain offering on this task.** This is the M2 RS-loses / RS-stale pattern: the win condition is real and computable, but the pathology it needs is absent — even on a 3B model.

## Honesty correction & the third guardrail (dissent pass, 2026-06-20)

Two corrections from the dissent pass (claude-initiated under dan's "dissent before building" rule; codex + cursor converged; dan ratified) — folded so this doc does not over-claim:

1. **The null is confounded — it is *not* evidence the organ failed.** Offer-dependence was never established (kagi/cursor: the answer was recoverable from priors / framing / **weights** — rw-0001 is the *fish* retraction and claude's ~Jan-2026 cutoff makes it a live memorization confound). A confounded measurement cannot distinguish "temperature is redundant with offering" from "the fixture never tested offer-dependence." So *"redundant with plain offering on this task"* above is **softened**: the data is uninformative. Synchronous eligibility-temperature is retired on the **placement argument** — it is an offer-time eligibility multiplier, explicit by construction (a priori) — **not** on the null. `retrieved ≠ true`, on ourselves.
2. **The third guardrail — scoring-axis law.** The deeper trap: we measured an implicit organ on the *explicit layer's ruler* (did the answer change?). On the answer axis, **withheld-hot, pruned, and cold-in-lineage are observationally equivalent** (codex) — so *any* offer-set organ, prune-to-cold-store included, nulls on a competent engine for the same reason. The implicit substrate's win must be scored on a metric the offer gate **cannot move**: **retention cost** at matched quality, **revocation**, **what survives** — over a session, not a single answer. The next organ (prune) is scored on cost, answer quality as a floor + loses-cell.

## What was built (all green, no regression)

`harness/temperature.py` (`TemperatureStore`, the sibling of `authority` — eligibility multiplier, floor-clamped, Wall II allowlist `apply`), the eligibility fourth factor + `decay_dynamics`/`landauer_oracle` flags (off by default; **M-track proven byte-identical**), the four thermal row kinds, `harness/run_x1.py` (the A/B/C decay-fork: authority read-only, two harness-authorized logical clocks, the Landauer observer writing a `thermal_projection` before every `temperature_delta`), `harness/score_decay.py` (M-track projection invariant → soft-ablation → fail-closed verdicts), `tests/test_decay.py` (`make x1-test`, 6/6).

## Machinery: X1-win PASS on the mock (wire, not evidence)

On `MockEngine` (a deliberately credulous stand-in: cites the most question-overlapping offered record, declines only when the misleading record is gone), the earned-reweighting phase transition fires exactly as designed on the rw-0001 chain:

| branch | finding | correction | probe |
|---|---|---|---|
| **C** oracle-gated | clawed to floor 0.1 | paid to 1.6 | offers correction → **declines** (right) |
| **B** closed-loop | reheated to 2.0 | withered to 0.4 | offers finding → **cites** (wrong) |
| **A** no-decay | 1.0 | 1.0 | offers finding → **cites** (wrong) |

`score_decay` → **X1-win pass**: C's offers differ from A/B, C is world-better, and **soft-ablation isolates temperature** — clamping the finding's temperature to 1.0 re-offers it (symdiff `{finding}`, confined to the cooled record), so temperature (not an M-track gate) drove the offer. The instrument detects earned reweighting when a credulous engine is present.

## Real cross-engine: X1-win not_engaged across the board (3 engines × correction styles)

| fixture (correction style) | gpt-oss-20b | claude-opus-4-8 | ministral-3-3b |
|---|---|---|---|
| `reweight.json` (imperative: "do not cite") | not_engaged | not_engaged | — |
| `reweight-real.json` (factual M0-C1 notice) | not_engaged | not_engaged | **not_engaged** |

In **every** real run all three branches **decline correctly** (oracle score 1.0), from episode 1. No branch is ever credulous, so `engaged = False` (no A/B failure for C to beat) → **X1-win not_engaged**. The branch temperatures evolved correctly — the correction record warmed (important), the finding cooled (passenger/clawed) — but it changed no answer, because the answer never depended on whether the finding was offered.

**The decisive run: even ministral-3-3b declines.** The weak-model regime was the hypothesis's last refuge — a small model overlooking an offered correction. It does not overlook it. A 3B model heeds "the article has been retracted" exactly as the 20B and the frontier model do. So the credulity gap reweighting needs **does not exist for the finding-plus-its-own-retraction-notice task on any model tested**: surfacing the correction (which the offer boundary already does) is sufficient, and reweighting adds nothing on top.

- **X1-U1: pass** in all four runs — the decision was scored against rw-0001, `source != authored`. The world leg holds whether or not the win engages.
- **X1-burial / X1-overcool: not_engaged** (disclosed nulls, as §8 anticipated) — no honest-disuse burial and no standing-claim claw arose on a sound oracle.

## The honest bound (why, and what it means)

Temperature changes the **offer set**; it changes the **answer** only when the answer depends on the offer set. All three engines — down to a 3B local model — heed an offered retraction signal and decline **regardless of whether the misleading finding is also offered**. So cooling the finding out is moot: the engine was already going to decline. The win requires an engine that is *credulous in the presence of the correction* (cites the finding while the notice sits right there) — the mock is exactly that; none of the three real models are.

**The sharper, more honest framing: reweighting is redundant with plain offering on this task.** The offer boundary already surfaces the correction record; every model tested *uses* it correctly. Earned reweighting (cooling the misleading record on top of surfacing the correction) adds nothing, because surfacing the correction was already sufficient. For reweighting to beat the baseline you need a task where **surfacing the correction is not enough** — and the finding-plus-its-own-retraction-notice task is not such a task for any model down to 3B.

This is squarely on-thesis: **offer-set governance matters where the engine is weak enough to need it** — and it turns out none of these engines are weak enough on *this* task. It is the same shape as M0's C-2 (a self-sufficient correction "costs nothing to bury" — here, costs nothing to surface, because it was already heeded).

**This is not an X1-win pass.** The §8 plan assumed X1-win would pass on the cross-engine pair; it did not, across three models. That is a finding, not an embarrassment — but it means **X1 does not close on the planned basis without a moderator ruling.**

## Carried to v0.2 (the engagement debt)

The weak-engine path was **tried and closed**: ministral-3-3b heeds the offered correction exactly like the larger models, so "use a smaller model" does not open the gap. What remains needs a **task where surfacing the correction is not sufficient** — a genuinely different shape, not a weaker model or a reworded notice:
1. **A correction the model can't directly act on** — e.g. the misleading record and the corrective signal are not about the same surface (the model must *infer* the conflict), so offering the correction doesn't auto-resolve it and cooling the misleading record carries real weight.
2. **Many-distractor retrieval** where the correction is one record among dozens and top-k budget (not eligibility) is the binding constraint — then cooling the misleading records is what gets the correction *into* the budget at all.
3. **Accept the negative result**: earned reweighting is redundant with plain offering on single-correction tasks; its value, if any, lives in the budgeted/inferential regime above, which X2+ can test. Do **not** rig credulity by framing — that is the result-fishing the lab refuses.

X2's outcome-linked dynamics, X3's dispositions/drift, and erasure-below-floor remain as specced.

## Instrument honesty

The real run exposed a gap in `score_decay`'s taxonomy: "every branch already correct" was scoring as `fail` rather than `not_engaged`. Fixed (the `engaged` predicate: a non-oracle branch must be wrong for the win to be engaged) before any verdict was recorded; the mock X1-win still passes. *The run reveals the truth* — second citation of the M-track refrain, one track over.

## Disclosure

Mock rows are machinery wire tests, never evidence (engine_backend recorded; `score_decay` stamps the disclosure). Real runs: gpt-oss-20b (LM Studio, local) + claude-opus-4-8 (API), single-sample ablation, lexical TF-IDF similarity, one chain (rw-0001), N=6-episode sequence. Ledgers: `runs/x1/`.
