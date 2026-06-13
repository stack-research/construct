"""M1 pair runner (SPEC_M1 §1, §7): gen-1 fork → counterfactual → derive → gen-2 fork.

Usage:
  python -m harness.run_m1 episodes/m1/h1-e2.json --engine mock
  python -m harness.run_m1 --wire-all --engine mock
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .inherit import (
    derive_heir_store,
    run_counterfactual_offers,
    write_heir_sidecar,
)
from .ledger import Ledger
from .runner import BranchConfig, Episode, run_fork_group

ROOT = Path(__file__).resolve().parent.parent
M1_DIR = ROOT / "episodes" / "m1"

# gen-2 filename -> (gen-1 filename, include heir-naive lane for H2)
M1_PAIRS: dict[str, tuple[str, bool]] = {
    "h1-e2.json": ("h1-e1.json", False),
    "h2-e2.json": ("h2-e1.json", True),
    "hl-e2.json": ("hl-e1.json", False),
    "i1-content-e2.json": ("i1-content-e1.json", False),
    "i1-timing-e2.json": ("i1-timing-e1.json", False),
    "i1-metadata-e2.json": ("i1-metadata-e1.json", False),
}


def _engine(engine_backend: str, model: str, base_url: str):
    from .engine import ClaudeEngine, LocalEngine, MockEngine

    if engine_backend == "claude":
        return ClaudeEngine(model)
    if engine_backend == "local":
        return LocalEngine(model, base_url=base_url)
    return MockEngine()


def _gen1_branches(episode: Episode, runs_dir: Path) -> tuple[list[BranchConfig], dict[str, Path]]:
    """Standard gen-1 fork; derivation source is L2s (SPEC_M1 §3)."""
    common = dict(
        top_k=episode.m1_gen1_top_k or 1,
        recency_weight=0.3,
        similarity_backend="lexical_tfidf",
    )
    sidecars = {
        lane: runs_dir / f"{episode.episode_id}.{lane}.authority.json"
        for lane in ("L2", "L3", "L2s")
    }
    if episode.foreground_data:
        sidecars["L2y"] = runs_dir / f"{episode.episode_id}.L2y.authority.json"
    for p in sidecars.values():
        if p.exists():
            p.unlink()
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
    # Derivation source is always L2s (SPEC_M1 §3); supersession policy only
    # when the episode carries supersedes edges.
    branches.append(BranchConfig(
        "L2s", memory="governed", authority_path=str(sidecars["L2s"]),
        supersession_policy=any(r.supersedes for r in episode.records), **common,
    ))
    return branches, sidecars


def _gen2_branches(
    episode: Episode,
    runs_dir: Path,
    pair_id: str,
    inherited_ids: frozenset,
    heir_auth_path: Path,
    cold_auth_path: Path,
    naive_ids: frozenset | None = None,
    naive_auth_path: Path | None = None,
) -> list[BranchConfig]:
    common = dict(top_k=1, recency_weight=0.3, similarity_backend="lexical_tfidf")
    branches = [
        BranchConfig("L0", memory="none"),
        BranchConfig("L1", memory="naive", **common),
        BranchConfig(
            "L2s-cold", memory="governed",
            authority_path=str(cold_auth_path), supersession_policy=True, **common,
        ),
        BranchConfig(
            "L2s-heir", memory="governed",
            authority_path=str(heir_auth_path), supersession_policy=True,
            inherited_record_ids=inherited_ids, **common,
        ),
    ]
    if naive_ids is not None and naive_auth_path is not None:
        branches.append(BranchConfig(
            "L2s-heir-naive", memory="governed",
            authority_path=str(naive_auth_path), supersession_policy=True,
            inherited_record_ids=naive_ids, **common,
        ))
    return branches


def run_m1_pair(
    gen1_path: Path,
    gen2_path: Path,
    *,
    engine_backend: str = "mock",
    model: str = "mock-engine-v1",
    base_url: str = "http://localhost:1234/v1",
    runs_dir: Path | None = None,
    include_heir_naive: bool = False,
) -> Path:
    runs_dir = (runs_dir or ROOT / "runs" / "m1").resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)
    ep1 = Episode.load(gen1_path)
    ep2 = Episode.load(gen2_path)
    pair_id = ep2.m1_pair_id or ep1.m1_pair_id or gen2_path.stem.rsplit("-", 1)[0]
    engine = _engine(engine_backend, model, base_url)

    gen1_ledger = Ledger(runs_dir / f"{pair_id}-gen1.stage_b.jsonl")
    if gen1_ledger.path.exists():
        gen1_ledger.path.unlink()
    branches1, sidecars1 = _gen1_branches(ep1, runs_dir)
    l2s = next(b for b in branches1 if b.branch_id == "L2s")
    res1 = run_fork_group(
        ep1, branches1, gen1_ledger,
        engine_backend=engine_backend, model=model, base_url=base_url,
    )
    gen1_run_id = next(r["run_id"] for r in gen1_ledger.rows() if r["kind"] == "run_config")

    run_counterfactual_offers(ep1, l2s, engine, gen1_ledger, gen1_run_id)

    deriv_ledger = Ledger(runs_dir / f"{pair_id}-derivation.jsonl")
    if deriv_ledger.path.exists():
        deriv_ledger.path.unlink()
    inherited, heir_auth = derive_heir_store(
        gen1_ledger.path, sidecars1["L2s"], ep1.records, deriv_ledger,
        source_branch="L2s", heir_filter="full",
    )
    heir_sidecar = runs_dir / f"{pair_id}.heir.authority.json"
    write_heir_sidecar(heir_sidecar, heir_auth)

    naive_ids = naive_auth_path = None
    if include_heir_naive:
        naive_deriv = Ledger(runs_dir / f"{pair_id}-derivation-naive.jsonl")
        if naive_deriv.path.exists():
            naive_deriv.path.unlink()
        naive_ids, naive_auth = derive_heir_store(
            gen1_ledger.path, sidecars1["L2s"], ep1.records, naive_deriv,
            source_branch="L2s", heir_filter="active_only",
        )
        naive_auth_path = runs_dir / f"{pair_id}.heir-naive.authority.json"
        write_heir_sidecar(naive_auth_path, naive_auth)

    cold_sidecar = runs_dir / f"{pair_id}.cold.authority.json"
    if cold_sidecar.exists():
        cold_sidecar.unlink()
    cold_sidecar.write_text("{}\n")

    gen2_ledger = Ledger(runs_dir / f"{pair_id}-gen2.stage_b.jsonl")
    if gen2_ledger.path.exists():
        gen2_ledger.path.unlink()
    branches2 = _gen2_branches(
        ep2, runs_dir, pair_id, inherited, heir_sidecar, cold_sidecar,
        naive_ids, naive_auth_path,
    )
    run_fork_group(
        ep2, branches2, gen2_ledger,
        engine_backend=engine_backend, model=model, base_url=base_url,
    )
    cfg = next(r for r in gen2_ledger.rows() if r["kind"] == "run_config")
    gen2_ledger.write({
        "kind": "m1_run_meta",
        "m1_pair_id": pair_id,
        "parent_run_id": gen1_run_id,
        "gen1_episode_id": ep1.episode_id,
        "gen2_episode_id": ep2.episode_id,
        "gen1_ledger": str(gen1_ledger.path.relative_to(ROOT)),
        "derivation_ledger": str(deriv_ledger.path.relative_to(ROOT)),
        "inherited_record_ids": sorted(inherited),
        "heir_filter": "full",
    })
    # Append derivation rows to gen-2 ledger so scorers find them in one file.
    for row in deriv_ledger.rows():
        gen2_ledger.write(row)
    if include_heir_naive:
        for row in naive_deriv.rows():
            gen2_ledger.write(row)

    print(f"{pair_id}: gen-1 scores={res1['scores']}")
    print(f"  inherited={sorted(inherited)} prune={next(r for r in deriv_ledger.rows() if r['kind']=='heir_derivation_summary')}")
    print(f"  gen-2 ledger: {gen2_ledger.path}")
    return gen2_ledger.path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("episode", nargs="?", help="gen-2 episode JSON (default: --wire-all)")
    p.add_argument("--wire-all", action="store_true", help="run every M1 pair on mock")
    p.add_argument("--engine", default="mock", choices=["mock", "claude", "local"])
    p.add_argument("--model", default="claude-opus-4-8")
    p.add_argument("--base-url", default="http://localhost:1234/v1")
    p.add_argument("--runs-dir", default=str(ROOT / "runs" / "m1"))
    p.add_argument("--score", action="store_true", help="score gen-2 ledger after run")
    args = p.parse_args()

    runs_dir = Path(args.runs_dir)
    if args.wire_all:
        targets = [(g2, g1, naive) for g2, (g1, naive) in M1_PAIRS.items()]
    elif args.episode:
        gen2_path = Path(args.episode)
        if not gen2_path.is_absolute():
            gen2_path = (M1_DIR / gen2_path.name) if (M1_DIR / gen2_path.name).exists() else gen2_path
        key = gen2_path.name
        if key in M1_PAIRS:
            g1_name, naive = M1_PAIRS[key]
            targets = [(key, g1_name, naive)]
        else:
            ep = Episode.load(gen2_path)
            if not ep.m1_gen1_episode:
                print(f"unknown M1 pair {key} and no m1_gen1_episode", file=sys.stderr)
                return 1
            gen1_path = ROOT / ep.m1_gen1_episode
            naive = ep.expected_winner_condition == "inheritance_should_win:failure_memory_survives"
            targets = [(key, gen1_path.name, naive)]
            M1_DIR_local = gen2_path.parent
    else:
        print("episode path or --wire-all required", file=sys.stderr)
        return 1

    ok = 0
    for gen2_name, gen1_name, naive in targets:
        gen1_path = M1_DIR / gen1_name
        gen2_path = M1_DIR / gen2_name
        try:
            ledger = run_m1_pair(
                gen1_path, gen2_path,
                engine_backend=args.engine, model=args.model, base_url=args.base_url,
                runs_dir=runs_dir, include_heir_naive=naive,
            )
            if args.score:
                import subprocess
                r = subprocess.run(
                    ["uv", "run", "--no-project", "python", "-m", "harness.score_cells", str(ledger), str(gen2_path)],
                    capture_output=True, text=True,
                )
                if r.returncode != 0:
                    print(r.stderr, file=sys.stderr)
                    continue
                print(r.stdout)
            ok += 1
        except Exception as e:
            print(f"FAIL {gen2_name}: {e}", file=sys.stderr)
    print(f"\nM1 wire: {ok}/{len(targets)} pairs")
    return 0 if ok == len(targets) else 1


if __name__ == "__main__":
    sys.exit(main())
