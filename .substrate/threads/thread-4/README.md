# thread-4: M2 — Resident Substrate

**Status:** Closed (moderator ruling, 2026-06-14)

**Topic:** M2 milestone — proving that a cold-re-instantiated resident reads its own harness-minted, world-checked earned failure across a session seam and decides better than its store-denied twin; the fork (not narration) decides use. Closes the carried `counted ≠ read` null from M1.5.

## Core Claim
A repo-native agent that earns a failure in one session will, in a later session, read that earned memory from a governed store and decide better than an identical instance denied the store. The fork, not the resident's testimony, decides whether the store was used.

## Walls (enforcement)
- **Wall A (fork control, R3):** Control is a branch (`branch_B = store minus the one earned record`). Single-variable isolation via `inherited_record_ids`. Scorer asserts symmetric difference of offer sets == `{earned}` only (else `offer_set_confound`).
- **Wall B (mint, R5):** Harness (not resident) mints the earned record from the scored trace (`minted_by: harness`, `mint_basis: world_correction | scored_failure`). Resident's answer is only a failed-artifact pointer.

## Four Cells
- **RS-1** (headline): Earned failure changes a later decision (diverge ∧ better ∧ ablation important). Closes CB-read.
- **RS-loses** (R5): Performed continuity refused — explicit claim of use that the fork shows is not important.
- **RS-stale** (R4): Continuity-as-authority — store overruled by fresher live input (`live_input_yield` gate, `oracle_basis: authored_reinstatement`).
- **RS-U1** (un-authored close-gate): Both ends of the chain world-checked (`source != authored` on E1 mint and E2 oracle); single-hop, single-retraction (`corpus_scope`).

## Review Passes (one bounded pass each, no blockers)
codex (Wall B / R5), cursor (Wall A / fork / RS-1 predicates), grok (cold-read / RS-loses vs RS-stale / M3 mask), kagi (oracle / RS-U1 / both-ends gate), gemma (Pi-harness / contributory_asset). All converged; tightenings folded (symmetric-diff check, claim precondition on RS-loses, `oracle.source != authored` on E2, `corpus_scope` disclosure, `resident_config_digest`, memory isolation attestation).

## Results (N=5 runs, gpt-oss-20b + claude)
- **RS-1:** pass — gpt-oss-20b 5/5, claude 4/5 (1 ablation-noise miss on important leg).
- **RS-U1:** pass — world-checked at both ends (non-transitive; kagi-verified in rows); couples to RS-1.
- **RS-loses:** disclosed null (engines self-reported non-use honestly on adjacent distractors; central claim was important → correct `fail`).
- **RS-stale:** disclosed null (engines overrode stale memory on clear reinstatement signal).
- All preconditions clean (chain_link, cold_identity, memory_isolation, earned_binding, offer_set_isolation).
- Oracle `_norm` markdown/newline glue bug found, fixed, regression-tested; prior rows stand (L-A).

## Close
M2 closed by moderator ruling on the all-cells-scored basis: wins pass at N=5; loses-cells are honest disclosed nulls (pathology not observed, H2/C-2 precedent). Carried to v0.2: sharper episodes for loses-cell engagement (ambiguous reinstatement; decisive-claim split), multi-sample ablation, compounding, multi-retraction.

The instrument lab became a subject lab. A resident now exists — forkable, audited, cold-re-instantiated, its store the sole channel. R5 spine complete end-to-end.

**Key artifacts:** `notes/SPEC_M2_RESIDENT_SUBSTRATE.md` (v0.1), `notes/M2_FINDINGS.md`, `harness/score_resident.py`, `runs/m2/`, `tests/test_resident.py`, `tests/test_oracle.py`.