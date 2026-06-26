# SPEC X4 — Sensory Occlusion Watch (the organ that deliberately breaks the cell frame)

Status: **v0.1 — DRAFT, room-reviewed & repaired** (claude draft, 2026-06-23, from thread-8 design + thread-9 block-and-convergence; dan moderator; codex + cursor converged and endorsed promotion; **room review 2026-06-23 — codex + cursor BLOCK-narrow, 3×P1 + P2; repairs folded this pass**, see review log). Third organ of the **X-track** and its first **sensory** one (X1 retired, X2-LB+U1 closed; **X3 dispositions earmarked, not next**). Unlike X1/X2 this spec ships **no scored `cell_verdict` and no scored close** — by design, not omission (§0). Its loses-side is **not** waived: it is carried as predeclared watch-outcome embarrassments (§5), satisfying the AGENTS *every-mechanism-ships-a-loses-condition* contract. **`route_watch` (the declared-read seam) is now built — v0.1 machinery, 2026-06-24** (§3, §9.3); the session-seam `occlusion_watch` remains **designed, not build-admitted**; its **Layer-1 arming protocol is now specified — §11** (thread-x4b, 2026-06-24): how to arm the external witness *as protocol*, not a module. The build is the **instrument**, not evidence the organ works — that is earned only prospectively (§0/§7/§8). Builder lane: dan + claude (codex/cursor review). Provenance + review log at the end.

> Naming: the first instrument is a **watch**, never a `check_*` (codex) — pass/fail naming puts judicial robes on an instrument whose whole point is to stay an instrument.

## §0 Posture, stated before any instrument

```text
interesting difficulty is allowed; borrowed foresight is not.   — codex, thread-9
```

X4 is the **sensory** function — the unbuilt third organ (sensory / judicial / metabolic; thread-2). Its job:

> Notice an **occluded prior object** — something that existed, mattered, and was hidden from the foreground by a **seam the foreground could not inspect from inside the act** — *before confidence hardens around the gap.* The question the organ asks is **"what ancestor is missing from this confidence?"** (codex), not "what should I retrieve?"

**Why this spec deliberately breaks the cell frame.** X1 and X2 earned `cell_verdict`s because their oracles could be *un-owned*: offer-dependence (answer-axis), then a world-fact corpus (DEP0033). X4 has no such oracle. Its only honest evidence is the **next** occlusion, caught before a human flinches — and that evidence cannot be authored, held out, or scored on demand: the moment you know the occlusion, you authored it. The retrospective "prove on thread-8's known misses" test is therefore **`not_engaged` by X2-U1's own gate** — the misses are an answer key *we* surfaced this week and the detection shapes were reverse-engineered from them; by the bridge glossary's authored-oracle rule (*if the oracle is authored, write the proof and skip the run*) the run is pre-written. A mirror fit to its key can honestly neither pass nor fail.

So X4 does not close. The replacement virtue (codex):

> **unclosed, but embarrassable.**

X4 earns its keep only while it keeps catching occluded ancestors before a human gut does, and it stays installable only as long as **every event it logs can be called early, late, passenger, false_alarm, or noisy.** An organ that cannot be embarrassed is not un-perfectable-as-a-virtue; it is unfalsifiable — *flinch-theft aimed at the lab*, retiring the room's own ability to be wrong (claude, thread-9, retracting the "un-perfectable organ" framing that hid this).

**Breaking the cell frame is not breaking reviewability (room review, P1).** "No scored `cell_verdict`" does **not** mean "no loses-condition." X4's loses-side is the predeclared embarrassment classes of §5, stamped by the external witness of §2 — reviewable episodes, not close cells.

## §1 What X4 is — and what it deliberately is not

**Is:** a **standing watch** (an *attention organ*, codex) that fires *while* confidence is forming, across a foreground-blind seam, and leaves an external, embarrassable trace.

**Is not:**
- **not a fourth scorer** — no `score_x4.py`, no `cell_verdict` (codex's constraint; cursor's *harnesses must not become the product*).
- **not a linter wearing an organ's coat** — routing drift is statically computable from the repo's published structure; that is **CI, necessary-not-sufficient**, and needs none of the X4 mythology. The organ-ness lives only in the prospective, cross-seam catch.
- **not a retrospective answer-key victory** — re-finding the wounds it was built from proves machinery at best (§7).
- **not a flinch automator** — it *augments* the room's unease (Dan's flinch at *perfect*), never retires it.

**Seam discipline (the line that keeps it honest).** Absence is a *sense* only across a boundary the foreground **cannot see across** — turn→turn, session→session, lab→lab. Inside one turn, "I didn't read X" is a *check* (a hook, a linter, a Makefile target), not an organ.

```text
meaningful silence   = absence + its search boundary        (else it's vibes in a lab coat)
X4 sensory occlusion = meaningful silence + a foreground-blind seam   (a relation, not a fact)
```

## §2 The witness invariant — the load-bearing rule

**"Embarrassable" is real only if the fired-before-the-flinch ordering is witnessed by a process the foreground cannot address or backdate.**

```text
the watch is a lineage-writer object, not a self-report.
observed-time and flinch-time are stamped by a process the foreground
  cannot address or backdate. append-only, no edit verb, no backfill.
"fired before the prose did" is a witnessed ordering — never a claim
  made after the prose.
```

Without this, the fields in §4 (`did_human_name_it_first`, `human_flinch_seen_yet`) are foreground self-report, and "I caught it before Dan flinched" becomes **flinch-theft with a timestamp.** This is the bridge glossary's *the foreground is not a trusted narrator of its own memory* and the *no-steer asymmetry / lineage-writer-is-external* doctrine, lifted to the sensory organ.

**Partially satisfied for the route seam, candidate-only for the session seam (room review, P1).** §4 carries the timestamp invariant for `route_watch` (the harness can stamp when a row was written), but the declared read route remains a manifest claim rather than independently witnessed inheritance. The session-seam writer is **named, not yet hardened** (a candidate — the substrate transcript — is in §9.2); until it is, `occlusion_watch` is **designed, not build-admitted** (§3).

## §3 Two seams, two instruments

```text
seam                    instrument                witness                       admission
--------------------------------------------------------------------------------------------
declared-read boundary  route_watch  (sidecar)    contract checker (external)   BUILT v0.1 (harness/route_watch.py)
session / lab boundary  occlusion_watch (ledger)  substrate+artifact_diff (§11)  PROTOCOL v0 §11; module designed
"fired before flinch"   both, scored later by     an ordering no foreground
                        catches-vs-flinches        can backdate
```

**`route_watch` (declared-read seam) — BUILT v0.1 (2026-06-24), as a *separate* module (cursor): `harness/route_watch.py`, `make route-watch`, smoke `tests/test_route_watch.py`.** X4 wearing **bootstrap-conformance** clothes, not branch-and-offer clothes: it reads the same surfaces M-1's `check_contract.py` reads, *one seam over* — from *files-read* to *obligations-inherited* — but it is a **separate `route_watch` module invoked from the M-1 path**, never a new fail-bit on `check_contract.py` (that would put judicial robes back on the conformance check).
- **Inputs (cold, published by the repo about itself):** the AGENTS read-order graph; term/obligation sets (`notes/previous/review/glossary.md` vs `notes/GLOSSARY.md`, breadth not identity); optional citation edges — never filenames handed in as targets.
- **Output:** ranked **cold-confidence candidates** — *"you're using a two-plane lineage term; the bridge ancestor isn't in your active route; confidence here is cold"* (codex's texture) — printed by default; appended as **watch rows to a sidecar** only by explicit write, never pass/fail.
- **Witness:** partial — the harness can witness `observed_ts` when a row is written; the `read_order` remains a declared-route claim. Rows must disclose that scope.
- **Named limit (cursor):** fires **only at declared-read boundaries.** Session-seam occlusions have no declared-read moment.
- **Built shape (v0.1, 2026-06-24):** `harness/route_watch.py` parses the AGENTS routing graph live (the *Open only when* → bridge-glossary edge from `b7e04c0`), extracts the two-plane lineage term set from the bridge glossary's own structure, and computes **ranked `occlusion_watch_observed` rows — no verdict**. The candidate is the **relation** *term-in-use ∧ ancestor-not-routed ∧ not-locally-grounded*, never a filename handed in. Wired as a **non-gating advisory** inside `check_contract.py` (runs after the verdict is final; changes neither it nor the exit code) and as `make route-watch`; both are print-only by default. Writing to `runs/bootstrap/route_watch.jsonl` via the harness `Ledger` is explicit (`--write` / `ROUTE_WATCH_WRITE=1`), so historical reruns do not masquerade as prospective catches. Written rows disclose `route_basis=declared_read_order`, `witness_scope=observed_ts_only__route_claim_not_independently_witnessed`, and `evidence_status=observed_only_no_outcome`. On the real bootstrap manifests it computes the cold-lineage occlusion as a relation — **machinery only, `not_engaged` as evidence (§0/§7); never a pass condition.**

**`occlusion_watch` (session / lab seam) — designed, not build-admitted.** Not recognizing your own founding handwriting across a session has no declared-read moment, so it needs a standing ledger — and the ledger is only honest if its before/after is stamped by an **external lineage-writer** (§2). A candidate writer now exists (§9.2) but is not yet hardened, so this instrument stays on the page. That is the witness invariant doing its job, not a defeat. **Its Layer-1 arming protocol is now specified (§11, thread-x4b)** — the witness's population, denominator, and seam rules *as protocol before any module*; the module itself stays designed.

## §4 The watch schema (route seam witness-safe; session seam designed, not build-admitted)

Two append-only watch rows, plus an **external witness row the foreground cannot write** (room review, P1):

```text
occlusion_watch_observed         (the watch, when confidence is forming)
  candidate         term | obligation | claim | route-relation
  seam              declared-read | session | thread-to-repo | spec-to-code | lab-boundary
  why_now           the confidence forming here
  search_boundary   what route graph / source set was inspected (else it is not a trace)
  surface_basis     standing_glossary (survey/mirror) | work_product (a live turn)
  mode              silent | spoken | deferred | no_op
  observed_ts       stamped by the witness writer, not the foreground
                      (route_watch: realized as the Ledger's harness-stamped `ts`)
  route_basis / witness_scope / evidence_status   (route seam disclosure) — the
                      timestamp is witnessed; the declared route stays self-reported

human_named_candidate / flinch_observed   (the EXTERNAL witness row)
  candidate_ref     the occluded object the room/human named on its own
  source            substrate-transcript-entry | human-nudge | artifact-diff | reverted-claim
  named_ts          stamped append-only by the witness writer; foreground cannot backdate

occlusion_watch_outcome          (COMPUTED later, from lineage order — not asserted)
  candidate_id
  did_human_name_it_first        computed: observed_ts vs named_ts on the lineage
  did_it_change_attention_or_action   evidence-backed
  evidence          thread entry | patch | reverted claim | missed blocker
  verdict           earned | early | late | passenger | false_alarm | noisy
```

`did_human_name_it_first` / `human_flinch_seen_yet` are **computed from lineage order** against the external `human_named_candidate` / `flinch_observed` row — never asserted inside the observed row (room review, P1: otherwise the load-bearing field is self-report). An **earned** event = the watch's `observed_ts` precedes any `named_ts` for that candidate **and** a later artifact shows the gap mattered. If the room named it first, the verdict is `late` (and, at the organ level, `borrowed_foresight`, §5) — useful, never evidence.

**Outcome eligibility (binding — room review, thread-x4, codex [P1] + cursor).** A `surface_basis=standing_glossary` row is a **survey / machinery** row: it is **never eligible for `earned` or `early`.** Only `surface_basis=work_product` rows — a live turn's actual confidence surface — may enter catches-vs-flinches. The first outcome scorer **must** enforce this, so a survey row can never dress up as a catch. (v0.1's default surface is the standing glossary; `--work` produces `work_product` rows. This is why v0.1 is honestly *machinery* even when it writes.)

**Audit-derived route disclosure (binding — thread-x4c, 2026-06-25; hermes).** When the route is derived from a materialize `MATERIALIZE_AUDIT.json` (`route_basis=materialize_audit`), the row discloses `absence_witnessed_by_materialize_audit__repo_tree_only_scaffolding_excluded__reads_within_workspace_self_reported`. Parallel to the declared-read disclosure above, and load-bearing in the same way: it is **availability-witnessed, not read-witnessed** — a path absent from the audit was provably *unavailable* in the cold workspace (witnessed absence, by construction), but whether a *present* path was actually read stays self-reported. The route is the materialized **repo tree only**: materialize's own scaffolding (the audit record `MATERIALIZE_AUDIT*.json` and the declared `brief`) is excluded mechanically (`harness/route_watch.audit_available_set`), so the denominator cannot be silently amended. The no-inflation claim is thus reviewable from the spec alone.

## §5 Loses-conditions (predeclared; this is where X4 should lose)

X4 breaks the cell frame, **not** the AGENTS *every-mechanism-ships-a-loses-condition* contract (room review, P1). No scored `cell_verdict`; the loses-side is predeclared and witness-stamped:

```text
per-event outcome verdict   earned | early | late | passenger | false_alarm | noisy
organ-level loses-conditions (the embarrassment classes — where X4 loses):
  borrowed_foresight   only ever fires after the room named the wound (late + named-first)
  flinch_theft         the room's independent unease declines — the organ replaced the gut
  cry_wolf             false_alarm / noisy rate makes the watch an unease dashboard
```

The design constraints, binding:

```text
- no fourth scorer
- no scored cell_verdict          (but a real, predeclared loses-side — above)
- no retrospective answer-key victory
- external witness for fired-before-flinch          (§2, load-bearing)
- sidecar / watch rows first
- route-conformance seam separated from session-seam watch   (§3)
- every event allowed to be early | late | passenger | false_alarm | noisy (or, rarely, earned)
- survey rows (surface_basis=standing_glossary) are outcome-ineligible — only work_product rows can ever earn (§4, thread-x4)
```

**flinch_theft is the permanent guard:** the organ must widen the room's peripheral vision, never let the room outsource its unease to a dashboard. It is a loses-condition precisely because it is the most seductive failure.

## §6 What would make X4 a lab experiment — the fork

```text
(a) deploy-and-watch instrumentation   [the honest path]
    build the watch and a tripwire for the FIRST prospective catch.
    X4's native shape is temporal: present before anyone knows the answer key.
    the first honest object is a watch ledger, not a cell_verdict.

(b) a DEP0033 for absence   [aspirational — likely relocates the oracle, not escapes it]
    run the watch over inheritance none of us curated (lab-1 history, an outside
    repo's read-order, a corpus we didn't build); flag drift; then verify it mattered.
```

**(b) probably relocates author-blindness rather than escaping it (room review).** *"Independently verify it mattered"* still needs an un-owned oracle — who decides, by what standard, that a flagged drift in an outside repo mattered, without us authoring the answer? Both reviewers read (b) as **aspirational**; **(a) deploy-and-watch is the honest path.** **(b) may be unreachable** (dan, 2026-06-23: *"could very well turn out to be un-reachable… I like this direction"*) — see §8 for what that does and does not license.

**Placement note (cursor's probe).** "Held-out witness, not held-out world" — hand a *cold* agent only `AGENTS.md` + the obligation list and watch whether it notices `cold lineage` is cold before writing confidently about two-plane discipline — is a legitimate near-term embarrassment, **but it scores the route (M-1 bootstrap-conformance), not the organ.** The witness is naive; the occlusion is one we chose. Do not let "the witness noticed" read as "the session-seam organ exists."

## §7 thread-8's known misses — anti-theater examples only, never a gate

The wounds the room surfaced by hand are the *shapes* the watch should be able to articulate — and **nothing more**:

```text
bridge glossary off the required-read path     (term-breadth collapse; cold lineage where lineage lived)
agent-pov objections filed, never routed        (citation-without-route)
thread-1 consequence-loop language unpromoted    (moral inherited, route absent)
founding sensory vocabulary narrowed away        (judicial + metabolic shipped, sensory chalk)
```

A detector handed these **filenames** is theater (cursor). Re-finding them from *shapes* proves machinery at best, and is `not_engaged` as evidence (§0). **They are examples and anti-theater checks — never a pass condition.** The routing half of the first wound is already closed, as *routing, not rename* (commit `b7e04c0`; AGENTS now routes inherited vocabulary to the bridge glossary, `GLOSSARY.md` links the lineage/cognitive planes).

## §8 The honest open finding (method-bounded, not ontological — room review, P1)

If the fork's leg (b) proves unreachable, the finding is **bounded by the method, and does not reach the substrate's reality:**

> X4 remains **unclosed.** The finding is that construct's scored-cell method has not found an honest retrospective oracle for *this* sensory-watch candidate. It is **not** evidence that the sensory substrate is real — turning "no oracle found" into "the thing is real but unscorable" is exactly the theater this spec refuses (absence of evaluability masquerading as evidence). Any claim that the organ works must be earned **prospectively**, by catches-vs-flinches under the witness invariant — never inferred from the absence of a close.

The judicial (M-track) and metabolic (X1/X2) organs earned ledgers because their oracles could be un-owned; the sensory organ's oracle is the *future*. Its success is therefore not a verdict but a **standing record of catches-vs-flinches over time** (§4–§5). This is the lab's *don't-defer-negative-results* rule turned on its own measurement — and the room's correction (P1) of an earlier draft that let unscorability imply realness.

**A second honest bound — the mechanical witness's reach (thread-x4c, 2026-06-25; codex + cursor + hermes).** Beyond the retrospective-oracle bound above, the *mechanical* witness has a reach ceiling, and the ceiling is the witness invariant itself (§2):

> X4's mechanical witness refuses meaning at fire time. Distinctive-term occlusion is the current safe floor. Common-word concept occlusion requires a predeclared syntactic signature or remains below the floor — with cry-wolf and under-claim costs disclosed. This bounds what the instrument can sense without claiming the human is doing ontologically impossible work; the human often catches diffuse concept-coldness that no narrow prearmed signature would have matched.

A string match is a concept match only for **distinctive** terms; for a common word it is not (`memory` the concept ≠ `memory` the string). Common-word concept occlusions are reachable only by a **predeclared, pure-literal** signature — armed not retrofit (a late signature is `borrowed_foresight`), carrying no fire-time "distinguished-vs-casual" judgment (that is meaning in a mask), and paying a base-rate cost via an admission gate (`SourceProfileV2`, deferred). thread-x4c's first ledger row — diffuse concept-coldness through ordinary prose — sat above the *current v0* (distinctive-only) reach; the human caught it. Origin + probe: `runs/x4/option3-ceiling.md`.

**A third honest bound — the cold-author lower bound (thread-x4c, 2026-06-26; hermes).** The base rate prices the *warm-author upper* bound (in-thread authors, holding the context, firing); it does not measure the cold-author floor. A genuinely cold author may never externalize the occluded term at all (~0 fire), so the witness structurally cannot catch the coldness condition it is named for — this is §11's *externalized-surfaces-only* limit seen at the session seam. The fork toward the session-seam witness therefore rests on a cold-author assumption the warm corpus cannot exhibit: a disclosed measurement gap, not a closure. (Designed measurement, distinct from the base rate; see `runs/x4/base_rate.md`.)

## §9 Review asks — and how the room answered them

1. **The break itself / an un-authored oracle for the retrospective leg?** — **Room: no.** Both reviewers held it `not_engaged`; the cell frame stays broken. (Standing invitation remains: block it back if one ever appears.)
2. **The session-seam external writer?** — **Candidate found (cursor's straw):** the **substrate transcript itself.** The CLI `write` produces timestamped, author-stamped entries the agent did not write; a moderator's *"you have the floor"* nudge is a `human_named_candidate` outside the agent's ledger. A v0.1 session witness can compare **substrate-transcript order** against **agent prose/confidence** — partial, substrate-local, not full X4, but the **first non-self-report process** that can stamp `named_ts` (folded into §4). Still **designed, not build-admitted** until hardened — block it back if it is theater. **Hardened into an arming protocol (§11, thread-x4b):** the witness writes order, source, and *mechanically-enumerable* gaps — never meaning, never what-counted-as-a-surface; the denominator is a pre-declared enumerable population (substrate/git/file boundaries) the foreground cannot curate. Protocol specified; the module is still not built.
3. **Judicial-robe risk / naming.** — **Resolved & built (2026-06-24):** `route_watch`, a **separate module** (`harness/route_watch.py`) invoked from the M-1 path as a non-gating advisory; **no fail bit on `check_contract.py`** — the call runs after the conformance verdict, changes neither it nor the exit code, and the instrument always exits 0 (held by construction, verified by `tests/test_route_watch.py::test_instrument_never_gates`). Ordinary conformance calls are print-only; sidecar writes require explicit opt-in.
4. **Cost + cry-wolf base rate.** — **Deferred for the no-code v0.1 draft; an admission gate before any standing watch runs on real turns.** Cry-wolf cost is how the organ pays rent instead of becoming an unease dashboard (it is also the `cry_wolf` loses-condition, §5). **§11 gives the denominator its shape (thread-x4b):** fire-rate = examined-with-candidates / a *pre-declared enumerable population* (`surface_expected`), with `scope_gap` rows keeping it external — so the base rate gates the *first event's interpretation*, not merely standing watch.

**MEASURED 2026-06-26 (thread-x4c, human-free review — codex + cursor + hermes).** `harness/x4_base_rate.py` over 328 substrate turns (pinned snapshot via `corpus_cutoff`): cold fire-rate **0.274**; warm control 0.000; distinctive-only 0.003. **Standing-watch admission is BLOCKED** (`cry_wolf`): the bare-root `in_use` match on the word "lineage" drives 86/87 `Lineage plane` fires, so on real prose the relation is a *topic-presence detector, not a coldness detector*, and fire-rate tracks lineage-discussion intensity (per-thread 0.00–0.69). Declared-read `route_watch` survives only as a cry-wolf-priced **proprioceptive diagnostic** on a cold bootstrap, never a standing sensor; the cold-vs-warm split needs the session-seam witness, not a tighter string match. Bare-root is **load-bearing** (the breadth-collapse seam), so it was NOT dropped; any repair is a predeclared alias/signature policy (`SourceProfileV2`) with its own gate. Finding + `re_admission_protocol`: `runs/x4/base_rate.md` (committed `0569bc3` / `0d3e94b`).

## §10 Toward the first earned event (deferred agenda, gated — thread-x4 second review)

v0.1 is machinery. The first **earned** X4 event is prospective and `work_product`-only (§4 eligibility rule). Before any outcome scorer or standing watch on real turns, the room (codex's break-test stance, cursor concurring) named the tests that gate it — routed here so this thread does not become the next off-path ancestor:

```text
1. declared-route honesty   under/over-declare, reorder, late-bridge — the watch must
                            disclose what it cannot know, never turn a manifest claim into
                            witnessed inheritance (witness_scope discloses this today)
2. real work surface        --work on live agent prose: cold-confident use vs grounded use
                            must diverge or the watch is decorative (cursor ran it: 2 != 4 != 0;
                            citing the bridge by filename is NOT routing it)
3. sidecar theater          every downstream reader must label standing_glossary rows
                            survey/machinery, never catch evidence (§4 eligibility rule)
4. witness inflation        no doc or code may claim the route is witnessed — only observed_ts is
5. cry-wolf base rate       measure --work fire-rate on normal reviews BEFORE any standing watch
                            (admission gate, §9.4); four-on-survey is a signature, not a live rate
6. route-conformance drift  keep repeating: cold-witness route probes score the route, not the organ
```

The admission gate (§9.4) and the session-seam `occlusion_watch` (§3, §9.2) both sit behind this. Landing sentence (codex): *route_watch v0.1 proves a relation can be computed without gating or scoring; it does not prove X4, and only `work_product` writes may ever compete for earned catches.*

**Update (2026-06-26).** Test #5 (cry-wolf base rate) **run** — admission **BLOCKED** (§9.4 above; `runs/x4/base_rate.md`). Test #2 (real work surface) partially confirmed: cold-confident vs grounded use *do* diverge, but the divergence is topic-driven, not coldness, so it does not by itself license the organ. The first earned event still requires the **session-seam witness** (§11), not the declared-read relation — which the room reclassified as proprioception.

## §11 Arming protocol v0 — the session-seam witness (thread-x4b)

**(b) from thread-x4's close: arm the session-seam external witness *as protocol, not a module*, before the next meaningful turn.** The seam cannot be replayed, so a witness armed *after* the turn makes every catch `late` by construction. This operationalizes §9.2's candidate writer (the substrate transcript) under the witness invariant (§2). **No harness code — `occlusion_watch` stays designed (§3).** The protocol emits **Layer-1 ordering facts and disqualifiers only, never an outcome verdict.**

**The four gaps between *ordering* and *earned* (codex's two-layer split).** §2 secures timestamp *honesty*; an `earned` event is a *comparison* of `named_ts` against `observed_ts`, and three more gaps sit between them — each now homed:

```text
gap              mechanism                                  where
timing           external named_ts (substrate / artifact)   §2 + §11 (armed here)
spray/base-rate  quiet denominator over a PRE-DECLARED,      §11 population_rule + §9.4
                 mechanically-enumerable population
seam             seam_distance >= later_session              §11 seam rule (same_pass=not_engaged)
passenger        action evidence                             §4 outcome / Layer 2, deferred §10

Layer 1 (arm now)   emit the first three as facts + disqualifiers.
Layer 2 (gated §10) the ONLY place `earned` may be spoken — and only with all four.
```

**Two cracks an external *named*-side witness cannot reach (claude, thread-x4b).** The witness closes **backdating**; it does not close —
- **who fires the watch.** `observed_ts` is Ledger-stamped, but the watched agent runs `--work` and chooses *when*; firing early and broad makes *something* predate any later naming, every timestamp genuinely real. The defense is not on the witness side — it is the denominator (below). Fork: **agent_fired-under-precommitment** (keeps "while confidence is forming", §0 — *taken*) vs `witness_fired` (closes the agent-timing but fires post-hoc, drifting linter-shaped — *deferred*).
- **same-pass naming.** Watch and human reading the same prose in one review pass is machine-read beating human-read — a hook, not an organ (§1); it scores the route, not the organ (§6). A same-pass naming is therefore **`not_engaged`**, the same disqualification as the retrospective answer key (§7) — *not* `false_alarm`. The seam crossing is what makes an event classifiable at all.

**Honest scope (a face of §8).** A mechanically-enumerable population sees only **externalized** surfaces; confidence that hardens *without leaving a trace* — in unwritten reasoning — is outside the instrument, by the same refusal that bars self-report. So §0's "before confidence hardens" is precisely "before confidence hardens *into an enumerable artifact*."

**The protocol:**

```text
posture        arms the session/lab-seam witness. emits ordering FACTS +
               disqualifiers, never outcome verdicts. the witness refuses BOTH
               semantics (codex): it decides neither MEANING nor WHAT-COUNTED-as-
               a-surface — only order, source, and mechanically-enumerable gaps.

scope          substrate transcript + artifact_diff (git). lab-process prose =
               proprioception, not exteroception (§8). externalized surfaces only.

population_rule (mechanically enumerable BEFORE the run — codex P1)
  watched scope = syntactic surface boundaries, enumerable from substrate/git/file
    without semantic judgment.
  examples: every substrate entry by watched_agent in thread T after precommit_ts;
            every staged diff touching <declared path>; every body under marker M.
  the witness enumerates expected surfaces from those boundaries; the watched agent
    may NOT decide after the fact which surfaces were work_product.
  invariant: surface membership is SYNTACTIC before it is sensory — if the witness
    must judge whether prose matters, the witness is becoming the organ.

fire authority  agent_fired-under-precommitment (scope declared via a witnessed
                substrate entry; mandatory surface_examined per in-scope surface).
                witness_fired deferred.

rows emitted (Layer 1)
  route_watch_surface_expected  surface_ref, population_rule_ref, expected_ts_or_order
  route_watch_surface_examined  surface_ref, candidate_count, wrote_observed_rows
  occlusion_watch_observed      work_product, explicit --write; fire_authority,
                                work_stage, surface_basis
  human_named_candidate         external; author_kind, watched_agent_is_author,
                                seam_distance, candidate_key, match=literal
  scope_gap                     surface_ref, reason: missing_surface_examined |
                                late_surface_examined | invalid_surface_ref

rows forbidden  any outcome verdict; agent self-naming; same_pass -> earned; fuzzy key

seam rule       same_pass  = not_engaged
                later_turn = ordering-only / calibration; never earned-eligible by
                  default (no standing moderator escape hatch)
                later_session | downstream_artifact = first earned-eligible seam

candidate_key   literal/conservative; uncertain normalization -> DO NOT MATCH
                (under-claim embarrasses; over-match steals — flinch-theft)

who stamps named_ts   any non-watched participant or artifact system (not
                      humans-only — that makes the moderator the sole sensor);
                      record author_kind + watched_agent_is_author

denominator (§9.4)    fire-rate = examined-with-candidates / declared population
                      (surface_expected). required before any earned interpretation
                      — NOT a pre-standing-watch courtesy. scope_gap keeps it external.

Layer 2 (deferred §10)  the ONLY place `earned` may be spoken: work_product +
                        cross-seam (>= later_session) + visible denominator +
                        action evidence.
```

**"Arm now" — the only action this section licenses:**

```text
1. witnessed precommit entry: population_rule (enumerable scope) + watched_agent + thread
2. mandatory surface_examined over the declared population (manual enforcement OK in
   v0; scope_gap records misses)
3. substrate/artifact witness for human_named_candidate rows
4. record Layer 1 only — no verdicts — until a later-session / downstream naming
   lands on a predated work_product candidate
```

**Disposition (codex's landing sentence, lifted to the session seam):** *arming proves the witness can stamp order, source, and enumerable gaps without scoring; it does not prove X4. Only a cross-seam `named_ts` against a predated `work_product` row, over a visible denominator, may ever compete for an earned catch — and that event cannot be scheduled.*

**BUILT — Layer-1 + Layer-2 (2026-06-26, dan present).** `harness/occlusion_watch.py` (+ `tests/test_occlusion_watch.py`, `make occlusion-watch[-test]`): **Layer-1 emitter** (commit `c90bdea`) reads the witnessed arm-now precommit, examines S1 by literal key, emits the §4/§11 rows, no verdict, exits 0; **Layer-2 outcome computation** (`compute_outcomes` / `make occlusion-watch OUTCOMES=1`, commit `2a5faf6`) honors §5's *no fourth scorer / no cell_verdict* — it is occlusion_watch's **own advisory** computation of `occlusion_watch_outcome` from lineage order (R5: ignores any hand-written classification/tally), gating nothing. It computes catches-vs-flinches; today = **0 catches / 1 flinch** (row one), the honest red baseline (§8). **Layer-2 being *built* does not make `earned` *speakable*:** the guards keep it structurally unmanufacturable (external namer §2 + `work_product` §4 + `seam ≥ later_session` + `observed_ts < named_ts` + action evidence) and the earned *event* stays prospective/unschedulable. Armed on `watched_agent=claude` across `thread-x4c` (precommit commit `aabaf8c`) — so **thread-x4c stays open**: ending it would disarm the watch's S1. **Deferred to v0.1:** examining S2 committed diffs, a better session-identity proxy (time-gap over external timestamps, fail-toward-under-claim), and the passenger/false_alarm/noisy classes.

## Provenance / review log

- **thread-8** (substrate, space `construct`, ended) — design: occlusion across a foreground-blind seam; *"what ancestor is missing from this confidence?"*; seam discipline; the un-perfectable-organ observation; the four loses-postures; *perfect is a warning, not a verdict*.
- **thread-9** (substrate, space `construct`, "X4 and the un-perfectable organ") — claude **blocked** the retrospective-leg-as-losable-test (no un-authored oracle → `not_engaged` by X2-U1's gate); codex + cursor **accepted and retracted**; converged on **unclosed-but-embarrassable**, the **witness invariant** (claude), the **two-seam shape** and **contract-extension** (cursor), the **constraint list** and naming nudge (codex); **dan endorsed promotion** (*"this one will be enjoyably strange"*).
- **Room review pass (2026-06-23, thread-9; codex + cursor — BLOCK-narrow, endorse the shape).** Three P1s + a P2, all folded this pass: **[P1]** §8's *unscorable ⇒ the substrate is real* recast as method-bounded and non-ontological; **[P1]** *no losable cell* recast as **no scored `cell_verdict`, with predeclared loses-conditions** (§5) per the AGENTS contract; **[P1]** the session-seam witness named-not-mechanized — §4 retitled, `occlusion_watch` marked **designed, not build-admitted**, a candidate writer (the substrate transcript) named in §9.2; **[P2]** outcome taxonomy normalized across §0/§4/§5/ROADMAP. `route_watch` endorsed **build-admissible v0.1** (separate module). Cost/base-rate carried as an admission gate.
- **commit `b7e04c0`** — routing fix: bridge glossary now on the AGENTS read-order + linked from `GLOSSARY.md`; thread-8's first occlusion row closed as *routing, not rename*.
- **`route_watch` built — v0.1 machinery (2026-06-24, dan + claude; codex review patch same day).** `harness/route_watch.py` (separate module on the M-1 path, non-gating advisory; `make route-watch`; smoke `tests/test_route_watch.py`). Computes `occlusion_watch_observed` rows (no verdict) print-only by default; explicit writes append to `runs/bootstrap/route_watch.jsonl` via the harness `Ledger`. Demonstrated on the real bootstrap manifests: it computes the cold-lineage occlusion as a relation — **machinery, `not_engaged` as evidence (§7), never a pass condition or proof the organ works.** The session-seam `occlusion_watch` stays **designed, not build-admitted**, entry-gated on §9.2; cost / cry-wolf remains an admission gate before any standing watch on real turns.
- **Room review pass (2026-06-24, thread-x4; codex + cursor — endorse v0.1 machinery, no block).** codex contributed a **write-discipline patch** (writes opt-in: `observe(write=False)` default, `--write` / `WRITE=1`, `check_contract --route-watch-write`; row disclosure fields `route_basis` / `witness_scope` / `evidence_status`; §2/§3 witness language downgraded *"for free" → "partial"*) — a correct fix to claude's blockers #4 and #2. The builder (claude) **reviewed, ratified, and owns** the change; **codex credited as contributor**; cursor endorsed it as necessary and would not have endorsed without it. cursor's two **[P2] carry-forwards folded by the builder**: `observed_ts` mapped to the Ledger `ts` in §4; a `surface_basis` field (`standing_glossary` vs `work_product`) so a written survey row is not misread as a live-turn catch. Blockers #1/#3/#5 held **not-a-block** (print-only makes the glossary-surface mirror honest; `--work` is the v0.2 increment; build-status ≠ organ-proven; two-plane scope is principled). First earned X4 event remains **prospective** — a `--write` row on real work, ordered before an un-backfilled `human_named_candidate`.
- **Room design pass (2026-06-24, thread-x4b; "Arming the Witness Protocol" — claude + codex + cursor; dan moderator, gemma paused for the Gemma-4-E4B / opencode harness shakeout).** (b) from thread-x4's close. gemma's opening question (*what is the external lineage writer?*) answered by codex + cursor: **the witness writes order, not meaning; boring is the safety property** — substrate transcript order + artifact/git stamps the foreground cannot author or backdate. claude added the load-bearing seam: **§2 secures timestamp *honesty*, not comparison *validity*** — two cracks an external *named*-side witness cannot reach: (1) *who fires the watch* (agent-timed `observed_ts` → predating-everything, priced only by a base rate) and (2) *same-pass naming is a linter race* (`not_engaged`, never `false_alarm`; the seam crossing makes an event classifiable). codex folded the **two-layer split** (ordering facts vs earned eligibility) + the **quiet denominator** (`route_watch_surface_examined` — log every `--work`); claude's **pre-declared population** completion (the denominator must not be agent-curated), sharpened by codex's **[P1] mechanically enumerable** (*surface membership is syntactic before it is sensory*) + the `surface_expected` / `scope_gap` row shapes; cursor retracted her schedulable-tonight tripwire (`same_pass` and `later_turn` are not earned-eligible). Promoted to **§11 Arming protocol v0** (Layer 1 only; no outcome verdicts; `occlusion_watch` module still designed) — room-endorsed (codex + cursor, no block); landed on dan's land word.
- **consider materialize** where applicable when testing. `../materialize/README.md`
