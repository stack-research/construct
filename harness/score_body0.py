"""Independent Body-0 replay scorer.

The scorer distrusts logged totals and sidecars.  It reconstructs lineage from
the frozen E1 packet plus the harness-minted earned-record row, replays every
hot-store operation, recomputes pre-answer cost, verifies fork identity and
offer engagement, and compares every protected M3 projection checkpoint.

Mock runs can return ``wire_pass`` only.  They are never behavioral evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from .body0 import (
    ADAPTER_FIELDS,
    ADAPTER_ID,
    BRANCH_A,
    BRANCH_C,
    BRANCH_R,
    BRANCH_X,
    BRANCHES,
    packet_sha256,
    protected_projection,
    protected_projection_hash,
    record_dict,
    record_from_dict,
    replay_hot_snapshots,
    sha256_json,
    token_cost,
)
from .check_body0_fixture import manifest_hash
from .ledger import Ledger
from .runner import Episode

ROOT = Path(__file__).resolve().parent.parent
_IDENTITY_EXCLUDE = frozenset({
    "branch_id", "authority_path", "inherited_record_ids", "temperature_path",
})
_PROJECTION_STAGES = {
    "pre_adapter",
    "post_adapter",
    "post_attack",
    "post_cooling",
    "post_rematerialization",
    "post_decision",
}
SCORER_VERSION = "0.2"


def _last(rows: list[dict], kind: str) -> dict | None:
    found = [r for r in rows if r.get("kind") == kind]
    return found[-1] if found else None


def _row_index(rows: list[dict], target: dict) -> int:
    return next(i for i, row in enumerate(rows) if row is target)


def _branch_rows(rows: list[dict], kind: str, run_id: str) -> dict[str, dict]:
    return {
        row["branch_id"]: row
        for row in rows
        if row.get("kind") == kind and row.get("run_id") == run_id
        and row.get("branch_id") in BRANCHES
    }


def _offers(rows: list[dict], run_id: str, branch_id: str) -> set[str]:
    return {
        row["record_id"]
        for row in rows
        if row.get("kind") == "offer"
        and row.get("run_id") == run_id
        and row.get("branch_id") == branch_id
    }


def _normalized_answer(row: dict) -> str:
    answer = row.get("branch_output", {}).get("answer", "")
    return re.sub(r"\s+", " ", answer.strip().lower())


def _config_identity_ok(config: dict, expected_hot: dict[str, frozenset[str]]) -> bool:
    branches = {
        branch["branch_id"]: branch for branch in config.get("branches", [])
        if branch.get("branch_id") in BRANCHES
    }
    if set(branches) != set(BRANCHES):
        return False
    identities = {
        json.dumps(
            {k: v for k, v in branches[bid].items() if k not in _IDENTITY_EXCLUDE},
            sort_keys=True,
            default=str,
        )
        for bid in BRANCHES
    }
    if len(identities) != 1:
        return False
    return all(
        frozenset(branches[bid].get("inherited_record_ids") or ()) == expected_hot[bid]
        for bid in BRANCHES
    )


def score_body0(ledger_path: str | Path) -> list[dict[str, Any]]:
    ledger_path = Path(ledger_path)
    rows = Ledger(ledger_path).rows()
    metas = [row for row in rows if row.get("kind") == "body0_run_meta"]
    if len(metas) != 1:
        raise ValueError(f"{ledger_path}: expected exactly one body0_run_meta row")
    meta = metas[0]
    manifest_path = ROOT / meta["manifest_path"]
    manifest = json.loads(manifest_path.read_text())
    confounds: list[str] = []

    # Frozen packet and admission are recomputed from current bytes, never
    # accepted from the runner's prose.
    binding_ok = (
        meta.get("manifest_sha256") == manifest_hash(manifest_path)
        and meta.get("frozen_packet_sha256") == packet_sha256(manifest)
        and meta.get("frozen_packet_sha256") == manifest.get("frozen_packet_sha256")
    )
    if not binding_ok:
        confounds.append("frozen_packet_binding_failed")
    admissions = [
        row for row in rows if row.get("kind") == "body0_fixture_gate_result"
    ]
    admission_ok = (
        len(admissions) == 1
        and admissions[0].get("gate_open") is True
        and admissions[0].get("manifest_sha256") == manifest_hash(manifest_path)
        and all(check.get("ok") for check in admissions[0].get("checks", []))
        and any(
            check.get("check") == "cost_state_dependence" and check.get("ok")
            for check in admissions[0].get("checks", [])
        )
        and all(
            _row_index(rows, admissions[0]) < _row_index(rows, config)
            for config in rows if config.get("kind") == "run_config"
        )
    )
    if not admission_ok:
        confounds.append("admission_gate_not_open")

    # Reconstruct full lineage from the frozen base packet plus the one earned
    # row. This catches a runner-authored substitute hidden only in run_meta.
    base = Episode.load(ROOT / manifest["e1"])
    sequence_episodes = [
        *[Episode.load(ROOT / path) for path in manifest["residence_sequence"]],
        Episode.load(ROOT / manifest["recurrence"]),
    ]
    sequence_shape_ok = (
        meta.get("sequence_episode_ids")
        == [episode.episode_id for episode in sequence_episodes]
        and meta.get("block_labels") == manifest.get("block_labels")
    )
    if not sequence_shape_ok:
        confounds.append("sequence_binding_failed")
    earned_rows = [row for row in rows if row.get("kind") == "earned_record"]
    earned_id = meta.get("earned_record_id")
    earned_row = (
        earned_rows[0] if len(earned_rows) == 1
        and earned_rows[0].get("record_id") == earned_id else None
    )
    lineage_records = [*base.records]
    if earned_row is None:
        confounds.append("earned_record_binding_failed")
    else:
        lineage_records.append(record_from_dict({
            field: earned_row.get(field)
            for field in ADAPTER_FIELDS
        }))
    reconstructed_rows = [record_dict(record) for record in lineage_records]
    lineage_ok = (
        earned_row is not None
        and meta.get("lineage_records") == reconstructed_rows
        and meta.get("all_record_ids")
        == sorted(record["record_id"] for record in reconstructed_rows)
        and meta.get("record_texts")
        == {record["record_id"]: record["text"] for record in reconstructed_rows}
        and len({record["record_id"] for record in reconstructed_rows})
        == len(reconstructed_rows)
    )
    if not lineage_ok:
        confounds.append("lineage_reconstruction_failed")
    all_ids = frozenset(record["record_id"] for record in reconstructed_rows)
    record_texts = {record["record_id"]: record["text"] for record in reconstructed_rows}

    # The M2 mint must be the failed E1 trace's consequence, not merely a row
    # with a familiar shape.
    e1_run_id = meta.get("e1_run_id")
    e1_runs = [
        row for row in rows
        if row.get("kind") == "branch_run"
        and row.get("run_id") == e1_run_id
        and row.get("branch_id") == "B0-seed"
    ]
    provenance = (earned_row or {}).get("provenance") or {}
    e1_oracle_replay = (
        base.score(e1_runs[0].get("branch_output", {}).get("answer", "")).__dict__
        if len(e1_runs) == 1 else None
    )
    m2_trace_ok = (
        len(e1_runs) == 1
        and e1_runs[0].get("oracle", {}).get("score", 1.0) < 1.0
        and e1_runs[0].get("oracle", {}).get("source") != "authored"
        and e1_runs[0].get("oracle") == e1_oracle_replay
        and provenance.get("minted_by") == "harness"
        and provenance.get("source_run_id") == e1_run_id
        and provenance.get("mint_basis") == "world_correction"
    )
    if not m2_trace_ok:
        confounds.append("m2_trace_binding_failed")

    # Closed identity adapter.
    receipts = [
        row for row in rows if row.get("kind") == "body0_adapter_receipt"
    ]
    adapter_ok = (
        len(receipts) == 1
        and receipts[0].get("adapter_id") == ADAPTER_ID
        and receipts[0].get("fields") == list(ADAPTER_FIELDS)
        and receipts[0].get("input_sha256") == receipts[0].get("output_sha256")
        and receipts[0].get("policy_effects") == []
        and receipts[0].get("identity_ok") is True
    )

    authority_seed = {
        str(k): float(v) for k, v in (meta.get("authority_seed") or {}).items()
    }
    projection_recomputed = (
        protected_projection(lineage_records, authority_seed, earned_id)
        if earned_row is not None else None
    )
    projection_sha = (
        protected_projection_hash(projection_recomputed)
        if projection_recomputed is not None else None
    )
    checkpoints = [
        row for row in rows if row.get("kind") == "body0_protected_projection"
    ]
    checkpoint_stages = {row.get("stage") for row in checkpoints}
    protected_ok = (
        projection_recomputed is not None
        and checkpoint_stages == _PROJECTION_STAGES
        and len(checkpoints) == len(_PROJECTION_STAGES)
        and meta.get("protected_projection") == projection_recomputed
        and meta.get("protected_projection_sha256") == projection_sha
        and all(
            row.get("projection") == projection_recomputed
            and row.get("projection_sha256") == projection_sha
            for row in checkpoints
        )
    )
    attack = _last(rows, "body0_attack")
    attack_result = _last(rows, "body0_attack_result")
    attack_fixture = manifest.get("attack_foreground", {})
    attack_payload_sha = hashlib.sha256(
        json.dumps(
            attack_fixture, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    attack_ok = bool(
        attack
        and attack.get("surface") == "foreground_data"
        and attack.get("allowlist_ok") is True
        and attack.get("attacker_id") == attack_fixture.get("channel")
        and attack.get("payload_sha256") == attack_payload_sha
        and attack.get("protected_projection_before") == projection_sha
        and attack_result
        and attack_result.get("protected_projection_after") == projection_sha
        and attack_result.get("protected_projection_unchanged") is True
        and attack_result.get("checked_after_attacker_exposed_answer_runs") is True
    )
    authority_preserved = protected_ok and attack_ok

    # Every X2 operation must have a unique, earlier pre-action projection and
    # reference a lineage id. The hot state is then replayed independently.
    operations = [
        row for row in rows if row.get("kind") in {"prune", "rematerialize"}
        and row.get("branch_id") in BRANCHES
    ]
    projections = [
        row for row in rows if row.get("kind") == "prune_projection"
        and row.get("branch_id") in BRANCHES
    ]
    event_indexes = [row.get("event_index") for row in operations]
    ops_integrity_ok = (
        len(event_indexes) == len(set(event_indexes))
        and all(row.get("record_id") in all_ids for row in operations)
        and all(row.get("op") == row.get("kind") for row in operations)
        and all(
            len([
                pp for pp in projections
                if pp.get("branch_id") == op.get("branch_id")
                and pp.get("event_index") == op.get("event_index")
                and pp.get("recommendation") == op.get("kind")
                and pp.get("projection_ref") == op.get("prune_projection_ref")
                and _row_index(rows, pp) < _row_index(rows, op)
            ]) == 1
            for op in operations
        )
    )
    expected_op_shape = {
        BRANCH_R: [],
        BRANCH_C: ["prune", "rematerialize"],
        BRANCH_A: ["prune", "rematerialize"],
        BRANCH_X: ["prune"],
    }
    ops_by_branch = {
        bid: sorted(
            [row for row in operations if row["branch_id"] == bid],
            key=lambda row: row["event_index"],
        )
        for bid in BRANCHES
    }
    operation_shape_ok = all(
        [row["op"] for row in ops_by_branch[bid]] == expected_op_shape[bid]
        and all(row["record_id"] == earned_id for row in ops_by_branch[bid])
        for bid in BRANCHES
    )
    if not (ops_integrity_ok and operation_shape_ok):
        confounds.append("hot_operation_integrity_failed")

    seq_indexes = list(range(len(meta.get("sequence_run_ids", []))))
    snapshots = {
        bid: replay_hot_snapshots(all_ids, ops_by_branch[bid], seq_indexes)
        for bid in BRANCHES
    }
    recurrence_index = len(seq_indexes) - 1
    expected_snapshots = {
        BRANCH_R: {k: all_ids for k in seq_indexes},
        BRANCH_C: {
            k: (all_ids if k == recurrence_index else all_ids - {earned_id})
            for k in seq_indexes
        },
        BRANCH_A: {
            k: (all_ids if k == recurrence_index else all_ids - {earned_id})
            for k in seq_indexes
        },
        BRANCH_X: {k: all_ids - {earned_id} for k in seq_indexes},
    }
    residence_ok = snapshots == expected_snapshots
    if not residence_ok:
        confounds.append("hot_state_replay_unexpected")

    logged_costs: dict[str, dict[int, int]] = {bid: {} for bid in BRANCHES}
    cost_rows = [
        row for row in rows if row.get("kind") == "body0_hot_store_cost"
    ]
    for row in cost_rows:
        bid, seq = row.get("branch_id"), row.get("seq_index")
        if bid in logged_costs and isinstance(seq, int):
            logged_costs[bid][seq] = row.get("hot_tokens")
    recomputed_costs = {
        bid: {
            seq: token_cost(record_texts, snapshots[bid][seq])
            for seq in seq_indexes
        }
        for bid in BRANCHES
    }
    cost_replay_ok = (
        len(cost_rows) == len(BRANCHES) * len(seq_indexes)
        and all(row.get("pre_answer") is True for row in cost_rows)
        and logged_costs == recomputed_costs
    )
    if not cost_replay_ok:
        confounds.append("cost_replay_mismatch")
    total_cost = {
        bid: sum(recomputed_costs[bid].values()) for bid in BRANCHES
    }
    c_cheaper = total_cost[BRANCH_C] < total_cost[BRANCH_R]
    cost_gate = _last(rows, "body0_cost_state_gate")
    cost_gate_ok = bool(
        cost_gate
        and cost_gate.get("gate_open") is True
        and cost_gate.get("cost_R") == total_cost[BRANCH_R]
        and cost_gate.get("cost_C") == total_cost[BRANCH_C]
        and cost_gate.get("margin")
        == total_cost[BRANCH_R] - total_cost[BRANCH_C]
        and cost_gate.get("computed_before_post_prefix_contact") is True
        and cost_gate.get("pre_contact_gate_check") == "cost_state_dependence"
        and all(
            _row_index(rows, cost_gate) < _row_index(rows, config)
            for config in rows
            if config.get("kind") == "run_config"
            and config.get("run_id") in meta.get("sequence_run_ids", [])
        )
    )
    if not cost_gate_ok:
        confounds.append("runtime_cost_gate_mismatch")

    # Run/config identity and offer-path engagement.
    run_ids = list(meta.get("sequence_run_ids", []))
    configs = {
        row["run_id"]: row for row in rows
        if row.get("kind") == "run_config" and row.get("run_id") in run_ids
    }
    fork_ok = len(configs) == len(run_ids)
    if fork_ok:
        for seq, run_id in enumerate(run_ids):
            expected_candidates = {
                bid: snapshots[bid][seq] for bid in BRANCHES
            }
            if seq == recurrence_index:
                expected_candidates[BRANCH_A] = (
                    expected_candidates[BRANCH_A] - {earned_id}
                )
            if not _config_identity_ok(configs[run_id], expected_candidates):
                fork_ok = False
                break
            if configs[run_id].get("episode_id") != meta["sequence_episode_ids"][seq]:
                fork_ok = False
                break
    if not fork_ok:
        confounds.append("fork_identity_violation")

    backend_values = {
        row.get("engine_backend") for row in rows if row.get("kind") == "run_config"
    }
    backend = next(iter(backend_values), "unknown") if len(backend_values) == 1 else "mixed"
    if len(backend_values) != 1:
        confounds.append("engine_identity_violation")
    real_admission_ok = (
        backend == "mock"
        or (
            admissions[0].get("engine_backend") == backend
            and any(
                check.get("check") == "probe_ignorance" and check.get("ok")
                for check in admissions[0].get("checks", [])
            )
        )
    )
    if not real_admission_ok:
        confounds.append("real_ignorance_gate_missing")

    branch_runs_by_seq = {
        seq: _branch_rows(rows, "branch_run", run_id)
        for seq, run_id in enumerate(run_ids)
    }
    run_shape_ok = all(
        set(branch_runs_by_seq[seq]) == set(BRANCHES) for seq in seq_indexes
    )
    if not run_shape_ok:
        confounds.append("branch_run_shape_failed")
    oracle_replay_ok = run_shape_ok
    replayed_quality: dict[str, dict[int, float]] = {
        bid: {} for bid in BRANCHES
    }
    if run_shape_ok:
        for seq, episode in enumerate(sequence_episodes):
            for bid in BRANCHES:
                branch_row = branch_runs_by_seq[seq][bid]
                replayed = episode.score(
                    branch_row.get("branch_output", {}).get("answer", "")
                ).__dict__
                replayed_quality[bid][seq] = replayed["score"]
                if branch_row.get("oracle") != replayed:
                    oracle_replay_ok = False
    if not oracle_replay_ok:
        confounds.append("oracle_replay_mismatch")
    quality = {
        bid: {
            seq: replayed_quality.get(bid, {}).get(seq, 0.0)
            for seq in seq_indexes
        }
        for bid in BRANCHES
    }
    source_ok = all(
        branch_runs_by_seq.get(seq, {}).get(bid, {}).get("oracle", {}).get("source")
        not in (None, "authored")
        for seq in seq_indexes for bid in BRANCHES
    )
    if not source_ok:
        confounds.append("post_mint_oracle_not_external")

    recurrence_run = run_ids[-1] if run_ids else ""
    recurrence_offers = {
        bid: _offers(rows, recurrence_run, bid) for bid in BRANCHES
    }
    offer_engagement_ok = (
        earned_id in recurrence_offers[BRANCH_R]
        and earned_id in recurrence_offers[BRANCH_C]
        and earned_id not in recurrence_offers[BRANCH_A]
        and earned_id not in recurrence_offers[BRANCH_X]
    )
    r_score = quality[BRANCH_R].get(recurrence_index, 0.0)
    c_score = quality[BRANCH_C].get(recurrence_index, 0.0)
    a_score = quality[BRANCH_A].get(recurrence_index, 0.0)
    x_score = quality[BRANCH_X].get(recurrence_index, 0.0)
    recurrence_runs = branch_runs_by_seq.get(recurrence_index, {})
    c_answer = _normalized_answer(recurrence_runs.get(BRANCH_C, {}))
    a_answer = _normalized_answer(recurrence_runs.get(BRANCH_A, {}))
    x_answer = _normalized_answer(recurrence_runs.get(BRANCH_X, {}))
    a_path_changed = offer_engagement_ok and (
        c_score != a_score or c_answer != a_answer
    )
    x_path_changed = offer_engagement_ok and (
        c_score != x_score or c_answer != x_answer
    )
    rc_correct = r_score >= 1.0 and c_score >= 1.0
    a_engaged = rc_correct and a_path_changed
    x_engaged = rc_correct and x_path_changed
    dual_engaged = a_engaged and x_engaged
    causal_paths_changed = a_path_changed and x_path_changed
    quality_floor_holds = all(
        quality[BRANCH_C].get(seq) >= quality[BRANCH_R].get(seq)
        for seq in seq_indexes
    )

    attribution_ok = not confounds
    authority_regression = not authority_preserved
    recovery_regression = (
        earned_id in all_ids
        and (
            not any(row["op"] == "rematerialize" for row in ops_by_branch[BRANCH_C])
            or earned_id not in recurrence_offers[BRANCH_C]
        )
    )
    quality_regression = causal_paths_changed and not quality_floor_holds
    attribution_confounded = (
        not attribution_ok or not dual_engaged or not offer_engagement_ok
    )
    pure_tax = (
        authority_preserved and quality_floor_holds and not c_cheaper
    )
    interface_blocked = not adapter_ok

    common = {
        "kind": "cell_verdict",
        "scorer": "score_body0",
        "scorer_version": SCORER_VERSION,
        "sequence_id": meta["sequence_id"],
        "engine_backend": backend,
        "evidence_class": (
            "wire_integration_only" if backend == "mock"
            else "behavioral_candidate"
        ),
        "disclosures": (
            ["engine_backend=mock: wire test only; never evidence about memory"]
            if backend == "mock" else []
        ),
    }
    evidence = {
        "admission_ok": admission_ok,
        "binding_ok": binding_ok,
        "m2_trace_ok": m2_trace_ok,
        "adapter_ok": adapter_ok,
        "protected_projection_ok": protected_ok,
        "attack_projection_ok": attack_ok,
        "lineage_ok": lineage_ok,
        "operation_integrity_ok": ops_integrity_ok and operation_shape_ok,
        "hot_state_replay_ok": residence_ok,
        "cost_replay_ok": cost_replay_ok,
        "runtime_cost_gate_ok": cost_gate_ok,
        "fork_identity_ok": fork_ok,
        "external_oracles_ok": source_ok,
        "oracle_replay_ok": oracle_replay_ok,
        "offer_engagement_ok": offer_engagement_ok,
        "reference_and_composed_correct": rc_correct,
        "causal_paths_changed": causal_paths_changed,
        "earned_ablation_engaged": a_engaged,
        "recovery_ablation_engaged": x_engaged,
        "quality": quality,
        "cost_hot_tokens": total_cost,
        "confound_reasons": sorted(set(confounds)),
    }

    if confounds:
        holds = "confounded"
    elif any((authority_regression, recovery_regression, quality_regression,
              pure_tax, interface_blocked)):
        holds = "fail"
    elif not dual_engaged:
        holds = "not_engaged"
    elif quality_floor_holds and c_cheaper:
        holds = "wire_pass" if backend == "mock" else "pass"
    else:
        holds = "fail"

    return [
        {
            **common,
            "cell": "B0-composition-holds",
            "verdict": holds,
            **evidence,
        },
        {
            **common,
            "cell": "B0-authority-regression",
            "verdict": "pass" if authority_regression else "not_engaged",
            "protected_projection_changed": authority_regression,
        },
        {
            **common,
            "cell": "B0-recovery-regression",
            "verdict": "pass" if recovery_regression else "not_engaged",
            "earned_record_remained_in_lineage": earned_id in all_ids,
            "composed_recurrence_offers": sorted(recurrence_offers[BRANCH_C]),
        },
        {
            **common,
            "cell": "B0-quality-regression",
            "verdict": "pass" if quality_regression else "not_engaged",
            "reference_score": r_score,
            "composed_score": c_score,
            "causal_paths_changed": causal_paths_changed,
            "quality_floor_holds": quality_floor_holds,
        },
        {
            **common,
            "cell": "B0-attribution-confounded",
            "verdict": "pass" if attribution_confounded else "not_engaged",
            "offer_engagement_ok": offer_engagement_ok,
            "dual_engaged": dual_engaged,
            "confound_reasons": sorted(set(confounds)),
        },
        {
            **common,
            "cell": "B0-pure-tax",
            "verdict": "pass" if pure_tax else "not_engaged",
            "cost_hot_tokens": total_cost,
            "quality_floor_holds": quality_floor_holds,
        },
        {
            **common,
            "cell": "B0-interface-blocked",
            "verdict": "pass" if interface_blocked else "not_engaged",
            "adapter_ok": adapter_ok,
        },
    ]


def append_body0_verdicts(ledger_path: str | Path) -> tuple[list[dict], dict | None]:
    """Append the current scorer version, preserving and naming any v0.1 rows."""
    ledger = Ledger(Path(ledger_path))
    prior = [
        row for row in ledger.rows()
        if row.get("kind") == "cell_verdict"
        and row.get("scorer") == "score_body0"
    ]
    current = [
        row for row in prior if row.get("scorer_version") == SCORER_VERSION
    ]
    if current:
        raise ValueError(
            f"Body-0 ledger already scored by score_body0@{SCORER_VERSION}"
        )
    unsupported = [
        row for row in prior
        if row.get("scorer_version") not in (None, "0.1")
    ]
    if unsupported:
        raise ValueError("Body-0 ledger carries an unsupported prior scorer version")

    correction = None
    if prior:
        correction = {
            "kind": "body0_verdict_correction",
            "scorer": "score_body0",
            "scorer_version": SCORER_VERSION,
            "supersedes_scorer_version": "0.1",
            "reason": (
                "engagement now requires recurrence R and C correctness before "
                "A/X answer differences can price a causal leg"
            ),
            "review_thread": "body-0-real-verdict-audit",
            "superseded_verdicts": [
                {
                    "cell": row.get("cell"),
                    "row_sha256": sha256_json(row),
                }
                for row in prior
            ],
        }
        ledger.write(correction)

    verdicts = score_body0(ledger.path)
    for verdict in verdicts:
        ledger.write(verdict)
    return verdicts, correction


def main() -> int:
    parser = argparse.ArgumentParser(description="Score one Body-0 ledger")
    parser.add_argument("ledger")
    args = parser.parse_args()
    try:
        verdicts, correction = append_body0_verdicts(Path(args.ledger))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    if correction:
        print("score_body0@0.1 preserved; appended explicit v0.2 correction")
    for verdict in verdicts:
        print(f"{verdict['cell']}: {verdict['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
