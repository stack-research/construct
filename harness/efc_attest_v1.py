"""EFC v1 attestation applier — records the cold_fixture_reviewer's signed ruling.

This module NEVER authors a plausibility judgment. It materializes attestation
records from an explicit, already-published human ruling (a substrate entry by
the cold_fixture_reviewer), stamping each fixture with the ruling's authority
pointer. Fabrication is structurally excluded: the applier requires the ruling
entry's runtime filename and timestamp as inputs, and the attestation_id is a
deterministic hash of (fixture_id, ruling entry filename) — nothing here can
mint an attestation without naming the human entry it records.

Pre-attestation fixture bytes remain in lineage (committed at D5 lifecycle
close); this applier performs the declared attestation transition of the D5
lifecycle, not an in-place mutation of unreviewed shape.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from harness.efc_fixtures_v1 import sha256_canon, validate_suite

COLD_FIXTURE_REVIEWER_SEAT = "cold_fixture_reviewer"


def attestation_for(
    fixture: dict[str, Any],
    ruling_entry_filename: str,
    ruling_timestamp_utc: str,
) -> dict[str, str]:
    """Deterministic attestation record for one fixture from one ruling entry."""
    if not ruling_entry_filename or not ruling_timestamp_utc:
        raise ValueError("ruling entry filename and timestamp are required")
    digest = hashlib.sha256(
        f"{fixture['fixture_id']}\n{ruling_entry_filename}".encode("utf-8")
    ).hexdigest()
    return {
        "fixture_id": fixture["fixture_id"],
        "stratum": fixture["stratum"],
        "reviewer_seat": COLD_FIXTURE_REVIEWER_SEAT,
        "reviewed_at": ruling_timestamp_utc,
        "attestation_id": f"efc-v1-att-{digest[:16]}",
    }


def apply_attestations(
    fixtures_dir: Path,
    manifest_path: Path,
    ruling_entry_filename: str,
    ruling_timestamp_utc: str,
) -> dict[str, Any]:
    """Stamp every pending fixture, revalidate strictly, and update the manifest.

    Returns the updated manifest dict. Raises on any strict-gate refusal so a
    failed attestation pass never leaves mixed state without an error.
    """
    fixture_paths = sorted(fixtures_dir.glob("efc_v1-*.json"))
    fixtures: list[dict[str, Any]] = []
    for path in fixture_paths:
        fx = json.loads(path.read_text(encoding="utf-8"))
        if "plausibility_attestation" in fx:
            raise ValueError(f"{fx['fixture_id']}: attestation already present")
        fx["plausibility_attestation"] = attestation_for(
            fx, ruling_entry_filename, ruling_timestamp_utc
        )
        fixtures.append(fx)

    result = validate_suite(fixtures)  # strict default: attestation required
    if result.refusals:
        raise ValueError(f"post-attestation validation refused: {result.refusals}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for fx, path in zip(fixtures, fixture_paths):
        path.write_text(
            json.dumps(fx, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    manifest["attestation_status"] = "signed"
    manifest["attestation_pending"] = []
    manifest["attestation_authority"] = {
        "ruling_entry": ruling_entry_filename,
        "ruling_timestamp_utc": ruling_timestamp_utc,
        "reviewer_seat": COLD_FIXTURE_REVIEWER_SEAT,
    }
    by_id = {fx["fixture_id"]: fx for fx in fixtures}
    manifest["fixtures"] = [
        {**row, "fixture_sha256": sha256_canon(by_id[row["fixture_id"]])}
        for row in manifest["fixtures"]
    ]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
