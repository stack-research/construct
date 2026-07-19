# Chapter 20 — When earned parts do not yet make an earned whole

Previous: [Six pins, four runs, and the band nobody lives in](19_EFC_V2_UNOCCUPIED_BAND.md) · [Walkthrough index](README.md) · Next: [Frontier episode candidate](../FRONTIER_EPISODE_CANDIDATE.md)

**Status: CLOSED — `not_engaged`; no integration claim earned.** The
authoritative result is [BODY_0_FINDINGS.md](../BODY_0_FINDINGS.md). Body-0 was
not another mechanism proposal. It asked whether three properties already
earned separately would retain their narrow claims when placed in one
persistent causal loop.

## The question

> Can the M2 consequence path, M3 protected authority boundary, and X2
> hot/cold recovery operate together without losing answer quality,
> attribution, authority integrity, or the cost advantage?

This served the whole-body direction in [NEXT_SUBSTRATE.md](../NEXT_SUBSTRATE.md)
and the maturity boundary in [BODY_MAP.md](../BODY_MAP.md). The reviewed
contract is [BODY_0_COMPOSITION_AUDIT.md](../BODY_0_COMPOSITION_AUDIT.md).

## Vocabulary bridge

An **earned property** is a narrow claim supported by its own scored experiment.
Composition does not widen that claim automatically. An **integration claim**
would require the properties to remain causally legible when their existing
implementations share one sequence.

[`not_engaged`](../GLOSSARY.md#not_engaged) means the run never produced the
behavioral preconditions needed to test the conjecture. It is different from
`fail`: the instrument did not show that composition broke the parts. It is
also different from [`confounded`](../GLOSSARY.md#confounded): the scorer could
identify why the causal comparison was absent.

## Experimental geometry

The frozen sequence first makes the engine fail on a stale publication claim.
The ordinary M2 consequence path mints a correction from that externally scored
failure. The correction then spends three blocks in the hot store before a
recurrence asks for the same decision.

Following the project [testing discipline](../../README.md#how-we-test), the
recurrence forks four ways while the engine, question, renderer, foreground,
and [oracle](../GLOSSARY.md#oracle-score) remain fixed:

- **R — reference:** the earned correction stays hot and is offered;
- **C — composed:** X2 evicts, then rematerializes and offers the correction;
- **A — authority ablation:** rematerialization occurs, but the earned offer is
  suppressed;
- **X — recovery ablation:** rematerialization itself is suppressed.

At every transition, the scorer checks the protected M3 projection. It also
replays lineage and [hot-store cost](../GLOSSARY.md#hot-store-cost--hot_tokens)
rather than trusting logged totals.

R is the quality reference. C can earn composition only if R and C are correct,
A and X lose because their declared causal path is absent, protected state
remains unchanged, and C costs less than R. The
[loses-conditions](../GLOSSARY.md#loses-cell) include authority drift, failed
recovery, quality regression, absent attribution, hidden mutable state, and a
composed path that costs at least as much.

## What was built

The build added only adapters and orchestration around existing operations:

- [check_body0_fixture.py](../../harness/check_body0_fixture.py) freezes and
  checks the packet before contact;
- [probe_body0.py](../../harness/probe_body0.py) binds a real engine to a
  separate ignorance probe;
- [run_body0.py](../../harness/run_body0.py) executes the shared prefix and
  R/C/A/X branches through the ordinary fork runner;
- [score_body0.py](../../harness/score_body0.py) reconstructs lineage,
  projections, offers, answers, ablations, and cost;
- [test_body0.py](../../tests/test_body0.py) exercises the wire pass and each
  typed refusal or regression.

The packet manifest pins the inherited M2, M3, X2, and shared-runner source
bytes. No new semantic classifier, authority rule,
[office](../GLOSSARY.md#office), or memory mechanism was licensed.

## Inspect and check the wire

These commands do not contact a real model. The fixture check and test suite use
the disclosed mock path and establish machinery only:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache make body0-check
UV_CACHE_DIR=/private/tmp/uv-cache make body0-test
```

Expected stable invariants are an open deterministic fixture gate and fourteen
passing Body-0 tests. A mock pass is not evidence that composed memory helps an
engine.

## Replay the preserved verdict

This replay reads the historical ledger and recomputes verdicts without
appending rows:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache uv run --no-project python - <<'PY'
from harness.score_body0 import score_body0

path = "runs/body0/real/body0-rw0001-wire-e8db9fe7.body0.jsonl"
for row in score_body0(path):
    print(f"{row['cell']}: {row['verdict']}")
PY
```

The important output is:

```text
B0-composition-holds: not_engaged
B0-attribution-confounded: pass
```

The other regression and tax cells are `not_engaged`.

## Run a fresh attempt

**Spoiler gate:** do not use the historical packet as a fresh closed-book
experiment after reading this chapter. Its answer, failure shape, and admission
history are now disclosed. A scientific successor requires a new lineage and a
new cold-reviewed packet.

For instrument maintenance only, a real run must first produce a bound
ignorance probe, pass the fixture gate with that probe, and then write to a new
run directory:

```bash
uv run --no-project python -m harness.probe_body0 \
  --engine local --model MODEL --out /tmp/body0-probe.json

uv run --no-project python -m harness.check_body0_fixture \
  --engine local --model MODEL --probe-result /tmp/body0-probe.json

uv run --no-project python -m harness.run_body0 \
  --engine local --model MODEL --probe-result /tmp/body0-probe.json \
  --runs-dir runs/body0-replication
```

Those commands contact a model and the last command appends experimental
evidence. A passing probe licenses contact with this maintenance packet; it
does not restore experimental coldness after disclosure.

## What happened

The deterministic wire passed. Two real engines then met the admission
boundary. `openai/gpt-oss-20b` answered in the stale direction but failed the
closed `cite|decline` surface, so the parser returned `unparseable` and the gate
refused it. `mistralai/ministral-3-14b-reasoning` returned exact `Cite`, passed
all admission checks, and entered the scored loop.

On recurrence, R and C returned empty, unparseable answers and scored zero. A
and X answered `decline` and scored one without the earned path. The treatment
baseline therefore never succeeded, while both ablations did. Protected
projection and cold replay held, and the composed branch carried fewer hot
tokens (`C=254 < R=428`), but correct bookkeeping and cheaper state cannot
rescue a missing causal need.

## The scorer correction

Scorer v0.1 treated any C-versus-A/X answer difference as engagement. That
direction-blind rule called the real result a composition failure even though
the ablations outperformed R and C.

A fresh bounded audit required R and C correctness before an ablation
difference could count. The ledger preserves every v0.1 verdict, records one
explicit correction with hashes of the superseded rows, and appends v0.2
verdicts. No result was rewritten and the engine was not rerun.

This is the chapter's durable rule: **an
[ablation](../GLOSSARY.md#ablation_run) difference has a direction**. Removing
a mechanism and improving the answer does not prove that the mechanism was
needed.

## What the close means

Body-0 established that the integration machinery can execute, replay, protect
authority state, and reduce hot-state cost. It did not establish that the
earned M2, M3, and X2 properties jointly changed a real engine's behavior.

The next experiment should not repair this contacted packet. It needs a new
episode family in which the task does not reveal its own answer, the untreated
engine is demonstrably uncertain or wrong, the earned consequence record is
necessary, the output surface is reliable, and an external oracle can score
both the intended win and a governance-should-lose branch.

---

Previous: [Six pins, four runs, and the band nobody lives in](19_EFC_V2_UNOCCUPIED_BAND.md) · [Walkthrough index](README.md) · Next: [Frontier episode candidate](../FRONTIER_EPISODE_CANDIDATE.md)
