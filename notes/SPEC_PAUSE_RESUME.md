# SPEC_PAUSE_RESUME v0.1-draft — the pause/resume frontier instrument (PRF)

Status: v0.1-draft-r3, folded from the `pause-resume-frontier` design event (2026-07-02, rounds 1–4: codex design + D2/D3 proposals; composer implementer validation + build inventory; hermes over-claim blocks on "matched decision quality", the hint_only drift, and the over-wipe corner; gemini reality checks — metabolic-vocabulary retirement, hint_only leak charge, decorative-floor refutation; glm syntheses — D1 opened, warmth-tax catch, fork resolution). Carried from x4-review / ROADMAP §"what lifts out". dan's votes encoded: round-2 (b) conditional-vs-verdict; round-3 items 1–5 (rulebooked-only, hermes floor, gate-independence, tags-as-metadata, (B)→v0.2); round-4 items 1–4 (mint-refusal floor, three hard gates, γ=0.20, AST block). **Spec review round (2026-07-03): hermes PASS-with-notes; codex/composer/gemini/glm BLOCK on one converged row-semantics point — content-floor legs as offer-time `frontier_mint_refused`, §9 as mirror, two-phase-mint ordering pin (fix list A+B+C) — encoded in r2; all four blocks converted. dan sealed 2026-07-03; v0.1 machinery built (commit `6317a55`). Build review (same day, unanimous BLOCK → fixed as r3): the §4c-1 ablation leg was fixture-attested where it must be computed — resolved by gemini's cut (compute the structural half via shared replay at the mint, disclose the empirical-adequacy half as a real-engine debt, delete every masquerade: the episode flag AND the hardcoded row boolean), plus glm's fix list #1–#11 (refusal→cell routing, gate_open scorer enforcement for non-mock, wire-gap emissions, leg-name polarity). §4c-1 rewritten as two legs below.**

## 0. Claim and non-claims

**The claim under test (governed-hint efficiency — never continuity fidelity, never metabolism):**

> For episodes whose pause-time frontier is expressible as **conditional transitions over structural surface tags** with a **population-pinned rulebook**: a witnessed, schema-bound frontier artifact — minted from a closed input set containing no answer lemmas — lets a fresh engine instance reach **adequate continuation** at lower `route_read_tokens` than cold reread of the symmetric post-seam catalog, with answer-cache refused at mint and residual leakage priced by the loses-cells.

**Named circularity (stated, not hidden):** the rulebook part-authors the obligation set that the continuation checkpoint tests. The positive win path is therefore *"reads intersect rulebook-derived obligations under priced world-move guards"* — **not** *"the agent oriented a frontier."* The loses-cells (changed-world, false-continuity, reconstruction-illusion) are what break the circle: they are defined by world movement and catalog topology, not by the rulebook.

**Non-claims:** no engine-internal state is claimed to persist (most harness engines have none; the artifact is a governed hint, and `PRF-reconstruction-illusion` is the computable guard on exactly this); metabolic/thermodynamic language stays in ROADMAP as empirical framing and never enters this spec's claims; no claim about open semantic frontiers, mid-thought pauses, or model-inferred "what matters now" (§11). `PRF-heir-dominates` is a first-class predeclared null: *trace-bookmark inheritance was sufficient; the frontier artifact bought no measurable continuation budget.*

**D1 boundary statement (verbatim-in-intent, load-bearing):** the mint discriminator bounds **overt** leakage (scores, ranks, NL rationales, answer tokens, evaluative labels). It does **not** prevent **covert** leakage through (a) which ids appear where — asymmetric assignment of `live` vs `blocked` *is* a frontier judgment — and (b) micro-conclusions compressed into gate-shaped relation codes. Leakage is **bounded, not zero**; the residual is priced downstream by D2 derivation honesty, the continuation checkpoint, and the loses-cells. We built a restricted prompt template, not an airtight seal.

## 1. Shape — one engine, two-branch fight, warm as witness

- **uninterrupted-warm** — the **witness branch**, never a cost comparator (no seam tax, no witness problem). Emits the authoritative freeze-time frontier trace and the quality **ceiling** (a record of state, not a grader of outcome).
- **cold-reread** — M1 heir + full reread of the symmetric post-seam catalog. The fair-fight comparator.
- **resumable-state** — cold-reread + the harness-minted frontier artifact, token-charged on **every** resume (§7).
- **trace-bookmark** — degraded treatment (witnessed pointer + read manifest, no frontier content): the **heir-dominates null branch**, never a competitor.

The cost fight is **cold-reread vs resumable-state** under identical resume prompt and symmetric post-seam catalog. The **witness invariant** (un-backdatable ordering) enters as infrastructure: here it blocks post-hoc *frontier* selection — choosing the seam because the scratchpad looks useful, or describing the paused frontier after seeing what resumed well.

**Ledger writer is external throughout.** The harness derives, mints, emits, and recomputes; the agent under test never steers the offer, the obligations, the reopen verdict, or any cost total. Lineage is immutable; forgetting is eviction-to-cold; no delete verb.

## 2. Event ordering (canonical, witness-stamped, refuse-on-prose)

`population_precommit` → `frontier_freeze` (freeze-time structural mint phase: §4b 13 checks + `state_content_void`) → seam → *world/frontier may move* → `post_seam_catalog_materialized` (symmetric: all post-seam public surfaces enter the shared catalog for ALL branches) → **offer-time content floor** (§4c-1/§4c-2; the second mint phase — `frontier_state_minted` or `frontier_mint_refused` is authoritatively emitted HERE) → resume routes → `continuation_checkpoint_reached`.

`population_precommit` pins: `frontier_schema_hash`, `obligation_rulebook_hash`, `predicate_library_hash`, `surface_tag_schema_hash`, `relation_code_enum_hash`, `canonicalization_schema_hash`, `population_reopen_rules_hash`, `continuation_step_id` derivation, `derivation_mode` (always `rulebooked` in v0.1), γ (§4c), and the fixture legs of §9. Post-hoc prose is the disqualifying shape.

## 3. `frontier_freeze` (own section — the graduated witness invariant)

The freeze binds: the allowed state **form** (schema), the read manifest, the live option set, discard/reopen rules, and the `continuation_step_id` hash. **Derivation function + schema are precommitted at population; content is witnessed at freeze** — content cannot be bound earlier because it is generated by pre-seam reads, and that is the correct discipline, not a flaw. The derivation is **single-path per freeze schema**: no alternate "current-frontier field" escape hatch after routes are seen. The `frontier_freeze` row cites `obligation_set_hash` (§5), never hand-authored obligation prose. If a relation tuple cannot cite the exact pre-seam read row(s) and rule id that emitted it, it is illegal.

## 4. The frontier artifact — D1 mint discriminator

**Three-way state split (the instrument lives in the middle):** *trace bookmark* (pointer + manifest — heir-dominates null) / **frontier state** (live/inactive options, pending obligations, discard/reopen rules, structural uncertainty — the branch) / *work product* (conclusions, drafts, rankings — banned; answer-cache refused at mint, not audited post-hoc).

### 4a. Closed vocabularies (pinned in `freeze_manifest` at population)

`option_ids` (opaque: `A`, `B` — never `refund_is_void`) · `surface_ids` · `obligation_ids` (content-addressed, §5) · `relation_codes` (closed appendix enum, ~6–8, **no population extension** — class-constrained extension is prose review in a structural trenchcoat) · `uncertainty_codes` (structural only: `unresolved`, `needs_check`, `conflict_unread`; no probabilities, confidence, priority, rationale) · `allowed_fields` / `forbidden_field_names` (`best_option`, `option_rank`, `confidence`, `draft_answer`, `summary`, `next_step`, `reason`, …).

**Conditional-transition-vs-verdict rule (adopted; dan + codex concur):** a relation code is legal iff its semantics is a **conditional transition whose firing is determined by post-seam catalog/world state** (`discard_if_world_key_changed`, `reopen_if_catalog_match`), never a **verdict whose truth is fixed at freeze**. `superseded_by_surface` and `factually_refuted` are OUT of the v0.1 enum. Each code's population-time spec names its firing condition as a closed predicate over catalog/world keys. Not "no evaluation" — *"no evaluation that the freeze gets to settle."*

### 4b. The 13-check mint validator (`mint_frontier_state.py`)

`schema_pinned` · `input_closure` (mint inputs = `{route_reads@freeze, m1_sidecar@freeze, freeze_manifest, derive_live_obligations_id}`; no work product, answer text, scored-trace fields, narration; extra kwargs → refuse) · `field_allowlist` · `vocab_closure` (depth-first; every scalar ∈ closed vocabularies) · `opaque_id_format` (ids match pinned pattern; no status-lemma or prose-token ids) · `relation_code_class` (manifest-pinned class ∈ {identity, topology, obligation, discard, reopen}; evaluation/preference/confidence/answer/rationale → refuse) · `no_natural_language` · `no_scalar_valuation` · `no_total_order` (lists are unordered sets, canonicalized sort-by-id before hash) · `partition_consistency` · `ref_integrity` · `gate_relation_shape` (no free-text `reason` key) · `canonical_hash` (`state_digest`; `state_tokens` logged, recomputed at score).

Failure → `frontier_mint_refused` row (`check`, `reason ∈ {work_product_field, out_of_vocab_token, state_content_void, …}`, `frontier_schema_hash`); the branch never resumes. Score-time re-check is demotion-only. **The freeze-time structural pass alone does not mint** — `frontier_state_minted` is emitted only after the offer-time content floor also clears (§4c).

### 4c. Content floor (D3 repair — `frontier_mint_refused` legs, dan round-4 votes 1–3)

The over-wipe corner: a near-empty artifact drives `A → 0` (§7) and honest-reopen wins on rounding — unfalsifiability returning. Repair (all three are v0.1 **hard gates**; a floor satisfiable by decoration is not a floor):

1. **Ablation — split into two legs (build review, 2026-07-03; the earlier "harness measures adequate quality" phrasing was an over-claim the mock layer cannot honor):**
   - **Leg 1 — structural dependency (computed, v0.1 hard gate).** Withholding the obligation-covered surfaces from the witness route must **change** the derived obligation batch (`obligation_set_hash` mismatch, shared replay in `prf_ablation.py` used by mint and gate alike). Unchanged batch = ghost rules = decorative → **`frontier_mint_refused(reason = fixture_obligations_decorative)`; the branch never resumes.** This is what the harness actually proves in v0.1.
   - **Leg 2 — empirical adequacy (disclosed real-engine debt, mock-bypassed).** Whether the witness's downstream continuation quality actually degrades without those reads is model-dependent and cannot be computed at the mock layer. v0.1 mock conservatively assumes the ablated witness is inadequate (never refuses on this leg) and discloses so in `run_config`. The leg lifts to a computed check only under the §6 determinism policy with a real engine + live oracle; until then **no minted row claims adequacy** (the `content_floor` carries the computed hash pair, never a causality boolean). Cross-reference §6 determinism debt and §11.
2. **Token ballast ratio** — `Σ tokens(derived_obligations) ≥ γ · cold_reread_tokens`, **γ = 0.20**, pinned at `population_precommit`, named in the spec appendix; re-pinning γ is a fixture-class re-derivation, never a calibration. Failure → **`frontier_mint_refused(reason = obligation_ballast_below_gamma)`; the branch never resumes.**
3. **Strict invalidation engagement** (assessed at reopen, §7 — branch behavior after the offer, not artifact content) — a valid `frontier_stale_reopen` requires the `invalidating_surface_ids` to be surfaces the branch **actually read** before the reopen row, evaluating true under the invalidation predicate. Reflexive reopen (zero reads / unrelated reads) → `reopen_unjustified`, scored `false_continuity` if it then undercuts cold's checkpoint cost.

**Offer-time placement (implementer timing, review round):** legs 1–2 cannot fire at pre-seam `frontier_freeze` — ablation needs a post-seam witness simulation; ballast needs `cold_reread_tokens` to the same `continuation_step_id`, which requires the symmetric post-seam catalog. They are evaluated at **frontier-state offer time**: after `post_seam_catalog_materialized`, before any resumable-branch post-seam read. Failures emit `frontier_mint_refused`; the resumable branch is never offered the artifact and never resumes.

**Two-phase mint, row-ordering pin:** the mint is two-phase — freeze-time structural (§4b's 13 checks + `state_content_void` when `planned_obligation_count = 0`) and offer-time content floor (legs 1–2). `frontier_state_minted` is authoritatively emitted **only after both phases pass**, at offer time; the freeze-time structural pass alone does not mint. An offer-time failure emits `frontier_mint_refused` and **no** `frontier_state_minted` for that fork — the two rows are mutually exclusive per fork, and the ledger can never carry a minted row that a later refusal contradicts. The event ordering in §2 shows the offer-time gate explicitly.

`planned_obligation_count = 0` → `frontier_mint_refused(state_content_void)` at freeze-time. All content-floor failures are mint refusals, **never** `gate_open` legs — an honorary artifact can never enter the win path and be demoted later via `comparator_incapable`.

## 5. D2 — `derive_live_obligations` (rulebooked-only)

**Scope ruling (dan, round 3):** v0.1 is **rulebooked-only**. `hint_only` is dropped — episodes that do not fit the grammar are **out of scope**, not a second lane. `derivation_mode` is declared at `population_precommit` and is always `rulebooked`. **Surface tags are catalog metadata (or deterministic extractor output recorded with the surface at population), never model-extracted at read time** — a model-extracted tag makes the rulebook+extractor a hidden second author and breaks replay; that episode is v0.2, not v0.1.

```text
derive_live_obligations(population_contract_hash, freeze_manifest,
                        pre_seam_read_rows, seam_id) -> obligation_derivation_batch
```

**Inputs closed at population:** `option_ids`; `surface_schema` (tags as above); `obligation_rulebook` — closed rule list, each `{rule_id, trigger_predicate_id, emits_relation_code, emits_obligation_type, satisfaction_predicate_id, option_id_binding}`; `relation_code_enum` (§4a, conditional-transition-only); `canonicalization_schema`. **No** branch route plan, answer text, post-seam branch reads, free-form rationale, "current best option."

**Application at freeze:** only `surface_read` rows with timestamps before the seam and content hashes matching the population catalog; rulebook runs once in canonical order over the witnessed read set. The minter does not choose salience — it receives the derived batch, intersects with D1 legal fields, and mints or refuses.

**Content-addressed obligations (no prior document hash → a provenance hash):**

```text
obligation_id = sha256(schema_version, episode_id, seam_id, rule_id, option_id,
                       relation_code, obligation_type, canonical(source_read_ids),
                       canonical(source_read_hashes), canonical(match_key_ids),
                       satisfaction_predicate_id)
```

Reproducible: same pre-seam reads + same rulebook → same id. No source reads + no rule id + no satisfaction predicate = authored, refused. Rows: `obligation_derivation_batch` (`obligation_set_hash`, sorted ids, `derivation_inputs_hash`) + one `live_obligation_derived` per obligation (rule_id, option_id, relation_code, obligation_type, source_read_ids/hashes, source_surface_tags, match_key_ids, satisfaction_predicate_id, status_at_freeze) + `obligation_derivation_refused` on provenance failure. Every `frontier_state` relation tuple carries `derived_from_obligation_id` ∈ batch (D1 says the vocabulary is cold; **D2 says the placement of ids in that vocabulary was earned**). The check is never "does this relation make semantic sense" — it is "can I replay the derivation from witnessed rows and get the same tuple."

**Second-author guards (the rulebook is the residual author seat):** `rulebook_genealogy_ok` (predicate literals + tag names swept for status vocabulary / answer lemmas / outcome-encoding names) · `rulebook_route_independence` **verdicting against the witness trace** (gate-independence sharpening: refuse fixtures where the only obligations that fire are on surfaces the witness never read — "the rulebook didn't author the frontier by construction" as a computed check, not a design promise) · tags assigned in the catalog at population · D2 constraint on ids: the population schema template holds obligation text with id slots; it cannot mint `O2 = "verify C is now correct"`.

**Predicate AST (closed; `predicate_ast.py`, fail-closed on unknown nodes, library hash-pinned):**

- *Fields:* `surface_id, surface_hash_t0, surface_hash_t1, surface_text_changed (derived), surface_tag, surface_kind, certificate_eligible, option_id, option_status, obligation_id, obligation_kind (read|verify|reopen|discard|continue), obligation_status (pending|satisfied|invalidated), match_key_id (AST name; resolves to the population vocabulary string), catalog_key (alias-class of status_key; a rule uses one, not both), status_key, status_value_t0/t1 (catalog metadata only), seam_id, timestamp (witness_read context only), continuation_step_id, frontier_artifact_id/hash, reopen_rule_id, world_leg, catalog_epoch, relation_code` — plus the `witness_read` evaluation context `{surface_id, surface_tags[], read_index}` with unary trigger `read_has_tag(tag)`.
- *Operators:* `eq, neq, in, not_in, exists, not_exists, and, or, not, changed(surface_hash_t0, surface_hash_t1)`.
- *Excluded (v0.1):* substring/regex over body text, semantic entity extraction, answer fields, branch route references, read-order win conditions, token counts, model-produced tags.

## 6. Oracle — ceiling + floor (no "matched decision quality")

The phrase "matched decision quality" is removed: it assumed commensurability the branches don't have (cold can match by rereading everything; warm by never pausing). Two irreducibles:

- **Quality ceiling** — the witness branch's freeze-time frontier trace: a *record of state*, never a grader of outcome.
- **Quality floor / engagement** — the branch produced a continuation **adequate by obligation coverage**, not *equivalent* to the warm route: `continuation_checkpoint_reached` is a **harness-emitted row** at the first prefix whose cumulative harness `surface_read` rows satisfy the `satisfaction_predicate` of every pending obligation (against the post-seam catalog) **or** the branch emitted a valid `frontier_stale_reopen` per precommitted discard rules. Inputs are branch-blind (freeze + post-seam catalog); no route plan, no answer text. Cost is compared **at the checkpoint**, never at final answer — otherwise cold wins by rereading everything and we measure latency theater.

**Replay (X2 discipline, transfers whole):** logged cost untrusted. `derivation_replay_ok` (re-derive → `obligation_set_hash` match, else cost cells `confounded`) · `frontier_derivation_parity` (minted tuples ⊆ replayed batch) · `continuation_obligation_intersection` · `route_replay_ok` (cumulative tokens recomputed from canonical surface text + ordered harness `surface_read` rows; engine narration is audit at most; mismatch → `confounded`). **Determinism debt (inherited from WB §6/M2, explicit):** wire tests on `mock`; first real-engine scoring needs frozen prefix plans with deterministic surface injection or a disclosed multi-sample floor at the competing prefix. `resumable_saves_over_cold` is never emitted on one draw.

## 7. D3 — the reopen warmth tax

**Principle:** `frontier_stale_reopen` forgives wrong continuity; it does not forgive the cost of having carried stale warmth. Without this, resumable-state is unfalsifiable — it wins when continuity works and pays nothing when it doesn't.

```text
resumable_cost_to_checkpoint = A + P + R
  A = frontier_artifact_tokens      (recomputed from canonical state at state_digest;
                                     charged on EVERY resume — the artifact was branch
                                     input at the seam; it cannot be free)
  P = pre_reopen_surface_read_tokens (ordered surface_read rows before the reopen row)
  R = post_reopen_surface_read_tokens_to_continuation_checkpoint
cold_cost_to_checkpoint = C          (cold reads to the same continuation_step_id)
```

No fixed carry fee (tunable theater); optional `governance_steps: 1` audit-only. Assessment at the continuation checkpoint — reopen is a route event folded into the checkpoint race, never a local reward or penalty.

**`frontier_stale_reopen` row (build contract):** `kind`, branch, fork_group_id, seam_id, `frontier_artifact_id/hash`, `frontier_state_minted_ref {state_digest, frontier_artifact_id}`, `reopen_rule_id`, `population_reopen_rules_hash`, `reopen_reason ∈ {changed_world, stale_frontier, rulebook_obligation_invalidated}` (mapped mechanically: `discard_if_world_key_changed` fired / option-topology rule fired / satisfaction predicate false at t1), `invalidating_surface_ids`, `invalidated_obligation_ids`, `obligation_set_hash`, `read_index_at_reopen`, `continuation_step_id`. Valid only if rule + predicate + reason enum were population-pinned and the invalidation is mechanically derivable from the post-seam catalog. Prose "looks stale" is ignored.

**Fail-closed:** missing pinned rule → `reopen_unreplayable` (confounded) · invalidating surface not in the symmetric catalog → `catalog_asymmetry` (confounded) · invalidation not derivable, or engagement leg (§4c-3) unmet → `reopen_unjustified` (scored `false_continuity` if the path undercut cold) · claimed totals mismatching recompute → `route_replay_ok=false`.

**Three regions (provable iff the §4c floor ships; drop the floor and D3 reverts to the round-1 hole):**

- **wins** — `A + P + R < C` at the quality floor: obligation-targeted reread beat the cold sweep (this is the governed-hint claim on the reopen path).
- **null** — `A + P + R ≥ C`, quality fine: honest reopen that didn't pay for its stale carry. Immediate reopen (`P=0, R≈C`) → `A + C > C` — provably null whenever `A > 0`. *Starting fresh was correct* is the null region, never a loses-cell.
- **loses** — false continuity / invalid reopen / replay failure: quality floor fails on a path that was cheaper (gate `false_continuity_not_priced` requires `F + A < C`, else the cell is decorative).

## 8. Cells

| cell | shape | axis |
|---|---|---|
| `PRF-frontier-win` | resumable-state reaches the checkpoint at `A + reads < C`, floor holds, all guards green. **Only positive close shape.** | cost/state |
| `PRF-reopen-win` | valid reopen; obligation-targeted reread beats cold after paying `A + P`. Win path, not a loses-cell — copying WB would have treated reopen as failure. | cost/state |
| `PRF-changed-world` / `false-continuity` | world moved a pinned key; branch continues through the stale obligation on a cheaper path → quality lose, priced (`F + A < C` gated). | guard |
| `PRF-stale-frontier` | option set moved (surface reopens/retires an option under a pinned match rule; world fact may be unchanged — **distinct invalidation path**, never the changed-world packet reused); branch continues on a ruled-out option. | guard |
| `PRF-answer-cache` | banned work-product field → `frontier_mint_refused` at mint. Never a scored run. | guard |
| `PRF-reconstruction-illusion` | resumable-state indistinguishable from cold-reread-with-a-good-summary (no derivation provenance / no obligation intersection advantage). Guards the non-claim in §0. | guard |
| `PRF-over-wipe` | artifact degenerates to trace bookmark → `state_content_void` at mint, or cold matches at ≤ cost. | null |
| `PRF-heir-dominates` | trace-bookmark/M1 inheritance matches continuation at ≤ cost — **the honest null.** | cost/state |
| `PRF-reopen-null` | honest reopen, `A + P + R ≥ C`. Disclosed, not a loss. | cost/state |

## 9. Admission gate — `check_prf_fixture.py` (a deliverable BESIDE this spec, computed, never attested)

Legs (each a computed row; `gate_open` required by the scorer before any non-mock evidence): `surface_tags_closed` · `predicate_closure` · `rulebook_genealogy_ok` · `rulebook_route_independence` (witness-trace verdicts) · `derivation_nontrivial` (dry-run derivation strictly richer than M1 sidecar alone, else `comparator_incapable`) · **ablation-structural-dependency mirror** and **ballast-γ mirror** (preflight re-execution of the §4c-1-leg-1/§4c-2 offer-time mint checks on the authored fixture via the SAME shared functions — these must **agree with** the mint-refusal semantics, never substitute for them: the gate refuses any fixture the offer-time minter would refuse, and a mismatch between gate and mint is a harness bug; the adequacy half is the disclosed leg-2 debt, never a gate leg or a fixture flag) · `witness_coverage` (no ghost rules) · **`invalidation_path_separation`** (changed-world and stale-frontier declare disjoint `trigger_predicate_id` sets and disjoint `reopen_reason` mappings — if they share one packet/predicate, one cell is decorative) · `resume_cost_ballast` (cold path must exceed a minimum `route_read_tokens` at the checkpoint, else `not_engaged`) · `false_continuity_not_priced` (§7) · per-engine ignorance probe before fork (X2 world-mode cousin; no asserted foresight) · **hermes floor**: every fork group includes ≥1 population-pinned, tagged, rulebooked episode with a **non-trivially gappy witness trace** and a **winner that is not the first `option_id` alphabetically** — the standing evidence that predicate-over-tags is a real class, not a friendly fixture.

## 10. Deliverables (composer's build inventory — the spec names these directly)

**Harness:** `mint_frontier_state.py` (D1) · `derive_live_obligations.py` (D2) · `predicate_ast.py` · `check_prf_fixture.py` (§9) · `run_prf.py` (fork runner: branches, seam ordering, `surface_read` + `frontier_stale_reopen` + `continuation_checkpoint_reached` emission) · `score_prf.py` (replay legs, D3 tax, cells).
**Tests:** `test_prf_mint.py` (golden allowed/refused states) · `test_prf_derive.py` (replay, content-addressing) · `test_prf_predicate_ast.py` (closure refusals) · `test_prf_d3_reopen.py` (null on honest reopen / win on targeted reread / lose on false-continuity) · `test_prf_fixture_gate.py`.
**Fixtures:** `episodes/prf/` — ≥1 fork group meeting the hermes floor; changed-world packet; stale-frontier packet (distinct invalidation paths); population sidecars (rulebook, predicate library, tag schema, reopen rules, freeze manifest).
**Ledger row kinds:** `population_precommit` (PRF extensions) · `frontier_freeze` · `obligation_derivation_batch` · `live_obligation_derived` · `obligation_derivation_refused` · `frontier_state_minted` · `frontier_mint_refused` · `surface_read` (branch, fork_group_id, seam_id, read_index, surface_id, catalog_epoch, content_hash, surface_tags; `route_read_tokens` optional-logged, always recomputed) · `frontier_stale_reopen` · `continuation_checkpoint_reached` · `gate_open` · `cell_verdict`. Row-kind key is `kind` (ledger convention), not `row_type`.
**Make targets:** `prf-test` (wire) · `prf-gate` · `prf-smoke` (mock-engine fork).

## 11. Scope and v0.2 debts (D4 — non-claims, explicit)

- **Precommitted seams only.** Arbitrary mid-thought interruption cannot produce a schema-bound witnessed freeze; scoring it honestly is impossible in this design. It is a **scope line, not a flaw**: carried as a v0.2 engagement debt, never answered by loosening the freeze.
- **Open-semantic frontiers** — out of scope (would make the derivation function a second frontier author). v0.2 debt.
- **(B) the agent-authored resume note** (gemini) — a *different instrument* measuring agent self-compaction, not governed memory architecture. Carried as a named v0.2 debt with its tensions recorded for resolution there: it violates **ledger-writer-external** (the agent authors its own memory offer — R2, present ≠ authorized) and its anti-caching guard is post-hoc content NLP (**R5**). Not a v0.1 replacement.
- **v0.2 transfer contract (gemini's four conditions — when v0.1 results count as evidence toward anything production-shaped):** (1) *representational isomorphism* — an agent-authored note must function as a frontier of remaining obligations, not a summary/answer cache; (2) *agent-as-compiler* — the read-history→obligations mapping (v0.1's rulebook) must be demonstrable as a model capability; (3) *semantic invalidation equivalence* — model-side change detection must approach the AST's fidelity or the priced-reopen guarantees collapse; (4) *information density* — derived obligations must stay a small fraction of cold-reread cost, or the warmth tax always exceeds the saving in production.
- **No shared verdict with the warming budget.** Adjacent instruments, separate closes. WB's certificate-parity comparator does **not** transfer: frontier parity is a shape of attention, not a hash — the parity object here is derived obligations (§5), the spec's hardest item, named as such.

## 12. Close discipline

Any close goes through `check_close.py` (a `prf` close rule per SPEC_CLOSE_GATE v0.1, wired **before** the first close attempt). Build order: harness modules + mock wire tests → `check_prf_fixture` green on authored fixtures → real-engine run under the §6 determinism policy → cells. Wire tests never promote a cell. The room's block-or-pass on this draft precedes any build beyond golden-case wire tests.

---

# Part II — v0.2-draft: SBR + ECAC (the behavioral regime)

Status: v0.2-draft-r2, folded from the engine-chosen-routes design round and the pre-draft round (2026-07-03; thread `pause-resume-frontier`). dan's rulings encoded: V1 = behavioral (SBR+ECAC — "does the engine genuinely manage tokens when driving, not just following rails"); V2 = cognitive-temptation fixture first, hermes's causal-reduction carried as experiment 2; glm's two flagged overrides acknowledged (static C_max; authored self-falsification fixtures). Drafted against glm's ten-item must-not-lose contract. **Review round (2026-07-03): five narrow verdicts, one converged fix list, encoded in r2 — `quality_threshold`=1.0 pinned (§16, codex); cells renamed to cost-only vocabulary (§21, hermes — disposition words never in machine-computed cell names); neutral-frontier band pinned at 0 over effective cost including `a_i` with `a_i(cold)=0` (§20, gemini + glm's inversion guard); `engine.py` multi-turn channel named as builder debt (§24, composer). glm's audit: no Part I/II contradiction, ten-item contract intact after fixes. Nothing in Part II builds until dan seals. v0.2 extends v0.1; it never invalidates it** — Part I remains the valid deterministic instrument, and the scorer runs dual-path on `instrument_version` pinned at `population_precommit`.

## 13. The v0.2 claim — and its prohibitions

**The question (dan's V1):** does a resumed frontier state suppress context-seeking when the engine is *driving* — choosing what to read and when to stop over a symmetric catalog — measured as expected cost to adequate continuation?

**Claim-language prohibitions (hermes's blocks, carried as prohibitions on what any v0.2 result may say — distinct from the computed guards in §15–§20, and never collapsed into them):**
- **The win channel is cost, never disposition.** ECAC licenses "the resumable branch's reads cost more/less to reach adequate continuation," never "the engine believed/intended/preferred X." The read *distribution* is never itself a win condition (R5).
- **No agency or governance credit from ordering.** Menu-reordering shapes are WB routing hints by definition (design round, unanimous); v0.2 makes no such claim because it builds no such shape.
- **No behavioral claim from the deterministic regime, ever** (§14). No cross-regime rigor citation: Regime-D machinery soundness is never evidence for Regime-S behavioral findings, and vice versa.
- **Suppression is a distributional property.** A single draw is never "suppression"; only dispersion-gated Regime-S rates and means license the word.

## 14. Two regimes, one instrument

| | Regime D (deterministic) | Regime S (stochastic) |
|---|---|---|
| params | temp=0, N=1 | temp in a precommitted range (e.g. [0.3, 0.7]); seed recorded, or `seed: unavailable` stated — never silently omitted |
| purpose | wire validation; v0.1 compatibility bridge | the behavioral experiment |
| win predicate | point-ECAC (collapses to Part I's `A+P+R<C` tree when routes match the v0.1 skeleton) | mean-ECAC (§17) |
| claims licensed | machinery only; `single_draw_disclosed` | behavioral, iff dispersion-gated |

`run_config` records the regime; the win predicate is regime-conditional in the scorer, not in prose.

## 15. The SBR loop (Symmetric Bounded Retrieval)

The two-phase mint (Part I §4) sits unchanged in front of the loop: no artifact is offered except through `frontier_freeze` → offer-time content floor → `frontier_state_minted`. Everything after the mint is new.

- **Presentation:** each branch receives its foreground (resumable: the canonical frontier state as a matter-of-fact record; cold: none) plus the flat symmetric **catalog list** — ids and neutral titles only, 10–15 surfaces, no grouping, one deterministic sort rule so every surface (above all the discriminator) sits at the **same physical index on both branches**.
- **Action space:** exactly `READ(surface_id)` and `STOP`, as **structured actions** (tool JSON / constrained grammar) — never parsed from free completion text. The harness intercepts, validates, fetches canonical text, ledgers, injects, decrements. Illegal actions are refused and ledgered; the engine never fetches.
- **Session end:** legal `STOP`; or `forced_stop` with `stop_reason ∈ {budget_exhausted, max_steps}` — budget exhaustion is recomputed from canonical reads + action overhead, never from logged totals.
- **Ledger rows (harness-emitted):** `sbr_session` (branch, session_id, sample_index, catalog_hash, action_space_hash, budgets) · `affordance_presented` (one per visible surface per session) · `route_decision` (one per step: action, surface_id?, step index) · `surface_read` (post-legal-READ only; gains session_id/step/sample_index) · `forced_stop`. **`route_session` (realized route, skip set) is scorer-derived, never runner-trusted**; the skip set is computed as `visible \ read` — materialized, not inferred. Scorer checks: `affordance_materialized`, `skip_computable`, `decision_read_chain_ok` (bijection step→read), `route_replay_ok`.
- Deleted from the hot path: pre-emitted `surface_read` routes, `injected_route`, answer-only redraws over a fixed offered batch.

## 16. ECAC — expected cost to adequate continuation

Per draw *i*: `effective_cost_i = read_cost_i + a_i` if `quality_ok_i`, else `c_max` — where `read_cost_i` is recomputed from canonical text over the session's ledgered reads, and `a_i` is the rendered frontier-artifact tokens: `a_i(resumable)` = the canonical artifact tokens, **`a_i(cold) = 0`** (the Part I warmth tax survives **as accounting inside ECAC**, never as an independent win predicate). **`quality_ok_i := authored_oracle_score_i ≥ quality_threshold`, with `quality_threshold = 1.0` pinned at `population_precommit` for the cognitive-temptation baseline** (review-round pin, codex/gemini). Win: `mean_eff(resumable) < mean_eff(cold)` in Regime S; point comparison in Regime D.

- **C_max (static, glm's C2d ruling, dan-acknowledged):** `c_max = max_read_tokens + max_steps × action_overhead_tokens` — the **budget supremum**, pinned at `population_precommit`, with the binding-budget precondition `max_read_tokens < Σ visible surface tokens` (the engine faces a real read-vs-stop tradeoff, or the fixture is refused). Scorer-recomputed (`c_max_replay_ok`); mismatch → `confounded`. Any re-pin is a fixture-class re-derivation.
- **Named modeling assumption (never buried in the formula):** a quality failure is priced as if the session exhausted its budget without adequate continuation — "we do not care what a failure spent; we care that it failed." The §20 loses-cells are this assumption's falsifiers.
- **Adequacy is discriminator-oracle, not checkpoint** — a deliberate, named split from Part I §6 (the obligation-intersection checkpoint survives only in the v0.1 compatibility path). Adequacy keys on continuation content against the fresh world state; the oracle key is explicit and machine-checked, **never the surface title, never prose**.

## 17. The Regime-S sampling contract

Precommitted before any run: temperature (from the pinned range), seed handling, K (dispersion probe draws, K≥5), the N-derivation rule, and the statistic. Then:

1. **Dispersion probe (load-bearing):** K pilot draws on the baseline branch. `unique_realizations == 1` → the runner emits `zero_dispersion_regime`, downgrades to point-mode, and **refuses to score a behavioral win** — the API-jitter masquerade dies at the verdict layer. `unique_realizations` is recorded in `run_config` on every Regime-S run.
2. **N from pilot variance,** targeting a precommitted CI on `mean_eff(cold) − mean_eff(resumable)` — never N=10 by fiat.
3. **Statistic:** mean-ECAC is primary. False-continuation rate and CIs are diagnostic — reported, never the win predicate. Stochastic dominance is excluded as a primary statistic (R5 ride-along without its own loses-cell).

## 18. `false_continuation` — the computed event

`false_continuation_i` is true iff, in draw *i*: the discriminator surface was visible in the catalog (`affordance_presented`) ∧ it was not read before the terminal action ∧ the continuation was not adequate ∧ the failure mode matches stale-summary continuation under the **oracle key** (content-matched against the stale state, never prose, never the title). `STOP` before the discriminator is **not** automatically false continuation — it is the event only where the discriminator is the predeclared exclusive discriminator for adequacy. Branch-blind, computed, fail-closed.

## 19. The cognitive-temptation fixture (dan's V2) + symmetry guards

- **Shape:** flat catalog (§15); the discriminator is an ordinary status surface with a neutral title (`S1: Plan R Status Note` grammar — `s1_not_theatrical`); ballast surfaces use parallel title grammar; the stale summary in the resumable foreground is a **matter-of-fact record** ("Plan R closed on <date>"), never an imperative ("do not read further") — an instructed skip is authored, not tempted. **The only asymmetry between branches is the stale-summary foreground.** Availability, title, physical index, read cost, and content hash of every surface are branch-symmetric.
- **Fixture gate legs (extend `check_prf_fixture.py`):** `discriminator_symmetric` · `stale_only_asymmetry` · `catalog_flat` · `title_grammar_parallel` · `c_max_derivation_mirror` · `s1_not_theatrical` · binding-budget precondition (§16).
- **`affordance_symmetry_ok` (glm's C2f ruling — both layers):** the population-level symmetry (catalog_hash, action_space_hash, sort rule, budgets, discriminator visibility/legality, title grammar) is **static-gated** pre-execution; a **thin runtime guard** confirms realized `affordance_presented` rows and the session's `catalog_hash` match the gated population (catches foreground-injection drift a static gate misses). Failure at either layer → `confounded`, never a behavioral loss. The stale summary alters foreground only, never catalog hashes.
- Mock `oracle` booleans remain legal for wire runs and **forbidden** for real-engine adequacy.

## 20. Measurement-regime loses-cells (scored, fail-closed, authored)

Two **population-precommitted authored fixtures** (glm's C2e ruling, dan-acknowledged: shared base + declared overrides on `discriminator_surface_id` / stale-summary presence; each variant passes the full fixture gate itself; runtime perturbation is refused — variants must not escape the gate):

- **`ballast-discriminator`:** same SBR geometry, but the named discriminator is ballast — reading it is unnecessary for adequacy. Expected as a **scored `cell_verdict`**: the ECAC win must NOT fire for resumable; `false_continuation` false or `not_engaged`. If the win fires, the instrument failed itself.
- **`neutral-frontier`:** same catalog and discriminator, no stale claim in the resumable foreground. Expected as a **scored `cell_verdict`, fail-closed exactly like ballast-discriminator**: **the warmth-tax accounting band is pinned at 0** — ANY strict ECAC win by resumable on this fixture is instrument self-refutation (`PRF2-neutral-null`); there is no tunable tolerance knob (gemini's pin, review round). The comparison runs over **effective cost including `a_i`** (`a_i(cold) = 0`): resumable pays the artifact carry with no stale summary to compensate, so it carries a structural disadvantage here — that is the falsifier's anchor, and comparing read-cost-only would erase it (glm's addition; one sentence so no future builder inverts it). No suppression claim is licensed.

"Expected: must not win" as manifest prose without a `cell_verdict` is a burn — this lab has been burned twice; these are cells, not comments.

## 21. v0.2 cells

| cell | shape |
|---|---|
| `PRF2-cost-win` | Regime S, dispersion-gated: resumable mean-ECAC < cold mean-ECAC on the cognitive-temptation fixture, all guards green. **Only positive behavioral shape.** |
| `PRF2-cost-loss` | resumable mean-ECAC > cold on the cognitive-temptation fixture (false continuations priced at c_max drag the mean). Diagnostic false-continuation rate reported — **"suppression" vocabulary lives ONLY in the diagnostic layer, never in a cell name** (hermes's rename, gemini-endorsed: a machine-computed cell may not carry a disposition word). |
| `PRF2-zero-dispersion` | dispersion probe fails — no behavioral verdict either way; point-mode only. |
| `PRF2-ballast-null` | ballast-discriminator cell: win fired where it must not → instrument self-refutation, fail-closed. |
| `PRF2-neutral-null` | neutral-frontier cell: resumable beat cold with no stale summary → the measured effect is not the summary's. |
| `PRF2-heir-dominates` | cold matches or beats resumable at mean-ECAC with quality — the honest null: driving with the artifact bought nothing. |
| `confounded` | symmetry/replay/c_max/regime guards — never a behavioral loss. |

## 22. Carry, demote, delete (v0.1 ↔ v0.2)

**Carries verbatim:** witnessed ordering; population precommit before any session; the two-phase mint and every D1 guard (banned fields, genealogy refusal, content floor, mutual exclusion); D2 derivation + replay-as-authority; canonical-text cost replay; branch-blind oracles; `gate_open`; the ignorance probe; `authored_oracle`. Modules unchanged: `predicate_ast`, `mint_frontier_state`, `derive_live_obligations`, `check_prf_fixture` core, `prf_ablation`.
**Demoted to special case:** the obligation-intersection checkpoint and the `A+P+R<C` tree — the Regime-D/v0.1 compatibility path, forked on `instrument_version`.
**Deleted from the v0.2 hot path:** pre-emitted `surface_read`, `injected_route`, fixed-batch answer redraws.

## 23. Non-claims and debts (v0.2)

- **Causal-reduction fixture (hermes)** — experiment 2, after the cognitive-temptation baseline is earned. Named debt, not dropped.
- **Arbitrary mid-thought interruption** — still out (Part I §11); SBR frees the reads, not the seam.
- **The empirical-adequacy ablation leg (Part I §4c-1 leg 2)** — carried; the SBR loop does not discharge it.
- **Seed control on `LocalEngine`** — today the backend ignores seeds; `seed: unavailable` is recorded, and cross-engine replication is the mitigation, not a claim of reproducibility.
- No claim about engines other than those probed and run; no production-transfer claim beyond gemini's four conditions (Part I §11).

## 24. Deliverables and build order

**New:** `harness/run_sbr.py` (action loop, structured-action parsing, budget enforcement, **the dispersion probe lives here**, row emission) · `score_prf.py` v0.2 path in the existing module, forked on `instrument_version` (ECAC with the §16 pinned constants — `quality_threshold`, band=0, `a_i(cold)=0` —, regime logic, **`PRF2-zero-dispersion` emitted by the scorer**, `false_continuation`, symmetry runtime guard, new cells) · `check_prf_fixture.py` SBR legs (§19) · fixtures: cognitive-temptation base + `ballast-discriminator` + `neutral-frontier` overrides · `tests/test_prf_sbr.py`, `tests/test_prf_ecac.py` (MockEngine, scripted action sequences — the mock proves the loop, never behavior). **Named builder debt (composer):** `engine.py` needs a multi-turn / tool-action channel for real Regime-S sessions — the current single-shot `run()` cannot host the SBR loop; this is mechanism work for the delegated builder, reviewed before landing.
**Build order:** room block-or-pass on this Part → harness + wire tests (Regime D) → fixture gate green including the two loses-cell fixtures → dispersion probe on the real engine → Regime S run under the §17 contract. Wire tests never promote a cell; the delegated-builder split holds (mechanism to composer from this sealed Part; fixtures, oracle keys, and anything measurement-shaped stay in the builder lane).

---

# Part III — v0.3-draft: the triangulation-docket fixture family (the pay-window experiment)

Status: v0.3-draft-r2, folded from the design round (2026-07-03/04: codex's triangulation-docket shape; composer's implementer mechanics; hermes's claim-vocabulary split; gemini's symmetry/ECAC math; glm's must-not-lose contract A1–A10/B11–B18 + conflicts C1–C4 + D-list) and the pin round (2026-07-04: all ten D-items pinned from values on the board; glm's three catches encoded — the D3 geometry amendment to C1, false-continuation as diagnostic-only, the `a_i` scorer alignment made law). dan sealed the brief 2026-07-04; the addendum seal is pre-authorized contingent on a clean review round — any BLOCK stops the line. **Review round (2026-07-04): codex/hermes/gemini PASS on their lanes; composer + glm BLOCK on a converged four-item fix list, encoded in r2 — F1: the §32 ballast analog required overrides the inherited §20 variant gate forbids (override allowlist for the 0.3 gate path now pinned in §32/§34); F2: the D1 `a_i` render-path binding was scorer-only, omitting the mint side (`minted.state_tokens`) — the `d6ab5a9` tautology family in a new shape, now bound in §34; F3: `_decision_read_chain_ok` is JSON-coupled and would fail every R-handle session — named in §34; F4: §27's `eq option_id "K-17"` trigger was not evaluable in the witness_read context and collided with §4a opacity — rewritten as `read_has_tag(leg_*) ∧ eq catalog_key "K-17"`. Re-review by the filers precedes the seal.** **Part III adds a fixture family and its gates. It changes no Part II claim semantics**: two regimes, the §17 sampling contract, ECAC, and the §13 prohibitions carry verbatim. The frozen `sbr-meridian` family is untouched and keeps its evidential status (declared zero-dispersion for gpt-oss-20b; Regime-D machinery/cost-loss evidence only for its probed engines).

## 25. The Part III question — the pay-window, made falsifiable

The cross-engine probes (`011680c`) left a measured gap: the meridian artifact was a pure cost tax for the strong engine (ignored it, re-read) and a distractor for the weak ones (failed with it present). The window where a frontier artifact *pays* — an engine strong enough to use it, weak enough to need it — was never observed, and on that surface could not have been. Part III's family is designed so that **"no pay-window exists" is a falsifiable instrument outcome, not a residue of miscalibration**:

> pay-window conditional (cost-only, per §21 vocabulary): `a_i(resumable) + Σ tokens(3 targeted leg reads) < Σ tokens(cold exploration of the pinned 6-surface plausible route)`, with both branches at `quality_ok` (§16, bar = 1.0).

Three priced outcomes if it fails to open: `PRF2-heir-dominates` (cold reads the same three legs and stops — the honest null), `PRF2-cost-loss` (quality failures priced at `c_max` drag the mean), and the self-refutation cells (`PRF2-ballast-null` / `PRF2-neutral-null`) if a win fires where it must not. The measured failure modes this family is built against: R1 — route entropy that survives a capable engine (the 20b collapse); R2 — an action surface small engines can hold (gemma's refused JSON); R3 — a quality bar reachable with the foreground present (the cognitive-load result).

## 26. The world and catalog geometry (D3 as pinned; C1 as amended)

A fresh fictional world: a facilities permit/case queue. Task: *"what disposition should be entered for case K-17: approve / defer / reject / reopen."* The answer is a **three-leg conjunction** — the case's status note, the exception-register row of the register that carries K-17's exception class, and the clearance-ledger row of the ledger that carries K-17's reviewer clearance.

- **Catalog: 21 surfaces = 9 plausible + 12 ordinary admin ballast; 3 dispositive.** The 9 plausible are **3 same-class surfaces per leg class**: status notes `K-17 / K-18 / K-19` (case-titled — title names class+case, symmetric across siblings, never sufficiency); Exception Registers `A / B / C` and Clearance Ledgers `A / B / C` (template-identical titles within class, **never case-titled**; K-17-relevance lives only in body rows). Exactly one register per class carries K-17's dispositive values. This is the C1 settlement made geometric: cold finds leg 1 by honest title and must genuinely explore for legs 2–3. (Pin-round amendment: the design-fold's "shared register" singular was the bug; it yielded 5 plausible surfaces and made the D4 geometry impossible.)
- **Structured-field discipline (D7):** all 9 plausible siblings carry the **identical structured-field schema**; dispositive K-17 values appear only on the 3 true legs. No schema-presence side channels; the oracle discriminates on field *values*. The oracle keys off **authored structured fields pinned in catalog metadata at population** — never body-prose inference (§5's exclusion of substring/regex over text is the seal; the disposition cannot be smuggled through the bundle because the bundle cannot do the oracle's work).
- **Red herrings are authored, not parallel-titled:** same-class siblings share title-grammar templates and parallel body-row structure; the discriminant lives only in field values the oracle reads. `s1_not_theatrical` does not catch "reads like the answer but isn't" — authoring does.
- **Branch symmetry carries verbatim (A8, §19):** identical titles, physical indices, costs, hashes on both branches; the resumable foreground artifact is the only asymmetry.

## 27. The frontier artifact — a narrow obligation bundle

The artifact names **obligation ids + surface ids/classes only**: no disposition value, no rank, no rationale (B14). It whispers the answer-*shape* legally only because of §26's structured-field oracle. Mint is Part I machinery unchanged: **three mutually exclusive trigger predicates** over leg tags (`leg_status` / `leg_exception` / `leg_clearance` on exactly the three K-17 leg surfaces), each the conjunction `read_has_tag(leg_*) ∧ eq catalog_key "K-17"` — `catalog_key` is surface catalog metadata evaluable in the witness_read context (§5), and `"K-17"` is a `catalog_key` value, **never** an `option_id` literal (§4a opacity holds: option ids stay `A`, `B`, …). Equivalent formulation `surface_id ∈ {the three K-17 leg ids}` is legal; an `option_id`-based trigger is NOT — `option_id` is unbound in the read-trigger context (F4, review round). Siblings never fire; three rules `R_status` / `R_exception` / `R_clearance` → `verify`/`read` kinds with disjoint `match_key_ids`; reopen via the existing `changed` invalidation rule on those keys. One rule → one obligation; the library cannot express "leg 2 only if leg 1" and the design does not need it. **The existing AST carries — no new predicate ops.**

- **`witness_route` (D8):** the witness reads a SET equal to the three leg surfaces (one read per leg, so the bundle derives at freeze). Order is unconstrained — witness (pre-seam) and calibration (post-mint) may order differently; derivation is set-based.
- **`a_i` (D1, and the scorer-alignment law):** `a_i(resumable) = tokens(render_canonical_artifact(canonical_state))`, `a_i(cold) = 0`; stale-claim tokens stay separately ledgered outside ECAC. **Bound to this pin, not builder options:** `_artifact_tokens` switches to the render path; `minted.state_tokens` stores *rendered* tokens; the `a_i_recomputed_ok` guard blocks (→ `confounded`) on `rendered_recompute ≠ minted.state_tokens`. (Pin round: three of four posts concurred on the value without the scorer change — the pin is dead on arrival without it.)
- **Foreground ceiling (D10):** canonical artifact + optional stale claim ≤ **160 rendered tokens**, enforced as fixture-gate leg `foreground_budget_ok` using the SAME render path as runtime (`render_resumable_foreground`). The ceiling is never stretched to rescue out-of-scope engines (C2).

## 28. The action surface — R-handle enum grammar (R2)

§15's closed action space carries; the surface changes. The menu presents numbered rows with stable handles; the only legal actions are `R01`…`R21` or `STOP` (`^\s*(R\d{2}|STOP)\s*$`, case-folded). The parser maps handle → `surface_id` via `physical_index` after `catalog_sort`, **before** the existing ledger path — ledger semantics unchanged; `action_space_hash` bumps. The handle menu is the **only** action vocabulary in `build_sbr_system` + `SBR_ACTION_INSTRUCTION`. This is §15 hygiene, not free-text routing (finite enum per session) — and it is **not** claimed to fix gemma-class empty-completion stalls (C2: those engines are out of pay-window scope by construction; their `calibration_gate: fail` rows are real, reportable foreground-pressure evidence).

## 29. Budgets, pricing, comparators (D2, D5, D9)

- **Budgets carry meridian verbatim:** `max_read_tokens = 700`, `max_steps = 8`, `action_overhead_tokens = 20`, `c_max = 860`; binding precondition `700 < Σ(visible surface tokens)` (§16 unchanged).
- **Pricing (D5):** terminal inadequacy (`quality_ok = false`, incl. forced stop and budget exhaustion) prices at `c_max`. An individual refused/illegal action burns a step toward `forced_stop` — never a separate surcharge, never zero. **`false_continuation` is diagnostic-only, never priced directly**: a stale-but-correct answer prices at its real cost with FC recorded as a diagnostic row (§18 semantics unchanged; B16 claim vocabulary — "cognitive load", "suppression", "malingering" never appear in a `cell_verdict`).
- **Comparators (D9):** strict `<` on per-episode mean ECAC (Regime S); loses-cells per episode; no roll-up; `quality_threshold = 1.0` pinned HERE, in text, before any engine runs (the pin-at-seal deferral was rejected — sliding the bar post-hoc is the `a_i`-anchor failure mode).

## 30. The calibration gate (B11) — admission precondition, never evidence

Two legs, both before any dispersion probe or Regime-S contact:

1. **Fixture leg (`check_prf_fixture`, no engine):** the episode pins `calibration_route` — the **ordered surface_ids** `[k17_status_id, exception_register_id, clearance_ledger_id]` (D6; R-handles are presentation-only and never appear in the pin) — plus `calibration_obligation_ids` (hash) and `calibration_expected_answer`. The leg verifies: the ids exist and are the three oracle legs; route token sum ≤ `max_read_tokens`; the obligation ids replay from `witness_route` through `derive_live_obligations`.
2. **Runner precondition (`run_and_score`):** per manifest `target_engine`, one **real** `resumable_state` session with the canonical foreground, scripted along `calibration_route`, `elicit_answer = True`; pass iff `quality_ok` and zero route refusals. Ledger row `kind: calibration_gate` per engine; any fail → `gate_refused`, no suite for that engine. Mock/scripted suites skip with disclosed `wire_test`.

**C3 ordering (hermes, adopted verbatim):** calibration is an admission precondition, **never evidence**. A calibrated strict resumable win still owes ablation + band=0 evidence before it is a verdict; the §23 causal-reduction debt rides on every win cell, every family. **C4:** the calibration route is the three base legs only; a changed-world/reopen episode, if shipped, pins its own scripted leg separately.

## 31. The pay-window geometry leg (D4)

The episode pre-pins `cold_exploration_route`: **exactly 6 ordered plausible surface_ids, none in `calibration_route`**. New fixture-gate leg `pay_window_geometry`: `tokens(cold_exploration_route) > a_i_rendered + tokens(calibration_route)` must hold or the family gate refuses. **This leg is fixture geometry only — it licenses the family to run; the verdict remains actual mean ECAC per §29.** (glm's conflation guard: a builder must not be able to pass the gate trivially while the cell fires on real costs, or vice versa.) `N = 6` is two-thirds of the plausible pool and 2× the true legs; it is pinned here so it is never chosen post-hoc to make the conditional hold.

## 32. Self-falsifiers (A2, B15) — authored overrides, gated before dispersion

Both carry §20's fail-closed shape on full effective cost with `a_i(cold) = 0`, band = 0:

- **Ballast analog:** same catalog geometry and action grammar; the named obligation bundle points at surfaces genuinely unnecessary for the oracle disposition (wrong-leg tags, same population discipline, `changed` invalidation on the wrong keys). Any strict resumable win → `PRF2-ballast-null`.
- **Neutral analog:** same-carry bundle (same rendered `a_i`, parallel obligation shape) whose obligations do not select a prunable frontier for the asked question; no stale/live tension. Any strict resumable win → `PRF2-neutral-null` — with `a_i(resumable) > 0` pinned at 0-band, resumable carries the structural disadvantage that anchors the falsifier.

Both are **declared overrides passing the full fixture gate themselves**, computed not attested (A6), authored before any engine contact.

**Override allowlist for the 0.3 gate path (F1, review round — the inherited §20 gate legs `variant_declared_overrides_only` / `stale_only_asymmetry` fork on `instrument_version = 0.3` for this family):** the **ballast analog** may override `witness_route` + `frontier_state` (and `calibration_obligation_ids`, replay-checked through `derive_live_obligations` against its own witness route) — a wrong-leg bundle is impossible otherwise, since rulebook and tags are population-pinned and `catalog_hash`-shared; the **neutral analog** may override `stale_claim` only. `catalog_hash`, budgets, action grammar, titles, physical indices, and per-surface costs stay shared across all variants — the catalog itself never forks. The 0.2 allowlist (`discriminator_surface_id`, `stale_claim`) remains the law for the meridian family; neither allowlist loosens the other.

## 33. Engines, precommitment, and no-mutation

- **`target_engines` (fail-closed pin):** the manifest names its engine roster, **precommitted in-thread before any engine contact** (the cross-engine round's shape: every result reports, no engine-fishing). Candidate set = the runnable local pool at build time. Per engine, in order: cold ignorance probe (attested per-engine, never inherited) → calibration gate (§30) → dispersion probe at the family's precommitted midpoint → Regime-S per §17. An empty passing set = family gate refuses, reported, no rescue.
- **No in-family mutation, ever (A5):** the family is designed right or it closes, like meridian's temperature lane. Fresh freeze, gate, probes; no shared frozen state with `sbr-meridian`.
- **Temperature stop-rule carries per engine** as adopted (one 0.7 attempt iff the midpoint collapses, then the engine is declared).

## 34. Part III deliverables and build order

**Fixtures (builder lane — measurement-shaped authoring):** `episodes/prf/` triangulation-docket population (21 surfaces, leg tags, structured disposition fields, red-herring siblings), rulebook (3 rules + reopen), predicate library entries, witness route, `calibration_route` + `calibration_obligation_ids` + `calibration_expected_answer`, `cold_exploration_route` (6 ids), freeze manifest, ballast + neutral overrides, oracle keys — all precommitted before engine contact.
**Harness:** R-handle grammar in `run_sbr.py` + `build_sbr_system` + `SBR_ACTION_INSTRUCTION` (`action_space_hash` bump; handle→surface_id mapping pre-ledger) · **`a_i` render-path alignment on BOTH sides of the guard (F2):** `mint_frontier_state.py` stores *rendered* `state_tokens` (the `freeze_validate` / `offer_gate` token-logging path), and `score_prf.py` `_artifact_tokens` / `a_i_recomputed_ok` recompute via the SAME shared `artifact_render_tokens(canonical_state)` function also used by `pay_window_geometry` and `foreground_budget_ok` — one render function, four consumers, or the guard is a tautology again · **`score_prf._decision_read_chain_ok` (F3):** the guard is JSON-coupled (`re.search(r"\{.*\}")`) and must be updated in the same change as the R-handle parser — key it off `surface_read` steps regardless of action grammar, or normalize `route_decision.raw_action` pre-ledger · `check_prf_fixture.py` new legs: `calibration_route` fixture leg (§30-1), `pay_window_geometry` (§31), `foreground_budget_ok` (§27), the 3+3+3 plausible-geometry count by pinned leg tags (§26), **and the §32 override-allowlist fork of `variant_declared_overrides_only` / `stale_only_asymmetry` on `instrument_version = 0.3` (F1)** · `run_and_score` per-engine `calibration_gate` precondition (§30-2).
**Tests:** golden pass/refuse cases per new gate leg; R-handle parser cases (case/whitespace variants, illegal handles); `a_i` render-alignment regression (the guard must block on a seeded mismatch — no tautological guards; the `d6ab5a9` lesson is a test now); scripted calibration wire run.
**Build order:** room block-or-pass on this Part → dan's seal → harness changes + wire tests → fixture authoring + family gate green (incl. both analogs) → in-thread engine-roster precommitment → per-engine ignorance probe → calibration gate → dispersion probe → Regime S. Wire tests never promote a cell. Builder ≠ auditor: whoever builds, the rest of the board reviews.

## 35. Part III non-claims

- No Part II semantics change; no meridian re-scoring; the meridian declarations stand.
- The §23 causal-reduction debt is advanced (one confound removed) but **not discharged**; it rides on every win cell.
- No claim about gemma-class engines beyond their `calibration_gate` rows (C2); no claim that R-handles fix foreground stalls (§28).
- "No pay-window observed for this engine/family" is a **diagnostic observation** (B16), never a cell name; the priced outcomes are §25's cells only.
- If the pay-window fails to open across the full precommitted roster with calibration passed and dispersion present, that is a finding about the resumable-state hypothesis at this scale — reported at that altitude, converted by nothing but the stop rules.
