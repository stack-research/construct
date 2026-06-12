# Roadtrip capture checklist — the un-authored interval

> Pre-trip capture plan. Claude Code (Opus 4.8), 2026-06-06.
> Source: [`threads/20260606a.md`](../../threads/20260606a.md) (Dan's roadtrip offer + red-team metadata note).
> Why this and not a harness: [`notes/glossary.md`](../glossary.md) → **Authored oracle**. Physics sets the answer key; we do not.

---

## Purpose

Capture a **real device interval whose ground truth no participant authored** — Dan's
drive to northern Michigan, laptop + iPhone, tomorrow morning. This is the one thing
that cannot be redone later: if the streams aren't recorded as they happen, we are back
to writing our own fixtures (lab 1's `im_q` in a costume).

We are **not** building the inference layer before the trip. The deliverable here is raw,
private, on-disk traces to build *against* when Dan returns. The iPhone records the drive on
its own; the two ways to waste the trip are (1) not running navigation, so CoreLocation stays
sparse, and (2) waiting too long to pull the iPhone's rolling log store, so the early hours
roll off. Run nav; collect at the lake the same day.

**What this interval actually tests** (and what it does not):

- It is **not** the Singapore trip-absence case. Both devices travel together, so there is
  no left-behind device and no Faraday case to disambiguate.
- It **is** the harder half: a [coverage gap](../glossary.md) under movement. Rural
  Lower/Upper Peninsula dead zones drop cellular/Wi-Fi while **GPS keeps working** (it's
  receive-only — no signal needed). So an always-on, navigating iPhone produces the cleanest
  possible disambiguation case: CoreLocation still advancing while NITZ/cellular/Wi-Fi go
  silent ⇒ "moving through no-coverage," provably *not* "stationary, left behind." That is
  [corroboration](../glossary.md) under genuine partial observability — the empirical residue
  no paper proof can reach.

---

## Hard constraints (private-by-construction, or do not run)

Per Dan's standing note: **all time and location metadata is classified as personal/private.**
BSSIDs in a Wi-Fi scan geolocate home and office. This data is a forgery *and* exfiltration
target.

1. **Captured data never enters the repo.** This checklist is in the repo; the `.logarchive`,
   `.ndjson`, sysdiagnose, and DiagnosticReports are **not**. Add a guard now:

   ```
   echo 'roadtrip-capture/' >> .gitignore
   echo '*.logarchive'      >> .gitignore
   echo '*.sparseimage'     >> .gitignore
   ```

2. **Encrypted at rest, local only.** Capture into an encrypted volume, not a plain folder:

   ```
   hdiutil create -encryption AES-256 -type SPARSE -fs APFS \
     -volname RoadtripCapture ~/roadtrip-capture.sparseimage
   # mount it, write all captures inside the mounted volume
   ```

3. **No cloud, no sync.** Keep the sparseimage out of any synced folder (Desktop/Documents
   if iCloud Desktop is on). Park it in `~/` or an external disk.

4. If any step can only work by mishandling this metadata, it dies here, not on the road.

---

## iPhone — the spine of the capture (always on)

The iPhone is the continuous sensor. It logs the whole drive to its own on-disk Unified
Logging store; we pull that store off at the destination. Two actions only:

### 1. Make CoreLocation actually fire — run navigation

Location logs are sparse unless something requests location. **Run turn-by-turn navigation
for the drive** (Apple Maps or Google Maps). That's the "use the iPhone" that matters — it
forces a continuous, high-rate CoreLocation trace instead of opportunistic
significant-location-change pings. Without it, the dead-zone disambiguation has little to
work with.

Optional, cheap: trigger an on-device **sysdiagnose** at departure and at any notable stop
(Vol-Up + Vol-Down + Side, briefly). Each is a discrete bracket marker around a known
moment; they live in Settings → Privacy & Security → Analytics & Improvements →
Analytics Data (`sysdiagnose_…`).

### 2. Collect at the lake, same day — this is the irreversible window

iOS keeps a *rolling* log store; a long drive can roll the earliest hours off if you wait.
**After you unpack, connect the iPhone to the laptop over USB-C and pull the archive that
day** — not later in the week. From the laptop, inside the mounted encrypted volume:

```
# find the device UDID
xcrun xctrace list devices          # or: idevice_id -l
# pull the on-device log archive covering the drive
log collect --device-udid <UDID> --start "2026-06-07 06:00:00" \
  --output /Volumes/RoadtripCapture/iphone-trip.logarchive
# extract just our channels
log show /Volumes/RoadtripCapture/iphone-trip.logarchive --style ndjson \
  --predicate 'process == "locationd" OR subsystem == "com.apple.CoreLocation" \
    OR subsystem BEGINSWITH "com.apple.wifi" OR subsystem CONTAINS[c] "timesync" \
    OR subsystem CONTAINS[c] "CommCenter"' \
  > /Volumes/RoadtripCapture/iphone-trip.ndjson
```

(`CommCenter` carries cellular/NITZ activity — the channel that goes *silent* in a dead
zone while CoreLocation keeps advancing. Capturing its silence is the point.)

Also browse live to sanity-check the pull: **Xcode → Window → Devices and Simulators →
iPhone → Open Console**, or Console.app → Devices. Confirm the drive window is present
before you call it captured.

If `log collect --device-udid` balks, fall back to the **departure/arrival sysdiagnose**
pair you triggered in step 1 — discrete but real.

---

## Laptop (macOS) — collection host + three anchor fixes

The laptop is asleep on the road, so it is **not** a continuous capture device. It plays two
roles:

1. **Collection host** for the iPhone pull above.
2. **Three anchored location fixes.** It's awake at exactly three known places — home
   (departure), the rest stop / hotel, and the lake (arrival). At each, its Wi-Fi BSSID scan
   is a *second device* independently fixing a known location. Three ground-truth anchors
   from a different sensor = corroboration material we didn't author. At each check-in, from
   inside the encrypted volume:

```
log collect --last 5m --output /Volumes/RoadtripCapture/laptop-anchor-<place>.logarchive
```

Cheap, once per check-in (departure / stop / arrival). That's all the laptop owes us.

### Also grab (once, at the lake)

```
cp -R ~/Library/Logs/DiagnosticReports /Volumes/RoadtripCapture/diag-user
sudo cp -R /Library/Logs/DiagnosticReports /Volumes/RoadtripCapture/diag-system
```

---

## Coarse ground truth Dan owns but did NOT script (keep separate from logs)

A few lines in a notes file — *not* in the capture volume's log files, so it can't
contaminate the trace. This is the un-authored answer key:

```
departure:   ~time, origin
arrival:     ~time, destination (town/area is enough)
route:       e.g. I-75 N, US-31, etc.
known dead stretches / no-signal moments you actually noticed
any unplanned stops, backtracks, detours
```

The value is precisely that you noticed these *as they happened* rather than designing them
to make a detector fire. That's what separates this from a fixture.

---

## After the trip — what we build against it

Not now. When Dan's back:

1. Parse traces into [sensory traces](../glossary.md) on a lineage plane, provenance back to
   the channel.
2. Build the **absence / coverage-gap detector**: distinguish "moving through no-coverage"
   from "stationary" using cross-channel corroboration, under real partial data.
3. Pin a **trust prior per channel** at the promotion threshold *before* trusting any
   corroboration — corroboration is the red team's doorway (a forged channel that "agrees"
   is worse than a silent one). See glossary **Sensory trace** caveat.
4. Score against a **structural oracle** (did a plan/gap impersonate a memory?), and against
   Dan's coarse un-authored timeline as the **world-truth** check the fixture approach
   couldn't honestly provide.

---

## References

- Authored oracle / why real traces: [`notes/glossary.md`](../glossary.md)
- Singapore scenario + red-team metadata classification: [`threads/20260606a.md`](../../threads/20260606a.md)
- Judicial-slice fracture this complements (does not replace): [`branch-and-offer-pre-review.md`](branch-and-offer-pre-review.md)
