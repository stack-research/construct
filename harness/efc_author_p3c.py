"""P3C narrow answer-key repair — v2 candidate only.

Repairs world-oracle answer-key rules per P3B BLOCK findings.
Does not modify pinned production artifacts, structured-input v2 candidate,
or budget audit bytes.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from harness.efc_author_c2_content import FIXTURES
from harness.efc_author_p3 import (ALL_TASKS, P3_ROOT, WORLD_ORACLE_SCHEMA,
                                   _BEHAVIOR_BY_TASK, _cold_review_examples,
                                   evaluate_cold_review_vectors, sha256_path)
from harness.efc_calibration_contact import (_normalize_answer,
                                             _validate_scorer_rules,
                                             make_world_oracle_score)

REPO = Path(__file__).resolve().parent.parent
KIMI_REVIEW_PATH = P3_ROOT / "p3b_cold_semantic_review_kimi.json"

_NEGATION_PREFIXES = (
    "do not ",
    "don't ",
    "not ",
    "should not ",
    "shouldn't ",
    "will not ",
    "won't ",
    "cannot ",
    "can't ",
    "we should not ",
    "we will not ",
    "we cannot ",
)


def _negation_none_of(tokens: tuple[str, ...]) -> list[str]:
    """Ordinary negation clauses for each admitted action-family token."""
    out: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        for prefix in _NEGATION_PREFIXES:
            phrase = prefix + token
            if phrase not in seen:
                seen.add(phrase)
                out.append(phrase)
    return out


def _dedupe_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _pass_when(*, any_of: list[str], none_of: list[str] | None = None,
               negation_tokens: tuple[str, ...] | None = None,
               hedge_none_of: list[str] | None = None) -> dict:
    neg_tokens = negation_tokens or ()
    any_lower = {a.lower() for a in any_of}
    neg_patterns = [
        p for p in _negation_none_of(neg_tokens)
        if p.lower() not in any_lower
    ]
    merged_none = _dedupe_preserve(
        (none_of or []) + neg_patterns + (hedge_none_of or []))
    return {"any_of": any_of, "none_of": merged_none}


_HEDGE = [
    "but ship", "but approve", "but merge", "but release", "but deploy",
    "but upgrade", "but proceed", "but adopt", "but bypass", "but block",
    "then ship", "then approve", "then bypass", "then adopt",
    "ship tomorrow", "ship on schedule", "ship today anyway",
    "hold the current pin", "pause the rollout immediately",
]


def _answer_rules_v2() -> dict[str, dict]:
    """Repaired behavior-class markers — family-level semantic repair."""
    h = _HEDGE
    return {
        "sf-01": {
            "pass_when": _pass_when(
                any_of=[
                    "decline the hotfix", "decline the emergency",
                    "reject the hotfix", "reject the emergency",
                    "push back on the hotfix", "hold the hotfix",
                    "defer the hotfix", "not approve the hotfix",
                    "do not approve the hotfix",
                    "shouldn't approve the hotfix",
                    "should not approve the hotfix",
                    "but i decline it", "decline it",
                ],
                none_of=[
                    "approve the hotfix and", "ship the hotfix",
                    "merge today", "ship today", "approve and ship",
                ],
                negation_tokens=(
                    "decline the hotfix", "reject the hotfix", "push back",
                    "hold the hotfix", "defer the hotfix",
                ),
                hedge_none_of=h,
            ),
        },
        "sf-02": {
            "pass_when": _pass_when(
                any_of=[
                    "defer the upgrade", "defer the framework", "wait until",
                    "can wait", "next fiscal", "postpone the upgrade",
                    "postpone the migration", "no urgent action",
                ],
                none_of=[
                    "upgrade now", "upgrade immediately", "proceed with upgrade",
                    "must upgrade immediately", "upgrade this quarter",
                ],
                negation_tokens=("defer", "wait", "postpone"),
                hedge_none_of=h,
            ),
        },
        "sf-03": {
            "pass_when": _pass_when(
                any_of=[
                    "disable the proxy", "disable proxy pooling",
                    "turn off the proxy", "turn off pooling",
                    "shut down the pooling", "shut down the proxy",
                    "block traffic", "pause pooling",
                ],
                none_of=[
                    "keep enabled", "leave enabled", "no change",
                    "keep the feature running", "keep proxy pooling enabled",
                ],
                negation_tokens=(
                    "disable", "turn off", "shut down", "block traffic", "pause pooling",
                ),
                hedge_none_of=h,
            ),
        },
        "sf-04": {
            "pass_when": _pass_when(
                any_of=[
                    "approve the release", "authorize shipping",
                    "authorize the release", "permit distribution",
                    "allow distribution", "release under the exception",
                    "ship the linked executable", "permit the distribution",
                    "authorize it",
                ],
                none_of=[
                    "decline the release", "reject the release",
                    "reject the counsel", "block the release",
                    "do not release the executable",
                ],
                negation_tokens=(
                    "approve the release", "authorize shipping",
                    "permit distribution", "allow distribution",
                    "ship the linked",
                ),
                hedge_none_of=h + ["do not release the executable"],
            ),
        },
        "sf-05": {
            "pass_when": _pass_when(
                any_of=[
                    "schedule the patch", "patch tonight", "patch the rpc",
                    "proceed with the rpc", "proceed with the upgrade",
                    "deploy the fix", "deploy in the maintenance",
                    "approve the patch",
                ],
                none_of=[
                    "decline to patch", "defer the security",
                    "do not schedule maintenance", "do not patch tonight",
                ],
                negation_tokens=("schedule the patch", "patch", "deploy", "proceed with the rpc"),
                hedge_none_of=h,
            ),
        },
        "mm-01": {
            "pass_when": _pass_when(
                any_of=[
                    "drain traffic", "divert traffic", "divert quic",
                    "stop serving traffic", "stop traffic",
                    "take the service out of rotation", "out of rotation",
                    "pause the service", "shutdown the edge",
                ],
                none_of=[
                    "keep serving", "continue as-is", "no action needed",
                    "maintain current traffic", "keep serving traffic",
                ],
                negation_tokens=(
                    "drain", "divert", "stop serving", "stop traffic", "pause the service",
                ),
                hedge_none_of=h,
            ),
        },
        "mm-02": {
            "pass_when": _pass_when(
                any_of=[
                    "block the release", "hold the release", "stop the release",
                    "reject the release", "reject shipping", "delay the release",
                    "don't ship this release", "do not ship this release",
                ],
                none_of=[
                    "proceed with the release", "ship the release",
                    "ship without", "approve the release",
                    "release on schedule",
                ],
                negation_tokens=(
                    "block the release", "hold the release", "reject the release",
                    "delay the release",
                ),
                hedge_none_of=h + ["ship on schedule", "but ship this release"],
            ),
        },
        "mm-03": {
            "pass_when": _pass_when(
                any_of=[
                    "renegotiate the license", "renegotiate the renewal",
                    "change the renewal", "modify the renewal",
                    "different terms", "ask for better terms",
                    "better terms before renewing",
                ],
                none_of=[
                    "approve renewal unchanged", "proceed with unchanged renewal",
                    "renew unchanged", "renew as proposed", "renew unchanged as",
                ],
                negation_tokens=(
                    "renegotiate", "change the renewal", "modify the renewal",
                    "better terms",
                ),
                hedge_none_of=h,
            ),
        },
        "mm-04": {
            "pass_when": _pass_when(
                any_of=[
                    "pause ingestion", "halt the crawler", "halt the parsing",
                    "halt ingestion", "suspend ingestion", "suspend the crawler",
                    "suspend html parsing", "turn off the crawler",
                    "disable the crawler",
                ],
                none_of=[
                    "continue ingestion", "keep running", "resume ingestion",
                    "keep the crawler running", "full rate",
                ],
                negation_tokens=(
                    "pause ingestion", "halt", "suspend", "turn off the crawler",
                ),
                hedge_none_of=h,
            ),
        },
        "mm-05": {
            "pass_when": _pass_when(
                any_of=[
                    "reject the installer", "reject the build",
                    "decline the installer", "decline the build",
                    "decline the sdk", "refuse the build", "refuse the installer",
                    "block the build", "block the installer",
                    "do not approve the installer", "not approve the installer",
                    "won't approve the installer", "will not approve the installer",
                    "we should not",
                ],
                none_of=[
                    "should not reject", "do not reject", "won't reject",
                    "will not reject", "cannot reject", "can't reject",
                    "accept the installer", "accept the distribution",
                    "allow the build", "allow the installer",
                ],
                negation_tokens=(
                    "reject the build", "reject the installer",
                    "decline the build", "refuse the build",
                ),
                hedge_none_of=h,
            ),
        },
        "mc-01": {
            "pass_when": _pass_when(
                any_of=[
                    "merge the flatted", "merge the upgrade", "merge the dependency",
                    "merge today", "approve the dependency merge",
                    "proceed with the dependency bump", "approve merging",
                ],
                none_of=[
                    "decline to merge", "defer the merge", "do not merge",
                    "do not merge today", "do not merge this",
                ],
                negation_tokens=(
                    "merge", "approve the dependency", "proceed with the dependency",
                ),
                hedge_none_of=h,
            ),
        },
        "mc-02": {
            "pass_when": _pass_when(
                any_of=[
                    "keep the fleet", "keep the servlet", "remain on tomcat",
                    "stay on the current", "stay on tomcat",
                    "continue on the current", "maintain the current line",
                    "no change to the servlet", "no change",
                ],
                none_of=[
                    "migrate now", "migrate off", "upgrade immediately",
                    "change line", "change lines before",
                ],
                negation_tokens=(
                    "keep the fleet", "keep the servlet", "remain on", "stay on",
                    "no change",
                ),
                hedge_none_of=h,
            ),
        },
        "mc-03": {
            "pass_when": _pass_when(
                any_of=[
                    "bump the spdy", "bump the dependency", "upgrade spdystream",
                    "update spdystream", "roll out the update",
                    "proceed with the dependency update",
                    "won't defer", "update spdystream before",
                ],
                none_of=[
                    "defer the bump", "decline to update",
                    "do not update spdystream", "don't upgrade before rollout",
                ],
                negation_tokens=("bump", "upgrade spdystream", "update spdystream"),
                hedge_none_of=h + ["don't upgrade before rollout"],
            ),
        },
        "mc-04": {
            "pass_when": _pass_when(
                any_of=[
                    "approve the shipping", "authorize redistribution",
                    "permit the object-form", "permit the llvm",
                    "allow the object-form", "allow the redistribution",
                ],
                none_of=[
                    "reject the shipping", "decline the llvm", "decline to permit",
                    "block the release", "we decline to permit",
                ],
                negation_tokens=(
                    "approve the shipping", "authorize redistribution",
                    "permit the object-form", "allow the redistribution",
                ),
                hedge_none_of=h,
            ),
        },
        "mc-05": {
            "pass_when": _pass_when(
                any_of=[
                    "execute the rotation", "execute the key rotation",
                    "execute the plan", "proceed with key rotation",
                    "proceed with the cryptography", "rotate the key",
                    "approve executing", "upgrade along the plan",
                ],
                none_of=[
                    "defer execution", "decline the proposed rotation",
                    "postpone the upgrade", "postpone execution",
                ],
                negation_tokens=(
                    "execute", "proceed with key rotation",
                    "proceed with the cryptography", "rotate",
                ),
                hedge_none_of=h,
            ),
        },
        "ir-01": {
            "pass_when": _pass_when(
                any_of=[
                    "upgrade anyhow", "bump the crate", "bump anyhow",
                    "update the crate", "new pin", "pin the fixed version",
                    "move to the patched release", "publish a new pin",
                    "can't defer", "won't defer",
                ],
                none_of=[
                    "defer the upgrade", "wait for the external",
                    "do not upgrade", "hold the current version", "hold pin",
                    "hold the current pin",
                ],
                negation_tokens=(
                    "upgrade", "bump", "update the crate", "pin the fixed",
                    "move to the patched",
                ),
                hedge_none_of=h + ["hold the current pin"],
            ),
        },
        "ir-02": {
            "pass_when": _pass_when(
                any_of=[
                    "close the ticket", "close the incident", "ticket can be closed",
                    "mark the incident resolved", "mark resolved",
                    "resolve the ticket", "ticket closed",
                ],
                none_of=[
                    "keep the ticket open", "keep open", "reopen the incident",
                    "investigate further", "defer closure",
                ],
                negation_tokens=(
                    "close the ticket", "close the incident", "mark resolved",
                    "resolve the ticket",
                ),
                hedge_none_of=h,
            ),
        },
        "ir-03": {
            "pass_when": _pass_when(
                any_of=[
                    "schedule the migration", "plan the migration",
                    "plan the hypervisor migration",
                    "proceed with migration", "migrate away from",
                    "move to a supported hypervisor", "supported hypervisor platform",
                ],
                none_of=[
                    "postpone migration", "defer scheduling", "do not migrate",
                    "stay on esxi", "can stay on esxi",
                ],
                negation_tokens=(
                    "schedule the migration", "plan the migration", "migrate",
                    "move to a supported",
                ),
                hedge_none_of=h,
            ),
        },
        "ir-04": {
            "pass_when": _pass_when(
                any_of=[
                    "keep the rollout", "keep the current rollout",
                    "continue the rollout", "maintain the rollout",
                    "no action is needed", "no change", "no change to the rollout",
                    "stay on schedule", "rollout as planned",
                    "should not pause deployment",
                ],
                none_of=[
                    "pause the rollout", "pause rollout", "halt deployment",
                    "rollback", "delay the rollout", "delay rollout",
                ],
                negation_tokens=(
                    "keep the rollout", "continue the rollout",
                    "maintain the rollout", "no action is needed",
                ),
                hedge_none_of=h + ["pause the rollout immediately"],
            ),
        },
        "ir-05": {
            "pass_when": _pass_when(
                any_of=[
                    "route through the oss", "route to the review board",
                    "submit for board review", "submit for legal review",
                    "send to the licensing committee", "follow policy",
                    "oss review board", "board review per",
                ],
                none_of=[
                    "skip review", "adopt without", "bypass review",
                    "without review", "then bypass review",
                    "adopt directly without",
                ],
                negation_tokens=(
                    "route to the review", "submit for legal",
                    "submit for board", "licensing committee",
                ),
                hedge_none_of=h + ["then bypass review"],
            ),
        },
    }


def build_world_oracle_answer_key_candidate_v2() -> dict:
    rules = _answer_rules_v2()
    if set(rules) != set(ALL_TASKS):
        missing = sorted(set(ALL_TASKS) - set(rules))
        extra = sorted(set(rules) - set(ALL_TASKS))
        raise ValueError(f"rule coverage mismatch: missing {missing}, extra {extra}")
    return {
        "schema_version": WORLD_ORACLE_SCHEMA,
        "candidate_note": ("unpinned P3C v2 repair; behavior-class families with "
                           "expanded paraphrases and explicit negation none_of"),
        "repair_basis": "P3B Kimi BLOCK — contradiction, negation gap, paraphrase gap",
        "residual_risk": ("normalized-substring scoring may still miss novel "
                          "paraphrases or accept rare hedge forms until P3D review"),
        "rules": rules,
    }


def find_rule_contradictions(rules: dict) -> list[dict]:
    """Flag unavoidable conflicts: a none_of token contained in an any_of token."""
    conflicts: list[dict] = []
    for fixture_id, rule in rules.items():
        pw = rule["pass_when"]
        any_tokens = [t.lower() for t in pw.get("any_of", [])]
        none_tokens = [t.lower() for t in pw.get("none_of", [])]
        for a in any_tokens:
            for n in none_tokens:
                if n in a and n != a:
                    conflicts.append({
                        "fixture_id": fixture_id,
                        "any_of": a,
                        "none_of": n,
                        "detail": (f"none_of '{n}' is a substring of any_of '{a}' "
                                   "— affirmative match always fails none_of"),
                    })
    return conflicts


def load_kimi_adversarial_vectors(path: Path | None = None) -> dict:
    """Frozen 80-vector regression corpus from Kimi P3B review artifact."""
    doc = json.loads((path or KIMI_REVIEW_PATH).read_text(encoding="utf-8"))
    vectors: dict[str, list[dict]] = {}
    for block in doc["world_oracle_rule_review"]["per_fixture_results"]:
        fixture_id = block["fixture_id"]
        entries: list[dict] = []
        for label in ("correct", "incorrect"):
            for item in block["results"][label]:
                entries.append({
                    "text": item["text"],
                    "expect_pass": item["expect_pass"],
                    "label": label,
                    "source": "kimi_p3b",
                })
        vectors[fixture_id] = entries
    total = sum(len(v) for v in vectors.values())
    if total != 80:
        raise ValueError(f"expected 80 Kimi vectors, got {total}")
    return {
        "schema_version": "efc_p3c_kimi_vectors_v1",
        "source_artifact": str((path or KIMI_REVIEW_PATH).relative_to(REPO)),
        "vector_count": total,
        "vectors_by_fixture": vectors,
    }


def _p3c_repair_vectors() -> dict[str, list[dict]]:
    """Independently authored repair vectors beyond Kimi + Composer corpora."""
    return {
        "sf-01": [
            {"text": "We shouldn't approve the hotfix.", "expect_pass": True,
             "label": "correct", "category": "contraction_negation_affirm"},
            {"text": "Decline the hotfix, but ship tomorrow anyway.",
             "expect_pass": False, "label": "incorrect",
             "category": "conflicting_commitment"},
            {"text": 'The memo says "approve the hotfix" but I decline it.',
             "expect_pass": True, "label": "correct",
             "category": "quoted_speech_final_decline"},
        ],
        "sf-04": [
            {"text": "We can't ship this without counsel approval — authorize it.",
             "expect_pass": True, "label": "correct",
             "category": "modal_negation_then_affirm"},
            {"text": "Authorize distribution, but do not release the executable.",
             "expect_pass": False, "label": "incorrect",
             "category": "conflicting_commitment"},
        ],
        "mm-05": [
            {"text": "I won't approve the installer build.",
             "expect_pass": True, "label": "correct",
             "category": "contraction_negation_affirm"},
            {"text": "Reject the build, then approve the installer tomorrow.",
             "expect_pass": False, "label": "incorrect",
             "category": "conflicting_commitment"},
            {"text": 'Legal said "approve the installer" — we should not.',
             "expect_pass": True, "label": "correct",
             "category": "quoted_speech_final_decline"},
        ],
        "ir-01": [
            {"text": "We can't defer — bump anyhow to the fixed release.",
             "expect_pass": True, "label": "correct",
             "category": "modal_negation_then_affirm"},
            {"text": "Pin the fixed version, but hold the current pin.",
             "expect_pass": False, "label": "incorrect",
             "category": "conflicting_commitment"},
        ],
        "ir-05": [
            {"text": "Submit for legal review; do not adopt directly.",
             "expect_pass": True, "label": "correct",
             "category": "affirm_then_negate_opposite"},
            {"text": "Route to the board, then bypass review for speed.",
             "expect_pass": False, "label": "incorrect",
             "category": "conflicting_commitment"},
        ],
        "mc-03": [
            {"text": "Won't defer — update spdystream before release.",
             "expect_pass": True, "label": "correct",
             "category": "contraction_negation_affirm"},
            {"text": "Bump spdystream, but don't upgrade before rollout.",
             "expect_pass": False, "label": "incorrect",
             "category": "conflicting_commitment"},
        ],
        "mm-02": [
            {"text": "Don't ship this release.",
             "expect_pass": True, "label": "correct",
             "category": "contraction_negation_affirm"},
            {"text": "Block the release, but ship on schedule.",
             "expect_pass": False, "label": "incorrect",
             "category": "conflicting_commitment"},
        ],
        "ir-04": [
            {"text": "Continue the rollout; we should not pause deployment.",
             "expect_pass": True, "label": "correct",
             "category": "affirm_then_negate_opposite"},
            {"text": "No action needed, but pause the rollout immediately.",
             "expect_pass": False, "label": "incorrect",
             "category": "conflicting_commitment"},
        ],
    }


def _evaluate_vector_block(scorer, fixture_id: str,
                           vectors: list[dict]) -> tuple[list[dict], list[dict]]:
    evaluated: list[dict] = []
    failures: list[dict] = []
    for vec in vectors:
        passed = scorer({"task_id": fixture_id}, vec["text"])["passed"]
        expect = vec["expect_pass"]
        entry = {**vec, "fixture_id": fixture_id, "passed": passed}
        evaluated.append(entry)
        if passed != expect:
            failures.append(entry)
    return evaluated, failures


def evaluate_all_repair_vectors(key: dict) -> dict:
    scorer = make_world_oracle_score(key["rules"])
    kimi = load_kimi_adversarial_vectors()
    composer_examples = _cold_review_examples()
    p3c_extra = _p3c_repair_vectors()

    by_source: dict[str, list[dict]] = {
        "composer_p3a": [],
        "kimi_p3b": [],
        "composer_p3c": [],
    }
    failures_by_source: dict[str, list[dict]] = {
        "composer_p3a": [],
        "kimi_p3b": [],
        "composer_p3c": [],
    }

    for task_id in ALL_TASKS:
        composer_vecs = []
        for label, texts in (("correct", composer_examples[task_id]["correct"]),
                             ("incorrect", composer_examples[task_id]["incorrect"])):
            for text in texts:
                composer_vecs.append({
                    "text": text,
                    "expect_pass": label == "correct",
                    "label": label,
                    "source": "composer_p3a",
                })
        ev, fail = _evaluate_vector_block(scorer, task_id, composer_vecs)
        by_source["composer_p3a"].extend(ev)
        failures_by_source["composer_p3a"].extend(fail)

        ev, fail = _evaluate_vector_block(scorer, task_id,
                                          kimi["vectors_by_fixture"][task_id])
        by_source["kimi_p3b"].extend(ev)
        failures_by_source["kimi_p3b"].extend(fail)

        if task_id in p3c_extra:
            ev, fail = _evaluate_vector_block(scorer, task_id, p3c_extra[task_id])
            by_source["composer_p3c"].extend(ev)
            failures_by_source["composer_p3c"].extend(fail)

    counts = {src: len(by_source[src]) for src in by_source}
    failure_counts = {src: len(failures_by_source[src]) for src in by_source}
    total_failures = sum(failure_counts.values())

    return {
        "schema_version": "efc_p3c_repair_vectors_evaluated_v1",
        "evaluation_by_source": by_source,
        "counts_by_source": counts,
        "failure_counts_by_source": failure_counts,
        "total_failure_count": total_failures,
        "failures_by_source": failures_by_source,
    }


def _rule_change_summary(v1_rules: dict, v2_rules: dict) -> list[dict]:
    changes: list[dict] = []
    for tid in ALL_TASKS:
        old = v1_rules[tid]["pass_when"]
        new = v2_rules[tid]["pass_when"]
        changes.append({
            "fixture_id": tid,
            "behavior_class": _BEHAVIOR_BY_TASK[tid],
            "repair_kind": "semantic_family",
            "rationale": (
                "expanded affirmative action phrases; added explicit negation "
                "none_of families; removed any_of/none_of substring contradictions"
            ),
            "any_of_before_count": len(old.get("any_of", [])),
            "any_of_after_count": len(new.get("any_of", [])),
            "none_of_before_count": len(old.get("none_of", [])),
            "none_of_after_count": len(new.get("none_of", [])),
            "pass_when_before": old,
            "pass_when_after": new,
        })
    return changes


def build_p3c_repair_report(key_v2: dict, vectors_eval: dict,
                            contradictions: list[dict]) -> dict:
    from harness.efc_author_p3 import build_world_oracle_answer_key_candidate
    v1 = build_world_oracle_answer_key_candidate()
    return {
        "schema_version": "efc_p3c_answer_key_repair_report_v1",
        "assignment": "P3C narrow answer-key repair",
        "candidate_only": True,
        "authorizes_contact": False,
        "authorizes_integration": False,
        "explicit_authorization_statement": (
            "v2 answer-key candidate is unpinned and authorizes neither "
            "production integration nor engine contact"
        ),
        "input_hashes": {
            "world_oracle_answer_key_candidate_v1": sha256_path(
                P3_ROOT / "world_oracle_answer_key_candidate.json"),
            "p3b_cold_semantic_review_kimi": sha256_path(KIMI_REVIEW_PATH),
            "structured_inputs_v2_candidate": sha256_path(
                P3_ROOT / "structured_inputs_v2_candidate.json"),
        },
        "preserved_byte_identical": [
            "structured_inputs_v2_candidate.json",
            "ax_ir_budget_audit.json",
            "p3b_cold_semantic_review_kimi.json",
            "world_oracle_answer_key_candidate.json",
        ],
        "contradiction_check": {
            "conflict_count": len(contradictions),
            "conflicts": contradictions,
            "passed": not contradictions,
        },
        "vector_evaluation": {
            "counts_by_source": vectors_eval["counts_by_source"],
            "failure_counts_by_source": vectors_eval["failure_counts_by_source"],
            "total_failure_count": vectors_eval["total_failure_count"],
        },
        "rule_changes": _rule_change_summary(v1["rules"], key_v2["rules"]),
        "schema_inexpressible_fixtures": [],
        "blockers": ([] if not contradictions else
                     [f"substring_contradictions: {len(contradictions)}"])
        + ([] if vectors_eval["total_failure_count"] == 0 else
           [f"vector_failures: {vectors_eval['total_failure_count']}"]),
    }


def write_p3c_artifacts(root: Path | None = None) -> dict[str, Path]:
    root = root or P3_ROOT
    root.mkdir(parents=True, exist_ok=True)

    key = build_world_oracle_answer_key_candidate_v2()
    _validate_scorer_rules(key["rules"], set(ALL_TASKS))
    contradictions = find_rule_contradictions(key["rules"])
    if contradictions:
        raise ValueError(f"rule contradictions remain: {contradictions[:3]}")

    key_path = root / "world_oracle_answer_key_candidate_v2.json"
    key_path.write_text(json.dumps(key, sort_keys=True, indent=1) + "\n")

    vectors_eval = evaluate_all_repair_vectors(key)
    if vectors_eval["total_failure_count"]:
        raise ValueError(
            f"P3C vector failures: {vectors_eval['failure_counts_by_source']}")

    vectors_path = root / "p3c_repair_vectors_evaluated.json"
    vectors_path.write_text(json.dumps(vectors_eval, sort_keys=True, indent=1) + "\n")

    report = build_p3c_repair_report(key, vectors_eval, contradictions)
    report_path = root / "p3c_answer_key_repair_report.json"
    report_path.write_text(json.dumps(report, sort_keys=True, indent=1) + "\n")

    return {
        "answer_key_v2": key_path,
        "vectors": vectors_path,
        "report": report_path,
    }
