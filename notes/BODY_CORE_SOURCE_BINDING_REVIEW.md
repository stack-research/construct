# Body Core source-binding review

Status: **ENDORSED 2026-07-21; thread ended**.

The bounded review ran in substrate thread
`source-binding-v01-review` over exact manifest
[`body_core_source_binding_review_manifest.json`](body_core_source_binding_review_manifest.json),
SHA-256:

```text
adfcf87dd7999daf4e7eb202a5ff6775786c7d5e49c34f40357c3131a5abc941
```

Both independent reviewers, `claude/fable-5` and
`cursor/composer-2.5`, reproduced all fourteen file hashes and all six
verification commands. Each returned **ENDORSE** with no requested repair:

- 22 Body Core tests;
- 9 X2 adapter tests over four closed ledgers;
- 11 M2 adapter tests over ten closed pairs;
- 6 walking-skeleton tests;
- scoped Ruff;
- `git diff --check`.

## Reviewed conclusion

The factoring shares source-binding validation without granting policy
authority. Missing, wrong-kind, non-causal, and coordinate-disagreeing bindings
refuse. X2 retains its prune/rematerialize and placement-fold rules. M2 retains
its activation-only policy and refuses a correctly source-bound placement
receipt because provenance is not authorization.

The reviewers independently identified and endorsed one real narrowing from the
prior X2 bytes: X2 now validates receipts only for item ids it claims. A foreign
item is outside X2's jurisdiction rather than incidentally rejected by X2's old
global scan. The closing testimony records the standing boundary:

> An adapter governs only the materialized item ids it explicitly claims. An
> item claimed by no adapter is protected only by Core's generic state machine,
> by design.

This review does not establish global item ownership, adapter registration, or
cross-adapter overlap detection. Any future adapter must declare its claimed
item-id set and selected receipt kinds. A future need to detect ownership gaps
or overlaps requires its own consumer, rule, and refusal surface.

## Promotion boundary

The endorsed helper satisfies the prerequisite named by the M2 adapter review.
It licenses at most a later third-adapter proposal. It does not license adapter
implementation, engine contact, frontier reopening, a scientific finding, a
security claim, or a reconstruction-cost claim.

Historical X2 and M2 review hashes remain unchanged and continue to attest only
to the bytes those reviews saw. This status record promotes the separately
reviewed factoring append-only; it does not rewrite those attestations.

The review manifest is likewise a historical snapshot. After the thread ended,
the reviewed documentation files were updated from pending to endorsed and the
living orientation documents gained the M3 proposal pointer. Those promoted
documentation bytes are therefore not expected to match the frozen manifest;
all reviewed implementation and test pins remain unchanged and reproducible.
