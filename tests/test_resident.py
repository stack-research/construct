"""SPEC_M2 mint + lesson tests — the subtlest M2 code, exercised without a model.

Run:
  uv run --no-project python -m tests.test_resident      (or: make m2-test)

Covers Wall B: the earned record is derived only from the scored trace + the
corpus that trace names (sha-pinned), never from the resident's answer; and
fail-closed on every path that does not resolve to a real world-checked failure.
"""

from __future__ import annotations

from dataclasses import replace

from harness.corpus import load_entry
from harness.resident import corrected_claim, mint_earned_record

RETRACTION = "corpus/retractions/rw-0001.json"


def _world_oracle(entry, score=0.0, sha=None):
    return {
        "score": score, "source": "retraction_corpus", "type": "world_checked",
        "corpus_entry": entry.path, "corpus_entry_sha256": sha or entry.sha256,
    }


def _branch_run(oracle, branch="RS-resident", run_id="R1", answer="cite — should never leak"):
    return {
        "kind": "branch_run", "branch_id": branch, "run_id": run_id,
        "branch_output": {"answer": answer}, "oracle": oracle,
    }


def _harness_chain(run_id="R1", session_id="S1"):
    return [
        {"kind": "run_config", "run_id": run_id, "episode_id": "rs-e1"},
        {"kind": "session", "session_id": session_id, "memory_isolation": "minimal_harness",
         "resident_config_digest": "d"},
    ]


def _mint(rows, branch="RS-resident", run_id="R1", *, with_chain: bool = True):
    full = rows + (_harness_chain(run_id) if with_chain else [])
    return mint_earned_record(full, branch, session_id="S1", source_run_id=run_id, created_at="t")


def test_corrected_claim_retraction():
    e = load_entry(RETRACTION)
    txt = corrected_claim(e)
    assert "Decline to cite it as a current finding." in txt
    assert e.corpus_id in txt and "RETRACTION" in txt
    print("ok  corrected_claim: retraction -> decline lesson")


def test_corrected_claim_standing_correction():
    # A correction whose core finding still stands earns a 'still citable' lesson.
    e = replace(load_entry(RETRACTION), category="correction", claim_stands_after_event=True)
    txt = corrected_claim(e)
    assert "remains citable" in txt and "Decline" not in txt
    print("ok  corrected_claim: standing correction -> citable lesson")


def test_mint_world_failure_is_trace_only():
    e = load_entry(RETRACTION)
    rec = _mint([_branch_run(_world_oracle(e, 0.0), answer="cite — PLANTED_NARRATION must not leak")])
    assert rec is not None
    assert rec.provenance["mint_basis"] == "world_correction"
    assert rec.record_id == f"earned-S1-{e.corpus_id}"
    assert "PLANTED_NARRATION" not in rec.text          # Wall B: answer text never enters
    assert rec.provenance["corrected_claim"] == rec.text  # spec/scorer expect both
    assert rec.provenance["source_oracle"]["corpus_entry_sha256"] == e.sha256
    print("ok  mint: world failure -> trace-only earned record")


def test_mint_fail_closed_no_failure():
    e = load_entry(RETRACTION)
    assert _mint([_branch_run(_world_oracle(e, 1.0))]) is None   # resident did not fail
    print("ok  mint fail-closed: resident passed -> None")


def test_mint_fail_closed_unledgered():
    rows = [{"kind": "branch_run", "branch_id": "RS-resident", "run_id": "R1",
             "branch_output": {"answer": "cite"}}]            # no `oracle` key
    assert _mint(rows) is None
    print("ok  mint fail-closed: outcome not ledgered -> None")


def test_mint_fail_closed_ambiguous_or_missing_branch():
    e = load_entry(RETRACTION)
    one = _branch_run(_world_oracle(e, 0.0))
    assert _mint([one], branch="OTHER") is None               # missing branch
    assert _mint([one, one]) is None                          # two matching rows -> ambiguous
    print("ok  mint fail-closed: missing/ambiguous branch -> None")


def test_mint_fail_closed_corpus_changed():
    e = load_entry(RETRACTION)
    bad_sha = _branch_run(_world_oracle(e, 0.0, sha="deadbeef"))
    assert _mint([bad_sha]) is None                           # corpus changed since scoring
    print("ok  mint fail-closed: sha mismatch -> None")


def test_mint_fail_closed_trace_auth():
    e = load_entry(RETRACTION)
    assert _mint([_branch_run(_world_oracle(e, 0.0))], with_chain=False) is None
    print("ok  mint fail-closed: corpus trace without harness chain -> None")


def test_mint_fail_closed_authored_oracle():
    # An authored oracle carries no world corpus -> nothing trace-grounded to learn.
    authored = {"score": 0.0, "source": "authored", "type": "authored"}
    assert _mint([_branch_run(authored)]) is None
    print("ok  mint fail-closed: authored oracle (no corpus) -> None")


if __name__ == "__main__":
    tests = sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f))
    for _, fn in tests:
        fn()
    print(f"\nALL {len(tests)} RESIDENT TESTS PASS")
