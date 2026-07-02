"""Warming-budget scorer — SPEC_WARMING_BUDGET v0.1 machinery.

The instrument's question: does consequence-earned ranking (the M1 heir's
authority sidecar) under-serve an unresolved frontier enough to measure — on
the warming-budget axis (route_read_tokens-to-matched-outcome along replayable
routes)? `WB-heir-dominates` (B+ needs no compact warmth) is a first-class
predeclared outcome, not a failure of the instrument.

Build scope (SPEC §8): machinery + mock wire tests + silent/noise legs.
Moved-leg PROMOTION stays withheld until a prospective `trigger_precommit`
exists against a live external stream; nothing here can promote a wire test.

The §6a centerpiece — `derive_answer_bearing_surfaces` — is a branch-blind
pure function. Hand-authored `answer_bearing_surface_ids` anywhere in a packet
or event stream are refused fail-closed: the world's movement enters the
comparator ONLY as the derived result of a match rule fixed at
`population_precommit` over symmetric catalog hashes.

Event row kinds (one JSONL ledger per chronology unit, harness-stamped ts):
  population_precommit    — match_rule_id, status_vocabulary_hash, frontier enum,
                            selection_rule_hash, noise_leg_population (fixed FIRST)
  ignorance_probe         — per engine, cold, before the fork group
  compact_resume_state_minted — the C treatment; strict input closure (§3)
  trigger_precommit       — cites population hashes (never defines rules);
                            external_stream_ref + pause catalog/artifact hashes
  world_move              — external chronology observation {external_ts, subject}
  t1_catalog_materialized — symmetric post-move catalog, ALL branches (§4)
  trigger_observed        — deterministic T1-vs-match-rule comparison
  route_plan              — per branch: ordered surface ids + neutral_rank map
                            (B0/B+ from the neutral planner; C = planner + hint;
                            C_ablated = C minus the trigger-reorder feature)
  surface_read            — HARNESS-emitted only: {branch, surface_id, order};
                            tokens are recomputed from canonical text at score
                            time (logged cost is cache, never authority)
  branch_outcome          — per branch per prefix: world-oracle score (never
                            engine narration; R5 fence)

Scoring is fail-closed: a missing guard is a failed guard, and every failed
guard names itself in the verdict evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .ledger import Ledger

REPO = Path(__file__).resolve().parent.parent

# Guard legs a WB win predicate may read. `opportunity`/latency vocabulary and
# any `agent_claimed_*` field are structurally absent (R5 fence, SPEC §6).
GUARDS = (
    "population_precommit_ok", "probe_before_fork_ok", "order_ok",
    "fork_identity_ok", "surface_symmetry_ok", "precommit_precedes_world_move",
    "genealogy_ok", "trigger_demoted_ok", "trigger_authority_leak_ok",
    "planner_ablation_ok", "eligibility_vs_cost_ok", "route_replay_ok",
    "route_cost_ok",
    "frontier_unresolved_at_pause", "information_parity_ok", "bplus_capable",
    "quality_floor_holds",
)

EVENT_ORDER = ("population_precommit", "compact_resume_state_minted",
               "trigger_precommit", "world_move", "t1_catalog_materialized")

# Compaction input closure (SPEC §3): everything else is banned at mint.
MINT_INPUTS = frozenset(
    {"route_catalog_t0", "m1_sidecar", "pause_question_id", "unresolved_frontier_tag"})

AUTHORITY_LEAK_RANK_GAP = 3   # B+ neutral rank must trail by > this many places
QUALITY_FLOOR = 1.0           # world-oracle pass score (mock oracle: 1.0/0.0)


def _tokens(text: str) -> int:
    """Deterministic token proxy — recomputed from canonical text, never trusted
    from a log row."""
    return len(text.split())


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def refuse_hand_authored_marks(obj: object, where: str = "packet") -> None:
    """§6a fail-closed rule: `answer_bearing_surface_ids` (or any *answer_bearing*
    key) appearing ANYWHERE in fixture or event data is a hidden authored key."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if "answer_bearing" in str(k):
                raise ValueError(
                    f"hand-authored answer-bearing mark {k!r} in {where} — "
                    "refused (SPEC §6a: the certificate set is derived, never authored)")
            refuse_hand_authored_marks(v, where)
    elif isinstance(obj, list):
        for v in obj:
            refuse_hand_authored_marks(v, where)


def derive_answer_bearing_surfaces(t0: dict, t1: dict, catalog: dict,
                                   status_key: str, match_rule_id: str,
                                   status_vocabulary: list[str],
                                   leg: str) -> tuple[set[str], str]:
    """§6a: the branch-blind pure function. Returns (certificate_set, parity_state)
    where parity_state is 'ok' or 'confounded'.

    Inputs are closed: canonical T0/T1 text, the catalog (surface_id ->
    {subject, ...}), and the population-precommitted status_key / match_rule_id /
    vocabulary. No route plans, no reads, no answers, no hints, no prose.

    One derivation path per match_rule_id (no dual anchor — the implementer
    never chooses a path after seeing routes). v0.1 defines `lifecycle_diff`:
      moved leg:  surface is a certificate iff its canonical text CHANGED
                  (sha(T1) != sha(T0)) AND its subject matches status_key under
                  the precommitted vocabulary.
      silent/noise leg: the STABLE certificate — subject matches AND text did
                  NOT change; irrelevant public churn never enters the set.
    Degenerate (empty) certificate sets are confounded, never a cost win.
    """
    if match_rule_id != "lifecycle_diff":
        raise ValueError(f"unknown match_rule_id {match_rule_id!r} — one derivation "
                         "path per enum value; no ad-hoc rules at score time")
    subj_match = {
        sid for sid, meta in catalog.items()
        if meta.get("subject") == status_key and status_key in status_vocabulary
        # certificate_eligible (population round, composer attack B): only
        # status-bearing surfaces may certify; prose bodies stay in the
        # symmetric catalog for ROUTING but revision churn on them never
        # fires a moved-leg certificate. Default True (a population that
        # doesn't tag has no prose surfaces to protect).
        and meta.get("certificate_eligible", True)
    }
    changed = {sid for sid in catalog
               if _sha(t1.get(sid, "")) != _sha(t0.get(sid, ""))}
    certs = (subj_match & changed) if leg == "moved" else (subj_match - changed)
    return certs, ("ok" if certs else "confounded")


def mint_compact_state(route_catalog_t0: dict, m1_sidecar: dict,
                       pause_question_id: str, unresolved_frontier_tag: str,
                       route_hint: list[str], trigger_key: str,
                       discard_rule: str, population: dict,
                       **extra_inputs) -> dict:
    """Harness-deterministic mint under the §3 input closure. Any extra input —
    work product, answers, probe content — refuses the mint. `genealogy_ok` is
    enforced here, not just scored: hints name catalog surface ids only, never
    status vocabulary lemmas or post-move strings."""
    if extra_inputs:
        raise ValueError(f"compaction input closure violated: {sorted(extra_inputs)} "
                         f"— permitted inputs are {sorted(MINT_INPUTS)} only (SPEC §3)")
    enum = population.get("unresolved_frontier_enum", [])
    if unresolved_frontier_tag not in enum:
        raise ValueError(f"unresolved_frontier_tag {unresolved_frontier_tag!r} not in "
                         "the population_precommit enum — free-text tags are refused")
    vocab = set(population.get("status_vocabulary", []))
    for sid in route_hint:
        if sid not in route_catalog_t0:
            raise ValueError(f"route_hint names {sid!r} which is not a T0 catalog "
                             "surface id — hints carry order, never world access")
        if any(lemma in sid for lemma in vocab):
            raise ValueError(f"route_hint {sid!r} carries status vocabulary — "
                             "genealogy_ok refused at mint (SPEC §5)")
    state = {
        "kind": "compact_resume_state",
        "input_digest": _sha(json.dumps(
            {"catalog": sorted(route_catalog_t0), "sidecar": m1_sidecar,
             "question": pause_question_id, "frontier": unresolved_frontier_tag},
            sort_keys=True)),
        "route_hint": list(route_hint), "trigger_key": trigger_key,
        "discard_rule": discard_rule,
        "demotion": "routing_hint_only",
        "forbidden_effects": ["authority_delta", "eligibility_override",
                              "answer_prefill"],
    }
    state["state_tokens"] = _tokens(json.dumps(state, sort_keys=True))
    return state


class WarmingScorer:
    """Scores one chronology unit's event ledger. Paths injectable for wire
    tests; verdicts are computed, never narrated."""

    def __init__(self, packet: dict, events: list[dict]):
        refuse_hand_authored_marks(packet, "packet")
        refuse_hand_authored_marks(events, "events")
        # §8a debt 3 (composer A3): axis smuggling refused at the door
        claimed = packet.get("organ_identity", "warming_budget")
        if claimed != "warming_budget":
            raise ValueError(f"packet claims organ_identity {claimed!r} — this "
                             "scorer prices route_read_tokens for warming_budget "
                             "only; X2 verdict rows are not evidence here")
        self.packet = packet
        self.events = events
        self.catalog = packet["route_catalog"]          # sid -> {subject, ...}
        self.t0 = packet["T0_snapshot"]                 # sid -> canonical text
        self.t1 = packet.get("T1_snapshot", self.t0)
        self.guards: dict[str, bool] = {}
        self.evidence: dict[str, object] = {}

    # -- event access -----------------------------------------------------------

    def _one(self, kind: str) -> dict | None:
        rows = [e for e in self.events if e.get("kind") == kind]
        return rows[-1] if rows else None

    def _all(self, kind: str) -> list[dict]:
        return [e for e in self.events if e.get("kind") == kind]

    def _fail(self, guard: str, why: object) -> None:
        self.guards[guard] = False
        self.evidence[guard] = why

    # -- guard legs ---------------------------------------------------------------

    def _check_precommit_chain(self) -> None:
        pop = self._one("population_precommit")
        if pop is None:
            self._fail("population_precommit_ok", "missing population_precommit")
            return
        required = {"match_rule_id", "status_vocabulary_hash", "status_vocabulary",
                    "selection_rule_hash", "unresolved_frontier_enum",
                    "noise_leg_population"}
        missing = required - set(pop)
        if missing:
            self._fail("population_precommit_ok", {"missing_fields": sorted(missing)})
            return
        if pop["status_vocabulary_hash"] != _sha(json.dumps(
                pop["status_vocabulary"], sort_keys=True)):
            self._fail("population_precommit_ok", "status_vocabulary_hash mismatch")
            return
        self.guards["population_precommit_ok"] = True

        trig = self._one("trigger_precommit")
        if trig is not None and (
                trig.get("match_rule_ref") != pop["status_vocabulary_hash"]
                or "match_rule" in trig or "status_vocabulary" in trig):
            # trigger time may CITE the precommitted rule, never define/extend it
            self._fail("population_precommit_ok",
                       "trigger_precommit defines or diverges from the population "
                       "match rule — refused (verification pass, composer placement attack)")

    def _check_order(self) -> None:
        idx = {}
        for i, e in enumerate(self.events):
            if e.get("kind") in EVENT_ORDER and e["kind"] not in idx:
                idx[e["kind"]] = i
        present = [k for k in EVENT_ORDER if k in idx]
        ordered = all(idx[a] < idx[b] for a, b in zip(present, present[1:]))
        # silent legs have no world_move; the rest of the chain is still ordered
        needed = {"population_precommit", "compact_resume_state_minted",
                  "trigger_precommit"}
        self.guards["order_ok"] = ordered and needed.issubset(idx)
        if not self.guards["order_ok"]:
            self.evidence["order_ok"] = {"present": present}

        probes = self._all("ignorance_probe")
        first_read = next((i for i, e in enumerate(self.events)
                           if e.get("kind") == "surface_read"), len(self.events))
        self.guards["probe_before_fork_ok"] = bool(probes) and all(
            self.events.index(p) < first_read for p in probes)

        move, trig = self._one("world_move"), self._one("trigger_precommit")
        if move is None:
            self.guards["precommit_precedes_world_move"] = True  # silent leg
        elif trig is None or "external_ts" not in move or "precommit_ts" not in trig:
            self._fail("precommit_precedes_world_move",
                       "external stream timestamp or precommit_ts missing — ledger "
                       "write order alone is not chronology (SPEC §4)")
        else:
            self.guards["precommit_precedes_world_move"] = (
                trig["precommit_ts"] < move["external_ts"])

    def _check_fork(self) -> None:
        reads = self._all("surface_read")
        branches = {r["branch"] for r in reads}
        self.guards["fork_identity_ok"] = {"B0", "B+", "C"}.issubset(branches)
        if not self.guards["fork_identity_ok"]:
            self.evidence["fork_identity_ok"] = {"branches_seen": sorted(branches)}
        t1cat = self._one("t1_catalog_materialized")
        known = set(self.catalog) | set(t1cat.get("surfaces", []) if t1cat else [])
        stray = [r["surface_id"] for r in reads if r["surface_id"] not in known]
        state = self._one("compact_resume_state_minted") or {}
        hint_stray = [s for s in state.get("route_hint", []) if s not in known]
        self.guards["surface_symmetry_ok"] = not stray and not hint_stray
        if stray or hint_stray:
            self.evidence["surface_symmetry_ok"] = {"read_outside_catalog": stray,
                                                    "hint_outside_catalog": hint_stray}
        # §8a debt 5 (population verification round): frontier_terminal is
        # ENFORCED here, not just population metadata — a structurally-certain
        # mover can never enter the moved leg, attestation or no attestation.
        attested = bool(
            (self._one("compact_resume_state_minted") or {}).get(
                "frontier_unresolved_attested") or
            self._one("frontier_unresolved_at_pause"))
        terminal = bool(self.packet.get("frontier_terminal"))
        self.guards["frontier_unresolved_at_pause"] = attested and not (
            terminal and self.packet.get("world_leg") == "moved")
        if terminal and self.packet.get("world_leg") == "moved":
            self.evidence["frontier_unresolved_at_pause"] = (
                "unit is frontier_terminal — movement structurally certain; "
                "moved-leg scoring refused (borrowed foresight as a win)")

        state = self._one("compact_resume_state_minted")
        # §8a debt 2: genealogy re-derived at score time, never trusted from the
        # mint — demotion intact AND every hint is a catalog surface id (a hint
        # that names anything else is world access, whatever the mint said).
        known_surfaces = set(self.catalog) | set(
            (self._one("t1_catalog_materialized") or {}).get("surfaces", []))
        hints = (state or {}).get("route_hint", [])
        self.guards["genealogy_ok"] = bool(state) and state.get(
            "demotion") == "routing_hint_only" and all(
            h in known_surfaces for h in hints)
        self.guards["trigger_demoted_ok"] = bool(state) and set(
            state.get("forbidden_effects", [])) >= {
            "authority_delta", "eligibility_override", "answer_prefill"}

    # -- cost + parity -------------------------------------------------------------

    def _branch_costs(self, certs: set[str]) -> dict[str, dict]:
        """Replay per-branch cumulative read tokens from canonical text; find the
        information-parity prefix (first read intersecting the certificate set —
        any one member suffices, SPEC §6a redundancy rule)."""
        text = {**self.t0, **self.t1}
        out: dict[str, dict] = {}
        replay_ok = True
        for br in ("B0", "B+", "C", "C_ablated"):
            reads = sorted((r for r in self._all("surface_read") if r["branch"] == br),
                           key=lambda r: r["order"])
            if not reads:
                continue
            cum, parity_cost = 0, None
            for r in reads:
                canonical = _tokens(text.get(r["surface_id"], ""))
                if "tokens" in r and r["tokens"] != canonical:
                    replay_ok = False  # logged cost is cache, not authority
                cum += canonical
                if parity_cost is None and r["surface_id"] in certs:
                    parity_cost = cum
            out[br] = {"read_tokens": cum, "parity_cost": parity_cost,
                       "surfaces": [r["surface_id"] for r in reads]}
        state = self._one("compact_resume_state_minted") or {}
        if "C" in out:
            out["C"]["treatment_tokens"] = state.get("state_tokens", 0)
        if "C_ablated" in out:
            out["C_ablated"]["treatment_tokens"] = state.get("state_tokens", 0)
        self.guards["route_replay_ok"] = replay_ok
        return out

    def _check_silent_mandate(self, leg: str, costs: dict) -> None:
        """Silent-leg mandate-of-read (SPEC §5): the hint is an order signal,
        never an exemption. C skipping a hinted surface on a silent trigger
        fails route_cost_ok — the warmth tax is unavoidable."""
        if leg == "moved":
            self.guards["route_cost_ok"] = True
            return
        hinted = set((self._one("compact_resume_state_minted") or {}).get("route_hint", []))
        read_by_c = set(costs.get("C", {}).get("surfaces", []))
        skipped = sorted(hinted - read_by_c)
        self.guards["route_cost_ok"] = not skipped
        if skipped:
            self.evidence["route_cost_ok"] = {"hinted_but_skipped_on_silent": skipped}

    def _check_authority(self, leg: str, certs: set[str], costs: dict) -> None:
        """composer A7, both legs of it. The leak conjunction: trigger fired AND
        C's first post-fire read is uniquely the certificate surface AND B+'s
        neutral planner ranks that surface deep below equal-relevance peers AND
        B+ cannot reach the outcome without it. Ablation: a C win must survive
        removal of the reorder feature (a C_ablated lane must exist and be
        scored) while the hint's token charge stays."""
        fired = bool((self._one("trigger_observed") or {}).get("fired"))
        if leg != "moved" or not fired:
            self.guards["trigger_authority_leak_ok"] = True
            self.guards["planner_ablation_ok"] = True
            self.guards["eligibility_vs_cost_ok"] = True
            return
        plans = {p["branch"]: p for p in self._all("route_plan")}
        bplus_ranks = plans.get("B+", {}).get("neutral_rank", {})
        c_first = next(iter(costs.get("C", {}).get("surfaces", [])), None)
        leak = (c_first in certs
                and bplus_ranks.get(c_first, 0) > AUTHORITY_LEAK_RANK_GAP
                and costs.get("B+", {}).get("parity_cost") is None)
        self.guards["trigger_authority_leak_ok"] = not leak
        if leak:
            self.evidence["trigger_authority_leak_ok"] = {
                "c_first_read": c_first, "bplus_neutral_rank": bplus_ranks.get(c_first),
                "note": "reorder indistinguishable from eligibility (composer A7)"}
        # ablation lane is mandatory for any moved-leg C win to stand
        self.guards["planner_ablation_ok"] = "C_ablated" in costs
        if "C_ablated" not in costs:
            self.evidence["planner_ablation_ok"] = (
                "no C_ablated lane scored — a C win cannot be attributed without it")
        # §8a debt 1 (hermes §5, eligibility-vs-cost): the reorder is cost-order,
        # not eligibility, ONLY if the ablated lane still reaches the certificate
        # eventually — if C_ablated never reaches parity, the trigger was deciding
        # WHAT C read, not WHEN: an answer-axis win in cost clothing. Refused.
        abl = costs.get("C_ablated", {})
        self.guards["eligibility_vs_cost_ok"] = (
            "C_ablated" not in costs or abl.get("parity_cost") is not None)
        if not self.guards["eligibility_vs_cost_ok"]:
            self.evidence["eligibility_vs_cost_ok"] = (
                "C_ablated never reached the certificate — the trigger was doing "
                "eligibility, not ordering (hermes §5; answer-axis in cost clothing)")

    def _quality(self) -> dict[str, float]:
        scores: dict[str, float] = {}
        for row in self._all("branch_outcome"):
            if "agent_claimed" in json.dumps(row):
                raise ValueError("agent_claimed_* field in branch_outcome — the R5 "
                                 "fence admits world-oracle scores only")
            scores[row["branch"]] = max(scores.get(row["branch"], 0.0),
                                        float(row["oracle_score"]))
        return scores

    # -- the verdict ----------------------------------------------------------------

    def score(self) -> dict:
        leg = self.packet.get("world_leg", "silent")
        pop = self._one("population_precommit") or {}
        self._check_precommit_chain()
        self._check_order()
        self._check_fork()

        certs, parity_state = (set(), "confounded")
        if self.guards.get("population_precommit_ok"):
            certs, parity_state = derive_answer_bearing_surfaces(
                self.t0, self.t1, self.catalog, self.packet["status_key"],
                pop.get("match_rule_id", ""), pop.get("status_vocabulary", []), leg)
        self.guards["information_parity_ok"] = parity_state == "ok"
        if parity_state != "ok":
            self.evidence["information_parity_ok"] = (
                "degenerate certificate set — confounded, never a cost win (§6a)")

        costs = self._branch_costs(certs)
        self._check_silent_mandate(leg, costs)
        self._check_authority(leg, certs, costs)

        quality = self._quality()
        self.guards["quality_floor_holds"] = quality.get("C", 0.0) >= QUALITY_FLOOR
        bplus_parity = costs.get("B+", {}).get("parity_cost")
        self.guards["bplus_capable"] = (quality.get("B+", 0.0) >= QUALITY_FLOOR
                                        and (leg != "moved" or bplus_parity is not None))

        cells = self._cells(leg, costs, quality)
        return {
            "kind": "cell_verdict_group", "unit_id": self.packet["unit_id"],
            "world_leg": leg, "cost_axis": "route_read_tokens",
            "organ_identity": "warming_budget",
            "certificate_set": sorted(certs),
            "guards": dict(sorted(self.guards.items())),
            "evidence": self.evidence, "costs": costs, "quality": quality,
            "cells": cells,
            "disclosure": "wire/mock runs can NEVER promote a cell (SPEC §8); "
                          "moved-leg promotion requires a prospective trigger stamp",
        }

    def _cells(self, leg: str, costs: dict, quality: dict) -> dict:
        guards_green = all(self.guards.get(g, False) for g in GUARDS)
        c, bp = costs.get("C", {}), costs.get("B+", {})
        c_total = (c.get("parity_cost") or 0) + c.get("treatment_tokens", 0)
        bp_total = bp.get("parity_cost") or 0
        cells: dict[str, str] = {}
        if not guards_green:
            failed = sorted(g for g in GUARDS if not self.guards.get(g, False))
            return {"all": "confounded", "failed_guards": failed}

        if leg == "moved":
            c_saves = c.get("parity_cost") is not None and c_total < bp_total
            cells["WB-moved-win"] = "pass" if c_saves else "not_engaged"
            cells["WB-heir-dominates"] = "pass" if not c_saves else "not_engaged"
            if quality.get("C", 0) >= QUALITY_FLOOR and not c_saves and \
                    costs.get("B0", {}).get("parity_cost") is not None and \
                    c_total < (costs["B0"].get("parity_cost") or 0):
                cells["WB-b0-only"] = "flagged_not_positive"
        else:
            # silent/noise: C pays the warmth tax; any C cost above B+ at equal
            # quality is the priced loses-cell doing its work
            tax = (c.get("read_tokens", 0) + c.get("treatment_tokens", 0)
                   - bp.get("read_tokens", 0))
            cells["WB-silent-cost" if leg == "silent" else "WB-noise-misroute"] = (
                "pass" if tax > 0 else "not_engaged")
            if quality.get("C", 1.0) < quality.get("B+", 0.0):
                cells["WB-quality-erosion"] = "pass"
        if quality.get("C", 0.0) < QUALITY_FLOOR and quality.get("B+", 0.0) < QUALITY_FLOOR:
            cells["WB-state-null"] = "not_engaged_state_grounds"
        return cells


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("packet", help="chronology packet JSON")
    ap.add_argument("events", help="event ledger JSONL")
    args = ap.parse_args()
    packet = json.loads(Path(args.packet).read_text())
    events = [json.loads(l) for l in Path(args.events).read_text().splitlines()
              if l.strip()]
    verdict = WarmingScorer(packet, events).score()
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
