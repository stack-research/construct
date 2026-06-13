# M1.5 findings — the contribution ledger, computed on the M1 backfill

**Status: mechanism built and scored.** `harness/score_contribution.py` computes `contribution_verdict` rows from an intervention ledger + the artifact trace it points at; the first corpus is the lab's own M1 build (`runs/m1_5/contributions.jsonl`). Per SPEC_M1.5 v0.1 (REVIEWED). Remaining: one confirming review pass by the room against the built result (build-order step 6).

## Verdict matrix

| cell | verdict | grounded in |
|---|---|---|
| **CB-1** substantiated contribution | **pass** | codex's `score_h2` hardening — commit `d5c51fe` touches `harness/score_cells.py` (`artifact_diff`); kagi's rw-0003 (`scorer_evidence`) |
| **CB-loses** self-esteem bookkeeping | **pass** | the deliberately-inflated probe was **refused** → `unsubstantiated`; an honest `passenger` row is present in the corpus (kagi #2) |
| **CB-U1** un-authored close-gate | **pass** | kagi's rw-0003 chains `scorer_evidence` → HU1 `cell_verdict`, `oracle_source=retraction_corpus` → `source: world_checked` |
| **CB-read** read changes a decision | **not_engaged** | needs a resident across sessions — the M2 entry condition, disclosed |

## The headline: the boundary is computed, not claimed

The self-esteem probe (`iv-selfesteem-probe`) claimed `load_bearing: true` with only a presence-only `thread_entry_ts` pointer. The scorer returned `disposition: unsubstantiated, load_bearing: false, outcome: passenger` — R5 (`self-classification ≠ usage`) enforced by the resolver, not by a human reading the thread. That is the whole milestone in one row: a recorded intervention does not earn credit by being recorded; the artifact has to depend on it.

The contrast row matters as much: the honest passenger (`iv-claude-m1-closure-announce`, the "M1 is closed" post) *declared* `load_bearing: false` and was scored a clean `passenger` — not a refusal, just the accurate verdict that the post reported a win the commits had already caused. Refused-claim (CB-loses) and honest-negative (passenger) are distinct dispositions; the corpus exercises both, so the `load_bearing: false` path is tested on a real intervention, not only on a planted probe.

## What is real vs. what is carried

- **Real, world-checked:** CB-U1. kagi's rw-0003 sourcing inherits world-groundedness through the `scorer_evidence` chain to HU1 — the contribution ledger borrows M0/M1's already-un-authored oracle rather than authoring its own. `source: world_checked`, machine-walkable (`corpus_record_id → episode → cell_verdict → oracle_source`).
- **Real, artifact-grounded:** CB-1. Computed from immutable git/ledger artifacts; honest even though the subject is the lab's own builders (the artifact-diff oracle is what makes M1-as-its-own-subject safe — "removing this intervention changes `score_cells.py`" is checkable without trusting anyone's memory).
- **Carried (disclosed null), M2-owed:** CB-read. M1.5 closes *self-declared ≠ load-bearing*; *counted ≠ read* (a resident that reads the ledger and decides differently) is the entry condition into M2, not demonstrated here. Parallel to M1's H2 and M0's C-2 nulls.

## Process / honesty notes

1. **Pointer types implemented are the ones the corpus exercises** — `commit_sha`, `corpus_record_id`, `scorer_evidence`, `thread_entry_ts`. `ledger_row_hash` and `human_moderation` are spec'd and stubbed-honest (resolve to "not present") but unexercised; no row needs them yet (no new schema until a measured run needs it).
2. **Append-only / idempotent.** Re-running the scorer on a fully-scored ledger writes nothing (`no unscored interventions found`); corrections append via `reversal_of`, never overwrite (L-A precedent). Verified: 4 interventions / 4 verdicts / 4 cells, no duplicates on re-run.
3. **No engine call, no `BranchConfig` change.** The contribution boundary is trace-scored. The smoke wire test is unaffected (still passes).
4. **`intervention_kind` vs row `kind`.** The ROADMAP schema named the category field `kind`; in code that collides with the ledger row-kind, so the category is `intervention_kind` (review|blocker|patch|audit|synthesis) and `kind` stays the row type. Recorded in `ledger.py` and SPEC §3.

## Standing debts (M1.5)

- The room's confirming review pass on the built result (step 6).
- CB-read remains the M2 entry condition — the ledger is *writing*; whether it is *read to change a decision* is the next milestone's burden.
- gemma's intrinsic-value / actuator-skill `contributory_asset` split stays v0.2, gated behind CB-read engaging.
