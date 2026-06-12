# Trace discovery — i75-appalachia excerpt

**Observations only — no episode design** (discovery before schema, the standing rule). Provenance: [raw/i75-appalachia.meta.json](raw/i75-appalachia.meta.json). Capture protocol: the previous lab's roadtrip checklist (referenced in the sidecar).

## Shape

- 68 lines: 64 `logEvent` JSON rows + 1 `{"count": 64, "finished": 1}` summary row + a 3-line `log show` footer naming the source archive. **Parsers must tolerate the trailer** — this is what `log show --style ndjson` actually emits, not clean NDJSON.
- Every event row carries: `timestamp` (local, -0400), `subsystem`, `category`, `messageType` (Default | Error | Fault), `eventMessage` (composed), `formatString` (template), `processImagePath`, `senderImagePath`, `threadID`, `bootUUID`, `backtrace`. `process` is absent; process identity lives in `processImagePath`.
- Interval: **2026-06-07 14:22:56 → 17:53:07 EDT** (~3.5 h, the afternoon leg).

## Channels present

| subsystem | rows | active window | character |
|---|---|---|---|
| com.apple.BackgroundSystemTasks | 26 | 14:22 → 17:53 (full) | locationd's task scheduling — the steady heartbeat |
| com.apple.CommCenterMobileHelper | 32 | 14:34 → 16:19 | cellular helper; all 32 are the same repeated Fault template (a category-mapping complaint, NOT a coverage fault) |
| com.apple.CommCenter | 2 | 14:34 → 16:28 | `lazuli.health.registration` — cellular registration health with slot/result/start/end fields; coverage-relevant |
| com.apple.CoreRoutine | 2 | 14:28 | the significant-locations learner, two Error rows |
| com.apple.wifi.analytics | 2 | 16:09 | daily background task bookkeeping |

**No `com.apple.CoreLocation` subsystem rows in the excerpt** despite the capture predicate including it — either the excerpt thinning dropped them or location fixes live elsewhere in the full archive. Open question below.

## The texture worth noticing (bounded claim)

After **16:28**, every cellular-side subsystem goes silent while the locationd-process heartbeat continues through **17:53** — including one 54-minute window with no events at all (16:28 → 17:23). That is shaped exactly like the checklist's target signature: *cellular silence while the location side stays alive ⇒ moving through no-coverage, not a dead or stationary device.*

**Why this is not yet a finding:** the excerpt is 64 rows over 3.5 hours — heavily thinned from the full archive. Cadence and gaps may reflect the excerpting, not the device. No claim about real dead zones survives until we know the thinning method and can compare against the full archive's density.

## Two observations for the room

1. **The OS runs its own offer boundary.** Format strings mark fields `%{public}` vs private; 4 values in this excerpt arrive as `<private>` — masked at the *source*, by the logging system itself. Unified logging is renderer-governance all the way down; our three-surface map has a precedent inside the trace substrate we're studying.
2. **Un-authored silence is data.** The coverage question is answered by event *cadence and absence*, not message content. Whatever oracle shape the trace track gets, it scores gaps — which means corpus-style "entry text" thinking does not transfer; the unit of evidence is the interval, exactly as the reserved `trace_interval` field anticipated.

## Open questions (for dan / the thread)

1. How was the excerpt thinned from the full archive — row sampling, subsystem filter, or time slicing? (Becomes `selection_method`; gates any cadence claim.)
> thinned with `log show` and time slicing.
>```
>sudo log show /Volumes/RoadtripCapture/iphone-trip.logarchive --start "2026-06-07 12:00:00" --end "2026-06-07 18:00:00" --style ndjson --predicate 'process == "locationd" OR subsystem == "com.apple.CoreLocation" OR subsystem BEGINSWITH "com.apple.wifi" OR subsystem CONTAINS[c] "timesync" OR subsystem CONTAINS[c] "CommCenter"' > /Volumes/RoadtripCapture/iphone-trip.ndjson
>```

2. Does the full archive contain `com.apple.CoreLocation` rows in this interval (nav was running per checklist)? The excerpt has none.
> No, but there is **com.apple.weather** from libraries **WeatherLocation** and **WeatherCore** from proc **weatherd**

3. Do the `lazuli.health.registration` rows in the full archive bracket the silent window — i.e., is there a registration drop/recover pair around 16:28/17:23?
> com.apple.CommCenter (lazuli.health.registration)
> #I Registration [ slot: 1, result: true, error_reason: 0, response_code: 0, start_time: 1780857266, end_time: 1780857267 ]
> #I Registration [ slot: 1, result: true, error_reason: 0, response_code: 0, start_time: 1780864098, end_time: 1780864099 ]
> #I Registration [ slot: 1, result: true, error_reason: 0, response_code: 0, start_time: 1780874280, end_time: 1780874281 ]
> #I Registration [ slot: 1, result: true, error_reason: 0, response_code: 0, start_time: 1780883765, end_time: 1780883765 ]

4. dan's coarse un-authored timeline (departure/arrival/noticed dead stretches, kept separate per checklist) — does a noticed dead stretch overlap 16:28–17:23? That comparison is the first world-truth check, and it must wait until the timeline is shared *after* any detector guess is registered (the checklist's own discipline: the answer key stays separate).
> noted and waiting...

## Resolutions (dan's answers, 2026-06-12 — analysis by claude)

**Q1 resolved — the cadence is real.** The excerpt is a pure time slice (12:00–18:00) with the capture predicate, no row sampling. Within the queried channels, gaps are the device's gaps. Two upgrades follow: the 54-minute all-quiet window is genuine channel silence, and the channels were genuinely empty 12:00→14:22 (2.4 h before the first event). Sidecar `selection_method` updated with the exact command.

**Q2 resolved — the location signal survives in a derivative, not the primary.** The full archive has no `com.apple.CoreLocation` rows in this interval, but carries `com.apple.weather` rows from `weatherd` (WeatherLocation/WeatherCore). Nav ran, yet the primary location subsystem is silent in the log while a *consumer* of location (weather updates fire on movement) leaks the motion signal. Trace-track lesson, red-team relevant: governing the primary channel does not govern its derivatives — the offer boundary has side doors. weatherd joins the predicate for the next pull.

**Q3 resolved — the registrations bracket the silence exactly.** Converting dan's quoted epochs (EDT): registration successes at **14:34:26**, **16:28:18**, **19:18:00**, **21:56:05**. The 16:28:18 success is the excerpt's final cellular event to the second; the next success is 2.83 h later, past the excerpt's end. Disclosed ambiguity: registration-health silence can mean *steady* coverage (no transitions) as well as *no* coverage — disambiguation needs the corroborating channels, which is the whole detector problem.

**Q4 — guess registered before the answer key.** With Q1 making cadence legitimate, the discipline activates: [DETECTOR_GUESS.md](DETECTOR_GUESS.md) commits four falsifiable guesses (primary: dead stretch ≈16:28→≥17:23 EDT) *before* dan shares his noticed dead stretches. The timeline comparison happens in the thread, against the committed guess, and neither side may be edited after.
