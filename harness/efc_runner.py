"""Admission-branch orchestration with an explicit wire/contact split —
sealed Part I §5.3/§6/§8.2/§10.2/§10.5; EFC_CALIBRATION_PACKET_DESIGN
§5/§6/§9; moderator resolutions A-G (final round).

Two unmistakable execution surfaces (resolution B):

- `run_wire_admission_branch` — synthetic/mock only, explicitly labeled
  wire. Takes the test-only `WireComparisonRule` executor, a
  `WireContactAuthorization`, and an injected pinned wire collapse detector.
  Everything it produces is disclosed wire machinery evidence.
- `run_admission_branch` — the production contact surface. It requires a
  typed `ContactAuthorization`, whose construction
  (`authorize_engine_contact`) REFUSES unconditionally in this workspace:
  the final check contract is pending (resolution A), so real-contact
  authorization is structurally impossible until the population-pinned rule
  artifact, its deterministic interpreter, and a conformance proof are
  separately reviewed. A nonempty dict is never authority.

Phase order per branch: manifest-precommit rows → isolated ignorance probes
→ primary S/analog board (T = 0.5) → conditional same-identity T = 0.7
collapse pass (at most once; never probes) → derived pilots → the computed
§5.3 `engine_admission_verdict` row (resolution C).

Collapse (resolution D): there is NO decision-capable default detector. The
eventual production rule must use exact answer AND route realization hashes;
until that route projection is separately pinned, real contact refuses. Wire
tests inject a conspicuously fictional detector whose identity the wire
authorization pins. The T=0.7 diagnostic pass has its own `t07.`-namespaced,
append-only, separately replayable ledger, hash-pinned into the admission
verdict row — it can never collide with or inflate primary K=5 evidence.

Probe audit (resolution E): §13 has no probe event type and none is added.
Each probe lands in a protected append-only sidecar entry `{probe_id,
answer_sha256, recovered, temperature, isolation_id}`; the ordered sidecar
is hashed, and hash + aggregate counts ride the admission verdict row
(including a typed refusal when a probe transport fails). Plaintext probe
responses are scorer-local ephemeral data.

Isolation honesty (resolution F): Python object identity is only a harness
guard. Every session lease must carry an operator/adapter-issued compact
`isolation_id`, tracked for uniqueness alongside wrapper identity. Fresh
provider process/client isolation is an OPERATOR-BOUND pre-contact
obligation — the pure harness cannot prove provider internals, and no
stronger claim is made. Provider cache stays `unverified`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from harness import efc_contracts as c
from harness.efc_check import (WireComparisonRule, ProvenanceStore,
                               validate_wire_comparison_rule,
                               wire_rule_contract_hash)
from harness.efc_controller import EngineResult, TaskRun, run_task
from harness.efc_intervals import sample_mean, sample_sd
from harness.efc_ledger import make_row, recompute_cost
from harness.efc_manifest import ManifestCheckResult, manifest_hash
from harness.efc_packet import Packet, derive_call_plan
from harness.efc_planner import (AdmissionInputs, BinaryPilot, CollapseState,
                                 IgnoranceProbeResult, Pilots,
                                 PopulationPilot, SBandCounts,
                                 StratumCostPilot, calibration_gate,
                                 planned_gates, _iter_leaves)
from harness.efc_renderer import RENDERER_ID, build_foreground, \
    foreground_template_hash

RUNNER_ID = "efc_runner_v0"
PROVIDER_CACHE_STATUS = "unverified"

STATUS_COMPLETED = "completed"
STATUS_BRANCH_REFUSED_TRANSPORT = "branch_refused_transport"

T07_NAMESPACE = "t07."

PHASES = ("manifest_precommit", "ignorance_probes", "primary_board",
          "collapse_pass", "admission_verdict")


class RunnerContractError(ValueError):
    """Runner invariant violated (stale session, retry, plan mismatch,
    unauthorized contact). Fail-closed."""


class TransportRefusal(RuntimeError):
    """Post-pin transport/API failure: terminates and types the branch."""


class _BranchRefused(Exception):
    """Internal: first transport failure ends the branch."""


def runner_contract_payload() -> dict:
    """Typed runner contract (resolution G)."""
    return {
        "runner_id": RUNNER_ID,
        "schema_version": "efc_runner_contract_v1",
        "phase_order": list(PHASES),
        "surfaces": {
            "wire": "run_wire_admission_branch (synthetic/mock only)",
            "contact": ("run_admission_branch (requires ContactAuthorization;"
                        " unconstructible while the check contract is "
                        "pending)"),
        },
        "transport_policy": "first transport failure terminates and types "
                            "the branch; no partial results reach planning",
        "session_lease_policy": ("fresh session per invocation; unique "
                                 "operator/adapter-issued isolation_id AND "
                                 "unique wrapper identity; provider "
                                 "process/client isolation is an "
                                 "operator-bound pre-contact obligation the "
                                 "harness cannot prove"),
        "collapse_detector": ("injected and identity-pinned by the "
                              "authorization; no decision-capable default; "
                              "production rule must hash answer AND route "
                              "realizations (pending)"),
        "temperatures": {"primary": c.CALIBRATION_TEMPERATURE,
                         "collapse_diagnostic":
                             c.COLLAPSE_DIAGNOSTIC_TEMPERATURE},
        "ledger_separation": "t07-namespaced diagnostic ledger, append-only, "
                             "separately replayable, hash-pinned in the "
                             "admission verdict row",
        "probe_audit": "typed sidecar {probe_id, answer_sha256, recovered, "
                       "temperature, isolation_id}; hashed; plaintext "
                       "scorer-local ephemeral",
        "provider_cache": PROVIDER_CACHE_STATUS,
        "placebo_position_gate": "structural_single_insertion_point",
    }


def runner_contract_hash() -> str:
    return hashlib.sha256(json.dumps(runner_contract_payload(),
                                     sort_keys=True, separators=(",", ":")
                                     ).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Collapse detector protocol (resolution D): injected, identity-pinned,
# no default.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PinnedCollapseDetector:
    """An injected §10.2 realization-collapse rule: declarative contract plus
    executable operation, identity-pinned by the authorization. In this
    workspace only conspicuously fictional wire detectors exist; the
    production rule must use exact answer AND route realization hashes and
    is pending a separately pinned route projection."""
    detector_id: str
    contract: dict
    detect: object  # callable(list[TaskRun]) -> bool


def validate_pinned_collapse_detector(det: PinnedCollapseDetector) -> None:
    if not isinstance(det, PinnedCollapseDetector):
        raise RunnerContractError(
            "a collapse detector must be an injected PinnedCollapseDetector; "
            "there is no decision-capable default (resolution D)")
    if not isinstance(det.detector_id, str) or not det.detector_id:
        raise RunnerContractError("detector_id must be a compact id")
    if not isinstance(det.contract, dict) or not det.contract \
            or det.contract.get("detector_id") != det.detector_id:
        raise RunnerContractError(
            "detector contract must be a dict carrying its own detector_id")
    if not callable(det.detect):
        raise RunnerContractError("detector operation must be callable")


def collapse_detector_contract_hash(det: PinnedCollapseDetector) -> str:
    validate_pinned_collapse_detector(det)
    return hashlib.sha256(json.dumps(det.contract, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")
                          ).hexdigest()


def packet_index_sha256(packet: Packet) -> str:
    return hashlib.sha256(json.dumps(packet.index, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")
                          ).hexdigest()


# ---------------------------------------------------------------------------
# Resolution B: two authorization types, one manifest schema.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WireContactAuthorization:
    """Wire-surface authorization: explicitly synthetic. It binds the wire
    run to a validated packet, a machine-checked manifest, the wire rule
    executor, and the pinned wire detector — but it is NOT contact
    authority and `run_admission_branch` refuses it."""
    packet_id: str
    packet_index_sha256: str
    manifest_sha256: str
    wire_rule_id: str
    wire_rule_contract_sha256: str
    detector_id: str
    detector_contract_sha256: str
    foreground_template_sha256: str
    part_i_spec_sha256: str
    wire: bool = True

    def precommit_payload(self) -> dict:
        return {
            "part_i_spec_hash": self.part_i_spec_sha256,
            "surface": "wire",
            "packet_id": self.packet_id,
            "packet_index_sha256": self.packet_index_sha256,
            "manifest_sha256": self.manifest_sha256,
            "wire_rule_id": self.wire_rule_id,
            "collapse_detector_id": self.detector_id,
            "foreground_template_hash": self.foreground_template_sha256,
        }


@dataclass(frozen=True)
class ContactAuthorization:
    """PRODUCTION contact authority. No construction path exists in this
    workspace: `authorize_engine_contact` refuses while the check contract
    is pending (resolution A/B). The type exists so the contact surface has
    a frozen shape to demand."""
    packet_id: str
    packet_index_sha256: str
    manifest_sha256: str
    check_contract_sha256: str          # final, non-pending — cannot exist yet
    collapse_detector_id: str
    collapse_detector_contract_sha256: str
    model_id: str
    decoding_contract_id: str
    foreground_template_sha256: str
    part_i_spec_sha256: str


def _bind_manifest_to_packet(packet: Packet, manifest: dict,
                             manifest_result: ManifestCheckResult) -> None:
    """Shared structural binding (resolution B): the ONE §5.2 manifest schema
    machine-checked, its bytes recomputing to the checked hash, and its
    fixture/probe identities byte-bound to the packet."""
    if not isinstance(packet, Packet) or not packet.ok:
        raise RunnerContractError("authorization requires a validated Packet")
    if not isinstance(manifest_result, ManifestCheckResult):
        raise RunnerContractError(
            "authorization requires the typed §5.2 ManifestCheckResult, not "
            "a bare mapping")
    if not manifest_result.ok or manifest_result.manifest_hash is None:
        raise RunnerContractError(
            f"manifest failed the §5.2 machine check: "
            f"{manifest_result.failures}")
    if manifest_hash(manifest) != manifest_result.manifest_hash:
        raise RunnerContractError(
            "manifest bytes do not recompute to the checked manifest hash")
    packet_fixture_pins = {
        (entry["id"], entry["sha256"])
        for entry in packet.index.get("entries", ())
        if entry.get("role") in ("s_family", "analog")}
    manifest_pins = {(e["fixture_id"], e["sha256"])
                     for e in manifest["calibration_fixtures"]}
    if manifest_pins != packet_fixture_pins:
        raise RunnerContractError(
            "manifest calibration_fixtures do not byte-bind to the packet's "
            "fixture entries (id + sha256 must match exactly)")
    manifest_probe_ids = set(
        manifest["ignorance_probe_contract"]["probe_fixture_ids"])
    if manifest_probe_ids != set(packet.probes.get("probe_fixture_ids", ())):
        raise RunnerContractError(
            "manifest probe ids do not bind to the packet's probe contract")
    if manifest["renderer_id"] != RENDERER_ID:
        raise RunnerContractError(
            f"manifest renderer_id {manifest['renderer_id']!r} is not the "
            f"implemented renderer {RENDERER_ID!r}")
    if manifest["foreground_template_hash"] != foreground_template_hash():
        raise RunnerContractError(
            "manifest foreground_template_hash is not the implemented "
            "template identity")


def authorize_wire_contact(packet: Packet, manifest: dict,
                           manifest_result: ManifestCheckResult,
                           wire_rule: WireComparisonRule,
                           collapse_detector: PinnedCollapseDetector,
                           ) -> WireContactAuthorization:
    """Mint the WIRE authorization for synthetic runs. Same structural
    discipline as the (unmintable) production path, minus the pending
    production-only identities."""
    _bind_manifest_to_packet(packet, manifest, manifest_result)
    validate_wire_comparison_rule(wire_rule)
    validate_pinned_collapse_detector(collapse_detector)
    return WireContactAuthorization(
        packet_id=str(packet.index["packet_id"]),
        packet_index_sha256=packet_index_sha256(packet),
        manifest_sha256=manifest_result.manifest_hash,
        wire_rule_id=wire_rule.rule_id,
        wire_rule_contract_sha256=wire_rule_contract_hash(wire_rule),
        detector_id=collapse_detector.detector_id,
        detector_contract_sha256=collapse_detector_contract_hash(
            collapse_detector),
        foreground_template_sha256=foreground_template_hash(),
        part_i_spec_sha256=c.PART_I_SPEC_SHA256)


def authorize_engine_contact(*_args, **_kwargs) -> ContactAuthorization:
    """Resolution A/B: PRODUCTION contact authorization is structurally
    impossible in this workspace and this function refuses unconditionally.

    Construction will additionally require, once the pending artifacts
    exist: `check_calibration_manifest(manifest).ok`; the pinned manifest
    hash; exact semantic artifact identity match; packet fixture/probe
    ids+hashes bound to manifest fields; population intent and a positive
    token budget; a FINAL, non-pending check contract (population-pinned
    rule artifact + deterministic interpreter + conformance proof); an exact
    model/decoding identity; and a pinned answer+route collapse detector.
    """
    raise RunnerContractError(
        "production contact authorization refused: the check contract is "
        "pending (no population-pinned comparison rule artifact, "
        "deterministic interpreter, or conformance proof exists) and the "
        "answer+route collapse projection is not pinned (resolutions A/B/D); "
        "wire runs use authorize_wire_contact + run_wire_admission_branch")


# ---------------------------------------------------------------------------
# Branch report and isolation machinery.
# ---------------------------------------------------------------------------

@dataclass
class BranchReport:
    rows: list[dict] = field(default_factory=list)
    runs: list[TaskRun] = field(default_factory=list)
    collapse_rows: list[dict] = field(default_factory=list)
    collapse_rows_sha256: str | None = None
    collapse_runs: list[TaskRun] = field(default_factory=list)
    probe_sidecar: list[dict] = field(default_factory=list)
    probe_sidecar_sha256: str | None = None
    refused: list[dict] = field(default_factory=list)
    invocations: int = 0
    probe_calls: int = 0
    phase_log: list[str] = field(default_factory=list)
    status: str = STATUS_COMPLETED
    eligible_for_planning: bool = False
    provider_cache: str = PROVIDER_CACHE_STATUS
    admission_verdict_row: dict | None = None
    # typed planner/admission inputs (None on a refused branch)
    s_band: SBandCounts | None = None
    ignorance: IgnoranceProbeResult | None = None
    collapse: CollapseState | None = None


class _SessionTracker:
    """Unique fresh session per invocation (B3, resolution F): tracked Python
    object identities (strong references, so an id cannot recycle) AND
    unique operator/adapter-issued `isolation_id` process handles — distinct
    wrapper objects sharing an isolation_id are refused. This guards the
    harness side only; fresh provider process/client isolation remains an
    operator-bound pre-contact obligation the harness cannot prove."""

    def __init__(self, factory):
        self._factory = factory
        self._sessions: list = []
        self._ids: set[int] = set()
        self._isolation_ids: set[str] = set()

    def fresh(self, temperature: float):
        session = self._factory(temperature)
        if id(session) in self._ids:
            raise RunnerContractError(
                "session factory returned an already-seen session object: "
                "every invocation must be a fresh process/session (design §6)")
        if getattr(session, "used", False):
            raise RunnerContractError(
                "session factory returned a used session (design §6)")
        isolation_id = getattr(session, "isolation_id", None)
        if not isinstance(isolation_id, str) or not isolation_id:
            raise RunnerContractError(
                "session lease lacks a non-empty operator/adapter-issued "
                "isolation_id (resolution F)")
        if isolation_id in self._isolation_ids:
            raise RunnerContractError(
                f"isolation_id {isolation_id!r} reused: a fresh lease is "
                "required even across distinct wrapper objects (resolution F)")
        self._ids.add(id(session))
        self._isolation_ids.add(isolation_id)
        self._sessions.append(session)
        return session


class _OnceGuard:
    """No retry, no redraw within a declared pass: one invocation per
    (fixture, lane)."""

    def __init__(self, pass_name: str):
        self._pass = pass_name
        self._seen: set[tuple[str, str]] = set()

    def claim(self, fixture_id: str, lane: str) -> None:
        key = (fixture_id, lane)
        if key in self._seen:
            raise RunnerContractError(
                f"retry/redraw refused in {self._pass}: {key} was already "
                "invoked once (design §5)")
        self._seen.add(key)


def _fixture_view(fixture: dict) -> dict:
    return {k: v for k, v in fixture.items()
            if k not in ("_shape", "entity_keys")}


def _rows_sha256(rows: list[dict]) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")
                          ).hexdigest()


def _run_board(packet: Packet, tracker: _SessionTracker, guard: _OnceGuard,
               report: BranchReport, sink: list[TaskRun], row_sink: list[dict],
               oracle_score, store: ProvenanceStore,
               wire_rule: WireComparisonRule, temperature: float,
               event_namespace: str = "") -> None:
    """One full S-family + analog pass. Raises _BranchRefused on the first
    transport failure — the branch is terminal from that point (B3)."""

    def one(fixture: dict, lane: str, foreground, placebo_text) -> None:
        fixture_id = str(fixture["task_id"])
        guard.claim(fixture_id, lane)
        session = tracker.fresh(temperature)
        report.invocations += 1
        try:
            run = run_task(_fixture_view(fixture), lane, foreground,
                           session, oracle_score, store=store,
                           wire_rule=wire_rule,
                           placebo_evidence_text=placebo_text,
                           event_namespace=event_namespace)
        except TransportRefusal as e:
            report.refused.append({"fixture_id": fixture_id, "lane": lane,
                                   "temperature": temperature,
                                   "reason": str(e)})
            raise _BranchRefused from e
        sink.append(run)
        row_sink.extend(run.rows)

    for fixture_id in sorted(packet.s_family):
        fixture = packet.s_family[fixture_id]
        foreground = build_foreground(_fixture_view(fixture))
        placebo = packet.placebos.get(fixture_id, {})
        for leg in c.SOURCE_LEGS:
            one(fixture, leg, foreground,
                placebo.get("text") if leg == "S2_placebo" else None)
    for fixture_id in sorted(packet.analog):
        fixture = packet.analog[fixture_id]
        foreground = build_foreground(_fixture_view(fixture))
        placebo = packet.placebos.get(fixture_id, {})
        for lane in c.LANES:
            one(fixture, lane, foreground,
                placebo.get("text") if lane == "P_placebo" else None)


def _board_call_count(packet: Packet) -> int:
    plan = derive_call_plan(dispositive_fact_count=1, roster_size=1,
                            s_count=len(packet.s_family),
                            analog_count=len(packet.analog))
    return plan.s_family_calls_branch + plan.analog_calls_branch


def _run_passed(run: TaskRun) -> bool:
    score = next(r["payload"] for r in run.rows
                 if r["event_type"] == "world_oracle_score")
    return bool(score.get("passed"))


def _s_band(packet: Packet, runs: list[TaskRun]) -> SBandCounts:
    passes = {leg: 0 for leg in c.SOURCE_LEGS}
    totals = {leg: 0 for leg in c.SOURCE_LEGS}
    for run in runs:
        if run.lane in c.SOURCE_LEGS and run.fixture_id in packet.s_family:
            totals[run.lane] += 1
            passes[run.lane] += int(_run_passed(run))
    return SBandCounts(
        s0_pass=passes["S0_no_check"], s0_n=totals["S0_no_check"],
        s1_pass=passes["S1_relevant_check"], s1_n=totals["S1_relevant_check"],
        s2_pass=passes["S2_placebo"], s2_n=totals["S2_placebo"])


# ---------------------------------------------------------------------------
# Resolution C: deterministic pilot derivation from replayed runs.
# ---------------------------------------------------------------------------

def _replayed_decision_tokens(run: TaskRun) -> int:
    """Cost from untrusting replay of the group rows — never the logged
    claim (§13)."""
    failures: list[str] = []
    cost = recompute_cost(list(run.rows), failures)
    if failures:
        raise RunnerContractError(
            f"cost replay failed for {run.fixture_id}/{run.lane}: {failures}")
    return cost.decision_tokens


def derive_pilots_from_runs(report: BranchReport, packet: Packet,
                            manifest: dict) -> Pilots:
    """Deterministic aggregation from the primary S/analog runs into the
    typed pilot bundle the §10.4 planner consumes: binary successes from
    `world_oracle_score.passed`, cost samples from REPLAYED decision tokens,
    population summaries against the pinned manifest vertices. Every planned
    contrast id must be derivable — a missing lane/stratum sample refuses
    (resolution C)."""
    if not isinstance(report, BranchReport) or not report.eligible_for_planning:
        raise RunnerContractError(
            "pilot derivation requires a completed, planning-eligible branch")
    region = manifest["population_region"]
    region_declared = isinstance(region, dict) and "vertices" in region
    vertices = region["vertices"] if region_declared else None

    # samples: (stratum, lane) -> [(passed, decision_tokens)]
    samples: dict[tuple[str, str], list[tuple[bool, int]]] = {}
    for run in report.runs:
        if run.fixture_id in packet.s_family:
            stratum = "source"
        else:
            stratum = packet.analog[run.fixture_id]["stratum"]
        samples.setdefault((stratum, run.lane), []).append(
            (_run_passed(run), _replayed_decision_tokens(run)))

    def _arm(stratum: str, lane: str) -> list[tuple[bool, int]]:
        got = samples.get((stratum, lane), [])
        if not got:
            raise RunnerContractError(
                f"incomplete analog contrast map: no runs for stratum "
                f"{stratum!r} lane {lane!r} (resolution C — assembly refuses,"
                " the planner never sees a shrunken board)")
        return got

    binary: dict[str, BinaryPilot] = {}
    population: dict[str, PopulationPilot] = {}
    for gate in planned_gates(region_declared):
        for spec in _iter_leaves(gate.node):
            if spec.kind == "population_cost":
                strata = []
                for stratum in c.STRATA:
                    treat = [float(t) for _, t in
                             _arm(stratum, spec.treatment)]
                    comp = [float(t) for _, t in
                            _arm(stratum, spec.comparator)]
                    strata.append(StratumCostPilot(
                        stratum=stratum,
                        mean_treatment=sample_mean(treat),
                        sd_treatment=sample_sd(treat),
                        mean_comparator=sample_mean(comp),
                        sd_comparator=sample_sd(comp)))
                population[spec.contrast_id] = PopulationPilot(
                    strata=tuple(strata))
            else:
                stratum = spec.strata[0]
                treat = _arm(stratum, spec.treatment)
                comp = _arm(stratum, spec.comparator)
                binary[spec.contrast_id] = BinaryPilot(
                    passes_t=float(sum(p for p, _ in treat)), n_t=len(treat),
                    passes_c=float(sum(p for p, _ in comp)), n_c=len(comp))
    return Pilots(binary=binary, population=population, vertices=vertices)


def emit_admission_verdict(report: BranchReport, packet: Packet,
                           manifest: dict,
                           run_id: str = "efc_calibration_wire") -> dict:
    """Compute the §5.3 admission event through the existing
    `calibration_gate` and append ONE legal run-level
    `engine_admission_verdict` row carrying the computed verdict, reasons,
    plan/count disclosure, OR selections, diagnostic summaries, the probe
    sidecar hash + aggregate counts, and the diagnostic-ledger pin
    (resolutions C/D/E). On a transport-refused branch the row carries the
    typed refusal instead of a partial board."""
    if report.status == STATUS_BRANCH_REFUSED_TRANSPORT:
        payload = {
            "verdict": "not_engaged",
            "reasons": ["branch_refused_transport: the band never opened; "
                        "no partial results are eligible for planning"],
            "refused": list(report.refused),
            "probe_sidecar_sha256": report.probe_sidecar_sha256,
            "probe_calls": report.probe_calls,
            "probes_recovered": sum(
                1 for e in report.probe_sidecar if e["recovered"]),
        }
        row = make_row(f"{run_id}.engine_admission_verdict",
                       "engine_admission_verdict", payload=payload)
        report.rows.append(row)
        report.admission_verdict_row = row
        return row

    region = manifest["population_region"]
    region_declared = isinstance(region, dict) and "vertices" in region
    pilots = derive_pilots_from_runs(report, packet, manifest)
    inputs = AdmissionInputs(
        s_band=report.s_band, ignorance=report.ignorance,
        collapse=report.collapse, pilots=pilots,
        population_intent=(c.POPULATION_INTENT_REGION if region_declared
                           else c.POPULATION_INTENT_RESPONSE_CURVE_ONLY),
        vertices=pilots.vertices)
    result = calibration_gate(inputs)
    payload = {
        "verdict": result.verdict,
        "reasons": list(result.reasons),
        "license_path": result.license_path,
        "stratum_n": (dict(result.plan.stratum_n) if result.plan else None),
        "unmet_contrasts": (list(result.plan.unmet) if result.plan else []),
        "or_selections": ({g: {"arm_id": s.arm_id,
                               "members": list(s.member_contrast_ids)}
                           for g, s in result.plan.or_selections.items()}
                          if result.plan else {}),
        # diagnostics only — never selection or verdict inputs (§10.4)
        "projected_clearance_diagnostics": (
            {r.contrast_id: r.projected_clearance_diagnostic
             for g in result.plan.resolved for r in g.requirements}
            if result.plan else {}),
        "projected_counts": (
            {"target_fixtures_per_stratum":
                 dict(result.counts.target_fixtures_per_stratum),
             "target_model_invocations":
                 result.counts.target_model_invocations,
             "source_fixtures": result.counts.source_fixtures,
             "source_model_invocations":
                 result.counts.source_model_invocations}
            if result.counts else None),
        "budget_disclosure_required": True,   # §14.7 stays a human act
        "probe_sidecar_sha256": report.probe_sidecar_sha256,
        "probe_calls": report.probe_calls,
        "probes_recovered": sum(
            1 for e in report.probe_sidecar if e["recovered"]),
        "collapse_rows_sha256": report.collapse_rows_sha256,
        "collapsed_at_t05": report.collapse.collapsed_at_t05,
        "collapsed_at_t07": report.collapse.collapsed_at_t07,
    }
    row = make_row(f"{run_id}.engine_admission_verdict",
                   "engine_admission_verdict", payload=payload)
    report.rows.append(row)
    report.admission_verdict_row = row
    return row


# ---------------------------------------------------------------------------
# Resolution B: the two execution surfaces.
# ---------------------------------------------------------------------------

def run_wire_admission_branch(packet: Packet, session_factory, oracle_score,
                              store: ProvenanceStore,
                              wire_rule: WireComparisonRule,
                              probe_scorer,
                              wire_authorization: WireContactAuthorization,
                              collapse_detector: PinnedCollapseDetector,
                              manifest: dict,
                              run_id: str = "efc_calibration_wire",
                              ) -> BranchReport:
    """The WIRE surface: synthetic/mock sessions only, disclosed wire
    evidence, never mechanism or admission evidence about a real engine.

    Executes the canonical phases and finishes with the computed
    `engine_admission_verdict` row (resolution C). The collapse detector is
    injected and identity-pinned by the wire authorization (resolution D).
    """
    if not isinstance(wire_authorization, WireContactAuthorization):
        raise RunnerContractError(
            "the wire surface requires a typed WireContactAuthorization "
            "minted by authorize_wire_contact; an arbitrary mapping cannot "
            "authorize contact (resolution B)")
    if not packet.ok:
        raise RunnerContractError(
            f"packet failed validation, refusing to run: {packet.failures}")
    if not packet.probes:
        raise RunnerContractError(
            "packet has no ignorance-probe contract: the isolated probe "
            "phase is mandatory before admission calls (design §1/§6)")
    if wire_authorization.packet_index_sha256 != packet_index_sha256(packet) \
            or wire_authorization.packet_id != packet.index.get("packet_id"):
        raise RunnerContractError(
            "authorization does not bind to this packet's identity")
    validate_wire_comparison_rule(wire_rule)
    if wire_rule_contract_hash(wire_rule) \
            != wire_authorization.wire_rule_contract_sha256 \
            or wire_rule.rule_id != wire_authorization.wire_rule_id:
        raise RunnerContractError(
            "run-time wire rule is not the authorized executor")
    validate_pinned_collapse_detector(collapse_detector)
    if collapse_detector.detector_id != wire_authorization.detector_id \
            or collapse_detector_contract_hash(collapse_detector) \
            != wire_authorization.detector_contract_sha256:
        raise RunnerContractError(
            "run-time collapse detector is not the authorized identity")
    if manifest_hash(manifest) != wire_authorization.manifest_sha256:
        raise RunnerContractError(
            "manifest bytes do not recompute to the authorized manifest hash")

    report = BranchReport()
    tracker = _SessionTracker(session_factory)

    # Phase 1: manifest-precommit rows from the typed authorization.
    report.phase_log.append("manifest_precommit")
    report.rows.append(make_row(f"{run_id}.run_config", "run_config", payload={
        "run_id": run_id,
        "surface": "wire",
        "engine_backend": "mock",
        "provider_cache": PROVIDER_CACHE_STATUS,
        "fresh_session_per_call": True,
    }))
    report.rows.append(make_row(f"{run_id}.contract_precommit",
                                "contract_precommit",
                                payload=wire_authorization.precommit_payload()))

    # Phase 2: isolated ignorance probes (resolution E).
    report.phase_log.append("ignorance_probes")
    recovered = 0
    probe_ids = list(packet.probes["probe_fixture_ids"])
    try:
        for probe_id in probe_ids:
            session = tracker.fresh(c.CALIBRATION_TEMPERATURE)
            report.invocations += 1
            report.probe_calls += 1
            try:
                result = session(packet.probes["probe_texts"][probe_id])
            except TransportRefusal as e:
                report.refused.append({"probe_id": probe_id,
                                       "reason": str(e)})
                raise _BranchRefused from e
            if not isinstance(result, EngineResult):
                raise RunnerContractError(
                    "probe session must return the typed EngineResult shape "
                    "(resolution E)")
            verdict = probe_scorer(probe_id, result.answer_text)
            if not isinstance(verdict, bool):
                raise RunnerContractError(
                    f"probe scorer returned {type(verdict).__name__}, not a "
                    "strict bool (resolution E)")
            recovered += int(verdict)
            report.probe_sidecar.append({
                "probe_id": probe_id,
                "answer_sha256": hashlib.sha256(
                    result.answer_text.encode("utf-8")).hexdigest(),
                "recovered": verdict,
                "temperature": c.CALIBRATION_TEMPERATURE,
                "isolation_id": session.isolation_id,
            })
        report.probe_sidecar_sha256 = _rows_sha256(report.probe_sidecar)

        # Phase 3: primary board at the pinned calibration temperature.
        report.phase_log.append("primary_board")
        _run_board(packet, tracker, _OnceGuard("primary_board"), report,
                   report.runs, report.rows, oracle_score, store,
                   wire_rule, c.CALIBRATION_TEMPERATURE)

        # Phase 4: single declared same-identity collapse pass (§10.2), on
        # its own namespaced, separately replayable, hash-pinned ledger
        # (resolution D).
        collapsed_t05 = collapse_detector.detect(report.runs)
        collapsed_t07: bool | None = None
        if collapsed_t05:
            report.phase_log.append("collapse_pass")
            report.collapse_rows.append(make_row(
                f"{T07_NAMESPACE}{run_id}.run_config", "run_config", payload={
                    "run_id": f"{T07_NAMESPACE}{run_id}",
                    "surface": "wire",
                    "engine_backend": "mock",
                    "provider_cache": PROVIDER_CACHE_STATUS,
                    "fresh_session_per_call": True,
                    "temperature": c.COLLAPSE_DIAGNOSTIC_TEMPERATURE,
                }))
            report.collapse_rows.append(make_row(
                f"{T07_NAMESPACE}{run_id}.contract_precommit",
                "contract_precommit",
                payload=wire_authorization.precommit_payload()))
            _run_board(packet, tracker, _OnceGuard("collapse_pass"), report,
                       report.collapse_runs, report.collapse_rows,
                       oracle_score, store, wire_rule,
                       c.COLLAPSE_DIAGNOSTIC_TEMPERATURE,
                       event_namespace=T07_NAMESPACE)
            report.collapse_rows_sha256 = _rows_sha256(report.collapse_rows)
            collapsed_t07 = collapse_detector.detect(report.collapse_runs)
    except _BranchRefused:
        # B3: first transport failure terminates and types the whole branch;
        # nothing partial may reach planning. The verdict row still records
        # the typed refusal and any completed probe audit (resolution E).
        report.status = STATUS_BRANCH_REFUSED_TRANSPORT
        report.eligible_for_planning = False
        if report.probe_sidecar and report.probe_sidecar_sha256 is None:
            report.probe_sidecar_sha256 = _rows_sha256(report.probe_sidecar)
        emit_admission_verdict(report, packet, manifest, run_id)
        return report

    # Counting surface (design §9): executed calls must equal the derived
    # plan — probes = |F|, board = |S|x3 + |X|x6 (+ one conditional pass).
    board = _board_call_count(packet)
    expected = (len(probe_ids) + board
                + (board if report.collapse_runs else 0))
    if report.invocations != expected:
        raise RunnerContractError(
            f"invocation count {report.invocations} != derived plan "
            f"{expected} (counts derive from identity cardinality and the "
            "stop rule)")

    report.status = STATUS_COMPLETED
    report.eligible_for_planning = True
    report.s_band = _s_band(packet, report.runs)
    report.ignorance = IgnoranceProbeResult(
        recovered=recovered, n=len(probe_ids),
        max_recoverable_rate=float(packet.probes["max_recoverable_rate"]))
    report.collapse = CollapseState(collapsed_at_t05=collapsed_t05,
                                    collapsed_at_t07=collapsed_t07)
    emit_admission_verdict(report, packet, manifest, run_id)
    return report


def run_admission_branch(packet: Packet, session_factory, oracle_score,
                         store: ProvenanceStore, probe_scorer,
                         authorization: ContactAuthorization,
                         run_id: str = "efc_admission") -> BranchReport:
    """The PRODUCTION contact surface. It demands the typed
    `ContactAuthorization`, which has no construction path while the check
    contract is pending — so this surface cannot run in this workspace, and
    says so rather than pretending (resolution B)."""
    if not isinstance(authorization, ContactAuthorization):
        raise RunnerContractError(
            "engine contact requires a typed ContactAuthorization; an "
            "arbitrary mapping is never authority (resolution B); wire runs "
            "use run_wire_admission_branch")
    raise RunnerContractError(
        "production contact surface refused: no production engine adapter, "
        "final check contract, or pinned answer+route collapse detector "
        "exists in this workspace (resolutions A/B/D)")
