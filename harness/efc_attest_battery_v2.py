"""Materialize plausibility attestations for the EFC v2 battery — dan's ruling 2026-07-17.

Attestation rows are NOT authored content. Each row is a mechanical projection
of the cold reviewer's on-record PASS entry in the substrate thread
`epistemic-frame-check-v2`: `reviewed_at` is that entry's timestamp and
`attestation_id` derives from the entry's sha256 plus the fixture id, so every
row is a pointer to the immutable review event, forgeable by no seat. The
author seat runs this script but signs nothing in the reviewer's name.

Provenance (pinned):
- reviewer entry: .substrate/threads/epistemic-frame-check-v2/
  20260717T120953980Z__cursor%2Fglm-5.2.md  (verdict: PASS, zero blockers)
- entry sha256: REVIEW_ENTRY_SHA256 below (recomputed from disk; refuses on drift)

Run:  python -m harness.efc_attest_battery_v2
"""

from __future__ import annotations

import hashlib
import json

from harness.efc_fixtures_v2 import (
    FIXTURES_DIR,
    REPO_ROOT,
    SUITE_DIR,
    suite_hash,
    validate_suite,
)
from harness.efc_menu_composition_v2 import COLD_FIXTURE_REVIEWER_SEAT
from harness.efc_provenance_record_store_v2 import build_record_store_from_fixtures

REVIEW_ENTRY_RELPATH = (
    ".substrate/threads/epistemic-frame-check-v2/"
    "20260717T120953980Z__cursor%2Fglm-5.2.md"
)
REVIEW_ENTRY_SHA256 = (
    "21b09cbcc6351ea284e7a93751c97b424f1cf29636327d1e9a1d6ca8efa9635e"
)
REVIEWED_AT = "2026-07-17T12:09:53.98Z"


def verify_review_entry() -> None:
    entry_path = REPO_ROOT / REVIEW_ENTRY_RELPATH
    digest = hashlib.sha256(entry_path.read_bytes()).hexdigest()
    if digest != REVIEW_ENTRY_SHA256:
        raise SystemExit(
            f"review entry drift: {digest} != pinned {REVIEW_ENTRY_SHA256}"
        )


def attestation_row(fixture_id: str, stratum: str) -> dict[str, str]:
    attestation_id = hashlib.sha256(
        f"{REVIEW_ENTRY_SHA256}:{fixture_id}".encode("utf-8")
    ).hexdigest()
    return {
        "fixture_id": fixture_id,
        "stratum": stratum,
        "reviewer_seat": COLD_FIXTURE_REVIEWER_SEAT,
        "reviewed_at": REVIEWED_AT,
        "attestation_id": attestation_id,
    }


def main() -> None:
    verify_review_entry()
    manifest = json.loads(
        (SUITE_DIR / "suite_manifest.json").read_text(encoding="utf-8")
    )
    fixtures: list[dict[str, object]] = []
    for entry in manifest["fixtures"]:
        path = FIXTURES_DIR / f"{entry['fixture_id']}.json"
        fixture = json.loads(path.read_text(encoding="utf-8"))
        fixture["plausibility_attestation"] = attestation_row(
            fixture["fixture_id"], fixture["stratum"]
        )
        path.write_text(
            json.dumps(fixture, sort_keys=True, indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        fixtures.append(fixture)

    store = build_record_store_from_fixtures(fixtures)
    result = validate_suite(
        fixtures,
        record_store=store,
        require_plausibility_attestation=True,
    )
    if not result.ok:
        raise SystemExit(f"validate_suite refused: {result.refusals[:5]}")
    digest = suite_hash(fixtures, k_pairs=len(manifest["fixtures"]) // 3,
                        record_store=store)
    print(f"attested fixtures: {result.fixture_count}")
    print(f"fixture_suite_hash: {digest}")


if __name__ == "__main__":
    main()
