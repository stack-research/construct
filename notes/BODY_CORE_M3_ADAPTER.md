# Body Core M3 adapter

Status: **v0.1 cold-endorsed 2026-07-21**. See the completed
[review record](BODY_CORE_M3_ADAPTER_REVIEW.md).

Claim boundary: **wire/integration preservation only**. This adapter does not
rerun M3, create red-team evidence, contact an engine, close the ingestion
border, authenticate Core writers, establish causal composition, or license a
scientific or reconstruction-cost claim.

The implementation follows the exact cold-endorsed
[proposal](BODY_CORE_M3_ADAPTER_PROPOSAL.md), reviewed under manifest SHA-256:

```text
ba2fad62d3be090f48bbe1dec018fee976683ce0ee129749cd91196eb31679a4
```

The frozen [source index](body_core_m3_adapter_source_index.json), SHA-256
`81b1a480d572a89e8a8dfab1baef84af8efb9eebdabebd13808d2451543a571d`,
names eleven ledgers, four pinned episode files, nine component pins, and 89
source rows. The implementation refuses a different source-index digest.

## Implemented boundary

[`m3_adapter.py`](../sketches/next_substrate/m3_adapter.py) creates one Core
lineage per source ledger. Every source field remains visible in a typed
`m3_source_row_carried` event with a contiguous row index, source kind, and
per-row digest. Unknown kinds, undeclared fields, and opaque escrow keys refuse.
The adapter-start event binds the source-index, ledger, episode, scorer, attack,
surface, and row-count pins.

For foreground-text and live-channel Track A:

- every record in the pinned episode becomes one active, hot
  `m3_materialized_record` item;
- an observer-authored `m3_episode_record_declared` event warrants each item;
- every source `offer` or `withholding` gets exactly one controller-authored
  `m3_boundary_decision_receipt`;
- the shared source-binding helper checks source kind, causal parenthood, row
  coordinates, and item jurisdiction;
- the M3 adapter separately checks receipt cardinality and exact
  run/branch/record/decision/reason semantics;
- lifecycle, placement, and metabolic events affecting a claimed M3 item refuse
  even when they carry a valid source binding.

All records remain active and hot regardless of offer/withhold. The decision is
therefore an adapter audit relation, not a generic Core state or placement
signal.

For ingestion Track B, source rows are carried exactly but no episode record,
state item, or boundary receipt is created. `minted: false` remains a refused
write. `poison_offered: true` and `asserted_trust` remain observer-carried
payload for the unchanged scorer; neither can choose a Core writer, authority,
or warrant.

## Projection and scorer authority

Projection first runs full Core replay, including stale-view refusal. It then
requires exact adapter writer ids, roles, and authorities; reconstructs the
source ledger by contiguous row index; checks per-row and aggregate pins; and
validates the Track-A or Track-B correspondence above. A different but
Core-legal writer identity still refuses.

Fresh scorer comparison writes source and projection to separate temporary
ledgers, strips all historical `cell_verdict` rows, and invokes the unchanged
`harness.score_redteam` CLI with the same pinned episode. Full verdict evidence
must match modulo only `ts`, and the fresh source verdict labels must equal the
per-ledger indexed matrix. The adapter does not reproduce organ projection,
reason normalization, precondition logic, store-digest computation, oracle
extraction, or cell scoring.

The review room found one non-blocking documentation omission in the frozen
source index: `matrix.close_summary.AG-U1` omits the defended draw's
`not_engaged: 1`. The eleven per-ledger entries and fresh scorer outputs are
authoritative and correct. The endorsed index remains historical and unchanged;
the implementation never consumes that derived rollup.

## Wire verification

Run:

```bash
make body-core-m3-test
```

The suite round-trips all eleven indexed ledgers and exercises fourteen named
checks:

1. full matrix and exact fresh scorer evidence;
2. unhashed source mutation;
3. rehashed source mutation against the adapter-start aggregate;
4. stale materialized-view claim;
5. unknown kind, undeclared field, and opaque escrow;
6. ledger and episode index-pin mismatch;
7. missing, wrong-kind, non-causal, and coordinate-drifted source bindings;
8. missing, duplicate, orphan, and semantically disagreeing receipts;
9. boundary decisions naming an episode-absent record;
10. well-bound lifecycle, placement, and metabolic events;
11. Core-legal writer substitution;
12. Track-B state or receipt minting;
13. historical verdict stripping;
14. unchanged-scorer store-digest precondition refusal.

The nine Track-A lineages contain eighteen Core rows each. The two Track-B
lineages contain five each: 172 Core rows total and 1,397 append-prefix rows.
That is a deterministic work disclosure, not latency or a cost win. Full replay
and quadratic append remain admitted.

The exact post-build code-analysis surface is frozen in
[`body_core_m3_adapter_implementation_manifest.json`](body_core_m3_adapter_implementation_manifest.json).
Both independent reviewers reproduced that surface and returned **ENDORSE**
without repair. The review's non-blocking topology and test-strength debts are
recorded in the [review record](BODY_CORE_M3_ADAPTER_REVIEW.md), not silently
folded into these historical implementation bytes.

## Non-claims

- Source binding is provenance, not truth or authorization.
- Active/hot Track-A admission does not encode offer or withholding.
- Track-B no-state transport does not close the asserted-trust breach.
- Local writer routing is not cryptographic authentication.
- Green wire checks preserve earlier evidence; they do not create evidence.
- M2, M3, and X2 have not been shown to compose causally.
