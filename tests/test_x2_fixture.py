"""X2 out-of-weights fixture + fictional oracle smoke tests."""

from __future__ import annotations

from pathlib import Path

from harness.check_x2_fixture import check_manifest
from harness.fictional_corpus import load_fictional_entry
from harness.oracle import fictional_fact_oracle
from harness.runner import Episode

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "episodes" / "x2" / "real" / "manifest.json"


def test_fixture_gate_opens():
    failed = [c for c in check_manifest(MANIFEST) if not c[1]]
    assert not failed, failed
    print("ok  x2 fixture gate: all checks pass")


def test_fictional_oracle_not_authored():
    entry = load_fictional_entry("corpus/fictional/lf-helix-site.json")
    o = fictional_fact_oracle(
        "kx7-morrow-pin-8812", entry, "workshop_wifi_password",
        representativeness="test",
    )
    assert o.score == 1.0
    assert o.source == "lab_fictional_corpus"
    assert o.type == "world_checked"
    print("ok  fictional_fact oracle: lab_fictional_corpus, score 1.0 on hit")


def test_episode_oracle_dispatch():
    ep = Episode.load(ROOT / "episodes" / "x2" / "real" / "core.json")
    o = ep.score("the password is kx7-morrow-pin-8812")
    assert o.source == "lab_fictional_corpus"
    assert o.score == 1.0
    print("ok  real core episode dispatches fictional_fact oracle")


def main() -> None:
    test_fixture_gate_opens()
    test_fictional_oracle_not_authored()
    test_episode_oracle_dispatch()
    print("\nALL X2 FIXTURE TESTS PASS")


if __name__ == "__main__":
    main()
