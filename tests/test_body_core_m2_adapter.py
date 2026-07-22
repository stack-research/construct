"""Wire tests for the M2-to-Body-Core v0.2 adapter.

Checked-in M2 ledgers remain prior evidence. These tests fresh-score temporary
copies before and after Core transport; they create no resident finding.
"""

from __future__ import annotations

import hashlib
import json
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory

from sketches.next_substrate.core import (
    LineageStore as KernelLineageStore,
    ReplayRefusal,
    Writer,
)
from sketches.next_substrate.policy import V02_POLICY_PROJECTOR
from sketches.next_substrate.m2_adapter import (
    SOURCE_EVENT_KIND,
    _fresh_resident_verdicts,
    ingest_m2,
    project_m2,
    verify_unchanged_scorer_round_trip,
)


LineageStore = partial(KernelLineageStore, projector=V02_POLICY_PROJECTOR)


ROOT = Path(__file__).resolve().parent.parent
M2_PAIRS = (
    (
        "runs/m2/local/rs-s1.jsonl",
        "runs/m2/local/rs-s2.jsonl",
        "episodes/m2/rs-e2.json",
    ),
    (
        "runs/m2/claude/rs-s1.jsonl",
        "runs/m2/claude/rs-s2.jsonl",
        "episodes/m2/rs-e2.json",
    ),
    (
        "runs/m2/abl5/rs-s1.jsonl",
        "runs/m2/abl5/rs-s2.jsonl",
        "episodes/m2/rs-e2.json",
    ),
    (
        "runs/m2/claude-l3/rs-s1.jsonl",
        "runs/m2/claude-l3/rs-s2.jsonl",
        "episodes/m2/rs-e2.json",
    ),
    (
        "runs/m2/local/rs-loses-s1.jsonl",
        "runs/m2/local/rs-loses-s2.jsonl",
        "episodes/m2/rs-loses-e2.json",
    ),
    (
        "runs/m2/claude/rs-loses-s1.jsonl",
        "runs/m2/claude/rs-loses-s2.jsonl",
        "episodes/m2/rs-loses-e2.json",
    ),
    (
        "runs/m2/loses-claude-v2/rs-loses-s1.jsonl",
        "runs/m2/loses-claude-v2/rs-loses-s2.jsonl",
        "episodes/m2/rs-loses-e2.json",
    ),
    (
        "runs/m2/local/rs-stale-s1.jsonl",
        "runs/m2/local/rs-stale-s2.jsonl",
        "episodes/m2/rs-stale-e2.json",
    ),
    (
        "runs/m2/claude/rs-stale-s1.jsonl",
        "runs/m2/claude/rs-stale-s2.jsonl",
        "episodes/m2/rs-stale-e2.json",
    ),
    (
        "runs/m2/stale-amb-claude/rs-stale-ambiguous-s1.jsonl",
        "runs/m2/stale-amb-claude/rs-stale-ambiguous-s2.jsonl",
        "episodes/m2/rs-stale-ambiguous-e2.json",
    ),
)
OBSERVER = Writer("m2-adapter-test-observer", "observer")
CONTROLLER = Writer("m2-adapter-test-controller", "controller")


def _paths(pair=M2_PAIRS[0]) -> tuple[Path, Path, Path]:
    return tuple(ROOT / relative for relative in pair)


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


def _rehash_chain(rows: list[dict]) -> None:
    previous = "0" * 64
    for row in rows:
        row["previous_event_hash"] = previous
        _rehash(row)
        previous = row["event_hash"]


def test_all_closed_m2_pairs_preserve_fresh_unchanged_scorer():
    for pair in M2_PAIRS:
        s1_path, s2_path, episode_path = _paths(pair)
        with TemporaryDirectory() as td:
            td_path = Path(td)
            receipt = verify_unchanged_scorer_round_trip(
                s1_path,
                s2_path,
                episode_path,
                td_path / "core.jsonl",
                td_path / "score",
            )
            assert receipt.s1_digest == receipt.projected_s1_digest
            assert receipt.s2_digest == receipt.projected_s2_digest
            assert receipt.core_rows == receipt.s1_rows + receipt.s2_rows + 3
            assert receipt.append_prefix_rows == (
                receipt.core_rows * (receipt.core_rows - 1) // 2
            )
    print("ok  M2 adapter: ten closed S1/S2 pairs preserve fresh scorer outputs")


def test_m2_source_mutation_without_rehash_is_refused():
    s1_path, s2_path, _ = _paths()
    with TemporaryDirectory() as td:
        path = Path(td) / "core.jsonl"
        ingest_m2(s1_path, s2_path, path)
        rows = LineageStore(path).raw_rows()
        carried = next(row for row in rows if row["kind"] == SOURCE_EVENT_KIND)
        carried["payload"]["source_kind"] = "forged"
        _rewrite(path, rows)
        try:
            project_m2(path)
        except ReplayRefusal as exc:
            assert "event_hash mismatch" in str(exc)
        else:
            raise AssertionError("unhashed M2 source mutation survived")
    print("ok  M2 refusal: mutation without rehash breaks Core lineage")


def test_m2_rehashed_stale_view_is_refused():
    s1_path, s2_path, _ = _paths()
    with TemporaryDirectory() as td:
        path = Path(td) / "core.jsonl"
        ingest_m2(s1_path, s2_path, path)
        store = LineageStore(path)
        store.append_view_claim(writer=Writer("m2-view-test", "runtime"))
        rows = store.raw_rows()
        rows[-1]["payload"]["view_digest"] = "f" * 64
        _rehash(rows[-1])
        _rewrite(path, rows)
        try:
            project_m2(path)
        except ReplayRefusal as exc:
            assert "view digest mismatch" in str(exc)
        else:
            raise AssertionError("rehashed stale M2 view survived")
    print("ok  M2 refusal: stale materialized view loses to replay")


def test_invalid_s1_failure_warrant_blocks_m2_projection():
    s1_path, s2_path, _ = _paths()
    with TemporaryDirectory() as td:
        path = Path(td) / "core.jsonl"
        ingest_m2(s1_path, s2_path, path)
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
                "reason": "M2 adapter refusal probe",
            },
        )
        try:
            project_m2(store)
        except ReplayRefusal as exc:
            assert "unhealthy carried state" in str(exc)
        else:
            raise AssertionError("invalid S1 warrant reached resident scorer")
    print("ok  M2 refusal: invalid S1 failure warrant blocks projection")


def test_extra_m2_lifecycle_transitions_are_refused():
    s1_path, s2_path, _ = _paths()
    with TemporaryDirectory() as td:
        path = Path(td) / "core.jsonl"
        ingest_m2(s1_path, s2_path, path)
        store = LineageStore(path)
        item = next(iter(store.replay().views.state_items.values()))
        suspended = store.append(
            "state_item_transition",
            writer=CONTROLLER,
            authority="controller_transition",
            payload={
                "item_id": item.item_id,
                "from_status": "active",
                "to_status": "suspended",
                "reason": "unbound transition probe",
            },
        )
        store.append(
            "state_item_transition",
            writer=CONTROLLER,
            authority="controller_transition",
            causal_parent_ids=[suspended["event_id"]],
            payload={
                "item_id": item.item_id,
                "from_status": "suspended",
                "to_status": "active",
                "reason": "unbound transition probe",
            },
        )
        try:
            project_m2(store)
        except ReplayRefusal as exc:
            assert "exactly one activation receipt" in str(exc)
        else:
            raise AssertionError("extra M2 lifecycle events survived projection")
    print("ok  M2 refusal: lifecycle correspondence is exactly one activation")


def test_m2_placement_change_without_declared_correspondence_is_refused():
    s1_path, s2_path, _ = _paths()
    with TemporaryDirectory() as td:
        path = Path(td) / "core.jsonl"
        ingest_m2(s1_path, s2_path, path)
        store = LineageStore(path)
        item = next(iter(store.replay().views.state_items.values()))
        store.append(
            "placement_changed",
            writer=CONTROLLER,
            authority="controller_transition",
            payload={
                "item_id": item.item_id,
                "from_placement": "hot",
                "to_placement": "cold",
                "reason": "unbound placement probe",
            },
        )
        try:
            project_m2(store)
        except ReplayRefusal as exc:
            assert "does not authorize placement-change receipts" in str(exc)
        else:
            raise AssertionError("unbound M2 placement event survived projection")
    print("ok  M2 refusal: undeclared placement events cannot alter carried state")


def test_m2_source_binding_does_not_authorize_placement():
    s1_path, s2_path, _ = _paths()
    with TemporaryDirectory() as td:
        path = Path(td) / "core.jsonl"
        ingest_m2(s1_path, s2_path, path)
        store = LineageStore(path)
        item = next(iter(store.replay().views.state_items.values()))
        meta_event = next(
            row
            for row in store.rows()
            if row["kind"] == SOURCE_EVENT_KIND
            and row["payload"].get("source_phase") == "s2"
            and row["payload"].get("source_kind") == "m2_run_meta"
        )
        store.append(
            "placement_changed",
            writer=CONTROLLER,
            authority="controller_transition",
            causal_parent_ids=[meta_event["event_id"]],
            payload={
                "item_id": item.item_id,
                "from_placement": "hot",
                "to_placement": "cold",
                "reason": "well-bound but unauthorized placement probe",
                "source_event_id": meta_event["event_id"],
                "source_phase": "s2",
                "source_row_index": meta_event["payload"]["source_row_index"],
                "source_kind": "m2_run_meta",
            },
        )
        try:
            project_m2(store)
        except ReplayRefusal as exc:
            assert "does not authorize placement-change receipts" in str(exc)
        else:
            raise AssertionError("source binding granted M2 placement authority")
    print("ok  M2 refusal: valid source binding does not grant policy authority")


def test_m2_metabolic_event_without_declared_correspondence_is_refused():
    s1_path, s2_path, _ = _paths()
    with TemporaryDirectory() as td:
        path = Path(td) / "core.jsonl"
        ingest_m2(s1_path, s2_path, path)
        store = LineageStore(path)
        item = next(iter(store.replay().views.state_items.values()))
        store.append(
            "metabolic_event",
            writer=CONTROLLER,
            authority="controller_transition",
            payload={
                "item_id": item.item_id,
                "metric": "fabricated_help",
                "units": 999,
            },
        )
        try:
            project_m2(store)
        except ReplayRefusal as exc:
            assert "does not authorize metabolic receipts" in str(exc)
        else:
            raise AssertionError("unbound M2 metabolic event survived projection")
    print("ok  M2 refusal: undeclared metabolic events cannot affect carried state")


def test_m2_admission_must_keep_world_failure_warrant():
    s1_path, s2_path, _ = _paths()
    with TemporaryDirectory() as td:
        path = Path(td) / "core.jsonl"
        ingest_m2(s1_path, s2_path, path)
        rows = LineageStore(path).raw_rows()
        admission = next(row for row in rows if row["kind"] == "state_item_admitted")
        other_source = next(
            row
            for row in rows
            if row["kind"] == SOURCE_EVENT_KIND
            and row["event_id"] not in admission["warrant_event_ids"]
            and row["event_id"] in admission["causal_parent_ids"]
        )
        admission["warrant_event_ids"] = [other_source["event_id"]]
        _rehash_chain(rows)
        _rewrite(path, rows)
        try:
            project_m2(path)
        except ReplayRefusal as exc:
            assert "admission disagrees" in str(exc)
        else:
            raise AssertionError("non-failure event became the M2 warrant")
    print("ok  M2 refusal: earned state remains warranted by the S1 failure")


def test_undeclared_m2_source_field_cannot_be_escrowed():
    s1_path, s2_path, _ = _paths()
    with TemporaryDirectory() as td:
        source = Path(td) / "s1.jsonl"
        rows = [
            json.loads(line)
            for line in s1_path.read_text(encoding="utf-8").splitlines()
        ]
        rows[0]["original_m2_row"] = {"opaque": True}
        _rewrite(source, rows)
        try:
            ingest_m2(source, s2_path, Path(td) / "core.jsonl")
        except ReplayRefusal as exc:
            assert "undeclared fields" in str(exc)
        else:
            raise AssertionError("opaque M2 source field was carried")
    print("ok  M2 refusal: undeclared row fields cannot become opaque escrow")


def test_resident_scorer_catches_fork_identity_tamper_after_transport():
    s1_path, s2_path, episode_path = _paths()
    with TemporaryDirectory() as td:
        td_path = Path(td)
        source_s2 = [
            json.loads(line)
            for line in s2_path.read_text(encoding="utf-8").splitlines()
        ]
        config = next(row for row in source_s2 if row["kind"] == "run_config")
        config["branches"][0]["recency_weight"] = 0.999
        tampered_s2 = td_path / "tampered-s2.jsonl"
        _rewrite(tampered_s2, source_s2)
        core_path = td_path / "core.jsonl"
        ingest_m2(s1_path, tampered_s2, core_path)
        projected_s1, projected_s2 = project_m2(core_path)
        verdicts = _fresh_resident_verdicts(
            projected_s1,
            projected_s2,
            episode_path,
            td_path / "score",
            "tampered",
        )
        assert all(row["verdict"] == "fail" for row in verdicts)
        assert all(row["preconditions"]["cold_identity"] is False for row in verdicts)
    print("ok  M2 refusal: unchanged scorer catches carried fork-identity tamper")


if __name__ == "__main__":
    tests = sorted(
        (name, fn)
        for name, fn in globals().items()
        if name.startswith("test_") and callable(fn)
    )
    for _, fn in tests:
        fn()
    print(f"\nALL {len(tests)} BODY CORE M2 ADAPTER TESTS PASS")
