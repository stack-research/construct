"""Reversible M3-to-Body-Core v0.2 wire adapter.

Track A carries foreground/live-channel attack ledgers and attaches source-bound
audit receipts to adapter-claimed episode records. Track B carries ingestion
rows without minting Core state. The unchanged ``harness.score_redteam`` CLI
remains the only verdict authority.

This is wire/integration preservation only. It does not close an M3 breach,
authenticate Core writers, or create new red-team evidence.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from harness.ledger import Ledger

from .correspondence import index_bound_state_receipts
from .core import LineageStore, ReplayRefusal, Writer
from .x2_adapter import canonical_verdicts


REPO = Path(__file__).resolve().parents[2]
ADAPTER_VERSION = "m3-body-core-adapter-v0.1"
SOURCE_INDEX_SHA256 = (
    "81b1a480d572a89e8a8dfab1baef84af8efb9eebdabebd13808d2451543a571d"
)
DEFAULT_SOURCE_INDEX = REPO / "notes/body_core_m3_adapter_source_index.json"

START_EVENT_KIND = "m3_adapter_started"
SOURCE_EVENT_KIND = "m3_source_row_carried"
DECLARATION_EVENT_KIND = "m3_episode_record_declared"
RECEIPT_EVENT_KIND = "m3_boundary_decision_receipt"
ITEM_KIND = "m3_materialized_record"

TRACK_A_SURFACES = frozenset({"foreground_text", "live_channel_spoof"})
TRACK_B_SURFACE = "ingestion_write"
DECISION_KINDS = frozenset({"offer", "withholding"})
FORBIDDEN_STATE_EVENT_KINDS = frozenset(
    {"state_item_transition", "placement_changed", "metabolic_event"}
)

ADAPTER_PAYLOAD_FIELDS = frozenset(
    {"source_row_index", "source_kind", "source_row_digest"}
)
FORBIDDEN_ESCROW_FIELDS = frozenset(
    {"original_m3_row", "original_source_row", "raw_row", "row_blob"}
)

M3_ROW_FIELD_CONTRACT: dict[str, frozenset[str]] = {
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
    "attack": frozenset(
        {
            "allowlist_ok",
            "attack_id",
            "attack_surface",
            "attacked_run_id",
            "attacker_id",
            "clean_run_id",
            "corpus_scope",
            "episode_id",
            "payload_digest",
            "resident_branch",
            "resident_config_digest",
            "store_digest",
            "target_record_ids",
            "ts",
        }
    ),
    "ingestion_attempt": frozenset(
        {
            "asserted_trust",
            "attack_id",
            "episode_id",
            "forged_record_id",
            "minted",
            "poison_offered",
            "poisoned_record_id",
            "refusal_reason",
            "ts",
        }
    ),
    "cell_verdict": frozenset(
        {
            "attack_id",
            "attack_surface",
            "cell",
            "corpus_scope",
            "engine_backend",
            "episode_id",
            "evidence",
            "model",
            "ts",
            "verdict",
            "wire_test",
        }
    ),
}

START_PAYLOAD_FIELDS = frozenset(
    {
        "adapter_version",
        "source_index_digest",
        "source_ledger_digest",
        "source_rows",
        "episode_digest",
        "episode_id",
        "attack_id",
        "attack_surface",
        "scorer_digest",
        "claim_boundary",
    }
)
DECLARATION_PAYLOAD_FIELDS = frozenset(
    {"episode_id", "episode_digest", "record_id", "record_digest"}
)
ADMISSION_PAYLOAD_FIELDS = frozenset(
    {"item_id", "item_kind", "status", "placement", "detail"}
)
RECEIPT_PAYLOAD_FIELDS = frozenset(
    {
        "item_id",
        "source_event_id",
        "source_row_index",
        "source_kind",
        "run_id",
        "branch_id",
        "record_id",
        "decision",
        "source_reason",
    }
)

ADAPTER_WRITER = Writer(ADAPTER_VERSION, "controller")
M3_OBSERVER = Writer("m3-ledger-observer-v0.1", "observer")


@dataclass(frozen=True)
class M3AdapterReceipt:
    attack_id: str
    attack_surface: str
    source_rows: int
    core_rows: int
    source_digest: str
    projected_digest: str
    source_index_digest: str
    episode_digest: str
    append_prefix_rows: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "adapter_version": ADAPTER_VERSION,
            "attack_id": self.attack_id,
            "attack_surface": self.attack_surface,
            "source_rows": self.source_rows,
            "core_rows": self.core_rows,
            "source_digest": self.source_digest,
            "projected_digest": self.projected_digest,
            "source_index_digest": self.source_index_digest,
            "episode_digest": self.episode_digest,
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


def _file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _jsonl_text(rows: Iterable[dict[str, Any]]) -> str:
    return "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)


def _jsonl_digest(rows: Iterable[dict[str, Any]]) -> str:
    return hashlib.sha256(_jsonl_text(rows).encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReplayRefusal(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ReplayRefusal(f"{path}: JSON object required")
    return value


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
    path.write_text(_jsonl_text(rows), encoding="utf-8")


def _load_source_index(source_index_path: Path) -> dict[str, Any]:
    source_index_path = Path(source_index_path)
    actual_digest = _file_digest(source_index_path)
    if actual_digest != SOURCE_INDEX_SHA256:
        raise ReplayRefusal(
            "M3 source index digest mismatch: "
            f"expected {SOURCE_INDEX_SHA256}, found {actual_digest}"
        )
    source_index = _read_json(source_index_path)
    if (
        source_index.get("claim_boundary")
        != "wire_integration_preservation_only"
        or not isinstance(source_index.get("ledgers"), list)
        or not isinstance(source_index.get("episodes"), dict)
        or not isinstance(source_index.get("component_pins"), dict)
    ):
        raise ReplayRefusal("M3 source index has an unsupported shape")
    scorer_path = REPO / "harness/score_redteam.py"
    expected_scorer = source_index["component_pins"].get(
        "harness/score_redteam.py"
    )
    if _file_digest(scorer_path) != expected_scorer:
        raise ReplayRefusal("unchanged M3 scorer digest mismatch")
    return source_index


def _source_payload(row: dict[str, Any], source_row_index: int) -> dict[str, Any]:
    allowed_fields = M3_ROW_FIELD_CONTRACT.get(row["kind"])
    if allowed_fields is None:
        raise ReplayRefusal(
            f"source row {source_row_index}: unsupported kind {row['kind']!r}"
        )
    unknown_fields = (set(row) - {"kind"}) - allowed_fields
    if unknown_fields:
        raise ReplayRefusal(
            f"source row {source_row_index}: undeclared fields "
            f"{sorted(unknown_fields)}"
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


def _one_required(rows: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    found = [row for row in rows if row["kind"] == kind]
    if len(found) != 1:
        raise ReplayRefusal(f"M3 source requires exactly one {kind} row")
    return found[0]


def _item_id(attack_id: str, record_id: str) -> str:
    return f"m3:{attack_id}:{record_id}"


def _episode_records(episode: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = episode.get("records")
    if not isinstance(records, list) or not records:
        raise ReplayRefusal("M3 episode requires a non-empty records list")
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        record_id = record.get("record_id") if isinstance(record, dict) else None
        if not isinstance(record_id, str) or not record_id or record_id in indexed:
            raise ReplayRefusal("M3 episode record ids must be unique non-empty strings")
        indexed[record_id] = record
    return indexed


def _indexed_ledger(
    source_index: dict[str, Any], attack_id: str
) -> dict[str, Any]:
    found = [
        entry
        for entry in source_index["ledgers"]
        if Path(entry.get("path", "")).stem == attack_id
    ]
    if len(found) != 1:
        raise ReplayRefusal(f"attack {attack_id!r} is not uniquely indexed")
    return found[0]


def _validate_source_semantics(
    rows: list[dict[str, Any]],
    episode: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    for source_row_index, row in enumerate(rows):
        _source_payload(row, source_row_index)
    attack = _one_required(rows, "attack")
    attack_id = attack.get("attack_id")
    surface = attack.get("attack_surface")
    episode_id = episode.get("episode_id")
    if not isinstance(attack_id, str) or not attack_id:
        raise ReplayRefusal("M3 attack_id is required")
    if surface not in TRACK_A_SURFACES | {TRACK_B_SURFACE}:
        raise ReplayRefusal(f"unsupported M3 attack surface {surface!r}")
    if attack.get("episode_id") != episode_id:
        raise ReplayRefusal("M3 attack and episode ids disagree")
    records = _episode_records(episode)

    decision_rows = [row for row in rows if row["kind"] in DECISION_KINDS]
    if surface in TRACK_A_SURFACES:
        clean_run_id = attack.get("clean_run_id")
        attacked_run_id = attack.get("attacked_run_id")
        resident_branch = attack.get("resident_branch")
        if (
            not isinstance(clean_run_id, str)
            or not clean_run_id
            or not isinstance(attacked_run_id, str)
            or not attacked_run_id
            or clean_run_id == attacked_run_id
            or not isinstance(resident_branch, str)
            or not resident_branch
        ):
            raise ReplayRefusal("Track-A attack requires two runs and a resident branch")
        run_configs = [row for row in rows if row["kind"] == "run_config"]
        if {row.get("run_id") for row in run_configs} != {
            clean_run_id,
            attacked_run_id,
        }:
            raise ReplayRefusal("Track-A run configs disagree with the attack pair")
        for row in decision_rows:
            if (
                row.get("run_id") not in {clean_run_id, attacked_run_id}
                or row.get("branch_id") != resident_branch
            ):
                raise ReplayRefusal("Track-A boundary decision is outside the attack pair")
            if row.get("record_id") not in records:
                raise ReplayRefusal(
                    "Track-A boundary decision names a record absent from the episode"
                )
    else:
        if decision_rows:
            raise ReplayRefusal("Track-B source must not contain boundary decisions")
        _one_required(rows, "ingestion_attempt")
    return attack, records


def _preflight(
    source_path: Path,
    episode_path: Path,
    source_index_path: Path,
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
    dict[str, dict[str, Any]],
    dict[str, Any],
]:
    source_rows = _read_jsonl(source_path)
    episode = _read_json(episode_path)
    attack, records = _validate_source_semantics(source_rows, episode)
    source_index = _load_source_index(source_index_path)
    indexed = _indexed_ledger(source_index, attack["attack_id"])
    indexed_episode = source_index["episodes"].get(indexed.get("episode"))
    if not isinstance(indexed_episode, dict):
        raise ReplayRefusal("indexed M3 episode pin is missing")
    if indexed.get("rows") != len(source_rows):
        raise ReplayRefusal("M3 source row count disagrees with source index")
    if indexed.get("attack_surface") != attack.get("attack_surface"):
        raise ReplayRefusal("M3 attack surface disagrees with source index")
    if _file_digest(source_path) != indexed.get("sha256"):
        raise ReplayRefusal("M3 source ledger digest disagrees with source index")
    if _file_digest(episode_path) != indexed_episode.get("sha256"):
        raise ReplayRefusal("M3 episode digest disagrees with source index")
    if episode.get("episode_id") != indexed_episode.get("episode_id"):
        raise ReplayRefusal("M3 episode id disagrees with source index")
    return source_rows, episode, attack, records, source_index


def ingest_m3(
    source_path: Path,
    episode_path: Path,
    lineage_path: Path,
    source_index_path: Path = DEFAULT_SOURCE_INDEX,
) -> M3AdapterReceipt:
    """Carry one indexed closed M3 ledger into a fresh Body Core lineage."""
    source_path = Path(source_path)
    episode_path = Path(episode_path)
    lineage_path = Path(lineage_path)
    if lineage_path.exists() and lineage_path.stat().st_size:
        raise ReplayRefusal(f"{lineage_path}: adapter requires an empty lineage")
    source_rows, episode, attack, records, source_index = _preflight(
        source_path, episode_path, source_index_path
    )
    source_digest = _file_digest(source_path)
    episode_digest = _file_digest(episode_path)
    scorer_digest = source_index["component_pins"]["harness/score_redteam.py"]

    store = LineageStore(lineage_path)
    started = store.append(
        START_EVENT_KIND,
        writer=ADAPTER_WRITER,
        authority="wire_diagnostic",
        payload={
            "adapter_version": ADAPTER_VERSION,
            "source_index_digest": SOURCE_INDEX_SHA256,
            "source_ledger_digest": source_digest,
            "source_rows": len(source_rows),
            "episode_digest": episode_digest,
            "episode_id": episode["episode_id"],
            "attack_id": attack["attack_id"],
            "attack_surface": attack["attack_surface"],
            "scorer_digest": scorer_digest,
            "claim_boundary": "wire integration preservation only",
        },
    )

    if attack["attack_surface"] in TRACK_A_SURFACES:
        for record_id, record in records.items():
            declared = store.append(
                DECLARATION_EVENT_KIND,
                writer=M3_OBSERVER,
                authority="external_observation",
                causal_parent_ids=[started["event_id"]],
                payload={
                    "episode_id": episode["episode_id"],
                    "episode_digest": episode_digest,
                    "record_id": record_id,
                    "record_digest": _digest(record),
                },
            )
            store.append(
                "state_item_admitted",
                writer=ADAPTER_WRITER,
                authority="controller_transition",
                causal_parent_ids=[declared["event_id"]],
                warrant_event_ids=[declared["event_id"]],
                payload={
                    "item_id": _item_id(attack["attack_id"], record_id),
                    "item_kind": ITEM_KIND,
                    "status": "active",
                    "placement": "hot",
                    "detail": {
                        "episode_id": episode["episode_id"],
                        "record_id": record_id,
                        "episode_digest": episode_digest,
                    },
                },
            )

    prior_source_event_id = started["event_id"]
    for source_row_index, row in enumerate(source_rows):
        carried = store.append(
            SOURCE_EVENT_KIND,
            writer=M3_OBSERVER,
            authority="external_observation",
            causal_parent_ids=[prior_source_event_id],
            payload=_source_payload(row, source_row_index),
        )
        prior_source_event_id = carried["event_id"]
        if row["kind"] not in DECISION_KINDS:
            continue
        store.append(
            RECEIPT_EVENT_KIND,
            writer=ADAPTER_WRITER,
            authority="wire_diagnostic",
            causal_parent_ids=[carried["event_id"]],
            payload={
                "item_id": _item_id(attack["attack_id"], row["record_id"]),
                "source_event_id": carried["event_id"],
                "source_row_index": source_row_index,
                "source_kind": row["kind"],
                "run_id": row["run_id"],
                "branch_id": row["branch_id"],
                "record_id": row["record_id"],
                "decision": "offer" if row["kind"] == "offer" else "withhold",
                "source_reason": row["reason"],
            },
        )

    projected = project_m3(store, episode_path, source_index_path)
    core_rows = len(store.rows())
    return M3AdapterReceipt(
        attack_id=attack["attack_id"],
        attack_surface=attack["attack_surface"],
        source_rows=len(source_rows),
        core_rows=core_rows,
        source_digest=source_digest,
        projected_digest=_jsonl_digest(projected),
        source_index_digest=SOURCE_INDEX_SHA256,
        episode_digest=episode_digest,
        append_prefix_rows=core_rows * (core_rows - 1) // 2,
    )


def _require_route(
    row: dict[str, Any], writer: Writer, authority: str, context: str
) -> None:
    if row["writer"] != writer.as_dict() or row["authority"] != authority:
        raise ReplayRefusal(f"{row['event_id']}: {context} writer/authority mismatch")


def _project_source_rows(
    rows: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    projected_by_index: dict[int, dict[str, Any]] = {}
    carried_by_id: dict[str, dict[str, Any]] = {}
    for event in rows:
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
        carried_by_id[event["event_id"]] = event
    indexes = sorted(projected_by_index)
    if indexes != list(range(len(indexes))):
        raise ReplayRefusal(f"non-contiguous source row indexes: {indexes}")
    return [projected_by_index[index] for index in indexes], carried_by_id


def project_m3(
    store_or_path: LineageStore | Path,
    episode_path: Path,
    source_index_path: Path = DEFAULT_SOURCE_INDEX,
) -> list[dict[str, Any]]:
    """Reconstruct an M3 ledger after Core replay and adapter checks."""
    store = (
        store_or_path
        if isinstance(store_or_path, LineageStore)
        else LineageStore(Path(store_or_path))
    )
    result = store.replay()
    source_index = _load_source_index(source_index_path)
    episode_path = Path(episode_path)
    episode = _read_json(episode_path)
    episode_digest = _file_digest(episode_path)

    starts = [row for row in result.rows if row["kind"] == START_EVENT_KIND]
    if len(starts) != 1:
        raise ReplayRefusal("M3 projection requires exactly one adapter start")
    started = starts[0]
    _require_route(started, ADAPTER_WRITER, "wire_diagnostic", "M3 start")
    if set(started["payload"]) != START_PAYLOAD_FIELDS:
        raise ReplayRefusal("M3 adapter start has an undeclared payload shape")
    start_payload = started["payload"]
    if (
        start_payload.get("adapter_version") != ADAPTER_VERSION
        or start_payload.get("source_index_digest") != SOURCE_INDEX_SHA256
        or start_payload.get("episode_digest") != episode_digest
        or start_payload.get("episode_id") != episode.get("episode_id")
        or start_payload.get("scorer_digest")
        != source_index["component_pins"]["harness/score_redteam.py"]
        or start_payload.get("claim_boundary")
        != "wire integration preservation only"
    ):
        raise ReplayRefusal("M3 adapter start pin mismatch")

    projected, carried_by_id = _project_source_rows(result.rows)
    attack, records = _validate_source_semantics(projected, episode)
    indexed = _indexed_ledger(source_index, attack["attack_id"])
    indexed_episode = source_index["episodes"].get(indexed.get("episode"), {})
    if (
        start_payload.get("attack_id") != attack.get("attack_id")
        or start_payload.get("attack_surface") != attack.get("attack_surface")
        or start_payload.get("source_rows") != len(projected)
        or start_payload.get("source_ledger_digest") != _jsonl_digest(projected)
        or indexed.get("rows") != len(projected)
        or indexed.get("sha256") != _jsonl_digest(projected)
        or indexed.get("attack_surface") != attack.get("attack_surface")
        or indexed_episode.get("sha256") != episode_digest
        or indexed_episode.get("episode_id") != episode.get("episode_id")
    ):
        raise ReplayRefusal("projected M3 source disagrees with adapter start or index")

    adapter_kinds = {
        START_EVENT_KIND,
        SOURCE_EVENT_KIND,
        DECLARATION_EVENT_KIND,
        RECEIPT_EVENT_KIND,
    }
    for row in result.rows:
        kind = row["kind"]
        if kind == START_EVENT_KIND:
            _require_route(row, ADAPTER_WRITER, "wire_diagnostic", "M3 start")
        elif kind in {SOURCE_EVENT_KIND, DECLARATION_EVENT_KIND}:
            _require_route(row, M3_OBSERVER, "external_observation", kind)
        elif kind == RECEIPT_EVENT_KIND:
            _require_route(row, ADAPTER_WRITER, "wire_diagnostic", kind)
        elif kind.startswith("m3_") and kind not in adapter_kinds:
            raise ReplayRefusal(f"{row['event_id']}: unknown M3 adapter event kind")

    attack_id = attack["attack_id"]
    item_prefix = f"m3:{attack_id}:"
    track_a = attack["attack_surface"] in TRACK_A_SURFACES
    expected_item_ids = {
        _item_id(attack_id, record_id) for record_id in records
    } if track_a else set()

    declarations = [
        row for row in result.rows if row["kind"] == DECLARATION_EVENT_KIND
    ]
    admissions = [
        row
        for row in result.rows
        if row["kind"] == "state_item_admitted"
        and (
            row["payload"].get("item_kind") == ITEM_KIND
            or str(row["payload"].get("item_id", "")).startswith(item_prefix)
        )
    ]
    receipts = [row for row in result.rows if row["kind"] == RECEIPT_EVENT_KIND]

    if not track_a:
        if declarations or admissions or receipts or result.views.state_items:
            raise ReplayRefusal("Track B cannot mint Core state or boundary receipts")
        if any(row["kind"] in FORBIDDEN_STATE_EVENT_KINDS for row in result.rows):
            raise ReplayRefusal("Track B cannot carry state-affecting events")
        return projected

    declarations_by_record: dict[str, dict[str, Any]] = {}
    for declaration in declarations:
        payload = declaration["payload"]
        if set(payload) != DECLARATION_PAYLOAD_FIELDS:
            raise ReplayRefusal("M3 record declaration has an undeclared payload shape")
        record_id = payload.get("record_id")
        if record_id in declarations_by_record or record_id not in records:
            raise ReplayRefusal("M3 record declarations do not match the episode")
        if (
            declaration["causal_parent_ids"] != [started["event_id"]]
            or declaration["warrant_event_ids"]
            or payload.get("episode_id") != episode["episode_id"]
            or payload.get("episode_digest") != episode_digest
            or payload.get("record_digest") != _digest(records[record_id])
        ):
            raise ReplayRefusal("M3 record declaration disagrees with pinned episode")
        declarations_by_record[record_id] = declaration
    if set(declarations_by_record) != set(records):
        raise ReplayRefusal("M3 record declaration set is incomplete")

    admissions_by_item: dict[str, dict[str, Any]] = {}
    for admission in admissions:
        _require_route(
            admission, ADAPTER_WRITER, "controller_transition", "M3 admission"
        )
        payload = admission["payload"]
        if set(payload) != ADMISSION_PAYLOAD_FIELDS:
            raise ReplayRefusal("M3 admission has an undeclared payload shape")
        item_id = payload.get("item_id")
        if item_id in admissions_by_item or item_id not in expected_item_ids:
            raise ReplayRefusal("M3 admission set disagrees with claimed item ids")
        record_id = item_id.removeprefix(item_prefix)
        declaration = declarations_by_record[record_id]
        expected_detail = {
            "episode_id": episode["episode_id"],
            "record_id": record_id,
            "episode_digest": episode_digest,
        }
        if (
            payload.get("item_kind") != ITEM_KIND
            or payload.get("status") != "active"
            or payload.get("placement") != "hot"
            or payload.get("detail") != expected_detail
            or admission["causal_parent_ids"] != [declaration["event_id"]]
            or admission["warrant_event_ids"] != [declaration["event_id"]]
        ):
            raise ReplayRefusal("M3 admission disagrees with episode declaration")
        admissions_by_item[item_id] = admission
    if set(admissions_by_item) != expected_item_ids:
        raise ReplayRefusal("M3 claimed item admission set is incomplete")

    m3_items = {
        item_id: item
        for item_id, item in result.views.state_items.items()
        if item.item_kind == ITEM_KIND or item_id.startswith(item_prefix)
    }
    if set(m3_items) != expected_item_ids:
        raise ReplayRefusal("M3 materialized item set disagrees with pinned episode")
    forbidden = [
        row
        for row in result.rows
        if row["kind"] in FORBIDDEN_STATE_EVENT_KINDS
        and row["payload"].get("item_id") in expected_item_ids
    ]
    if forbidden:
        raise ReplayRefusal(
            "M3 does not authorize lifecycle, placement, or metabolic receipts"
        )
    unhealthy = [
        item_id
        for item_id, item in m3_items.items()
        if item.item_kind != ITEM_KIND
        or item.status != "active"
        or item.placement != "hot"
        or any(
            result.views.warrant_health.get(warrant) != "current"
            for warrant in item.warrant_event_ids
        )
    ]
    if unhealthy:
        raise ReplayRefusal(f"M3 projection refused unhealthy state {sorted(unhealthy)}")
    if any(
        receipt["payload"].get("item_id") not in expected_item_ids
        for receipt in receipts
    ):
        raise ReplayRefusal("M3 boundary receipt targets an unclaimed item")

    bindings = index_bound_state_receipts(
        result.rows,
        source_event_kind=SOURCE_EVENT_KIND,
        receipt_event_kinds={RECEIPT_EVENT_KIND},
        affected_item_ids=expected_item_ids,
        coordinate_fields=("source_row_index", "source_kind"),
        context="M3",
    )
    for receipt in receipts:
        if set(receipt["payload"]) != RECEIPT_PAYLOAD_FIELDS:
            raise ReplayRefusal("M3 boundary receipt has an undeclared payload shape")

    for source_event_id, source_event in carried_by_id.items():
        payload = source_event["payload"]
        source_kind = payload["source_kind"]
        bound = bindings.receipts_by_source.get(source_event_id, ())
        if source_kind in DECISION_KINDS:
            if len(bound) != 1:
                raise ReplayRefusal(
                    f"{source_event_id}: M3 decision requires exactly one receipt"
                )
            receipt = bound[0]
            receipt_payload = receipt["payload"]
            if receipt["causal_parent_ids"] != [source_event_id]:
                raise ReplayRefusal("M3 receipt has unexpected causal parents")
            expected = {
                "item_id": _item_id(attack_id, payload["record_id"]),
                "source_event_id": source_event_id,
                "source_row_index": payload["source_row_index"],
                "source_kind": source_kind,
                "run_id": payload["run_id"],
                "branch_id": payload["branch_id"],
                "record_id": payload["record_id"],
                "decision": "offer" if source_kind == "offer" else "withhold",
                "source_reason": payload["reason"],
            }
            if receipt_payload != expected:
                raise ReplayRefusal("M3 boundary receipt disagrees with source decision")
        elif bound:
            raise ReplayRefusal("M3 non-decision source has a boundary receipt")
    return projected


def _fresh_m3_verdicts(
    rows: list[dict[str, Any]],
    episode_path: Path,
    directory: Path,
    label: str,
) -> list[dict[str, Any]]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    ledger_path = directory / f"{label}.jsonl"
    clean_rows = [row for row in rows if row["kind"] != "cell_verdict"]
    _write_jsonl(ledger_path, clean_rows)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "harness.score_redteam",
            str(ledger_path),
            str(Path(episode_path).resolve()),
        ],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ReplayRefusal(
            f"unchanged M3 scorer failed: {completed.stderr.strip()}"
        )
    verdicts = [
        row for row in Ledger(ledger_path).rows() if row["kind"] == "cell_verdict"
    ]
    if not verdicts:
        raise ReplayRefusal("unchanged M3 scorer emitted no fresh verdicts")
    return verdicts


def verify_unchanged_scorer_round_trip(
    source_path: Path,
    episode_path: Path,
    lineage_path: Path,
    work_dir: Path,
    source_index_path: Path = DEFAULT_SOURCE_INDEX,
) -> M3AdapterReceipt:
    """Ingest, project, and require fresh unchanged-scorer equality."""
    receipt = ingest_m3(
        source_path, episode_path, lineage_path, source_index_path
    )
    source_rows = _read_jsonl(source_path)
    projected_rows = project_m3(lineage_path, episode_path, source_index_path)
    work_dir = Path(work_dir)
    before = _fresh_m3_verdicts(
        source_rows, episode_path, work_dir, "source"
    )
    after = _fresh_m3_verdicts(
        projected_rows, episode_path, work_dir, "projected"
    )
    if canonical_verdicts(before) != canonical_verdicts(after):
        raise ReplayRefusal(
            "unchanged M3 scorer output changed after Core round trip"
        )
    source_index = _load_source_index(source_index_path)
    attack = _one_required(source_rows, "attack")
    indexed = _indexed_ledger(source_index, attack["attack_id"])
    actual_verdicts = {row["cell"]: row["verdict"] for row in before}
    if actual_verdicts != indexed.get("expected_verdicts"):
        raise ReplayRefusal("fresh M3 scorer output disagrees with indexed matrix")
    return receipt
