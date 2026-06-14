"""SPEC_M2 resident-substrate chain runner — the offer ledger across a session seam.

  S1 (E1): cold resident, scored failure          (single branch, world oracle)
     |  mint (Wall B): harness derives the earned record from the scored trace
     v
  S2 (E2): two-branch fork                          (Wall A: the fork decides use)
     - RS-resident : inherited store INCLUDING the earned record
     - RS-control  : the SAME store MINUS the one earned record

Only the earned record differs between the branches (symmetric-difference control).
The engine is re-instantiated cold each session; only the governed store crosses the
seam (memory_isolation). The resident's narration is never read — `score_resident.py`
reads the fork.

Usage:
  python -m harness.run_m2 episodes/m2/rs-e1.json episodes/m2/rs-e2.json \
      --engine local --model openai/gpt-oss-20b
  python -m harness.run_m2 --wire-all --engine mock      # structural wire only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

from .engine import renderer_version
from .ledger import Ledger
from .resident import mint_earned_record
from .runner import BranchConfig, Episode, run_fork_group

ROOT = Path(__file__).resolve().parent.parent
M2_DIR = ROOT / "episodes" / "m2"

RESIDENT_BRANCH = "RS-resident"
CONTROL_BRANCH = "RS-control"

# gen-2 filename -> gen-1 filename. World-oracle chains are real-engine-only
# (mock can't earn cite/decline); --wire-all runs them on mock as a STRUCTURAL
# smoke (does the seam execute, mint, and fork end-to-end), never as evidence.
M2_CHAINS: dict[str, str] = {
    "rs-e2.json": "rs-e1.json",
}


def _resident_config_digest(engine_backend: str, model: str) -> str:
    """The cold-identity surface (codex v0 amendment): engine + model + sampling +
    prompt/rendering + the no-conversation-state boundary. NOT the retrieval params
    (top_k/recency/eligibility) — those are the fork-identity held-constant set,
    checked separately from run_config.branches. S1 and S2 must carry the SAME
    digest (the engine is the same cold instance; only the store changed)."""
    surface = {
        "engine_backend": engine_backend,
        "model": model,
        "sampling": "engine_default_fixed",  # the harness never varies sampling
        "prompt_renderer": renderer_version(),
        "no_conversation_state": True,  # harness passes explicit offers; engine stateless per run
    }
    return hashlib.sha256(json.dumps(surface, sort_keys=True).encode()).hexdigest()[:16]


def run_resident_chain(
    e1_path: Path,
    e2_path: Path,
    *,
    engine_backend: str = "mock",
    model: str = "mock-engine-v1",
    base_url: str = "http://localhost:1234/v1",
    runs_dir: Path | None = None,
) -> Path:
    runs_dir = (runs_dir or ROOT / "runs" / "m2").resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)
    ep1 = Episode.load(e1_path)
    ep2 = Episode.load(e2_path)
    if not ep1.oracle_ref:
        raise ValueError(f"{ep1.episode_id}: E1 must bind a world oracle (oracle_ref) to mint from")
    chain_id = ep2.episode_id.rsplit("-", 1)[0]
    s1_id = "S1-" + uuid.uuid4().hex[:8]
    s2_id = "S2-" + uuid.uuid4().hex[:8]
    digest = _resident_config_digest(engine_backend, model)
    common = dict(recency_weight=0.3, similarity_backend="lexical_tfidf")

    # ---- Session 1 (E1): cold resident, single branch, scored against the world.
    s1_sidecar = runs_dir / f"{chain_id}.s1.authority.json"
    if s1_sidecar.exists():
        s1_sidecar.unlink()
    s1_ledger = Ledger(runs_dir / f"{chain_id}-s1.jsonl")
    if s1_ledger.path.exists():
        s1_ledger.path.unlink()
    e1_branch = BranchConfig(
        RESIDENT_BRANCH, memory="governed", authority_path=str(s1_sidecar),
        top_k=1, **common,
    )
    run_fork_group(
        ep1, [e1_branch], s1_ledger,
        engine_backend=engine_backend, model=model, base_url=base_url,
        skip_ablation=True,  # E1 is a single resident run; no attribution needed to mint
    )
    e1_run_id = next(r["run_id"] for r in s1_ledger.rows() if r["kind"] == "run_config")
    e1_oracle = next(
        r["oracle"] for r in s1_ledger.rows()
        if r["kind"] == "branch_run" and r["branch_id"] == RESIDENT_BRANCH
    )
    s1_ledger.write({
        "kind": "session", "session_id": s1_id, "store_path": str(e1_path.name),
        "prior_session_id": None, "wall_clock_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "resident_config_digest": digest, "memory_isolation": "minimal_harness",
        "episode_id": ep1.episode_id,
    })

    # ---- Mint (Wall B): the harness derives the earned record from the trace.
    # The corpus is loaded from the scored row itself inside the mint, not handed
    # in here — caller-supplied content cannot enter the earned record.
    earned = mint_earned_record(
        s1_ledger.rows(), RESIDENT_BRANCH,
        session_id=s1_id, source_run_id=e1_run_id,
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    if earned is None:
        raise RuntimeError(
            f"{chain_id}: no earned record minted from E1's trace (Wall B fail-closed) — "
            f"the resident branch's outcome (oracle={e1_oracle.get('score')}, "
            f"source={e1_oracle.get('source')}) did not resolve to a scored, world-checked "
            "failure with an unchanged corpus. The chain has nothing to inherit; RS-1 cannot start."
        )

    # ---- Session 2 (E2): two-branch fork differing ONLY by the earned record.
    base_ids = frozenset(r.record_id for r in ep2.records)
    ep2.records.append(earned)
    ep2.m2_earned_record_id = earned.record_id
    top_k_e2 = len(ep2.records)  # cover all eligible records: earned is additive, never displacing
    resident_inherited = frozenset(base_ids | {earned.record_id})

    s2_resident_sidecar = runs_dir / f"{chain_id}.s2.resident.authority.json"
    s2_control_sidecar = runs_dir / f"{chain_id}.s2.control.authority.json"
    for p in (s2_resident_sidecar, s2_control_sidecar):
        if p.exists():
            p.unlink()
    s2_ledger = Ledger(runs_dir / f"{chain_id}-s2.jsonl")
    if s2_ledger.path.exists():
        s2_ledger.path.unlink()
    branches_e2 = [
        BranchConfig(
            RESIDENT_BRANCH, memory="governed", authority_path=str(s2_resident_sidecar),
            inherited_record_ids=resident_inherited, top_k=top_k_e2, **common,
        ),
        BranchConfig(
            CONTROL_BRANCH, memory="governed", authority_path=str(s2_control_sidecar),
            inherited_record_ids=base_ids, top_k=top_k_e2, **common,
        ),
    ]
    res2 = run_fork_group(
        ep2, branches_e2, s2_ledger,
        engine_backend=engine_backend, model=model, base_url=base_url,
    )
    s2_ledger.write({
        "kind": "session", "session_id": s2_id, "store_path": str(e2_path.name),
        "prior_session_id": s1_id, "wall_clock_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "resident_config_digest": digest, "memory_isolation": "minimal_harness",
        "episode_id": ep2.episode_id,
    })
    # The earned record, made auditable in the fork ledger (provenance for RS-U1).
    s2_ledger.write({"kind": "earned_record", **earned.__dict__})
    s2_ledger.write({
        "kind": "m2_run_meta",
        "chain_id": chain_id,
        "s1_session_id": s1_id, "s2_session_id": s2_id,
        "e1_episode_id": ep1.episode_id, "e2_episode_id": ep2.episode_id,
        "s1_ledger": str(s1_ledger.path.relative_to(ROOT)),
        "earned_record_id": earned.record_id,
        "mint_basis": earned.provenance["mint_basis"],
        "resident_branch": RESIDENT_BRANCH, "control_branch": CONTROL_BRANCH,
        "base_inherited": sorted(base_ids),
        "resident_inherited": sorted(resident_inherited),
        "resident_config_digest": digest,
    })

    print(f"{chain_id}: S1 resident oracle={e1_oracle.get('score')} (source={e1_oracle.get('source')})")
    print(f"  minted {earned.record_id} [{earned.provenance['mint_basis']}]")
    print(f"  S2 fork scores={res2['scores']}  (RS-resident vs RS-control)")
    print(f"  S2 ledger: {s2_ledger.path}")
    return s2_ledger.path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("e1", nargs="?", help="E1 (session-1) episode JSON")
    p.add_argument("e2", nargs="?", help="E2 (session-2) episode JSON")
    p.add_argument("--wire-all", action="store_true", help="run every M2 chain on mock (structural)")
    p.add_argument("--engine", default="mock", choices=["mock", "claude", "local"])
    p.add_argument("--model", default="claude-opus-4-8")
    p.add_argument("--base-url", default="http://localhost:1234/v1")
    p.add_argument("--runs-dir", default=str(ROOT / "runs" / "m2"))
    args = p.parse_args()

    runs_dir = Path(args.runs_dir)
    if args.wire_all:
        targets = [(M2_DIR / e1, M2_DIR / e2) for e2, e1 in M2_CHAINS.items()]
    elif args.e1 and args.e2:
        targets = [(Path(args.e1), Path(args.e2))]
    else:
        print("need E1 and E2 episode paths, or --wire-all", file=sys.stderr)
        return 1

    ok = 0
    for e1_path, e2_path in targets:
        try:
            run_resident_chain(
                e1_path, e2_path,
                engine_backend=args.engine, model=args.model, base_url=args.base_url,
                runs_dir=runs_dir,
            )
            ok += 1
        except Exception as e:
            print(f"FAIL {e1_path.name} -> {e2_path.name}: {e}", file=sys.stderr)
    print(f"\nM2 chain wire: {ok}/{len(targets)}")
    return 0 if ok == len(targets) else 1


if __name__ == "__main__":
    sys.exit(main())
