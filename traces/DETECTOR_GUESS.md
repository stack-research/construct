# Registered detector guess — i75-appalachia

**Registered 2026-06-12 by claude, BEFORE dan's coarse trip timeline is shared.** This is the checklist's world-truth discipline: the guess is committed first, the answer key arrives second, and neither may be edited after the comparison. This is a *manual* guess (hand-derived from the excerpt plus dan's Q3 registration rows) — it sets the protocol precedent; a built detector repeats this mechanically later.

## Inputs used

Only: `traces/raw/i75-appalachia.ndjson` (64 rows, no-sampling time slice per dan's Q1 answer) and the four `lazuli.health.registration` rows dan quoted in DISCOVERY.md Q3. **Not used:** dan's timeline (unshared), the full archive, any map of I-75.

## Guesses

**G1 (primary, high confidence): a cellular dead stretch beginning ≈16:28 EDT, extending at least to ≈17:23 EDT.**
Reasoning: (a) active cellular chatter (CommCenterMobileHelper, 32 rows) runs 14:34→16:19 and then stops for good; (b) a registration success fires at 16:28:18 — registration *events* mark transitions, and this one is the last cellular event in the excerpt; (c) all channels, including locationd-process task scheduling, go silent 16:28→17:23 — background tasks are commonly network-gated, so even the local scheduler starving is coverage-consistent; (d) the next registration success is 19:18, a 2.83 h gap on a channel that had been chattering every few minutes.

**G2 (secondary, medium confidence): degraded or intermittent coverage continues past 17:23 until ≈19:18 EDT.**
After 17:23 the locationd heartbeat resumes on a clean 15-minute cadence (17:23 / 17:38 / 17:53) but no cellular subsystem returns within the excerpt. The 19:18 registration success is the first cellular life after 16:28. Ambiguity disclosed: registration-health silence can also mean *steady* coverage (no transition events to log). G2 leans on the corroborating absence of MobileHelper chatter, which was near-continuous when coverage was good.

**G3 (weak, low confidence): the device was idle/stationary or the early hours rolled off before ≈14:22 EDT.**
dan's slice requested 12:00–18:00; the queried channels are empty until 14:22:56. Either pre-departure idle (no nav, opportunistic logging only), or rolling-store loss as the checklist warned. No basis to pick between them from this excerpt.

**G4 (negative claim, medium confidence): coverage was healthy 14:34→16:19.**
Continuous cellular fault chatter is, ironically, a liveness signal: the stack was awake and talking.

## What would falsify these

dan's noticed dead stretches NOT overlapping 16:28–17:23 kills G1. A noticed dead stretch entirely inside 14:34–16:19 kills G4. A remembered departure well before 14:00 with nav running weakens G3's idle reading toward rolling-store loss.

## Scoring note

When dan shares the timeline (in the thread, after this commit), the comparison scores each guess separately. Coarse human recall is the oracle here — `human_judgment` source, confidence well below corpus-grade; that limitation is the point of the exercise, not a defect.
