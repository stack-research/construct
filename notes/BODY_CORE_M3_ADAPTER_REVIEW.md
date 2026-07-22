# Body Core M3 adapter review

Status: **ENDORSED 2026-07-21; proposal and post-build passes complete**.

The bounded review ran in substrate thread `body-core-m3-adapter-review` in two
stages. First, `cursor/grok-4.5` and `claude/fable-5` independently endorsed the
proposal and its exact eleven-ledger source corpus. After implementation, both
reviewers independently reproduced the frozen code-analysis surface and
returned **ENDORSE** again. No blocker or repair was issued.

## Exact reviewed surfaces

Proposal review manifest:

```text
notes/body_core_m3_adapter_proposal_review_manifest.json
ba2fad62d3be090f48bbe1dec018fee976683ce0ee129749cd91196eb31679a4
```

Implementation review manifest:

```text
notes/body_core_m3_adapter_implementation_manifest.json
8598e54b9826fd3ff847d37debe0758d2f4c84f559350b119e73a6aa41ae39d5
```

The implementation pass reproduced all seventeen manifest file hashes, nine
source component pins, four episode pins, and eleven ledger pins. It also
reproduced:

- 22 Body Core tests;
- 9 X2 adapter tests over four closed ledgers;
- 11 M2 adapter tests over ten closed pairs;
- 14 M3 adapter tests over eleven indexed ledgers;
- 6 walking-skeleton tests;
- 8 M3 component red-team tests;
- scoped Ruff and `git diff --check`.

The eleven M3 lineages contain 172 Core rows and expose 1,397 append-prefix
rows, exactly matching the proposal's deterministic work disclosure.

## Reviewed conclusion

The adapter preserves M3 without promoting source assertions into Core
authority:

- Track-A writer, authority, status, placement, warrant, and item-detail fields
  are adapter-fixed or derived from the pinned episode, never from source trust
  or attacker fields;
- every offer/withhold receipt for a claimed M3 item has a valid source binding
  and exact client semantics;
- lifecycle, placement, and metabolic events affecting claimed M3 items refuse
  even when correctly source-bound;
- Track B creates no Core state or receipt from `minted`, `poison_offered`, or
  `asserted_trust`;
- projection is field-exact for the M3 ledger and fresh scoring invokes the
  unchanged digest-pinned CLI after stripping historical verdict rows;
- the adapter does not consume the source index's derived summary rollup.

This endorses only reversible wire/integration preservation. It does not show
that Body Core creates or protects earned trust, close the live-channel or
ingestion breaches, authenticate writer principals, establish causal
composition, reduce replay cost, or create new M3 evidence.

## Carried review debts

Four observations remain explicit and non-blocking:

1. The frozen source index's `matrix.close_summary.AG-U1` omits the defended
   draw's `not_engaged: 1`. Per-ledger entries and fresh scorer output are
   authoritative; the adapter never consumes this derived rollup.
2. A rehashed `m3_source_row_carried` event can be reparented to another valid
   earlier event while field-exact projection still succeeds. Transport-chain
   topology is not part of the current preservation claim. A future consumer
   of that topology must name and test the additional rule.
3. Historical verdict stripping is implemented correctly, but its present test
   would not detect removal of the strip on already-scored Track-B ledgers. A
   future revision should refuse the scorer's `already scored` path or attest
   that fresh verdict rows were appended.
4. Several multi-mutation tests assert a broad M3 refusal message. They prove
   refusal, but future maintenance should pin each mutation to its intended
   refusal path.

No observation triggered the bounded repair budget. The exact reviewed
implementation remains unchanged.

## Historical-manifest boundary

The implementation manifest freezes the bytes the reviewers saw. This review
record and the later status promotions in living documents are append-only
documentation after that review, so those promoted documentation bytes are not
expected to match the historical manifest. The reviewed adapter, tests, Core,
helper, scorer, proposal, and source-index bytes remain unchanged.
