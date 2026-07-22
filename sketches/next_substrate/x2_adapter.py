"""Reversible X2-to-Body-Core v0.2 wire adapter.

The adapter carries each X2 field visibly in a typed Body Core source event,
adds separate policy-profile events for hot/cold transitions, and projects the
original X2 ledger back for the unchanged ``score_prune`` oracle. It is
integration engineering only, not a new X2 finding or a reconstruction-cost
claim.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from harness.score_prune import score_prune

from .correspondence import index_bound_state_receipts
from .core import LineageStore, ReplayRefusal, Writer


ADAPTER_VERSION = "x2-body-core-adapter-v0.2"
SOURCE_EVENT_KIND = "x2_source_row_carried"
POLICY_EVENT_KIND = "placement_changed"
PINNED_NON_SEMANTIC_FIELDS = frozenset({"ts"})
ADAPTER_PAYLOAD_FIELDS = frozenset(
    {"source_row_index", "source_kind", "source_row_digest"}
)
FORBIDDEN_ESCROW_FIELDS = frozenset({"original_x2_row", "raw_row", "row_blob"})

# Closed-ledger transport is deliberately finite. New row kinds or fields need
# an explicit adapter revision instead of disappearing into a generic JSON blob.
X2_ROW_FIELD_CONTRACT: dict[str, frozenset[str]] = {
    "ablation_run": frozenset(
        {
            "ablated_oracle_scores",
            "ablated_record_id",
            "ablation_samples",
            "baseline_oracle_score",
            "branch_id",
            "branch_output",
            "completion_tokens",
            "episode_id",
            "fork_group_id",
            "latency_ms",
            "oracle_score",
            "outcome_changed",
            "outcome_changed_fraction",
            "prompt_tokens",
            "run_id",
            "ts",
        }
    ),
    "branch_run": frozenset(
        {
            "ablation_calls",
            "branch_id",
            "branch_output",
            "completion_tokens",
            "episode_id",
            "fork_group_id",
            "governance_steps",
            "latency_ms",
            "oracle",
            "prompt_tokens",
            "run_id",
            "ts",
        }
    ),
    "diff_outcome": frozenset(
        {
            "authority_updates",
            "branches",
            "diff_summary",
            "diverged",
            "episode_id",
            "expected_winner_condition",
            "fork_group_id",
            "oracle_scores",
            "run_id",
            "ts",
        }
    ),
    "fixture_attestation": frozenset(
        {
            "attested_at",
            "attested_by",
            "corpus_entry",
            "corpus_identity_pin",
            "engine_cutoffs_disclosed",
            "fictional",
            "fixture_id",
            "out_of_weights",
            "ts",
        }
    ),
    "fixture_gate_result": frozenset(
        {"checks", "gate_open", "manifest_hash", "n_checks", "n_passed", "ts"}
    ),
    "hot_store_cost": frozenset(
        {
            "branch_id",
            "episode_id",
            "hot_record_count",
            "hot_tokens",
            "materialized_bytes",
            "rematerialize_steps",
            "run_id",
            "seq_index",
            "ts",
        }
    ),
    "offer": frozenset(
        {
            "attention_cost_tokens",
            "branch_id",
            "episode_id",
            "fork_group_id",
            "predeclared_usage",
            "reason",
            "record_id",
            "run_id",
            "ts",
            "vocabulary_kind",
        }
    ),
    "prune": frozenset(
        {
            "branch_id",
            "episode_id",
            "event_index",
            "in_hot_after",
            "in_hot_before",
            "op",
            "prune_projection_ref",
            "record_id",
            "seq_index",
            "ts",
            "world_check",
            "world_check_ref",
        }
    ),
    "prune_projection": frozenset(
        {
            "authorized_basis",
            "branch_id",
            "episode_id",
            "event_index",
            "projection_ref",
            "recommendation",
            "seq_index",
            "ts",
            "world_check_ref",
        }
    ),
    "rematerialize": frozenset(
        {
            "branch_id",
            "episode_id",
            "event_index",
            "in_hot_after",
            "in_hot_before",
            "op",
            "prune_projection_ref",
            "reason",
            "record_id",
            "seq_index",
            "ts",
            "world_check",
            "world_check_ref",
        }
    ),
    "run_config": frozenset(
        {
            "branches",
            "cost_tiebreak_window",
            "disclosures",
            "engine_backend",
            "episode_id",
            "episode_overrides",
            "foreground_renderer_version",
            "fork_group_id",
            "model",
            "run_id",
            "similarity_backends",
            "ts",
        }
    ),
    "withholding": frozenset(
        {
            "branch_id",
            "episode_id",
            "fork_group_id",
            "predeclared_usage",
            "reason",
            "record_id",
            "run_id",
            "ts",
            "vocabulary_kind",
        }
    ),
    "x2_run_meta": frozenset(
        {
            "all_record_ids",
            "authority_frozen",
            "block_labels",
            "branches",
            "episode_ids",
            "fixture_id",
            "hot_paths",
            "primary_cost",
            "primary_cost_metric",
            "probe_episode_id",
            "probe_run_id",
            "record_texts",
            "seq_id",
            "top_k",
            "ts",
        }
    ),
}

ADAPTER_WRITER = Writer("x2-body-core-adapter-v0.2", "controller")
X2_OBSERVER = Writer("x2-ledger-observer-v0.2", "observer")


@dataclass(frozen=True)
class AdapterReceipt:
    source_rows: int
    core_rows: int
    source_digest: str
    projected_digest: str
    append_prefix_rows: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "adapter_version": ADAPTER_VERSION,
            "source_rows": self.source_rows,
            "core_rows": self.core_rows,
            "source_digest": self.source_digest,
            "projected_digest": self.projected_digest,
            # LineageStore validates all prior rows before each append. This is
            # the exact count of prior rows presented to that first validation
            # pass, not a latency metric or a full operation count.
            "append_prefix_rows": self.append_prefix_rows,
            "performance_boundary": (
                "deterministic prefix-row exposure; quadratic append/replay "
                "cost remains admitted; no optimization claim"
            ),
        }


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            raise ReplayRefusal(
                f"{path}: line {line_number}: blank lines are not permitted"
            )
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReplayRefusal(
                f"{path}: line {line_number}: invalid JSON: {exc.msg}"
            ) from exc
        if not isinstance(row, dict) or not isinstance(row.get("kind"), str):
            raise ReplayRefusal(f"{path}: line {line_number}: typed row required")
        rows.append(row)
    return rows


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _item_id(branch_id: str, record_id: str) -> str:
    return f"x2:{branch_id}:{record_id}"


def _source_payload(row: dict[str, Any], source_row_index: int) -> dict[str, Any]:
    allowed_fields = X2_ROW_FIELD_CONTRACT.get(row["kind"])
    if allowed_fields is None:
        raise ReplayRefusal(
            f"source row {source_row_index}: unsupported kind {row['kind']!r}"
        )
    unknown_fields = (set(row) - {"kind"}) - allowed_fields
    if unknown_fields:
        raise ReplayRefusal(
            f"source row {source_row_index}: undeclared fields {sorted(unknown_fields)}"
        )
    collisions = (set(row) - {"kind"}) & (
        ADAPTER_PAYLOAD_FIELDS | FORBIDDEN_ESCROW_FIELDS
    )
    if collisions:
        raise ReplayRefusal(
            f"source row {source_row_index}: reserved fields {sorted(collisions)}"
        )
    return {
        "source_row_index": source_row_index,
        "source_kind": row["kind"],
        "source_row_digest": _digest(row),
        **{key: value for key, value in row.items() if key != "kind"},
    }


def ingest_x2(source_path: Path, lineage_path: Path) -> AdapterReceipt:
    """Carry one X2 ledger into a new Body Core lineage."""
    source_path = Path(source_path)
    lineage_path = Path(lineage_path)
    if lineage_path.exists() and lineage_path.stat().st_size:
        raise ReplayRefusal(f"{lineage_path}: adapter requires an empty lineage")

    source_rows = _read_jsonl(source_path)
    meta = next((row for row in source_rows if row["kind"] == "x2_run_meta"), None)
    if meta is None:
        raise ReplayRefusal(f"{source_path}: x2_run_meta is required")
    branches = meta.get("branches")
    record_ids = meta.get("all_record_ids")
    record_texts = meta.get("record_texts")
    if (
        not isinstance(branches, dict)
        or not isinstance(record_ids, list)
        or not isinstance(record_texts, dict)
    ):
        raise ReplayRefusal(f"{source_path}: incomplete X2 lineage metadata")
    branch_ids = list(branches.values())
    if len(branch_ids) != len(set(branch_ids)):
        raise ReplayRefusal(f"{source_path}: duplicate X2 branch ids")
    if not set(record_ids) <= set(record_texts):
        raise ReplayRefusal(f"{source_path}: record_texts does not cover lineage")

    store = LineageStore(lineage_path)
    started = store.append(
        "x2_adapter_started",
        writer=ADAPTER_WRITER,
        authority="wire_diagnostic",
        payload={
            "adapter_version": ADAPTER_VERSION,
            "source_digest": _digest(source_rows),
            "source_rows": len(source_rows),
            "claim_boundary": "wire integration only; unchanged X2 scorer remains oracle",
        },
    )

    placements: dict[str, str] = {}
    for branch_id in branch_ids:
        for record_id in record_ids:
            warrant = store.append(
                "x2_record_declared",
                writer=X2_OBSERVER,
                authority="external_observation",
                causal_parent_ids=[started["event_id"]],
                payload={
                    "branch_id": branch_id,
                    "record_id": record_id,
                    "record_text_digest": _digest(record_texts[record_id]),
                },
            )
            item_id = _item_id(branch_id, record_id)
            store.append(
                "state_item_admitted",
                writer=ADAPTER_WRITER,
                authority="controller_transition",
                causal_parent_ids=[warrant["event_id"]],
                warrant_event_ids=[warrant["event_id"]],
                payload={
                    "item_id": item_id,
                    "item_kind": "x2_materialized_record",
                    "status": "active",
                    "placement": "hot",
                    "detail": {
                        "branch_id": branch_id,
                        "record_id": record_id,
                    },
                },
            )
            placements[item_id] = "hot"

    prior_source_event_id = started["event_id"]
    for source_row_index, row in enumerate(source_rows):
        carried = store.append(
            SOURCE_EVENT_KIND,
            writer=X2_OBSERVER,
            authority="external_observation",
            causal_parent_ids=[prior_source_event_id],
            payload=_source_payload(row, source_row_index),
        )
        prior_source_event_id = carried["event_id"]
        if row["kind"] not in {"prune", "rematerialize"}:
            continue
        branch_id = row.get("branch_id")
        record_id = row.get("record_id")
        item_id = _item_id(branch_id, record_id)
        if item_id not in placements:
            raise ReplayRefusal(
                f"source row {source_row_index}: operation references unknown item"
            )
        expected_from = "hot" if row["kind"] == "prune" else "cold"
        expected_to = "cold" if row["kind"] == "prune" else "hot"
        if placements[item_id] != expected_from:
            raise ReplayRefusal(
                f"source row {source_row_index}: {row['kind']} expected "
                f"{expected_from}, found {placements[item_id]}"
            )
        if row.get("in_hot_before") is not (expected_from == "hot"):
            raise ReplayRefusal(
                f"source row {source_row_index}: in_hot_before disagrees with operation"
            )
        if row.get("in_hot_after") is not (expected_to == "hot"):
            raise ReplayRefusal(
                f"source row {source_row_index}: in_hot_after disagrees with operation"
            )
        store.append(
            POLICY_EVENT_KIND,
            writer=ADAPTER_WRITER,
            authority="controller_transition",
            causal_parent_ids=[carried["event_id"]],
            payload={
                "item_id": item_id,
                "from_placement": expected_from,
                "to_placement": expected_to,
                "reason": "X2 lineage operation carried through provisional policy",
                "source_event_id": carried["event_id"],
                "source_row_index": source_row_index,
                "source_kind": row["kind"],
            },
        )
        placements[item_id] = expected_to

    projected = project_x2(store)
    core_rows = len(store.rows())
    return AdapterReceipt(
        source_rows=len(source_rows),
        core_rows=core_rows,
        source_digest=_digest(source_rows),
        projected_digest=_digest(projected),
        append_prefix_rows=core_rows * (core_rows - 1) // 2,
    )


def project_x2(store_or_path: LineageStore | Path) -> list[dict[str, Any]]:
    """Reconstruct the X2 ledger after Core replay and policy consistency checks."""
    store = (
        store_or_path
        if isinstance(store_or_path, LineageStore)
        else LineageStore(Path(store_or_path))
    )
    result = store.replay()
    starts = [row for row in result.rows if row["kind"] == "x2_adapter_started"]
    if len(starts) != 1:
        raise ReplayRefusal("X2 projection requires exactly one adapter start")
    start_payload = starts[0]["payload"]
    x2_items = {
        item_id: item
        for item_id, item in result.views.state_items.items()
        if item.item_kind == "x2_materialized_record"
    }
    unhealthy = [
        item_id
        for item_id, item in x2_items.items()
        if item.status != "active"
        or any(
            result.views.warrant_health.get(warrant) != "current"
            for warrant in item.warrant_event_ids
        )
    ]
    if unhealthy:
        raise ReplayRefusal(
            f"X2 projection refused: unhealthy carried state {sorted(unhealthy)}"
        )

    bindings = index_bound_state_receipts(
        result.rows,
        source_event_kind=SOURCE_EVENT_KIND,
        receipt_event_kinds={POLICY_EVENT_KIND},
        affected_item_ids=x2_items,
        coordinate_fields=("source_row_index", "source_kind"),
        context="X2",
    )
    policy_by_source = bindings.receipts_by_source

    projected_by_index: dict[int, dict[str, Any]] = {}
    for event in result.rows:
        if event["kind"] != SOURCE_EVENT_KIND:
            continue
        payload = event["payload"]
        source_row_index = payload.get("source_row_index")
        source_kind = payload.get("source_kind")
        if (
            not isinstance(source_row_index, int)
            or isinstance(source_row_index, bool)
            or not isinstance(source_kind, str)
        ):
            raise ReplayRefusal(f"{event['event_id']}: invalid source coordinates")
        row = {
            "kind": source_kind,
            **{
                key: value
                for key, value in payload.items()
                if key not in ADAPTER_PAYLOAD_FIELDS
            },
        }
        if payload.get("source_row_digest") != _digest(row):
            raise ReplayRefusal(f"{event['event_id']}: source row digest mismatch")
        if source_row_index in projected_by_index:
            raise ReplayRefusal(f"duplicate source row index {source_row_index}")
        projected_by_index[source_row_index] = row

        receipts = policy_by_source.get(event["event_id"], [])
        if source_kind in {"prune", "rematerialize"}:
            if len(receipts) != 1:
                raise ReplayRefusal(
                    f"{event['event_id']}: X2 operation requires one policy receipt"
                )
            receipt = receipts[0]["payload"]
            expected_from = "hot" if source_kind == "prune" else "cold"
            expected_to = "cold" if source_kind == "prune" else "hot"
            if (
                receipt.get("item_id")
                != _item_id(row.get("branch_id"), row.get("record_id"))
                or receipt.get("from_placement") != expected_from
                or receipt.get("to_placement") != expected_to
            ):
                raise ReplayRefusal(
                    f"{event['event_id']}: policy receipt disagrees with X2 operation"
                )
        elif receipts:
            raise ReplayRefusal(
                f"{event['event_id']}: non-operation has a placement receipt"
            )

    indexes = sorted(projected_by_index)
    if indexes != list(range(len(indexes))):
        raise ReplayRefusal(f"non-contiguous source row indexes: {indexes}")
    projected = [projected_by_index[index] for index in indexes]
    if start_payload.get("source_rows") != len(projected):
        raise ReplayRefusal("projected row count disagrees with adapter start")
    if start_payload.get("source_digest") != _digest(projected):
        raise ReplayRefusal("projected source digest disagrees with adapter start")

    meta = next((row for row in projected if row["kind"] == "x2_run_meta"), None)
    if meta is None:
        raise ReplayRefusal("projected X2 lineage lacks x2_run_meta")
    expected_placements = {
        _item_id(branch_id, record_id): "hot"
        for branch_id in meta["branches"].values()
        for record_id in meta["all_record_ids"]
    }
    for row in projected:
        if row["kind"] not in {"prune", "rematerialize"}:
            continue
        item_id = _item_id(row.get("branch_id"), row.get("record_id"))
        expected_from = "hot" if row["kind"] == "prune" else "cold"
        expected_to = "cold" if row["kind"] == "prune" else "hot"
        if expected_placements.get(item_id) != expected_from:
            raise ReplayRefusal(
                f"projected X2 operation history is inconsistent for {item_id}"
            )
        expected_placements[item_id] = expected_to
    placement_mismatches = [
        item_id
        for item_id, expected in expected_placements.items()
        if item_id not in x2_items or x2_items[item_id].placement != expected
    ]
    if placement_mismatches:
        raise ReplayRefusal(
            "terminal Core placement disagrees with bound X2 operations: "
            f"{sorted(placement_mismatches)}"
        )
    return projected


def canonical_verdicts(verdicts: list[dict[str, Any]]) -> str:
    """Canonical scorer output under the pinned, predeclared ``ts`` exception."""

    def strip(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: strip(item)
                for key, item in value.items()
                if key not in PINNED_NON_SEMANTIC_FIELDS
            }
        if isinstance(value, list):
            return [strip(item) for item in value]
        return value

    return _canonical_json(strip(verdicts))


def verify_unchanged_scorer_round_trip(
    source_path: Path, lineage_path: Path, projected_path: Path
) -> AdapterReceipt:
    """Ingest, project, and require unchanged X2 scorer equality."""
    receipt = ingest_x2(source_path, lineage_path)
    projected = project_x2(lineage_path)
    _write_jsonl(projected_path, projected)
    before = canonical_verdicts(score_prune(source_path))
    after = canonical_verdicts(score_prune(projected_path))
    if before != after:
        raise ReplayRefusal("unchanged X2 scorer output changed after Core round trip")
    return receipt
