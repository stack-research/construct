"""SPEC_M2 resident-substrate scorer — the fork decides use, not the testimony.

Computes RS-1 / RS-loses / RS-stale / RS-U1 from an S2 fork ledger and the S1
ledger it chains to. Preconditions are asserted BEFORE any cell scores and fail
closed (cursor's predicate table + codex's digest/chain-link + kagi's both-ends
world check):

  - chain link      : S2.session.prior_session_id resolves to S1.session_id
  - cold identity    : S1 and S2 carry the same resident_config_digest, and the
                       two E2 branches share their controlled surface (differ only
                       in the inherited store + authority sidecar)
  - earned binding   : m2_run_meta.earned_record_id is the record under test
  - offer-set isolation: offers(resident) symdiff offers(control) == {earned}
  - memory isolation : both sessions attest minimal_harness | scrubbed

The resident's narration is never read. `used` is computed only from the fork:
divergence, a better world-scored outcome, and branch-A ablation load-bearing.

Usage:
  python -m harness.score_resident runs/m2/rs-s2.jsonl episodes/m2/rs-e2.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .ledger import Ledger

REPO = Path(__file__).resolve().parent.parent

# Controlled-surface fields the two E2 branches MUST share (fork identity); the
# memory condition (inherited store) and its sidecar are the only legal diffs.
SURFACE_FIELDS = ("memory", "top_k", "recency_weight", "similarity_backend",
                  "eligibility_threshold", "live_input_yield", "supersession_policy")


def _one(rows: list[dict], kind: str) -> dict | None:
    found = [r for r in rows if r.get("kind") == kind]
    return found[-1] if found else None


def _session(rows: list[dict]) -> dict | None:
    return _one(rows, "session")


def _offers(rows: list[dict], branch: str) -> set[str]:
    return {r["record_id"] for r in rows if r.get("kind") == "offer" and r.get("branch_id") == branch}


def _diff_outcome(rows: list[dict], a: str, b: str) -> dict | None:
    for r in rows:
        if r.get("kind") == "diff_outcome" and set(r.get("branches", [])) == {a, b}:
            return r
    return None


def _ablation_changed(rows: list[dict], branch: str, record_id: str) -> bool | None:
    """True/False if an ablation_run row exists for (branch, record_id); None if none."""
    hits = [
        r for r in rows
        if r.get("kind") == "ablation_run" and r.get("branch_id") == branch
        and r.get("ablated_record_id") == record_id
    ]
    return hits[-1]["outcome_changed"] if hits else None


def check_preconditions(s2: list[dict], s1: list[dict], meta: dict) -> dict[str, Any]:
    res, ctrl = meta["resident_branch"], meta["control_branch"]
    earned = meta["earned_record_id"]
    s2_sess, s1_sess = _session(s2), _session(s1)
    cfg = _one(s2, "run_config")

    checks: dict[str, Any] = {}

    # chain link
    checks["chain_link"] = bool(
        s2_sess and s1_sess and s2_sess.get("prior_session_id") == s1_sess.get("session_id")
        and s1_sess.get("session_id") == meta.get("s1_session_id")
    )

    # cold identity: same digest across the seam, and branches share the surface
    digest_ok = bool(s1_sess and s2_sess
                     and s1_sess.get("resident_config_digest")
                     and s1_sess["resident_config_digest"] == s2_sess.get("resident_config_digest"))
    surface_ok = False
    if cfg:
        branches = {b["branch_id"]: b for b in cfg.get("branches", [])}
        if res in branches and ctrl in branches:
            surface_ok = all(branches[res].get(f) == branches[ctrl].get(f) for f in SURFACE_FIELDS)
    checks["cold_identity"] = digest_ok and surface_ok

    # memory isolation attested on both sessions
    checks["memory_isolation"] = bool(
        s2_sess and s1_sess
        and s2_sess.get("memory_isolation") in ("minimal_harness", "scrubbed")
        and s1_sess.get("memory_isolation") in ("minimal_harness", "scrubbed")
    )

    # earned binding: the named earned record is in the resident store, not the control
    checks["earned_binding"] = bool(
        earned and earned in set(meta.get("resident_inherited", []))
        and earned not in set(meta.get("base_inherited", []))
    )

    # offer-set isolation (symmetric-difference): earned is the ONLY record that
    # differs across the fork, in either direction (no fixed-budget displacement).
    sym = _offers(s2, res) ^ _offers(s2, ctrl)
    checks["offer_set_isolation"] = (sym == {earned})
    checks["_offer_symdiff"] = sorted(sym)

    checks["ok"] = all(v for k, v in checks.items() if not k.startswith("_"))
    return checks


def score_rs1(s2: list[dict], meta: dict) -> dict[str, Any]:
    res, ctrl = meta["resident_branch"], meta["control_branch"]
    earned = meta["earned_record_id"]
    dout = _diff_outcome(s2, res, ctrl)
    if not dout:
        return {"verdict": "fail", "evidence": {"error": "no diff_outcome for the fork pair"}}
    r_score = dout["oracle_scores"][res]["score"]
    c_score = dout["oracle_scores"][ctrl]["score"]
    diverged = dout["diverged"]
    load_bearing = _ablation_changed(s2, res, earned)
    evidence = {
        "diverged": diverged, "resident_oracle": r_score, "control_oracle": c_score,
        "earned_record_id": earned, "earned_load_bearing": load_bearing,
        "e2_oracle_source": dout["oracle_scores"][res].get("source"),
    }
    if c_score >= 1.0:
        return {"verdict": "not_engaged", "evidence": {
            **evidence, "note": "control reached the world-correct decision without the earned record — lesson not needed here"}}
    if diverged and r_score > c_score and load_bearing:
        return {"verdict": "pass", "evidence": evidence}
    # which leg failed, made explicit (fail-closed)
    why = []
    if not diverged:
        why.append("branches did not diverge")
    if not r_score > c_score:
        why.append("resident not better than control (R3: acted-different != acted-better)")
    if not load_bearing:
        why.append("earned record not ablation-load-bearing (recalled != load-bearing)"
                   if load_bearing is False else "no ablation row for the earned record on the resident")
    return {"verdict": "fail", "evidence": {**evidence, "why": why}}


def score_rsU1(s2: list[dict], meta: dict, rs1: dict, earned_row: dict | None) -> dict[str, Any]:
    """Un-authored close-gate: RS-1 holds AND both ends are world-checked."""
    e1_world = bool(earned_row and earned_row.get("provenance", {}).get("mint_basis") == "world_correction")
    e2_source = rs1["evidence"].get("e2_oracle_source")
    e2_world = e2_source not in (None, "authored")
    evidence = {"e1_world_checked": e1_world, "e1_mint_basis": (earned_row or {}).get("provenance", {}).get("mint_basis"),
                "e2_world_checked": e2_world, "e2_oracle_source": e2_source, "rs1_verdict": rs1["verdict"]}
    if rs1["verdict"] == "not_engaged":
        return {"verdict": "not_engaged", "evidence": {**evidence, "note": "RS-1 not engaged; nothing to close-gate"}}
    if rs1["verdict"] != "pass":
        return {"verdict": "fail", "evidence": {**evidence, "note": "RS-1 did not pass"}}
    if e1_world and e2_world:
        return {"verdict": "pass", "evidence": evidence}
    return {"verdict": "fail", "evidence": {
        **evidence, "error": "RS-1 passed but a chain end is authored — better against our oracle, not the world (W1' one level up)"}}


def _claimed_use(s2: list[dict], branch: str, earned: str) -> bool:
    """Did the resident NARRATE using the earned record (L3 elicitation)? Audit
    input for RS-loses only — never a pass condition, only the claim to refuse."""
    for r in s2:
        if r.get("kind") == "branch_run" and r.get("branch_id") == branch:
            for c in r.get("agent_claimed_usage", []):
                if c.get("record_id") == earned and c.get("claimed") not in (None, "unused", "none"):
                    return True
    return False


def score_rs_loses(s2: list[dict], meta: dict, rs1: dict) -> dict[str, Any]:
    """Performed continuity: a claim of use the fork says is not load-bearing.
    Needs an elicited continuity claim (L3) to refuse — else it is RS-passenger,
    the null, not the loses-cell."""
    claimed = _claimed_use(s2, meta["resident_branch"], meta["earned_record_id"])
    load_bearing = rs1["evidence"].get("earned_load_bearing")
    evidence = {"claimed_use": claimed, "earned_load_bearing": load_bearing}
    if not claimed:
        return {"verdict": "not_engaged", "evidence": {
            **evidence, "note": "no elicited continuity claim (governed lane, not construct_aware) — needs a performed-continuity chain"}}
    if load_bearing is False:
        return {"verdict": "pass", "evidence": {**evidence, "note": "claimed continuity refused by the fork (not load-bearing)"}}
    return {"verdict": "fail", "evidence": {**evidence, "note": "claim of use was in fact load-bearing — not performed continuity"}}


def score_rs_stale(s2: list[dict], meta: dict, episode: dict) -> dict[str, Any]:
    """Continuity-as-authority: the store overruled by fresher reality. Engaged
    only by a stale-veto chain (live_input_outranks_stale_memory)."""
    cond = episode.get("expected_winner_condition")
    if cond != "live_input_outranks_stale_memory":
        return {"verdict": "not_engaged", "evidence": {
            "note": "not a stale-veto chain — needs a reinstated/superseded finding + live_input_yield",
            "expected_winner_condition": cond}}
    # The mechanism reuses select_offers Gate 2 (yields_to_live_input); a dedicated
    # stale-veto episode wires it. Computed there, tagged oracle_basis at scoring.
    return {"verdict": "fail", "evidence": {"error": "stale-veto chain present but RS-stale scorer leg not yet wired"}}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("s2_ledger", help="the E2 fork ledger (carries m2_run_meta)")
    p.add_argument("episode", help="the E2 episode JSON")
    args = p.parse_args()

    s2 = Ledger(Path(args.s2_ledger))
    s2_rows = s2.rows()
    episode = json.loads(Path(args.episode).read_text())
    meta = _one(s2_rows, "m2_run_meta")
    if not meta:
        print("no m2_run_meta in the S2 ledger — not a resident-substrate chain", file=sys.stderr)
        return 1
    cfg = _one(s2_rows, "run_config")
    if any(r.get("kind") == "cell_verdict" and r.get("fork_group_id") == cfg["fork_group_id"] for r in s2_rows):
        print("fork group already scored (append-only); nothing written", file=sys.stderr)
        return 0
    s1_rows = [json.loads(l) for l in (REPO / meta["s1_ledger"]).read_text().splitlines() if l.strip()]
    wire_test = cfg.get("engine_backend") == "mock"

    pre = check_preconditions(s2_rows, s1_rows, meta)
    earned_row = _one(s2_rows, "earned_record")
    corpus_id = (earned_row or {}).get("provenance", {}).get("source_oracle", {}).get("corpus_entry", "?")
    corpus_scope = f"one_hop: S1->S2; one_retraction: {Path(str(corpus_id)).stem}"

    if pre["ok"]:
        rs1 = score_rs1(s2_rows, meta)
        rsU1 = score_rsU1(s2_rows, meta, rs1, earned_row)
        rsloses = score_rs_loses(s2_rows, meta, rs1)
        rsstale = score_rs_stale(s2_rows, meta, episode)
        cells = {"RS-1": rs1, "RS-loses": rsloses, "RS-stale": rsstale, "RS-U1": rsU1}
    else:
        failed = [k for k, v in pre.items() if not k.startswith("_") and k != "ok" and not v]
        fail = {"verdict": "fail", "evidence": {"error": "precondition(s) failed", "failed": failed,
                                                "offer_symdiff": pre["_offer_symdiff"]}}
        cells = {c: fail for c in ("RS-1", "RS-loses", "RS-stale", "RS-U1")}

    wrote = []
    for cell, result in cells.items():
        row = {
            "kind": "cell_verdict", "cell": cell,
            "episode_id": episode["episode_id"],
            "chain_id": meta["chain_id"], "fork_group_id": cfg["fork_group_id"],
            "engine_backend": cfg["engine_backend"], "model": cfg["model"],
            "wire_test": wire_test,
            "preconditions": {k: v for k, v in pre.items() if not k.startswith("_")},
            "corpus_scope": corpus_scope,
            **result,
        }
        s2.write(row)
        wrote.append(row)
        print(json.dumps({"cell": cell, "verdict": result["verdict"], "wire_test": wire_test}, sort_keys=True))

    print("\n" + json.dumps({r["cell"]: r["verdict"] for r in wrote}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
