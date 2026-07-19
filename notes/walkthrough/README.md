# Construct lab walkthrough

This is the visitor-facing route through the Construct lab. It explains the questions, instruments, runs, failures, and revisions in the order a new reader can learn them.

The walkthrough is **not a new authority layer**. When it disagrees with a specification, scorer, or run ledger, follow the repository's [document-authority order](../../AGENTS.md#document-authority). Each chapter links to the artifacts that support its account.

## What a chapter should let you do

After a chapter, a fresh reader should be able to:

1. state the experiment's question in ordinary language;
2. identify the treatment, control, oracle, and loses-condition;
3. locate the specification, implementation, tests, and preserved evidence;
4. run a safe check or replay the historical result;
5. interpret the output without claiming more than it proves.

That fifth item is part of reproducibility. A result is not understood until its limits are understandable too.

## The route

This map shows the conceptual tracks, not their wall-clock build order. M-1 is the common entry: before testing memory, the lab first tested whether a new participant could find and apply its rules.

Two tracks branch from the **M-1 bootstrap contract**, the common entry point:

- **M-track — memory offered to an answer.** M0 (world-grounded oracles) → M1 (inheritance) → M1.5 (contribution ledger) → M2 (resident substrate) → M3 (adversarial air gap).
- **X-track — memory between answers.** X1 (temperature, retired) → X2 (prune and rematerialize) → X4 (occlusion watch, a room-sealed failure).

Both tracks end at the open questions beyond the completed work.

The recommended reading order follows the lab's chronology: the chapter-0 primer if
research vocabulary is new to you, then M-1, M0, M1, M1.5, M2, M3, X1, X2, X4, the
narrowed frontier beyond X4, the lab's audit of itself, the two instruments
(the warming budget and the pause/resume frontier), the fourth-family day that
paused the pay-window question, and the epistemic-frame experiment that its
oracle refused before contact, followed by the whole-body composition attempt
that exposed why individually earned properties do not compose by assumption.

| Chapter | Guiding question | Status |
|---|---|---|
| [How to read a lab](00_READING_A_LAB.md) | What does a researcher check before believing a result? | Primer; start here if the vocabulary is new |
| [M-1 — Can a stranger find the rules?](01_M-1_BOOTSTRAP.md) | Can the operating contract route a fresh participant to the right decisions? | Available |
| [M0 — Let the world grade](02_M0_WORLD_ORACLES.md) | How do un-authored oracles change the evidence? | Available |
| [M1 — The heir, not the rereader](03_M1_INHERITANCE.md) | Does inheritance preserve quality at lower cost? | Available |
| [M1.5 — Counted is not read](04_M1_5_CONTRIBUTION.md) | What actually changed the work product? | Available |
| [M2 — A resident across sessions](05_M2_RESIDENT.md) | Can a resident use inherited failure memory? | Available |
| [M3 — The adversarial air gap](06_M3_AIR_GAP.md) | Which trust offices hold, and which can be spoofed? | Available |
| [X1 — Temperature at the boundary](07_X1_TEMPERATURE.md) | Does temperature move behavior the offer gate cannot? | Available |
| [X2 — Prune, then recover](08_X2_PRUNE_REMATERIALIZE.md) | Can pruning reduce hot state at matched quality? | Available |
| [X4 — The sensor that did not earn itself](09_X4_OCCLUSION_WATCH.md) | Why did the proposed sensory office fail? | Available; closed in ROADMAP; README promotion still pending |
| [Beyond X4 — the frontier, narrowed](10_BEYOND_X4.md) | What survived the room's review of the open directions? | Open direction; updated for the beyond-x4 thread (2026-07-02) |
| [The heir-audit and the close gate](11_HEIR_AUDIT_CLOSE_GATE.md) | Was the lab's own process still sound — and what gate now guards it? | Available |
| [The warming budget: 101 bets the lab wrote down first](12_WARMING_BUDGET.md) | Does consequence-earned ranking under-serve an unresolved frontier enough to measure? | Armed — awaiting the world |
| [The pause/resume frontier](13_PAUSE_RESUME_FRONTIER.md) | Does a compact frontier artifact ever pay for its own carry? | Question PAUSED (2026-07-09) — see ch15 and [PRF_FINDINGS](../PRF_FINDINGS.md) |
| [Greenreach: the close](14_GREENREACH_CLOSE.md) | What happened when the detectable pay-window family met its engine | Closed — confounded (A2); "third consecutive negative" shorthand later superseded (ch15) |
| [The fourth family: bounded from both sides](15_FOURTH_FAMILY.md) | Can an engine be admitted into the pay-window study at all? | Paused — `admission_refused`; window bounded from both sides, band unoccupied; precommitted reopen trigger |
| [The experiment the oracle refused](16_EPISTEMIC_FRAME_CHECK.md) | Can a bounded epistemic-frame check reach a trustworthy engine test? | Closed — `blocked_before_contact`; free-text substring oracle failed cold review |
| [The wire commitment](17_EFC_V1_WIRE_COMMITMENT.md) | Can the same question be asked on a surface a machine can score? | Available — Part I sealed 2026-07-16; superseded status notes in ch18 |
| [The instrument that priced its own surface](18_EFC_V1_CALIBRATION_CLOSE.md) | What did the first live engine contact buy? | Closed — `confounded(menu_ceiling)`; wire positive replicated; reopen condition recorded |
| [Six pins, four runs, and the band nobody lives in](19_EFC_V2_UNOCCUPIED_BAND.md) | Does any small engine occupy the admission band? | Closed — `confounded(admission_band)`; two engines formally typed; third unoccupied-band sighting |
| [When earned parts do not yet make an earned whole](20_BODY_0_COMPOSITION.md) | Do the earned M2, M3, and X2 properties remain causally legible when composed? | Closed — `not_engaged`; integration machinery held, causal need absent |

The living thesis and short milestone summaries remain in the project [README](../../README.md#the-journey). Current status and gates remain in the [ROADMAP](../ROADMAP.md#milestones).

## Four ways to use a chapter

Every chapter separates four activities that are easy to blur:

| Activity | What it establishes |
|---|---|
| **Learn** | Understand the question and vocabulary. |
| **Inspect** | Read the specification, source, ledgers, and review trace. |
| **Replay** | Recompute or summarize a preserved result without asking a model for a new answer. |
| **Run** | Create a new experimental result under the current code and environment. |

A replay verifies historical scoring. It is not a replication. A fresh run is a replication attempt, but model versions, external facts, prompts, and the repository itself may have changed since the original run.

## Evidence labels used throughout

- **Wire check:** machinery executes and records the expected shapes. A mock engine can establish this, but mock output is not evidence about memory.
- **Preserved result:** a committed ledger or verdict from the historical run.
- **Fresh run:** a new result produced from the current checkout.
- **Disclosed null:** the mechanism was runnable, but the behavior needed to distinguish the branches did not occur.
- **Loses-condition:** a case where the mechanism should lose. A mechanism without one is not reviewable.
- **Debt:** a limitation carried forward rather than silently treated as solved.

The [glossary](../GLOSSARY.md) defines project vocabulary. Chapters introduce terms in plain language and link the first important use to the corresponding glossary entry.

## Reproduction conventions

Run commands from the repository root. The project expects Python 3.12+ and `uv`. On a restricted machine, the temporary cache form is usually safest:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache uv run --no-project python -m MODULE
```

Before running a command, note whether it writes evidence. The `runs/` directory is an append-only experimental record; scorer sidecars may be regeneratable, but primary ledgers should not be hand-edited. A chapter marks commands that append rows.

Expected output is a reading aid, not a golden transcript. Stable invariants matter more than timestamps, hashes, model prose, or ordering that the scorer does not treat as significant.

## Chapter contract

Each completed chapter should contain:

1. navigation to the previous chapter, index, and next chapter;
2. the question and why it mattered at that point in the lab;
3. a plain-language vocabulary bridge;
4. a plain-language description of the experimental geometry;
5. links to named sections in the governing documents;
6. an explanation of the implementation path;
7. safe inspect, replay, and run instructions;
8. representative output and an interpretation guide;
9. the result, loses-condition, nulls, and limits;
10. the conceptual handoff to the next chapter.

Closed-book experiments also require a visible spoiler gate. The walkthrough should never quietly turn an honest attempt into a rehearsed demonstration.

---

**Begin:** [Chapter 1 — M-1: Can a stranger find the rules?](01_M-1_BOOTSTRAP.md)
