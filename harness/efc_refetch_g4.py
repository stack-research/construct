"""EFC v0 G4 independent 40-record K4 promotion refetch + positive requalification.

Derives ordered allowlist mechanically from k4/promotion_identity_ledger.json.
One GET per promoted row, zero retries, refuse redirects, no search/substitution.
Does not modify K1–K4 acquisition trees or promotion ledgers.

Usage:
  python -m harness.efc_refetch_g4                 # dry-run, zero network
  python -m harness.efc_refetch_g4 --write-plan    # create-once plan only
  python -m harness.efc_refetch_g4 --execute       # one live run (create-once)
  python -m harness.efc_refetch_g4 --verify-hashes
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from harness import efc_capture_k3c as k3c
from harness.efc_capture import (
    CaptureSpec,
    _github_finite_bound_conservative_present,
    _github_ranges,
    _osv_finite_bound_present,
    _osv_ranges,
    _parse_json as k1_parse_json,
    _year_2026,
    validate_capture,
)
from harness.efc_capture_k2 import FAMILY_C, CSpec, validate_family_c, _parse_json
from harness.efc_capture_k2b import FROZEN_CANDIDATES, DSpec, qualify_candidate
from harness.efc_capture_k3 import (
    K3Spec,
    extract_family_f,
    validate_family_e,
)
from harness.efc_capture_k4 import (
    CaptureRefusal,
    FROZEN_P,
    canonical_json,
    extract_aliases,
    qualify_p01,
    qualify_p02,
    qualify_p03,
    qualify_p04,
    qualify_p05,
    qualify_p06,
    sha256_bytes,
    sha256_file,
    utc_now_iso,
)
from harness.efc_capture_k4br import (
    EXCLUDED_B_SLOTS,
    FROZEN_BR,
    KIMI_DISCOVERY_ONLY_URLS,
    qualify_br,
)
from harness.efc_refetch_g2 import positive_d_evidence

REPO = Path(__file__).resolve().parent.parent
ACQ = REPO / "corpus" / "efc_calibration" / "_acquisition"
G4_ROOT = ACQ / "g4"
REFETCH_ROOT = G4_ROOT / "refetch"
LEDGER_PATH = ACQ / "k4" / "promotion_identity_ledger.json"
SCHEMA_VERSION = "efc-g4-refetch-v1"
SEAT = "cursor/grok-4.5"
MAX_CALLS = 40
TARGET_FAMILY_COUNTS = {"A": 8, "B": 7, "C": 7, "D": 7, "E": 7, "F": 4}
PERSON_NAME_RE = re.compile(r"^[A-Z][a-z]+ [A-Z][a-z]+$")

EXCLUDED_B_URLS: frozenset[str] = frozenset({
    "https://api.github.com/advisories/GHSA-pmch-g965-grmr",
    "https://api.github.com/advisories/GHSA-mf9w-mj56-hr94",
    "https://api.github.com/advisories/GHSA-37w4-hwhx-4rc4",
})

_F_CAPTURE_IDS = {
    "F01": "capF-01",
    "F02": "capF-02",
    "F03": "capF-03",
    "F04": "capF-04",
}

_BR_BY_SLOT = {s.slot: s for s in FROZEN_BR}
_P_BY_SLOT = {s.slot: s for s in FROZEN_P}
_C_BY_SLUG = {s.product_slug: s for s in FAMILY_C}
_D_BY_GO_ID = {s.go_id: s for s in FROZEN_CANDIDATES if s.role == "primary"}


@dataclass(frozen=True)
class G4Spec:
    logical_slot: str
    family: str
    record_id: str
    entity_key: str
    capture_url: str
    raw_name: str
    acquisition_raw_path: Path
    acquisition_raw_sha256: str
    format_provenance: str | None = None


@dataclass
class TransportResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]
    redirect_refused: bool


Transport = Callable[[str], TransportResponse]


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class CallCeiling:
    def __init__(self, max_calls: int = MAX_CALLS) -> None:
        self.max_calls = max_calls
        self.count = 0

    def record(self) -> None:
        self.count += 1
        if self.count > self.max_calls:
            raise CaptureRefusal(
                f"call ceiling exceeded: {self.count} > {self.max_calls}")


def module_sha256() -> str:
    return sha256_file(Path(__file__).resolve())


def load_ledger(path: Path = LEDGER_PATH) -> dict:
    if not path.exists():
        raise CaptureRefusal(f"missing promotion ledger: {path}")
    return json.loads(path.read_text())


def _raw_name_from_capture_path(capture_path: str) -> str:
    suffix = Path(capture_path).suffix.lower()
    if suffix in (".json", ".html", ".rst"):
        return f"raw{suffix}"
    raise CaptureRefusal(f"unsupported capture extension: {capture_path}")


def _alias_format(spec: G4Spec) -> str:
    if spec.format_provenance:
        fp = spec.format_provenance
        if fp in ("rustsec_osv_mirror", "rustsec_osv"):
            return "rustsec_osv"
        if fp == "ghsa":
            return "ghsa"
        if fp == "endoflife":
            return "endoflife"
        if fp == "go_vuln":
            return "go_vuln"
        if fp == "spdx":
            return "spdx"
    if spec.capture_url.startswith("https://api.github.com/advisories/"):
        return "ghsa"
    if spec.capture_url.startswith("https://api.osv.dev/"):
        return "rustsec_osv"
    if "rustsec/advisory-db" in spec.capture_url:
        return "rustsec_osv"
    if spec.capture_url.startswith("https://endoflife.date/"):
        return "endoflife"
    if spec.capture_url.startswith("https://vuln.go.dev/"):
        return "go_vuln"
    if "spdx/license-list-data" in spec.capture_url:
        return "spdx"
    if spec.family == "C":
        return "endoflife"
    if spec.family == "D":
        return "go_vuln"
    if spec.family == "E":
        return "spdx"
    if spec.family == "F":
        return "html_deprecation"
    raise CaptureRefusal(f"cannot determine alias format for {spec.logical_slot}")


def assert_allowlist_exclusions(urls: tuple[str, ...] | list[str]) -> None:
    for slot in EXCLUDED_B_SLOTS:
        if any(f"/{slot}" in u or slot in u for u in urls):
            raise CaptureRefusal(f"excluded slot URL present in allowlist: {slot}")
    for url in urls:
        if url in EXCLUDED_B_URLS:
            raise CaptureRefusal(f"excluded B-family URL in allowlist: {url}")
        if url in KIMI_DISCOVERY_ONLY_URLS:
            raise CaptureRefusal(f"discovery-only alternate in allowlist: {url}")


def build_g4_sources(ledger: dict | None = None) -> tuple[G4Spec, ...]:
    ledger = ledger or load_ledger()
    rows = ledger.get("rows") or []
    if len(rows) != MAX_CALLS:
        raise CaptureRefusal(f"expected {MAX_CALLS} promoted rows, got {len(rows)}")
    sources: list[G4Spec] = []
    for row in rows:
        slot = row["logical_slot"]
        if slot in EXCLUDED_B_SLOTS:
            raise CaptureRefusal(f"excluded logical slot in promotion ledger: {slot}")
        acq_path = REPO / row["capture_path"]
        if not acq_path.exists():
            raise CaptureRefusal(f"missing acquisition raw: {acq_path}")
        sources.append(G4Spec(
            logical_slot=slot,
            family=row["family"],
            record_id=row["record_id"],
            entity_key=row["entity_key"],
            capture_url=row["canonical_url"],
            raw_name=_raw_name_from_capture_path(row["capture_path"]),
            acquisition_raw_path=acq_path,
            acquisition_raw_sha256=row["raw_sha256"],
            format_provenance=row.get("format_provenance"),
        ))
    urls = tuple(s.capture_url for s in sources)
    assert_allowlist_exclusions(urls)
    return tuple(sources)


def derive_allowlist(
    ledger: dict | None = None,
) -> tuple[tuple[str, ...], frozenset[str]]:
    sources = build_g4_sources(ledger)
    ordered = tuple(s.capture_url for s in sources)
    return ordered, frozenset(ordered)


def refuse_unknown_url(url: str, allowlist: frozenset[str] | None = None) -> None:
    allowlist = allowlist or derive_allowlist()[1]
    if url not in allowlist:
        raise CaptureRefusal(f"unknown or unauthorized G4 URL: {url}")


def live_transport(
    url: str,
    ceiling: CallCeiling | None = None,
    allowlist: frozenset[str] | None = None,
) -> TransportResponse:
    allowlist = allowlist or derive_allowlist()[1]
    refuse_unknown_url(url, allowlist)
    if ceiling is not None:
        ceiling.record()
    opener = urllib.request.build_opener(_RefuseRedirect())
    req = urllib.request.Request(
        url, headers={"Accept": "*/*", "User-Agent": "efc-g4-refetch/1"})
    try:
        with opener.open(req, timeout=120) as resp:
            body = resp.read()
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return TransportResponse(
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
        return TransportResponse(
            status=e.code, headers=hdrs, body=body, url=url,
            redirect_chain=chain, redirect_refused=redirect,
        )


def _capture_spec_for_k1_row(spec: G4Spec) -> CaptureSpec:
    is_github = spec.capture_url.startswith("https://api.github.com/")
    eco = "crates.io" if spec.family == "A" else (
        "npm" if spec.entity_key in ("flatted", "shell-quote", "lodash") else "PyPI"
    )
    if is_github and spec.entity_key in ("form-data", "undici"):
        eco = "npm"
    if is_github and spec.entity_key == "pyjwt":
        eco = "pip"
    if is_github and spec.entity_key == "protobufjs":
        eco = "npm"
    return CaptureSpec(
        capture_id=spec.logical_slot,
        record_id=spec.record_id,
        discovery_url=spec.capture_url,
        capture_url=spec.capture_url,
        package_expected=spec.entity_key,
        ecosystem_expected=eco,
        kind="capture",
    )


def _qualify_osv_a(
    spec: G4Spec, data: dict, http_status: int, redirect_refused: bool,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if http_status != 200:
        reasons.append("http_not_200")
    if redirect_refused:
        reasons.append("redirect_refused")
    if data.get("id") != spec.record_id:
        reasons.append("id_mismatch")
    if not _year_2026(data.get("published")):
        reasons.append("publication_not_2026")
    pkg, eco = None, None
    for aff in data.get("affected") or []:
        p = (aff.get("package") or {})
        if p.get("name") and p.get("ecosystem"):
            pkg, eco = p.get("name"), p.get("ecosystem")
            break
    if pkg != spec.entity_key:
        reasons.append("package_mismatch")
    if eco != "crates.io":
        reasons.append("ecosystem_mismatch")
    if not _osv_finite_bound_present(_osv_ranges(data)):
        reasons.append("missing_finite_bound")
    return not reasons, reasons


def _qualify_ghsa_b(
    spec: G4Spec, data: dict, http_status: int, redirect_refused: bool,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if http_status != 200:
        reasons.append("http_not_200")
    if redirect_refused:
        reasons.append("redirect_refused")
    if data.get("ghsa_id") != spec.record_id:
        reasons.append("ghsa_id_mismatch")
    if not _year_2026(data.get("published_at")):
        reasons.append("published_at_not_2026")
    vulns = data.get("vulnerabilities") or []
    if not vulns:
        reasons.append("missing_vulnerabilities")
    for v in vulns:
        pkg = (v.get("package") or {}).get("name")
        if pkg != spec.entity_key:
            reasons.append("package_mismatch")
        vr = v.get("vulnerable_version_range")
        if not isinstance(vr, str) or not vr.strip():
            reasons.append("empty_vulnerable_version_range")
    if not _github_finite_bound_conservative_present(_github_ranges(data)):
        reasons.append("missing_finite_upper")
    return not reasons, reasons


def _e_spec(spec: G4Spec) -> K3Spec:
    kind = "exception" if spec.logical_slot in ("E01", "E02", "E03") else "license"
    return K3Spec(
        capture_id=spec.logical_slot,
        family="E",
        capture_url=spec.capture_url,
        record_id=spec.record_id,
        entity_kind=kind,
        raw_name=spec.raw_name,
    )


def _f_spec(spec: G4Spec) -> K3Spec:
    cid = _F_CAPTURE_IDS[spec.logical_slot]
    kind = "rst" if spec.raw_name.endswith(".rst") else "html"
    return K3Spec(
        capture_id=cid,
        family="F",
        capture_url=spec.capture_url,
        record_id=spec.record_id,
        entity_kind=kind,
        raw_name=spec.raw_name,
    )


def positive_requalification(
    spec: G4Spec,
    body: bytes,
    resp: TransportResponse,
    selected_modules: set[str],
) -> tuple[bool, list[str], dict]:
    """Family predicate on fresh body; independent of byte identity."""
    slot = spec.logical_slot
    http_ok = resp.status == 200 and not resp.redirect_refused
    extra: dict = {}

    if slot == "P01":
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False, ["json_parse_error"], extra
        ok, reasons = qualify_p01(data)
        return ok and http_ok, (["http_not_200"] if not http_ok else []) + reasons, extra

    if slot == "P06":
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False, ["json_parse_error"], extra
        ok, reasons = qualify_p06(data)
        return ok and http_ok, (["http_not_200"] if not http_ok else []) + reasons, extra

    if slot == "P02":
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False, ["json_parse_error"], extra
        ok, reasons = qualify_p02(data)
        return ok and http_ok, (["http_not_200"] if not http_ok else []) + reasons, extra

    if slot == "P03":
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False, ["json_parse_error"], extra
        if not isinstance(data, list):
            return False, ["not_array"], extra
        ok, reasons, extra = qualify_p03(data)
        return ok and http_ok, (["http_not_200"] if not http_ok else []) + reasons, extra

    if slot == "P04":
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False, ["json_parse_error"], extra
        ok, reasons = qualify_p04(data)
        return ok and http_ok, (["http_not_200"] if not http_ok else []) + reasons, extra

    if slot == "P05":
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False, ["json_parse_error"], extra
        ok, reasons = qualify_p05(data)
        return ok and http_ok, (["http_not_200"] if not http_ok else []) + reasons, extra

    if slot in _BR_BY_SLOT:
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False, ["json_parse_error"], extra
        br = _BR_BY_SLOT[slot]
        ok, reasons = qualify_br(br, data)
        if not http_ok:
            reasons = ["http_not_200"] + reasons
        if resp.redirect_refused:
            reasons = ["redirect_refused"] + reasons
        return ok and http_ok and not resp.redirect_refused, reasons, extra

    if spec.family == "A":
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False, ["json_parse_error"], extra
        ok, reasons = _qualify_osv_a(spec, data, resp.status, resp.redirect_refused)
        return ok, reasons, extra

    if spec.family == "B":
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False, ["json_parse_error"], extra
        if slot in ("B01", "B04", "B05"):
            k1spec = _capture_spec_for_k1_row(spec)
            data_parsed, parse_err = k1_parse_json(body)
            verdict, failures, _ = validate_capture(
                k1spec, data_parsed, http_ok, parse_err)
            if resp.redirect_refused and "redirect_refused" not in failures:
                failures = ["redirect_refused"] + failures
            return verdict == "pass", failures, extra
        ok, reasons = _qualify_ghsa_b(spec, data, resp.status, resp.redirect_refused)
        return ok, reasons, extra

    if spec.family == "C":
        cspec = _C_BY_SLUG.get(spec.entity_key)
        if cspec is None:
            return False, ["unknown_c_slug"], extra
        verdict, _, failures = validate_family_c(
            body, cspec, resp.url if not resp.redirect_refused else spec.capture_url)
        if resp.redirect_refused:
            failures = list(failures) + ["redirect_refused"]
        if resp.status != 200:
            failures = list(failures) + ["http_not_200"]
        return verdict == "pass" and not resp.redirect_refused and resp.status == 200, (
            failures), extra

    if spec.family == "D":
        dspec = _D_BY_GO_ID.get(spec.record_id)
        if dspec is None and slot == "P04":
            try:
                data = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return False, ["json_parse_error"], extra
            ok, reasons = qualify_p04(data)
            return ok and http_ok, (["http_not_200"] if not http_ok else []) + reasons, extra
        if dspec is None:
            return False, ["unknown_go_id"], extra
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False, ["json_parse_error"], extra
        if not isinstance(data, dict):
            return False, ["json_not_object"], extra
        evidence = positive_d_evidence(dspec, data)
        mod = evidence.get("module")
        module_distinct = mod not in selected_modules
        evidence["module_distinct_in_batch"] = module_distinct
        ok, reasons, _ = qualify_candidate(
            dspec, data,
            http_status=resp.status,
            redirect_refused=resp.redirect_refused,
            selected_modules=selected_modules,
        )
        if not module_distinct:
            ok = False
            reasons = list(reasons) + ["module_already_selected"]
        extra["positive_evidence"] = evidence
        positive_ok = evidence.get("positive_requalification_pass", False) and module_distinct
        return positive_ok and ok, reasons, extra

    if spec.family == "E":
        data, parse_err = k1_parse_json(body)
        k3spec = _e_spec(spec)
        verdict, failures, meta = validate_family_e(
            k3spec, data, http_ok, parse_err, resp.redirect_refused)
        extra["validation_meta"] = meta
        return verdict == "pass", failures, extra

    if spec.family == "F":
        if slot == "F03":
            extract, failures = k3c.extract_f03c_rst(body)
        else:
            extract, failures = extract_family_f(_f_spec(spec), body)
        extra["extract"] = extract
        if resp.redirect_refused:
            failures = ["redirect_refused"] + list(failures)
        if resp.status != 200:
            failures = ["http_not_200"] + list(failures)
        ok = (
            not failures
            and bool(extract.get("matched_statement"))
            and http_ok
            and not resp.redirect_refused
        )
        return ok, failures, extra

    return False, ["unknown_family"], extra


def type_identity(raw_equal: bool) -> dict:
    if raw_equal:
        return {
            "content_identity": "exact",
            "raw_bytes_equal": True,
            "drift_type": None,
        }
    return {
        "content_identity": "drift",
        "raw_bytes_equal": False,
        "drift_type": "raw_byte_mismatch",
    }


def build_plan(
    sources: tuple[G4Spec, ...] | None = None,
    ledger_path: Path = LEDGER_PATH,
) -> dict:
    ledger = load_ledger(ledger_path)
    sources = sources or build_g4_sources(ledger)
    ledger_sha = sha256_file(ledger_path)
    ordered_urls, _ = derive_allowlist(ledger)
    entries = []
    for spec in sources:
        entries.append({
            "logical_slot": spec.logical_slot,
            "family": spec.family,
            "record_id": spec.record_id,
            "entity_key": spec.entity_key,
            "capture_url": spec.capture_url,
            "format_provenance": spec.format_provenance,
            "acquisition_raw_path": str(spec.acquisition_raw_path.relative_to(REPO)),
            "acquisition_raw_sha256": spec.acquisition_raw_sha256,
            "refetch_raw_path": f"refetch/{spec.logical_slot}/{spec.raw_name}",
            "refetch_sidecar_path": f"refetch/{spec.logical_slot}/sidecar.json",
            "raw_name": spec.raw_name,
        })
    body = {
        "schema_version": SCHEMA_VERSION,
        "assignment": "G4",
        "seat": SEAT,
        "max_calls": MAX_CALLS,
        "zero_redirects": True,
        "zero_retries": True,
        "no_search_or_substitution": True,
        "promotion_identity_ledger_sha256": ledger_sha,
        "excluded_slots": list(EXCLUDED_B_SLOTS),
        "excluded_b_urls": sorted(EXCLUDED_B_URLS),
        "excluded_discovery_only_urls": sorted(KIMI_DISCOVERY_ONLY_URLS),
        "allowlist_assertions": {
            "excluded_slots_absent": all(
                s.logical_slot not in EXCLUDED_B_SLOTS for s in sources),
            "discovery_only_absent": not any(
                u in KIMI_DISCOVERY_ONLY_URLS for u in ordered_urls),
            "excluded_b_urls_absent": not any(
                u in EXCLUDED_B_URLS for u in ordered_urls),
        },
        "source_count": len(entries),
        "entries": entries,
        "implementation_module_sha256": module_sha256(),
    }
    plan = dict(body)
    plan["plan_sha256"] = sha256_bytes(canonical_json(body).encode())
    return plan


def check_g4_create_once(root: Path = G4_ROOT) -> None:
    if (root / "refetch_report.json").exists():
        raise CaptureRefusal(f"create-once refusal: {root / 'refetch_report.json'}")
    if (root / "identity_audit.json").exists():
        raise CaptureRefusal(f"create-once refusal: {root / 'identity_audit.json'}")
    refetch = root / "refetch"
    if refetch.exists():
        for p in refetch.rglob("*"):
            if p.is_file():
                raise CaptureRefusal(f"create-once refusal: {p}")


def write_plan(root: Path = G4_ROOT, ledger_path: Path = LEDGER_PATH) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    plan_path = root / "plan.json"
    if plan_path.exists():
        raise CaptureRefusal(f"create-once refusal: {plan_path}")
    plan = build_plan(ledger_path=ledger_path)
    for entry in plan["entries"]:
        path = REPO / entry["acquisition_raw_path"]
        if not path.exists():
            raise CaptureRefusal(f"missing acquisition raw: {path}")
        actual = sha256_file(path)
        if actual != entry["acquisition_raw_sha256"]:
            raise CaptureRefusal(
                f"acquisition hash mismatch {entry['logical_slot']}")
    plan_path.write_text(canonical_json(plan) + "\n")
    return plan


def compare_one(
    spec: G4Spec,
    resp: TransportResponse,
    acquisition_body: bytes,
    plan_sha: str,
    selected_modules: set[str],
) -> dict:
    body = resp.body
    raw_sha = sha256_bytes(body)
    acq_sha = sha256_bytes(acquisition_body)
    if acq_sha != spec.acquisition_raw_sha256:
        raise CaptureRefusal(
            f"acquisition body hash drift before compare: {spec.logical_slot}")
    raw_equal = body == acquisition_body
    typed = type_identity(raw_equal)
    requal_ok, requal_reasons, requal_extra = positive_requalification(
        spec, body, resp, selected_modules)

    alias_info: dict = {"fields_inspected": [], "aliases": []}
    if spec.family == "F":
        alias_info = {"fields_inspected": [], "aliases": []}
    else:
        fmt = _alias_format(spec)
        try:
            if spec.family in ("A", "B", "D", "E") or spec.logical_slot.startswith("P"):
                parsed_alias = json.loads(body.decode("utf-8"))
            elif spec.family == "C":
                parsed_alias = json.loads(body.decode("utf-8"))
            else:
                parsed_alias = {}
            alias_info = extract_aliases(parsed_alias, fmt)
        except (json.JSONDecodeError, UnicodeDecodeError):
            alias_info = {"fields_inspected": [], "aliases": [], "parse_error": True}

    row: dict = {
        "logical_slot": spec.logical_slot,
        "family": spec.family,
        "record_id": spec.record_id,
        "entity_key": spec.entity_key,
        "capture_url": spec.capture_url,
        "http_status": resp.status,
        "redirect_refused": resp.redirect_refused,
        "redirect_chain": list(resp.redirect_chain),
        "final_url": resp.url,
        "content_type": resp.headers.get("content-type"),
        "raw_byte_length": len(body),
        "refetch_raw_sha256": raw_sha,
        "acquisition_raw_sha256": acq_sha,
        "positive_requalification_pass": requal_ok,
        "requalification_reasons": requal_reasons,
        "alias_extraction": alias_info,
        "plan_sha256": plan_sha,
        "retrieved_at_utc": utc_now_iso(),
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        **typed,
        **{k: v for k, v in requal_extra.items() if k != "positive_evidence"},
    }
    if "positive_evidence" in requal_extra:
        row["positive_evidence"] = requal_extra["positive_evidence"]
    row["disclaimer"] = (
        "independent G4 refetch + positive requalification; byte identity and "
        "predicate success are separate; drift is not erased by requalification; "
        "no fixture, packet, oracle, engine, or mechanism claim")
    return row


def write_refetch_pair(
    spec: G4Spec,
    resp: TransportResponse,
    acquisition_body: bytes,
    plan_sha: str,
    selected_modules: set[str],
    root: Path = REFETCH_ROOT,
) -> dict:
    adir = root / spec.logical_slot
    adir.mkdir(parents=True, exist_ok=True)
    raw_path = adir / spec.raw_name
    sidecar_path = adir / "sidecar.json"
    if raw_path.exists() or sidecar_path.exists():
        raise CaptureRefusal(f"create-once refusal: {adir} not empty")
    row = compare_one(spec, resp, acquisition_body, plan_sha, selected_modules)
    raw_path.write_bytes(resp.body)
    sidecar_path.write_text(canonical_json(row) + "\n")
    return row


def _person_name_flags(rows: list[dict]) -> list[dict]:
    flags: list[dict] = []
    for r in rows:
        for field in ("entity_key", "record_id"):
            val = r.get(field)
            if isinstance(val, str) and PERSON_NAME_RE.match(val):
                flags.append({"logical_slot": r["logical_slot"], "field": field, "value": val})
    return flags


def build_identity_audit(rows: list[dict], plan: dict) -> dict:
    ids = [r.get("record_id") for r in rows]
    urls = [r.get("capture_url") for r in rows]
    entities = [r.get("entity_key") for r in rows]
    all_aliases: list[str] = []
    for r in rows:
        all_aliases.extend(r.get("alias_extraction", {}).get("aliases") or [])
    counts = {fam: sum(1 for r in rows if r["family"] == fam) for fam in "ABCDEF"}
    person_flags = _person_name_flags(rows)
    assertions = {
        "distinct_record_ids": len(set(ids)) == len(ids) and all(ids),
        "distinct_urls": len(set(urls)) == len(urls) and all(urls),
        "distinct_entities": len(set(entities)) == len(entities) and all(entities),
        "no_alias_cross_row_duplicates": len(all_aliases) == len(set(all_aliases)),
        "promoted_row_count": len(rows) == MAX_CALLS,
        "target_row_count": len(rows) == MAX_CALLS,
        "family_A": counts["A"] == TARGET_FAMILY_COUNTS["A"],
        "family_B": counts["B"] == TARGET_FAMILY_COUNTS["B"],
        "family_C": counts["C"] == TARGET_FAMILY_COUNTS["C"],
        "family_D": counts["D"] == TARGET_FAMILY_COUNTS["D"],
        "family_E": counts["E"] == TARGET_FAMILY_COUNTS["E"],
        "family_F": counts["F"] == TARGET_FAMILY_COUNTS["F"],
        "p_slots": sum(1 for r in rows if r["logical_slot"].startswith("P")) == 6,
        "all_positive_requalification": all(r.get("positive_requalification_pass") for r in rows),
        "no_tbd": not any("TBD" in str(v) for r in rows for v in r.values()),
        "person_name_screen_clear": len(person_flags) == 0,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "assignment": "G4",
        "seat": SEAT,
        "generated_at_utc": utc_now_iso(),
        "plan_sha256": plan["plan_sha256"],
        "promotion_identity_ledger_sha256": plan["promotion_identity_ledger_sha256"],
        "row_count": len(rows),
        "family_counts": counts,
        "target_family_counts": TARGET_FAMILY_COUNTS,
        "person_name_flags": person_flags,
        "assertions": assertions,
        "rows": [
            {
                "logical_slot": r["logical_slot"],
                "family": r["family"],
                "record_id": r["record_id"],
                "entity_key": r["entity_key"],
                "capture_url": r["capture_url"],
                "content_identity": r.get("content_identity"),
                "positive_requalification_pass": r.get("positive_requalification_pass"),
                "alias_extraction": r.get("alias_extraction"),
            }
            for r in rows
        ],
    }


def build_report(rows: list[dict], plan: dict, network_calls: int) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "assignment": "G4",
        "seat": SEAT,
        "generated_at_utc": utc_now_iso(),
        "network_calls": network_calls,
        "max_calls": MAX_CALLS,
        "plan_sha256": plan["plan_sha256"],
        "promotion_identity_ledger_sha256": plan["promotion_identity_ledger_sha256"],
        "implementation_module_sha256": module_sha256(),
        "source_count": len(rows),
        "content_identity_counts": {
            "exact": sum(1 for r in rows if r.get("content_identity") == "exact"),
            "drift": sum(1 for r in rows if r.get("content_identity") == "drift"),
        },
        "positive_requalification_counts": {
            "pass": sum(1 for r in rows if r.get("positive_requalification_pass")),
            "fail": sum(1 for r in rows if not r.get("positive_requalification_pass")),
        },
        "rows": rows,
        "disclaimer": (
            "independent G4 refetch verification only; no K1–K4 acquisition mutation; "
            "no engine contact"),
    }


def dry_run(ledger_path: Path = LEDGER_PATH) -> dict:
    plan = build_plan(ledger_path=ledger_path)
    sources = build_g4_sources(load_ledger(ledger_path))
    ordered, allowlist = derive_allowlist(load_ledger(ledger_path))
    return {
        "mode": "dry_run",
        "network_calls": 0,
        "plan": plan,
        "source_count": plan["source_count"],
        "allowlist_size": len(allowlist),
        "first_url": ordered[0] if ordered else None,
        "last_url": ordered[-1] if ordered else None,
    }


def execute_live(
    transport: Transport | None = None,
    root: Path = G4_ROOT,
    ledger_path: Path = LEDGER_PATH,
    write_plan_if_missing: bool = True,
) -> dict:
    check_g4_create_once(root)
    root.mkdir(parents=True, exist_ok=True)
    plan_path = root / "plan.json"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
    elif write_plan_if_missing:
        plan = write_plan(root, ledger_path)
    else:
        raise CaptureRefusal("plan.json missing; write plan before contact")

    ledger = load_ledger(ledger_path)
    sources = build_g4_sources(ledger)
    if [s.logical_slot for s in sources] != [
            e["logical_slot"] for e in plan["entries"]]:
        raise CaptureRefusal("plan/source slot order mismatch")

    allowlist = frozenset(s.capture_url for s in sources)
    ceiling = CallCeiling(MAX_CALLS)
    refetch_root = root / "refetch"
    refetch_root.mkdir(parents=True, exist_ok=True)

    def wrapped(url: str) -> TransportResponse:
        if transport is None:
            return live_transport(url, ceiling, allowlist)
        ceiling.record()
        return transport(url)

    rows: list[dict] = []
    selected_modules: set[str] = set()
    for spec in sources:
        acquisition_body = spec.acquisition_raw_path.read_bytes()
        resp = wrapped(spec.capture_url)
        row = write_refetch_pair(
            spec, resp, acquisition_body, plan["plan_sha256"],
            selected_modules, root=refetch_root)
        rows.append(row)
        if spec.family == "D" and row.get("positive_requalification_pass"):
            pe = row.get("positive_evidence") or {}
            mod = pe.get("module")
            if isinstance(mod, str):
                selected_modules.add(mod)

    report = build_report(rows, plan, network_calls=ceiling.count)
    report_path = root / "refetch_report.json"
    if report_path.exists():
        raise CaptureRefusal(f"create-once refusal: {report_path}")
    report_path.write_text(canonical_json(report) + "\n")

    audit = build_identity_audit(rows, plan)
    audit_path = root / "identity_audit.json"
    if audit_path.exists():
        raise CaptureRefusal(f"create-once refusal: {audit_path}")
    audit_path.write_text(canonical_json(audit) + "\n")

    errors = verify_hashes(root)
    if errors:
        raise CaptureRefusal(f"hash verification failed: {errors}")

    return {
        "mode": "execute",
        "network_calls": ceiling.count,
        "report_sha256": sha256_file(report_path),
        "identity_audit_sha256": sha256_file(audit_path),
        "plan_sha256": plan["plan_sha256"],
        "module_sha256": module_sha256(),
        "content_identity_counts": report["content_identity_counts"],
        "positive_requalification_counts": report["positive_requalification_counts"],
        "identity_assertions": audit["assertions"],
        "rows": [
            {
                "logical_slot": r["logical_slot"],
                "content_identity": r["content_identity"],
                "raw_bytes_equal": r["raw_bytes_equal"],
                "positive_requalification_pass": r["positive_requalification_pass"],
                "http_status": r["http_status"],
                "redirect_refused": r["redirect_refused"],
            }
            for r in rows
        ],
    }


def verify_hashes(root: Path = G4_ROOT) -> list[str]:
    errors: list[str] = []
    refetch = root / "refetch"
    if not refetch.exists():
        return ["missing refetch tree"]
    for adir in sorted(p for p in refetch.iterdir() if p.is_dir()):
        sc_path = adir / "sidecar.json"
        if not sc_path.exists():
            errors.append(f"missing sidecar {adir}")
            continue
        sc = json.loads(sc_path.read_text())
        raw_name = sc.get("logical_slot")
        plan_entries = []
        plan_path = root / "plan.json"
        if plan_path.exists():
            plan_entries = json.loads(plan_path.read_text()).get("entries") or []
        raw_file = None
        for e in plan_entries:
            if e.get("logical_slot") == sc.get("logical_slot"):
                raw_file = e.get("raw_name")
                break
        if not raw_file:
            for ext in (".json", ".html", ".rst"):
                candidate = adir / f"raw{ext}"
                if candidate.exists():
                    raw_file = f"raw{ext}"
                    break
        if not raw_file:
            errors.append(f"missing raw file name for {adir}")
            continue
        raw_path = adir / raw_file
        if not raw_path.exists():
            errors.append(f"missing raw {raw_path}")
            continue
        actual = sha256_file(raw_path)
        if actual != sc.get("refetch_raw_sha256"):
            errors.append(
                f"hash mismatch {raw_path}: {actual} != "
                f"{sc.get('refetch_raw_sha256')}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="EFC G4 independent 40-record promotion refetch")
    parser.add_argument("--write-plan", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--verify-hashes", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.verify_hashes:
            errors = verify_hashes()
            out = {"mode": "verify", "errors": errors,
                   "module_sha256": module_sha256()}
            print(canonical_json(out))
            return 0 if not errors else 1
        if args.write_plan:
            plan = write_plan()
            out = {"mode": "write_plan", "network_calls": 0,
                   "plan_sha256": plan["plan_sha256"],
                   "module_sha256": module_sha256()}
        elif args.execute:
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
