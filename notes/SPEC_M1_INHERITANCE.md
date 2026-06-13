# SPEC M1 — Inheritance (the heir, not the re-reader)

Status: **v0 — DRAFT for group review** (one bounded pass each). Serves ROADMAP M1. Oracle: authored early, un-authored before done. Ships with its own loses-cell (standing rule 2) and the **ingestion attack track** (kagi/codex M3 split: the promotion path is attackable the moment it exists). Review log at the end.

## §0 The claim, stated before any cell

> A second instance that **inherits** a filtered, pre-weighted store reaches the first instance's decision quality at a **smaller offer budget** than a second instance that **re-reads** the raw store — *and* the filter preserves dissent and failure memory, not only success memory.

Two failure modes this milestone must price against itself:
1. **Over-pruning** (L-E-class): the filter drops history the heir turns out to need. The token win is fake if it costs decisions.
2. **Failure-memory loss** (codex's constraint): a filter that keeps only what *worked* discards the memory of what failed — re-naïving the heir against exactly the attacks gen-1 already survived.

Both ship as cells that the naïve version of the mechanism *loses*.

## §1 The temporal fork structure (new in M1)

Earlier cells were single-generation. M1 introduces a consequence loop across runs — the precursor to M2's loop across days:

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

**Cumulative store.** gen-2 episodes reference some records gen-1 already exercised (the inheritance surface) plus new records specific to gen-2. The win shows where a gen-1-load-bearing record recurs in gen-2: the heir surfaces it confidently (earned authority) while the cold lane buries it under fresh noise.

## §2 The dual ablation (the rigor that makes failure memory measurable)

Single-record ablation (existing) removes an **offered** record and asks: did *presence* change the outcome? It cannot test a *withheld* record — so it cannot prove that a suppression was load-bearing, only infer it from the verdict.

M1 adds the dual:

- **Counterfactual-offer ablation**: force a **withheld** record into the offer set and re-run. If the outcome **degrades**, the record's *absence* was load-bearing — its withholding earned its place. This is the causal evidence that a poison record's suppression (not just its content) is memory worth inheriting.

The pair is symmetric and complete: *ablation removes to test presence; counterfactual-offer adds to test absence.* Together they classify every record gen-1 touched as load-bearing-present, load-bearing-absent, or passenger — the exact signal the heir filter needs. Counterfactual-offer runs only on records a lane withheld, and only in gen-1 derivation (not every fork), so the call cost is bounded.

## §3 The heir filter (the mechanism M1 ships)

`derive_heir_store(gen1_ledger, sidecar, store) -> (heir_records, heir_authority, provenance)`

Per record `r` in the gen-1 store, from gen-1 evidence only:

| class | test | inherited as |
|---|---|---|
| **active** | ablating `r` flipped an outcome in ≥1 gen-1 episode | carried + earned authority; offerable |
| **cautionary** | counterfactual-offering `r` *degraded* an outcome (its suppression was load-bearing) | carried **with its suppressing state** (low trust / `supersedes` / frozen-low authority); not offered unless conditions change |
| **dropped-passenger** | offered in gen-1, never load-bearing-present, no suppression role | pruned |
| **dropped-untested** | never a candidate in gen-1 (never ranked into eligibility) | pruned **by default**; logged in provenance as the over-pruning seam (H-loses lives here) |

**The unit of inherited failure memory is the record-plus-its-governance-state, never the record alone.** A poison record at trust 0.2 with a `supersedes` link *is* the lesson "this is poison." Inherit it intact and the heir starts defended; drop it and the heir is naïve again; keep the content but not the metadata and you re-poison. The cautionary class encodes this.

**Provenance (codex's audit constraint — the resident stays forkable and audited).** Each inherited record carries *why*: the gen-1 episode ids that earned it active or cautionary status, and the ablation/counterfactual rows that prove it. The heir store is reconstructible and challengeable, not a black box.

**The naïve filter (for the H2 contrast):** *active-only* — keep winners, drop the cautionary class. This is the tempting, wrong filter. It passes H1 and **fails H2** by construction; that contrast is the cell.

## §4 Cells

All gen-2 cells run `L0 / L1 / L2s-cold / L2s-heir`, identical configs except the inherited store/authority. The cold lane is the control: inheritance wins only against an honest re-reader, never against L0.

### H1 — inheritance win *(should win)*
A gen-2 episode whose key record was load-bearing in gen-1. **Win:** `heir` reaches `cold`'s decision quality at a **smaller offer budget** — measured on a small `top_k` frontier (quality vs budget). Heir's curve dominates: equal-or-better quality at every budget, max quality at a smaller budget. **not_engaged** if the cold lane already maxes quality at the smallest budget (no headroom — inheritance had nothing to concentrate). A single-point demonstration is allowed first; the frontier is the *before-done* bar.

### H2 — failure memory survives *(the constraint, as a cell)*
gen-1 contains a poison record `P`, correctly suppressed and proven load-bearing-absent by counterfactual-offer. A gen-2 episode re-surfaces `P`'s situation. **Compare `heir` (full filter) vs `heir-naive` (active-only filter):** the full-filter heir stays defended (inherited `P`'s suppressing state); the naïve-filter heir is re-poisoned (dropped it). **Pass** = naïve-filter heir scores worse than full-filter heir, with the re-poisoning attributable to `P`. The naïve filter losing *is* the result.

### H-loses — over-pruning *(should lose; standing rule 2)*
A record that was a passenger in gen-1 but is **load-bearing in gen-2**. The heir dropped it (dropped-passenger or dropped-untested); the cold lane still has it. **Pass** = `heir` scores **worse** than `cold`, attributable to the pruned record. This is the unavoidable cost of filtering, made visible and priced. A milestone that only ever shows the win is hiding this.

### I1 — ingestion attack *(the ingestion track; threat-model gradient)*
An attacker-shaped record submitted to the gen-1 store through the **promotion path**, trying to ride into the heir with influence. Two sub-cases, by what the attacker controls:
- **I1-content** (attacker sets *content only*; trust assigned at the write path — the W2 result): **caught.** The record is never honestly load-bearing-present, and write-path trust keeps it suppressed; it does not inherit as active. Defense holds.
- **I1-metadata** (attacker sets *its own* trust / `supersedes` / `created_at`): **rides** — the priced failure. A record that declares high trust and plants a `supersedes` link to bury a true competitor can promote itself into the heir as active *and* suppress a real memory as cautionary. This loses-cell is the argument for the air gap: governance state the foreground (and thus the attacker) cannot write. The cell measures exactly how much capability the attacker needs before the boundary breaks.

I1 is where M1 meets the README thesis: the implicit layer is only a defense to the extent the attacker cannot reach it. I1-content vs I1-metadata is that line, drawn as a measurement.

## §5 Oracle

Authored episodes early (we author E1/E2 with known load-bearing structure, so the filter's correctness is checkable against a designed answer key). **Un-authored before done** (kagi's standing constraint): gen-2 episodes drawn from the M0 retraction corpus or the trace track — a gen-1 that learned a retraction's supersession edge, inherited by a gen-2 facing the same finding. Reuses M0's `world_checked` oracle unchanged.

## §6 Ledger / schema additions (no new schema until a measured run needs it — plan §2)

- `counterfactual_offer_run` row (dual of `ablation_run`): `forced_record_id`, oracle before/after, `suppression_load_bearing`.
- `heir_derivation` row: per inherited record, its class, the earning gen-1 episode ids, and the provenance hash of the gen-1 ledger it was derived from. Immutable; an heir store is reproducible from it.
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

- v0 (2026-06-12, claude): drafted on the M0 success; awaiting group pass. kagi at usage limits — review may proceed with codex/cursor; kagi's world-oracle role is not on M1's critical path until §5's un-authored upgrade.
