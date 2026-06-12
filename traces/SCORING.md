# Detector-guess scoring — i75-appalachia

**The answer key (dan, 2026-06-12, in thread):** "a few and very brief [dead spots], this was a stretch in the mountains of TN and KY along I-75. But, GPS was always active and regained at least minimal cellular connectivity within minutes."

Scored against the committed guesses in [DETECTOR_GUESS.md](DETECTOR_GUESS.md) (registered before this recall was shared). No edits to either side after this point.

| guess | claim | verdict |
|---|---|---|
| **G1** (primary, high conf) | cellular dead stretch ≈16:28 → ≥17:23 EDT (~55 min) | **FALSIFIED** |
| **G2** (secondary, med) | degraded/intermittent past 17:23 to ≈19:18 | **partial / unconfirmed** |
| **G3** (weak, low) | idle or rolled-off before 14:22 | **unresolved** |
| **G4** (negative, med) | coverage healthy 14:34→16:19 | **consistent** |

## G1 was wrong, and the error is the finding

I read a ~55-minute all-channel silence (16:28→17:23) as a sustained coverage gap. dan's recall says the opposite: dead spots were *brief*, minutes-long, cellular always recovered fast. A 55-minute outage is not "a few and very brief."

**What I actually did:** inferred *outage* from *silence* on a single channel family, without the cross-channel corroboration the checklist explicitly demands. The registration-health rows even pointed the other way and I underweighted them: successes at 14:34 / 16:28 / 19:18 / 21:56 are *sparse*, and sparse registration transitions are what *steady* coverage looks like — a phone that keeps losing and regaining signal logs *more* registration churn, not less. The silence meant the queried channels had nothing to report (stable state), not that the device was dark. That is the registration-silence ambiguity I flagged in DISCOVERY.md §Q3 — and then walked straight into.

## Why this is a good outcome, not an embarrassment

This is the checklist's world-truth discipline doing exactly its job. The guess was committed first, in git, before the recall arrived; the recall falsified it cleanly; and the failure names a specific, transferable lesson for the eventual built detector:

- **Silence is not absence.** A coverage-gap detector must require corroborating positive evidence of signal loss (registration *drop* events, failed-attach rows, CommCenter error transitions), not merely the cessation of chatter. Absence-of-events is the null hypothesis, not the alarm.
- **GPS-always-active is confirmed from the side door, not the front.** dan says GPS never dropped; the log has zero `com.apple.CoreLocation` rows. The only location signal in the archive is the `weatherd` derivative (DISCOVERY.md §Q2). So the one channel that would have *directly* corroborated "moving through coverage" was the silent one, and motion had to be inferred from a consumer. The detector's hardest real-world case is precisely this: the primary sensor is quiet and you must triangulate from derivatives.

## What survives

G4 stands: 14:34→16:19 had continuous cellular chatter — coverage was healthy through the early leg, consistent with "a few brief" spots rather than a sustained dead zone. G3 stays unresolved (dan's recall doesn't reach before 14:22). G2 is unconfirmed: "intermittent, brief" is *closer* to dan's account than G1's sustained framing, but I won't claim a partial win on a guess whose headline duration was wrong.

## Scoring provenance (for the eventual oracle row)

- oracle source: `human_judgment` (coarse recall), confidence well below corpus-grade — the stated limitation, not a defect.
- This is a *manual* scoring of a *manual* guess: it sets the protocol precedent (commit guess → reveal key → score, no edits). A built detector repeats it mechanically against the same key.
