"""Contribution-boundary scorer (SPEC_M1.5 — the offer ledger, one level up).

Computes `contribution_verdict` rows from an intervention ledger plus the
artifact trace it points at — never from the contributor's claim. This is R5
(`self-classification != usage`) at the agent-intervention level: an
`intervention` row carries a *claim* (audit input); `contribution_verdict`
carries the *computed* load-bearing decision, and the two never get copied
across.

Load-bearing is an artifact counterfactual: does the target artifact's current
state depend on the intervention? Resolved by closed pointer types, deterministic
and fail-closed — the scorer never interprets thread prose. `review_basis` is
single-valued, strongest-wins by BASIS_PRECEDENCE.

Usage:
  python -m harness.score_contribution runs/m1_5/contributions.jsonl
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .ledger import Ledger

REPO = Path(__file__).resolve().parent.parent

# Strongest basis wins when several resolve (kagi #3 / cursor #3 / grok #3).
BASIS_PRECEDENCE = ["artifact_diff", "scorer_evidence", "human_moderation", "later_audit"]


def _git(*args: str) -> tuple[int, str]:
    p = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    return p.returncode, p.stdout.strip()


def _commit_files(sha: str) -> list[str] | None:
    """Files touched by a commit, or None if the commit does not resolve."""
    code, _ = _git("cat-file", "-e", f"{sha}^{{commit}}")
    if code != 0:
        return None
    code, out = _git("show", "--name-only", "--pretty=format:", sha)
    if code != 0:
        return None
    return [l for l in out.splitlines() if l.strip()]


def _ledger_rows(rel_path: str) -> list[dict]:
    p = REPO / rel_path
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def resolve_pointer(ptr: dict, target_artifact: str) -> dict:
    """Resolve one typed pointer. Returns a dict with:
      resolved: bool        — the pointer object exists
      grants_load_bearing   — a non-vacuous artifact counterfactual (delta / chain)
      basis                 — the review_basis this pointer would supply, or None
      source                — 'world_checked' | 'artifact_grounded' | None
      detail                — machine-checkable evidence of what was resolved
    Fails closed: an unresolved pointer grants nothing.
    """
    t = ptr.get("type")

    if t == "commit_sha":
        files = _commit_files(ptr["value"])
        if files is None:
            return {"resolved": False, "grants_load_bearing": False, "basis": None,
                    "source": None, "detail": {"commit": ptr["value"], "error": "commit not found"}}
        artifact = ptr.get("artifact", target_artifact)
        touched = artifact in files
        return {
            "resolved": True,
            "grants_load_bearing": touched,  # non-vacuous delta on the named path
            "basis": "artifact_diff" if touched else None,
            "source": "artifact_grounded" if touched else None,
            "detail": {"commit": ptr["value"], "artifact": artifact, "touched": touched},
        }

    if t == "corpus_record_id":
        # Presence only — load-bearing for a corpus record comes via the
        # scorer_evidence chain that consumes it (cursor's resolver table).
        f = REPO / ptr["artifact"]
        present = False
        if f.exists():
            stem_match = f.stem == ptr["value"]
            present = stem_match or (ptr["value"] in f.read_text())
        return {"resolved": present, "grants_load_bearing": False, "basis": None,
                "source": None,
                "detail": {"corpus_record": ptr["value"], "artifact": ptr["artifact"], "present": present}}

    if t == "scorer_evidence":
        # Walk to the named ledger's cell_verdict and read its oracle source.
        rows = _ledger_rows(ptr["ledger"])
        cv = next((r for r in rows
                   if r.get("kind") == "cell_verdict" and r.get("cell") == ptr["cell"]), None)
        if cv is None:
            return {"resolved": False, "grants_load_bearing": False, "basis": None,
                    "source": None, "detail": {"ledger": ptr["ledger"], "cell": ptr["cell"],
                                               "error": "cell_verdict not found"}}
        if cv.get("verdict") not in ("pass", "fail") or cv.get("wire_test"):
            return {"resolved": True, "grants_load_bearing": False, "basis": None, "source": None,
                    "detail": {"cell": ptr["cell"], "verdict": cv.get("verdict"),
                               "wire_test": cv.get("wire_test"),
                               "error": "terminal verdict is audit_pending/wire_test — no close-gate credit"}}
        oracle_source = cv.get("evidence", {}).get("oracle_source") or cv.get("oracle_source")
        world = oracle_source not in (None, "authored")
        return {
            "resolved": True,
            "grants_load_bearing": True,
            "basis": "scorer_evidence",
            "source": "world_checked" if world else "artifact_grounded",
            "detail": {"ledger": ptr["ledger"], "cell": ptr["cell"], "verdict": cv["verdict"],
                       "oracle_source": oracle_source},
        }

    if t == "thread_entry_ts":
        f = REPO / ".substrate" / "threads" / ptr["thread"] / f"{ptr['value']}__{ptr['agent']}.md"
        present = f.exists() and f.read_text().strip() != ""
        # Presence only — never load-bearing by itself (cursor's resolver table).
        return {"resolved": present, "grants_load_bearing": False, "basis": None, "source": None,
                "detail": {"thread_entry": f"{ptr['value']}__{ptr['agent']}", "present": present}}

    if t == "human_moderation":
        # Disclosed external evidence (a moderation row exists), never close-gate alone.
        rows = _ledger_rows(ptr["ledger"])
        present = any(r.get("kind") == "moderation" and r.get("intervention_id") == ptr.get("value")
                      for r in rows)
        return {"resolved": present, "grants_load_bearing": False, "basis": "human_moderation" if present else None,
                "source": None, "detail": {"moderation_row": ptr.get("value"), "present": present}}

    # later_audit is a *deferred* basis — never present at score time.
    return {"resolved": False, "grants_load_bearing": False, "basis": None, "source": None,
            "detail": {"type": t, "error": "unknown or deferred pointer type"}}


def score_intervention(iv: dict) -> dict:
    resolved = [resolve_pointer(p, iv["target_artifact"]) for p in iv.get("artifact_pointers", [])]

    granting = [r for r in resolved if r["grants_load_bearing"]]
    load_bearing = bool(granting)

    # Strongest basis among everything that resolved with a basis.
    bases = [r["basis"] for r in resolved if r["basis"]]
    review_basis = min(bases, key=BASIS_PRECEDENCE.index) if bases else None

    # source: world_checked dominates; else artifact_grounded if any delta; else authored.
    if any(r["source"] == "world_checked" for r in granting):
        source = "world_checked"
    elif granting:
        source = "artifact_grounded"
    else:
        source = "authored"

    claimed_lb = bool(iv.get("claimed_load_bearing"))
    claimed_outcome = iv.get("claimed_outcome")

    # outcome, against the trace.
    if not load_bearing:
        outcome = "passenger"
    elif claimed_outcome == "blocked":
        # blocked needs TWO resolved pointers showing the prevented delta (cursor #1).
        if sum(1 for r in resolved if r["grants_load_bearing"]) >= 2:
            outcome = "blocked"
        else:
            outcome = "passenger"
            load_bearing = False
            review_basis = None
            source = "authored"
    elif claimed_outcome in ("landed", "reversed"):
        outcome = claimed_outcome
    else:
        outcome = "landed"

    # disposition: did the computed verdict substantiate the claim?
    if load_bearing and review_basis in ("artifact_diff", "scorer_evidence"):
        disposition = "substantiated"
    elif claimed_lb and not load_bearing:
        disposition = "unsubstantiated"  # the refused inflated claim (CB-loses)
    else:
        disposition = "passenger"        # honest non-load-bearing

    return {
        "kind": "contribution_verdict",
        "intervention_id": iv["intervention_id"],
        "contributor": iv.get("contributor"),
        "intervention_kind": iv.get("intervention_kind"),
        "target_artifact": iv["target_artifact"],
        "outcome": outcome,
        "load_bearing": load_bearing,
        "disposition": disposition,
        "review_basis": review_basis,
        "source": source,
        "claimed_load_bearing": claimed_lb,
        "reversal_of": iv.get("reversal_of"),
        "evidence": {"resolved_pointers": resolved},
    }


def _cell(cell: str, verdict: str, evidence: dict) -> dict:
    return {"kind": "cell_verdict", "cell": cell, "verdict": verdict, "evidence": evidence}


def score_cells(verdicts: list[dict]) -> list[dict]:
    cb1 = [v for v in verdicts
           if v["disposition"] == "substantiated" and v["outcome"] in ("landed", "blocked")]
    refused = [v for v in verdicts if v["disposition"] == "unsubstantiated"]
    passengers = [v for v in verdicts
                  if v["disposition"] == "passenger" and not v["claimed_load_bearing"]]
    world = [v for v in verdicts if v["source"] == "world_checked"]

    cells = []
    cells.append(_cell("CB-1", "pass" if cb1 else "fail", {
        "substantiated": [v["intervention_id"] for v in cb1]}))
    # CB-loses passes by REFUSING an inflated claim; the honest-passenger presence
    # is the kagi #2 corpus requirement, surfaced here.
    cells.append(_cell("CB-loses", "pass" if refused else "not_engaged", {
        "refused_inflated_claims": [v["intervention_id"] for v in refused],
        "honest_passenger_present": [v["intervention_id"] for v in passengers]}))
    cells.append(_cell("CB-U1", "pass" if world else "fail", {
        "world_checked": [v["intervention_id"] for v in world]}))
    cells.append(_cell("CB-read", "not_engaged", {
        "note": "read-changes-a-decision needs a resident across sessions — M2 entry condition"}))
    return cells


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ledger")
    args = ap.parse_args()

    ledger = Ledger(Path(args.ledger))
    rows = ledger.rows()
    interventions = [r for r in rows if r.get("kind") == "intervention"]
    already = {r["intervention_id"] for r in rows if r.get("kind") == "contribution_verdict"}

    verdicts = []
    for iv in interventions:
        if iv["intervention_id"] in already:  # append-only; L-A immutability
            continue
        v = score_intervention(iv)
        ledger.write(v)
        verdicts.append(v)
        print(json.dumps(v, indent=2, sort_keys=True))

    if not verdicts:
        print("no unscored interventions found", file=sys.stderr)
        return 1

    # Cell verdicts read every contribution_verdict in the ledger (incl. prior).
    all_verdicts = [r for r in ledger.rows() if r.get("kind") == "contribution_verdict"]
    for c in score_cells(all_verdicts):
        ledger.write(c)
        print(json.dumps(c, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
