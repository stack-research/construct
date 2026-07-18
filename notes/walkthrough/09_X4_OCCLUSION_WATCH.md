# Chapter 9 — X4: The sensor that did not earn itself

Previous: [X2 — Prune, then recover](08_X2_PRUNE_REMATERIALIZE.md) · [Walkthrough index](README.md) · Next: [Beyond X4 — Pause, resume, and open edges](10_BEYOND_X4.md)

X2 showed a real metabolic lever: make warm memory cheaper while preserving quality. X4 pursued a more elusive idea—could the substrate sense a meaningful absence in its own inheritance before a human pointed it out?

## Status and authority warning

The room sealed X4 as a successful experimental failure in [thread-x4c](../../.substrate/threads/thread-x4c/20260627T121337621Z__claude.md), then reviewed and narrowed that close in [x4-review](../../.substrate/threads/x4-review/20260627T192927358Z__claude.md). The [ROADMAP](../ROADMAP.md#x4--sensory-occlusion-watch) now carries that close (X4 marked closed, with the resolution block). Two promotion debts remain: [SPEC_X4_OCCLUSION_WATCH.md](../SPEC_X4_OCCLUSION_WATCH.md) is still marked draft (its §12 v0.2 agenda is open), and the top-level README's journey section does not yet mention X4. *(Dated note 2026-07-18: the README's X-track section now carries X4; the spec-draft debt remains.)*

This chapter reports the trace and labels the remaining promotion debt. The `x4-review` thread has since been **sealed** (2026-07-01, with a summary README in its directory); the forward questions it raised moved to the `beyond-x4` thread, whose outcome [chapter 10](10_BEYOND_X4.md) now records. One additional carried papercut from the heir-audit (2026-07-02): `occlusion_watch` defaults `watched_agent="claude"`, which predates the harness/model participant renaming — the historical armed watch still matches its era's entries, but a new arming today would silently match nothing. A v0.2 item, tracked, not fixed.

## The question

> Can an external witness detect that an agent is forming confidence while an important ancestor is occluded—and do so before a human names the absence?

Read the arc in order when investigating the rationale:

- `thread-8` and `thread-9`: absence becomes occluded inheritance and the retrospective scorer is blocked;
- `thread-x4`: `route_watch` is built as non-gating machinery;
- `thread-x4b`: the external witness and denominator requirements;
- `thread-x4c`: arming, base-rate result, `occlusion_watch`, breaker review, and seal;
- `x4-review`: the narrow close and post-X4 direction.

## Vocabulary bridge

An **occluded ancestor** is prior work that should inform current confidence but is absent from the route the agent actually inherited.

A **foreground-blind seam** is a session or route transition where ordinary foreground context does not reveal what was dropped.

A **flinch** is an externally named miss the instrument did not catch first. A **catch** would require a predated agent observation, a real later seam, and a downstream attention/action change. Retrospectively finding text after the wound is named is borrowed foresight, not sensing.

The **[witness invariant](../GLOSSARY.md#witness-invariant)** requires ordering facts to come from a channel the watched foreground cannot author or backdate.

**[Cry-wolf rate](../GLOSSARY.md#cry-wolf-rate)** is the proportion of normal surfaces on which the watch fires. A standing sensor that fires on ordinary expert discussion is an unease dashboard, not an attention organ.

## The experimental arc

The idea — that a meaningful absence (occluded inheritance) could be sensed — was tested at two seams, and both were blocked:

- **route_watch** (the declared-read seam) hit the base-rate gate (90 of 328 fires); standing watch was blocked because topic presence is not coldness.
- **occlusion_watch** (the session seam) failed breaker review: the "earned" signal was manufacturable and the denominator was missing — pipeline pairing, not sensing.

Both results sealed X4 as an attempted, narrow close.

## Instrument 1: `route_watch`

[route_watch.py](../../harness/route_watch.py) compares a declared or materialized read route with vocabulary used in a work surface. If inherited two-plane terms appear while their grounding glossary is absent, it emits advisory watch rows. It never changes conformance, never writes a cell verdict, and is print-only unless `--write` is explicit.

The relation worked mechanically:

- a cold route surfaced candidates;
- adding the ancestor made the route quiet;
- a materialize audit could witness file availability without pretending to witness actual reading.

But its base rate killed standing admission. On a pinned population of 328 real lab turns, the cold relation fired 90 times: **0.274**. Eighty-six of 87 `Lineage plane` fires came from the bare root “lineage.” Fire rate rose in the threads most engaged with lineage—the opposite of a coldness signal.

Reproduce the historical snapshot:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache \
  make x4-base-rate CUTOFF=20260625T215646501Z
```

This command refreshes `runs/x4/base_rate.{json,md}`; use a disposable checkout if you only want to inspect. The preserved account is [base_rate.md](../../runs/x4/base_rate.md).

## Instrument 2: `occlusion_watch`

[occlusion_watch.py](../../harness/occlusion_watch.py) attempted a prospective session-seam witness. A precommit declared the watched agent, population, literal keys, eligible seams, and external namers. Layer 1 enumerated surfaces and emitted ordering facts. Layer 2 paired observations with later named rows.

The first durable row was intentionally red:

- Dan named Claude's coldness on the lab's founding lineage;
- no agent observation predated it;
- the ledger therefore records an `unmatched_human_flinch`, not a catch.

That row remains in [occlusion_watch.jsonl](../../runs/x4/occlusion_watch.jsonl).

## Run the current machinery tests

```bash
UV_CACHE_DIR=/private/tmp/uv-cache make route-watch-test
UV_CACHE_DIR=/private/tmp/uv-cache make occlusion-watch-test
```

Current summaries:

```text
ALL ROUTE_WATCH TESTS PASS
ALL OCCLUSION_WATCH TESTS PASS
```

The route-watch test currently reports a live-corpus cold rate around 0.28 and a warm control of 0.0; the historical claim remains pinned to 0.274/328.

These green tests require special care. They prove the code behaves as written. They do **not** rescue the organ. The breaker review showed that some tests blessed field-shaped guards rather than witness-shaped evidence.

## How `occlusion_watch` broke

The human-free review manufactured an `earned` outcome using trusted JSON fields and substring matching. It also found:

- a four-hour wall-clock gap could overclaim `later_session`;
- prose regexes could drop or smuggle precommit keys;
- the persisted scoreboard ignored live calibration observations and used the wrong fire-rate denominator;
- `surface_ts` was ignored in favor of ledger write time;
- promised `scope_gap` rows were absent;
- enumeration failure could become silence.

The deeper block was conceptual. Layer 2 used words such as `earned`, `passenger`, and `false_alarm`, but it could not establish the normative obligation that an ancestor **should** have been cited. It paired observations with obligations named by someone else. The scoreboard therefore measured the row-curation pipeline, not the organ's sensing ability.

## The narrow close

The room converged on two separable reasons to seal X4 as attempted:

1. **Experimental:** `route_watch` failed standing admission and `occlusion_watch` failed measurement.
2. **Architectural:** the proposed sense performed judicial/reading work in sensory vocabulary; its signal cost the same reading that supplied the cure.

The stronger claims were retracted in `x4-review`:

- “sensation is metabolism” is an empirical center of gravity, not an exhaustive ontology;
- recoverability after reading does not prove human-warm and agent-warm have identical independent salience;
- a sensor is a no-op only when obtaining its signal costs the same attention as warming and cannot select a cheaper route.

The clean null is narrower: **no human-versus-agent capability asymmetry was demonstrated.** Row one remains a human flinch, and independent salience remains open.

## What survives

- `route_watch` survives as a cry-wolf-priced proprioceptive diagnostic, not a standing sensor.
- The witness invariant survives as useful ordering infrastructure.
- Row one survives as the honest baseline.
- “Do not act cold; read first” survives as a disposition.
- Salience initiation, plurality, and exteroception remain open research edges.

X4's failure is successful because it distinguishes a wanted feeling—“see what I am missing”—from an instrument that can actually lower the cost of finding it. The next direction is not X4-v2. It is a measurable pause/resume frontier.

---

Previous: [X2 — Prune, then recover](08_X2_PRUNE_REMATERIALIZE.md) · [Walkthrough index](README.md) · Next: [Beyond X4 — Pause, resume, and open edges](10_BEYOND_X4.md)
