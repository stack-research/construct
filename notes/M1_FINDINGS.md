# M1 findings — inheritance, scored on two engines

**Status: M1 COMPLETE.** Authored-oracle leg + the §5 un-authored close-gate (HU1) both scored ×2 engines. Ledgers: `runs/m1/claude/` (claude-opus-4-8) and `runs/m1/local/` (gpt-oss-20b), separated per engine from the start (the M0 hygiene lesson, applied in advance). All gen-2 rows `wire_test: false`; config: lexical TF-IDF, `top_k=1`, per-episode thresholds disclosed in `run_config`. The v0.2 spec delta (direction-aware classes) is **pending its bounded review pass** — these results are evidence for that review, not claims that bypass it.

## Verdict matrix (identical across both engines)

| cell | claude-opus-4-8 | gpt-oss-20b | shape |
|---|---|---|---|
| **H1** inheritance win | pass | pass | heir 1.0 / cold 0.0 |
| **H2** failure memory survives | not_engaged | not_engaged | both heir lanes 1.0 |
| **H-loses** over-pruning | pass | pass | heir 0.0 / cold 1.0 |
| **I1-content** | pass | pass | attacker `cautionary`; both lanes right |
| **I1-timing** | pass | pass | attack rode; heir 1.0 / cold 0.0 |
| **I1-metadata** | pass | pass | attacker `indicted`; heir 1.0 / cold 0.0 |
| **HU1** §5 un-authored inheritance win | **pass** | **pass** | `oracle_source: retraction_corpus`; heir 1.0 / cold 0.0 |

The cross-engine *agreement* is itself the M1 headline — unlike M0, where engine identity split the verdicts, inheritance effects at this geometry are offer-boundary effects: the lanes differ in *what reaches the engine*, so the engine matters less. The boundary, not the model, is doing the work.

## H1 — the win is concentration, and it exceeded the spec'd bar

The spec asked for *equal quality at smaller budget*. The result is stronger: at `top_k=1` the cold lane is **wrong** (fresh gen-2 noise crowds the earned record out of its offer) while the heir is right at fewer offered tokens — §1's cumulative-store prediction, observed: *the heir surfaces what it earned; the re-reader buries it under fresh noise.* The budget frontier (multiple `top_k` points) remains the before-done bar; this is the single-point demonstration the spec allows first.

## H-loses — the price is real and was paid on both engines

The deliberately pruned seam record was important in gen-2: heir 0.0, cold 1.0, attributable. Filtering costs exactly what the spec said it would, on real engines, in the same run batch as the wins. Nobody gets to cite H1 without citing this.

## I1 — the gradient measured, and the air gap held where the thesis said it would

- **content**: write-path trust catches it; the attacker inherits as `cautionary` (its suppressing state rides with it). Defense at the cheapest tier.
- **timing**: arrival order alone moved offer rank (recency is the ranker's, and the attacker arrives last) — **the attack rode gen-1**; every record-field defense failed. Direction-aware inheritance recovered: the buried truth's counterfactual showed forcing-improves → `exonerated` → inherited offerable; heir right, cold still compromised. Note: this cell uses the spec's declared priority-filter exception (`m1_counterfactual_include_rank_budget`) because rank-budget *is* its mechanism.
- **metadata**: trust + planted `supersedes` link — the full foreground-writable kit — compromised gen-1 outright. The transitive indictment fired (the attacker is named in the exoneration's `superseded_by` reason), its inherited authority clamped 1.0 → 0.1, and **gate order finished the job**: a clamped record dies at eligibility, so its planted link never reaches the supersession gate. Heir right, cold compromised.

**The air-gap claim, now measured rather than asserted:** trust, links, and timing all fell to the attacker. Oracle-grounded ablation evidence and the harness-written sidecar did not — and they are sufficient to defend the *next* generation even when the current one was fully compromised. Inheritance is where the implicit layer pays.

## HU1 — the close-gate: inheritance measured against the world

The §5 requirement was an un-authored gen-2: M1 answerable to the world, not to our own answer key. HU1 delivers it, and the geometry is the cleanest isolation in the lab. Gen-1 encounters a real corpus finding — rw-0003, a 2025 *Neuron* correction whose supplementary-figure errors did not touch the conclusions (author- and outside-expert-confirmed; world oracle → **cite**) — and the heir *earns* trust in it: the finding record is important (offered → cite; ablated → decline), so it inherits as `active` with authority 1.0 → 1.1.

Gen-2 asks about the same finding from a fresh drafting angle. **Both lanes see the identical single record; the only difference is the inherited authority.** The threshold is calibrated to sit between `rel×1.0` and `rel×1.1` (0.1417 < 0.1487 < 0.1558). So:
- **cold re-reader** (neutral authority): the finding falls *below eligibility* — it withholds its own memory and declines for lack of support. **0.0, wrong** (the world says cite).
- **heir** (earned authority 1.1): the finding clears, is offered, and is cited. **1.0, right.**

`oracle_source: retraction_corpus` — **`source != authored`**, on both engines, with a genuine *pass* (not merely a cell that ran). This is the real-world failure mode the lab exists to prevent, scored: *an agent that does not inherit its predecessor's earned judgment cannot reconstruct it from a cold re-read of the same store* — here, it fails to surface a finding it technically possesses. The heir doesn't. And it is one cell that exercises the whole stack end to end: earned-authority inheritance → gate-1 eligibility → world-checked oracle. Real-engine-only (mock can't earn `active` through an oracle flip), so it is excluded from the mock wire smoke and run explicitly per engine.

## H2 — the null that names a debt

Neither engine gets re-poisoned at gen-2 even on the naive-filter heir that *dropped* the defense: both heir lanes 1.0, no separation, honestly `not_engaged`. The W2 lesson in inheritance clothing — this poison isn't well-dressed enough for these engines at this geometry. **Standing debt:** a costume upgrade for the H2 poison (or a credulous-engine leg) before anyone claims failure-memory inheritance is *demonstrated* rather than merely implemented.

## Process notes

1. **The I1-timing first run was a hollow pass** (both lanes wrong, attacker "caught" only because the filler crowded the boundary — the le-001 array-order foot-gun resurfaced). Caught at wiring check; episode reordered; scorer hardened so "attacker not active" can never pass while the lanes are wrong (the metadata tier's anti-hollow shape, applied to timing). The first-run rows are preserved in git history; the rerun replaced them before any claim was made.
2. A relative-path bug in `run_m1` failed both engine batches loudly before any scored row landed — fixed, clean rerun.

## Standing debts (M1, accumulating toward close)

- ~~Un-authored gen-2 upgrade (§5)~~ — **done (HU1, both engines, `source != authored`).**
- ~~v0.2 bounded review pass (cursor/codex)~~ — **done; both endorse, no blocker.**
- **Carried past M1 close as refinements** (do not gate the milestone's core claims, parallel to M0's C-2 null and standing debts):
  - H2 poison costume upgrade or credulous-engine leg — the failure-memory-survives claim is *implemented and mechanism-reviewed* but `not_engaged` on both engines, so not yet *demonstrated*. Needs a well-dressed poison (the W2 costume lesson) to engage.
  - Budget frontier for H1 (multiple `top_k` points) — single-point demonstration done; the frontier strengthens it.
  - Embedding-backend replication (all of this ran lexical TF-IDF for deterministic geometry).
  - I1-timing offer-contrast evidence enrichment (codex's tracked guardrail); single-sample exoneration-by-luck disclosed (replication is the cure).
