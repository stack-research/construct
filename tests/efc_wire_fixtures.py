"""Conspicuously fictional synthetic wire fixtures for the EFC machinery
tests. Disclosed wire material only (AGENTS.md standing rule): nothing here
is a software-provenance fact, a source, an oracle record, a comparison-rule
choice, or a plausible future calibration item, and nothing here may later
become calibration evidence. Every identifier is stamped fictional.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

from harness.efc_carrier import V0_PREDICATE_FEATURE_BINDINGS
from harness.efc_check import (ProvenanceRecord, ProvenanceStore,
                               WireComparisonRule)
from harness.efc_controller import EngineResult

FICTIONAL_POP = "wire-fictional-population-0"

_ISOLATION_COUNTER = itertools.count()


def _fict_hash(seed: str) -> str:
    return hashlib.sha256(f"fictional:{seed}".encode("utf-8")).hexdigest()


# --- injected fictional comparison rules (B1: the adapter carries, never
# chooses; these are test fixtures, not production rules) ---------------------

def token_cover_rule() -> WireComparisonRule:
    """Fictional wire rule A: decision-scope tokens covered by authoritative
    scope."""
    rule_id = "wire_fictional_token_cover"
    return WireComparisonRule(
        rule_id=rule_id,
        contract={"rule_id": rule_id, "fictional": True,
                  "semantics": "decision tokens subset of authoritative"},
        compare=lambda auth, dec: set(dec.split()) <= set(auth.split()))


def exact_equality_rule() -> WireComparisonRule:
    """Fictional wire rule B: byte equality — deliberately different
    semantics so tests can prove the adapter carries the injected rule."""
    rule_id = "wire_fictional_exact_equality"
    return WireComparisonRule(
        rule_id=rule_id,
        contract={"rule_id": rule_id, "fictional": True,
                  "semantics": "exact string equality"},
        compare=lambda auth, dec: auth == dec)


def _wire_lane_answer_collapse(runs) -> bool:
    """Conspicuously fictional wire collapse rule: every lane/leg group's
    answer realizations collapse to one. Test material only — the production
    rule must hash answer AND route realizations and is pending (resolution
    D)."""
    by_lane = {}
    for run in runs:
        digest = hashlib.sha256(run.answer_text.encode("utf-8")).hexdigest()
        by_lane.setdefault(run.lane, set()).add(digest)
    return bool(by_lane) and all(len(v) == 1 for v in by_lane.values())


def pinned_collapse_detector():
    """A pinned fictional §10.2 wire detector (resolution D machinery test
    material)."""
    from harness.efc_runner import PinnedCollapseDetector
    detector_id = "wire_fictional_lane_answer_collapse"
    return PinnedCollapseDetector(
        detector_id=detector_id,
        contract={"detector_id": detector_id, "fictional": True,
                  "semantics": "per-lane answer realization collapse "
                               "(answer-only; wire stand-in, never the "
                               "pending answer+route production rule)"},
        detect=_wire_lane_answer_collapse)


def fictional_source_ref(i: int) -> str:
    return f"wire://fictional/examplon-record-{i}"


def make_store(refs: list[str]) -> ProvenanceStore:
    records = []
    for i, ref in enumerate(refs):
        records.append(ProvenanceRecord(
            oracle_id=f"FICTIONAL-ORACLE-{i}",
            source_reference=ref,
            authoritative_scope=("fictional examplon deployments of the "
                                 "glimmer subsystem only"),
            cited_text=(f"Entirely fictional wire record {i}: the examplon "
                        "glimmer subsystem scope statement.")))
    return ProvenanceStore(records)


def default_store() -> ProvenanceStore:
    return make_store([fictional_source_ref(i) for i in range(30)])


def firing_fixture(task_id: str, ref: str, mismatch: bool) -> dict:
    scope = ("fictional examplon deployments of the glimmer subsystem"
             if not mismatch else
             "fictional examplon deployments of the UNRELATED sprocket subsystem")
    return {
        "task_id": task_id,
        "population_id": FICTIONAL_POP,
        "surface_text": (f"[FICTIONAL WIRE TASK {task_id}] A cited fictional "
                         "record is asserted to authorize a decision."),
        "assertion_basis_kind": "cited_source",
        "observation_boundary_present": False,
        "source_reference_present": True,
        "decision_scope_present": True,
        "source_reference": ref,
        "decision_scope": scope,
    }


def irrelevant_fixture(task_id: str, ref: str) -> dict:
    fixture = firing_fixture(task_id, ref, mismatch=False)
    fixture["observation_boundary_present"] = True  # canonical §8.5 shape
    return fixture


def mock_oracle(fixture: dict, answer_text: str) -> dict:
    return {"oracle_source": "wire_fictional", "passed": True}


def mock_probe_scorer(probe_id: str, answer_text: str) -> bool:
    """Fictional machine-scoring rule: nothing is ever 'recovered'."""
    return False


class MockSession:
    """One fresh stateless call; a second use fails the isolation contract.
    Each instance carries a unique `isolation_id` process handle unless the
    test forges one (item F)."""

    def __init__(self, temperature: float = 0.5, answer: str | None = None,
                 isolation_id: str | None = None):
        self.temperature = temperature
        self.used = False
        self._answer = answer
        self.isolation_id = (isolation_id if isolation_id is not None
                             else f"wire-iso-{next(_ISOLATION_COUNTER)}")

    def __call__(self, prompt: str) -> EngineResult:
        if self.used:
            raise AssertionError("mock session reused: not a fresh session")
        self.used = True
        answer = self._answer or (
            "fictional-wire-answer:"
            f"{hashlib.sha256(prompt.encode()).hexdigest()[:8]}")
        return EngineResult(answer_text=answer,
                            prompt_tokens=len(prompt.split()),
                            completion_tokens=7)


def mock_session_factory(temperature: float) -> MockSession:
    """Fresh varied-answer session per invocation."""
    return MockSession(temperature)


def constant_session_factory(collapse_at_t07: bool = True):
    """Sessions whose answer is constant regardless of prompt, to drive the
    §10.2 collapse path. If `collapse_at_t07` is False, T=0.7 sessions vary."""
    def factory(temperature: float) -> MockSession:
        if temperature >= 0.7 and not collapse_at_t07:
            return MockSession(temperature)
        return MockSession(temperature, answer="fictional-constant-answer")
    return factory


def synthetic_carrier_payload() -> dict:
    """§3.1-complete, conspicuously fictional, non-mintable (design §4.2)."""
    envelope = {
        "model_id": "wire-fictional-engine-0",
        "renderer_id": "efc_renderer_v0",
        "foreground_template_hash": _fict_hash("template"),
        "tool_contract_id": "wire-fictional-tool-contract",
        "decoding_contract_id": "wire-fictional-decoding",
        "controller_id": "efc_controller_v0",
        "predicate_contract_hash": _fict_hash("predicate"),
        "extractor_hash": _fict_hash("extractor"),
        "check_contract_hash": _fict_hash("check"),
        "engine_admission_packet_hash": _fict_hash("packet"),
        "source_family_hash": _fict_hash("source-family"),
        "target_population_hash": _fict_hash("population"),
        "per_invocation_cost_ceiling": 1024,
    }
    return {
        "synthetic": True,
        "non_mintable": True,
        "carrier": {
            "mechanism_id": "epistemic_frame_check",
            "mechanism_version": "v0",
            "predicate_contract_hash": _fict_hash("predicate"),
            "predicate_feature_bindings": dict(V0_PREDICATE_FEATURE_BINDINGS),
            "extractor_hash": _fict_hash("extractor"),
            "check_id": "scope_provenance_check_v0",
            "check_contract_hash": _fict_hash("check"),
            "warrant_event_ids": ["wire-fictional-warrant-0"],
            "warrant_result_hash": _fict_hash("warrant"),
            "validity_envelope": envelope,
            "status": "experimental_probationary",
            "per_invocation_cost_ceiling": 1024,
            "revision_scope_rules_hash": _fict_hash("revision-rules"),
            "retirement_rules_hash": _fict_hash("retirement-rules"),
        },
    }


def _placebo_payload(placebo_id: str, target: str, n: int) -> dict:
    return {
        "placebo_id": placebo_id, "placebo_for": target,
        "text": ("check_id: fictional_placebo source_reference: "
                 f"wire://fictional/disjoint-{n} cited_provenance: "
                 "Entirely fictional disjoint wire record about the "
                 "unrelated whistle registry. scope_matches: n/a pad pad"),
        "disjoint_reference": f"wire://fictional/disjoint-{n}",
        "entity_keys": [f"fictional-disjoint-entity-{n}"],
    }


def write_packet(root: Path) -> Path:
    """Write a structurally valid synthetic packet under `root` in the closed
    index shape (B2)."""
    root.mkdir(parents=True, exist_ok=True)
    entries = []

    def _write(rel: str, payload: dict, entry_id: str, role: str):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(payload, sort_keys=True).encode("utf-8")
        path.write_bytes(data)
        entries.append({"id": entry_id, "path": rel, "role": role,
                        "sha256": hashlib.sha256(data).hexdigest()})

    refs = [fictional_source_ref(i) for i in range(30)]
    # S-family: 3 mismatch / 2 commit, each with an S2 placebo
    for i in range(5):
        fx = firing_fixture(f"sf-{i:02d}", refs[i], mismatch=i < 3)
        fx["shape"] = "mismatch" if i < 3 else "commit"
        fx["entity_keys"] = ["examplon-glimmer"]
        _write(f"s_family/sf-{i:02d}.json", fx, f"sf-{i:02d}", "s_family")
        _write(f"placebo/pb-sf-{i:02d}.json",
               _placebo_payload(f"pb-sf-{i:02d}", f"sf-{i:02d}", i),
               f"pb-sf-{i:02d}", "placebo")
    # analog board: 5 per stratum; P placebos on trigger-matching strata only
    n = 5
    for j in range(5):
        for stratum, maker in (("match_mismatch",
                                lambda t, r: firing_fixture(t, r, True)),
                               ("match_commit",
                                lambda t, r: firing_fixture(t, r, False)),
                               ("irrelevant", irrelevant_fixture)):
            tid = f"{stratum[:2]}-{j:02d}-{stratum}"
            fx = maker(tid, refs[n]); n += 1
            fx["stratum"] = stratum
            fx["entity_keys"] = ["examplon-glimmer"]
            _write(f"analog/{tid}.json", fx, tid, "analog")
            if stratum != "irrelevant":
                _write(f"placebo/pb-{tid}.json",
                       _placebo_payload(f"pb-{tid}", tid, 100 + n),
                       f"pb-{tid}", "placebo")
    _write("probes/ignorance_probe_contract.json", {
        "probe_fixture_ids": ["probe-fictional-0", "probe-fictional-1"],
        "probe_texts": {
            "probe-fictional-0": "[FICTIONAL PROBE 0] What is the scope of "
                                 "the examplon whistle registry?",
            "probe-fictional-1": "[FICTIONAL PROBE 1] Name the fictional "
                                 "glimmer subsystem's deprecation state.",
        },
        "max_recoverable_rate": 0.2,
    }, "probe-contract", "probe_contract")
    _write("carrier/synthetic_carrier.json", synthetic_carrier_payload(),
           "synthetic-carrier", "carrier")
    siblings = {}
    for name, rel in (("exclusion_manifest", "exclusion/exclusion_manifest.json"),
                      ("difficulty_rationale", "difficulty_rationale.md"),
                      ("isolation_contract", "isolation_contract.md")):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        data = f"fictional wire sibling artifact: {name}\n".encode("utf-8")
        path.write_bytes(data)
        siblings[name] = {"path": rel,
                          "sha256": hashlib.sha256(data).hexdigest()}
    index = {"packet_id": "wire-fictional-packet-0", "entries": entries,
             "siblings": siblings}
    (root / "packet_index.json").write_text(json.dumps(index, indent=1))
    return root


def wire_manifest(packet) -> dict:
    """A structurally valid, conspicuously fictional §5.2 manifest bound to
    the given loaded packet — machinery test material only. Real manifest
    authoring belongs to other seats. Its check_contract_hash is a FICTIONAL
    placeholder: no production check contract exists (resolution A)."""
    from harness import efc_contracts as c
    from harness.efc_packet import derive_call_plan, derive_total_budget_tokens
    from harness.efc_renderer import RENDERER_ID, foreground_template_hash
    fixtures = [{"fixture_id": e["id"], "sha256": e["sha256"]}
                for e in packet.index["entries"]
                if e["role"] in ("s_family", "analog")]
    plan = derive_call_plan(len(packet.probes["probe_fixture_ids"]), 1)
    return {
        "part_i_spec_hash": c.PART_I_SPEC_SHA256,
        "engine_roster": ["wire-fictional-engine-0"],
        "model_id": "wire-fictional-engine-0",
        "decoding_contract_id": "wire-fictional-decoding-0",
        "renderer_id": RENDERER_ID,
        "foreground_template_hash": foreground_template_hash(),
        "calibration_fixtures": fixtures,
        "world_oracles": [{"oracle_id": "FICTIONAL-ORACLE-0",
                           "timestamp": "2026-07-12T00:00:00Z",
                           "sha256": hashlib.sha256(
                               b"fictional-oracle").hexdigest()}],
        "ignorance_probe_contract": {
            "probe_fixture_ids": list(packet.probes["probe_fixture_ids"]),
            "max_recoverable_rate": packet.probes["max_recoverable_rate"],
        },
        "predicate_contract_hash": hashlib.sha256(
            b"fictional-predicate").hexdigest(),
        "extractor_hash": hashlib.sha256(b"fictional-extractor").hexdigest(),
        "check_contract_hash": hashlib.sha256(
            b"wire-fictional-check-contract-placeholder").hexdigest(),
        "generic_caution_text": c.GENERIC_CAUTION_TEXT,
        "generic_caution_sha256": c.GENERIC_CAUTION_SHA256,
        "offer_projection_text": c.OFFER_PROJECTION_TEXT,
        "offer_projection_sha256": c.OFFER_PROJECTION_SHA256,
        "calibration_k": c.CALIBRATION_K,
        "temperature": c.CALIBRATION_TEMPERATURE,
        "collapse_diagnostic_temperature": c.COLLAPSE_DIAGNOSTIC_TEMPERATURE,
        "stop_rule": c.STOP_RULE_ID,
        "n_max": c.N_MAX,
        "total_budget_tokens": derive_total_budget_tokens(plan, 2000, 1000),
        "population_region": {"vertices": [
            {"match_mismatch": 0.5, "match_commit": 0.3, "irrelevant": 0.2},
            {"match_mismatch": 0.2, "match_commit": 0.3, "irrelevant": 0.5},
        ]},
    }


def rewrite_entry(root: Path, rel: str, payload: dict, entry_id: str) -> None:
    """Test helper: replace one packet file and fix its index hash so only
    the intended defect is visible."""
    data = json.dumps(payload, sort_keys=True).encode("utf-8")
    (root / rel).write_bytes(data)
    index_path = root / "packet_index.json"
    index = json.loads(index_path.read_text())
    for entry in index["entries"]:
        if entry["id"] == entry_id:
            entry["sha256"] = hashlib.sha256(data).hexdigest()
    index_path.write_text(json.dumps(index))
