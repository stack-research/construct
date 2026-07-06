# Chapter 13 — The pause/resume frontier: the instrument that keeps refusing

Previous: [The warming budget](12_WARMING_BUDGET.md) · [Walkthrough index](README.md)

Chapter 12 armed a watch against the world's calendar. This chapter is what the lab
built while waiting: a second live instrument, designed in a room, sealed in parts,
and — three fixture families in — still refusing to answer its own central question.
The refusals are the story. Each one is a measurement of the instrument's own
limits, written down before anyone could be tempted to soften them.

**Status: in flight at time of writing; Part IV was subsequently sealed
(2026-07-05), built, and closed — that arc is [Chapter 14](14_GREENREACH_CLOSE.md).** When it disagrees with the spec, the spec wins —
this chapter narrates; [SPEC_PAUSE_RESUME.md](../SPEC_PAUSE_RESUME.md) governs.

## The question

> When work is interrupted and resumed, does a compact **frontier artifact** —
> minted at pause time from structural evidence only, carrying obligations but
> never answers — ever let the resumed session reach the same-quality decision
> **cheaper** than re-reading from cold?

In the lab's vocabulary: does the artifact ever *pay*? The claim under test is
**governed-hint efficiency** — never continuity, never metabolism, never "the
model remembers." Everything the artifact whispers must be something the rules
could derive; anything more is a leak the gates exist to catch.

Note the inheritance from earlier chapters: M1 asked whether an *heir* beats a
rereader with the answers in hand; X2 asked whether pruning hot state preserves
quality. PRF asks the harder marginal question — whether a *bundle of pointers*
minted at a seam is worth its own carry cost, measured in tokens, against an
honest cold competitor on a symmetric surface.

## Read

- [SPEC_PAUSE_RESUME.md](../SPEC_PAUSE_RESUME.md) — four parts, one instrument:
  Part I (§0–§12) the mint/derivation machinery and its 13-check discriminator;
  Part II (§13–§24) the behavioral regime (SBR + ECAC); Part III (§25–§35) the
  triangulation-docket family, the first pay-window experiment; Part IV (§36–§46,
  draft) the Greenreach family, the first *detectable* pay-window experiment.
- The `pause-resume-frontier` thread
  (`.substrate/threads/pause-resume-frontier/`) — the entire discourse: design
  rounds, pin rounds, seals, execution reports, board reviews, dan's rulings.
  This is the longest single thread in the lab and the best available record of
  the room operating as an instrument.
- Harness: [run_sbr.py](../../harness/run_sbr.py),
  [score_prf.py](../../harness/score_prf.py),
  [mint_frontier_state.py](../../harness/mint_frontier_state.py),
  [derive_live_obligations.py](../../harness/derive_live_obligations.py),
  [check_prf_fixture.py](../../harness/check_prf_fixture.py).
- Fixtures: `episodes/prf/sbr-meridian/` (v0.2 family, frozen),
  `episodes/prf/triangulation-docket/` (v0.3 family, executed 2026-07-04).
- Ledgers: `runs/prf/` — every engine contact, including the superseded and the
  confounded, append-only.

## Vocabulary bridge

**SBR (Symmetric Bounded Retrieval)** is the arena: a catalog of numbered
surfaces behind a closed action grammar (`R01`…`R21` or `STOP`), identical on
both branches, with a hard read budget. The **cold-reread** branch gets the
catalog and nothing else. The **resumable-state** branch gets the same catalog
plus the rendered artifact — and *pays for it*: the artifact's rendered tokens
(`a_i`) are charged to every resume.

**ECAC (expected cost to adequate continuation)** is the score: read tokens plus
artifact carry, counted only when the answer passes the oracle at the pinned
quality bar. Failure prices at `c_max` — there is no partial credit.

A **loses-cell** is an authored outcome where the artifact *should* lose
(`PRF2-heir-dominates`: cold reads the same legs and stops). A **self-falsifier**
is a fixture variant where any artifact win refutes the instrument itself
(`PRF2-ballast-null`: the bundle points at wrong surfaces; `PRF2-neutral-null`:
the bundle carries no prunable frontier). Band = 0: any strict win fires.

The **pay-window** is the region where an engine is strong enough to use the
artifact but weak enough to need it. Whether it exists, for any engine on any
family, is the falsifiable target.

## The arc, briefly

1. **v0.1 (meridian, sealed + built 2026-07-03).** The machinery: two-phase mint,
   rulebooked derivation, ceiling+floor oracle. First real engine walk landed all
   five designed cells — including a genuine false-continuation on the
   changed-world episode.
2. **v0.2 (SBR + ECAC, same day).** The behavioral regime. First finding:
   `gpt-oss-20b` is **zero-dispersion** on the meridian surface at every legal
   temperature — every cold run takes the same route, so no sampling claim is
   licensed at all. The family was declared, not rescued.
3. **Cross-engine (2026-07-03).** Small engines disperse — and fail *with* the
   foreground present while passing cold. The artifact acted as cognitive load,
   not warmth. Standing observation: resumable **never won** in ~24 real runs
   across 3 engines. The pay-window had never been observed.
4. **v0.3 (triangulation-docket, designed/sealed/built/run 2026-07-04).** A
   fresh world where the answer is a three-leg conjunction, built to make "no
   pay-window" falsifiable. Result: the docket *restored dispersion* for the
   capable engine (R1 answered) — and the same dispersion blew the precommitted
   CI budget (`n_required 171 > n_max 24` → `ci_target_unmet`, confounded,
   symmetric). The pay-window question survived its own experiment. Same run:
   the first `PRF2-neutral-null` firing in lab history (the artifact did
   unmeasured reasoning work on an engine that failed cold — the instrument
   self-refuted exactly where designed), and both small engines failed
   calibration *at answer time* with the route force-fed — sharpening the
   cognitive-load observation.
5. **v0.4 (Greenreach, drafted 2026-07-04 night).** The design round produced
   the arc's sharpest piece of arithmetic (glm): under docket-form geometry,
   **the band where 24 draws suffice and the band where the pay-window is open
   do not intersect** — a docket-shaped third family was precommitted to
   confound-or-heir-dominates before it ran. The repair: cheap enumeration
   decoys convert cold's distracted route from a `c_max` failure into an
   expensive *pass*, collapsing the variance and making the artifact's value
   (~145 tokens of targeted reading) detectable inside 24 draws. The cost of
   the repair is named in §36 as a family-level re-pin of what "pay" means —
   with the licensing boundary stated: a Greenreach negative licenses "no
   pay-window in the detectable regime," never "no pay-window anywhere."

## What the pin round caught (and why it belongs in this chapter)

The v0.4 pin round is the lab's best small specimen of adversarial arithmetic
doing real work. One reviewer found the proposed cold route needed nine reads
against an eight-step budget. Three reviewers converged on `max_steps=9`. A
fourth traced the harness loop and showed nine was still one short — the STOP
action consumes a loop slot. When the moderator verified *who was right*, the
answer was **both, about different layers**: the spec (§29) prices forced stops
at `c_max`, but the mechanism never enforced it — a forced-stopped session
could still answer and pass. The divergence had already fired, silently, in six
committed docket ledgers.

No licensed result rested on it (every affected lane was already confounded,
and enforcement only strengthens the confounds), but the episode is the
chapter's thesis in miniature: **a disagreement between two correct reviewers
is a measurement of the thing they disagree about.** The enforcement is now a
Part IV build obligation with a seeded regression test, and — dan's addition —
a `boundary_forced_stop` diagnostic row so the boundary-condition rate is
telemetry, not archaeology.

## Inspect / replay

Wire tests (no engine, no evidence appended):

```bash
make prf-test    # Part I machinery
make prf2-test   # Part II SBR/ECAC
make prf3-test   # Part III docket family
make prf3-gate   # docket family admission gate (should be GATE OPEN)
```

Replay the F1 divergence from the preserved ledgers (read-only; this reproduces
the moderator's pin-round check):

```bash
python3 - <<'EOF'
import json, glob
for f in sorted(glob.glob('runs/prf/docket-*.jsonl')):
    forced, outcomes = set(), {}
    for line in open(f):
        r = json.loads(line)
        if r.get('kind') == 'forced_stop': forced.add(r.get('session_id'))
        if r.get('kind') == 'session_outcome': outcomes[r.get('session_id')] = r.get('quality_ok')
    hits = [s for s in forced if outcomes.get(s)]
    if hits: print(f, len(hits), 'forced-stop sessions with quality_ok=true')
EOF
```

Interpretation guide: those rows are sessions the sealed spec says should have
priced at `c_max` but did not. They are *disclosed*, not repaired — the docket
family stays sealed as run, because repricing can only raise variance and every
affected lane was already confounded. That "a fortiori" reasoning is the
standard the lab holds for leaving a known defect in place.

## Result, nulls, limits

- **Preserved result:** the pay-window has never been observed — across three
  engines, two families, ~40 real sessions. Every branch of the negative is
  typed: zero-dispersion (meridian), heir-dominates and cost-loss (both
  families), `ci_target_unmet` (docket), calibration refusal (small engines).
- **Disclosed nulls:** one `PRF2-neutral-null` (point-mode, board-reviewed,
  standing as an instrument alarm under dan's single-run ruling — never a
  behavior claim).
- **Debts, carried:** §23 causal-reduction rides every future win cell; the
  rendered-carry undercount (B) remains a warmth-tax question; the §29
  enforcement and D13 telemetry are owed by the v0.4 build.
- **Limit that matters most:** every negative so far is *per family, per
  budget*. The instrument refuses to convert "not observed here" into "does not
  exist." Greenreach is the first family where a positive is arithmetically
  reachable inside the budget discipline — which makes it the first family
  whose negative would carry real weight.

## Handoff

If Greenreach opens the window, the lab has its first measured case of a
frontier artifact paying for its own carry — and §23's causal-reduction debt
immediately comes due. If it closes, that is three families of typed negatives
under one budget discipline, and the honest question shifts from "does the
artifact pay?" to "what would have to be true of an engine for it to pay?" —
which is a question about engines, not fixtures, and would mark the boundary of
what this instrument can see.

Next: [Greenreach: the close](14_GREENREACH_CLOSE.md)
