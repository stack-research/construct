"""route_watch (X4 declared-read seam) instrument smoke — SPEC_X4 §3.

These assert MACHINERY only: the relation computes, the witness path is external
and append-only, and the instrument never gates. Per SPEC_X4 §0/§7 they are NOT
evidence the organ works — re-finding the known cold-lineage wound is `not_engaged`
as evidence by X2-U1's own gate. The organ is earned prospectively, by
catches-vs-flinches under the witness invariant, never by a passing test.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from harness import route_watch
from harness.check_contract import parse_contract

ROOT = Path(__file__).resolve().parent.parent
BRIDGE = "notes/previous/review/glossary.md"

# A route that uses the two-plane vocabulary (via the required active glossary) but
# never reaches the bridge ancestor — the shape every pre-b7e04c0 bootstrap had.
COLD_ROUTE = ["AGENTS.md", "README.md", "notes/ROADMAP.md", "notes/GLOSSARY.md"]
WARM_ROUTE = COLD_ROUTE + [BRIDGE]  # the route the routing fix now makes available


def test_cold_route_surfaces_lineage_plane():
    rows = route_watch.observe(COLD_ROUTE, agent="test-cold", write=False)
    assert rows, "a route that uses two-plane vocabulary but omits the bridge ancestor must surface candidates"
    top = rows[0]
    assert top["candidate"] == "Lineage plane", top
    assert top["candidate_kind"] == "route-relation"
    assert top["breadth_collapse"] is True
    assert "cold lineage" in top["derived_in_use"], top["derived_in_use"]
    assert top["seam"] == "declared-read"
    assert top["route_basis"] == "declared_read_order"
    assert top["witness_scope"] == "observed_ts_only__route_claim_not_independently_witnessed"
    assert top["evidence_status"] == "observed_only_no_outcome"
    assert "verdict" not in top, "observed row carries no verdict (computed later vs the external witness, §4)"
    assert all(rows[i]["cold_confidence"] >= rows[i + 1]["cold_confidence"] for i in range(len(rows) - 1)), \
        "candidates must be ranked descending by cold_confidence"
    print(f"ok  cold route surfaces {len(rows)} candidate(s); top {top['candidate']!r} [{top['cold_confidence']}]")


def test_warm_route_is_quiet():
    rows = route_watch.observe(WARM_ROUTE, agent="test-warm", write=False)
    assert rows == [], f"a route that reaches the bridge ancestor must be quiet, got {[r['candidate'] for r in rows]}"
    print("ok  warm route (bridge ancestor reached) → no candidates")


def test_route_trigger_resolves_from_contract():
    # The obligation->ancestor edge the b7e04c0 fix added must be the one we read,
    # parsed live from AGENTS.md (never hard-coded), so the contract stays authoritative.
    _, conditional = parse_contract((ROOT / "AGENTS.md").read_text())
    assert BRIDGE in conditional, "bridge glossary must be a routed conditional source in AGENTS.md"
    rows = route_watch.observe(COLD_ROUTE, write=False)
    trigger = rows[0]["route_trigger"]
    assert trigger and "vocabulary" in trigger.lower(), f"route_trigger should name the inherited-vocabulary edge, got {trigger!r}"
    print(f"ok  route trigger resolves from contract: {trigger!r}")


def test_witness_path_is_external_and_appendonly():
    # The Ledger (harness) stamps observed_ts; the agent under watch never writes the
    # row. A second run appends — it never overwrites or backfills (SPEC_X4 §2).
    with tempfile.TemporaryDirectory() as td:
        sidecar = Path(td) / "rw.jsonl"
        r1 = route_watch.observe(COLD_ROUTE, agent="a1", write=True, sidecar=sidecar)
        r2 = route_watch.observe(COLD_ROUTE, agent="a2", write=True, sidecar=sidecar)
        lines = sidecar.read_text().splitlines()
        assert len(lines) == len(r1) + len(r2), "append-only: the second run adds rows, never replaces"
        rows = [json.loads(l) for l in lines]
        assert all("ts" in r for r in rows), "observed_ts (the Ledger ts) is harness-stamped, not agent-written"
    print(f"ok  witness path external + append-only ({len(lines)} rows across 2 runs)")


def test_observe_default_is_print_only():
    # Retrospective and ordinary conformance calls must not append rows by accident;
    # writing a watch row is an explicit prospective act.
    with tempfile.TemporaryDirectory() as td:
        sidecar = Path(td) / "rw.jsonl"
        rows = route_watch.observe(COLD_ROUTE, agent="a1", sidecar=sidecar)
        assert rows, "the relation still computes"
        assert not sidecar.exists(), "default observe() is print-only, not a historical sidecar write"
    print("ok  observe() default is print-only; writes require write=True / --write")


def test_instrument_never_gates():
    # No judicial robes: main() returns 0 regardless of how many candidates it finds,
    # and a no-input invocation is a no-op, not a failure.
    assert route_watch.main(["--read-order", ",".join(COLD_ROUTE), "--no-write"]) == 0
    assert route_watch.main(["--read-order", ",".join(WARM_ROUTE), "--no-write"]) == 0
    assert route_watch.main(["--no-write"]) == 0
    print("ok  instrument exit code is always 0 (never a gate)")


def main() -> None:
    test_cold_route_surfaces_lineage_plane()
    test_warm_route_is_quiet()
    test_route_trigger_resolves_from_contract()
    test_witness_path_is_external_and_appendonly()
    test_observe_default_is_print_only()
    test_instrument_never_gates()
    print("\nALL ROUTE_WATCH TESTS PASS")


if __name__ == "__main__":
    main()
