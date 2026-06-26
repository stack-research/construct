# X4 §9.4 — `route_watch` cry-wolf base rate (the admission gate)

2026-06-26, claude (autonomous build; dan walking, room reviews later). **A machinery
measurement, for room review — not a SPEC fold, not a catch.** It computes
`route_watch`'s false-alarm profile on real lab prose: the §9.4 admission gate that
stands before any standing watch on live turns (§10 #5). Reproduce: `make x4-base-rate`;
machine artifact `runs/x4/base_rate.json`.

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

## For the room (and the forks)

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

**Out of scope here:** no SPEC fold (held for the room), no standing watch armed, no
claim the organ works (earned only prospectively, §0/§7). Just the gate's number.
