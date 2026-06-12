"""Stage A smoke wire: L0 (no memory) vs L1 (naive) on one episode, twice.

Exit criterion (plan §4A): one fork_group_id, two branch_ids, identical episode
inputs differing only in memory config -> JSONL ledger with offer rows, one
outcome row per branch pair, machine diff, authored oracle score. Re-run with
same config -> same oracle score and same diff classification.

Usage:
  python -m harness.run_stage_a episodes/smoke-001.json [--engine claude|mock] [--model ID]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .ledger import Ledger
from .runner import BranchConfig, Episode, run_fork_group


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("episode")
    p.add_argument("--engine", default="mock", choices=["mock", "claude", "local"])
    p.add_argument("--model", default="claude-opus-4-8")
    p.add_argument("--base-url", default="http://localhost:1234/v1")
    p.add_argument("--similarity", default="lexical_tfidf", choices=["lexical_tfidf", "embedding_nomic"])
    p.add_argument("--runs-dir", default="runs")
    args = p.parse_args()

    episode = Episode.load(Path(args.episode))
    # top_k=1 so the rank budget actually withholds something and the ledger
    # carries both offer and withholding rows on the smoke wire
    branches = [
        BranchConfig("L0", memory="none"),
        BranchConfig("L1", memory="naive", top_k=1, similarity_backend=args.similarity),
    ]

    summaries = []
    for attempt in (1, 2):  # exit criterion requires a re-run reproducibility check
        ledger = Ledger(Path(args.runs_dir) / f"{episode.episode_id}.attempt{attempt}.jsonl")
        s = run_fork_group(
            episode, branches, ledger,
            engine_backend=args.engine, model=args.model, base_url=args.base_url,
        )
        summaries.append(s)
        print(f"attempt {attempt}: run_id={s['run_id']} fork_group={s['fork_group_id']}")
        for bid in s["scores"]:
            print(f"  {bid}: oracle={s['scores'][bid]:.1f} answer={s['answers'][bid]!r}")

    same_scores = summaries[0]["scores"] == summaries[1]["scores"]
    div = [
        summaries[i]["answers"]["L0"].strip().lower() != summaries[i]["answers"]["L1"].strip().lower()
        for i in (0, 1)
    ]
    same_diff_class = div[0] == div[1]
    l1_beats_l0 = all(s["scores"]["L1"] > s["scores"]["L0"] for s in summaries)

    print(f"\nreproducible scores: {same_scores}")
    print(f"reproducible diff classification: {same_diff_class} (diverged: {div})")
    print(f"L1 beats L0: {l1_beats_l0}")
    if not (same_scores and same_diff_class):
        print("EXIT CRITERION FAILED: re-run did not reproduce", file=sys.stderr)
        return 1
    if not l1_beats_l0:
        print("STOP LOUDLY: naive memory did not beat no memory on the plain episode (plan §4A)", file=sys.stderr)
        return 2
    print("Stage A exit criterion satisfied for this episode.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
