# Body Core v0.2 — X2 adapter contract

Status: **v0.1 endorsed; v0.2 correspondence repair cold-reviewed and
endorsed**. Wire/integration engineering only. See the v0.1
[review](BODY_CORE_X2_REVIEW.md) and the v0.2
[cross-client review](BODY_CORE_M2_REVIEW.md). This adapter does not create a
new X2 run, alter the closed X2 finding, or license a scientific mechanism.

Implementation note (2026-07-21): the source-binding logic was factored through
a shared Core-adjacent [helper](BODY_CORE_SOURCE_BINDING.md) and independently
[endorsed](BODY_CORE_SOURCE_BINDING_REVIEW.md). The prior review hashes remain
historical attestations; the helper review separately pins the refactored bytes.

## Milestone gate

Scientific milestone: **none**. This is the first non-stub pressure test of the
provisional whole-body Core while frontier search is paused.

Oracle: the unchanged [`harness.score_prune`](../harness/score_prune.py) scorer
run on both the checked-in X2 ledger and its Body-Core round-trip projection.

Loses-condition: the build is refused if any earned verdict or cost total
changes under the pinned canonical comparison, or if a mutation, stale view,
invalid warrant, or independently detectable cost mismatch reaches the scorer
as clean lineage.

Exact success statement:

> Body Core v0.2 carries X2 closed lineage so the unchanged scorer reproduces
> every earned verdict and cost total under pinned canonical equality, while
> four refusals bite.

The equality exception is declared before execution:

```text
non-semantic fields = {"ts"}
```

The adapter currently preserves `ts` too. The exception exists so canonical
comparison is explicit rather than accidentally stronger than the contract.

## Two layers

The Core integrity kernel supplies contiguous ordering, hash linkage,
writer-role/authority checks, backward references, scope checks, retention
shape validation, and replay-over-cache authority.

Its provisional policy profile supplies the lifecycle table, binary hot/cold
placement, three-value warrant health, invalid-warrant suspension, and the rule
that disputed or invalid warrants cannot activate state. X2 exercises the
binary placement and warrant rules. Those rules are not presented as neutral
ontology.

## Reversible field provenance

Every X2 row becomes one `x2_source_row_carried` event. Its fields are flattened
directly into the event payload beside three adapter coordinates:
`source_row_index`, `source_kind`, and `source_row_digest`. The reserved escrow
keys `original_x2_row`, `raw_row`, and `row_blob` are rejected. The code pins a
finite per-kind field allowlist covering the closed X2 schema; an unknown kind
or field requires an adapter revision rather than generic transport.

| Scorer input | Body Core source |
| --- | --- |
| Row order | `payload.source_row_index`; must be contiguous and unique |
| Row kind | `payload.source_kind` |
| All remaining X2 fields, including `ts` | Same-name, top-level payload fields |
| Whole source row integrity | `payload.source_row_digest` plus Core event hash |
| `x2_run_meta.branches`, record ids/texts, metric, block labels | Same-name fields on the carried `x2_run_meta` event |
| `run_config.engine_backend`, branch configs | Same-name fields on carried `run_config` events |
| `hot_store_cost` run/sequence/branch and reported cost fields | Same-name fields on carried `hot_store_cost` events |
| `branch_run` run/branch/oracle fields | Same-name fields on carried `branch_run` events |
| `prune` / `rematerialize` operation fields | Same-name fields on carried operation events |
| Computed fixture gate | Same-name fields on carried `fixture_gate_result` |
| Fixture claim | Same-name fields on carried `fixture_attestation` |

Projection reconstructs the X2 rows field-for-field and then calls the existing
scorer. The adapter does not reproduce scorer logic.

Each carried prune or rematerialize row also requires exactly one separate
`placement_changed` policy receipt. That receipt binds the source event, source
index, operation kind, state item, and hot/cold transition. A non-operation may
not have such a receipt. v0.2 additionally refuses any placement change for an
X2 materialized record without a source binding and requires terminal Core
placement to equal the fold of all bound X2 operations.

`reported_metabolic_totals` remains writer-reported accounting derived from
lineage events. It is not an independently recomputed cost. X2's scorer-side
cost replay remains the authority for the cost claim.

## Refusal legs

Named wire tests require:

1. a carried-row mutation without rehash breaks the Core chain;
2. a rehashed stale materialized view loses to full replay;
3. invalidating a record warrant suspends its state and blocks X2 projection;
4. changing a reported X2 cost survives transport but the unchanged scorer
   returns `cost_replay_mismatch` on its cost-attribution cells.

An additional binding probe rewrites and rehashes the final carried source row;
the aggregate source digest pinned in `x2_adapter_started` must still refuse it.
Two v0.2 probes reproduce and close the prior review residual: an unbound
placement transition is refused, and a chain-consistent terminal placement
rewrite loses to the independent operation fold.

The Core suite also names the earlier adversarial probe families as tests:
duplicate parents/warrants, invalid retention shapes, disputed-warrant
reactivation, mid-chain rehash, unknown scopes, and blank JSONL rows.

## Performance admission

`LineageStore.append` validates all prior rows before every append. The adapter
reports `append_prefix_rows = n(n-1)/2`: the exact number of prior rows presented
to that first validation pass across the build. It is a deterministic
engineering work proxy, not latency and not the full operation count.

| Closed ledger | X2 rows | Core rows | append prefix rows |
| --- | ---: | ---: | ---: |
| Helix / local | 102 | 131 | 8,515 |
| Helix / Claude | 102 | 131 | 8,515 |
| DEP0033 / local | 92 | 117 | 6,786 |
| DEP0033 / Claude | 92 | 117 | 6,786 |

The quadratic append/replay path is admitted debt. This build makes no
reconstruction-cost or optimization claim.

## Review budget

The builders initially proposed contract review before implementation. The
human moderator instead ruled **build, then review with Fable**. The remaining
budget is therefore one cold build review, one bounded repair if blocked, and
one fresh final review. The review may endorse or block; it does not rewrite the
adapter by committee.

## Run

```bash
make body-core-test
make body-core-x2-test
```

Both are wire checks. The real ledgers are read-only prior evidence; the tests
write projections only to temporary directories.
