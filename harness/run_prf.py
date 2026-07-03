"""PRF fork runner — SPEC_PAUSE_RESUME v0.1 §1/§2/§6 machinery.

Executes one fork group end-to-end in the canonical event order:

  population_precommit -> witness (t0) reads -> derive_live_obligations ->
  frontier_freeze (phase-1 structural mint) -> seam ->
  post_seam_catalog_materialized (symmetric) -> OFFER-TIME CONTENT FLOOR
  (phase-2: frontier_state_minted | frontier_mint_refused) -> resume routes ->
  branch outcomes

and writes every row to a JSONL ledger the scorer replays. The ledger writer
is external throughout: branches execute FIXTURE-SCRIPTED deterministic routes
(§6 determinism policy — frozen prefix plans with deterministic surface
injection; no model chooses over the catalog in a wire run), and no branch
writes its own cost or verdict.

Mock runs (`--engine mock`, default) are wire tests: fixture-declared oracle
outcomes, never evidence about resumability — disclosed in run_config.

Real-engine runs (`--engine local|claude`, or an explicit engine instance in
tests) inject canonical t1 surface texts in route order, score answers with the
authored oracle against `expected_answer_t1`, and ledger `ablation_adequacy`
(§4c-1 leg 2). Multi-sample disclosure per §6: `--samples N` (default 1);
N=1 marks single-draw win cells inadmissible in the outcome row.

Episode fixture shape (episodes/prf/*.json):
  {"episode_id", "seam_id", "world_leg": moved|stale|silent,
   "t0_texts": {surface_id: text}, "t1_texts": {...},
   "witness_route": [surface_id, ...],          # pre-seam, gappy
   "frontier_state": {...},                     # D1-legal, provenance-cited
   "routes": {"cold_reread": [...], "resumable_state": [...]},
   "reopen": null | {reopen_rule_id, reopen_reason,
                     invalidating_surface_ids, read_index_at_reopen},
   "oracle": {"cold_reread": bool, "resumable_state": bool},  # mock only
   "question": str, "expected_answer_t1": str,   # real-engine oracle
   "ballast": {"derived_obligation_tokens": int}}
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .check_prf_fixture import check_manifest
from .derive_live_obligations import DerivationRefused, derive_live_obligations
from .engine import ClaudeEngine, LocalEngine, MockEngine, build_prompt
from .ledger import Ledger
from .mint_frontier_state import (MintRefusal, freeze_validate, manifest_hash,
                                  offer_gate)
from .oracle import _norm, authored_oracle
from .prf_ablation import ADEQUACY_DEBT_DISCLOSURE, structural_dependency
from .score_prf import PRFScorer, _tokens

REPO = Path(__file__).resolve().parent.parent

# Cold ignorance probe (§9 per-engine, pre-fork). Fictional meridian corpus
# invented 2026-07-03 — markers are fixture-specific, not generic geography.
PROBE_QUESTION = (
    "What is the current commissioning status of plan R at the Meridian relay "
    "junction? Answer from your own knowledge only — no context records are "
    "provided."
)
_PRIOR_KNOWLEDGE_MARKERS = (
    "meridian relay junction status ledger",
    "plan r commissioning window pending survey confirmation",
    "plan r commissioning window now closed",
)

SINGLE_DRAW_DISCLOSURE = (
    "N=1 single-draw win cells inadmissible under §6 determinism policy "
    "(SPEC_PAUSE_RESUME §6)"
)


def _engine(engine_backend: str, model: str, base_url: str):
    if engine_backend == "claude":
        return ClaudeEngine(model)
    if engine_backend == "local":
        return LocalEngine(model, base_url=base_url)
    return MockEngine()


def _witness_reads(episode: dict, population: dict) -> list[dict]:
    catalog = population["catalog"]
    return [{"kind": "surface_read", "branch": "uninterrupted_warm",
             "surface_id": sid, "read_index": i, "catalog_epoch": "t0",
             "content_hash": catalog[sid]["content_hash_t0"],
             "surface_tags": catalog[sid]["surface_tags"]}
            for i, sid in enumerate(episode["witness_route"])]


def _frontier_foreground(canonical_state: dict) -> str:
    return (
        "Frontier artifact (schema-bound resume state, charged on every resume):\n"
        + json.dumps(canonical_state, sort_keys=True)
        + "\n\n"
    )


def _draw_samples(engine, question: str, offered: list[str],
                  foreground: str, expected: str, samples: int) -> dict:
    """N engine draws scored by authored_oracle; quality_ok = all pass."""
    sample_rows: list[dict] = []
    for i in range(samples):
        result = engine.run(question, offered, foreground_block=foreground)
        score = authored_oracle(result.answer, expected)
        sample_rows.append({
            "sample_index": i,
            "score": score.score,
            "answer_excerpt": result.answer[:240],
            "model": result.model,
            "latency_ms": result.latency_ms,
        })
    scores = [r["score"] for r in sample_rows]
    return {
        "samples": samples,
        "sample_scores": scores,
        "sample_details": sample_rows,
        "quality_ok": all(s >= 1.0 for s in scores),
        "single_draw_inadmissible": samples == 1,
        "determinism_disclosure": SINGLE_DRAW_DISCLOSURE if samples == 1 else None,
    }


def _engine_branch_outcome(engine, episode: dict, branch: str, route: list[str],
                         samples: int, canonical_state: dict | None) -> dict:
    question = episode["question"]
    expected = episode["expected_answer_t1"]
    offered = [episode["t1_texts"][sid] for sid in route]
    foreground = _frontier_foreground(canonical_state) if canonical_state else ""
    drawn = _draw_samples(engine, question, offered, foreground, expected,
                          samples)
    return {
        "kind": "branch_outcome",
        "branch": branch,
        "quality_ok": drawn["quality_ok"],
        "oracle_source": "authored_oracle:fictional_meridian",
        "oracle_type": "authored",
        "expected_answer_t1": expected,
        "injected_route": list(route),
        **drawn,
    }


def _ablation_adequacy(engine, episode: dict, ablation: dict,
                       samples: int) -> dict:
    """§4c-1 leg 2 — ablated witness through engine+oracle (real engine only)."""
    covered = set(ablation["covered_surfaces"])
    ablated_route = [sid for sid in episode["witness_route"]
                     if sid not in covered]
    offered = [episode["t0_texts"][sid] for sid in ablated_route]
    drawn = _draw_samples(
        engine, episode["question"], offered, "",
        episode["expected_answer_t1"], samples)
    return {
        "kind": "ablation_adequacy",
        "ablated_quality_ok": drawn["quality_ok"],
        "ablated_witness_route": ablated_route,
        "covered_surfaces": sorted(covered),
        "oracle_source": "authored_oracle:fictional_meridian",
        **drawn,
    }


def run_fork_group(episode: dict, population: dict, freeze_manifest: dict,
                   ledger: Ledger, *, engine=None, samples: int = 1,
                   engine_backend: str = "mock") -> dict:
    """One fork group, canonical order, every row harness-stamped."""
    wire_mock = engine is None
    cfg: dict[str, Any] = {
        "kind": "run_config",
        "engine": engine_backend if wire_mock else engine.backend_name,
        "wire_test": wire_mock,
        "episode_id": episode["episode_id"],
        "samples": samples,
        "adequacy_debt": ADEQUACY_DEBT_DISCLOSURE,
    }
    if wire_mock:
        cfg["disclosure"] = (
            "mock fork runner — machinery wire, never evidence about "
            "resumability (SPEC §12)")
    else:
        cfg["disclosure"] = (
            "real-engine fork — §6 frozen prefix plans with deterministic "
            "surface injection; oracle mints branch_outcome quality_ok")
        if samples == 1:
            cfg["determinism_disclosure"] = SINGLE_DRAW_DISCLOSURE
    ledger.write(cfg)
    ledger.write(population)

    witness = _witness_reads(episode, population)
    for row in witness:
        ledger.write(row)

    try:
        out = derive_live_obligations(population, freeze_manifest, witness,
                                      episode["seam_id"])
    except DerivationRefused as e:
        ledger.write(e.row)
        return {"halted": "derivation_refused", **e.row}
    ledger.write(out["batch"])
    for row in out["obligations"]:
        ledger.write(row)

    try:
        cand = freeze_validate(episode["frontier_state"], freeze_manifest,
                               out["batch"], manifest_hash(freeze_manifest))
    except MintRefusal as e:
        ledger.write(e.row)
        return {"halted": "frontier_mint_refused", **e.row}
    ledger.write({"kind": "frontier_freeze",
                  "canonical_state": cand["canonical_state"],
                  "state_digest": cand["state_digest"],
                  "obligation_set_hash": cand["obligation_set_hash"],
                  "seam_id": episode["seam_id"]})

    ledger.write({"kind": "post_seam_catalog_materialized",
                  "surfaces": sorted(population["catalog"]),
                  "disclosure": "symmetric: all branches receive the t1 "
                                "catalog (SPEC §2)"})

    cold_cost = sum(_tokens(episode["t1_texts"][sid])
                    for sid in episode["routes"]["cold_reread"])
    ablation = structural_dependency(population, freeze_manifest, witness,
                                     episode["seam_id"])
    try:
        minted = offer_gate(
            cand,
            derived_obligation_tokens=episode["ballast"]
                ["derived_obligation_tokens"],
            cold_reread_tokens=cold_cost, gamma=population["gamma"],
            ablation=ablation,
            frontier_artifact_id=f"fa:{episode['episode_id']}")
    except MintRefusal as e:
        ledger.write(e.row)
        return {"halted": "frontier_mint_refused", **e.row}
    ledger.write(minted)

    for branch in ("cold_reread", "resumable_state"):
        for i, sid in enumerate(episode["routes"][branch]):
            ledger.write({"kind": "surface_read", "branch": branch,
                          "surface_id": sid, "read_index": i,
                          "catalog_epoch": "t1"})
    if episode.get("reopen"):
        rule_id = episode["reopen"].get("reopen_rule_id")
        invalidated = [o["obligation_id"] for o in out["obligations"]
                       if population.get("reopen_rules", {})
                       .get(rule_id, {}).get("invalidation_predicate_id")
                       == o["satisfaction_predicate_id"]]
        ledger.write({"kind": "frontier_stale_reopen",
                      "branch": "resumable_state",
                      "population_reopen_rules_hash":
                          population["population_reopen_rules_hash"],
                      "frontier_artifact_id": minted["frontier_artifact_id"],
                      "obligation_set_hash": minted["obligation_set_hash"],
                      "frontier_state_minted_ref": {
                          "state_digest": minted["state_digest"],
                          "frontier_artifact_id":
                              minted["frontier_artifact_id"]},
                      "invalidated_obligation_ids": invalidated,
                      **episode["reopen"]})

    if wire_mock:
        for branch, ok in episode["oracle"].items():
            ledger.write({"kind": "branch_outcome", "branch": branch,
                          "quality_ok": bool(ok),
                          "oracle_source": "fixture_mock"})
    else:
        for branch in ("cold_reread", "resumable_state"):
            state = cand["canonical_state"] if branch == "resumable_state" else None
            ledger.write(_engine_branch_outcome(
                engine, episode, branch, episode["routes"][branch],
                samples, state))
        ledger.write(_ablation_adequacy(engine, episode, ablation, samples))

    return {"halted": None, "minted": minted["state_digest"]}


def run_ignorance_probe(engine, engine_label: str | None = None) -> dict:
    """Per-engine cold ignorance probe (§9) — no context, pre-fork."""
    result = engine.run(PROBE_QUESTION, [], foreground_block="")
    norm = _norm(result.answer)
    knew = any(_norm(m) in norm for m in _PRIOR_KNOWLEDGE_MARKERS)
    label = engine_label or getattr(engine, "model", engine.backend_name)
    return {
        "knew": knew,
        "engine": label,
        "backend": engine.backend_name,
        "answer_excerpt": result.answer[:320],
        "probe_question": PROBE_QUESTION,
        "note": "cold probe before fork — fold into manifest attestation",
    }


def probe_attestation_block(probe: dict) -> dict:
    """JSON block for manifest.json attestation.ignorance_probe.engines."""
    key = probe["engine"]
    return {
        "ignorance_probe": {
            "engines": {
                key: {
                    "knew": probe["knew"],
                    "note": probe["note"],
                    "answer_excerpt": probe["answer_excerpt"],
                }
            }
        }
    }


def run_and_score(episode_path: Path, ledger_path: Path | None = None,
                  *, engine=None, samples: int = 1,
                  engine_backend: str = "mock") -> dict:
    episode = json.loads(episode_path.read_text())
    fixture_dir = episode_path.parent
    population = json.loads((fixture_dir / "population.json").read_text())
    freeze_manifest = json.loads(
        (fixture_dir / "freeze_manifest.json").read_text())
    ledger_path = ledger_path or (
        REPO / "runs" / "prf" / f"{episode['episode_id']}.jsonl")
    if ledger_path.exists():
        ledger_path.unlink()
    ledger = Ledger(ledger_path)

    gate_checks = check_manifest(fixture_dir / "manifest.json")
    gate_failed = [name for name, ok, _ in gate_checks if not ok]
    if gate_failed:
        ledger.write({"kind": "gate_refused", "failed": gate_failed})
        return {"run": {"halted": "gate_refused", "failed": gate_failed},
                "verdict": None, "ledger": str(ledger_path)}
    ledger.write({"kind": "gate_open", "checks": len(gate_checks),
                  "manifest": str(fixture_dir / "manifest.json")})


    outcome = run_fork_group(
        episode, population, freeze_manifest, ledger,
        engine=engine, samples=samples, engine_backend=engine_backend)
    events = ledger.rows()
    scorer = PRFScorer(population, freeze_manifest, events,
                       episode["t0_texts"], episode["t1_texts"])
    verdict = scorer.score()
    for branch, key in (("cold_reread", "cold_checkpoint"),
                        ("resumable_state", "resumable_checkpoint")):
        idx = verdict.get("costs", {}).get(key)
        if idx is not None:
            ledger.write({"kind": "continuation_checkpoint_reached",
                          "branch": branch, "read_index": idx})
    ledger.write(verdict)
    return {"run": outcome, "verdict": verdict,
            "ledger": str(ledger_path)}


def main() -> int:
    ap = argparse.ArgumentParser(description="PRF fork runner")
    ap.add_argument("episode", nargs="?", default=None,
                    help="episodes/prf/<fixture>/<episode>.json")
    ap.add_argument("--engine", choices=("mock", "local", "claude"),
                    default="mock")
    ap.add_argument("--model", default="claude-opus-4-8",
                    help="model id (local/claude)")
    ap.add_argument("--base-url", default="http://localhost:1234/v1",
                    help="OpenAI-compatible base URL (local)")
    ap.add_argument("--samples", type=int, default=1,
                    help="answer draws per branch (real engine; §6)")
    ap.add_argument("--probe", action="store_true",
                    help="cold ignorance probe only; print attestation JSON")
    args = ap.parse_args()

    if args.probe:
        eng = _engine(args.engine, args.model, args.base_url)
        probe = run_ignorance_probe(eng, engine_label=args.model)
        block = probe_attestation_block(probe)
        print(json.dumps(block, indent=2, sort_keys=True))
        return 0

    if not args.episode:
        ap.error("episode path required unless --probe")
    if args.engine != "mock" and args.samples < 1:
        ap.error("--samples must be >= 1")

    engine = None
    if args.engine != "mock":
        engine = _engine(args.engine, args.model, args.base_url)

    out = run_and_score(
        Path(args.episode), engine=engine, samples=args.samples,
        engine_backend=args.engine)
    print(json.dumps(out, indent=2, sort_keys=True))
    if out["verdict"] is None:
        return 1
    return 0 if out["verdict"]["cell"] != "confounded" else 1


if __name__ == "__main__":
    sys.exit(main())
