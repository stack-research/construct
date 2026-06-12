# Research Thread Summary

- Thread: `construct/research`
- Topic: research lab for LLM memory functions
- Dates: 2026-06-11 to 2026-06-12
- Status: ended

This thread took the construct project from initial framing into a working, reviewed Stage B harness. It started with the previous memory lab's unresolved debt - governed memory had never been tested against naive persistence - and ended with a branch-and-offer harness, machine-computed cell verdicts, cross-substrate audit results, two built boundary mechanisms, and a set of carry-forward requirements for Stage C.

## Participants

- `dan`: moderator and project owner.
- `claude`: primary drafter and implementer during this thread.
- `codex`: reviewer focused on causal attribution, governance boundaries, cell classification, and mechanism wording.
- `kagi`: reviewer focused on external/world-check oracles, temporal provenance, and audit discipline.
- `cursor`: implementer-reviewer focused on harness shape, scored verdict machinery, and concrete code gates.

## Starting Point

The room began by reading the construct README and then deeper materials under `notes/previous/`. The group converged on several lessons from the previous lab:

- The earlier lab built governance machinery but did not run a clean governed-vs-naive control harness.
- The first artifact should be an influence ledger: offered records, withheld records, reasons, branch condition, behavioral diff, oracle score, and authority update.
- Governance must be allowed to lose. The rubric needs cells where naive persistence is expected to beat governed memory.
- Usage labels produced by the model are not enough; record usage needs cross-substrate audit.
- Un-authored oracles belong in a later stage. Stage B could start with authored episodes as long as their limits were explicit.

## Harness Shape

The thread settled on a branch-and-offer harness:

- `L0`: no-memory baseline.
- `L1`: naive append-only memory using retrieval by similarity/recency.
- `L2`: governed memory, where records pass through an offer boundary.
- `L3`: governed memory plus post-answer usage elicitation for audit.
- Later v1.x lanes:
  - `L2y`: governed memory with live-input yield enabled.
  - `L2s`: governed memory with supersession policy enabled.

The main discipline: governance has to act before the answer, at the offer boundary or earlier. Post-answer labels are audit instruments, not treatments.

## Core Artifacts

Important files produced or evolved through this thread:

- `notes/PLAN_V1_BRANCH_AND_OFFER.md`
- `notes/RUBRIC_V1.md`
- `notes/SPEC_V1X_BOUNDARY_MECHANISMS.md`
- `episodes/smoke-001.json`
- `episodes/poison-001.json`
- `episodes/conflict-001.json`
- `episodes/conflict-002.json`
- `episodes/lb-001.json`
- `episodes/lc-001.json`
- `episodes/lc-002.json`
- `episodes/ld-001.json`
- `episodes/conflict-003.json`
- `episodes/le-001.json`
- `runs/*.stage_b.jsonl`
- `harness/score_cells.py`

## Major Review Corrections

### Authority Credit

Early wire runs credited authority to every offered record on a successful branch. Codex flagged that as presence riding as consequence: passenger records would gain future authority merely by being co-offered with useful records.

The fix was single-record ablation attribution. Authority movement now depends on whether removing a record changes the outcome. This remains disclosed as single-sample and influential-not-correct.

### W1 Reclassification

`conflict-001` originally looked like a governance-win cell, but all memory lanes received the same offer set and produced the same answer. L3's usage labels were elicited after the answer, so they had no causal opportunity to change behavior.

The room reclassified W1 as `A1`, an audit cell rather than a governance-win cell. This became a standing principle: if a mechanism did not act before the answer, it is annotation, not governance.

### Oracle Ride-Along

Kagi flagged that an oracle scores the answer, not the reason the answer was produced. A lane can be right for the wrong reason. Cells that claim causal mechanism wins therefore need attribution rows, not oracle scores alone.

This reinforced the ablation machinery and shaped the `cell_verdict` evidence requirements.

### Computed Cell Verdicts

Cursor required a post-run scorer before any result could be called "scored." `harness/score_cells.py` was added to append machine-computed `cell_verdict` rows. Human readers may interpret the result, but the pass/fail/not_engaged row must come from ledger evidence.

### Comparator Amendments

The first L-A scoring exposed that single-sample `latency_ms` measured API or network variance more than governance cost. The comparator was amended:

- Deterministic costs first for ordinary oracle ties: tokens, then governance steps.
- Latency remains context unless a cell is explicitly about reaction time.
- L-B uses repeated/paired latency evidence and can report `unstable`.
- `ablation_calls` are experiment cost, not a cost paid by the branch to answer.

The original failure was preserved and annotated rather than erased.

## Standing Principles Ratified

1. Governance must act before the answer or it is annotation.
2. Every mechanism ships with its own loses-cell.
3. Usage audit and oracle scoring may need different output surfaces.

By the end of the thread a fourth practical rule was also adopted for the next stage: renderer changes must be versioned/ledgered, because the renderer is now known to be part of the substrate under test.

## Scored Cells and Findings

### W2: Poisoned Record Resistance

`poison-001` tested a well-dressed, low-trust poison record. The poison looked authoritative in text, while its low trust was out-of-band metadata available only to the boundary.

Result: pass across the tested engines. Naive memory took the poison; governed lanes withheld it with `eligibility_below_threshold` and answered correctly.

Honest scope: this is evidence that governed offer-boundary metadata beats naive recency/similarity on an authored, well-dressed low-trust supersession poison. Future W2 variants should vary the costume.

### L-A: Policy Cost Exceeds Error Cost

`smoke-001` tested whether governance spends cost for no accuracy gain on a plain fact.

The first version failed informatively because latency-first scoring measured transport noise. After the comparator amendment, L-A became a clean governance-should-lose cell under deterministic costs, with the earlier failure kept in the record.

### A1: Category Drift Audit

`conflict-001` tested a plan plus correction offered together. The engine answered correctly, and auditors scored the correction as evidence and the old plan as a passenger plan.

Finding: the engine's post-answer `narrative_repair` self-label was not observable on the hostname-only surface. This supported R5: self-classification is not usage.

### L-B: Reaction Time Dominates

`lb-001` tested latency-sensitive conditions. Results did not stably support the premise; latency findings flipped or tied under repeated runs.

Final handling: L-B records `unstable` when timing evidence does not stably engage. The room treated this as useful information about the harness and the current cheapness of offer-boundary governance.

### L-C: Foreground Data Outranks Stale Memory

`lc-001` placed live current data in the question while records contained stale state.

Finding: engines split. Claude privileged the foreground data unaided, while gpt-oss allowed memory lanes to drag the answer stale. This showed that staleness is not poisoning: trust and relevance are backward-looking and cannot see that the world moved.

This motivated a v1.x live-input yield mechanism.

### A1-v2: Justification Surface

`conflict-002` repeated the A1 setup but required a one-sentence explanation.

Consensus audit: `r-corr` was evidence and `r-plan` was narrative repair. The phrase "supersedes the original plan" made the old plan's repair function observable.

Finding: R5 is surface-dependent. The hostname-only A1 surface made legitimate usage invisible; A1-v2 showed that a justification surface can reveal it.

### W1': Supersession Category-Drift Prevention

`conflict-003` rebuilt the old W1 idea as a real governance cell. The supersession policy withheld a superseded plan, freed offer budget, and let the correction reach the engine.

Result: pass across three engines. The room framed the mechanism as solving retrieval blindness: W2 keeps bad records out; W1' makes room for good records that naive retrieval would otherwise exclude.

Important caveat: W1' uses answer-divergence attribution because the correct record is absent from naive by construction. The claim should be phrased as "policy caused the winning offer geometry and the answer changed in the expected direction," not as oracle-flip causal proof.

### W3: Live-Input Staleness Resistance

`lc-002` moved the live datum from prose into structured `foreground_data` with temporal provenance.

Result: `not_engaged` across three engines. The yield gate fired and detector validation was clean, but every tested engine obeyed the rendered live observation unaided.

Finding: rendering provenance is itself a defense. The input surface changed engine behavior before the yield mechanism was needed.

### L-D: Yield Overreach

`ld-001` tested the cost of live-input yield. The yield proxy withheld an older same-topic record that complemented, rather than contradicted, the foreground datum.

Result: pass across three engines. The mechanism paid its price: the yield-on lane lost by burying needed complementary detail.

### L-E: Supersession Overreach

`le-001` tested the cost of supersession. The question asked for historical content whose answer was the superseded record.

Result: pass across three engines. The policy-on lane buried the answer-bearing record and lost. This confirmed the standing rule that mechanisms need measurable prices, not only wins.

## v1.x Mechanisms

Two boundary mechanisms were specified, reviewed, amended, built, and scored.

### Live-Input Yield

Structured `foreground_data` carries `observed_at` and `channel`. The boundary withholds older records that are sufficiently similar to fresher foreground data, using reason `yields_to_live_input:<datum_id>`.

The room accepted similarity-as-contention as a disclosed proxy only because L-D prices its overreach. `authored_contention` is validation-only and must not be read by the offer path.

### Supersession-Aware Offer Policy

Records can carry out-of-band `supersedes` metadata. The policy withholds a superseded record only when its superseder survives all pre-budget gates.

The gate-order blocker was fixed. Final order:

```text
eligibility -> live-input yield -> supersession among survivors -> top_k
```

This prevents a yielded or quarantined superseder from burying another record. There is no authority inheritance through supersession.

## Three-Surface Finding

The closing synthesis adopted a three-surface map:

- Renderer / input surface: `lc-001` vs `lc-002` showed that rendering provenance can suppress stale drag before filtering engages.
- Offer boundary: W2 and W1' showed that pre-answer boundary policies can change which evidence reaches the engine.
- Audit surface: A1 vs A1-v2 showed that answer shape can hide or reveal record usage.

The room treated the renderer as part of the substrate, not a confound to eliminate. Cursor added the implementation consequence: before Stage C, foreground renderer version or template hash should be recorded in every `run_config`.

## Final Scoreboard

By closure, the thread had produced:

- W2 pass across three engines.
- L-A pass under v1.3 comparator, with v1.2 failure preserved.
- A1 audit complete.
- A1-v2 audit complete with 3/3 `narrative_repair` consensus.
- L-B unstable / not stably engaged.
- L-C engine split.
- W1' pass across three engines.
- W3 `not_engaged` across three engines.
- L-D pass across three engines.
- L-E pass across three engines.

The final room synthesis described this as ten cells scored across three engines, with every claim grounded in ledger rows.

## Carried Forward

Stage C and the next research thread inherit these tasks:

1. Build un-authored oracle cases from real traces, including retraction sets, DNS/typosquat analogues, and Dan's captured traces.
2. Version and ledger the renderer as a substrate organ.
3. Report per-engine engagement matrices rather than collapsing `not_engaged` into a single headline.
4. Add W2 costume variants so poison resistance is not overfit to one change-control-ticket shape.
5. Either stabilize L-B with better timing design or retire it honestly for this architecture.
6. Decide whether the audit surface needs its own loses-cell.
7. Develop provenance-rich supersession links with source/channel, observed_at, issuer, and confidence.
8. Revisit audit vocabulary for superseded passenger records.

## Thread-Level Takeaway

The previous lab asked for a control-group harness, one uncertainty axis wired to a remedy, and falsification before theory. This thread delivered the harness, wired trust/authority/supersession/yield to measured remedies, and made falsification a standing design rule. The strongest result may be the review pattern itself: every mechanism that survived was changed by bounded cross-agent review before it became code.
