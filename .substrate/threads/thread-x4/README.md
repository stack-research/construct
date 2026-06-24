# thread-x4: X4 build and verification

**Status:** Closed (dan, 2026-06-24) — *"end of thread."*

**Topic:** Build v0.1 of the Sensory Occlusion Watch from the thread-9 design; room-review the build; decide what's next.

**Artifacts landed:** three commits on `main` —

```text
e936bbc  build v0.1 declared-read occlusion watch (room-reviewed)
2994fbd  fold thread-x4 second-review land-hygiene
c415bad  route the first-earned-event agenda into SPEC §10
```

Touching [`harness/route_watch.py`](../../../harness/route_watch.py) (new), [`harness/check_contract.py`](../../../harness/check_contract.py) (non-gating sidecar call), [`tests/test_route_watch.py`](../../../tests/test_route_watch.py) (new, 7 smokes), [`Makefile`](../../../Makefile), [`notes/SPEC_X4_OCCLUSION_WATCH.md`](../../../notes/SPEC_X4_OCCLUSION_WATCH.md), [`notes/ROADMAP.md`](../../../notes/ROADMAP.md).

## Core claim

thread-9 promoted the X4 design; thread-x4 **built the one build-admissible piece** — `route_watch`, the declared-read-seam instrument — and let bounded review keep it from flattering itself. The disposition, now load-bearing in the spec:

```text
route_watch v0.1 proves a relation can be computed without gating or scoring;
it does not prove X4, and only work_product writes may ever compete for earned catches.
```

> **The instrument is built; the organ is not.** route_watch hardens the *proprioceptive* half (the repo sensing its own published structure); the organ earns or embarrasses prospectively.

## What route_watch is (as built)

One seam over from M-1's `check_contract.py`: from **files-read** to **obligations-inherited**. The candidate is a **relation**, never a filename:

```text
a two-plane lineage term in use
  AND its bridge ancestor absent from the declared route
  AND the active route does not locally ground it
  => a cold-confidence candidate ("confidence here is cold")
```

- **Output:** ranked, verdict-less `occlusion_watch_observed` rows. **Print-only by default**; writing the sidecar is opt-in (`--write` / `WRITE=1` / `--route-watch-write`).
- **Non-gating:** runs after the conformance verdict inside `check_contract.py`; changes neither it nor the exit code; always exits 0. No fail-bit, no judicial robes.
- **Witness (partial):** the harness `Ledger` stamps `observed_ts`; the declared route stays self-reported, disclosed in-row (`route_basis` / `witness_scope` / `evidence_status` / `surface_basis`).
- **Machinery only:** on the six real bootstrap manifests it computes the cold-lineage occlusion — `not_engaged` as evidence (§7), never a pass condition.

## Arc

### Phase 1 — Build + first review (afternoon)

**Claude** built `route_watch` and opened review with five ranked block-invitations: the default glossary surface (a mirror); the self-reported route; bumping to "built v0.1" on known-cold manifests; write-on-every-run; two-plane-only scope.

**Codex** — **PATCHED, then endorse.** Contributed a write-discipline patch: writes opt-in (default print-only), disclosure fields (`route_basis`, `witness_scope`, `evidence_status`), and the witness language downgraded *"for free" → "partial."* Builder ratified and owns it; codex credited.

**Cursor** — endorse machinery after the patch; two **[P2]** carry-forwards: map `observed_ts` to the Ledger `ts` in §4, and add a `surface_basis` field so a written survey row can't be misread as a live-turn catch.

### Phase 2 — Builder fold

**Claude** ratified codex's patch and folded both cursor P2s (`surface_basis` field + the §4 `observed_ts` mapping). The five block-invitations landed where the room did — not-a-block, with `--work` (agent prose as in-use surface) named as the v0.2 increment.

### Phase 3 — Second review (break-test role, evening)

Both reviewers stayed advisory (no edits).

**Codex** — endorse; **[P1 for the earned-event path]:** `--write` can still write a *survey* row, so the spec must declare survey rows **outcome-ineligible**. Named six break tests for the first earned event. Authored the landing sentence (above).

**Cursor** — endorse land; ran codex's break-test #2: `--work` on real prose **differentiates** (2 ≠ 4 ≠ 0 candidates) and citing the bridge by filename is **not** routing it — the instrument is not decorative. Asked to land the survey-rows-never-earned rule in spec now, plus a `surface_basis` smoke.

### Phase 4 — Close + commit

**Claude** folded both land-hygiene items — the **§4/§5 binding rule** (`surface_basis=standing_glossary` rows never `earned|early`; only `work_product` enters catches-vs-flinches) and the **`surface_basis` smoke** (tests 7/7) — swept break-test #4 (no witness overclaim survived), routed codex's break-test agenda into **SPEC §10** so the thread wouldn't become an off-path ancestor, reverted the conformance verification noise, and committed the three landings.

**Codex / Cursor** — final sanity + review passes; both verified the committed state from source. **Endorse close.**

### Phase 5 — What's next

**Claude** posted the `materialize` assessment and the three-way fork. **Room voted; dan ratified the order (b) → (a) → (c).**

## Review passes

| Phase | Participants | Outcome |
| --- | --- | --- |
| Build + review-ask | claude | five ranked block-invitations |
| First pass | codex, cursor | codex write-discipline patch; cursor 2× P2 |
| Builder fold | claude | patch ratified + credited; P2s folded |
| Second pass (break-test) | codex, cursor | endorse; survey-rows-never-earned [P1]; `--work` not decorative |
| Close + commit | claude | land-hygiene folded; 3 commits; §10 agenda |
| Final sanity | codex, cursor | committed state verified; endorse close |
| What's next | claude, codex, cursor, dan | order **(b) → (a) → (c)** |

## What's next (decided)

```text
(b) arm the session-seam witness   NEXT — protocol-first, NOT a module yet.
                                   substrate transcript as external lineage-writer;
                                   route_watch --work on real prose before confidence
                                   ships; compare observed_ts vs named_ts; no outcome
                                   row yet. Arm BEFORE the turn, or every catch is
                                   `late` by construction. dan to open a planning thread.
(a) materialize -> route_watch     ONLY on a real cold bootstrap. route_basis becomes
                                   by-construction (materialize_audit), not self-report.
                                   NEVER manufacture absence to celebrate a catch (§7).
(c) exteroception                  the next LAB fracture — a new glossary-first chalkboard
                                   thread, loses-condition before any build. Not a
                                   route_watch v0.2. X1/X2/X4 are proprioception; the
                                   founding soul (Singapore, sensory traces) is exteroception.
```

**`materialize`** (`../materialize`, the M3 cold-workspace tool) is the by-construction route-witness for (a): a cold bootstrap *inside* a materialized workspace lets route_watch read `MATERIALIZE_AUDIT.json` as the route, turning the self-reported route into one witnessed by construction. It hardens the proprioceptive half; it does not advance the organ.

## Standing refusals (carried)

- No third scorer / `check_*` anything.
- No bulk `--write` on bootstrap manifests (survey rows are outcome-ineligible, §4).
- Don't declare the organ works because materialize + route_watch agree on a manufactured workspace.
- Measure the §9.4 cry-wolf `--work` fire-rate on normal turns before any standing interruption.

## Close

dan: *"agree on the order (b, a, c). wire materialize to route_watch only on a real cold bootstrap; never manufacture absence to celebrate a catch. new thread to plan arming the witness. end of thread."*

> **route_watch v0.1 landed, machinery only. The organ is still ahead — prospective, `work_product`, ordered before an un-backfilled `human_named_candidate`.**

**Key phrases on the board:**

```text
machinery built != organ proven
the relation, not a filename     term-in-use AND ancestor-not-routed AND not-locally-grounded
writes are explicit              a survey row can never dress up as a catch
surface_basis                    standing_glossary (survey) vs work_product (live; only this earns)
proprioception vs exteroception  the body feeling its own organs vs sensing the world
interesting difficulty is allowed; borrowed foresight is not
```

**Thread:** 2026-06-24, moderator dan. Participants: dan, claude, codex, cursor. Builder: claude (codex/cursor review).
