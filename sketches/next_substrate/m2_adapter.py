"""Reversible M2-to-Body-Core v0.2 wire adapter.

The adapter carries an S1/S2 resident pair field-for-field, then materializes
the earned record as probationary Core state warranted by the world-scored S1
failure. The carried ``m2_run_meta`` row activates that state across the session
seam. Fresh verdict comparison is delegated to the unchanged
``harness.score_resident`` CLI.
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
from .policy import V02_POLICY_PROJECTOR
from .x2_adapter import X2_ROW_FIELD_CONTRACT, canonical_verdicts


ADAPTER_VERSION = "m2-body-core-adapter-v0.1"
SOURCE_EVENT_KIND = "m2_source_row_carried"
ADAPTER_PAYLOAD_FIELDS = frozenset(
    {"source_phase", "source_row_index", "source_kind", "source_row_digest"}
)
FORBIDDEN_ESCROW_FIELDS = frozenset(
    {"original_m2_row", "original_s1_row", "original_s2_row", "raw_row", "row_blob"}
)

M2_ROW_FIELD_CONTRACT: dict[str, frozenset[str]] = {
    "run_config": X2_ROW_FIELD_CONTRACT["run_config"],
    "offer": X2_ROW_FIELD_CONTRACT["offer"],
    "branch_run": X2_ROW_FIELD_CONTRACT["branch_run"]
    | frozenset(
        {
            "agent_claimed_load_bearing",
            "agent_claimed_usage",
            "elicitation_completion_tokens",
            "elicitation_latency_ms",
            "elicitation_prompt_tokens",
            "loadbearing_parse_error",
            "parse_error",
        }
    ),
    "ablation_run": X2_ROW_FIELD_CONTRACT["ablation_run"],
    "diff_outcome": X2_ROW_FIELD_CONTRACT["diff_outcome"],
    "session": frozenset(
        {
            "episode_id",
            "memory_isolation",
            "prior_session_id",
            "resident_config_digest",
            "session_id",
            "store_path",
            "ts",
            "wall_clock_start",
        }
    ),
    "earned_record": frozenset(
        {
            "created_at",
            "predeclared_usage",
            "provenance",
            "record_id",
            "supersedes",
            "text",
            "trust",
            "ts",
            "vocabulary_kind",
        }
    ),
    "m2_run_meta": frozenset(
        {
            "base_inherited",
            "chain_id",
            "control_branch",
            "e1_episode_id",
            "e2_episode_id",
            "earned_record_id",
            "mint_basis",
            "resident_branch",
            "resident_config_digest",
            "resident_inherited",
            "s1_ledger",
            "s1_session_id",
            "s2_session_id",
            "ts",
        }
    ),
    "cell_verdict": frozenset(
        {
            "cell",
            "chain_id",
            "corpus_scope",
            "engine_backend",
            "episode_id",
            "evidence",
            "fork_group_id",
            "model",
            "preconditions",
            "ts",
            "verdict",
            "wire_test",
        }
    ),
}

ADAPTER_WRITER = Writer("m2-body-core-adapter-v0.1", "controller")
M2_OBSERVER = Writer("m2-ledger-observer-v0.1", "observer")


@dataclass(frozen=True)
class M2AdapterReceipt:
    s1_rows: int
    s2_rows: int
    core_rows: int
    s1_digest: str
    s2_digest: str
    projected_s1_digest: str
    projected_s2_digest: str
    append_prefix_rows: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "adapter_version": ADAPTER_VERSION,
            "s1_rows": self.s1_rows,
            "s2_rows": self.s2_rows,
            "core_rows": self.core_rows,
            "s1_digest": self.s1_digest,
            "s2_digest": self.s2_digest,
            "projected_s1_digest": self.projected_s1_digest,
            "projected_s2_digest": self.projected_s2_digest,
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


def _item_id(record_id: str) -> str:
    return f"m2:{record_id}"


def _source_payload(
    row: dict[str, Any], phase: str, source_row_index: int
) -> dict[str, Any]:
    allowed_fields = M2_ROW_FIELD_CONTRACT.get(row["kind"])
    if allowed_fields is None:
        raise ReplayRefusal(
            f"{phase} row {source_row_index}: unsupported kind {row['kind']!r}"
        )
    unknown_fields = (set(row) - {"kind"}) - allowed_fields
    if unknown_fields:
        raise ReplayRefusal(
            f"{phase} row {source_row_index}: undeclared fields "
            f"{sorted(unknown_fields)}"
        )
    collisions = (set(row) - {"kind"}) & (
        ADAPTER_PAYLOAD_FIELDS | FORBIDDEN_ESCROW_FIELDS
    )
    if collisions:
        raise ReplayRefusal(
            f"{phase} row {source_row_index}: reserved fields {sorted(collisions)}"
        )
    return {
        "source_phase": phase,
        "source_row_index": source_row_index,
        "source_kind": row["kind"],
        "source_row_digest": _digest(row),
        **{key: value for key, value in row.items() if key != "kind"},
    }


def _one(rows: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
    found = [row for row in rows if row["kind"] == kind]
    return found[-1] if found else None


def _validate_pair(
    s1_rows: list[dict[str, Any]], s2_rows: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    s1_session = _one(s1_rows, "session")
    s2_session = _one(s2_rows, "session")
    earned = _one(s2_rows, "earned_record")
    meta = _one(s2_rows, "m2_run_meta")
    if not all((s1_session, s2_session, earned, meta)):
        raise ReplayRefusal("M2 pair requires S1/S2 sessions, earned_record, and meta")
    if (
        s2_session["prior_session_id"] != s1_session["session_id"]
        or meta["s1_session_id"] != s1_session["session_id"]
        or meta["s2_session_id"] != s2_session["session_id"]
        or meta["earned_record_id"] != earned["record_id"]
    ):
        raise ReplayRefusal("M2 pair session or earned-record binding is inconsistent")
    provenance = earned.get("provenance", {})
    source_run_id = provenance.get("source_run_id")
    source_session_id = provenance.get("source_session_id")
    failure = next(
        (
            row
            for row in s1_rows
            if row["kind"] == "branch_run"
            and row.get("run_id") == source_run_id
            and row.get("oracle", {}).get("score") == 0.0
            and row.get("oracle", {}).get("source") not in {None, "authored"}
        ),
        None,
    )
    if failure is None or source_session_id != s1_session["session_id"]:
        raise ReplayRefusal("earned record lacks a world-scored S1 failure warrant")
    return s1_session, s2_session, earned, meta


def ingest_m2(s1_path: Path, s2_path: Path, lineage_path: Path) -> M2AdapterReceipt:
    """Carry one closed M2 S1/S2 pair into a new Body Core lineage."""
    s1_path = Path(s1_path)
    s2_path = Path(s2_path)
    lineage_path = Path(lineage_path)
    if lineage_path.exists() and lineage_path.stat().st_size:
        raise ReplayRefusal(f"{lineage_path}: adapter requires an empty lineage")
    s1_rows = _read_jsonl(s1_path)
    s2_rows = _read_jsonl(s2_path)
    s1_session, _, earned, meta = _validate_pair(s1_rows, s2_rows)
    provenance = earned["provenance"]

    store = LineageStore(lineage_path, projector=V02_POLICY_PROJECTOR)
    started = store.append(
        "m2_adapter_started",
        writer=ADAPTER_WRITER,
        authority="wire_diagnostic",
        payload={
            "adapter_version": ADAPTER_VERSION,
            "s1_source_digest": _digest(s1_rows),
            "s2_source_digest": _digest(s2_rows),
            "s1_source_rows": len(s1_rows),
            "s2_source_rows": len(s2_rows),
            "claim_boundary": (
                "wire integration only; unchanged resident scorer remains oracle"
            ),
        },
    )

    prior_source_event_id = started["event_id"]
    failure_event_id: str | None = None
    for phase, rows in (("s1", s1_rows), ("s2", s2_rows)):
        for source_row_index, row in enumerate(rows):
            carried = store.append(
                SOURCE_EVENT_KIND,
                writer=M2_OBSERVER,
                authority="external_observation",
                causal_parent_ids=[prior_source_event_id],
                payload=_source_payload(row, phase, source_row_index),
            )
            prior_source_event_id = carried["event_id"]

            if (
                phase == "s1"
                and row["kind"] == "branch_run"
                and row.get("run_id") == provenance["source_run_id"]
                and row.get("oracle", {}).get("score") == 0.0
                and row.get("oracle", {}).get("source") not in {None, "authored"}
            ):
                if failure_event_id is not None:
                    raise ReplayRefusal("ambiguous S1 failure warrant")
                failure_event_id = carried["event_id"]

            if phase == "s2" and row["kind"] == "earned_record":
                if failure_event_id is None:
                    raise ReplayRefusal("S2 earned record precedes its S1 warrant")
                store.append(
                    "state_item_admitted",
                    writer=ADAPTER_WRITER,
                    authority="controller_transition",
                    causal_parent_ids=[carried["event_id"], failure_event_id],
                    warrant_event_ids=[failure_event_id],
                    payload={
                        "item_id": _item_id(row["record_id"]),
                        "item_kind": "m2_earned_record",
                        "status": "probationary",
                        "placement": "hot",
                        "detail": {
                            "record_id": row["record_id"],
                            "source_session_id": provenance["source_session_id"],
                            "source_run_id": provenance["source_run_id"],
                        },
                    },
                )

            if phase == "s2" and row["kind"] == "m2_run_meta":
                item_id = _item_id(row["earned_record_id"])
                if item_id not in store.replay().views.state_items:
                    raise ReplayRefusal(
                        "M2 meta precedes earned-record materialization"
                    )
                store.append(
                    "state_item_transition",
                    writer=ADAPTER_WRITER,
                    authority="controller_transition",
                    causal_parent_ids=[carried["event_id"]],
                    payload={
                        "item_id": item_id,
                        "from_status": "probationary",
                        "to_status": "active",
                        "reason": "M2 resident inheritance bound across session seam",
                        "source_event_id": carried["event_id"],
                        "source_phase": phase,
                        "source_row_index": source_row_index,
                        "source_kind": row["kind"],
                    },
                )

    if failure_event_id is None:
        raise ReplayRefusal(
            f"no carried failure for S1 session {s1_session['session_id']}"
        )
    projected_s1, projected_s2 = project_m2(store)
    core_rows = len(store.rows())
    return M2AdapterReceipt(
        s1_rows=len(s1_rows),
        s2_rows=len(s2_rows),
        core_rows=core_rows,
        s1_digest=_digest(s1_rows),
        s2_digest=_digest(s2_rows),
        projected_s1_digest=_digest(projected_s1),
        projected_s2_digest=_digest(projected_s2),
        append_prefix_rows=core_rows * (core_rows - 1) // 2,
    )


def project_m2(
    store_or_path: LineageStore | Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Reconstruct S1/S2 after Core replay and policy correspondence checks."""
    store = (
        store_or_path
        if isinstance(store_or_path, LineageStore)
        else LineageStore(Path(store_or_path))
    )
    result = store.replay(projector=V02_POLICY_PROJECTOR)
    starts = [row for row in result.rows if row["kind"] == "m2_adapter_started"]
    if len(starts) != 1:
        raise ReplayRefusal("M2 projection requires exactly one adapter start")
    start_payload = starts[0]["payload"]

    m2_items = {
        item_id: item
        for item_id, item in result.views.state_items.items()
        if item.item_kind == "m2_earned_record"
    }
    if len(m2_items) != 1:
        raise ReplayRefusal("M2 projection requires exactly one earned state item")
    item_id, item = next(iter(m2_items.items()))
    if item.status != "active" or any(
        result.views.warrant_health.get(warrant) != "current"
        for warrant in item.warrant_event_ids
    ):
        raise ReplayRefusal(f"M2 projection refused: unhealthy carried state {item_id}")

    projected: dict[str, dict[int, dict[str, Any]]] = {"s1": {}, "s2": {}}
    carried_by_id: dict[str, dict[str, Any]] = {}
    for event in result.rows:
        if event["kind"] != SOURCE_EVENT_KIND:
            continue
        payload = event["payload"]
        phase = payload.get("source_phase")
        source_row_index = payload.get("source_row_index")
        source_kind = payload.get("source_kind")
        if (
            phase not in projected
            or not isinstance(source_row_index, int)
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
        if source_row_index in projected[phase]:
            raise ReplayRefusal(
                f"duplicate {phase} source row index {source_row_index}"
            )
        projected[phase][source_row_index] = row
        carried_by_id[event["event_id"]] = event

    phase_rows: dict[str, list[dict[str, Any]]] = {}
    for phase in ("s1", "s2"):
        indexes = sorted(projected[phase])
        if indexes != list(range(len(indexes))):
            raise ReplayRefusal(f"non-contiguous {phase} source row indexes: {indexes}")
        phase_rows[phase] = [projected[phase][index] for index in indexes]
        if start_payload.get(f"{phase}_source_rows") != len(phase_rows[phase]):
            raise ReplayRefusal(f"{phase} row count disagrees with adapter start")
        if start_payload.get(f"{phase}_source_digest") != _digest(phase_rows[phase]):
            raise ReplayRefusal(f"{phase} source digest disagrees with adapter start")

    s1_rows, s2_rows = phase_rows["s1"], phase_rows["s2"]
    _, _, earned, meta = _validate_pair(s1_rows, s2_rows)
    earned_event = next(
        event
        for event in carried_by_id.values()
        if event["payload"]["source_phase"] == "s2"
        and event["payload"]["source_kind"] == "earned_record"
        and event["payload"].get("record_id") == earned["record_id"]
    )
    failure_event = next(
        (
            event
            for event in carried_by_id.values()
            if event["payload"]["source_phase"] == "s1"
            and event["payload"]["source_kind"] == "branch_run"
            and event["payload"].get("run_id") == earned["provenance"]["source_run_id"]
            and event["payload"].get("oracle", {}).get("score") == 0.0
            and event["payload"].get("oracle", {}).get("source")
            not in {None, "authored"}
        ),
        None,
    )
    if failure_event is None:
        raise ReplayRefusal("carried M2 state lacks its S1 failure event")
    admissions = [
        row
        for row in result.rows
        if row["kind"] == "state_item_admitted"
        and row["payload"].get("item_id") == item_id
    ]
    if (
        len(admissions) != 1
        or admissions[0]["warrant_event_ids"] != [failure_event["event_id"]]
        or earned_event["event_id"] not in admissions[0]["causal_parent_ids"]
        or failure_event["event_id"] not in admissions[0]["causal_parent_ids"]
    ):
        raise ReplayRefusal("M2 earned-state admission disagrees with source lineage")

    transitions = [
        row
        for row in result.rows
        if row["kind"] == "state_item_transition"
        and row["payload"].get("item_id") == item_id
    ]
    meta_event = next(
        event
        for event in carried_by_id.values()
        if event["payload"]["source_phase"] == "s2"
        and event["payload"]["source_kind"] == "m2_run_meta"
    )
    if len(transitions) != 1:
        raise ReplayRefusal("M2 earned state requires exactly one activation receipt")
    bindings = index_bound_state_receipts(
        result.rows,
        source_event_kind=SOURCE_EVENT_KIND,
        receipt_event_kinds={"state_item_transition"},
        affected_item_ids={item_id},
        coordinate_fields=("source_phase", "source_row_index", "source_kind"),
        context="M2",
    )
    if bindings.receipts_by_source.get(meta_event["event_id"]) != (transitions[0],):
        raise ReplayRefusal("M2 activation receipt disagrees with carried meta")
    transition = transitions[0]["payload"]
    if (
        transition.get("from_status") != "probationary"
        or transition.get("to_status") != "active"
        or meta["earned_record_id"] != earned["record_id"]
    ):
        raise ReplayRefusal("M2 activation receipt disagrees with carried meta")

    placement_events = [
        row
        for row in result.rows
        if row["kind"] == "placement_changed"
        and row["payload"].get("item_id") == item_id
    ]
    if placement_events or item.placement != "hot":
        raise ReplayRefusal(
            "M2 earned state does not authorize placement-change receipts"
        )
    metabolic_events = [
        row
        for row in result.rows
        if row["kind"] == "metabolic_event" and row["payload"].get("item_id") == item_id
    ]
    if metabolic_events:
        raise ReplayRefusal("M2 earned state does not authorize metabolic receipts")
    return s1_rows, s2_rows


def _unscored_pair(
    s1_rows: list[dict[str, Any]],
    s2_rows: list[dict[str, Any]],
    directory: Path,
    label: str,
) -> tuple[Path, Path]:
    s1_path = directory / f"{label}.s1.jsonl"
    s2_path = directory / f"{label}.s2.jsonl"
    clean_s1 = [row for row in s1_rows if row["kind"] != "cell_verdict"]
    clean_s2 = [dict(row) for row in s2_rows if row["kind"] != "cell_verdict"]
    meta = next(row for row in clean_s2 if row["kind"] == "m2_run_meta")
    meta["s1_ledger"] = str(s1_path.resolve())
    _write_jsonl(s1_path, clean_s1)
    _write_jsonl(s2_path, clean_s2)
    return s1_path, s2_path


def _fresh_resident_verdicts(
    s1_rows: list[dict[str, Any]],
    s2_rows: list[dict[str, Any]],
    episode_path: Path,
    directory: Path,
    label: str,
) -> list[dict[str, Any]]:
    _, s2_path = _unscored_pair(s1_rows, s2_rows, directory, label)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "harness.score_resident",
            str(s2_path),
            str(Path(episode_path).resolve()),
        ],
        cwd=Path(__file__).resolve().parents[2],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ReplayRefusal(
            f"unchanged resident scorer failed: {completed.stderr.strip()}"
        )
    return [row for row in Ledger(s2_path).rows() if row["kind"] == "cell_verdict"]


def verify_unchanged_scorer_round_trip(
    s1_path: Path,
    s2_path: Path,
    episode_path: Path,
    lineage_path: Path,
    work_dir: Path,
) -> M2AdapterReceipt:
    """Ingest, project, and require fresh unchanged-scorer equality."""
    receipt = ingest_m2(s1_path, s2_path, lineage_path)
    source_s1 = _read_jsonl(s1_path)
    source_s2 = _read_jsonl(s2_path)
    projected_s1, projected_s2 = project_m2(lineage_path)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    before = _fresh_resident_verdicts(
        source_s1, source_s2, episode_path, work_dir, "source"
    )
    after = _fresh_resident_verdicts(
        projected_s1, projected_s2, episode_path, work_dir, "projected"
    )
    if canonical_verdicts(before) != canonical_verdicts(after):
        raise ReplayRefusal(
            "unchanged resident scorer output changed after Core round trip"
        )
    return receipt
