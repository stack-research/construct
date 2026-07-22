"""Wire tests for Body Core v0.3 and its preserved v0.2 policy projector.

These tests establish envelope integrity, fail-closed replay, and deterministic
views only. They are not memory evidence.
"""

from __future__ import annotations

import hashlib
import json
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory

from sketches.next_substrate.correspondence import index_bound_state_receipts
from sketches.next_substrate.core import (
    LineageStore as KernelLineageStore,
    ReplayRefusal,
    Writer,
)
from sketches.next_substrate.policy import (
    POLICY_MUTATING_EVENT_KINDS,
    POLICY_PROFILE_ID,
    V02_POLICY_PROJECTOR,
)


LineageStore = partial(KernelLineageStore, projector=V02_POLICY_PROJECTOR)


RUNTIME = Writer("test-runtime", "runtime")
CONTROLLER = Writer("test-controller", "controller")
OBSERVER = Writer("test-observer", "observer")
MODEL = Writer("test-model", "model")


def _seed(store: LineageStore) -> tuple[dict, dict]:
    start = store.append(
        "sketch_started",
        writer=RUNTIME,
        authority="administration",
        payload={"claim_boundary": "wire only"},
    )
    warrant = store.append(
        "consequence_observed",
        writer=OBSERVER,
        authority="external_consequence",
        causal_parent_ids=[start["event_id"]],
        payload={"score": 0.0},
    )
    return start, warrant


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


def _source_bound_store(path: Path) -> tuple[LineageStore, dict, dict]:
    store = LineageStore(path)
    _, warrant = _seed(store)
    source = store.append(
        "test_source_row_carried",
        writer=OBSERVER,
        authority="external_observation",
        causal_parent_ids=[warrant["event_id"]],
        payload={
            "source_phase": "s2",
            "source_row_index": 7,
            "source_kind": "meta",
        },
    )
    store.append(
        "state_item_admitted",
        writer=CONTROLLER,
        authority="controller_transition",
        causal_parent_ids=[source["event_id"]],
        warrant_event_ids=[warrant["event_id"]],
        payload={
            "item_id": "bound-item",
            "item_kind": "test",
            "status": "probationary",
            "placement": "hot",
            "detail": {},
        },
    )
    receipt = store.append(
        "state_item_transition",
        writer=CONTROLLER,
        authority="controller_transition",
        causal_parent_ids=[source["event_id"]],
        payload={
            "item_id": "bound-item",
            "from_status": "probationary",
            "to_status": "active",
            "source_event_id": source["event_id"],
            "source_phase": "s2",
            "source_row_index": 7,
            "source_kind": "meta",
        },
    )
    return store, source, receipt


def _index_test_receipts(store: LineageStore):
    return index_bound_state_receipts(
        store.replay().rows,
        source_event_kind="test_source_row_carried",
        receipt_event_kinds={"state_item_transition"},
        affected_item_ids={"bound-item"},
        coordinate_fields=("source_phase", "source_row_index", "source_kind"),
        context="test",
    )


def test_source_binding_indexes_valid_receipts():
    with TemporaryDirectory() as td:
        store, source, receipt = _source_bound_store(Path(td) / "lineage.jsonl")
        bindings = _index_test_receipts(store)
        assert bindings.receipts == (receipt,)
        assert bindings.receipts_by_source == {source["event_id"]: (receipt,)}
    print("ok  correspondence: valid source-bound receipt is indexed")


def test_source_binding_requires_explicit_source_id():
    with TemporaryDirectory() as td:
        path = Path(td) / "lineage.jsonl"
        store, _, receipt = _source_bound_store(path)
        rows = store.raw_rows()
        rows[receipt["event_index"] - 1]["payload"].pop("source_event_id")
        _rehash_chain(rows)
        _rewrite(path, rows)
        try:
            _index_test_receipts(store)
        except ReplayRefusal as exc:
            assert "lacks source_event_id" in str(exc)
        else:
            raise AssertionError("state receipt without source id was indexed")
    print("ok  correspondence refusal: explicit source id is required")


def test_source_binding_requires_causal_parent():
    with TemporaryDirectory() as td:
        path = Path(td) / "lineage.jsonl"
        store, _, receipt = _source_bound_store(path)
        rows = store.raw_rows()
        rows[receipt["event_index"] - 1]["causal_parent_ids"] = []
        _rehash_chain(rows)
        _rewrite(path, rows)
        try:
            _index_test_receipts(store)
        except ReplayRefusal as exc:
            assert "must be a causal parent" in str(exc)
        else:
            raise AssertionError("non-causal source binding was indexed")
    print("ok  correspondence refusal: source id must be a causal parent")


def test_source_binding_requires_declared_source_kind():
    with TemporaryDirectory() as td:
        path = Path(td) / "lineage.jsonl"
        store, _, receipt = _source_bound_store(path)
        rows = store.raw_rows()
        rows[receipt["event_index"] - 1]["payload"]["source_event_id"] = receipt[
            "event_id"
        ]
        _rehash_chain(rows)
        _rewrite(path, rows)
        try:
            _index_test_receipts(store)
        except ReplayRefusal as exc:
            assert "is not a test_source_row_carried event" in str(exc)
        else:
            raise AssertionError("binding to a non-source event was indexed")
    print("ok  correspondence refusal: binding target must be a carried source")


def test_source_binding_requires_exact_coordinates():
    with TemporaryDirectory() as td:
        path = Path(td) / "lineage.jsonl"
        store, _, receipt = _source_bound_store(path)
        rows = store.raw_rows()
        rows[receipt["event_index"] - 1]["payload"]["source_row_index"] = 8
        _rehash_chain(rows)
        _rewrite(path, rows)
        try:
            _index_test_receipts(store)
        except ReplayRefusal as exc:
            assert "source coordinate 'source_row_index'" in str(exc)
        else:
            raise AssertionError("coordinate-drifted source binding was indexed")
    print("ok  correspondence refusal: source coordinates must match")


def test_replay_derives_state_warrant_placement_and_metabolism():
    with TemporaryDirectory() as td:
        store = LineageStore(Path(td) / "lineage.jsonl")
        _, warrant = _seed(store)
        admitted = store.append(
            "state_item_admitted",
            writer=CONTROLLER,
            authority="controller_transition",
            causal_parent_ids=[warrant["event_id"]],
            warrant_event_ids=[warrant["event_id"]],
            payload={
                "item_id": "item-1",
                "item_kind": "procedure",
                "status": "probationary",
                "placement": "hot",
                "detail": {"procedure_id": "check-before-commit"},
            },
        )
        store.append(
            "placement_changed",
            writer=CONTROLLER,
            authority="controller_transition",
            causal_parent_ids=[admitted["event_id"]],
            warrant_event_ids=[warrant["event_id"]],
            payload={
                "item_id": "item-1",
                "from_placement": "hot",
                "to_placement": "cold",
                "reason": "wire exercise",
            },
        )
        store.append(
            "metabolic_event",
            writer=CONTROLLER,
            authority="controller_transition",
            causal_parent_ids=[admitted["event_id"]],
            payload={"item_id": "item-1", "metric": "check_steps", "units": 2},
        )
        claim = store.append_view_claim(writer=RUNTIME)

        result = store.replay()
        item = result.views.state_items["item-1"]
        assert item.status == "probationary"
        assert item.placement == "cold"
        assert result.views.warrant_health[warrant["event_id"]] == "current"
        assert result.views.dependents_by_warrant[warrant["event_id"]] == ["item-1"]
        assert result.views.reported_metabolic_totals["item-1"] == {"check_steps": 2}
        assert result.verified_view_claim_ids == (claim["event_id"],)
        print("ok  views: state + warrant + placement + metabolism rebuild")


def test_cold_reconstruction_is_byte_stable():
    with TemporaryDirectory() as td:
        path = Path(td) / "lineage.jsonl"
        store = LineageStore(path)
        _, warrant = _seed(store)
        store.append(
            "state_item_admitted",
            writer=CONTROLLER,
            authority="controller_transition",
            warrant_event_ids=[warrant["event_id"]],
            payload={
                "item_id": "item-1",
                "item_kind": "claim",
                "status": "active",
                "placement": "hot",
                "detail": {"scope": "test"},
            },
        )
        before = store.replay().views.digest()
        after = LineageStore(path).replay().views.digest()
        assert before == after
        print("ok  replay: process-cold reconstruction has identical digest")


def test_payload_tamper_is_refused():
    with TemporaryDirectory() as td:
        path = Path(td) / "lineage.jsonl"
        store = LineageStore(path)
        _seed(store)
        rows = store.raw_rows()
        rows[1]["payload"]["score"] = 1.0
        _rewrite(path, rows)
        try:
            store.replay()
        except ReplayRefusal as exc:
            assert "event_hash mismatch" in str(exc)
        else:
            raise AssertionError("mutated payload survived replay")
        print("ok  refusal: payload mutation breaks the event hash")


def test_deletion_and_reordering_are_refused():
    with TemporaryDirectory() as td:
        path = Path(td) / "lineage.jsonl"
        store = LineageStore(path)
        _seed(store)
        third = store.append(
            "model_action",
            writer=MODEL,
            authority="model_proposal",
            payload={"action": "wait"},
        )
        assert third["event_index"] == 3
        rows = store.raw_rows()

        _rewrite(path, [rows[0], rows[2]])
        try:
            store.replay()
        except ReplayRefusal as exc:
            assert "expected ev-000002" in str(exc)
        else:
            raise AssertionError("deleted row survived replay")

        _rewrite(path, [rows[1], rows[0], rows[2]])
        try:
            store.replay()
        except ReplayRefusal:
            pass
        else:
            raise AssertionError("reordered rows survived replay")
        print("ok  refusal: deletion and reordering break lineage")


def test_authority_and_dangling_references_are_refused_before_append():
    with TemporaryDirectory() as td:
        store = LineageStore(Path(td) / "lineage.jsonl")
        _seed(store)
        count = len(store.rows())
        try:
            store.append(
                "forged_consequence",
                writer=MODEL,
                authority="external_consequence",
                payload={},
            )
        except ReplayRefusal as exc:
            assert "cannot exercise" in str(exc)
        else:
            raise AssertionError("model minted external consequence authority")
        assert len(store.rows()) == count

        try:
            store.append(
                "dangling",
                writer=RUNTIME,
                authority="system_record",
                causal_parent_ids=["ev-999999"],
                payload={},
            )
        except ReplayRefusal as exc:
            assert "dangling causal_parent_ids" in str(exc)
        else:
            raise AssertionError("dangling causal parent was appended")
        assert len(store.rows()) == count
        print("ok  refusal: authority and backward-reference rules fail before write")


def test_reference_and_redaction_retention_are_enveloped_without_payload():
    with TemporaryDirectory() as td:
        store = LineageStore(Path(td) / "lineage.jsonl")
        start, _ = _seed(store)
        digest = hashlib.sha256(b"external payload").hexdigest()
        reference = store.append(
            "external_payload_referenced",
            writer=OBSERVER,
            authority="external_observation",
            causal_parent_ids=[start["event_id"]],
            retention={
                "mode": "reference",
                "external_ref": "artifact://example/source",
                "digest": digest,
            },
        )
        redacted = store.append(
            "sensitive_payload_redacted",
            writer=OBSERVER,
            authority="external_observation",
            causal_parent_ids=[reference["event_id"]],
            retention={
                "mode": "redacted",
                "digest": digest,
                "reason": "wire-only privacy boundary",
            },
        )
        rows = store.replay().rows
        assert rows[-2]["payload"] == {}
        assert rows[-1]["payload"] == {}
        assert redacted["retention"]["mode"] == "redacted"
        print("ok  retention: reference and redaction preserve envelope, not payload")


def test_impossible_transition_is_refused_before_append():
    with TemporaryDirectory() as td:
        store = LineageStore(Path(td) / "lineage.jsonl")
        _, warrant = _seed(store)
        store.append(
            "state_item_admitted",
            writer=CONTROLLER,
            authority="controller_transition",
            warrant_event_ids=[warrant["event_id"]],
            payload={
                "item_id": "retired-item",
                "item_kind": "procedure",
                "status": "retired",
                "placement": "cold",
            },
        )
        count = len(store.rows())
        try:
            store.append(
                "state_item_transition",
                writer=CONTROLLER,
                authority="controller_transition",
                payload={
                    "item_id": "retired-item",
                    "from_status": "retired",
                    "to_status": "active",
                    "reason": "forged resurrection",
                },
            )
        except ReplayRefusal as exc:
            assert "illegal state transition" in str(exc)
        else:
            raise AssertionError("retired item returned to active state")
        assert len(store.rows()) == count
        print("ok  refusal: impossible state transition never reaches disk")


def test_stale_materialized_view_claim_is_refused():
    with TemporaryDirectory() as td:
        path = Path(td) / "lineage.jsonl"
        store = LineageStore(path)
        _seed(store)
        claim = store.append_view_claim(writer=RUNTIME)
        rows = store.raw_rows()
        rows[-1]["payload"]["view_digest"] = "f" * 64
        # Recompute only the envelope hash to prove replay distrusts the view,
        # not merely the outer tamper chain.
        unsigned = {
            key: value for key, value in rows[-1].items() if key != "event_hash"
        }
        canonical = json.dumps(
            unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        rows[-1]["event_hash"] = hashlib.sha256(canonical.encode()).hexdigest()
        _rewrite(path, rows)
        try:
            store.replay()
        except ReplayRefusal as exc:
            assert claim["event_id"] in str(exc)
            assert "view digest mismatch" in str(exc)
        else:
            raise AssertionError("stale materialized view was trusted")
        print("ok  refusal: rehashed stale view loses to full replay")


def test_invalid_warrant_suspends_dependents_without_projection_row():
    with TemporaryDirectory() as td:
        store = LineageStore(Path(td) / "lineage.jsonl")
        _, warrant = _seed(store)
        store.append(
            "state_item_admitted",
            writer=CONTROLLER,
            authority="controller_transition",
            warrant_event_ids=[warrant["event_id"]],
            payload={
                "item_id": "dependent",
                "item_kind": "procedure",
                "status": "active",
                "placement": "hot",
            },
        )
        store.append(
            "provenance_revision",
            writer=OBSERVER,
            authority="external_observation",
            causal_parent_ids=[warrant["event_id"]],
            payload={
                "target_event_id": warrant["event_id"],
                "health": "invalid",
                "reason": "external warrant revoked",
            },
        )
        views = store.replay().views
        assert views.warrant_health[warrant["event_id"]] == "invalid"
        assert views.state_items["dependent"].status == "suspended"
        print("ok  warrant: invalidation suspends dependents during replay")


def test_invalid_warrant_cannot_be_reactivated():
    with TemporaryDirectory() as td:
        store = LineageStore(Path(td) / "lineage.jsonl")
        _, warrant = _seed(store)
        store.append(
            "state_item_admitted",
            writer=CONTROLLER,
            authority="controller_transition",
            warrant_event_ids=[warrant["event_id"]],
            payload={
                "item_id": "dependent",
                "item_kind": "procedure",
                "status": "active",
                "placement": "hot",
            },
        )
        revision = store.append(
            "provenance_revision",
            writer=OBSERVER,
            authority="external_observation",
            causal_parent_ids=[warrant["event_id"]],
            payload={
                "target_event_id": warrant["event_id"],
                "health": "invalid",
                "reason": "external warrant revoked",
            },
        )
        count = len(store.rows())
        try:
            store.append(
                "state_item_transition",
                writer=CONTROLLER,
                authority="controller_transition",
                causal_parent_ids=[revision["event_id"]],
                warrant_event_ids=[warrant["event_id"]],
                payload={
                    "item_id": "dependent",
                    "from_status": "suspended",
                    "to_status": "active",
                    "reason": "attempted bypass",
                },
            )
        except ReplayRefusal as exc:
            assert "unhealthy warrants" in str(exc)
        else:
            raise AssertionError("invalid warrant returned to active state")
        assert len(store.rows()) == count
        print("ok  refusal: invalid warrant cannot be reactivated")


def test_invalid_warrant_cannot_mint_new_active_state():
    with TemporaryDirectory() as td:
        store = LineageStore(Path(td) / "lineage.jsonl")
        _, warrant = _seed(store)
        revision = store.append(
            "provenance_revision",
            writer=OBSERVER,
            authority="external_observation",
            causal_parent_ids=[warrant["event_id"]],
            payload={
                "target_event_id": warrant["event_id"],
                "health": "invalid",
                "reason": "external warrant revoked",
            },
        )
        count = len(store.rows())
        try:
            store.append(
                "state_item_admitted",
                writer=CONTROLLER,
                authority="controller_transition",
                causal_parent_ids=[revision["event_id"]],
                warrant_event_ids=[warrant["event_id"]],
                payload={
                    "item_id": "late-dependent",
                    "item_kind": "procedure",
                    "status": "active",
                    "placement": "hot",
                },
            )
        except ReplayRefusal as exc:
            assert "cannot admit active state with unhealthy warrants" in str(exc)
        else:
            raise AssertionError("invalid warrant minted new active state")
        assert len(store.rows()) == count
        print("ok  refusal: invalid warrant cannot mint active state")


def test_duplicate_parent_and_warrant_references_are_refused():
    with TemporaryDirectory() as td:
        store = LineageStore(Path(td) / "lineage.jsonl")
        start, warrant = _seed(store)
        for field, references in (
            ("causal_parent_ids", [start["event_id"], start["event_id"]]),
            ("warrant_event_ids", [warrant["event_id"], warrant["event_id"]]),
        ):
            kwargs = {field: references}
            try:
                store.append(
                    "duplicate_reference_probe",
                    writer=CONTROLLER,
                    authority="wire_diagnostic",
                    payload={},
                    **kwargs,
                )
            except ReplayRefusal as exc:
                assert f"duplicate {field}" in str(exc)
            else:
                raise AssertionError(f"duplicate {field} survived")
        print("ok  refusal: duplicate parents and warrants are not ambiguous")


def test_invalid_retention_shapes_are_refused():
    invalid = (
        ({"mode": "reference", "digest": "bad", "external_ref": "artifact://x"}, {}),
        ({"mode": "reference", "digest": "a" * 64}, {}),
        ({"mode": "redacted", "digest": "a" * 64}, {}),
    )
    with TemporaryDirectory() as td:
        store = LineageStore(Path(td) / "lineage.jsonl")
        _seed(store)
        for retention, payload in invalid:
            try:
                store.append(
                    "retention_probe",
                    writer=OBSERVER,
                    authority="external_observation",
                    retention=retention,
                    payload=payload,
                )
            except ReplayRefusal:
                pass
            else:
                raise AssertionError(f"invalid retention survived: {retention}")
        print("ok  refusal: invalid retention shapes fail closed")


def test_disputed_warrant_cannot_reactivate_suspended_state():
    with TemporaryDirectory() as td:
        store = LineageStore(Path(td) / "lineage.jsonl")
        _, warrant = _seed(store)
        store.append(
            "state_item_admitted",
            writer=CONTROLLER,
            authority="controller_transition",
            warrant_event_ids=[warrant["event_id"]],
            payload={
                "item_id": "disputed-dependent",
                "item_kind": "procedure",
                "status": "suspended",
                "placement": "hot",
            },
        )
        revision = store.append(
            "provenance_revision",
            writer=OBSERVER,
            authority="external_observation",
            payload={
                "target_event_id": warrant["event_id"],
                "health": "disputed",
            },
        )
        try:
            store.append(
                "state_item_transition",
                writer=CONTROLLER,
                authority="controller_transition",
                causal_parent_ids=[revision["event_id"]],
                payload={
                    "item_id": "disputed-dependent",
                    "from_status": "suspended",
                    "to_status": "active",
                },
            )
        except ReplayRefusal as exc:
            assert "unhealthy warrants" in str(exc)
        else:
            raise AssertionError("disputed warrant reactivated state")
        print("ok  refusal: disputed warrant blocks reactivation")


def test_mid_chain_rehash_does_not_repair_descendant_link():
    with TemporaryDirectory() as td:
        path = Path(td) / "lineage.jsonl"
        store = LineageStore(path)
        _seed(store)
        store.append(
            "third_event",
            writer=RUNTIME,
            authority="system_record",
            payload={},
        )
        rows = store.raw_rows()
        rows[1]["payload"]["score"] = 1.0
        unsigned = {key: value for key, value in rows[1].items() if key != "event_hash"}
        canonical = json.dumps(
            unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        rows[1]["event_hash"] = hashlib.sha256(canonical.encode()).hexdigest()
        _rewrite(path, rows)
        try:
            store.replay()
        except ReplayRefusal as exc:
            assert "previous_event_hash mismatch" in str(exc)
        else:
            raise AssertionError("mid-chain rehash repaired its descendant")
        print("ok  refusal: local rehash cannot repair the rest of the chain")


def test_unknown_invocation_and_encounter_scopes_are_refused():
    with TemporaryDirectory() as td:
        store = LineageStore(Path(td) / "lineage.jsonl")
        _seed(store)
        for scope in (
            {"invocation_id": "ev-999998"},
            {"encounter_id": "ev-999999"},
        ):
            try:
                store.append(
                    "scope_probe",
                    writer=RUNTIME,
                    authority="system_record",
                    payload={},
                    **scope,
                )
            except ReplayRefusal as exc:
                assert "unknown" in str(exc) and "scope" in str(exc)
            else:
                raise AssertionError(f"unknown scope survived: {scope}")
        print("ok  refusal: event scopes must name established boundaries")


def test_blank_line_is_refused_instead_of_silently_skipped():
    with TemporaryDirectory() as td:
        path = Path(td) / "lineage.jsonl"
        store = LineageStore(path)
        _seed(store)
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text(f"{lines[0]}\n\n{lines[1]}\n", encoding="utf-8")
        try:
            store.replay()
        except ReplayRefusal as exc:
            assert "blank lines are not permitted" in str(exc)
        else:
            raise AssertionError("blank lineage row was silently skipped")
        print("ok  refusal: blank lineage rows fail closed")


def test_cognitive_replay_and_view_claim_require_explicit_projector():
    with TemporaryDirectory() as td:
        store = KernelLineageStore(Path(td) / "lineage.jsonl")
        store.append(
            "sketch_started",
            writer=RUNTIME,
            authority="administration",
            payload={"claim_boundary": "kernel only"},
        )
        assert len(store.rows()) == 1
        for operation in (
            store.replay,
            lambda: store.append_view_claim(writer=RUNTIME),
        ):
            try:
                operation()
            except ReplayRefusal as exc:
                assert "explicit projector required" in str(exc)
            else:
                raise AssertionError("kernel-only store certified cognitive state")
        print("ok  projection refusal: cognitive access requires explicit selection")


def test_kernel_validation_does_not_certify_policy_view_claim():
    with TemporaryDirectory() as td:
        path = Path(td) / "lineage.jsonl"
        policy_store = LineageStore(path)
        _seed(policy_store)
        claim = policy_store.append_view_claim(writer=RUNTIME)
        rows = policy_store.raw_rows()
        rows[-1]["payload"]["view_digest"] = "f" * 64
        _rehash(rows[-1])
        _rewrite(path, rows)

        kernel_store = KernelLineageStore(path)
        assert kernel_store.rows()[-1]["event_id"] == claim["event_id"]
        try:
            policy_store.replay()
        except ReplayRefusal as exc:
            assert "view digest mismatch" in str(exc)
        else:
            raise AssertionError("policy projector trusted a stale view claim")
        print("ok  projection refusal: kernel validation cannot certify a view claim")


def test_unowned_kind_changes_only_the_policy_cursor():
    with TemporaryDirectory() as td:
        store = LineageStore(Path(td) / "lineage.jsonl")
        _seed(store)
        before = store.replay().views
        before_canonical = before.canonical()

        unowned_kind = "wire_causal_probe"
        assert unowned_kind not in POLICY_MUTATING_EVENT_KINDS
        row = store.append(
            unowned_kind,
            writer=CONTROLLER,
            authority="wire_diagnostic",
            payload={"effect": "authored probe only"},
        )
        after = store.replay().views
        after_canonical = after.canonical()

        assert before.policy_profile_id == after.policy_profile_id == POLICY_PROFILE_ID
        assert after.event_count == before.event_count + 1
        assert after.through_event_id == row["event_id"]
        assert before.digest() != after.digest()
        for cursor_field in ("event_count", "through_event_id"):
            before_canonical.pop(cursor_field)
            after_canonical.pop(cursor_field)
        assert before_canonical == after_canonical
        print(
            "ok  projection: unowned row advances cursor without mutating policy state"
        )


def test_split_does_not_add_a_generic_kind_authority_rule():
    with TemporaryDirectory() as td:
        store = LineageStore(Path(td) / "lineage.jsonl")
        _, warrant = _seed(store)
        store.append(
            "state_item_admitted",
            writer=MODEL,
            authority="model_proposal",
            warrant_event_ids=[warrant["event_id"]],
            payload={
                "item_id": "historical-route-shape",
                "item_kind": "test",
                "status": "probationary",
                "placement": "hot",
            },
        )
        assert "historical-route-shape" in store.replay().views.state_items
        print("ok  preservation: split adds no generic kind-authority policy")


if __name__ == "__main__":
    tests = sorted(
        (name, fn)
        for name, fn in globals().items()
        if name.startswith("test_") and callable(fn)
    )
    for _, fn in tests:
        fn()
    print(f"\nALL {len(tests)} BODY CORE V0.3 TESTS PASS")
