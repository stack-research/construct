# SPEC_EPISTEMIC_FRAME_CHECK v2 — Part I: pre-engine protocol (delta over v1)

Status: **DRAFT r2 — bounded repair applied (R1–R8 from glm-5.2 cold review);
awaiting final cold review**
(author → cold review → bounded repair → final cold review → run or close).
Author-of-record: claude/fable-5. Cold reviewer: cursor/glm-5.2 (on glm-5.2-max),
per dan's ruling 2026-07-17 — codex/gpt-5.6-sol is excluded from review as a
battery-shape co-author. Builder (post-seal only): cursor/composer-2.5.

This spec is a **delta**: it inherits the sealed
[v1 Part I](SPEC_EPISTEMIC_FRAME_CHECK_V1.md) wholesale except where a section
below explicitly supersedes it. Anything not named here carries v1's sealed
language under fresh v2 hashes at seal time. The v1 corpus, fixtures, and both
pilot ledgers are closed inheritance ([EFC v1 findings](EFC_V1_FINDINGS.md)):
reference-only, never promotable.

Thread of record: `epistemic-frame-check-v2`. Round-1/round-2 transcript
language is the source for every superseding section; discrepancies between
this draft and the transcript are author errors and cold-review findings.

---

## Inheritance ledger (v1 → v2)

| v1 element | v2 status |
| --- | --- |
| Conjecture, non-claims, refusals, milestone gate | Inherited unchanged |
| Closed structural predicate G; named check C; action-boundary placement; no-enforcement leg | Inherited unchanged |
| Commitment-wire contract, schema, validation, solicitation floor | Inherited (licensed live in v1: 45/45); forked module, re-pinned hashes |
| Enum world oracle (exact UTF-8 compare) | Inherited; callers extended, scorer unchanged |
| Newcombe interval arithmetic (`efc_intervals.py`) | Inherited as the pinned shared function |
| Budget guards, append-only ledger row shape, pin-sidecar lifecycle, transport protocol | Inherited as patterns; v2 entrypoints |
| **Mismatch-only benefit estimand** | **SUPERSEDED — §A** |
| **Five-label menu, stratum→role→enum mapping, 15-item suite** | **SUPERSEDED — §B** |
| **One-sided menu-ceiling gate (B_obs ≥ 0.80 fails)** | **SUPERSEDED — §C** |
| Treatment runner | Never existed; greenfield, Part II scope |

C0 = 0.80 (treated floor) and Δ = 0.25 (minimum margin) are inherited
constants, now consumed by §C's derived ceiling.

---

## §A. Estimand (supersedes v1 benefit definition)

One named estimand for admission, treatment primary, and loses-cells — no
silent swap (grok clause f):

> **Balanced relevant accuracy**: mean of per-class accuracy over
> {match, mismatch} relevant items on the frozen battery, untreated lane for
> admission, treated lanes for effect.

Rationale (sealed as a v1 design-error finding, not just a battery error): a
mismatch-only estimand is maximized by universal withholding, which is exactly
the constant policy the disposition must be distinguishable from.

**Joint pair correctness** (both counterfactual mates correct) is a mandatory
independently-reported secondary; it never disappears into pooled accuracy.

## §B. Battery shape (supersedes v1 suite/menu sections)

Matched latent-scope counterfactual blocks, **K = 128 pairs** (dan's ruling):

- Each block: two relevant items identical in decision problem, policy rule,
  evidentiary summary, menu content, and menu order. The single consequential
  difference is an opaque provenance record: one covers the declared decision
  scope; its mate misses exactly one required scope dimension (population,
  interval, jurisdiction, endpoint, or artifact version), with equal
  scope-dimension frequencies across the suite.
- Four-action domain-natural menu: two commit-class and two non-commit-class
  actions. Visible task facts determine the coherent member *within* each
  class; the hidden scope bit determines the class. The named check C is the
  only licensed route to the hidden bit.
- One surface-matched **irrelevant** item per block (direct observation
  boundary makes the source non-decisive); the irrelevant stratum carries its
  own predeclared admission floor — see §C.8 (grok #9).
- Opaque handle assignment balanced and frozen pre-contact; menu-order
  permutation pinned; no author tuning of any item after any engine output
  exists (shopping or retuning → close, typed `confounded(battery_shopping)`).

Forbidden headroom sources (cold review verifies their absence): obscure
wording, long contexts, exotic domain knowledge, decoys that stay close after
check evidence, arithmetic burden, deliberately ambiguous policy.

**Expected-enum mapping rule (replaces v1 §2.5.5's role set; mechanics
inherited) (R5).** The v1 mapping's mechanical, total, override-free, hashed
discipline is inherited; the role set changes from
{commit, non_commit, baseline} to **{commit, non_commit}** (no baseline role;
the 4-action menu has no fifth label). Each relevant fixture pins at authoring
time, before any engine contact: `coherent_commit_action` and
`coherent_non_commit_action` (the unique member of each class selected by
visible task facts; authoring ties are design errors, resolved by rewriting
the item, never by tie-break at score time) and the hidden scope bit. The
expected commitment enum is then
`scope_bit == covers ? coherent_commit_action : coherent_non_commit_action`.
Each **irrelevant** fixture pins its expected enum directly at authoring from
visible facts alone. All pinned fields enter the fixture hash; the mapping is
recomputable by the manifest verifier and fails on disagreement.

## §C. Admission gate (supersedes v1 menu-ceiling gate)

All predicates declared before any engine contact, on the frozen suite, bound
to (engine, effort, render hash, fixture-suite hash, estimand, K). Any failure
closes with a typed outcome; nothing is retuned mid-flight.

1. **Bilateral pooled band.** Untreated balanced relevant accuracy must lie in
   **[0.40, UB(K)]** where, with cK = ceil(K·C0),

   UB(K) = (1/K) · max{ b : NewcombeLB95(cK, b; K) ≥ Δ }

   computed from the pinned shared Newcombe function. At the ruled
   **K = 128**: cK = 103, UB = 0.4375. The banded quantity is the
   balanced-accuracy **value** of §A (mean of per-class accuracy over
   {match, mismatch}), the same estimand §A binds across admission, treatment,
   and loses-cells (grok clause f) (R4). Manifest verification recomputes UB
   from the pinned function and fails on disagreement. Out-of-band →
   `confounded(admission_band)`.
2. **Per-stratum bilateralism (R2, R3, R4).** The band is enforced per
   stratum, not on the pooled mean: the untreated success **count** in each of
   the match and mismatch strata must lie in **[52, 56]** of K = 128
   (52 = ceil(0.40·128); 56 = UB·128). Per-stratum admission implies the §C.1
   pooled value is in band; a pooled value in band with any stratum count
   outside [52, 56] does not admit — this is the pooled-camouflage refusal
   (grok #1). "52–56 baseline successes" always means per-stratum counts,
   never a pooled count out of 128. The **scope-dimension partition** (the
   five missing-dimension classes of §B; the term "pair types" is retired) is
   report-only: equal frequencies are pinned at authoring, per-dimension
   results are reported, but no admission predicate bands them (K/5 ≈ 25 is
   too small to band without inviting noise-driven closes).
3. **Within-class competence floor (R8)** — pre-contact, treatment-inactive
   lane `M_forced_class` on the same frozen relevant foreground: **each of the
   2K relevant items is scored twice, once under each supplied class bit**
   (one commit-supplied call, one non-commit-supplied call; two separate
   invocations, no check available in either). This dual scoring yields 2K
   item-level observations per class. For each class q ∈
   {commit, non_commit}: Wilson lower bound (95%) of W_q over its 2K
   observations ≥ 0.80, no pooling, invalid structured outputs count as
   failures. Failure → `confounded(within_class_commit)` /
   `confounded(within_class_non_commit)`.
4. **Anti-constant-policy pair predicate.** For untreated pair p, S_p = 1 iff
   the two selected action classes differ. Require S = ΣS_p inside the central
   95% acceptance region of Binomial(K, 0.5): **53 ≤ S ≤ 75 at K = 128**.
   Outside → `confounded(pair_constant_policy)`. **Orientation-neutrality test
   (R7):** among the S switched pairs (S known only at score time), let R be
   the number in the correct orientation (committed on the covering mate,
   withheld on the non-covering mate). R must lie in the central 95%
   acceptance region of **Binomial(S, 0.5)**, computed at score time from the
   realized S by the same pinned central-region procedure used for the
   S-region itself (equal-tail, each tail ≤ 0.025). R above the region →
   `confounded(pair_leak)`; below → `confounded(pair_anticue)`. Correct
   untreated switching is deliberately NOT required — it would demand the
   leakage the design excludes.
5. **Validity gate upstream.** Commitment-wire validity rate gates before any
   band arithmetic; excluded trials never create headroom (grok #5). Inherits
   v1's validity machinery and its cap-truncation lesson.
6. **Leak audit: v1 legs retained, full-render leg added (R6).** v1 §8.6's
   L1 (menu-only) and L2 (task+menu) predictor legs are inherited by
   reference, including their `chance + 0.10` threshold form. v2 adds **L3**:
   a frozen predictor operating on the complete rendered surface (closing
   v1's trigger-features-only audit gap) targeting the hidden scope bit.
   The scope bit is binary, so chance = 0.50 and the L3 threshold is
   **0.60**: predictor accuracy above 0.60 on the frozen suite →
   `confounded(render_leak)`. All three legs run pre-contact on the frozen
   suite; predictor identities and hashes are pinned in the manifest.
7. **Fork identity.** Admission and scored legs share engine, effort, and
   render constants; band-pass does not travel across forks (grok #8).
8. **Irrelevant-stratum admission (R1).** The K irrelevant items carry their
   own predeclared untreated floor: Wilson lower bound (95%) of irrelevant
   accuracy ≥ 0.80 — the stratum must be ordinary competence the engine
   already has, so any treated-lane degradation is attributable tax, not
   noise on an already-hard stratum. There is no ceiling (saturation is
   acceptable here; the stratum measures tax, not headroom). Failure →
   `confounded(irrelevant_band)`.

## §D. Typed outcome vocabulary (extends v1)

`confounded(admission_band)`, `confounded(within_class_commit)`,
`confounded(within_class_non_commit)`, `confounded(pair_constant_policy)`,
`confounded(pair_leak)`, `confounded(pair_anticue)`,
`confounded(render_leak)`, `confounded(irrelevant_band)`,
`confounded(battery_shopping)` — each a close, not
a repair ticket. v1's `confounded(menu_ceiling)` and
`confounded(commitment_invalid_rate)` remain in the family as historical
types.

## §E. Roles and seats (v2 binding)

| Seat | Holder | Constraint |
| --- | --- | --- |
| Author-of-record (spec) | claude/fable-5 | May not cold-review |
| Battery-shape co-author | codex/gpt-5.6-sol | May respond to review findings; may not review |
| Cold reviewer | cursor/glm-5.2 (glm-5.2-max) | No authorship of any sealed instrument |
| Builder | cursor/composer-2.5 | Builds only post-seal; reviews nothing it builds |
| Adversarial clause | cursor/grok-4.5 | Clauses (a)–(g) bind from transcript; budget spent |
| Ruling authority | dan | K, floor, roster, seal, close |

Harness-execution note (dan): calibration/cli runs on the Cursor harness use
glm-5.2-high; review uses glm-5.2-max.

## §F. Seal procedure

Part I seals when: final cold review passes → dan pins the manifest by hand
(v1 discipline: dan-executed pin). Seal hash covers this file, the v2 schema
artifacts, and the derived-band computation. No fixture is authored before
seal; no engine is contacted before the sealed admission gate runs.
