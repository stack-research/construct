"""EFC v0 K4 BR — three frozen B-family replacement captures.

Usage:
  python -m harness.efc_capture_k4br              # dry-run
  python -m harness.efc_capture_k4br --execute  # three GETs
  python -m harness.efc_capture_k4br --verify-hashes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

from harness.efc_capture_k4 import (
    K4_ROOT,
    SEAT,
    CaptureRefusal,
    build_global_ledger,
    canonical_json,
    extract_aliases,
    p_rows_from_disk,
    rel_repo,
    sha256_bytes,
    sha256_file,
)

SCHEMA_VERSION = "efc-k4br-acquisition-v1"
MAX_CALLS = 3

KIMI_DISCOVERY_ONLY = (
    "GHSA-6q6h-j7hj-3r64",
    "GHSA-537c-gmf6-5ccf",
    "GHSA-wgvc-ghv9-3pmm",
)

KIMI_DISCOVERY_ONLY_URLS = frozenset({
    "https://api.github.com/advisories/GHSA-6q6h-j7hj-3r64",
    "https://api.github.com/advisories/GHSA-537c-gmf6-5ccf",
    "https://api.github.com/advisories/GHSA-wgvc-ghv9-3pmm",
})

EXCLUDED_B_SLOTS = ("B02", "B03", "B06")


@dataclass(frozen=True)
class BRSpec:
    slot: str
    ghsa_id: str
    package: str
    ecosystem: str
    capture_url: str
    cve_alias: str
    branches: tuple[tuple[str, str], ...]


FROZEN_BR: tuple[BRSpec, ...] = (
    BRSpec(
        "BR01", "GHSA-hmw2-7cc7-3qxx", "form-data", "npm",
        "https://api.github.com/advisories/GHSA-hmw2-7cc7-3qxx",
        "CVE-2026-12143",
        (("< 2.5.6", "2.5.6"),
         (">= 3.0.0, < 3.0.5", "3.0.5"),
         (">= 4.0.0, < 4.0.6", "4.0.6")),
    ),
    BRSpec(
        "BR02", "GHSA-hm92-r4w5-c3mj", "undici", "npm",
        "https://api.github.com/advisories/GHSA-hm92-r4w5-c3mj",
        "CVE-2026-6734",
        ((">= 7.23.0, < 7.28.0", "7.28.0"),
         (">= 8.0.0, < 8.2.0", "8.2.0")),
    ),
    BRSpec(
        "BR03", "GHSA-xgmm-8j9v-c9wx", "pyjwt", "pip",
        "https://api.github.com/advisories/GHSA-xgmm-8j9v-c9wx",
        "CVE-2026-48526",
        (("< 2.13.0", "2.13.0"),),
    ),
)

FROZEN_URLS: frozenset[str] = frozenset(s.capture_url for s in FROZEN_BR)


class TransportResponse(Protocol):
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]
    redirect_refused: bool


Transport = Callable[[str], TransportResponse]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def module_sha256() -> str:
    return sha256_file(Path(__file__).resolve())


def assembly_base_ledger_sha256(root: Path = K4_ROOT) -> str:
    path = root / "promotion_identity_ledger.json"
    if not path.exists():
        raise CaptureRefusal("promotion_identity_ledger.json missing")
    return sha256_file(path)


def check_br_create_once(root: Path = K4_ROOT) -> None:
    for spec in FROZEN_BR:
        cap = root / "captures" / spec.slot
        if cap.exists():
            for p in cap.rglob("*"):
                if p.is_file():
                    raise CaptureRefusal(f"br create-once: {p}")


def _branch_tuple(vuln: dict) -> tuple[str, str, str, str]:
    pkg = vuln.get("package") or {}
    return (
        str(pkg.get("ecosystem", "")),
        str(pkg.get("name", "")),
        str(vuln.get("vulnerable_version_range", "")),
        str(vuln.get("first_patched_version", "")),
    )


def qualify_br(spec: BRSpec, data: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if data.get("ghsa_id") != spec.ghsa_id:
        reasons.append("ghsa_id_mismatch")
    if data.get("type") != "reviewed":
        reasons.append("not_reviewed")
    pub = data.get("published_at") or ""
    if not str(pub).startswith("2026"):
        reasons.append("published_at_not_2026")
    if data.get("cve_id") != spec.cve_alias:
        reasons.append("cve_alias_mismatch")
    vulns = data.get("vulnerabilities") or []
    if len(vulns) != len(spec.branches):
        reasons.append("branch_count_mismatch")
    else:
        actual = [_branch_tuple(v) for v in vulns]
        expected = [
            (spec.ecosystem, spec.package, vuln, patch)
            for vuln, patch in spec.branches
        ]
        if actual != expected:
            reasons.append("branch_values_mismatch")
    return not reasons, reasons


def qualify_br_slot(
    spec: BRSpec, body: bytes, *, http_status: int, redirect_refused: bool,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if http_status != 200:
        reasons.append("http_not_200")
    if redirect_refused:
        reasons.append("redirect_refused")
    try:
        data = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        reasons.append("json_parse_error")
        return False, reasons
    if not isinstance(data, dict):
        reasons.append("not_object")
        return False, reasons
    ok, r = qualify_br(spec, data)
    reasons.extend(r)
    return ok and not reasons, reasons


@dataclass
class LiveResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]
    redirect_refused: bool = False


def live_transport(url: str) -> LiveResponse:
    if url not in FROZEN_URLS:
        raise CaptureRefusal(f"url not in allowlist: {url}")
    req = urllib.request.Request(
        url, headers={"User-Agent": "efc-k4br-capture/1.0"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            final = resp.geturl()
            if final != url:
                return LiveResponse(
                    resp.status, dict(resp.headers), resp.read(), url,
                    [url, final], redirect_refused=True)
            return LiveResponse(
                resp.status, dict(resp.headers), resp.read(), final, [url])
    except urllib.error.HTTPError as e:
        return LiveResponse(
            e.code, dict(e.headers), e.read(), url, [url])


def build_plan(root: Path = K4_ROOT) -> dict:
    body = {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "phase": "b_replacement_capture",
        "max_network_calls": MAX_CALLS,
        "redirect_policy": "refuse",
        "retry_policy": "zero",
        "assembly_base_ledger_sha256": assembly_base_ledger_sha256(root),
        "slots": [
            {
                "slot": s.slot,
                "family": "B",
                "ghsa_id": s.ghsa_id,
                "package": s.package,
                "ecosystem": s.ecosystem,
                "capture_url": s.capture_url,
                "cve_alias": s.cve_alias,
                "branches": [{"vulnerable": v, "patched": p} for v, p in s.branches],
                "raw_path": f"captures/{s.slot}/raw.json",
                "sidecar_path": f"captures/{s.slot}/sidecar.json",
            }
            for s in FROZEN_BR
        ],
        "excluded_k1_b_slots": list(EXCLUDED_B_SLOTS),
        "discovery_only_exclusions": {
            "ghsa_ids": list(KIMI_DISCOVERY_ONLY),
            "urls": sorted(KIMI_DISCOVERY_ONLY_URLS),
        },
        "implementation_module_sha256": module_sha256(),
    }
    plan = dict(body)
    plan["plan_sha256"] = sha256_bytes(canonical_json(body).encode())
    return plan


def br_rows_from_captures(root: Path = K4_ROOT) -> list[dict]:
    rows: list[dict] = []
    for spec in FROZEN_BR:
        cap_dir = root / "captures" / spec.slot
        if not cap_dir.exists():
            continue
        sc = json.loads((cap_dir / "sidecar.json").read_text())
        try:
            parsed = json.loads((cap_dir / "raw.json").read_text())
        except Exception:
            parsed = {}
        ok = sc.get("qualification_verdict") == "pass"
        rows.append({
            "logical_slot": spec.slot,
            "family": "B",
            "record_id": spec.ghsa_id,
            "entity_key": spec.package,
            "canonical_url": spec.capture_url,
            "capture_path": rel_repo(cap_dir / "raw.json"),
            "raw_sha256": sc["raw_sha256"],
            "sidecar_sha256": sha256_file(cap_dir / "sidecar.json"),
            "qualification_verdict": sc["qualification_verdict"],
            "promotion_eligible": ok,
            "source_seat": SEAT,
            "alias_extraction": extract_aliases(parsed, "ghsa"),
            "format_provenance": "ghsa",
            "replacement_for": "b_family_shortfall",
        })
    return rows


def dry_run(root: Path = K4_ROOT) -> dict:
    return {
        "mode": "dry_run",
        "network_calls": 0,
        "plan": build_plan(root),
    }


def execute_live(
    root: Path = K4_ROOT,
    transport: Transport | None = None,
) -> dict:
    check_br_create_once(root)
    transport = transport or live_transport
    plan = build_plan(root)
    plan_sha = plan["plan_sha256"]
    (root / "br_plan.json").write_text(canonical_json(plan) + "\n")

    call_count = 0
    br_ledger: list[dict] = []
    br_rows: list[dict] = []

    for spec in FROZEN_BR:
        resp = transport(spec.capture_url)
        call_count += 1
        ok, reasons = qualify_br_slot(
            spec, resp.body, http_status=resp.status,
            redirect_refused=resp.redirect_refused)
        cap_dir = root / "captures" / spec.slot
        cap_dir.mkdir(parents=True)
        (cap_dir / "raw.json").write_bytes(resp.body)
        raw_sha = sha256_bytes(resp.body)
        parsed = json.loads(resp.body.decode("utf-8"))
        alias_info = extract_aliases(parsed, "ghsa")
        sidecar = {
            "schema_version": SCHEMA_VERSION,
            "slot": spec.slot,
            "family": "B",
            "ghsa_id": spec.ghsa_id,
            "package": spec.package,
            "ecosystem": spec.ecosystem,
            "capture_url": spec.capture_url,
            "http_status": resp.status,
            "redirect_refused": resp.redirect_refused,
            "redirect_chain": resp.redirect_chain,
            "raw_sha256": raw_sha,
            "raw_byte_length": len(resp.body),
            "qualification_verdict": "pass" if ok else "fail",
            "failure_reasons": reasons,
            "plan_sha256": plan_sha,
            "assembly_base_ledger_sha256": plan["assembly_base_ledger_sha256"],
            "format_provenance": "ghsa",
            "retrieved_at_utc": utc_now_iso(),
            "implementation_module_sha256": module_sha256(),
        }
        if ok:
            sidecar["oracle_id"] = f"efc-calibration-{spec.slot}"
        (cap_dir / "sidecar.json").write_text(canonical_json(sidecar) + "\n")

        br_ledger.append({
            "slot": spec.slot,
            "ghsa_id": spec.ghsa_id,
            "qualification_verdict": sidecar["qualification_verdict"],
            "failure_reasons": reasons,
            "raw_sha256": raw_sha,
        })
        br_rows.append({
            "logical_slot": spec.slot,
            "family": "B",
            "record_id": spec.ghsa_id,
            "entity_key": spec.package,
            "canonical_url": spec.capture_url,
            "capture_path": rel_repo(cap_dir / "raw.json"),
            "raw_sha256": raw_sha,
            "sidecar_sha256": sha256_file(cap_dir / "sidecar.json"),
            "qualification_verdict": sidecar["qualification_verdict"],
            "promotion_eligible": ok,
            "source_seat": SEAT,
            "alias_extraction": alias_info,
            "format_provenance": "ghsa",
            "replacement_for": "b_family_shortfall",
        })

    p_rows = p_rows_from_disk(root)
    global_ledger = build_global_ledger(root, p_rows, br_rows)

    (root / "br_qualification_ledger.json").write_text(
        canonical_json({
            "schema_version": SCHEMA_VERSION,
            "seat": SEAT,
            "plan_sha256": plan_sha,
            "assembly_base_ledger_sha256": plan["assembly_base_ledger_sha256"],
            "slots": br_ledger,
            "generated_at_utc": utc_now_iso(),
        }) + "\n")
    (root / "promotion_identity_ledger.json").write_text(
        canonical_json(global_ledger) + "\n")

    report = {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "phase": "b_replacement_capture",
        "network_calls": call_count,
        "max_network_calls": MAX_CALLS,
        "plan_sha256": plan_sha,
        "br_pass_count": sum(1 for x in br_ledger if x["qualification_verdict"] == "pass"),
        "br_shortfall": any(x["qualification_verdict"] != "pass" for x in br_ledger),
        "global_assertions": global_ledger["assertions"],
        "promoted_row_count": global_ledger["row_count"],
        "replacement_shortfall": global_ledger["replacement_shortfall"],
        "b_replacement_shortfall": global_ledger["b_replacement_shortfall"],
        "generated_at_utc": utc_now_iso(),
    }
    (root / "br_capture_report.json").write_text(canonical_json(report) + "\n")

    capture_report = root / "capture_report.json"
    if capture_report.exists():
        merged = json.loads(capture_report.read_text())
        merged["global_assertions"] = global_ledger["assertions"]
        merged["promoted_row_count"] = global_ledger["row_count"]
        merged["replacement_shortfall"] = global_ledger["replacement_shortfall"]
        merged["b_replacement_shortfall"] = global_ledger["b_replacement_shortfall"]
        merged["br_capture_completed_at_utc"] = utc_now_iso()
        capture_report.write_text(canonical_json(merged) + "\n")

    return {
        "mode": "live",
        "network_calls": call_count,
        "br_qualification_ledger": br_ledger,
        "promotion_identity_ledger": global_ledger,
        "report": report,
    }


def verify_hashes(root: Path = K4_ROOT) -> list[str]:
    errors: list[str] = []
    for spec in FROZEN_BR:
        cdir = root / "captures" / spec.slot
        if not cdir.exists():
            errors.append(f"missing {spec.slot}")
            continue
        sc = json.loads((cdir / "sidecar.json").read_text())
        if sha256_file(cdir / "raw.json") != sc.get("raw_sha256"):
            errors.append(f"hash mismatch {spec.slot}")
        if sc.get("qualification_verdict") == "fail" and sc.get("oracle_id"):
            errors.append(f"oracle on failed {spec.slot}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EFC K4 B replacement capture")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--verify-hashes", action="store_true")
    args = parser.parse_args(argv)

    if args.verify_hashes:
        errs = verify_hashes()
        if errs:
            for e in errs:
                print(e, file=sys.stderr)
            return 1
        print("all K4 BR hashes verified")
        return 0

    if args.execute:
        try:
            print(canonical_json(execute_live()))
        except CaptureRefusal as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        return 0

    print(canonical_json(dry_run()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
