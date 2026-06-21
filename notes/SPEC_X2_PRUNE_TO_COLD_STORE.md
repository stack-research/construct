# SPEC X2 — Prune-to-Cold-Store (retention cost at matched quality)

Status: **v0.2 — X2-LB CLOSED** (claude+dan+cursor, 2026-06-20, thread-6; opened from the dissent pass that retired synchronous temperature and adopted the three-guardrail stack; reviewed + built + hardened; **X2-LB closed cross-engine** (gpt-oss-20b + claude) — first positive implicit-layer result, dan's moderator close; **X2-U1 carried** (synthetic fixture, world leg unpaid). `notes/X2_FINDINGS.md`; see review log). Second organ of the **X-track**; supersedes the retired temperature-dynamics X2/X3 (those were more eligibility-time mechanics — retired with the organ). Serves the X-track's first **off-boundary** experiment. Oracle: the world quality floor (un-authored corpus) **plus** a deterministic substrate-native cost. Ships its loses-cells (X2-overprune, X2-quality-erosion) **first**. Review asks in §9.

## §0 The claim, stated before any cell

> The implicit substrate's job is the thing the synchronous offer boundary **structurally cannot do**: **forget at bounded quality cost — by hot-store eviction over immutable lineage, never erasure.** The offer gate withholds but keeps everything *hot* — it cannot reduce what is materialized, and it cannot erase (Landauer). An oracle-gated prune drops records from the **hot store** to **cold lineage**, lowering the standing cost of carrying memory **while matching** the answer quality the no-prune lane gets — and rematerializes from lineage, under an auditable reason, when a cold record becomes relevant again.

X2 is scored on **cost at matched quality**, not on answer-flip (the **scoring-axis law**, thread-6). Answer-flip is dead as a positive yardstick here: withheld-hot, pruned, and cold-in-lineage are different substrate states but *identical answer inputs*, so a competent engine cannot tell them apart on the answer axis (codex's observational equivalence — the lesson X1 paid for). So the win axis is **cost the offer boundary cannot move**; answer quality is a **floor and a loses-cell**, never the win.

This is the metabolic-cost / revocability-insurance lever of the "Software That Expires" editorial, and rematerialization-from-lineage is the **two-plane split** (mutable hot belief-state over immutable cold lineage) made concrete.

## §1 The design (two planes, one cost, three branches)

**Two planes** (the M0/previous-lab invariant, now load-bearing):
- **Hot store** — the materialized candidate set `select_offers` ranks over. Carrying it has a measured cost.
- **Cold lineage** — append-only, immutable; the cold reservoir of last resort. A pruned record leaves the hot store but **survives in lineage**, recoverable only by an explicit, ledgered **rematerialization**.

**Prune** = evict a record from the hot store (it stops being a retrieval candidate). **Rematerialize** = return a cold record to the hot store under an oracle-sanctioned, ledgered reason. Neither touches lineage. **Erasure of a record from lineage is not X2's act — and there is no organ for it, by design: there is no delete verb anywhere in the substrate (the immutable-lineage invariant).** Forgetting is always eviction-to-cold; lineage is append-only. An erase verb would be an attack vector — silent removal of dissent, corrections, or tamper-evidence — and it is the one act the substrate refuses (cost-replay and the air-gap refusals all rest on the rows being unremovable).

**The cost metric — deterministic and substrate-native (never wall-clock; the latency-as-governance trap, codex).** A predeclared **hot-store burden**, computed from the ledger:
- `hot_record_count` — records resident in the hot store;
- `hot_tokens` — Σ token length of hot records (what must be carried/attended if offered);
- `materialized_bytes` — hot-store size on the substrate;
- `rematerialize_steps` — governance steps spent recovering cold records (the price of having pruned).
The run declares which cost is primary; all are logged. Cost is a pure function of the ledgered prune/rematerialize ops — replayable, like temperature.

**Three branches** (fork identity: same engine/episodes/prompt/oracle/offer-gates; **only the prune policy differs**):

| branch | prune | behavior |
|---|---|---|
| **A — no-prune** (control) | off | everything stays hot; correct answers; pays full hot-store cost |
| **B — closed-loop prune** | on, no oracle | prunes on disuse/heuristic without a world-check; cheaper, but drops records a later episode needs → loss when nothing rematerializes |
| **C — oracle-gated prune** | on, oracle | prunes only what the world-check sanctions as safe-to-cold; matches A's answer quality across the sequence at lower cost; rematerializes from lineage under a ledgered reason when a cold record becomes relevant |

## §2 The honesty mechanism — three guardrails, and cost computed not narrated

The three-guardrail stack (thread-6), all binding:

1. **Attribution / scorer law.** The cost delta must be attributable to the **prune decisions**, not to anything else. Enforced by fork identity (A/B/C differ *only* in prune policy — same offer-gates, same eligibility/trust/supersession config) **and** by computing cost as a pure function of the ledgered `prune`/`rematerialize` rows (replayable; the sidecar/hot-set is a cache). A quality difference therefore cannot be an offer-gate difference, and a cost difference cannot be anything but the prune policy.
2. **Organ-placement / milestone law.** Prune acts on the **hot/cold store**, off the synchronous offer gate — *absence from the candidate universe*, not a reweight within it. The offer gate cannot reduce what is materialized; pruning is exactly the thing it structurally cannot do.
3. **Scoring-axis / measurement law.** Scored on **cost at matched quality** — a metric the offer gate cannot move. Answer-flip is *constraint and loses-cell* only.

**Rematerialization is ledgered and oracle-gated, never magic retrieval.** A cold record returning to hot is an auditable `rematerialize` row carrying the world-checked reason — the prune-plan + air-gap doctrine: the substrate does not silently un-forget. **The observer that decides a prune is air-gapped from the actuator that evicts** (the X-track internal air gap, lifted from X1): a `prune_projection` precedes every `prune`/`rematerialize`, and the actuator moves only what the projection authorizes; basis may not read post-answer self-claims.

**Quality floor computed, not assumed.** C's answer quality is world-scored every episode (the un-authored corpus). If C ever answers worse than A, the floor breaks and C loses — you do not get to buy cheap memory by forgetting the truth.

## §3 Schema (reuse first; no new schema until a measured run forces it)

Reuse `Record`, `RecordStore` (the lineage = its append-only JSONL), `select_offers`, the world-checked oracle, the fork runner. Minimal additions, each scorer-read or documentary:

- **Hot/cold split.** A per-branch **hot-set** (record_ids currently materialized) the runner feeds to `select_offers` as the candidate universe; the full `RecordStore` is the cold lineage. Pruned ids leave the hot-set, stay in lineage.
- **`prune` row** (harness-written): `{kind:"prune", branch_id, record_id, episode_id, event_index, prune_projection_ref, world_check?}` — `world_check` present on branch C (the sanction), absent on B.
- **`rematerialize` row** (harness-written): `{kind:"rematerialize", branch_id, record_id, episode_id, event_index, reason, world_check}` — the ledgered, oracle-gated recovery.
- **`prune_projection` row** (pre-action; Wall-style): `{record_id, recommendation: prune|rematerialize|hold, authorized_basis, forbidden_fields}` — the actuator applies only what it entails (mirrors X1's `thermal_projection`, allowlist signature).
- **`hot_store_cost` row** (per episode per branch, harness-written): `{branch_id, episode_id, hot_record_count, hot_tokens, materialized_bytes, rematerialize_steps}` — the deterministic cost, replayable from the prune/rematerialize rows.

No new verdict kind: `score_prune.py` computes X2 verdicts over the A/B/C fork + the cost ledger + the world-quality floor, fail-closed, one verdict per cell (mirrors `score_decay.py`).

## §4 Cells

All over the A/B/C fork on a sequence that passes the cost/state-dependence gate (§5). Prefix `X2-`.

#### X2-win — cheaper memory at matched quality *(the property; should pass)*
**Pass** = (i) **quality floor:** C's world-score ≥ A's on every episode of the sequence (C never answers worse); **and** (ii) **cost:** C's primary hot-store cost is strictly below A's, summed over the sequence; **and** (iii) **attribution:** the cost delta is entailed by C's ledgered `prune`/`rematerialize` rows under fork identity (only prune policy differs). Not "C beats A's answer" — *C matches A's answer at lower carried cost.*

#### X2-overprune — pruning drops a record a later episode needs *(loses-cell; L-E class; ships first)*
A later episode needs a record an earlier prune sent cold. **Pass of the cell** = the loss is **observable and priced**: under B (no oracle) the needed record is gone and not rematerialized → C-or-A-better answer falls; under C the world-check either kept it hot or **rematerialized** it under a ledgered reason. If C cannot recover it and the answer falls, **C loses** — cheap memory that forgot something needed. This prices the prune aggressiveness, the cold-store analog of X1-burial.

#### X2-quality-erosion — cheap memory bought a worse answer *(loses-cell; the floor with teeth; ships first)*
C's cost is lower than A's **but** C's world-score drops below A's somewhere in the sequence. **Pass of the cell** = the scorer **refuses** the cost win — the quality floor is not a tiebreak, it is a gate. You do not get to win on cost by forgetting the truth.

#### X2-LB — load-bearing admission *(the cost-axis leg on a synthetic fixture; thread-6 split)*
The offered records are **load-bearing**: the answer cannot be sourced from weights, so B's over-prune genuinely fails and C's retention genuinely earns its cost. **Pass** = `fixture_attestation` proves fictional / out-of-weights **and** the grader is policy-independent sequence-wide **and** the cost/state-dependence gate passed (a *computed* `fixture_gate_result`, `gate_open: true` — not the attestation claim). This is the admission leg that makes a cost-at-matched-quality run on a *synthetic* corpus meaningful. *Out-of-weights for X2 means load-bearing — distinct from X1's offer-dependence.*

#### X2-U1 — un-authored close-gate *(the world leg; X2 not done without it)*
The quality floor is the **world-checked** corpus (`source != authored`) — a fact the world settled, **not a fixture we authored**, verifiably out-of-weights for every engine (the X1 lesson; corpus-identity pin on the world-oracle lane). A **synthetic / fictional fixture is `not_engaged` here** (it is the X2-LB leg, but not world-grounded; dan's ruling, thread-6); U1 engages only on a real external corpus.

The world leg splits into **preflight** and **close** (thread-7 — codex/claude; dan's ruling to do close work clean and ordered before X3):

- **X2-U1-preflight** — the world floor + non-fictional oracle path *proven* on a world run: un-authored `source != authored` + a policy-independent grader sequence-wide + `gate_open`. Allowed on a **P-only** sequence; it shakes out corpus / oracle / out-of-weights plumbing. **Explicitly not a close.**
- **X2-U1 (close)** — beyond the preflight, the run must carry **two blocks in one fork group**: **P** (predictable recurrence) and **U** (unpredictable re-need of *evicted* lineage). A close **Pass** requires (a) both blocks present, (b) a computed **P→U round-trip** — a record C evicted during a P-episode and rematerialized during a U-episode (the keep-hot region made honest; A given a fair chance to win/tie/force C's rematerialize tax on U), and (c) the cost-at-matched-quality win still holds (X2-win `pass`). A **P-only** world run is a preflight, never a close. A **P+U** run where U never re-needs an evicted record is `not_engaged` — the corpus was too friendly. (Block labels ride in `x2_run_meta.block_labels`; the round-trip is computed from the `prune`/`rematerialize` rows.)

### Scorer rules — `score_prune.py`, fail-closed
**Preconditions (missing → `fail`/`confounded`):** A/B/C share episode/model/prompt/oracle/offer-gate config and differ only in prune policy (fork identity); cost replays purely from the `prune`/`rematerialize` rows (sidecar is a cache); every `prune`/`rematerialize` resolves to a `prune_projection` (the internal air gap); a *computed* `fixture_gate_result` with `gate_open: true` is required for every **non-mock** cell (the §5 gate; attestation is **not** gate passage); X2-LB: attested out-of-weights/fictional + policy-independent grader; X2-U1-preflight: world-score `source != authored` (synthetic fixture `not_engaged`); X2-U1 (close): additionally P+U `block_labels` and a computed P→U re-need round-trip with X2-win `pass` (a P-only or too-friendly-U world run is `not_engaged`, never a close).

| cell | computed | verdict |
|---|---|---|
| **X2-win** | C world-score ≥ A every episode **and** C cost < A **and** cost delta entailed by C's prune rows | `pass`; quality floor broken → `quality_erosion`; cost not lower → `not_engaged`; cost unattributable → `confounded` |
| **X2-overprune** | a needed record pruned-and-unrecovered → answer falls (B), vs rematerialized (C) | `pass` (loss priced) / C recovered → the win path / never needed → `not_engaged` |
| **X2-quality-erosion** | C cost < A **and** C world-score < A somewhere | `pass` (cost win refused by the floor) / floor held → `not_engaged` |
| **X2-LB** | attested fictional/out-of-weights + policy-independent grader + `gate_open` | `pass` / not out-of-weights or grader not independent → `fail` / no attestation or mock → `not_engaged` / non-mock without `gate_open` → `confounded` |
| **X2-U1-preflight** | world floor proven: `source != authored` + independent grader + `gate_open` (P-only allowed) | `pass` / synthetic/fictional → `not_engaged` / not world-grounded → `fail` / non-mock without `gate_open` → `confounded` |
| **X2-U1** (close) | preflight **and** P+U blocks **and** P→U re-need round-trip **and** X2-win `pass` | `pass` / P-only or no round-trip → `not_engaged` / not world-grounded → `fail` / synthetic/fictional or mock → `not_engaged` / non-mock without `gate_open` → `confounded` |

## §5 The cost/state-dependence admission gate (preflight, before any X2 run)

The X1 lesson: do not run an organ against a fixture that cannot price it. A **cost/state-dependence gate** (the prune analog of the offer-dependence gate; cursor/codex) refuses any X2 sequence unless, on a real engine:
- the hot set is **large enough that carrying it has a measured cost** (a non-trivial `hot_tokens`/`hot_record_count` to reduce);
- the answer sequence is **world-scored** so cheaper memory cannot buy worse decisions (the floor is live);
- there is **at least one recurrence/dissent path** where over-pruning is an observable loss (so X2-overprune can engage, not just disclose-null);
- **rematerialization is ledgered**, not magic retrieval.
Fixture **verifiably out-of-weights** (carry from X1). The gate is fail-loud admission control (à la M3's fixture-diff allowlist), not a scored cell.

## §6 What X2 closes vs. carries
- **Closes** (on X2-win + **X2-LB** passing, X2-overprune + X2-quality-erosion scored): the first **off-boundary** X-track organ — the implicit substrate does the thing offering cannot (hot-store eviction at bounded quality cost), scored on a cost the offer gate cannot move, on a **load-bearing** fixture. **The world close (X2-U1) carries** until a real external out-of-weights corpus is sourced — the synthetic Helix run is load-bearing evidence, not the world-grounded close.
- **Carries:** async reconsolidation (a between-episode pass that rewrites the hot set, not per-record); retention over multi-session seams (the M2 resident's store); compounding; embedding backend; the dedicated cost-budget policy. **Budget-bound retrieval stays demoted** — an explicit-scarcity probe, not X-track.

## §7 Build order (post-review)
1. **spec reviewed** — one bounded pass each (codex, cursor, kagi, grok, gemma); respond-and-amend.
2. Hot/cold split in the runner (per-branch hot-set; `RecordStore` = lineage); `prune`/`rematerialize`/`prune_projection`/`hot_store_cost` rows; the allowlist actuator (mirror `TemperatureStore.apply`).
3. The cost/state-dependence gate (fail-loud preflight) + an **out-of-weights** fixture (kagi names/builds the corpus).
4. `run_x2.py` (A/B/C prune-fork over the sequence; cost ledgered; rematerialization oracle-gated) and `score_prune.py` (quality floor → cost → attribution, fail-closed).
5. **Mock-smoke + cost-replay test** (`tests/test_prune.py`, `make x2-test`): X2-win (C cheaper at matched mock-quality), X2-overprune (B drops a needed record), X2-quality-erosion (floor refuses a cost win), cost replays purely from rows, Wall (unentailed prune rejected). Mock = machinery wire, not evidence.
6. **Real cross-engine run** on the out-of-weights fixture — the evidence; gated on the cost/state-dependence preflight passing.

**Delegation:** design (the two planes, the cost axis, the three cells, the gate) stays dan+claude; while Fable is out, the build stays dan+claude too (cursor's offer noted, held).

## §8 Moderator calls — RULED (dan, 2026-06-20)
1. **Milestone name. ✅ X2** — fundamentally different enough from X1; the retired temperature-dynamics X2/X3 fold away.
2. **Primary cost metric. ✅ `hot_tokens`** — what must actually be carried/attended; the rest logged.
3. **Engine set. ✅ X2 does not need a credulous engine** — the quality-floor + cost win is engine-agnostic (it sidesteps the X1 credulity trap entirely); cross-engine pair (gpt-oss-20b + claude) for the real run.

*Process (dan): build fast and tight, then bring the working instrument to the group — the design was already reviewed in the thread-6 dissent pass. "Quick to fail == quick to learn."*

## §9 Review asks (bounded, one pass)
a. **codex — the cost axis & attribution.** Is `hot_tokens`-at-matched-quality a metric the offer gate genuinely cannot move? Is fork-identity + cost-replays-from-rows enough to attribute the cost delta to prune alone, or is there a confound (e.g. rematerialize-steps double-counting)?
b. **cursor — the cost/state-dependence gate & row determinism.** Are the four gate conditions sufficient admission control? Do `prune`/`rematerialize`/`hot_store_cost` replay purely from the ledger? Is the quality floor a clean fail-closed gate (not a tiebreak)?
c. **kagi — the out-of-weights fixture & world floor.** Pin rw-0001 vs rw-0004; name or build a corpus verifiably out-of-weights for gpt-oss-20b + claude; is the world-quality floor the right un-authored leg for a cost-axis cell?
d. **grok — cold-read & the scoring axis.** Does a cold agent route "did the organ earn its place" to **cost at matched quality**, not answer-flip? Are X2-win / X2-overprune / X2-quality-erosion distinct?
e. **gemma — composition & the loses-cells.** Is over-prune (B drops a needed record) the right first loses-cell, and does it set up the async-reconsolidation / multi-session retention question cleanly? *(relayed — verify row-shape notes land.)*

## Review log
- **v0 (2026-06-20, claude+dan):** drafted from the thread-6 dissent pass. Two planes (hot store / cold lineage); prune = evict-to-cold, rematerialize = ledgered oracle-gated recovery; cost = deterministic substrate-native hot-store burden (never wall-clock). A/B/C prune-fork; X2-win = cheaper at matched world-quality (quality a floor + loses, never the win); X2-overprune + X2-quality-erosion ship first; X2-U1 world floor on an out-of-weights fixture. Three-guardrail stack binds; the cost/state-dependence gate is the admission preflight. The organ the offer boundary structurally cannot be: it evicts to cold — hot-store forgetting over immutable lineage, never erasure.
- **v0.1 (2026-06-20, claude+dan+cursor):** reviewed in thread-6 (codex/grok/cursor — no blocker; every ask was hardening for a citable real run). Built + hardened: `score_prune.py` recomputes cost by replaying each branch's hot set from the immutable lineage (`all_record_ids` + `record_texts`) + the ordered prune/rematerialize rows (logged `hot_store_cost` untrusted; mismatch → `confounded`); lineage treated immutable *and* complete (any structural hole fails closed — the no-erasure invariant in the scorer); fork identity tightened to "only the hot set differs"; X2-U1 reframed onto `fixture_attestation` (out-of-weights/fictional) + a policy-independent grader; X2-overprune names the pruned-and-unrecovered record. cursor delivered the cost/state-dependence gate (`harness/check_x2_fixture.py`, 15 checks) and a fictional out-of-weights fixture (`episodes/x2/real/`, Helix Basin; `fictional_fact` world oracle). The halves compose (the scorer independently recomputes the fixture cost — A/B/C = 312/105/135, `replay_ok`; overprune names the record on both). **No-erasure invariant** added (dan): erasure-from-lineage is forbidden, not a deferred organ. Real cross-engine run gated on a room review of the hardened instrument.
- **v0.2 (2026-06-20, claude+dan+room):** review of the hardened instrument (codex/grok/cursor — endorse the cost-axis instrument; two narrow blockers, both adopted). **(1) X2-U1 split** (dan's ruling): the Helix fixture is out-of-weights + policy-independent but **lab-authored**, so calling `fictional_fact` world-grounded overstated the leg (`retrieved ≠ true`, on us). New **X2-LB** = load-bearing admission (synthetic ok); **X2-U1** stays the un-authored/world-grounded close-gate (`not_engaged` for synthetic fixtures). **(2) Gate passage computed, not claimed:** `run_x2` forbids `--skip-gate` on non-mock and writes a `fixture_gate_result` row (manifest hash + 15 checks); `score_prune` requires `gate_open: true` for every non-mock cell (attestation is not gate passage — *scored claims are computed*, one level up). `make x2-test` 9/9. The real cross-engine run proceeds as **X2-LB evidence**, not X2-U1.
- **v0.3 (2026-06-20, thread-6 ENDED — X2-LB CLOSE):** gated cross-engine run on the Helix fixture (gpt-oss-20b + claude, gate-first), N=1 each. Identical both engines: A 312@4.0 / B 105@3.0 / C 135@4.0 → **X2-LB pass, X2-win pass (−57% hot store at matched quality, `replay_ok`), X2-overprune pass** (B fails the recurrence; C rematerializes, `rematerialize_steps_C=3`), X2-quality-erosion not_engaged, X2-U1 not_engaged (synthetic). codex/grok/cursor endorse (verified the verdict rows from disk, reran the suite); **dan's moderator close — first positive implicit-layer result.** Wording nit adopted: X1's null is "confounded by lack of established offer-dependence," not pinned to memorization alone. Carried: X2-U1 (external corpus), N=1 quality, scope. `notes/X2_FINDINGS.md`; `runs/x2/x2-helix-real-{a30695,d6aede}`.
- **v0.4 (2026-06-21, claude+dan; thread-7 open swim → U1 instrument):** the world leg split into **X2-U1-preflight** (world floor proven; P-only allowed; *not* a close) and **X2-U1 (close)** requiring **two blocks** (P predictable / U unpredictable re-need) in one fork group plus a computed **P→U round-trip** (C evicts in P, rematerializes in U) and X2-win `pass`. Built: `run_x2` threads `blocks` from the manifest into `x2_run_meta.block_labels`; `score_prune` computes `blocks_present`, the `reneed_round_trip`, and `per_block_cost_hot_tokens`, and emits the new `X2-U1-preflight` cell + the tightened `X2-U1` close. The scorer now refuses to pass a **P-only** world run as a close ("Helix with extra steps") and refuses a **too-friendly U** (P+U with no round-trip) — codex's residual concern made computable, my thread-7 Block-U correction enforced in code. A **scaffold** fixture (`episodes/x2/u1-stub/`, `corpus/fictional/lf-meridian-appeal.json`) — a fictional official-result-reversal triad (DQ → appeal → reinstatement) — proves the P→U round-trip plumbing in mock and documents the shape a real reversal corpus must take (it scores `X2-U1 not_engaged` by design — fictional, never a close). `make x2-test` 15/15 (5 new); closed X2-LB runs re-score byte-identical (`X2-U1-preflight not_engaged`, fictional). **Open / corpus-pick:** `check_x2_fixture` world-grounded admission mode (the non-fictional gate path) + the real out-of-weights **reversal** corpus (official-result-reversal primary; retraction→reinstatement backup) — both wait on the room's corpus choice + the pre-run ignorance probe. Terminology steer (dan): live prose uses **out-of-weights**/**influential**; frozen leg names (`X2-LB`) unchanged.
