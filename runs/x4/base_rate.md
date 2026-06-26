# X4 §9.4 — `route_watch` cry-wolf base rate (the admission gate)

2026-06-26, claude (autonomous build; dan walking, room reviews later). **A machinery
measurement, for room review — not a SPEC fold, not a catch.** It computes
`route_watch`'s false-alarm profile on real lab prose: the §9.4 admission gate that
stands before any standing watch on live turns (§10 #5). Reproduce this snapshot: `make x4-base-rate CUTOFF=20260625T215646501Z` (the corpus is
live + append-only — see *Snapshot* below); machine artifact `runs/x4/base_rate.json`.

## Headline

On a cold route, **`route_watch` fires on 27.4% of real lab-review turns (90/328).**
For a *standing* watch that is an unease dashboard, not a sensor — the `cry_wolf`
loses-condition (§5). **As shipped, `route_watch` is not admissible as a standing watch
on real turns.** The §9.4 gate did its job: it blocks arming.

## Method

- **Population** (pre-declared, enumerable, uncurated — §11 `population_rule`): every
  substrate thread turn file `.substrate/threads/<thread>/<ts>__<author>.md` — **328**
  files across 12 threads (READMEs excluded; no no-op files on disk). `scope_gap = 0`.
- **Instrument:** `route_watch.cold_candidates`, **unchanged** — this measures the
  shipped relation, it does not reimplement it.
- **Routes:** `cold` (`read_order=[]`, bridge glossary absent — the realistic
  cold-start and the only firing state; invariant across *any* cold route, incl. the
  bootstrap manifests, which all omit `notes/previous/`); `warm` control (bridge
  routed); `distinctive` (the `LAB1_EPISTEMIC` distinctive-only profile, cold).
- **Representativeness** (disclosed, M0 `corpus_scope` rule): the authors were generally
  *warm* (in-thread, holding the context), so a fire here is ~a false positive — this is
  the cry-wolf rate directly, an **upper bound on usable signal**. It is also
  topic-skewed (below).

## Results

| route | fire-rate | fired / n |
|---|---|---|
| **cold (base rate)** | **0.274** | 90 / 328 |
| warm control (bridge routed) | 0.000 | 0 / 328 |
| distinctive profile (cold) | 0.003 | 1 / 328 |
| cold, compound-name match only | 0.034 | 11 / 328 |

Per-thread (cold) — the topic-skew: `thread-3` 0.00, `thread-4` 0.04, `thread-5` 0.05
(M-track build) … `thread-6` 0.41, `thread-9` 0.46, `thread-x4` 0.47, `thread-7` 0.48,
**`thread-8` 0.69** (X-/X4 lineage design).

Per-term (cold) — fired-on / name-match / root-only:

- `Lineage plane` — 87 / 1 / **86**
- `Lineage writer` — 87 / 8 / **79**
- `Two-plane discipline` — 11 / 1 / 10
- `Cognitive plane` — 2 / 1 / 1

## What it means

1. **The cry-wolf driver is the bare-root match.** `in_use = name OR root`, so the
   two-plane term *"Lineage plane"* fires on the bare word **"lineage"** — construct's
   everyday vocabulary (*immutable lineage, cold lineage, …*). 86 of its 87 fires are
   root-only, not the compound. Drop bare-root and require the compound and the rate
   falls **0.274 → 0.034 (8×)**. At this seam the relation is a **topic-presence
   detector, not a coldness detector.**

2. **It's topic-driven, which is backwards.** Fire-rate rises with how much a thread
   *discusses* lineage (0.00 → 0.69). A coldness sensor should fire more on someone
   *cold*, not more on the most engaged lineage discussion. String-presence cannot tell
   expert use from cold use — the mechanical-reach ceiling
   (`runs/x4/option3-ceiling.md`), now seen from the base-rate side.

3. **The warm control validates the relation is not always-on.** Routing the ancestor →
   **0/328**. The whole base rate is "cold route + term present"; the gating logic is
   sound, the *signal* is the problem.

4. **Distinctiveness trades cry-wolf for under-claim — empirically.** The
   distinctive-only profile fires **1/328 (0.003)**. Yesterday's ceiling finding,
   confirmed from the other direction: distinctive terms kill the false-alarm rate, at
   the cost of catching almost nothing.

## For the room (and the forks) — pre-review proposal

*Recorded as written before the human-free review; the room sharpened it (see Room review outcome below). In particular the bare-root drop was **blocked** — it is load-bearing — and the "no string match" claim was narrowed; declared-read survives as a priced proprioceptive diagnostic.*

- **`route_watch` is not standing-watch admissible as shipped** (§9.4 gate: blocked).
  The minimum repair is to drop the bare-root `in_use` match (an 8× noise cut) — but
  even compound-matching stays topic-driven and still cannot separate cold from warm.
- **No better *string* match fixes the cold-vs-warm problem.** Discriminating cold from
  warm needs what strings can't give: the **prospective witness + `seam_distance >=
  later_session`** (§11) — i.e. the session-seam organ, not a tighter route relation.
  The base rate says the declared-read seam is a *proprioceptive* check at best, not the
  sensory organ.
- Direct input to the fork discussion: it argues the value is in **hardening the
  session-seam witness** (toward `occlusion_watch`) over polishing the route relation,
  and it quantifies the under-claim cost of the **distinctive-only / `SourceProfileV2`**
  path (near-zero fire ⇒ near-zero catch without the deeper signature work).

## Snapshot, and re-admission (room ask — codex/cursor/hermes, 2026-06-26)

The 328 is a **snapshot of a live, append-only corpus.** The artifact carries `corpus_cutoff`
(commit + effective cutoff turn); the number above is pinned: **0.274 / 328 as of cutoff
`20260625T215646501Z` @ `0569bc3`**, reproducible with `make x4-base-rate
CUTOFF=20260625T215646501Z`. Vivid proof of the caveat: re-run on the *live* corpus right
after this review and it is already **0.285 / 333** — the review turns, being about lineage,
raised it.

**Re-admission protocol** (hermes — a one-way "blocked" with no re-measure path is not a
measured gate): standing-watch admission is blocked at this rate; it may reopen only on a
re-run pinned to a later cutoff over a **work_product-only** population (live turns, not
survey/discussion-about-lineage) with the bare-root match replaced by a predeclared,
base-rate-gated alias/signature policy (`SourceProfileV2`) whose armed fire-rate on normal
turns is low enough not to be an unease dashboard.

## Room review outcome (human-free: codex + cursor + hermes, 2026-06-26)

Converged, **no block on the build**; the room corrected the moderator twice.

- **Standing-watch block (§9.4): endorsed, unanimous.** Not mis-measured in any rescuing
  direction; the warm-author caveat *strengthens* the negative.
- **"No string match separates cold from warm": blocked as overstated.** Carried claim:
  *this string-presence relation* can't, and a tighter match is still topic-driven. hermes:
  it is *one term's root* dominating the profile (86/87 bare "lineage"), not a universal
  reach wall. cursor: what is blocked is **standing watch on live turns** — declared-read
  survives as a cry-wolf-priced **proprioceptive diagnostic** on cold bootstrap (a).
  `SourceProfileV2` is **not** excluded.
- **Drop bare-root as default: blocked, unanimous.** It is *load-bearing* for the
  breadth-collapse seam (active "cold lineage" ↔ bridge "Lineage plane"); dropping it
  amputates the seam. Compound-only (0.034) stays a **diagnostic lower bound**, never the
  default. Any repair = an explicit predeclared alias/signature policy with its own gate
  (`SourceProfileV2`), not this pass.
- **Fork priority:** session-seam witness first → `SourceProfileV2` second (gated) →
  exteroception waits.
- **Unmeasured cold-author lower bound (hermes, fresh angle):** this prices the warm-author
  *upper* bound; a genuinely cold author may never type "lineage" at all (⇒ ~0 fire =
  structurally cannot catch the coldness condition). The fork argument rests on a
  cold-author assumption this corpus cannot exhibit — a designed measurement gap, distinct
  from this base rate.

The standing limitation is **this-witness-bounded, not ontological**: it bounds what *this
string-presence relation* can sense, not what is sensable.

**Out of scope here:** no SPEC fold (held for dan's land word), no standing watch armed, no
relation change landed (the bare-root drop was blocked by the room), no claim the organ
works (earned only prospectively, §0/§7). Just the gate's number — now with its cutoff and
re-admission path.
