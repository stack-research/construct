# SPEC_CLOSE_GATE — the close as a computed artifact

Status: **v0.1 DRAFT — bounded review pass complete (codex/gpt-5.5 + cursor/glm-5.2, both
endorse-direction/block-v0); all written blockers folded, §8. Build awaits dan's go.**
(dan's rulings 2026-07-02, heir-audit thread: F1 gets the schema field + a close-gate
forcing function; close_latency proceeds per cursor/glm-5.2's review blockers 1–3.)
Builder: claude/fable-5.

## 0) One-line thesis

A milestone close is currently prose — a ROADMAP paragraph and a thread entry. This spec
makes the close a **computed ledger artifact** that refuses to exist until four process
obligations are demonstrably met: **contribution-liveness** (a forward, packet-grounded
contribution row exists), **packet immutability** (the ruling read the packet that was
offered — the gate binds reviewers to the offered packet; it does NOT certify the packet
is complete beyond its declared artifact classes, §3.2), **reader-firing** (cold readers
demonstrably fired on it), and a **rest floor** (a moderator-calibrated opportunity
window). Relabeled per review (glm-5 B2): the v0 claim "closes packet *review*" overclaimed.

## 1) What the heir-audit established (inputs)

- **F1:** the contribution ledger died the day M1.5 closed — nothing forced later closes
  to write it. hermes/glm-5: the schema cannot represent its own dormancy; a revive
  without a forcing function "dies the same death."
- **S3:** the audit's own review pass reproduced the fast-convergence shape it diagnosed
  (4 reviews in ~54 min). A coverage-only gate is satisfiable at engine speed.
- **S4 + glm-5's close_latency review:** the read-latency gate must be an instrument
  (computable events), reader-agnostic, with `emit_event` wired to a real caller (blocker 1),
  the wall-clock-vs-logical-tick question resolved in prose (blocker 2), and `ts` stamped
  harness-side (blocker 3).

## 2) The object: `milestone_close` rows

New append-only ledger `runs/closes/closes.jsonl`, written **only** by
`harness/check_close.py` (the single writer; humans and agents request, the harness
stamps). Row kinds:

```jsonc
// stamped when the evidence packet is frozen and offered for review
{"kind": "close_packet_stamped", "milestone": "M4", "packet_sha256": "…",
 "artifact_classes": {"findings": ["notes/M4_FINDINGS.md"],           // per-class, and the
   "verdict_sidecars": "runs/m4/**/*.verdicts.jsonl",                  // sidecar class is a GLOB
   "ledgers": "runs/m4/**/*.jsonl", "corpora": ["corpus/…"]},          // the HARNESS expands —
 "packet_manifest": ["…expanded file list…"],                          // never a hand list (S1 fix)
 "builders": ["claude/fable-5"],                                       // declared at stamp: defines non-builder for leg 3
 "thread": "…", "requested_by": "dan", "ts": "…"}                      // every ts harness-written; caller ts rejected

// EVERY check_close invocation writes an attempt row — the gate instruments its own use (B3)
{"kind": "close_requested", "milestone": "M4", "by": "…", "ts": "…"}
{"kind": "close_refused", "milestone": "M4", "failed_legs": ["coverage"], "ts": "…"}

// review coverage, derived (not hand-written): one row per qualifying review entry.
// Qualifying = posted after the stamp, by a participant NOT in builders, AND the entry
// text references the packet hash (first 8 hex chars) — unbound room traffic never counts.
{"kind": "close_review_observed", "milestone": "M4", "reviewer": "codex/gpt-5.5",
 "thread_entry_ts": "…", "packet_ref": "a1b2c3d4", "ts": "…"}

// the ruling — REFUSED unless the §3 predicate holds
{"kind": "close_ruled", "milestone": "M4", "ruled_by": "dan",
 "packet_sha256": "…", "override": null, "ts": "…"}
```

`emit_event` in `harness/close_latency.py` gains its caller: `check_close.py` (blocker 1).
All `ts` fields are stamped by the harness at write time; caller-supplied timestamps are
rejected (blocker 3 — the X1 harness-authorized-tick law applied to process events).

## 3) The gate predicate (fail-closed)

`check_close.py --rule <milestone>` writes a `close_ruled` row **only if all four legs hold**,
else exits nonzero with the failing leg named:

1. **Contribution leg (F1's forcing function).** ≥1 intervention row in
   `runs/m1_5/contributions.jsonl` with `claimed_target_milestone == <milestone>` whose
   computed verdict has **`outcome ∈ {landed, blocked}`** (terminal and forward — excludes
   `reversed` and `passenger`; codex B1, glm-5's outcome-field sharpening), not superseded
   by a later `reversal_of`, **and** whose `target_artifact` is in the stamped packet
   manifest (or reaches a cell in the packet via a `scorer_evidence` chain). A close with
   an unwritten ledger is structurally impossible, and the row that satisfies the leg is
   forward, close-relevant, and packet-grounded — F1 paid in spirit, not letter.
2. **Packet leg (immutability + declared-class completeness).** A `close_packet_stamped`
   row exists; the current manifest hashes to the stamped `packet_sha256`; and the
   manifest was **harness-expanded from declared artifact classes** (globs for enumerable
   classes like verdict sidecars — the S1 fix: the harness enumerates, a hand list cannot
   silently drop the third sidecar). Evidence changed after stamping → re-stamp, resetting
   legs 3–4. **Disclosed limit (glm-5 B2):** completeness is relative to the declared
   classes; an artifact outside every declared class is structurally invisible to this
   gate. The gate certifies *immutability and class-completeness*, never total completeness.
3. **Coverage leg (logical, reader-agnostic).** ≥K `close_review_observed` rows (default
   K=2) from distinct participants **not in the stamped `builders` set**, each posted
   after the stamp and **referencing the packet hash** in the entry text. Derived from
   the thread record by the harness, never asserted. Measures that cold readers *fired
   on this packet* — not that time passed, and not that room traffic happened nearby.
4. **Rest leg (wall-clock floor — moderator-calibrated policy, NOT evidence, NOT
   reader-agnostic).** `close_ruled.ts − close_packet_stamped.ts ≥ min_interval`
   (default 12h). Exempt from the latency-as-governance-cost ban and the X1 tick
   discipline because those laws govern *measurement*; this leg prices nothing and scores
   nothing. The predicate's output vocabulary is **`opportunity_window_met`** — never
   "read latency proven," and no cell_verdict may ever consume this leg (codex's labeling
   boundary). **Calibration disclosure (glm-5's boundary):** the 12h default was chosen
   with the current moderator's biologic read cycle in mind — it is *dan-informed,
   moderator-calibrated policy*, retunable by governance, and the spec does **not** claim
   reader-agnosticity for this leg. Leg 3 carries the reader-agnostic property; leg 4
   holds a door open for whoever the slow reader is, sized today for the one we have.
   S3 is why coverage alone cannot substitute: four cold reviews landed in 54 minutes.

**Override (the loses-cell, §5).** `--override "<reason>"` bypasses legs 3–4 only, never
legs 1–2, and writes the reason into the row. *Allow intervention, don't require it* —
the moderator stays sovereign; the lineage records that sovereignty was used.

## 4) Schema change: `claimed_target_milestone`

Intervention rows gain one optional field, `claimed_target_milestone` (string, e.g.
`"M4"`, `"X5"`, `"audit"`). Like every `claimed_*` field it is a claim (R5): the scorer
does not trust it — leg 1 requires claim **and** computed substantiation. `score_contribution.py`
gains a `--status` view: per-milestone row counts + latest ts, so dormancy is visible
*from inside the instrument* (hermes's schema-blindness finding paid). Existing 13 rows
stay untouched (append-only; absence of the field reads as pre-gate history).

## 5) Loses-cell: gate-as-ceremony (denominator fixed per codex B3 / glm-5 S2-recurrence)

Every mechanism ships a loses-cell. The gate **should lose** when correction speed
matters more than review coverage — e.g. retracting an overclaim in a live doc must not
wait 12h for a rest leg. That is what the ledgered override is for. But override rate
among successful rulings alone cannot see the chief ceremony failure — **stalled or
avoided closes** (F1's dark-gap shape recurring in the gate built to fix F1). So the
gate instruments its own use: every invocation writes `close_requested`, every failure
writes `close_refused` with the failing legs, and `check_close.py --status` reports
refused-attempt counts, open-packet age, and stale stamped packets alongside overrides.

**Embarrassment line (retunable policy, post-hoc by nature — not an early warning):**
override rate **>1/5 of rulings across any 10 consecutive attempts** (attempts = the B3
denominator, not rulings alone). Provenance, stated not smuggled: the route_watch §9.4
analog is "an instrument that mostly cries" (>1/2); we choose materially stricter because
overrides encode *emergencies*, and the threshold asserts a prior that legitimate
emergencies occur in fewer than one close in five. If the measured rate approaches the
line, the gate is ceremony: retune or retire.

## 6) What this does NOT do

- No judicial robes on prose: ROADMAP paragraphs and thread entries remain what they are.
  The convention this spec proposes is only that a close **without** its computed row is
  un-closed — the same convention cells already live under (no `cell_verdict`, no pass).
- No retroactive rows for M0–X4 (immutable history; the gate starts at the next close).
- No automation of the ruling itself — `check_close.py` verifies preconditions and stamps;
  the ruling decision stays human.
- The M2→X4 contribution backfill stays a **named debt (owner: claude/fable-5)** — a
  separate job over the existing git/thread trace, not smuggled into this mechanism.

## 7) Review log

**v0 → v0.1 (2026-07-02, heir-audit thread — one bounded pass each; both
endorse-direction / block-v0; all blockers folded):**

- **codex B1 (accepted, glm-5 sharpening adopted):** leg 1 was satisfiable by a token
  one-line diff or a substantiated-but-`reversed` row (`score_contribution.py:181-188`
  accepts `landed`/`reversed` from the claim once a pointer grants importance). Fixed on
  the **`outcome`** field: `∈ {landed, blocked}`, not superseded, packet-grounded (§3.1).
  codex's tighten-OR-rename resolved as tighten-and-keep-F1 per glm-5's partial refute.
- **codex B2 / glm-5 "S1 recurring in the predicate" (accepted, both halves):** the
  packet leg certified immutability while §0 claimed packet *review* — the exact
  subset-verification failure (S1) this thread caught, re-encoded structurally. Fixed:
  harness-expanded artifact-class globs (the enumerator a hand list lacks) **and** the
  disclosed limit + §0 relabel (§3.2). The gate never claims total completeness.
- **codex B3 / glm-5 "S2 firing on the loses-metric" (accepted):** the gate could not see
  its own non-use — clean override rate while closes stall is F1's dark gap reborn.
  Fixed: `close_requested`/`close_refused` rows, attempt-denominated metrics, staleness
  in `--status` (§2, §5).
- **coverage note (accepted as hard requirement):** `builders` declared at stamp;
  `close_review_observed` requires packet-hash reference — unbound room traffic and
  review-of-the-wrong-packet never count (§2, §3.3).
- **leg 4 (codex: accept with labeling boundary; glm-5: concur + calibration boundary —
  both adopted):** output vocabulary pinned to `opportunity_window_met`; no cell_verdict
  may consume the leg; and the honest disclosure glm-5 forced — the 12h default **is**
  dan-informed, so leg 4 is *moderator-calibrated policy* and the reader-agnostic claim
  is withdrawn for leg 4 (retained for leg 3). Borrowed-foresight-in-temporal-clothing
  averted by disclosure, not denial (§3.4).
- **override threshold (glm-5: vibes-with-a-number — accepted):** re-based on the B3
  attempt denominator, tightened to >1/5-over-10-attempts, provenance and the encoded
  emergency prior stated, named post-hoc (§5).
- **override scope (both: correct as written):** legs 3–4 only; neither reviewer could
  name an honest emergency that skips packet identity or the contribution ledger.
