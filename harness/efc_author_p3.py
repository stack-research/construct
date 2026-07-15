"""P3A candidate authoring — structured-input v2 + world-oracle answer key.

Candidate-only artifacts under corpus/efc_calibration/authoring_p3/.
Does not modify pinned production bindings, manifests, or contact surfaces.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from harness.efc_author_c2_content import FIXTURES
from harness.efc_author_c4 import (COMPLETION_REQUEST_CEILING,
                                     CONTROLLER_SOURCE_READ_BOUND,
                                     fixture_render_view)
from harness.efc_calibration_contact import make_world_oracle_score
from harness import efc_contracts as c
from harness.efc_check import ProvenanceRecord, ProvenanceStore
from harness.efc_compare_inputs import (STRUCTURED_INPUTS_SCHEMA_VERSION,
                                        decision_scope_sha256,
                                        population_binding_sha256)
from harness.efc_compare_production import interpret_structured_input
from harness.efc_renderer import (build_foreground, canonical_tokens,
                                  render_prompt)

REPO = Path(__file__).resolve().parent.parent
P3_ROOT = REPO / "corpus" / "efc_calibration" / "authoring_p3"
V1_PATH = REPO / "corpus" / "efc_calibration" / "comparison" / \
    "structured_inputs_v1.json"
BUDGET_LEDGER_PATH = REPO / "corpus" / "efc_calibration" / "authoring_c4" / \
    "budget_derivation_ledger.json"
ORACLE_ROOT = REPO / "corpus/efc_calibration/oracle"
EPISODE_ROOT = REPO / "episodes/efc_calibration"

IR_TASKS = ("ir-01", "ir-02", "ir-03", "ir-04", "ir-05")
ALL_TASKS = tuple(sorted(FIXTURES))
WORLD_ORACLE_SCHEMA = "efc_world_oracle_answer_key_v1"

FORBIDDEN_ROW_KEYS = frozenset({
    "task_id", "fixture_id", "expected_answer", "required_behavior",
    "behavior_class", "scope_matches", "lane", "stratum",
})

_BEHAVIOR_BY_TASK = {
    tid: FIXTURES[tid]["behavior"] for tid in ALL_TASKS
}


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_canon(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _load_oracle(task_id: str) -> dict:
    return json.loads((ORACLE_ROOT / f"{task_id}.json").read_text())


def _load_fixture(task_id: str) -> dict:
    spec = FIXTURES[task_id]
    role = spec["role"]
    sub = "s_family" if role == "s_family" else "analog"
    return json.loads((EPISODE_ROOT / sub / f"{task_id}.json").read_text())


def _parse_go_scope_ir(scope: str) -> tuple[str, str, str]:
    m = re.search(
        r"Go module (\S+) at version ([\d.]+), using the (\S+) module",
        scope)
    if not m:
        raise ValueError(f"ir go scope parse failed: {scope!r}")
    return m.group(1), m.group(2), m.group(3)


def _extract_mpl_section_6_clause(raw_path: Path) -> str:
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    text = raw["licenseText"]
    start = text.index("6. Disclaimer of Warranty")
    end = text.index("7. Limitation of Liability", start)
    return text[start:end].strip()


def derive_ir_structured_input(task_id: str) -> dict:
    """Derive one irrelevant-stratum structured-input row from fixture + oracle."""
    if task_id not in IR_TASKS:
        raise ValueError(f"not an ir task: {task_id!r}")
    spec = FIXTURES[task_id]
    oracle = _load_oracle(task_id)
    ev = oracle["extracted_values"]
    scope = spec["decision_scope"]
    record = spec["record"]
    base = {
        "source_reference": oracle["source_reference"],
        "raw_sha256": oracle["raw_sha256"],
        "decision_scope_sha256": decision_scope_sha256(scope),
    }

    if record.startswith("A"):
        pkg, version = re.search(
            r"crate (\S+) at version ([\d.]+)", scope).groups()
        if pkg != ev["pkg"]:
            raise ValueError(f"{task_id}: crate mismatch")
        return {
            **base,
            "operation": "cargo_affected_membership",
            "operands": {
                "ecosystem": "crates.io",
                "package": pkg,
                "version": version,
                "upper_exclusive": ev["fixed"],
            },
        }

    if record.startswith("B"):
        pkg, version = re.search(
            r"pip package (\S+) at version ([\d.]+)", scope).groups()
        return {
            **base,
            "operation": "ghsa_semver_membership",
            "operands": {
                "ecosystem": ev.get("eco", "pip"),
                "package": pkg,
                "version": version,
                "range_strings": [ev["range"]],
            },
        }

    if record.startswith("C"):
        product, cycle, check_date = re.search(
            r"(\S+) release line ([\d.]+) remaining in (?:security )?support "
            r"on (\d{4}-\d{2}-\d{2})", scope).groups()
        return {
            **base,
            "operation": "eol_support_on_date",
            "operands": {
                "product": product,
                "cycle": cycle,
                "eol_date": ev["eol"],
                "check_date": check_date,
            },
        }

    if record.startswith("D"):
        mod, version, symbol = _parse_go_scope_ir(scope)
        if mod != ev["mod"]:
            raise ValueError(f"{task_id}: module mismatch")
        return {
            **base,
            "operation": "go_symbol_version_membership",
            "operands": {
                "module": mod,
                "version": version,
                "upper_exclusive": ev["fixed"],
                "symbol": symbol,
                "listed_symbol": symbol,
            },
        }

    if record.startswith("E"):
        raw_path = REPO / oracle["capture_path"]
        clause = _extract_mpl_section_6_clause(raw_path)
        return {
            **base,
            "operation": "license_permission_granted",
            "operands": {
                "license_id": ev["id"],
                "required_phrases": [
                    "Larger Work",
                    "independent modules",
                    "terms of your choice",
                ],
                "clause_text": clause,
            },
        }

    raise ValueError(f"unsupported ir derivation: {task_id}")


def build_structured_inputs_v2_candidate() -> dict:
    v1 = json.loads(V1_PATH.read_text(encoding="utf-8"))
    old_rows = v1["rows"]
    if len(old_rows) != 15:
        raise ValueError("v1 row count is not 15")
    ir_rows = [derive_ir_structured_input(tid) for tid in IR_TASKS]
    rows = old_rows + ir_rows
    schema_version = STRUCTURED_INPUTS_SCHEMA_VERSION
    row_count = len(rows)
    return {
        "schema_version": schema_version,
        "row_count": row_count,
        "population_binding_sha256": population_binding_sha256(
            rows, schema_version, row_count),
        "rows": rows,
        "candidate_note": ("unpinned P3A candidate; v1 rows byte-identical; "
                           "five ir rows added for §8.2/§8.5 repair"),
    }


def _answer_rules() -> dict[str, dict]:
    """Behavior-class markers for the 20 calibration fixtures."""
    return {
        "sf-01": {
            "pass_when": {
                "any_of": ["decline", "reject", "do not approve",
                           "not approve", "hold", "defer"],
                "none_of": ["approve the hotfix", "ship the hotfix",
                            "merge today"],
            },
        },
        "sf-02": {
            "pass_when": {
                "any_of": ["defer", "wait", "postpone", "can wait",
                           "next fiscal"],
                "none_of": ["upgrade now", "proceed with upgrade",
                            "must upgrade immediately"],
            },
        },
        "sf-03": {
            "pass_when": {
                "any_of": ["disable", "turn off", "shut down", "block",
                           "pause pooling"],
                "none_of": ["keep enabled", "leave enabled", "no change"],
            },
        },
        "sf-04": {
            "pass_when": {
                "any_of": ["approve", "authorize", "permit", "release",
                           "ship"],
                "none_of": ["decline", "reject", "block", "do not approve"],
            },
        },
        "sf-05": {
            "pass_when": {
                "any_of": ["schedule", "patch", "proceed", "deploy",
                           "approve"],
                "none_of": ["decline", "defer", "do not patch",
                            "do not schedule"],
            },
        },
        "mm-01": {
            "pass_when": {
                "any_of": ["drain", "divert", "stop traffic", "pause",
                           "shutdown"],
                "none_of": ["keep serving", "continue as-is", "no action"],
            },
        },
        "mm-02": {
            "pass_when": {
                "any_of": ["block", "hold", "stop", "reject", "delay"],
                "none_of": ["proceed with release", "ship the release",
                            "approve release"],
            },
        },
        "mm-03": {
            "pass_when": {
                "any_of": ["renegotiate", "change the renewal",
                           "modify the renewal", "different terms"],
                "none_of": ["approve renewal unchanged",
                            "proceed with unchanged renewal",
                            "renew unchanged"],
            },
        },
        "mm-04": {
            "pass_when": {
                "any_of": ["pause", "stop", "halt", "suspend", "disable"],
                "none_of": ["continue ingestion", "keep running", "resume"],
            },
        },
        "mm-05": {
            "pass_when": {
                "any_of": ["reject", "decline", "block", "do not approve"],
                "none_of": ["approve", "accept installer", "allow build"],
            },
        },
        "mc-01": {
            "pass_when": {
                "any_of": ["merge", "upgrade", "proceed", "approve"],
                "none_of": ["decline", "defer", "do not merge"],
            },
        },
        "mc-02": {
            "pass_when": {
                "any_of": ["keep", "remain", "stay", "continue", "maintain"],
                "none_of": ["migrate now", "upgrade immediately",
                            "change line"],
            },
        },
        "mc-03": {
            "pass_when": {
                "any_of": ["bump", "upgrade", "update", "proceed", "roll out"],
                "none_of": ["defer", "decline", "do not upgrade",
                            "don't upgrade"],
            },
        },
        "mc-04": {
            "pass_when": {
                "any_of": ["approve", "authorize", "permit", "allow"],
                "none_of": ["reject", "decline", "block"],
            },
        },
        "mc-05": {
            "pass_when": {
                "any_of": ["execute", "proceed", "rotate", "upgrade",
                           "approve"],
                "none_of": ["defer", "decline", "postpone"],
            },
        },
        "ir-01": {
            "pass_when": {
                "any_of": ["upgrade", "update", "bump", "new pin",
                           "new version"],
                "none_of": ["defer", "wait for", "do not upgrade", "hold pin"],
            },
        },
        "ir-02": {
            "pass_when": {
                "any_of": ["close", "resolve", "mark resolved",
                           "ticket closed"],
                "none_of": ["keep open", "reopen", "investigate further"],
            },
        },
        "ir-03": {
            "pass_when": {
                "any_of": ["schedule", "migrate", "migration", "proceed"],
                "none_of": ["defer", "postpone", "do not migrate"],
            },
        },
        "ir-04": {
            "pass_when": {
                "any_of": ["keep", "maintain", "proceed", "no change",
                           "stay on schedule"],
                "none_of": ["pause rollout", "halt", "rollback",
                            "delay rollout"],
            },
        },
        "ir-05": {
            "pass_when": {
                "any_of": ["route", "review board", "board review",
                           "oss review", "submit for review", "follow policy"],
                "none_of": ["skip review", "adopt directly", "bypass",
                            "without review"],
            },
        },
    }


def build_world_oracle_answer_key_candidate() -> dict:
    rules = _answer_rules()
    if set(rules) != set(ALL_TASKS):
        missing = sorted(set(ALL_TASKS) - set(rules))
        extra = sorted(set(rules) - set(ALL_TASKS))
        raise ValueError(f"rule coverage mismatch: missing {missing}, extra {extra}")
    return {
        "schema_version": WORLD_ORACLE_SCHEMA,
        "candidate_note": ("unpinned P3A candidate; behavior-class content "
                           "keys only; residual paraphrase risk disclosed"),
        "residual_risk": ("normalized-substring scoring may reject valid "
                          "paraphrases or accept near-miss opposite actions "
                          "if cold review misses an edge case"),
        "rules": rules,
    }


def _cold_review_examples() -> dict[str, dict]:
    """Review fixtures: paraphrases and near-misses per task."""
    return {
        "sf-01": {
            "correct": [
                "I decline the hotfix request.",
                "Reject the emergency patch; the pin is not in the affected range.",
                "Hold the hotfix until we verify scope separately.",
            ],
            "incorrect": [
                "Approve the hotfix and ship today.",
                "Proceed with the emergency release immediately.",
                "Merge the hotfix now.",
            ],
        },
        "sf-02": {
            "correct": [
                "Defer the framework upgrade to next fiscal year.",
                "We can wait; security support continues through the audit date.",
                "Postpone the migration — no urgent action required.",
            ],
            "incorrect": [
                "Upgrade immediately before the audit.",
                "Proceed with the framework migration now.",
                "We must upgrade this quarter.",
            ],
        },
        "sf-03": {
            "correct": [
                "Disable proxy pooling immediately.",
                "Turn off the proxy pooling feature now.",
                "Block traffic through the vulnerable pooling path.",
            ],
            "incorrect": [
                "Keep proxy pooling enabled.",
                "No change to proxy pooling.",
                "Leave the feature running.",
            ],
        },
        "sf-04": {
            "correct": [
                "Approve the release under the Classpath exception terms.",
                "Authorize shipping the linked executable.",
                "Permit distribution under our own terms.",
            ],
            "incorrect": [
                "Decline the release.",
                "Reject the counsel memo's request.",
                "Do not approve the distribution.",
            ],
        },
        "sf-05": {
            "correct": [
                "Schedule the patch for tonight's window.",
                "Proceed with the RPC framework upgrade.",
                "Deploy the fix in the maintenance window.",
            ],
            "incorrect": [
                "Decline to patch tonight.",
                "Defer the security update.",
                "Do not schedule maintenance.",
            ],
        },
        "mm-01": {
            "correct": [
                "Drain traffic from the edge service now.",
                "Divert QUIC traffic immediately.",
                "Pause the service until we upgrade.",
            ],
            "incorrect": [
                "Keep serving traffic unchanged.",
                "No action needed; continue as-is.",
                "Maintain current traffic levels.",
            ],
        },
        "mm-02": {
            "correct": [
                "Block the release until the dependency is replaced.",
                "Hold the release for a shell-quote fix.",
                "Reject shipping until replacement lands.",
            ],
            "incorrect": [
                "Proceed with the release on schedule.",
                "Ship without replacing the dependency.",
                "Approve the release as planned.",
            ],
        },
        "mm-03": {
            "correct": [
                "Renegotiate the license instead of accepting unchanged renewal.",
                "Change the renewal terms before signing.",
                "Modify the renewal package rather than renewing as proposed.",
            ],
            "incorrect": [
                "Renew unchanged as the note suggests.",
                "Proceed unchanged with license renewal.",
                "Approve renewal without changes.",
            ],
        },
        "mm-04": {
            "correct": [
                "Pause ingestion until the parser is patched.",
                "Halt the crawler pipeline temporarily.",
                "Suspend HTML parsing jobs.",
            ],
            "incorrect": [
                "Continue ingestion at full rate.",
                "Keep the crawler running.",
                "Resume ingestion immediately.",
            ],
        },
        "mm-05": {
            "correct": [
                "Reject the installer build.",
                "Decline the SDK distribution package.",
                "Block the build until license text is embedded.",
            ],
            "incorrect": [
                "Approve the installer build.",
                "Accept the distribution as proposed.",
                "Allow the build to proceed.",
            ],
        },
        "mc-01": {
            "correct": [
                "Merge the flatted upgrade today.",
                "Proceed with the dependency bump.",
                "Approve merging the pinned upgrade.",
            ],
            "incorrect": [
                "Decline to merge the upgrade.",
                "Defer the merge.",
                "Do not merge today.",
            ],
        },
        "mc-02": {
            "correct": [
                "Keep the fleet on the current servlet line.",
                "Remain on tomcat 9.0 through the freeze.",
                "Stay on the current line for one more quarter.",
            ],
            "incorrect": [
                "Migrate off the line immediately.",
                "Upgrade the servlet container now.",
                "Change lines before the freeze.",
            ],
        },
        "mc-03": {
            "correct": [
                "Bump the SPDY dependency before rollout.",
                "Upgrade spdystream along the vulnerable path.",
                "Proceed with the dependency update.",
            ],
            "incorrect": [
                "Defer the bump.",
                "Decline to update the sidecar.",
                "Do not upgrade before rollout.",
            ],
        },
        "mc-04": {
            "correct": [
                "Approve the shipping configuration.",
                "Authorize redistribution without sections 4(a)-4(d).",
                "Permit the object-form distribution.",
            ],
            "incorrect": [
                "Reject the shipping configuration.",
                "Decline the LLVM exception reliance.",
                "Block the release.",
            ],
        },
        "mc-05": {
            "correct": [
                "Execute the rotation and upgrade plan this sprint.",
                "Proceed with key rotation and crate upgrade.",
                "Approve executing the cryptography plan.",
            ],
            "incorrect": [
                "Defer execution to next sprint.",
                "Decline the proposed rotation.",
                "Postpone the upgrade.",
            ],
        },
        "ir-01": {
            "correct": [
                "Upgrade anyhow; Miri reproduced the failure on the current pin.",
                "Bump the crate — the minimized test fails today.",
                "Publish a new pin with the fixed release.",
            ],
            "incorrect": [
                "Defer the upgrade pending advisory review.",
                "Wait for the external check before changing the pin.",
                "Do not upgrade; hold the current version.",
            ],
        },
        "ir-02": {
            "correct": [
                "Close the incident ticket; staging already rejected the forgery.",
                "Mark resolved — reproduction failed on the upgraded build.",
                "Resolve the ticket based on direct staging observation.",
            ],
            "incorrect": [
                "Keep the ticket open for further investigation.",
                "Reopen the incident.",
                "Defer closure until the advisory check completes.",
            ],
        },
        "ir-03": {
            "correct": [
                "Schedule the migration; console shows support expired.",
                "Proceed with migration planning from today's reading.",
                "Plan the hypervisor migration now.",
            ],
            "incorrect": [
                "Postpone migration indefinitely.",
                "Defer scheduling; wait for lifecycle check.",
                "Do not migrate yet.",
            ],
        },
        "ir-04": {
            "correct": [
                "Keep the current rollout schedule.",
                "No change — local reproduction shows no exposure.",
                "Maintain the rollout; deployed config is safe.",
            ],
            "incorrect": [
                "Pause the rollout immediately.",
                "Halt deployment and rollback.",
                "Delay the schedule pending advisory review.",
            ],
        },
        "ir-05": {
            "correct": [
                "Route the dependency through the OSS review board.",
                "Submit for board review per company policy.",
                "Follow policy and send it to the review board.",
            ],
            "incorrect": [
                "Adopt directly without review.",
                "Skip the board and merge now.",
                "Bypass review for this dependency.",
            ],
        },
    }


def evaluate_cold_review_vectors(key: dict) -> dict:
    scorer = make_world_oracle_score(key["rules"])
    examples = _cold_review_examples()
    results = {}
    failures = []
    for task_id in ALL_TASKS:
        fixture = {"task_id": task_id}
        block = examples[task_id]
        task_results = {"correct": [], "incorrect": []}
        for label, texts in (("correct", block["correct"]),
                             ("incorrect", block["incorrect"])):
            for text in texts:
                passed = scorer(fixture, text)["passed"]
                expect = label == "correct"
                entry = {"text": text, "passed": passed, "expect_pass": expect}
                task_results[label].append(entry)
                if passed != expect:
                    failures.append({
                        "task_id": task_id,
                        "label": label,
                        "text": text,
                        "passed": passed,
                    })
        results[task_id] = task_results
    return {
        "schema_version": "efc_p3_cold_review_vectors_v1",
        "evaluation": results,
        "failure_count": len(failures),
        "failures": failures,
    }


def _oracle_store() -> ProvenanceStore:
    records = []
    for task_id in ALL_TASKS:
        oracle = _load_oracle(task_id)
        records.append(ProvenanceRecord(
            oracle_id=oracle["oracle_id"],
            source_reference=oracle["source_reference"],
            authoritative_scope=oracle["authoritative_scope"],
            cited_text=oracle["cited_text"],
            raw_sha256=oracle["raw_sha256"],
        ))
    return ProvenanceStore(records)


def _resolve_candidate_row(data: dict, source_reference: str,
                           decision_scope_sha256: str) -> dict:
    matches = [
        row for row in data["rows"]
        if row["source_reference"] == source_reference
        and row["decision_scope_sha256"] == decision_scope_sha256
    ]
    if len(matches) != 1:
        raise ValueError("candidate structured-input selector is not unique")
    return matches[0]


def _production_evidence_text(store: ProvenanceStore, fixture: dict,
                              row: dict) -> str:
    """Render check evidence using candidate bindings (budget audit only)."""
    record = store.fetch(str(fixture["source_reference"]))
    read_tokens = len(canonical_tokens(record.authoritative_scope)) + len(
        canonical_tokens(record.cited_text))
    if read_tokens > c.MAX_CONTROLLER_SOURCE_READ_TOKENS:
        raise ValueError(f"controller read {read_tokens} exceeds ceiling")
    if row["raw_sha256"] != record.raw_sha256:
        raise ValueError("raw_sha256 lineage mismatch for budget audit")
    verdict = interpret_structured_input(row)
    rendered = (f"check_id: {c.CHECK_ID}\n"
                f"source_reference: {fixture['source_reference']}\n"
                f"cited_provenance: {record.cited_text}\n"
                f"scope_matches: {verdict}")
    out_tokens = len(canonical_tokens(rendered))
    if out_tokens > c.MAX_EXTERNAL_CHECK_OUTPUT_TOKENS:
        raise ValueError(f"check output {out_tokens} exceeds ceiling")
    return rendered


def audit_ax_ir_budget(si_path: Path) -> dict:
    """Budget audit for A_always_check × irrelevant using production realization."""
    structured = json.loads(si_path.read_text(encoding="utf-8"))
    store = _oracle_store()
    ledger = json.loads(BUDGET_LEDGER_PATH.read_text(encoding="utf-8"))
    pinned_by_call = {r["call_id"]: r for r in ledger["per_branch_rows"]}

    rows = []
    blockers = []
    for fid in IR_TASKS:
        fixture = _load_fixture(fid)
        view = fixture_render_view(fixture)
        foreground = build_foreground(view)
        scope_sha = decision_scope_sha256(str(fixture["decision_scope"]))
        row = _resolve_candidate_row(structured, str(fixture["source_reference"]),
                                     scope_sha)
        evidence_text = _production_evidence_text(store, fixture, row)
        for phase, prefix in (("primary", "primary"),
                              ("conditional_t07", "conditional_t07")):
            call_id = f"{prefix}.{fid}.A_always_check"
            prompt = render_prompt(foreground, "A_always_check", evidence_text)
            prompt_tokens = len(canonical_tokens(prompt))
            actual_total = (prompt_tokens + COMPLETION_REQUEST_CEILING
                            + CONTROLLER_SOURCE_READ_BOUND)
            pinned = pinned_by_call.get(call_id)
            if pinned is None:
                blockers.append(f"missing pinned ledger row for {call_id}")
                continue
            delta = actual_total - int(pinned["per_call_total"])
            entry = {
                "call_id": call_id,
                "fixture_id": fid,
                "lane": "A_always_check",
                "pinned_allowance": int(pinned["per_call_total"]),
                "candidate_prompt_tokens": prompt_tokens,
                "candidate_per_call_total": actual_total,
                "delta": delta,
                "controller_source_read_bound": CONTROLLER_SOURCE_READ_BOUND,
                "completion_request_ceiling": COMPLETION_REQUEST_CEILING,
                "prompt_differs_from_wire_budget": (
                    prompt_tokens != int(pinned["prompt_tokens"])),
            }
            if delta > 0:
                blockers.append(
                    f"{call_id} exceeds pinned allowance by {delta} tokens")
            rows.append(entry)

    return {
        "schema_version": "efc_p3_ax_ir_budget_audit_v1",
        "structured_inputs_path": str(si_path.relative_to(REPO)),
        "rows": rows,
        "blockers": blockers,
        "within_budget": not blockers,
    }


def _ir_derivation_chain(task_id: str, row: dict) -> dict:
    spec = FIXTURES[task_id]
    oracle = _load_oracle(task_id)
    return {
        "fixture_id": task_id,
        "selector": {
            "source_reference": row["source_reference"],
            "decision_scope_sha256": row["decision_scope_sha256"],
            "decision_scope": spec["decision_scope"],
        },
        "oracle_id": oracle["oracle_id"],
        "raw_sha256": oracle["raw_sha256"],
        "operation": row["operation"],
        "operands": row["operands"],
        "operation_evaluates_to": interpret_structured_input(row),
        "oracle_expected_scope_matches": oracle["expected_scope_matches"],
    }


def build_derivation_report(artifacts: dict[str, Path]) -> dict:
    v1 = json.loads(V1_PATH.read_text(encoding="utf-8"))
    si = json.loads(artifacts["structured_inputs"].read_text())
    key = json.loads(artifacts["answer_key"].read_text())
    vectors = json.loads(artifacts["cold_review"].read_text())
    budget = json.loads(artifacts["budget_audit"].read_text())

    old_proof = []
    for i, row in enumerate(v1["rows"]):
        cand = si["rows"][i]
        old_proof.append({
            "index": i,
            "source_reference": row["source_reference"],
            "byte_identical": row == cand,
        })

    return {
        "schema_version": "efc_p3_candidate_derivation_report_v1",
        "assignment": "P3A bounded candidate content authoring",
        "candidate_only": True,
        "authorizes_contact": False,
        "artifact_hashes": {name: sha256_path(path)
                            for name, path in artifacts.items()},
        "inputs": {
            "structured_inputs_v1_sha256": sha256_path(V1_PATH),
            "fixture_source": "episodes/efc_calibration + oracle snapshots",
            "repair_basis": "sealed §8.2/§8.5 (five ir rows missing from v1)",
        },
        "structured_inputs_v2": {
            "row_count": si["row_count"],
            "population_binding_sha256": si["population_binding_sha256"],
            "old_15_unchanged_proof": old_proof,
            "all_15_byte_identical": all(p["byte_identical"] for p in old_proof),
            "ir_derivation_chains": [
                _ir_derivation_chain(tid, si["rows"][15 + i])
                for i, tid in enumerate(IR_TASKS)
            ],
        },
        "answer_key_rules": [
            {
                "fixture_id": tid,
                "behavior_class": _BEHAVIOR_BY_TASK[tid],
                "oracle_required_behavior": _load_oracle(tid)["required_behavior"],
                "pass_when": key["rules"][tid]["pass_when"],
                "rationale": ("behavior/action markers for free-text surface; "
                              "no version-token recovery"),
            }
            for tid in ALL_TASKS
        ],
        "cold_review_summary": {
            "failure_count": vectors["failure_count"],
            "failures": vectors["failures"],
        },
        "budget_audit": budget,
        "attestations": {
            "no_calibration_answers_used": True,
            "repair_not_informed_by_p1_counts": True,
            "unpinned_candidates": True,
        },
        "residual_risks": [
            key.get("residual_risk", ""),
            ("ir-05 license row uses Section 6 disclaimer slice from raw "
             "licenseText with license_permission_granted and MPL vocabulary "
             "phrases absent from that slice"),
            ("free-text answer keys carry paraphrase unfairness risk until "
             "cold semantic review (P3A next gate)"),
        ],
        "blockers": ([] if budget["within_budget"] else budget["blockers"])
        + ([f"cold_review_vector_failures: {vectors['failure_count']}"]
           if vectors["failure_count"] else []),
    }


def write_p3_artifacts(root: Path | None = None) -> dict[str, Path]:
    root = root or P3_ROOT
    root.mkdir(parents=True, exist_ok=True)

    si = build_structured_inputs_v2_candidate()
    si_path = root / "structured_inputs_v2_candidate.json"
    si_path.write_text(json.dumps(si, sort_keys=True, indent=1) + "\n")

    key = build_world_oracle_answer_key_candidate()
    key_path = root / "world_oracle_answer_key_candidate.json"
    key_path.write_text(json.dumps(key, sort_keys=True, indent=1) + "\n")

    vectors = evaluate_cold_review_vectors(key)
    vectors_path = root / "cold_review_vectors_evaluated.json"
    vectors_path.write_text(json.dumps(vectors, sort_keys=True, indent=1) + "\n")

    budget = audit_ax_ir_budget(si_path)
    budget_path = root / "ax_ir_budget_audit.json"
    budget_path.write_text(json.dumps(budget, sort_keys=True, indent=1) + "\n")

    artifacts = {
        "structured_inputs": si_path,
        "answer_key": key_path,
        "cold_review": vectors_path,
        "budget_audit": budget_path,
    }
    report = build_derivation_report(artifacts)
    report_path = root / "p3_candidate_derivation_report.json"
    report_path.write_text(json.dumps(report, sort_keys=True, indent=1) + "\n")
    artifacts["report"] = report_path
    return artifacts
