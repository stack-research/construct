"""PRF fork runner — SPEC_PAUSE_RESUME v0.1 §1/§2 machinery (mock engine).

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

Mock runs are wire tests, never evidence about resumability — disclosed in the
run_config row. Real-engine runs are gated behind `check_prf_fixture` and the
§6 disclosure debt.

Episode fixture shape (episodes/prf/*.json):
  {"episode_id", "seam_id", "world_leg": moved|stale|silent,
   "t0_texts": {surface_id: text}, "t1_texts": {...},
   "witness_route": [surface_id, ...],          # pre-seam, gappy
   "frontier_state": {...},                     # D1-legal, provenance-cited
   "routes": {"cold_reread": [...], "resumable_state": [...]},
   "reopen": null | {reopen_rule_id, reopen_reason,
                     invalidating_surface_ids, read_index_at_reopen},
   "oracle": {"cold_reread": bool, "resumable_state": bool},
   "ballast": {"derived_obligation_tokens": int}}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .check_prf_fixture import check_manifest
from .derive_live_obligations import DerivationRefused, derive_live_obligations
from .ledger import Ledger
from .mint_frontier_state import (MintRefusal, freeze_validate, manifest_hash,
                                  offer_gate)
from .prf_ablation import ADEQUACY_DEBT_DISCLOSURE, structural_dependency
from .score_prf import PRFScorer, _tokens

REPO = Path(__file__).resolve().parent.parent


def _witness_reads(episode: dict, population: dict) -> list[dict]:
    catalog = population["catalog"]
    return [{"kind": "surface_read", "branch": "uninterrupted_warm",
             "surface_id": sid, "read_index": i, "catalog_epoch": "t0",
             "content_hash": catalog[sid]["content_hash_t0"],
             "surface_tags": catalog[sid]["surface_tags"]}
            for i, sid in enumerate(episode["witness_route"])]


def run_fork_group(episode: dict, population: dict, freeze_manifest: dict,
                   ledger: Ledger) -> dict:
    """One fork group, canonical order, every row harness-stamped."""
    ledger.write({"kind": "run_config", "engine": "mock", "wire_test": True,
                  "episode_id": episode["episode_id"],
                  "disclosure": "mock fork runner — machinery wire, never "
                                "evidence about resumability (SPEC §12)",
                  "adequacy_debt": ADEQUACY_DEBT_DISCLOSURE})
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

    # phase 1: freeze-time structural mint (does NOT mint — §4c two-phase pin)
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

    # seam -> symmetric post-seam catalog for ALL branches
    ledger.write({"kind": "post_seam_catalog_materialized",
                  "surfaces": sorted(population["catalog"]),
                  "disclosure": "symmetric: all branches receive the t1 "
                                "catalog (SPEC §2)"})

    # phase 2: OFFER-TIME content floor (§4c-1 leg 1 / §4c-2). Cold's
    # checkpoint cost and the ablation replay exist only now. The structural-
    # dependency leg is COMPUTED here (never read from the episode — the
    # build review killed the attested flag); the empirical-adequacy leg is
    # the disclosed real-engine debt in run_config.
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

    # resume routes: fixture-scripted deterministic prefix plans
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

    # world-oracle outcomes (fixture-declared on mock; R5: never narration)
    for branch, ok in episode["oracle"].items():
        ledger.write({"kind": "branch_outcome", "branch": branch,
                      "quality_ok": bool(ok), "oracle_source": "fixture_mock"})
    return {"halted": None, "minted": minted["state_digest"]}


def run_and_score(episode_path: Path, ledger_path: Path | None = None) -> dict:
    episode = json.loads(episode_path.read_text())
    fixture_dir = episode_path.parent
    population = json.loads((fixture_dir / "population.json").read_text())
    freeze_manifest = json.loads(
        (fixture_dir / "freeze_manifest.json").read_text())
    ledger_path = ledger_path or (
        REPO / "runs" / "prf" / f"{episode['episode_id']}.jsonl")
    if ledger_path.exists():
        ledger_path.unlink()   # a wire ledger regenerates fresh each run
    ledger = Ledger(ledger_path)

    # self-gating (fix #9, X2 pattern): the run re-executes the §9 admission
    # gate and ledgers the computed gate_open row; the scorer requires it for
    # any non-mock verdict. A refused gate halts the fork before any row.
    gate_checks = check_manifest(fixture_dir / "manifest.json")
    gate_failed = [name for name, ok, _ in gate_checks if not ok]
    if gate_failed:
        ledger.write({"kind": "gate_refused", "failed": gate_failed})
        return {"run": {"halted": "gate_refused", "failed": gate_failed},
                "verdict": None, "ledger": str(ledger_path)}
    ledger.write({"kind": "gate_open", "checks": len(gate_checks),
                  "manifest": str(fixture_dir / "manifest.json")})

    outcome = run_fork_group(episode, population, freeze_manifest, ledger)
    events = ledger.rows()
    scorer = PRFScorer(population, freeze_manifest, events,
                       episode["t0_texts"], episode["t1_texts"])
    verdict = scorer.score()
    # harness-emitted checkpoint rows (fix #10) — from the scorer's own
    # branch-blind computation, never branch narration
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
    ap = argparse.ArgumentParser(description="PRF mock fork runner (wire only)")
    ap.add_argument("episode", help="episodes/prf/<fixture>/<episode>.json")
    args = ap.parse_args()
    out = run_and_score(Path(args.episode))
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["verdict"]["cell"] != "confounded" else 1


if __name__ == "__main__":
    sys.exit(main())
