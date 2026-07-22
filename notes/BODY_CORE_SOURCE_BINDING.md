# Body Core adapter source-binding helper

Status: **endorsed 2026-07-21** in the ended bounded
[`source-binding-v01-review`](BODY_CORE_SOURCE_BINDING_REVIEW.md).

This is wire/integration engineering only. It discharges the prerequisite named
by the completed [M2 adapter review](BODY_CORE_M2_REVIEW.md) before a third
adapter may be authored. It does not create a scientific mechanism, rerun M2 or
X2, reopen frontier search, or license an M3 adapter.

## Milestone gate

Scientific milestone: **none**. This serves the active Body Core engineering
direction while frontier search remains paused.

Question: can the repeated source-correspondence rule be shared without turning
source provenance into policy authority?

Preservation oracle:

- all four closed X2 ledgers retain exact reverse-projection equality and the
  unchanged X2 scorer's verdicts and costs;
- all ten closed M2 S1/S2 pairs retain exact reverse-projection equality and
  fresh output from the unchanged resident scorer;
- all previously named X2 and M2 refusal probes continue to bite.

Loses-condition: refuse the factoring if a selected state receipt can bind to a
missing, wrong-kind, non-causal, or coordinate-disagreeing source event, or if a
valid source binding grants an event class the client did not authorize.

## Shared rule

[`sketches/next_substrate/correspondence.py`](../sketches/next_substrate/correspondence.py)
is Core-adjacent, not part of the integrity kernel. A caller declares:

- its carried source-event kind;
- the state-receipt kinds that client authorizes;
- the adapter-materialized item ids in scope;
- the source-coordinate fields that must agree;
- a diagnostic context label.

For each selected receipt affecting an in-scope item, the helper requires:

1. a non-empty `source_event_id`;
2. a target event of the declared carried-source kind;
3. that target in the receipt's `causal_parent_ids`;
4. exact equality for every declared source-coordinate field.

It returns receipts grouped by source event. It does not decide receipt
cardinality, authorize any event kind the caller did not select, interpret a
source operation, or validate terminal policy state.

## Client boundaries

X2 selects `placement_changed` receipts and coordinates
`source_row_index`/`source_kind`. The X2 adapter still independently requires
exactly one receipt for each prune/rematerialize operation, none for any other
source row, matching item and hot/cold transition, and terminal placement equal
to the independent operation fold.

M2 selects only `state_item_transition` receipts and coordinates
`source_phase`/`source_row_index`/`source_kind`. The M2 adapter still requires
exactly one probationary-to-active receipt bound to the carried `m2_run_meta`,
terminal hot placement, and no placement or metabolic receipts. A new probe
shows that even a correctly source-bound placement event remains unauthorized.

Admission and warrant correspondence remain client-specific. This helper covers
post-admission state receipts only.

## Review surface

Exact files and verification commands are frozen in
[`body_core_source_binding_review_manifest.json`](body_core_source_binding_review_manifest.json).
Historical hashes in the X2 and M2 review records remain unchanged; they attest
to the bytes those reviews actually saw.

The bounded review ended with two independent **ENDORSE** verdicts and no
repair. The exact reviewed surface and the foreign-item jurisdiction
clarification are recorded in the [review record](BODY_CORE_SOURCE_BINDING_REVIEW.md).
The endorsement licenses this helper as the prerequisite for proposing a third
adapter; it does not license that adapter itself.

## Non-claims

- Source binding is provenance, not truth or authorization.
- Writer-role claims remain locally enforced assertions, not cryptographic
  authentication.
- The build does not reduce full-replay or append cost.
- Green wire tests preserve prior evidence; they are not new memory evidence.
