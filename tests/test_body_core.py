"""Wire tests for Body Core v0.2.

These tests establish envelope integrity, fail-closed replay, and deterministic
views only. They are not memory evidence.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from sketches.next_substrate.core import LineageStore, ReplayRefusal, Writer


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


if __name__ == "__main__":
    tests = sorted(
        (name, fn)
        for name, fn in globals().items()
        if name.startswith("test_") and callable(fn)
    )
    for _, fn in tests:
        fn()
    print(f"\nALL {len(tests)} BODY CORE V0.2 TESTS PASS")
