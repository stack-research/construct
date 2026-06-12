# M0 findings — first scored verdicts against an un-authored oracle

**Success condition met (ROADMAP M0):** the first `cell_verdict` rows carrying `oracle_source: retraction_corpus` (`source != authored`), `wire_test: false`, on real engines. Ledgers: `runs/c1-rw0001.stage_b.jsonl` (claude), `runs/c1-rw0001.local.stage_b.jsonl` (gpt-oss-20b), and the two C-2 ledgers. Config: lexical TF-IDF, `top_k=1`, `eligibility_threshold=0.18` (disclosed in `run_config.episode_overrides`), recency off.

## Verdict matrix

| cell | claude-opus-4-8 | gpt-oss-20b |
|---|---|---|
| **C-1** retraction (governance should win) | `not_engaged` | **`pass`** |
| **C-2** correction (governance should lose / null) | `not_engaged` (null) | `not_engaged` (null) |

## C-1 — the governance win is engine-dependent, and that is the finding

On **gpt-oss-20b**: policy-off lanes (L1/L2/L3) cite the retracted finding — the attractive claim crowds out everything at `top_k=1` — and score 0.0. L2s declines, because supersession buried the claim and surfaced the retraction notice, scoring 1.0. **Supersession is the sole cause of the correct outcome.** A clean governance win on an un-authored oracle.

On **claude-opus-4-8**: every lane declined, so `not_engaged`. But the *reasons* diverge — policy-off lanes declined out of generic DOI skepticism ("the DOI does not correspond to a verifiable article"), while L2s declined for the actual reason ("this finding comes from an article that was retracted"). Right answer, wrong reason in the policy-off lanes. Claude is cautious enough to refuse citing any finding it cannot verify in-weights, so the offer boundary had nothing to add.

**The lab's recurring lesson, again:** engine identity is a variable in every finding (cf. smoke-001, where claude abstained while gpt-oss confabulated). Governed supersession earns its cost on a credulous engine and is redundant on a maximally cautious one. The mechanism's value is real but conditional — and the condition is measurable, not hand-waved.

## C-2 — the disclosed null, on both engines

Both engines cite correctly in L2s despite the claim being buried, because the correction notice is **self-sufficient**: it states the conclusions are unaffected, so the engine reads it and cites. No price. This is the null result SPEC_M0 §3 predicted for non-terse notices — a finding about correction notices as a memory surface, not a failed cell. A *terse* correction (one that does not restate that the claim stands) would force a wrong decline; none of the three verified corrections in the corpus are terse, so the price is currently unobservable. Recorded as a standing debt: M0 wants a terse correction to make C-2 bite.

## Sub-finding (not the cell's job, but logged) — generated ≠ true

In C-2 on **claude**, lanes L1 and L3 — holding only the *claim* record — declined by **confabulating a retraction** ("This paper has been retracted from Neuron"). The paper was corrected, not retracted, and no record said otherwise. The engine invented the stronger event. This is an R1-flavored artifact on the generation side (generated ≠ true), and it cuts against naive lanes specifically: the offer boundary that surfaced the *actual* correction notice (L2/L2s) produced accurate reasoning, while the lanes left to their own parametric memory hallucinated a harsher world. Worth a dedicated cell later.

## What M0 has now

- Un-authored oracle wired end to end: corpus → loader → `world_checked_oracle` → scored cell verdict, decision computed from the world's category, not authored here.
- One governance win (C-1/gpt-oss) and one disclosed null (C-2/both) on real retraction/correction events.
- A cross-engine split that is itself a result.
- Standing debts: a terse correction for C-2; the generated≠true confabulation cell; embedding-backend replication (these ran on lexical TF-IDF for deterministic geometry).
