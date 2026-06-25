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


def test_surface_basis_labels_survey_vs_work():
    # The structured write-discipline label (cursor P2): a default run is a standing-
    # glossary SURVEY; --work reads a live work_product. Only work_product rows are ever
    # outcome-eligible (SPEC_X4 §4/§5: survey rows can never be earned|early), so this
    # label must not regress silently.
    survey = route_watch.observe(COLD_ROUTE, agent="survey", write=False)
    assert survey and all(r["surface_basis"] == "standing_glossary" for r in survey), \
        "default in-use surface is the standing glossary (a survey/mirror)"
    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / "turn.md"
        work.write_text("We inherit cold lineage here without routing the bridge ancestor.\n")
        rows = route_watch.observe(COLD_ROUTE, agent="live", work_path=work, write=False)
        assert rows and all(r["surface_basis"] == "work_product" for r in rows), \
            "--work rows are work_product (the only rows that may ever earn)"
    print("ok  surface_basis labels survey (standing_glossary) vs live (work_product)")


def test_instrument_never_gates():
    # No judicial robes: main() returns 0 regardless of how many candidates it finds,
    # and a no-input invocation is a no-op, not a failure.
    assert route_watch.main(["--read-order", ",".join(COLD_ROUTE), "--no-write"]) == 0
    assert route_watch.main(["--read-order", ",".join(WARM_ROUTE), "--no-write"]) == 0
    assert route_watch.main(["--no-write"]) == 0
    print("ok  instrument exit code is always 0 (never a gate)")


def test_audit_route_witnesses_absence():
    # (a) materialize -> route_watch: when the route comes from a MATERIALIZE_AUDIT.json
    # (what a cold workspace provably contained), an ABSENT bridge ancestor is witnessed
    # by CONSTRUCTION, not a self-reported claim. The disclosure must say exactly that —
    # and must NOT over-claim that reading was witnessed (SPEC_X4 §2, §10 gate 4).
    with tempfile.TemporaryDirectory() as td:
        audit = Path(td) / "MATERIALIZE_AUDIT.json"
        audit.write_text(json.dumps({
            "brief": "REDTEAM_BRIEF.md",
            "file_count": 2,
            # the bridge ancestor (notes/previous/review/glossary.md) is ABSENT by construction
            "files": [
                {"path": "AGENTS.md", "sha256": "0" * 64},
                {"path": "notes/GLOSSARY.md", "sha256": "1" * 64},
            ],
        }))
        rows = route_watch.observe(audit_path=audit, agent="cold-bootstrap", write=False)
        assert rows, "an audit that omits the bridge ancestor must surface witnessed-cold candidates"
        top = rows[0]
        assert top["candidate"] == "Lineage plane", top
        assert top["route_basis"] == "materialize_audit", top["route_basis"]
        assert "absence_witnessed_by_materialize_audit" in top["witness_scope"]
        assert "repo_tree_only_scaffolding_excluded" in top["witness_scope"], \
            "the route must disclose repo-tree-only / scaffolding-excluded (hermes: no silent amendment)"
        assert "reads_within_workspace_self_reported" in top["witness_scope"], \
            "must NOT claim reading was witnessed — materialize witnesses availability, not reading (§10 gate 4)"
        assert "witnessed by construction" in top["why_now"], \
            "audit-route prose must say witnessed, not 'declared route' (match the prose to the witness basis)"
        assert top["evidence_status"] == "observed_only_no_outcome"
        assert "verdict" not in top, "observed row carries no verdict (computed later vs the external witness, §4)"
    print(f"ok  audit route witnesses ABSENCE by construction (route_basis=materialize_audit); top {top['candidate']!r}")


def test_audit_route_present_ancestor_is_quiet():
    # If the audit shows the bridge ancestor WAS present, it was reachable —
    # witnessed-available — so there is no cold-by-construction candidate.
    with tempfile.TemporaryDirectory() as td:
        audit = Path(td) / "MATERIALIZE_AUDIT.json"
        audit.write_text(json.dumps({
            "files": [
                {"path": "AGENTS.md", "sha256": "0" * 64},
                {"path": "notes/GLOSSARY.md", "sha256": "1" * 64},
                {"path": BRIDGE, "sha256": "2" * 64},
            ],
        }))
        rows = route_watch.observe(audit_path=audit, agent="warm-bootstrap", write=False)
        assert rows == [], f"an audit with the bridge ancestor present must be quiet, got {[r['candidate'] for r in rows]}"
    print("ok  audit route with ancestor present -> witnessed-available, no candidates")


def test_audit_available_set_parses_paths():
    # The witnessed route is exactly the audit's file paths — nothing inferred.
    with tempfile.TemporaryDirectory() as td:
        audit = Path(td) / "MATERIALIZE_AUDIT.json"
        audit.write_text(json.dumps({"files": [{"path": "a.py", "sha256": "x"}, {"path": "b.md", "sha256": "y"}]}))
        assert route_watch.audit_available_set(audit) == {"a.py", "b.md"}
    print("ok  audit_available_set parses the witnessed path set")


def test_audit_route_excludes_materialize_scaffolding():
    # hermes's catch (thread-x4c): the materialize workspace also holds the instrument's
    # OWN scaffolding — the audit record and the brief — that live in no normal repo
    # listing. The witnessed route must be the repo tree ONLY; scaffolding excluded
    # mechanically AND disclosed, so the denominator cannot be silently amended later.
    with tempfile.TemporaryDirectory() as td:
        audit = Path(td) / "MATERIALIZE_AUDIT.json"
        audit.write_text(json.dumps({
            "brief": "REDTEAM_BRIEF.md",
            "file_count": 4,
            "files": [
                {"path": "AGENTS.md", "sha256": "0" * 64},
                {"path": "notes/GLOSSARY.md", "sha256": "1" * 64},
                {"path": "REDTEAM_BRIEF.md", "sha256": "2" * 64},               # the brief — scaffolding
                {"path": "MATERIALIZE_AUDIT_PHASE_A.json", "sha256": "3" * 64},  # an audit record — scaffolding
            ],
        }))
        available = route_watch.audit_available_set(audit)
        assert available == {"AGENTS.md", "notes/GLOSSARY.md"}, available
        assert "REDTEAM_BRIEF.md" not in available, "the brief is materialize scaffolding, not repo lineage"
        assert not any("MATERIALIZE_AUDIT" in p for p in available), "audit records are scaffolding, not route"
        rows = route_watch.observe(audit_path=audit, agent="scaffolding-test", write=False)
        assert rows and all("repo_tree_only_scaffolding_excluded" in r["witness_scope"] for r in rows), \
            "the route must disclose scaffolding-excluded (hermes: no silent amendment)"
    print("ok  audit route excludes materialize scaffolding (repo tree only, disclosed)")


def test_source_profile_lab1_epistemic_distinctive_only():
    # (b) generalization (runs/x4/option3-ceiling.md): the relation transfers to a
    # second un-curated inherited source — lab-1's epistemic vocab — but DISTINCTIVE
    # terms only. Common-word concepts are below the mechanical floor and excluded by
    # design (fail-toward-under-claim; the witness writes structure, not meaning).
    prof = route_watch.LAB1_EPISTEMIC
    term_names = {t.name for t in prof.terms}
    assert term_names and not (term_names & {"belief", "claim", "memory", "evidence", "reality"}), \
        "common-word epistemic terms must be excluded (they cry-wolf; see option3-ceiling.md)"
    route = ["AGENTS.md", "README.md"]  # a route WITHOUT the lab-1 vocab source
    surface = "We weigh confidence_in_provenance_chain on old sources; the system has memory and a claim."
    rows = route_watch.observe_source(prof, route, surface)
    fired = {r["candidate"] for r in rows}
    assert "confidence_in_provenance_chain" in fired, "the distinctive term transfers (the (b) detection prize)"
    assert "memory" not in fired and "claim" not in fired, \
        "common words must NOT fire — they are not in the profile (no cry-wolf)"
    top = rows[0]
    assert top["ancestor_source"] == "notes/previous/MEMORY_!=_REALITY.md", top["ancestor_source"]
    assert "distinctive_terms_only" in top["witness_scope"]
    assert "option3-ceiling.md" in top["witness_scope"], "the ceiling must travel disclosed on the row"
    print("ok  source profile (lab1-epistemic): distinctive transfers; common words excluded; ceiling disclosed")


def main() -> None:
    test_cold_route_surfaces_lineage_plane()
    test_warm_route_is_quiet()
    test_route_trigger_resolves_from_contract()
    test_witness_path_is_external_and_appendonly()
    test_observe_default_is_print_only()
    test_surface_basis_labels_survey_vs_work()
    test_instrument_never_gates()
    test_audit_route_witnesses_absence()
    test_audit_route_present_ancestor_is_quiet()
    test_audit_available_set_parses_paths()
    test_audit_route_excludes_materialize_scaffolding()
    test_source_profile_lab1_epistemic_distinctive_only()
    print("\nALL ROUTE_WATCH TESTS PASS")


if __name__ == "__main__":
    main()
