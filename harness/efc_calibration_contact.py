"""Production calibration contact surface — P2 (Sol's assignment).

Replaces the wire-era unconditional production refusal with a typed,
recompute-from-current-bytes authority: `CalibrationContactAuthorization`
(a `ContactAuthorization` subtype) minted only by
`authorize_calibration_contact`, and one execution surface
`run_production_calibration_branch` that runs the canonical phases STARTING
AFTER PROBES — the completed P1 ignorance result is imported as a bound
prior event and probes are never called again.

Authority is branch-specific, single-use, full-board-only. It requires, all
recomputed from current bytes at mint AND again at execute time:

- a passing C4d full verification through the sole active status selector
  (`efc-cal-manifest-pin-2600d1fdba7b-s2`);
- the exact manifest/packet/population bindings of the active pin;
- the P1 append-only ignorance result: all four original run-file hashes,
  recomputed sidecar canonical hashes and counts, and the branch-specific
  `ignorance_gate_pass` — the premature `engine_admitted` strings in the
  original result files are never accepted as authority;
- the exact roster branch/model and its co-pinned decoding payload bytes;
- the final production comparison contract
  (`af370e93…`, == the pinned manifest's `check_contract_hash`);
- the pinned production answer+route collapse contract
  (harness/efc_collapse_production.py);
- a pinned production world-oracle answer scorer artifact — SEE BELOW;
- named-check population-binding coverage for every fixture x lane that
  runs the check — SEE BELOW;
- K=5, T=0.5/T=0.7, the no-retry stop rule, and a positive remaining branch
  budget covering the full 105-call primary board plus the single
  conditional 105-call T=0.7 pass (ceiling 210 calibration calls/branch).

Two structural gaps discovered while building this surface make production
authority UNMINTABLE on the current tree; both refuse fail-closed with
typed messages rather than being papered over:

1. **No pinned production world-oracle answer scorer exists.** Oracle
   records pin `required_behavior`, but nothing in the repo maps free
   engine text to a world-scored `passed`, and the foreground template is
   hash-pinned so no answer grammar can be added to the prompt. This module
   defines the scorer artifact's closed schema
   (`efc_world_oracle_answer_key_v1` at
   corpus/efc_calibration/oracle/world_oracle_answer_key.json) and the
   deterministic evaluator, but authoring the semantic rules is oracle
   content outside this seat's P2 authorization.
2. **The pinned population bindings (15 rows) do not cover the five
   irrelevant-stratum fixtures**, yet lane `A_always_check` runs the named
   check on every analog fixture. A production A-lane check on ir-01..05
   has no hash-pinned row and would refuse mid-board; authority therefore
   refuses at mint with the exact missing selectors.

Wire objects are never authority here: a dict, `WireContactAuthorization`,
`ProbeContactAuthorization`, a bare `ContactAuthorization`, a stale/forged
dataclass, a name-only decoding id, or an answer-only collapse detector all
refuse. `run_admission_branch` (wire-era) still refuses unconditionally and
is left byte-untouched; this module is the P0-precedent typed opening.

Zero network unless `--contact` is explicitly passed with a mintable
authorization. Nothing in this module authorizes probe reruns, held-out
work, or listing calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field, fields
from pathlib import Path

from harness import efc_contracts as c
from harness import efc_pin_c4b as c4b
from harness import efc_pin_c4d as c4d
from harness.efc_check import (ProvenanceRecord, ProvenanceStore,
                               production_check_contract_hash)
from harness.efc_collapse_production import (
    DETECTOR_ID as COLLAPSE_DETECTOR_ID,
    build_production_collapse_detector, production_collapse_contract_hash,
    verify_collapse_pin)
from harness.efc_compare_production import build_production_contract
from harness.efc_controller import EngineResult
from harness.efc_ledger import make_row
from harness.efc_manifest import check_calibration_manifest
from harness.efc_packet import derive_call_plan, load_packet
from harness.efc_planner import CollapseState, IgnoranceProbeResult
from harness.efc_probe_contact import (P1_RUN_ROOT_REL,
                                       IGNORANCE_GATE_RESULT_NAME,
                                       RESULT_NAME as PROBE_RESULT_NAME,
                                       SIDECAR_NAME as PROBE_SIDECAR_NAME,
                                       VERDICT_IGNORANCE_GATE_PASS,
                                       ProbeContactAuthorization,
                                       _load_sidecar_rows, sha256_canon,
                                       sha256_path)
from harness.efc_renderer import foreground_template_hash
from harness.efc_roster_r2 import (API_BASE, API_TOP_P_INCLUDED, LOCAL_BASE,
                                   OUTPUT_CEILING, _extract_text, _http_post)
from harness.efc_runner import (BranchReport, ContactAuthorization,
                                RunnerContractError, TransportRefusal,
                                WireContactAuthorization, _BranchRefused,
                                _OnceGuard, _SessionTracker, _rows_sha256,
                                _run_board, _s_band,
                                STATUS_BRANCH_REFUSED_TRANSPORT,
                                STATUS_COMPLETED, T07_NAMESPACE,
                                emit_admission_verdict,
                                packet_index_sha256,
                                validate_pinned_collapse_detector)

ROOT = Path(__file__).resolve().parents[1]
MODULE_REL = "harness/efc_calibration_contact.py"
PACKET_ROOT_REL = "episodes/efc_calibration"
ORACLE_ROOT_REL = "corpus/efc_calibration/oracle"
WORLD_ORACLE_SCORER_REL = (
    "corpus/efc_calibration/oracle/world_oracle_answer_key.json")
WORLD_ORACLE_SCORER_SCHEMA = "efc_world_oracle_answer_key_v1"
P2_REPORT_REL = ("corpus/efc_calibration/authoring_c4/"
                 "p2_calibration_contact_implementation_report.json")

# resolution A closed: the final population-pinned check contract identity
CHECK_CONTRACT_SHA = ("af370e93a021436771dd805b384139c59be592bda677d2675eb1"
                      "904ea5bfa79b")

BRANCH_LOCAL = "local"
BRANCH_API = "api"
BRANCH_MODEL = {BRANCH_LOCAL: "openai/gpt-oss-20b",
                BRANCH_API: "gpt-5.4-2026-03-05"}
ROSTER_BRANCH_ORDER = (BRANCH_LOCAL, BRANCH_API)

PRIMARY_BOARD_CALLS = 105          # 15 S-family + 90 analog, T=0.5
CONDITIONAL_BOARD_CALLS = 105      # single same-identity T=0.7 pass
CEILING_CALLS_PER_BRANCH = PRIMARY_BOARD_CALLS + CONDITIONAL_BOARD_CALLS

PRIMARY_ROWS_NAME = "calibration_rows.jsonl"
T07_ROWS_NAME = "t07.calibration_rows.jsonl"
RESULT_NAME = "calibration_branch_result.json"

PROVIDER_CACHE_STATUS = "unverified"


class CalibrationContactError(ValueError):
    """Production calibration contact outside the pinned contract.
    Fail-closed."""


def _refuse(msg: str) -> None:
    raise CalibrationContactError(msg)


# ---------------------------------------------------------------------------
# Typed authority.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CalibrationContactAuthorization(ContactAuthorization):
    """Branch-specific, single-use, full-board-only production authority.

    Cannot authorize probes: `run_production_ignorance_probes` rejects any
    `ContactAuthorization` instance, and this runner rejects probe/wire
    authorities symmetrically. The wire-era `run_admission_branch` still
    refuses unconditionally and never gains a construction path here."""
    branch: str = ""
    pin_event_id: str = ""
    manifest_file_sha256: str = ""
    decoding_contract_sha256: str = ""
    world_oracle_scorer_sha256: str = ""
    p1_correction_result_sha256: str = ""
    p1_sidecar_file_sha256: str = ""
    p1_sidecar_canonical_sha256: str = ""
    p1_original_result_sha256: str = ""
    p1_recovered: int = -1
    p1_n: int = -1
    p1_max_recoverable_rate: float = -1.0
    p1_ignorance_gate_verdict: str = ""
    calibration_k: int = -1
    temperature_primary: float = -1.0
    temperature_diagnostic: float = -1.0
    probe_budget_spent_tokens: int = -1
    primary_budget_tokens: int = -1
    conditional_budget_tokens: int = -1
    remaining_branch_budget_tokens: int = -1
    roster_total_budget_tokens: int = -1
    consumed: bool = field(default=False, repr=False, compare=False)

    def mark_consumed(self) -> None:
        if self.consumed:
            _refuse("calibration authorization already consumed (single-use)")
        object.__setattr__(self, "consumed", True)


def _reject_non_authority(authorization: object
                          ) -> CalibrationContactAuthorization:
    if isinstance(authorization, dict):
        _refuse("a mapping is never calibration authority")
    if isinstance(authorization, WireContactAuthorization):
        _refuse("wire authorization cannot authorize production calibration")
    if isinstance(authorization, ProbeContactAuthorization):
        _refuse("probe-only authorization cannot authorize the calibration "
                "board")
    if not isinstance(authorization, CalibrationContactAuthorization):
        _refuse("calibration execution requires a typed "
                "CalibrationContactAuthorization minted by "
                "authorize_calibration_contact (a bare ContactAuthorization "
                "carries no recomputable bindings and is refused)")
    if authorization.consumed:
        _refuse("calibration authorization already consumed (single-use)")
    return authorization


# ---------------------------------------------------------------------------
# Pinned world-oracle answer scorer (schema + evaluator; artifact unauthored).
# ---------------------------------------------------------------------------

def _normalize_answer(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def _validate_scorer_rules(rules: dict, fixture_ids: set[str]) -> None:
    if set(rules) != fixture_ids:
        _refuse("world-oracle answer key must cover exactly the pinned "
                f"calibration fixture ids; missing "
                f"{sorted(fixture_ids - set(rules))}, extra "
                f"{sorted(set(rules) - fixture_ids)}")
    for fixture_id, rule in rules.items():
        if not isinstance(rule, dict) or set(rule) - {"pass_when"} \
                or not isinstance(rule.get("pass_when"), dict):
            _refuse(f"malformed scorer rule for {fixture_id!r}")
        pw = rule["pass_when"]
        if set(pw) - {"all_of", "any_of", "none_of"}:
            _refuse(f"scorer rule for {fixture_id!r} carries undeclared "
                    "clauses")
        if not (pw.get("all_of") or pw.get("any_of")):
            _refuse(f"scorer rule for {fixture_id!r} needs at least one "
                    "positive clause (all_of or any_of)")
        for key in ("all_of", "any_of", "none_of"):
            tokens = pw.get(key, [])
            if not isinstance(tokens, list) or not all(
                    isinstance(t, str) and t for t in tokens):
                _refuse(f"scorer rule for {fixture_id!r}: {key} must be a "
                        "list of non-empty strings")


def load_world_oracle_scorer(root: Path, fixture_ids: set[str]
                             ) -> tuple[dict, str]:
    """Load and validate the pinned scorer artifact. Refuses with the typed
    structural-gap message while the artifact is unauthored."""
    path = root / WORLD_ORACLE_SCORER_REL
    if not path.is_file():
        _refuse("production world-oracle answer scorer is not pinned: no "
                f"artifact at {WORLD_ORACLE_SCORER_REL} (schema "
                f"{WORLD_ORACLE_SCORER_SCHEMA}). Free engine text cannot be "
                "world-scored without a reviewed frozen rule, and the "
                "foreground template is hash-pinned so no answer grammar "
                "can be added to the prompt. Authoring the rules is oracle "
                "content requiring a separate assignment and cold review; "
                "calibration authority is unmintable until then "
                "(fail-closed, P2 structural finding 1)")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema_version") != WORLD_ORACLE_SCORER_SCHEMA:
        _refuse("world-oracle answer key schema_version mismatch")
    rules = doc.get("rules")
    if not isinstance(rules, dict):
        _refuse("world-oracle answer key carries no rules mapping")
    _validate_scorer_rules(rules, fixture_ids)
    return rules, sha256_path(path)


def make_world_oracle_score(rules: dict):
    """Deterministic, engine-invisible world-oracle scorer over the pinned
    rules: normalized-substring clauses, strict bool."""
    def oracle_score(fixture: dict, answer_text: str) -> dict:
        fixture_id = str(fixture.get("task_id"))
        rule = rules.get(fixture_id)
        if rule is None:
            _refuse(f"no pinned world-oracle rule for {fixture_id!r}")
        norm = _normalize_answer(answer_text)
        pw = rule["pass_when"]
        passed = (all(t.lower() in norm for t in pw.get("all_of", []))
                  and (not pw.get("any_of")
                       or any(t.lower() in norm for t in pw["any_of"]))
                  and not any(t.lower() in norm
                              for t in pw.get("none_of", [])))
        return {"passed": bool(passed),
                "oracle_source": WORLD_ORACLE_SCORER_SCHEMA}
    return oracle_score


# ---------------------------------------------------------------------------
# Mint-time bindings.
# ---------------------------------------------------------------------------

def _derive_budget(ledger: dict) -> dict:
    rows = ledger.get("per_branch_rows", ())
    def total(*categories):
        return sum(int(r["per_call_total"]) for r in rows
                   if r.get("category") in categories)
    probe = total("probe")
    primary = total("s_family", "analog")
    conditional = total("conditional_s_family", "conditional_analog")
    branch_total = int(ledger["totals"]["branch_total_tokens"])
    remaining = branch_total - probe
    if remaining <= 0 or remaining < primary + conditional:
        _refuse("remaining branch budget after the completed probes does "
                "not cover the primary board plus the single conditional "
                "pass")
    counts = {cat: sum(1 for r in rows if r.get("category") == cat)
              for cat in ("s_family", "analog", "conditional_s_family",
                          "conditional_analog")}
    if counts["s_family"] != 15 or counts["analog"] != 90 \
            or counts["conditional_s_family"] != 15 \
            or counts["conditional_analog"] != 90:
        _refuse(f"pinned ledger call cardinalities are not the 105/105 "
                f"board: {counts}")
    return {"probe_spent": probe, "primary": primary,
            "conditional": conditional, "remaining": remaining,
            "roster_total": int(
                ledger["totals"]["roster_total_budget_tokens"])}


def _load_p1_prior(root: Path, branch: str) -> dict:
    """Bind the completed P1 ignorance event: recompute everything from the
    preserved sidecars; never accept the premature engine_admitted label."""
    run_root = root / P1_RUN_ROOT_REL
    correction_path = run_root / IGNORANCE_GATE_RESULT_NAME
    if not correction_path.is_file():
        _refuse("P1 append-only ignorance result is missing: "
                f"{P1_RUN_ROOT_REL}/{IGNORANCE_GATE_RESULT_NAME}")
    correction = json.loads(correction_path.read_text(encoding="utf-8"))
    branch_entry = correction.get("branches", {}).get(branch)
    if not isinstance(branch_entry, dict):
        _refuse(f"P1 correction carries no {branch!r} branch entry")

    sidecar_path = run_root / branch / PROBE_SIDECAR_NAME
    result_path = run_root / branch / PROBE_RESULT_NAME
    for label, path in (("sidecar", sidecar_path), ("result", result_path)):
        if not path.is_file():
            _refuse(f"missing original P1 {branch} {label}")
    sidecar_file_sha = sha256_path(sidecar_path)
    result_sha = sha256_path(result_path)
    if sidecar_file_sha != branch_entry.get(
            "original_probe_sidecar_file_sha256") \
            or result_sha != branch_entry.get(
                "original_probe_branch_result_sha256"):
        _refuse(f"original P1 {branch} run files do not match the "
                "append-only correction bindings (mutation)")

    rows = _load_sidecar_rows(sidecar_path)
    if len(rows) != 15:
        _refuse("P1 sidecar denominator is not exactly 15 (structural)")
    recovered = sum(1 for r in rows if r.get("recovered"))
    canonical = sha256_canon(rows)
    if canonical != branch_entry.get("probe_sidecar_canonical_sha256") \
            or recovered != branch_entry.get("recovered_count"):
        _refuse(f"P1 {branch} sidecar recomputation disagrees with the "
                "correction artifact")
    verdict = branch_entry.get("ignorance_gate_verdict")
    if verdict != VERDICT_IGNORANCE_GATE_PASS or recovered > 3:
        _refuse(f"P1 {branch} ignorance gate is not a recomputed pass "
                f"(verdict {verdict!r}, recovered {recovered}/15); a "
                "premature engine_admitted label is never authority")
    return {
        "correction_sha256": sha256_path(correction_path),
        "sidecar_file_sha256": sidecar_file_sha,
        "sidecar_canonical_sha256": canonical,
        "original_result_sha256": result_sha,
        "sidecar_rows": rows,
        "recovered": recovered,
        "n": 15,
        "max_recoverable_rate": float(
            branch_entry.get("max_recoverable_rate", 0.0)),
    }


def _build_provenance_store(root: Path) -> tuple[ProvenanceStore, dict]:
    oracle_root = root / ORACLE_ROOT_REL
    records, by_fixture = [], {}
    for path in sorted(oracle_root.glob("*.json")):
        if path.name in ("probe_answer_key.json",
                         "world_oracle_answer_key.json"):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        records.append(ProvenanceRecord(
            oracle_id=str(payload["oracle_id"]),
            source_reference=str(payload["source_reference"]),
            authoritative_scope=str(payload["authoritative_scope"]),
            cited_text=str(payload["cited_text"]),
            raw_sha256=str(payload["raw_sha256"])))
        by_fixture[str(payload["task_id"])] = payload
    return ProvenanceStore(records), by_fixture


def _check_population_coverage(contract, packet) -> None:
    """P2 structural finding 2: every fixture x lane that runs the named
    check must resolve a hash-pinned population binding. Today the five
    irrelevant-stratum fixtures have none, yet A_always_check checks them."""
    from harness.efc_compare_production import REPO
    data_rows = json.loads(
        (REPO / contract.structured_inputs_path).read_text(
            encoding="utf-8"))["rows"]
    selectors = {(r["source_reference"], r["decision_scope_sha256"])
                 for r in data_rows}
    missing = []
    for fixture_id, fixture in sorted({**packet.s_family,
                                       **packet.analog}.items()):
        key = (str(fixture["source_reference"]),
               hashlib.sha256(str(fixture["decision_scope"])
                              .encode("utf-8")).hexdigest())
        if key not in selectors:
            missing.append(fixture_id)
    if missing:
        _refuse("named-check population bindings are incomplete: lane "
                "A_always_check runs the check on every fixture, but the "
                f"pinned structured inputs carry no row for {missing}. A "
                "production check there refuses mid-board; extending the "
                "population binding is pinned-content work requiring a "
                "separate ruling (fail-closed, P2 structural finding 2)")


def _load_calibration_bindings(root: Path) -> dict:
    c4d.verify(root, full=True)
    manifest_path = root / c4b.MANIFEST_REL
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sibling = json.loads((root / c4b.SIBLING_REL).read_text(encoding="utf-8"))
    ledger = json.loads((root / c4b.LEDGER_REL).read_text(encoding="utf-8"))

    result = check_calibration_manifest(manifest)
    if not result.ok:
        _refuse(f"manifest failed closed-schema check: {result.failures}")
    if sha256_path(manifest_path) != c4b.MANIFEST_FILE_SHA:
        _refuse("manifest file sha256 does not match the active pin binding")
    if result.manifest_hash != c4b.MANIFEST_CANONICAL_HASH:
        _refuse("manifest canonical hash does not match the active pin "
                "binding")
    packet_index_sha = sha256_path(root / f"{PACKET_ROOT_REL}/"
                                          "packet_index.json")
    if packet_index_sha != c4d.validate_bundle(root)["lineage"][
            "packet_index"]:
        _refuse("packet index sha256 does not recompute from lineage "
                "bindings")

    # final production comparison contract (resolution A, closed)
    contract = build_production_contract()
    check_hash = production_check_contract_hash(contract)
    if check_hash != CHECK_CONTRACT_SHA \
            or check_hash != manifest["check_contract_hash"]:
        _refuse("production check contract hash does not recompute to the "
                "pinned identity")

    # pinned production collapse contract (this P2 build)
    verify_collapse_pin(root)
    collapse_contract_sha = production_collapse_contract_hash(root)

    # store + packet, loaded THROUGH the production contract (no wire rule)
    store, oracles_by_fixture = _build_provenance_store(root)
    packet = load_packet(root / PACKET_ROOT_REL, store, contract)
    if not packet.ok:
        _refuse(f"packet failed validation under the production contract: "
                f"{packet.failures}")
    # the packet index FILE identity is lineage-bound above; also pin the
    # canonical in-memory identity the runner machinery uses
    packet_canonical_sha = packet_index_sha256(packet)

    _check_population_coverage(contract, packet)

    fixture_ids = set(packet.s_family) | set(packet.analog)
    scorer_rules, scorer_sha = load_world_oracle_scorer(root, fixture_ids)

    plan = derive_call_plan(
        len(packet.probes["probe_fixture_ids"]),
        len(manifest["engine_roster"]),
        s_count=len(packet.s_family), analog_count=len(packet.analog))
    if plan.s_family_calls_branch + plan.analog_calls_branch \
            != PRIMARY_BOARD_CALLS \
            or plan.conditional_calls_branch != CONDITIONAL_BOARD_CALLS:
        _refuse("derived call plan is not the pinned 105/105 board")

    budget = _derive_budget(ledger)
    if budget["roster_total"] != c4b.APPROVED_BUDGET \
            or manifest["total_budget_tokens"] != c4b.APPROVED_BUDGET:
        _refuse("ledger/manifest budget does not match the approved total")

    if float(manifest["temperature"]) != c.CALIBRATION_TEMPERATURE \
            or float(manifest["collapse_diagnostic_temperature"]) \
            != c.COLLAPSE_DIAGNOSTIC_TEMPERATURE \
            or int(manifest["calibration_k"]) != c.CALIBRATION_K:
        _refuse("manifest K/temperature pins do not match the sealed "
                "contract values")

    return {"manifest": manifest, "sibling": sibling, "ledger": ledger,
            "packet": packet, "store": store,
            "oracles_by_fixture": oracles_by_fixture,
            "contract": contract, "check_hash": check_hash,
            "collapse_contract_sha": collapse_contract_sha,
            "packet_index_sha256": packet_index_sha,
            "packet_canonical_sha256": packet_canonical_sha,
            "scorer_rules": scorer_rules, "scorer_sha256": scorer_sha,
            "budget": budget}


def _branch_decoding(sibling: dict, branch: str) -> tuple[dict, str]:
    entry = sibling["branches"].get(branch)
    if not entry:
        _refuse(f"unknown roster branch {branch!r}")
    payload = entry.get("decoding_contract")
    if not payload:
        _refuse(f"sibling carries no {branch} decoding payload bytes: the "
                "decoding name alone is never authority")
    got = sha256_canon(payload)
    want = {"local": c4b.DECODING_LOCAL_SHA,
            "api": c4b.DECODING_API_SHA}[branch]
    if got != want or got != entry.get(
            "decoding_contract_canonical_sha256"):
        _refuse(f"{branch} decoding payload does not recompute to the "
                "co-pinned sibling hash")
    temps = payload.get("temperature_values", ())
    if c.CALIBRATION_TEMPERATURE not in temps \
            or c.COLLAPSE_DIAGNOSTIC_TEMPERATURE not in temps:
        _refuse(f"{branch} decoding contract does not admit both T=0.5 and "
                "T=0.7")
    if payload.get("output_ceiling") != OUTPUT_CEILING \
            or payload.get("seed") != "unsupported_unavailable" \
            or payload.get("top_p") != 1.0 or payload.get("tools"):
        _refuse(f"{branch} decoding contract violates the pinned surface")
    return payload, got


def authorize_calibration_contact(branch: str, root: Path = ROOT
                                  ) -> CalibrationContactAuthorization:
    """Mint full-board calibration authority for one pinned roster branch.
    Every binding recomputes from current bytes; refusal is the default."""
    if branch not in BRANCH_MODEL:
        _refuse(f"branch must be one of {sorted(BRANCH_MODEL)}; "
                f"got {branch!r}")
    loaded = _load_calibration_bindings(root)
    manifest, sibling = loaded["manifest"], loaded["sibling"]
    model_id = BRANCH_MODEL[branch]
    if model_id not in manifest["engine_roster"]:
        _refuse(f"{model_id!r} is not a pinned roster member")
    if sibling["branches"][branch].get("model_id") != model_id:
        _refuse(f"{branch} model_id does not match the pinned roster member")
    decoding_payload, decoding_sha = _branch_decoding(sibling, branch)
    p1 = _load_p1_prior(root, branch)
    detector = build_production_collapse_detector(root)
    validate_pinned_collapse_detector(detector)
    budget = loaded["budget"]
    return CalibrationContactAuthorization(
        packet_id=str(loaded["packet"].index["packet_id"]),
        packet_index_sha256=loaded["packet_index_sha256"],
        manifest_sha256=c4b.MANIFEST_CANONICAL_HASH,
        check_contract_sha256=loaded["check_hash"],
        collapse_detector_id=COLLAPSE_DETECTOR_ID,
        collapse_detector_contract_sha256=loaded["collapse_contract_sha"],
        model_id=model_id,
        decoding_contract_id=str(manifest["decoding_contract_id"]),
        foreground_template_sha256=foreground_template_hash(),
        part_i_spec_sha256=c.PART_I_SPEC_SHA256,
        branch=branch,
        pin_event_id=c4d.SUPERSEDING_EVENT_ID,
        manifest_file_sha256=c4b.MANIFEST_FILE_SHA,
        decoding_contract_sha256=decoding_sha,
        world_oracle_scorer_sha256=loaded["scorer_sha256"],
        p1_correction_result_sha256=p1["correction_sha256"],
        p1_sidecar_file_sha256=p1["sidecar_file_sha256"],
        p1_sidecar_canonical_sha256=p1["sidecar_canonical_sha256"],
        p1_original_result_sha256=p1["original_result_sha256"],
        p1_recovered=p1["recovered"],
        p1_n=p1["n"],
        p1_max_recoverable_rate=p1["max_recoverable_rate"],
        p1_ignorance_gate_verdict=VERDICT_IGNORANCE_GATE_PASS,
        calibration_k=c.CALIBRATION_K,
        temperature_primary=c.CALIBRATION_TEMPERATURE,
        temperature_diagnostic=c.COLLAPSE_DIAGNOSTIC_TEMPERATURE,
        probe_budget_spent_tokens=budget["probe_spent"],
        primary_budget_tokens=budget["primary"],
        conditional_budget_tokens=budget["conditional"],
        remaining_branch_budget_tokens=budget["remaining"],
        roster_total_budget_tokens=budget["roster_total"])


def _verify_authorization_bindings(auth: CalibrationContactAuthorization,
                                   root: Path) -> None:
    """Re-mint from current bytes and compare every field: forged or stale
    authority refuses before any output, transport, or lease exists."""
    fresh = authorize_calibration_contact(auth.branch, root)
    for f in fields(CalibrationContactAuthorization):
        if f.name == "consumed":
            continue
        if getattr(auth, f.name) != getattr(fresh, f.name):
            _refuse("calibration authorization bindings do not recompute "
                    f"from current bytes (forged or stale authority: "
                    f"{f.name})")


# ---------------------------------------------------------------------------
# Production transport (P0a shapes, fresh-session discipline).
# ---------------------------------------------------------------------------

def build_calibration_request_body(branch: str, model_id: str, prompt: str,
                                   temperature: float) -> dict:
    if temperature not in (c.CALIBRATION_TEMPERATURE,
                           c.COLLAPSE_DIAGNOSTIC_TEMPERATURE):
        _refuse(f"temperature {temperature} outside the pinned T=0.5/T=0.7 "
                "contract")
    if branch == BRANCH_LOCAL:
        return {"model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature, "top_p": 1.0,
                "max_tokens": OUTPUT_CEILING, "stream": False}
    if branch == BRANCH_API:
        body = {"model": model_id,
                "input": [{"role": "user", "content": prompt}],
                "reasoning": {"effort": "none"},
                "temperature": temperature,
                "max_output_tokens": OUTPUT_CEILING,
                "store": False, "stream": False}
        if API_TOP_P_INCLUDED:
            body["top_p"] = 1.0
        return body
    _refuse(f"unsupported branch {branch!r}")


def _extract_usage(branch: str, data: dict) -> tuple[int, int]:
    usage = (data or {}).get("usage") or {}
    if branch == BRANCH_LOCAL:
        prompt_t, completion_t = usage.get("prompt_tokens"), \
            usage.get("completion_tokens")
    else:
        prompt_t, completion_t = usage.get("input_tokens"), \
            usage.get("output_tokens")
    if not isinstance(prompt_t, int) or not isinstance(completion_t, int):
        raise TransportRefusal(
            f"transport failure on {branch}: response carries no usable "
            "token usage (deterministic cost accounting is mandatory)")
    return prompt_t, completion_t


class _ProductionCalibrationSession:
    """One fresh lease per invocation; single-use; unique isolation_id."""

    def __init__(self, branch: str, model_id: str, temperature: float,
                 isolation_id: str):
        self._branch = branch
        self._model_id = model_id
        self._temperature = temperature
        self.isolation_id = isolation_id
        self.used = False

    def __call__(self, prompt: str) -> EngineResult:
        if self.used:
            raise CalibrationContactError("session lease reused")
        self.used = True
        body = build_calibration_request_body(
            self._branch, self._model_id, prompt, self._temperature)
        if self._branch == BRANCH_LOCAL:
            url, api_key = f"{LOCAL_BASE}/chat/completions", None
        else:
            url = f"{API_BASE}/responses"
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise TransportRefusal(
                    "OPENAI_API_KEY required for api branch")
        result = _http_post(url, body, api_key=api_key)
        if result.get("error") or result.get("http_status") != 200:
            raise TransportRefusal(
                f"transport failure on {self._branch}: "
                f"status={result.get('http_status')} "
                f"error={result.get('error')}")
        text = _extract_text(result.get("data"))
        if not text:
            raise TransportRefusal(
                f"transport failure on {self._branch}: missing text output")
        prompt_t, completion_t = _extract_usage(self._branch,
                                                result.get("data"))
        return EngineResult(answer_text=text, prompt_tokens=prompt_t,
                            completion_tokens=completion_t)


class ProductionCalibrationSessionFactory:
    def __init__(self, branch: str, model_id: str):
        self._branch = branch
        self._model_id = model_id
        self._counter = 0

    def __call__(self, temperature: float) -> _ProductionCalibrationSession:
        self._counter += 1
        return _ProductionCalibrationSession(
            self._branch, self._model_id, temperature,
            isolation_id=f"cal-{self._branch}-{self._counter}")


# ---------------------------------------------------------------------------
# The production execution surface.
# ---------------------------------------------------------------------------

def _write_rows(path: Path, rows: list[dict]) -> str:
    with path.open("x", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")))
            fh.write("\n")
    return sha256_path(path)


def run_production_calibration_branch(
        authorization: CalibrationContactAuthorization,
        output_dir: Path,
        session_factory=None,
        root: Path = ROOT,
        run_id: str | None = None) -> dict:
    """Execute one authorized branch's full calibration board: 105 primary
    calls at T=0.5; the single conditional 105-call T=0.7 pass iff the
    pinned production detector says T=0.5 collapsed; the computed §5.3
    `engine_admission_verdict`. Probes are NEVER called — the P1 result is
    imported as a bound prior event. First transport failure terminates the
    branch; no retry, replacement, or later call."""
    auth = _reject_non_authority(authorization)
    try:
        _verify_authorization_bindings(auth, root)
        loaded = _load_calibration_bindings(root)
        packet, manifest = loaded["packet"], loaded["manifest"]
        store, contract = loaded["store"], loaded["contract"]
        # §10.2 grouping: stratum from the pinned packet bytes ("source"
        # for S-family fixtures), bound into the detect operation only
        stratum_map = {fid: "source" for fid in packet.s_family}
        stratum_map.update({fid: str(fx["stratum"])
                            for fid, fx in packet.analog.items()})
        detector = build_production_collapse_detector(
            root, stratum_of=stratum_map.get)
        validate_pinned_collapse_detector(detector)
        if detector.detector_id != auth.collapse_detector_id \
                or production_collapse_contract_hash(root) \
                != auth.collapse_detector_contract_sha256:
            _refuse("run-time collapse detector is not the authorized "
                    "pinned identity (an answer-only or substituted "
                    "detector refuses)")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        primary_path = output_dir / PRIMARY_ROWS_NAME
        t07_path = output_dir / T07_ROWS_NAME
        result_path = output_dir / RESULT_NAME
        for path in (primary_path, t07_path, result_path):
            if path.exists():
                _refuse(f"conflicting existing output {path.name}: "
                        "append-only surface refuses overwrite")

        if session_factory is None:
            session_factory = ProductionCalibrationSessionFactory(
                auth.branch, auth.model_id)
        oracle_score = make_world_oracle_score(loaded["scorer_rules"])
        run_id = run_id or f"efc_calibration_{auth.branch}"

        report = BranchReport()
        tracker = _SessionTracker(session_factory)
        report.phase_log.append("manifest_precommit")
        report.rows.append(make_row(
            f"{run_id}.run_config", "run_config", payload={
                "run_id": run_id,
                "surface": "production_calibration",
                "branch": auth.branch,
                "engine_backend": auth.model_id,
                "provider_cache": PROVIDER_CACHE_STATUS,
                "fresh_session_per_call": True,
            }))
        report.rows.append(make_row(
            f"{run_id}.contract_precommit", "contract_precommit", payload={
                "part_i_spec_hash": auth.part_i_spec_sha256,
                "surface": "production_calibration",
                "pin_event_id": auth.pin_event_id,
                "packet_id": auth.packet_id,
                "packet_index_sha256": auth.packet_index_sha256,
                "manifest_sha256": auth.manifest_sha256,
                "manifest_file_sha256": auth.manifest_file_sha256,
                "check_contract_sha256": auth.check_contract_sha256,
                "collapse_detector_id": auth.collapse_detector_id,
                "collapse_detector_contract_sha256":
                    auth.collapse_detector_contract_sha256,
                "decoding_contract_sha256": auth.decoding_contract_sha256,
                "world_oracle_scorer_sha256":
                    auth.world_oracle_scorer_sha256,
                "foreground_template_hash": auth.foreground_template_sha256,
                "p1_prior_event": {
                    "imported_not_rerun": True,
                    "correction_result_sha256":
                        auth.p1_correction_result_sha256,
                    "sidecar_canonical_sha256":
                        auth.p1_sidecar_canonical_sha256,
                    "recovered": auth.p1_recovered,
                    "n": auth.p1_n,
                    "ignorance_gate_verdict":
                        auth.p1_ignorance_gate_verdict,
                },
            }))

        # phase: ignorance probes — IMPORTED prior event, zero new calls.
        report.phase_log.append("ignorance_probes_imported_p1")
        p1 = _load_p1_prior(root, auth.branch)
        report.probe_sidecar = list(p1["sidecar_rows"])
        report.probe_sidecar_sha256 = p1["sidecar_canonical_sha256"]
        report.probe_calls = 0    # NEW probe calls this surface makes
        report.ignorance = IgnoranceProbeResult(
            recovered=p1["recovered"], n=p1["n"],
            max_recoverable_rate=p1["max_recoverable_rate"])

        collapsed_t05: bool | None = None
        collapsed_t07: bool | None = None
        try:
            report.phase_log.append("primary_board")
            _run_board(packet, tracker, _OnceGuard("primary_board"), report,
                       report.runs, report.rows, oracle_score, store,
                       contract, c.CALIBRATION_TEMPERATURE)

            collapsed_t05 = detector.detect(report.runs)
            if collapsed_t05:
                report.phase_log.append("collapse_pass")
                report.collapse_rows.append(make_row(
                    f"{T07_NAMESPACE}{run_id}.run_config", "run_config",
                    payload={"run_id": f"{T07_NAMESPACE}{run_id}",
                             "surface": "production_calibration",
                             "branch": auth.branch,
                             "engine_backend": auth.model_id,
                             "provider_cache": PROVIDER_CACHE_STATUS,
                             "fresh_session_per_call": True,
                             "temperature":
                                 c.COLLAPSE_DIAGNOSTIC_TEMPERATURE}))
                _run_board(packet, tracker, _OnceGuard("collapse_pass"),
                           report, report.collapse_runs,
                           report.collapse_rows, oracle_score, store,
                           contract, c.COLLAPSE_DIAGNOSTIC_TEMPERATURE,
                           event_namespace=T07_NAMESPACE)
                report.collapse_rows_sha256 = _rows_sha256(
                    report.collapse_rows)
                collapsed_t07 = detector.detect(report.collapse_runs)
        except _BranchRefused:
            report.status = STATUS_BRANCH_REFUSED_TRANSPORT
            report.eligible_for_planning = False
            emit_admission_verdict(report, packet, manifest, run_id)
            return _persist_branch(auth, report, output_dir, run_id)

        expected = PRIMARY_BOARD_CALLS \
            + (CONDITIONAL_BOARD_CALLS if report.collapse_runs else 0)
        if report.invocations != expected \
                or report.invocations > CEILING_CALLS_PER_BRANCH:
            raise RunnerContractError(
                f"invocation count {report.invocations} != derived plan "
                f"{expected} (never exceed {CEILING_CALLS_PER_BRANCH} "
                "calibration calls per branch after the completed probes)")

        report.status = STATUS_COMPLETED
        report.eligible_for_planning = True
        report.s_band = _s_band(packet, report.runs)
        report.collapse = CollapseState(collapsed_at_t05=collapsed_t05,
                                        collapsed_at_t07=collapsed_t07)
        emit_admission_verdict(report, packet, manifest, run_id)
        return _persist_branch(auth, report, output_dir, run_id)
    finally:
        auth.mark_consumed()


def _persist_branch(auth: CalibrationContactAuthorization,
                    report: BranchReport, output_dir: Path,
                    run_id: str) -> dict:
    """Append-only evidence: §13 rows only (answer plaintext is excluded by
    the row contract — hashes and token counts, never text)."""
    primary_sha = _write_rows(output_dir / PRIMARY_ROWS_NAME, report.rows)
    t07_sha = None
    if report.collapse_rows:
        t07_sha = _write_rows(output_dir / T07_ROWS_NAME,
                              report.collapse_rows)
    verdict = (report.admission_verdict_row or {}).get("payload", {})
    result = {
        "schema_version": "efc_p2_calibration_branch_result_v1",
        "branch": auth.branch,
        "model_id": auth.model_id,
        "pin_event_id": auth.pin_event_id,
        "run_id": run_id,
        "status": report.status,
        "invocations": report.invocations,
        "new_probe_calls": report.probe_calls,
        "p1_prior_imported": True,
        "engine_admission_verdict": verdict.get("verdict"),
        "verdict_reasons": verdict.get("reasons"),
        "s_band": (report.s_band.__dict__ if report.s_band else None),
        "ignorance_prior": {
            "recovered": auth.p1_recovered, "n": auth.p1_n,
            "max_recoverable_rate": auth.p1_max_recoverable_rate,
            "sidecar_canonical_sha256": auth.p1_sidecar_canonical_sha256,
        },
        "collapse": ({"collapsed_at_t05": report.collapse.collapsed_at_t05,
                      "collapsed_at_t07": report.collapse.collapsed_at_t07}
                     if report.collapse else None),
        "primary_rows_sha256": primary_sha,
        "t07_rows_sha256": t07_sha,
        "probe_sidecar_canonical_sha256": report.probe_sidecar_sha256,
        "provider_cache": report.provider_cache,
        "refused": list(report.refused),
        "calibration_outcomes_are": "admission diagnostics only (§6); "
                                    "never mechanism evidence",
    }
    (output_dir / RESULT_NAME).write_text(
        json.dumps(result, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    result["result_sha256"] = sha256_path(output_dir / RESULT_NAME)
    return result


# ---------------------------------------------------------------------------
# Pre-contact implementation report + CLI.
# ---------------------------------------------------------------------------

def implementation_report_payload(root: Path = ROOT) -> dict:
    from harness.efc_collapse_production import COLLAPSE_PIN_REL
    module_path = root / MODULE_REL
    collapse_module = root / "harness/efc_collapse_production.py"
    tests = {
        "tests/test_efc_collapse_production.py":
            sha256_path(root / "tests/test_efc_collapse_production.py"),
        "tests/test_efc_calibration_contact.py":
            sha256_path(root / "tests/test_efc_calibration_contact.py"),
    }
    pin_path = root / COLLAPSE_PIN_REL
    return {
        "schema_version": "efc_p2_calibration_contact_report_v1",
        "assignment": "P2 production calibration authority and collapse "
                      "detector (pre-contact)",
        "seat": "claude/fable-5",
        "active_pin_event_id": c4d.SUPERSEDING_EVENT_ID,
        "module_sha256": {MODULE_REL: sha256_path(module_path),
                          "harness/efc_collapse_production.py":
                              sha256_path(collapse_module)},
        "modified_shared_modules_sha256": {
            "harness/efc_controller.py":
                sha256_path(root / "harness/efc_controller.py"),
            "harness/efc_packet.py":
                sha256_path(root / "harness/efc_packet.py"),
        },
        "test_sha256": tests,
        "collapse_contract_pin": {
            "path": COLLAPSE_PIN_REL,
            "sha256": (sha256_path(pin_path) if pin_path.is_file()
                       else None),
            "detector_contract_sha256":
                production_collapse_contract_hash(root),
        },
        "check_contract_sha256": CHECK_CONTRACT_SHA,
        "structural_findings_blocking_contact": [
            {"finding": "no pinned production world-oracle answer scorer",
             "expected_artifact": WORLD_ORACLE_SCORER_REL,
             "expected_schema": WORLD_ORACLE_SCORER_SCHEMA,
             "consequence": "authorize_calibration_contact refuses on the "
                            "real tree until the scorer is authored and "
                            "cold-reviewed under a separate ruling"},
            {"finding": "population bindings missing for irrelevant-stratum "
                        "fixtures under A_always_check",
             "missing_fixture_ids": ["ir-01", "ir-02", "ir-03", "ir-04",
                                     "ir-05"],
             "consequence": "authority refuses at mint; extending "
                            "structured_inputs_v1 is pinned-content work "
                            "requiring a separate ruling"},
        ],
        "future_contact_commands": [
            {"command": ("python3 -m harness.efc_calibration_contact "
                         "--contact --branch local --output-dir <dir>"),
             "max_real_calls": CEILING_CALLS_PER_BRANCH,
             "unconditional_calls": PRIMARY_BOARD_CALLS,
             "conditional_calls": CONDITIONAL_BOARD_CALLS,
             "condition": "T=0.7 pass only if the pinned detector says "
                          "T=0.5 collapsed"},
            {"command": ("python3 -m harness.efc_calibration_contact "
                         "--contact --branch api --output-dir <dir>"),
             "max_real_calls": CEILING_CALLS_PER_BRANCH,
             "unconditional_calls": PRIMARY_BOARD_CALLS,
             "conditional_calls": CONDITIONAL_BOARD_CALLS,
             "condition": "T=0.7 pass only if the pinned detector says "
                          "T=0.5 collapsed"},
        ],
        "roster_branch_order": list(ROSTER_BRANCH_ORDER),
        "probe_policy": "P1 result imported as bound prior event; probes "
                        "are never rerun by this surface",
        "provider_cache": PROVIDER_CACHE_STATUS,
        "disclosure": {
            "engines_contacted": 0, "listing_calls": 0, "probes_run": 0,
            "network_calls": 0, "real_inference_calls": 0,
            "held_out_fixtures_authored": 0,
        },
        "authorizes_calibration_contact": False,
    }


def write_implementation_report(root: Path = ROOT) -> dict:
    payload = implementation_report_payload(root)
    path = root / P2_REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")
    payload["report_path"] = P2_REPORT_REL
    payload["report_sha256"] = sha256_path(path)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness.efc_calibration_contact",
        description="Production calibration surface (offline by default)")
    parser.add_argument("--write-collapse-pin", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--contact", action="store_true",
                        help="run one authorized branch's calibration board")
    parser.add_argument("--branch", choices=[BRANCH_LOCAL, BRANCH_API])
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.write_collapse_pin and not args.contact:
            from harness.efc_collapse_production import write_collapse_pin
            print(json.dumps(write_collapse_pin(), indent=1))
            return 0
        if args.write_report and not args.contact:
            print(json.dumps(write_implementation_report(), indent=1))
            return 0
        if args.contact:
            if not args.branch or not args.output_dir:
                parser.print_usage(sys.stderr)
                print("refused: --contact requires --branch and "
                      "--output-dir", file=sys.stderr)
                return 2
            auth = authorize_calibration_contact(args.branch, ROOT)
            result = run_production_calibration_branch(
                auth, args.output_dir)
            print(json.dumps(result, indent=1))
            return 0
    except (CalibrationContactError, RunnerContractError,
            TransportRefusal, ValueError) as exc:
        print(json.dumps({"refused": str(exc)}, indent=1))
        return 1

    parser.print_usage(sys.stderr)
    print("refused: an explicit mode (--write-collapse-pin, --write-report, "
          "or --contact) is required", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
