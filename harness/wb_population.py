"""IETF Datatracker population authoring — SPEC_WARMING_BUDGET v0.1 §2.

Authors the first prospective `population_precommit` for the warming-budget
instrument: a BRANCH-BLIND enumeration of every `draft-ietf-*` Internet-Draft
currently in a non-terminal IESG state, snapshotted at T0.

Selection discipline (§2, hermes's foresight-leak law): the query below is the
whole selection rule — no telechat/Last-Call affordance filter, no movement-
probability predicate, no hand-picked names. Movement is an observable OUTCOME.
The silent tail (drafts that sit in AD Evaluation for months) is enrolled on
purpose: it is the silent leg's honest denominator.

Frontier-terminal handling: units in {approved, ann, rfcqueue} are ENROLLED
(excluding by current state is a source-class property, not foresight) but
flagged `frontier_terminal: true` — movement from those states is structurally
certain, so `frontier_unresolved_at_pause` refuses them for the moved leg;
they remain noise/silent-eligible surfaces.

Noise assignment (§2, pinned): sha256(status_key) last byte % 4 == 0 → the
noise leg (~25%, matching `noise_leg_population`), decided by hash at
precommit time, never by inspection.

T0 canonical surface per unit is the STATUS SLICE of the Datatracker API
document object (states, rev, time — canonical JSON), `certificate_eligible:
true`. The draft body URL enters the catalog `certificate_eligible: false`
(routing surface only; revision churn never certifies — composer attack B).

Usage:
  python -m harness.wb_population stamp     # fetch, enumerate, write precommit
  python -m harness.wb_population status    # show the armed population
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

from .ledger import Ledger

REPO = Path(__file__).resolve().parent.parent
WB_DIR = REPO / "runs" / "wb"
LEDGER = WB_DIR / "population_precommit.jsonl"
T0_DIR = WB_DIR / "t0"

API = "https://datatracker.ietf.org/api/v1"
# The frozen selection rule. This string IS the enumeration — hashed into
# selection_rule_hash; any edit is a new population.
QUERY = ("/doc/document/?format=json&limit=500&type=draft"
         "&states__type__slug=draft-iesg"
         "&states__slug__in=pub-req,ad-eval,lc-req,lc,writeupw,goaheadw,"
         "iesg-eva,defer,approved,ann,rfcqueue"
         "&name__startswith=draft-ietf-")
STATE_QUERY = "/doc/state/?format=json&limit=60&type__slug=draft-iesg"
FRONTIER_TERMINAL = ("approved", "ann", "rfcqueue")
NOISE_MOD = 4  # sha(status_key)[-1] % 4 == 0 -> noise leg (~0.25)


def _get(path: str) -> dict:
    with urllib.request.urlopen(API + path, timeout=60) as r:
        return json.loads(r.read().decode())


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def _canonical_status_slice(doc: dict, id_to_slug: dict[int, str]) -> dict:
    iesg = sorted(id_to_slug[i] for i in
                  (int(u.rstrip("/").rsplit("/", 1)[-1]) for u in doc["states"])
                  if i in id_to_slug)
    return {"name": doc["name"], "iesg_states": iesg, "rev": doc["rev"],
            "time": doc["time"]}


def stamp() -> dict:
    states = _get(STATE_QUERY)["objects"]
    id_to_slug = {s["id"]: s["slug"] for s in states}
    label_enum = {s["slug"]: s["name"] for s in states}

    docs, path = [], QUERY
    while path:
        page = _get(path)
        docs.extend(page["objects"])
        path = page["meta"].get("next")
    docs.sort(key=lambda d: d["name"])

    T0_DIR.mkdir(parents=True, exist_ok=True)
    units, vocabulary = [], []
    for doc in docs:
        status_key = f"ietf_doc_state:{doc['name']}"
        vocabulary.append(status_key)
        status = _canonical_status_slice(doc, id_to_slug)
        t0_text = json.dumps(status, sort_keys=True)
        (T0_DIR / f"{doc['name']}.json").write_text(t0_text)
        noise = hashlib.sha256(status_key.encode()).digest()[-1] % NOISE_MOD == 0
        units.append({
            "unit_id": doc["name"], "status_key": status_key,
            "iesg_states_t0": status["iesg_states"],
            "frontier_terminal": any(s in FRONTIER_TERMINAL
                                     for s in status["iesg_states"]),
            "world_leg_at_watch": "noise" if noise else "silent",
            "t0_sha256": hashlib.sha256(t0_text.encode()).hexdigest(),
            "route_catalog": {
                f"status:{doc['name']}": {
                    "subject": status_key, "certificate_eligible": True,
                    "url": f"{API}/doc/document/{doc['name']}/"},
                f"body:{doc['name']}": {
                    "subject": status_key, "certificate_eligible": False,
                    "url": f"https://datatracker.ietf.org/doc/{doc['name']}/"},
            },
        })

    vocabulary.sort()
    t0_digest = _sha([u["t0_sha256"] for u in units])
    row = {
        "kind": "population_precommit",
        "population_id": "ietf-iesg-lifecycle-2026q3",
        "source_class": "IETF Datatracker draft-ietf-* Internet-Drafts in "
                        "non-terminal IESG states (official API)",
        "selection_rule": QUERY,
        "selection_rule_hash": _sha(QUERY + t0_digest),
        "t0_result_digest": t0_digest,
        "unit_count": len(units),
        "match_rule_id": "lifecycle_diff",
        "status_vocabulary": vocabulary,
        "status_vocabulary_hash": _sha(vocabulary),
        "state_label_enum_hash": _sha(label_enum),
        "state_label_enum": label_enum,
        "unresolved_frontier_enum": ["ietf_iesg_lifecycle"],
        "noise_leg_population": 0.25,
        "noise_rule": f"sha256(status_key)[-1] % {NOISE_MOD} == 0",
        "frontier_terminal_states": list(FRONTIER_TERMINAL),
        "frontier_terminal_count": sum(u["frontier_terminal"] for u in units),
        "noise_unit_count": sum(u["world_leg_at_watch"] == "noise" for u in units),
        "disclosure": "branch-blind enumeration; movement is outcome, never "
                      "enrollment criterion (SPEC §2 selection discipline); "
                      "the silent tail is enrolled as the honest denominator",
    }
    ledger = Ledger(LEDGER)
    ledger.write(row)
    ledger.write({"kind": "population_units", "population_id": row["population_id"],
                  "units": units})
    return row


def status() -> dict:
    rows = Ledger(LEDGER).rows()
    pops = [r for r in rows if r.get("kind") == "population_precommit"]
    if not pops:
        return {"armed": False}
    p = pops[-1]
    units = next(r["units"] for r in reversed(rows)
                 if r.get("kind") == "population_units"
                 and r["population_id"] == p["population_id"])
    return {"armed": True, "population_id": p["population_id"], "stamped": p["ts"],
            "units": p["unit_count"], "noise_units": p["noise_unit_count"],
            "frontier_terminal": p["frontier_terminal_count"],
            "selection_rule_hash": p["selection_rule_hash"][:16],
            "moved_eligible": sum(1 for u in units if not u["frontier_terminal"])}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["stamp", "status"])
    args = ap.parse_args()
    if args.cmd == "stamp":
        row = stamp()
        print(json.dumps({k: v for k, v in row.items()
                          if k not in ("status_vocabulary", "state_label_enum")},
                         indent=2, sort_keys=True))
        return 0
    print(json.dumps(status(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
