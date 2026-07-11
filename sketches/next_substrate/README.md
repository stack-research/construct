# NEXT substrate embodiment sketch

This is an executable walking skeleton for the body described in
[NEXT_SUBSTRATE.md](../../notes/NEXT_SUBSTRATE.md). It exists to make the whole
runtime traversable before any proposed organ is treated as a finding.

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
| Durable lineage | Append-only disk JSONL with deterministic event indexes | **Provisional sketch** |
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
make body-sketch-test
```

The tests check only wire properties: complete traversal, ordered append,
replayable materialization, action-boundary placement, silence on a non-matching
task, and refusal of an unresolved warrant.
