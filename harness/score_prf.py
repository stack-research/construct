"""PRF scorer — SPEC_PAUSE_RESUME v0.1 §6/§7/§8 machinery.

The instrument's question (governed-hint efficiency, §0): does a witnessed,
schema-bound frontier artifact let a fresh engine instance reach ADEQUATE
continuation at lower `route_read_tokens` than cold reread of the symmetric
post-seam catalog? `PRF-heir-dominates` is a first-class predeclared null.

Build scope (§12): machinery + mock wire tests. Nothing here can promote a
cell — real-engine evidence waits on `check_prf_fixture` green and the §6
determinism policy (frozen prefix plans or disclosed multi-sample; never one
draw).

Everything is computed, never narrated (X2 replay discipline, transfers
whole):
  - the continuation checkpoint is scorer-derived from harness `surface_read`
    rows intersected with the derived obligations' satisfaction predicates —
    runner narration of "checkpoint reached" is audit at most;
  - every cost term is recomputed from canonical surface text; a logged
    token total that disagrees confounds the cost cells (`route_replay_ok`);
  - `frontier_artifact_tokens` (D3's A) is recomputed from the canonical
    state at `state_digest`;
  - the derivation is replayed (`derivation_replay_ok`); hash mismatch
    confounds everything downstream.

D3 (§7): resumable_cost = A + P + R vs cold_cost = C, assessed at the
continuation checkpoint. A is charged on EVERY resume. `frontier_stale_reopen`
forgives wrong continuity; it does not forgive the cost of having carried
stale warmth. Three regions: wins (A+P+R < C at the floor), null (honest
reopen that did not pay for its carry), loses (false continuity on a cheaper
path / invalid reopen / replay failure).
"""

from __future__ import annotations

import hashlib
import json

from .derive_live_obligations import replay_ok
from .mint_frontier_state import recompute_state_tokens
from .predicate_ast import evaluate, validate

GUARDS = ("derivation_replay_ok", "frontier_derivation_parity",
          "route_replay_ok", "mint_two_phase_ok", "reopen_ok",
          "quality_floor_holds", "reconstruction_distinct")

CONDITIONAL_KINDS = ("discard", "reopen")


def _tokens(text: str) -> int:
    return len(text.split())


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


class PRFScorer:
    """Scores one fork group's event ledger against the population contract
    and the canonical T0/T1 surface texts. Verdicts are computed fail-closed:
    a missing guard is a failed guard, and every failed guard names itself."""

    def __init__(self, population: dict, freeze_manifest: dict,
                 events: list[dict], t0_texts: dict[str, str],
                 t1_texts: dict[str, str]):
        self.pop = population
        self.manifest = freeze_manifest
        self.events = events
        self.t0 = t0_texts
        self.t1 = t1_texts
        self.evidence: list[str] = []
        self.guards: dict[str, bool] = {}

    # ---------- row access ----------
    def _rows(self, kind: str, **match) -> list[dict]:
        return [r for r in self.events if r.get("kind") == kind
                and all(r.get(k) == v for k, v in match.items())]

    def _one(self, kind: str, **match) -> dict | None:
        rows = self._rows(kind, **match)
        return rows[0] if rows else None

    def _reads(self, branch: str) -> list[dict]:
        return sorted(self._rows("surface_read", branch=branch,
                                 catalog_epoch="t1"),
                      key=lambda r: r["read_index"])

    # ---------- context for satisfaction predicates ----------
    def _ctx(self, surface_id: str) -> dict:
        meta = self.pop["catalog"].get(surface_id, {})
        return {**meta.get("fields", {}),
                "surface_id": surface_id,
                "surface_tags": meta.get("surface_tags", []),
                "catalog_epoch": "t1",
                "surface_hash_t0": _sha(self.t0.get(surface_id, "")),
                "surface_hash_t1": _sha(self.t1.get(surface_id, ""))}

    # ---------- the continuation checkpoint (scorer-derived, branch-blind) ----
    def checkpoint(self, branch: str, valid_reopen_index: int | None,
                   carries_frontier: bool = True) -> tuple[int | None, dict]:
        """First read prefix at which every derived obligation is RESOLVED:
        verify/read obligations resolve when their satisfaction predicate
        evaluates true on a read surface; conditional obligations (discard/
        reopen kinds) resolve when their predicate has been EVALUATED on a
        read of a source surface — false = still-valid frontier, true =
        invalidated. A branch that CARRIES the frontier (resumable-state) must
        answer an invalidation with a valid `frontier_stale_reopen` to remain
        honest; cold-reread carries no frontier, so an invalidation is just
        world truth it read. Returns (read_index or None, resolution map)."""
        obligations = self._rows("live_obligation_derived")
        library = self.pop["predicate_library"]
        status: dict[str, str] = {o["obligation_id"]: "pending"
                                  for o in obligations}
        reads = self._reads(branch)
        checkpoint_at = None
        for row in reads:
            ctx = self._ctx(row["surface_id"])
            for o in obligations:
                oid = o["obligation_id"]
                if status[oid] != "pending":
                    continue
                relevant = row["surface_id"] in o["source_read_ids"] or \
                    o["obligation_type"] in ("verify", "read")
                if not relevant:
                    continue
                pred = library[o["satisfaction_predicate_id"]]
                validate(pred)
                fired = evaluate(pred, ctx)
                if o["obligation_type"] in CONDITIONAL_KINDS:
                    status[oid] = "invalidated" if fired else "satisfied"
                elif fired:
                    status[oid] = "satisfied"
            invalidated = [oid for oid, s in status.items()
                           if s == "invalidated"]
            unresolved = [oid for oid, s in status.items() if s == "pending"]
            if not unresolved:
                if carries_frontier and invalidated and \
                        valid_reopen_index is None:
                    # frontier invalidated with no honest reopen: the branch
                    # never reaches an adequate checkpoint on this route
                    return None, status
                checkpoint_at = row["read_index"]
                break
        return checkpoint_at, status

    # ---------- reopen validity (§7 fail-closed + §4c-3 engagement) ----------
    def validate_reopen(self, branch: str) -> tuple[int | None, bool]:
        """Returns (read_index_at_reopen or None, reopen_ok). No reopen row is
        (None, True) — reopening is never mandatory; continuing through an
        invalidated frontier is caught by the checkpoint/quality legs."""
        row = self._one("frontier_stale_reopen", branch=branch)
        if row is None:
            return None, True
        rules = self.pop.get("reopen_rules", {})
        rule = rules.get(row.get("reopen_rule_id"))
        if rule is None or row.get("population_reopen_rules_hash") != \
                self.pop.get("population_reopen_rules_hash"):
            self.evidence.append("reopen_unreplayable: reopen rule not "
                                 "population-pinned")
            return row.get("read_index_at_reopen"), False
        if row.get("reopen_reason") not in ("changed_world", "stale_frontier",
                                            "rulebook_obligation_invalidated"):
            self.evidence.append(
                f"reopen_unreplayable: reason {row.get('reopen_reason')!r} "
                "outside the enum")
            return row.get("read_index_at_reopen"), False
        inv = row.get("invalidating_surface_ids", [])
        if not inv or any(s not in self.pop["catalog"] for s in inv):
            self.evidence.append("catalog_asymmetry: invalidating surface not "
                                 "in the symmetric catalog")
            return row.get("read_index_at_reopen"), False
        # §4c-3 strict invalidation engagement: the invalidating surfaces must
        # have been ACTUALLY READ before the reopen row, and must evaluate
        # true under the pinned invalidation predicate. Reflexive reopen fails.
        idx = row.get("read_index_at_reopen")
        read_before = {r["surface_id"] for r in self._reads(branch)
                       if idx is not None and r["read_index"] < idx}
        if not set(inv) <= read_before:
            self.evidence.append("reopen_unjustified: invalidating surfaces "
                                 "were not read before the reopen row "
                                 "(engagement leg, §4c-3)")
            return idx, False
        pred = self.pop["predicate_library"][rule["invalidation_predicate_id"]]
        validate(pred)
        if not all(evaluate(pred, self._ctx(s)) for s in inv):
            self.evidence.append("reopen_unjustified: invalidation predicate "
                                 "false on the cited surfaces")
            return idx, False
        return idx, True

    # ---------- cost recompute (route_replay_ok) ----------
    def _cost(self, reads: list[dict]) -> int:
        total = 0
        for r in reads:
            canon = _tokens(self.t1.get(r["surface_id"], ""))
            logged = r.get("route_read_tokens")
            if logged is not None and logged != canon:
                self.guards["route_replay_ok"] = False
                self.evidence.append(
                    f"route_replay_ok=false: {r['surface_id']} logged "
                    f"{logged} != canonical {canon}")
            total += canon
        return total

    # ---------- the verdict ----------
    def score(self) -> dict:
        g = self.guards
        ev = self.evidence

        # derivation replay is the authority
        batch = self._one("obligation_derivation_batch")
        witness_reads = [r for r in self._rows("surface_read",
                                               branch="uninterrupted_warm")
                         if r.get("catalog_epoch") == "t0"]
        g["derivation_replay_ok"] = bool(batch) and replay_ok(
            self.pop, self.manifest, witness_reads, batch.get("seam_id", ""),
            batch)
        if not g["derivation_replay_ok"]:
            ev.append("derivation_replay_ok=false: re-derivation does not "
                      "reproduce obligation_set_hash")
            return self._verdict("confounded")

        # two-phase mint: exactly one of minted/refused per fork; a refusal
        # is a terminal cell, not a scored run
        minted = self._one("frontier_state_minted")
        refused = self._one("frontier_mint_refused")
        g["mint_two_phase_ok"] = (minted is None) != (refused is None)
        if not g["mint_two_phase_ok"]:
            ev.append("mint_two_phase_ok=false: minted and refused rows are "
                      "not mutually exclusive")
            return self._verdict("confounded")
        if refused is not None:
            cell = {"state_content_void": "PRF-over-wipe"}.get(
                refused.get("reason"), "PRF-answer-cache")
            ev.append(f"mint refused: {refused.get('check')}/"
                      f"{refused.get('reason')} — branch never resumed")
            return self._verdict(cell)

        # A recomputed from the canonical state (logged is audit-only)
        freeze = self._one("frontier_freeze")
        if not freeze or "canonical_state" not in freeze:
            ev.append("frontier_freeze row with canonical_state missing")
            return self._verdict("confounded")
        a_tokens = recompute_state_tokens(freeze["canonical_state"])
        if minted.get("state_tokens") not in (None, a_tokens):
            ev.append(f"state_tokens logged {minted['state_tokens']} != "
                      f"recomputed {a_tokens} (audit note)")

        g.setdefault("route_replay_ok", True)
        reopen_idx, g_reopen = self.validate_reopen("resumable_state")
        g["reopen_ok"] = g_reopen

        cold_cp, _ = self.checkpoint("cold_reread", None,
                                     carries_frontier=False)
        res_cp, res_status = self.checkpoint(
            "resumable_state", reopen_idx if g_reopen else None)

        cold_reads = self._reads("cold_reread")
        res_reads = self._reads("resumable_state")
        C = self._cost([r for r in cold_reads
                        if cold_cp is not None and r["read_index"] <= cold_cp])
        if reopen_idx is not None:
            P = self._cost([r for r in res_reads if r["read_index"] < reopen_idx])
            R = self._cost([r for r in res_reads
                            if res_cp is not None
                            and reopen_idx <= r["read_index"] <= res_cp])
        else:
            P = 0
            R = self._cost([r for r in res_reads
                            if res_cp is not None and r["read_index"] <= res_cp])
        costs = {"A": a_tokens, "P": P, "R": R, "C": C,
                 "resumable_total": a_tokens + P + R,
                 "cold_checkpoint": cold_cp, "resumable_checkpoint": res_cp}

        # quality floor: world-oracle rows only (R5 fence — never narration)
        floors = {r["branch"]: bool(r.get("quality_ok"))
                  for r in self._rows("branch_outcome")}
        g["quality_floor_holds"] = floors.get("resumable_state", False)
        cold_ok = floors.get("cold_reread", False)

        if not g["route_replay_ok"]:
            return self._verdict("confounded", costs)
        if cold_cp is None or not cold_ok:
            ev.append("cold_reread did not reach an adequate checkpoint — "
                      "comparator_incapable")
            return self._verdict("comparator_incapable", costs)

        invalidated = [o for o, s in res_status.items() if s == "invalidated"]

        # loses: false continuity — frontier invalidated, no honest reopen,
        # quality floor failed on a path cheaper than cold (priced, §7)
        if res_cp is None or not g["quality_floor_holds"]:
            spent = a_tokens + self._cost(res_reads)
            if not g_reopen:
                ev.append("invalid reopen scored as false continuity")
            cell = "PRF-stale-frontier" if self._stale_invalidator(invalidated) \
                else "PRF-changed-world"
            if spent < C:
                ev.append(f"false continuity was cheaper than cold "
                          f"({spent} < {C}) — priced lose")
                return self._verdict(cell, costs)
            ev.append("false continuity not cheaper than cold — lose engaged "
                      "but the fixture gate should have priced it")
            return self._verdict(cell, costs)

        # reconstruction-illusion guard: a resumable win must be
        # obligation-targeted — reading the whole cold sweep is
        # indistinguishable from cold-reread-with-a-good-summary
        res_set = {r["surface_id"] for r in res_reads
                   if r["read_index"] <= res_cp}
        cold_set = {r["surface_id"] for r in cold_reads
                    if r["read_index"] <= cold_cp}
        g["reconstruction_distinct"] = res_set != cold_set or reopen_idx is not None
        g["frontier_derivation_parity"] = True  # tuples checked at mint (D1)

        total = costs["resumable_total"]
        if reopen_idx is not None and g_reopen:
            if total < C:
                return self._verdict("PRF-reopen-win", costs)
            ev.append("honest reopen did not pay for its stale carry — null, "
                      "not a loss")
            return self._verdict("PRF-reopen-null", costs)
        if total < C:
            if not g["reconstruction_distinct"]:
                ev.append("resumable read the full cold sweep — win refused "
                          "(reconstruction-illusion)")
                return self._verdict("PRF-reconstruction-illusion", costs)
            return self._verdict("PRF-frontier-win", costs)
        return self._verdict("PRF-heir-dominates", costs)

    def _stale_invalidator(self, invalidated_ids: list[str]) -> bool:
        obs = {o["obligation_id"]: o
               for o in self._rows("live_obligation_derived")}
        return any(obs[oid]["obligation_type"] == "reopen"
                   for oid in invalidated_ids if oid in obs)

    def _verdict(self, cell: str, costs: dict | None = None) -> dict:
        return {"kind": "cell_verdict", "instrument": "pause_resume_frontier",
                "cell": cell,
                "guards": {k: self.guards.get(k, False) for k in GUARDS},
                "costs": costs or {},
                "evidence": list(self.evidence),
                "wire_test": True}
