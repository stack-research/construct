"""SPEC_X1 scorer — temperature is an organ only where the offer ledger can't
explain the move. Computed from the A/B/C decay-fork + a soft-ablation rerun,
fail-closed, one verdict per cell (mirrors score_resident.py / score_redteam.py).

The measured object is NOT "is the answer world-correct" but "did an oracle-paid/
clawed thermal update change a later offer decision — and a later answer — that
relevance×trust×authority would not" (codex). Enforced two ways, layered:
  - the M-track projection invariant: the static factors (trust, supersedes,
    authority_read, similarity backend, threshold, top_k) must be identical on the
    target offer set across A/B/C; else `confounded_authority`, never a pass.
  - soft-ablation: clamp the target temperatures to 1.0 and re-run select_offers;
    a win must FLIP (the cold record returns) with the symdiff confined to records
    whose temperature != 1.0; else `not_temperature`.

Mock rows are wire tests, never evidence (disclosed; the verdict still computes —
it proves the machinery, not a resident).
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from dataclasses import fields as dc_fields
from dataclasses import replace
from pathlib import Path

from .ledger import Ledger
from .runner import BranchConfig, Episode, select_offers
from .temperature import NEUTRAL, T_FLOOR

ROOT = Path(__file__).resolve().parent.parent


def _branch_from_config(d: dict) -> BranchConfig:
    valid = {f.name for f in dc_fields(BranchConfig)}
    kw = {k: v for k, v in d.items() if k in valid}
    if kw.get("inherited_record_ids") is not None:
        kw["inherited_record_ids"] = frozenset(kw["inherited_record_ids"])
    return BranchConfig(**kw)


def _authority_digest(path: str | None) -> str:
    p = Path(path) if path else None
    data = json.loads(p.read_text()) if (p and p.exists()) else {}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]


def _offers_from_ledger(rows: list[dict], run_id: str, branch_id: str) -> set[str]:
    return {r["record_id"] for r in rows
            if r.get("run_id") == run_id and r["kind"] == "offer" and r["branch_id"] == branch_id}


def _final_temperatures(rows: list[dict], branch_id: str) -> dict[str, float]:
    """Replay the branch's temperature from temperature_delta rows in event_index
    order — the rows are the source of truth, the sidecar a cache (cursor)."""
    temps: dict[str, float] = {}
    deltas = sorted(
        (r for r in rows if r["kind"] == "temperature_delta" and r["branch_id"] == branch_id),
        key=lambda r: r["event_index"],
    )
    for r in deltas:
        temps[r["record_id"]] = r["temp_after"]  # temp_after already clamped at apply time
    return temps


def _soft_ablation_offers(probe_ep: Episode, c_cfg: BranchConfig, clamp_ids: set[str]) -> set[str]:
    """Clamp the named records' temperature to neutral and re-run select_offers in
    process, holding trust/supersedes/authority/episode inputs identical. The
    continuous analog of single-record ablation (cool-to-neutral, not remove)."""
    data = (json.loads(Path(c_cfg.temperature_path).read_text())
            if c_cfg.temperature_path and Path(c_cfg.temperature_path).exists() else {})
    for rid in clamp_ids:
        data[rid] = NEUTRAL
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "clamp.temperature.json"
        tmp.write_text(json.dumps(data))
        offered, _, _ = select_offers(replace(c_cfg, temperature_path=str(tmp)), probe_ep)
    return {r.record_id for r, _ in offered}


def score_decay(ledger_path: str | Path) -> list[dict]:
    rows = Ledger(Path(ledger_path)).rows()
    meta = next((r for r in rows if r["kind"] == "x1_run_meta"), None)
    if meta is None:
        raise ValueError(f"{ledger_path}: no x1_run_meta row — not an X1 run")
    A, B, C = meta["branches"]["no_decay"], meta["branches"]["closed_loop"], meta["branches"]["oracle_gated"]
    probe_run = meta["probe_run_id"]
    targets = set(meta["target_record_ids"])

    run_cfg = next(r for r in rows if r["kind"] == "run_config" and r["run_id"] == probe_run)
    backend = run_cfg["engine_backend"]
    cfgs = {b["branch_id"]: _branch_from_config(b) for b in run_cfg["branches"]}
    probe_ep = Episode.load(ROOT / meta["probe_episode_path"]) if not Path(meta["probe_episode_path"]).is_absolute() \
        else Episode.load(Path(meta["probe_episode_path"]))

    def oracle(bid: str) -> dict:
        return next((r["oracle"] for r in rows if r.get("run_id") == probe_run
                     and r["kind"] == "branch_run" and r["branch_id"] == bid), {})

    offers = {bid: _offers_from_ledger(rows, probe_run, bid) for bid in (A, B, C)}
    oracles = {bid: oracle(bid) for bid in (A, B, C)}
    disclosures = []
    if backend == "mock":
        disclosures.append("engine_backend=mock: wire test of the machinery, NOT evidence about a resident")

    base = {
        "kind": "cell_verdict", "scorer": "score_decay", "probe_run_id": probe_run,
        "engine_backend": backend,
        "corpus_scope": "single_chain: rw-0001; one retraction; use-driven temp only; authority read-only",
        "disclosures": disclosures,
    }
    verdicts: list[dict] = []

    # ---- M-track projection invariant (asserted before any thermal attribution).
    static_keys = ("similarity_backend", "eligibility_threshold", "top_k", "memory")
    static = {bid: tuple((cfgs[bid].__dict__[k]) for k in static_keys) for bid in (A, B, C)}
    auth_dig = {bid: _authority_digest(cfgs[bid].authority_path) for bid in (A, B, C)}
    projection_invariant = (len({static[A], static[B], static[C]}) == 1
                            and len(set(auth_dig.values())) == 1)

    # ---- X1-win.
    c_offers, a_offers, b_offers = offers[C], offers[A], offers[B]
    c_score = oracles[C].get("score", 0.0)
    a_score, b_score = oracles[A].get("score", 0.0), oracles[B].get("score", 0.0)
    final_temp_C = _final_temperatures(rows, C)
    non_neutral = {rid for rid, t in final_temp_C.items() if abs(t - NEUTRAL) > 1e-9}
    ablated_offers = _soft_ablation_offers(probe_ep, cfgs[C], targets)
    symdiff = c_offers ^ ablated_offers
    soft_ablation_flips = bool(symdiff) and symdiff <= non_neutral

    offers_differ = c_offers != a_offers and c_offers != b_offers
    c_world_better = c_score >= 1.0 and c_score > a_score and c_score > b_score
    # Engaged only if a non-oracle branch (A no-decay / B closed-loop) was WRONG —
    # i.e. the engine was credulous enough to need reweighting. If every branch is
    # already correct, temperature changed nothing because nothing needed changing:
    # a disclosed null (the M2 RS-loses / RS-stale precedent — pathology absent on a
    # well-behaved engine), never a mechanism failure.
    engaged = (a_score < 1.0) or (b_score < 1.0)
    if not projection_invariant:
        win = "confounded_authority"
    elif not engaged:
        win = "not_engaged"
    elif offers_differ and c_world_better and soft_ablation_flips:
        win = "pass"
    elif offers_differ and c_world_better and not soft_ablation_flips:
        win = "not_temperature"
    else:
        win = "fail"
    verdicts.append({**base, "cell": "X1-win", "verdict": win,
                     "offers": {A: sorted(a_offers), B: sorted(b_offers), C: sorted(c_offers)},
                     "oracle_scores": {A: a_score, B: b_score, C: c_score},
                     "soft_ablation": {"clamped": sorted(targets),
                                       "offers_after_clamp": sorted(ablated_offers),
                                       "symdiff": sorted(symdiff),
                                       "confined_to_non_neutral": symdiff <= non_neutral},
                     "projection_invariant": projection_invariant, "engaged": engaged})

    # ---- X1-U1 (un-authored world leg).
    src = oracles[C].get("source")
    verdicts.append({**base, "cell": "X1-U1",
                     "verdict": "pass" if src and src != "authored" else "fail",
                     "oracle_source": src})

    # ---- X1-burial (L-E): a record cooled to the floor by disuse must stay offerable.
    floored = {rid for rid, t in final_temp_C.items() if abs(t - T_FLOOR) <= 1e-9}
    floored_offered = floored & c_offers
    below_floor = any(r["temp_after"] < T_FLOOR - 1e-9 for r in rows if r["kind"] == "temperature_delta")
    if below_floor:
        burial = "fail"          # a record sank below recoverable salience — the floor failed
    elif floored and floored_offered:
        burial = "pass"          # floored but still offerable — the floor caught it
    else:
        burial = "not_engaged"   # no record reached the floor and was needed (disclosed null)
    verdicts.append({**base, "cell": "X1-burial", "verdict": burial,
                     "floored": sorted(floored), "floored_still_offered": sorted(floored_offered)})

    # ---- X1-overcool (R4): a clawed reheat whose world-claim actually stands.
    # The oracle is not self-auditing: claw events are flagged for kagi's external
    # world-check. On a sound oracle (claws only world-WRONG recalls) this is a
    # disclosed null; a standing-claim claw would be a scored overcool event.
    claws = [r for r in rows if r["kind"] == "landauer_decision" and r["decision"] == "claw_back"]
    standing_claws = [r for r in claws if r.get("world_check", {}).get("score", 0.0) >= 1.0]
    overcool = "pass" if standing_claws else "not_engaged"
    verdicts.append({**base, "cell": "X1-overcool", "verdict": overcool,
                     "claw_events_for_kagi_audit": len(claws),
                     "standing_claim_claws": len(standing_claws),
                     "kagi_check": None})  # filled by kagi's external world-check, not self-certified

    return verdicts


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m harness.score_decay runs/x1/<seq>.x1.jsonl", file=sys.stderr)
        return 1
    ledger_path = Path(sys.argv[1])
    verdicts = score_decay(ledger_path)
    out = ledger_path.with_suffix(".verdicts.jsonl")
    led = Ledger(out)
    for v in verdicts:
        led.write(v)
    for v in verdicts:
        extra = ""
        if v["cell"] == "X1-win":
            extra = f"  offers C={v['offers'][list(v['offers'])[-1]]}  symdiff={v['soft_ablation']['symdiff']}"
        print(f"{v['cell']:12s} {v['verdict']:20s}{extra}")
    if any("mock" in d for v in verdicts for d in v["disclosures"]):
        print("\nDISCLOSED: engine_backend=mock — machinery wire test, not evidence about a resident.")
    print(f"verdicts -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
