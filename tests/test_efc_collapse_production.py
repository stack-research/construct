"""P2 production §10.2 collapse contract — offline tests only."""

from __future__ import annotations

import copy
import json
import shutil
import socket
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from harness.efc_collapse_production import (COLLAPSE_PIN_REL, DETECTOR_ID,
                                             MODULE_REL,
                                             RouteProjectionError,
                                             _group, branch_collapsed,
                                             build_production_collapse_detector,
                                             collapse_pin_payload,
                                             conformance_vectors,
                                             production_collapse_contract_hash,
                                             project_route,
                                             realization_sha256,
                                             run_conformance_vectors,
                                             verify_collapse_pin,
                                             write_collapse_pin)
from harness.efc_runner import validate_pinned_collapse_detector

ROOT = Path(__file__).resolve().parents[1]
K = 5


class _RefusingSocket(socket.socket):
    def __init__(self, *a, **k):
        raise AssertionError("collapse test attempted a network call")


class SocketRefusalMixin:
    @classmethod
    def setUpClass(cls):
        cls._real_socket = socket.socket
        socket.socket = _RefusingSocket

    @classmethod
    def tearDownClass(cls):
        socket.socket = cls._real_socket


def _runs(spec):
    return [SimpleNamespace(lane=lane, fixture_id=fid, rows=rows)
            for lane, fid, rows in spec]


class TestRouteProjection(SocketRefusalMixin, unittest.TestCase):

    def test_checked_and_silent_shapes_project(self):
        checked = project_route(_group(checked=True, answer="a"))
        silent = project_route(_group(checked=False, answer="a"))
        self.assertEqual(checked["external_check"]["realization"],
                         "started_completed")
        self.assertEqual(checked["external_check"]["treatment_class"],
                         "named_check")
        self.assertIsNotNone(
            checked["external_check"]["evidence_identity"])
        self.assertEqual(silent["external_check"]["realization"], "silent")
        self.assertIsNone(silent["external_check"]["evidence_identity"])

    def test_placebo_treatment_class(self):
        route = project_route(_group(checked=False, answer="a",
                                     silent_reason="placebo_treatment"))
        self.assertEqual(route["external_check"]["treatment_class"],
                         "pinned_placebo_evidence")

    def test_volatile_fields_do_not_enter_the_realization(self):
        base = SimpleNamespace(lane="L", fixture_id="f1",
                               rows=_group(checked=True, answer="a",
                                           prompt_tokens=100,
                                           oracle_passed=True))
        other = SimpleNamespace(lane="L", fixture_id="f2",
                                rows=_group(checked=True, answer="a",
                                            prompt_tokens=999,
                                            oracle_passed=False))
        self.assertEqual(realization_sha256(base),
                         realization_sha256(other))

    def test_route_diversity_changes_the_realization(self):
        a = SimpleNamespace(rows=_group(checked=True, answer="a"))
        b = SimpleNamespace(rows=_group(checked=False, answer="a"))
        self.assertNotEqual(realization_sha256(a), realization_sha256(b))

    def test_malformed_route_evidence_refuses(self):
        cases = [
            _group(checked=False, answer="a", kinds=(1, 0, 2, 3, 4, 5)),
            _group(checked=False, answer="a", kinds=(0, 1, 3, 4, 5)),
            _group(checked=False, answer="a", kinds=(0, 1, 1, 2, 3, 4, 5)),
            [],
        ]
        for rows in cases:
            with self.assertRaises(RouteProjectionError):
                project_route(rows)
        bad_reason = _group(checked=False, answer="a")
        bad_reason[1]["payload"]["reason"] = "made_up_reason"
        with self.assertRaises(RouteProjectionError):
            project_route(bad_reason)
        no_answer = _group(checked=False, answer="a")
        del no_answer[2]["payload"]["answer_sha256"]
        with self.assertRaises(RouteProjectionError):
            realization_sha256(SimpleNamespace(rows=no_answer))


class TestBranchCollapse(SocketRefusalMixin, unittest.TestCase):

    def test_answer_only_false_positive_cleared_by_route_diversity(self):
        runs = _runs([("C", f"f{i}", _group(checked=(i < 3), answer="same"))
                      for i in range(K)])
        self.assertFalse(branch_collapsed(runs))

    def test_fixture_ids_differ_but_realizations_collapse(self):
        runs = _runs([("A", f"f{i}", _group(checked=True, answer="same"))
                      for i in range(K)])
        self.assertTrue(branch_collapsed(runs))

    def test_duplicate_fixture_and_bad_cardinality_refuse(self):
        dup = _runs([("A", "f0", _group(checked=True, answer="s"))
                     for _ in range(K)])
        with self.assertRaises(RouteProjectionError):
            branch_collapsed(dup)
        short = _runs([("A", f"f{i}", _group(checked=True, answer="s"))
                       for i in range(K - 1)])
        with self.assertRaises(RouteProjectionError):
            branch_collapsed(short)
        with self.assertRaises(RouteProjectionError):
            branch_collapsed([])

    def test_stratum_grouping_partitions_multi_stratum_lane(self):
        runs = []
        strata = {}
        for stratum in ("s-a", "s-b", "s-c"):
            for i in range(K):
                fid = f"{stratum}-{i}"
                strata[fid] = stratum
                runs.append(SimpleNamespace(
                    lane="A", fixture_id=fid,
                    rows=_group(checked=True, answer=f"per {stratum}")))
        # without the pinned stratum map the 15-fixture lane refuses
        with self.assertRaises(RouteProjectionError):
            branch_collapsed(runs)
        self.assertTrue(branch_collapsed(runs, stratum_of=strata.get))
        # in-group diversity clears
        runs[0] = SimpleNamespace(lane="A", fixture_id="s-a-0",
                                  rows=_group(checked=True, answer="odd"))
        self.assertFalse(branch_collapsed(runs, stratum_of=strata.get))

    def test_missing_stratum_refuses(self):
        runs = _runs([("A", f"f{i}", _group(checked=True, answer="s"))
                      for i in range(K)])
        with self.assertRaises(RouteProjectionError):
            branch_collapsed(runs, stratum_of={}.get)


class TestDetectorAndPin(SocketRefusalMixin, unittest.TestCase):

    def test_detector_validates_and_pins_identity(self):
        det = build_production_collapse_detector(ROOT)
        validate_pinned_collapse_detector(det)
        self.assertEqual(det.detector_id, DETECTOR_ID)
        self.assertEqual(det.contract["detector_id"], DETECTOR_ID)

    def test_conformance_vectors_all_hold(self):
        results = run_conformance_vectors()
        self.assertGreaterEqual(len(results), 11)
        self.assertTrue(all(r["ok"] for r in results), results)

    def test_required_vector_directions_present(self):
        names = {v["name"] for v in conformance_vectors()}
        self.assertIn(
            "answer_only_false_positive_cleared_by_route_diversity", names)
        self.assertIn("fixture_ids_differ_but_realizations_collapse", names)

    def test_pin_on_disk_recomputes(self):
        self.assertTrue(verify_collapse_pin(ROOT)["verified"])

    def test_pin_write_verify_and_tamper_refusal(self):
        box = Path(tempfile.mkdtemp(prefix="efc-p2-collapse-"))
        self.addCleanup(shutil.rmtree, box, ignore_errors=True)
        dst = box / MODULE_REL
        dst.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / MODULE_REL, dst)
        written = write_collapse_pin(box)
        self.assertEqual(written["detector_contract_sha256"],
                         production_collapse_contract_hash(box))
        self.assertTrue(verify_collapse_pin(box)["verified"])
        # idempotent rerun allowed; tampered bytes refuse
        write_collapse_pin(box)
        pin_path = box / COLLAPSE_PIN_REL
        doc = json.loads(pin_path.read_text())
        doc["detector_contract"]["calibration_k"] = 6
        pin_path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
        with self.assertRaises(RouteProjectionError):
            verify_collapse_pin(box)
        with self.assertRaises(RouteProjectionError):
            write_collapse_pin(box)

    def test_pin_detects_module_drift(self):
        box = Path(tempfile.mkdtemp(prefix="efc-p2-collapse-"))
        self.addCleanup(shutil.rmtree, box, ignore_errors=True)
        dst = box / MODULE_REL
        dst.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / MODULE_REL, dst)
        write_collapse_pin(box)
        dst.write_bytes(dst.read_bytes() + b"\n# drift\n")
        with self.assertRaises(RouteProjectionError):
            verify_collapse_pin(box)

    def test_pin_payload_conformance_gate(self):
        payload = collapse_pin_payload(ROOT)
        self.assertFalse(payload["authorizes_calibration_contact"])
        self.assertTrue(all(r["ok"] for r in payload["conformance_results"]))


if __name__ == "__main__":
    unittest.main()
