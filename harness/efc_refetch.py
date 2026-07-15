"""EFC v0 G1 independent K1 refetch verification — pre-pin acquisition QC only.

One GET per closed K1 final source URL, zero retries, no search, no substitution.
Does not modify harness/efc_capture.py or its K1 acquisition artifacts.
Writes create-once artifacts under corpus/efc_calibration/_acquisition/k1/refetch/.

Usage:
  python -m harness.efc_refetch              # dry-run: print plan, zero network
  python -m harness.efc_refetch --execute    # one live run (create-once)
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from harness.efc_capture import (
    CaptureRefusal,
    _extract_github_range_paths,
    _extract_osv_range_paths,
    _package_ecosystem_github,
    _package_ecosystem_osv,
    _parse_json,
    _publication_field,
    _record_id_from_payload,
    _withdrawn_present,
    canonical_json,
    ecosystems_match,
    normalize_ecosystem,
    sha256_bytes,
    sha256_file,
    utc_now_iso,
)

REPO = Path(__file__).resolve().parent.parent
K1_ROOT = REPO / "corpus" / "efc_calibration" / "_acquisition" / "k1"
REFETCH_ROOT = K1_ROOT / "refetch"
SCHEMA_VERSION = "efc-k1-refetch-v1"
SEAT = "cursor/grok-4.5"

AMENDMENT_PATH = K1_ROOT / "normalization_amendment.json"
RECONCILED_REPORT_PATH = K1_ROOT / "capture_report.reconciled.json"
PLAN_PATH = K1_ROOT / "plan.json"
REFETCH_REPORT_PATH = K1_ROOT / "refetch_report.json"


@dataclass(frozen=True)
class RefetchSpec:
    capture_id: str
    capture_url: str
    record_id_expected: str
    package_expected: str
    ecosystem_expected: str


# Exactly the twelve final K1 sources authorized by Assignment G1.
G1_SOURCES: tuple[RefetchSpec, ...] = (
    RefetchSpec("capA-01", "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0002",
                "RUSTSEC-2026-0002", "lru", "crates.io"),
    RefetchSpec("capA-02", "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0038",
                "RUSTSEC-2026-0038", "rssn", "crates.io"),
    RefetchSpec("capA-03", "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0186",
                "RUSTSEC-2026-0186", "memmap2", "crates.io"),
    RefetchSpec("capA-04", "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0190",
                "RUSTSEC-2026-0190", "anyhow", "crates.io"),
    RefetchSpec("capA-05", "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0185",
                "RUSTSEC-2026-0185", "quinn-proto", "crates.io"),
    RefetchSpec("capA-06", "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0072",
                "RUSTSEC-2026-0072", "hpke-rs-rust-crypto", "crates.io"),
    RefetchSpec("capB-01", "https://api.github.com/advisories/GHSA-25h7-pfq9-p65f",
                "GHSA-25h7-pfq9-p65f", "flatted", "npm"),
    RefetchSpec("capB-02", "https://api.github.com/advisories/GHSA-pmch-g965-grmr",
                "GHSA-pmch-g965-grmr", "langroid", "PyPI"),
    RefetchSpec("capB-03", "https://api.github.com/advisories/GHSA-mf9w-mj56-hr94",
                "GHSA-mf9w-mj56-hr94", "python-dotenv", "PyPI"),
    RefetchSpec("capB-04", "https://api.github.com/advisories/GHSA-w7jw-789q-3m8p",
                "GHSA-w7jw-789q-3m8p", "shell-quote", "npm"),
    RefetchSpec("capB-05", "https://api.github.com/advisories/GHSA-r5fr-rjxr-66jc",
                "GHSA-r5fr-rjxr-66jc", "lodash", "npm"),
    RefetchSpec("capB-06", "https://api.github.com/advisories/GHSA-37w4-hwhx-4rc4",
                "GHSA-37w4-hwhx-4rc4", "jupyterlab", "PyPI"),
)

G1_URLS = frozenset(s.capture_url for s in G1_SOURCES)
G1_IDS = tuple(s.capture_id for s in G1_SOURCES)


@dataclass
class TransportResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]


Transport = Callable[[str], TransportResponse]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return urllib.request.Request(newurl, headers=req.headers,
                                      method=req.get_method())


def refuse_unknown_url(url: str) -> None:
    if url not in G1_URLS:
        raise CaptureRefusal(f"unknown or unauthorized G1 URL: {url}")


def live_transport(url: str) -> TransportResponse:
    refuse_unknown_url(url)
    chain: list[str] = [url]
    opener = urllib.request.build_opener(_NoRedirect())
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "efc-k1-refetch/1",
        },
    )
    current = req
    while True:
        try:
            with opener.open(current, timeout=120) as resp:
                body = resp.read()
                final_url = resp.geturl()
                if final_url not in chain:
                    chain.append(final_url)
                hdrs = {k.lower(): v for k, v in resp.headers.items()}
                return TransportResponse(
                    status=resp.status, headers=hdrs, body=body,
                    url=final_url, redirect_chain=chain)
        except urllib.error.HTTPError as e:
            body = e.read()
            hdrs = {k.lower(): v for k, v in e.headers.items()}
            if e.code in (301, 302, 303, 307, 308) and "location" in hdrs:
                nxt = hdrs["location"]
                if nxt not in chain:
                    chain.append(nxt)
                current = urllib.request.Request(
                    nxt,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "efc-k1-refetch/1",
                    },
                )
                continue
            return TransportResponse(
                status=e.code, headers=hdrs, body=body,
                url=chain[-1], redirect_chain=chain)


def original_capture_dir(capture_id: str) -> Path:
    return K1_ROOT / "captures" / capture_id


def refetch_dir(capture_id: str, root: Path = REFETCH_ROOT) -> Path:
    return root / capture_id


def load_amendment(root: Path = K1_ROOT) -> dict:
    path = root / "normalization_amendment.json"
    if not path.exists():
        raise CaptureRefusal("missing normalization_amendment.json")
    return json.loads(path.read_text())


def load_pinned_original_raw_sha(amendment: dict, capture_id: str) -> str:
    pins = amendment["pinned_original_artifacts"]["raw_sha256"]
    if capture_id not in pins:
        raise CaptureRefusal(f"amendment missing raw_sha256 for {capture_id}")
    return pins[capture_id]


def extract_identity_fields(body: bytes, capture_url: str) -> dict:
    """Bounded identity/date/withdrawal/range fields for drift notes."""
    is_github = capture_url.startswith("https://api.github.com/")
    data, parse_err = _parse_json(body)
    if data is None:
        return {
            "parse_error": parse_err,
            "record_id": None,
            "package": None,
            "ecosystem": None,
            "ecosystem_normalized": None,
            "published": None,
            "withdrawn": None,
            "affected_range_fields": [],
        }
    if is_github:
        pkg, eco = _package_ecosystem_github(data)
        ranges = _extract_github_range_paths(data)
    else:
        pkg, eco = _package_ecosystem_osv(data)
        ranges = _extract_osv_range_paths(data)
    return {
        "parse_error": None,
        "record_id": _record_id_from_payload(data, is_github),
        "package": pkg,
        "ecosystem": eco,
        "ecosystem_normalized": normalize_ecosystem(eco) if eco else None,
        "published": _publication_field(data, is_github),
        "withdrawn": _withdrawn_present(data, is_github),
        "affected_range_fields": ranges,
    }


def field_level_diff(original: dict, refetch: dict) -> list[dict]:
    """Bounded diff over identity/date/withdrawal/range fields only."""
    diffs: list[dict] = []
    for key in ("record_id", "package", "ecosystem", "ecosystem_normalized",
                "published", "withdrawn"):
        if original.get(key) != refetch.get(key):
            diffs.append({
                "field": key,
                "original": original.get(key),
                "refetch": refetch.get(key),
            })
    orig_ranges = original.get("affected_range_fields") or []
    ref_ranges = refetch.get("affected_range_fields") or []
    if orig_ranges != ref_ranges:
        diffs.append({
            "field": "affected_range_fields",
            "original": orig_ranges,
            "refetch": ref_ranges,
        })
    return diffs


def verify_identity_against_expected(spec: RefetchSpec, fields: dict) -> list[str]:
    """Non-repair notes: confirm returned identity fields vs closed nomination."""
    notes: list[str] = []
    if fields.get("record_id") != spec.record_id_expected:
        notes.append("record_id_mismatch")
    if fields.get("package") != spec.package_expected:
        notes.append("package_mismatch")
    if not ecosystems_match(spec.ecosystem_expected, fields.get("ecosystem")):
        notes.append("ecosystem_mismatch")
    if fields.get("withdrawn"):
        notes.append("withdrawn")
    return notes


def check_refetch_create_once(refetch_root: Path, report_path: Path) -> None:
    if report_path.exists():
        raise CaptureRefusal(
            f"create-once refusal: artifact already exists: {report_path}")
    if refetch_root.exists():
        for p in refetch_root.rglob("*"):
            if p.is_file():
                raise CaptureRefusal(
                    f"create-once refusal: artifact already exists: {p}")


def build_refetch_sidecar(spec: RefetchSpec, resp: TransportResponse,
                          body: bytes, original_raw_sha: str,
                          original_fields: dict, refetch_fields: dict,
                          content_identity: str,
                          field_diffs: list[dict],
                          identity_notes: list[str],
                          amendment_sha: str,
                          reconciled_report_sha: str,
                          plan_sha: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "capture_id": spec.capture_id,
        "capture_url": spec.capture_url,
        "final_url": resp.url,
        "redirect_chain": list(resp.redirect_chain),
        "retrieved_at_utc": utc_now_iso(),
        "http_status": resp.status,
        "content_type": resp.headers.get("content-type"),
        "raw_sha256": sha256_bytes(body),
        "raw_byte_length": len(body),
        "original_raw_sha256": original_raw_sha,
        "content_identity": content_identity,
        "record_id_expected": spec.record_id_expected,
        "package_expected": spec.package_expected,
        "ecosystem_expected": spec.ecosystem_expected,
        "record_id_returned": refetch_fields.get("record_id"),
        "package_returned": refetch_fields.get("package"),
        "ecosystem_returned": refetch_fields.get("ecosystem"),
        "ecosystem_normalized": refetch_fields.get("ecosystem_normalized"),
        "published": refetch_fields.get("published"),
        "withdrawn": refetch_fields.get("withdrawn"),
        "affected_range_fields": refetch_fields.get("affected_range_fields"),
        "identity_notes": identity_notes,
        "field_diffs": field_diffs,
        "original_identity_fields": original_fields,
        "refetch_identity_fields": refetch_fields,
        "pinned_plan_sha256": plan_sha,
        "pinned_amendment_sha256": amendment_sha,
        "pinned_reconciled_report_sha256": reconciled_report_sha,
        "disclaimer": (
            "independent refetch verification only; dated drift note is not a "
            "repair; no fixture, oracle, engine, or mechanism claim"),
    }


def write_refetch_pair(spec: RefetchSpec, resp: TransportResponse,
                       original_raw_sha: str, original_body: bytes,
                       amendment_sha: str, reconciled_report_sha: str,
                       plan_sha: str, root: Path = REFETCH_ROOT) -> dict:
    adir = refetch_dir(spec.capture_id, root)
    adir.mkdir(parents=True, exist_ok=True)
    raw_path = adir / "raw.json"
    sidecar_path = adir / "sidecar.json"
    if raw_path.exists() or sidecar_path.exists():
        raise CaptureRefusal(f"create-once refusal: {adir} not empty")

    body = resp.body
    refetch_sha = sha256_bytes(body)
    content_identity = "exact" if refetch_sha == original_raw_sha else "drift"

    original_fields = extract_identity_fields(original_body, spec.capture_url)
    refetch_fields = extract_identity_fields(body, spec.capture_url)
    field_diffs = (
        [] if content_identity == "exact"
        else field_level_diff(original_fields, refetch_fields)
    )
    identity_notes = verify_identity_against_expected(spec, refetch_fields)

    raw_path.write_bytes(body)
    sidecar = build_refetch_sidecar(
        spec, resp, body, original_raw_sha, original_fields, refetch_fields,
        content_identity, field_diffs, identity_notes,
        amendment_sha, reconciled_report_sha, plan_sha,
    )
    sidecar_path.write_text(canonical_json(sidecar) + "\n")
    return sidecar


def build_refetch_report(rows: list[dict], amendment: dict,
                         amendment_file_sha: str,
                         amendment_payload_sha: str,
                         reconciled_report_sha: str,
                         plan_file_sha: str,
                         network_calls: int) -> dict:
    pins = amendment["pinned_original_artifacts"]
    return {
        "schema_version": SCHEMA_VERSION,
        "assignment": "G1",
        "seat": SEAT,
        "generated_at_utc": utc_now_iso(),
        "network_calls": network_calls,
        "source_count": len(rows),
        "pinned_plan_sha256": pins["plan_sha256"],
        "plan_file_sha256": plan_file_sha,
        "pinned_amendment_payload_sha256": amendment_payload_sha,
        "amendment_file_sha256": amendment_file_sha,
        "pinned_reconciled_report_sha256": reconciled_report_sha,
        "pinned_original_capture_report_sha256": pins["capture_report_sha256"],
        "ecosystem_mapping": amendment.get("ecosystem_mapping"),
        "rows": rows,
        "content_identity_counts": {
            "exact": sum(1 for r in rows if r.get("content_identity") == "exact"),
            "drift": sum(1 for r in rows if r.get("content_identity") == "drift"),
        },
        "disclaimer": (
            "independent refetch verification only; exact byte drift is typed, "
            "not repaired; no fixture, packet, oracle, engine, or mechanism claim"),
    }


def dry_run() -> dict:
    amendment = load_amendment()
    return {
        "mode": "dry_run",
        "network_calls": 0,
        "source_count": len(G1_SOURCES),
        "sources": [
            {
                "capture_id": s.capture_id,
                "capture_url": s.capture_url,
                "original_raw_sha256": load_pinned_original_raw_sha(
                    amendment, s.capture_id),
            }
            for s in G1_SOURCES
        ],
    }


def execute_live(transport: Transport | None = None,
                 refetch_root: Path | None = None,
                 k1_root: Path | None = None,
                 report_path: Path | None = None,
                 captures_root: Path | None = None) -> dict:
    refetch_root = refetch_root or REFETCH_ROOT
    k1_root = k1_root or K1_ROOT
    report_path = report_path or (k1_root / "refetch_report.json")
    captures_root = captures_root or (k1_root / "captures")

    check_refetch_create_once(refetch_root, report_path)

    amendment = load_amendment(k1_root)
    amendment_file_sha = sha256_file(k1_root / "normalization_amendment.json")
    amendment_payload_sha = sha256_bytes(canonical_json(amendment).encode())
    reconciled_report_sha = sha256_file(k1_root / "capture_report.reconciled.json")
    plan_file_sha = sha256_file(k1_root / "plan.json")
    pins = amendment["pinned_original_artifacts"]

    if plan_file_sha != pins["plan_sha256"]:
        raise CaptureRefusal(
            f"plan file hash mismatch: {plan_file_sha} != {pins['plan_sha256']}")

    for cap_id in G1_IDS:
        expected = pins["raw_sha256"][cap_id]
        actual = sha256_file(captures_root / cap_id / "raw.json")
        if actual != expected:
            raise CaptureRefusal(
                f"original raw hash changed before refetch: {cap_id}")

    transport = transport or live_transport
    refetch_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for spec in G1_SOURCES:
        original_raw_sha = load_pinned_original_raw_sha(amendment, spec.capture_id)
        original_body = (captures_root / spec.capture_id / "raw.json").read_bytes()
        resp = transport(spec.capture_url)
        sidecar = write_refetch_pair(
            spec, resp, original_raw_sha, original_body,
            amendment_file_sha, reconciled_report_sha, pins["plan_sha256"],
            root=refetch_root,
        )
        rows.append({
            "capture_id": spec.capture_id,
            "capture_url": spec.capture_url,
            "http_status": sidecar["http_status"],
            "original_raw_sha256": sidecar["original_raw_sha256"],
            "refetch_raw_sha256": sidecar["raw_sha256"],
            "content_identity": sidecar["content_identity"],
            "identity_notes": sidecar["identity_notes"],
            "field_diffs": sidecar["field_diffs"],
            "record_id_returned": sidecar["record_id_returned"],
            "package_returned": sidecar["package_returned"],
            "ecosystem_returned": sidecar["ecosystem_returned"],
            "ecosystem_normalized": sidecar["ecosystem_normalized"],
            "published": sidecar["published"],
            "withdrawn": sidecar["withdrawn"],
        })

    report = build_refetch_report(
        rows, amendment, amendment_file_sha, amendment_payload_sha,
        reconciled_report_sha, plan_file_sha, network_calls=len(G1_SOURCES),
    )
    if report_path.exists():
        raise CaptureRefusal(
            f"create-once refusal: {report_path} already exists")
    report_path.write_text(canonical_json(report) + "\n")

    errors = verify_refetch_hashes(refetch_root)
    if errors:
        raise CaptureRefusal(f"refetch hash verification failed: {errors}")

    return {
        "mode": "execute",
        "network_calls": len(G1_SOURCES),
        "report_sha256": sha256_file(report_path),
        "content_identity_counts": report["content_identity_counts"],
        "rows": rows,
    }


def verify_refetch_hashes(root: Path = REFETCH_ROOT) -> list[str]:
    errors: list[str] = []
    for raw_path in sorted(root.rglob("raw.json")):
        sidecar_path = raw_path.parent / "sidecar.json"
        if not sidecar_path.exists():
            errors.append(f"missing sidecar for {raw_path}")
            continue
        sc = json.loads(sidecar_path.read_text())
        expected = sc.get("raw_sha256")
        actual = sha256_file(raw_path)
        if expected != actual:
            errors.append(f"hash mismatch {raw_path}: {expected} != {actual}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EFC G1 independent K1 refetch")
    parser.add_argument("--execute", action="store_true",
                        help="one live create-once refetch of the twelve sources")
    args = parser.parse_args(argv)

    try:
        if args.execute:
            out = execute_live()
        else:
            out = dry_run()
    except CaptureRefusal as e:
        print(f"REFUSAL: {e}", file=sys.stderr)
        return 2

    print(canonical_json(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
