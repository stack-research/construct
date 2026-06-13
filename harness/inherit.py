"""M1 inheritance mechanisms (SPEC_M1 v0.1 §2–§3): the dual ablation and the heir filter.

Counterfactual-offer ablation is a FIXED-BUDGET SUBSTITUTION (codex blocker):
the forced record replaces the lowest-ranked normally-offered record at the
same top_k/token budget. An append-style run would measure robustness to extra
context, not suppression causality — if ever needed it is a different row kind.

derive_heir_store is a pure function over gen-1 evidence: ledger + sidecar +
store -> heir store + inherited authority + provenance. The unit of inherited
failure memory is the record-plus-its-governance-state, never the record alone.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .authority import AuthorityStore
from .engine import render_foreground
from .ledger import Ledger
from .runner import BranchConfig, Episode, select_offers

FILTER_VERSION = "heir-filter-v2"  # v2: direction-aware (indicted/exonerated, SPEC_M1 v0.2)
# v1 priority filter (cursor): governance withholdings only — the gate's
# intended suppressions are the question; rank-budget noise is not.
GOVERNANCE_REASONS = ("eligibility_below_threshold", "superseded_by:", "yields_to_live_input:")


def _is_governance_withholding(reason: str) -> bool:
    return reason.startswith(GOVERNANCE_REASONS)


def run_counterfactual_offers(
    episode: Episode, branch: BranchConfig, engine, ledger: Ledger, run_id: str
) -> dict[str, bool]:
    """Fixed-budget substitution per governance-withheld record (SPEC_M1 §2).
    Returns {record_id: suppression_load_bearing}. Gen-1 derivation only."""
    offered, withheld, _ = select_offers(branch, episode)
    foreground_block = render_foreground(episode.foreground_data)
    base = engine.run(episode.question, [r.text for r, _ in offered], foreground_block)
    base_score = episode.score(base.answer).score

    out: dict[str, bool] = {}
    include_rank_budget = getattr(episode, "m1_counterfactual_include_rank_budget", False)
    for record, reason in withheld:
        if not _is_governance_withholding(reason):
            # SPEC_M1 §2 priority-filter exception: a cell may declare
            # rank-budget the mechanism (I1-timing) via episode flag.
            if not (include_rank_budget and reason == "below_rank_budget"):
                continue
        if offered:
            replaced = offered[-1][0]  # lowest-ranked offered record
            forced_texts = [r.text for r, _ in offered[:-1]] + [record.text]
        else:
            replaced = None
            forced_texts = [record.text]
        forced = engine.run(episode.question, forced_texts, foreground_block)
        forced_score = episode.score(forced.answer).score
        load_bearing_absent = forced_score < base_score
        out[record.record_id] = load_bearing_absent
        ledger.write({
            "kind": "counterfactual_offer_run", "run_id": run_id,
            "episode_id": episode.episode_id, "branch_id": branch.branch_id,
            "forced_record_id": record.record_id,
            "replaced_record_id": replaced.record_id if replaced else None,
            "withholding_reason": reason,
            "original_offer_set": [r.record_id for r, _ in offered],
            "forced_offer_set": [r.record_id for r, _ in offered[:-1]] + [record.record_id]
            if offered else [record.record_id],
            "oracle_score_before": base_score, "oracle_score_after": forced_score,
            "suppression_load_bearing": load_bearing_absent,
            "branch_output": {"answer": forced.answer, "tool_calls": []},
        })
    return out


def derive_heir_store(
    gen1_ledger_path: Path,
    source_authority_path: Path,
    records: list,
    derivation_ledger: Ledger,
    source_branch: str = "L2s",
    heir_filter: str = "full",  # full | active_only (the H2 naive contrast)
) -> tuple[frozenset, dict[str, float]]:
    """Classify every gen-1 record from ledger evidence (SPEC_M1 §3) and emit
    heir_derivation rows. Returns (inherited_record_ids, inherited_authority)."""
    rows = Ledger(gen1_ledger_path).rows()
    ledger_hash = hashlib.sha256(gen1_ledger_path.read_bytes()).hexdigest()
    src = [r for r in rows if r.get("branch_id") == source_branch]

    # Direction-aware evidence buckets (SPEC_M1 v0.2 §2): harm and help must
    # not inherit identically. Legacy ablation rows without baseline_oracle_score
    # fall back to direction-blind 'active' (disclosed in the derivation row).
    active_evidence: dict[str, list[str]] = {}
    indicted_evidence: dict[str, list[str]] = {}
    cautionary_evidence: dict[str, list[str]] = {}
    exonerated_evidence: dict[str, list[str]] = {}
    legacy_direction: set[str] = set()
    tested: set[str] = set()
    for r in src:
        rid = r.get("ablated_record_id") or r.get("forced_record_id") or r.get("record_id")
        if r["kind"] == "ablation_run" and r["outcome_changed"]:
            base = r.get("baseline_oracle_score")
            if base is not None and r["oracle_score"] > base:
                indicted_evidence.setdefault(rid, []).append(r["episode_id"])  # removal improves
            else:
                active_evidence.setdefault(rid, []).append(r["episode_id"])  # removal degrades
                if base is None:
                    legacy_direction.add(rid)
        if r["kind"] == "counterfactual_offer_run":
            if r["suppression_load_bearing"]:
                cautionary_evidence.setdefault(rid, []).append(r["episode_id"])  # forcing degrades
            elif r["oracle_score_after"] > r["oracle_score_before"]:
                exonerated_evidence.setdefault(rid, []).append(r["episode_id"])  # forcing improves
                # Transitive indictment: the suppressor named in the withholding
                # reason buried the truth (SPEC_M1 v0.2 §3).
                reason = r.get("withholding_reason", "")
                if reason.startswith("superseded_by:"):
                    indicted_evidence.setdefault(reason.split(":", 1)[1], []).append(r["episode_id"])
        if r["kind"] == "offer" or (
            r["kind"] == "withholding" and _is_governance_withholding(r["reason"])
        ):
            tested.add(rid)

    authority = AuthorityStore(source_authority_path)
    inherited: set[str] = set()
    inherited_authority: dict[str, float] = {}
    counts = {"active": 0, "indicted": 0, "cautionary": 0, "exonerated": 0,
              "dropped_passenger": 0, "dropped_untested": 0}
    INDICTED_CLAMP = 0.1
    for rec in records:
        rid = rec.record_id
        # Precedence (SPEC_M1 v0.2 §3): harm dominates help.
        if rid in indicted_evidence and heir_filter == "full":
            cls = "indicted"
        elif rid in cautionary_evidence and heir_filter == "full":
            cls = "cautionary"
        elif rid in active_evidence:
            cls = "active"
        elif rid in exonerated_evidence and heir_filter == "full":
            cls = "exonerated"
        elif rid in tested or rid in cautionary_evidence or rid in indicted_evidence:
            cls = "dropped_passenger"
        else:
            cls = "dropped_untested"
        counts[cls] += 1
        if cls in ("active", "cautionary", "exonerated"):
            inherited.add(rid)
            # Bounded inheritance (codex): the earned value carried as-is.
            inherited_authority[rid] = authority.get(rid)
        elif cls == "indicted":
            inherited.add(rid)
            # The indictment lives in the layer the foreground cannot write:
            # clamped authority suppresses at gate 1, so a planted supersedes
            # link never reaches gate 3. Original preserved in the row.
            inherited_authority[rid] = min(authority.get(rid), INDICTED_CLAMP)
        evidence_eps = (indicted_evidence.get(rid) or cautionary_evidence.get(rid)
                        or active_evidence.get(rid) or exonerated_evidence.get(rid) or [])
        derivation_ledger.write({
            "kind": "heir_derivation", "record_id": rid, "class": cls,
            "earning_episodes": evidence_eps,
            "original_authority": authority.get(rid),
            "inherited_authority": inherited_authority.get(rid),
            "direction_legacy_fallback": rid in legacy_direction or None,
            "source_branch": source_branch,
            "source_authority_path": str(source_authority_path),
            "source_ledger_hash": ledger_hash,
            "filter_version": FILTER_VERSION, "heir_filter": heir_filter,
        })

    total = len(records)
    derivation_ledger.write({
        "kind": "heir_derivation_summary",
        "heir_filter": heir_filter, "filter_version": FILTER_VERSION,
        "source_branch": source_branch, "source_ledger_hash": ledger_hash,
        "total_records": total, **counts,
        "prune_ratio": round((counts["dropped_passenger"] + counts["dropped_untested"]) / total, 3)
        if total else 0.0,
    })
    return frozenset(inherited), inherited_authority


def write_heir_sidecar(path: Path, inherited_authority: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(inherited_authority, indent=2, sort_keys=True))
