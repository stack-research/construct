# Chapter 8 — X2: Prune, then recover

Previous: [X1 — Temperature at the boundary](07_X1_TEMPERATURE.md) ·
[Walkthrough index](README.md) · Next: [X4 — The sensor that did not earn itself](09_X4_OCCLUSION_WATCH.md)
X1 changed the offer set and measured answers—the M-track's own territory. X2
moved both mechanism and ruler: evict records from the hot store, then measure
the cost of carrying memory while holding answer quality fixed.

## The question

> Can the substrate carry less hot memory without losing answer quality—and
> recover an evicted record when the world needs it again?

Read:

- [SPEC_X2_PRUNE_TO_COLD_STORE.md](../SPEC_X2_PRUNE_TO_COLD_STORE.md), especially
  the three guardrails, A/B/C design, cost metric, and cells;
- [X2_FINDINGS.md](../X2_FINDINGS.md);
- [harness/prune.py](../../harness/prune.py);
- [harness/run_x2.py](../../harness/run_x2.py);
- [harness/score_prune.py](../../harness/score_prune.py);
- [harness/check_x2_fixture.py](../../harness/check_x2_fixture.py).

The findings headline still contains pre-close “pending review” language. The
later [ROADMAP](../ROADMAP.md) and project [README](../../README.md#the-x-track--memory-between-answers)
record X2-U1 as closed on 2026-06-21. The walkthrough follows that later status
while leaving the stale line visible as documentation debt.

## Vocabulary bridge

The [hot store](../GLOSSARY.md#hot-store) is memory carried in active state. The
[cold lineage](../GLOSSARY.md#cold-lineage) is immutable history that remains
available for reconstruction.

[Prune](../GLOSSARY.md#prune) evicts a record from hot state; it never erases the
lineage. [Rematerialize](../GLOSSARY.md#rematerialize) returns an evicted record
when an external signal says it is needed.

[Hot-store cost](../GLOSSARY.md#hot-store-cost--hot_tokens) is measured in
`hot_tokens`. [Cost at matched quality](../GLOSSARY.md#cost-at-matched-quality)
means a cheaper branch wins only if it meets the no-prune branch's answer
quality. The cheapest wrong memory is not a win.

## Experimental geometry

One four-episode sequence runs three ways:

- **A** — plain L2, no prune;
- **B** — L2p, prune with no recovery;
- **C** — L2pR, oracle-gated prune plus rematerialize.

For each, the harness replays hot-token cost and checks the answer-quality floor;
the two together give the X2 verdicts.

B is the required loss. If a record recurs after pruning, B cannot recover it.
C must pay a small rematerialization cost and regain the correct answer.

## What was built

`HotStore` maintains the active record ids and emits pre-action projections for
prune/rematerialize. No delete verb exists; erasure from lineage is forbidden.

`run_x2.py` executes A/B/C across a sequence. `score_prune.py` distrusts logged
cost: it reconstructs the hot set from immutable lineage and operation rows,
then recomputes `hot_tokens`. Missing ids, tampered costs, broken fork identity,
or a missing admission-gate result confound the claim.

Two fixtures matter:

- Helix Basin: fictional and out-of-weights by construction, proving the record
  is important;
- [DEP0033](../../corpus/world/wf-dep0033.json): a real Node.js deprecation later
  revoked, with a pre-run ignorance probe showing both engines did not know the
  revocation.

## Run the instrument tests and fixture gates

```bash
UV_CACHE_DIR=/private/tmp/uv-cache make x2-test
UV_CACHE_DIR=/private/tmp/uv-cache make x2-fixture-check

UV_CACHE_DIR=/private/tmp/uv-cache \
  uv run --no-project python -m harness.check_x2_fixture \
  episodes/x2/u1-dep0033/manifest.json
```

Current summaries:

```text
ALL 16 PRUNE TESTS PASS
DISCLOSED: mock engine — machinery wire, not evidence about a resident.

GATE OPEN: Helix manifest passes 15 checks.
ALL X2 FIXTURE TESTS PASS

GATE OPEN: DEP0033 manifest passes 16 checks.
```

The gate verifies sequence files, record universe, answer records, prunable
distractor, oracle kind, cost ballast, savings, ranking, and—for DEP0033—the
world source and ignorance probe.

## Replay the world-grounded result

```bash
python3 - <<'PY'
import json
from pathlib import Path

for path in sorted(Path("runs/x2").glob("x2-u1-dep0033-*.x2.verdicts.jsonl")):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    keep = {r["cell"]: r for r in rows if r.get("cell") in {"X2-win", "X2-overprune", "X2-U1"}}
    win = keep["X2-win"]
    print(f"{path.name}: win={win['verdict']} cost={win['cost_hot_tokens']}; "
          f"overprune={keep['X2-overprune']['verdict']}; U1={keep['X2-U1']['verdict']}")
PY
```

Expected for both engines:

```text
win=pass cost={'L2': 248, 'L2p': 92, 'L2pR': 102}; overprune=pass; U1=pass
```

## Run a fresh gated sequence

```bash
UV_CACHE_DIR=/private/tmp/uv-cache \
  uv run --no-project python -m harness.run_x2 \
  --manifest episodes/x2/u1-dep0033/manifest.json \
  --engine local --model openai/gpt-oss-20b \
  --runs-dir runs/x2-replication --ablation-samples 5
```

The runner prints the primary ledger. Pass it to
`python -m harness.score_prune`; the scorer replaces only the derived verdict
sidecar. Do not use `--skip-gate` for a real claim.

## The result

On the fictional Helix fixture, A carried 312 hot tokens at quality 4.0; B
carried 105 but fell to 3.0 on recurrence; C carried 135 and held 4.0. C reduced
hot state by 57% at matched quality on both engines.

On DEP0033, A carried 248 at 4.0; B carried 92 but missed the revocation and fell
to 3.0; C rematerialized the revoked record, carried 102, and held 4.0. The
world-grounded reduction was 59%, identical across Claude and gpt-oss-20b.

The extra ten hot tokens C paid over B in the recurrence block are revocability
insurance. B is cheaper only because it cannot recover.

## What X2 proves—and does not

X2 is the first positive implicit-layer result: hot-store eviction and recovery
change a deterministic cost the synchronous offer gate cannot move, while
answer quality remains fixed against an external fact.

It remains N=1 quality per engine, one corpus, and one sequence shape. It does
not establish long-horizon consolidation, multi-recurrence behavior, or
asynchronous rematerialization. Its durable rule is: **forget the cost, never
lose the record.**

---

Previous: [X1 — Temperature at the boundary](07_X1_TEMPERATURE.md) ·
[Walkthrough index](README.md) · Next: [X4 — The sensor that did not earn itself](09_X4_OCCLUSION_WATCH.md)
