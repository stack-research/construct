"""On-disk EFC v2 battery regression — SPEC §B authored suite."""

from __future__ import annotations

import json

import pytest

from harness.efc_author_battery_v2 import (
    K_PAIRS,
    assert_authoring_invariants,
    build_suite,
)
from harness.efc_fixtures_v2 import (
    FIXTURES_DIR,
    SUITE_DIR,
    suite_hash,
    validate_suite,
)
from harness.efc_leak_audit_v2 import evaluate_leak_audit
from harness.efc_provenance_record_store_v2 import (
    build_record_store_from_fixtures,
    record_store_canonical_payload,
)


def load_disk_suite() -> list[dict]:
    manifest_path = SUITE_DIR / "suite_manifest.json"
    if not manifest_path.is_file():
        pytest.skip("battery not authored on disk")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [
        json.loads(
            (FIXTURES_DIR / f"{entry['fixture_id']}.json").read_text(
                encoding="utf-8"
            )
        )
        for entry in manifest["fixtures"]
    ]


def test_disk_suite_matches_deterministic_author() -> None:
    disk = load_disk_suite()
    built = build_suite()
    assert disk == built


def test_disk_suite_validates() -> None:
    fixtures = load_disk_suite()
    store = build_record_store_from_fixtures(fixtures)
    result = validate_suite(fixtures, record_store=store)
    assert result.ok, result.refusals[:5]
    assert result.fixture_count == 3 * K_PAIRS


def test_disk_suite_leak_audit_green() -> None:
    fixtures = load_disk_suite()
    leak = evaluate_leak_audit(fixtures)
    assert leak.ok, leak.refusals
    for cell in leak.cells:
        assert cell.passed
        if cell.leg in ("L1", "L2"):
            assert cell.accuracy == pytest.approx(0.25)
        else:
            assert cell.accuracy == pytest.approx(0.50)


def test_authoring_invariants_hold() -> None:
    assert_authoring_invariants(load_disk_suite())


def test_disk_record_store_matches_fixtures() -> None:
    fixtures = load_disk_suite()
    store = build_record_store_from_fixtures(fixtures)
    on_disk = json.loads(
        (SUITE_DIR / "provenance_record_store.json").read_text(encoding="utf-8")
    )
    assert on_disk == record_store_canonical_payload(store)


def test_suite_hash_stable() -> None:
    fixtures = load_disk_suite()
    store = build_record_store_from_fixtures(fixtures)
    digest = suite_hash(fixtures, k_pairs=K_PAIRS, record_store=store)
    assert digest == (
        "aca52a4a78c0aaf25731758aeff89bfd1f3c79585114e76c25f3fe3cf9065df0"
    )
