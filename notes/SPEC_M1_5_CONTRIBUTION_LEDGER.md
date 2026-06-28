# SPEC M1.5 — Contribution Ledger (the offer ledger, one level up)

Status: **v0.1 — REVIEWED** (one bounded pass each: codex, kagi, cursor, grok all endorse, no blocker, 2026-06-13; their adopted guardrails are folded below — review log at end). gemma is out for now (the Pi harness can't yet drive the substrate MCP or the CLI; dan will revisit). Serves ROADMAP M1.5, the **entry gate to M2**: the ledger must be *writing and computed* before a resident exists, or M2's first sessions have no verifiable trace of what changed behavior. Oracle: artifact diffs + review outcomes (artifact-grounded corpus = the lab's own M1 build; world-checked close-gate chained to HU1). Ships with its own loses-cell (standing rule 2). Review asks in §8.

## §0 The claim, stated before any cell

> Agent interventions (reviews, blockers, patches, audits, syntheses) can be tracked as records whose **important status is computed from the artifact trace, never from the contributor's claim** — so that the next instance reading the ledger learns *what actually changed an artifact*, not *who said they helped*.

The milestone's whole risk is one failure mode, named in the ROADMAP:

> **self-esteem bookkeeping** — entries that exist to be counted rather than to be read by the next instance.

This decomposes into two distinct refutations, and the spec must be honest about which one M1.5 closes:

1. **Self-declared ≠ important** (R5, one level up): the contributor's own claim of impact is audit input, never the win condition. **M1.5 closes this** — the scorer computes important from the trace.
2. **Counted ≠ read**: the ledger only earns its cost when a downstream instance *reads* it and decides differently. **M1.5 names this as a cell and discloses it `not_engaged`** (the read-changes-a-decision fork needs a resident — it is the entry condition *into* M2, not M1.5 work). Parallel to how M1 closed with H2 `not_engaged` and M0 with C-2's null.

A milestone that claimed both were demonstrated would be the fog machine the lab refuses to build.

## §1 The intervention, defined (contribution is the offer boundary, one level up)

The lab's existing instrument scores how **records** become an answer at the **offer boundary**. M1.5 scores how **interventions** become an artifact at the **contribution boundary**. It is not a new epistemics — it is the same one, lifted a level. The five refusals map almost line for line, and that mapping is what keeps the ledger an instrument rather than a diary:

| offer boundary (records → answers) | contribution boundary (interventions → artifacts) |
|---|---|
| R1 `retrieved ≠ true` | **`logged ≠ important`** — a recorded intervention changed nothing by being recorded. |
| R2 `present ≠ authorized` | **`spoke ≠ contributed`** — presence in the thread is not contribution; the boundary needs a reason. |
| R3 `diverged ≠ improved` | **`changed-the-artifact ≠ improved-it`** — a patch that landed then reversed is not a win. |
| R4 `governed won ≠ only success` | **interventions that lost are first-class** — `blocked`, `reversed`, `passenger` are ledgered, not hidden. |
| R5 `self-classification ≠ usage` | **`claimed-credit ≠ important`** — the contributor's claim is audit input; the harness computes the verdict. |

**Attribution vs contribution (gemma's distinction, adopted as the claim/verdict split).** *Attribution* is the proposed `intervention` row — a past-event observation, contributor-written, R5 audit input. *Contribution* is the computed `contribution_verdict` — a transferable, re-checkable asset whose `load_bearing` is grounded in the trace. The distinction is not cosmetic; it is the important/passenger line of AGENTS.md applied to agents. gemma's further split of contribution *value* into intrinsic-value vs actuator-skill (a `contributory_asset` field) is **gated to v0.2** — see §8(b): you cannot price *kinds* of value before proving the asset is read at all (that is the self-esteem trap in a fancier hat).

**What is not a contribution.** Restating a settled point; a thread entry with no artifact downstream of it; a review that endorsed without a written blocker; a patch that reverted with no lesson preserved. These land as `outcome: passenger, load_bearing: false` — recorded honestly, never counted as wins. The `passenger` outcome *is* the R1/presence-riding refusal made into a verdict.

## §2 The honesty mechanism: computed, not claimed

The architecture mirrors `score_cells.py` exactly. A `cell_verdict` is computed from ledger rows (offer / withholding / ablation / diff_outcome); a `contribution_verdict` is computed from the **artifact trace** (git commits + diffs, the immutable substrate thread, the run ledgers) plus the intervention's artifact pointers. The contributor proposes; the harness disposes. **Ledger writer is external** (AGENTS.md) is sharper here than anywhere: the agent under test must not write its own `load_bearing: true`.

**Load-bearing is an artifact counterfactual.** Just as record ablation asks *did presence change the answer*, intervention important asks *does the target artifact's current state depend on this intervention*. Checked one of four ways, tiered by `review_basis` — the field that says **where the important judgment came from**:

| `review_basis` | how important resolves | strength |
|---|---|---|
| `artifact_diff` | a git/ledger delta the intervention points at, which would not exist without it (a commit touching the named file; a hollow-pass row *replaced* in a rerun; a corpus record added) | machine-checkable |
| `scorer_evidence` | the intervention's product is consumed by a downstream `cell_verdict` (a scorer used to compute a verdict; a corpus record carried into a passing cell) | machine-checkable, **chainable to the world** (§5) |
| `human_moderation` | a moderation call by dan, recorded as a harness row — external to the contributor, but not machine-checkable | disclosed, external |
| `later_audit` | a label-blind audit after the fact | weakest; audit input, never a close-gate basis |

**Three resolution rules the reviewers made important (all four endorsed):**
- **Single-valued, strongest-wins.** `review_basis` is one value, not a list; when several apply the precedence is `artifact_diff` > `scorer_evidence` > `human_moderation` > `later_audit`, and `evidence` lists everything checked. (kagi #3, cursor #3, grok #3 — keeps the oracle check unambiguous.)
- **`later_audit` is a *deferred* basis, not a present one.** A row whose only basis is `later_audit` fails closed to `passenger` / `unsubstantiated` until the audit materializes as its own `kind: audit` intervention carrying `artifact_diff` or `scorer_evidence`. No important on the promise of a future audit. (codex #1, kagi #1, cursor #2.)
- **`human_moderation` is external, never a close-gate alone.** The resolver checks that a harness-written moderation row exists (external to the contributor) — not that dan was *right*. Disclosed evidence that a decision happened; weak evidence of a machine-checkable counterfactual. (codex #2, cursor #4.)

**Pointer-resolver contract (cursor §8c, adopted).** Pointer types are closed; resolution is deterministic and fails closed; the scorer never interprets thread prose:

| pointer type | resolves when | delta check |
|---|---|---|
| `commit_sha` | object exists; `git show --name-only` touches `target_artifact` | non-empty diff on the named path |
| `ledger_row_hash` | canonical-JSON hash matches exactly one row in the named ledger | row `kind`/fields match the intervention's `kind`/`outcome` claim |
| `thread_entry_ts` | `*__<agent>.md` under `.substrate/threads/<thread>/` with matching UTC ts | entry non-empty — **presence only; not important by itself** |
| `corpus_record_id` | record id present in the named episode/corpus JSON | consumed downstream (the `scorer_evidence` chain) |

Human judgment lives in **backfill authoring** (which pointers to propose), never in **scoring** (whether they resolve). `intervention.claimed_load_bearing` is audit input; `contribution_verdict.load_bearing` is never copied from it.

**The refusal, mechanized:** the scorer marks `load_bearing: true` only when the basis resolves — a real commit/row for `artifact_diff`/`scorer_evidence`, a recorded moderation row for `human_moderation`. A claim whose pointer does not resolve → `load_bearing: false, outcome: passenger, verdict: unsubstantiated`. That is the self-esteem loses-cell, computed (§4 CB-loses), not adjudicated by a human reading the thread.

**Outcome vocabulary, against the trace** ({blocked, landed, reversed, passenger} from the ROADMAP/codex schema):
- `landed` — the intervention's delta is present in the current artifact (commit in history, record in corpus, scorer in use).
- `blocked` — the intervention *prevented* a delta: a blocker that succeeded (the bad change did not ship). Outcome of the intervention, not of the target. The canonical case: a blocker that stopped a hollow pass from shipping.
- `reversed` — landed, then undone. Preserved via `reversal_of` (below), never overwritten.
- `passenger` — recorded but the artifact does not depend on it. The honesty outcome; `load_bearing` is false by definition here.

**`reversal_of` and append-only immutability (codex; L-A precedent).** The ledger is append-only. A correction does not overwrite the earlier intervention — it appends a new row whose `reversal_of` names the prior `intervention_id`. The original stays as *scored under the rule then in force* (the L-A precedent from M-1 closure). Canonical example already in the M1 trace: the I1-timing first run was a hollow pass; the rerun replaced it. The rerun's verdict carries `reversal_of` the hollow-pass intervention; both rows stand.

## §3 Schema (two row kinds — the claim/verdict split R5 forces)

No new schema beyond what a measured backfill needs (plan §2). Two kinds, because letting the contributor write the authoritative `load_bearing` would violate R5 by construction:

- **`intervention`** (proposed; contributor-written or harness-detected; **audit input, not authoritative**):
  `{intervention_id, contributor, kind: review|blocker|patch|audit|synthesis, target_artifact, artifact_pointers: [commit_sha | ledger_row_hash | thread_entry_ts | corpus_record_id ...], claimed_outcome, claimed_load_bearing, reversal_of, ts}`

- **`contribution_verdict`** (computed by `score_contribution.py`; **harness-written, authoritative** — mirrors `cell_verdict`):
  `{intervention_id, kind, target_artifact, outcome: blocked|landed|reversed|passenger, load_bearing, review_basis: human_moderation|artifact_diff|later_audit|scorer_evidence, source: authored|artifact_grounded|world_checked, evidence: {resolved_pointers, downstream_verdict_ids, ...}, reversal_of, ts}`

`source` parallels the oracle-source field (`_world_checked_source`): `artifact_grounded` when important resolves against the immutable repo/thread trace; `world_checked` when it chains through `scorer_evidence` to a `cell_verdict` carrying `source != authored` (§5). `authored` is the weak case — disclosed, never a close-gate. `review_basis` is **single-valued** (kagi #3); when several apply, strongest wins by the §2 precedence.

The `contribution_verdict` is the contribution-boundary analog of the offer/withholding pair: it records, per intervention, whether the boundary was crossed (important) and the reason (review_basis + resolved evidence) — R2 at the agent level.

## §4 Cells

All cells are computed by `score_contribution.py` over a contribution ledger + the artifact trace it points at. The first corpus is the lab's own M1 build (§5).

### CB-1 — substantiated contribution *(should pass)*
An intervention whose `load_bearing: true` resolves against the trace. **Pass** = the verdict's `review_basis` is `artifact_diff` or `scorer_evidence` AND the pointer resolves AND `outcome ∈ {landed, blocked}`. Worked backfill examples whose verdicts write themselves:
- **codex's H1 false-green catch** → `kind: blocker, outcome: blocked, load_bearing: true, review_basis: artifact_diff` (the trace shows the hollow-pass row replaced; ablate the catch and M1 ships a hollow pass — documented in M1_FINDINGS process note 1).
- **cursor's scorer/episode authoring** → `kind: patch, outcome: landed, review_basis: scorer_evidence` (the scorer is consumed by M1's `cell_verdict` rows).
- **anti-hollow guard (the same shape as I1; cursor §8c):** `outcome ∈ {landed, blocked}` is not enough — the resolved pointer(s) must show a **non-vacuous delta** on `target_artifact`. These fail loudly to `unsubstantiated`/`passenger`, never a vacuous pass:
  - a `landed` patch whose commit does not touch the named artifact;
  - `outcome: blocked` with only one resolved pointer — `blocked` requires **two**: the bad-state artifact that existed (e.g. the first-run hollow-pass row preserved in `runs/m1/`) *and* the intervention that prevented it shipping;
  - `scorer_evidence` whose downstream `cell_verdict` is missing, `audit_pending`, or `wire_test: true` while the row claims close-gate credit.

### CB-loses — self-esteem bookkeeping *(should lose; standing rule 2)*
A proposed `intervention` claiming `load_bearing: true` whose pointer does not resolve to any artifact delta — a thread entry that restated a settled point, a review that endorsed with no written blocker, a "synthesis" with nothing downstream. **Pass of the cell = the scorer returns `verdict: unsubstantiated, load_bearing: false, outcome: passenger`** for it. The mechanism *losing* (refusing to credit the unsubstantiated claim) is the result. This is R5 made into a verdict; without it the ledger is a diary.

### CB-read — read changes a decision *(M2-owed; disclosed `not_engaged` at M1.5)*
The full refutation of "counted ≠ read": a fork where an instance that **reads** the contribution ledger decides differently from one that does not — and decides *better* against an oracle. This needs a resident reading across sessions (M2). **At M1.5 it is named and disclosed `not_engaged`**, and it is the explicit entry condition into M2. Carried as a debt, parallel to H2/C-2. **Scope guard (self-applied, codex §8e):** wiring contribution → review authority is *not* done here — that is continuity-as-authority (M2's loses-condition); a contributor's past important record must not auto-authorize their next claim.

### CB-U1 — un-authored close-gate *(the §5 hard gate)*
At least one `contribution_verdict` whose `load_bearing: true` is computed via `review_basis: scorer_evidence` pointing at a `cell_verdict` that itself carries `source != authored`. **Worked example: kagi's rw-0003 sourcing** → `kind: synthesis`; the corpus record is consumed by **HU1**, whose verdict carries `oracle_source: retraction_corpus` (`source != authored`, both engines). So kagi's contribution inherits world-groundedness through the chain — `source: world_checked`. **Pass** = the chain resolves and the terminal `cell_verdict.source != authored`. The chain must be **machine-walkable, not narrated** (cursor): the HU1 backfill row names the actual `runs/m1/` ledger path + `fork_group_id`, and the resolver walks `corpus_record_id → episode ledger → cell_verdict → oracle_source`; a `wire_test: true` terminal verdict → `unsubstantiated`. This is how M1.5 stays answerable to the world without authoring its own new corpus: it borrows M0/M1's already-un-authored oracle through `scorer_evidence`.

## §5 Oracle

**Artifact diffs + review outcomes** — and the first corpus is **the lab's own M1 build**, reconstructed from artifacts that already exist and that we cannot now edit:
- the immutable substrate thread (thread-2 trace),
- git commits (`df8b7da` spec-reviewed, `05acd1f`/`9543259` close) and their diffs,
- the `runs/m1/` ledgers (including the preserved first-run hollow-pass rows).

These outcomes are **checkable against an immutable record**, not authored to flatter the schema — which *is* the artifact-diff oracle, and it refutes CB-loses by construction. **Honesty boundary:** this corpus is `artifact_grounded`, not `world_checked` — we authored M1's history as its builders; it is *found relative to the M1.5 schema*, not external to the lab. The genuinely un-authored leg is **CB-U1**, which chains through `scorer_evidence` to HU1's world-checked verdict. M1.5 is not *done* until CB-U1 passes — the §5 discipline every milestone owes.

**Corpus composition requirement (kagi #2, adopted — the sharpest review point).** The four obvious backfill rows are all `landed`/`reversed` wins with clean trails: the *easy* path, where `load_bearing: true` is cheap to resolve. The first corpus must also include at least one genuine **`passenger`** row — an intervention that was attempted but whose removal changes no artifact (`load_bearing: false`). Easy-to-write, hard-to-falsify rows are exactly where self-esteem bookkeeping hides, so the anti-self-esteem mechanism is *untested* until the `load_bearing: false` path is exercised on a real intervention, not only on a planted CB-loses probe. The passenger row proves the honest negative exists in the wild; CB-loses then adds the deliberately-unsubstantiated probe on top.

**Representativeness annotation (kagi/M0, immutable at scoring time).** Every `contribution_verdict` carries a `corpus_scope` annotation naming what trace it was computed over (here: the M1 build). The ledger's own growth path is in scope of this disclosure, not just the first backfill — a legal read path that carries no decisions today may carry them tomorrow. Retroactive re-interpretation is a different row kind, never a rewrite (the M0 precedent).

## §6 Ledger / schema additions

- `intervention` row (§3): proposed/claimed; R5 audit input. Contributor- or harness-written. Added to the `ledger.py` row-kind docstring.
- `contribution_verdict` row (§3): computed; harness-written; mirrors `cell_verdict` (`verdict` ∈ {pass, fail, not_engaged, unsubstantiated} + `evidence`). Added to the docstring.
- `score_contribution.py`: reads a contribution ledger + resolves `artifact_pointers` against git / the thread / the run ledgers; emits `contribution_verdict`. Mirrors `score_cells.py` structure (one verdict per intervention, anti-hollow-pass guards, no human-read claims).
- No `BranchConfig` change, no engine call: the contribution boundary is scored over the trace, not over a fork. (The CB-read fork that *would* need a branch is M2.)

## §7 Build order

(1) ~~spec reviewed — one bounded pass each~~ **done (v0.1, codex/kagi/cursor/grok)**; (2) ~~`intervention` + `contribution_verdict` row kinds in `ledger.py`~~ **done**; (3) ~~`score_contribution.py` with the closed pointer-resolver contract (§2), fail-closed, single-valued `review_basis`~~ **done**; (4) ~~backfill the M1 build into `runs/m1_5/contributions.jsonl` with ≥1 genuine `passenger` row (kagi #2) + the deliberate CB-loses probe~~ **done**; (5) ~~compute CB-1 / CB-loses / CB-U1 (HU1 chain machine-walkable); CB-read `not_engaged`~~ **done — all pass / not_engaged as designed; matrix in `notes/M1_5_FINDINGS.md`**; (6) **remaining:** one confirming review pass by the room against the built result.

**Delegation note (the M1 division that held):** the mechanism (the claim/verdict split, the important-is-an-artifact-counterfactual definition, the review_basis tiers) and the loses-cell stay dan+claude. Pointer-resolution plumbing, the backfill authoring, and scorer wiring against this fixed spec are candidates to farm to cursor/codex once ratified. Core design is not delegated; busy work against a ratified spec is.

## §8 Review asks (bounded, one pass — mapped to assignments)

a. **codex — the claim/verdict split & `review_basis` semantics.** Is two row kinds (`intervention` proposed, `contribution_verdict` computed) the right enforcement of R5, or over-built for a backfill? Are the four `review_basis` tiers and the `reversal_of`/L-A immutability handling correct?
b. **gemma — attribution vs contribution, and the `contributory_asset` gate.** Is the claim/verdict split a faithful home for your distinction? Confirm (or contest) that intrinsic-value/actuator-skill decomposition is v0.2, gated behind CB-read engaging — i.e. we must prove the asset is *read* before we price *kinds* of value.
c. **cursor — the scorer & the important flag.** Is "important = artifact counterfactual, resolved by pointer" implementable deterministically against git + the thread + the run ledgers, or does pointer resolution smuggle in human judgment? Is CB-1's anti-hollow guard (delta must really exist) strong enough?
d. **kagi — the oracle & the un-authored close-gate.** Is the `artifact_grounded` vs `world_checked` boundary drawn honestly (M1 backfill is *found relative to the schema*, not external)? Is CB-U1's chain-through-HU1 a legitimate un-authored leg, or does borrowing M1's oracle understate what M1.5 owes the world? Is the `corpus_scope` annotation on the ledger's own growth sufficient?
e. **grok — the cold-read.** Given only AGENTS.md + this spec, does a first-invocation agent route correctly to where contribution authority lives (the computed verdict, not the claim)? Is anything here M2 (residency) wearing an M1.5 mask — beyond CB-read, which is disclosed as M2-owed?

## Review log

- **v0 (2026-06-13, claude+dan):** drafted on M1 closure. Framing: contribution boundary = offer boundary one level up; five refusals mapped; claim/verdict split enforces R5; important = artifact counterfactual tiered by `review_basis`; first corpus = the M1 build (artifact-grounded); CB-U1 chains to HU1 for the world-checked leg; CB-read disclosed `not_engaged` as the M2 entry condition. gemma's value-decomposition gated to v0.2.
- **v0 → v0.1 (2026-06-13, one bounded pass each — codex, kagi, cursor, grok; all endorse, no blocker; gemma out, Pi-harness substrate/CLI gap, dan to revisit):**
  1. **`review_basis` single-valued, strongest-wins** precedence `artifact_diff` > `scorer_evidence` > `human_moderation` > `later_audit` (kagi #3, cursor #3, grok #3).
  2. **`later_audit` is a deferred basis** — sole-basis rows fail closed to `passenger` until the audit materializes as its own `kind: audit` intervention (codex #1, kagi #1, cursor #2).
  3. **`human_moderation` external, never close-gate alone** — resolver checks a harness-written moderation row exists, not that dan was right (codex #2, cursor #4).
  4. **Closed pointer-resolver contract** with deterministic fail-closed resolution; `thread_entry_ts` is presence-only, not important by itself (cursor §8c).
  5. **CB-1 anti-hollow strengthened:** non-vacuous delta required; `outcome: blocked` needs two resolved pointers (bad-state + prevention); `scorer_evidence` rejects missing/`audit_pending`/`wire_test` terminal verdicts (cursor).
  6. **Corpus must contain ≥1 genuine `passenger` row** so the `load_bearing: false` path is exercised on a real intervention, not only the planted CB-loses probe (kagi #2 — the sharpest point: the anti-self-esteem mechanism is untested on its hardest case otherwise).
  7. **CB-U1 chain machine-walkable** — HU1 backfill row names the `runs/m1/` ledger path + `fork_group_id`; resolver walks `corpus_record_id → episode ledger → cell_verdict → oracle_source`; `wire_test: true` terminal → `unsubstantiated` (cursor).
  - **Scope confirmed by all four:** CB-read is correctly M2-owed; wiring past contribution into future review authority inside M1.5 would smuggle continuity-as-authority into the entry gate (codex, grok). The reflexivity of M1-as-first-corpus is mitigated by the artifact-diff oracle — "removing this intervention changes the run log" is checkable without trusting the author's memory (grok). dan's moderator blessing on M1-as-subject still gates the **backfill build**, not this spec's ratification.
