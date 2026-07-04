"""Author the triangulation-docket fixture family (SPEC Part III, sealed 9e9d4a4).

Builder-lane authoring script: every computed field (content hashes, rulebook /
predicate-library / population hashes, obligation ids, frontier_state tuples,
ballast tokens) is produced through the real harness modules — never typed in.
Run:  python -m harness.author_docket   (writes episodes/prf/triangulation-docket/)

Design notes bound to the seal:
- 21 surfaces = 9 plausible (3 per leg class, identical field schema) + 12 admin
  ballast; dispositive K-17 legs: S1 (status note), S4 (Exception Register A),
  S8 (Clearance Ledger B).  calibration_route = [S1, S4, S8];
  cold_exploration_route = the remaining 6 plausible [S2, S3, S5, S6, S7, S9].
- Rulebook: three K-17 rules (verify, disjoint match keys) + one K-17 discard
  rule (meridian RR1 shape) + three K-18 rules — the K-18 rules exist so the
  BALLAST analog's wrong-leg bundle is *derivable* through
  derive_live_obligations against its own witness route (S2, S5, S9), per the
  sealed §32 override allowlist. Disclosed to the room at build review.
- Neutral analog overrides stale_claim only (allowlist); ballast overrides
  witness_route + frontier_state + calibration_obligation_ids (replay-checked).
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from .derive_live_obligations import (derive_live_obligations,
                                      validate_rulebook, library_hash)
from .mint_frontier_state import freeze_validate, offer_gate, manifest_hash
from .prf_ablation import structural_dependency

OUT = Path(__file__).resolve().parent.parent / "episodes" / "prf" / "triangulation-docket"

FIXTURE_ID = "prf-triangulation-docket"
SEAM_ID = "seam-docket-1"
QUESTION = ("In the Harbor Ridge facilities case queue, what disposition should "
            "be entered now for case K-17: approve, defer, reject, or reopen?")

def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ---------------------------------------------------------------- surfaces
# (id, title-line lead, leg tag or None, fields, t0 body, t1 body)
# Body texts are fictional, out-of-weights, ~60-75 whitespace tokens each for
# the plausible set so the pay-window geometry has honest margin.

def _pad(base: str, n: int) -> str:
    """Repeat the record text to a target token width, meridian style."""
    words = base.split()
    out = list(words)
    while len(out) < n:
        out.extend(words)
    return " ".join(out[:n])


SURFACES: list[dict] = [
    # ---- plausible: status notes (case-titled; leg_status on all three)
    dict(sid="S1", tag="leg_status", key="K-17",
         fields=dict(surface_kind="status_note", status_key="K17_status"),
         t0="harbor ridge case K-17 status note case active disposition not yet "
            "entered exception matter referred to the register of record reviewer "
            "clearance tracked in the ledger of record second reviewer clearance "
            "outstanding at this writing status recorded by the queue clerk",
         t1="harbor ridge case K-17 status note case active disposition not yet "
            "entered exception matter referred to the register of record reviewer "
            "clearance tracked in the ledger of record no items outstanding on the "
            "status side status recorded by the queue clerk"),
    dict(sid="S2", tag="leg_status", key="K-18",
         fields=dict(surface_kind="status_note", status_key="K18_status"),
         t0="harbor ridge case K-18 status note case active fee schedule variance "
            "under review exception matter referred to the register of record "
            "reviewer clearance tracked in the ledger of record status recorded by "
            "the queue clerk",
         t1="harbor ridge case K-18 status note case active fee schedule variance "
            "under review exception matter referred to the register of record "
            "reviewer clearance tracked in the ledger of record status recorded by "
            "the queue clerk"),
    dict(sid="S3", tag="leg_status", key="K-19",
         fields=dict(surface_kind="status_note", status_key="K19_status"),
         t0="harbor ridge case K-19 status note case held at applicant request "
            "exception matter referred to the register of record reviewer clearance "
            "tracked in the ledger of record status recorded by the queue clerk",
         t1="harbor ridge case K-19 status note case held at applicant request "
            "exception matter referred to the register of record reviewer clearance "
            "tracked in the ledger of record status recorded by the queue clerk"),
    # ---- plausible: exception registers (class-titled A/B/C; K-17 row in A)
    dict(sid="S4", tag="leg_exception", key="K-17",
         fields=dict(surface_kind="exception_register", status_key="K17_exception"),
         t0="harbor ridge exception register volume A row entries by case case "
            "K-17 exception class E2 site frontage variance waiver requested "
            "waiver decision pending panel action register maintained by the "
            "facilities exceptions panel entries current to date of issue",
         t1="harbor ridge exception register volume A row entries by case case "
            "K-17 exception class E2 site frontage variance waiver granted by "
            "panel action no conditions attached register maintained by the "
            "facilities exceptions panel entries current to date of issue"),
    dict(sid="S5", tag="leg_exception", key="K-18",
         fields=dict(surface_kind="exception_register", status_key="K18_exception"),
         t0="harbor ridge exception register volume B row entries by case case "
            "K-18 exception class E5 fee variance under review no panel action "
            "recorded register maintained by the facilities exceptions panel "
            "entries current to date of issue",
         t1="harbor ridge exception register volume B row entries by case case "
            "K-18 exception class E5 fee variance under review no panel action "
            "recorded register maintained by the facilities exceptions panel "
            "entries current to date of issue"),
    dict(sid="S6", tag="leg_exception", key="K-19",
         fields=dict(surface_kind="exception_register", status_key="K19_exception"),
         t0="harbor ridge exception register volume C row entries by case case "
            "K-19 no exception on file placeholder row retained for numbering "
            "register maintained by the facilities exceptions panel entries "
            "current to date of issue",
         t1="harbor ridge exception register volume C row entries by case case "
            "K-19 no exception on file placeholder row retained for numbering "
            "register maintained by the facilities exceptions panel entries "
            "current to date of issue"),
    # ---- plausible: clearance ledgers (class-titled A/B/C; K-17 rows in B)
    dict(sid="S7", tag="leg_clearance", key="K-19",
         fields=dict(surface_kind="clearance_ledger", status_key="K19_clearance"),
         t0="harbor ridge reviewer clearance ledger volume A rows by case case "
            "K-19 clearance not initiated pending case release ledger kept by the "
            "review office signatures on file at the records desk",
         t1="harbor ridge reviewer clearance ledger volume A rows by case case "
            "K-19 clearance not initiated pending case release ledger kept by the "
            "review office signatures on file at the records desk"),
    dict(sid="S8", tag="leg_clearance", key="K-17",
         fields=dict(surface_kind="clearance_ledger", status_key="K17_clearance"),
         t0="harbor ridge reviewer clearance ledger volume B rows by case case "
            "K-17 first reviewer clearance granted second reviewer clearance "
            "outstanding ledger kept by the review office signatures on file at "
            "the records desk",
         t1="harbor ridge reviewer clearance ledger volume B rows by case case "
            "K-17 first reviewer clearance granted second reviewer clearance "
            "granted clearance complete two of two ledger kept by the review "
            "office signatures on file at the records desk"),
    dict(sid="S9", tag="leg_clearance", key="K-18",
         fields=dict(surface_kind="clearance_ledger", status_key="K18_clearance"),
         t0="harbor ridge reviewer clearance ledger volume C rows by case case "
            "K-18 first reviewer clearance granted second reviewer assignment "
            "pending ledger kept by the review office signatures on file at the "
            "records desk",
         t1="harbor ridge reviewer clearance ledger volume C rows by case case "
            "K-18 first reviewer clearance granted second reviewer assignment "
            "pending ledger kept by the review office signatures on file at the "
            "records desk"),
]

_BALLAST = [
    ("S10", "inspection addendum quarterly walkthrough notes lighting and egress "
            "items logged no case dispositions recorded here"),
    ("S11", "regional deferral bulletin advisory on seasonal workload deferrals "
            "general guidance only names no specific case"),
    ("S12", "facilities contact roster names desks and shift assignments no case "
            "content maintained by the front office"),
    ("S13", "maintenance log routine service entries for the records annex no "
            "case content equipment identifiers only"),
    ("S14", "permit fee schedule standard fee table by permit class reference "
            "sheet no case entries"),
    ("S15", "rotation schedule reviewer duty rotation by week reference only no "
            "clearance decisions recorded here"),
    ("S16", "visitor log digest weekly counts at the records desk reference "
            "figures no case content"),
    ("S17", "corridor capacity tables nominal occupancy figures for hearing rooms "
            "static reference sheet"),
    ("S18", "signage standards sheet posting requirements for public notices "
            "static reference no case content"),
    ("S19", "archive extract closed cases from prior seasons retained for "
            "numbering no active case content"),
    ("S20", "rainfall digest seasonal figures for the catchment reference only "
            "unrelated to the case queue"),
    ("S21", "bulletin board notes miscellaneous postings and reminders no "
            "official standing"),
]
for sid, body in _BALLAST:
    SURFACES.append(dict(
        sid=sid, tag=None, key=None,
        fields=dict(surface_kind="prose_body"),
        t0=_pad("harbor ridge " + body, 36),
        t1=_pad("harbor ridge " + body, 36)))

TITLES = {'S1': 'Case K-17 Status Note', 'S2': 'Case K-18 Status Note', 'S3': 'Case K-19 Status Note', 'S4': 'Exception Register A', 'S5': 'Exception Register B', 'S6': 'Exception Register C', 'S7': 'Clearance Ledger A', 'S8': 'Clearance Ledger B', 'S9': 'Clearance Ledger C', 'S10': 'Inspection Addendum', 'S11': 'Regional Deferral Bulletin', 'S12': 'Facilities Contact Roster', 'S13': 'Maintenance Log', 'S14': 'Permit Fee Schedule', 'S15': 'Reviewer Rotation Schedule', 'S16': 'Visitor Log Digest', 'S17': 'Corridor Capacity Tables', 'S18': 'Signage Standards Sheet', 'S19': 'Archive Extract (Closed Cases)', 'S20': 'Catchment Rainfall Digest', 'S21': 'Bulletin Board Notes'}
for s in SURFACES:
    s["title"] = TITLES[s["sid"]]
    if s["tag"]:
        s["t0"] = _pad(s["t0"], 100)
        s["t1"] = _pad(s["t1"], 100)

OPTION_IDS = ["A", "B", "C"]      # C = the K-17 live disposition candidate (not
                                  # first alphabetically — hermes floor); B = the
                                  # K-18 neighbour's binding; A = defer candidate
SURFACE_IDS = [s["sid"] for s in SURFACES]

# ------------------------------------------------------------- predicates
def _leg_trigger(tag: str, key: str) -> dict:
    return {"op": "and", "args": [
        {"op": "read_has_tag", "tag": tag},
        {"op": "eq", "field": "catalog_key", "value": key}]}

def _sat(sid: str) -> dict:
    return {"op": "and", "args": [
        {"op": "eq", "field": "surface_id", "value": sid},
        {"op": "eq", "field": "catalog_epoch", "value": "t1"}]}

PREDICATES = {
    "P_status_k17":    _leg_trigger("leg_status", "K-17"),
    "P_exception_k17": _leg_trigger("leg_exception", "K-17"),
    "P_clearance_k17": _leg_trigger("leg_clearance", "K-17"),
    "P_status_k18":    _leg_trigger("leg_status", "K-18"),
    "P_exception_k18": _leg_trigger("leg_exception", "K-18"),
    "P_clearance_k18": _leg_trigger("leg_clearance", "K-18"),
    "P_sat_status":    _sat("S1"),
    "P_sat_exception": _sat("S4"),
    "P_sat_clearance": _sat("S8"),
    "P_sat_status_b":  _sat("S2"),
    "P_sat_exception_b": _sat("S5"),
    "P_sat_clearance_b": _sat("S9"),
    "P_world_moved":   {"op": "changed"},
}

def _rule(rid, trig, code, kind, keys, opt, sat):
    return dict(rule_id=rid, trigger_predicate_id=trig, emits_relation_code=code,
                emits_obligation_type=kind, match_key_ids=keys, option_id=opt,
                satisfaction_predicate_id=sat)

RULEBOOK = [
    _rule("R1", "P_status_k17",    "pending_evidence", "verify",
          ["K17_status"], "C", "P_sat_status"),
    _rule("R2", "P_exception_k17", "pending_evidence", "verify",
          ["K17_exception"], "C", "P_sat_exception"),
    _rule("R3", "P_clearance_k17", "pending_evidence", "verify",
          ["K17_clearance"], "C", "P_sat_clearance"),
    _rule("R4", "P_status_k17",    "discard_if_world_key_changed", "discard",
          ["K17_status", "K17_exception", "K17_clearance"], "C", "P_world_moved"),
    _rule("R5", "P_status_k18",    "pending_evidence", "verify",
          ["K18_status"], "B", "P_sat_status_b"),
    _rule("R6", "P_exception_k18", "pending_evidence", "verify",
          ["K18_exception"], "B", "P_sat_exception_b"),
    _rule("R7", "P_clearance_k18", "pending_evidence", "verify",
          ["K18_clearance"], "B", "P_sat_clearance_b"),
]

RELATION_CODE_CLASSES = {
    "live": "identity",
    "pending_evidence": "obligation",
    "discard_if_world_key_changed": "discard",
    "reopen_if_catalog_match": "reopen",
    "blocked_by_missing_surface": "topology",
}

CALIBRATION_ROUTE = ["S1", "S4", "S8"]
COLD_EXPLORATION_ROUTE = ["S2", "S3", "S5", "S6", "S7", "S9"]
WITNESS_ROUTE = ["S1", "S4", "S8"]           # D8: set = the three legs
BALLAST_WITNESS_ROUTE = ["S2", "S5", "S9"]   # the K-18 legs (wrong for K-17)

STALE_CLAIM = ("Resume note (recorded at pause): case K-17 was awaiting second "
               "reviewer clearance at that time; disposition then indicated: defer.")

EXPECTED_T0 = "defer"
EXPECTED_T1 = "approve"


def build_population() -> dict:
    catalog = {}
    for s in SURFACES:
        fields = dict(s["fields"])
        fields["certificate_eligible"] = bool(s["tag"])
        if s["key"]:
            fields["catalog_key"] = s["key"]
        catalog[s["sid"]] = {
            "content_hash_t0": _sha(s["t0"]),
            "fields": fields,
            "surface_tags": [s["tag"]] if s["tag"] else [],
        }
    pop = {
        "kind": "population_precommit",
        "episode_id": FIXTURE_ID,
        "seam_id": SEAM_ID,
        "derivation_mode": "rulebooked",
        "gamma": 0.2,
        "option_ids": OPTION_IDS,
        "catalog": catalog,
        "obligation_rulebook": RULEBOOK,
        "predicate_library": PREDICATES,
        "relation_code_classes": RELATION_CODE_CLASSES,
        "reopen_rules": {
            "RR1": {"invalidation_predicate_id": "P_world_moved",
                    "reason": "changed_world"},
        },
        "surface_tag_schema": ["leg_status", "leg_exception", "leg_clearance"],
        "status_vocabulary": ["disposition_pending"],
        "uncertainty_codes": ["unresolved", "needs_check", "conflict_unread"],
        "continuation_step_id": "csid-docket-1",
        "sbr_cold_reread_tokens_rule": (
            "sum of visible t1 catalog surface tokens (static, branch-blind "
            "supremum; pinned at population_precommit for the offer-gate gamma "
            "ballast, meridian rule carried)"),
    }
    pop["sbr_cold_reread_tokens"] = sum(len(s["t1"].split()) for s in SURFACES)
    pop["obligation_rulebook_hash"] = validate_rulebook(RULEBOOK, PREDICATES,
                                                        RELATION_CODE_CLASSES)
    pop["predicate_library_hash"] = library_hash(PREDICATES)
    pop["population_reopen_rules_hash"] = _sha(
        json.dumps(pop["reopen_rules"], sort_keys=True))
    pop["population_contract_hash"] = _sha(
        json.dumps({k: pop[k] for k in ("obligation_rulebook_hash",
                                        "predicate_library_hash",
                                        "option_ids", "seam_id")},
                   sort_keys=True))
    return pop


def freeze_manifest_for(pop: dict) -> dict:
    fm = {
        "allowed_fields": ["live_options", "inactive_options",
                           "pending_obligations", "reopen_rules",
                           "read_manifest", "uncertainty"],
        "forbidden_field_names": ["best_option", "option_rank", "confidence",
                                  "draft_answer", "summary", "next_step",
                                  "reason"],
        # frontier_schema_hash filled below via manifest_hash (schema_pinned)
        "id_pattern": "^[A-Z][0-9]*$",
        "option_ids": OPTION_IDS,
        "surface_ids": SURFACE_IDS,
        "relation_code_classes": RELATION_CODE_CLASSES,
        "uncertainty_codes": pop["uncertainty_codes"],
    }
    fm["frontier_schema_hash"] = manifest_hash(fm)
    return fm


def witness_reads(pop: dict, route: list[str]) -> list[dict]:
    return [{"surface_id": sid, "read_index": i, "catalog_epoch": "t0",
             "content_hash": pop["catalog"][sid]["content_hash_t0"]}
            for i, sid in enumerate(route)]


def derive(pop: dict, fm: dict, route: list[str]) -> dict:
    return derive_live_obligations(pop, fm, witness_reads(pop, route), SEAM_ID)


def frontier_state_from(batch: dict, route: list[str],
                        live: list[str], option: str) -> dict:
    pending, reopen = [], []
    for ob in batch["obligations"]:
        row = {"obligation_id": ob["obligation_id"],
               "derived_from_obligation_id": ob["obligation_id"],
               "option_id": ob["option_id"],
               "relation_code": ob["relation_code"]}
        if ob["relation_code"] == "discard_if_world_key_changed":
            row = {"derived_from_obligation_id": ob["obligation_id"],
                   "option_id": ob["option_id"],
                   "relation_code": ob["relation_code"],
                   "surface_id": ob["source_read_ids"][0]}
            reopen.append(row)
        else:
            pending.append(row)
    return {
        "live_options": live,
        "inactive_options": [],
        "pending_obligations": pending,
        "reopen_rules": reopen,
        "read_manifest": sorted(route),
        "uncertainty": [{"option_id": option, "uncertainty_code": "unresolved"}],
    }


def base_episode(pop: dict, fm: dict, frontier_state: dict,
                 batch: dict, route: list[str]) -> dict:
    t0_by_sid = {s["sid"]: s["t0"] for s in SURFACES}
    catalog = {}
    for s in SURFACES:
        fields = dict(s["fields"])
        fields["certificate_eligible"] = bool(s["tag"])
        if s["key"]:
            fields["catalog_key"] = s["key"]
        catalog[s["sid"]] = {
            "content_hash": _sha(s["t1"]),
            "text": s["t1"],
            "title": s["title"],
            "tokens": len(s["t1"].split()),
            "surface_tags": [s["tag"]] if s["tag"] else [],
            "fields": fields,
        }
    return {
        "fixture_id": FIXTURE_ID,
        "instrument_version": "0.3",
        "seam_id": SEAM_ID,
        "question": QUESTION,
        "quality_threshold": 1.0,
        "catalog_sort": "by_id",
        "budgets": {"max_read_tokens": 700, "max_steps": 8,
                    "action_overhead_tokens": 20, "c_max": 860,
                    "c_max_rule": ("max_read_tokens + max_steps * "
                                   "action_overhead_tokens (static, §16)")},
        "regime_s": {"temperature_range": [0.3, 0.7], "dispersion_probe_k": 5,
                     "ci_halfwidth_tokens": 100, "n_max": 24,
                     "n_rule": ("derived from pilot variance targeting the "
                                "precommitted CI; never by fiat (§17)")},
        "expected_answer_t0": EXPECTED_T0,
        "expected_answer_t1": EXPECTED_T1,
        "witness_route": route,
        "frontier_state": frontier_state,
        "t0_texts": {s["sid"]: s["t0"] for s in SURFACES},
        "catalog": catalog,
        "calibration_route": CALIBRATION_ROUTE,
        "calibration_obligation_ids": sorted(
            ob["obligation_id"] for ob in batch["obligations"]),
        "calibration_expected_answer": EXPECTED_T1,
        "cold_exploration_route": COLD_EXPLORATION_ROUTE,
        "ballast": {"covered_surfaces": sorted(route),
                    "derived_obligation_tokens": sum(
                        len(t0_by_sid[sid].split()) for sid in route)},
        "foreground_disclosure": (
            "resumable foreground = canonical frontier artifact + stale claim, "
            "rendered by the shared render path; stale-claim tokens ledgered "
            "outside ECAC (§16/§27)"),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pop = build_population()
    fm = freeze_manifest_for(pop)

    # --- K-17 mint (main episode): derive → freeze_validate → offer_gate
    batch = derive(pop, fm, WITNESS_ROUTE)
    fs = frontier_state_from(batch, WITNESS_ROUTE, ["A", "C"], "C")
    ep = base_episode(pop, fm, fs, batch, WITNESS_ROUTE)
    ep["episode_id"] = "docket-temptation"
    ep["stale_claim"] = STALE_CLAIM
    ep["expected_cells"] = {"kind": "pay_window_baseline"}

    # --- ballast analog: wrong-leg bundle from the K-18 legs (sealed §32
    #     allowlist: overrides witness_route + frontier_state +
    #     calibration_obligation_ids, replay-checked)
    bbatch = derive(pop, fm, BALLAST_WITNESS_ROUTE)
    bfs = frontier_state_from(bbatch, BALLAST_WITNESS_ROUTE, ["A", "C"], "C")
    epb = base_episode(pop, fm, bfs, bbatch, BALLAST_WITNESS_ROUTE)
    epb["episode_id"] = "docket-ballast"
    epb["stale_claim"] = STALE_CLAIM
    epb["expected_cells"] = {"kind": "self_falsification_ballast",
                             "must_not": "PRF2-cost-win"}
    epb["self_falsification"] = "ballast_discriminator"
    epb["variant_overrides"] = ["witness_route", "frontier_state",
                                "calibration_obligation_ids"]
    epb["calibration_gate_disposition"] = (
        "skip: self-falsifier fixture, not pay-window admission (sealed watch 2)")

    # --- neutral analog: stale_claim override only (allowlist)
    epn = copy.deepcopy(ep)
    epn["episode_id"] = "docket-neutral"
    epn["stale_claim"] = None
    epn["expected_cells"] = {"kind": "self_falsification_neutral",
                             "must_not": "PRF2-cost-win"}
    epn["self_falsification"] = "neutral_frontier"
    epn["variant_overrides"] = ["stale_claim"]
    epn["calibration_gate_disposition"] = (
        "skip: self-falsifier fixture, not pay-window admission (sealed watch 2)")

    # prove MINTED end-to-end through the real modules (meridian discipline)
    for name, (b, f, route) in {
            "temptation": (batch, fs, WITNESS_ROUTE),
            "ballast": (bbatch, bfs, BALLAST_WITNESS_ROUTE)}.items():
        cand = freeze_validate(
            f, fm, b["batch"], fm["frontier_schema_hash"],
            route_reads_at_freeze=witness_reads(pop, route),
            m1_sidecar_at_freeze={},
            derive_live_obligations_id="derive_live_obligations")
        abl = structural_dependency(pop, fm, witness_reads(pop, route), SEAM_ID)
        t0_by_sid = {s["sid"]: s["t0"] for s in SURFACES}
        dot = sum(len(t0_by_sid[sid].split()) for sid in route)
        minted = offer_gate(cand, derived_obligation_tokens=dot,
                            cold_reread_tokens=pop["sbr_cold_reread_tokens"],
                            gamma=pop["gamma"],
                            ablation=abl, frontier_artifact_id=f"fa:docket-{name}")
        print(f"MINTED [{name}]: digest={minted['state_digest'][:16]} "
              f"state_tokens={minted['state_tokens']}")

    manifest = {
        "fixture_id": FIXTURE_ID,
        "instrument_version": "0.3",
        "fictional": True,
        "out_of_weights": True,
        "invented": "2026-07-04",
        "episodes": ["ep-docket-temptation.json", "ep-docket-ballast.json",
                     "ep-docket-neutral.json"],
        "target_engines": [],  # precommitted IN-THREAD before any engine
                               # contact (§33); empty until that entry exists
        "shared_base_note": (
            "0.3 override allowlist (sealed §32): ballast overrides "
            "witness_route + frontier_state + calibration_obligation_ids "
            "(replay-checked); neutral overrides stale_claim only; catalog, "
            "budgets, action grammar, titles, indices, costs shared"),
        "attestation": {
            "attested_at": "2026-07-04",
            "attested_by": ("claude/fable-5 (builder lane; oracle keys "
                            "precommitted before any engine run)"),
            "probe_debt": ("per-engine cold ignorance probe REQUIRED before "
                           "any real-engine run (§33; never inherited)"),
            "ignorance_probe": {"engines": {"mock": {
                "knew": False, "note": "mock engine — wire machinery only"}}},
        },
    }

    files = {"population.json": pop,
             "freeze_manifest.json": fm,
             "manifest.json": manifest,
             "ep-docket-temptation.json": ep,
             "ep-docket-ballast.json": epb,
             "ep-docket-neutral.json": epn}
    for name, obj in files.items():
        (OUT / name).write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")
    print("authored", len(files), "files ->", OUT)
    print("K-17 batch:", [o["obligation_id"][:20] for o in batch["obligations"]])
    print("ballast batch:", [o["obligation_id"][:20] for o in bbatch["obligations"]])


if __name__ == "__main__":
    main()
