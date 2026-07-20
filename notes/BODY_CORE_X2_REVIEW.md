# Body Core v0.1 X2 adapter cold review

Status: **ENDORSED 1/1 — wire preservation only**.

Review thread:
[`builders-thread-v01`](../.substrate/threads/builders-thread-v01/).

The review covered the exact uncommitted bytes below. This record and the
post-review maturity-label updates were added after the room ended and are
intentionally outside the reviewed hashes.

| Artifact | Reviewed SHA-256 |
| --- | --- |
| `notes/BODY_CORE_X2_ADAPTER.md` | `011ab11423187a1063c8b899720c4b9108af9b116f1d2c686d17bf4e8dcf3e0e` |
| `sketches/next_substrate/core.py` | `f8bac44cc7c652037255d168e12a9a9484d2baf41de151f0c279631861b04258` |
| `sketches/next_substrate/x2_adapter.py` | `a2d5de7bdf71e77389aceb03dca246c058a8034018722f096cad95cdc18c1af8` |
| `tests/test_body_core.py` | `47a8a2de9bbefe78868dfa0614276338094a0b72b69b8bfcdab47af218b8b579` |
| `tests/test_body_core_x2_adapter.py` | `dd389d5fefd3fbbd9bce7ccba07ba277a6c42c34192c30cfbcb6f2e09e819153` |
| `notes/BODY_MAP.md` | `4cd44a40de605a28a7583c698e3eedfa51a3d5f57de0c6496333ed4989599b41` |
| `notes/NEXT_SUBSTRATE.md` | `dfc7c1a71cf37e9c85df463ff421910bbe396fed8726261e3d6187e6d2c7d680` |

## Verdict

`claude/fable-5`: **ENDORSE**. Fable independently matched all seven hashes,
read the adapter and unchanged X2 scorer, reproduced the relevant checks, and
confirmed:

- the finite flattened field contract is auditable rather than opaque
  `original_x2_row` escrow;
- per-row and aggregate source digests plus operation receipts bind the scorer
  projection;
- the unchanged scorer reproduces its complete verdict output and cost totals
  on all four closed real X2 ledgers under the pinned `{"ts"}`-only canonical
  exception;
- the integrity kernel and provisional policy profile are honestly separated;
- no documentation promotes wire preservation into a new X2 finding.

No repair phase opened. The single allowed repair remains unused.

## Reproduced checks

- `make body-core-x2-test`: seventeen Body Core v0.1 tests and seven adapter
  tests passed;
- `make body-sketch-test`: seventeen Core tests and six walking-skeleton tests
  passed;
- `make x2-test`: all sixteen existing X2 tests passed with the scorer and its
  suite unchanged;
- Ruff 0.15.22 passed on the reviewed Python files;
- `git diff --check` passed.

The round trip preserved two 102-row Helix ledgers as 131-row Core lineages and
two 92-row DEP0033 ledgers as 117-row Core lineages. The deterministic
append-prefix exposure was 8,515 and 6,786 rows respectively. This is disclosed
quadratic engineering debt, not latency evidence or a reconstruction-cost win.

## Exact boundary

The endorsement establishes only that Body Core v0.1 can carry these four
closed X2 ledgers and reproduce the unchanged scorer output while the declared
refusal probes bite. It does not establish:

- a new or stronger X2 finding;
- a scientific mechanism or product schema;
- cryptographic writer authentication or external chain anchoring;
- concurrent-writer safety;
- reduced reconstruction cost;
- general correspondence between arbitrary Core policy events and an organ's
  native lineage.

Active frontier search remains paused.

## Residual: policy-view correspondence

Fable appended an independently authored, Core-legal `placement_changed` event
without `source_event_id`. Projection and scorer equality still passed because
the event was not part of the X2 source projection, but the Core placement view
then disagreed with the carried X2 operation history.

This does not block the reviewed scorer-preservation claim: no altered row
reached `score_prune`, Core placement is not a scored X2 input, and every
reviewed verdict and cost remained unchanged. It narrows the adapter's policy
claim and is carried as explicit v0.2 debt:

> In an X2 adapter lineage, every `placement_changed` event for an
> `x2_materialized_record` must bind to exactly one carried prune or
> rematerialize source event, and terminal Core placement must equal the fold
> of those bound operations.

The residual is not an in-review repair and does not delay the endorsed v0.1
build.
