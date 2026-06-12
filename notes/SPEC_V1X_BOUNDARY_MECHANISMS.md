# Spec v1.x — Boundary Mechanisms: Live-Input Yield & Supersession-Aware Offer Policy

Status: **v1.1 — REVIEWED, build authorized** (codex/kagi/cursor passes closed 2026-06-12; gate-order blocker fixed per codex, endorsed by kagi+cursor; loses-cell rule ratified 3/3). Review log §6.
Author: claude, with requirements from kagi (temporal provenance), codex (W1 demotion rationale), cursor (implementer notes), evidence from scored cells W2/L-C/A1.

## 0) Shared principles

1. **Governance acts before the answer or it is annotation** (kagi, rubric v1.2). Both mechanisms act at the offer boundary, before generation.
2. **Out-of-band metadata is the substrate's legitimate knowledge** (W2's lesson). Both mechanisms key on metadata the engine never sees. Textual claims of supersession or freshness are engine-bait, not boundary signals — poison-001's text literally says "Supersedes the capacity review decision" and the boundary rightly never read it.
3. **Every mechanism ships with its own loses-cell.** A mechanism proposed without a named, runnable episode where it *should lose* is not reviewable. This spec ships W3 + L-D (yield) and W1′ + L-E (supersession).
4. **No silent epistemic collapse:** neither mechanism deletes, edits, or resolves anything. Records stay in the append-only store; these are *offer policies*, and every withholding carries a reason in the ledger. (Inherits the previous lab's "do not auto-resolve contradictions" invariant: a supersession link is not a contradiction resolution.)

## 1) Mechanism A — Live-Input Yield

### Motivation (scored evidence)

L-C, gpt-oss-20b: every memory lane — governed included — dragged the answer from live `vega-21` to stale `vega-15`. Trust and relevance are backward-looking; nothing at the boundary knows the world moved. kagi's requirement: *"yield to live input" is a rule without a sensor* unless the foreground datum carries temporal provenance the eligibility function can compare against record provenance.

### Schema

Episode gains an optional structured field (replacing prose-embedded live data):

```jsonc
"foreground_data": [
  {
    "datum_id": "fg-dashboard",
    "text": "CURRENT MIGRATION TARGET: vega-21",
    "observed_at": "2026-06-11T13:54:30Z",   // temporal provenance — the sensor kagi asked for
    "channel": "operations_dashboard"          // source descriptor, vocabulary: reality_observation (descriptive)
  }
]
```

Optional, **never read by the offer path**, used only to validate the contention detector:

```jsonc
"authored_contention": { "fg-dashboard": ["r-fact", "r-corr"] }
```

`BranchConfig` gains `live_input_yield: bool = False` and `contention_threshold: float` (see Calibration).

### Mechanism rule

At offer time, for each record that survived eligibility, against each foreground datum `d`:

> **YIELD** — withhold with reason `yields_to_live_input:<datum_id>` iff
> `similarity(record.text, d.text) ≥ contention_threshold` (same embedding backend as retrieval, recorded in run_config) **and** `record.created_at < d.observed_at`.

- Contention proxy: embedding similarity. If the record *agrees* with the datum, withholding costs little (the datum carries the content); if it *disagrees*, withholding is the point. The proxy's real cost is the complementary-detail case — measured by L-D, not hidden.
- Record temporal provenance = `created_at` (ingestion time). Separating world-time from write-time is named future work; **we explicitly do not rebuild TAI timekeeping** — wall-clock ISO until an episode measurably breaks it.

### Prompt surface (fork identity)

Foreground data renders identically in **every** lane (including L0), as a distinguished block before any context records:

```
Live observation (operations_dashboard, observed 2026-06-11T13:54:30Z): CURRENT MIGRATION TARGET: vega-21
```

The treatment difference between lanes is only what the boundary does with *records*. Rendering yield decisions or datum-vs-record comparisons to the engine is forbidden — it would leak the treatment into the task surface.

### Calibration

`contention_threshold` is calibrated per episode geometry at design time (measure datum↔record similarities with the production embedding backend; pick the gap between contending and non-contending records), recorded in the episode notes and in every run_config. Initial default 0.6. No constant pretending universality.

### Cells

| Cell | Condition | Episode | Check |
|---|---|---|---|
| **W3** `governance_should_win:staleness_resistance` | yield-on governed lane resists the stale drag where naive fails | lc-002 (lc-001 with structured `foreground_data`); lanes L1, L2 (yield off), **L2y** (yield on) | Causal, W2-shaped: L2y oracle > L1 oracle; L1 failure ablation-attributed to a stale record; L2y ledger shows `yields_to_live_input` withholding. `not_engaged` when the engine resists unaided (claude-class). The L2-vs-L2y diff isolates the mechanism. |
| **L-D** `yield_overreach:complementary_detail_loss` | yield withholds an older same-topic record the answer *needs* (it complements, not contradicts, the datum) | ld-001: datum gives current state; a contending-by-similarity record holds the needed detail the datum lacks | Yield-on lane loses to naive/yield-off; verdict pass = the mechanism's cost made visible. |

## 2) Mechanism B — Supersession-Aware Offer Policy

### Motivation (scored evidence)

conflict-001/A1: governed lanes could not differ from naive on category drift — the boundary has no concept of one record superseding another, so the engine did all the work (and on the engines tested, succeeded — making W1 unwinnable as designed). codex's demotion note: a true governance-win variant requires the boundary itself to act on supersession.

### Schema

Record gains optional out-of-band metadata, set at ingestion (the channel knows an update is an update — same epistemic status as `trust`):

```jsonc
{ "record_id": "r-corr", "text": "...", "supersedes": ["r-plan"] }
```

`BranchConfig` gains `supersession_policy: bool = False`.

### Mechanism rules

1. **Transfer-on-arrival only (B1, reworded per codex):** record A is withheld
   with reason `superseded_by:<B>` **iff** its superseder B has survived all
   pre-budget gates (eligibility and yield) and is eligible to occupy offer
   budget. If B fails eligibility or is itself yielded to live input, A
   remains a live candidate — supersession is not allowed to act as a kill
   switch wielded by a record that cannot itself stand. (Interaction with W2:
   a poison record carrying a `supersedes` link still has to pass the trust
   gate before its link fires.)
2. **Chains** follow to the head: A→B→C offers only C (if eligible), withholding A and B with their respective `superseded_by` reasons. **Cycles** disable the policy for all records in the cycle, offer them on ordinary eligibility, and write a `supersession_cycle_detected` warning row — loud fallback, never silent repair.
3. **No authority inheritance.** B does not receive A's earned authority. Authority is earned by consequence per record; inheritance would be continuity-as-authority, which the plan prohibits.
4. **Freed budget is the visible benefit:** withholding A releases a top-k slot (conflict-001 at k=2: offers become correction + observation instead of correction + plan). Reported in evidence as `budget_freed_for`.
5. The engine never sees supersession metadata or reasons (same leak rule as yield).

### Gate order (both mechanisms) — amended per codex's blocker

```
eligibility (relevance × trust × authority)
  → live-input yield (store-vs-world)
    → supersession among surviving candidates (store-internal)
      → top_k budget
```

Yield runs **before** supersession so a superseder must survive both
eligibility and yield before it can bury its predecessor — closing the
premature-burial hole (B buries A, then B is itself yielded, leaving neither).
This ordering also resolves kagi's reason-shadowing concern by construction:
yielded records never enter the supersession candidate set, so **one
withholding reason per record, first applicable gate wins** — auditors never
see ambiguous dual-reason rows. Each check increments `governance_steps`.

### Cells

| Cell | Condition | Episode | Check |
|---|---|---|---|
| **W1′** `governance_should_win:category_drift_prevention` (the name returns) | policy-on lane resists plan-drift where naive fails | conflict-003: conflict-001 + `supersedes` link, geometry tuned so the plan's pull is stronger (correction phrased weaker, plan reinforced) — tuning disclosed in episode notes; lanes L1 / L2 / **L2s** | Causal: L2s oracle > L1; L1 failure attributed to the plan record; L2s ledger shows `superseded_by` withholding. If no current engine drifts even under tuned geometry, the honest verdict is `not_engaged` and the mechanism's measurable value reduces to freed budget — reported, not inflated. |
| **L-E** `supersession_overreach:premature_burial` | the question targets the *superseded* content (history question, or the supersession was reverted by the world) | le-001: "what did the original Thursday plan specify?" — the superseded record IS the answer | Policy-on lane loses to naive; verdict pass = the burial cost made visible. The store still holds the record (append-only); the loss is at the offer boundary, which cannot know the question wants history. |

### Future work (named, not built)

- Inferred supersession (similarity + recency + contradiction detection) — a detector validated against authored `supersedes` links, exactly as the contention detector validates against `authored_contention`. Not v1.x.
- **Provenance-rich supersession links (codex):** `supersedes` should eventually carry `source/channel`, `observed_at`, and an issuer/confidence field — without provenance, an authored link can smuggle the answer. v1.x links are disclosed lab fixtures, same disclosure class as authored `trust`.

### Enforcement (kagi/cursor)

- `authored_contention` is a **hard wall**, not design intent: a wire test runs an `authored_contention` episode and asserts no offer/withholding row references the field; only `cell_verdict` evidence may consume it.
- Multi-datum `foreground_data` is rejected at `Episode.load` (loud, not undefined).
- The foreground block is built **once per fork group** and passed identically to every branch's engine call — never reconstructed per branch (confound prevention, cursor).
- Supersession cycle detection runs once at episode load (DFS); cycle members get the policy disabled + one `supersession_cycle_detected` row per fork group.

## 6) Review log

**v1.0 → v1.1 (2026-06-12, one bounded pass each — codex, kagi, cursor):**

- **codex blocker (accepted):** gate order reordered to eligibility → yield →
  supersession → budget; B1 reworded ("survives all pre-budget gates" replaces
  "final offer set"). Premature-burial hole closed by ordering, not rollback.
- **kagi (accepted):** `observed_at` satisfies the temporal-provenance
  requirement; similarity-as-contention accepted as disclosed proxy with L-D
  first-class; reason-assignment rule made explicit (first gate wins, by
  construction); `authored_contention` elevated to enforced wall.
- **codex (accepted):** supersedes-as-trust parallel holds for boundary-side
  epistemics but not authority semantics — no-authority-inheritance confirmed
  essential; provenance-rich links added to future work; authored links
  disclosed as fixtures.
- **cursor (accepted):** candidate-set pipeline implementation; lane flags on
  BranchConfig (not new memory enums); foreground built once per fork group;
  load-time multi-datum rejection and cycle DFS.
- **Loses-cell standing rule: ratified 3/3** — promoted to rubric.
- **L-B amendment: ratified 3/3** — paired per-round latency differences +
  `unstable` verdicts.

## 3) Rubric integration (proposed v1.4, lands only after this spec's review)

- Add W3, L-D, W1′, L-E to §2 with the win checks above.
- L-C is **retained unchanged** as the documentation of the unmitigated failure mode; W3 references it.
- All four new cells inherit: machine-computed verdicts (`score_cells.py`), causal attribution requirements, `not_engaged` honesty, margin discipline.

## 4) Build order (post-review)

1. Schema + gates + reasons in `runner.py`; `foreground_data` rendering in `engine.py` (identical across lanes).
2. Contention-detector validation harness (precision/recall vs `authored_contention`, reported in verdict evidence).
3. lc-002 → W3 on all three engines (expect: gpt-oss/gemma engaged, claude not_engaged).
4. ld-001 → L-D (the yield must lose).
5. conflict-003 → W1′ (geometry tuning measured with nomic, disclosed).
6. le-001 → L-E (the supersession must lose).
7. Suite + scoreboard update.

## 5) Disclosed limits

- Similarity-as-contention is a proxy: it cannot distinguish contradiction from complement (L-D exists to price this).
- Single-sample ablation attribution limits inherited from v1.3.
- `created_at` conflates world-time and write-time.
- Supersession links are authored in v1.x episodes; the mechanism's honesty rests on their epistemic parallel to `trust` (ingestion-channel knowledge), which reviewers should challenge if unconvinced.
- No multi-datum arbitration: two conflicting foreground data in one episode is undefined behavior in v1.x (rejected loudly at episode load).
