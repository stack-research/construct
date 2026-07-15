"""EFC v0 G3 independent K3 refetch verification — pre-pin acquisition QC only.

Ten selected K3 sources from promotion ledger v2. One GET per URL, zero retries,
zero redirects, no search, no substitution. Does not modify K3/K3c/K3d acquisition
artifacts or promotion ledgers.

Usage:
  python -m harness.efc_refetch_g3                 # dry-run plan, zero network
  python -m harness.efc_refetch_g3 --write-plan    # create-once plan only
  python -m harness.efc_refetch_g3 --execute       # one live run (create-once)
  python -m harness.efc_refetch_g3 --verify-hashes
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

from harness import efc_capture_k3 as k3
from harness import efc_capture_k3c as k3c
from harness.efc_capture_k3 import (
    CaptureRefusal,
    K3Spec,
    canonical_json,
    extract_family_f,
    sha256_bytes,
    sha256_file,
    utc_now_iso,
    validate_family_e,
    _parse_json,
)

REPO = Path(__file__).resolve().parent.parent
ACQ = REPO / "corpus" / "efc_calibration" / "_acquisition"
K3_ROOT = ACQ / "k3"
K3C_ROOT = ACQ / "k3c"
K3D_ROOT = ACQ / "k3d"
G3_ROOT = ACQ / "g3"
REFETCH_ROOT = G3_ROOT / "refetch"
LEDGER_PATH = K3D_ROOT / "promotion_ledger_v2.json"
SCHEMA_VERSION = "efc-g3-refetch-v1"
SEAT = "cursor/grok-4.5"
MAX_CALLS = 10


@dataclass(frozen=True)
class G3Spec:
    logical_slot: str
    capture_url: str
    family: str  # E | F
    entity_kind: str  # exception | license | html | rst
    record_id: str
    source_capture_id: str
    source_kind: str
    raw_name: str
    acquisition_raw_sha256: str


# Exact ten URLs from Assignment G3, ordered.
G3_URLS_ORDERED: tuple[str, ...] = (
    "https://raw.githubusercontent.com/spdx/license-list-data/main/json/exceptions/Classpath-exception-2.0.json",
    "https://raw.githubusercontent.com/spdx/license-list-data/main/json/exceptions/LLVM-exception.json",
    "https://raw.githubusercontent.com/spdx/license-list-data/main/json/exceptions/Bootloader-exception.json",
    "https://raw.githubusercontent.com/spdx/license-list-data/main/json/details/BSL-1.0.json",
    "https://raw.githubusercontent.com/spdx/license-list-data/main/json/details/MPL-2.0.json",
    "https://raw.githubusercontent.com/spdx/license-list-data/main/json/details/EPL-2.0.json",
    "https://kubernetes.io/docs/reference/using-api/deprecation-guide/",
    "https://docs.djangoproject.com/en/6.0/releases/5.0/",
    "https://raw.githubusercontent.com/pallets/flask/2.3.0/CHANGES.rst",
    "https://guides.rubyonrails.org/7_2_release_notes.html",
)

G3_URLS = frozenset(G3_URLS_ORDERED)

_SLOT_META: dict[str, dict] = {
    "E01": {"family": "E", "entity_kind": "exception",
            "record_id": "Classpath-exception-2.0", "raw_name": "raw.json"},
    "E02": {"family": "E", "entity_kind": "exception",
            "record_id": "LLVM-exception", "raw_name": "raw.json"},
    "E03": {"family": "E", "entity_kind": "exception",
            "record_id": "Bootloader-exception", "raw_name": "raw.json"},
    "E04": {"family": "E", "entity_kind": "license",
            "record_id": "BSL-1.0", "raw_name": "raw.json"},
    "E05": {"family": "E", "entity_kind": "license",
            "record_id": "MPL-2.0", "raw_name": "raw.json"},
    "E06": {"family": "E", "entity_kind": "license",
            "record_id": "EPL-2.0", "raw_name": "raw.json"},
    "F01": {"family": "F", "entity_kind": "html",
            "record_id": "kubernetes-deprecation-v1.32-flowcontrol",
            "raw_name": "raw.html"},
    "F02": {"family": "F", "entity_kind": "html",
            "record_id": "django-5.0-pytz-removal", "raw_name": "raw.html"},
    "F03": {"family": "F", "entity_kind": "rst",
            "record_id": "flask-2.3.0-env-removal", "raw_name": "raw.rst"},
    "F04": {"family": "F", "entity_kind": "html",
            "record_id": "rails-7.2-dependency-loading-removal",
            "raw_name": "raw.html"},
}

_SLOT_ORDER = ("E01", "E02", "E03", "E04", "E05", "E06",
               "F01", "F02", "F03", "F04")


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


def refuse_unknown_url(url: str) -> None:
    if url not in G3_URLS:
        raise CaptureRefusal(f"unknown or unauthorized G3 URL: {url}")


def live_transport(url: str, ceiling: CallCeiling | None = None) -> TransportResponse:
    refuse_unknown_url(url)
    if ceiling is not None:
        ceiling.record()
    opener = urllib.request.build_opener(_RefuseRedirect())
    req = urllib.request.Request(
        url, headers={"Accept": "*/*", "User-Agent": "efc-g3-refetch/1"})
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


def load_ledger(path: Path = LEDGER_PATH) -> dict:
    if not path.exists():
        raise CaptureRefusal(f"missing promotion ledger: {path}")
    return json.loads(path.read_text())


def acquisition_raw_path(source_capture_id: str, source_kind: str,
                         raw_name: str) -> Path:
    if source_kind in ("k3_original", "k3c_reconciled"):
        return K3_ROOT / "captures" / source_capture_id / raw_name
    if source_kind == "k3c_corrected":
        return K3C_ROOT / "captures" / source_capture_id / raw_name
    raise CaptureRefusal(f"unknown source_kind: {source_kind}")


def build_g3_sources(ledger: dict | None = None) -> tuple[G3Spec, ...]:
    ledger = ledger or load_ledger()
    by_slot = {m["logical_slot"]: m for m in ledger["logical_slot_mappings"]}
    sources: list[G3Spec] = []
    for i, slot in enumerate(_SLOT_ORDER):
        if slot not in by_slot:
            raise CaptureRefusal(f"ledger missing logical slot {slot}")
        meta = _SLOT_META[slot]
        row = by_slot[slot]
        url = G3_URLS_ORDERED[i]
        sources.append(G3Spec(
            logical_slot=slot,
            capture_url=url,
            family=meta["family"],
            entity_kind=meta["entity_kind"],
            record_id=meta["record_id"],
            source_capture_id=row["source_capture_id"],
            source_kind=row["source_kind"],
            raw_name=meta["raw_name"],
            acquisition_raw_sha256=row["artifact_hashes"]["raw_sha256"],
        ))
    if len(sources) != 10:
        raise CaptureRefusal(f"expected 10 sources, got {len(sources)}")
    return tuple(sources)


def _to_e_spec(spec: G3Spec) -> K3Spec:
    return K3Spec(
        capture_id=spec.source_capture_id,
        family="E",
        capture_url=spec.capture_url,
        record_id=spec.record_id,
        entity_kind=spec.entity_kind,
        raw_name=spec.raw_name,
    )


def _to_f_spec(spec: G3Spec) -> K3Spec:
    # extract_family_f branches on original K3 capture ids.
    cid = {
        "F01": "capF-01",
        "F02": "capF-02",
        "F03": "capF-03",
        "F04": "capF-04",
    }[spec.logical_slot]
    return K3Spec(
        capture_id=cid,
        family="F",
        capture_url=spec.capture_url,
        record_id=spec.record_id,
        entity_kind="html" if spec.entity_kind == "html" else "rst",
        raw_name=spec.raw_name,
    )


def extract_e_fields(body: bytes, spec: G3Spec) -> dict:
    data, parse_err = _parse_json(body)
    k3spec = _to_e_spec(spec)
    http_ok = True
    verdict, failures, meta = validate_family_e(
        k3spec, data, http_ok, parse_err, False)
    return {
        "json_parse_ok": data is not None and parse_err is None,
        "parse_error": parse_err,
        "validation_verdict": verdict,
        "validation_failures": failures,
        "canonical_id": meta.get("licenseExceptionId") or meta.get("licenseId"),
        "text_present": meta.get("licenseExceptionText_present")
        if spec.entity_kind == "exception"
        else meta.get("licenseText_present"),
        "licenseExceptionId": meta.get("licenseExceptionId"),
        "licenseId": meta.get("licenseId"),
        "parsed_object": data,
    }


def extract_f_fields(body: bytes, spec: G3Spec) -> dict:
    if spec.logical_slot == "F03":
        extract, failures = k3c.extract_f03c_rst(body)
    else:
        extract, failures = extract_family_f(_to_f_spec(spec), body)
    return {
        "extract_failures": failures,
        "normalized_text_sha256": extract.get("normalized_text_sha256"),
        "section_text_sha256": extract.get("section_text_sha256"),
        "matched_statement": extract.get("matched_statement"),
        "named_surface": extract.get("named_surface"),
        "framework_version": extract.get("framework_version"),
        "relation": extract.get("relation"),
        "official_record_date": extract.get("official_record_date"),
        "locator_method": extract.get("locator_method"),
        "heading_anchor": extract.get("heading_anchor"),
        "extract": extract,
    }


def e_parsed_diff(acq: dict, ref: dict) -> list[dict]:
    diffs: list[dict] = []
    for key in ("canonical_id", "text_present", "licenseExceptionId", "licenseId",
                "json_parse_ok"):
        if acq.get(key) != ref.get(key):
            diffs.append({"field": key, "acquisition": acq.get(key),
                          "refetch": ref.get(key)})
    # Full parsed-object equality is typed separately; surface key diffs for
    # identity/text only here.
    a_obj = acq.get("parsed_object") or {}
    r_obj = ref.get("parsed_object") or {}
    for key in ("licenseExceptionId", "licenseId", "licenseExceptionText",
                "licenseText"):
        if a_obj.get(key) != r_obj.get(key):
            # For text, compare presence/hash rather than dumping full text.
            if key in ("licenseExceptionText", "licenseText"):
                a_t = a_obj.get(key)
                r_t = r_obj.get(key)
                diffs.append({
                    "field": key,
                    "acquisition_sha256": (
                        sha256_bytes(a_t.encode("utf-8"))
                        if isinstance(a_t, str) else None),
                    "refetch_sha256": (
                        sha256_bytes(r_t.encode("utf-8"))
                        if isinstance(r_t, str) else None),
                    "equal": a_t == r_t,
                })
            else:
                diffs.append({"field": key, "acquisition": a_obj.get(key),
                              "refetch": r_obj.get(key)})
    return diffs


def f_field_diff(acq: dict, ref: dict) -> list[dict]:
    diffs: list[dict] = []
    for key in ("normalized_text_sha256", "section_text_sha256",
                "matched_statement", "named_surface", "framework_version",
                "relation", "official_record_date"):
        if acq.get(key) != ref.get(key):
            diffs.append({"field": key, "acquisition": acq.get(key),
                          "refetch": ref.get(key)})
    return diffs


def type_content_identity(family: str, raw_equal: bool,
                          acq_fields: dict, ref_fields: dict) -> dict:
    """Type raw vs parsed/normalized identity without declaring drift harmless."""
    if family == "E":
        a_obj = acq_fields.get("parsed_object")
        r_obj = ref_fields.get("parsed_object")
        parsed_equal = (
            a_obj is not None and r_obj is not None and a_obj == r_obj
        )
        field_diffs = e_parsed_diff(acq_fields, ref_fields)
        if raw_equal:
            identity = "exact"
            drift_type = None
        elif parsed_equal:
            identity = "drift"
            drift_type = "json_key_order_only"
        else:
            identity = "drift"
            drift_type = "json_parsed_diff"
        return {
            "content_identity": identity,
            "raw_bytes_equal": raw_equal,
            "parsed_objects_equal": parsed_equal,
            "drift_type": drift_type,
            "field_diffs": field_diffs,
        }

    # Family F: raw and normalized/section levels are independent.
    field_diffs = f_field_diff(acq_fields, ref_fields)
    norm_eq = (acq_fields.get("normalized_text_sha256")
               == ref_fields.get("normalized_text_sha256"))
    sec_eq = (acq_fields.get("section_text_sha256")
              == ref_fields.get("section_text_sha256"))
    stmt_eq = (acq_fields.get("matched_statement")
               == ref_fields.get("matched_statement"))
    if raw_equal:
        identity = "exact"
        drift_type = None
    else:
        identity = "drift"
        if norm_eq and sec_eq and stmt_eq and not field_diffs:
            drift_type = "raw_byte_drift_normalized_and_section_match"
        elif norm_eq and not sec_eq:
            drift_type = "raw_and_section_drift_normalized_match"
        elif not norm_eq:
            drift_type = "raw_and_normalized_drift"
        else:
            drift_type = "raw_byte_drift_with_field_diffs"
    return {
        "content_identity": identity,
        "raw_bytes_equal": raw_equal,
        "normalized_equal": norm_eq,
        "section_equal": sec_eq,
        "matched_statement_equal": stmt_eq,
        "drift_type": drift_type,
        "field_diffs": field_diffs,
        # Explicit non-claim: normalized/section match does not erase raw drift.
        "raw_drift_erased_by_normalized_match": False,
    }


def build_plan(sources: tuple[G3Spec, ...] | None = None,
               ledger_path: Path = LEDGER_PATH) -> dict:
    sources = sources or build_g3_sources(load_ledger(ledger_path))
    ledger_sha = sha256_file(ledger_path)
    entries = []
    for spec in sources:
        acq_path = acquisition_raw_path(
            spec.source_capture_id, spec.source_kind, spec.raw_name)
        entries.append({
            "logical_slot": spec.logical_slot,
            "capture_url": spec.capture_url,
            "family": spec.family,
            "entity_kind": spec.entity_kind,
            "record_id": spec.record_id,
            "source_capture_id": spec.source_capture_id,
            "source_kind": spec.source_kind,
            "acquisition_raw_path": str(acq_path.relative_to(REPO)),
            "acquisition_raw_sha256": spec.acquisition_raw_sha256,
            "refetch_raw_path": f"refetch/{spec.logical_slot}/{spec.raw_name}",
            "refetch_sidecar_path": f"refetch/{spec.logical_slot}/sidecar.json",
        })
    body = {
        "schema_version": SCHEMA_VERSION,
        "assignment": "G3",
        "seat": SEAT,
        "max_calls": MAX_CALLS,
        "zero_redirects": True,
        "zero_retries": True,
        "promotion_ledger_v2_sha256": ledger_sha,
        "source_count": len(entries),
        "entries": entries,
    }
    plan = dict(body)
    plan["plan_sha256"] = sha256_bytes(canonical_json(body).encode())
    return plan


def check_g3_create_once(root: Path = G3_ROOT) -> None:
    report = root / "refetch_report.json"
    if report.exists():
        raise CaptureRefusal(f"create-once refusal: {report}")
    refetch = root / "refetch"
    if refetch.exists():
        for p in refetch.rglob("*"):
            if p.is_file():
                raise CaptureRefusal(f"create-once refusal: {p}")


def write_plan(root: Path = G3_ROOT, ledger_path: Path = LEDGER_PATH) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    plan_path = root / "plan.json"
    if plan_path.exists():
        raise CaptureRefusal(f"create-once refusal: {plan_path}")
    plan = build_plan(ledger_path=ledger_path)
    # Verify acquisition bytes match ledger pins before any network.
    for entry in plan["entries"]:
        path = REPO / entry["acquisition_raw_path"]
        if not path.exists():
            raise CaptureRefusal(f"missing acquisition raw: {path}")
        actual = sha256_file(path)
        if actual != entry["acquisition_raw_sha256"]:
            raise CaptureRefusal(
                f"acquisition hash mismatch {entry['logical_slot']}: "
                f"{actual} != {entry['acquisition_raw_sha256']}")
    plan_path.write_text(canonical_json(plan) + "\n")
    return plan


def compare_one(spec: G3Spec, resp: TransportResponse,
                acquisition_body: bytes, plan_sha: str) -> dict:
    body = resp.body
    raw_sha = sha256_bytes(body)
    acq_sha = sha256_bytes(acquisition_body)
    if acq_sha != spec.acquisition_raw_sha256:
        raise CaptureRefusal(
            f"acquisition body hash drift before compare: {spec.logical_slot}")
    raw_equal = body == acquisition_body

    row: dict = {
        "logical_slot": spec.logical_slot,
        "capture_url": spec.capture_url,
        "source_capture_id": spec.source_capture_id,
        "source_kind": spec.source_kind,
        "family": spec.family,
        "http_status": resp.status,
        "redirect_refused": resp.redirect_refused,
        "redirect_chain": list(resp.redirect_chain),
        "final_url": resp.url,
        "content_type": resp.headers.get("content-type"),
        "raw_byte_length": len(body),
        "refetch_raw_sha256": raw_sha,
        "acquisition_raw_sha256": acq_sha,
        "raw_bytes_equal": raw_equal,
        "plan_sha256": plan_sha,
    }

    if spec.family == "E":
        acq_fields = extract_e_fields(acquisition_body, spec)
        ref_fields = extract_e_fields(body, spec)
        # Drop parsed_object from sidecar (large); keep hashes/flags.
        typed = type_content_identity("E", raw_equal, acq_fields, ref_fields)
        row.update({
            "json_parse_ok": ref_fields["json_parse_ok"],
            "canonical_id_returned": ref_fields["canonical_id"],
            "canonical_id_expected": spec.record_id,
            "canonical_id_match": ref_fields["canonical_id"] == spec.record_id,
            "text_present": ref_fields["text_present"],
            "validation_verdict": ref_fields["validation_verdict"],
            "validation_failures": ref_fields["validation_failures"],
            **typed,
        })
    else:
        acq_fields = extract_f_fields(acquisition_body, spec)
        ref_fields = extract_f_fields(body, spec)
        typed = type_content_identity("F", raw_equal, acq_fields, ref_fields)
        row.update({
            "normalized_text_sha256": ref_fields["normalized_text_sha256"],
            "section_text_sha256": ref_fields["section_text_sha256"],
            "matched_statement": ref_fields["matched_statement"],
            "named_surface": ref_fields["named_surface"],
            "framework_version": ref_fields["framework_version"],
            "relation": ref_fields["relation"],
            "official_record_date": ref_fields.get("official_record_date"),
            "locator_method": ref_fields.get("locator_method"),
            "heading_anchor": ref_fields.get("heading_anchor"),
            "extract_failures": ref_fields["extract_failures"],
            "acquisition_normalized_text_sha256": acq_fields[
                "normalized_text_sha256"],
            "acquisition_section_text_sha256": acq_fields["section_text_sha256"],
            "acquisition_matched_statement": acq_fields["matched_statement"],
            **typed,
        })

    row["retrieved_at_utc"] = utc_now_iso()
    row["schema_version"] = SCHEMA_VERSION
    row["seat"] = SEAT
    row["disclaimer"] = (
        "independent G3 refetch only; typed drift is not a repair; "
        "normalized/section match does not erase raw-byte drift; "
        "no fixture, packet, oracle, engine, or mechanism claim")
    return row


def write_refetch_pair(spec: G3Spec, resp: TransportResponse,
                       acquisition_body: bytes, plan_sha: str,
                       root: Path = REFETCH_ROOT) -> dict:
    adir = root / spec.logical_slot
    adir.mkdir(parents=True, exist_ok=True)
    raw_path = adir / spec.raw_name
    sidecar_path = adir / "sidecar.json"
    if raw_path.exists() or sidecar_path.exists():
        raise CaptureRefusal(f"create-once refusal: {adir} not empty")
    row = compare_one(spec, resp, acquisition_body, plan_sha)
    raw_path.write_bytes(resp.body)
    sidecar_path.write_text(canonical_json(row) + "\n")
    return row


def build_report(rows: list[dict], plan: dict, network_calls: int) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "assignment": "G3",
        "seat": SEAT,
        "generated_at_utc": utc_now_iso(),
        "network_calls": network_calls,
        "max_calls": MAX_CALLS,
        "plan_sha256": plan["plan_sha256"],
        "promotion_ledger_v2_sha256": plan["promotion_ledger_v2_sha256"],
        "source_count": len(rows),
        "content_identity_counts": {
            "exact": sum(1 for r in rows if r.get("content_identity") == "exact"),
            "drift": sum(1 for r in rows if r.get("content_identity") == "drift"),
        },
        "rows": rows,
        "disclaimer": (
            "independent G3 refetch verification only; no K2/K4 refetch; "
            "no promotion-ledger modification; no engine contact"),
    }


def dry_run(ledger_path: Path = LEDGER_PATH) -> dict:
    plan = build_plan(ledger_path=ledger_path)
    return {
        "mode": "dry_run",
        "network_calls": 0,
        "plan": plan,
        "source_count": plan["source_count"],
    }


def execute_live(transport: Transport | None = None,
                 root: Path = G3_ROOT,
                 ledger_path: Path = LEDGER_PATH,
                 write_plan_if_missing: bool = True) -> dict:
    check_g3_create_once(root)
    root.mkdir(parents=True, exist_ok=True)
    plan_path = root / "plan.json"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
    elif write_plan_if_missing:
        plan = write_plan(root, ledger_path)
    else:
        raise CaptureRefusal("plan.json missing; write plan before contact")

    sources = build_g3_sources(load_ledger(ledger_path))
    if [s.logical_slot for s in sources] != [e["logical_slot"] for e in plan["entries"]]:
        raise CaptureRefusal("plan/source slot order mismatch")

    ceiling = CallCeiling(MAX_CALLS)
    refetch_root = root / "refetch"
    refetch_root.mkdir(parents=True, exist_ok=True)

    def wrapped(url: str) -> TransportResponse:
        if transport is None:
            return live_transport(url, ceiling)
        ceiling.record()
        return transport(url)

    rows: list[dict] = []
    for spec in sources:
        acq_path = acquisition_raw_path(
            spec.source_capture_id, spec.source_kind, spec.raw_name)
        acquisition_body = acq_path.read_bytes()
        resp = wrapped(spec.capture_url)
        row = write_refetch_pair(
            spec, resp, acquisition_body, plan["plan_sha256"],
            root=refetch_root)
        rows.append(row)

    if ceiling.count > MAX_CALLS:
        raise CaptureRefusal("call ceiling exceeded after run")

    report = build_report(rows, plan, network_calls=ceiling.count)
    report_path = root / "refetch_report.json"
    if report_path.exists():
        raise CaptureRefusal(f"create-once refusal: {report_path}")
    report_path.write_text(canonical_json(report) + "\n")

    errors = verify_hashes(root)
    if errors:
        raise CaptureRefusal(f"hash verification failed: {errors}")

    return {
        "mode": "execute",
        "network_calls": ceiling.count,
        "report_sha256": sha256_file(report_path),
        "content_identity_counts": report["content_identity_counts"],
        "rows": [
            {
                "logical_slot": r["logical_slot"],
                "content_identity": r["content_identity"],
                "raw_bytes_equal": r["raw_bytes_equal"],
                "drift_type": r.get("drift_type"),
                "http_status": r["http_status"],
                "redirect_refused": r["redirect_refused"],
            }
            for r in rows
        ],
    }


def verify_hashes(root: Path = G3_ROOT) -> list[str]:
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
        raw_name = _SLOT_META[sc["logical_slot"]]["raw_name"]
        raw_path = adir / raw_name
        if not raw_path.exists():
            errors.append(f"missing raw {raw_path}")
            continue
        actual = sha256_file(raw_path)
        if actual != sc.get("refetch_raw_sha256"):
            errors.append(
                f"hash mismatch {raw_path}: {actual} != {sc.get('refetch_raw_sha256')}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EFC G3 independent K3 refetch")
    parser.add_argument("--write-plan", action="store_true",
                        help="create-once plan only, zero network")
    parser.add_argument("--execute", action="store_true",
                        help="one live create-once refetch of ten sources")
    parser.add_argument("--verify-hashes", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.verify_hashes:
            errors = verify_hashes()
            out = {"mode": "verify", "errors": errors}
            print(canonical_json(out))
            return 0 if not errors else 1
        if args.write_plan:
            plan = write_plan()
            out = {"mode": "write_plan", "network_calls": 0,
                   "plan_sha256": plan["plan_sha256"]}
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
