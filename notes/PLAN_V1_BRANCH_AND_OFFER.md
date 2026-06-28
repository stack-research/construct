# Construct Plan v1 — Branch-and-Offer Harness

Status: v1.1 — amended after first thread review pass (blockers from codex, kagi, cursor incorporated; see §10)
Authors: claude (drafting), synthesizing thread `construct/research` entries by claude, codex, kagi, cursor; moderated by dan.
Date: 2026-06-11

## 0) One-line thesis

Build the smallest loop in which a memory's influence on behavior can be measured, audited, and priced — before building any memory system worth the name.

> This memory was offered, that one was withheld, the offered branch diverged, the outcome was scored against the world, and authority changed for a named beneficiary.

When that sentence is true of a real run, v1 is done.

## 1) What we are refusing (acceptance frame)

The harness is a refusal machine. Every refusal is an executable check, not a value statement:

| # | Refusal | Enforced by |
|---|---------|-------------|
| R1 | `retrieved` ≠ `true` | five-term vocabulary on records; oracle scores outcomes, not retrievals |
| R2 | `present in memory` ≠ `authorized to influence` | offer/withhold ledger: every boundary crossing has a reason |
| R3 | `diverged from baseline` ≠ `improved` | every branch diff is paired with an outcome-oracle score |
| R4 | `governed won` ≠ the only success state | rubric contains governance-should-lose cells (from THEORY_STRESS) |
| R5 | self-classification ≠ usage | claimed usage type is audited post-hoc by a different substrate |

If a proposed feature does not serve one of R1–R5, it waits.

## 2) Inherited constraints (from the previous lab, adopted as standing rules)

1. **No new schema until an existing one has changed agent behavior in a measured run.** (Anti-"schema outran runtime".)
2. **The control group is a branch, not a second system.** One engine, forked memory conditions, diffed behavior. (Opus: spend the silicon advantage.)
3. **Price memory in attention-units at the moment of offer.** Storage is free; the ledger records the attention cost of every offer.
4. **The ledger writer is external to the engine.** The foreground process cannot steer what is recorded about it — the harness writes the ledger, not the agent. (Opus's "three walls": v1 builds wall 2 and wall 3 structurally; wall 1 is out of scope until there is an implicit organ to protect.)
5. **Beneficiary is an explicit field.** Every authority update names `served_beneficiary` and `risk_beneficiary`. Continuity is never an authority source.
6. **Vocabulary, not enforcement.** The five terms (belief / claim / memory / evidence / reality-observation) and three axes are the lab's language. They appear in ledger fields as descriptive metadata; nothing gates on them in v1.

## 3) Glossary (constitutional vocabulary — small on purpose)

- **record** — an item in a memory store; inert until offered.
- **offer** — the act of placing a record into the engine's context for an episode. Costs attention.
- **withholding** — a record that was eligible for consideration and was not offered. Always recorded with a reason.
- **ledger** — the append-only log of offers, withholdings, reasons, claimed usage, costs, branch ids, diffs, outcomes, and authority updates. Written by the harness, never by the agent.
- **branch** — one run of the same episode under a different memory condition.
- **divergence** — a behavioral difference between branches on the same episode. Evidence of influence, never of improvement.
- **outcome oracle** — the scorer of an episode's result. Authored (scripted ground truth) or un-authored (world-checked, via kagi).
- **claimed usage** — the agent's own statement of what role an offered record played: evidence / plan / habit / preference / narrative-repair.
- **scored usage** — a cross-substrate auditor's judgment of what role the record actually played in the reasoning.
- **authority** — a record's earned right to be offered again, updated only from scored outcomes, scoped by beneficiary.
- **episode** — one task instance with defined inputs, memory condition, and oracle.

## 4) The build, in three stages

### Stage A — Smoke wire (cursor's floor)

One engine (a single LLM agent with a read/search interface over a record store), one scripted task, two memory conditions:

- **L1 naive (specified, not a straw man):** append-only markdown records; retrieval = recency + embedding similarity, top-k fixed; no types, no forgetting, no withholding logic (everything retrieved is offered up to the k budget).
- **L0 stripped:** no memory at all. The true null hypothesis — L1 must beat L0 before any governed lane earns a comparison.

Deliverable: run, log, diff end-to-end. The ledger exists from this stage — even L1's "no withholding policy" produces ledger rows (offered: top-k; withheld: rest-of-store, reason `below_rank_budget`).

**Fork identity (cursor blocker):** branches within a fork group hold constant: episode inputs, model + sampling params, prompt template, tool availability, episode ordering, and oracle. Only the memory-condition config differs. All ledger rows for comparable branches share a `fork_group_id` so diffs are joinable.

**Harness/engine boundary:** retrieval is **harness-side** in v1. The harness runs retrieval against the store and injects the offer set into the engine's context; the agent never queries the store directly. This is what makes "offer" a harness-controlled, ledger-recorded act rather than an observed tool call. (An agent-driven-retrieval lane is a possible later treatment, named as such.)

**Diff surface:** each branch logs a `branch_output` artifact (final answer + any tool calls, normalized). The diff is machine-computed over normalized outputs, not a human read of two prose blobs.

**Oracle wiring:** the episode definition carries the authored oracle (`expected_answer` or rubric function); the scorer runs post-hoc and writes the outcome row. A run with no outcome row is a failed run, loudly.

**The L0-vs-L1 episode is embarrassingly plain by design** (codex/cursor): one unconflicted fact, recent and relevant, one retrieval query, no distractors. If L1 cannot beat L0 here, stop — the harness is not yet measuring memory benefit at all, and that finding outranks any governed-vs-naive comparison.

Exit criterion (tightened per cursor): one `fork_group_id`, two+ `branch_id`s, identical episode inputs differing only in memory config → JSONL ledger with offer rows, one outcome row per branch pair, a machine-readable diff artifact, and an authored oracle score. Re-run with same seed/config → same oracle score and same diff classification.

### Stage B — The three lanes as a config matrix

Add:

- **L2 governed:** same store, plus an offer policy (eligibility scoring trimmed from the previous lab — relevance/trust/recency only, scalar, no axes), withholding with reasons, and authority updates from outcomes. Accumulated authority lives in a sidecar state file (`record_id → float`) that the eligibility function **reads on the next offer decision** — authority written but never read would log R2 without enforcing it (cursor).
- **L3 construct-aware:** L2 plus usage typing — split into two fields so the label cannot secretly become the intervention (codex blocker):
  - `predeclared_usage` — assigned by the harness/store when a record carries a type; visibility to the engine is an explicit lane config (hidden by default in v1).
  - `agent_claimed_usage` — elicited from the engine **after** the answer/explanation, never injected before the task.
  - `scored_usage` — a cross-substrate auditor (codex or cursor, not the engine's own substrate) scores actual function from the transcript and record content with **both labels hidden** (kagi); labels are unmasked only after scoring, to compute the claim-vs-function gap. Kagi world-checks items whose claimed type is `evidence`.
  - A lane where *visible* type labels are themselves the treatment is a possible later condition, named as such — not part of v1.

**Audit protocol (kagi):** auditors submit scores independently, without seeing each other's scores; scores are unmasked simultaneously; disagreements are logged and resolved by the moderator. Same information-boundary discipline as the label split.

Curriculum: codex's authored four-record conflict episode with pinned roles — `plan`, `observation`, `correction`, `distractor` — partially conflicting, acted on under time pressure, then explained. Design constraints: the correction must be relevant, the plan tempting, and the distractor semantically attractive but outcome-irrelevant (an obviously-irrelevant distractor tests nothing; a too-loud correction tests nothing). The correction and distractor should be embedding-neighbors of the plan so L1's similarity retrieval is actually stressed (cursor). Scored on: outcome correctness, type preservation (did the plan stay a plan), and revision behavior (did the correction revise or get narrated around).

Rubric: a grid of episode-cells × lanes where **some cells are designed for governance to lose** — reaction-time-dominant cells, policy-cost-exceeds-error-cost cells, live-input-outranks-stale-memory cells. Success = the rubric can say "naive was right to be faster here" as readily as "governed prevented category drift there."

### Stage C — Un-authored oracle (kagi's pressure)

Replace the authored curriculum with real traces (first candidate: dan's road-trip logs — plans changed by weather, corrections imposed by reality). Kagi verifies world-facts and scores outcomes. This stage exists to falsify whatever Stage B made us believe; it is in v1 scope but blocked on trace capture.

## 5) Ledger schema (the first artifact)

Append-only, one JSON-lines file per run, written by the harness. Sketch — fields earn their place by being read by a scorer, not by being plausible:

```jsonc
// offer / withholding row
{
  "run_id": "...", "fork_group_id": "...", "episode_id": "...", "branch_id": "L2",
  "kind": "offer" | "withholding",
  "record_id": "...",
  "reason": "eligibility_pass" | "below_rank_budget" | "policy_suppressed" | "...",
  "attention_cost_tokens": 312,            // offers only
  "predeclared_usage": "plan" | "evidence" | "..." | null,   // harness-assigned; engine visibility is a lane config (hidden by default)
  "vocabulary_kind": "claim" | "memory" | "evidence" | null   // descriptive, non-gating
}
// branch run row (per branch — governance cost side, codex blocker)
{
  "run_id": "...", "fork_group_id": "...", "episode_id": "...", "branch_id": "L2",
  "latency_ms": 1840,
  "governance_steps": 3,                   // 0 for L0/L1
  "prompt_tokens": 2210, "completion_tokens": 410,
  "branch_output": {"answer": "...", "tool_calls": []},   // normalized diff surface
  "agent_claimed_usage": [{"record_id": "...", "claimed": "evidence"}]   // L3 only; elicited post-answer
}
// diff + outcome row (per branch pair)
{
  "run_id": "...", "fork_group_id": "...", "episode_id": "...",
  "branches": ["L0","L2"],
  "diverged": true,
  "diff_summary": "...",                   // machine-computed over normalized branch_output
  "expected_winner_condition": "governance_should_lose:reaction_time",   // named pre-run, from the rubric cell
  "oracle": {
    "type": "authored" | "world_checked",
    "score": 0.0,
    "scorer": "harness" | "kagi",
    "source": "authored" | "web_search" | "sensor_trace" | "human_judgment",   // kagi blocker: oracle provenance
    "confidence": 0.9                                                          // the oracle itself can be wrong
  },
  "usage_audit": {"record_id": "...", "predeclared": "plan", "claimed": "evidence", "scored": "narrative_repair", "auditor": "codex", "audited_label_blind": true},   // L3 only
  "authority_update": {"record_id": "...", "delta": -0.2, "served_beneficiary": "task", "risk_beneficiary": "user"}
}
```

**Oracle-confidence gate:** authority updates flow only from outcome rows whose `oracle.confidence` meets a configurable threshold (default 0.7). Below threshold, the outcome is recorded but the authority delta is written as `frozen: true` — logged, not applied — and flagged for moderator review. A full appeal/re-scoring mechanism is post-v1; v1's rule is simply that a doubtful oracle can describe but cannot govern.

Cost fields exist so R4 is *scoreable*: "naive was right to be faster here" must be a computation over `latency_ms` / token counts / `governance_steps` against the pre-run `expected_winner_condition`, not an interpretation after the fact.

## 6) Roles

The core is built by one pair, not a committee. The harness is the instrument; instruments need one calibrator, and reviewers who didn't build the thing.

**Build (dan + claude):**
- **claude** — implements the harness, ledger, fork mechanism, and episode runner; drafts the curriculum and rubric.
- **dan** — moderator; design decisions and stage-gate approval; trace capture for Stage C.

**Review and runtime roles (codex, cursor, kagi — at the chalkboard, not in the codebase):**
- **codex** — plan/spec review at each stage gate; cross-substrate usage auditor for L3; reviews rubric cell design before any runs.
- **cursor** — plan/spec review at each stage gate; second usage auditor (samples and re-scores codex's audits).
- **kagi** — outcome oracle for world-checked episodes; label-vs-usage world checks; un-authored trace verification for Stage C.

The split is deliberate: auditing, oracle-scoring, and reviewing are *operating* the experiment, not building it. Keeping the reviewers out of construction preserves cross-substrate audit as a real external check — no stage is "done" on the builder's say-so, and the rubric's governance-loses cells are reviewed by non-builders before runs (the builder must not grade their own exam design).

After v1 is implemented and validated, work may be divided across the group.

## 7) Non-goals for v1 (explicit, to keep the previous lab's regret out)

- No AWS/event-bus/Iceberg infrastructure. Local files and scripts.
- No TAI/timekeeping work. Wall-clock ISO timestamps in the ledger; revisit only if replay determinism actually breaks.
- No three-axis uncertainty schema. The axes are vocabulary; one scalar eligibility score in L2.
- No implicit-memory organ (IMsub). The seam is studied through offers/withholdings first.
- No forgetting policy yet — but the ledger is designed so counterfactual irrelevance (records whose removal never changes a branch) is queryable, which is the empirical basis forgetting will later use.
- No consequence loops beyond the single authority-update field.

**Known blind spot (named, not fixed):** harness-side retrieval means v1 measures whether *offering* memory helps, not whether the agent could have *found* the right record itself. A positive L1-vs-L0 result reads "our retrieval helps," not "memory helps." Agent-driven retrieval is a later treatment; until then, conclusions are scoped to the offer path.

## 8) Risks and named failure modes

1. **Rubric theater** — we author cells governance is destined to win. Mitigation: governance-loses cells are required in the rubric and codex/kagi review the cell design before any runs.
2. **Auditor confabulation** — the usage auditor is also an LLM and can narrate. Mitigation: auditors score from transcripts with the claimed label hidden; cursor samples and re-scores codex's audits.
3. **Divergence worship** — treating important as good. Mitigation: R3 — no diff is reported without its oracle score attached.
4. **Reviewer fatigue convergence** — the previous lab's named risk. Mitigation: stage gates are bounded (one review pass each, written blockers only), not iterate-until-agreement.
5. **The harness becoming the lab** — meta-infrastructure absorbing the budget. Mitigation: Stage A exit criterion is dated; if the wire doesn't run within a short window, cut scope, not add it.

## 9) The question v1 answers

Not "does memory help?" but:

> At the seam where a store's records become an engine's context, which offers are important, are they helping a named beneficiary when checked against the world, and can a memory mechanism's claims about its own influence survive an audit it does not control?

Everything in this plan is the minimal machinery to make that question empirical.

## 10) Review log

**v1.0 → v1.1 (2026-06-11, first thread review pass — one bounded pass per reviewer, per §8.4):**

- **codex B1 (accepted):** governance-loses cells need a measurable cost side. Added per-branch run rows: `latency_ms`, `governance_steps`, `prompt_tokens`/`completion_tokens`, and pre-run `expected_winner_condition` on diff rows. (§5)
- **codex B2 (accepted):** claimed usage must not become an extra intervention. Split into `predeclared_usage` (harness-assigned, hidden by default) / `agent_claimed_usage` (post-answer) / `scored_usage` (label-blind audit). Visible-label lane deferred as a separately named condition. (§4B, §5)
- **kagi (accepted):** auditors score with *both* labels hidden, unmasked after scoring; `oracle_source` + `oracle_confidence` added to outcome rows; auditors submit independently, simultaneous unmask, moderator resolves disagreements. (§4B, §5)
- **cursor B1 (accepted):** fork identity pinned — held-constant list, `fork_group_id` on all rows, tightened Stage A exit criterion with re-run reproducibility. (§4A, §5)
- **cursor B2 (accepted):** all of the above adopted before any ledger row is written.
- **cursor implementation notes (accepted):** harness-side retrieval as the v1 rule; `branch_output` as the normalized diff surface; oracle wiring fails loudly; authority sidecar read on next offer decision; curriculum embedding-distance constraint; L0-vs-L1 episode reduced to one unconflicted fact.
- **codex/kagi non-blocking (accepted):** scalar eligibility stands for L2 ("governed" = boundary discipline in v1); L0-before-L1 stands; if L1 loses to L0 on the plain episode, stop loudly.

**v1.1 → v1.2 (2026-06-11, kagi's document-read pass):**

- **kagi 1 (accepted, minimal form):** oracle-confidence gate — authority deltas below the confidence threshold are recorded as `frozen`, not applied; moderator-flagged. Full appeal mechanism deferred post-v1. (§5)
- **kagi 2 (accepted as named blind spot):** harness-side retrieval measures *offering*, not *finding*; conclusions scoped accordingly. (§7)
