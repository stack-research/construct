# SPEC M1 — Inheritance (the heir, not the re-reader)

Status: **v0.2 — REVIEWED** (direction-aware additions endorsed by cursor + codex, 2026-06-13, no blockers; they resolved the I1-metadata harmful-influence question the v0.1 review deferred to dan+claude). Serves ROADMAP M1. Oracle: authored early, **un-authored before done — the §5 gen-2 upgrade is M1's hard close-gate, still owed.** Ships with its own loses-cell (standing rule 2) and the **ingestion attack track**. Review log at the end.

## §0 The claim, stated before any cell

> A second instance that **inherits** a filtered, pre-weighted store reaches the first instance's decision quality at a **smaller offer budget** than a second instance that **re-reads** the raw store — *and* the filter preserves dissent and failure memory, not only success memory.

Two failure modes this milestone must price against itself:
1. **Over-pruning** (L-E-class): the filter drops history the heir turns out to need. The token win is fake if it costs decisions.
2. **Failure-memory loss** (codex's constraint): a filter that keeps only what *worked* discards the memory of what failed — re-naïving the heir against exactly the attacks gen-1 already survived.

Both ship as cells that the naïve version of the mechanism *loses*.

## §1 The temporal fork structure (new in M1)

Earlier cells were single-generation. M1 introduces a consequence loop across **episode generations and branch state** — never agent identity; the resident claim waits for M2 (codex's scope note). The precursor to M2's loop across days:

```
gen-1 run  ──►  derive heir  ──►  gen-2 fork
(episodes E1)   (filter+carry)    (episodes E2, two lanes differing only in store)
```

- **gen-1 run**: ordinary `run_fork_group` on first-generation episodes with a governed lane, producing `ablation_run` rows + an authority sidecar. (Existing machinery.)
- **derive heir**: a pure function over gen-1's ledger + sidecar + store → a *heir store* (subset of records, each carrying its governance state) + provenance. (New; §3.)
- **gen-2 fork**: `run_fork_group` on second-generation episodes with two governed lanes that hold everything constant except the store they inherit:
  - **`L2s-cold`** (the re-reader): full store, neutral authority.
  - **`L2s-heir`** (the heir): heir store, inherited authority + carried links.

Fork identity holds: same engine, params, prompt, renderer, oracle; **only the memory condition differs** — which is exactly the store + authority state. This is legal under the standing rule and is the whole point.

**Cumulative store.** gen-2 episodes reference some records gen-1 already exercised (the inheritance surface) plus new records specific to gen-2. The win shows where a gen-1-important record recurs in gen-2: the heir surfaces it confidently (earned authority) while the cold lane buries it under fresh noise.

## §2 The dual ablation (the rigor that makes failure memory measurable)

Single-record ablation (existing) removes an **offered** record and asks: did *presence* change the outcome? It cannot test a *withheld* record — so it cannot prove that a suppression was important, only infer it from the verdict.

M1 adds the dual:

- **Counterfactual-offer ablation**: force a **withheld** record into the offer set and re-run. If the outcome **degrades**, the record's *absence* was important — its withholding earned its place. This is the causal evidence that a poison record's suppression (not just its content) is memory worth inheriting.

**Fixed-budget substitution (codex blocker, adopted):** the counterfactual run must not change the context budget — otherwise degradation can come from extra context or attention dilution, and "absence was important" becomes an oracle ride-along. Definition: *the forced record replaces the lowest-ranked normally-offered record at the same `top_k` / token budget* (a cell may declare a different replacement rule, disclosed). The ledger row records `forced_record_id`, `replaced_record_id`, the original and forced offer sets, and the oracle delta. On budget-frontier cells the substitution runs at each tested budget. An append-style diagnostic (extra record on top) measures robustness to added context, not suppression causality — if ever needed it is a **different row kind**, never this one.

**Priority filter (cursor):** v1 counterfactual runs target **governance withholdings** (`eligibility_below_threshold`, `superseded_by:*`, frozen/low-authority) — not `below_rank_budget`, unless a cell explicitly makes rank-budget the mechanism. The gate's intended suppressions are the question; rank noise is not. *(v0.2: the exception is declared per-episode via `m1_counterfactual_include_rank_budget: true` — I1-timing uses it, because arrival order moving offer rank IS that cell's mechanism.)*

The pair is symmetric and complete: *ablation removes to test presence; counterfactual-offer substitutes to test absence at the same budget.* Counterfactual-offer runs only in gen-1 derivation (not every fork), so the call cost is bounded.

**Both diagnostics are direction-aware (v0.2, from the I1-metadata deferred question).** `outcome_changed` alone is direction-blind: it cannot distinguish a record whose removal *breaks* a good outcome from one whose removal *fixes* a bad one — harm and help would inherit identically. So `ablation_run` rows carry `baseline_oracle_score`, and the counterfactual rows already carry before/after. Four causal signals result: removal-degrades (helpful presence), removal-improves (harmful presence), forcing-degrades (earned suppression), forcing-improves (harmful suppression — the buried record was the truth).

## §3 The heir filter (the mechanism M1 ships)

`derive_heir_store(gen1_ledger, sidecar, store) -> (heir_records, heir_authority, provenance)`

**Derivation source is pinned (cursor/codex): the v1 source branch is `L2s`** — supersession is on the critical path for the cautionary class. `heir_derivation` names `source_branch`, `source_authority_path`, `source_ledger_hash`, and the filter version; a multi-lane gen-1 run otherwise produces ambiguous heir provenance.

Per record `r` in the gen-1 store, from gen-1 evidence only:

| class | test | inherited as |
|---|---|---|
| **active** | ablating `r` *degraded* an outcome (removal breaks; helpful presence) | carried + earned authority; offerable |
| **indicted** *(v0.2)* | ablating `r` *improved* an outcome (removal fixes; harmful presence), **or transitively**: a record `r` suppressed via `superseded_by:r` was exonerated | carried with **authority clamped to `min(original, 0.1)`** — original preserved in the derivation row. The clamp suppresses at gate 1, so a planted `supersedes` link never reaches gate 3 (gate order is the defense) |
| **cautionary** | counterfactual-offering `r` *degraded* an outcome (its suppression was important) | carried **with its suppressing state** (low trust / `supersedes` / frozen-low authority); not offered unless conditions change |
| **exonerated** *(v0.2)* | counterfactual-offering `r` *improved* an outcome (its suppression was harmful — `r` was the buried truth) | carried + authority as-is; **offerable** (its suppressor is indicted; absent or clamped, the burying link cannot fire) |
| **dropped-passenger** | offered in gen-1, never important either direction, no suppression role | pruned |
| **dropped-untested** | never a candidate in gen-1 (never ranked into eligibility) | pruned **by default**; logged in provenance as the over-pruning seam (H-loses lives here) |

**Precedence on conflicting multi-episode evidence (v0.2): harm dominates help** — `indicted > cautionary > active > exonerated > dropped`. One proven harm outweighs any help (the min() spirit). Single-sample misattribution remains the disclosed limit; exoneration-by-luck is its sharpest edge and is named in every derivation row that uses it.

**Why the indictment lives in authority and not in record fields (the air-gap sentence, mechanized):** a cautionary record's suppression rides in trust/`supersedes` — fields that carry with the record. An I1-metadata attacker *owns* those fields; its suppression must therefore live in the one layer the foreground cannot write — oracle-grounded ablation evidence and the harness-written authority sidecar. The asymmetry between cautionary and indicted is not an implementation detail; it is the thesis.

**The unit of inherited failure memory is the record-plus-its-governance-state, never the record alone.** A poison record at trust 0.2 with a `supersedes` link *is* the lesson "this is poison." Inherit it intact and the heir starts defended; drop it and the heir is naïve again; keep the content but not the metadata and you re-poison. The cautionary class encodes this.

**Provenance (codex's audit constraint — the resident stays forkable and audited).** Each inherited record carries *why*: the gen-1 episode ids that earned it active or cautionary status, and the ablation/counterfactual rows that prove it. The heir store is reconstructible and challengeable, not a black box. `heir_derivation` also emits **`prune_ratio`**, `dropped_passenger_count`, and `dropped_untested_count` (cursor/codex) — on small authored gen-1 stores the prune will be modest and the token win marginal; that is disclosed, not dressed up.

**Authority inheritance is bounded in v1 (codex):** the heir inherits each record's earned authority value as-is, with the original value and the evidence rows that earned it preserved in the derivation row. No aggregation, no rule-level authority. An inherited active record that goes stale in gen-2 is an H-loses variant, never something the filter silently repairs.

**The naïve filter (for the H2 contrast):** *active-only* — keep winners, drop the cautionary class. This is the tempting, wrong filter. It passes H1 and **fails H2** by construction; that contrast is the cell.

## §4 Cells

All gen-2 cells run `L0 / L1 / L2s-cold / L2s-heir`, identical configs except the inherited store/authority. The cold lane is the control: inheritance wins only against an honest re-reader, never against L0.

### H1 — inheritance win *(should win)*
A gen-2 episode whose key record was important in gen-1. **Win:** `heir` reaches `cold`'s decision quality at a **smaller offer budget**. **Primary comparator (codex): total offered tokens (`attention_cost_tokens`)**, with `top_k` as the controlled frontier variable — record both, decide on tokens (a short heir record vs a long cold record makes `top_k` alone misleading). Heir's curve dominates: equal-or-better quality at every budget, max quality at fewer offered tokens. **not_engaged** is first-class (cursor): if the cold lane already maxes quality at the smallest budget there was no headroom and inheritance had nothing to concentrate. A single-point demonstration is allowed first; the frontier is the *before-done* bar.

### H2 — failure memory survives *(the constraint, as a cell)*
gen-1 contains a poison record `P`, correctly suppressed and proven important-absent by counterfactual-offer. A gen-2 episode re-surfaces `P`'s situation. **Lane set (codex's matrix fix): H2 runs `L0 / L1 / L2s-cold / L2s-heir / L2s-heir-naive`** — the only cell with the fifth lane, declared here. **Compare `heir` (full filter) vs `heir-naive` (active-only filter):** the full-filter heir stays defended (inherited `P`'s suppressing state); the naïve-filter heir is re-poisoned (dropped it). **Pass** = naïve-filter heir scores worse than full-filter heir, with the re-poisoning attributable to `P`. The naïve filter losing *is* the result.

### H-loses — over-pruning *(should lose; standing rule 2)*
A record that was a passenger in gen-1 but is **important in gen-2**. The heir dropped it (dropped-passenger or dropped-untested); the cold lane still has it. **Pass** = `heir` scores **worse** than `cold`, attributable to the pruned record. **Authored deliberately (cursor/codex): the episode targets a specific dropped-untested or dropped-passenger record that gen-2 makes important** — a designed seam, not a gotcha from random pruning. This is the unavoidable cost of filtering, made visible and priced. A milestone that only ever shows the win is hiding this.

### I1 — ingestion attack *(the ingestion track; threat-model gradient)*
An attacker-shaped record submitted to the gen-1 store through the **promotion path**, trying to ride into the heir with influence. Three sub-cases on a capability gradient (cursor's middle case, codex's naming — adopted):
- **I1-content** (attacker sets *text only*; write path assigns trust/links/time — the W2 result): **caught.** The record is never honestly important-present, and write-path trust keeps it suppressed; it does not inherit as active. Defense holds.
- **I1-timing** (attacker controls *arrival order / timing-derived `created_at`*, but not trust or links — the realistic middle): tests whether recency and supersession edges are **indirectly writable** through the promotion path. Expected caught if write-path trust holds; **rides if `created_at` alone moves offer rank or yield ordering** — in which case temporal provenance is part of the attack surface and the v1 air-gap line moves.
- **I1-metadata** (attacker sets *its own* trust / `supersedes` / authority-like state): **rides in gen-1** — every foreground-writable defense fails, the truth is buried, the answer is compromised. That ride is the priced failure, measured on the cold lane. **(v0.2 semantics, from the deferred harmful-influence question):** at `top_k=1` the attack's deepest damage is to the *filter's evidence* — the buried truth's counterfactual shows forcing-improves, which direction-blind rules read as "passenger" and **prune the truth from the inheritance**. Direction-aware classes close this: the truth is *exonerated* (inherits offerable), the attacker is *indicted* (transitively, via the exoneration's `superseded_by` reason) and inherits authority-clamped, where gate order keeps its planted link from ever firing. **Verdicts:** `pass` = indictment/exoneration evidence formed in gen-1 AND heir defends (`heir > cold`) while cold stays compromised; `fail` = the attacker inherits as `active` (harm-as-help — the exact bug) or the heir stays compromised despite evidence; `not_engaged` = the attack never bit in gen-1 (nothing to price).

I1 is where M1 meets the README thesis: **the air gap protects exactly the fields the foreground cannot write.** The gradient locates the line instead of asserting it — and I1-metadata now states the line precisely: trust, links, and timing all fall to the attacker; oracle-grounded ablation evidence and the harness-written sidecar do not.

## §5 Oracle

Authored episodes early (we author E1/E2 with known important structure, so the filter's correctness is checkable against a designed answer key). **Un-authored before done** (kagi's standing constraint): gen-2 episodes drawn from the M0 retraction corpus or the trace track — a gen-1 that learned a retraction's supersession edge, inherited by a gen-2 facing the same finding. Reuses M0's `world_checked` oracle unchanged.

## §6 Ledger / schema additions (no new schema until a measured run needs it — plan §2)

- `counterfactual_offer_run` row (dual of `ablation_run`): `forced_record_id`, `replaced_record_id`, original + forced offer sets, oracle before/after, `suppression_load_bearing`. Fixed-budget substitution only (§2); append-style would be a different row kind.
- `heir_derivation` row: per inherited record, its class, the earning gen-1 episode ids, the proving ablation/counterfactual rows, original + inherited authority; plus `source_branch`, `source_authority_path`, `source_ledger_hash`, filter version, `prune_ratio`, `dropped_passenger_count`, `dropped_untested_count`. Immutable; an heir store is reproducible from it.
- `BranchConfig.inherited_record_ids: set[str] | None` (None = full store) — the per-branch store override that makes cold/heir a clean fork. Heir lane also points `authority_path` at the inherited sidecar.
- gen-2 `run_config` discloses `parent_run_id` + `heir_filter` (`full` | `active_only`) so a reader knows which generation and which filter produced the lane.

## §7 Build order

(1) this spec reviewed — one bounded pass each; (2) counterfactual-offer ablation in the runner + `counterfactual_offer_run` rows; (3) `derive_heir_store` + `heir_derivation` rows + provenance; (4) `inherited_record_ids` branch override + gen-2 fork wiring; (5) authored E1/E2 episode pairs for H1/H2/H-loses/I1; (6) `score_h1/h2/h_loses/i1` cell scorers; (7) scored runs across engines; (8) un-authored gen-2 from the M0 corpus before the milestone is called done.

**Delegation note (dan, 2026-06-12):** once this spec is ratified, the authored E1/E2 episode *authoring* (step 5) and scorer wiring against the fixed spec (step 6) are candidates to farm to codex/cursor — mechanical against a frozen design. The heir-filter and dual-ablation mechanisms (steps 2–3) and the ingestion threat model stay dan+claude. Core design is not delegated; busy work against a ratified spec is.

## §8 Review asks (bounded, one pass)

a. **The dual ablation** (§2): is counterfactual-offer the right rigor for failure-memory, or is the inferential proxy (verdict + withholding reason) enough for v1? Cost vs honesty.
b. **The cautionary class** (§3): is "inherit the poison record *with* its suppressing state" the right unit, or should failure memory be a generalized rule (source-trust prior, a pattern) rather than a specific carried record? The latter is stronger but bigger.
c. **H-loses framing** (§4): is over-pruning priced honestly, or does "active + cautionary, drop the rest" already prune so little that the token win is marginal? If the win is marginal, the milestone is weaker than it sounds — say so now.
d. **The ingestion gradient** (§4 I1): is content-only-vs-metadata-capable the right threat-model split, or does the real attacker live in between (e.g., can influence `created_at` via submission timing but not trust)? Where exactly is the air-gap line worth drawing for v1?
e. **Scope**: is anything here M2 (residency) or M1.5 (contribution ledger) wearing an M1 mask? Cut it now (codex's scope discipline).

## Review log

- v0 (2026-06-12, claude): drafted on the M0 success. kagi at usage limits — review proceeded with codex/cursor; kagi's world-oracle role is not on M1's critical path until §5's un-authored upgrade.
- **v0 → v0.1 (2026-06-13, one bounded pass each — cursor, codex; both endorse):**
  1. **Fixed-budget counterfactual substitution** (codex, blocker — adopted): the forced record replaces the lowest-ranked offered record at the same budget; append-style is a different row kind. Without this the diagnostic measures context-budget change and calls it suppression causality.
  2. **Counterfactual priority filter** (cursor): governance withholdings first; `below_rank_budget` excluded unless a cell declares it.
  3. **Derivation source pinned to L2s** (cursor/codex) with `source_branch` / `source_authority_path` / `source_ledger_hash` / filter version in `heir_derivation`.
  4. **I1-timing** added as the realistic middle of the ingestion gradient (cursor; codex's three-way naming). The air gap protects exactly the fields the foreground cannot write; the gradient locates the line.
  5. **H2 lane matrix fixed** (codex): `L2s-heir-naive` declared as H2's fifth lane.
  6. **H1 primary comparator = offered tokens** (codex), `top_k` as frontier variable; `not_engaged` first-class (cursor).
  7. **H-loses authored deliberately** at a designed dropped-record seam (cursor/codex); `prune_ratio` + dropped counts disclosed in derivation (modest prune on small stores disclosed, not dressed up).
  8. **Authority inheritance bounded** (codex): values carried as-is with original + evidence preserved; no aggregation or rule-level authority in v1.
  9. **(b) settled**: cautionary class stays record-plus-state for M1; generalized rules (source-trust priors, patterns) are M1.5/M2 work — may appear as provenance annotation only, never filter input.
  10. Consequence-loop wording tied to episode generations and branch state, not agent identity (codex's scope guard).
- **v0.1 → v0.2 (2026-06-13, claude+dan — resolves the deferred I1-metadata harmful-influence question; PENDING one bounded pass from cursor/codex):**
  1. **Direction-aware diagnostics** (§2): `ablation_run` rows carry `baseline_oracle_score`; four causal signals (removal-degrades/-improves, forcing-degrades/-improves) replace direction-blind `outcome_changed`.
  2. **Two new classes** (§3): `indicted` (harmful presence, direct or transitive via a `superseded_by` exoneration) inherits authority-clamped to 0.1 — gate order keeps its links from firing; `exonerated` (harmful suppression — the buried truth) inherits offerable. Precedence: harm dominates help (`indicted > cautionary > active > exonerated > dropped`).
  3. **The air-gap asymmetry named** (§3): cautionary suppression rides in record fields; indicted suppression must live in oracle-grounded evidence + the harness-written sidecar, because the I1-metadata attacker owns the record fields.
  4. **I1-metadata cell semantics** (§4): the ride is priced on the cold lane; the defense is measured on the heir; `active`-classified attacker is a loud `fail` (harm-as-help).
  5. Driven by codex's wire finding (metadata attacker unmeasurable under oracle-flip `active`) and the discovery that at `top_k=1` the attack's deepest damage is pruning the truth from the inheritance — an attack on the filter's evidence, not on the store.
  - **Bounded pass landed (2026-06-13): cursor + codex both endorse v0.2, no blocker.** Both: authored-oracle leg *reviewable as met*; milestone *not closed* until §5 un-authored gen-2. Non-blocking guardrails: (1) I1-content given the same anti-hollow discipline as timing/metadata — *done* (`score_i1`, both lanes must be correct, attacker-not-active is no longer a hollow pass); (2) *tracked* — I1-timing evidence should tie the exonerated truth's offer-contrast explicitly to the attacker being the crowding record. Disclosed sharp edge (cursor): single-sample exoneration-by-luck; replication across episodes/engines is the cure if it bites.
