"""Close-gate wire tests (SPEC_CLOSE_GATE v0.1). Mock fixtures — machinery only,
never evidence about a real close. Every leg fails individually; the review-pass
regressions (S1 third-sidecar, B1 token/reversed rows, B3 refusal rows, override
scope, caller-ts strip) each have a named test."""

from __future__ import annotations

import datetime
import json
import shutil
import tempfile
from pathlib import Path

from harness.check_close import CloseGate, _parse_iso

UTC = datetime.timezone.utc


def make_lab(root: Path, *, sidecars: int = 3) -> CloseGate:
    """A tiny fake lab: packet artifacts (findings + N verdict sidecars), a
    contribution ledger with one qualifying row, and a thread directory."""
    (root / "notes").mkdir(parents=True)
    (root / "notes" / "M9_FINDINGS.md").write_text("# findings\n")
    (root / "runs" / "m9").mkdir(parents=True)
    for i in range(sidecars):
        (root / "runs" / "m9" / f"cell-{i}.verdicts.jsonl").write_text(
            json.dumps({"kind": "cell_verdict", "cell": f"C{i}", "verdict": "pass"}) + "\n")
    (root / "runs" / "m1_5").mkdir(parents=True)
    contributions = root / "runs" / "m1_5" / "contributions.jsonl"
    rows = [
        {"kind": "intervention", "intervention_id": "iv-good", "contributor": "builder",
         "claimed_target_milestone": "M9", "target_artifact": "notes/M9_FINDINGS.md",
         "artifact_pointers": [], "reversal_of": None},
        {"kind": "contribution_verdict", "intervention_id": "iv-good",
         "target_artifact": "notes/M9_FINDINGS.md", "outcome": "landed",
         "disposition": "substantiated", "load_bearing": True},
    ]
    contributions.write_text("".join(json.dumps(r) + "\n" for r in rows))
    (root / "threads" / "close-m9").mkdir(parents=True)
    return CloseGate(closes=root / "runs" / "closes" / "closes.jsonl",
                     contributions=contributions,
                     threads_dir=root / "threads", repo=root)


CLASSES = {"findings": ["notes/M9_FINDINGS.md"],
           "verdict_sidecars": "runs/m9/*.verdicts.jsonl"}


def add_review(root: Path, gate: CloseGate, author: str, when: datetime.datetime,
               text: str) -> None:
    fname = when.strftime("%Y%m%dT%H%M%S%f")[:-3] + f"Z__{author.replace('/', '%2F')}.md"
    (root / "threads" / "close-m9" / fname).write_text(text)


def stamp(gate: CloseGate) -> dict:
    return gate.stamp("M9", CLASSES, builders=["builder"], thread="close-m9",
                      requested_by="dan")


def later(s: dict, hours: float) -> datetime.datetime:
    return _parse_iso(s["ts"]) + datetime.timedelta(hours=hours)


def with_lab(fn):
    root = Path(tempfile.mkdtemp())
    try:
        fn(root, make_lab(root))
    finally:
        shutil.rmtree(root)


def test_s1_regression_glob_enumerates_all_sidecars():
    def body(root, gate):
        s = stamp(gate)
        sidecars = [p for p in s["packet_manifest"] if p.endswith(".verdicts.jsonl")]
        assert len(sidecars) == 3, sidecars  # the hand-list failure cannot recur
        # empty class fails loud
        try:
            gate.expand_classes({"sidecars": "runs/nowhere/*.jsonl"})
            raise AssertionError("empty class must refuse")
        except ValueError:
            pass
    with_lab(body)
    print("ok  S1 regression: harness glob enumerates all sidecars; empty class refuses")


def test_all_legs_green_rules():
    def body(root, gate):
        s = stamp(gate)
        ref = s["packet_sha256"][:8]
        add_review(root, gate, "codex/gpt-5.5", later(s, 1), f"reviewed packet {ref}: endorse")
        add_review(root, gate, "cursor/glm-5.2", later(s, 2), f"packet {ref} verified")
        row = gate.rule("M9", "dan", min_interval_s=3600, now=later(s, 13))
        assert row["kind"] == "close_ruled" and row["override"] is None, row
        assert row["evidence"]["rest"]["opportunity_window_met"] is True
    with_lab(body)
    print("ok  all four legs green -> close_ruled")


def test_b1_regression_reversed_and_passenger_rows_refused():
    def body(root, gate):
        c = gate.contributions
        rows = [json.loads(l) for l in c.read_text().splitlines()]
        for r in rows:
            if r["kind"] == "contribution_verdict":
                r["outcome"] = "reversed"  # substantiated-but-reversed token row
        c.write_text("".join(json.dumps(r) + "\n" for r in rows))
        s = stamp(gate)
        ref = s["packet_sha256"][:8]
        add_review(root, gate, "a/x", later(s, 1), f"{ref} ok")
        add_review(root, gate, "b/y", later(s, 1), f"{ref} ok")
        row = gate.rule("M9", "dan", min_interval_s=0, now=later(s, 2))
        assert row["kind"] == "close_refused" and "contribution" in row["failed_legs"], row
    with_lab(body)
    print("ok  B1 regression: reversed-outcome row does not satisfy leg 1")


def test_packet_leg_catches_post_stamp_mutation():
    def body(root, gate):
        s = stamp(gate)
        (root / "runs" / "m9" / "cell-1.verdicts.jsonl").write_text("tampered\n")
        ref = s["packet_sha256"][:8]
        add_review(root, gate, "a/x", later(s, 1), f"{ref}")
        add_review(root, gate, "b/y", later(s, 1), f"{ref}")
        row = gate.rule("M9", "dan", min_interval_s=0, now=later(s, 2))
        assert "packet" in row["failed_legs"], row
    with_lab(body)
    print("ok  packet leg: post-stamp mutation refused (re-stamp required)")


def test_coverage_binding_and_builder_exclusion():
    def body(root, gate):
        s = stamp(gate)
        ref = s["packet_sha256"][:8]
        add_review(root, gate, "a/x", later(s, 1), "great work, endorse")   # no hash ref
        add_review(root, gate, "builder", later(s, 1), f"{ref} self-review")  # builder
        add_review(root, gate, "b/y", later(s, 1), f"{ref} verified")        # counts
        row = gate.rule("M9", "dan", min_interval_s=0, now=later(s, 2))
        assert "coverage" in row["failed_legs"], row
        assert row["evidence"]["coverage"]["reviewers"] == ["b/y"], row["evidence"]
    with_lab(body)
    print("ok  coverage: unbound traffic and builder self-review never count")


def test_rest_leg_and_override_scope():
    def body(root, gate):
        s = stamp(gate)
        ref = s["packet_sha256"][:8]
        add_review(root, gate, "a/x", later(s, 0.1), f"{ref}")
        add_review(root, gate, "b/y", later(s, 0.1), f"{ref}")
        # rest fails at 1h into a 12h window
        row = gate.rule("M9", "dan", now=later(s, 1))
        assert row["kind"] == "close_refused" and row["failed_legs"] == ["rest"], row
        # override bypasses rest, ledgered
        row = gate.rule("M9", "dan", override="urgent retraction", now=later(s, 1))
        assert row["kind"] == "close_ruled", row
        assert row["override"]["bypassed_legs"] == ["rest"], row
        # override can NEVER bypass leg 1: empty the contribution ledger
        gate.contributions.write_text("")
        row = gate.rule("M9", "dan", override="try to skip everything", now=later(s, 1))
        assert row["kind"] == "close_refused" and "contribution" in row["failed_legs"], row
    with_lab(body)
    print("ok  rest leg refuses early ruling; override bypasses 3-4 only, never leg 1")


def test_b3_self_instrumentation_and_status():
    def body(root, gate):
        row = gate.rule("M9", "dan", now=datetime.datetime(2026, 7, 2, tzinfo=UTC))
        assert row["kind"] == "close_refused"  # no stamp at all
        kinds = [r["kind"] for r in gate.ledger.rows()]
        assert "close_requested" in kinds and "close_refused" in kinds, kinds
        st = gate.status()
        assert st["attempts"] == 1 and st["refused"] == 1, st
        assert st["line_crossed"] is False
    with_lab(body)
    print("ok  B3: refused attempts enter the ledger; status sees non-use")


def test_caller_ts_is_stripped():
    def body(root, gate):
        row = gate._write({"kind": "close_requested", "milestone": "M9",
                           "ts": "1999-01-01T00:00:00Z"})
        assert row["ts"] != "1999-01-01T00:00:00Z", row  # harness stamped, caller ignored
    with_lab(body)
    print("ok  caller-supplied ts stripped; harness stamps (X1 tick law)")


if __name__ == "__main__":
    test_s1_regression_glob_enumerates_all_sidecars()
    test_all_legs_green_rules()
    test_b1_regression_reversed_and_passenger_rows_refused()
    test_packet_leg_catches_post_stamp_mutation()
    test_coverage_binding_and_builder_exclusion()
    test_rest_leg_and_override_scope()
    test_b3_self_instrumentation_and_status()
    test_caller_ts_is_stripped()
    print("\nALL 8 CLOSE-GATE TESTS PASS")
    print("DISCLOSED: mock fixtures — machinery wire, never evidence about a real close.")
