# Body Core v0.3 — explicit projection boundary

Status: **implementation built 2026-07-22; post-build cold review pending**.

Milestone: **none scientific**. This is provisional whole-body engineering
while active frontier search remains paused. It creates no memory, security,
composition, or reconstruction-cost finding.

The design target was reviewed in substrate thread
`explicit-projection-boundary`. Two independent reviewers endorsed the seam;
the convergence entry incorporated their acceptance pins before implementation.
The exact post-build code, test, and living-document surface is frozen in
[`body_core_v03_implementation_manifest.json`](body_core_v03_implementation_manifest.json)
for the pending review.

## Claim boundary

> The lineage kernel can validate durable event structure without silently
> selecting the lifecycle/placement/warrant ontology. An explicitly selected
> projector can reproduce the exact historical v0.2 canonical view and every
> closed X2, M2, and M3 scorer result.

The kernel is **cognitive-policy-neutral at this seam**, not ontology-free. It
still interprets the declared writer-role/authority table and two scope-anchor
kinds, `invocation_started` and `encounter_observed`. Those are provisional
structural vocabulary.

## Implemented split

[`core.py`](../sketches/next_substrate/core.py) retains:

- schema and evidence-class checks;
- contiguous event ids and indexes;
- previous-hash and event-hash verification;
- declared writer-role/authority compatibility;
- causal-parent and warrant backward references;
- invocation and encounter scope anchors;
- inline, reference, and redacted retention shapes;
- blank-row refusal;
- the generic `Projector` boundary and projector-explicit replay.

[`policy.py`](../sketches/next_substrate/policy.py) owns the exact historical
v0.2 fold:

- lifecycle and transition rules;
- binary hot/cold placement;
- warrant health, dependents, and invalid-warrant suspension;
- reported metabolic totals;
- canonical `BodyViews` and view digests;
- materialized-view-claim verification.

The literal projector id remains:

```text
body-core-v0.2-provisional-policy
```

No ledger schema or historical row changed.

## Fail-closed selection

A `LineageStore` may remain kernel-only for raw-row reading, structural
validation, or envelope-only append. It cannot return cognitive views or append
a semantic materialized-view claim without either:

- an explicitly bound projector at store construction; or
- an explicitly supplied projector on that operation.

The walking skeleton and all three adapters bind or supply the v0.2 projector
explicitly. Their existing append paths therefore retain policy validation
before write. The established impossible-transition and unhealthy-warrant
admission tests pass with their test bodies unchanged.

## Cursor ownership

Every kernel-validated row still advances `event_count` and
`through_event_id`, including a kind the projector does not interpret. Those
cursor fields remain part of the canonical policy view and therefore its digest.

An unowned row is inert only with respect to policy state:

- `state_items`;
- `warrant_health`;
- `dependents_by_warrant`;
- `reported_metabolic_totals`.

The new regression test asserts that an unowned row changes the canonical view
only through the two cursor fields.

## Preserved non-rule

The refactor deliberately adds no generic event-kind-to-writer-authority rule.
The v0.2 projector continues to ignore writer identity when folding a policy
kind. Runtime and adapter routing rules remain client policy. Tightening that
boundary would be a separate behavior change, not refactor hygiene.

## Verification oracle

Run:

```bash
make body-core-test
make body-core-x2-test
make body-core-m2-test
make body-core-m3-test
make body-sketch-test
```

The build currently passes:

```text
26 Body Core/projector tests
9 X2 adapter tests over four closed ledgers
11 M2 adapter tests over ten closed S1/S2 pairs
14 M3 adapter tests over eleven indexed ledgers
6 walking-skeleton tests
```

The four new Core tests establish:

1. bare cognitive replay and view claims require explicit selection;
2. kernel validation alone cannot certify a stale policy view claim;
3. an unowned kind changes only the canonical cursor;
4. the split introduces no generic kind-to-authority policy.

The prior 22 Core tests remain green. X2 verdicts and costs, M2 fresh resident
evidence, M3 fresh red-team evidence, walking-skeleton output, canonical profile
id, view shape, and established refusals remain unchanged.

The complete pre-split and post-split walking-skeleton summaries were also run
from separate checkouts at `10cdcd7` and the working tree. Apart from temporary
lineage paths, they match exactly; both produce 38 rows and final view digest:

```text
c2041076508d84b730d1bd8a486f6d0a8988448824921b25fd9d526ed6a23de3
```

The walking-skeleton regression now pins that historical digest literally.

## Loses-condition and non-goals

The slice loses to v0.2 if review finds changed canonical output, softened
refusals, silent projector selection, adapter callbacks in the kernel, or
abstraction machinery without an existing consumer.

This build adds no fourth adapter, global ownership registry, schema expansion,
kind-authority rule, engine contact, scientific rerun, checkpoint, compaction,
migration, concurrency, signature, external chain-head anchor, or replay
optimization. Full replay remains authoritative and append/replay remains
quadratic.
