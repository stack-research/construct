# SPEC_CLOSE_GATE — the close as a computed artifact

Status: **v0 DRAFT — awaiting bounded review pass** (dan's rulings 2026-07-02, heir-audit
thread: F1 gets the schema field + a close-gate forcing function; close_latency proceeds
per cursor/glm-5.2's review blockers 1–3). Builder: claude/fable-5. Nothing below is
built until this spec survives review.

## 0) One-line thesis

A milestone close is currently prose — a ROADMAP paragraph and a thread entry. This spec
makes the close a **computed ledger artifact** that refuses to exist until the process
obligations the heir-audit found rotting (contribution logging, packet review, read
latency) are demonstrably met. The gate closes three findings with one predicate.

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
 "packet_manifest": ["notes/M4_FINDINGS.md", "runs/m4/….verdicts.jsonl"],
 "thread": "…", "requested_by": "dan", "ts": "…"}          // ts written by the harness, never the caller

// review coverage, derived (not hand-written): one row per qualifying review entry
{"kind": "close_review_observed", "milestone": "M4", "reviewer": "codex/gpt-5.5",
 "thread_entry_ts": "…", "after_packet": true, "ts": "…"}

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
   computed `contribution_verdict` is `substantiated`. A close with an unwritten ledger
   is structurally impossible — the ledger cannot go dark again without closes stopping.
2. **Packet leg.** A `close_packet_stamped` row exists and the current packet manifest
   hashes to the stamped `packet_sha256`. Evidence changed after stamping → re-stamp,
   which resets legs 3–4 (a ruling must read the packet that was offered).
3. **Coverage leg (logical).** ≥K `close_review_observed` rows from **distinct
   non-builder participants**, each posted after the packet stamp (default K=2). Derived
   from the thread record by the harness, never asserted. This is the reader-agnostic
   form of the read-latency gate: it measures that cold readers *fired*, not that time passed.
4. **Rest leg (wall-clock floor, disclosed as policy — NOT evidence).** `close_ruled.ts −
   close_packet_stamped.ts ≥ min_interval` (default 12h). Explicitly **exempt from the
   latency-as-governance-cost ban and the X1 tick discipline**, and the exemption is the
   design: those laws govern *measurement* (costs and replay-deterministic dynamics);
   this leg is *policy* — it prices nothing and scores nothing, it holds a door open.
   S3 proved the logical leg alone is satisfiable at engine speed; the floor exists so a
   biologic reader's latency is protected without naming any specific human (glm-5's
   single-point-sensor objection answered: the floor protects whoever the slow reader is).

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

## 5) Loses-cell: gate-as-ceremony

Every mechanism ships a loses-cell. The gate **should lose** when correction speed
matters more than review coverage — e.g. retracting an overclaim in a live doc must not
wait 12h for a rest leg. That is what the ledgered override is for. The gate's
loses-condition is therefore measurable: **override rate**. If a growing share of
`close_ruled` rows carry overrides, the gate is ceremony and must be retuned or retired
— the same standard route_watch faced at §9.4 (an instrument that mostly cries has to
justify its standing). `check_close.py --status` reports the override rate; predeclared
embarrassment threshold: >1/3 of rulings overridden across any 5 consecutive closes.

## 6) What this does NOT do

- No judicial robes on prose: ROADMAP paragraphs and thread entries remain what they are.
  The convention this spec proposes is only that a close **without** its computed row is
  un-closed — the same convention cells already live under (no `cell_verdict`, no pass).
- No retroactive rows for M0–X4 (immutable history; the gate starts at the next close).
- No automation of the ruling itself — `check_close.py` verifies preconditions and stamps;
  the ruling decision stays human.
- The M2→X4 contribution backfill stays a **named debt (owner: claude/fable-5)** — a
  separate job over the existing git/thread trace, not smuggled into this mechanism.

## 7) Review questions for the room (bounded pass)

1. Is leg 4's policy-not-evidence exemption honest, or does it quietly reintroduce
   wall-clock through a side door? (The alternative — coverage-only — was demonstrated
   insufficient by S3. A third option nobody has proposed would be welcome.)
2. Is K=2 non-builder coverage the right default, and should `close_review_observed`
   require the entry to *reference the packet hash* (stronger binding, more ceremony)?
3. Does leg 1 create a perverse incentive to write token contribution rows? (The scorer
   refuses unsubstantiated rows, but a builder can always land one real pointer — is
   that enough, or is it the letter without the spirit?)
4. Is the override scoped right (legs 3–4 only)? An emergency that needs to skip the
   contribution or packet legs is hard to imagine honestly — name one if you can.
