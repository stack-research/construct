"""EFC v0 K3d — zero-network identity attestation + promotion ledger v2.

Corrects K3c reconciliation lineage mislabeling without altering K3/K3c bytes.

Usage:
  python -m harness.efc_capture_k3d --dry-run
  python -m harness.efc_capture_k3d --execute
  python -m harness.efc_capture_k3d --verify-all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from harness import efc_capture_k3 as k3
from harness.efc_capture_k3c import (
    K3C_ROOT,
    K3_ROOT,
    LOGICAL_SLOTS,
    RECON_ROOT,
    CAPTURE_ROOT,
    K3_SUPERSEDED_INELIGIBLE,
    CaptureRefusal,
    canonical_json,
    sha256_bytes,
    sha256_file,
    verify_all as verify_k3c,
)

REPO = Path(__file__).resolve().parent.parent
K3D_ROOT = REPO / "corpus" / "efc_calibration" / "_acquisition" / "k3d"
SCHEMA_VERSION = "efc-k3d-v1"
SEAT = "cursor/composer-2.5-capture"

AUTHORITATIVE_CAPTURE_IMPL = (
    "1f750b8b48ca5a3b6e49ba67c38e366a6fec061f70103325cf8f0b59fec899d9"
)
ERRONEOUS_CAPTURE_IMPL_LABEL = (
    "e2b9448b7f0fe0c202e76654764e766d03061a6876437b32db652dd8ef85f701"
)
K3C_RECON_IMPL = (
    "f9225019397774ae45676ce0397b94e7d73d6f59d148a9c216262ef22f19d659"
)
FINDING = "post_fix_k3_hash_mislabeled_as_capture_implementation_hash"
CORRECTION_RULE = (
    "For F01/F04 lineage, original capture implementation identity comes from "
    "the original K3 plan/sidecars; reconciliation implementation identity "
    "comes from the K3c plan/sidecars."
)
RECON_IDS = ("capF-01", "capF-04")

K3D_ARTIFACTS = (
    "identity_plan.json",
    "identity_attestation.json",
    "promotion_ledger_v2.json",
    "verification_report.json",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def module_sha256() -> str:
    return sha256_file(Path(__file__).resolve())


def rel_repo(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def tree_digest(root: Path) -> str:
    if not root.exists():
        raise CaptureRefusal(f"missing tree: {root}")
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def check_create_once() -> None:
    if K3D_ROOT.exists():
        for name in K3D_ARTIFACTS:
            if (K3D_ROOT / name).exists():
                raise CaptureRefusal(f"create-once: {name} exists")


def read_k3_plan() -> dict:
    path = K3_ROOT / "plan.json"
    if not path.exists():
        raise CaptureRefusal("missing k3/plan.json")
    return json.loads(path.read_text())


def build_identity_plan() -> dict:
    k3_plan_path = K3_ROOT / "plan.json"
    body = {
        "schema_version": SCHEMA_VERSION,
        "phase": "identity_attestation",
        "network_calls": 0,
        "seat": SEAT,
        "inputs": {
            "k3_plan_path": rel_repo(k3_plan_path),
            "k3c_reconciliation_plan_path": rel_repo(RECON_ROOT / "plan.json"),
            "k3c_promotion_ledger_path": rel_repo(K3C_ROOT / "promotion_ledger.json"),
            "reconciled_capture_ids": list(RECON_IDS),
        },
        "outputs": {name: name for name in K3D_ARTIFACTS},
        "authoritative_capture_implementation_module_sha256": AUTHORITATIVE_CAPTURE_IMPL,
        "erroneous_capture_implementation_label": ERRONEOUS_CAPTURE_IMPL_LABEL,
        "k3c_reconciliation_implementation_module_sha256": K3C_RECON_IMPL,
        "finding": FINDING,
        "correction_rule": CORRECTION_RULE,
        "attestation_module_sha256": module_sha256(),
        "no_byte_changes": True,
    }
    body["plan_sha256"] = sha256_bytes(canonical_json(body).encode())
    return body


def build_identity_attestation(plan: dict) -> dict:
    k3_plan_path = K3_ROOT / "plan.json"
    k3_plan = read_k3_plan()
    auth_impl = k3_plan.get("implementation_module_sha256")
    if auth_impl != AUTHORITATIVE_CAPTURE_IMPL:
        raise CaptureRefusal(
            f"k3 plan capture impl mismatch: {auth_impl}")

    original_sidecars: dict[str, dict] = {}
    for cid in RECON_IDS:
        sc_path = K3_ROOT / "captures" / cid / "sidecar.json"
        sc = json.loads(sc_path.read_text())
        impl = sc.get("implementation_module_sha256")
        if impl != AUTHORITATIVE_CAPTURE_IMPL:
            raise CaptureRefusal(
                f"original {cid} sidecar impl mismatch: {impl}")
        original_sidecars[cid] = {
            "path": rel_repo(sc_path),
            "sha256": sha256_file(sc_path),
            "implementation_module_sha256": impl,
        }

    recon_plan_path = RECON_ROOT / "plan.json"
    recon_plan = json.loads(recon_plan_path.read_text())
    erroneous_plan_impl = recon_plan.get("k3_implementation_module_sha256")
    if erroneous_plan_impl != ERRONEOUS_CAPTURE_IMPL_LABEL:
        raise CaptureRefusal(
            "k3c reconciliation plan missing expected erroneous label")

    erroneous_sidecars: dict[str, dict] = {}
    for cid in RECON_IDS:
        sc_path = RECON_ROOT / cid / "sidecar.json"
        sc = json.loads(sc_path.read_text())
        bad = sc.get("k3_implementation_module_sha256")
        if bad != ERRONEOUS_CAPTURE_IMPL_LABEL:
            raise CaptureRefusal(
                f"k3c recon sidecar {cid} missing expected erroneous label")
        erroneous_sidecars[cid] = {
            "path": rel_repo(sc_path),
            "sha256": sha256_file(sc_path),
            "erroneous_field": "k3_implementation_module_sha256",
            "erroneous_value": bad,
        }

    recon_impl = recon_plan.get("reconciliation_module_sha256")
    if recon_impl != K3C_RECON_IMPL:
        raise CaptureRefusal(f"k3c reconciliation impl mismatch: {recon_impl}")

    attestation = {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "network_calls": 0,
        "finding": FINDING,
        "correction_rule": CORRECTION_RULE,
        "no_byte_changes": True,
        "authoritative": {
            "k3_plan_path": rel_repo(k3_plan_path),
            "k3_plan_sha256": sha256_file(k3_plan_path),
            "capture_implementation_module_sha256": AUTHORITATIVE_CAPTURE_IMPL,
            "k3_plan_recorded_impl": auth_impl,
        },
        "original_capture_sidecars": original_sidecars,
        "erroneous_k3c_artifacts": {
            "reconciliation_plan": {
                "path": rel_repo(recon_plan_path),
                "sha256": sha256_file(recon_plan_path),
                "erroneous_field": "k3_implementation_module_sha256",
                "erroneous_value": erroneous_plan_impl,
            },
            "reconciliation_sidecars": erroneous_sidecars,
        },
        "reconciliation_implementation_module_sha256": K3C_RECON_IMPL,
        "identity_plan_sha256": plan["plan_sha256"],
        "attestation_module_sha256": module_sha256(),
        "generated_at_utc": utc_now_iso(),
    }
    attestation["attestation_sha256"] = sha256_bytes(
        canonical_json(attestation).encode())
    return attestation


def _recon_extract_hashes(cid: str) -> dict:
    base = RECON_ROOT / cid
    out: dict[str, str] = {}
    for name in ("extract.json", "normalized.txt", "section.txt"):
        p = base / name
        if p.exists():
            out[name.replace(".", "_")] = sha256_file(p)
    return out


def _slot_mapping_v2(slot: str, attestation_sha: str) -> dict:
    if slot in ("F01", "F04"):
        cid = "capF-01" if slot == "F01" else "capF-04"
        orig_sc_path = K3_ROOT / "captures" / cid / "sidecar.json"
        recon_sc_path = RECON_ROOT / cid / "sidecar.json"
        orig_sc = json.loads(orig_sc_path.read_text())
        recon_sc = json.loads(recon_sc_path.read_text())
        return {
            "logical_slot": slot,
            "source_capture_id": cid,
            "source_kind": "k3c_reconciled",
            "qualification_verdict": recon_sc["reconciliation_verdict"],
            "promotion_eligible": recon_sc["reconciliation_verdict"] == "pass",
            "capture_time_verdict": orig_sc["capture_verdict"],
            "reconciliation_verdict": recon_sc["reconciliation_verdict"],
            "identity_lineage": {
                "original_raw_sha256": orig_sc["raw_sha256"],
                "original_capture_sidecar_sha256": sha256_file(orig_sc_path),
                "authoritative_capture_implementation_module_sha256": (
                    AUTHORITATIVE_CAPTURE_IMPL),
                "reconciliation_sidecar_sha256": sha256_file(recon_sc_path),
                "reconciliation_extract_hashes": _recon_extract_hashes(cid),
                "reconciliation_implementation_module_sha256": K3C_RECON_IMPL,
                "identity_attestation_sha256": attestation_sha,
                "erroneous_k3c_capture_impl_label": ERRONEOUS_CAPTURE_IMPL_LABEL,
            },
            "artifact_hashes": {
                "raw_sha256": orig_sc["raw_sha256"],
                "sidecar_sha256": sha256_file(recon_sc_path),
            },
        }

    # eight non-reconciled slots — mirror k3c ledger evidence
    mapping = _base_slot_from_k3c(slot)
    return mapping


def _base_slot_from_k3c(slot: str) -> dict:
    ledger = json.loads((K3C_ROOT / "promotion_ledger.json").read_text())
    for m in ledger["logical_slot_mappings"]:
        if m["logical_slot"] == slot:
            return dict(m)
    raise CaptureRefusal(f"missing k3c slot {slot}")


def build_promotion_ledger_v2(attestation: dict) -> dict:
    att_sha = attestation["attestation_sha256"]
    mappings = [_slot_mapping_v2(slot, att_sha) for slot in LOGICAL_SLOTS]
    slots = {m["logical_slot"] for m in mappings}
    if len(slots) != 10:
        raise CaptureRefusal("promotion ledger v2 slot count != 10")

    k3c_ledger_path = K3C_ROOT / "promotion_ledger.json"
    k3c_ledger = json.loads(k3c_ledger_path.read_text())
    superseded = []
    for row in k3c_ledger.get("superseded_ineligible", []):
        superseded.append(dict(row))

    e_pass = sum(
        1 for m in mappings
        if m["logical_slot"].startswith("E") and m["promotion_eligible"])
    f_pass = sum(
        1 for m in mappings
        if m["logical_slot"].startswith("F") and m["promotion_eligible"])

    for slot in ("F01", "F04"):
        m = next(x for x in mappings if x["logical_slot"] == slot)
        lin = m["identity_lineage"]
        if lin["authoritative_capture_implementation_module_sha256"] != (
                AUTHORITATIVE_CAPTURE_IMPL):
            raise CaptureRefusal(f"{slot} lineage capture impl wrong")
        if lin["reconciliation_implementation_module_sha256"] != K3C_RECON_IMPL:
            raise CaptureRefusal(f"{slot} lineage recon impl wrong")
        if m["capture_time_verdict"] != "fail":
            raise CaptureRefusal(f"{slot} capture_time_verdict must be fail")
        if m["reconciliation_verdict"] != "pass":
            raise CaptureRefusal(f"{slot} reconciliation_verdict must be pass")
        if not m["promotion_eligible"]:
            raise CaptureRefusal(f"{slot} must be promotion_eligible")

    all_eligible = all(m["promotion_eligible"] for m in mappings)
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "logical_slot_mappings": mappings,
        "superseded_ineligible": superseded,
        "superseded_closure_ledger": {
            "path": rel_repo(k3c_ledger_path),
            "sha256": sha256_file(k3c_ledger_path),
            "superseded_for_closure": True,
            "prior_k3_closed_claim": k3c_ledger.get("k3_closed"),
        },
        "identity_attestation_sha256": att_sha,
        "family_e_pass_count": e_pass,
        "family_f_pass_count": f_pass,
        "k3_closed": all_eligible and e_pass == 6 and f_pass == 4,
        "generated_at_utc": utc_now_iso(),
    }
    return ledger


def verify_lineage(attestation: dict, ledger_v2: dict) -> list[str]:
    errors: list[str] = []
    k3_plan = read_k3_plan()
    plan_impl = k3_plan.get("implementation_module_sha256")
    if plan_impl != AUTHORITATIVE_CAPTURE_IMPL:
        errors.append("k3 plan authoritative capture impl mismatch")

    att_auth = attestation["authoritative"]["capture_implementation_module_sha256"]
    if att_auth != plan_impl:
        errors.append("attestation capture impl != k3 plan")

    for cid in RECON_IDS:
        sc = json.loads((K3_ROOT / "captures" / cid / "sidecar.json").read_text())
        if sc.get("implementation_module_sha256") != plan_impl:
            errors.append(f"{cid} original sidecar impl != k3 plan")

        recon_sc = json.loads((RECON_ROOT / cid / "sidecar.json").read_text())
        mislabeled = recon_sc.get("k3_implementation_module_sha256")
        if mislabeled != ERRONEOUS_CAPTURE_IMPL_LABEL:
            errors.append(f"{cid} k3c sidecar missing erroneous label")
        if mislabeled == plan_impl:
            errors.append(
                f"{cid} reconciled sidecar falsely matches capture impl")

    for m in ledger_v2["logical_slot_mappings"]:
        if m["logical_slot"] in ("F01", "F04"):
            lin = m.get("identity_lineage", {})
            if lin.get("authoritative_capture_implementation_module_sha256") != (
                    plan_impl):
                errors.append(
                    f"{m['logical_slot']} ledger v2 capture impl wrong")
            if lin.get("reconciliation_implementation_module_sha256") == plan_impl:
                errors.append(
                    f"{m['logical_slot']} ledger confuses recon with capture")
            if lin.get("identity_attestation_sha256") != attestation.get(
                    "attestation_sha256"):
                errors.append(f"{m['logical_slot']} attestation hash mismatch")

    if ledger_v2.get("k3_closed") and not (
            K3D_ROOT / "identity_attestation.json").exists():
        errors.append("k3_closed without attestation artifact")

    k3c_path = K3C_ROOT / "promotion_ledger.json"
    if k3c_path.exists():
        k3c = json.loads(k3c_path.read_text())
        if k3c.get("k3_closed") and not ledger_v2.get("identity_attestation_sha256"):
            errors.append("k3c closure without v2 attestation reference")

    return errors


def verify_trees_unchanged(pre: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for label, root in (("k3", K3_ROOT), ("k3c", K3C_ROOT)):
        if tree_digest(root) != pre[label]:
            errors.append(f"{label} tree changed after K3d")
    errors.extend(k3.verify_hashes(K3_ROOT))
    errors.extend(verify_k3c())
    return errors


def build_verification_report(
    pre_trees: dict[str, str],
    attestation: dict,
    ledger_v2: dict,
) -> dict:
    post_trees = {"k3": tree_digest(K3_ROOT), "k3c": tree_digest(K3C_ROOT)}
    lineage_errors = verify_lineage(attestation, ledger_v2)
    tree_errors = verify_trees_unchanged(pre_trees)
    checks = [
        {"name": "k3_tree_unchanged",
         "pass": pre_trees["k3"] == post_trees["k3"]},
        {"name": "k3c_tree_unchanged",
         "pass": pre_trees["k3c"] == post_trees["k3c"]},
        {"name": "lineage_attestation",
         "pass": len(lineage_errors) == 0},
        {"name": "promotion_ledger_v2_closed",
         "pass": ledger_v2.get("k3_closed") is True},
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "network_calls": 0,
        "pre_tree_hashes": pre_trees,
        "post_tree_hashes": post_trees,
        "checks": checks,
        "lineage_errors": lineage_errors,
        "tree_errors": tree_errors,
        "identity_attestation_sha256": attestation["attestation_sha256"],
        "promotion_ledger_v2_k3_closed": ledger_v2.get("k3_closed"),
        "all_checks_pass": all(c["pass"] for c in checks)
        and not tree_errors and not lineage_errors,
        "generated_at_utc": utc_now_iso(),
    }


def execute() -> dict:
    check_create_once()
    K3D_ROOT.mkdir(parents=True, exist_ok=True)
    pre_trees = {"k3": tree_digest(K3_ROOT), "k3c": tree_digest(K3C_ROOT)}

    plan = build_identity_plan()
    (K3D_ROOT / "identity_plan.json").write_text(canonical_json(plan) + "\n")

    attestation = build_identity_attestation(plan)
    (K3D_ROOT / "identity_attestation.json").write_text(
        canonical_json(attestation) + "\n")

    ledger_v2 = build_promotion_ledger_v2(attestation)
    (K3D_ROOT / "promotion_ledger_v2.json").write_text(
        canonical_json(ledger_v2) + "\n")

    report = build_verification_report(pre_trees, attestation, ledger_v2)
    (K3D_ROOT / "verification_report.json").write_text(
        canonical_json(report) + "\n")

    if not report["all_checks_pass"]:
        raise CaptureRefusal("verification failed at execute time")

    return {
        "mode": "execute",
        "network_calls": 0,
        "pre_tree_hashes": pre_trees,
        "post_tree_hashes": report["post_tree_hashes"],
        "identity_attestation_sha256": attestation["attestation_sha256"],
        "promotion_ledger_v2_k3_closed": ledger_v2["k3_closed"],
        "verification_report": report,
    }


def verify_all() -> list[str]:
    errors: list[str] = []
    errors.extend(k3.verify_hashes(K3_ROOT))
    errors.extend(verify_k3c())
    for name in K3D_ARTIFACTS:
        if not (K3D_ROOT / name).exists():
            errors.append(f"missing k3d artifact: {name}")
            return errors

    attestation = json.loads(
        (K3D_ROOT / "identity_attestation.json").read_text())
    ledger_v2 = json.loads(
        (K3D_ROOT / "promotion_ledger_v2.json").read_text())
    report = json.loads(
        (K3D_ROOT / "verification_report.json").read_text())

    errors.extend(verify_lineage(attestation, ledger_v2))
    if report.get("post_tree_hashes"):
        errors.extend(verify_trees_unchanged(report["pre_tree_hashes"]))

    if not ledger_v2.get("k3_closed"):
        errors.append("promotion_ledger_v2 k3_closed is false")

    if not report.get("all_checks_pass"):
        errors.append("verification_report all_checks_pass is false")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EFC K3d identity attestation")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--verify-all", action="store_true")
    args = parser.parse_args(argv)

    if args.verify_all:
        errs = verify_all()
        if errs:
            for e in errs:
                print(e, file=sys.stderr)
            return 1
        print("all K3+K3c+K3d verification passed")
        return 0

    if args.dry_run:
        plan = build_identity_plan()
        print(canonical_json({
            "mode": "dry_run",
            "network_calls": 0,
            "plan": plan,
        }))
        return 0

    if args.execute:
        try:
            print(canonical_json(execute()))
        except CaptureRefusal as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
