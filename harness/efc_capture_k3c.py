"""EFC v0 K3c — offline F reconciliation + corrected four-URL capture.

Phase 1: reconcile saved capF-01/capF-04 raw.html from K3 (zero network).
Phase 2: capture capE-04c..06c + capF-03c (max four GETs, no redirects).

Usage:
  python -m harness.efc_capture_k3c --reconcile-dry-run
  python -m harness.efc_capture_k3c --reconcile
  python -m harness.efc_capture_k3c --capture-dry-run
  python -m harness.efc_capture_k3c --capture
  python -m harness.efc_capture_k3c --execute   # reconcile then capture
  python -m harness.efc_capture_k3c --verify-all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

from harness import efc_capture_k3 as k3

REPO = Path(__file__).resolve().parent.parent
K3_ROOT = k3.K3_ROOT
K3C_ROOT = REPO / "corpus" / "efc_calibration" / "_acquisition" / "k3c"
RECON_ROOT = K3C_ROOT / "reconciliation"
CAPTURE_ROOT = K3C_ROOT / "captures"
SCHEMA_VERSION = "efc-k3c-v1"
SEAT = "cursor/composer-2.5-capture"
MAX_CAPTURE_CALLS = 4

RECON_IDS = ("capF-01", "capF-04")

LOGICAL_SLOTS = (
    "E01", "E02", "E03", "E04", "E05", "E06",
    "F01", "F02", "F03", "F04",
)

K3_SUPERSEDED_INELIGIBLE = (
    "capE-04", "capE-05", "capE-06",
    "capF-01", "capF-03", "capF-04",
)

EXPECTED_F01 = {
    "locator": "Removed APIs by release / v1.32 / flowcontrol v1beta3",
    "statement_contains": "flowcontrol.apiserver.k8s.io/v1beta3",
    "surface": "flowcontrol.apiserver.k8s.io/v1beta3 FlowSchema PriorityLevelConfiguration",
    "version": "v1.32",
    "relation": "no_longer_served",
}
EXPECTED_F04 = {
    "locator": "Railties / Removals",
    "statement": "Remove deprecated Rails.config.enable_dependency_loading",
    "surface": "Rails.config.enable_dependency_loading",
    "version": "7.2",
    "relation": "removed",
}
EXPECTED_F03C = {
    "section": "Version 2.3.0",
    "date": "2023-04-25",
    "statement": (
        "The FLASK_ENV environment variable, ENV config key, "
        "and app.env property are removed."
    ),
    "surface": "FLASK_ENV; ENV; app.env",
    "version": "2.3.0",
    "relation": "removed",
}


@dataclass(frozen=True)
class CorrectedSpec:
    capture_id: str
    family: str
    capture_url: str
    record_id: str
    entity_kind: str
    raw_name: str


CORRECTED_CAPTURES: tuple[CorrectedSpec, ...] = (
    CorrectedSpec(
        "capE-04c", "E",
        "https://raw.githubusercontent.com/spdx/license-list-data/main/json/details/BSL-1.0.json",
        "BSL-1.0", "license", "raw.json"),
    CorrectedSpec(
        "capE-05c", "E",
        "https://raw.githubusercontent.com/spdx/license-list-data/main/json/details/MPL-2.0.json",
        "MPL-2.0", "license", "raw.json"),
    CorrectedSpec(
        "capE-06c", "E",
        "https://raw.githubusercontent.com/spdx/license-list-data/main/json/details/EPL-2.0.json",
        "EPL-2.0", "license", "raw.json"),
    CorrectedSpec(
        "capF-03c", "F",
        "https://raw.githubusercontent.com/pallets/flask/2.3.0/CHANGES.rst",
        "flask-2.3.0-env-removal", "rst", "raw.rst"),
)

CORRECTED_URLS: frozenset[str] = frozenset(s.capture_url for s in CORRECTED_CAPTURES)


class CaptureRefusal(Exception):
    """Create-once or plan violation."""


class TransportResponse(Protocol):
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]
    redirect_refused: bool


Transport = Callable[[str], TransportResponse]


def canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def module_sha256() -> str:
    return sha256_file(Path(__file__).resolve())


def _to_k3_spec(capture_id: str) -> k3.K3Spec:
    for spec in k3.FROZEN_ATTEMPTS:
        if spec.capture_id == capture_id:
            return spec
    raise CaptureRefusal(f"unknown reconciliation id: {capture_id}")


def _to_k3_license_spec(c: CorrectedSpec) -> k3.K3Spec:
    return k3.K3Spec(c.capture_id, c.family, c.capture_url,
                     c.record_id, c.entity_kind, c.raw_name)


def rel_repo(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)
    if root.exists():
        for p in root.rglob("*"):
            if p.is_file():
                raise CaptureRefusal(
                    f"create-once refusal: artifact already exists: {p}")


def verify_k3_tree_unchanged() -> list[str]:
    """Pin hashes of original K3 tree at reconciliation start."""
    errors: list[str] = []
    if not K3_ROOT.exists():
        return ["missing K3 root"]
    return k3.verify_hashes(K3_ROOT)


def build_reconciliation_plan() -> dict:
    inputs = []
    k3_plan = json.loads((K3_ROOT / "plan.json").read_text())
    for cid in RECON_IDS:
        raw_path = K3_ROOT / "captures" / cid / "raw.html"
        sc_path = K3_ROOT / "captures" / cid / "sidecar.json"
        if not raw_path.exists() or not sc_path.exists():
            raise CaptureRefusal(f"missing K3 inputs for {cid}")
        sc = json.loads(sc_path.read_text())
        inputs.append({
            "capture_id": cid,
            "original_raw_path": rel_repo(raw_path),
            "original_raw_sha256": sha256_file(raw_path),
            "original_sidecar_path": rel_repo(sc_path),
            "original_sidecar_sha256": sha256_file(sc_path),
            "capture_timestamp_utc": sc.get("retrieved_at_utc"),
            "capture_time_verdict": sc.get("capture_verdict"),
        })
    body = {
        "schema_version": SCHEMA_VERSION,
        "phase": "reconciliation",
        "network_calls": 0,
        "inputs": inputs,
        "k3_plan_sha256": k3_plan.get("plan_sha256"),
        "k3_implementation_module_sha256": k3.module_sha256(),
        "reconciliation_module_sha256": module_sha256(),
        "expected": {
            "capF-01": EXPECTED_F01,
            "capF-04": EXPECTED_F04,
        },
        "output_paths": {
            cid: {
                "normalized": f"reconciliation/{cid}/normalized.txt",
                "section": f"reconciliation/{cid}/section.txt",
                "extract": f"reconciliation/{cid}/extract.json",
                "sidecar": f"reconciliation/{cid}/sidecar.json",
            }
            for cid in RECON_IDS
        },
        "seat": SEAT,
    }
    plan = dict(body)
    plan["plan_sha256"] = sha256_bytes(canonical_json(body).encode())
    return plan


def _section_text_for(spec_id: str, normalized: str) -> str:
    if spec_id == "capF-01":
        ra = normalized.find("Removed APIs by release")
        fc = normalized.find("flowcontrol.apiserver.k8s.io/v1beta3")
        return normalized[ra:fc + 400] if ra >= 0 and fc > ra else ""
    if spec_id == "capF-04":
        stmt_pos = normalized.find("Rails.config.enable_dependency_loading")
        rt = max((m.start() for m in re.finditer("Railties", normalized)
                  if m.start() < stmt_pos), default=-1)
        return normalized[rt:stmt_pos + 120] if rt >= 0 and stmt_pos >= 0 else ""
    return ""


def reconcile_one(capture_id: str, plan: dict) -> dict:
    raw_path = K3_ROOT / "captures" / capture_id / "raw.html"
    orig_sc = json.loads(
        (K3_ROOT / "captures" / capture_id / "sidecar.json").read_text())
    raw_bytes = raw_path.read_bytes()
    if sha256_bytes(raw_bytes) != orig_sc.get("raw_sha256"):
        raise CaptureRefusal(f"raw hash mismatch for {capture_id}")

    spec = _to_k3_spec(capture_id)
    verdict, failures, extract = k3.validate_family_f(
        spec, raw_bytes, http_ok=True, redirect_refused=False)
    normalized = k3.normalize_text(k3.html_to_text(raw_bytes))
    section_text = _section_text_for(capture_id, normalized)

    out_dir = RECON_ROOT / capture_id
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("normalized.txt", "section.txt", "extract.json", "sidecar.json"):
        if (out_dir / name).exists():
            raise CaptureRefusal(f"create-once: {out_dir / name}")

    (out_dir / "normalized.txt").write_bytes(normalized.encode("utf-8"))
    (out_dir / "section.txt").write_bytes(section_text.encode("utf-8"))
    extract["capture_id"] = capture_id
    extract["section_text_sha256"] = sha256_bytes(
        section_text.encode("utf-8")) if section_text else None
    (out_dir / "extract.json").write_text(canonical_json(extract) + "\n")

    sidecar = {
        "schema_version": SCHEMA_VERSION,
        "capture_id": capture_id,
        "derived_from_saved_raw": True,
        "capture_time_verdict": orig_sc.get("capture_verdict"),
        "capture_time_failure_reasons": orig_sc.get("failure_reasons", []),
        "reconciliation_verdict": verdict,
        "reconciliation_failure_reasons": failures,
        "original_raw_sha256": orig_sc.get("raw_sha256"),
        "original_raw_path": rel_repo(raw_path),
        "original_capture_timestamp_utc": orig_sc.get("retrieved_at_utc"),
        "k3_plan_sha256": plan.get("k3_plan_sha256"),
        "k3_implementation_module_sha256": plan.get(
            "k3_implementation_module_sha256"),
        "reconciliation_module_sha256": plan.get(
            "reconciliation_module_sha256"),
        "reconciliation_plan_sha256": plan.get("plan_sha256"),
        "normalized_text_sha256": extract.get("normalized_text_sha256"),
        "section_text_sha256": extract.get("section_text_sha256"),
        "extract_summary": {
            k: extract.get(k)
            for k in (
                "locator_method", "heading_anchor", "matched_statement",
                "named_surface", "framework_version", "relation",
            )
        },
        "generated_at_utc": utc_now_iso(),
        "network_calls": 0,
    }
    (out_dir / "sidecar.json").write_text(canonical_json(sidecar) + "\n")
    return sidecar


def execute_reconciliation() -> dict:
    if RECON_ROOT.exists() and any(RECON_ROOT.rglob("*")):
        raise CaptureRefusal("create-once: reconciliation artifacts exist")
    errs = verify_k3_tree_unchanged()
    if errs:
        raise CaptureRefusal(f"K3 tree verification failed: {errs}")
    RECON_ROOT.mkdir(parents=True, exist_ok=True)
    plan = build_reconciliation_plan()
    (RECON_ROOT / "plan.json").write_text(canonical_json(plan) + "\n")
    rows = [reconcile_one(cid, plan) for cid in RECON_IDS]
    report = {
        "schema_version": SCHEMA_VERSION,
        "phase": "reconciliation",
        "network_calls": 0,
        "reconciliation_plan_sha256": plan["plan_sha256"],
        "rows": [{
            "capture_id": r["capture_id"],
            "capture_time_verdict": r["capture_time_verdict"],
            "reconciliation_verdict": r["reconciliation_verdict"],
            "failure_reasons": r["reconciliation_failure_reasons"],
        } for r in rows],
        "generated_at_utc": utc_now_iso(),
        "seat": SEAT,
    }
    (RECON_ROOT / "reconciliation_report.json").write_text(
        canonical_json(report) + "\n")
    return {"mode": "reconcile", "network_calls": 0, "report": report}


def normalize_rst(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if re.match(r'^[-=~^"]+$', line.strip()):
            continue
        lines.append(re.sub(r"`([^`]*)`", r"\1", line))
    return k3.normalize_text("\n".join(lines))


def extract_f03c_rst(rst_bytes: bytes) -> tuple[dict, list[str]]:
    failures: list[str] = []
    raw = rst_bytes.decode("utf-8")
    normalized = normalize_rst(raw)
    section = k3._section_between(
        normalized,
        "Version 2.3.0",
        ("Version 2.2", "Version 2.4", "Version 2.1"),
    )
    bounded = section or ""
    required = EXPECTED_F03C["statement"]
    if section is None:
        failures.append("missing_bounded_section")
    if EXPECTED_F03C["date"] not in bounded:
        failures.append("wrong_official_record_date")
    matched = k3._find_statement(k3._collapse_ws(bounded), required)
    if matched != required:
        failures.append("missing_exact_statement")
    extract = {
        "capture_id": "capF-03c",
        "locator_method": "rst:Version 2.3.0 before next version heading",
        "heading_anchor": "Version 2.3.0",
        "matched_statement": matched,
        "named_surface": EXPECTED_F03C["surface"],
        "framework_version": EXPECTED_F03C["version"],
        "official_record_date": EXPECTED_F03C["date"],
        "relation": EXPECTED_F03C["relation"],
        "normalized_text_sha256": sha256_bytes(normalized.encode("utf-8")),
        "section_text_sha256": sha256_bytes(
            bounded.encode("utf-8")) if bounded else None,
    }
    return extract, failures


def validate_f03c(rst_bytes: bytes, http_ok: bool,
                  redirect_refused: bool) -> tuple[str, list[str], dict]:
    failures: list[str] = []
    if redirect_refused:
        failures.append("redirect_refused")
    if not http_ok:
        failures.append("http_failure")
    extract: dict = {}
    if http_ok and not redirect_refused:
        extract, ext_failures = extract_f03c_rst(rst_bytes)
        failures.extend(ext_failures)
    return ("pass" if not failures else "fail"), failures, extract


@dataclass
class _LiveResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]
    redirect_refused: bool


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def live_transport(url: str) -> _LiveResponse:
    if url not in CORRECTED_URLS:
        raise CaptureRefusal(f"unauthorized URL: {url}")
    opener = urllib.request.build_opener(_RefuseRedirect())
    req = urllib.request.Request(
        url, headers={"Accept": "*/*", "User-Agent": "efc-k3c-capture/1"})
    try:
        with opener.open(req, timeout=120) as resp:
            body = resp.read()
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return _LiveResponse(
                status=resp.status, headers=hdrs, body=body,
                url=resp.geturl(), redirect_chain=[url],
                redirect_refused=False,
            )
    except urllib.error.HTTPError as e:
        body = e.read()
        hdrs = {k.lower(): v for k, v in e.headers.items()}
        redirect = 300 <= e.code < 400
        chain = [url]
        loc = hdrs.get("location")
        if redirect and loc:
            chain.append(loc)
        return _LiveResponse(
            status=e.code, headers=hdrs, body=body, url=url,
            redirect_chain=chain, redirect_refused=redirect,
        )


def build_capture_plan() -> dict:
    entries = []
    for spec in CORRECTED_CAPTURES:
        cdir = CAPTURE_ROOT / spec.capture_id
        row = {
            "id": spec.capture_id,
            "family": spec.family,
            "entity_kind": spec.entity_kind,
            "record_id": spec.record_id,
            "capture_url": spec.capture_url,
            "raw_path": str((cdir / spec.raw_name).relative_to(K3C_ROOT)),
            "sidecar_path": str((cdir / "sidecar.json").relative_to(K3C_ROOT)),
        }
        if spec.capture_id == "capF-03c":
            edir = K3C_ROOT / "extracts" / spec.capture_id
            row["extract_paths"] = {
                "normalized": str((edir / "normalized.txt").relative_to(K3C_ROOT)),
                "section": str((edir / "section.txt").relative_to(K3C_ROOT)),
                "extract": str((edir / "extract.json").relative_to(K3C_ROOT)),
            }
        entries.append(row)
    body = {
        "schema_version": SCHEMA_VERSION,
        "phase": "corrected_capture",
        "attempt_count": len(CORRECTED_CAPTURES),
        "max_network_calls": MAX_CAPTURE_CALLS,
        "redirect_policy": "refuse",
        "retry_policy": "zero",
        "implementation_module_sha256": module_sha256(),
        "entries": entries,
        "expected_f03c": EXPECTED_F03C,
    }
    plan = dict(body)
    plan["plan_sha256"] = sha256_bytes(canonical_json(body).encode())
    return plan


def write_corrected_e(spec: CorrectedSpec, plan_sha: str,
                      resp: TransportResponse) -> dict:
    k3spec = _to_k3_license_spec(spec)
    body = resp.body
    data, parse_err = k3._parse_json(body)
    http_ok = 200 <= resp.status < 300 and not resp.redirect_refused
    verdict, failures, meta = k3.validate_family_e(
        k3spec, data, http_ok, parse_err, resp.redirect_refused)
    cdir = CAPTURE_ROOT / spec.capture_id
    cdir.mkdir(parents=True, exist_ok=True)
    raw_path = cdir / spec.raw_name
    sc_path = cdir / "sidecar.json"
    if raw_path.exists() or sc_path.exists():
        raise CaptureRefusal(f"create-once: {cdir}")
    raw_path.write_bytes(body)
    sidecar = {
        "schema_version": SCHEMA_VERSION,
        "capture_id": spec.capture_id,
        "oracle_id": f"efc-calibration-{spec.capture_id}",
        "family": spec.family,
        "entity_kind": spec.entity_kind,
        "record_id_expected": spec.record_id,
        "capture_url": spec.capture_url,
        "final_url": resp.url,
        "redirect_chain": list(resp.redirect_chain),
        "redirect_refused": resp.redirect_refused,
        "retrieved_at_utc": utc_now_iso(),
        "http_status": resp.status,
        "content_type": resp.headers.get("content-type"),
        "raw_sha256": sha256_bytes(body),
        "raw_byte_length": len(body),
        "capture_plan_sha256": plan_sha,
        "implementation_module_sha256": module_sha256(),
        "capture_verdict": verdict,
        "failure_reasons": failures,
        **meta,
    }
    sc_path.write_text(canonical_json(sidecar) + "\n")
    return sidecar


def write_corrected_f03c(spec: CorrectedSpec, plan_sha: str,
                         resp: TransportResponse) -> dict:
    body = resp.body
    http_ok = 200 <= resp.status < 300 and not resp.redirect_refused
    verdict, failures, extract = validate_f03c(
        body, http_ok, resp.redirect_refused)
    cdir = CAPTURE_ROOT / spec.capture_id
    edir = K3C_ROOT / "extracts" / spec.capture_id
    cdir.mkdir(parents=True, exist_ok=True)
    edir.mkdir(parents=True, exist_ok=True)
    paths = [cdir / spec.raw_name, cdir / "sidecar.json",
             edir / "normalized.txt", edir / "section.txt", edir / "extract.json"]
    for p in paths:
        if p.exists():
            raise CaptureRefusal(f"create-once: {p}")
    raw_path = cdir / spec.raw_name
    raw_path.write_bytes(body)
    if http_ok and not resp.redirect_refused:
        normalized = normalize_rst(body.decode("utf-8"))
        section = k3._section_between(
            normalized, "Version 2.3.0",
            ("Version 2.2", "Version 2.4", "Version 2.1")) or ""
        (edir / "normalized.txt").write_bytes(normalized.encode("utf-8"))
        (edir / "section.txt").write_bytes(section.encode("utf-8"))
        (edir / "extract.json").write_text(canonical_json(extract) + "\n")
    else:
        for name in ("normalized.txt", "section.txt"):
            (edir / name).write_bytes(b"")
        (edir / "extract.json").write_text(
            canonical_json({"capture_id": spec.capture_id}) + "\n")
    sidecar = {
        "schema_version": SCHEMA_VERSION,
        "capture_id": spec.capture_id,
        "oracle_id": f"efc-calibration-{spec.capture_id}",
        "family": spec.family,
        "entity_kind": spec.entity_kind,
        "record_id_expected": spec.record_id,
        "capture_url": spec.capture_url,
        "final_url": resp.url,
        "redirect_chain": list(resp.redirect_chain),
        "redirect_refused": resp.redirect_refused,
        "retrieved_at_utc": utc_now_iso(),
        "http_status": resp.status,
        "content_type": resp.headers.get("content-type"),
        "raw_sha256": sha256_bytes(body),
        "raw_byte_length": len(body),
        "capture_plan_sha256": plan_sha,
        "implementation_module_sha256": module_sha256(),
        "capture_verdict": verdict,
        "failure_reasons": failures,
        "extract_summary": {
            k: extract.get(k)
            for k in (
                "locator_method", "heading_anchor", "matched_statement",
                "named_surface", "framework_version", "relation",
                "official_record_date", "normalized_text_sha256",
                "section_text_sha256",
            )
        },
    }
    (cdir / "sidecar.json").write_text(canonical_json(sidecar) + "\n")
    return sidecar


def execute_capture(transport: Transport | None = None) -> dict:
    capture_marker = K3C_ROOT / "capture_plan.json"
    if capture_marker.exists():
        raise CaptureRefusal("create-once: capture already executed")
    K3C_ROOT.mkdir(parents=True, exist_ok=True)
    CAPTURE_ROOT.mkdir(parents=True, exist_ok=True)
    plan = build_capture_plan()
    (K3C_ROOT / "capture_plan.json").write_text(canonical_json(plan) + "\n")
    plan_sha = plan["plan_sha256"]
    transport = transport or live_transport
    results: list[dict] = []
    call_count = 0
    for spec in CORRECTED_CAPTURES:
        resp = transport(spec.capture_url)
        call_count += 1
        if spec.family == "E":
            sc = write_corrected_e(spec, plan_sha, resp)
        else:
            sc = write_corrected_f03c(spec, plan_sha, resp)
        results.append({"id": spec.capture_id, "verdict": sc["capture_verdict"]})
    report = {
        "schema_version": SCHEMA_VERSION,
        "phase": "corrected_capture",
        "network_calls": call_count,
        "max_network_calls": MAX_CAPTURE_CALLS,
        "plan_sha256": plan_sha,
        "attempts": results,
        "generated_at_utc": utc_now_iso(),
        "seat": SEAT,
    }
    (K3C_ROOT / "capture_report.json").write_text(canonical_json(report) + "\n")
    return {"mode": "capture", "network_calls": call_count,
            "results": results, "report": report}


def _slot_source_verdict(slot: str) -> tuple[str, str, str, bool]:
    """Return (source_id, source_kind, verdict, promotion_eligible)."""
    if slot == "E01":
        sc = json.loads((K3_ROOT / "captures/capE-01/sidecar.json").read_text())
        return "capE-01", "k3_original", sc["capture_verdict"], sc["capture_verdict"] == "pass"
    if slot == "E02":
        sc = json.loads((K3_ROOT / "captures/capE-02/sidecar.json").read_text())
        return "capE-02", "k3_original", sc["capture_verdict"], sc["capture_verdict"] == "pass"
    if slot == "E03":
        sc = json.loads((K3_ROOT / "captures/capE-03/sidecar.json").read_text())
        return "capE-03", "k3_original", sc["capture_verdict"], sc["capture_verdict"] == "pass"
    if slot == "E04":
        sc = json.loads((CAPTURE_ROOT / "capE-04c/sidecar.json").read_text())
        return "capE-04c", "k3c_corrected", sc["capture_verdict"], sc["capture_verdict"] == "pass"
    if slot == "E05":
        sc = json.loads((CAPTURE_ROOT / "capE-05c/sidecar.json").read_text())
        return "capE-05c", "k3c_corrected", sc["capture_verdict"], sc["capture_verdict"] == "pass"
    if slot == "E06":
        sc = json.loads((CAPTURE_ROOT / "capE-06c/sidecar.json").read_text())
        return "capE-06c", "k3c_corrected", sc["capture_verdict"], sc["capture_verdict"] == "pass"
    if slot == "F01":
        sc = json.loads((RECON_ROOT / "capF-01/sidecar.json").read_text())
        v = sc["reconciliation_verdict"]
        return "capF-01", "k3c_reconciled", v, v == "pass"
    if slot == "F02":
        sc = json.loads((K3_ROOT / "captures/capF-02/sidecar.json").read_text())
        return "capF-02", "k3_original", sc["capture_verdict"], sc["capture_verdict"] == "pass"
    if slot == "F03":
        sc = json.loads((CAPTURE_ROOT / "capF-03c/sidecar.json").read_text())
        return "capF-03c", "k3c_corrected", sc["capture_verdict"], sc["capture_verdict"] == "pass"
    if slot == "F04":
        sc = json.loads((RECON_ROOT / "capF-04/sidecar.json").read_text())
        v = sc["reconciliation_verdict"]
        return "capF-04", "k3c_reconciled", v, v == "pass"
    raise CaptureRefusal(f"unknown slot {slot}")


def _artifact_hashes(source_id: str, source_kind: str) -> dict:
    if source_kind == "k3_original":
        base = K3_ROOT / "captures" / source_id
        raw_name = "raw.json" if source_id.startswith("capE") else "raw.html"
    elif source_kind == "k3c_corrected":
        base = CAPTURE_ROOT / source_id
        raw_name = "raw.json" if source_id.startswith("capE") else "raw.rst"
    else:
        base = RECON_ROOT / source_id
        raw_name = "normalized.txt"  # reconciled uses k3 raw path reference
    raw_path = base / raw_name if source_kind != "k3c_reconciled" else (
        K3_ROOT / "captures" / source_id / "raw.html")
    sc_path = base / "sidecar.json"
    out = {
        "sidecar_sha256": sha256_file(sc_path) if sc_path.exists() else None,
        "raw_sha256": sha256_file(raw_path) if raw_path.exists() else None,
    }
    return out


def build_promotion_ledger() -> dict:
    mappings = []
    for slot in LOGICAL_SLOTS:
        sid, kind, verdict, eligible = _slot_source_verdict(slot)
        mappings.append({
            "logical_slot": slot,
            "source_capture_id": sid,
            "source_kind": kind,
            "qualification_verdict": verdict,
            "promotion_eligible": eligible,
            "artifact_hashes": _artifact_hashes(sid, kind),
        })
    superseded = []
    for cid in K3_SUPERSEDED_INELIGIBLE:
        sc_path = K3_ROOT / "captures" / cid / (
            "raw.json" if cid.startswith("capE") else "raw.html")
        sidecar_path = K3_ROOT / "captures" / cid / "sidecar.json"
        sc = json.loads(sidecar_path.read_text())
        superseded.append({
            "capture_id": cid,
            "capture_verdict": sc.get("capture_verdict"),
            "promotion_eligible": False,
            "reason": "superseded_k3_failed_attempt",
            "sidecar_sha256": sha256_file(sidecar_path),
            "raw_sha256": sc.get("raw_sha256"),
        })
    e_pass = sum(1 for m in mappings if m["logical_slot"].startswith("E")
                   and m["promotion_eligible"])
    f_pass = sum(1 for m in mappings if m["logical_slot"].startswith("F")
                   and m["promotion_eligible"])
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "logical_slot_mappings": mappings,
        "superseded_ineligible": superseded,
        "family_e_pass_count": e_pass,
        "family_f_pass_count": f_pass,
        "k3_closed": e_pass == 6 and f_pass == 4,
        "generated_at_utc": utc_now_iso(),
        "seat": SEAT,
    }
    return ledger


def write_promotion_ledger() -> dict:
    path = K3C_ROOT / "promotion_ledger.json"
    if path.exists():
        raise CaptureRefusal("create-once: promotion_ledger exists")
    ledger = build_promotion_ledger()
    path.write_text(canonical_json(ledger) + "\n")
    return ledger


def execute_all(transport: Transport | None = None) -> dict:
    recon = execute_reconciliation()
    cap = execute_capture(transport=transport)
    ledger = write_promotion_ledger()
    return {
        "mode": "execute_all",
        "reconciliation_network_calls": 0,
        "capture_network_calls": cap["network_calls"],
        "reconciliation": recon,
        "capture": cap,
        "promotion_ledger": ledger,
    }


def verify_all() -> list[str]:
    errors = verify_k3_tree_unchanged()
    if RECON_ROOT.exists():
        for cid in RECON_IDS:
            raw_k3 = K3_ROOT / "captures" / cid / "raw.html"
            sc = json.loads((RECON_ROOT / cid / "sidecar.json").read_text())
            if sha256_file(raw_k3) != sc.get("original_raw_sha256"):
                errors.append(f"recon raw pin mismatch {cid}")
    if CAPTURE_ROOT.exists():
        for spec in CORRECTED_CAPTURES:
            if spec.family == "E":
                rp = CAPTURE_ROOT / spec.capture_id / spec.raw_name
                sc = json.loads((CAPTURE_ROOT / spec.capture_id /
                                 "sidecar.json").read_text())
                if sha256_file(rp) != sc.get("raw_sha256"):
                    errors.append(f"corrected raw hash {spec.capture_id}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EFC K3c reconciliation + capture")
    parser.add_argument("--reconcile-dry-run", action="store_true")
    parser.add_argument("--reconcile", action="store_true")
    parser.add_argument("--capture-dry-run", action="store_true")
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--execute", action="store_true",
                        help="reconcile then capture then ledger")
    parser.add_argument("--verify-all", action="store_true")
    args = parser.parse_args(argv)

    if args.verify_all:
        errs = verify_all()
        if errs:
            for e in errs:
                print(e, file=sys.stderr)
            return 1
        print("all K3+K3c verification passed")
        return 0

    if args.reconcile_dry_run:
        print(canonical_json({
            "mode": "reconcile_dry_run",
            "plan": build_reconciliation_plan(),
            "network_calls": 0,
        }))
        return 0

    if args.capture_dry_run:
        print(canonical_json({
            "mode": "capture_dry_run",
            "plan": build_capture_plan(),
            "network_calls": 0,
        }))
        return 0

    try:
        if args.execute:
            print(canonical_json(execute_all()))
            return 0
        if args.reconcile:
            print(canonical_json(execute_reconciliation()))
            return 0
        if args.capture:
            print(canonical_json(execute_capture()))
            return 0
    except CaptureRefusal as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
