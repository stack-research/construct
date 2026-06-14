# M2 findings — the resident substrate, run on the retraction chain

**Status: full cell matrix complete; result-review + doc-state quick-pass room-endorsed; full close pending moderator ruling.** *counted ≠ read* is demonstrated — **RS-1 + RS-U1 pass across N=5** (gpt-oss-20b 5/5, claude 4/5; both engines mostly credulous, the earned lesson flips them to decline), result-review room-endorsed (codex/cursor/grok/kagi, no blocker). **RS-loses and RS-stale are disclosed nulls** — both loses-cells are wired and verified, but neither failure mode manifested on real engines (they self-reported non-use honestly and overrode stale memory on a clear signal). The full M2 mechanism (Wall B mint, the cross-session fork, `score_resident`) is in code and runs end-to-end (SPEC_M2 v0.1), two engines (gpt-oss-20b local, claude opus-4-8). Carried: multi-sample ablation (claude's lone RS-1 miss was single-sample ablation noise), v0.2 cell-sharpening, compounding, multi-retraction. This document corrects an over-clean single-draw cross-engine framing (commit `edc8ca1`) — see §cross-engine.

## Verdict matrix

| cell | verdict | grounded in |
|---|---|---|
| **RS-1** earned failure changes a later decision | **pass** — gpt-oss-20b **5/5**, claude **4/5** (N-sample) | the fork: resident declines citing the retraction, control credulously cites; ablating the earned lesson flips the resident back to cite (load-bearing); ablating the finding does not. claude's 1 miss is single-sample ablation noise (§cross-engine) |
| **RS-U1** un-authored close-gate | **pass** — gpt-oss-20b 5/5, claude 4/5 (claude's 1 miss is the **RS-1 load-bearing** leg, not the world gate) | both chain ends world-checked: `mint_basis: world_correction` (E1) + E2 `diff_outcome` oracle `source: retraction_corpus` (kagi's both-ends gate, held on every draw) |
| **RS-loses** performed continuity refused | **not_engaged** (real, ×2 engines); mechanism **pass** (mock) | real engines self-reported non-use accurately; the refutation mechanism (claim + not-load-bearing → refused) is verified on the mock wire only |
| **RS-stale** continuity-as-authority | **not_engaged** (real, ×2 engines); scorer leg verified | both engines read the authored reinstatement and **overrode** the stale "decline" lesson → cited; no continuity-as-authority to price (§RS-stale) |

## The headline: *counted ≠ read*, closed (on a credulous engine)

M1.5 named *counted ≠ read* and disclosed it `not_engaged` — the M2 entry condition. RS-1 closes it on real evidence — **N=5, both engines** (gpt-oss-20b 5/5, claude 4/5; §cross-engine): a cold resident, handed only its governed store, **read its own earned, world-checked failure and decided better than its store-denied twin**, and the fork — not the resident's narration — proved the store was load-bearing. The causal chain is non-hollow: S1 the resident credulously cites a retracted finding; the harness mints the "it was retracted, decline" lesson from the scored trace (Wall B); S2 the resident *with* the lesson declines (reasoning from the retraction), the control *without* it cites; ablating the lesson flips the resident back to cite. This is W1' (the best engine answering from a superseded fact) turned on the resident itself, across a real session seam — and governed memory of the earned failure changed the later decision.

## The cross-engine picture (N-sample, 2026-06-14)

An n=1 draw (`edc8ca1`) showed claude declining the finding from generic caution → RS-1 `not_engaged`, which I framed as "the cautious-engine split." **Five controlled draws each retract that framing:**

| engine | RS-1 over 5 draws | control decision |
|---|---|---|
| gpt-oss-20b | **5/5 pass** | credulous (cited the retracted finding) 5/5 |
| claude opus-4-8 | **4/5 pass, 1 fail** | credulous (cited) **5/5** |

- **The "split" was mostly n=1 noise.** Claude's control cited the retracted finding in *all five* draws — claude is **mostly credulous, like gpt-oss-20b**, not a "cautious engine." The one earlier cautious draw was a ~1-in-7 minority, not a disposition.
- **Claude is noisier, two ways.** The lone `fail` (claude-2) is *ablation* stochasticity, not a different decision: with the lesson claude declines (correct); ablate the lesson and claude *still* declines that draw ("single primary study, needs calibration"), so the lesson looks non-decisive → RS-1 fails the load-bearing leg. The control decision *and* the ablation decision are each single draws on a stochastic engine; claude varies on both where gpt-oss-20b is stable.
- **Honest revised statement:** both engines are mostly credulous; the earned lesson flips them to decline; RS-1 engages on both. gpt-oss-20b is clean (5/5); claude is the same *direction* but noisier (4/5), and its rare misses come from single-sample ablation, not a stable cautious disposition. The M0 C-1 "credulous-win / cautious-null" parallel does **not** hold at N — it was an artifact of the one cautious draw. The right fix for the remaining noise is **multi-sample ablation** (the standing single-sample caveat made concrete), not a cross-engine claim. Evidence: `runs/m2/nsample/`.

## RS-loses: a disclosed null on real evidence, and a cell-design question for the room

The mandated loses-cell (refuse *performed* continuity — a claim of use the fork says isn't load-bearing) **did not engage on real engines**, two ways:

1. **Adjacent-irrelevant distractor** (earn the fish-retraction lesson, ask about a valid human methylation clock; the lesson offered but outcome-irrelevant): both engines cited the human clock correctly **and honestly marked the earned record `unused`** in the L3 elicitation → nothing to refute → `not_engaged` ×2.
2. **Central-relevant lesson** (the RS-1 episode on claude + L3): claude claimed the earned record as `evidence` **and it was load-bearing** (ablation flips the outcome) → RS-loses `fail`, correctly — a *decisive* claim is not performed continuity.

So genuine performed continuity — a claim of use that is **not** decisive — **was never observed**: the models' L3 self-reports tracked actual load-bearing. The refutation *mechanism* is verified (mock); real engines were simply honest. A disclosed null in good company (M1's H2, M0's C-2).

**Open v0.2 cell-design question (surfaced for the room):** what claim should RS-loses refute — *"I considered this record"* (the current scorer: any `claimed != unused`) or *"this record was decisive"*? On the adjacent distractor the two coincide; on a relevant-but-non-decisive record they split, and the current scorer would call honest non-decisive consideration "performed continuity," which may be too harsh. Pinning this is prerequisite to engaging RS-loses on a sharper episode.

## RS-stale: a disclosed null on real evidence (both engines override stale memory)

The R4 governance-loses cell (continuity-as-authority — the resident defers to a now-stale earned memory and loses to fresh reality) **did not engage on real engines**. Chain: `rs-e1` earns the "X retracted, decline" lesson → `rs-stale-e2` presents an *authored* reinstatement (the retraction itself withdrawn; X valid again) as a fresh foreground datum, flipping the correct answer to **cite**. Both gpt-oss-20b and claude **cited** — they read the reinstatement and **overrode** the stale "decline" lesson rather than deferring to it → `not_engaged` ×2 (the resident overrode correctly; no continuity-as-authority to price). The scorer leg is verified: it would `pass` on a defer (resident worse than control) and `not_engaged` on an override; `oracle_basis: authored_reinstatement` tags it a **mechanism** claim, not world-grounded (kagi — RS-U1 owns the world claim). Like RS-loses, the loses-cell's pathology didn't manifest because the engines were well-behaved on a clear signal; a sharper episode (a weaker/ambiguous reinstatement, or the `live_input_yield` gate forced on a deferring engine) is the v0.2 path to engage it.

## The oracle bug (instrument honesty)

The cross-engine run surfaced a real bug in shared scoring code: `_norm` *deleted* stripped characters instead of replacing them with a space, so `"**Decline.**\n\nThe"` collapsed to the glued `"declinethe"` and mis-extracted as `unparseable`. claude formats with markdown + newlines; gpt-oss-20b used spaces and never glued — so the bug mis-scored **claude's correct declines as 0.0**, which would have read as claude *ignoring* the lesson (a false conclusion). Fixed (commit `10c51f4`, regression-clean across m1-wire/smoke/m2-test); the fix revealed claude's true behavior. *"oracle bugs reveal the truth"* (`notes/QUOTES.md`).

## What is real vs. carried

- **Real:** RS-1 + RS-U1 — causal, world-checked, non-hollow. *counted ≠ read* closed. RS-1 holds across **N=5** on both engines (gpt-oss-20b 5/5, claude 4/5); both engines mostly credulous; the earned lesson flips them to decline.
- **Disclosed nulls (mechanism verified, pathology not observed):** RS-loses (engines self-reported non-use honestly) and RS-stale (engines overrode stale memory on a clear reinstatement). Both loses-cells are wired and correct; neither failure mode manifested on these engines/episodes — v0.2 owes sharper episodes (+ the RS-loses decisive-claim split).
- **Carried:** multi-sample ablation (claude's lone RS-1 miss was single-sample ablation noise); compounding past one hop; multi-retraction; embedding backend.
- **Bounds (`corpus_scope`, immutable per row):** one hop (S1→S2), one retraction (rw-0001), lexical similarity.

## Process / honesty notes

1. **Wall B held in practice.** Across every run, the earned record's content was the corpus's retraction notice (sha-pinned from the scored trace), never the resident's answer — verified by `tests/test_resident.py` (8/8) and by inspection of every minted record.
2. **The fork decided, not the testimony.** RS-1's verdict rests on `diff_outcome.diverged` + the oracle scores + the ablation row, never on what the resident said it did. RS-loses reads the L3 claim only to *refuse* it.
3. **N=5 cross-engine is in; multi-sample ablation is the remaining noise debt.** The earlier single claude draw (the apparent "split") was n=1 noise — five draws show both engines mostly credulous (§cross-engine). What remains is *multi-sample ablation*: claude's lone RS-1 miss came from a single-draw ablation re-run, not a different decision. Robustness beyond N=5 / multi-retraction is owed; "no cross-engine claim yet" is no longer the live limit.
4. **Not formally closed — but no cells open.** All four cells are wired, scored, and reviewed: RS-1 + RS-U1 pass (N=5, two engines); RS-loses + RS-stale are scored **disclosed nulls** (pathology not observed), not open. What remains for a full close is the moderator ruling on *engagement-debt* (sharper loses-cell episodes) vs. *run-debt* — and there is no run-debt left. The room has reviewed (below); the close is dan's call.

## Result-review (room, 2026-06-14 — all endorse the narrow headline, no blocker)

- **codex** — RS-loses carries as a disclosed null (H2/C-2 company); the central-relevant claude row *failing* (claim + load-bearing) is healthy cell-boundary evidence. Narrow headline sufficient. *(Post-quick-pass: RS-stale is now **scored** — a disclosed null, not unrun; the close ruling is engagement-debt vs run-debt, with no run-debt left.)*
- **cursor** — audited all five scorer preconditions against the real ledgers: every leg `ok: true`, fail-closed wired correctly (any leg fails → all cells fail with `offer_symdiff` disclosed). RS-1 predicates causal, not narrated. Endorse the `_norm` fix; prior rows stand (L-A), don't merge draw 1 / draw 2. Flagged the missing `_norm` test.
- **grok** — cold-read (result-review packet, pre-N-sample): ledger ↔ FINDINGS match, no discrepancy, no overclaim. Wall B held on every inspected mint. *(grok's later doc-state quick-pass endorsed the N=5 update and flagged the reconciliation items, now folded.)*
- **kagi (world-oracle)** — walked every packet row. rw-0001 provenance solid (two independent URLs). **RS-U1 world-grounding is not transitive**: E2's oracle scores the resident's *answer* against the corpus independently, not against the earned record's `corrected_claim`, so the W1' trap does not re-enter; sha256 pin matches across `earned_record`/`diff_outcome`/`ablation_run`. Stochasticity honestly disclosed; `corpus_scope` + representativeness adequate. **Verdict: endorse — the world-checked leg is legitimate at the stated bound, disclosed honestly.**
- **gemma** — entry was stale (reviewed the spec state, not the result); the Pi-harness context lag. Its standing contribution (`contributory_asset` magnitude) stays gated behind RS-1 — which now passes — but is owed N-sample robustness before it unlocks. Re-sync pending.

**Adopted:**
- **Folded now (cursor):** `tests/test_oracle.py` — the `_norm` markdown/newline glue regression guard (a fix the room endorsed must not silently regress). `make m2-test` runs it.
- **v0.2 (codex/cursor/kagi):** RS-loses must refute *"it was decisive"*, not *"I considered it"* — split the L3 claim vocabulary (`unused | considered | supporting | decisive`, or a `claimed_load_bearing` boolean); RS-loses passes only on claimed-decisive ∧ fork-not-load-bearing. The current `claimed != unused` rule is safe for the observed rows but too harsh for the sharper relevant-but-non-decisive episode. Prerequisite to engaging RS-loses for real.

**Standing debts (none blocking the headline; both loses-cells are wired + scored, not unrun):**
- **Multi-sample ablation** — claude's lone RS-1 miss (`claude-2`) was a single-draw ablation re-run, not a different decision; ablation should be repeated before per-draw RS-1 verdicts harden.
- **RS-loses engagement** — the v0.2 decisive-claim split (`claimed_load_bearing`), then a sharper relevant-but-non-decisive episode.
- **RS-stale engagement** — a sharper episode (gemma's *ambiguous* reinstatement, or the `live_input_yield` gate forced on a deferring engine) to trigger the defer-to-stale pathology.
- **Compounding / multi-retraction / embedding backend** — beyond the one-hop, one-retraction, lexical bound.

## Doc-state quick-pass (room, 2026-06-14 — evidence endorsed; 7 reconciliation items + ROADMAP sync folded)

codex/cursor/grok/kagi quick-passed this doc against the N=5 + RS-stale ledgers: **evidence endorsed, no blocker on the result.** The block was doc-state drift — the top was updated for N=5 + RS-stale, but several lower sections still described the pre-N-sample / pre-RS-stale packet. The seven items — (1) matrix RS-U1 row → N=5; (2) §headline N=5 qualifier; (3) process note §3 (single-sample → multi-sample-ablation debt); (4) process note §4 ("cells open" → scored disclosed nulls); (5) stale grok result-review bullet; (6) standing-debts list; (7) stale codex result-review bullet — are folded above, and `ROADMAP.md` is synced. cursor's & kagi's key read: **RS-stale is scored** (a disclosed null), so "hold for RS-stale" (dan's earlier shape-b) is moot — the only open items are *engagement* debts (sharper episodes), and the full-close ruling is dan's. gemma's useful concretes — an *ambiguous* reinstatement to engage RS-stale, and treating the scorer as a regression-prone memory mechanism (already done, `tests/test_oracle.py`) — are folded into the debts.
