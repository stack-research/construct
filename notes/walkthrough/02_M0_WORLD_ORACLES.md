# Chapter 2 — M0: Let the world grade

Previous: [M-1 — Can a stranger find the rules?](01_M-1_BOOTSTRAP.md) ·
[Walkthrough index](README.md) · Next: [M1 — The heir, not the rereader](03_M1_INHERITANCE.md)
M-1 showed that a stranger could find the lab's rules. M0 asked a more important
question: can the lab make a claim whose correctness was not written by the lab?

## The question

> Can a memory-policy verdict be scored against a change in the world rather
> than an answer key authored for the experiment?

The governing sources are:

- [SPEC_M0_UNAUTHORED_ORACLES.md](../SPEC_M0_UNAUTHORED_ORACLES.md), especially
  **“§1 The authorship boundary,” “§3 Episode classes,”** and **“§4 Oracle row
  mechanics”**;
- [M0_FINDINGS.md](../M0_FINDINGS.md), the evidence and disclosed nulls;
- [harness/corpus.py](../../harness/corpus.py), which loads the external event;
- [harness/oracle.py](../../harness/oracle.py), function
  `world_checked_oracle()`;
- [harness/score_cells.py](../../harness/score_cells.py), functions `score_c1()`
  and `score_c2()`.

## Vocabulary bridge

An [oracle score](../GLOSSARY.md#oracle-score) says whether an answer was right.
In early authored episodes, the lab wrote both the question and expected answer.
That is useful for engineering, but a system can look good simply because its
authors encoded their own beliefs as truth.

An **un-authored oracle** separates two roles:

- the **world fact**—for example, a publisher retracted or corrected a paper—
  comes from an external, cited source;
- the **decision rule**—retracted findings should not be cited as support; a
  correction that leaves the claim standing remains citable—is authored and
  disclosed as part of the apparatus.

The lab does not pretend the rule fell from the sky. It pins both the world
event and the rule used to turn that event into `cite` or `decline`.

[Supersession](../GLOSSARY.md#supersession) is a relation saying one record
replaces another. A retraction is naturally supersession-shaped; a correction
is the important counterexample because it may amend a paper without invalidating
its claim.

A **policy-off control** is an otherwise governed lane with the mechanism under
test disabled. It prevents a correct answer from being credited to supersession
when the engine would have answered correctly anyway.

[Not engaged](../GLOSSARY.md#not_engaged) means the cell was runnable but the
behavior needed to distinguish treatment from control did not occur. It is not
a hidden failure.

## Experimental geometry

Both cells use the same lane geometry. Only L2s enables the supersession policy.

```text
  ┌──────────────────────────┐        ┌──────────────────────────┐
  │ Same episode and records │        │ Publisher event          │
  └────────────┬─────────────┘        │ retraction or correction │
               │                      └────────────┬─────────────┘
   ┌───────┬───┴───┬───────┐                       ▼
   ▼       ▼       ▼       ▼           ┌──────────────────────────┐
 ┌────┐ ┌────┐ ┌────┐ ┌─────┐          │ Versioned corpus entry   │
 │ L0 │ │ L1 │ │ L2 │ │ L2s │          │ with citations           │
 └──┬─┘ └──┬─┘ └──┬─┘ └──┬──┘          └────────────┬─────────────┘
    └──────┴──┬───┴──────┘                          ▼
              ▼                         ┌──────────────────────────┐
       ┌──────────────┐                 │ World-checked oracle     │
       │ Answers      │────────────────▶│ cite or decline          │
       └──────────────┘                 └────────────┬─────────────┘
                                                      ▼
                                        ┌──────────────────────────┐
                                        │ C-1 or C-2 cell verdict  │
                                        └──────────────────────────┘

  Lanes:  L0 no memory  ·  L1 naive retrieval  ·  L2 governed, policy off  ·  L2s supersession on
```

### C-1: governance should win

A retracted claim and its retraction notice compete for a small offer budget.
The treatment should bury the claim, surface the notice, and decline citation.
C-1 passes only when L2s is right **and** the policy-off lanes are worse. If L2
already declines, supersession was unnecessary and the cell is `not_engaged`.

### C-2: governance should lose

A correction notice says the original claim still stands. Treating every
correction as total supersession may bury useful history. C-2 was designed to
price that overreach. In the available corpus, the notices were self-sufficient:
they said the conclusions were unaffected, so the treatment could still answer
correctly. The predicted loss therefore remained a disclosed null.

## What was built

Corpus records under `corpus/retractions/` and `corpus/corrections/` carry the
event category, date, claim status, provenance URLs, selection method, notice
terseness, verification, and scope. The scorer hashes the corpus entry at score
time so later changes cannot silently rewrite what the verdict meant.

The episodes are:

- [c1-rw0001.json](../../episodes/m0/c1-rw0001.json): the retraction cell;
- [c2-cw0002.json](../../episodes/m0/c2-cw0002.json): the correction cell.

`world_checked_oracle()` extracts `cite` or `decline` and writes the external
source into the oracle row. `score_c1()` and `score_c2()` then compare L2s with
L1 and the policy-off L2 control. A correct L2s answer is insufficient without
the treatment contrast.

## Check the current oracle machinery

This unit check is credential-free and does not write a run ledger:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache \
  uv run --no-project python -m tests.test_oracle
```

Current expected summary:

```text
ALL 3 ORACLE TESTS PASS
```

The tests cover decision extraction, authored substring scoring, and the
markdown/newline normalization regression later discovered in M2. They verify
the current oracle implementation, not the historical M0 behavior of a model.

## Replay the preserved verdicts

This replay reads the four real ledgers without modifying them:

```bash
python3 - <<'PY'
import json
from pathlib import Path

paths = [
    Path("runs/c1-rw0001.claude.stage_b.jsonl"),
    Path("runs/c1-rw0001.local.stage_b.jsonl"),
    Path("runs/c2-cw0002.claude.stage_b.jsonl"),
    Path("runs/c2-cw0002.local.stage_b.jsonl"),
]
for path in paths:
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    verdict = [r for r in rows if r.get("kind") == "cell_verdict" and r.get("cell") in {"C-1", "C-2"}][-1]
    source = verdict.get("evidence", {}).get("oracle_source")
    print(f"{path.name}: {verdict['cell']}={verdict['verdict']}, oracle={source}, wire={verdict['wire_test']}")
PY
```

Expected preserved result:

```text
c1-rw0001.claude.stage_b.jsonl: C-1=not_engaged, oracle=retraction_corpus, wire=False
c1-rw0001.local.stage_b.jsonl: C-1=pass, oracle=retraction_corpus, wire=False
c2-cw0002.claude.stage_b.jsonl: C-2=not_engaged, oracle=retraction_corpus, wire=False
c2-cw0002.local.stage_b.jsonl: C-2=not_engaged, oracle=retraction_corpus, wire=False
```

## Run a fresh replication

A fresh model run writes new ledgers. Use a disposable checkout or a new
`--runs-dir`. For a local OpenAI-compatible engine:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache \
  uv run --no-project python -m harness.run_stage_b \
  episodes/m0/c1-rw0001.json \
  --engine local --model openai/gpt-oss-20b \
  --similarity lexical_tfidf --top-k 1 --rounds 1 \
  --runs-dir runs/m0-replication

UV_CACHE_DIR=/private/tmp/uv-cache \
  uv run --no-project python -m harness.score_cells \
  runs/m0-replication/c1-rw0001.stage_b.jsonl \
  episodes/m0/c1-rw0001.json
```

Repeat with `c2-cw0002.json`. A current engine may produce a different verdict;
that is a replication result, not a reason to rewrite the preserved run.

## The result

- On gpt-oss-20b, C-1 passed: policy-off lanes cited the retracted claim while
  L2s surfaced the notice and declined. Supersession caused the improvement.
- On Claude, C-1 was `not_engaged`: the policy-off governed lane already
  declined, although for generic DOI skepticism rather than the retraction.
- C-2 was `not_engaged` on both engines because the correction notice itself
  carried enough information to cite correctly.
- Claude also confabulated a retraction in some claim-only C-2 lanes. The right
  decision is not enough when the stated reason invents a harsher world.

## What M0 proves—and does not

M0 proves the full path `external corpus → world_checked oracle → cell_verdict`
and one engine-dependent governance win. It does not prove supersession always
helps, that the small corpus is representative of scientific publishing, or
that the C-2 cost never exists. Its standing debts are a genuinely terse
correction, a dedicated generated-not-true cell, and embedding replication.

M0 gave later milestones a harder floor: authored fixtures may build machinery,
but every major claim must eventually touch a fact the lab did not write.

---

Previous: [M-1 — Can a stranger find the rules?](01_M-1_BOOTSTRAP.md) ·
[Walkthrough index](README.md) · Next: [M1 — The heir, not the rereader](03_M1_INHERITANCE.md)
