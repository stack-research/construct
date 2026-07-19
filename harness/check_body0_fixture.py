"""Body-0 fixture and admission gate.

Static checks prove the packet can exercise the reviewed composition geometry.
For non-mock contact, a separate ignorance-probe result must additionally show
that the named engine still takes the stale decision cold.  A probe is admission
only; it never counts as Body-0 evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

from .body0 import (
    ADAPTER_ID,
    Body0ContractError,
    adapt_earned_record,
    cost_state_preflight,
    packet_sha256,
)
from .corpus import load_entry
from .records import Record
from .resident import corrected_claim
from .runner import BranchConfig, Episode, select_offers
from .world_fact_corpus import load_world_fact_entry

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "episodes" / "body0" / "wire" / "manifest.json"

Check = tuple[str, bool, str]
BACKEND_RECEIPT_NAMES = {
    "mock": "mock",
    "local": "local_openai_compat",
    "claude": "claude",
}


def manifest_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def backend_receipt_name(engine_backend: str) -> str:
    try:
        return BACKEND_RECEIPT_NAMES[engine_backend]
    except KeyError as exc:
        raise ValueError(f"unknown engine backend {engine_backend!r}") from exc


def _record_universe(ep: Episode) -> list[dict]:
    return [
        {
            "record_id": r.record_id,
            "text": r.text,
            "created_at": r.created_at,
            "predeclared_usage": r.predeclared_usage,
            "vocabulary_kind": r.vocabulary_kind,
            "trust": r.trust,
            "supersedes": list(r.supersedes),
            "provenance": r.provenance,
        }
        for r in ep.records
    ]


def _probe_checks(manifest_path: Path, manifest: dict, probe_result: dict | None,
                  engine_backend: str, model: str) -> list[Check]:
    if engine_backend == "mock":
        return [("real_probe", True, "mock wire: real-engine ignorance probe not consumed")]
    if not probe_result:
        return [("real_probe", False, "non-mock contact requires a separate probe-result packet")]
    expected = manifest["ignorance_probe"]
    receipt_backend = backend_receipt_name(engine_backend)
    checks = [
        (
            "probe_manifest_binding",
            probe_result.get("manifest_sha256") == manifest_hash(manifest_path),
            "probe binds current manifest bytes",
        ),
        (
            "probe_engine_binding",
            probe_result.get("engine_backend") == receipt_backend
            and probe_result.get("model") == model,
            f"probe engine={probe_result.get('engine_backend')}/{probe_result.get('model')}",
        ),
        (
            "probe_transport",
            probe_result.get("wire_only") is False,
            "real probe, not mock transport",
        ),
        (
            "probe_ignorance",
            probe_result.get("decision") == expected["ignorant_decision"]
            and probe_result.get("knew_current") is False,
            f"decision={probe_result.get('decision')!r}; expected stale={expected['ignorant_decision']!r}",
        ),
    ]
    return checks


def check_manifest(manifest_path: Path, *, probe_result: dict | None = None,
                   engine_backend: str = "mock", model: str = "mock-engine-v1") -> list[Check]:
    checks: list[Check] = []
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [("manifest_load", False, str(exc))]

    checks.append((
        "instrument_version",
        manifest.get("instrument_version") == "0.2",
        f"instrument_version={manifest.get('instrument_version')!r}",
    ))
    checks.append((
        "evidence_class",
        manifest.get("evidence_class") == "wire_integration_only",
        f"evidence_class={manifest.get('evidence_class')!r}",
    ))
    checks.append(("impersonal", manifest.get("impersonal") is True, "fixture declares no person-level subject"))
    checks.append((
        "adapter",
        manifest.get("adapter_id") == ADAPTER_ID,
        f"adapter_id={manifest.get('adapter_id')!r}",
    ))
    required_pins = {
        "m2_wall_b_mint",
        "m3_protected_projection",
        "x2_hot_store_actuator",
        "shared_offer_runner",
    }
    pins = manifest.get("component_pins", {})
    pin_failures: list[str] = []
    if set(pins) != required_pins:
        pin_failures.append(
            f"keys={sorted(pins)} expected={sorted(required_pins)}"
        )
    for name, pin in pins.items():
        path = ROOT / pin.get("path", "")
        if not path.is_file():
            pin_failures.append(f"{name}:missing:{pin.get('path')}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if pin.get("sha256") != actual:
            pin_failures.append(f"{name}:sha256:{actual}")
    checks.append((
        "component_pins",
        not pin_failures,
        "M2 mint, M3 projection, X2 actuator, and shared runner pinned"
        if not pin_failures else "; ".join(pin_failures),
    ))
    checks.append((
        "primary_cost_metric",
        manifest.get("primary_cost_metric") == "hot_tokens",
        f"primary_cost_metric={manifest.get('primary_cost_metric')!r}",
    ))

    # The reviewed repair inherits the already-earned X2 P/P/P/U multiplicity;
    # Body-0 may not add repetitions to make the cost inequality true.
    inherited = manifest.get("inherited_x2_geometry", {})
    source_path = ROOT / inherited.get("source_manifest", "")
    try:
        source = json.loads(source_path.read_text())
        source_blocks = list(source.get("blocks", []))
    except (OSError, json.JSONDecodeError) as exc:
        source_blocks = []
        checks.append(("inherited_geometry_source", False, str(exc)))
    else:
        checks.append(("inherited_geometry_source", True, str(source_path.relative_to(ROOT))))
    blocks = list(manifest.get("block_labels", []))
    residence_paths = list(manifest.get("residence_sequence", []))
    geometry_ok = (
        blocks == source_blocks == inherited.get("source_blocks")
        and blocks == ["P"] * len(residence_paths) + ["U"]
    )
    checks.append((
        "inherited_block_multiplicity",
        geometry_ok,
        f"body0={blocks}; source={source_blocks}; residence_n={len(residence_paths)}",
    ))

    path_keys = [manifest.get("e1"), *residence_paths, manifest.get("recurrence")]
    missing = [p for p in path_keys if not p or not (ROOT / p).is_file()]
    if missing:
        checks.append(("episode_files", False, f"missing={missing}"))
        return checks + _probe_checks(
            manifest_path, manifest, probe_result, engine_backend, model
        )
    checks.append(("episode_files", True, f"{len(path_keys)} sequence references present"))

    try:
        pinned = packet_sha256(manifest)
    except Body0ContractError as exc:
        checks.append(("frozen_packet", False, str(exc)))
    else:
        checks.append((
            "frozen_packet",
            pinned == manifest.get("frozen_packet_sha256"),
            f"computed={pinned}; pinned={manifest.get('frozen_packet_sha256')}",
        ))

    e1 = Episode.load(ROOT / manifest["e1"])
    residence = [Episode.load(ROOT / p) for p in residence_paths]
    recurrence = Episode.load(ROOT / manifest["recurrence"])
    universes = [_record_universe(ep) for ep in [e1, *residence, recurrence]]
    checks.append((
        "lineage_universe",
        all(u == universes[0] for u in universes[1:]),
        "base record universe byte-equal across Failure, Residence, and Recurrence",
    ))

    try:
        retraction = load_entry(e1.oracle_ref["corpus_entry"])
    except (KeyError, ValueError) as exc:
        checks.append(("m2_world_mint_source", False, str(exc)))
        retraction = None
    else:
        checks.append((
            "m2_world_mint_source",
            e1.oracle_ref.get("kind") in (None, "retraction") and retraction.category == "retraction",
            f"corpus={retraction.corpus_id}; category={retraction.category}",
        ))

    # Every post-mint episode must remain externally scored.
    post_eps = [*residence, recurrence]
    external_ok = True
    external_details: list[str] = []
    for ep in post_eps:
        ref = ep.oracle_ref
        try:
            if ref.get("kind") == "world_fact":
                entry = load_world_fact_entry(ref["corpus_entry"])
                external_details.append(f"{ep.episode_id}:world_fact:{entry.corpus_id}")
            else:
                entry = load_entry(ref["corpus_entry"])
                external_details.append(f"{ep.episode_id}:retraction:{entry.corpus_id}")
        except (KeyError, ValueError) as exc:
            external_ok = False
            external_details.append(f"{ep.episode_id}:{exc}")
    checks.append(("external_oracles", external_ok, "; ".join(external_details)))

    predicted_earned = None
    if retraction is not None:
        predicted_earned = Record(
            record_id=f"earned-gate-{retraction.corpus_id}",
            text=corrected_claim(retraction),
            created_at="BODY0-GATE",
            predeclared_usage="correction",
            vocabulary_kind="reality_observation",
            trust=1.0,
            provenance={"minted_by": "harness", "gate_prediction": True},
        )
        try:
            _carried, receipt = adapt_earned_record(predicted_earned, manifest.get("adapter_id", ""))
            checks.append(("adapter_identity", receipt.identity_ok, receipt.input_sha256))
        except Body0ContractError as exc:
            checks.append(("adapter_identity", False, str(exc)))

    if predicted_earned is not None:
        # Static offer-dependence check on the exact runtime record text.
        with tempfile.TemporaryDirectory() as td:
            auth = Path(td) / "authority.json"
            auth.write_text("{}")
            branch = BranchConfig(
                "body0-gate",
                memory="governed",
                top_k=int(manifest.get("top_k", 1)),
                recency_weight=float(manifest.get("recency_weight", 0.0)),
                similarity_backend="lexical_tfidf",
                eligibility_threshold=0.0,
                authority_path=str(auth),
            )
            p = residence[0]
            p.records.append(predicted_earned)
            u = recurrence
            u.records.append(predicted_earned)
            p_offer = [r.record_id for r, _ in select_offers(branch, p)[0]]
            u_offer = [r.record_id for r, _ in select_offers(branch, u)[0]]
        checks.append((
            "offer_residence",
            p_offer == [manifest.get("answer_record_residence")],
            f"offered={p_offer}",
        ))
        checks.append((
            "offer_recurrence",
            u_offer == [predicted_earned.record_id],
            f"offered={u_offer}; earned={predicted_earned.record_id}",
        ))
        record_texts = {r["record_id"]: r["text"] for r in universes[0]}
        record_texts[predicted_earned.record_id] = predicted_earned.text
        cost = cost_state_preflight(
            record_texts, predicted_earned.record_id, len(residence_paths)
        )
        checks.append((
            "cost_state_dependence",
            cost["gate_open"],
            json.dumps(cost, sort_keys=True),
        ))

    attack = manifest.get("attack_foreground", {})
    attack_ok = (
        set(attack) == {"datum_id", "channel", "observed_at", "text"}
        and attack.get("channel") == "attacker_owned_foreground"
        and bool(attack.get("text"))
    )
    checks.append(("attack_surface", attack_ok, f"keys={sorted(attack)}"))

    checks.extend(_probe_checks(manifest_path, manifest, probe_result, engine_backend, model))
    return checks


def gate_result(manifest_path: Path, *, probe_result: dict | None = None,
                engine_backend: str = "mock", model: str = "mock-engine-v1") -> dict:
    checks = check_manifest(
        manifest_path,
        probe_result=probe_result,
        engine_backend=engine_backend,
        model=model,
    )
    return {
        "manifest_sha256": manifest_hash(manifest_path),
        "gate_open": all(ok for _name, ok, _detail in checks),
        "n_checks": len(checks),
        "n_passed": sum(1 for _name, ok, _detail in checks if ok),
        "checks": [
            {"check": name, "ok": ok, "detail": detail}
            for name, ok, detail in checks
        ],
        "engine_backend": backend_receipt_name(engine_backend),
        "engine_backend_cli": engine_backend,
        "model": model,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Body-0 fixture/admission gate")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--probe-result")
    parser.add_argument("--engine", default="mock", choices=["mock", "claude", "local"])
    parser.add_argument("--model", default="mock-engine-v1")
    args = parser.parse_args()
    path = Path(args.manifest)
    probe = json.loads(Path(args.probe_result).read_text()) if args.probe_result else None
    result = gate_result(
        path,
        probe_result=probe,
        engine_backend=args.engine,
        model=args.model,
    )
    for check in result["checks"]:
        print(f"{'PASS' if check['ok'] else 'FAIL':4s}  {check['check']}: {check['detail']}")
    if not result["gate_open"]:
        print(
            f"\nGATE REFUSED: {result['n_checks'] - result['n_passed']} Body-0 check(s) failed.",
            file=sys.stderr,
        )
        return 1
    print(f"\nGATE OPEN: {path.name} passes Body-0 preflight ({args.engine}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
