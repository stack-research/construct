"""Body-1 executable-consequence sequence runner.

Mock mode exercises the complete wire and is never behavioral evidence. Real
mode refuses before contact unless a fresh engine-specific admission receipt
matches the exact packet, renderer, backend, and model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

from .body0 import record_dict
from .body1 import (
    BRANCH_A,
    BRANCH_C,
    BRANCH_L0,
    BRANCH_L1,
    BRANCH_L1_ABLATION,
    BRANCH_L2,
    BRANCH_R,
    BRANCH_X,
    ENDORSED_PACKET_INDEX_SHA256,
    FORM_NONBINDING,
    PACKET_DIR,
    PACKET_INDEX,
    RECURRENCE_BRANCHES,
    ROOT,
    Body1ContractError,
    ballast_records,
    body1_projection,
    body1_projection_hash,
    build_body1_prompt,
    classify_expression,
    cost_state_preflight,
    derive_scope,
    earned_record_from_mint,
    execute_packet_form,
    fixture,
    load_json,
    mint_conditions_hold,
    packet_index_sha256,
    records_as_rows,
    renderer_sha256,
    runtime_row,
    scope_matches_declared,
)
from .body1_engine import Body1Engine
from .check_body1_fixture import gate_result
from .ledger import Ledger
from .prune import HotStore
from .records import Record

SEED_BRANCH = "B1-seed"


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _write_projection(
    ledger: Ledger,
    *,
    stage: str,
    records: list[Record],
    authority_seed: dict[str, float],
    earned_record_id: str,
    seq_index: int | None = None,
) -> dict:
    projection = body1_projection(records, authority_seed, earned_record_id)
    ledger.write({
        "kind": "body1_protected_projection",
        "stage": stage,
        "seq_index": seq_index,
        "projection": projection,
        "projection_sha256": body1_projection_hash(projection),
    })
    return projection


def _operation_projection(
    branch_id: str,
    event_index: int,
    recommendation: str,
    *,
    needed_by: str | None = None,
) -> dict:
    if recommendation == "prune":
        basis = {
            "mode": "oracle_gated",
            "disuse": True,
            "world_check_id": "body1_cold_residence_not_eligible",
        }
        world_ref = "body1_cold_residence_not_eligible"
    else:
        basis = {
            "mode": "oracle_gated",
            "needed_by": needed_by,
            "world_check_id": "body1_recurrence_structurally_eligible",
            "recall_load_bearing": True,
        }
        world_ref = "body1_recurrence_structurally_eligible"
    return {
        "recommendation": recommendation,
        "authorized_basis": basis,
        "projection_ref": f"b1-pp-{branch_id}-{event_index}",
        "world_check_ref": world_ref,
    }


def _apply_hot_operation(
    ledger: Ledger,
    store: HotStore,
    *,
    branch_id: str,
    record_id: str,
    recommendation: str,
    fixture_id: str,
    seq_index: int,
    event_index: int,
    effective_before_seq: int,
    needed_by: str | None = None,
) -> None:
    projection = _operation_projection(
        branch_id,
        event_index,
        recommendation,
        needed_by=needed_by,
    )
    ledger.write({
        "kind": "prune_projection",
        "branch_id": branch_id,
        "fixture_id": fixture_id,
        "seq_index": seq_index,
        "event_index": event_index,
        "effective_before_seq": effective_before_seq,
        **projection,
    })
    applied = store.apply(record_id, projection)
    ledger.write({
        "kind": recommendation,
        "branch_id": branch_id,
        "fixture_id": fixture_id,
        "seq_index": seq_index,
        "event_index": event_index,
        "effective_before_seq": effective_before_seq,
        "reason": (
            "body1_recurrence_structurally_eligible"
            if recommendation == "rematerialize"
            else "body1_cold_residence_not_eligible"
        ),
        "world_check": {
            "lineage_preserved": True,
            "rule": projection["world_check_ref"],
        },
        **applied,
    })


def _policy(
    *,
    current: dict,
    branch_id: str,
    records: list[Record],
    hot_ids: frozenset[str],
    earned_record_id: str,
    mode: str,
) -> tuple[list[Record], list[tuple[Record, str]], int]:
    """Closed offer policy over the one earned record plus frozen ballast."""
    if mode == "none":
        return [], [], 0
    derived = derive_scope(current)
    if not scope_matches_declared(current, derived):
        raise Body1ContractError("scope inputs differ from frozen program structure")
    earned = next(record for record in records if record.record_id == earned_record_id)
    withheld: list[tuple[Record, str]] = [
        (record, "ballast_not_offerable")
        for record in records
        if record.record_id != earned_record_id
    ]
    if mode == "naive":
        return [earned], withheld, 1
    if earned.record_id not in hot_ids:
        withheld.append((earned, "cold_not_materialized"))
        return [], withheld, 1
    if branch_id == BRANCH_A:
        withheld.append((earned, "offer_ablation"))
        return [], withheld, 1
    if derived.descriptor_slot == 0:
        return [earned], withheld, 1
    if derived.descriptor_slot == 1:
        withheld.append((earned, "scope_descriptor_slot_1"))
        return [], withheld, 1
    raise Body1ContractError("blocked(scope_relation_outside_packet)")


def _write_offer_rows(
    ledger: Ledger,
    *,
    run_id: str,
    fork_group_id: str,
    current: dict,
    branch_id: str,
    offered: list[Record],
    withheld: list[tuple[Record, str]],
) -> None:
    for record in offered:
        ledger.write({
            "kind": "offer",
            "run_id": run_id,
            "fork_group_id": fork_group_id,
            "episode_id": current["fixture_id"],
            "branch_id": branch_id,
            "record_id": record.record_id,
            "reason": "body1_structural_eligibility",
            "attention_cost_tokens": len(record.text.split()),
            "predeclared_usage": record.predeclared_usage,
            "vocabulary_kind": record.vocabulary_kind,
        })
    for record, reason in withheld:
        ledger.write({
            "kind": "withholding",
            "run_id": run_id,
            "fork_group_id": fork_group_id,
            "episode_id": current["fixture_id"],
            "branch_id": branch_id,
            "record_id": record.record_id,
            "reason": reason,
            "predeclared_usage": record.predeclared_usage,
            "vocabulary_kind": record.vocabulary_kind,
        })


def _run_action(
    ledger: Ledger,
    engine: Body1Engine,
    *,
    current: dict,
    branch_id: str,
    run_id: str,
    fork_group_id: str,
    offered: list[Record],
    withheld: list[tuple[Record, str]],
    governance_steps: int,
    foreground: list[dict],
    role: str,
) -> dict:
    _write_offer_rows(
        ledger,
        run_id=run_id,
        fork_group_id=fork_group_id,
        current=current,
        branch_id=branch_id,
        offered=offered,
        withheld=withheld,
    )
    prompt = build_body1_prompt(current, offered, foreground)
    result = engine.run(
        prompt,
        current,
        [record.record_id for record in offered],
    )
    selection = classify_expression(result.raw_answer, current)
    runtime = (
        execute_packet_form(current, selection.form)
        if selection.form else None
    )
    ledger.write({
        "kind": "body1_action",
        "run_id": run_id,
        "fork_group_id": fork_group_id,
        "episode_id": current["fixture_id"],
        "branch_id": branch_id,
        "role": role,
        "engine_backend": engine.backend_name,
        "requested_model": engine.requested_model,
        "observed_model": result.observed_model,
        "renderer_sha256": renderer_sha256(),
        "prompt_sha256": _sha256_text(prompt),
        "raw_answer": result.raw_answer,
        "raw_answer_sha256": selection.raw_sha256,
        "selection_status": selection.status,
        "selected_form": selection.form,
        "selection_refusal": selection.refusal,
        "offered_record_ids": [record.record_id for record in offered],
        "governance_steps": governance_steps,
        "latency_ms": result.latency_ms,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "model_bytes_executed": False,
    })
    if runtime:
        ledger.write({
            "kind": "body1_subprocess_result",
            "run_id": run_id,
            "fork_group_id": fork_group_id,
            "branch_id": branch_id,
            "role": role,
            **runtime_row(runtime),
        })
    else:
        ledger.write({
            "kind": "body1_subprocess_refusal",
            "run_id": run_id,
            "fork_group_id": fork_group_id,
            "branch_id": branch_id,
            "role": role,
            "fixture_id": current["fixture_id"],
            "reason": selection.refusal or selection.status,
        })
    return {
        "selection": selection,
        "runtime": runtime,
        "engine_result": result,
        "prompt_sha256": _sha256_text(prompt),
    }


def _write_fork_config(
    ledger: Ledger,
    *,
    run_id: str,
    fork_group_id: str,
    current: dict,
    engine: Body1Engine,
    branches: list[dict],
    foreground: list[dict],
) -> None:
    base_prompt = build_body1_prompt(current, [], foreground)
    ledger.write({
        "kind": "body1_fork_config",
        "run_id": run_id,
        "fork_group_id": fork_group_id,
        "fixture_id": current["fixture_id"],
        "fixture_sha256": hashlib.sha256(
            (PACKET_DIR / f"{_fixture_name(current)}.json").read_bytes()
        ).hexdigest(),
        "base_prompt_sha256": _sha256_text(base_prompt),
        "renderer_sha256": renderer_sha256(),
        "engine_backend": engine.backend_name,
        "requested_model": engine.requested_model,
        "parameters": {"temperature": 0, "max_tokens": 256},
        "branches": branches,
        "foreground_sha256": hashlib.sha256(
            json.dumps(foreground, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "model_bytes_executed": False,
        "disclosures": (
            ["deterministic mock: wire integration only; never memory evidence"]
            if engine.backend_name == "mock" else []
        ),
    })


def _fixture_name(current: dict) -> str:
    mapping = {
        "b1-surface-control": "surface_control",
        "b1-ignorance-probe": "ignorance_probe",
        "b1-e1-route-key": "e1_failure",
        "b1-residence-ticket-key": "residence",
        "b1-u-unit-key": "recurrence",
        "b1-l-owner-key": "scope_loses",
    }
    return mapping[current["fixture_id"]]


def _load_probe(path: Path | None) -> dict | None:
    return json.loads(path.read_text()) if path else None


def run_body1(
    *,
    engine_backend: str = "mock",
    model: str = "mock-engine-v1",
    base_url: str = "http://localhost:1234/v1",
    runs_dir: Path | None = None,
    probe_result: dict | None = None,
) -> Path:
    runs_dir = (runs_dir or ROOT / "runs" / "body1").resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)
    sequence_id = f"body1-partial-binding-{uuid.uuid4().hex[:8]}"
    ledger = Ledger(runs_dir / f"{sequence_id}.body1.jsonl")
    admission = gate_result(
        probe_result=probe_result,
        engine_backend=engine_backend,
        model=model,
    )
    ledger.write({"kind": "body1_admission_gate_result", **admission})
    if not admission["gate_open"]:
        ledger.write({
            "kind": "body1_admission_refused",
            "reason": "pre_contact_gate_closed",
            "failed_checks": [
                check["check"] for check in admission["checks"]
                if not check["ok"]
            ],
        })
        raise Body1ContractError(
            f"Body-1 refused before engine contact; ledger={ledger.path}"
        )

    engine = Body1Engine(
        backend=engine_backend,
        model=model,
        base_url=base_url,
    )
    sequence = load_json(PACKET_DIR / "sequence_contract.json")
    attack = load_json(PACKET_DIR / "attack.json")

    # Fresh scored failure source.
    e1 = fixture("e1_failure")
    e1_run_id = uuid.uuid4().hex[:12]
    e1_fork_id = uuid.uuid4().hex[:12]
    _write_fork_config(
        ledger,
        run_id=e1_run_id,
        fork_group_id=e1_fork_id,
        current=e1,
        engine=engine,
        branches=[{"branch_id": SEED_BRANCH, "memory_condition": "none"}],
        foreground=[],
    )
    e1_action = _run_action(
        ledger,
        engine,
        current=e1,
        branch_id=SEED_BRANCH,
        run_id=e1_run_id,
        fork_group_id=e1_fork_id,
        offered=[],
        withheld=[],
        governance_steps=0,
        foreground=[],
        role="e1_failure",
    )
    counterfactual = execute_packet_form(e1, FORM_NONBINDING)
    ledger.write({
        "kind": "body1_counterfactual",
        "run_id": e1_run_id,
        "branch_id": SEED_BRANCH,
        "source": "packet_authored_nonbinding_form",
        **runtime_row(counterfactual),
    })
    observed = e1_action["runtime"]
    if (
        observed is None
        or not mint_conditions_hold(
            e1,
            e1_action["selection"],
            observed,
            counterfactual,
        )
    ):
        ledger.write({
            "kind": "body1_sequence_close",
            "reason": "not_engaged(cold_failure_absent)",
        })
        raise Body1ContractError(
            f"Body-1 E1 mint conditions absent; ledger={ledger.path}"
        )
    earned = earned_record_from_mint(
        source_run_id=e1_run_id,
        source_runtime=observed,
        counterfactual_runtime=counterfactual,
    )
    ledger.write({"kind": "earned_record", **record_dict(earned)})

    records = [*ballast_records(sequence), earned]
    all_ids = frozenset(record.record_id for record in records)
    record_texts = {record.record_id: record.text for record in records}
    authority_seed = {earned.record_id: 1.0}
    pre_attack_projection = _write_projection(
        ledger,
        stage="pre_attack",
        records=records,
        authority_seed=authority_seed,
        earned_record_id=earned.record_id,
    )
    ledger.write({
        "kind": "body1_interface_receipt",
        "adapter": "record_identity",
        "fields": sorted(record_dict(earned)),
        "policy_effects": [],
        "identity_sha256": hashlib.sha256(
            json.dumps(record_dict(earned), sort_keys=True).encode()
        ).hexdigest(),
        "identity_ok": True,
    })
    attack_sha = hashlib.sha256(
        json.dumps(attack, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    ledger.write({
        "kind": "body1_attack",
        "surface": "attacker_owned_foreground",
        "payload_sha256": attack_sha,
        "allowlist_ok": set(attack) == {
            "channel", "datum_id", "forbidden_targets", "observed_at", "text"
        },
        "protected_projection_before": body1_projection_hash(pre_attack_projection),
    })
    post_attack_projection = _write_projection(
        ledger,
        stage="post_attack",
        records=records,
        authority_seed=authority_seed,
        earned_record_id=earned.record_id,
    )
    if body1_projection_hash(pre_attack_projection) != body1_projection_hash(
        post_attack_projection
    ):
        raise Body1ContractError("protected projection changed under foreground attack")

    stores: dict[str, HotStore] = {}
    hot_paths: dict[str, str] = {}
    for branch_id in RECURRENCE_BRANCHES:
        path = runs_dir / f"{sequence_id}.{branch_id}.hot.json"
        stores[branch_id] = HotStore(path, seed_ids=all_ids)
        hot_paths[branch_id] = str(path)
    event_index = 0
    residence = fixture("residence")
    for branch_id in (BRANCH_C, BRANCH_A, BRANCH_X):
        _apply_hot_operation(
            ledger,
            stores[branch_id],
            branch_id=branch_id,
            record_id=earned.record_id,
            recommendation="prune",
            fixture_id=residence["fixture_id"],
            seq_index=0,
            event_index=event_index,
            effective_before_seq=0,
        )
        event_index += 1
    _write_projection(
        ledger,
        stage="post_cooling",
        records=records,
        authority_seed=authority_seed,
        earned_record_id=earned.record_id,
        seq_index=0,
    )
    cost_gate = cost_state_preflight(records, earned.record_id, 3)
    ledger.write({
        "kind": "body1_cost_state_gate",
        "primary_cost_metric": "hot_tokens",
        "computed_before_post_mint_contact": True,
        **cost_gate,
    })
    if not cost_gate["gate_open"]:
        raise Body1ContractError("blocked(cost_state_dependence)")

    sequence_run_ids: list[str] = []
    foreground = [attack]
    for seq_index in range(4):
        current = residence if seq_index < 3 else fixture("recurrence")
        is_recurrence = seq_index == 3
        if is_recurrence:
            for branch_id in (BRANCH_C, BRANCH_A):
                _apply_hot_operation(
                    ledger,
                    stores[branch_id],
                    branch_id=branch_id,
                    record_id=earned.record_id,
                    recommendation="rematerialize",
                    fixture_id=current["fixture_id"],
                    seq_index=seq_index,
                    event_index=event_index,
                    effective_before_seq=seq_index,
                    needed_by=current["fixture_id"],
                )
                event_index += 1
            ledger.write({
                "kind": "body1_intervention",
                "branch_id": BRANCH_A,
                "seq_index": seq_index,
                "intervention": "suppress_earned_offer",
                "record_id": earned.record_id,
                "declared_at_population": True,
            })
            ledger.write({
                "kind": "body1_intervention",
                "branch_id": BRANCH_X,
                "seq_index": seq_index,
                "intervention": "suppress_rematerialization",
                "record_id": earned.record_id,
                "declared_at_population": True,
            })
            _write_projection(
                ledger,
                stage="post_rematerialization",
                records=records,
                authority_seed=authority_seed,
                earned_record_id=earned.record_id,
                seq_index=seq_index,
            )
        run_id = uuid.uuid4().hex[:12]
        fork_group_id = uuid.uuid4().hex[:12]
        sequence_run_ids.append(run_id)
        branch_descriptors = []
        policies: dict[str, tuple[list[Record], list[tuple[Record, str]], int]] = {}
        for branch_id in RECURRENCE_BRANCHES:
            hot_ids = stores[branch_id].get_hot()
            policies[branch_id] = _policy(
                current=current,
                branch_id=branch_id,
                records=records,
                hot_ids=hot_ids,
                earned_record_id=earned.record_id,
                mode="governed",
            )
            branch_descriptors.append({
                "branch_id": branch_id,
                "memory_condition": {
                    BRANCH_R: "reference",
                    BRANCH_C: "composed",
                    BRANCH_A: "offer_ablation",
                    BRANCH_X: "recovery_ablation",
                }[branch_id],
                "hot_record_ids": sorted(hot_ids),
            })
            cost = stores[branch_id].cost(records)
            ledger.write({
                "kind": "body1_hot_store_cost",
                "run_id": run_id,
                "branch_id": branch_id,
                "episode_id": current["fixture_id"],
                "seq_index": seq_index,
                "pre_answer": True,
                "primary_cost_metric": "hot_tokens",
                **cost,
            })
        _write_fork_config(
            ledger,
            run_id=run_id,
            fork_group_id=fork_group_id,
            current=current,
            engine=engine,
            branches=branch_descriptors,
            foreground=foreground,
        )
        for branch_id in RECURRENCE_BRANCHES:
            offered, withheld, steps = policies[branch_id]
            _run_action(
                ledger,
                engine,
                current=current,
                branch_id=branch_id,
                run_id=run_id,
                fork_group_id=fork_group_id,
                offered=offered,
                withheld=withheld,
                governance_steps=steps,
                foreground=foreground,
                role="recurrence" if is_recurrence else "residence",
            )

    # Separate scope-loss fork. L1's offered record is ablated in an additional
    # predeclared action only when its selected action is harmed.
    scope = fixture("scope_loses")
    scope_run_id = uuid.uuid4().hex[:12]
    scope_fork_id = uuid.uuid4().hex[:12]
    scope_policies = {
        BRANCH_L0: _policy(
            current=scope,
            branch_id=BRANCH_L0,
            records=records,
            hot_ids=all_ids,
            earned_record_id=earned.record_id,
            mode="none",
        ),
        BRANCH_L1: _policy(
            current=scope,
            branch_id=BRANCH_L1,
            records=records,
            hot_ids=all_ids,
            earned_record_id=earned.record_id,
            mode="naive",
        ),
        BRANCH_L2: _policy(
            current=scope,
            branch_id=BRANCH_L2,
            records=records,
            hot_ids=all_ids,
            earned_record_id=earned.record_id,
            mode="governed",
        ),
    }
    _write_fork_config(
        ledger,
        run_id=scope_run_id,
        fork_group_id=scope_fork_id,
        current=scope,
        engine=engine,
        branches=[
            {"branch_id": BRANCH_L0, "memory_condition": "no_memory"},
            {"branch_id": BRANCH_L1, "memory_condition": "ungoverned_offer"},
            {"branch_id": BRANCH_L2, "memory_condition": "governed_withholding"},
        ],
        foreground=foreground,
    )
    scope_results = {}
    for branch_id in (BRANCH_L0, BRANCH_L1, BRANCH_L2):
        offered, withheld, steps = scope_policies[branch_id]
        scope_results[branch_id] = _run_action(
            ledger,
            engine,
            current=scope,
            branch_id=branch_id,
            run_id=scope_run_id,
            fork_group_id=scope_fork_id,
            offered=offered,
            withheld=withheld,
            governance_steps=steps,
            foreground=foreground,
            role="scope_loses",
        )
    l1_runtime = scope_results[BRANCH_L1]["runtime"]
    ablation_run_id: str | None = None
    if l1_runtime and l1_runtime.outcome != "pass":
        ablation_run_id = uuid.uuid4().hex[:12]
        ablation_fork_id = uuid.uuid4().hex[:12]
        _write_fork_config(
            ledger,
            run_id=ablation_run_id,
            fork_group_id=ablation_fork_id,
            current=scope,
            engine=engine,
            branches=[{
                "branch_id": BRANCH_L1_ABLATION,
                "memory_condition": "single_record_ablation",
            }],
            foreground=foreground,
        )
        ablated = _run_action(
            ledger,
            engine,
            current=scope,
            branch_id=BRANCH_L1_ABLATION,
            run_id=ablation_run_id,
            fork_group_id=ablation_fork_id,
            offered=[],
            withheld=[(earned, "single_record_ablation")],
            governance_steps=1,
            foreground=foreground,
            role="scope_single_record_ablation",
        )
        ledger.write({
            "kind": "body1_ablation_result",
            "source_branch": BRANCH_L1,
            "ablation_branch": BRANCH_L1_ABLATION,
            "record_id": earned.record_id,
            "source_runtime_outcome": l1_runtime.outcome,
            "ablation_runtime_outcome": (
                ablated["runtime"].outcome if ablated["runtime"] else None
            ),
            "outcome_changed": (
                ablated["runtime"] is not None
                and ablated["runtime"].outcome != l1_runtime.outcome
            ),
        })

    final_projection = _write_projection(
        ledger,
        stage="post_decision",
        records=records,
        authority_seed=authority_seed,
        earned_record_id=earned.record_id,
        seq_index=3,
    )
    ledger.write({
        "kind": "body1_attack_result",
        "protected_projection_after": body1_projection_hash(final_projection),
        "protected_projection_unchanged": (
            body1_projection_hash(pre_attack_projection)
            == body1_projection_hash(final_projection)
        ),
        "checked_after_attacker_exposed_actions": True,
    })
    ledger.write({
        "kind": "body1_run_meta",
        "sequence_id": sequence_id,
        "packet_id": sequence["packet_id"],
        "packet_index_path": str(PACKET_INDEX.relative_to(ROOT)),
        "packet_index_sha256": packet_index_sha256(),
        "endorsed_packet_index_sha256": ENDORSED_PACKET_INDEX_SHA256,
        "renderer_sha256": renderer_sha256(),
        "engine_backend": engine.backend_name,
        "requested_model": model,
        "e1_run_id": e1_run_id,
        "sequence_run_ids": sequence_run_ids,
        "scope_run_id": scope_run_id,
        "scope_ablation_run_id": ablation_run_id,
        "block_labels": sequence["residence_contract"]["block_labels"],
        "branches": {
            "reference": BRANCH_R,
            "composed": BRANCH_C,
            "offer_ablation": BRANCH_A,
            "recovery_ablation": BRANCH_X,
            "scope_no_memory": BRANCH_L0,
            "scope_ungoverned": BRANCH_L1,
            "scope_governed": BRANCH_L2,
        },
        "earned_record_id": earned.record_id,
        "lineage_records": records_as_rows(records),
        "all_record_ids": sorted(all_ids),
        "record_texts": record_texts,
        "authority_seed": authority_seed,
        "protected_projection": final_projection,
        "protected_projection_sha256": body1_projection_hash(final_projection),
        "hot_paths": hot_paths,
        "primary_cost_metric": "hot_tokens",
        "evidence_class": (
            "wire_integration_only"
            if engine_backend == "mock" else "behavioral_candidate"
        ),
        "model_bytes_executed": False,
    })
    print(
        f"{sequence_id}: Body-1 sequence complete "
        f"({engine_backend}; wire={engine_backend == 'mock'})"
    )
    print(f"  ledger: {ledger.path}")
    return ledger.path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Body-1 composition wire")
    parser.add_argument("--engine", default="mock", choices=["mock", "claude", "local"])
    parser.add_argument("--model", default="mock-engine-v1")
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument("--runs-dir", default=str(ROOT / "runs" / "body1"))
    parser.add_argument("--probe-result")
    args = parser.parse_args()
    try:
        run_body1(
            engine_backend=args.engine,
            model=args.model,
            base_url=args.base_url,
            runs_dir=Path(args.runs_dir),
            probe_result=_load_probe(
                Path(args.probe_result) if args.probe_result else None
            ),
        )
    except (Body1ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
