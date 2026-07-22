"""Wire tests for the endorsed M3-to-Body-Core v0.2 adapter proposal.

The eleven indexed ledgers remain prior evidence. These tests verify exact
transport, source correspondence, refusal behavior, and unchanged-scorer
preservation only; they do not create or strengthen an M3 finding.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

from sketches.next_substrate.core import LineageStore, ReplayRefusal, Writer
from sketches.next_substrate.m3_adapter import (
    ADAPTER_PAYLOAD_FIELDS,
    ADAPTER_WRITER,
    DECLARATION_EVENT_KIND,
    DEFAULT_SOURCE_INDEX,
    ITEM_KIND,
    RECEIPT_EVENT_KIND,
    SOURCE_EVENT_KIND,
    TRACK_B_SURFACE,
    _digest,
    _fresh_m3_verdicts,
    ingest_m3,
    project_m3,
    verify_unchanged_scorer_round_trip,
)


ROOT = Path(__file__).resolve().parent.parent
INDEX = json.loads(DEFAULT_SOURCE_INDEX.read_text(encoding="utf-8"))
M3_CASES = tuple(
    (
        ROOT / entry["path"],
        ROOT / entry["episode"],
        entry["attack_surface"],
        entry["expected_verdicts"],
    )
    for entry in INDEX["ledgers"]
)
CONTROLLER = Writer("m3-adapter-test-controller", "controller")


def _case(index: int = 0) -> tuple[Path, Path, str, dict[str, str]]:
    return M3_CASES[index]


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


def _refresh_carried_digest(carried: dict) -> None:
    source_row = {
        "kind": carried["payload"]["source_kind"],
        **{
            key: value
            for key, value in carried["payload"].items()
            if key not in ADAPTER_PAYLOAD_FIELDS
        },
    }
    carried["payload"]["source_row_digest"] = _digest(source_row)


def _ingested(
    directory: Path, case_index: int = 0
) -> tuple[Path, Path, Path]:
    source_path, episode_path, _, _ = _case(case_index)
    core_path = directory / "core.jsonl"
    ingest_m3(source_path, episode_path, core_path)
    return source_path, episode_path, core_path


def _expect_refusal(action: Callable[[], object], text: str) -> None:
    try:
        action()
    except ReplayRefusal as exc:
        assert text in str(exc), str(exc)
    else:
        raise AssertionError(f"expected refusal containing {text!r}")


def test_all_eleven_ledgers_preserve_fresh_unchanged_m3_scorer():
    total_core_rows = 0
    total_prefix_rows = 0
    for case_index, (source_path, episode_path, surface, _) in enumerate(M3_CASES):
        with TemporaryDirectory() as td:
            directory = Path(td)
            receipt = verify_unchanged_scorer_round_trip(
                source_path,
                episode_path,
                directory / "core.jsonl",
                directory / "score",
            )
            expected_core_rows = 5 if surface == TRACK_B_SURFACE else 18
            assert receipt.source_digest == receipt.projected_digest
            assert receipt.core_rows == expected_core_rows, case_index
            assert receipt.append_prefix_rows == (
                expected_core_rows * (expected_core_rows - 1) // 2
            )
            total_core_rows += receipt.core_rows
            total_prefix_rows += receipt.append_prefix_rows
    assert total_core_rows == 172
    assert total_prefix_rows == 1397
    print("ok  M3 adapter: eleven ledgers preserve exact fresh scorer evidence")


def test_m3_source_mutation_without_rehash_is_refused():
    with TemporaryDirectory() as td:
        directory = Path(td)
        _, episode_path, core_path = _ingested(directory)
        rows = LineageStore(core_path).raw_rows()
        carried = next(row for row in rows if row["kind"] == SOURCE_EVENT_KIND)
        carried["payload"]["source_kind"] = "forged"
        _rewrite(core_path, rows)
        _expect_refusal(
            lambda: project_m3(core_path, episode_path), "event_hash mismatch"
        )
    print("ok  M3 refusal: source mutation without rehash breaks Core lineage")


def test_rehashed_m3_source_mutation_loses_to_start_digest():
    with TemporaryDirectory() as td:
        directory = Path(td)
        _, episode_path, core_path = _ingested(directory)
        rows = LineageStore(core_path).raw_rows()
        carried = [row for row in rows if row["kind"] == SOURCE_EVENT_KIND][-1]
        carried["payload"]["payload_digest"] = "rehashed-tamper"
        _refresh_carried_digest(carried)
        _rehash_chain(rows)
        _rewrite(core_path, rows)
        _expect_refusal(
            lambda: project_m3(core_path, episode_path),
            "disagrees with adapter start or index",
        )
    print("ok  M3 refusal: adapter start binds a rehashed source mutation")


def test_rehashed_stale_m3_view_is_refused():
    with TemporaryDirectory() as td:
        directory = Path(td)
        _, episode_path, core_path = _ingested(directory)
        store = LineageStore(core_path)
        store.append_view_claim(writer=Writer("m3-view-test", "runtime"))
        rows = store.raw_rows()
        rows[-1]["payload"]["view_digest"] = "f" * 64
        _rehash(rows[-1])
        _rewrite(core_path, rows)
        _expect_refusal(
            lambda: project_m3(core_path, episode_path), "view digest mismatch"
        )
    print("ok  M3 refusal: stale materialized view loses to replay")


def test_unknown_m3_source_shapes_and_opaque_escrow_are_refused():
    source_path, episode_path, _, _ = _case()
    mutations = (
        lambda rows: rows[0].__setitem__("kind", "unknown_m3_row"),
        lambda rows: rows[0].__setitem__("undeclared_field", True),
        lambda rows: rows[0].__setitem__("row_blob", {"opaque": True}),
    )
    expected = ("unsupported kind", "undeclared fields", "undeclared fields")
    for offset, (mutate, message) in enumerate(zip(mutations, expected, strict=True)):
        with TemporaryDirectory() as td:
            directory = Path(td)
            rows = [
                json.loads(line)
                for line in source_path.read_text(encoding="utf-8").splitlines()
            ]
            mutate(rows)
            mutated = directory / f"mutated-{offset}.jsonl"
            _rewrite(mutated, rows)
            _expect_refusal(
                lambda: ingest_m3(
                    mutated, episode_path, directory / "core.jsonl"
                ),
                message,
            )
    print("ok  M3 refusal: unknown source shapes cannot become opaque escrow")


def test_m3_ledger_and_episode_pin_mismatches_refuse_before_projection():
    source_path, episode_path, _, _ = _case()
    with TemporaryDirectory() as td:
        directory = Path(td)
        source_rows = [
            json.loads(line)
            for line in source_path.read_text(encoding="utf-8").splitlines()
        ]
        source_rows[0]["model"] = "pin-drift"
        mutated_source = directory / "source.jsonl"
        _rewrite(mutated_source, source_rows)
        _expect_refusal(
            lambda: ingest_m3(
                mutated_source, episode_path, directory / "source-core.jsonl"
            ),
            "source ledger digest disagrees",
        )

        episode = json.loads(episode_path.read_text(encoding="utf-8"))
        episode["question"] = "pin drift"
        mutated_episode = directory / "episode.json"
        mutated_episode.write_text(json.dumps(episode, sort_keys=True), encoding="utf-8")
        _expect_refusal(
            lambda: ingest_m3(
                source_path, mutated_episode, directory / "episode-core.jsonl"
            ),
            "episode digest disagrees",
        )
    print("ok  M3 refusal: source and episode digest/index pins fail closed")


def test_m3_decision_bindings_refuse_missing_wrong_kind_noncausal_and_drift():
    mutation_names = ("missing", "wrong-kind", "noncausal", "coordinate")
    for mutation_name in mutation_names:
        with TemporaryDirectory() as td:
            directory = Path(td)
            _, episode_path, core_path = _ingested(directory)
            rows = LineageStore(core_path).raw_rows()
            receipt = next(row for row in rows if row["kind"] == RECEIPT_EVENT_KIND)
            declaration = next(
                row for row in rows if row["kind"] == DECLARATION_EVENT_KIND
            )
            if mutation_name == "missing":
                receipt["payload"].pop("source_event_id")
            elif mutation_name == "wrong-kind":
                receipt["payload"]["source_event_id"] = declaration["event_id"]
                receipt["causal_parent_ids"] = [declaration["event_id"]]
            elif mutation_name == "noncausal":
                receipt["causal_parent_ids"] = []
            else:
                receipt["payload"]["source_kind"] = "coordinate-drift"
            _rehash_chain(rows)
            _rewrite(core_path, rows)
            _expect_refusal(
                lambda: project_m3(core_path, episode_path), "M3"
            )
    print("ok  M3 refusal: shared helper enforces every decision binding leg")


def test_m3_receipts_refuse_missing_duplicate_orphan_and_semantic_drift():
    mutation_names = ("missing", "duplicate", "orphan", "semantic")
    for mutation_name in mutation_names:
        with TemporaryDirectory() as td:
            directory = Path(td)
            _, episode_path, core_path = _ingested(directory)
            store = LineageStore(core_path)
            rows = store.raw_rows()
            receipt = next(row for row in rows if row["kind"] == RECEIPT_EVENT_KIND)
            if mutation_name == "missing":
                receipt["kind"] = "diagnostic_note"
                _rehash_chain(rows)
                _rewrite(core_path, rows)
            elif mutation_name == "duplicate":
                store.append(
                    RECEIPT_EVENT_KIND,
                    writer=ADAPTER_WRITER,
                    authority="wire_diagnostic",
                    causal_parent_ids=receipt["causal_parent_ids"],
                    payload=receipt["payload"],
                )
            elif mutation_name == "orphan":
                attack_source = next(
                    row
                    for row in rows
                    if row["kind"] == SOURCE_EVENT_KIND
                    and row["payload"]["source_kind"] == "attack"
                )
                payload = dict(receipt["payload"])
                payload.update(
                    {
                        "source_event_id": attack_source["event_id"],
                        "source_row_index": attack_source["payload"][
                            "source_row_index"
                        ],
                        "source_kind": "attack",
                    }
                )
                store.append(
                    RECEIPT_EVENT_KIND,
                    writer=ADAPTER_WRITER,
                    authority="wire_diagnostic",
                    causal_parent_ids=[attack_source["event_id"]],
                    payload=payload,
                )
            else:
                receipt["payload"]["decision"] = "withhold"
                _rehash_chain(rows)
                _rewrite(core_path, rows)
            _expect_refusal(lambda: project_m3(core_path, episode_path), "M3")
    print("ok  M3 refusal: receipt cardinality and source semantics are exact")


def test_m3_boundary_row_for_absent_episode_record_is_refused():
    source_path, episode_path, _, _ = _case()
    with TemporaryDirectory() as td:
        directory = Path(td)
        rows = [
            json.loads(line)
            for line in source_path.read_text(encoding="utf-8").splitlines()
        ]
        decision = next(row for row in rows if row["kind"] in {"offer", "withholding"})
        decision["record_id"] = "absent-record"
        mutated = directory / "absent.jsonl"
        _rewrite(mutated, rows)
        _expect_refusal(
            lambda: ingest_m3(mutated, episode_path, directory / "core.jsonl"),
            "absent from the episode",
        )
    print("ok  M3 refusal: absent episode records are inconsistent source")


def test_source_binding_never_authorizes_m3_state_policy_events():
    event_kinds = ("placement_changed", "metabolic_event", "state_item_transition")
    for event_kind in event_kinds:
        with TemporaryDirectory() as td:
            directory = Path(td)
            _, episode_path, core_path = _ingested(directory)
            store = LineageStore(core_path)
            result = store.replay()
            item = next(
                item for item in result.views.state_items.values() if item.item_kind == ITEM_KIND
            )
            source = next(
                row
                for row in result.rows
                if row["kind"] == SOURCE_EVENT_KIND
                and row["payload"]["source_kind"] in {"offer", "withholding"}
            )
            common = {
                "item_id": item.item_id,
                "source_event_id": source["event_id"],
                "source_row_index": source["payload"]["source_row_index"],
                "source_kind": source["payload"]["source_kind"],
            }
            if event_kind == "placement_changed":
                store.append(
                    event_kind,
                    writer=CONTROLLER,
                    authority="controller_transition",
                    causal_parent_ids=[source["event_id"]],
                    payload={
                        **common,
                        "from_placement": "hot",
                        "to_placement": "cold",
                    },
                )
            elif event_kind == "metabolic_event":
                store.append(
                    event_kind,
                    writer=CONTROLLER,
                    authority="controller_transition",
                    causal_parent_ids=[source["event_id"]],
                    payload={**common, "metric": "forged", "units": 1},
                )
            else:
                suspended = store.append(
                    event_kind,
                    writer=CONTROLLER,
                    authority="controller_transition",
                    causal_parent_ids=[source["event_id"]],
                    payload={
                        **common,
                        "from_status": "active",
                        "to_status": "suspended",
                    },
                )
                store.append(
                    event_kind,
                    writer=CONTROLLER,
                    authority="controller_transition",
                    causal_parent_ids=[source["event_id"], suspended["event_id"]],
                    payload={
                        **common,
                        "from_status": "suspended",
                        "to_status": "active",
                    },
                )
            _expect_refusal(
                lambda: project_m3(core_path, episode_path), "does not authorize"
            )
    print("ok  M3 refusal: valid binding grants no generic state-policy authority")


def test_m3_adapter_writer_identity_and_authority_are_exact():
    with TemporaryDirectory() as td:
        directory = Path(td)
        _, episode_path, core_path = _ingested(directory)
        rows = LineageStore(core_path).raw_rows()
        receipt = next(row for row in rows if row["kind"] == RECEIPT_EVENT_KIND)
        receipt["writer"]["id"] = "other-core-legal-controller"
        _rehash_chain(rows)
        _rewrite(core_path, rows)
        _expect_refusal(
            lambda: project_m3(core_path, episode_path), "writer/authority mismatch"
        )
    print("ok  M3 refusal: Core-legal writer substitution still loses")


def test_track_b_cannot_mint_state_or_boundary_receipts():
    track_b_index = next(
        index
        for index, (_, _, surface, _) in enumerate(M3_CASES)
        if surface == TRACK_B_SURFACE
    )
    for mutation_name in ("state", "receipt"):
        with TemporaryDirectory() as td:
            directory = Path(td)
            _, episode_path, core_path = _ingested(directory, track_b_index)
            store = LineageStore(core_path)
            carried = next(
                row for row in store.rows() if row["kind"] == SOURCE_EVENT_KIND
            )
            if mutation_name == "state":
                store.append(
                    "state_item_admitted",
                    writer=ADAPTER_WRITER,
                    authority="controller_transition",
                    causal_parent_ids=[carried["event_id"]],
                    warrant_event_ids=[carried["event_id"]],
                    payload={
                        "item_id": "m3:atk-1aa2b813:r-poison",
                        "item_kind": ITEM_KIND,
                        "status": "active",
                        "placement": "hot",
                        "detail": {},
                    },
                )
            else:
                store.append(
                    RECEIPT_EVENT_KIND,
                    writer=ADAPTER_WRITER,
                    authority="wire_diagnostic",
                    causal_parent_ids=[carried["event_id"]],
                    payload={
                        "item_id": "m3:atk-1aa2b813:r-poison",
                        "source_event_id": carried["event_id"],
                        "source_row_index": carried["payload"]["source_row_index"],
                        "source_kind": carried["payload"]["source_kind"],
                        "run_id": None,
                        "branch_id": None,
                        "record_id": "r-poison",
                        "decision": "offer",
                        "source_reason": "asserted trust",
                    },
                )
            _expect_refusal(
                lambda: project_m3(core_path, episode_path),
                "Track B cannot mint",
            )
    print("ok  M3 refusal: Track B asserted trust cannot become Core standing")


def test_historical_verdicts_are_stripped_before_fresh_m3_scoring():
    source_path, episode_path, _, expected = next(
        case for case in M3_CASES if case[2] == TRACK_B_SURFACE
    )
    rows = [
        json.loads(line)
        for line in source_path.read_text(encoding="utf-8").splitlines()
    ]
    assert sum(row["kind"] == "cell_verdict" for row in rows) == 2
    with TemporaryDirectory() as td:
        verdicts = _fresh_m3_verdicts(rows, episode_path, Path(td), "fresh")
    assert {row["cell"]: row["verdict"] for row in verdicts} == expected
    print("ok  M3 scorer: historical verdicts cannot ride into fresh comparison")


def test_unchanged_m3_scorer_fails_store_digest_precondition_mismatch():
    source_path, episode_path, _, _ = _case()
    rows = [
        json.loads(line)
        for line in source_path.read_text(encoding="utf-8").splitlines()
    ]
    attack = next(row for row in rows if row["kind"] == "attack")
    attack["store_digest"] = "bad-store-digest"
    with TemporaryDirectory() as td:
        verdicts = _fresh_m3_verdicts(rows, episode_path, Path(td), "tampered")
    assert verdicts
    assert all(row["verdict"] == "fail" for row in verdicts)
    assert all(
        "store_integrity" in row["evidence"].get("failed", []) for row in verdicts
    )
    print("ok  M3 scorer: store-digest precondition mismatch remains fail-closed")


if __name__ == "__main__":
    tests = sorted(
        (name, function)
        for name, function in globals().items()
        if name.startswith("test_") and callable(function)
    )
    for _, function in tests:
        function()
    print(f"\nALL {len(tests)} BODY CORE M3 ADAPTER TESTS PASS")
