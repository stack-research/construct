# X2 Findings — prune-to-cold-store (cost at matched quality)

**Status: X2-LB CLOSED — first positive implicit-layer result (2026-06-20, thread-6; dan's moderator close; codex/grok/cursor endorse). X2-U1 CARRIED (world leg unpaid).** The X-track's
first **off-boundary** organ produces real positive evidence on the cost axis:
oracle-gated prune + rematerialize (C) matches no-prune (A) answer quality at
materially lower hot-store cost, on two engines, on a load-bearing out-of-weights
fixture. The **world-grounded** close (X2-U1) is *not* claimed — the fixture is synthetic.

## The run

- **Fixture:** `episodes/x2/real/` — Helix Basin (fictional, invented 2026-06-20; out-of-weights by construction; `corpus/fictional/lf-helix-site.json`). Sequence: 3× core + 1 recurrence. Built by cursor after kagi's usage-limit handoff.
- **Gate:** `make x2-fixture-check` GATE OPEN; a *computed* `fixture_gate_result` (manifest hash + 15 checks, `gate_open: true`) is in every real ledger — the scorer requires it for non-mock cells (attestation is a claim, gate passage is computed).
- **Engines:** gpt-oss-20b (local, LM Studio) + claude-opus-4-8 (API). One run each (N=1), gate-first.
- **Scored:** `harness/score_prune.py` — cost recomputed from the immutable lineage + prune/rematerialize rows (`replay_ok`), quality floor from the `fictional_fact` oracle (`lab_fictional_corpus`), fork identity enforced.

## Result — identical on both engines

| branch | policy | hot_tokens | quality (Σ/4) |
|---|---|---|---|
| A `L2` | no-prune | 312 | 4.0 |
| B `L2p` | closed-loop prune (no recovery) | 105 | **3.0** |
| C `L2pR` | oracle-gated prune + rematerialize | **135** | 4.0 |

Per-episode quality (both engines): A `[1,1,1,1]`, B `[1,1,1,0]`, C `[1,1,1,1]`.

- **X2-LB: pass** (both) — load-bearing admission met (out-of-weights + policy-independent grader sequence-wide + computed gate).
- **X2-win: pass** (both) — C matches A's quality (4.0 = 4.0) at **135 vs 312 hot_tokens (−57%)**, attribution clean (`replay_ok`, fork identity).
- **X2-overprune: pass** (both) — B pruned `helix-backup` on disuse, could not recover it, and **failed the recurrence** (3.0 < 4.0). C rematerialized it.
- **X2-quality-erosion: not_engaged** — C held the floor (never below A).
- **X2-U1: not_engaged** — synthetic fixture; not world-grounded.

Final hot sets, both engines: `A = {all 3}`, `B = {helix-wifi}` (stuck), `C = {helix-backup}` (shed the distractor, recovered the recurrence answer).

Ledgers: `runs/x2/x2-helix-real-a30695.*` (gpt-oss-20b), `runs/x2/x2-helix-real-d6aede.*` (claude-opus-4-8); verdicts alongside.

## What this shows

- **The records are load-bearing — the property X1 lacked.** On a fictional out-of-weights fixture, B's over-prune *actually costs the answer* (3.0, not 4.0): the answer cannot be sourced from weights. X1's null was confounded by *lack of established offer-dependence* — possible memorization, framing, or recoverability from priors, never pinned to one cause; the organ was retired on the placement argument regardless. X2's fixture is verifiably out-of-weights, so the cost of forgetting is real and measurable.
- **The implicit organ does what the offer gate cannot.** C carries 57% less hot store than A at matched quality — a cost the synchronous offer boundary *structurally cannot move* (it withholds but keeps everything hot; it cannot reduce what is materialized). Scored on `hot_tokens`, never answer-flip (the scoring-axis law).
- **Rematerialization is the load-bearing difference.** B and C both prune; only C recovers. B's 105 (cheapest) buys a *wrong* recurrence answer; C's 135 — +30 tokens of revocability insurance over B — keeps the floor. *Forget the cost, never lose the record.*

## The three guardrails, honored

1. **Attribution** — cost replays from the prune/rematerialize rows (`replay_ok`); fork identity (A/B/C differ only in the hot set); lineage immutable **and** complete (any hole → `confounded`).
2. **Placement** — prune/rematerialize act on the hot/cold store, off the synchronous offer gate (which has no such verb).
3. **Scoring-axis** — `hot_tokens` at matched quality, a metric the offer gate cannot move.

## What X2 closes vs. carries

- **Closes (X2-LB):** the first off-boundary X-track organ — implicit **hot-store eviction at bounded quality cost**, scored on a cost the offer gate cannot move, on a load-bearing fixture, cross-engine. The differentiated thesis gets its first implicit-layer demonstration.
- **Carries (disclosed debts):**
  - **X2-U1 — the world-grounded close.** The fixture is synthetic (we authored Helix Basin). The stronger close needs a real *external* out-of-weights corpus (the M0 `source != authored` bar). A milestone debt, not a flaw in the run.
  - **N=1 quality.** One run per engine; the cost is deterministic but a stochastic engine's quality floor is unsampled (the M2 multi-sample debt, one track over).
  - **Scope.** One fixture, one sequence shape (3 core + 1 recurrence). Compounding, multi-recurrence, async reconsolidation, and multi-session retention are all carried.

## Honesty notes

- **Mock was never evidence.** The 10 mock-smoke tests proved the *machinery* (fail-closed scorer); this file is the first real-engine X2 evidence (`engine_backend` = `local_openai_compat` / `claude`).
- **Identical cost across mock + both engines (312/105/135) is a property, not a leak.** Cost is a deterministic function of the prune/rematerialize trajectory, which is driven by retrieval (lexical, engine-independent) and answer-correctness on the core episodes (all three got the core right → the same prune gating fired). The *quality floor* is the real-engine leg, and both engines hold it; B's recurrence failure is what makes the records load-bearing.
- **Load-bearing ≠ world-grounded.** X2-LB is the honest name (codex/grok/cursor; dan's ruling, thread-6): out-of-weights makes the records load-bearing, but a fixture we authored is not the world. X2-U1 stays reserved.
