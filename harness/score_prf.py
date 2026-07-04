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
import re

from .derive_live_obligations import replay_ok
from .mint_frontier_state import recompute_state_tokens
from .sbr_util import (artifact_render_tokens, action_space_hash, catalog_hash,
                       handle_to_surface_id)
from .predicate_ast import evaluate, validate

GUARDS_V01 = ("derivation_replay_ok", "frontier_derivation_parity",
              "route_replay_ok", "mint_two_phase_ok", "reopen_ok",
              "quality_floor_holds", "reconstruction_distinct")

GUARDS_V02 = ("c_max_replay_ok", "affordance_materialized",
              "skip_computable", "decision_read_chain_ok",
              "route_replay_ok", "affordance_symmetry_ok",
              "derivation_replay_ok", "mint_two_phase_ok",
              "a_i_recomputed_ok")

CONDITIONAL_KINDS = ("discard", "reopen")


def _tokens(text: str) -> int:
    return len(text.split())


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


class PRFScorer:
    """Scores one fork group's event ledger. Verdicts are computed fail-closed."""

    def __init__(self, population: dict | None = None,
                 freeze_manifest: dict | None = None,
                 events: list[dict] | None = None,
                 t0_texts: dict[str, str] | None = None,
                 t1_texts: dict[str, str] | None = None,
                 episode: dict | None = None):
        self.pop = population
        self.manifest = freeze_manifest
        self.events = events or []
        self.t0 = t0_texts or {}
        self.t1 = t1_texts or {}
        self.episode = episode
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

    # ---------- instrument version fork (Part II §22) ----------
    def _instrument_version(self) -> str:
        if self.episode:
            return str(self.episode.get("instrument_version", "0.2"))
        cfg = self._one("run_config") or {}
        return str(cfg.get("instrument_version", "0.1"))

    def score(self) -> dict:
        ver = self._instrument_version()
        if ver in ("0.2", "0.3"):
            return self._score_v02()
        return self._score_v01()

    def _uses_rendered_a_i(self) -> bool:
        return self._instrument_version() == "0.3"

    def _recompute_a_i(self, canonical_state: dict) -> int:
        if self._uses_rendered_a_i():
            return artifact_render_tokens(canonical_state)
        return recompute_state_tokens(canonical_state)

    # ---------- v0.2 ECAC (Part II §16/§21) ----------
    def _artifact_tokens(self, branch: str) -> int:
        """a_i: rendered (0.3) or canonical-body (0.2) artifact tokens; a_i(cold)=0."""
        if branch != "resumable_state":
            return 0
        freeze = self._one("frontier_freeze")
        if not freeze or "canonical_state" not in freeze:
            return 0
        return self._recompute_a_i(freeze["canonical_state"])

    def _stale_claim_tokens(self) -> int:
        """Disclosed stale_claim carry — NOT included in a_i (§16)."""
        row = self._one("stale_claim_tokens")
        if row:
            return int(row.get("tokens", 0))
        stale = (self.episode or {}).get("stale_claim")
        if not stale:
            return 0
        from .sbr_util import render_foreground_block
        return _tokens(render_foreground_block(stale))

    def _recompute_c_max(self) -> int:
        budgets = self.episode["budgets"]
        return (budgets["max_read_tokens"]
                + budgets["max_steps"] * budgets["action_overhead_tokens"])

    def _session_reads(self, branch: str, session_id: str) -> list[dict]:
        return sorted(
            [r for r in self._rows("surface_read", branch=branch,
                                   session_id=session_id)],
            key=lambda r: r.get("step", r.get("read_index", 0)))

    def _route_session(self, branch: str, session_id: str,
                       sample_index: int) -> tuple[list[str], list[str], list[str]]:
        """SCORER-DERIVED: visible, read, skip (§15)."""
        aff = self._rows("affordance_presented", branch=branch,
                         session_id=session_id, sample_index=sample_index)
        visible = sorted(
            [r["surface_id"] for r in aff],
            key=lambda s: next(r["physical_index"] for r in aff
                                if r["surface_id"] == s))
        read = [r["surface_id"] for r in self._session_reads(branch, session_id)]
        skip = [s for s in visible if s not in set(read)]
        return visible, read, skip

    def _session_read_cost(self, branch: str, session_id: str) -> int:
        catalog = self.episode["catalog"]
        total = 0
        g = self.guards
        g.setdefault("route_replay_ok", True)
        for r in self._session_reads(branch, session_id):
            canon = _tokens(catalog[r["surface_id"]]["text"])
            logged = r.get("route_read_tokens")
            if logged is not None and logged != canon:
                g["route_replay_ok"] = False
                self.evidence.append(
                    f"route_replay_ok=false: {r['surface_id']} "
                    f"logged {logged} != canonical {canon}")
            total += canon
        return total

    def _false_continuation(self, branch: str, session_id: str,
                            sample_index: int, quality_ok: bool) -> bool | None:
        """§18: branch-blind computed event.

        Non-mock basis (§18, pays the §23 debt): content-matched against the
        precommitted stale-state answer key `expected_answer_t0` under the
        authored oracle — never prose markers, never the title. A non-mock
        run WITHOUT the key still returns None (the caller confounds,
        fail-closed). Mock wire tests keep the disclosed prose markers."""
        wire = getattr(self, "wire_test", True)
        stale_key = self.episode.get("expected_answer_t0")
        if not wire and not stale_key:
            return None
        # stamp the basis up front so the report is honest even when every
        # draw early-returns False (real-run catch 2026-07-03)
        self._fc_basis = ("mock_prose_markers" if wire
                          else "oracle_key:expected_answer_t0")
        disc = self.episode.get("discriminator_surface_id")
        if disc is None:
            return False
        visible, read, _ = self._route_session(branch, session_id, sample_index)
        if disc not in visible or disc in read or quality_ok:
            return False
        outcome = self._one("session_outcome", branch=branch,
                            session_id=session_id, sample_index=sample_index)
        if not outcome:
            return False
        answer = outcome.get("answer", "")
        from .oracle import _norm, authored_oracle
        if not wire:
            self._fc_basis = "oracle_key:expected_answer_t0"
            return authored_oracle(answer, stale_key).score >= 1.0
        # mock_prose_markers basis — wire tests only, disclosed
        self._fc_basis = "mock_prose_markers"
        stale_markers = ("pending survey", "pending confirmation",
                         "commissioning window pending")
        norm = _norm(answer)
        expected = _norm(self.episode["expected_answer_t1"])
        return any(_norm(m) in norm for m in stale_markers) and expected not in norm

    def _decision_read_chain_ok(self, branch: str, session_id: str) -> bool:
        """Bijection between successful READ decisions and surface_read rows."""
        read_steps: list[tuple[int, str]] = []
        iv = self._instrument_version()
        visible: list[str] | None = None
        if iv == "0.3":
            aff = self._rows("affordance_presented", branch=branch,
                             session_id=session_id)
            visible = sorted(
                [r["surface_id"] for r in aff],
                key=lambda s: next(r["physical_index"] for r in aff
                                    if r["surface_id"] == s))

        for d in self._rows("route_decision", branch=branch,
                            session_id=session_id):
            if not d.get("parsed") or d.get("refuse_reason"):
                continue
            if iv == "0.3" and visible is not None:
                sid = handle_to_surface_id(d.get("raw_action", ""), visible)
                if not sid:
                    continue
                read_steps.append((d["step"], sid))
                continue
            raw = d.get("raw_action", "")
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                continue
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                continue
            if str(data.get("action", "")).upper() != "READ":
                continue
            sid = data.get("surface_id")
            if not sid:
                return False
            read_steps.append((d["step"], sid))

        reads = self._session_reads(branch, session_id)
        if len(reads) != len(read_steps):
            return False
        by_step = {r["step"]: r["surface_id"] for r in reads}
        return all(by_step.get(step) == sid for step, sid in read_steps)

    def _effective_cost(self, branch: str, session_id: str, sample_index: int,
                        c_max: int) -> int:
        outcome = self._one("session_outcome", branch=branch,
                            session_id=session_id, sample_index=sample_index)
        quality_ok = bool(outcome and outcome.get("quality_ok"))
        read_cost = self._session_read_cost(branch, session_id)
        a_i = self._artifact_tokens(branch)
        if quality_ok:
            return read_cost + a_i
        return c_max

    def _affordance_symmetry_ok(self) -> bool:
        """Thin runtime guard (§19): realized rows match gated population."""
        iv = self._instrument_version()
        cat_hash = catalog_hash(self.episode["catalog"],
                                self.episode["catalog_sort"])
        act_hash = action_space_hash(iv)
        for row in self._rows("sbr_session"):
            if row.get("catalog_hash") != cat_hash:
                self.evidence.append(
                    f"catalog_hash drift in session {row.get('session_id')}")
                return False
            if row.get("action_space_hash") != act_hash:
                self.evidence.append("action_space_hash drift")
                return False
        return True

    def _score_v02(self) -> dict:
        g = self.guards
        ev = self.evidence
        cfg = self._one("run_config") or {}
        self.wire_test = bool(cfg.get("wire_test", True)) or \
            cfg.get("engine", "mock") == "mock"

        if not self.wire_test and self._one("gate_open") is None:
            ev.append("non-mock run without gate_open — confounded (§9)")
            return self._verdict_v02("confounded")

        # §17 executed N-rule, fail-closed and symmetric: if the pilot-derived
        # N exceeded the precommitted n_max, NO behavioral cell is emitted —
        # win, loss, and null alike are refused, never just the win.
        if not self.wire_test and cfg.get("ci_target_unmet"):
            ev.append(
                f"§17 CI target unmet (n_required={cfg.get('n_required')} > "
                f"n_max={cfg.get('n_max')}) — behavioral verdict refused, "
                "confounded")
            return self._verdict_v02("confounded")

        precommit = self._one("population_precommit")
        minted = self._one("frontier_state_minted")
        refused = self._one("frontier_mint_refused")
        g["mint_two_phase_ok"] = (minted is None) != (refused is None)
        if not precommit or not g["mint_two_phase_ok"]:
            ev.append("v0.2 ledger lacks population_precommit + minted-or-refused "
                      "row — confounded (§22)")
            return self._verdict_v02("confounded")
        if refused is not None:
            ev.append(f"mint refused: {refused.get('check')}/"
                      f"{refused.get('reason')} — confounded for v0.2 scoring")
            return self._verdict_v02("confounded")

        if self.pop and self.manifest:
            batch = self._one("obligation_derivation_batch")
            witness_reads = [r for r in self._rows("surface_read",
                                                   branch="uninterrupted_warm")
                             if r.get("catalog_epoch") == "t0"]
            g["derivation_replay_ok"] = bool(batch) and replay_ok(
                self.pop, self.manifest, witness_reads,
                batch.get("seam_id", ""), batch)
            if not g["derivation_replay_ok"]:
                ev.append("derivation_replay_ok=false — confounded (§22)")
                return self._verdict_v02("confounded")
        else:
            g["derivation_replay_ok"] = False
            ev.append("population/freeze_manifest missing for derivation replay")
            return self._verdict_v02("confounded")

        freeze = self._one("frontier_freeze")
        if not freeze or "canonical_state" not in freeze:
            ev.append("frontier_freeze row with canonical_state missing")
            return self._verdict_v02("confounded")
        a_recomputed = self._recompute_a_i(freeze["canonical_state"])
        # glm re-review residual A: the guard must compare the recomputation
        # against the LOGGED minted state_tokens (an independent quantity),
        # not against _artifact_tokens on the same row — that was tautological,
        # green by construction. Mismatch is blocking, not an audit note.
        g["a_i_recomputed_ok"] = minted.get("state_tokens") == a_recomputed
        if not g["a_i_recomputed_ok"]:
            ev.append(f"minted state_tokens {minted.get('state_tokens')} != "
                      f"recomputed-from-canonical_state {a_recomputed} — "
                      "a_i replay failed, confounded (§16)")
            return self._verdict_v02("confounded")

        c_max = self._recompute_c_max()
        attested = self.episode["budgets"].get("c_max")
        g["c_max_replay_ok"] = attested is None or attested == c_max
        if not g["c_max_replay_ok"]:
            ev.append(f"c_max_replay_ok=false: attested {attested} != "
                      f"recomputed {c_max}")
            return self._verdict_v02("confounded")

        g["affordance_symmetry_ok"] = self._affordance_symmetry_ok()
        if not g["affordance_symmetry_ok"]:
            return self._verdict_v02("confounded")

        regime = cfg.get("regime", "D")
        unique_real = cfg.get("unique_realizations")

        if regime == "S" and unique_real == 1:
            ev.append("zero dispersion — behavioral win refused (§17)")
            return self._verdict_v02("PRF2-zero-dispersion",
                                     ecac={"regime": regime,
                                           "unique_realizations": unique_real})

        sessions = self._rows("sbr_session")
        g["affordance_materialized"] = all(
            len(self._rows("affordance_presented", session_id=s["session_id"],
                           branch=s["branch"]))
            == len(self.episode["catalog"])
            for s in sessions)
        if not g["affordance_materialized"]:
            ev.append("affordance_materialized=false")
            return self._verdict_v02("confounded")

        branch_costs: dict[str, list[int]] = {
            "cold_reread": [], "resumable_state": []}
        false_cont_rate: dict[str, list[bool]] = {
            "cold_reread": [], "resumable_state": []}
        route_sessions: dict[str, dict] = {}

        for sess in sessions:
            if sess.get("probe"):
                continue
            branch = sess["branch"]
            sid = sess["session_id"]
            si = sess["sample_index"]
            visible, read, skip = self._route_session(branch, sid, si)
            route_sessions[f"{branch}:{si}"] = {
                "visible": visible, "read": read, "skip": skip}
            g["skip_computable"] = all(s in visible for s in read) and \
                set(skip) == set(visible) - set(read)

            chain_ok = self._decision_read_chain_ok(branch, sid)
            g["decision_read_chain_ok"] = \
                g.get("decision_read_chain_ok", True) and chain_ok
            if not chain_ok:
                ev.append(f"decision/read bijection broken in "
                          f"{branch}:{sid} — route ledger not "
                          "replay-authoritative (§34 F1)")

            outcome = self._one("session_outcome", branch=branch,
                                session_id=sid, sample_index=si)
            qok = bool(outcome and outcome.get("quality_ok"))
            branch_costs[branch].append(
                self._effective_cost(branch, sid, si, c_max))
            fc = self._false_continuation(branch, sid, si, qok)
            if fc is None and not self.wire_test:
                ev.append("no precommitted expected_answer_t0 oracle key — "
                          "false_continuation unavailable for a non-mock run, "
                          "confounded (§18/§23)")
                return self._verdict_v02("confounded")
            false_cont_rate[branch].append(bool(fc))

        g.setdefault("route_replay_ok", True)
        if not g.get("route_replay_ok", True):
            return self._verdict_v02("confounded")
        g.setdefault("decision_read_chain_ok", True)
        if not g["decision_read_chain_ok"]:
            # accumulated across ALL non-probe sessions (build review F1):
            # a broken bijection in any session confounds — never a cell.
            return self._verdict_v02("confounded")

        def mean(xs: list[int]) -> float:
            return sum(xs) / len(xs) if xs else float("inf")

        mean_cold = mean(branch_costs["cold_reread"])
        mean_res = mean(branch_costs["resumable_state"])
        ecac = {
            "mean_eff_cold": mean_cold,
            "mean_eff_resumable": mean_res,
            "c_max": c_max,
            "a_i_resumable": self._artifact_tokens("resumable_state"),
            "a_i_cold": 0,
            "stale_claim_tokens": self._stale_claim_tokens(),
            "false_continuation_basis": getattr(
                self, "_fc_basis", "mock_prose_markers"),
            "regime": regime,
            "route_sessions": route_sessions,
            "false_continuation_rate": {
                b: (sum(v) / len(v) if v else 0.0)
                for b, v in false_cont_rate.items()},
        }

        sf = self.episode.get("self_falsification")
        kind = self.episode.get("expected_cells", {}).get("kind")
        cost_win = mean_res < mean_cold

        if sf == "ballast_discriminator" and cost_win:
            ev.append("PRF2-cost-win fired on ballast-discriminator — "
                      "instrument self-refutation")
            return self._verdict_v02("PRF2-ballast-null", ecac=ecac)

        if sf == "neutral_frontier" and cost_win:
            ev.append("resumable beat cold on neutral-frontier — "
                      "instrument self-refutation (band=0)")
            return self._verdict_v02("PRF2-neutral-null", ecac=ecac)

        if cost_win and regime == "S" and unique_real and unique_real > 1:
            return self._verdict_v02("PRF2-cost-win", ecac=ecac)
        if mean_res > mean_cold:
            return self._verdict_v02("PRF2-cost-loss", ecac=ecac)
        if not cost_win and mean_res <= mean_cold:
            return self._verdict_v02("PRF2-heir-dominates", ecac=ecac)
        if cost_win and regime == "D":
            ev.append("point-mode Regime-D win — machinery only, not behavioral")
            return self._verdict_v02("PRF2-heir-dominates", ecac=ecac)
        return self._verdict_v02("PRF2-heir-dominates", ecac=ecac)

    def _verdict_v02(self, cell: str, ecac: dict | None = None) -> dict:
        return {
            "kind": "cell_verdict",
            "instrument": "pause_resume_frontier",
            "instrument_version": self._instrument_version(),
            "cell": cell,
            "guards": {k: self.guards.get(k, False) for k in GUARDS_V02},
            "ecac": ecac or {},
            "evidence": list(self.evidence),
            "wire_test": getattr(self, "wire_test", True),
        }

    # ---------- v0.1 (Part I) ----------
    def _score_v01(self) -> dict:
        g = self.guards
        ev = self.evidence

        # gate_open enforcement (build-review fix #9, X2 pattern): a NON-mock
        # verdict requires the computed §9 gate_open row in the ledger; mock
        # wire runs are disclosed as wire_test either way.
        cfg = self._one("run_config") or {}
        self.wire_test = bool(cfg.get("wire_test", True)) or \
            cfg.get("engine", "mock") == "mock"
        if not self.wire_test and self._one("gate_open") is None:
            ev.append("non-mock run without a computed gate_open row — "
                      "confounded (§9)")
            return self._verdict("confounded")

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
            # refusal-reason -> cell (build-review fix #7): the content-floor
            # family (honorary artifact) is PRF-over-wipe; only banned
            # work-product/vocab shapes are answer-cache; anything outside
            # the enum confounds rather than misroutes.
            cell = {"state_content_void": "PRF-over-wipe",
                    "fixture_obligations_decorative": "PRF-over-wipe",
                    "obligation_ballast_below_gamma": "PRF-over-wipe",
                    "work_product_field": "PRF-answer-cache",
                    "out_of_vocab_token": "PRF-answer-cache"}.get(
                refused.get("reason"))
            if cell is None:
                ev.append(f"unknown mint refusal reason "
                          f"{refused.get('reason')!r}")
                return self._verdict("confounded")
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
                "instrument_version": "0.1",
                "cell": cell,
                "guards": {k: self.guards.get(k, False) for k in GUARDS_V01},
                "costs": costs or {},
                "evidence": list(self.evidence),
                "wire_test": getattr(self, "wire_test", True)}
