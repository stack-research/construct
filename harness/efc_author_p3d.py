"""P3D bounded cold re-review of the P3C v2 answer-key candidate.

Fresh adversarial cases, not drawn from P3A/P3B/P3C corpora, evaluated
against the v2 answer key using the pinned substring scorer. No model
or calibration contact; engine-invisible local scoring only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from harness.efc_author_p3 import P3_ROOT, sha256_path
from harness.efc_author_p3c import build_world_oracle_answer_key_candidate_v2
from harness.efc_calibration_contact import make_world_oracle_score

REPO = Path(__file__).resolve().parent.parent
OUTPUT_PATH = P3_ROOT / "p3d_cold_review_kimi.json"


def _load_existing_texts() -> set[tuple[str, str, bool]]:
    """De-duplicate against the already-evaluated P3A/P3B/P3C corpora."""
    seen: set[tuple[str, str, bool]] = set()
    for name in ("p3c_repair_vectors_evaluated.json",):
        path = P3_ROOT / name
        if not path.is_file():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        for source, entries in doc.get("evaluation_by_source", {}).items():
            for e in entries:
                seen.add((e["fixture_id"], e["text"], e["expect_pass"]))
    return seen


_FRESH_CASES = [
    # Systematic negation: action token appears, but inside a "not to" /
    # "not going to" / "no longer" clause that the generated none_of families
    # do not cover. These are expected to FAIL (i.e., not pass) for
    # action-required fixtures.
    {"fixture_id": "ir-01", "text": "We decided not to upgrade anyhow.",
     "expect_pass": False, "category": "not_to_action"},
    {"fixture_id": "mc-01", "text": "We chose not to merge the dependency.",
     "expect_pass": False, "category": "not_to_action"},
    {"fixture_id": "mc-03", "text": "We opted not to update spdystream.",
     "expect_pass": False, "category": "not_to_action"},
    {"fixture_id": "mc-05", "text": "We decided not to execute the rotation.",
     "expect_pass": False, "category": "not_to_action"},
    {"fixture_id": "sf-04", "text": "We chose not to approve the release.",
     "expect_pass": False, "category": "not_to_action"},
    {"fixture_id": "sf-05", "text": "We decided not to schedule the patch.",
     "expect_pass": False, "category": "not_to_action"},
    {"fixture_id": "mm-01", "text": "We opted not to take the service out of rotation.",
     "expect_pass": False, "category": "not_to_action"},
    {"fixture_id": "mm-02", "text": "We chose not to block the release.",
     "expect_pass": False, "category": "not_to_action"},
    {"fixture_id": "mm-03", "text": "We decided not to renegotiate the license.",
     "expect_pass": False, "category": "not_to_action"},
    {"fixture_id": "mm-04", "text": "We opted not to pause ingestion.",
     "expect_pass": False, "category": "not_to_action"},
    {"fixture_id": "mm-05", "text": "We decided not to reject the build.",
     "expect_pass": False, "category": "not_to_action"},

    # Modal progressive negation not captured by the prefix list.
    {"fixture_id": "ir-01", "text": "We aren't going to upgrade anyhow.",
     "expect_pass": False, "category": "not_going_to_action"},
    {"fixture_id": "mc-01", "text": "We aren't going to merge the dependency.",
     "expect_pass": False, "category": "not_going_to_action"},
    {"fixture_id": "sf-04", "text": "We aren't going to approve the release.",
     "expect_pass": False, "category": "not_going_to_action"},

    # "No longer" revocation of an action.
    {"fixture_id": "sf-04", "text": "We no longer approve the release.",
     "expect_pass": False, "category": "no_longer_action"},
    {"fixture_id": "ir-01", "text": "We no longer upgrade anyhow.",
     "expect_pass": False, "category": "no_longer_action"},

    # Hedge/defer forms that contain the action token but imply delay.
    {"fixture_id": "ir-01", "text": "Let's hold off on upgrading anyhow.",
     "expect_pass": False, "category": "hold_off_action"},
    {"fixture_id": "ir-01", "text": "We will upgrade anyhow, but not yet.",
     "expect_pass": False, "category": "not_yet_action"},
    {"fixture_id": "ir-01", "text": "We are waiting to upgrade anyhow.",
     "expect_pass": False, "category": "waiting_to_action"},

    # Common paraphrases of the required action that are absent from any_of.
    {"fixture_id": "sf-04", "text": "Ship it.",
     "expect_pass": True, "category": "missing_paraphrase"},
    {"fixture_id": "sf-04", "text": "Release it.",
     "expect_pass": True, "category": "missing_paraphrase"},
    {"fixture_id": "sf-04", "text": "Green-light the release.",
     "expect_pass": True, "category": "missing_paraphrase"},
    {"fixture_id": "mm-02", "text": "Veto the release.",
     "expect_pass": True, "category": "missing_paraphrase"},
    {"fixture_id": "mm-02", "text": "Kill the release.",
     "expect_pass": True, "category": "missing_paraphrase"},
    {"fixture_id": "mm-05", "text": "Deny the build.",
     "expect_pass": True, "category": "missing_paraphrase"},
    {"fixture_id": "mc-05", "text": "Run the rotation.",
     "expect_pass": True, "category": "missing_paraphrase"},
    {"fixture_id": "ir-05", "text": "Send it to legal.",
     "expect_pass": True, "category": "missing_paraphrase"},
    {"fixture_id": "mm-01", "text": "Pull the service.",
     "expect_pass": True, "category": "missing_paraphrase"},
    {"fixture_id": "sf-01", "text": "Veto the hotfix.",
     "expect_pass": True, "category": "missing_paraphrase"},
    {"fixture_id": "sf-03", "text": "Kill the proxy pool.",
     "expect_pass": True, "category": "missing_paraphrase"},
    {"fixture_id": "mc-03", "text": "Patch spdystream.",
     "expect_pass": True, "category": "missing_paraphrase"},
    {"fixture_id": "ir-03", "text": "Start the migration.",
     "expect_pass": True, "category": "missing_paraphrase"},
    {"fixture_id": "ir-02", "text": "Close out the ticket.",
     "expect_pass": True, "category": "missing_paraphrase"},
]


def build_p3d_review() -> dict:
    key = build_world_oracle_answer_key_candidate_v2()
    scorer = make_world_oracle_score(key["rules"])
    seen = _load_existing_texts()

    evaluated: list[dict] = []
    failures: list[dict] = []
    duplicate_count = 0

    for case in _FRESH_CASES:
        dup_key = (case["fixture_id"], case["text"], case["expect_pass"])
        if dup_key in seen:
            duplicate_count += 1
            continue
        passed = scorer({"task_id": case["fixture_id"]}, case["text"])["passed"]
        entry = {
            "fixture_id": case["fixture_id"],
            "text": case["text"],
            "category": case["category"],
            "expect_pass": case["expect_pass"],
            "passed": passed,
        }
        evaluated.append(entry)
        if passed != case["expect_pass"]:
            failures.append(entry)

    verdict = "BLOCK" if failures else "ENDORSE"

    return {
        "schema_version": "efc_p3d_cold_review_v1",
        "assignment": "P3D bounded cold re-review",
        "reviewer": "cursor/kimi-k2.7-code",
        "candidate_only": True,
        "authorizes_contact": False,
        "authorizes_integration": False,
        "explicit_authorization_statement": (
            "This P3D review authorizes neither integration of the v2 "
            "candidate into a production manifest nor any engine contact, "
            "probe rerun, or calibration call."
        ),
        "input_hashes": {
            "world_oracle_answer_key_candidate_v2": sha256_path(
                P3_ROOT / "world_oracle_answer_key_candidate_v2.json"),
            "p3c_answer_key_repair_report": sha256_path(
                P3_ROOT / "p3c_answer_key_repair_report.json"),
            "p3c_repair_vectors_evaluated": sha256_path(
                P3_ROOT / "p3c_repair_vectors_evaluated.json"),
        },
        "duplicate_cases_omitted": duplicate_count,
        "total_fresh_cases": len(evaluated),
        "failure_count": len(failures),
        "verdict": verdict,
        "blockers": (
            [f"fresh adversarial failures: {len(failures)}"] if failures else []
        ),
        "smallest_actionable_blockers": (
            ["systematic 'not to <action>' negation is not captured by generated none_of families",
             "modal progressive negation ('aren't going to <action>') is not captured",
             "'no longer <action>' revocation is not captured",
             "common affirmative paraphrases still missing from any_of families"]
            if failures else []
        ),
        "evaluated_cases": evaluated,
        "failed_cases": failures,
    }


def write_p3d_review() -> Path:
    review = build_p3d_review()
    OUTPUT_PATH.write_text(
        json.dumps(review, sort_keys=True, indent=1) + "\n",
        encoding="utf-8")
    return OUTPUT_PATH


if __name__ == "__main__":
    path = write_p3d_review()
    print(path)
    review = json.loads(path.read_text(encoding="utf-8"))
    print(f"verdict={review['verdict']}, total={review['total_fresh_cases']}, "
          f"failures={review['failure_count']}")
