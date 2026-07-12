"""§10.4 N-rule planner and the §6/§5.3 computed calibration gate.

SPEC_EPISTEMIC_FRAME_CHECK_V0 Part I. The planner enumerates candidate equal N
from N_ENUM_MIN through N_MAX and, for every planned contrast, invokes the SAME
interval functions the score-time verdict will use (harness/efc_intervals) at
the gate's actual confidence level and contrast-specific half-width target. No
closed-form z approximation exists on any admission path.

Everything here is calibration/scorer preparation under §14. Outputs are
admission diagnostics, never mechanism evidence. The admission verdict is a
computed value from typed inputs; no human reading of answers can overwrite it
(§9.5), and the gate never accepts a budget — §14 item 7 is an explicit human
act, so results only carry the disclosure.

Interpretation decisions recorded in notes/EFC_TRACEABILITY.md (design-level
items ratified by the designer seat in `epistemic-frame-check-v0-build`; the
population width criterion was promoted from interpretation to the explicit
§10.3 v0.2 pin in the §18 amendment):
- half-width of an asymmetric interval is (upper - lower) / 2;
- binary pilots project onto candidate N as continuous successes p_hat * N
  through the same Wilson/Newcombe code path score time uses with integers;
- admission is decided by precision alone (§10.4 v0.2 three-layer split): no
  projected difference, margin clearance, positivity clearance, or apparent
  arm win may decide admission; projected clearance at pilot point estimates
  is reported as a diagnostic only;
- the §9.3 preconditions are intersection legs and keep 95% intervals; only
  the OR alternatives use the Bonferroni 97.5% level;
- the §9.3 efficiency alternative's token comparison uses the §9.4/§12
  population construction against its named comparator at family alpha 0.025;
- the population-cost precision pin applies vertex-level: at every declared
  vertex, (estimated_saving - lower_saving) must fit within
  POPULATION_COST_CI_HALF_WIDTH of the comparator's weighted mean.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from harness import efc_contracts as c
from harness.efc_intervals import (DegenerateVarianceError, StratumCostStats,
                                   half_width, linear_prevalence_sum,
                                   newcombe_diff_interval,
                                   simultaneous_stratum_lower_bounds,
                                   welch_interval)


class PlannerContractError(ValueError):
    """Planner precondition violated (malformed pilots, illegal region).
    Fail-closed: a packet the planner cannot fully walk is refused, never
    partially planned."""


# ---------------------------------------------------------------------------
# Contrast specifications — the planned-contrast board (§7, §9.2, §9.3, §9.4).
# ---------------------------------------------------------------------------

BINARY_SUPERIORITY = "binary_superiority"
BINARY_NONINFERIORITY = "binary_noninferiority"
POPULATION_COST = "population_cost"


@dataclass(frozen=True)
class ContrastSpec:
    contrast_id: str
    kind: str
    section: str
    confidence: float                 # gate's actual confidence level (§10.4)
    strata: tuple[str, ...]           # strata whose fixtures this contrast consumes
    margin: float
    target_half_width: float | None   # None only for POPULATION_COST (vertex rule)
    treatment: str
    comparator: str
    population_family_alpha: float | None = None  # POPULATION_COST only


def _sup(cid: str, section: str, stratum: str, treatment: str, comparator: str,
         confidence: float = c.CONFIDENCE_STANDARD) -> ContrastSpec:
    return ContrastSpec(
        contrast_id=cid, kind=BINARY_SUPERIORITY, section=section,
        confidence=confidence, strata=(stratum,),
        margin=c.QUALITY_SUPERIORITY_MARGIN,
        target_half_width=c.QUALITY_SUPERIORITY_CI_HALF_WIDTH,
        treatment=treatment, comparator=comparator)


def _ni(cid: str, section: str, stratum: str, treatment: str, comparator: str,
        confidence: float = c.CONFIDENCE_STANDARD) -> ContrastSpec:
    return ContrastSpec(
        contrast_id=cid, kind=BINARY_NONINFERIORITY, section=section,
        confidence=confidence, strata=(stratum,),
        margin=c.QUALITY_NONINFERIORITY_MARGIN,
        target_half_width=c.QUALITY_NONINFERIORITY_CI_HALF_WIDTH,
        treatment=treatment, comparator=comparator)


def _population(cid: str, section: str, treatment: str, comparator: str,
                margin: float, family_alpha: float) -> ContrastSpec:
    return ContrastSpec(
        contrast_id=cid, kind=POPULATION_COST, section=section,
        confidence=1.0 - family_alpha, strata=c.STRATA, margin=margin,
        target_half_width=None, treatment=treatment, comparator=comparator,
        population_family_alpha=family_alpha)


# Gate trees: a leaf is a ContrastSpec; ALL means every child must be
# plannable (n = max); ANY is the §9.3 OR (n = min over plannable arms).

@dataclass(frozen=True)
class AllOf:
    children: tuple


@dataclass(frozen=True)
class AnyOf:
    children: tuple


@dataclass(frozen=True)
class PlannedGate:
    gate_id: str
    section: str
    node: object


def _boundary_necessity_gate(comparator_lane: str,
                             population_region_declared: bool) -> PlannedGate:
    """§9.3: preconditions AND (quality win OR efficiency win) vs G or O."""
    tag = comparator_lane[0].lower()  # g / o
    preconditions = (
        _ni(f"ni_mc_C_vs_{tag}", "9.3", "match_commit",
            "C_controlled_check", comparator_lane),
        _ni(f"ni_irr_C_vs_{tag}", "9.3", "irrelevant",
            "C_controlled_check", comparator_lane),
    )
    quality_arm = _sup(f"or_quality_mm_C_vs_{tag}", "9.3", "match_mismatch",
                       "C_controlled_check", comparator_lane,
                       confidence=c.CONFIDENCE_OR_GATE)
    arms: list[object] = [quality_arm]
    if population_region_declared:
        # §12: efficiency alternatives use the §9.4 construction with their
        # named comparator, at the OR-gate Bonferroni alpha.
        efficiency_arm = AllOf((
            _ni(f"or_eff_ni_mm_C_vs_{tag}", "9.3", "match_mismatch",
                "C_controlled_check", comparator_lane,
                confidence=c.CONFIDENCE_OR_GATE),
            _population(f"or_eff_cost_C_vs_{tag}", "9.3/12",
                        "C_controlled_check", comparator_lane,
                        margin=c.COST_EFFICIENCY_MARGIN,
                        family_alpha=1.0 - c.CONFIDENCE_OR_GATE),
        ))
        arms.append(efficiency_arm)
    return PlannedGate(
        gate_id=f"boundary_necessity_{comparator_lane}", section="9.3",
        node=AllOf(preconditions + (AnyOf(tuple(arms)),)))


def planned_gates(population_region_declared: bool) -> list[PlannedGate]:
    """The full precommitted contrast board Part I requires the planner to
    admit (§6: every required quality and cost comparison)."""
    gates = [
        PlannedGate("source_mint", "7", AllOf((
            _sup("src_s1_vs_s0", "7", "source",
                 "S1_relevant_check", "S0_no_check"),
            _sup("src_s1_vs_s2", "7", "source",
                 "S1_relevant_check", "S2_placebo"),
        ))),
        PlannedGate("relevant_benefit", "9.2.1",
                    _sup("sup_mm_C_vs_B", "9.2.1", "match_mismatch",
                         "C_controlled_check", "B_inactive")),
        PlannedGate("content_attribution", "9.2.2",
                    _sup("sup_mm_C_vs_P", "9.2.2", "match_mismatch",
                         "C_controlled_check", "P_placebo")),
        PlannedGate("match_commit_loses_cell", "9.2.3",
                    _ni("ni_mc_C_vs_B", "9.2.3", "match_commit",
                        "C_controlled_check", "B_inactive")),
        PlannedGate("irrelevant_silence", "9.2.4",
                    _ni("ni_irr_C_vs_B", "9.2.4", "irrelevant",
                        "C_controlled_check", "B_inactive")),
        PlannedGate("always_check_quality", "9.2.5", AllOf((
            _ni("ni_mm_C_vs_A", "9.2.5", "match_mismatch",
                "C_controlled_check", "A_always_check"),
            _ni("ni_mc_C_vs_A", "9.2.5", "match_commit",
                "C_controlled_check", "A_always_check"),
        ))),
        _boundary_necessity_gate("G_generic_caution", population_region_declared),
        _boundary_necessity_gate("O_offer_projection", population_region_declared),
    ]
    if population_region_declared:
        gates.append(PlannedGate(
            "population_always_check_cost", "9.4",
            _population("pop_cost_C_vs_A", "9.4", "C_controlled_check",
                        "A_always_check",
                        margin=c.POPULATION_ALWAYS_CHECK_MARGIN,
                        family_alpha=c.POPULATION_FAMILY_ALPHA)))
    return gates


# ---------------------------------------------------------------------------
# Pilot summaries (calibration analog board, §6: variance and N only).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BinaryPilot:
    """K-fixture pass counts for one binary contrast (treatment, comparator)."""
    passes_t: float
    n_t: int
    passes_c: float
    n_c: int

    def rates(self) -> tuple[float, float]:
        if self.n_t < 1 or self.n_c < 1:
            raise PlannerContractError(f"binary pilot with empty arm: {self}")
        if not (0 <= self.passes_t <= self.n_t and 0 <= self.passes_c <= self.n_c):
            raise PlannerContractError(f"binary pilot counts out of range: {self}")
        return self.passes_t / self.n_t, self.passes_c / self.n_c


@dataclass(frozen=True)
class StratumCostPilot:
    """Pilot decision-token cost for one stratum of one comparison.
    `treatment` is the candidate lane (C); `comparator` is the lane priced
    against it (A, G, or O) whose saving d_s = mean_comp - mean_treat."""
    stratum: str
    mean_treatment: float
    sd_treatment: float
    mean_comparator: float
    sd_comparator: float


@dataclass(frozen=True)
class PopulationPilot:
    strata: tuple[StratumCostPilot, ...]

    def by_stratum(self) -> dict[str, StratumCostPilot]:
        got = {s.stratum: s for s in self.strata}
        if set(got) != set(c.STRATA):
            raise PlannerContractError(
                f"population pilot strata {sorted(got)} != {sorted(c.STRATA)}")
        return got


# ---------------------------------------------------------------------------
# Per-contrast n_required (§10.4 enumeration through score-time functions).
# ---------------------------------------------------------------------------

STATUS_MET = "met"
STATUS_UNMET = "ci_target_unmet"
STATUS_DEGENERATE = "degenerate_pilot_variance"


@dataclass(frozen=True)
class NRequirement:
    contrast_id: str
    kind: str
    status: str
    n_required: int | None
    # width the shared function reports at n_required (met) or at N_MAX
    # (unmet); the honest number either way.
    achieved_half_width: float | None
    target_half_width: float | None
    # diagnostic only (§10.3: calibration may estimate variance, not rescue
    # margins): would the gate clear at pilot point estimates and n_required?
    projected_clearance_diagnostic: bool | None = None
    # POPULATION_COST only (§19): per-vertex diagnostics at the admitted N,
    # reconstructible via population_vertex_diagnostics; never verdicts.
    vertex_diagnostics: tuple = ()


def n_required_binary(pilot: BinaryPilot, spec: ContrastSpec) -> NRequirement:
    p_t, p_c = pilot.rates()
    target = spec.target_half_width
    assert target is not None
    found: int | None = None
    achieved: float | None = None
    for n in range(c.N_ENUM_MIN, c.N_MAX + 1):
        interval = newcombe_diff_interval(p_t * n, n, p_c * n, n, spec.confidence)
        hw = half_width(interval)
        if hw <= target:
            found, achieved = n, hw
            break
    if found is None:
        interval = newcombe_diff_interval(p_t * c.N_MAX, c.N_MAX,
                                          p_c * c.N_MAX, c.N_MAX,
                                          spec.confidence)
        return NRequirement(spec.contrast_id, spec.kind, STATUS_UNMET, None,
                            half_width(interval), target)
    lower = newcombe_diff_interval(p_t * found, found,
                                   p_c * found, found, spec.confidence)[0]
    if spec.kind == BINARY_SUPERIORITY:
        clears = (p_t - p_c) >= spec.margin and lower > 0.0
    else:
        clears = lower >= -spec.margin
    return NRequirement(spec.contrast_id, spec.kind, STATUS_MET, found,
                        achieved, target, projected_clearance_diagnostic=clears)


def n_required_cost(mean_t: float, sd_t: float, mean_c: float, sd_c: float,
                    confidence: float, target_half_width_abs: float,
                    contrast_id: str = "scalar_cost") -> NRequirement:
    """Plain scalar-cost planning (§10.4 bullet 2): shared Welch function with
    N-dependent Welch-Satterthwaite df at the gate's actual confidence."""
    if target_half_width_abs <= 0.0:
        raise PlannerContractError(
            f"cost target half-width must be positive: {target_half_width_abs}")
    for n in range(c.N_ENUM_MIN, c.N_MAX + 1):
        try:
            w = welch_interval(mean_t, sd_t, n, mean_c, sd_c, n, confidence)
        except DegenerateVarianceError:
            return NRequirement(contrast_id, "cost", STATUS_DEGENERATE, None,
                                None, target_half_width_abs)
        hw = 0.5 * (w.upper - w.lower)
        if hw <= target_half_width_abs:
            return NRequirement(contrast_id, "cost", STATUS_MET, n, hw,
                                target_half_width_abs)
    return NRequirement(contrast_id, "cost", STATUS_UNMET, None, hw,
                        target_half_width_abs)


@dataclass(frozen=True)
class VertexProjection:
    vertex: dict[str, float]
    estimated_saving: float
    lower_saving: float
    comparator_weighted_mean: float


@dataclass(frozen=True)
class VertexDiagnostic:
    """§19/§10.4: reconstructible per-vertex calibration diagnostic — never a
    verdict. Untrusting replay recomputes these from the typed pilot summaries
    and the pinned region via `population_vertex_diagnostics`; serialized
    booleans are not trusted."""
    vertex: dict[str, float]
    comparator_weighted_mean: float
    estimated_saving: float
    lower_saving: float
    precision_gap: float
    precision_target: float
    margin_ok: bool
    positivity_ok: bool


def population_vertex_diagnostics(pilot: PopulationPilot, spec: ContrastSpec,
                                  vertices: list[dict[str, float]],
                                  n: int) -> tuple[VertexDiagnostic, ...]:
    """The single recompute path for per-vertex population diagnostics at a
    given N. `n_required_population` calls this at the admitted N; score-time
    replay calls it with the same typed inputs to verify any recorded rows."""
    assert spec.population_family_alpha is not None
    out = []
    for pr in _project_population_at_n(pilot, n, vertices,
                                       spec.population_family_alpha):
        target = c.POPULATION_COST_CI_HALF_WIDTH * pr.comparator_weighted_mean
        out.append(VertexDiagnostic(
            vertex=pr.vertex,
            comparator_weighted_mean=pr.comparator_weighted_mean,
            estimated_saving=pr.estimated_saving,
            lower_saving=pr.lower_saving,
            precision_gap=pr.estimated_saving - pr.lower_saving,
            precision_target=target,
            margin_ok=(pr.estimated_saving
                       >= spec.margin * pr.comparator_weighted_mean),
            positivity_ok=pr.lower_saving > 0.0))
    return tuple(out)


def _project_population_at_n(pilot: PopulationPilot, n: int,
                             vertices: list[dict[str, float]],
                             family_alpha: float) -> list[VertexProjection]:
    by_stratum = pilot.by_stratum()
    stats = [StratumCostStats(stratum=s.stratum,
                              mean_a=s.mean_comparator, sd_a=s.sd_comparator,
                              n_a=n,
                              mean_c=s.mean_treatment, sd_c=s.sd_treatment,
                              n_c=n)
             for s in (by_stratum[name] for name in c.STRATA)]
    bounds = simultaneous_stratum_lower_bounds(stats, family_alpha=family_alpha)
    d_point = {b.stratum: b.d_point for b in bounds}
    d_lower = {b.stratum: b.d_lower for b in bounds}
    comp_mean = {s: by_stratum[s].mean_comparator for s in c.STRATA}
    out = []
    for v in vertices:
        out.append(VertexProjection(
            vertex=dict(v),
            estimated_saving=linear_prevalence_sum(v, d_point),
            lower_saving=linear_prevalence_sum(v, d_lower),
            comparator_weighted_mean=linear_prevalence_sum(v, comp_mean)))
    return out


def validate_prevalence_region(vertices: list[dict[str, float]]) -> None:
    """§9.4: finite vertex list on the three-stratum simplex with
    p_irrelevant bounded away from zero at every vertex."""
    if not vertices:
        raise PlannerContractError("population region has no vertices")
    for v in vertices:
        if set(v) != set(c.STRATA):
            raise PlannerContractError(f"vertex strata {sorted(v)} != {sorted(c.STRATA)}")
        if abs(sum(v.values()) - 1.0) > 1.0e-9 or any(p < 0.0 for p in v.values()):
            raise PlannerContractError(f"vertex not on simplex: {v}")
        if v["irrelevant"] <= 0.0:
            raise PlannerContractError(
                f"region closure reaches p_irrelevant = 0 at {v}: refused (§9.4 "
                "— C and A run the same check everywhere, selective-cost claim "
                "undecidable)")


def n_required_population(pilot: PopulationPilot, spec: ContrastSpec,
                          vertices: list[dict[str, float]]) -> NRequirement:
    """Admission uses only the explicit §10.3 v0.2 population precision pin:
    at every declared vertex, the simultaneous saving gap
    (estimated_saving - lower_saving) must fit within
    POPULATION_COST_CI_HALF_WIDTH of the comparator's weighted mean. The 10%
    saving margin and positive lower bound are computed at the admitted N and
    reported as `projected_clearance_diagnostic` only (§10.4 three-layer
    split); at held-out score time they remain mandatory §9.4 verdict
    conditions. Linearity makes vertex checks exact (§9.4)."""
    validate_prevalence_region(vertices)
    assert spec.population_family_alpha is not None
    worst_gap: float | None = None
    for n in range(c.N_ENUM_MIN, c.N_MAX + 1):
        try:
            projections = _project_population_at_n(
                pilot, n, vertices, spec.population_family_alpha)
        except DegenerateVarianceError:
            return NRequirement(spec.contrast_id, spec.kind, STATUS_DEGENERATE,
                                None, None, None)
        worst_gap = 0.0
        precision_ok = True
        for pr in projections:
            gap = pr.estimated_saving - pr.lower_saving
            worst_gap = max(worst_gap, gap)
            if gap > c.POPULATION_COST_CI_HALF_WIDTH * pr.comparator_weighted_mean:
                precision_ok = False
        if precision_ok:
            diagnostics = population_vertex_diagnostics(pilot, spec, vertices, n)
            clears = all(d.margin_ok and d.positivity_ok for d in diagnostics)
            return NRequirement(spec.contrast_id, spec.kind, STATUS_MET, n,
                                worst_gap, None,
                                projected_clearance_diagnostic=clears,
                                vertex_diagnostics=diagnostics)
    return NRequirement(spec.contrast_id, spec.kind, STATUS_UNMET, None,
                        worst_gap, None)


# ---------------------------------------------------------------------------
# Gate-tree resolution and the stratum N table (§10.2).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Pilots:
    """Typed pilot bundle keyed by contrast_id. Population pilots are keyed
    per contrast because §9.3 arms price different comparators."""
    binary: dict[str, BinaryPilot] = field(default_factory=dict)
    population: dict[str, PopulationPilot] = field(default_factory=dict)
    vertices: list[dict[str, float]] | None = None


@dataclass(frozen=True)
class ResolvedGate:
    gate_id: str
    section: str
    n_required: int | None
    requirements: tuple[NRequirement, ...]
    # §0.2 "separately precommitted comparisons": which OR arms are powered
    # at the gate's chosen N — decision-bearing arms are sealed pre-run.
    decision_bearing_arms: tuple[str, ...] = ()


def _resolve_node(node, pilots: Pilots) -> tuple[int | None, list[NRequirement], list[str]]:
    """Returns (n_required, leaf requirements, decision-bearing arm ids)."""
    if isinstance(node, ContrastSpec):
        req = _resolve_leaf(node, pilots)
        return req.n_required, [req], [node.contrast_id]
    if isinstance(node, AllOf):
        reqs: list[NRequirement] = []
        arms: list[str] = []
        worst: int | None = 0
        for child in node.children:
            n, child_reqs, child_arms = _resolve_node(child, pilots)
            reqs.extend(child_reqs)
            arms.extend(child_arms)
            if n is None or worst is None:
                worst = None
            else:
                worst = max(worst, n)
        return worst, reqs, arms
    if isinstance(node, AnyOf):
        reqs = []
        best: int | None = None
        best_arms: list[str] = []
        for child in node.children:
            n, child_reqs, child_arms = _resolve_node(child, pilots)
            reqs.extend(child_reqs)
            if n is not None and (best is None or n < best):
                best, best_arms = n, child_arms
        return best, reqs, best_arms
    raise PlannerContractError(f"unknown gate node: {node!r}")


def _resolve_leaf(spec: ContrastSpec, pilots: Pilots) -> NRequirement:
    if spec.kind in (BINARY_SUPERIORITY, BINARY_NONINFERIORITY):
        pilot = pilots.binary.get(spec.contrast_id)
        if pilot is None:
            raise PlannerContractError(f"missing binary pilot: {spec.contrast_id}")
        return n_required_binary(pilot, spec)
    if spec.kind == POPULATION_COST:
        pilot = pilots.population.get(spec.contrast_id)
        if pilot is None:
            raise PlannerContractError(f"missing population pilot: {spec.contrast_id}")
        if pilots.vertices is None:
            raise PlannerContractError("population contrast without declared region")
        return n_required_population(pilot, spec, pilots.vertices)
    raise PlannerContractError(f"unknown contrast kind: {spec.kind}")


@dataclass(frozen=True)
class SuitePlan:
    resolved: tuple[ResolvedGate, ...]
    stratum_n: dict[str, int | None]      # equalized per §10.2
    all_plannable: bool
    unmet: tuple[str, ...]                # contrast ids that refuse the family
    # §9.3 v0.3: the pinned decision-bearing arms per gate, selected on
    # precision/N alone before held-out contact. Only a pinned bearing arm can
    # satisfy a §9.3 OR at score time; held-out outcomes cannot promote a
    # non-bearing arm (architect ruling, §19).
    decision_bearing_arms: dict[str, tuple[str, ...]] = field(default_factory=dict)


def resolve_gates(gates: list[PlannedGate], pilots: Pilots) -> SuitePlan:
    resolved: list[ResolvedGate] = []
    # stratum -> observed decision-bearing n_required values (None poisons)
    stratum_ns: dict[str, list[int | None]] = {}
    spec_strata: dict[str, tuple[str, ...]] = {}
    for gate in gates:
        for spec in _iter_leaves(gate.node):
            spec_strata[spec.contrast_id] = spec.strata
    unmet: list[str] = []
    for gate in gates:
        n, reqs, arms = _resolve_node(gate.node, pilots)
        resolved.append(ResolvedGate(gate.gate_id, gate.section, n,
                                     tuple(reqs), tuple(arms)))
        if n is None:
            # gate unplannable: every stratum it touches is poisoned and its
            # failing leaves refuse the family (§10.4)
            for req in reqs:
                for stratum in spec_strata[req.contrast_id]:
                    stratum_ns.setdefault(stratum, []).append(None)
            unmet.extend(r.contrast_id for r in reqs if r.status != STATUS_MET)
        else:
            # only decision-bearing leaves size the suite (§0.2: separately
            # precommitted comparisons; an unpowered OR arm is sealed out)
            bearing = set(arms)
            for req in reqs:
                if req.contrast_id in bearing:
                    for stratum in spec_strata[req.contrast_id]:
                        stratum_ns.setdefault(stratum, []).append(req.n_required)
    stratum_n: dict[str, int | None] = {}
    for stratum, ns in stratum_ns.items():
        stratum_n[stratum] = None if any(v is None for v in ns) else max(ns)
    # §10.2: the two trigger-matching strata share one N, the maximum admitted
    # requirement across their comparisons. A stratum no decision-bearing
    # leaf touches is absent, not poisoned; a poisoned (None) entry poisons
    # both.
    present = [stratum_n[s] for s in c.TRIGGER_MATCHING_STRATA if s in stratum_n]
    if present:
        shared = None if any(v is None for v in present) else max(present)
        stratum_n["match_mismatch"] = stratum_n["match_commit"] = shared
    all_plannable = bool(resolved) and all(g.n_required is not None
                                           for g in resolved)
    return SuitePlan(tuple(resolved), stratum_n, all_plannable,
                     tuple(dict.fromkeys(unmet)),
                     decision_bearing_arms={g.gate_id: g.decision_bearing_arms
                                            for g in resolved})


def _iter_leaves(node):
    if isinstance(node, ContrastSpec):
        yield node
    elif isinstance(node, (AllOf, AnyOf)):
        for child in node.children:
            yield from _iter_leaves(child)
    else:
        raise PlannerContractError(f"unknown gate node: {node!r}")


# ---------------------------------------------------------------------------
# §6 calibration bands, ignorance probe, §10.2 point-mode detection.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SBandCounts:
    s0_pass: int
    s0_n: int
    s1_pass: int
    s1_n: int
    s2_pass: int
    s2_n: int


def calibration_band_failures(counts: SBandCounts) -> list[str]:
    for name in ("s0", "s1", "s2"):
        n = getattr(counts, f"{name}_n")
        p = getattr(counts, f"{name}_pass")
        if n < 1 or not (0 <= p <= n):
            raise PlannerContractError(f"malformed S-band counts: {counts}")
    s0 = counts.s0_pass / counts.s0_n
    s1 = counts.s1_pass / counts.s1_n
    s2 = counts.s2_pass / counts.s2_n
    failures = []
    if s0 > c.S0_MAX_PASS_RATE:
        failures.append(f"s0_pass_rate {s0:.3f} > {c.S0_MAX_PASS_RATE}")
    if s1 < c.S1_MIN_PASS_RATE:
        failures.append(f"s1_pass_rate {s1:.3f} < {c.S1_MIN_PASS_RATE}")
    if s1 - s0 < c.S1_S0_MIN_DIFF:
        failures.append(f"s1-s0 {s1 - s0:.3f} < {c.S1_S0_MIN_DIFF}")
    if s1 - s2 < c.S1_S2_MIN_DIFF:
        failures.append(f"s1-s2 {s1 - s2:.3f} < {c.S1_S2_MIN_DIFF}")
    return failures


@dataclass(frozen=True)
class IgnoranceProbeResult:
    recovered: int
    n: int
    max_recoverable_rate: float  # pinned by the calibration manifest contract

    def failure(self) -> str | None:
        if self.n < 1 or not (0 <= self.recovered <= self.n):
            raise PlannerContractError(f"malformed ignorance probe: {self}")
        rate = self.recovered / self.n
        if rate > self.max_recoverable_rate:
            return (f"dispositive facts recoverable at {rate:.3f} > "
                    f"{self.max_recoverable_rate} (weights/foreground leak)")
        return None


@dataclass(frozen=True)
class CollapseState:
    """§10.2: exact answer+route hash collapse within a branch at T=0.5,
    then the single declared diagnostic pass at T=0.7."""
    collapsed_at_t05: bool
    collapsed_at_t07: bool | None  # None = diagnostic not run


def detect_collapse(realization_hashes: list[str]) -> bool:
    if not realization_hashes:
        raise PlannerContractError("collapse detection over zero realizations")
    return len(set(realization_hashes)) == 1


# ---------------------------------------------------------------------------
# The computed calibration gate (§5.3 event `engine_admission_verdict`).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProjectedCounts:
    """Pre-build budget disclosure inputs (§10.2): fixture identities and
    model invocations implied by the plan. Counts, not acceptance — §14.7
    budget acceptance is an explicit human act."""
    target_fixtures_per_stratum: dict[str, int]
    target_model_invocations: int      # per engine branch: sum_s N_s * |lanes|
    source_fixtures: int
    source_model_invocations: int      # N_source * |source legs|


def projected_counts(plan: SuitePlan, source_n: int | None) -> ProjectedCounts | None:
    if not plan.all_plannable or source_n is None:
        return None
    per_stratum = {s: n for s, n in plan.stratum_n.items()
                   if s in c.STRATA and n is not None}
    if set(per_stratum) != set(c.STRATA):
        return None
    invocations = sum(per_stratum.values()) * len(c.LANES)
    return ProjectedCounts(
        target_fixtures_per_stratum=per_stratum,
        target_model_invocations=invocations,
        source_fixtures=source_n,
        source_model_invocations=source_n * len(c.SOURCE_LEGS))


@dataclass(frozen=True)
class AdmissionInputs:
    s_band: SBandCounts | None
    ignorance: IgnoranceProbeResult | None
    collapse: CollapseState | None
    pilots: Pilots | None
    # §5.2 v0.3: the pre-calibration population intent, exactly one of
    # c.POPULATION_INTENT_REGION / c.POPULATION_INTENT_RESPONSE_CURVE_ONLY.
    # None means the packet is not license-seeking and the band does not open.
    population_intent: str | None
    vertices: list[dict[str, float]] | None


@dataclass(frozen=True)
class AdmissionResult:
    verdict: str                       # one of c.ENGINE_ADMISSION_VERDICTS
    reasons: tuple[str, ...]
    plan: SuitePlan | None
    counts: ProjectedCounts | None
    budget_disclosure_required: bool = True  # §14.7 stays a human act
    # §12 v0.3: which license path the declared intent selects. Under
    # response_curve_only the frozen envelope can never emit `licensed`.
    license_path: str | None = None


def calibration_gate(inputs: AdmissionInputs) -> AdmissionResult:
    """Composes the §5.3 admission event from typed calibration inputs.

    Verdict precedence: absent packet -> not_engaged; persistent §10.2
    collapse -> point_mode_diagnostic; §6 band or ignorance failure ->
    engine_refused; any contrast with n_required > N_MAX or a degenerate
    pilot -> confounded(ci_target_unmet) (§10.4, refuses Part II authoring);
    else engine_admitted. Never a mechanism verdict (§6)."""
    if inputs.s_band is None or inputs.ignorance is None or inputs.collapse is None \
            or inputs.pilots is None:
        return AdmissionResult("not_engaged",
                               ("calibration packet incomplete: band never opens",),
                               None, None)
    if inputs.collapse.collapsed_at_t05:
        if inputs.collapse.collapsed_at_t07 is None:
            return AdmissionResult(
                "not_engaged",
                ("T=0.5 realizations collapsed and the single declared T=0.7 "
                 "diagnostic pass has not run (§10.2)",), None, None)
        if inputs.collapse.collapsed_at_t07:
            return AdmissionResult(
                "point_mode_diagnostic",
                ("answer/route hashes collapse at T=0.5 and T=0.7; behavioral "
                 "mechanism license unavailable (§10.2)",), None, None)
    if inputs.population_intent is None:
        # §10.4 v0.3: a packet with no declared population intent is not a
        # license-seeking packet and does not open the band.
        return AdmissionResult(
            "not_engaged",
            ("no §5.2 population intent declared (license-bearing region or "
             "response_curve_only, exactly one, before calibration contact)",),
            None, None)
    if inputs.population_intent == c.POPULATION_INTENT_REGION:
        if inputs.vertices is None:
            raise PlannerContractError(
                "population region declared but no vertices supplied")
        validate_prevalence_region(inputs.vertices)
        region_declared = True
    elif inputs.population_intent == c.POPULATION_INTENT_RESPONSE_CURVE_ONLY:
        if inputs.vertices is not None:
            raise PlannerContractError(
                "response_curve_only declared together with vertices: the "
                "§5.2 intent is exactly one choice")
        region_declared = False
    else:
        raise PlannerContractError(
            f"unknown population intent {inputs.population_intent!r}")
    refusals = list(calibration_band_failures(inputs.s_band))
    ignorance_failure = inputs.ignorance.failure()
    if ignorance_failure:
        refusals.append(ignorance_failure)
    if refusals:
        return AdmissionResult("engine_refused", tuple(refusals), None, None,
                               license_path=inputs.population_intent)
    pilots = Pilots(binary=dict(inputs.pilots.binary),
                    population=dict(inputs.pilots.population),
                    vertices=inputs.vertices)
    plan = resolve_gates(planned_gates(region_declared), pilots)
    counts = projected_counts(plan, _source_n(plan))
    if not plan.all_plannable:
        return AdmissionResult(
            "confounded(ci_target_unmet)",
            tuple(f"n_required > {c.N_MAX} or degenerate: {cid}"
                  for cid in plan.unmet),
            plan, counts, license_path=inputs.population_intent)
    return AdmissionResult("engine_admitted", (), plan, counts,
                           license_path=inputs.population_intent)


def _source_n(plan: SuitePlan) -> int | None:
    return plan.stratum_n.get("source")
