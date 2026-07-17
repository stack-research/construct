"""Authoritative provenance record store — SPEC_EPISTEMIC_FRAME_CHECK_V2 §B.

Schema and validator only: population-pinned records keyed by
``source_reference``. The suite validator resolves each reference, compares
``authoritative_scope`` against ``decision_scope`` the way named check C does,
and derives covers vs exactly-one-dimension-miss. No battery content is
authored here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from harness.efc_menu_composition_v2 import (
    RELEVANT_STRATA,
    SCOPE_BIT_LEXICAL_MARKERS,
    SCOPE_DIMENSIONS,
    CompositionCheck,
    provenance_carries_scope_lexicon,
)

ScopeVerdict = Literal["covers", "misses"]

STORE_SCHEMA_VERSION = "efc_provenance_record_store_v2"


@dataclass(frozen=True)
class ProvenanceRecordEntry:
    record_id: str
    source_reference: str
    authoritative_scope: str


@dataclass(frozen=True)
class ProvenanceRecordStore:
    schema_version: str
    records: tuple[ProvenanceRecordEntry, ...]

    def fetch(self, source_reference: str) -> ProvenanceRecordEntry:
        for record in self.records:
            if record.source_reference == source_reference:
                return record
        raise KeyError(source_reference)


def _canon_bytes(obj: object) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def parse_scope_dimensions(scope: str) -> dict[str, str]:
    """Parse a frozen semicolon-separated scope string (all five dimensions)."""
    dims = parse_scope_dimensions_partial(scope)
    missing = [dim for dim in SCOPE_DIMENSIONS if dim not in dims]
    if missing:
        raise ValueError(f"scope missing dimensions: {missing}")
    return dims


def parse_scope_dimensions_partial(scope: str) -> dict[str, str]:
    """Parse scope dimensions present in an authoritative record."""
    if not isinstance(scope, str) or not scope.strip():
        raise ValueError("scope must be a non-empty string")
    dims: dict[str, str] = {}
    for fragment in scope.split(";"):
        piece = fragment.strip()
        if not piece:
            continue
        if "=" not in piece:
            raise ValueError(f"malformed scope fragment: {piece!r}")
        key, value = piece.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key not in SCOPE_DIMENSIONS:
            raise ValueError(f"unknown scope dimension: {key!r}")
        if not value:
            raise ValueError(f"empty scope value for dimension {key!r}")
        dims[key] = value
    return dims


def format_scope_dimensions(dimensions: dict[str, str]) -> str:
    """Canonical scope serialization — sorted keys, no lexical scope-bit markers."""
    ordered = {dim: dimensions[dim] for dim in SCOPE_DIMENSIONS if dim in dimensions}
    return ";".join(f"{key}={ordered[key]}" for key in sorted(ordered))


def decision_scope_for_block(block_index: int) -> str:
    """Neutral synthetic decision scope for wire fixtures (not battery content)."""
    return format_scope_dimensions({
        "population": f"pop-efc-wire-{block_index:04d}",
        "interval": "2026-Q1",
        "jurisdiction": "us-west",
        "endpoint": "api.example/v1",
        "artifact_version": "1.0",
    })


def authoritative_scope_for_stratum(
    *,
    decision_scope: str,
    stratum: str,
    missing_scope_dimension: str,
) -> str:
    """Build the authoritative scope a mate's record must carry."""
    dims = parse_scope_dimensions(decision_scope)
    if stratum == "match":
        return format_scope_dimensions(dims)
    if missing_scope_dimension not in dims:
        raise ValueError(f"invalid missing_scope_dimension: {missing_scope_dimension!r}")
    narrowed = {key: value for key, value in dims.items() if key != missing_scope_dimension}
    return format_scope_dimensions(narrowed)


def scope_missing_dimensions(authoritative_scope: str, decision_scope: str) -> frozenset[str]:
    """Dimensions required by decision_scope that authoritative_scope does not cover."""
    decision_dims = parse_scope_dimensions(decision_scope)
    try:
        authoritative_dims = parse_scope_dimensions_partial(authoritative_scope)
    except ValueError:
        authoritative_dims = {}
    missing: set[str] = set()
    for dim, required in decision_dims.items():
        actual = authoritative_dims.get(dim)
        if actual != required:
            missing.add(dim)
    return frozenset(missing)


def derive_scope_verdict(
    authoritative_scope: str,
    decision_scope: str,
) -> tuple[ScopeVerdict, str | None]:
    """Named-check-C contract: covers, or misses on exactly one dimension."""
    missing = scope_missing_dimensions(authoritative_scope, decision_scope)
    if not missing:
        return "covers", None
    if len(missing) == 1:
        return "misses", next(iter(missing))
    return "misses", None


def compare_scope_like_check_c(
    authoritative_scope: str,
    decision_scope: str,
) -> bool:
    """Boolean scope comparison — True iff decision_scope is fully covered."""
    verdict, _ = derive_scope_verdict(authoritative_scope, decision_scope)
    return verdict == "covers"


def record_store_canonical_payload(store: ProvenanceRecordStore) -> dict[str, Any]:
    return {
        "schema_version": store.schema_version,
        "records": [
            {
                "record_id": record.record_id,
                "source_reference": record.source_reference,
                "authoritative_scope": record.authoritative_scope,
            }
            for record in sorted(store.records, key=lambda r: r.source_reference)
        ],
    }


def record_store_canonical_bytes(store: ProvenanceRecordStore) -> bytes:
    return _canon_bytes(record_store_canonical_payload(store))


def record_store_hash(store: ProvenanceRecordStore) -> str:
    return hashlib.sha256(record_store_canonical_bytes(store)).hexdigest()


def validate_record_entry_lexical_neutrality(entry: ProvenanceRecordEntry) -> str | None:
    for field in (entry.record_id, entry.source_reference):
        if provenance_carries_scope_lexicon(field):
            return "provenance_lexical_scope_leak"
    return None


def build_record_store(entries: list[ProvenanceRecordEntry]) -> ProvenanceRecordStore:
    """Construct and validate a population-pinned record store."""
    if not entries:
        raise ValueError("record store must contain at least one entry")
    seen_refs: set[str] = set()
    seen_ids: set[str] = set()
    for entry in entries:
        if not entry.record_id or not entry.source_reference:
            raise ValueError("record_id and source_reference must be non-empty")
        if entry.source_reference in seen_refs:
            raise ValueError(
                f"duplicate source_reference in store: {entry.source_reference!r}"
            )
        if entry.record_id in seen_ids:
            raise ValueError(f"duplicate record_id in store: {entry.record_id!r}")
        leak = validate_record_entry_lexical_neutrality(entry)
        if leak:
            raise ValueError(leak)
        seen_refs.add(entry.source_reference)
        seen_ids.add(entry.record_id)
    return ProvenanceRecordStore(
        schema_version=STORE_SCHEMA_VERSION,
        records=tuple(entries),
    )


def build_record_store_from_fixtures(
    fixtures: list[dict[str, Any]],
) -> ProvenanceRecordStore:
    """Synthetic wire helper: derive store bytes from fixture references."""
    entries: list[ProvenanceRecordEntry] = []
    seen_refs: set[str] = set()
    for fixture in fixtures:
        stratum = fixture.get("stratum")
        if stratum not in ("match", "mismatch"):
            continue
        source_reference = fixture.get("source_reference")
        opaque_handle = fixture.get("opaque_source_handle")
        decision_scope = fixture.get("decision_scope")
        missing_dim = fixture.get("missing_scope_dimension")
        if not all(
            isinstance(value, str) and value
            for value in (
                source_reference,
                opaque_handle,
                decision_scope,
                missing_dim,
            )
        ):
            raise ValueError("fixture missing provenance fields for store build")
        if source_reference in seen_refs:
            continue
        seen_refs.add(source_reference)
        authoritative_scope = authoritative_scope_for_stratum(
            decision_scope=decision_scope,
            stratum=stratum,
            missing_scope_dimension=missing_dim,
        )
        entries.append(
            ProvenanceRecordEntry(
                record_id=opaque_handle,
                source_reference=source_reference,
                authoritative_scope=authoritative_scope,
            )
        )
    return build_record_store(entries)


def check_fixture_provenance_against_store(
    fixture: dict[str, Any],
    store: ProvenanceRecordStore,
) -> CompositionCheck:
    """Resolve the pinned reference and verify scope_bit against fetched scope."""
    stratum = fixture.get("stratum")
    if stratum not in RELEVANT_STRATA:
        return CompositionCheck(True)

    source_reference = fixture.get("source_reference")
    decision_scope = fixture.get("decision_scope")
    scope_bit = fixture.get("scope_bit")
    missing_dim = fixture.get("missing_scope_dimension")
    if not all(
        isinstance(value, str) and value
        for value in (source_reference, decision_scope, scope_bit, missing_dim)
    ):
        return CompositionCheck(False, refusal="malformed_fixture")

    try:
        record = store.fetch(source_reference)
    except KeyError:
        return CompositionCheck(False, refusal="provenance_record_missing")

    try:
        verdict, missed_dim = derive_scope_verdict(
            record.authoritative_scope,
            decision_scope,
        )
    except ValueError:
        return CompositionCheck(False, refusal="provenance_record_scope_invalid")

    if scope_bit != verdict:
        return CompositionCheck(False, refusal="provenance_scope_bit_contradicts_record")

    if stratum == "match" and verdict != "covers":
        return CompositionCheck(False, refusal="provenance_scope_bit_contradicts_record")
    if stratum == "mismatch" and verdict != "misses":
        return CompositionCheck(False, refusal="provenance_scope_bit_contradicts_record")
    if verdict == "misses":
        if missed_dim is None or missed_dim != missing_dim:
            return CompositionCheck(
                False,
                refusal="provenance_scope_dimension_contradicts_record",
            )
    return CompositionCheck(True)


def check_suite_provenance_against_store(
    fixtures: list[dict[str, Any]],
    store: ProvenanceRecordStore,
) -> CompositionCheck:
    """Verify every relevant fixture against the authoritative record store."""
    for fixture in fixtures:
        result = check_fixture_provenance_against_store(fixture, store)
        if not result.ok:
            return result
    return CompositionCheck(True)

