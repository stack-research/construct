"""Pause-episode harness — SPEC_WARMING_BUDGET v0.1 §3/§4 against population -r2.

Arms the prospective triggers: for EVERY moved-eligible unit in the stamped
population (arithmetic over the `frontier_terminal` flag — no selection, no
inspection), mints the deterministic compact resume state and stamps a
witnessed `trigger_precommit` citing the population's precommitted match rule.

Chronology (§4): these rows must exist BEFORE the world moves. From this stamp
forward, any IESG transition on a precommitted unit is a scoreable moved-leg
candidate; any transition on a unit WITHOUT a precommit is unusable for the
moved leg, permanently. That is why this runs today and not when the calendar
obliges.

The compact state is minted under the §3 input closure from artifacts that
exist at pause time: the unit's T0 route catalog, the (v0: empty) M1 sidecar,
a deterministic pause question, and the population's frontier tag. The pause
QUESTION is fixed per unit ("current IESG lifecycle status of <draft> and
whether prior work remains valid") so the engine episode, when it runs, resumes
against a state that was frozen before anyone knew which units would move.

`frontier_unresolved_attested`: stamped true for non-terminal units directly
from the population's T0 `iesg_states` — a mechanical check against the same
snapshot the precommit binds, not an oracle opinion.

watch: re-fetches the live status slices, diffs the transition-only projection
against T0, and appends `world_move` + `t1_catalog_materialized` rows for any
unit whose `iesg_states` changed. Datatracker's own `time` field is the
external stream timestamp, so a late check never corrupts chronology — the
world stamps its own movement.

Usage:
  python -m harness.wb_pause arm       # mint + precommit all moved-eligible units
  python -m harness.wb_pause watch     # T1 check: diff live slices against T0
  python -m harness.wb_pause status
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from .ledger import Ledger
from .score_warming import mint_compact_state
from .wb_population import API, LEDGER as POP_LEDGER, T0_DIR, _get

REPO = Path(__file__).resolve().parent.parent
WB_DIR = REPO / "runs" / "wb"
PAUSE_LEDGER = WB_DIR / "pause_precommit.jsonl"
WATCH_LEDGER = WB_DIR / "watch.jsonl"


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def _population() -> tuple[dict, list[dict]]:
    rows = Ledger(POP_LEDGER).rows()
    pop = [r for r in rows if r.get("kind") == "population_precommit"][-1]
    units = next(r["units"] for r in reversed(rows)
                 if r.get("kind") == "population_units"
                 and r["population_id"] == pop["population_id"])
    return pop, units


def arm() -> dict:
    pop, units = _population()
    ledger = Ledger(PAUSE_LEDGER)
    done = {r["unit_id"] for r in ledger.rows()
            if r.get("kind") == "trigger_precommit"
            and r.get("population_id") == pop["population_id"]}
    armed, skipped_terminal = [], 0
    for u in units:
        if u["frontier_terminal"]:
            skipped_terminal += 1
            continue
        if u["unit_id"] in done:
            continue
        state = mint_compact_state(
            route_catalog_t0=u["route_catalog"],
            m1_sidecar={},  # v0 pause: no prior episode; disclosed, not hidden
            pause_question_id=f"wbq:{u['unit_id']}",
            unresolved_frontier_tag=pop["unresolved_frontier_enum"][0],
            route_hint=[f"status:{u['unit_id']}"],
            trigger_key=f"official_status_changed:{u['status_key']}",
            discard_rule="discard after the certificate surface is read at T1",
            population=pop)
        state["kind"] = "compact_resume_state_minted"
        state["unit_id"] = u["unit_id"]
        state["population_id"] = pop["population_id"]
        # mechanical attestation from the same T0 snapshot the precommit binds
        state["frontier_unresolved_attested"] = not u["frontier_terminal"]
        ledger.write({k: v for k, v in state.items() if k != "ts"})
        ledger.write({
            "kind": "trigger_precommit", "unit_id": u["unit_id"],
            "population_id": pop["population_id"],
            "status_key": u["status_key"],
            "match_rule_ref": pop["status_vocabulary_hash"],
            "external_stream_ref": u["route_catalog"][f"status:{u['unit_id']}"]["url"],
            "catalog_hash": _sha(sorted(u["route_catalog"])),
            "pause_artifact_hash": state["input_digest"],
            "t0_sha256": u["t0_sha256"],
            # the harness stamps precommit_ts — recorded explicitly so score-time
            # comparison against external_ts needs no ledger parsing
            "precommit_ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        armed.append(u["unit_id"])
    return {"population_id": pop["population_id"], "armed_now": len(armed),
            "already_armed": len(done), "skipped_frontier_terminal": skipped_terminal,
            "total_precommitted": len(done) + len(armed)}


def watch() -> dict:
    """T1 check. Diffs the live transition-only projection against T0 for every
    precommitted unit; ledgers world_move + t1_catalog_materialized on change.
    The external timestamp is Datatracker's own `time` field on the document."""
    from .wb_population import _canonical_status_slice, STATE_QUERY
    pop, units = _population()
    id_to_slug = {s["id"]: s["slug"] for s in _get(STATE_QUERY)["objects"]}
    pause_rows = Ledger(PAUSE_LEDGER).rows()
    precommitted = {r["unit_id"]: r for r in pause_rows
                    if r.get("kind") == "trigger_precommit"}
    wl = Ledger(WATCH_LEDGER)
    already_moved = {r["unit_id"] for r in wl.rows() if r.get("kind") == "world_move"}
    moved, checked = [], 0
    for u in units:
        if u["unit_id"] not in precommitted or u["unit_id"] in already_moved:
            continue
        checked += 1
        doc = _get(f"/doc/document/{u['unit_id']}/?format=json")
        t1_slice = _canonical_status_slice(doc, id_to_slug)
        t1_text = json.dumps(t1_slice, sort_keys=True)
        t0_text = (T0_DIR / f"{u['unit_id']}.json").read_text()
        if t1_text == t0_text:
            continue
        (WB_DIR / "t1").mkdir(parents=True, exist_ok=True)
        (WB_DIR / "t1" / f"{u['unit_id']}.json").write_text(t1_text)
        wl.write({"kind": "world_move", "unit_id": u["unit_id"],
                  "population_id": pop["population_id"],
                  "subject": u["status_key"],
                  "external_ts": doc["time"],   # the world stamps its own movement
                  "iesg_states_t0": json.loads(t0_text)["iesg_states"],
                  "iesg_states_t1": t1_slice["iesg_states"],
                  "t1_sha256": hashlib.sha256(t1_text.encode()).hexdigest()})
        wl.write({"kind": "t1_catalog_materialized", "unit_id": u["unit_id"],
                  "population_id": pop["population_id"],
                  "surfaces": sorted(u["route_catalog"]),
                  "disclosure": "symmetric: ALL branches receive the T1 catalog; "
                                "the trigger may only affect queue order (SPEC §4)"})
        moved.append({"unit": u["unit_id"],
                      "t0": json.loads(t0_text)["iesg_states"],
                      "t1": t1_slice["iesg_states"]})
    return {"checked": checked, "moved_this_check": moved,
            "moved_total": len(already_moved) + len(moved)}


def status() -> dict:
    pop, units = _population()
    pause_rows = Ledger(PAUSE_LEDGER).rows()
    pre = sum(1 for r in pause_rows if r.get("kind") == "trigger_precommit")
    moves = [r for r in Ledger(WATCH_LEDGER).rows() if r.get("kind") == "world_move"]
    return {"population_id": pop["population_id"],
            "moved_eligible": sum(1 for u in units if not u["frontier_terminal"]),
            "triggers_precommitted": pre,
            "world_moves_observed": len(moves),
            "moved_units": [m["unit_id"] for m in moves]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["arm", "watch", "status"])
    args = ap.parse_args()
    out = {"arm": arm, "watch": watch, "status": status}[args.cmd]()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
