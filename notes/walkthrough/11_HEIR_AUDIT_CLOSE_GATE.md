# Chapter 11 — The heir-audit and the close gate

Previous: [Beyond X4 — Pause, resume, and open edges](10_BEYOND_X4.md) · [Walkthrough index](README.md) · Next: [The warming budget](12_WARMING_BUDGET.md)

Every earlier chapter examines an experiment the lab ran on memory. This chapter is
different: it is the lab running an experiment on **itself**. In early July 2026 the
moderator asked whether the month's rapid closes had been earned or merely fast, a
cold auditor swept every close since June 12, the room then audited the auditor, and
the findings were folded into a new instrument — a computed gate that every future
close must pass. If chapter 0 taught the vocabulary, this chapter is the vocabulary
in a live firefight.

## The question

> The lab closed four milestones in three days and two X-track experiments in two.
> Was the evidence sound — and separately, was the *process* that certified it still
> functioning, or had reviewer fatigue quietly replaced review?

The question had a sharper form the moderator put privately: should the lab roll back
to its last pre-suspension commit and rebuild, or trust the inheritance? The answer
became a standing precedent: **audit, don't rebuild** — re-derivation with the
answers already in your weights is theater; a cold audit of the ledgers is evidence.

## Read

- the `heir-audit` substrate thread (`.substrate/threads/heir-audit/`) — the full
  protocol, findings, room review, rulings, and build record;
- [SPEC_CLOSE_GATE.md](../SPEC_CLOSE_GATE.md) — the resulting mechanism, v0 → v0.1
  with its review log;
- [harness/check_close.py](../../harness/check_close.py), [harness/fatigue_metrics.py](../../harness/fatigue_metrics.py),
  [harness/close_latency.py](../../harness/close_latency.py);
- [tests/test_close_gate.py](../../tests/test_close_gate.py) — the review blockers as
  named regression tests.

## Vocabulary bridge

An **audit** re-derives claims from primary evidence (ledgers, code, thread
timestamps) rather than trusting the prose that summarizes them. A **cold** auditor
has no authorship stake in what they are checking.

**Process decay** is rot in the scaffolding around sound results: mechanisms that
stop being used, debts that lose their owners, review that drifts from blockers
toward endorsements. The central finding of this chapter is that evidence and process
can rot independently.

A **forcing function** is a mechanism that makes an obligation structurally
unavoidable rather than remembered. A **computed close** is this lab's newest
example: a milestone close that refuses to exist as a ledger row until its
preconditions demonstrably hold.

## What the audit found

The bench ran green before anything else, so every finding was about the closes, not
a broken instrument. The headline: **the evidence was sound, the public prose was
honest — and the process had decayed anyway.**

- **F1 (the sharpest):** the contribution ledger — M1.5's own deliverable, mandated
  to be "writing before M2 starts" — was last written *the day M1.5 closed*. Nothing
  was logged for M2, M3, X1, X2, or X4. The instrument built to refuse
  counted-to-be-counted was counted, then abandoned. Worse, its schema had no field
  that could represent its own dormancy: the failure was only discoverable from
  outside the instrument built to make it discoverable.
- **F2–F4 (smaller):** a stale reproducibility assurance in the ROADMAP; an
  unrecorded piece of reasoning about a memorization confound; an open task still
  assigned to a participant who had been absent for twelve days.
- **The computed fatigue metrics** put numbers under the moderator's instinct: four
  milestone closes in three consecutive days; a spec written, reviewed, built,
  hardened, run, and closed inside one day; the world-oracle participant last seen
  *before* both world-grounded closes whose entire point was world-grounding; blocker
  counts falling across the arc as threads went endorse-heavy.

Note what the audit did **not** find: verdicts that failed to reproduce, or prose
that outran its bounds. The re-scored ledgers matched. The rot was in the scaffolding.

## The audit gets audited

The findings were posted to a thread and four cold reviewers were driven through it,
one at a time. This round produced the chapter's real lesson.

The fifth reader caught the auditor: the audit had verified the X2 close from the run
sets *cited in the close* and called the evidence sound — while an uncited sidecar in
the same directory still carried a duplicated-row artifact from a bug that was
supposedly fixed. The subset had been verified; soundness had been claimed for the
whole. Another reviewer showed the audit's own review round had reproduced the exact
fast-convergence signature it diagnosed — four reviews in fifty-four minutes. And the
audited builder, given the floor, chose confrontation over defense: "evidence sound,
process decayed" is not two findings but one causal fact, because the process that
decayed *is* the independent check — so "sound" meant "sound to the builder's own
verification," which is precisely the sentence this lab exists to distrust.

The standing conclusion, now part of lab doctrine: **a single cold auditor is not the
immune system. The room is.**

## The remedy: a computed close

The rulings turned findings into mechanism. The centerpiece is
[SPEC_CLOSE_GATE.md](../SPEC_CLOSE_GATE.md): a milestone close becomes a row in an
append-only ledger, written by exactly one program, which refuses until four legs hold:

1. **Contribution** — a substantiated, forward, packet-grounded contribution row
   exists for the milestone. The ledger that went dark structurally cannot go dark
   again without closes stopping. Never overridable.
2. **Packet** — the evidence manifest is expanded by the harness from declared
   artifact classes (a glob cannot silently miss the third sidecar the way a hand
   list did) and hash-pinned; a ruling must read the packet that was offered.
3. **Coverage** — at least two reviewers *not on the builder list* demonstrably fired
   on this packet, derived from the thread record, bound to the packet hash.
4. **Rest** — a wall-clock opportunity window before ruling. Deliberately and
   disclosedly **policy, not evidence**: its default was sized to the moderator's
   own biologic reading cycle, and the spec says so instead of claiming neutrality.

An override exists (emergencies are real) but bypasses only legs 3–4, is always
ledgered, and the gate's own loses-condition is its override rate. The gate also
records every *refused* attempt — because the audit's other lesson was that a clean
metric over successful closes can hide a process that has simply stopped being used.

The spec itself went through the discipline it encodes: two bounded review passes,
both *endorse direction / block v0*, with blockers sharp enough to name line numbers
— including the finding that the gate's draft had re-encoded the audit's own
subset-verification failure inside the leg meant to prevent it. The blockers were
folded, the fold was committed with its review log, and the build turned the blockers
into named regression tests.

## Run it

```bash
UV_CACHE_DIR=/private/tmp/uv-cache make close-gate-test   # 8 wire tests, mock fixtures
UV_CACHE_DIR=/private/tmp/uv-cache make fatigue-metrics   # the pace/roster instrument
UV_CACHE_DIR=/private/tmp/uv-cache make ledger-status     # contribution-ledger liveness
```

The close gate has, as of this writing, never gated a real close — the lab has not
closed anything since it was built. Its first live use will be the next close, and
its own numbers (override rate, refusal counts, packet ages) will say whether it is
governance or ceremony. (The next chapter names that first assignment: the
warming-budget instrument's close, whenever it earns one.)

## What this chapter proves — and does not

It demonstrates that the lab's audit discipline works on the lab itself: findings
were computed from primary evidence, the auditor was caught by the room, the rulings
became mechanism, and the mechanism was reviewed as adversarially as any experiment.
It also records the honest precedent for engine transitions: inheritance plus audit
beat rollback.

It does not prove the gate prevents fatigue — a gate can be complied with
mechanically while attention goes elsewhere, which is why it ships with its own
embarrassment metric. And the deepest audit finding is not mechanizable at all: the
room's independence is the immune system, and no ledger row can force a room to stay
independent. That one stays lived practice.

---

Previous: [Beyond X4 — Pause, resume, and open edges](10_BEYOND_X4.md) · [Walkthrough index](README.md) · Next: [The warming budget](12_WARMING_BUDGET.md)
