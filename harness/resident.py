"""SPEC_M2 — resident substrate: the cross-session earned-memory mint (Wall B).

The resident does not hold the pen on its own past. The earned-failure record is
minted by the HARNESS from the *scored trace* of session N — content derived from
the oracle's correction (the world, via the corpus), never from the resident's
answer text. Fail-closed: no resolved scored failure -> no earned record -> the
chain has nothing to inherit and RS-1 cannot even start (codex's mint contract).

This module is the write-path half of the air gap. The read-path half (the fork
decides use, not the testimony) lives in the session-chain runner + score_resident.
"""

from __future__ import annotations

from .corpus import CorpusEntry, expected_decision, load_entry
from .records import Record


def corrected_claim(entry: CorpusEntry) -> str:
    """The lesson, derived from the corpus entry (the world), not the resident.

    Direction comes from the disclosed decision rule (SPEC_M0): a retraction (or a
    correction whose claim no longer stands) earns a 'decline' lesson; a correction
    whose core finding stands earns a 'still citable' lesson. Either way the text is
    the world's notice, never the resident's narration of what it learned.
    """
    if expected_decision(entry) == "decline":
        reason = entry.stated_reason.rstrip(". ")
        return (
            f"{entry.claim_summary} — {entry.category.upper()} "
            f"({entry.corpus_id}, {entry.event_date}): {reason}. "
            f"Decline to cite it as a current finding."
        )
    return (
        f"{entry.claim_summary} — corrected ({entry.corpus_id}, {entry.event_date}) "
        f"but the core finding stands per the publisher's notice; it remains citable."
    )


def trace_chain_refusal(e1_rows: list[dict], source_run_id: str) -> str | None:
    """SPEC_M3 IN-1: promotion must resolve through a harness-written chain.

    Returns a refusal reason when the trace lacks external-ledger markers; None if ok.
  """
    cfgs = [r for r in e1_rows if r.get("kind") == "run_config" and r.get("run_id") == source_run_id]
    if len(cfgs) != 1:
        return "trace_auth_missing: run_config.run_id must match source_run_id"
    sessions = [r for r in e1_rows if r.get("kind") == "session"]
    if len(sessions) != 1:
        return "trace_auth_missing: harness-written session row required"
    sess = sessions[0]
    if sess.get("memory_isolation") not in ("minimal_harness", "scrubbed"):
        return "trace_auth_missing: memory_isolation not attested"
    if not sess.get("resident_config_digest"):
        return "trace_auth_missing: resident_config_digest required"
    return None


def mint_earned_record(
    e1_rows: list[dict],
    resident_branch_id: str,
    *,
    session_id: str,
    source_run_id: str,
    created_at: str,
) -> Record | None:
    """Derive the earned-failure record from E1's scored trace (Wall B).

    Reads the resident branch's outcome from the ledger's `branch_run.oracle` —
    never `branch_output.answer` — and derives the lesson from the world corpus
    that *that scored row* names, loaded and sha-pinned HERE (not handed in by
    the caller). The lesson can only come from the corpus that actually scored
    the failure. Returns None (fail-closed) when there is no resolved scored
    failure to learn from: ambiguous/missing trace, an unledgered outcome, a
    session the resident did not fail, no world corpus in the trace (e.g. an
    authored oracle), or a corpus that changed since it scored the failure.
    """
    runs = [
        r for r in e1_rows
        if r.get("kind") == "branch_run"
        and r.get("branch_id") == resident_branch_id
        and r.get("run_id") == source_run_id
    ]
    if len(runs) != 1:
        return None  # ambiguous or missing E1 trace -> no mint
    oracle = runs[0].get("oracle")
    if not isinstance(oracle, dict) or "score" not in oracle:
        return None  # outcome not ledgered -> no mint (the branch_run audit gap, closed)
    if oracle["score"] >= 1.0:
        return None  # the resident did NOT fail -> nothing earned, no mint

    # The lesson is derived from the corpus the trace says scored the failure —
    # loaded here, never passed in, so caller-supplied content cannot enter the
    # earned record. No world corpus in the trace -> nothing trace-grounded to
    # learn -> no mint (Wall B airtight).
    corpus_ref = oracle.get("corpus_entry")
    if not corpus_ref:
        return None
    if trace_chain_refusal(e1_rows, source_run_id) is not None:
        return None  # forged trace with corpus still refused without harness chain
    entry = load_entry(corpus_ref)
    expected_sha = oracle.get("corpus_entry_sha256")
    if expected_sha and entry.sha256 != expected_sha:
        return None  # corpus changed since it scored the failure -> can't trust the lesson

    source = oracle.get("source")
    # mint_basis distinguishes the world-checked leg (RS-U1) from an authored
    # wiring failure. Read off the E1 oracle's provenance, not asserted.
    mint_basis = "world_correction" if source not in (None, "authored") else "scored_failure"

    lesson = corrected_claim(entry)
    return Record(
        record_id=f"earned-{session_id}-{entry.corpus_id}",
        text=lesson,
        created_at=created_at,
        predeclared_usage="correction",
        vocabulary_kind="reality_observation",
        trust=1.0,
        provenance={
            "minted_by": "harness",
            "source_session_id": session_id,
            "source_run_id": source_run_id,
            "mint_basis": mint_basis,
            "corrected_claim": lesson,
            "source_oracle": {
                "source": source,
                "score": oracle["score"],
                "type": oracle.get("type"),
                "corpus_entry": corpus_ref,
                "corpus_entry_sha256": entry.sha256,  # the sha we loaded + pinned
            },
        },
    )
