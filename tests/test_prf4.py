"""Wire tests for PRF v0.4 Greenreach mechanism (SPEC Part IV §37–§45).

Mock/scripted only — never promotes a cell. The §45 test inventory:
seeded forced-stop-pass regression (F1), wire-sweep golden cases (§41),
D5-floor margin case, step-geometry case, D13 row emission on both stop
reasons, R-handle and action-space regressions.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from itertools import combinations
from pathlib import Path

from harness.check_prf_fixture import check_manifest
from harness.ledger import Ledger
from harness.oracle import conjunctive_oracle
from harness.run_sbr import (parse_action, run_and_score, run_mint_spine,
                             run_sbr_session)
from harness.score_prf import PRFScorer
from harness.sbr_util import action_space_hash, build_sbr_system

from tests.fixtures.prf4_wire.build import (DECOY_IDS, DISPOSITIONS, LEG_IDS,
                                            write_fixture)


def _wire_fixture(**kw) -> Path:
    dst = Path(tempfile.mkdtemp()) / "prf4-wire"
    write_fixture(dst, **kw)
    return dst


def _rows(ledger_path: Path, kind: str) -> list[dict]:
    return [json.loads(line) for line in ledger_path.read_text().splitlines()
            if json.loads(line).get("kind") == kind]


def _load(fixture: Path, name: str) -> dict:
    return json.loads((fixture / name).read_text())


def _mint(fixture: Path, episode: dict, ledger: Ledger) -> dict:
    population = _load(fixture, "population.json")
    freeze = _load(fixture, "freeze_manifest.json")
    return run_mint_spine(episode, population, freeze, ledger)


def _visible_handles(episode: dict) -> dict[str, str]:
    from harness.sbr_util import sorted_surface_ids
    visible = sorted_surface_ids(episode["catalog"], episode["catalog_sort"])
    return {sid: f"R{visible.index(sid) + 1:02d}" for sid in visible}


class TestActionSpaceAndParser(unittest.TestCase):
    def test_v04_bumps_hash_from_v03(self):
        self.assertNotEqual(action_space_hash("0.4"), action_space_hash("0.3"))
        self.assertNotEqual(action_space_hash("0.4"), action_space_hash("0.2"))

    def test_v04_uses_r_handles(self):
        visible = [f"S{i}" for i in range(21)]
        parsed, refuse = parse_action("R03", visible, "0.4")
        self.assertIsNone(refuse)
        self.assertEqual(parsed, {"action": "READ", "surface_id": "S2"})
        parsed, refuse = parse_action('{"action":"STOP"}', visible, "0.4")
        self.assertIsNotNone(refuse)

    def test_v04_menu_presentation(self):
        fixture = _wire_fixture()
        ep = _load(fixture, "ep-baseline.json")
        system = build_sbr_system(ep["catalog"], ep["catalog_sort"],
                                  ep["question"], "0.4")
        self.assertIn("R01:", system)
        self.assertIn("R21:", system)
        shutil.rmtree(fixture.parent)


class TestConjunctiveWireSweep(unittest.TestCase):
    """§41 golden cases: every < 3-leg subset fails on every legal token."""

    def test_28_case_sweep_all_fail(self):
        for k in range(0, 3):
            for subset in combinations(LEG_IDS, k):
                for token in DISPOSITIONS:
                    s = conjunctive_oracle(token, "release", list(subset),
                                           LEG_IDS)
                    self.assertEqual(
                        s.score, 0.0,
                        f"leak: {list(subset)} + {token!r} scored {s.score}")

    def test_decoys_never_substitute_for_legs(self):
        reads = DECOY_IDS + LEG_IDS[:2]
        s = conjunctive_oracle("release", "release", reads, LEG_IDS)
        self.assertEqual(s.score, 0.0)

    def test_positive_control_triple_release_passes(self):
        s = conjunctive_oracle("release", "release", LEG_IDS, LEG_IDS)
        self.assertEqual(s.score, 1.0)

    def test_wrong_token_with_triple_fails(self):
        s = conjunctive_oracle("hold", "release", LEG_IDS, LEG_IDS)
        self.assertEqual(s.score, 0.0)

    def test_gate_carries_the_sweep(self):
        fixture = _wire_fixture()
        checks = check_manifest(fixture / "manifest.json")
        sweep = [c for c in checks if c[0].startswith("conjunctive_evidence_ok")]
        self.assertTrue(sweep)
        self.assertTrue(all(ok for _, ok, _ in sweep))
        shutil.rmtree(fixture.parent)


class TestV04FixtureGate(unittest.TestCase):
    def test_wire_fixture_gate_open(self):
        fixture = _wire_fixture()
        checks = check_manifest(fixture / "manifest.json")
        failed = [(n, d) for n, ok, d in checks if not ok]
        self.assertFalse(failed, f"gate refused: {failed}")
        shutil.rmtree(fixture.parent)

    def test_d5_floor_margin_34_token_decoys_refused(self):
        """§45 D5-floor case: decoys at 34 sit below the pinned floor — the
        authoring corner (6×34 − 65 = 139 < 145) is excluded by construction."""
        fixture = _wire_fixture(decoy_tokens=34)
        checks = check_manifest(fixture / "manifest.json")
        pins = [c for c in checks if c[0].startswith("token_pins_d5")]
        self.assertTrue(pins)
        self.assertTrue(all(not ok for _, ok, _ in pins),
                        f"34-token decoys must fail the D5 pin: {pins}")
        shutil.rmtree(fixture.parent)

    def test_pay_window_margin_holds_at_floor(self):
        fixture = _wire_fixture(decoy_tokens=35)
        checks = check_manifest(fixture / "manifest.json")
        pw = [c for c in checks if c[0].startswith("pay_window_geometry")]
        self.assertTrue(pw)
        self.assertTrue(all(ok for _, ok, _ in pw), pw)
        shutil.rmtree(fixture.parent)

    def test_budget_pins_enforced(self):
        fixture = _wire_fixture()
        ep_path = fixture / "ep-baseline.json"
        ep = json.loads(ep_path.read_text())
        ep["budgets"] = {"max_read_tokens": 700, "max_steps": 8,
                         "action_overhead_tokens": 20, "c_max": 860}
        ep_path.write_text(json.dumps(ep))
        checks = check_manifest(fixture / "manifest.json")
        pins = [c for c in checks
                if c[0] == "budget_pins[prf4-wire-baseline]"]
        self.assertTrue(pins and not pins[0][1],
                        "docket budgets on a 0.4 episode must refuse")
        shutil.rmtree(fixture.parent)

    def test_exclusion_certificate_required(self):
        fixture = _wire_fixture()
        ep_path = fixture / "ep-baseline.json"
        ep = json.loads(ep_path.read_text())
        del ep["catalog"]["N30"]["fields"]["applicability"]
        ep_path.write_text(json.dumps(ep))
        checks = check_manifest(fixture / "manifest.json")
        certs = [c for c in checks
                 if c[0] == "exclusion_certificates[prf4-wire-baseline]"]
        self.assertTrue(certs and not certs[0][1])
        shutil.rmtree(fixture.parent)


class TestForcedStopEnforcement(unittest.TestCase):
    """F1 (§40): forced stop prices at c_max even when the elicited answer
    passes the oracle — enforced at the runner outcome AND recomputed at
    scoring from the ledger's own forced_stop rows."""

    def _forced_stop_session(self, budgets=None):
        fixture = _wire_fixture()
        ep = _load(fixture, "ep-baseline.json")
        if budgets:
            ep["budgets"] = budgets
        ledger_path = fixture / "test.jsonl"
        ledger = Ledger(ledger_path)
        mint = _mint(fixture, ep, ledger)
        self.assertIsNone(mint.get("halted"), mint)
        handles = _visible_handles(ep)
        # 10 READs, no STOP: 3 legs first (a passing answer), then 7 decoys/
        # ballast — max_steps forces the stop with the triple already read.
        route = LEG_IDS + DECOY_IDS + ["B01"]
        actions = [handles[s] for s in route]
        from harness.engine import MockEngine
        session = MockEngine(scripted_actions=actions).start_session()
        summary = run_sbr_session(
            ep, "cold_reread", "forced-1", 0, session, ledger,
            canonical_state=mint["canonical_state"])
        return fixture, ep, ledger_path, summary

    def test_seeded_forced_stop_pass_regression(self):
        fixture, ep, ledger_path, summary = self._forced_stop_session()
        self.assertEqual(summary["stop_reason"], "max_steps")
        self.assertFalse(summary["quality_ok"],
                         "forced stop must never carry quality_ok=true (§29)")
        outcome = _rows(ledger_path, "session_outcome")[0]
        self.assertFalse(outcome["quality_ok"])
        self.assertEqual(outcome["stop_reason"], "max_steps")
        d13 = _rows(ledger_path, "boundary_forced_stop")
        self.assertEqual(len(d13), 1)
        self.assertEqual(d13[0]["stop_reason"], "max_steps")
        self.assertTrue(d13[0]["would_have_passed"],
                        "the seeded session reads the full triple — the "
                        "elicited answer would have passed (D13 signal)")
        shutil.rmtree(fixture.parent)

    def test_d13_row_on_budget_exhausted(self):
        budgets = {"max_read_tokens": 120, "max_steps": 10,
                   "action_overhead_tokens": 20, "c_max": 320}
        fixture, ep, ledger_path, summary = self._forced_stop_session(budgets)
        self.assertEqual(summary["stop_reason"], "budget_exhausted")
        self.assertFalse(summary["quality_ok"])
        d13 = _rows(ledger_path, "boundary_forced_stop")
        self.assertEqual(len(d13), 1)
        self.assertEqual(d13[0]["stop_reason"], "budget_exhausted")
        self.assertFalse(d13[0]["would_have_passed"])
        shutil.rmtree(fixture.parent)

    def test_scorer_reprices_even_if_runner_lied(self):
        """The scorer-side enforcement is independent: a doctored ledger
        whose outcome row still says quality_ok=true prices at c_max."""
        fixture, ep, ledger_path, summary = self._forced_stop_session()
        events = [json.loads(line)
                  for line in ledger_path.read_text().splitlines()]
        for row in events:
            if row.get("kind") == "session_outcome":
                row["quality_ok"] = True  # the F1 divergence, seeded
        scorer = PRFScorer(events=events, episode=ep)
        scorer.wire_test = True
        cost = scorer._effective_cost("cold_reread", "forced-1", 0, 900)
        self.assertEqual(cost, 900,
                         "forced_stop + quality_ok=true must price c_max")
        self.assertTrue(any("§29 enforced" in e for e in scorer.evidence))
        shutil.rmtree(fixture.parent)

    def test_v03_ledgers_not_repriced(self):
        """§46: enforcement is family-keyed at 0.4 — a 0.3 ledger with the
        same divergence keeps its historical pricing (sealed families
        re-score byte-identical)."""
        events = [
            {"kind": "run_config", "instrument_version": "0.3"},
            {"kind": "forced_stop", "branch": "cold_reread",
             "session_id": "s1", "sample_index": 0,
             "stop_reason": "max_steps"},
            {"kind": "session_outcome", "branch": "cold_reread",
             "session_id": "s1", "sample_index": 0, "quality_ok": True,
             "read_ids": []},
        ]
        episode = {"instrument_version": "0.3", "catalog": {},
                   "budgets": {"max_read_tokens": 700, "max_steps": 8,
                               "action_overhead_tokens": 20}}
        scorer = PRFScorer(events=events, episode=episode)
        self.assertTrue(scorer._session_quality_ok("cold_reread", "s1", 0))


class TestStepGeometry(unittest.TestCase):
    """§40: the distracted-pass route is 9 READs + STOP = 10 slots; at
    max_steps=10 it terminates naturally, at 9 it forces the stop."""

    def _run_route(self, max_steps: int):
        fixture = _wire_fixture()
        ep = _load(fixture, "ep-baseline.json")
        ep["budgets"] = dict(ep["budgets"], max_steps=max_steps,
                             c_max=700 + max_steps * 20)
        ledger_path = fixture / "test.jsonl"
        ledger = Ledger(ledger_path)
        mint = _mint(fixture, ep, ledger)
        handles = _visible_handles(ep)
        route = DECOY_IDS + LEG_IDS  # the distracted-pass route: 9 READs
        actions = [handles[s] for s in route] + ["STOP"]
        from harness.engine import MockEngine
        session = MockEngine(scripted_actions=actions).start_session()
        summary = run_sbr_session(
            ep, "cold_reread", "geom-1", 0, session, ledger,
            canonical_state=mint["canonical_state"])
        shutil.rmtree(fixture.parent)
        return summary

    def test_nine_read_route_natural_stop_at_ten(self):
        summary = self._run_route(10)
        self.assertIsNone(summary["stop_reason"])
        self.assertEqual(len(summary["read_ids"]), 9)
        self.assertTrue(summary["quality_ok"],
                        "distracted-pass: triple read, release adequate")

    def test_nine_read_route_forced_at_nine(self):
        summary = self._run_route(9)
        self.assertEqual(summary["stop_reason"], "max_steps")
        self.assertFalse(summary["quality_ok"])


class TestV04EndToEnd(unittest.TestCase):
    def test_run_and_score_wire_baseline(self):
        fixture = _wire_fixture()
        out = run_and_score(fixture / "ep-baseline.json",
                            ledger_path=fixture / "e2e.jsonl",
                            scripted_sessions={
                                "cold_reread": [
                                    [f"R{i:02d}" for i in (13, 14, 15, 16, 17,
                                                           18, 19, 20, 21)]
                                    + ["STOP"]],
                                "resumable_state": [
                                    ["R18", "R21", "R15", "STOP"]],
                            })
        verdict = out["verdict"]
        self.assertIsNotNone(verdict)
        self.assertEqual(verdict["instrument_version"], "0.4")
        self.assertTrue(verdict["wire_test"])
        self.assertNotEqual(verdict["cell"], "confounded", verdict)
        shutil.rmtree(fixture.parent)

    def test_calibration_gate_scripted(self):
        fixture = _wire_fixture()
        ep = _load(fixture, "ep-baseline.json")
        ledger_path = fixture / "cal.jsonl"
        ledger = Ledger(ledger_path)
        mint = _mint(fixture, ep, ledger)
        from harness.run_sbr import run_calibration_gate
        row = run_calibration_gate(ep, mint["canonical_state"], ledger)
        self.assertTrue(row["passed"], row)
        shutil.rmtree(fixture.parent)


if __name__ == "__main__":
    unittest.main()
