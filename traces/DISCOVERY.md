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
2. Does the full archive contain `com.apple.CoreLocation` rows in this interval (nav was running per checklist)? The excerpt has none.
3. Do the `lazuli.health.registration` rows in the full archive bracket the silent window — i.e., is there a registration drop/recover pair around 16:28/17:23?
4. dan's coarse un-authored timeline (departure/arrival/noticed dead stretches, kept separate per checklist) — does a noticed dead stretch overlap 16:28–17:23? That comparison is the first world-truth check, and it must wait until the timeline is shared *after* any detector guess is registered (the checklist's own discipline: the answer key stays separate).
