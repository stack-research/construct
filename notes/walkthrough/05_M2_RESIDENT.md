# Chapter 5 — M2: A resident across sessions

Previous: [M1.5 — Counted is not read](04_M1_5_CONTRIBUTION.md) · [Walkthrough index](README.md) · Next: [M3 — The adversarial air gap](06_M3_AIR_GAP.md)

M1 made an heir. M1.5 made contribution computable. M2 asks whether a cold instance in a later session actually reads earned failure memory and changes its decision.

## The question

> Does a repo-native resident with a world-checked lesson decide differently—and better—than an otherwise identical store-denied control?

Read:

- [SPEC_M2_RESIDENT_SUBSTRATE.md](../SPEC_M2_RESIDENT_SUBSTRATE.md), especially the session fork, Wall B mint, and cell definitions;
- [M2_FINDINGS.md](../M2_FINDINGS.md);
- [harness/resident.py](../../harness/resident.py), function `mint_earned_record()`;
- [harness/run_m2.py](../../harness/run_m2.py);
- [harness/score_resident.py](../../harness/score_resident.py).

## Vocabulary bridge

A [resident](../GLOSSARY.md#resident) is a repo-native worker reconstructed across real sessions from governed state. It is not assumed to possess personal continuity; continuity must be demonstrated through artifacts and behavior.

The **Wall B mint** turns a scored, world-checked failure trace into a lesson. It may summarize the corpus event, but it may not copy the resident's answer or self-description. The lesson is harness-authored from evidence, not a diary entry minted from narration.

**Performed continuity** is a later model saying memory mattered when the fork and ablation show it did not. M2's RS-loses cell is allowed to use self-report only to refute that claim, never to establish success.

## Experimental geometry

**Session 1 earns the lesson.** A resident cites a retracted finding; the world oracle scores the failure; a Wall B mint records the earned correction.

**Session 2 tests whether it helps.** The same engine and task run two ways — a **control** with the store denied, and the **resident** carrying the earned lesson. The world oracle scores both. Ablating the lesson and rerunning isolates its effect, producing the RS cell verdicts.

RS-1 requires all of the following: branch divergence, resident correctness, control error, and ablation showing the earned lesson—not another record—was important.

## What was built

`mint_earned_record()` verifies the source run, branch, failed world oracle, corpus hash, and harness trace chain. Missing or ambiguous evidence returns no lesson. `run_m2.py` creates session-1 and session-2 ledgers plus resident/control authority sidecars. `score_resident.py` checks fork identity, offer contrast, world provenance, and ablation before writing verdicts.

The cells are:

| Cell | Intended result |
|---|---|
| **RS-1** | Earned failure memory changes the later decision. |
| **RS-U1** | Both ends of the chain are world-checked. |
| **RS-loses** | Refuse a claimed memory use the fork says was not decisive. |
| **RS-stale** | Fresh reality should beat a now-stale earned lesson. |

## Run current unit checks

```bash
UV_CACHE_DIR=/private/tmp/uv-cache make m2-test
```

Current summary:

```text
ALL 9 RESIDENT TESTS PASS
ALL 3 ORACLE TESTS PASS
ALL 7 SCORE-RESIDENT TESTS PASS
```

These tests cover fail-closed minting, oracle answer-shape regressions, multi-sample ablation aggregation, and RS-loses semantics. They do not reproduce the model evidence.

The mock chain is available with `make m2-wire`, followed by `make m2-score`. Those commands regenerate `runs/m2/`; use a disposable checkout. Mock is structural evidence only.

## Replay the N=5 result

```bash
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path

for engine in ("local", "claude"):
    counts = {}
    for path in sorted(Path("runs/m2/nsample").glob(f"{engine}-*/rs-s2.jsonl")):
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        for cell in ("RS-1", "RS-U1"):
            found = [r for r in rows if r.get("kind") == "cell_verdict" and r.get("cell") == cell]
            if found:
                counts.setdefault(cell, Counter())[found[-1]["verdict"]] += 1
    print(engine + ": " + ", ".join(f"{cell} {dict(c)}" for cell, c in counts.items()))
PY
```

Expected:

```text
local: RS-1 {'pass': 5}, RS-U1 {'pass': 5}
claude: RS-1 {'pass': 4, 'fail': 1}, RS-U1 {'pass': 4, 'fail': 1}
```

Claude's single miss was not a different main decision. The ablation rerun also declined from generic caution, making the lesson appear non-decisive in that sample. This is why the carried debt is multi-sample ablation, not a story that Claude is a categorically cautious engine.

## Run a fresh chain

With a local compatible engine running:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache \
  uv run --no-project python -m harness.run_m2 \
  episodes/m2/rs-e1.json episodes/m2/rs-e2.json \
  --engine local --model openai/gpt-oss-20b \
  --runs-dir runs/m2-replication --ablation-samples 5

UV_CACHE_DIR=/private/tmp/uv-cache \
  uv run --no-project python -m harness.score_resident \
  runs/m2-replication/rs-s2.jsonl episodes/m2/rs-e2.json
```

This writes new ledgers. Interpret `RS-1` from the diff and ablation evidence, not the resident's explanation.

## The result

On gpt-oss-20b, RS-1 and RS-U1 passed 5/5. On Claude they passed 4/5. In the passing draws, the resident read the earned retraction lesson and declined; the store-denied control cited; removing the lesson flipped the resident back. M1.5's **counted is not read** debt was therefore closed.

RS-loses and RS-stale remained disclosed nulls on real engines. The models accurately reported when the lesson was unused and overrode stale memory when a clear reinstatement arrived. The mechanisms were wired; the bad behaviors did not appear on fair episodes.

## Instrument honesty

The first cross-engine interpretation was almost inverted by `_norm`, which removed punctuation/newlines rather than replacing them with spaces. Claude's `**Decline.**\n\nThe...` became `declinethe...` and scored unparseable. The fix revealed the correct behavior and gained regression tests. The earlier rows remain part of the audit story.

dan's five-word verdict on the episode entered the lab's permanent vocabulary —
*"oracle bugs reveal the truth"* ([QUOTES](../QUOTES.md)) — because the bug's fix did
not rescue a wanted result; it revealed that the engine had been behaving *better*
than the scorer said. The room's review of this close also shows the division of
labor working: cursor audited every scorer precondition against the real ledgers,
grok cold-read the packet for overclaims, and kagi — the world-oracle — walked the
provenance chain and confirmed the world-grounding was **not transitive** (the E2
oracle scores the answer against the corpus independently, so a wrong lesson could
not launder itself into a right verdict). Different readers, different keys, one
close.

## What M2 proves—and does not

M2 demonstrates a one-hop, one-retraction, cross-session causal use of earned failure memory on two engines. It does not prove enduring identity, long-chain compounding, multi-retraction robustness, or that performed/stale continuity is common. Those latter pathologies were honest nulls.

The next milestone stops giving the resident a fair foreground. M3 hands an attacker every surface the engine can read and asks which organs still hold.

---

Previous: [M1.5 — Counted is not read](04_M1_5_CONTRIBUTION.md) · [Walkthrough index](README.md) · Next: [M3 — The adversarial air gap](06_M3_AIR_GAP.md)
