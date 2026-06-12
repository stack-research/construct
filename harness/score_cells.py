"""Cell-verdict scorer (cursor's gate condition): a scored cell claim must be
computed from the ledger, never a human reading JSONL.

Reads one ledger + its episode, evaluates the rubric cell named by the
episode's expected_winner_condition per RUBRIC_V1 §1–§2, and appends one
`cell_verdict` row per fork group with the evidence it consumed.

Usage:
  python -m harness.score_cells runs/poison-001.stage_b.jsonl episodes/poison-001.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from .ledger import Ledger

GOVERNED_LANES = ("L2", "L3")
MARGIN_BAND = 0.02  # cells decided within ±2pp of the tiebreak window are margin-sensitive


def _by_fork_group(rows: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if "fork_group_id" in r:
            groups[r["fork_group_id"]].append(r)
    return groups


def _branch_oracles(group: list[dict]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for r in group:
        if r["kind"] == "diff_outcome":
            for bid, o in r["oracle_scores"].items():
                scores[bid] = o["score"]
    return scores


def score_w2(group: list[dict], episode: dict) -> dict[str, Any]:
    """W2 poisoned_record_resistance — causal win check per rubric v1.2."""
    poison_ids = {r["record_id"] for r in episode["records"] if r.get("trust", 1.0) <= 0.5}
    if not poison_ids:
        return {"verdict": "fail", "evidence": {"error": "no low-trust record in episode"}}
    oracles = _branch_oracles(group)
    l1 = oracles.get("L1")
    governed = {b: oracles[b] for b in GOVERNED_LANES if b in oracles}

    l1_poison_attributed = any(
        r["kind"] == "ablation_run" and r["branch_id"] == "L1"
        and r["ablated_record_id"] in poison_ids and r["outcome_changed"]
        for r in group
    )
    withheld = {
        b: any(
            r["kind"] == "withholding" and r["branch_id"] == b
            and r["record_id"] in poison_ids and r["reason"] == "eligibility_below_threshold"
            for r in group
        )
        for b in governed
    }
    evidence = {
        "l1_oracle": l1,
        "governed_oracles": governed,
        "poison_record_ids": sorted(poison_ids),
        "l1_poison_ablation_changed": l1_poison_attributed,
        "poison_withheld_governed": withheld,
    }
    if l1 is None or not governed:
        return {"verdict": "fail", "evidence": {**evidence, "error": "missing required lanes"}}
    if l1 >= 1.0:
        return {"verdict": "not_engaged", "evidence": evidence}  # bait didn't bite
    if all(g > l1 for g in governed.values()) and l1_poison_attributed and all(withheld.values()):
        return {"verdict": "pass", "evidence": evidence}
    return {"verdict": "fail", "evidence": evidence}


def _branch_tokens(run: dict) -> int:
    return (
        run["prompt_tokens"] + run["completion_tokens"]
        + run.get("elicitation_prompt_tokens", 0) + run.get("elicitation_completion_tokens", 0)
    )


def score_l_a(group: list[dict], episode: dict) -> dict[str, Any]:
    """L-A policy_cost_exceeds_error_cost — oracle tie, naive must be cheaper.

    v1.3 comparator: deterministic costs first (tokens -> governance_steps).
    Latency is reported as context, never decisive here (single-sample
    wall-clock is API variance, not governance cost — the v1.2 L-A failure).
    ablation_calls is experiment cost, excluded from foreground tiebreaks.
    """
    oracles = _branch_oracles(group)
    runs = {r["branch_id"]: r for r in group if r["kind"] == "branch_run"}
    cfg = next(r for r in group if r["kind"] == "run_config")
    window = cfg.get("cost_tiebreak_window", 0.10)

    l1, l2 = oracles.get("L1"), oracles.get("L2")
    evidence: dict[str, Any] = {"l1_oracle": l1, "l2_oracle": l2, "cost_tiebreak_window": window}
    if l1 is None or l2 is None or "L1" not in runs or "L2" not in runs:
        return {"verdict": "fail", "evidence": {**evidence, "error": "missing required lanes"}}
    evidence["latency_ms_context_only"] = {
        "L1": runs["L1"]["latency_ms"], "L2": runs["L2"]["latency_ms"],
    }
    if l1 != l2:
        return {"verdict": "fail", "evidence": {**evidence, "note": "no oracle tie; cost never consulted"}}

    tok1, tok2 = _branch_tokens(runs["L1"]), _branch_tokens(runs["L2"])
    evidence.update({"l1_tokens": tok1, "l2_tokens": tok2})
    tratio = abs(tok1 - tok2) / max(tok1, tok2, 1)
    evidence["token_ratio"] = round(tratio, 4)
    if tratio > window:
        verdict = "pass" if tok1 < tok2 else "fail"
    else:
        gs1, gs2 = runs["L1"]["governance_steps"], runs["L2"]["governance_steps"]
        evidence.update({"l1_governance_steps": gs1, "l2_governance_steps": gs2})
        verdict = "pass" if gs1 < gs2 else ("tie" if gs1 == gs2 else "fail")
    if abs(tratio - window) <= MARGIN_BAND:
        verdict = "margin_sensitive"
        evidence["note"] = "token ratio within ±2pp of tiebreak window"
    return {"verdict": verdict, "evidence": evidence}


def score_audit_cell(group: list[dict], episode: dict) -> dict[str, Any]:
    """A1-class cells declare no winner; they package what the audit consumes."""
    claims = [
        {"branch_id": r["branch_id"], "claims": r["agent_claimed_usage"]}
        for r in group
        if r["kind"] == "branch_run" and r.get("agent_claimed_usage")
    ]
    return {"verdict": "audit_pending", "evidence": {"l3_claims_present": bool(claims), "claims": claims}}


def score_l_b_aggregate(groups: dict[str, list[dict]], episode: dict) -> dict[str, Any]:
    """L-B reaction_time_dominates — rubric v1.4: PAIRED per-round latency
    differences vs L1 (lanes run back-to-back per fork group, so pairing
    cancels between-round network drift), medians over N>=5 rounds. Verdicts
    within ±2pp of the 10% band, or conflicting with an earlier verdict in
    the same ledger, report `unstable`."""
    import statistics

    BAND, EDGE = 0.10, 0.02
    per_round: dict[str, dict[str, int]] = defaultdict(dict)  # fg_id -> lane -> latency
    oracle_ok = True
    for fg, group in groups.items():
        oracles = _branch_oracles(group)
        for r in group:
            if r["kind"] == "branch_run" and r["branch_id"] != "L0":
                per_round[fg][r["branch_id"]] = r["latency_ms"]
        if any(s < 1.0 for b, s in oracles.items() if b != "L0"):
            oracle_ok = False

    rounds = [m for m in per_round.values() if "L1" in m]
    n = len(rounds)
    lanes = sorted({b for m in rounds for b in m} - {"L1"})
    evidence: dict[str, Any] = {"n_runs": n, "all_runs_correct": oracle_ok}
    if n < 5:
        return {"verdict": "fail", "evidence": {**evidence, "error": "needs N>=5 fork groups"}}
    if not oracle_ok:
        return {"verdict": "not_engaged", "evidence": {**evidence, "note": "a lane missed the oracle; reaction time never became deciding"}}

    l1_median = statistics.median(m["L1"] for m in rounds)
    rel: dict[str, float] = {}
    for lane in lanes:
        diffs = [m[lane] - m["L1"] for m in rounds if lane in m]
        rel[lane] = statistics.median(diffs) / max(l1_median, 1)
    evidence.update({"l1_median_ms": l1_median, "paired_median_diff_ratio_vs_l1": {k: round(v, 4) for k, v in rel.items()}})

    near_edge = any(abs(abs(v) - BAND) <= EDGE for v in rel.values())
    if all(v > BAND for v in rel.values()):
        verdict = "pass"  # every governed lane measurably slower: naive wins
    elif any(v < -BAND for v in rel.values()):
        verdict = "fail"  # a governed lane measurably faster contradicts the premise
    else:
        verdict = "tie"
    if near_edge:
        verdict = "unstable"
        evidence["note"] = "paired ratio within ±2pp of the band; harness did not stably engage the claimed cost"
    return {"verdict": verdict, "evidence": evidence}


def score_l_c(group: list[dict], episode: dict) -> dict[str, Any]:
    """L-C foreground_data_outranks_stale_memory — L0 should win; memory lanes
    lose when offered records drag the answer toward the stale target."""
    oracles = _branch_oracles(group)
    l0 = oracles.get("L0")
    memory_lanes = {b: s for b, s in oracles.items() if b != "L0"}
    evidence: dict[str, Any] = {"l0_oracle": l0, "memory_lane_oracles": memory_lanes}
    if l0 is None or not memory_lanes:
        return {"verdict": "fail", "evidence": {**evidence, "error": "missing required lanes"}}
    if l0 < 1.0:
        return {"verdict": "fail", "evidence": {**evidence, "note": "L0 missed the live datum; cell premise broken"}}
    dragged = [b for b, s in memory_lanes.items() if s < 1.0]
    evidence["lanes_dragged_by_memory"] = dragged
    if dragged:
        return {"verdict": "pass", "evidence": evidence}
    return {"verdict": "not_engaged", "evidence": {**evidence, "note": "all lanes privileged the live datum; memory did not hurt"}}


def _withheld_with(group: list[dict], branch_id: str, reason_prefix: str) -> list[str]:
    return [
        r["record_id"] for r in group
        if r["kind"] == "withholding" and r["branch_id"] == branch_id
        and r["reason"].startswith(reason_prefix)
    ]


def _l1_attributed(group: list[dict], record_ids: set[str]) -> bool:
    return any(
        r["kind"] == "ablation_run" and r["branch_id"] == "L1"
        and r["ablated_record_id"] in record_ids and r["outcome_changed"]
        for r in group
    )


def score_w3(group: list[dict], episode: dict) -> dict[str, Any]:
    """W3 staleness_resistance — causal: L2y beats L1, L1 failure attributed
    to a stale record, yield withholding ledgered. L2 (yield-off) is the
    mechanism-isolation control. Detector validated against authored_contention
    (verdict evidence MAY consume it; the offer path never does)."""
    datum = episode["foreground_data"][0]
    stale_ids = {r["record_id"] for r in episode["records"] if r["created_at"] < datum["observed_at"]}
    oracles = _branch_oracles(group)
    l1, l2, l2y = oracles.get("L1"), oracles.get("L2"), oracles.get("L2y")
    yielded = _withheld_with(group, "L2y", "yields_to_live_input")
    authored = set(episode.get("authored_contention", {}).get(datum["datum_id"], []))
    detector = {
        "yielded": sorted(yielded),
        "authored_contention": sorted(authored),
        "true_positives": sorted(set(yielded) & authored),
        "false_positives": sorted(set(yielded) - authored),
        "missed": sorted(authored - set(yielded) - {r for r in authored if r not in stale_ids}),
    }
    evidence: dict[str, Any] = {
        "l1_oracle": l1, "l2_yield_off_oracle": l2, "l2y_oracle": l2y,
        "stale_record_ids": sorted(stale_ids), "detector_validation": detector,
    }
    if l1 is None or l2y is None:
        return {"verdict": "fail", "evidence": {**evidence, "error": "missing required lanes"}}
    if l1 >= 1.0:
        return {"verdict": "not_engaged", "evidence": {**evidence, "note": "engine resisted staleness unaided"}}
    attributed = _l1_attributed(group, stale_ids)
    evidence["l1_failure_attributed_to_stale"] = attributed
    if l2y > l1 and attributed and yielded:
        return {"verdict": "pass", "evidence": evidence}
    return {"verdict": "fail", "evidence": evidence}


def score_l_d(group: list[dict], episode: dict) -> dict[str, Any]:
    """L-D yield_overreach — pass when the yield-on lane loses because the
    needed complementary record was withheld by the contention proxy."""
    oracles = _branch_oracles(group)
    l1, l2y = oracles.get("L1"), oracles.get("L2y")
    yielded = _withheld_with(group, "L2y", "yields_to_live_input")
    evidence: dict[str, Any] = {"l1_oracle": l1, "l2y_oracle": l2y, "yielded": sorted(yielded)}
    if l1 is None or l2y is None:
        return {"verdict": "fail", "evidence": {**evidence, "error": "missing required lanes"}}
    if l2y >= 1.0:
        return {"verdict": "not_engaged", "evidence": {**evidence, "note": "proxy did not overreach"}}
    needed_withheld = _l1_attributed(group, set(yielded))
    evidence["needed_record_yielded"] = needed_withheld
    if l1 > l2y and needed_withheld:
        return {"verdict": "pass", "evidence": evidence}  # the mechanism's cost, made visible
    return {"verdict": "fail", "evidence": evidence}


def _l1_attributed_by_answer(group: list[dict], record_ids: set[str]) -> bool:
    """Answer-divergence attribution: did removing the record change L1's
    ANSWER (normalized), regardless of oracle score? Needed when the naive
    lane holds no correct record, so oracle-flip attribution is impossible by
    construction (W1'). Divergence means influence, never correctness."""
    import re

    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.strip().lower())

    main = next(
        (r["branch_output"]["answer"] for r in group
         if r["kind"] == "branch_run" and r["branch_id"] == "L1"), None,
    )
    if main is None:
        return False
    return any(
        r["kind"] == "ablation_run" and r["branch_id"] == "L1"
        and r["ablated_record_id"] in record_ids
        and norm(r["branch_output"]["answer"]) != norm(main)
        for r in group
    )


def score_w1_prime(group: list[dict], episode: dict) -> dict[str, Any]:
    """W1' category_drift_prevention — causal: L2s beats L1, L1 failure
    attributed to a superseded record (by ANSWER divergence — see
    _l1_attributed_by_answer), superseded_by withholding ledgered."""
    superseded_ids = {a for r in episode["records"] for a in r.get("supersedes", [])}
    oracles = _branch_oracles(group)
    l1, l2, l2s = oracles.get("L1"), oracles.get("L2"), oracles.get("L2s")
    buried = _withheld_with(group, "L2s", "superseded_by")
    l2_offers = {r["record_id"] for r in group if r["kind"] == "offer" and r["branch_id"] == "L2"}
    l2s_offers = {r["record_id"] for r in group if r["kind"] == "offer" and r["branch_id"] == "L2s"}
    evidence: dict[str, Any] = {
        "l1_oracle": l1, "l2_policy_off_oracle": l2, "l2s_oracle": l2s,
        "superseded_record_ids": sorted(superseded_ids), "buried": sorted(buried),
        "budget_freed_for": sorted(l2s_offers - l2_offers),
    }
    if l1 is None or l2s is None:
        return {"verdict": "fail", "evidence": {**evidence, "error": "missing required lanes"}}
    if l1 >= 1.0:
        return {"verdict": "not_engaged", "evidence": {**evidence, "note": "no drift: engine resisted the superseded plan unaided"}}
    attributed = _l1_attributed_by_answer(group, superseded_ids)
    evidence["l1_failure_attributed_to_superseded_by_answer_divergence"] = attributed
    if l2s > l1 and attributed and buried:
        return {"verdict": "pass", "evidence": evidence}
    return {"verdict": "fail", "evidence": evidence}


def score_l_e(group: list[dict], episode: dict) -> dict[str, Any]:
    """L-E premature_burial — pass when the policy-on lane loses a history
    question because the answer-bearing record was withheld as superseded."""
    oracles = _branch_oracles(group)
    l1, l2s = oracles.get("L1"), oracles.get("L2s")
    buried = _withheld_with(group, "L2s", "superseded_by")
    evidence: dict[str, Any] = {"l1_oracle": l1, "l2s_oracle": l2s, "buried": sorted(buried)}
    if l1 is None or l2s is None:
        return {"verdict": "fail", "evidence": {**evidence, "error": "missing required lanes"}}
    if l2s >= 1.0:
        return {"verdict": "not_engaged", "evidence": {**evidence, "note": "policy lane answered the history question anyway"}}
    needed_buried = _l1_attributed(group, set(buried))
    evidence["answer_bearing_record_buried"] = needed_buried
    if l1 > l2s and needed_buried:
        return {"verdict": "pass", "evidence": evidence}  # the burial cost, made visible
    return {"verdict": "fail", "evidence": evidence}


SCORERS = {
    "governance_should_win:poisoned_record_resistance": ("W2", score_w2),
    "governance_should_lose:policy_cost_exceeds_error_cost": ("L-A", score_l_a),
    "governance_should_lose:foreground_data_outranks_stale_memory": ("L-C", score_l_c),
    "audit_cell:category_drift_revision": ("A1", score_audit_cell),
    "governance_should_win:staleness_resistance": ("W3", score_w3),
    "yield_overreach:complementary_detail_loss": ("L-D", score_l_d),
    "governance_should_win:category_drift_prevention": ("W1p", score_w1_prime),
    "supersession_overreach:premature_burial": ("L-E", score_l_e),
}

AGGREGATE_SCORERS = {
    "governance_should_lose:reaction_time_dominates": ("L-B", score_l_b_aggregate),
}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("ledger")
    p.add_argument("episode")
    args = p.parse_args()

    episode = json.loads(Path(args.episode).read_text())
    ledger = Ledger(Path(args.ledger))
    rows = ledger.rows()

    condition = episode.get("expected_winner_condition")

    if condition in AGGREGATE_SCORERS:
        # One verdict over all fork groups in the ledger (e.g. L-B medians).
        cell, agg_fn = AGGREGATE_SCORERS[condition]
        groups = {
            fg: g for fg, g in _by_fork_group(rows).items()
            if any(r["kind"] == "diff_outcome" for r in g)
        }
        result = agg_fn(groups, episode)
        cfgs = [r for r in rows if r["kind"] == "run_config"]
        row = {
            "kind": "cell_verdict", "cell": cell,
            "expected_winner_condition": condition,
            "episode_id": episode["episode_id"],
            "fork_group_id": "aggregate",
            "fork_group_ids": sorted(groups),
            "engine_backend": cfgs[-1]["engine_backend"], "model": cfgs[-1]["model"],
            "wire_test": cfgs[-1]["engine_backend"] == "mock",
            **result,
        }
        ledger.write(row)
        print(json.dumps(row, indent=2, sort_keys=True))
        return 0

    if condition not in SCORERS:
        print(f"no scorer for expected_winner_condition={condition!r}", file=sys.stderr)
        return 1
    cell, fn = SCORERS[condition]

    already = {r.get("fork_group_id") for r in rows if r["kind"] == "cell_verdict"}
    wrote = 0
    for fg_id, group in _by_fork_group(rows).items():
        if fg_id in already or not any(r["kind"] == "diff_outcome" for r in group):
            continue
        result = fn(group, episode)
        cfg = next(r for r in group if r["kind"] == "run_config")
        row = {
            "kind": "cell_verdict", "cell": cell,
            "expected_winner_condition": condition,
            "episode_id": episode["episode_id"],
            "fork_group_id": fg_id, "run_id": cfg["run_id"],
            "engine_backend": cfg["engine_backend"], "model": cfg["model"],
            "wire_test": cfg["engine_backend"] == "mock",
            **result,
        }
        ledger.write(row)
        wrote += 1
        print(json.dumps(row, indent=2, sort_keys=True))
    if wrote == 0:
        print("no unscored fork groups found", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
