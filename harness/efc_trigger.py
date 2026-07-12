"""Closed structural trigger — SPEC_EPISTEMIC_FRAME_CHECK_V0 §2.1/§8.5/§9.1.

The v0 trigger is a deterministic four-conjunct predicate over DECLARED
foreground structure. The extractor may read only the task surface and
population-pinned metadata; it may not read fetched source scope, expected
action, oracle rows, outcome labels, model narration, or any field equivalent
to `required_scope`. Removing oracle and outcome material must leave the
trigger result byte-identical (§2.1) — `check_extraction_integrity` is that
gate, and the §9.1 family-validity functions consume it per fixture.

The predicate answers only WHEN TO LOOK. Nothing in this module may consult
what the check would find; the extractor never sees `source_reference` or
`decision_scope` VALUES, only their declared presence booleans. Discipline is
PRF `predicate_ast` one level up: closed field vocabulary, fail-closed on any
fixture the extractor cannot fully walk.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from harness import efc_contracts as c


class ExtractionClosureError(ValueError):
    """The extractor stepped outside the closed surface vocabulary or the
    fixture is missing a declared trigger field. Fail-closed."""


# §2.1: the four declared trigger fields (presence booleans + basis kind).
TRIGGER_FIELDS = ("assertion_basis_kind", "observation_boundary_present",
                  "source_reference_present", "decision_scope_present")

CITED_SOURCE = "cited_source"

# Task surface + population-pinned metadata the extractor MAY read (§2.1).
# Note: `source_reference` / `decision_scope` values are deliberately absent —
# the trigger sees presence booleans only.
ALLOWED_SURFACE_FIELDS = frozenset({
    "task_id", "surface_text", "population_id",
    *TRIGGER_FIELDS,
})

# Oracle/outcome material whose removal must leave the trigger result
# byte-identical (§2.1), plus fields equivalent to required_scope and the
# authored stratum (an outcome-equivalent routing label).
ORACLE_AND_OUTCOME_FIELDS = frozenset({
    "oracle", "oracle_rows", "oracle_answer", "outcome_label",
    "world_oracle_score", "expected_action", "required_scope",
    "fetched_source_scope", "model_narration", "nomination_prose",
    "stratum",
})


@dataclass(frozen=True)
class TriggerFeatures:
    assertion_basis_kind: str
    observation_boundary_present: bool
    source_reference_present: bool
    decision_scope_present: bool


def extract_trigger_features(fixture: dict) -> TriggerFeatures:
    """Deterministic extraction from the whitelisted surface view only."""
    surface = {k: v for k, v in fixture.items() if k in ALLOWED_SURFACE_FIELDS}
    missing = [f for f in TRIGGER_FIELDS if f not in surface]
    if missing:
        raise ExtractionClosureError(
            f"fixture lacks declared trigger fields {missing}; a fixture the "
            "extractor cannot fully walk is refused, never part-evaluated")
    kind = surface["assertion_basis_kind"]
    if not isinstance(kind, str):
        raise ExtractionClosureError(
            f"assertion_basis_kind must be a string, got {type(kind).__name__}")
    for flag in TRIGGER_FIELDS[1:]:
        if not isinstance(surface[flag], bool):
            raise ExtractionClosureError(
                f"{flag} must be a declared boolean, got "
                f"{type(surface[flag]).__name__}")
    return TriggerFeatures(
        assertion_basis_kind=kind,
        observation_boundary_present=surface["observation_boundary_present"],
        source_reference_present=surface["source_reference_present"],
        decision_scope_present=surface["decision_scope_present"])


def trigger_fires(features: TriggerFeatures) -> bool:
    """§2.1 conjunction, verbatim."""
    return (features.assertion_basis_kind == CITED_SOURCE
            and features.observation_boundary_present is False
            and features.source_reference_present is True
            and features.decision_scope_present is True)


def trigger_result_record(fixture: dict) -> bytes:
    """Canonical bytes of (features, fires) — the §2.1 byte-identity artifact
    and the value score-time replay recomputes (§13)."""
    features = extract_trigger_features(fixture)
    record = {
        "assertion_basis_kind": features.assertion_basis_kind,
        "observation_boundary_present": features.observation_boundary_present,
        "source_reference_present": features.source_reference_present,
        "decision_scope_present": features.decision_scope_present,
        "fires": trigger_fires(features),
    }
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def strip_oracle_and_outcome(fixture: dict) -> dict:
    return {k: v for k, v in fixture.items()
            if k not in ORACLE_AND_OUTCOME_FIELDS}


def check_extraction_integrity(fixture: dict) -> bool:
    """§2.1: removing oracle and outcome material leaves the trigger result
    byte-identical."""
    return (trigger_result_record(fixture)
            == trigger_result_record(strip_oracle_and_outcome(fixture)))


# ---------------------------------------------------------------------------
# §8.5 irrelevant-stratum shape.
# ---------------------------------------------------------------------------

def irrelevant_shape_failures(fixture: dict) -> list[str]:
    """Every irrelevant fixture keeps both check inputs (so A_always_check
    executes the identical action) while at least one trigger-only semantic
    conjunct is false. No content-free routing tag exists to be checked —
    the shape IS the two declared semantic fields."""
    features = extract_trigger_features(fixture)
    failures = []
    if not features.source_reference_present:
        failures.append("irrelevant fixture dropped source_reference_present")
    if not features.decision_scope_present:
        failures.append("irrelevant fixture dropped decision_scope_present")
    if (features.assertion_basis_kind == CITED_SOURCE
            and features.observation_boundary_present is False):
        failures.append(
            "no trigger-only semantic conjunct is false: fixture would fire "
            "(canonical shape sets observation_boundary_present = true; the "
            "allowed variant sets assertion_basis_kind != cited_source)")
    return failures


# ---------------------------------------------------------------------------
# §9.1 family-validity gates (computed over authored fixture collections).
# Family functions read authored strata directly — they are scorer-side
# validation, not extraction; the extractor itself never sees `stratum`.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FamilyValidityResult:
    ok: bool
    failures: tuple[str, ...]


def family_validity(fixtures: list[dict],
                    forbidden_phrases: tuple[str, ...] = ()) -> FamilyValidityResult:
    failures: list[str] = []
    by_stratum: dict[str, list[dict]] = {s: [] for s in c.STRATA}
    for fixture in fixtures:
        stratum = fixture.get("stratum")
        if stratum not in by_stratum:
            failures.append(f"fixture {fixture.get('task_id')}: unknown stratum "
                            f"{stratum!r}")
            continue
        by_stratum[stratum].append(fixture)

    # equal counts across the trigger-matching strata
    n_mm = len(by_stratum["match_mismatch"])
    n_mc = len(by_stratum["match_commit"])
    if n_mm != n_mc:
        failures.append(f"unbalanced trigger-matching strata: {n_mm} vs {n_mc}")

    fires_by_stratum: dict[str, int] = {s: 0 for s in c.STRATA}
    for stratum, members in by_stratum.items():
        for fixture in members:
            try:
                if not check_extraction_integrity(fixture):
                    failures.append(
                        f"fixture {fixture.get('task_id')}: trigger result not "
                        "byte-identical after oracle/outcome removal")
                features = extract_trigger_features(fixture)
            except ExtractionClosureError as e:
                failures.append(f"fixture {fixture.get('task_id')}: {e}")
                continue
            fires = trigger_fires(features)
            fires_by_stratum[stratum] += int(fires)
            # exactly zero false and missed fires at the deterministic layer
            if stratum == "irrelevant":
                if fires:
                    failures.append(f"false fire on irrelevant fixture "
                                    f"{fixture.get('task_id')}")
                failures.extend(f"fixture {fixture.get('task_id')}: {msg}"
                                for msg in irrelevant_shape_failures(fixture))
            elif not fires:
                failures.append(f"missed fire on {stratum} fixture "
                                f"{fixture.get('task_id')}")
            text = fixture.get("surface_text", "")
            for phrase in forbidden_phrases:
                if phrase and phrase in text:
                    failures.append(
                        f"fixture {fixture.get('task_id')}: leakage phrase "
                        f"{phrase!r} in surface text")

    # firing alone predicts neither target action above 0.50 in the balanced
    # family: among firing fixtures, neither matching stratum may dominate
    total_fires = fires_by_stratum["match_mismatch"] + fires_by_stratum["match_commit"]
    if total_fires:
        for stratum in c.TRIGGER_MATCHING_STRATA:
            share = fires_by_stratum[stratum] / total_fires
            if share > 0.5:
                failures.append(
                    f"firing predicts {stratum} at {share:.3f} > 0.50")

    return FamilyValidityResult(ok=not failures, failures=tuple(failures))
