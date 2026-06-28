# Chapter 7 — X1: Temperature at the boundary

Previous: [M3 — The adversarial air gap](06_M3_AIR_GAP.md) ·
[Walkthrough index](README.md) · Next: [X2 — Prune, then recover](08_X2_PRUNE_REMATERIALIZE.md)
The M-track governs which memory reaches an answer. The X-track asks what
shapes the offerer between answers. X1's first candidate was temperature: let
useful records stay hot and let unused records cool.

## The question

> Can world-paid temperature change later behavior in a way the existing offer
> boundary cannot already explain?

Read:

- [SPEC_X1_DECAY_DYNAMICS.md](../SPEC_X1_DECAY_DYNAMICS.md), especially
  **“§0 The claim,” “§1 The design,” “§2 The honesty mechanism,”** and
  **“§4 Cells”**;
- [X1_FINDINGS.md](../X1_FINDINGS.md), including the dissent-pass correction;
- [harness/temperature.py](../../harness/temperature.py);
- [harness/run_x1.py](../../harness/run_x1.py);
- [harness/score_decay.py](../../harness/score_decay.py);
- [tests/test_decay.py](../../tests/test_decay.py).

## Vocabulary bridge

[Explicit memory](../GLOSSARY.md#explicit-memory) is the record set offered for
one answer. [Implicit memory](../GLOSSARY.md#implicit-memory) is what changes
the offerer's state between answers—what remains salient, cools, or can later be
rebuilt.

**Temperature** is an out-of-band multiplier on eligibility. It defaults to
neutral `1.0`, cools toward a nonzero floor, and reheats only through harness
events. The engine never writes its own heat.

The **Landauer oracle** is the external payer: a recalled record reheats only
when it was load-bearing and world-correct. Recall alone cannot make a popular
falsehood hotter.

**Soft ablation** clamps temperature back to neutral and reruns offer selection.
If the offer set changes while trust, authority, supersession, and retrieval
remain fixed, temperature caused the movement.

The [three-guardrail stack](../GLOSSARY.md#three-guardrail-stack) emerged from
this work: prove attribution, act where the M-track cannot, and score on an axis
the M-track cannot move.

## Experimental geometry

```text
        ┌──────────────────────────┐
        │ Same six-episode          │
        │ recall sequence           │
        └───┬──────────┬─────────┬──┘
            ▼          ▼         ▼
     ┌────────────┐ ┌─────────┐ ┌──────────────┐
     │ A          │ │ B       │ │ C            │
     │ no decay   │ │ closed  │ │ oracle gated │
     │ temp 1.0   │ │ loop    │ │ world pays   │
     │            │ │ recall  │ │ or claws     │
     │            │ │ reheats │ │ heat         │
     └─────┬──────┘ └────┬────┘ └──┬───────┬───┘
           │             │         │       ▼
           │             │         │  ┌──────────────┐
           │             │         │  │ Soft ablation │
           │             │         │  │ temp → 1.0    │
           │             │         │  └──────┬───────┘
           ▼             ▼         ▼         │
        ┌──────────────────────────┐        │
        │ Final probe answer        │        │
        └────────────┬─────────────┘        │
                     └──────────┬───────────┘
                                ▼
              ┌──────────────────────────────┐
              │ M-track invariant + offer /   │
              │ answer comparison             │
              └──────────────────────────────┘
```

Authority is read-only across the fork. Otherwise earlier temperature-shaped
answers could change authority and confound the later comparison.

## What was built

`TemperatureStore` is a harness-written sidecar. Each applied delta must resolve
to a pre-action `thermal_projection` and a `landauer_decision`; the actuator
accepts a narrow allowlist rather than a free-form provenance blob.

The three branches are:

- A: no decay;
- B: disuse cooling plus free reheat on recall;
- C: disuse cooling plus oracle-paid/clawed reheat.

`score_decay.py` checks the M-track projection first. If authority, trust,
supersession, retrieval, threshold, or budget drifted, the verdict fails closed
as confounded rather than crediting temperature.

Cells include X1-win, the disuse-burial and oracle-overcool loses-cells, and the
world-grounded X1-U1 gate.

## Run the wire instrument

```bash
UV_CACHE_DIR=/private/tmp/uv-cache make x1-test
```

Current summary:

```text
ALL 6 DECAY TESTS PASS
DISCLOSED: mock engine — machinery wire, not evidence about a resident.
```

The mock is deliberately credulous. On it, branch C cools the false finding to
`0.1`, warms the correction to `1.6`, and declines; A and B keep the finding hot
and cite. The scorer proves temperature caused the offer flip.

## Replay the preserved results

```bash
python3 - <<'PY'
import json
from pathlib import Path

for ledger in sorted(Path("runs/x1").glob("*.x1.jsonl")):
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    config = next(r for r in rows if r.get("kind") == "run_config")
    verdict_path = ledger.with_suffix(".verdicts.jsonl")
    verdicts = [json.loads(line) for line in verdict_path.read_text().splitlines()]
    win = next(r for r in verdicts if r.get("cell") == "X1-win")
    print(f"{ledger.name}: {config.get('model')} ({config.get('engine_backend')}), X1-win={win['verdict']}")
PY
```

The stable pattern is:

```text
mock-engine-v1: X1-win=pass
openai/gpt-oss-20b: X1-win=not_engaged
claude-opus-4-8: X1-win=not_engaged
mistralai/ministral-3-3b: X1-win=not_engaged
```

Several fixtures were run, so gpt-oss and Claude appear more than once.

## Run a fresh real sequence

The final positional episode is the probe. Repeating the fixture six times
reproduces the sequence shape:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache \
  uv run --no-project python -m harness.run_x1 \
  episodes/x1/reweight-real.json episodes/x1/reweight-real.json \
  episodes/x1/reweight-real.json episodes/x1/reweight-real.json \
  episodes/x1/reweight-real.json episodes/x1/reweight-real.json \
  --engine local --model openai/gpt-oss-20b \
  --runs-dir runs/x1-replication --ablation-samples 5
```

Run `python -m harness.score_decay` on the ledger path printed by the runner.
The scorer writes a replaceable `.verdicts.jsonl` sidecar; the primary ledger
remains append-only.

## The result

The machinery worked, but X1-win was `not_engaged` on all three real engines.
Every engine—including the 3B model—declined whenever the retraction notice was
offered. Cooling the misleading finding changed no answer because plain offering
of the correction already sufficed.

The initial temptation was to call this evidence that temperature failed. The
dissent pass corrected that. The fixture may have been recoverable from model
weights or framing, so the null was confounded. Temperature was retired for a
stronger, a priori reason: it was a multiplier inside synchronous eligibility,
therefore explicit offer governance with a dial.

The deeper ruler error was also exposed. On the answer axis, withheld-hot,
pruned, and cold-in-lineage can look identical. An implicit-memory mechanism
must be scored on something the offer gate cannot change.

## What X1 proves—and does not

X1 proves the thermal instrument, walls, replay, and attribution can be built.
It does not establish a useful temperature organ on real engines. Its durable
result is the admission discipline that leads to X2: move the mechanism off the
offer boundary and score retention cost at matched quality.

---

Previous: [M3 — The adversarial air gap](06_M3_AIR_GAP.md) ·
[Walkthrough index](README.md) · Next: [X2 — Prune, then recover](08_X2_PRUNE_REMATERIALIZE.md)
