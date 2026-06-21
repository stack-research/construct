"""SPEC_X2 scorer — prune is an organ only where it lowers a cost the offer gate
cannot move, at a world-checked quality FLOOR. Scored on cost at matched quality
(the scoring-axis law), never answer-flip. Fail-closed, one verdict per cell
(mirrors score_decay.py / score_resident.py).

Tier-1 hardening (thread-6 review — codex/grok/cursor + dan):
  * Cost is RECOMPUTED independently. The hot set is replayed from the immutable
    lineage (`all_record_ids` + `record_texts`) and the ordered prune/rematerialize
    rows, and `hot_tokens` recomputed from the record texts. The logged
    `hot_store_cost` rows are NOT trusted as authority — a mismatch is `confounded`.
  * Lineage is treated as immutable AND complete: any structural hole (a row
    referencing an id outside `all_record_ids`, a `record_texts` gap, a duplicated
    event_index) fails closed. There is no erase-from-lineage verb; a hole is an
    attack surface, not a measurement.
  * Fork identity: the ONLY permitted config diff across A/B/C is the hot set
    (`inherited_record_ids`) and per-branch sidecar paths — every other field of
    every branch config must be identical.
  * `primary_cost_metric` is read from the run; the scorer certifies only the
    metric it can recompute (hot_tokens).
  * X2-LB engages on a `fixture_attestation` (out-of-weights / fictional) + a
    policy-independent grader + a COMPUTED gate pass (`fixture_gate_result`); X2-U1
    stays the un-authored world close-gate — a synthetic fixture is not_engaged there.
    Every non-mock cell (X2-win/X2-LB/X2-overprune/X2-quality-erosion) fails closed
    without `gate_open` — attestation is a claim, gate passage is computed.

Mock rows are wire tests, never evidence about a resident.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .ledger import Ledger

ROOT = Path(__file__).resolve().parent.parent

# The only fields a branch config may differ on (fork identity): the hot set it
# evolves (`inherited_record_ids`) and per-branch sidecar paths. Everything else
# — memory/top_k/recency_weight/similarity_backend/eligibility/yield/supersession/
# decay flags — must be byte-identical across A/B/C, or the cost delta is not
# attributable to the prune policy alone.
_IDENTITY_EXCLUDE = frozenset({
    "branch_id", "authority_path", "inherited_record_ids", "temperature_path",
})


def _replay_hot_sets(all_ids: list, ops: list, seq_list: list) -> dict:
    """Replay per-episode hot-set SNAPSHOTS from the immutable lineage + ordered
    prune/rematerialize rows, in the runner's order: seed full, then for each episode
    apply that episode's rematerialize (pre-answer) -> snapshot -> apply that episode's
    prune (post-answer). Returns {seq_index: frozenset(hot at the cost snapshot)} — the
    one source for both the recomputed cost and the over-prune evidence."""
    hot = set(all_ids)
    by_seq: dict[int, list] = {}
    for o in ops:
        by_seq.setdefault(o["seq_index"], []).append(o)
    snaps: dict[int, frozenset] = {}
    for k in seq_list:
        ks = sorted(by_seq.get(k, []), key=lambda r: r["event_index"])
        for o in ks:
            if o["op"] == "rematerialize":
                hot.add(o["record_id"])
        snaps[k] = frozenset(hot)
        for o in ks:
            if o["op"] == "prune":
                hot.discard(o["record_id"])
    return snaps


def score_prune(ledger_path: str | Path) -> list[dict]:
    rows = Ledger(Path(ledger_path)).rows()
    meta = next((r for r in rows if r["kind"] == "x2_run_meta"), None)
    if meta is None:
        raise ValueError(f"{ledger_path}: no x2_run_meta row — not an X2 run")
    A, B, C = meta["branches"]["no_prune"], meta["branches"]["closed_loop"], meta["branches"]["oracle_gated"]
    all_ids = list(meta.get("all_record_ids", []))
    record_texts = meta.get("record_texts", {})
    metric = meta.get("primary_cost_metric") or meta.get("primary_cost") or "hot_tokens"
    backend = next((r["engine_backend"] for r in rows if r["kind"] == "run_config"), "mock")

    confound: list[str] = []

    # ---- Episode index: seq_index <- run_id, logged cost, rematerialize steps.
    seq_of_run: dict[str, int] = {}
    seq_set: set[int] = set()
    logged_cost: dict[str, dict[int, int]] = {A: {}, B: {}, C: {}}
    remat_steps: dict[str, dict[int, int]] = {A: {}, B: {}, C: {}}
    for r in rows:
        if r["kind"] == "hot_store_cost" and r["branch_id"] in logged_cost:
            k = r.get("seq_index")
            seq_set.add(k)
            seq_of_run[r.get("run_id")] = k
            logged_cost[r["branch_id"]][k] = r.get("hot_tokens", 0)
            remat_steps[r["branch_id"]][k] = r.get("rematerialize_steps", 0)
    seq_list = sorted(seq_set, key=lambda x: (x is None, x))

    # Block labels (thread-7 preflight/close split): P = predictable recurrence,
    # U = unpredictable re-need of evicted lineage. Absent (legacy/flat runs) -> None.
    block_labels = list(meta.get("block_labels") or [])

    def _block(k):
        return block_labels[k] if isinstance(k, int) and 0 <= k < len(block_labels) else None

    blocks_present = {b for k in seq_list if (b := _block(k))}

    quality: dict[str, dict[int, float]] = {A: {}, B: {}, C: {}}
    source: dict[str, dict[int, str]] = {A: {}, B: {}, C: {}}
    for r in rows:
        if r["kind"] == "branch_run" and r["branch_id"] in quality:
            k = seq_of_run.get(r.get("run_id"))
            if k is None and r.get("run_id") not in seq_of_run:
                continue
            quality[r["branch_id"]][k] = r.get("oracle", {}).get("score", 0.0)
            source[r["branch_id"]][k] = r.get("oracle", {}).get("source", "authored")

    # ---- Ops for the replay (+ structural-integrity collection).
    ops: dict[str, list] = {A: [], B: [], C: []}
    event_indices: list = []
    referenced_ids: set = set()
    for r in rows:
        if r["kind"] in ("prune", "rematerialize") and r["branch_id"] in ops:
            ops[r["branch_id"]].append(r)
            event_indices.append(r.get("event_index"))
            referenced_ids.add(r.get("record_id"))

    # ---- X2-U1 close evidence (thread-7): a record C evicted during a P-block episode
    # and rematerialized during a U-block episode — the unpredictable recurrence of
    # evicted lineage that separates a world CLOSE from a world PREFLIGHT. A P-only run
    # cannot produce this round-trip, so it cannot pass as a close ("Helix + extra steps").
    c_pruned_in_P = {o["record_id"] for o in ops[C]
                     if o["op"] == "prune" and _block(o.get("seq_index")) == "P"}
    c_remat_in_U = {o["record_id"] for o in ops[C]
                    if o["op"] == "rematerialize" and _block(o.get("seq_index")) == "U"}
    reneed_round_trip = sorted(c_pruned_in_P & c_remat_in_U)

    # ---- Lineage integrity: immutable AND complete; fail closed on any hole.
    integrity_ok = True
    if not set(all_ids) <= set(record_texts):
        integrity_ok = False; confound.append("lineage_map_incomplete")
    if not referenced_ids <= set(all_ids):
        integrity_ok = False; confound.append("op_references_unknown_record")
    if len(event_indices) != len(set(event_indices)):
        integrity_ok = False; confound.append("duplicate_event_index")

    # ---- Independent cost recompute; the logged rows are NOT trusted as authority.
    metric_supported = (metric == "hot_tokens")
    if not metric_supported:
        confound.append(f"unsupported_primary_cost_metric:{metric}")
    cost_replay_ok = integrity_ok and metric_supported
    snaps: dict[str, dict] = {A: {}, B: {}, C: {}}
    if integrity_ok and metric_supported:
        snaps = {bid: _replay_hot_sets(all_ids, ops[bid], seq_list) for bid in (A, B, C)}
        cost = {bid: {k: sum(len(record_texts[rid].split()) for rid in snaps[bid][k])
                      for k in seq_list} for bid in (A, B, C)}
        for bid in (A, B, C):
            for k in seq_list:
                if cost[bid].get(k) != logged_cost[bid].get(k):
                    cost_replay_ok = False
        if not cost_replay_ok:
            confound.append("cost_replay_mismatch")
    else:
        cost = logged_cost  # cannot certify; attribution fails below regardless

    cost_present = bool(seq_list) and all(
        k in cost[A] and k in cost[B] and k in cost[C] for k in seq_list)

    per_block_cost = {b: {bid: sum(cost[bid].get(k, 0) for k in seq_list if _block(k) == b)
                          for bid in (A, B, C)} for b in sorted(blocks_present)}

    # ---- Fork identity: only the hot set (+ sidecar paths) may differ across A/B/C.
    fork_ok = True
    for r in rows:
        if r["kind"] != "run_config":
            continue
        bys = {b["branch_id"]: b for b in r.get("branches", [])}
        if not {A, B, C} <= set(bys):
            fork_ok = False; break
        idents = {json.dumps({k: v for k, v in bys[bid].items() if k not in _IDENTITY_EXCLUDE},
                             sort_keys=True, default=str) for bid in (A, B, C)}
        if len(idents) != 1:
            fork_ok = False; break
    if not fork_ok:
        confound.append("fork_identity_violation")

    # Gate passage is COMPUTED, not claimed: a non-mock cell needs a fixture_gate_result
    # row with gate_open (attestation is not gate passage — codex/grok/cursor).
    gate = next((r for r in rows if r["kind"] == "fixture_gate_result"), None)
    gate_open = bool(gate and gate.get("gate_open"))
    gate_required_ok = (backend == "mock") or gate_open
    if backend != "mock" and not gate_open:
        confound.append("fixture_gate_not_open")

    attribution_ok = (fork_ok and cost_present and integrity_ok and cost_replay_ok
                      and metric_supported and gate_required_ok)

    a_cost = sum(cost[A].get(k, 0) for k in seq_list)
    b_cost = sum(cost[B].get(k, 0) for k in seq_list)
    c_cost = sum(cost[C].get(k, 0) for k in seq_list)
    a_q = sum(quality[A].values())

    disclosures = []
    if backend == "mock":
        disclosures.append("engine_backend=mock: wire test of the machinery, NOT evidence about a resident")
    base = {"kind": "cell_verdict", "scorer": "score_prune", "engine_backend": backend,
            "corpus_scope": "synthetic mock fixture" if backend == "mock"
            else "single sequence; out-of-weights fixture; hot_tokens cost",
            "disclosures": disclosures, "primary_cost_metric": metric}
    verdicts: list[dict] = []

    # ---- X2-win: C matches A's quality every episode AND C cheaper than A,
    # attribution clean (fork identity + lineage integrity + cost replays from rows).
    floor_holds = all(quality[C].get(k, 0.0) >= quality[A].get(k, 0.0) for k in seq_list)
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
                     "attribution_ok": attribution_ok, "cost_replay_ok": cost_replay_ok,
                     "lineage_integrity_ok": integrity_ok, "fork_identity_ok": fork_ok,
                     "rematerialize_steps_C": sum(remat_steps[C].values()),
                     "confound_reasons": sorted(set(confound))})

    # ---- X2-overprune (loses-cell): B went cheaper than A but its quality fell —
    # and the loss must POINT to a record (Tier-2 specificity, codex): name the
    # record B pruned-and-could-not-recover that the loss episode needed, and show C
    # held it (kept or rematerialized). A bare "B cheaper and worse" does not pass.
    loss_eps = [k for k in seq_list if quality[B].get(k, 0.0) < quality[A].get(k, 0.0)]
    needed_unrecovered = sorted({rid for k in loss_eps
                                 for rid in (snaps[C].get(k, frozenset()) - snaps[B].get(k, frozenset()))})
    c_via_remat = sorted({o["record_id"] for o in ops[C] if o["op"] == "rematerialize"}
                         & set(needed_unrecovered))
    b_fell = bool(loss_eps)
    # Gate-fail-closed like every other non-mock cell (codex): a loses-cell may not
    # fire on a ledger we cannot attribute — no computed gate / broken fork / bad
    # replay -> confounded, never a manufactured loss.
    if not attribution_ok:
        overprune = "confounded"
    elif b_fell and b_cost < a_cost and needed_unrecovered:
        overprune = "pass"
    else:
        overprune = "not_engaged"
    verdicts.append({**base, "cell": "X2-overprune", "verdict": overprune,
                     "branch": B, "fell_below_A": b_fell, "cheaper_than_A": b_cost < a_cost,
                     "loss_episodes": loss_eps, "pruned_unrecovered_by_B": needed_unrecovered,
                     "C_recovered_via_rematerialize": c_via_remat,
                     "rematerialize_steps_C": sum(remat_steps[C].values()),
                     "confound_reasons": sorted(set(confound))})

    # ---- X2-quality-erosion (loses-cell): C cheaper but its quality dipped below A —
    # the floor must REFUSE the cost win. (On a sound run C holds the floor.)
    erosion_present = c_cheaper and not floor_holds
    verdicts.append({**base, "cell": "X2-quality-erosion",
                     "verdict": "pass" if (erosion_present and attribution_ok) else "not_engaged",
                     "note": "floor refuses C's cost win" if erosion_present else "C held the floor"})

    # ---- X2-LB / X2-U1 (split — thread-6 review + dan's ruling). Out-of-weights gives
    # *load-bearing* (the answer cannot be sourced from weights), the admission leg for
    # the COST axis — but a fixture we authored is NOT world-grounded. So:
    #   X2-LB = load-bearing admission (synthetic ok): attested out-of-weights/fictional
    #           + policy-independent grader sequence-wide + a COMPUTED gate pass.
    #   X2-U1 = the un-authored / world-grounded close-gate (M0 vocabulary): a fictional
    #           fixture is not_engaged here; it engages only on a real external corpus.
    att = next((r for r in rows if r["kind"] == "fixture_attestation"), None)
    a_c_sources = [s for bid in (A, C) for s in source[bid].values()]
    independent = (bool(a_c_sources) and all(s != "authored" for s in a_c_sources)
                   and all(k in source[A] and k in source[C] for k in seq_list))
    fictional = bool(att and att.get("fictional"))
    oow = bool(att and att.get("out_of_weights"))
    _SYNTHETIC_SOURCES = {None, "authored", "fictional_fact", "lab_fictional_corpus"}

    if backend == "mock" or att is None:
        lb, lb_note = "not_engaged", "no fixture_attestation (mock/authored floor)"
    elif backend != "mock" and not gate_open:
        lb, lb_note = "confounded", "fixture_gate_result absent or not open — attestation is not gate passage"
    elif not (fictional or oow):
        lb, lb_note = "fail", "attestation not out-of-weights/fictional (load-bearing not guaranteed)"
    elif not independent:
        lb, lb_note = "fail", "grader not policy-independent sequence-wide"
    else:
        lb, lb_note = "pass", "out-of-weights/fictional + independent grader + gate open"
    verdicts.append({**base, "cell": "X2-LB", "verdict": lb, "note": lb_note,
                     "fictional": fictional, "out_of_weights": oow, "gate_open": gate_open,
                     "fixture_attestation": att})

    # X2-U1-preflight (thread-7 split): the world floor + non-fictional oracle path
    # PROVEN on a world run — explicitly NOT a close. Pass == the old single-cell X2-U1
    # condition (un-authored source + independent grader, gate open). A P-only world run
    # legitimately reaches here; it shakes out corpus/oracle/out-of-weights plumbing.
    a_world = bool(seq_list) and all(source[A].get(k) not in _SYNTHETIC_SOURCES for k in seq_list)
    world_floor = independent and a_world
    if backend == "mock" or att is None:
        pf, pf_note = "not_engaged", "no fixture_attestation (mock/authored floor)"
    elif fictional:
        pf, pf_note = "not_engaged", "synthetic out-of-weights fixture; world floor not exercised — see X2-LB"
    elif backend != "mock" and not gate_open:
        pf, pf_note = "confounded", "fixture_gate_result absent or not open"
    elif world_floor:
        pf, pf_note = "pass", "world floor proven (un-authored source + independent grader sequence-wide)"
    else:
        pf, pf_note = "fail", "not world-grounded (authored/synthetic source)"
    verdicts.append({**base, "cell": "X2-U1-preflight", "verdict": pf, "note": pf_note,
                     "blocks_present": sorted(blocks_present), "fixture_attestation": att})

    # X2-U1 (the world-grounded CLOSE). Beyond the preflight, a close must (a) carry both
    # a P and a U block in one fork group and (b) show the honest keep-hot region: C
    # evicted a record in P and re-needed it (rematerialized) in U — and still win cost at
    # matched quality (X2-win pass). A P-only world run is a preflight, never a close; a
    # P+U run where U never re-needs evicted lineage means the corpus was too friendly.
    has_PU = {"P", "U"} <= blocks_present
    if backend == "mock" or att is None:
        u1, u1_note = "not_engaged", "no fixture_attestation (mock/authored floor)"
    elif fictional:
        u1, u1_note = "not_engaged", "synthetic out-of-weights fixture; not world-grounded — load-bearing leg is X2-LB"
    elif backend != "mock" and not gate_open:
        u1, u1_note = "confounded", "fixture_gate_result absent or not open"
    elif not world_floor:
        u1, u1_note = "fail", "not world-grounded (authored/synthetic source) — use X2-LB or an external corpus"
    elif not has_PU:
        u1, u1_note = "not_engaged", "world preflight only — no P+U blocks; see X2-U1-preflight (not a close)"
    elif not reneed_round_trip:
        u1, u1_note = "not_engaged", "Block U never re-needed evicted lineage (no C prune-in-P / rematerialize-in-U round-trip) — corpus too friendly"
    elif win != "pass":
        u1, u1_note = "not_engaged", f"cost-at-matched-quality not established (X2-win={win}) — a close needs the cost win to hold"
    else:
        u1, u1_note = "pass", "world-grounded + P/U blocks + C re-needed evicted lineage in U, at matched quality"
    verdicts.append({**base, "cell": "X2-U1", "verdict": u1, "note": u1_note,
                     "blocks_present": sorted(blocks_present), "reneed_round_trip": reneed_round_trip,
                     "per_block_cost_hot_tokens": per_block_cost, "fixture_attestation": att})

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
            extra = (f"  cost A/B/C={list(v['cost_hot_tokens'].values())}"
                     f"  floor={v['quality_floor_holds']}  replay_ok={v['cost_replay_ok']}")
            if v["confound_reasons"]:
                extra += f"  confound={v['confound_reasons']}"
        print(f"{v['cell']:18s} {v['verdict']:16s}{extra}")
    if any("mock" in d for v in verdicts for d in v["disclosures"]):
        print("\nDISCLOSED: engine_backend=mock — machinery wire test, not evidence.")
    print(f"verdicts -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
