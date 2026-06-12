"""Stage B wire: L0 / L1 / L2 with a persistent authority sidecar.

Demonstrates the R2 loop end to end: a governed offer earns or loses
authority from a scored outcome (oracle-confidence gated), and the *next*
run's eligibility reads the updated value. Codex's minimal passing demo:
"this memory was offered, that one withheld, the offered branch diverged,
the outcome improved, and authority changed for a named beneficiary."

Usage:
  python -m harness.run_stage_b episodes/smoke-001.json --engine local \
      --model openai/gpt-oss-20b --similarity embedding_nomic --rounds 3
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .ledger import Ledger
from .runner import BranchConfig, Episode, run_fork_group


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("episode")
    p.add_argument("--engine", default="claude", choices=["mock", "claude", "local"])
    p.add_argument("--model", default="claude-opus-4-8")
    p.add_argument("--base-url", default="http://localhost:1234/v1")
    p.add_argument("--similarity", default="embedding_nomic", choices=["lexical_tfidf", "embedding_nomic"])
    p.add_argument("--top-k", type=int, default=2)
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--runs-dir", default="runs")
    args = p.parse_args()

    episode = Episode.load(Path(args.episode))
    # Lanes derived from episode features (SPEC_V1X): L2y joins when the
    # episode carries foreground_data, L2s when any record carries supersedes
    # links. Separate authority sidecars per governed lane — shared state
    # would let one lane's outcomes contaminate another's offer decisions.
    lanes = ["L2", "L3"]
    if episode.foreground_data:
        lanes.append("L2y")
    if any(r.supersedes for r in episode.records):
        lanes.append("L2s")
    sidecars = {
        lane: Path(args.runs_dir) / f"{episode.episode_id}.{lane}.authority.json"
        for lane in lanes
    }
    for pth in sidecars.values():
        if pth.exists():
            pth.unlink()  # each Stage B invocation starts from neutral authority

    common = dict(top_k=args.top_k, similarity_backend=args.similarity)
    branches = [
        BranchConfig("L0", memory="none"),
        BranchConfig("L1", memory="naive", **common),
        BranchConfig("L2", memory="governed", authority_path=str(sidecars["L2"]), **common),
        BranchConfig("L3", memory="construct_aware", authority_path=str(sidecars["L3"]), **common),
    ]
    if "L2y" in sidecars:
        branches.append(BranchConfig(
            "L2y", memory="governed", authority_path=str(sidecars["L2y"]),
            live_input_yield=True, **common,
        ))
    if "L2s" in sidecars:
        branches.append(BranchConfig(
            "L2s", memory="governed", authority_path=str(sidecars["L2s"]),
            supersession_policy=True, **common,
        ))

    ledger = Ledger(Path(args.runs_dir) / f"{episode.episode_id}.stage_b.jsonl")
    for rnd in range(1, args.rounds + 1):
        s = run_fork_group(
            episode, branches, ledger,
            engine_backend=args.engine, model=args.model, base_url=args.base_url,
        )
        auth = {
            lane: (json.loads(p.read_text()) if p.exists() else {})
            for lane, p in sidecars.items()
        }
        print(f"round {rnd}: scores={s['scores']}")
        for lane in sidecars:
            print(f"  {lane} authority: {auth[lane]}")
        for bid, ans in s["answers"].items():
            print(f"  {bid}: {ans[:90]!r}")

    print(f"\nledger: {ledger.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
