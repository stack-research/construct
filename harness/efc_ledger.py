"""External ledger rows, canonical event order, and deterministic cost replay
— SPEC_EPISTEMIC_FRAME_CHECK_V0 §13, §2.3/§5.3 (order), §10.1 (cost).

Logged claims are untrusted (§13): every score-time consumer recomputes the
trigger result, event order, and deterministic costs from the rows and the
fixture surface. Any structural hole, duplicate event identity, or
score-order inversion fails closed — the group is refused, not repaired.

The §2.3 boundary is the load-bearing invariant: a candidate check must
COMPLETE before model action and commitment. A completion logged after
model_action is a post-answer annotation; it can never enter a win path, and
for §9.1 family validity it is an ordering failure.

§10.1 ceilings are hard: exceeding one is a loss, not a tunable warning. The
replay surfaces `ceiling_violations` for the §9 verdict layer to convert into
the loss outcome; nothing here averages or waives them.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from harness import efc_contracts as c
from harness.efc_trigger import trigger_result_record

_ID = re.compile(r"^[A-Za-z0-9._/:+-]{1,128}$")

# canonical §2.3 order per fixture x lane group, in §13 row vocabulary
_GROUP_REQUIRED = ("activation_evaluated", "model_action", "task_commit",
                   "world_oracle_score", "cost_recompute")
_CANONICAL_INDEX = {
    "activation_evaluated": 0,
    "external_check_started": 1,
    "external_check_silent": 1,
    "external_check_completed": 2,
    "model_action": 3,
    "task_commit": 4,
    "world_oracle_score": 5,
    "cost_recompute": 6,
}
# suite-level rows that never belong to a fixture group
_RUN_LEVEL = ("run_config", "contract_precommit", "engine_admission_verdict",
              "source_causal_verdict", "disposition_minted",
              "disposition_mint_refused", "provenance_revision",
              "authorization_verdict", "typed_cell_verdict",
              "untrusted_nomination")


class LedgerContractError(ValueError):
    """Row outside the closed §13 vocabulary. Fail-closed."""


def make_row(event_id: str, event_type: str, fixture_id: str | None = None,
             lane: str | None = None, payload: dict | None = None) -> dict:
    row = {"event_id": event_id, "event_type": event_type,
           "fixture_id": fixture_id, "lane": lane,
           "payload": dict(payload or {})}
    validate_event_row(row)
    return row


def validate_event_row(row: dict) -> None:
    event_id = row.get("event_id")
    if not isinstance(event_id, str) or not _ID.fullmatch(event_id):
        raise LedgerContractError(f"event_id {event_id!r} is not a compact id")
    event_type = row.get("event_type")
    if event_type not in c.EVENT_TYPES:
        raise LedgerContractError(
            f"event_type {event_type!r} outside the §13 row vocabulary")
    if not isinstance(row.get("payload", {}), dict):
        raise LedgerContractError("payload must be a dict")
    if event_type in _CANONICAL_INDEX:
        for key in ("fixture_id", "lane"):
            value = row.get(key)
            if not isinstance(value, str) or not _ID.fullmatch(value):
                raise LedgerContractError(
                    f"{event_type} row needs a compact {key}, got {value!r}")


# ---------------------------------------------------------------------------
# §10.1 deterministic cost.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CostReplay:
    decision_tokens: int
    governance_steps: int
    controller_source_read_tokens: int
    check_output_tokens: int
    check_invocations: int
    ceiling_violations: tuple[str, ...]
    matches_logged_claim: bool


def _int_field(payload: dict, key: str, failures: list[str],
               default: int = 0) -> int:
    value = payload.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        failures.append(f"{key} must be a non-negative integer, got {value!r}")
        return 0
    return value


def recompute_cost(group_rows: list[dict], failures: list[str]) -> CostReplay:
    """decision_tokens = model_prompt_tokens + model_completion_tokens
    + controller_source_read_tokens (§10.1). Evidence rendered to the model is
    already inside model_prompt_tokens and is never added twice; governance
    steps are reported separately and only break token ties."""
    by_type: dict[str, list[dict]] = {}
    for row in group_rows:
        by_type.setdefault(row["event_type"], []).append(row)

    prompt = completion = controller_read = check_out = 0
    governance = 0
    for row in by_type.get("model_action", []):
        prompt = _int_field(row["payload"], "model_prompt_tokens", failures)
        completion = _int_field(row["payload"], "model_completion_tokens", failures)
    for row in by_type.get("activation_evaluated", []):
        governance = _int_field(row["payload"], "governance_steps", failures)
    for row in by_type.get("external_check_completed", []):
        controller_read = _int_field(row["payload"],
                                     "controller_source_read_tokens", failures)
        check_out = _int_field(row["payload"], "check_output_tokens", failures)
    invocations = len(by_type.get("external_check_started", []))

    decision_tokens = prompt + completion + controller_read
    violations = []
    if invocations > c.MAX_CHECK_INVOCATIONS_PER_TASK:
        violations.append(f"check invocations {invocations} > "
                          f"{c.MAX_CHECK_INVOCATIONS_PER_TASK}")
    if controller_read > c.MAX_CONTROLLER_SOURCE_READ_TOKENS:
        violations.append(f"controller_source_read_tokens {controller_read} > "
                          f"{c.MAX_CONTROLLER_SOURCE_READ_TOKENS}")
    if check_out > c.MAX_EXTERNAL_CHECK_OUTPUT_TOKENS:
        violations.append(f"check_output_tokens {check_out} > "
                          f"{c.MAX_EXTERNAL_CHECK_OUTPUT_TOKENS}")
    if governance > c.MAX_GOVERNANCE_STEPS_PER_TASK:
        violations.append(f"governance_steps {governance} > "
                          f"{c.MAX_GOVERNANCE_STEPS_PER_TASK}")

    matches = True
    for row in by_type.get("cost_recompute", []):
        claimed = _int_field(row["payload"], "decision_tokens", failures)
        if claimed != decision_tokens:
            matches = False
            failures.append(
                f"cost_recompute claims {claimed} decision tokens; replay "
                f"computes {decision_tokens} — logged claims are untrusted")
    return CostReplay(decision_tokens, governance, controller_read, check_out,
                      invocations, tuple(violations), matches)


# ---------------------------------------------------------------------------
# Group replay: §2.3 order, §13 holes/duplicates, trigger recompute.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GroupReplay:
    fixture_id: str
    lane: str
    ok: bool
    failures: tuple[str, ...]
    cost: CostReplay
    post_answer_annotation: bool  # completion after model_action (never a win path)


def replay_fixture_group(rows: list[dict], fixture: dict | None = None,
                         forced_inactive: bool = False) -> GroupReplay:
    """Replay one fixture x lane group in ledger order. `fixture` (when
    supplied) lets the replay recompute the §2.1 trigger result against the
    activation row's recorded hash. `forced_inactive` asserts the §8.2
    B_inactive contract: the control path is ledgered and silent."""
    failures: list[str] = []
    if not rows:
        return GroupReplay("?", "?", False, ("empty group",),
                           recompute_cost([], failures), False)
    for row in rows:
        validate_event_row(row)
    fixture_ids = {row["fixture_id"] for row in rows}
    lanes = {row["lane"] for row in rows}
    if len(fixture_ids) != 1 or len(lanes) != 1:
        failures.append(f"group mixes fixtures {fixture_ids} / lanes {lanes}")
    fixture_id, lane = rows[0]["fixture_id"], rows[0]["lane"]

    types = [row["event_type"] for row in rows]
    for required in _GROUP_REQUIRED:
        if required not in types:
            failures.append(f"structural hole: no {required} row")
    for event_type in set(types):
        if types.count(event_type) > 1:
            failures.append(f"duplicate {event_type} row in group")

    started = "external_check_started" in types
    silent = "external_check_silent" in types
    completed = "external_check_completed" in types
    if started and silent:
        failures.append("both external_check_started and external_check_silent")
    if not started and not silent:
        failures.append("structural hole: neither check_started nor check_silent")
    if started and not completed:
        failures.append("structural hole: check started but never completed")
    if completed and not started:
        failures.append("check completed without a start row")

    # canonical order over the append sequence (§2.3/§5.3)
    post_answer_annotation = False
    indices = [(row["event_type"], i) for i, row in enumerate(rows)]
    canonical = [_CANONICAL_INDEX[t] for t, _ in indices]
    if canonical != sorted(canonical):
        # locate the §2.3 boundary case for the honest specific message
        if completed:
            i_completed = types.index("external_check_completed")
            i_action = types.index("model_action") if "model_action" in types else -1
            if i_action != -1 and i_completed > i_action:
                post_answer_annotation = True
                failures.append(
                    "check completed AFTER model_action: post-answer checks "
                    "are annotation and cannot enter a win path (§2.3)")
        if "world_oracle_score" in types and "task_commit" in types:
            if types.index("world_oracle_score") < types.index("task_commit"):
                failures.append("score-order inversion: world_oracle_score "
                                "before task_commit")
        failures.append("event order violates the §2.3 canonical sequence")

    if forced_inactive:
        if started or completed:
            failures.append("B_inactive lane ran the check: control path must "
                            "be forcibly inactive and ledgered (§8.2)")
        activation = next((r for r in rows
                           if r["event_type"] == "activation_evaluated"), None)
        if activation is not None and not activation["payload"].get(
                "forced_inactive", False):
            failures.append("B_inactive activation row lacks the "
                            "forced_inactive ledger mark (§8.2)")

    if fixture is not None:
        activation = next((r for r in rows
                           if r["event_type"] == "activation_evaluated"), None)
        if activation is not None:
            recorded = activation["payload"].get("trigger_result_sha256")
            recomputed = hashlib.sha256(trigger_result_record(fixture)).hexdigest()
            if recorded != recomputed:
                failures.append(
                    "trigger result recompute mismatch: activation row is "
                    "not the deterministic §2.1 result of the fixture surface")

    cost = recompute_cost(rows, failures)
    if not cost.matches_logged_claim:
        pass  # failure message already appended by recompute_cost
    return GroupReplay(fixture_id, lane, not failures, tuple(failures), cost,
                       post_answer_annotation)


# ---------------------------------------------------------------------------
# Ledger-level replay: duplicates across groups, run preamble.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LedgerReplayResult:
    ok: bool
    failures: tuple[str, ...]
    groups: tuple[GroupReplay, ...] = field(default=())


def replay_ledger(rows: list[dict], fixtures: dict[str, dict] | None = None,
                  expected_contract_hashes: dict[str, str] | None = None,
                  ) -> LedgerReplayResult:
    """Whole-ledger replay. Contract hashes, fixture hashes, oracle hashes,
    and seat identities are recorded before the relevant rows are opened
    (§4/§5.2): the preamble rows must precede every fixture row, and their
    hashes must match the expected precommit."""
    failures: list[str] = []
    for row in rows:
        validate_event_row(row)
    seen: set[str] = set()
    for row in rows:
        if row["event_id"] in seen:
            failures.append(f"duplicate event identity {row['event_id']!r}")
        seen.add(row["event_id"])

    first_group_row = next((i for i, row in enumerate(rows)
                            if row["event_type"] in _CANONICAL_INDEX), None)
    for preamble_type in ("run_config", "contract_precommit"):
        idx = next((i for i, row in enumerate(rows)
                    if row["event_type"] == preamble_type), None)
        if idx is None:
            failures.append(f"structural hole: no {preamble_type} row")
        elif first_group_row is not None and idx > first_group_row:
            failures.append(f"{preamble_type} recorded after fixture rows "
                            "opened (§4: precommit precedes rows)")

    if expected_contract_hashes:
        precommit = next((row for row in rows
                          if row["event_type"] == "contract_precommit"), None)
        if precommit is not None:
            for name, expected in expected_contract_hashes.items():
                got = precommit["payload"].get(name)
                if got != expected:
                    failures.append(
                        f"contract_precommit {name} {got!r} != precommitted "
                        f"{expected!r}")

    groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        if row["event_type"] in _CANONICAL_INDEX:
            groups.setdefault((row["fixture_id"], row["lane"]), []).append(row)
    replays = []
    for (fixture_id, lane), group_rows in groups.items():
        fixture = (fixtures or {}).get(fixture_id)
        replay = replay_fixture_group(
            group_rows, fixture=fixture,
            forced_inactive=(lane == "B_inactive"))
        replays.append(replay)
        failures.extend(f"[{fixture_id}/{lane}] {msg}"
                        for msg in replay.failures)
    return LedgerReplayResult(ok=not failures, failures=tuple(failures),
                              groups=tuple(replays))
