"""Phase C4 offline manifest conformance and exact budget derivation.

Consumes ONLY existing, reviewed on-disk artifacts: the C2 packet
(episodes/efc_calibration, hash-verified through its own index), the C2 world
oracle store, the R1/R2 roster artifacts (corpus/efc_calibration/roster), the
production comparison artifacts (corpus/efc_calibration/comparison + the C3
integration artifact), and the pinned §5.2/§10 constants. It contacts no
engine, performs no listing, runs no probe, fetches nothing, and commits
nothing. Every populated manifest field is derived from one of those
artifacts; where a required production identity cannot be derived, a typed
blocker is emitted instead (design §11 — never an invented value).

Produces, all CANDIDATE / pre-pin (corpus/efc_calibration/authoring_c4/):

  - C4_candidate_calibration_manifest.json  — the closed §5.2 schema, every
    placeholder replaced with an evidence-backed value; NOT a pin;
  - roster_decoding_pin_candidate.json      — the branch-specific R2 decoding
    payloads and hashes the single closed `decoding_contract_id` field
    cannot carry; sibling to the manifest, awaiting the same approval;
  - budget_derivation_ledger.json           — one row per ceiling call with
    the exact rendered-prompt bound; `total_budget_tokens` recomputes from
    the rows alone;
  - c4_conformance_report.json              — checks, lineage hashes, typed
    blockers, zero-network disclosure.

Budget rule (assignment + design §9): for each of the derived 450 ceiling
calls, per-call total = exact prompt upper bound (canonical tokenizer over
the actual rendered text, `harness.efc_renderer.canonical_tokens`) + 2048
completion-request ceiling (both branches, probes included, per the frozen
R2 surface) + 512 controller source-read bound (§10.1). The ≤256
check-output cap sizes evidence already inside the prompt envelope and is
never added again. A conditional T=0.7 call uses the same prompt bound as
its T=0.5 counterpart; probes are never repeated conditionally.

Branch prompt-bound identity: both R2 contracts transport exactly one
stateless user message whose content is the rendered prompt string — no
system prompt, no tools, no steering fields (local: chat.completions single
user message, `system_prompt: false`, `tools: false`; API: responses
stateless text input, `tools: false`, `reasoning_effort: "none"`). The
renderer is branch-independent, so per-call prompt bounds are identical
across branches and the roster total is exactly twice the branch total.

The comparison executor used here to render check evidence for the budget is
a WIRE-ONLY lookup of the authored expected verdicts (resolution A), used
solely to obtain the exact evidence text lengths; the production rule's
outputs agree with it on all 15 dispositive rows (C3 integration artifact)
and the rendered token count is verdict-invariant. It mints nothing.

Run:  python3 -m harness.efc_author_c4
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from harness import efc_contracts as c
from harness.efc_artifacts import predicate_contract_hash
from harness.efc_check import (ProvenanceRecord, ProvenanceStore,
                               WireComparisonRule, check_adapter_contract_hash,
                               run_scope_provenance_check)
from harness.efc_compare_production import (build_production_contract,
                                            production_check_contract_hash)
from harness.efc_controller import controller_contract_hash
from harness.efc_manifest import (check_calibration_manifest, manifest_hash,
                                  population_choice_canonical)
from harness.efc_packet import derive_call_plan, load_packet
from harness.efc_renderer import (build_foreground, canonical_tokens,
                                  foreground_template_hash,
                                  renderer_contract_hash)
from harness.efc_runner import runner_contract_hash

ROOT = Path(__file__).resolve().parents[1]
PACKET_ROOT = ROOT / "episodes/efc_calibration"
ORACLE_ROOT = ROOT / "corpus/efc_calibration/oracle"
ROSTER_ROOT = ROOT / "corpus/efc_calibration/roster"
C2_ROOT = ROOT / "corpus/efc_calibration/authoring_c2"
C4_ROOT = ROOT / "corpus/efc_calibration/authoring_c4"

# frozen decoding surface for the budget (assignment; R2-verified ceilings)
COMPLETION_REQUEST_CEILING = 2048
CONTROLLER_SOURCE_READ_BOUND = c.MAX_CONTROLLER_SOURCE_READ_TOKENS  # 512

# expected R2 identities (Sol's R2 close ruling; re-verified below against
# the artifact bytes, never trusted from this constant alone)
EXPECTED_LOCAL_MODEL = "openai/gpt-oss-20b"
EXPECTED_API_MODEL = "gpt-5.4-2026-03-05"

# lanes/legs on which a named check renders evidence (mirror of the frozen
# controller policy — asserted against controller semantics by tests)
_CHECKING = {"C_controlled_check": "trigger", "A_always_check": "always",
             "S1_relevant_check": "always"}
_PLACEBO = {"P_placebo": "trigger", "S2_placebo": "always"}


class C4DerivationError(ValueError):
    """A required identity or check failed. Fail-closed; never patched."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json_bytes(payload) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=1).encode("utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# packet + oracle store (hash-verified reads only)
# ---------------------------------------------------------------------------

def load_verified_packet_files() -> tuple[dict, dict[str, dict], dict]:
    """Read the packet through its index, re-verifying every entry and
    sibling hash before use. Returns (index, {entry_id: payload}, sibling
    hash map)."""
    index = load_json(PACKET_ROOT / "packet_index.json")
    payloads: dict[str, dict] = {}
    for entry in index["entries"]:
        path = PACKET_ROOT / entry["path"]
        data = path.read_bytes()
        if sha256_bytes(data) != entry["sha256"]:
            raise C4DerivationError(f"packet entry {entry['id']}: bytes do "
                                    "not match the index hash")
        payloads[entry["id"]] = json.loads(data.decode("utf-8"))
    siblings = {}
    for name, sib in index["siblings"].items():
        path = PACKET_ROOT / sib["path"]
        if sha256_path(path) != sib["sha256"]:
            raise C4DerivationError(f"packet sibling {name}: bytes do not "
                                    "match the index hash")
        siblings[name] = sib["sha256"]
    return index, payloads, siblings


def load_oracles() -> dict[str, dict]:
    oracles = {}
    for path in sorted(ORACLE_ROOT.glob("*.json")):
        if path.name == "probe_answer_key.json":
            continue
        oracles[path.stem] = {"payload": load_json(path),
                              "sha256": sha256_path(path)}
    return oracles


# ---------------------------------------------------------------------------
# R1/R2 roster + decoding surface
# ---------------------------------------------------------------------------

def load_roster_surface() -> dict:
    r1_path = ROSTER_ROOT / "roster_enumeration_r1.json"
    r2_path = ROSTER_ROOT / "decoding_surface_r2.json"
    r1, r2 = load_json(r1_path), load_json(r2_path)
    surface = {"r1_artifact_sha256": sha256_path(r1_path),
               "r2_artifact_sha256": sha256_path(r2_path),
               "branches": {}}
    for branch in ("local", "api"):
        entry = r2["branches"][branch]
        contract = entry["contract"]
        recomputed = c.sha256_utf8(json.dumps(contract, sort_keys=True,
                                              separators=(",", ":")))
        if recomputed != entry["decoding_contract_canonical_sha256"]:
            raise C4DerivationError(
                f"{branch}: decoding contract payload does not recompute to "
                "its recorded canonical hash")
        if entry["verdict"] != "pass":
            raise C4DerivationError(f"{branch}: R2 verdict is not pass")
        if contract["output_ceiling"] != COMPLETION_REQUEST_CEILING:
            raise C4DerivationError(f"{branch}: R2 output ceiling != "
                                    f"{COMPLETION_REQUEST_CEILING}")
        if sorted(contract["temperature_values"]) != [
                c.CALIBRATION_TEMPERATURE, c.COLLAPSE_DIAGNOSTIC_TEMPERATURE]:
            raise C4DerivationError(f"{branch}: R2 temperatures are not the "
                                    "pinned §10.2 pair")
        if contract["seed"] != "unsupported_unavailable":
            raise C4DerivationError(f"{branch}: seed availability changed")
        surface["branches"][branch] = {
            "model_id": contract["model_id"],
            "contract": contract,
            "decoding_contract_canonical_sha256":
                entry["decoding_contract_canonical_sha256"],
        }
    if surface["branches"]["local"]["model_id"] != EXPECTED_LOCAL_MODEL \
            or surface["branches"]["api"]["model_id"] != EXPECTED_API_MODEL:
        raise C4DerivationError("R2 model ids differ from the R2 close ruling")
    # branch prompt-bound identity proof (module docstring): one stateless
    # user message, no system prompt, no tools, on both branches
    local, api = (surface["branches"]["local"]["contract"],
                  surface["branches"]["api"]["contract"])
    if not (local["stateless_single_user_message"] and not local["tools"]
            and not local["system_prompt"]
            and api["stateless_text_input"] and not api["tools"]
            and api["reasoning_effort"] == "none"):
        raise C4DerivationError(
            "R2 wrappers are not both bare single-user-message transports; "
            "branch-specific prompt bounds would be required")
    return surface


def decoding_contract_id(surface: dict) -> str:
    """One compact id naming the R2-verified pair. The full branch payloads
    live in the pin sibling; this id binds the manifest to them by hash
    prefix. Naming only — it adds no evidence beyond R2."""
    local8 = surface["branches"]["local"][
        "decoding_contract_canonical_sha256"][:8]
    api8 = surface["branches"]["api"][
        "decoding_contract_canonical_sha256"][:8]
    return f"efc-decoding-r2-local-{local8}-api-{api8}"


# ---------------------------------------------------------------------------
# exact per-call budget derivation
# ---------------------------------------------------------------------------

def fixture_render_view(fixture: dict) -> dict:
    return {k: v for k, v in fixture.items()
            if k not in ("shape", "entity_keys")}


def derive_budget_rows(payloads: dict[str, dict],
                       oracles: dict[str, dict]) -> tuple[list[dict], dict]:
    """One row per ceiling call for ONE branch. Prompt bounds are the exact
    canonical token counts of the actually rendered text."""
    store = ProvenanceStore([ProvenanceRecord(
        oracle_id=o["payload"]["oracle_id"],
        source_reference=o["payload"]["source_reference"],
        authoritative_scope=o["payload"]["authoritative_scope"],
        cited_text=o["payload"]["cited_text"])
        for o in oracles.values()])
    verdict_by_scope = {o["payload"]["authoritative_scope"]:
                        o["payload"]["expected_scope_matches"]
                        for o in oracles.values()}
    if len(verdict_by_scope) != len(oracles):
        raise C4DerivationError("authoritative scopes are not unique")
    rule_id = "efc_c4_budget_lookup"
    rule = WireComparisonRule(
        rule_id=rule_id,
        contract={"rule_id": rule_id, "wire_only": True,
                  "semantics": ("budget-derivation-only lookup of the "
                                "authored expected verdicts; used solely to "
                                "render exact evidence text lengths; the "
                                "rendered token count is verdict-invariant; "
                                "never a production comparison rule "
                                "(resolution A)")},
        compare=lambda auth, dec: verdict_by_scope[auth])

    probe_contract = payloads["ignorance-probe-contract"]
    fixtures = {tid: p for tid, p in payloads.items()
                if tid.startswith(("sf-", "mm-", "mc-", "ir-"))}
    placebos = {p["placebo_for"]: p for pid, p in payloads.items()
                if pid.startswith("pb-")}

    rows: list[dict] = []

    def add(call_id: str, category: str, fixture_id: str, lane: str,
            prompt_text: str, conditional: bool) -> None:
        prompt_tokens = len(canonical_tokens(prompt_text))
        rows.append({
            "call_id": call_id,
            "category": category,
            "fixture_id": fixture_id,
            "lane": lane,
            "temperature": (c.COLLAPSE_DIAGNOSTIC_TEMPERATURE if conditional
                            else c.CALIBRATION_TEMPERATURE),
            "conditional": conditional,
            "prompt_tokens": prompt_tokens,
            "completion_request_ceiling": COMPLETION_REQUEST_CEILING,
            "controller_source_read_bound": CONTROLLER_SOURCE_READ_BOUND,
            "per_call_total": (prompt_tokens + COMPLETION_REQUEST_CEILING
                               + CONTROLLER_SOURCE_READ_BOUND),
        })

    # probes: primary only, never conditional (§10.5)
    for probe_id in probe_contract["probe_fixture_ids"]:
        add(f"probe.{probe_id}", "probe", probe_id, "ignorance_probe",
            probe_contract["probe_texts"][probe_id], conditional=False)

    # board rows, shared between the primary pass and the conditional T=0.7
    # pass (same prompt bound by assignment/§10.2)
    board: list[tuple[str, str, str, str]] = []  # (category, fid, lane, text)

    from harness.efc_renderer import render_prompt

    def board_prompt(fixture: dict, lane: str) -> str:
        view = fixture_render_view(fixture)
        foreground = build_foreground(view)
        fires = foreground.trigger_fires
        evidence_text = None
        if lane in _CHECKING and (_CHECKING[lane] == "always" or fires):
            evidence = run_scope_provenance_check(
                store, str(fixture["source_reference"]),
                str(fixture["decision_scope"]), rule)
            evidence_text = evidence.rendered()
        elif lane in _PLACEBO and (_PLACEBO[lane] == "always" or fires):
            evidence_text = placebos[fixture["task_id"]]["text"]
        return render_prompt(foreground, lane, evidence_text)

    s_family = sorted(t for t in fixtures if t.startswith("sf-"))
    analog = sorted(t for t in fixtures if not t.startswith("sf-"))
    for fid in s_family:
        for leg in c.SOURCE_LEGS:
            board.append(("s_family", fid, leg,
                          board_prompt(fixtures[fid], leg)))
    for fid in analog:
        for lane in c.LANES:
            board.append(("analog", fid, lane,
                          board_prompt(fixtures[fid], lane)))

    for category, fid, lane, text in board:
        add(f"primary.{fid}.{lane}", category, fid, lane, text,
            conditional=False)
    for category, fid, lane, text in board:
        add(f"conditional_t07.{fid}.{lane}", f"conditional_{category}", fid,
            lane, text, conditional=True)

    totals = {
        "probe_calls": sum(1 for r in rows if r["category"] == "probe"),
        "s_family_calls": sum(1 for r in rows
                              if r["category"] == "s_family"),
        "analog_calls": sum(1 for r in rows if r["category"] == "analog"),
        "conditional_calls": sum(1 for r in rows if r["conditional"]),
        "branch_ceiling_calls": len(rows),
        "branch_prompt_tokens": sum(r["prompt_tokens"] for r in rows),
        "branch_total_tokens": sum(r["per_call_total"] for r in rows),
    }
    return rows, totals


# ---------------------------------------------------------------------------
# main derivation
# ---------------------------------------------------------------------------

def main() -> int:
    report: dict = {
        "phase": "C4",
        "assignment": ("offline manifest conformance and exact budget "
                       "derivation — candidate, pre-pin, pre-approval"),
        "checks": {}, "blockers": [], "failures": []}

    # ---- verified inputs ---------------------------------------------------
    index, payloads, sibling_hashes = load_verified_packet_files()
    oracles = load_oracles()
    surface = load_roster_surface()
    report["checks"]["packet_hash_verification"] = (
        f"{len(payloads)} entries + {len(sibling_hashes)} siblings match "
        "packet_index.json")
    report["checks"]["roster_r2_contract_match"] = {
        "local": surface["branches"]["local"][
            "decoding_contract_canonical_sha256"],
        "api": surface["branches"]["api"][
            "decoding_contract_canonical_sha256"],
        "recomputed_from_payload_bytes": True,
        "output_ceiling_both_branches": COMPLETION_REQUEST_CEILING,
        "seed": "unsupported_unavailable (disclosed)",
    }

    # ---- production check-contract identity (recomputed, never copied) ----
    adapter_hash = check_adapter_contract_hash()
    contract = build_production_contract()
    check_hash = production_check_contract_hash(contract, adapter_hash)
    integration = load_json(C2_ROOT / "production_comparison_integration.json")
    if integration["candidate_check_contract_hash"] != check_hash:
        raise C4DerivationError(
            "recomputed production check contract hash differs from the C3 "
            "integration artifact")
    if not (integration["dispositive_row_count"] == 15
            and integration["oracle_agreement_count"] == 15):
        raise C4DerivationError(
            "production rule does not agree with the authored verdicts on "
            "all 15 dispositive rows")
    report["checks"]["check_contract_recomputation"] = {
        "candidate_check_contract_hash": check_hash,
        "adapter_contract_sha256": adapter_hash,
        "oracle_agreement": "15/15 (C3 integration artifact, re-read)",
    }

    # ---- exact call plan ----------------------------------------------------
    probe_ids = payloads["ignorance-probe-contract"]["probe_fixture_ids"]
    plan = derive_call_plan(len(probe_ids), 2)
    expected_plan = {"probe_calls_branch": 15, "s_family_calls_branch": 15,
                     "analog_calls_branch": 90, "primary_calls_branch": 120,
                     "conditional_calls_branch": 105,
                     "ceiling_calls_branch": 225,
                     "roster_ceiling_total": 450}
    derived_plan = {
        "probe_calls_branch": plan.probe_calls_branch,
        "s_family_calls_branch": plan.s_family_calls_branch,
        "analog_calls_branch": plan.analog_calls_branch,
        "primary_calls_branch": plan.primary_calls_branch,
        "conditional_calls_branch": plan.conditional_calls_branch,
        "ceiling_calls_branch": plan.ceiling_calls_branch,
        "roster_ceiling_total": plan.roster_ceiling_total,
    }
    if derived_plan != expected_plan:
        raise C4DerivationError(f"derived call plan {derived_plan} != "
                                f"assignment plan {expected_plan}")
    report["checks"]["derived_call_plan"] = derived_plan

    # ---- exact budget --------------------------------------------------------
    rows, totals = derive_budget_rows(payloads, oracles)
    if totals["branch_ceiling_calls"] != plan.ceiling_calls_branch:
        raise C4DerivationError("budget rows do not match the derived plan")
    for r in rows:
        if r["per_call_total"] != (r["prompt_tokens"]
                                   + COMPLETION_REQUEST_CEILING
                                   + CONTROLLER_SOURCE_READ_BOUND):
            raise C4DerivationError(f"{r['call_id']}: per-call total does "
                                    "not recompute (double count?)")
    total_budget_tokens = 2 * totals["branch_total_tokens"]
    report["checks"]["budget_recomputation"] = {
        **totals,
        "prompt_bound_unit": ("canonical whitespace tokens "
                              "(harness.efc_renderer.canonical_tokens) over "
                              "the exact rendered text; completion and "
                              "controller terms are the frozen request/§10.1 "
                              "contract caps"),
        "branch_identity_proof": ("both R2 wrappers transport one stateless "
                                  "user message with no system prompt and no "
                                  "tools; renderer output is branch-"
                                  "independent, so roster total = 2 x branch "
                                  "total"),
        "check_output_cap_not_double_counted": True,
        "total_budget_tokens": total_budget_tokens,
    }

    # ---- world oracles + fixtures from verified bytes ------------------------
    fixture_entries = [{"fixture_id": e["id"], "sha256": e["sha256"]}
                       for e in index["entries"]
                       if e["role"] in ("s_family", "analog")]
    oracle_rows = [{"oracle_id": o["payload"]["oracle_id"],
                    "timestamp": o["payload"]["retrieved_at_utc"],
                    "sha256": o["sha256"]}
                   for o in oracles.values()]
    if len(fixture_entries) != 20 or len(oracle_rows) != 20:
        raise C4DerivationError("expected exactly 20 fixtures and 20 oracles")

    # ---- population declaration byte match -----------------------------------
    declaration = load_json(C2_ROOT / "population_intent_declaration.json")
    population_region = declaration["population_region"]
    if (c.sha256_utf8(population_choice_canonical(population_region)
                      .decode("utf-8"))
            != declaration["canonical_serialization_sha256"]):
        raise C4DerivationError(
            "population declaration canonical hash does not recompute")
    report["checks"]["population_declaration_byte_match"] = {
        "canonical_serialization_sha256":
            declaration["canonical_serialization_sha256"],
        "manifest_region_is_byte_identical": True,
    }

    # ---- extractor identity (typed disclosure, not a blocker) ----------------
    extractor_module = ROOT / "harness/efc_trigger.py"
    extractor_hash = sha256_path(extractor_module)
    report["checks"]["extractor_identity_disclosure"] = (
        "extractor_hash is the sha256 of harness/efc_trigger.py source "
        "bytes: the repo's identity registry (efc_artifacts) defines the "
        "extractor's SEMANTIC identity as the predicate contract and keeps "
        "the module hash diagnostic; no distinct semantic extractor "
        "contract artifact exists, so the module-source identity is the "
        "only derivable non-synthetic value — flagged for cold review")

    # ---- candidate manifest ---------------------------------------------------
    manifest = {
        "part_i_spec_hash": c.PART_I_SPEC_SHA256,
        "engine_roster": [surface["branches"]["local"]["model_id"],
                          surface["branches"]["api"]["model_id"]],
        "model_id": surface["branches"]["api"]["model_id"],
        "decoding_contract_id": decoding_contract_id(surface),
        "renderer_id": "efc_renderer_v0",
        "foreground_template_hash": foreground_template_hash(),
        "calibration_fixtures": fixture_entries,
        "world_oracles": oracle_rows,
        "ignorance_probe_contract": {
            "probe_fixture_ids": list(probe_ids),
            "max_recoverable_rate":
                payloads["ignorance-probe-contract"]["max_recoverable_rate"]},
        "predicate_contract_hash": predicate_contract_hash(),
        "extractor_hash": extractor_hash,
        "check_contract_hash": check_hash,
        "generic_caution_text": c.GENERIC_CAUTION_TEXT,
        "generic_caution_sha256": c.GENERIC_CAUTION_SHA256,
        "offer_projection_text": c.OFFER_PROJECTION_TEXT,
        "offer_projection_sha256": c.OFFER_PROJECTION_SHA256,
        "calibration_k": c.CALIBRATION_K,
        "temperature": c.CALIBRATION_TEMPERATURE,
        "collapse_diagnostic_temperature": c.COLLAPSE_DIAGNOSTIC_TEMPERATURE,
        "stop_rule": c.STOP_RULE_ID,
        "n_max": c.N_MAX,
        "total_budget_tokens": total_budget_tokens,
        "population_region": population_region,
    }
    result = check_calibration_manifest(manifest)
    report["checks"]["manifest_machine_check"] = {
        "ok": result.ok,
        "failures": list(result.failures),
        "candidate_hash_NOT_A_PIN": result.manifest_hash,
    }
    if not result.ok:
        report["failures"].extend(result.failures)

    # ---- no placeholder/synthetic identity in production fields --------------
    manifest_bytes = json.dumps(manifest, sort_keys=True)
    placeholder_hits = [
        marker for marker in
        ("PENDING", "PLACEHOLDER", "synthetic",
         c.sha256_utf8("PENDING-PLACEHOLDER:predicate_contract_hash"),
         c.sha256_utf8("PENDING-PLACEHOLDER:extractor_hash"),
         c.sha256_utf8("PENDING-PLACEHOLDER:check_contract_hash(resolution A)"))
        if marker in manifest_bytes]
    if placeholder_hits:
        raise C4DerivationError(
            f"placeholder/synthetic markers in the candidate manifest: "
            f"{placeholder_hits}")
    report["checks"]["no_placeholder_identities"] = "clean"

    # ---- full packet load under the budget lookup rule -----------------------
    store = ProvenanceStore([ProvenanceRecord(
        oracle_id=o["payload"]["oracle_id"],
        source_reference=o["payload"]["source_reference"],
        authoritative_scope=o["payload"]["authoritative_scope"],
        cited_text=o["payload"]["cited_text"])
        for o in oracles.values()])
    verdicts = {o["payload"]["authoritative_scope"]:
                o["payload"]["expected_scope_matches"]
                for o in oracles.values()}
    rule = WireComparisonRule(
        rule_id="efc_c4_budget_lookup",
        contract={"rule_id": "efc_c4_budget_lookup", "wire_only": True,
                  "semantics": "see budget_derivation_ledger.json"},
        compare=lambda auth, dec: verdicts[auth])
    packet = load_packet(PACKET_ROOT, store, rule)
    report["checks"]["packet_loader"] = ("ok" if packet.ok
                                         else list(packet.failures))
    if not packet.ok:
        report["failures"].extend(packet.failures)

    # ---- lineage hashes --------------------------------------------------------
    lineage_paths = {
        "roster_enumeration_r1":
            "corpus/efc_calibration/roster/roster_enumeration_r1.json",
        "decoding_surface_r2":
            "corpus/efc_calibration/roster/decoding_surface_r2.json",
        "k4_promotion_identity_ledger":
            "corpus/efc_calibration/_acquisition/k4/promotion_identity_ledger.json",
        "g4_refetch_report":
            "corpus/efc_calibration/_acquisition/g4/refetch_report.json",
        "g4_identity_audit":
            "corpus/efc_calibration/_acquisition/g4/identity_audit.json",
        "packet_index": "episodes/efc_calibration/packet_index.json",
        "c2_check_report":
            "corpus/efc_calibration/authoring_c2/c2_check_report.json",
        "cold_semantic_review_kimi":
            "corpus/efc_calibration/authoring_c2/cold_semantic_review_kimi.json",
        "production_comparison_review_grok":
            "corpus/efc_calibration/authoring_c2/production_comparison_review_grok.json",
        "production_comparison_integration":
            "corpus/efc_calibration/authoring_c2/production_comparison_integration.json",
        "comparison_expectations_v1":
            "corpus/efc_calibration/authoring_c2/comparison_expectations_v1.json",
        "population_intent_declaration":
            "corpus/efc_calibration/authoring_c2/population_intent_declaration.json",
        "allocation": "corpus/efc_calibration/authoring_c2/allocation.json",
        "placebo_truth_verification":
            "corpus/efc_calibration/authoring_c2/placebo_truth_verification.json",
        "production_rule_v1":
            "corpus/efc_calibration/comparison/production_rule_v1.json",
        "structured_inputs_v1":
            "corpus/efc_calibration/comparison/structured_inputs_v1.json",
        "conformance_vectors_v1":
            "corpus/efc_calibration/comparison/conformance_vectors_v1.json",
    }
    report["lineage_sha256"] = {name: sha256_path(ROOT / rel)
                                for name, rel in lineage_paths.items()}
    report["lineage_sha256"]["exclusion_manifest"] = \
        sibling_hashes["exclusion_manifest"]
    report["contract_identities"] = {
        "renderer_contract_sha256": renderer_contract_hash(),
        "controller_contract_sha256": controller_contract_hash(),
        "runner_contract_sha256": runner_contract_hash(),
        "predicate_contract_sha256": predicate_contract_hash(),
        "planner_module_sha256_diagnostic":
            sha256_path(ROOT / "harness/efc_planner.py"),
        "intervals_module_sha256_diagnostic":
            sha256_path(ROOT / "harness/efc_intervals.py"),
    }

    # ---- typed blockers (approval gates, not derivation gaps) -----------------
    report["blockers"] = [
        {"id": "operator_roster_budget_approval",
         "blocking": True,
         "detail": ("dan must approve the exact two-model roster and "
                    f"total_budget_tokens={total_budget_tokens} in their "
                    "exact manifest form before any pin or contact")},
        {"id": "extractor_identity_layer",
         "blocking": False,
         "detail": ("extractor_hash carries the module-source identity of "
                    "harness/efc_trigger.py (no distinct semantic extractor "
                    "contract artifact exists); cold review should ratify or "
                    "demand a typed extractor contract before pin")},
        {"id": "decoding_contract_id_is_a_name",
         "blocking": False,
         "detail": ("the closed schema holds one decoding_contract_id; the "
                    "branch payloads and canonical hashes are pinned in "
                    "roster_decoding_pin_candidate.json, which must be "
                    "approved and pinned together with the manifest")},
        {"id": "license_binding_conformance_review",
         "blocking": False,
         "detail": ("carried forward from the C3 integration artifact: "
                    "typed license atoms and population bindings require "
                    "separate conformance review")},
    ]
    report["disclosure"] = {
        "engines_contacted": 0, "listing_calls": 0, "probes_run": 0,
        "network_calls": 0, "held_out_fixtures_authored": 0, "commits": 0,
        "manifest_status": "candidate_not_pinned",
    }

    # ---- write candidate artifacts --------------------------------------------
    C4_ROOT.mkdir(parents=True, exist_ok=True)
    (C4_ROOT / "C4_candidate_calibration_manifest.json").write_bytes(
        canonical_json_bytes(manifest))
    pin_sibling = {
        "schema_version": "efc_roster_decoding_pin_v1",
        "status": "candidate_not_pinned",
        "decoding_contract_id": decoding_contract_id(surface),
        "r1_artifact_sha256": surface["r1_artifact_sha256"],
        "r2_artifact_sha256": surface["r2_artifact_sha256"],
        "branches": {
            branch: {
                "model_id": b["model_id"],
                "decoding_contract": b["contract"],
                "decoding_contract_canonical_sha256":
                    b["decoding_contract_canonical_sha256"],
            } for branch, b in surface["branches"].items()},
        "probe_output_ceiling_note": (
            "ignorance probes use the same 2048 request ceiling as "
            "calibration calls in the operational budget — deliberately "
            "conservative; no second request contract is introduced"),
        "no_retries_or_replacement_calls": True,
        "seed": "unsupported_unavailable (disclosed)",
    }
    (C4_ROOT / "roster_decoding_pin_candidate.json").write_bytes(
        canonical_json_bytes(pin_sibling))
    ledger = {
        "schema_version": "efc_budget_derivation_ledger_v1",
        "status": "candidate_not_pinned",
        "derivation_rule": ("per ceiling call: exact rendered-prompt "
                            "canonical token count + 2048 completion request "
                            "ceiling + 512 controller source-read bound; "
                            "check-output <=256 cap sizes evidence inside "
                            "the prompt envelope, never added; conditional "
                            "T=0.7 rows reuse the primary prompt bound; "
                            "probes never conditional; roster total = 2 x "
                            "branch total (branch prompt-bound identity "
                            "proven from the R2 wrapper shapes)"),
        "per_branch_rows": rows,
        "totals": {**totals, "roster_total_budget_tokens":
                   2 * totals["branch_total_tokens"]},
    }
    (C4_ROOT / "budget_derivation_ledger.json").write_bytes(
        canonical_json_bytes(ledger))
    report["artifact_sha256"] = {
        "C4_candidate_calibration_manifest": sha256_path(
            C4_ROOT / "C4_candidate_calibration_manifest.json"),
        "roster_decoding_pin_candidate": sha256_path(
            C4_ROOT / "roster_decoding_pin_candidate.json"),
        "budget_derivation_ledger": sha256_path(
            C4_ROOT / "budget_derivation_ledger.json"),
    }
    report["candidate_manifest_hash_NOT_A_PIN"] = manifest_hash(manifest)
    report["total_budget_tokens"] = total_budget_tokens
    (C4_ROOT / "c4_conformance_report.json").write_bytes(
        canonical_json_bytes(report))

    ok = not report["failures"]
    print(json.dumps(report, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
