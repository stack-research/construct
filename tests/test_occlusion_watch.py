"""occlusion_watch (X4 session-seam witness) Layer-1 smoke — SPEC_X4 §11.

MACHINERY only (SPEC_X4 §0/§7): proves the emitter loads the WITNESSED precommit,
examines surfaces by LITERAL key, emits Layer-1 rows with seam_distance, and NEVER
writes a verdict. Not evidence the organ works — the earned event is Layer 2 (§10),
cross-seam, prospective, and cannot be scheduled.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from harness import occlusion_watch as ow


def _write(tdir: Path, ts: str, author: str, body: str) -> None:
    (tdir / f"{ts}__{author}.md").write_text(
        f"---\nauthor: {author}\ntimestamp: {ts}\n---\n\n{body}\n"
    )


def _armed_space() -> Path:
    threads = Path(tempfile.mkdtemp())
    tdir = threads / "t"
    tdir.mkdir()
    _write(tdir, "20260626T120000000Z", "claude", (
        "ARM-NOW PRECOMMIT — occlusion_watch v0.\n"
        "candidate_key (literal):\n"
        '"witness invariant" → §2\n'
        '"seam_distance" → §11\n'
        "population_rule: S2 committed diffs touching:\n"
        "harness/occlusion_watch*\n"
        "notes/SPEC_X4_OCCLUSION_WATCH.md\n"
    ))
    return threads


def test_load_precommit_is_witnessed():
    threads = _armed_space()
    pc = ow.load_precommit("t", threads_dir=threads)
    assert pc is not None
    assert pc.precommit_ts == "20260626T120000000Z", "precommit_ts is the entry filename ts (substrate-witnessed)"
    assert pc.candidate_keys == ("witness invariant", "seam_distance"), pc.candidate_keys
    assert "harness/occlusion_watch*" in pc.declared_paths, pc.declared_paths
    assert "notes/SPEC_X4_OCCLUSION_WATCH.md" in pc.declared_paths, pc.declared_paths
    print(f"ok  precommit loaded from witnessed entry: ts {pc.precommit_ts}, {len(pc.candidate_keys)} keys")


def test_examine_is_literal_conservative():
    keys = ("witness invariant", "seam_distance")
    assert ow.examine("the seam_distance gate fires", keys) == ["seam_distance"]
    assert ow.examine("a witness to the event", keys) == [], "'witness' alone must NOT match 'witness invariant'"
    assert ow.examine("nothing relevant here", keys) == []
    print("ok  examine is literal/conservative (compound only; bare token does not match)")


def test_anchor_and_author_excluded_seam_distance():
    threads = _armed_space()
    tdir = threads / "t"
    _write(tdir, "20260626T130000000Z", "claude", "I rely on the witness invariant here.")  # same date
    _write(tdir, "20260627T090000000Z", "claude", "the seam_distance gate handles it, no re-read.")  # later date
    _write(tdir, "20260627T100000000Z", "codex", "seam_distance witness invariant")  # non-watched author
    pc = ow.load_precommit("t", threads_dir=threads)
    refs = {Path(s.ref).name for s in ow.enumerate_s1(pc, threads_dir=threads)}
    assert "20260626T120000000Z__claude.md" not in refs, "the precommit anchor is never a watched surface"
    assert "20260627T100000000Z__codex.md" not in refs, "non-watched authors are not S1"
    assert len(refs) == 2, refs
    assert ow.seam_distance("20260626T130000000Z", pc.precommit_ts) == "same_session"
    assert ow.seam_distance("20260627T090000000Z", pc.precommit_ts) == "later_session"
    print("ok  precommit anchor + non-watched authors excluded; seam_distance same vs later session")


def test_observe_layer1_only_never_a_verdict():
    threads = _armed_space()
    _write(threads / "t", "20260627T090000000Z", "claude", "the seam_distance gate handles it.")
    pc = ow.load_precommit("t", threads_dir=threads)
    rows = ow.observe(pc, threads_dir=threads)
    kinds = {r["row"] for r in rows}
    assert {"route_watch_surface_expected", "route_watch_surface_examined",
            "occlusion_watch_observed", "scope_gap"} <= kinds, kinds
    observed = [r for r in rows if r["row"] == "occlusion_watch_observed"]
    assert observed and observed[0]["candidate_key"] == "seam_distance"
    assert observed[0]["seam_distance"] == "later_session"
    assert observed[0]["match"] == "literal"
    assert observed[0]["evidence_status"] == "observed_only_no_outcome"
    assert all("verdict" not in r for r in rows), "Layer 1 emits NO outcome verdict (earned is Layer 2, §10)"
    gaps = [r for r in rows if r["row"] == "scope_gap"]
    assert gaps and all(g["population_rule_ref"] == "S2" for g in gaps), "S2 stays in the denominator as scope_gap"
    print(f"ok  observe emits Layer-1 facts only, no verdict ({len(rows)} rows; {len(observed)} observed, {len(gaps)} scope_gap)")


def test_instrument_never_gates():
    assert ow.run(thread="t", threads_dir=Path(tempfile.mkdtemp())) == (None, []), "nothing armed -> no-op"
    assert ow.main(["--thread", "nonexistent-xyz-thread"]) == 0, "CLI no-op still exits 0 (no judicial robes)"
    print("ok  instrument exits 0 (armed or not); no judicial robes")


def main() -> None:
    test_load_precommit_is_witnessed()
    test_examine_is_literal_conservative()
    test_anchor_and_author_excluded_seam_distance()
    test_observe_layer1_only_never_a_verdict()
    test_instrument_never_gates()
    print("\nALL OCCLUSION_WATCH TESTS PASS")


if __name__ == "__main__":
    main()
