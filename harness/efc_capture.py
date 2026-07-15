"""EFC v0 K1 mechanical snapshot capture — pre-pin acquisition QC only.

Deterministic acquisition of fifteen frozen HTTP GET attempts (eight released
canonical captures + seven quarantined RustSec qualification fetches) under
substrate assignment from codex/gpt-5.6-sol. No calibration engine contact,
no search, no retry, no substitution.

Usage:
  python -m harness.efc_capture              # dry-run: print plan, zero network
  python -m harness.efc_capture --execute    # one live run (create-once)
  python -m harness.efc_capture --reconcile # offline K1c derived reconciliation
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

REPO = Path(__file__).resolve().parent.parent
K1_ROOT = REPO / "corpus" / "efc_calibration" / "_acquisition" / "k1"
SCHEMA_VERSION = "efc-k1-acquisition-v1"

# ---------------------------------------------------------------------------
# Frozen plan — exactly fifteen attempts, no other URLs authorized.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CaptureSpec:
    capture_id: str
    record_id: str
    discovery_url: str
    capture_url: str
    package_expected: str
    ecosystem_expected: str
    kind: str  # "capture" | "qa"


CANONICAL_CAPTURES: tuple[CaptureSpec, ...] = (
    CaptureSpec("capA-02", "RUSTSEC-2026-0038",
                "https://rustsec.org/advisories/RUSTSEC-2026-0038.html",
                "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0038",
                "rssn", "crates.io", "capture"),
    CaptureSpec("capA-04", "RUSTSEC-2026-0190",
                "https://rustsec.org/advisories/RUSTSEC-2026-0190.html",
                "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0190",
                "anyhow", "crates.io", "capture"),
    CaptureSpec("capB-01", "GHSA-25h7-pfq9-p65f",
                "https://github.com/advisories/GHSA-25h7-pfq9-p65f",
                "https://api.github.com/advisories/GHSA-25h7-pfq9-p65f",
                "flatted", "npm", "capture"),
    CaptureSpec("capB-02", "GHSA-pmch-g965-grmr",
                "https://github.com/advisories/GHSA-pmch-g965-grmr",
                "https://api.github.com/advisories/GHSA-pmch-g965-grmr",
                "langroid", "PyPI", "capture"),
    CaptureSpec("capB-03", "GHSA-mf9w-mj56-hr94",
                "https://github.com/advisories/GHSA-mf9w-mj56-hr94",
                "https://api.github.com/advisories/GHSA-mf9w-mj56-hr94",
                "python-dotenv", "PyPI", "capture"),
    CaptureSpec("capB-04", "GHSA-w7jw-789q-3m8p",
                "https://github.com/advisories/GHSA-w7jw-789q-3m8p",
                "https://api.github.com/advisories/GHSA-w7jw-789q-3m8p",
                "shell-quote", "npm", "capture"),
    CaptureSpec("capB-05", "GHSA-r5fr-rjxr-66jc",
                "https://github.com/advisories/GHSA-r5fr-rjxr-66jc",
                "https://api.github.com/advisories/GHSA-r5fr-rjxr-66jc",
                "lodash", "npm", "capture"),
    CaptureSpec("capB-06", "GHSA-37w4-hwhx-4rc4",
                "https://github.com/advisories/GHSA-37w4-hwhx-4rc4",
                "https://api.github.com/advisories/GHSA-37w4-hwhx-4rc4",
                "jupyterlab", "PyPI", "capture"),
)

QA_ATTEMPTS: tuple[CaptureSpec, ...] = (
    CaptureSpec("qaA-lru", "RUSTSEC-2026-0002",
                "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0002",
                "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0002",
                "lru", "crates.io", "qa"),
    CaptureSpec("qaA-memmap2", "RUSTSEC-2026-0186",
                "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0186",
                "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0186",
                "memmap2", "crates.io", "qa"),
    CaptureSpec("qaA-quinn-proto", "RUSTSEC-2026-0185",
                "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0185",
                "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0185",
                "quinn-proto", "crates.io", "qa"),
    CaptureSpec("qaA-hpke-rs-rust-crypto", "RUSTSEC-2026-0072",
                "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0072",
                "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0072",
                "hpke-rs-rust-crypto", "crates.io", "qa"),
    CaptureSpec("qaA-crossbeam-epoch", "RUSTSEC-2026-0204",
                "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0204",
                "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0204",
                "crossbeam-epoch", "crates.io", "qa"),
    CaptureSpec("qaA-hickory-proto", "RUSTSEC-2026-0119",
                "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0119",
                "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0119",
                "hickory-proto", "crates.io", "qa"),
    CaptureSpec("qaA-enum-map", "RUSTSEC-2026-0019",
                "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0019",
                "https://api.osv.dev/v1/vulns/RUSTSEC-2026-0019",
                "enum-map", "crates.io", "qa"),
)

FROZEN_ATTEMPTS: tuple[CaptureSpec, ...] = CANONICAL_CAPTURES + QA_ATTEMPTS
FROZEN_URLS: frozenset[str] = frozenset(s.capture_url for s in FROZEN_ATTEMPTS)

PROMOTION_ORIGINALS = ("qaA-lru", "qaA-memmap2", "qaA-quinn-proto",
                       "qaA-hpke-rs-rust-crypto")
PROMOTION_FALLBACKS = ("qaA-enum-map", "qaA-hickory-proto", "qaA-crossbeam-epoch")
PROMOTION_TARGETS = ("capA-01", "capA-03", "capA-05", "capA-06")
RESERVED_PACKAGES = frozenset({"rssn", "anyhow"})

FINAL_CAPTURE_IDS: tuple[str, ...] = tuple(
    f"capA-0{i}" for i in range(1, 7)
) + tuple(f"capB-0{i}" for i in range(1, 7))

AMENDMENT_ID = "efc-k1-normalization-v1"
FINITE_BOUND_RULE_ID = "github-vrange-finite-upper-v1"
RECONCILER_SEAT = "cursor/composer-2.5-capture"

_DERIVED_ARTIFACTS = ("normalization_amendment.json", "capture_report.reconciled.json")


class CaptureRefusal(Exception):
    """Create-once or plan violation — refuse before network contact."""


class TransportResponse(Protocol):
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]


Transport = Callable[[str], TransportResponse]


def canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def artifact_dir(spec: CaptureSpec, root: Path = K1_ROOT) -> Path:
    if spec.kind == "qa":
        return root / "qualification" / spec.capture_id
    return root / "captures" / spec.capture_id


def build_plan(root: Path = K1_ROOT) -> dict:
    entries = []
    for spec in FROZEN_ATTEMPTS:
        adir = artifact_dir(spec, root)
        entries.append({
            "id": spec.capture_id,
            "kind": spec.kind,
            "record_id_expected": spec.record_id,
            "package_expected": spec.package_expected,
            "ecosystem_expected": spec.ecosystem_expected,
            "discovery_url": spec.discovery_url,
            "capture_url": spec.capture_url,
            "raw_path": str(adir.relative_to(root) / "raw.json"),
            "sidecar_path": str(adir.relative_to(root) / "sidecar.json"),
        })
    plan_body = {
        "schema_version": SCHEMA_VERSION,
        "attempt_count": len(FROZEN_ATTEMPTS),
        "entries": entries,
        "promotion_rule": {
            "originals": list(PROMOTION_ORIGINALS),
            "fallbacks": list(PROMOTION_FALLBACKS),
            "targets": list(PROMOTION_TARGETS),
            "reserved_packages": sorted(RESERVED_PACKAGES),
        },
    }
    plan = dict(plan_body)
    plan["plan_sha256"] = sha256_bytes(canonical_json(plan_body).encode())
    return plan


def lookup_spec(attempt_id: str) -> CaptureSpec | None:
    for spec in FROZEN_ATTEMPTS:
        if spec.capture_id == attempt_id:
            return spec
    return None


def refuse_unknown_url(url: str) -> None:
    if url not in FROZEN_URLS:
        raise CaptureRefusal(f"unknown or unauthorized URL: {url}")


def check_create_once(root: Path = K1_ROOT) -> None:
    if root.exists():
        for p in root.rglob("*"):
            if p.is_file():
                raise CaptureRefusal(
                    f"create-once refusal: artifact already exists: {p}")


# ---------------------------------------------------------------------------
# HTTP transport (live) — zero retries, redirect chain recorded.
# ---------------------------------------------------------------------------

@dataclass
class _LiveResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return urllib.request.Request(newurl, headers=req.headers,
                                      method=req.get_method())


def live_transport(url: str) -> _LiveResponse:
    refuse_unknown_url(url)
    chain: list[str] = [url]
    opener = urllib.request.build_opener(_NoRedirect())
    req = urllib.request.Request(url, headers={"Accept": "application/json",
                                                 "User-Agent": "efc-k1-capture/1"})
    current = req
    while True:
        try:
            with opener.open(current, timeout=120) as resp:
                body = resp.read()
                final_url = resp.geturl()
                if final_url not in chain:
                    chain.append(final_url)
                hdrs = {k.lower(): v for k, v in resp.headers.items()}
                return _LiveResponse(status=resp.status, headers=hdrs, body=body,
                                     url=final_url, redirect_chain=chain)
        except urllib.error.HTTPError as e:
            body = e.read()
            hdrs = {k.lower(): v for k, v in e.headers.items()}
            return _LiveResponse(status=e.code, headers=hdrs, body=body,
                                 url=chain[-1], redirect_chain=chain)


# ---------------------------------------------------------------------------
# Field extraction and mechanical validation
# ---------------------------------------------------------------------------

def _parse_json(body: bytes) -> tuple[dict | None, str | None]:
    try:
        return json.loads(body.decode("utf-8")), None
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return None, f"json_parse_error:{type(e).__name__}"


def _record_id_from_payload(data: dict, is_github: bool) -> str | None:
    if is_github:
        return data.get("ghsa_id") or data.get("id")
    return data.get("id")


def _publication_field(data: dict, is_github: bool) -> str | None:
    return data.get("published_at") if is_github else data.get("published")


def _modified_field(data: dict, is_github: bool) -> str | None:
    return data.get("updated_at") if is_github else data.get("modified")


def _withdrawn_present(data: dict, is_github: bool) -> bool:
    if is_github:
        return bool(data.get("withdrawn_at") or data.get("state") == "withdrawn")
    return bool(data.get("withdrawn"))


def _package_ecosystem_osv(data: dict) -> tuple[str | None, str | None]:
    for aff in data.get("affected") or []:
        pkg = aff.get("package") or {}
        name = pkg.get("name")
        eco = pkg.get("ecosystem")
        if name and eco:
            return name, eco
    return None, None


def _package_ecosystem_github(data: dict) -> tuple[str | None, str | None]:
    vulns = data.get("vulnerabilities") or []
    if not vulns:
        return None, None
    pkg = vulns[0].get("package") or {}
    return pkg.get("name"), pkg.get("ecosystem")


def _osv_ranges(data: dict) -> list[dict]:
    out: list[dict] = []
    for aff in data.get("affected") or []:
        for rng in aff.get("ranges") or []:
            out.append({
                "type": rng.get("type"),
                "events": list(rng.get("events") or []),
                "affected_versions": aff.get("versions"),
                "database_specific": aff.get("database_specific"),
            })
    return out


def _github_ranges(data: dict) -> list[dict]:
    out: list[dict] = []
    for v in data.get("vulnerabilities") or []:
        out.append({
            "vulnerable_version_range": v.get("vulnerable_version_range"),
            "package": v.get("package"),
        })
    return out


def _osv_finite_bound(events: list[dict]) -> bool:
    has_intro0 = any(e.get("introduced") == "0" for e in events)
    has_finite = any(
        k in e for e in events for k in ("fixed", "last_affected")
    )
    if has_intro0 and has_finite:
        return True
    if not has_intro0:
        return has_finite
    return False


def _osv_finite_bound_present(ranges: list[dict]) -> bool:
    for rng in ranges:
        if _osv_finite_bound(rng.get("events") or []):
            return True
    return False


def _github_finite_bound_present_plan(ranges: list[dict]) -> bool:
    """Plan-time rule frozen at K1 capture — permissive nonempty string check."""
    for rng in ranges:
        v = rng.get("vulnerable_version_range")
        if isinstance(v, str) and v.strip():
            return True
    return False


_VERSION_OP = re.compile(r"^\s*(<=|<|=|>=|>)\s*([0-9][^\s,]*)")


def github_finite_bound_conservative(vrange: str) -> bool:
    """K1c conservative rule: require explicit finite upper or exact bound."""
    if not vrange or not vrange.strip():
        return False
    s = vrange.strip()
    if s == "*" or s.startswith("*"):
        return False
    clauses = [c.strip() for c in s.split(",")]
    has_upper_or_exact = False
    for clause in clauses:
        if not clause:
            return False
        m = _VERSION_OP.match(clause)
        if not m:
            return False
        if m.group(1) in ("<", "<=", "="):
            has_upper_or_exact = True
    return has_upper_or_exact


def _github_finite_bound_conservative_present(ranges: list[dict]) -> bool:
    for rng in ranges:
        v = rng.get("vulnerable_version_range")
        if isinstance(v, str) and github_finite_bound_conservative(v):
            return True
    return False


# Closed ecosystem normalization — derived reconciliation only (K1c).
_PYPI_NORMALIZED = "pypi_registry"

_ECOSYSTEM_NORMALIZATION: dict[str, str] = {
    "PyPI": _PYPI_NORMALIZED,
    "pip": _PYPI_NORMALIZED,
}


def normalize_ecosystem(token: str) -> str:
    """Map docket PyPI and GitHub API pip to one typed value; no other aliases."""
    return _ECOSYSTEM_NORMALIZATION.get(token, token)


def ecosystems_match(expected: str, returned: str | None) -> bool:
    if returned is None:
        return False
    return normalize_ecosystem(expected) == normalize_ecosystem(returned)


def _affected_range_paths(is_github: bool, ranges: list[dict]) -> list[dict]:
    paths: list[dict] = []
    if is_github:
        for i, rng in enumerate(ranges):
            paths.append({
                "path": f"vulnerabilities[{i}].vulnerable_version_range",
                "value": rng.get("vulnerable_version_range"),
            })
    else:
        idx = 0
        for aff_i, aff in enumerate((ranges and ranges) or []):
            for rng_i, rng in enumerate([aff] if "events" in aff else []):
                for ev_i, ev in enumerate(rng.get("events") or []):
                    for key, val in ev.items():
                        paths.append({
                            "path": f"affected[{aff_i}].ranges[{rng_i}].events[{ev_i}].{key}",
                            "value": val,
                        })
                idx += 1
    return paths


def _extract_osv_range_paths(data: dict) -> list[dict]:
    paths: list[dict] = []
    for aff_i, aff in enumerate(data.get("affected") or []):
        for rng_i, rng in enumerate(aff.get("ranges") or []):
            for ev_i, ev in enumerate(rng.get("events") or []):
                for key, val in ev.items():
                    paths.append({
                        "path": (f"affected[{aff_i}].ranges[{rng_i}]"
                                 f".events[{ev_i}].{key}"),
                        "value": val,
                    })
            if aff.get("database_specific"):
                paths.append({
                    "path": f"affected[{aff_i}].database_specific",
                    "value": aff.get("database_specific"),
                })
    return paths


def _extract_github_range_paths(data: dict) -> list[dict]:
    paths: list[dict] = []
    for i, v in enumerate(data.get("vulnerabilities") or []):
        paths.append({
            "path": f"vulnerabilities[{i}].vulnerable_version_range",
            "value": v.get("vulnerable_version_range"),
        })
    return paths


def _year_2026(pub: str | None) -> bool:
    return bool(pub and pub.startswith("2026"))


def validate_capture(spec: CaptureSpec, data: dict | None,
                     http_ok: bool, parse_err: str | None) -> tuple[str, list[str], bool]:
    """Return (verdict, failure_reasons, qualifies_for_qa)."""
    failures: list[str] = []
    is_github = spec.capture_url.startswith("https://api.github.com/")
    if not http_ok:
        failures.append("http_failure")
    if parse_err:
        failures.append(parse_err)
    if data is None:
        return ("fail", failures, False)

    rid = _record_id_from_payload(data, is_github)
    if rid != spec.record_id:
        failures.append("record_id_mismatch")

    if is_github:
        pkg, eco = _package_ecosystem_github(data)
        ranges = _github_ranges(data)
        finite = _github_finite_bound_present_plan(ranges)
    else:
        pkg, eco = _package_ecosystem_osv(data)
        ranges = _osv_ranges(data)
        finite = _osv_finite_bound_present(ranges)

    if pkg != spec.package_expected:
        failures.append("package_mismatch")
    if eco != spec.ecosystem_expected:
        failures.append("ecosystem_mismatch")

    pub = _publication_field(data, is_github)
    if not _year_2026(pub):
        failures.append("publication_not_2026")

    if _withdrawn_present(data, is_github):
        failures.append("withdrawn")

    if not finite:
        failures.append("missing_finite_bound")

    if not ranges:
        failures.append("missing_range")

    verdict = "pass" if not failures else "fail"
    qualifies = (
        verdict == "pass"
        and pkg == spec.package_expected
        and pkg not in RESERVED_PACKAGES
    )
    return verdict, failures, qualifies


def _base_sidecar(spec: CaptureSpec, plan_sha: str, resp: TransportResponse,
                  raw_sha: str, raw_len: int) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "discovery_url": spec.discovery_url,
        "capture_url": spec.capture_url,
        "final_url": resp.url,
        "redirect_chain": list(resp.redirect_chain),
        "retrieved_at_utc": utc_now_iso(),
        "http_status": resp.status,
        "content_type": resp.headers.get("content-type"),
        "raw_sha256": raw_sha,
        "raw_byte_length": raw_len,
        "record_id_expected": spec.record_id,
        "package_expected": spec.package_expected,
        "ecosystem_expected": spec.ecosystem_expected,
        "plan_sha256": plan_sha,
    }


def build_capture_sidecar(spec: CaptureSpec, plan_sha: str,
                          resp: TransportResponse, body: bytes) -> dict:
    raw_sha = sha256_bytes(body)
    sc = _base_sidecar(spec, plan_sha, resp, raw_sha, len(body))
    sc["capture_id"] = spec.capture_id
    sc["oracle_id"] = f"efc-calibration-{spec.capture_id}"

    data, parse_err = _parse_json(body)
    http_ok = 200 <= resp.status < 300
    is_github = spec.capture_url.startswith("https://api.github.com/")

    sc["record_id_returned"] = None
    sc["package_returned"] = None
    sc["ecosystem_returned"] = None
    sc["published"] = None
    sc["modified"] = None
    sc["withdrawn"] = None
    sc["affected_range_fields"] = []
    sc["finite_bound_present"] = False
    sc["failure_reasons"] = []
    sc["capture_verdict"] = "fail"

    if data is not None:
        sc["record_id_returned"] = _record_id_from_payload(data, is_github)
        if is_github:
            sc["package_returned"], sc["ecosystem_returned"] = _package_ecosystem_github(data)
            sc["affected_range_fields"] = _extract_github_range_paths(data)
            sc["finite_bound_present"] = _github_finite_bound_present_plan(
                _github_ranges(data))
        else:
            sc["package_returned"], sc["ecosystem_returned"] = _package_ecosystem_osv(data)
            sc["affected_range_fields"] = _extract_osv_range_paths(data)
            sc["ranges"] = _osv_ranges(data)
            sc["finite_bound_present"] = _osv_finite_bound_present(_osv_ranges(data))
        sc["published"] = _publication_field(data, is_github)
        sc["modified"] = _modified_field(data, is_github)
        sc["withdrawn"] = _withdrawn_present(data, is_github)

    verdict, failures, _ = validate_capture(spec, data, http_ok, parse_err)
    if parse_err and parse_err not in failures:
        failures = [parse_err] + failures
    sc["failure_reasons"] = failures
    sc["capture_verdict"] = verdict
    return sc


def build_qa_sidecar(spec: CaptureSpec, plan_sha: str,
                     resp: TransportResponse, body: bytes) -> dict:
    raw_sha = sha256_bytes(body)
    sc = _base_sidecar(spec, plan_sha, resp, raw_sha, len(body))
    sc["qa_id"] = spec.capture_id

    data, parse_err = _parse_json(body)
    http_ok = 200 <= resp.status < 300
    is_github = False  # all QA are OSV

    sc["record_id_returned"] = None
    sc["package_returned"] = None
    sc["ecosystem_returned"] = None
    sc["published"] = None
    sc["modified"] = None
    sc["withdrawn"] = None
    sc["ranges"] = []
    sc["finite_bound_present"] = False
    sc["qualifies"] = False
    sc["failure_reasons"] = []

    if data is not None:
        sc["record_id_returned"] = data.get("id")
        sc["package_returned"], sc["ecosystem_returned"] = _package_ecosystem_osv(data)
        sc["ranges"] = _osv_ranges(data)
        sc["published"] = data.get("published")
        sc["modified"] = data.get("modified")
        sc["withdrawn"] = bool(data.get("withdrawn"))
        sc["finite_bound_present"] = _osv_finite_bound_present(_osv_ranges(data))

    _, failures, qualifies = validate_capture(spec, data, http_ok, parse_err)
    sc["failure_reasons"] = failures
    sc["qualifies"] = qualifies
    return sc


def write_artifact_pair(spec: CaptureSpec, root: Path, plan_sha: str,
                        resp: TransportResponse) -> dict:
    adir = artifact_dir(spec, root)
    adir.mkdir(parents=True, exist_ok=True)
    raw_path = adir / "raw.json"
    sidecar_path = adir / "sidecar.json"
    if raw_path.exists() or sidecar_path.exists():
        raise CaptureRefusal(f"create-once refusal: {adir} not empty")

    body = resp.body
    raw_path.write_bytes(body)
    if spec.kind == "qa":
        sidecar = build_qa_sidecar(spec, plan_sha, resp, body)
    else:
        sidecar = build_capture_sidecar(spec, plan_sha, resp, body)
    sidecar_path.write_text(canonical_json(sidecar) + "\n")
    return sidecar


def run_attempt(spec: CaptureSpec, transport: Transport, root: Path,
                plan_sha: str) -> dict:
    refuse_unknown_url(spec.capture_url)
    resp = transport(spec.capture_url)
    return write_artifact_pair(spec, root, plan_sha, resp)


def apply_promotion(root: Path, plan_sha: str) -> dict:
    qa_by_id: dict[str, dict] = {}
    for qa_id in list(PROMOTION_ORIGINALS) + list(PROMOTION_FALLBACKS):
        sc_path = root / "qualification" / qa_id / "sidecar.json"
        if sc_path.exists():
            qa_by_id[qa_id] = json.loads(sc_path.read_text())

    ledger_entries: list[dict] = []
    selected: list[tuple[str, str]] = []  # (qa_id, target_cap_id)
    used_packages: set[str] = set(RESERVED_PACKAGES)

    def consider(qa_id: str) -> None:
        if len(selected) >= 4:
            return
        sc = qa_by_id.get(qa_id)
        entry = {"qa_id": qa_id, "considered": True}
        if sc is None:
            entry.update({"qualifies": False, "rejection_reason": "artifact_missing",
                          "promoted_to": None})
            ledger_entries.append(entry)
            return
        pkg = sc.get("package_returned")
        qualifies = sc.get("qualifies", False)
        if not qualifies:
            entry.update({"qualifies": False,
                          "rejection_reason": sc.get("failure_reasons") or ["not_qualified"],
                          "promoted_to": None})
            ledger_entries.append(entry)
            return
        if pkg in used_packages:
            entry.update({"qualifies": True, "rejection_reason": "package_collision",
                          "promoted_to": None})
            ledger_entries.append(entry)
            return
        target = PROMOTION_TARGETS[len(selected)]
        selected.append((qa_id, target))
        used_packages.add(pkg)
        entry.update({"qualifies": True, "rejection_reason": None,
                      "promoted_to": target, "selection_order": len(selected)})
        ledger_entries.append(entry)

    for qa_id in PROMOTION_ORIGINALS:
        consider(qa_id)
    if len(selected) < 4:
        for qa_id in PROMOTION_FALLBACKS:
            consider(qa_id)

    family_shortfall = len(selected) < 4
    for qa_id, target in selected:
        qa_dir = root / "qualification" / qa_id
        cap_dir = root / "captures" / target
        cap_dir.mkdir(parents=True, exist_ok=True)
        raw_src = qa_dir / "raw.json"
        raw_dst = cap_dir / "raw.json"
        sidecar_dst = cap_dir / "sidecar.json"
        if raw_dst.exists() or sidecar_dst.exists():
            raise CaptureRefusal(f"promotion target exists: {cap_dir}")
        raw_bytes = raw_src.read_bytes()
        raw_dst.write_bytes(raw_bytes)
        qa_sc = json.loads((qa_dir / "sidecar.json").read_text())
        promo_sc = dict(qa_sc)
        promo_sc["capture_id"] = target
        promo_sc["oracle_id"] = f"efc-calibration-{target}"
        promo_sc["promoted_from_qa_id"] = qa_id
        promo_sc.pop("qa_id", None)
        promo_sc["capture_verdict"] = "pass"
        promo_sc["qualifies"] = None
        sidecar_dst.write_text(canonical_json(promo_sc) + "\n")

    ledger = {
        "schema_version": SCHEMA_VERSION,
        "plan_sha256": plan_sha,
        "entries": ledger_entries,
        "promotions": [{"qa_id": q, "capture_id": t} for q, t in selected],
        "family_shortfall": family_shortfall,
        "shortfall_count": 4 - len(selected) if family_shortfall else 0,
    }
    (root / "promotion_ledger.json").write_text(canonical_json(ledger) + "\n")
    return ledger


def build_capture_report(root: Path, plan: dict) -> dict:
    attempts: list[dict] = []
    for spec in FROZEN_ATTEMPTS:
        adir = artifact_dir(spec, root)
        raw_path = adir / "raw.json"
        sc_path = adir / "sidecar.json"
        row = {"id": spec.capture_id, "kind": spec.kind,
               "capture_url": spec.capture_url}
        if raw_path.exists() and sc_path.exists():
            sc = json.loads(sc_path.read_text())
            row.update({
                "http_status": sc.get("http_status"),
                "raw_sha256": sc.get("raw_sha256"),
                "verdict": sc.get("capture_verdict") or sc.get("qualifies"),
                "failure_reasons": sc.get("failure_reasons", []),
            })
        else:
            row["status"] = "not_executed"
        attempts.append(row)

    captures = {}
    for spec in CANONICAL_CAPTURES:
        sc_path = root / "captures" / spec.capture_id / "sidecar.json"
        if sc_path.exists():
            sc = json.loads(sc_path.read_text())
            captures[spec.capture_id] = sc.get("capture_verdict")

    for target in PROMOTION_TARGETS:
        sc_path = root / "captures" / target / "sidecar.json"
        if sc_path.exists():
            sc = json.loads(sc_path.read_text())
            captures[target] = sc.get("capture_verdict")

    qa_verdicts = {}
    for spec in QA_ATTEMPTS:
        sc_path = root / "qualification" / spec.capture_id / "sidecar.json"
        if sc_path.exists():
            sc = json.loads(sc_path.read_text())
            qa_verdicts[spec.capture_id] = sc.get("qualifies")

    report = {
        "schema_version": SCHEMA_VERSION,
        "plan_sha256": plan["plan_sha256"],
        "attempts": attempts,
        "capture_verdicts": captures,
        "qa_qualifies": qa_verdicts,
        "generated_at_utc": utc_now_iso(),
    }
    if (root / "promotion_ledger.json").exists():
        report["promotion_ledger"] = json.loads(
            (root / "promotion_ledger.json").read_text())
    (root / "capture_report.json").write_text(canonical_json(report) + "\n")
    return report


def verify_sidecar_hashes(root: Path = K1_ROOT) -> list[str]:
    """Independent read-path verification of raw_sha256 vs on-disk bytes."""
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


def validate_capture_reconciled(
    record_id_expected: str,
    package_expected: str,
    ecosystem_expected: str,
    capture_url: str,
    data: dict | None,
    http_ok: bool,
    parse_err: str | None,
) -> tuple[str, list[str]]:
    """Derived K1c verdict from raw bytes — normalization + conservative GitHub bound."""
    failures: list[str] = []
    is_github = capture_url.startswith("https://api.github.com/")
    if not http_ok:
        failures.append("http_failure")
    if parse_err:
        failures.append(parse_err)
    if data is None:
        return "fail", failures

    rid = _record_id_from_payload(data, is_github)
    if rid != record_id_expected:
        failures.append("record_id_mismatch")

    if is_github:
        pkg, eco = _package_ecosystem_github(data)
        ranges = _github_ranges(data)
        finite = _github_finite_bound_conservative_present(ranges)
    else:
        pkg, eco = _package_ecosystem_osv(data)
        ranges = _osv_ranges(data)
        finite = _osv_finite_bound_present(ranges)

    if pkg != package_expected:
        failures.append("package_mismatch")
    if not ecosystems_match(ecosystem_expected, eco):
        failures.append("ecosystem_mismatch")

    pub = _publication_field(data, is_github)
    if not _year_2026(pub):
        failures.append("publication_not_2026")

    if _withdrawn_present(data, is_github):
        failures.append("withdrawn")

    if not finite:
        failures.append("missing_finite_bound")

    if not ranges:
        failures.append("missing_range")

    return ("pass" if not failures else "fail"), failures


def _capture_dir_for_id(capture_id: str, root: Path) -> Path:
    return root / "captures" / capture_id


def _require_k1_artifacts(root: Path) -> None:
    required = [
        root / "plan.json",
        root / "capture_report.json",
        root / "promotion_ledger.json",
    ]
    for spec in FROZEN_ATTEMPTS:
        adir = artifact_dir(spec, root)
        required.extend([adir / "raw.json", adir / "sidecar.json"])
    for cap_id in FINAL_CAPTURE_IDS:
        required.extend([
            _capture_dir_for_id(cap_id, root) / "raw.json",
            _capture_dir_for_id(cap_id, root) / "sidecar.json",
        ])
    missing = [str(p.relative_to(root)) for p in required if not p.exists()]
    if missing:
        raise CaptureRefusal(
            f"reconciliation refused: missing artifacts: {', '.join(missing)}")


def _pin_original_hashes(root: Path) -> dict:
    plan_path = root / "plan.json"
    report_path = root / "capture_report.json"
    pins = {
        "plan_sha256": sha256_file(plan_path),
        "capture_report_sha256": sha256_file(report_path),
        "capture_sidecar_sha256": {},
        "raw_sha256": {},
    }
    for cap_id in FINAL_CAPTURE_IDS:
        cdir = _capture_dir_for_id(cap_id, root)
        sc_path = cdir / "sidecar.json"
        raw_path = cdir / "raw.json"
        pins["capture_sidecar_sha256"][cap_id] = sha256_file(sc_path)
        pins["raw_sha256"][cap_id] = sha256_file(raw_path)
    return pins


def _verify_pinned_hashes(root: Path, pins: dict) -> None:
    if sha256_file(root / "plan.json") != pins["plan_sha256"]:
        raise CaptureRefusal("reconciliation refused: plan.json hash changed")
    if sha256_file(root / "capture_report.json") != pins["capture_report_sha256"]:
        raise CaptureRefusal("reconciliation refused: capture_report.json hash changed")
    for cap_id, expected in pins["capture_sidecar_sha256"].items():
        sc_path = _capture_dir_for_id(cap_id, root) / "sidecar.json"
        if sha256_file(sc_path) != expected:
            raise CaptureRefusal(
                f"reconciliation refused: sidecar hash changed for {cap_id}")
    for cap_id, expected in pins["raw_sha256"].items():
        raw_path = _capture_dir_for_id(cap_id, root) / "raw.json"
        if sha256_file(raw_path) != expected:
            raise CaptureRefusal(
                f"reconciliation refused: raw hash changed for {cap_id}")


def reconciler_module_sha256() -> str:
    return sha256_file(Path(__file__).resolve())


def build_normalization_amendment(root: Path, pins: dict) -> dict:
    return {
        "schema_version": "efc-k1-normalization-amendment-v1",
        "amendment_id": AMENDMENT_ID,
        "amendment_version": "1",
        "reason": "docket token PyPI vs GitHub Advisory API token pip",
        "ecosystem_mapping": {
            "closed": True,
            "PyPI": _PYPI_NORMALIZED,
            "pip": _PYPI_NORMALIZED,
            "npm": "npm",
            "note": "no fuzzy, case-insensitive, or general aliasing",
        },
        "finite_bound_rule": {
            "rule_id": FINITE_BOUND_RULE_ID,
            "applies_to": "github_vulnerabilities_vulnerable_version_range",
            "accept_examples": [
                "< 1.2.2", "<= 0.63.0", ">= 1.1.0, <= 1.8.3", "= 1.2.3",
            ],
            "reject_examples": ["", "*", ">= 0", ">= 1.0.0"],
        },
        "pinned_original_artifacts": pins,
        "reconciler_module_sha256": reconciler_module_sha256(),
        "seat": RECONCILER_SEAT,
        "generated_at_utc": utc_now_iso(),
        "network_calls": 0,
    }


def reconcile_capture_verdict(root: Path, capture_id: str) -> dict:
    cdir = _capture_dir_for_id(capture_id, root)
    sc_path = cdir / "sidecar.json"
    raw_path = cdir / "raw.json"
    original = json.loads(sc_path.read_text())
    raw_bytes = raw_path.read_bytes()
    if sha256_bytes(raw_bytes) != original.get("raw_sha256"):
        raise CaptureRefusal(
            f"reconciliation refused: raw/sidecar hash mismatch for {capture_id}")

    data, parse_err = _parse_json(raw_bytes)
    http_ok = 200 <= int(original.get("http_status", 0)) < 300
    reconciled_verdict, reconciled_failures = validate_capture_reconciled(
        original["record_id_expected"],
        original["package_expected"],
        original["ecosystem_expected"],
        original["capture_url"],
        data,
        http_ok,
        parse_err,
    )
    return {
        "capture_id": capture_id,
        "original_verdict": original.get("capture_verdict"),
        "original_failure_reasons": list(original.get("failure_reasons") or []),
        "reconciled_verdict": reconciled_verdict,
        "reconciled_failure_reasons": reconciled_failures,
        "raw_sha256": original.get("raw_sha256"),
    }


def build_reconciled_report(root: Path, amendment: dict,
                            rows: list[dict]) -> dict:
    original_report = json.loads((root / "capture_report.json").read_text())
    by_id = {r["capture_id"]: r for r in rows}
    capture_verdicts = {cid: by_id[cid]["reconciled_verdict"]
                        for cid in FINAL_CAPTURE_IDS}
    family_a = {f"capA-0{i}": capture_verdicts[f"capA-0{i}"] for i in range(1, 7)}
    family_b = {f"capB-0{i}": capture_verdicts[f"capB-0{i}"] for i in range(1, 7)}
    return {
        "schema_version": "efc-k1-capture-report-reconciled-v1",
        "normalization_amendment_sha256": sha256_bytes(
            canonical_json(amendment).encode()),
        "original_capture_report_sha256": amendment["pinned_original_artifacts"][
            "capture_report_sha256"],
        "plan_sha256": amendment["pinned_original_artifacts"]["plan_sha256"],
        "rows": rows,
        "capture_verdicts_reconciled": capture_verdicts,
        "family_a_pass_count": sum(1 for v in family_a.values() if v == "pass"),
        "family_b_pass_count": sum(1 for v in family_b.values() if v == "pass"),
        "qa_qualifies_unchanged": original_report.get("qa_qualifies", {}),
        "qaA_enum_map_note": (
            "qaA-enum-map remains qualifies=false; not promoted; unchanged"),
        "generated_at_utc": utc_now_iso(),
        "seat": RECONCILER_SEAT,
        "network_calls": 0,
        "disclaimer": (
            "derived pre-pin QC only; no eligibility, fixture, oracle, "
            "or mechanism claim"),
    }


def reconcile_k1(root: Path = K1_ROOT) -> dict:
    """Offline derived reconciliation — create-once, zero network."""
    for name in _DERIVED_ARTIFACTS:
        if (root / name).exists():
            raise CaptureRefusal(
                f"create-once refusal: derived artifact exists: {name}")

    _require_k1_artifacts(root)
    pins = _pin_original_hashes(root)
    _verify_pinned_hashes(root, pins)

    amendment = build_normalization_amendment(root, pins)
    rows = [reconcile_capture_verdict(root, cid) for cid in FINAL_CAPTURE_IDS]
    report = build_reconciled_report(root, amendment, rows)

    (root / "normalization_amendment.json").write_text(
        canonical_json(amendment) + "\n")
    (root / "capture_report.reconciled.json").write_text(
        canonical_json(report) + "\n")

    _verify_pinned_hashes(root, pins)
    return {
        "mode": "reconcile",
        "network_calls": 0,
        "amendment_sha256": sha256_bytes(canonical_json(amendment).encode()),
        "reconciled_report_sha256": sha256_bytes(
            canonical_json(report).encode()),
        "rows": rows,
        "family_a_pass_count": report["family_a_pass_count"],
        "family_b_pass_count": report["family_b_pass_count"],
    }


    """Independent read-path verification of raw_sha256 vs on-disk bytes."""
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


def dry_run(root: Path = K1_ROOT) -> dict:
    plan = build_plan(root)
    return {"mode": "dry_run", "plan": plan, "network_calls": 0}


def execute_live(root: Path = K1_ROOT, transport: Transport | None = None) -> dict:
    check_create_once(root)
    root.mkdir(parents=True, exist_ok=True)
    plan = build_plan(root)
    plan_path = root / "plan.json"
    plan_path.write_text(canonical_json(plan) + "\n")
    plan_sha = plan["plan_sha256"]
    transport = transport or live_transport

    results: list[dict] = []
    terminal = False
    for spec in FROZEN_ATTEMPTS:
        if terminal:
            break
        try:
            sidecar = run_attempt(spec, transport, root, plan_sha)
            row = {"id": spec.capture_id, "verdict": sidecar.get("capture_verdict")
                   or sidecar.get("qualifies")}
            results.append(row)
            # transport/HTTP/JSON hard failures stop further requests
            if spec.kind == "capture":
                if sidecar.get("capture_verdict") == "fail" and any(
                    r in sidecar.get("failure_reasons", [])
                    for r in ("http_failure", "json_parse_error")
                ):
                    terminal = True
            else:
                if sidecar.get("failure_reasons") and any(
                    str(r).startswith("json_parse") or r == "http_failure"
                    for r in sidecar.get("failure_reasons", [])
                ):
                    terminal = True
        except CaptureRefusal:
            raise
        except Exception as e:
            terminal = True
            results.append({"id": spec.capture_id, "error": str(e)})

    # promotion after QA phase — run if we completed all QA or stopped after captures+some QA
    qa_done = all(
        (root / "qualification" / s.capture_id / "raw.json").exists()
        for s in QA_ATTEMPTS
    ) or terminal
    promotion = None
    if qa_done or any(
        (root / "qualification" / s.capture_id / "raw.json").exists()
        for s in QA_ATTEMPTS
    ):
        promotion = apply_promotion(root, plan_sha)

    report = build_capture_report(root, plan)
    return {"mode": "live", "results": results, "promotion": promotion,
            "report": report, "terminal_partial": terminal}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EFC K1 mechanical snapshot capture")
    parser.add_argument("--execute", action="store_true",
                        help="run one live capture (create-once)")
    parser.add_argument("--reconcile", action="store_true",
                        help="offline K1c derived reconciliation (create-once)")
    parser.add_argument("--root", type=Path, default=K1_ROOT,
                        help="acquisition root directory")
    parser.add_argument("--verify-hashes", action="store_true",
                        help="verify sidecar raw_sha256 against on-disk bytes")
    args = parser.parse_args(argv)

    if args.verify_hashes:
        errs = verify_sidecar_hashes(args.root)
        if errs:
            for e in errs:
                print(e, file=sys.stderr)
            return 1
        print("all sidecar hashes verified")
        return 0

    if args.reconcile:
        try:
            outcome = reconcile_k1(args.root)
        except CaptureRefusal as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        print(canonical_json(outcome))
        return 0

    if args.execute:
        try:
            outcome = execute_live(args.root)
        except CaptureRefusal as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        print(canonical_json(outcome))
        return 0

    plan_out = dry_run(args.root)
    print(canonical_json(plan_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
