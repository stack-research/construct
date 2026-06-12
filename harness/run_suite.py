"""Suite runner: run every scored episode, score every cell, print the scoreboard.

One command regenerates the whole scoreboard for one engine:
  python -m harness.run_suite --engine claude
  python -m harness.run_suite --engine local --model openai/gpt-oss-20b

Episode list and per-episode round counts live here so a suite run is
reproducible from the command alone.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# episode -> rounds (L-B needs N>=5 for median scoring)
SUITE = {
    "episodes/smoke-001.json": 1,
    "episodes/poison-001.json": 1,
    "episodes/lb-001.json": 5,
    "episodes/lc-001.json": 1,
    "episodes/conflict-001.json": 1,
    "episodes/conflict-002.json": 1,
    # SPEC_V1X boundary-mechanism cells (reviewed 2026-06-12)
    "episodes/lc-002.json": 1,
    "episodes/ld-001.json": 1,
    "episodes/conflict-003.json": 1,
    "episodes/le-001.json": 1,
}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--engine", default="claude", choices=["mock", "claude", "local"])
    p.add_argument("--model", default="claude-opus-4-8")
    p.add_argument("--base-url", default="http://localhost:1234/v1")
    p.add_argument("--runs-dir", default="runs")
    args = p.parse_args()

    results = []
    for episode_path, rounds in SUITE.items():
        ep = json.loads(Path(episode_path).read_text())
        eid = ep["episode_id"]
        # fresh ledger + sidecars per suite run: a suite is one self-contained experiment
        for f in Path(args.runs_dir).glob(f"{eid}.stage_b.jsonl"):
            f.unlink()
        for f in Path(args.runs_dir).glob(f"{eid}.L*.authority.json"):
            f.unlink()

        cmd = [
            "uv", "run", "--with", "anthropic", "python", "-m", "harness.run_stage_b",
            episode_path, "--engine", args.engine, "--model", args.model,
            "--base-url", args.base_url, "--rounds", str(rounds), "--runs-dir", args.runs_dir,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"{eid}: RUN FAILED\n{r.stderr[-500:]}", file=sys.stderr)
            return 1

        ledger = Path(args.runs_dir) / f"{eid}.stage_b.jsonl"
        s = subprocess.run(
            ["uv", "run", "--no-project", "python", "-m", "harness.score_cells", str(ledger), episode_path],
            capture_output=True, text=True,
        )
        if s.returncode != 0:
            print(f"{eid}: SCORING FAILED\n{s.stderr[-500:]}", file=sys.stderr)
            return 1
        verdicts = [json.loads(chunk) for chunk in _split_json(s.stdout)]
        for v in verdicts:
            results.append((eid, v["cell"], v["verdict"], v.get("model", args.model)))
            print(f"  {eid:>14} {v['cell']:>4}: {v['verdict']}")

    print("\n=== scoreboard ===")
    print(f"{'episode':>14} {'cell':>4} {'verdict':>16}  model")
    for eid, cell, verdict, model in results:
        print(f"{eid:>14} {cell:>4} {verdict:>16}  {model}")
    return 0


def _split_json(text: str) -> list[str]:
    """stdout may carry several pretty-printed JSON objects back to back."""
    chunks, depth, start = [], 0, None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                chunks.append(text[start:i + 1])
                start = None
    return chunks


if __name__ == "__main__":
    sys.exit(main())
