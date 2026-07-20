# Passive anomaly log

Status: **OPENED 2026-07-20 — append-only observational register**.

Authority and cadence:
[FRONTIER_PAUSE.md](FRONTIER_PAUSE.md).

This log captures unplanned observations from ordinary work that may later
justify a cold frontier pass. It is not a candidate queue, idea backlog,
findings document, or substitute for an experiment ledger.

## Capture instructions

Add an entry when all of these are true:

- the behavior arose during work undertaken for another purpose;
- the behavior had, or could have had, a concrete downstream consequence;
- prior records, missing records, carried state, or context selection is one
  plausible cause;
- exact raw evidence can be linked or identified.

Do not add:

- hypothetical episodes invented during deliberate frontier search;
- mechanism ideas without an observed behavior;
- stylistic model quirks without a consequential outcome;
- known failures repeated without a materially new condition;
- conclusions inferred only from summary prose when raw evidence exists.

Capture promptly and minimally. Preserve the source date. Link the exact file,
ledger row, transcript entry, or external artifact rather than a repository
root. Never include secrets, credentials, or unnecessary personal data.

At capture time:

- describe what happened, not what should be built;
- name competing explanations;
- do not assign a candidate name;
- do not propose a treatment;
- do not claim that memory caused the behavior;
- leave `review_status` as `unreviewed`.

Entries are append-only. Correct an earlier entry with a new entry containing
`amends: <entry heading>`; do not silently revise the original observation.
Periodic reviews likewise leave `review_status: unreviewed` untouched in the
original entry and record the later classification in a new review entry.

## Observation template

```markdown
## YYYY-MM-DD — short factual label

- kind: observation
- source_task:
- raw_evidence:
- observed_behavior:
- expected_behavior:
- downstream_consequence:
- why_memory_may_have_mattered:
- competing_explanations:
- related_known_shape:
- reporter:
- review_status: unreviewed
```

Use `related_known_shape: none known` when appropriate. Similarity to an old
lineage is context for review, not proof that the new observation belongs to
it.

## Periodic review template

```markdown
## YYYY-MM-DD — periodic anomaly review

- kind: review
- interval_reviewed:
- entries_reviewed:
- classifications:
- possible_clusters:
- raw_evidence_complete:
- external_oracle_visible:
- loses_condition_visible:
- decision: remain_paused | cold_frontier_pass_warranted
- basis:
- reviewers:
- next_scheduled_review:
```

The four allowed classifications are:

- `isolated_noise`;
- `existing_failure_mode`;
- `repeated_insufficient`;
- `credible_cluster`.

One entry cannot reopen active search by itself. An early review requires three
materially similar observations. A scheduled review may identify a credible
cluster, but reopening still requires the evidence, consumer, oracle, competing
explanation, and loses-condition in
[FRONTIER_PAUSE.md](FRONTIER_PAUSE.md).

## Entries

## 2026-07-20 — log opened

- kind: administration
- decision: active frontier search paused; passive capture opened
- first_scheduled_review: on or after 2026-08-20
- observations_promoted: none
- note: deliberately elicited frontier-team ideas are not passive anomalies
