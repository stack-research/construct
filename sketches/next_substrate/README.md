# NEXT substrate embodiment sketch

This is an executable walking skeleton for the body described in
[NEXT_SUBSTRATE.md](../../notes/NEXT_SUBSTRATE.md). It exists to make the whole
runtime traversable before any proposed organ is treated as a finding.

Its base is [Body Core v0.2](core.py): a provisional integrity kernel plus an
explicitly provisional lifecycle/placement/warrant policy profile. The
epistemic-frame behavior in `runtime.py` is one stubbed consumer of that
core. The policy profile is not part of a mechanism-neutral ontology.

## Evidence boundary

Every event carries:

```text
evidence_class = wire_integration_only
```

The opening configuration and every disposition activation additionally disclose:

```text
mechanism_license / license_status = stubbed_not_earned
```

The model behavior, trigger, check, oracle, and counterfactual are authored and
deterministic. The sketch may establish that the parts compose and replay. It
cannot establish that:

- a language model learned from experience;
- structural transfer works on a real engine;
- the epistemic-frame check deserves a mechanism license;
- any branch is better than a simpler baseline;
- the event shapes are product schema.
- Body Core reduces reconstruction cost;
- the local writer-role claims are cryptographic authentication.

The hash chain detects mutation, deletion, and reordering relative to a trusted
chain head. It does not prevent a fully privileged writer from rebuilding a
different chain. v0.2 is also a single-process sketch: it has no concurrent-writer
locking, external chain-head anchoring, signature verification, compaction, or
schema migration. Reference/redaction retention validates the envelope and
content digest shape; it does not fetch or independently verify the external
payload.

Do not write its output under `runs/` or cite it as memory evidence.

## What it traverses

The demo reloads the body from disk between four invocations:

1. A deterministic model stub treats a source assertion as observation and
   fails an external deterministic oracle.
2. The external controller activates a probationary disposition under an
   explicitly stubbed license. On a different-domain task with the same declared
   structure, the disposition runs a provenance/scope check before commitment.
3. A direct-observation task does not match and pays no check.
4. An external provenance revision invalidates the original warrant, suspends
   the disposition, and a later invocation reconstructs that suspension from
   lineage.

The trace includes encounter, activation, action-boundary controller events,
model action, external consequence, metabolic events, a wire-only causal probe,
and an external provenance-health sweep.

## Component maturity

| Component | Sketch implementation | Maturity |
| --- | --- | --- |
| Language model | Replaceable port; deterministic authored stub | **Stubbed** |
| Durable lineage | Body Core v0.2 integrity kernel: deterministic indexes, hash chain, declared authority and references | **Provisional engineering** |
| Untrusting replay | Fail-closed envelope/state validation; stale view claims refused | **Provisional engineering** |
| Policy profile | Lifecycle, binary hot/cold, warrant health/dependents, invalid-warrant suspension | **Provisional engineering** |
| Derived reports | State, placement, and reported metabolic totals | **Provisional engineering** |
| X2 adapter | Reversible field-visible transport through unchanged scorer | **v0.2 cold-reviewed; endorsed** |
| M2 adapter | Paired S1/S2 transport; world-failure warrant; session-seam activation | **Cold-reviewed; endorsed after one repair** |
| Cognitive materialization | Full replay from lineage on each reawakening | **Provisional sketch** |
| Activation field | Empty ordinary offer phase plus action-boundary placement | **Provisional sketch** |
| Disposition mechanism license | Hard-coded epistemic-frame template | **Stubbed, not earned** |
| Resident disposition | Probationary instance with validity envelope | **Provisional sketch** |
| Required check | Deterministic provenance/scope comparison | **Stubbed** |
| Consequence | External deterministic oracle | **Stubbed** |
| Metabolic sensor | Check execution plus authored wire causal probe | **Provisional sketch** |
| Provenance health | External revision sweep suspends dependent state | **Provisional sketch** |

## Run

```bash
make body-sketch
```

Retain the temporary lineage in a new directory:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache uv run --no-project \
  python -m sketches.next_substrate.demo --state-dir /private/tmp/body-sketch
```

The command refuses to append a second demo to an existing non-empty lineage.

## Test

```bash
make body-core-test
make body-core-x2-test
make body-core-m2-test
make body-sketch-test
```

`body-core-test` checks only core wire properties: deterministic reconstruction,
derived views, authority and reference validation, lifecycle invariants,
hash-chain tamper detection, and refusal of stale materialized-view claims.
`body-core-x2-test` round-trips four closed real X2 ledgers through Core, checks
the unchanged scorer under pinned canonical equality, and exercises four
contract refusal legs plus the aggregate source-digest binding. It preserves
prior evidence; it creates no finding. The
[cold review](../../notes/BODY_CORE_X2_REVIEW.md) endorsed that exact boundary
and recorded policy-view correspondence, now closed in v0.2, as debt.
`body-core-m2-test` round-trips ten closed S1/S2 pairs, fresh-scores both sides
with the unchanged resident scorer, and checks warrant and lifecycle refusal
paths. It creates no M2 finding.
`body-sketch-test` also checks complete traversal, action-boundary placement,
silence on a non-matching task, and refusal of an unresolved warrant.
