# Body Core v0.2 — M2 adapter contract

Status: **cold-reviewed; endorsed after one bounded repair**. Wire/integration
engineering only. See the [review record](BODY_CORE_M2_REVIEW.md). This adapter
does not rerun M2, strengthen its closed finding, or license a scientific
mechanism.

Implementation note (2026-07-21): the activation-source checks were factored
through a shared Core-adjacent [helper](BODY_CORE_SOURCE_BINDING.md) and
independently [endorsed](BODY_CORE_SOURCE_BINDING_REVIEW.md). The prior review
hashes remain historical attestations; the helper review separately pins the
refactored bytes.

## Milestone gate

Scientific milestone: **none**. This is the second independent pressure test of
the provisional whole-body Core while frontier search remains paused.

Preservation oracle: exact aggregate and per-row digest equality after reverse
projection. Fresh invocations of the unchanged
[`harness.score_resident`](../harness/score_resident.py) CLI on temporary
unscored copies test scorer sovereignty and the verdict-stripping/path-rebinding
surgery; scorer equality is not independent evidence beyond byte equality on
the happy path.

Loses-condition: the build is refused if any fresh verdict row changes under
the pinned canonical comparison, if the carried state loses its world-scored
S1 warrant or S2 inheritance receipt, or if mutation, stale views, opaque
escrow, invalid warrants, extra lifecycle transitions, or fork-identity drift
reach the scorer as clean.

Exact success statement:

> Body Core v0.2 carries all ten closed M2 S1/S2 pairs under exact reverse-
> projection digest equality, while the unchanged scorer remains sovereign over
> M2 validity and the declared warrant, session, lifecycle, policy-event, and
> scorer refusal probes bite.

The predeclared non-semantic allowlist remains:

```text
non-semantic fields = {"ts"}
```

Transport preserves source timestamps exactly. Newly written scorer verdict
timestamps are excluded because the source and projection are scored
separately.

## Policy path under test

X2 exercised binary placement. M2 exercises the other side of the provisional
policy profile:

1. the S1 `branch_run` must be a world-scored failure;
2. the S2 `earned_record` becomes a probationary `m2_earned_record` state item
   warranted by that exact carried failure event;
3. the carried `m2_run_meta` must bind the S1/S2 sessions, name the earned
   record, include it only in the resident inheritance set, and activate the
   probationary state across the session seam;
4. projection requires current warrant health, one admission, one activation
   receipt, terminal `active` state, terminal `hot` placement, and no placement
   or metabolic events (the M2 adapter defines neither).

The Core does not recompute M2's scientific verdict. The unchanged scorer
remains sovereign over chain identity, fork identity, memory isolation, earned
binding, offer-set isolation, ablation importance, and world checking.

## Reversible field provenance

Every source row becomes one `m2_source_row_carried` event with a declared
`source_phase` (`s1` or `s2`), contiguous row index, row kind, row digest, and
same-name flattened source fields. A finite per-kind allowlist covers the
closed M2 schema. Unknown kinds and fields require an adapter revision.

The escrow keys `original_m2_row`, `original_s1_row`, `original_s2_row`,
`raw_row`, and `row_blob` are rejected.

| Scorer input | Body Core source |
| --- | --- |
| S1/S2 membership and row order | `source_phase` + `source_row_index` |
| Row kind and all source fields | `source_kind` + same-name payload fields |
| Per-row integrity | `source_row_digest` plus Core event hash |
| Whole-ledger integrity | S1/S2 aggregate digests pinned in `m2_adapter_started` |
| Session seam | Carried S1/S2 `session` fields plus carried `m2_run_meta` |
| World-failure warrant | Carried S1 `branch_run.oracle` and earned-record provenance |
| Earned record and inherited sets | Same-name carried `earned_record` and `m2_run_meta` fields |
| Fork, offers, ablations, outcomes | Same-name carried runner rows |
| Fresh verdicts | Written only by the unchanged scorer on temporary projections |

Historical `cell_verdict` rows are transported for exact ledger preservation
but are removed from both temporary copies before fresh scoring. They are not
trusted as the comparison oracle.

## Closed pairs

Ten checked-in pairs are exercised:

- local and Claude RS-1;
- five-sample-ablation and Claude-L3 RS-1;
- local, Claude, and v0.2 decisive-claim RS-loses;
- local, Claude, and ambiguous-reinstatement RS-stale.

Every pair contains four S1 rows and seventeen S2 rows. It becomes a 24-row
Core lineage: one adapter start, twenty-one source rows, one probationary
admission, and one activation. Deterministic append-prefix exposure is 276
rows per pair. This is a work proxy and admitted quadratic debt, not latency or
a reconstruction-cost claim.

## Refusal legs

Named tests require:

1. source mutation without rehash breaks Core lineage;
2. a rehashed stale materialized view loses to replay;
3. invalidating the S1 failure warrant blocks projection;
4. extra lifecycle transitions fail the exactly-one-activation rule;
5. a rehashed admission with a non-failure warrant is refused;
6. undeclared fields cannot become opaque escrow;
7. carried fork-identity drift reaches the unchanged scorer and fails
   `cold_identity`;
8. an undeclared placement event affecting the M2 item is refused;
9. an undeclared metabolic event affecting the M2 item is refused;
10. a valid source binding does not grant an otherwise unauthorized placement
    event policy authority.

## Review budget

One independent cold review may endorse or block the exact build. A block
licenses one bounded repair and one fresh final review, then close. No engine
contact, scientific rerun, replay optimization, or mechanism expansion belongs
in this review.

## Run

```bash
make body-core-m2-test
```

This is a wire-preservation check over prior evidence, never new evidence.
