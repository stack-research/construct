"""Production §10.2 answer+route realization collapse — P2 (Sol's assignment).

The wire era had NO decision-capable default detector (efc_runner resolution
D): real contact refused until the route projection was separately pinned.
This module is that pin. It derives a **route realization** exclusively from
harness-authored, replayable §13 ledger rows — never from model claims — and
combines it with the exact raw UTF-8 answer SHA-256 the controller recorded
at `model_action` time.

Projection contract (declarative; hashed into the detector contract):

- INCLUDED (the decision-relevant path): activation outcome (`trigger_fires`,
  `forced_inactive`); the external-check realization
  (started+completed vs silent); the treatment class (named check vs pinned
  placebo insertion vs none, with the normalized silent reason); the
  check-evidence identity when a named check ran (`check_id`,
  `comparison_rule_id`); the model-action/commit path; and the canonical
  event-kind order.
- EXCLUDED (must not create fake route diversity, §10.2): volatile event ids,
  timestamps, token counts (`model_prompt_tokens`, `model_completion_tokens`,
  `controller_source_read_tokens`, `check_output_tokens`,
  `governance_steps`), the world-oracle outcome, `cost_recompute` payloads,
  and every fixture-identity-bearing value — `fixture_id`, `event_id`,
  `trigger_result_sha256`, `placebo_sha256`, and the evidence verdict
  `scope_matches` (which is derived from the fixture's pinned scope and would
  make every trigger-matching lane collapse-immune by construction). The
  verdict still reaches the model through the prompt, so a degenerate engine
  that ignores it and emits one realization anyway IS detected.

Lane identity is the GROUPING key, never a route component. A T=0.5 branch is
collapsed iff, for every populated lane/leg, all K=5 distinct fixture runs
produce exactly one identical (answer hash, route hash) realization. Any
malformed, missing, duplicate, or out-of-order route evidence refuses —
fail-closed, never a silent pass.

Zero network. Nothing here authorizes contact.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from harness import efc_contracts as c
from harness.efc_runner import PinnedCollapseDetector

ROOT = Path(__file__).resolve().parents[1]
MODULE_REL = "harness/efc_collapse_production.py"

DETECTOR_ID = "efc_production_collapse_v1"
PROJECTION_ID = "efc_production_route_projection_v1"
SCHEMA_VERSION = "efc_production_collapse_contract_v1"

COLLAPSE_PIN_REL = ("corpus/efc_calibration/authoring_c4/"
                    "p2_production_collapse_contract.json")

# canonical §2.3 group shapes: exactly one of these two event-kind sequences
_SHAPE_CHECKED = ("activation_evaluated", "external_check_started",
                  "external_check_completed", "model_action", "task_commit",
                  "world_oracle_score", "cost_recompute")
_SHAPE_SILENT = ("activation_evaluated", "external_check_silent",
                 "model_action", "task_commit", "world_oracle_score",
                 "cost_recompute")

_SILENT_REASONS = ("placebo_treatment", "forced_inactive", "trigger_silent",
                   "lane_has_no_controller_check")


class RouteProjectionError(ValueError):
    """Route evidence outside the pinned §10.2 projection. Fail-closed."""


def _refuse(msg: str) -> None:
    raise RouteProjectionError(msg)


def sha256_canon(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def project_route(rows) -> dict:
    """Project one group's §13 rows onto the pinned route realization.

    Consumes only harness-authored, replayable execution facts. Refuses any
    malformed, missing, duplicate, or out-of-order evidence."""
    rows = list(rows)
    if not rows:
        _refuse("route projection over zero rows")
    kinds = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("payload"),
                                                       dict):
            _refuse(f"rows[{i}] is not a §13 row")
        kind = row.get("event_type")
        if not isinstance(kind, str) or not kind:
            _refuse(f"rows[{i}] carries no event_type")
        kinds.append(kind)
    kinds_t = tuple(kinds)
    if kinds_t == _SHAPE_CHECKED:
        checked = True
    elif kinds_t == _SHAPE_SILENT:
        checked = False
    else:
        _refuse(f"event-kind order {kinds} matches neither canonical §2.3 "
                "group shape (missing/duplicate/out-of-order/unknown route "
                "evidence refuses)")

    by_kind = {row["event_type"]: row for row in rows}
    activation = by_kind["activation_evaluated"]["payload"]
    for key in ("trigger_fires", "forced_inactive"):
        if not isinstance(activation.get(key), bool):
            _refuse(f"activation_evaluated payload lacks boolean {key!r}")

    if checked:
        completed = by_kind["external_check_completed"]["payload"]
        check_id = completed.get("check_id")
        rule_id = completed.get("comparison_rule_id")
        if not isinstance(check_id, str) or not check_id \
                or not isinstance(rule_id, str) or not rule_id:
            _refuse("external_check_completed payload lacks the check "
                    "evidence identity (check_id, comparison_rule_id)")
        external = {
            "realization": "started_completed",
            "treatment_class": "named_check",
            "silent_reason": None,
            "evidence_identity": {"check_id": check_id,
                                  "comparison_rule_id": rule_id},
        }
    else:
        silent = by_kind["external_check_silent"]["payload"]
        reason = silent.get("reason")
        if reason not in _SILENT_REASONS:
            _refuse(f"external_check_silent reason {reason!r} outside the "
                    f"frozen vocabulary {_SILENT_REASONS}")
        treatment = ("pinned_placebo_evidence"
                     if reason == "placebo_treatment" else "none")
        external = {
            "realization": "silent",
            "treatment_class": treatment,
            "silent_reason": reason,
            "evidence_identity": None,
        }

    return {
        "projection_id": PROJECTION_ID,
        "activation": {
            "trigger_fires": activation["trigger_fires"],
            "forced_inactive": activation["forced_inactive"],
        },
        "external_check": external,
        "action_path": ["model_action", "task_commit"],
        "event_kind_order": list(kinds_t),
    }


def route_realization_sha256(rows) -> str:
    return sha256_canon(project_route(rows))


def answer_sha256_from_rows(rows) -> str:
    """The exact raw UTF-8 answer hash the controller recorded — a
    harness-authored execution fact, never a model claim."""
    actions = [row for row in rows
               if isinstance(row, dict)
               and row.get("event_type") == "model_action"]
    if len(actions) != 1:
        _refuse(f"group must carry exactly one model_action row; "
                f"got {len(actions)}")
    answer = actions[0].get("payload", {}).get("answer_sha256")
    if not isinstance(answer, str) or len(answer) != 64:
        _refuse("model_action payload lacks a well-formed answer_sha256")
    return answer


def realization_sha256(run) -> str:
    """One run's (answer hash, route hash) realization identity. Fixture
    identity does not enter (§10.2)."""
    rows = getattr(run, "rows", None)
    if rows is None:
        _refuse("collapse input lacks §13 rows")
    return sha256_canon({
        "answer_sha256": answer_sha256_from_rows(rows),
        "route_sha256": route_realization_sha256(rows),
    })


def branch_collapsed(runs, k: int = c.CALIBRATION_K,
                     stratum_of=None) -> bool:
    """§10.2 branch collapse over one pass.

    Grouping is stratum x lane/leg within one engine branch — §10.2 pins
    `K = 5` distinct fixture identities per STRATUM x lane x branch, so an
    analog lane spanning three strata partitions into three groups of K.
    `stratum_of(fixture_id)` supplies the pinned packet's stratum for each
    fixture (harness-authored, hash-bound bytes — never model claims); when
    omitted, every fixture is one implicit stratum and the group key is the
    lane alone (single-stratum inputs such as conformance vectors).

    Every populated group must carry exactly `k` DISTINCT fixture
    identities; the branch is collapsed iff every populated group has
    exactly one (answer, route) realization."""
    runs = list(runs)
    if not runs:
        _refuse("collapse detection over zero runs")
    groups: dict[tuple, dict[str, str]] = {}
    for run in runs:
        lane = getattr(run, "lane", None)
        fixture_id = getattr(run, "fixture_id", None)
        if not isinstance(lane, str) or not lane \
                or not isinstance(fixture_id, str) or not fixture_id:
            _refuse("collapse input lacks harness-authored lane/fixture "
                    "identity")
        if stratum_of is None:
            stratum = None
        else:
            stratum = stratum_of(fixture_id)
            if not isinstance(stratum, str) or not stratum:
                _refuse(f"no pinned stratum for fixture {fixture_id!r}")
        group = groups.setdefault((stratum, lane), {})
        if fixture_id in group:
            _refuse(f"duplicate fixture {fixture_id!r} in group "
                    f"{(stratum, lane)!r}: repeated draws may not enter "
                    "collapse detection (§10.2)")
        group[fixture_id] = realization_sha256(run)
    for key, group in groups.items():
        if len(group) != k:
            _refuse(f"group {key!r} carries {len(group)} distinct "
                    f"fixtures; the declared pass requires exactly K={k}")
    return all(len(set(group.values())) == 1
               for group in groups.values())


# ---------------------------------------------------------------------------
# Pinned detector contract + conformance vectors.
# ---------------------------------------------------------------------------

def production_collapse_contract_payload(root: Path = ROOT) -> dict:
    return {
        "detector_id": DETECTOR_ID,
        "schema_version": SCHEMA_VERSION,
        "projection_id": PROJECTION_ID,
        "spec_clause": "SPEC_EPISTEMIC_FRAME_CHECK_V0 §10.2",
        "realization": "sha256_canonical({answer_sha256, route_sha256}); "
                       "answer is the exact raw UTF-8 answer SHA-256 the "
                       "controller recorded at model_action",
        "route_source": "harness-authored replayable §13 ledger rows only; "
                        "never model claims",
        "route_included": [
            "activation outcome (trigger_fires, forced_inactive)",
            "external-check realization (started+completed vs silent)",
            "treatment class (named_check vs pinned_placebo_evidence vs "
            "none) with normalized silent reason",
            "check-evidence identity when a named check ran "
            "(check_id, comparison_rule_id)",
            "model-action/commit path",
            "canonical event-kind order",
        ],
        "route_excluded": [
            "event ids", "timestamps", "token counts",
            "governance_steps", "world-oracle outcome",
            "cost_recompute payloads", "fixture identity",
            "trigger_result_sha256 (fixture-derived)",
            "placebo_sha256 (fixture-pinned bytes)",
            "scope_matches (fixture-scope-derived; including it would make "
            "trigger-matching lanes collapse-immune by construction — the "
            "verdict still reaches the model via the prompt, so a "
            "degenerate single-realization engine is detected regardless)",
        ],
        "grouping": "stratum x lane/leg within one engine branch (§10.2 "
                    "pins K per stratum x lane x branch); the stratum comes "
                    "from the pinned packet's fixture bytes; lane/stratum "
                    "are grouping keys, never route components",
        "calibration_k": c.CALIBRATION_K,
        "collapse_rule": "branch collapsed iff every populated lane/leg has "
                         "exactly one identical (answer, route) realization "
                         "across its K distinct fixture runs",
        "refusals": "malformed, missing, duplicate, or out-of-order route "
                    "evidence refuses; duplicate fixture in a lane refuses; "
                    "lane cardinality != K refuses; zero runs refuse",
        "t07_rule": "exactly one same-identity diagnostic pass at T=0.7 is "
                    "authorized only if T=0.5 collapses; probes are never "
                    "rerun; continued collapse is point_mode_diagnostic, "
                    "not admission evidence",
        "implementation_module": MODULE_REL,
        "implementation_module_sha256": hashlib.sha256(
            (root / MODULE_REL).read_bytes()).hexdigest(),
    }


def production_collapse_contract_hash(root: Path = ROOT) -> str:
    return sha256_canon(production_collapse_contract_payload(root))


def build_production_collapse_detector(root: Path = ROOT, stratum_of=None
                                       ) -> PinnedCollapseDetector:
    """`stratum_of` binds the pinned packet's fixture->stratum mapping into
    the detect operation; it never enters the contract identity (grouping
    keys are not route components)."""
    def detect(runs):
        return branch_collapsed(runs, stratum_of=stratum_of)
    return PinnedCollapseDetector(
        detector_id=DETECTOR_ID,
        contract=production_collapse_contract_payload(root),
        detect=detect)


# --- conformance vectors ----------------------------------------------------

def _row(kind: str, payload: dict) -> dict:
    return {"event_id": f"vector.{kind}", "event_type": kind,
            "fixture_id": None, "lane": None, "payload": payload}


def _group(checked: bool, answer: str, trigger_fires: bool = True,
           silent_reason: str = "trigger_silent", rule_id: str = "rule-x",
           prompt_tokens: int = 100, oracle_passed: bool = True,
           kinds: tuple | None = None) -> list[dict]:
    answer_hash = hashlib.sha256(answer.encode("utf-8")).hexdigest()
    if checked:
        rows = [
            _row("activation_evaluated", {"trigger_fires": trigger_fires,
                                          "forced_inactive": False,
                                          "governance_steps": 2}),
            _row("external_check_started", {}),
            _row("external_check_completed", {"check_id": c.CHECK_ID,
                                              "comparison_rule_id": rule_id,
                                              "controller_source_read_tokens":
                                                  77,
                                              "check_output_tokens": 33}),
        ]
    else:
        rows = [
            _row("activation_evaluated", {"trigger_fires": trigger_fires,
                                          "forced_inactive": False,
                                          "governance_steps": 1}),
            _row("external_check_silent", {"reason": silent_reason}),
        ]
    rows += [
        _row("model_action", {"answer_sha256": answer_hash,
                              "model_prompt_tokens": prompt_tokens,
                              "model_completion_tokens": 40}),
        _row("task_commit", {}),
        _row("world_oracle_score", {"passed": oracle_passed}),
        _row("cost_recompute", {"decision_tokens": prompt_tokens + 40}),
    ]
    if kinds is not None:
        rows = [rows[i] for i in kinds]
    return rows


def conformance_vectors() -> list[dict]:
    """Deterministic §10.2 vectors, pinned by hash in the contract artifact.

    Includes the two Sol-required directions: answer-only would falsely
    declare collapse but route diversity clears it; fixture identities differ
    but realizations correctly collapse."""
    k = c.CALIBRATION_K

    def runs(spec):
        return [{"lane": lane, "fixture_id": fid, "rows": rows}
                for lane, fid, rows in spec]

    same = "the same answer text"
    vectors = [
        {
            "name": "answer_only_false_positive_cleared_by_route_diversity",
            "expect": "not_collapsed",
            "runs": runs([("C_controlled_check", f"fx-{i}",
                           _group(checked=(i < 3), answer=same))
                          for i in range(k)]),
            "note": "identical answers everywhere; an answer-only detector "
                    "would falsely declare collapse; route diversity "
                    "(started+completed vs silent) correctly clears it",
        },
        {
            "name": "fixture_ids_differ_but_realizations_collapse",
            "expect": "collapsed",
            "runs": runs([("A_always_check", f"fx-{i}",
                           _group(checked=True, answer=same))
                          for i in range(k)]),
            "note": "K distinct fixture identities, one realization: "
                    "fixture identity must not enter the hash, so this "
                    "correctly collapses",
        },
        {
            "name": "volatile_fields_do_not_create_fake_diversity",
            "expect": "collapsed",
            "runs": runs([("S0_no_check", f"fx-{i}",
                           _group(checked=False, answer=same,
                                  prompt_tokens=100 + i,
                                  oracle_passed=(i % 2 == 0)))
                          for i in range(k)]),
            "note": "token counts and oracle outcomes differ per run; "
                    "neither may enter the realization",
        },
        {
            "name": "genuine_answer_diversity_clears",
            "expect": "not_collapsed",
            "runs": runs([("S0_no_check", f"fx-{i}",
                           _group(checked=False, answer=f"answer {i}"))
                          for i in range(k)]),
        },
        {
            "name": "stratum_grouping_partitions_a_multi_stratum_lane",
            "expect": "collapsed",
            "runs": [{"lane": "A_always_check",
                      "fixture_id": f"{stratum}-{i}",
                      "stratum": stratum,
                      "rows": _group(checked=True,
                                     answer=f"answer for {stratum}")}
                     for stratum in ("s-a", "s-b", "s-c")
                     for i in range(k)],
            "note": "one lane spanning three strata of K fixtures each; "
                    "realizations are uniform within each stratum group "
                    "(though different across strata), so §10.2 collapses; "
                    "without stratum grouping this 15-fixture lane would "
                    "be misjudged",
        },
        {
            "name": "stratum_grouping_detects_within_group_diversity",
            "expect": "not_collapsed",
            "runs": [{"lane": "A_always_check",
                      "fixture_id": f"{stratum}-{i}",
                      "stratum": stratum,
                      "rows": _group(checked=True,
                                     answer=("odd one out"
                                             if (stratum, i) == ("s-c", 0)
                                             else same))}
                     for stratum in ("s-a", "s-b", "s-c")
                     for i in range(k)],
        },
        {
            "name": "out_of_order_route_evidence_refuses",
            "expect": "refusal",
            "runs": runs([("S0_no_check", f"fx-{i}",
                           _group(checked=False, answer=same,
                                  kinds=(1, 0, 2, 3, 4, 5)))
                          for i in range(k)]),
        },
        {
            "name": "missing_route_evidence_refuses",
            "expect": "refusal",
            "runs": runs([("S0_no_check", f"fx-{i}",
                           _group(checked=False, answer=same,
                                  kinds=(0, 1, 3, 4, 5)))
                          for i in range(k)]),
        },
        {
            "name": "duplicate_fixture_in_lane_refuses",
            "expect": "refusal",
            "runs": runs([("S0_no_check", "fx-0",
                           _group(checked=False, answer=same))
                          for _ in range(k)]),
        },
        {
            "name": "lane_cardinality_not_k_refuses",
            "expect": "refusal",
            "runs": runs([("S0_no_check", f"fx-{i}",
                           _group(checked=False, answer=same))
                          for i in range(k - 1)]),
        },
        {
            "name": "zero_runs_refuse",
            "expect": "refusal",
            "runs": [],
        },
    ]
    return vectors


def run_conformance_vectors() -> list[dict]:
    results = []
    for vector in conformance_vectors():
        wrapped = [SimpleNamespace(**run) for run in vector["runs"]]
        strata = {run["fixture_id"]: run["stratum"]
                  for run in vector["runs"] if "stratum" in run}
        stratum_of = strata.get if strata else None
        try:
            outcome = "collapsed" \
                if branch_collapsed(wrapped, stratum_of=stratum_of) \
                else "not_collapsed"
        except RouteProjectionError:
            outcome = "refusal"
        results.append({"name": vector["name"], "expect": vector["expect"],
                        "observed": outcome,
                        "ok": outcome == vector["expect"]})
    return results


def collapse_pin_payload(root: Path = ROOT) -> dict:
    results = run_conformance_vectors()
    if not all(r["ok"] for r in results):
        _refuse(f"conformance vectors do not hold: "
                f"{[r for r in results if not r['ok']]}")
    contract = production_collapse_contract_payload(root)
    return {
        "schema_version": "efc_p2_collapse_contract_pin_v1",
        "assignment": "P2 production collapse contract (pre-contact pin)",
        "seat": "claude/fable-5",
        "detector_contract": contract,
        "detector_contract_sha256": sha256_canon(contract),
        "conformance_vectors_sha256": sha256_canon(conformance_vectors()),
        "conformance_results": results,
        "disclosure": {
            "engines_contacted": 0, "listing_calls": 0, "probes_run": 0,
            "network_calls": 0, "real_inference_calls": 0,
        },
        "authorizes_calibration_contact": False,
    }


def write_collapse_pin(root: Path = ROOT) -> dict:
    payload = collapse_pin_payload(root)
    path = root / COLLAPSE_PIN_REL
    data = json.dumps(payload, indent=1, sort_keys=True) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != data:
            _refuse(f"conflicting existing {COLLAPSE_PIN_REL}: append-only "
                    "surface refuses overwrite")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")
    payload["pin_path"] = COLLAPSE_PIN_REL
    payload["pin_sha256"] = hashlib.sha256(
        path.read_bytes()).hexdigest()
    return payload


def verify_collapse_pin(root: Path = ROOT) -> dict:
    path = root / COLLAPSE_PIN_REL
    if not path.is_file():
        _refuse(f"missing collapse contract pin {COLLAPSE_PIN_REL}")
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    expected = collapse_pin_payload(root)
    if on_disk != expected:
        _refuse("collapse contract pin does not recompute from current "
                "bytes (module or vector drift)")
    return {"verified": True,
            "detector_contract_sha256": expected["detector_contract_sha256"]}
