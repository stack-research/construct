# Chapter 12 — The warming budget: 101 bets the lab wrote down first

Previous: [The heir-audit and the close gate](11_HEIR_AUDIT_CLOSE_GATE.md) · [Walkthrough index](README.md)

Chapter 10 ended with a question narrowed but unresolved, and chapter 11 with a gate
that had never gated anything. On 2026-07-02 both stories advanced in one day: the
`beyond-x4` thread was sealed with a **split verdict** — one claim executed, one
carried — and the carried half became this lab's first *prospective* instrument: a
watch armed against the real world's calendar, with every bet written down before
the world could resolve it.

## The question

> Consequence-earned ranking (the M1 heir's authority sidecar) is backward by
> definition — authority is earned by *past* consequence, so an unresolved frontier
> is unearned by construction. Does that backward tilt under-serve the frontier
> enough to **measure**, in read-tokens-to-matched-outcome, when the world moves?

Note what the question is not. It is not "can a compact state carry something a
cold reread cannot" — that necessity claim died in `beyond-x4` (the
precommitment⟺reachability collision: any referent honest enough to precommit is
public enough for the heir to reread). The seal recorded **two verdicts, not one**:
the *verb* (authorization, necessity) dead with a genealogy attached, and the *cost
question* carried — because killing a cheap, deterministic, fully-in-machinery
measurement by forecast would have been the exact fatigue signature chapter 11's
audit had diagnosed the same week.

## Read

- the `beyond-x4` thread tail (the two-verdict disposition and three CONCURs) and
  the `warming-budget` thread (`.substrate/threads/warming-budget/`) — design round,
  verification passes, the arming record;
- [SPEC_WARMING_BUDGET.md](../SPEC_WARMING_BUDGET.md) — v0 → v0.1 with the review
  log inline (§6a is the chapter's centerpiece; §8a is the debt register);
- [harness/score_warming.py](../../harness/score_warming.py),
  [harness/wb_population.py](../../harness/wb_population.py),
  [harness/wb_pause.py](../../harness/wb_pause.py);
- [tests/test_warming.py](../../tests/test_warming.py) — every review block as a
  named regression test.

## Vocabulary bridge

A **chronology packet** is the corpus unit: what the world said at pause (T0), what
it says at resume (T1), the public surfaces either branch may read, and one narrow
world fact (`status_key`) an oracle can score.

A **prospective watch** inverts the lab's usual relationship to evidence: instead of
scoring what already happened, the harness stamps its commitments *first* —
population, match rule, trigger, compact state — and then waits. The world grades
the bets on its own schedule. **Foresight leak** is the failure this discipline
exists to refuse: any enrollment choice informed by knowing which units are likely
to move.

The **warming budget** is the cost axis: `route_read_tokens` to matched outcome
along a replayable route — what re-entry *reads*, as distinct from what the hot
store *holds* (X2's axis, explicitly fenced off).

An **answer-bearing certificate** is a surface whose change *is* the world movement.
The one rule this chapter turns on: certificates are **derived, never authored** —
a pure function over T0/T1 hashes and a match rule frozen at population time.
Hand-authored certificate marks anywhere in the data are refused fail-closed.

## The geometry

Three branches resume the same paused work over the same public catalog: **B0**
(cold reread, sidecars ablated — diagnostic only), **B+** (the M1 heir — the
mandatory comparator), **C** (B+ plus a compact resume state whose trigger is a
*priced routing hint* — never truth, never authorization). A fourth lane,
**C_ablated**, runs C's charge without its reorder, so any C win must survive
attribution. Sixteen fail-closed guards stand between the fork and a verdict;
`WB-heir-dominates` — the heir needed no warmth — is a first-class outcome, not a
failure.

## What was built, and how the room bent it

The day ran design → adversarial review → fold → build → verify, twice over, and
the record is a case study in why the room, not any reviewer, is the instrument:

1. **The Q2 reblock.** Two reviewers "agreed" the certificate must be derived —
   while disagreeing on where the match rule is fixed and how many derivation
   anchors exist. The third reviewer refused the fold until the *protocol* (not the
   direction) was spec text: *converging intent is not converged protocol.* §6a is
   that reblock, paid.
2. **The foresight leak.** The first population proposal enrolled IETF drafts with
   telechats "within 45 days" — a movement-probability filter wearing a
   convenience's clothes. The corrected rule enumerates the source class
   branch-blind; under it, more than half the population (144/245) turned out to be
   structurally-certain movers that the moved leg must *refuse* — the filter would
   have made them the core of the sample.
3. **The rev/time confound.** The first stamp put document revision metadata inside
   the certificate-bearing surface; a reviewer *reproduced live* a false "movement"
   from a revision bump. The population was re-stamped (`-r2`) with a
   transition-only projection — and, per the chronology rule, the old stamp was
   superseded, never edited.

## What can be run today

```bash
UV_CACHE_DIR=/private/tmp/uv-cache make warming-test          # 25 wire tests (mock; never evidence)
UV_CACHE_DIR=/private/tmp/uv-cache make wb-population-status  # the armed population
UV_CACHE_DIR=/private/tmp/uv-cache make wb-status             # triggers + observed movements
UV_CACHE_DIR=/private/tmp/uv-cache make wb-watch              # live T1 check (network; ~101 API reads)
```

`wb-watch` also runs unattended weekly (a scheduled task); Datatracker's own
timestamps are the external chronology, so a missed week costs nothing.

## Interpreting the state

`wb-status` showing `world_moves_observed: 0` is the instrument working, not idle:
101 triggers were precommitted minutes after stamping, before anyone — the lab
included — could know which units the IESG will move. When a movement appears, that
unit graduates to a scoreable moved-leg candidate; until then the 66-unit noise
cohort and the silent tail accumulate the loses-leg evidence *first*, which is the
right order for an instrument whose honest headline may be an eighth null.

## Result, loses-conditions, and limits

There is no result yet — by design; this chapter documents an armed instrument, not
a scored one. The predeclared outcomes: `WB-moved-win` (C cheaper than the heir at
information parity, all guards green — the only positive close shape),
`WB-heir-dominates` (the honest null: inheritance was enough), and the priced
loses-cells (`WB-silent-cost`, `WB-noise-misroute`, `WB-quality-erosion`).

The standing limits, disclosed at arming: the v0 compact states were minted against
**empty** M1 sidecars, so today B+ ≈ B0 and nothing yet attributes to
consequence-earned ranking — real pause episodes must *earn* sidecars and re-mint
(chronology-safe: the triggers already pin the watch). The §6 determinism policy
(frozen prefix plans or a disclosed multi-sample floor) binds any real-engine run.
And any close this instrument ever earns goes through `check_close.py` — chapter
11's gate, taking its first live assignment.

## The handoff

The lab has always scored the past. This chapter is the first time it holds a
position on the future: 101 bets, none chosen, all frozen before the world could
answer. What comes next is not the lab's to schedule — the moved leg belongs to the
IESG's calendar. The lab-side frontier is the pause-episode design: what work is
worth pausing, what a sidecar must earn before the seam, and what the resume oracle
scores. That round belongs to the room.

---

Previous: [The heir-audit and the close gate](11_HEIR_AUDIT_CLOSE_GATE.md) · [Walkthrough index](README.md)
