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

Watch hardening (board review 2026-07-06, codex #1-#4 + composer):
  watch_checkpoint  — every watch run ledgers {checked, unchanged_digest,
    fetch_failures}: the silent leg becomes recorded evidence, never an
    unledgered absence. Silent/noise cells may only be scored against
    checkpoints, not against the mover-only rows of earlier runs.
  freeze            — full T1 route-packet freeze for moved units: canonical
    text + sha256 + token count for EVERY catalog surface. The status slice is
    frozen from detection (hash-bound to the world_move row); meta/body are
    fetched at freeze time and disclosed as such — churn between detection and
    freeze is disclosed by `as_of`, not hidden.
  external_ts_attestation — the IESG state history (statedocevent stream)
    attests the transition chain. `doc.time` is the document's LAST event of
    ANY type, not necessarily the IESG transition (sidrops-rpki-ccr: doc.time
    was an IANA Action event; the true iesg-eva exit was 16:26:29Z, two hops
    eva→approved→ann). Chronology is proven against the FIRST IESG event after
    precommit, and doc.time disagreement is recorded, not smoothed over.
  world_leg_at_watch — clarified in the population ledger: static noise-cohort
    pin only, never leg assignment; the observed world_move decides the leg.

Usage:
  python -m harness.wb_pause arm       # mint + precommit all moved-eligible units
  python -m harness.wb_pause watch     # T1 check: diff live slices against T0
  python -m harness.wb_pause freeze    # freeze full T1 packets for moved units
  python -m harness.wb_pause status
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

from .ledger import Ledger
from .score_warming import _tokens, mint_compact_state
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


def checkpoint_row(population_id: str, checked: int, moved: list[str],
                   unchanged: list[tuple[str, str]],
                   fetch_failures: list[dict]) -> dict:
    """The silent leg, ledgered positively (codex #1). `unchanged` is the sorted
    (unit_id, t1_sha256) list of units checked and NOT moved this run — its
    digest is what WB-silent-cost/WB-noise-misroute scoring may cite."""
    return {"kind": "watch_checkpoint", "population_id": population_id,
            "checked": checked, "moved_this_check": sorted(moved),
            "unchanged_count": len(unchanged),
            "unchanged_digest": _sha(sorted(unchanged)),
            "fetch_failures": fetch_failures,
            "t1_projection": "transition-only",
            "disclosure": "silent/noise legs are scoreable only against "
                          "checkpoint rows; absence of a world_move row in "
                          "earlier, checkpoint-less runs is not evidence"}


def watch() -> dict:
    """T1 check. Diffs the live transition-only projection against T0 for every
    precommitted unit; ledgers world_move + t1_catalog_materialized on change,
    and a watch_checkpoint row unconditionally. Per-unit fetch failures are
    recorded, never allowed to abort the sweep."""
    from .wb_population import _canonical_status_slice, STATE_QUERY
    pop, units = _population()
    id_to_slug = {s["id"]: s["slug"] for s in _get(STATE_QUERY)["objects"]}
    pause_rows = Ledger(PAUSE_LEDGER).rows()
    precommitted = {r["unit_id"]: r for r in pause_rows
                    if r.get("kind") == "trigger_precommit"}
    wl = Ledger(WATCH_LEDGER)
    already_moved = {r["unit_id"] for r in wl.rows() if r.get("kind") == "world_move"}
    moved, unchanged, failures, checked = [], [], [], 0
    for u in units:
        if u["unit_id"] not in precommitted or u["unit_id"] in already_moved:
            continue
        checked += 1
        try:
            doc = _get(f"/doc/document/{u['unit_id']}/?format=json")
        except Exception as e:  # noqa: BLE001 — recorded, never rescored as silent
            failures.append({"unit_id": u["unit_id"], "error": str(e)})
            continue
        t1_slice = _canonical_status_slice(doc, id_to_slug)
        t1_text = json.dumps(t1_slice, sort_keys=True)
        t1_sha = hashlib.sha256(t1_text.encode()).hexdigest()
        t0_text = (T0_DIR / f"{u['unit_id']}.json").read_text()
        if t1_text == t0_text:
            unchanged.append((u["unit_id"], t1_sha))
            continue
        (WB_DIR / "t1").mkdir(parents=True, exist_ok=True)
        (WB_DIR / "t1" / f"{u['unit_id']}.json").write_text(t1_text)
        wl.write({"kind": "world_move", "unit_id": u["unit_id"],
                  "population_id": pop["population_id"],
                  "subject": u["status_key"],
                  "external_ts": doc["time"],   # doc-level stamp; see attestation
                  "iesg_states_t0": json.loads(t0_text)["iesg_states"],
                  "iesg_states_t1": t1_slice["iesg_states"],
                  "t1_sha256": t1_sha})
        wl.write({"kind": "t1_catalog_materialized", "unit_id": u["unit_id"],
                  "population_id": pop["population_id"],
                  "surfaces": sorted(u["route_catalog"]),
                  "disclosure": "symmetric: ALL branches receive the T1 catalog; "
                                "the trigger may only affect queue order (SPEC §4)"})
        moved.append({"unit": u["unit_id"],
                      "t0": json.loads(t0_text)["iesg_states"],
                      "t1": t1_slice["iesg_states"]})
    wl.write(checkpoint_row(pop["population_id"], checked,
                            [m["unit"] for m in moved], sorted(unchanged),
                            failures))
    out = {"checked": checked, "moved_this_check": moved,
           "fetch_failures": len(failures),
           "moved_total": len(already_moved) + len(moved)}
    if moved:  # freeze at detection — the body surface is live until frozen
        out["freeze"] = freeze()
    return out


def freeze_packet_row(unit: dict, move_row: dict, status_text: str,
                      meta_text: str, body_text: str) -> dict:
    """Pure builder for the full-T1-freeze row (codex #2). Refuses a status
    slice that does not hash-match the world_move row — the frozen packet must
    be the SAME T1 the watch detected, or it is a different world."""
    status_sha = hashlib.sha256(status_text.encode()).hexdigest()
    if status_sha != move_row["t1_sha256"]:
        raise ValueError(
            f"status slice sha {status_sha[:12]} != world_move t1_sha256 "
            f"{move_row['t1_sha256'][:12]} for {unit['unit_id']} — refusing to "
            "freeze a T1 the watch did not detect")
    uid = unit["unit_id"]
    surfaces = {
        f"status:{uid}": {"sha256": status_sha, "tokens": _tokens(status_text),
                          "path": f"runs/wb/t1/{uid}.json", "as_of": "detection"},
        f"meta:{uid}": {"sha256": hashlib.sha256(meta_text.encode()).hexdigest(),
                        "tokens": _tokens(meta_text),
                        "path": f"runs/wb/t1/{uid}.meta.json", "as_of": "freeze"},
        f"body:{uid}": {"sha256": hashlib.sha256(body_text.encode()).hexdigest(),
                        "tokens": _tokens(body_text),
                        "path": f"runs/wb/t1/{uid}.body.html", "as_of": "freeze"},
    }
    if sorted(surfaces) != sorted(unit["route_catalog"]):
        raise ValueError(f"frozen surfaces diverge from the T0 route catalog "
                         f"for {uid} — symmetry requires the same surface set")
    return {"kind": "t1_route_packet_frozen", "unit_id": uid,
            "population_id": move_row["population_id"], "surfaces": surfaces,
            "disclosure": "status frozen from detection (hash-bound to the "
                          "world_move row); meta/body fetched at freeze time — "
                          "churn between detection and freeze is disclosed by "
                          "as_of, never hidden"}


def attestation_row(unit_id: str, population_id: str, precommit_ts: str,
                    external_ts: str, iesg_events: list[dict]) -> dict:
    """Pure builder for the external-ts attestation (codex #3). `iesg_events`
    are the draft-iesg statedocevent rows since precommit, oldest first:
    [{time, state_slug}]. doc.time is the document's last event of ANY type —
    the IESG state history is the stream that actually attests the transition.
    Chronology is proven against the FIRST IESG event after precommit; a
    doc.time that is not an IESG event time is recorded as disagreement."""
    times = [e["time"] for e in iesg_events]
    first = min(times) if times else None
    return {"kind": "external_ts_attestation", "unit_id": unit_id,
            "population_id": population_id,
            "source": f"/doc/statedocevent/?doc__name={unit_id} "
                      "(state_type=draft-iesg, client-filtered)",
            "iesg_events_since_precommit": iesg_events,
            "external_ts_ledgered": external_ts,
            "doc_time_is_iesg_event": external_ts in times,
            "first_iesg_event_ts": first,
            "precommit_ts": precommit_ts,
            "precommit_precedes_first_iesg_event":
                bool(first) and precommit_ts < first,
            "multi_hop": len(iesg_events) > 1}


def freeze() -> dict:
    """Freeze the full T1 route packet + IESG state-history attestation for
    every moved unit that lacks one. Idempotent; runs as soon after detection
    as possible — the body surface is live until frozen."""
    from .wb_population import STATE_QUERY
    pop, units = _population()
    by_id = {u["unit_id"]: u for u in units}
    id_to_slug = {s["id"]: s["slug"] for s in _get(STATE_QUERY)["objects"]}
    wl = Ledger(WATCH_LEDGER)
    rows = wl.rows()
    frozen = {r["unit_id"] for r in rows
              if r.get("kind") == "t1_route_packet_frozen"}
    precommits = {r["unit_id"]: r for r in Ledger(PAUSE_LEDGER).rows()
                  if r.get("kind") == "trigger_precommit"}
    out = []
    for move in [r for r in rows if r.get("kind") == "world_move"]:
        uid = move["unit_id"]
        if uid in frozen:
            continue
        u = by_id[uid]
        status_text = (WB_DIR / "t1" / f"{uid}.json").read_text()
        doc = _get(f"/doc/document/{uid}/?format=json")
        meta_text = json.dumps({"name": doc["name"], "rev": doc["rev"],
                                "time": doc["time"]}, sort_keys=True)
        with urllib.request.urlopen(
                u["route_catalog"][f"body:{uid}"]["url"], timeout=60) as r:
            body_text = r.read().decode("utf-8", errors="replace")
        (WB_DIR / "t1" / f"{uid}.meta.json").write_text(meta_text)
        (WB_DIR / "t1" / f"{uid}.body.html").write_text(body_text)
        wl.write(freeze_packet_row(u, move, status_text, meta_text, body_text))

        pre_ts = precommits[uid]["precommit_ts"]
        events = _get(f"/doc/statedocevent/?format=json&doc__name={uid}"
                      "&limit=50&order_by=-id")["objects"]
        iesg = sorted(
            ({"time": e["time"],
              "state_slug": id_to_slug.get(
                  int(e["state"].rstrip("/").rsplit("/", 1)[-1]), "?")}
             for e in events
             if e.get("state_type", "").rstrip("/").endswith("draft-iesg")
             and e.get("state") and e["time"] > pre_ts),
            key=lambda e: e["time"])
        wl.write(attestation_row(uid, pop["population_id"], pre_ts,
                                 move["external_ts"], iesg))
        out.append({"unit": uid, "iesg_events": iesg,
                    "doc_time_is_iesg_event": move["external_ts"]
                    in [e["time"] for e in iesg]})

    # world_leg_at_watch clarification (codex #4) — one appended row, once
    pop_ledger = Ledger(POP_LEDGER)
    if not any(r.get("kind") == "label_clarification"
               for r in pop_ledger.rows()):
        pop_ledger.write({
            "kind": "label_clarification",
            "population_id": pop["population_id"],
            "field": "world_leg_at_watch",
            "reading": "static noise-cohort pin (hash rule at precommit), "
                       "never leg assignment — the observed world_move decides "
                       "the leg (board review 2026-07-06, codex #4, composer "
                       "concurring)"})
    return {"frozen_now": out,
            "frozen_total": len(frozen) + len(out)}


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
    ap.add_argument("cmd", choices=["arm", "watch", "freeze", "status"])
    args = ap.parse_args()
    out = {"arm": arm, "watch": watch, "freeze": freeze,
           "status": status}[args.cmd]()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
