"""Wire tests for the X2-to-Body-Core v0.1 adapter.

The four checked-in real ledgers are prior evidence. These tests only verify
that transport through the provisional Core preserves the unchanged X2 scorer;
they do not create or strengthen a memory finding.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from harness.score_prune import score_prune
from sketches.next_substrate.core import LineageStore, ReplayRefusal, Writer
from sketches.next_substrate.x2_adapter import (
    SOURCE_EVENT_KIND,
    canonical_verdicts,
    ingest_x2,
    project_x2,
    verify_unchanged_scorer_round_trip,
)


ROOT = Path(__file__).resolve().parent.parent
REAL_X2_LEDGERS = (
    ROOT / "runs/x2/x2-helix-real-a30695.x2.jsonl",
    ROOT / "runs/x2/x2-helix-real-d6aede.x2.jsonl",
    ROOT / "runs/x2/x2-u1-dep0033-e10cef.x2.jsonl",
    ROOT / "runs/x2/x2-u1-dep0033-f4e7ab.x2.jsonl",
)
OBSERVER = Writer("adapter-test-observer", "observer")


def _rewrite(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _rehash(row: dict) -> None:
    unsigned = {key: value for key, value in row.items() if key != "event_hash"}
    canonical = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    row["event_hash"] = hashlib.sha256(canonical.encode()).hexdigest()


def test_four_closed_real_ledgers_preserve_unchanged_x2_scorer():
    for source in REAL_X2_LEDGERS:
        with TemporaryDirectory() as td:
            td_path = Path(td)
            receipt = verify_unchanged_scorer_round_trip(
                source,
                td_path / "core.jsonl",
                td_path / "projected.x2.jsonl",
            )
            assert receipt.source_digest == receipt.projected_digest
            assert receipt.source_rows in {92, 102}
            assert receipt.core_rows > receipt.source_rows
            assert receipt.append_prefix_rows == (
                receipt.core_rows * (receipt.core_rows - 1) // 2
            )
    print("ok  X2 adapter: four real closed ledgers preserve scorer verdicts and costs")


def test_source_event_mutation_without_rehash_is_refused():
    with TemporaryDirectory() as td:
        path = Path(td) / "core.jsonl"
        ingest_x2(REAL_X2_LEDGERS[0], path)
        rows = LineageStore(path).raw_rows()
        carried = next(row for row in rows if row["kind"] == SOURCE_EVENT_KIND)
        carried["payload"]["source_kind"] = "forged"
        _rewrite(path, rows)
        try:
            project_x2(path)
        except ReplayRefusal as exc:
            assert "event_hash mismatch" in str(exc)
        else:
            raise AssertionError("unhashed carried-row mutation survived")
    print("ok  X2 refusal: mutation without rehash breaks Core lineage")


def test_undeclared_source_field_cannot_be_escrowed():
    with TemporaryDirectory() as td:
        source = Path(td) / "opaque.x2.jsonl"
        rows = [
            json.loads(line)
            for line in REAL_X2_LEDGERS[0].read_text(encoding="utf-8").splitlines()
        ]
        rows[0]["original_x2_row"] = {"opaque": True}
        _rewrite(source, rows)
        try:
            ingest_x2(source, Path(td) / "core.jsonl")
        except ReplayRefusal as exc:
            assert "undeclared fields" in str(exc)
        else:
            raise AssertionError("undeclared opaque source field was carried")
    print("ok  X2 refusal: undeclared row fields cannot become opaque escrow")


def test_rehashed_stale_view_is_refused_before_projection():
    with TemporaryDirectory() as td:
        path = Path(td) / "core.jsonl"
        ingest_x2(REAL_X2_LEDGERS[0], path)
        store = LineageStore(path)
        store.append_view_claim(writer=Writer("adapter-view-test", "runtime"))
        rows = store.raw_rows()
        rows[-1]["payload"]["view_digest"] = "f" * 64
        _rehash(rows[-1])
        _rewrite(path, rows)
        try:
            project_x2(path)
        except ReplayRefusal as exc:
            assert "view digest mismatch" in str(exc)
        else:
            raise AssertionError("rehashed stale Core view survived")
    print("ok  X2 refusal: stale materialized view loses to replay")


def test_rehashed_last_source_row_is_bound_to_adapter_start():
    with TemporaryDirectory() as td:
        path = Path(td) / "core.jsonl"
        ingest_x2(REAL_X2_LEDGERS[0], path)
        rows = LineageStore(path).raw_rows()
        carried = [row for row in rows if row["kind"] == SOURCE_EVENT_KIND][-1]
        carried["payload"]["top_k"] = 999
        source_row = {
            "kind": carried["payload"]["source_kind"],
            **{
                key: value
                for key, value in carried["payload"].items()
                if key
                not in {
                    "source_row_index",
                    "source_kind",
                    "source_row_digest",
                }
            },
        }
        canonical = json.dumps(
            source_row, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        carried["payload"]["source_row_digest"] = hashlib.sha256(
            canonical.encode()
        ).hexdigest()
        _rehash(carried)
        _rewrite(path, rows)
        try:
            project_x2(path)
        except ReplayRefusal as exc:
            assert "adapter start" in str(exc)
        else:
            raise AssertionError("rehashed source row escaped the start digest")
    print("ok  X2 refusal: start digest binds even a rehashed last source row")


def test_invalid_record_warrant_blocks_projection():
    with TemporaryDirectory() as td:
        path = Path(td) / "core.jsonl"
        ingest_x2(REAL_X2_LEDGERS[0], path)
        store = LineageStore(path)
        item = next(iter(store.replay().views.state_items.values()))
        warrant = item.warrant_event_ids[0]
        store.append(
            "provenance_revision",
            writer=OBSERVER,
            authority="external_observation",
            causal_parent_ids=[warrant],
            payload={
                "target_event_id": warrant,
                "health": "invalid",
                "reason": "adapter refusal probe",
            },
        )
        try:
            project_x2(store)
        except ReplayRefusal as exc:
            assert "unhealthy carried state" in str(exc)
        else:
            raise AssertionError("invalid record warrant reached X2 scorer")
    print("ok  X2 refusal: invalid warrant blocks scorer projection")


def test_x2_cost_tamper_is_caught_by_unchanged_scorer():
    with TemporaryDirectory() as td:
        td_path = Path(td)
        source = td_path / "tampered-source.x2.jsonl"
        rows = [
            json.loads(line)
            for line in REAL_X2_LEDGERS[0].read_text(encoding="utf-8").splitlines()
        ]
        cost_row = next(row for row in rows if row["kind"] == "hot_store_cost")
        cost_row["hot_tokens"] += 1
        _rewrite(source, rows)
        core_path = td_path / "core.jsonl"
        projected_path = td_path / "projected.x2.jsonl"
        ingest_x2(source, core_path)
        _rewrite(projected_path, project_x2(core_path))
        verdicts = score_prune(projected_path)
        cost_cells = [
            verdict
            for verdict in verdicts
            if verdict["cell"] in {"X2-win", "X2-overprune"}
        ]
        assert all(verdict["verdict"] == "confounded" for verdict in cost_cells)
        assert all(
            "cost_replay_mismatch" in verdict["confound_reasons"]
            for verdict in cost_cells
        )
        assert canonical_verdicts(score_prune(source)) == canonical_verdicts(verdicts)
    print("ok  X2 refusal: independent cost replay catches a carried cost tamper")


if __name__ == "__main__":
    tests = sorted(
        (name, fn)
        for name, fn in globals().items()
        if name.startswith("test_") and callable(fn)
    )
    for _, fn in tests:
        fn()
    print(f"\nALL {len(tests)} BODY CORE X2 ADAPTER TESTS PASS")
