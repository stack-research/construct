"""SPEC_X2 scorer — prune is an organ only where it lowers cost the offer gate
cannot move, at a world-checked quality FLOOR. Scored on cost at matched quality
(the scoring-axis law), never answer-flip. Fail-closed, one verdict per cell
(mirrors score_decay.py / score_resident.py).

The win axis is hot-store cost (hot_tokens primary); answer quality is a FLOOR and
a loses-cell, never the win leg. Attribution: A/B/C differ only in prune policy
(fork identity — same engine/episode/offer-gates), and cost replays purely from the
prune/rematerialize rows (the hot_store_cost rows are a materialization of them).
Mock rows are wire tests, never evidence.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .ledger import Ledger

ROOT = Path(__file__).resolve().parent.parent

# Config fields that must be identical across A/B/C (fork identity); the ONLY
# permitted difference is inherited_record_ids — i.e. the hot set the prune policy evolves.
_FORK_IDENTITY_KEYS = ("memory", "top_k", "recency_weight", "similarity_backend", "eligibility_threshold")


def score_prune(ledger_path: str | Path) -> list[dict]:
    rows = Ledger(Path(ledger_path)).rows()
    meta = next((r for r in rows if r["kind"] == "x2_run_meta"), None)
    if meta is None:
        raise ValueError(f"{ledger_path}: no x2_run_meta row — not an X2 run")
    A, B, C = meta["branches"]["no_prune"], meta["branches"]["closed_loop"], meta["branches"]["oracle_gated"]

    run_ids = [r["run_id"] for r in rows if r["kind"] == "run_config"]
    backend = next(r["engine_backend"] for r in rows if r["kind"] == "run_config")

    quality: dict[str, dict[str, float]] = {A: {}, B: {}, C: {}}
    cost: dict[str, dict[str, int]] = {A: {}, B: {}, C: {}}
    source: dict[str, str] = {}
    for r in rows:
        if r["kind"] == "branch_run" and r["branch_id"] in quality:
            quality[r["branch_id"]][r["run_id"]] = r.get("oracle", {}).get("score", 0.0)
            source[r["branch_id"]] = r.get("oracle", {}).get("source", "authored")
        elif r["kind"] == "hot_store_cost" and r["branch_id"] in cost:
            cost[r["branch_id"]][r.get("run_id")] = r.get("hot_tokens", 0)

    # ---- Preconditions: fork identity (only inherited_record_ids may differ) + cost present.
    fork_ok = True
    for rid in run_ids:
        rc = next((r for r in rows if r["kind"] == "run_config" and r["run_id"] == rid), None)
        if not rc:
            continue
        bys = {b["branch_id"]: b for b in rc["branches"]}
        if not {A, B, C} <= set(bys):
            fork_ok = False; break
        for k in _FORK_IDENTITY_KEYS:
            if len({bys[A].get(k), bys[B].get(k), bys[C].get(k)}) != 1:
                fork_ok = False; break
    cost_present = all(rid in cost[A] and rid in cost[B] and rid in cost[C] for rid in run_ids)
    attribution_ok = fork_ok and cost_present

    a_cost = sum(cost[A].values()); b_cost = sum(cost[B].values()); c_cost = sum(cost[C].values())
    a_q = sum(quality[A].values())

    disclosures = []
    if backend == "mock":
        disclosures.append("engine_backend=mock: wire test of the machinery, NOT evidence about a resident")
    base = {"kind": "cell_verdict", "scorer": "score_prune", "engine_backend": backend,
            "corpus_scope": "synthetic mock fixture" if backend == "mock"
            else "single sequence; out-of-weights fixture; hot_tokens cost",
            "disclosures": disclosures}
    verdicts: list[dict] = []

    # ---- X2-win: C matches A quality every episode AND C cheaper than A, attribution clean.
    floor_holds = all(quality[C].get(rid, 0.0) >= quality[A].get(rid, 0.0) for rid in run_ids)
    c_cheaper = c_cost < a_cost
    if not attribution_ok:
        win = "confounded"
    elif not floor_holds:
        win = "quality_erosion"          # C bought cost by dropping below A's quality — refused
    elif not c_cheaper:
        win = "not_engaged"              # no cost to save (the gate should have caught this)
    else:
        win = "pass"
    verdicts.append({**base, "cell": "X2-win", "verdict": win,
                     "cost_hot_tokens": {A: a_cost, B: b_cost, C: c_cost},
                     "quality_sum": {A: a_q, B: sum(quality[B].values()), C: sum(quality[C].values())},
                     "quality_floor_holds": floor_holds, "c_cheaper_than_a": c_cheaper,
                     "attribution_ok": attribution_ok})

    # ---- X2-overprune (loses-cell): a branch went cheaper than A but its quality fell
    # below A on some episode — pruning dropped a record it could not recover.
    b_fell = any(quality[B].get(rid, 0.0) < quality[A].get(rid, 0.0) for rid in run_ids)
    overprune = "pass" if (b_fell and b_cost < a_cost) else "not_engaged"
    verdicts.append({**base, "cell": "X2-overprune", "verdict": overprune,
                     "branch": B, "fell_below_A": b_fell, "cheaper_than_A": b_cost < a_cost})

    # ---- X2-quality-erosion (loses-cell): C cheaper but its quality dipped below A —
    # the floor must REFUSE the cost win. (On a sound run C holds the floor -> not_engaged.)
    erosion_present = c_cheaper and not floor_holds
    verdicts.append({**base, "cell": "X2-quality-erosion",
                     "verdict": "pass" if erosion_present else "not_engaged",
                     "note": "floor refuses C's cost win" if erosion_present else "C held the floor"})

    # ---- X2-U1: the quality floor must be world-checked (source != authored) on the
    # real run. Authored (mock) leaves the world leg unexercised -> not_engaged.
    src = source.get(A, "authored")
    if backend == "mock" or src == "authored":
        u1 = "not_engaged"
    else:
        u1 = "pass" if src != "authored" else "fail"
    verdicts.append({**base, "cell": "X2-U1", "verdict": u1, "oracle_source": src})

    return verdicts


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m harness.score_prune runs/x2/<seq>.x2.jsonl", file=sys.stderr)
        return 1
    ledger_path = Path(sys.argv[1])
    verdicts = score_prune(ledger_path)
    out = ledger_path.with_suffix(".verdicts.jsonl")
    led = Ledger(out)
    for v in verdicts:
        led.write(v)
    for v in verdicts:
        extra = ""
        if v["cell"] == "X2-win":
            extra = f"  cost A/B/C={list(v['cost_hot_tokens'].values())}  floor={v['quality_floor_holds']}"
        print(f"{v['cell']:18s} {v['verdict']:16s}{extra}")
    if any("mock" in d for v in verdicts for d in v["disclosures"]):
        print("\nDISCLOSED: engine_backend=mock — machinery wire test, not evidence.")
    print(f"verdicts -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
