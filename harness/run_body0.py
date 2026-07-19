"""Body-0 runner: compose the earned M2, protected M3, and hot/cold X2 paths.

The shared prefix (failure -> mint -> adapter -> attack) executes once.  The
four-way fork begins at cooling:

* B0-R keeps the earned correction hot;
* B0-C prunes it and rematerializes it at recurrence;
* B0-A follows C's residence trajectory, then suppresses the earned offer;
* B0-X follows C's residence trajectory, then suppresses rematerialization.

All answer runs use the existing ``run_fork_group`` path.  Body-0 adds only
ledgered orchestration and an identity adapter; it does not add a selector,
semantic classifier, authority source, or hot-store operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

from .body0 import (
    BRANCH_A,
    BRANCH_C,
    BRANCH_R,
    BRANCH_X,
    BRANCHES,
    Body0ContractError,
    adapt_earned_record,
    cost_state_preflight,
    packet_sha256,
    protected_projection,
    protected_projection_hash,
    record_dict,
)
from .check_body0_fixture import DEFAULT_MANIFEST, gate_result
from .ledger import Ledger
from .prune import HotStore
from .resident import mint_earned_record
from .run_m2 import _resident_config_digest
from .runner import BranchConfig, Episode, run_fork_group

ROOT = Path(__file__).resolve().parent.parent
SEED_BRANCH = "B0-seed"


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write_projection(ledger: Ledger, *, stage: str, records: list,
                      authority_seed: dict[str, float], earned_record_id: str,
                      seq_index: int | None = None) -> dict:
    projection = protected_projection(records, authority_seed, earned_record_id)
    ledger.write({
        "kind": "body0_protected_projection",
        "stage": stage,
        "seq_index": seq_index,
        "projection": projection,
        "projection_sha256": protected_projection_hash(projection),
    })
    return projection


def _operation_projection(branch_id: str, event_index: int, recommendation: str,
                          *, needed_by: str | None = None) -> dict:
    if recommendation == "prune":
        basis = {
            "mode": "oracle_gated",
            "disuse": True,
            "world_check_id": "m2_earned_record_preserved_in_lineage",
        }
        world_ref = "m2_earned_record_preserved_in_lineage"
    else:
        basis = {
            "mode": "oracle_gated",
            "needed_by": needed_by,
            "world_check_id": "frozen_recurrence_requires_earned_record",
            "recall_load_bearing": True,
        }
        world_ref = "frozen_recurrence_requires_earned_record"
    return {
        "recommendation": recommendation,
        "authorized_basis": basis,
        "projection_ref": f"b0-pp-{branch_id}-{event_index}",
        "world_check_ref": world_ref,
    }


def _apply_hot_operation(
    ledger: Ledger,
    store: HotStore,
    *,
    branch_id: str,
    record_id: str,
    recommendation: str,
    episode_id: str,
    seq_index: int,
    event_index: int,
    effective_before_seq: int,
    needed_by: str | None = None,
) -> None:
    projection = _operation_projection(
        branch_id, event_index, recommendation, needed_by=needed_by
    )
    ledger.write({
        "kind": "prune_projection",
        "branch_id": branch_id,
        "episode_id": episode_id,
        "seq_index": seq_index,
        "event_index": event_index,
        "effective_before_seq": effective_before_seq,
        **projection,
    })
    applied = store.apply(record_id, projection)
    ledger.write({
        "kind": recommendation,
        "branch_id": branch_id,
        "episode_id": episode_id,
        "seq_index": seq_index,
        "event_index": event_index,
        "effective_before_seq": effective_before_seq,
        "reason": (
            "frozen_recurrence_requires_earned_record"
            if recommendation == "rematerialize"
            else "cold_residence_not_needed"
        ),
        "world_check": {
            "lineage_preserved": True,
            "rule": projection["world_check_ref"],
        },
        **applied,
    })


def _load_probe(path: Path | None) -> dict | None:
    return json.loads(path.read_text()) if path else None


def run_body0(
    manifest_path: Path = DEFAULT_MANIFEST,
    *,
    engine_backend: str = "mock",
    model: str = "mock-engine-v1",
    base_url: str = "http://localhost:1234/v1",
    runs_dir: Path | None = None,
    probe_result: dict | None = None,
) -> Path:
    """Run one admitted Body-0 sequence and return its append-only ledger."""
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text())
    runs_dir = (runs_dir or ROOT / "runs" / "body0").resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)
    sequence_id = f"{manifest['fixture_id']}-{uuid.uuid4().hex[:8]}"
    ledger = Ledger(runs_dir / f"{sequence_id}.body0.jsonl")

    admission = gate_result(
        manifest_path,
        probe_result=probe_result,
        engine_backend=engine_backend,
        model=model,
    )
    ledger.write({"kind": "body0_fixture_gate_result", **admission})
    if not admission["gate_open"]:
        ledger.write({
            "kind": "body0_admission_refused",
            "reason": "fixture_or_ignorance_gate_closed",
            "failed_checks": [
                c["check"] for c in admission["checks"] if not c["ok"]
            ],
        })
        raise Body0ContractError(
            f"Body-0 admission refused before engine contact; ledger={ledger.path}"
        )

    e1 = Episode.load(ROOT / manifest["e1"])
    residence = [Episode.load(ROOT / p) for p in manifest["residence_sequence"]]
    recurrence = Episode.load(ROOT / manifest["recurrence"])
    base_record_rows = [record_dict(r) for r in e1.records]
    if any([record_dict(r) for r in ep.records] != base_record_rows
           for ep in [*residence, recurrence]):
        raise Body0ContractError("base lineage differs after admission")

    # Shared prefix: one cold, stale E1 run.  The session attestation is written
    # before minting so the unchanged M2 Wall-B mint can verify its trace.
    seed_authority = runs_dir / f"{sequence_id}.seed.authority.json"
    e1_result = run_fork_group(
        e1,
        [
            BranchConfig(
                SEED_BRANCH,
                memory="governed",
                authority_path=str(seed_authority),
                top_k=int(manifest["top_k"]),
                recency_weight=float(manifest["recency_weight"]),
                similarity_backend="lexical_tfidf",
            )
        ],
        ledger,
        engine_backend=engine_backend,
        model=model,
        base_url=base_url,
        skip_ablation=True,
        freeze_authority=True,
    )
    session_id = "b0s-" + uuid.uuid4().hex[:8]
    resident_digest = _resident_config_digest(engine_backend, model)
    ledger.write({
        "kind": "session",
        "session_id": session_id,
        "store_path": manifest["e1"],
        "prior_session_id": None,
        "wall_clock_start": _utc_now(),
        "resident_config_digest": resident_digest,
        "memory_isolation": "minimal_harness",
        "episode_id": e1.episode_id,
    })
    earned = mint_earned_record(
        ledger.rows(),
        SEED_BRANCH,
        session_id=session_id,
        source_run_id=e1_result["run_id"],
        created_at=_utc_now(),
    )
    if earned is None:
        ledger.write({
            "kind": "body0_admission_refused",
            "reason": "m2_trace_mint_failed",
            "source_run_id": e1_result["run_id"],
        })
        raise Body0ContractError(
            f"Body-0 M2 mint refused; ledger={ledger.path}"
        )
    ledger.write({"kind": "earned_record", **record_dict(earned)})

    full_records_pre_adapter = [*e1.records, earned]
    authority_seed = {earned.record_id: 1.0}
    _write_projection(
        ledger,
        stage="pre_adapter",
        records=full_records_pre_adapter,
        authority_seed=authority_seed,
        earned_record_id=earned.record_id,
    )
    carried, receipt = adapt_earned_record(earned, manifest["adapter_id"])
    ledger.write({
        "kind": "body0_adapter_receipt",
        "adapter_id": receipt.adapter_id,
        "input_sha256": receipt.input_sha256,
        "output_sha256": receipt.output_sha256,
        "fields": list(receipt.fields),
        "policy_effects": list(receipt.policy_effects),
        "identity_ok": receipt.identity_ok,
    })
    lineage_records = [*e1.records, carried]
    _write_projection(
        ledger,
        stage="post_adapter",
        records=lineage_records,
        authority_seed=authority_seed,
        earned_record_id=carried.record_id,
    )

    # The attack owns prompt foreground only.  It is recorded before the fork;
    # no attacker-provided field enters lineage, authority, or the adapter.
    attack = dict(manifest["attack_foreground"])
    attack_payload_sha256 = hashlib.sha256(
        json.dumps(attack, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    pre_attack = protected_projection_hash(
        protected_projection(lineage_records, authority_seed, carried.record_id)
    )
    ledger.write({
        "kind": "body0_attack",
        "surface": "foreground_data",
        "attacker_id": attack["channel"],
        "payload_sha256": attack_payload_sha256,
        "allowlist_ok": set(attack) == {"datum_id", "channel", "observed_at", "text"},
        "protected_projection_before": pre_attack,
    })
    post_attack_projection = _write_projection(
        ledger,
        stage="post_attack",
        records=lineage_records,
        authority_seed=authority_seed,
        earned_record_id=carried.record_id,
    )
    if pre_attack != protected_projection_hash(post_attack_projection):
        raise Body0ContractError("protected projection changed while binding attack input")

    # Populate post-mint episodes only after the adapter and prefix checks.
    for ep in [*residence, recurrence]:
        ep.records.append(carried)
        ep.m2_earned_record_id = carried.record_id
        ep.foreground_data = [dict(attack)]

    all_ids = frozenset(r.record_id for r in lineage_records)
    record_texts = {r.record_id: r.text for r in lineage_records}
    sidecars: dict[str, tuple[Path, Path]] = {}
    hot: dict[str, HotStore] = {}
    for branch_id in BRANCHES:
        authority_path = runs_dir / f"{sequence_id}.{branch_id}.authority.json"
        hot_path = runs_dir / f"{sequence_id}.{branch_id}.hot.json"
        authority_path.write_text(json.dumps(authority_seed, indent=2, sort_keys=True))
        sidecars[branch_id] = (authority_path, hot_path)
        hot[branch_id] = HotStore(hot_path, seed_ids=all_ids)

    # Cooling is the fork point. R stays hot; C/A/X use the unchanged X2
    # actuator to evict exactly the earned record while retaining full lineage.
    event_index = 0
    for branch_id in (BRANCH_C, BRANCH_A, BRANCH_X):
        _apply_hot_operation(
            ledger,
            hot[branch_id],
            branch_id=branch_id,
            record_id=carried.record_id,
            recommendation="prune",
            episode_id=residence[0].episode_id,
            seq_index=0,
            event_index=event_index,
            effective_before_seq=0,
        )
        event_index += 1
    _write_projection(
        ledger,
        stage="post_cooling",
        records=lineage_records,
        authority_seed=authority_seed,
        earned_record_id=carried.record_id,
        seq_index=0,
    )

    # Important ordering: this is the complete-sequence replay gate and is
    # written before the first post-prefix behavioral run.
    cost_gate = cost_state_preflight(
        record_texts, carried.record_id, len(residence)
    )
    ledger.write({
        "kind": "body0_cost_state_gate",
        "primary_cost_metric": manifest["primary_cost_metric"],
        "computed_before_post_prefix_contact": True,
        "pre_contact_gate_check": "cost_state_dependence",
        **cost_gate,
    })
    if not cost_gate["gate_open"]:
        ledger.write({
            "kind": "body0_admission_refused",
            "reason": "blocked(cost_state_dependence)",
        })
        raise Body0ContractError(
            f"Body-0 cost/state gate refused; ledger={ledger.path}"
        )

    sequence = [*residence, recurrence]
    run_ids: list[str] = []
    for seq_index, ep in enumerate(sequence):
        is_recurrence = seq_index == len(sequence) - 1
        if is_recurrence:
            for branch_id in (BRANCH_C, BRANCH_A):
                _apply_hot_operation(
                    ledger,
                    hot[branch_id],
                    branch_id=branch_id,
                    record_id=carried.record_id,
                    recommendation="rematerialize",
                    episode_id=ep.episode_id,
                    seq_index=seq_index,
                    event_index=event_index,
                    effective_before_seq=seq_index,
                    needed_by=ep.episode_id,
                )
                event_index += 1
            ledger.write({
                "kind": "body0_intervention",
                "branch_id": BRANCH_A,
                "seq_index": seq_index,
                "intervention": "suppress_earned_offer",
                "record_id": carried.record_id,
                "declared_at_population": True,
            })
            ledger.write({
                "kind": "body0_intervention",
                "branch_id": BRANCH_X,
                "seq_index": seq_index,
                "intervention": "suppress_rematerialization",
                "record_id": carried.record_id,
                "declared_at_population": True,
            })
            _write_projection(
                ledger,
                stage="post_rematerialization",
                records=lineage_records,
                authority_seed=authority_seed,
                earned_record_id=carried.record_id,
                seq_index=seq_index,
            )

        branch_configs: list[BranchConfig] = []
        for branch_id in BRANCHES:
            candidate_ids = hot[branch_id].get_hot()
            if is_recurrence and branch_id == BRANCH_A:
                candidate_ids = frozenset(candidate_ids - {carried.record_id})
            branch_configs.append(
                BranchConfig(
                    branch_id,
                    memory="governed",
                    authority_path=str(sidecars[branch_id][0]),
                    inherited_record_ids=candidate_ids,
                    top_k=int(manifest["top_k"]),
                    recency_weight=float(manifest["recency_weight"]),
                    similarity_backend="lexical_tfidf",
                )
            )

        run_id = uuid.uuid4().hex[:12]
        for branch_id in BRANCHES:
            cost = hot[branch_id].cost(lineage_records)
            ledger.write({
                "kind": "body0_hot_store_cost",
                "run_id": run_id,
                "branch_id": branch_id,
                "episode_id": ep.episode_id,
                "seq_index": seq_index,
                "pre_answer": True,
                "primary_cost_metric": manifest["primary_cost_metric"],
                **cost,
            })
        result = run_fork_group(
            ep,
            branch_configs,
            ledger,
            engine_backend=engine_backend,
            model=model,
            base_url=base_url,
            run_id=run_id,
            skip_ablation=True,
            freeze_authority=True,
        )
        run_ids.append(result["run_id"])

    post_decision_projection = _write_projection(
        ledger,
        stage="post_decision",
        records=lineage_records,
        authority_seed=authority_seed,
        earned_record_id=carried.record_id,
        seq_index=len(sequence) - 1,
    )
    ledger.write({
        "kind": "body0_attack_result",
        "protected_projection_after": protected_projection_hash(post_decision_projection),
        "protected_projection_unchanged": (
            pre_attack == protected_projection_hash(post_decision_projection)
        ),
        "checked_after_attacker_exposed_answer_runs": True,
    })

    expected_projection = protected_projection(
        lineage_records, authority_seed, carried.record_id
    )
    ledger.write({
        "kind": "body0_run_meta",
        "sequence_id": sequence_id,
        "fixture_id": manifest["fixture_id"],
        "manifest_path": str(manifest_path.relative_to(ROOT)),
        "manifest_sha256": admission["manifest_sha256"],
        "frozen_packet_sha256": packet_sha256(manifest),
        "e1_episode_id": e1.episode_id,
        "e1_run_id": e1_result["run_id"],
        "sequence_episode_ids": [ep.episode_id for ep in sequence],
        "sequence_run_ids": run_ids,
        "block_labels": list(manifest["block_labels"]),
        "branches": {
            "reference": BRANCH_R,
            "composed": BRANCH_C,
            "earned_ablation": BRANCH_A,
            "recovery_ablation": BRANCH_X,
        },
        "earned_record_id": carried.record_id,
        "all_record_ids": sorted(all_ids),
        "lineage_records": [record_dict(r) for r in lineage_records],
        "record_texts": record_texts,
        "authority_seed": authority_seed,
        "protected_projection": expected_projection,
        "protected_projection_sha256": protected_projection_hash(expected_projection),
        "resident_config_digest": resident_digest,
        "primary_cost_metric": manifest["primary_cost_metric"],
        "hot_paths": {bid: str(sidecars[bid][1]) for bid in BRANCHES},
        "authority_paths": {bid: str(sidecars[bid][0]) for bid in BRANCHES},
        "evidence_class": (
            "wire_integration_only" if engine_backend == "mock"
            else "behavioral_candidate"
        ),
    })
    print(
        f"{sequence_id}: Body-0 sequence complete "
        f"({engine_backend}; {len(sequence)} post-prefix episodes)"
    )
    print(f"  ledger: {ledger.path}")
    return ledger.path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Body-0 composition audit")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--engine", default="mock", choices=["mock", "claude", "local"])
    parser.add_argument("--model", default="mock-engine-v1")
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument("--runs-dir", default=str(ROOT / "runs" / "body0"))
    parser.add_argument("--probe-result")
    args = parser.parse_args()
    try:
        run_body0(
            Path(args.manifest),
            engine_backend=args.engine,
            model=args.model,
            base_url=args.base_url,
            runs_dir=Path(args.runs_dir),
            probe_result=_load_probe(Path(args.probe_result) if args.probe_result else None),
        )
    except (Body0ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
