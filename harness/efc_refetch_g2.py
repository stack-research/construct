"""EFC v0 G2 independent K2 refetch + positive requalification.

Twelve selected K2 sources from k2b/promotion_ledger.json (C01–C06, D01–D06).
One GET per URL, zero retries, refuse redirects, no search/index contact.
Does not modify K2/K2b acquisition trees or promotion ledgers.

Usage:
  python -m harness.efc_refetch_g2                 # dry-run, zero network
  python -m harness.efc_refetch_g2 --write-plan    # create-once plan only
  python -m harness.efc_refetch_g2 --execute       # one live run (create-once)
  python -m harness.efc_refetch_g2 --verify-hashes
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

from harness.efc_capture_k2 import (
    FAMILY_C,
    CSpec,
    CaptureRefusal,
    canonical_json,
    sha256_bytes,
    sha256_file,
    utc_now_iso,
    validate_family_c,
    _iso_date_year_ok,
    _parse_json,
)
from harness.efc_capture_k2b import (
    FROZEN_CANDIDATES,
    DSpec,
    _imports_map,
    _normalize_events,
    qualify_candidate,
)

REPO = Path(__file__).resolve().parent.parent
ACQ = REPO / "corpus" / "efc_calibration" / "_acquisition"
K2_ROOT = ACQ / "k2"
K2B_ROOT = ACQ / "k2b"
G2_ROOT = ACQ / "g2"
REFETCH_ROOT = G2_ROOT / "refetch"
LEDGER_PATH = K2B_ROOT / "promotion_ledger.json"
SCHEMA_VERSION = "efc-g2-refetch-v1"
SEAT = "cursor/grok-4.5"
MAX_CALLS = 12

G2_URLS_ORDERED: tuple[str, ...] = (
    "https://endoflife.date/api/tomcat.json",
    "https://endoflife.date/api/spring-boot.json",
    "https://endoflife.date/api/windows-server.json",
    "https://endoflife.date/api/visual-studio.json",
    "https://endoflife.date/api/esxi.json",
    "https://endoflife.date/api/windows.json",
    "https://vuln.go.dev/ID/GO-2026-4440.json",
    "https://vuln.go.dev/ID/GO-2026-4507.json",
    "https://vuln.go.dev/ID/GO-2026-4535.json",
    "https://vuln.go.dev/ID/GO-2026-4762.json",
    "https://vuln.go.dev/ID/GO-2026-4610.json",
    "https://vuln.go.dev/ID/GO-2026-4958.json",
)
G2_URLS = frozenset(G2_URLS_ORDERED)
_SLOT_ORDER = (
    "C01", "C02", "C03", "C04", "C05", "C06",
    "D01", "D02", "D03", "D04", "D05", "D06",
)


@dataclass(frozen=True)
class G2Spec:
    logical_slot: str
    capture_url: str
    family: str  # C | D
    source_capture_id: str
    source_kind: str
    acquisition_raw_sha256: str
    product_slug: str | None = None
    go_id: str | None = None
    module: str | None = None
    d_spec: DSpec | None = None
    c_spec: CSpec | None = None
    acquisition_locators: tuple[dict, ...] = ()


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
    if url not in G2_URLS:
        raise CaptureRefusal(f"unknown or unauthorized G2 URL: {url}")


def live_transport(url: str, ceiling: CallCeiling | None = None) -> TransportResponse:
    refuse_unknown_url(url)
    if ceiling is not None:
        ceiling.record()
    opener = urllib.request.build_opener(_RefuseRedirect())
    req = urllib.request.Request(
        url, headers={"Accept": "*/*", "User-Agent": "efc-g2-refetch/1"})
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


def acquisition_raw_path(spec: G2Spec) -> Path:
    if spec.family == "C":
        return K2_ROOT / "captures" / spec.source_capture_id / "raw.json"
    return K2B_ROOT / "captures" / spec.source_capture_id / "raw.json"


def acquisition_sidecar_path(spec: G2Spec) -> Path:
    if spec.family == "C":
        return K2_ROOT / "captures" / spec.source_capture_id / "sidecar.json"
    return K2B_ROOT / "captures" / spec.source_capture_id / "sidecar.json"


def _d_spec_by_go_id(go_id: str) -> DSpec:
    for s in FROZEN_CANDIDATES:
        if s.go_id == go_id and s.role == "primary":
            return s
    raise CaptureRefusal(f"no primary DSpec for {go_id}")


def build_g2_sources(ledger: dict | None = None) -> tuple[G2Spec, ...]:
    ledger = ledger or load_ledger()
    by_slot = {m["logical_slot"]: m for m in ledger["logical_slot_mappings"]}
    sources: list[G2Spec] = []
    for i, slot in enumerate(_SLOT_ORDER):
        if slot not in by_slot:
            raise CaptureRefusal(f"ledger missing logical slot {slot}")
        row = by_slot[slot]
        url = G2_URLS_ORDERED[i]
        if slot.startswith("C"):
            cspec = FAMILY_C[i]  # C01..C06 are first six
            if cspec.capture_url != url:
                raise CaptureRefusal(f"C URL mismatch for {slot}")
            sc_path = K2_ROOT / "captures" / row["source_capture_id"] / "sidecar.json"
            sc = json.loads(sc_path.read_text())
            locators = tuple(sc.get("qualifying_locators") or [])
            sources.append(G2Spec(
                logical_slot=slot,
                capture_url=url,
                family="C",
                source_capture_id=row["source_capture_id"],
                source_kind=row["source_kind"],
                acquisition_raw_sha256=row["artifact_hashes"]["raw_sha256"],
                product_slug=cspec.product_slug,
                c_spec=cspec,
                acquisition_locators=locators,
            ))
        else:
            go_id = row["source_go_id"]
            dspec = _d_spec_by_go_id(go_id)
            if dspec.capture_url != url:
                raise CaptureRefusal(f"D URL mismatch for {slot}")
            sources.append(G2Spec(
                logical_slot=slot,
                capture_url=url,
                family="D",
                source_capture_id=row["source_capture_id"],
                source_kind=row["source_kind"],
                acquisition_raw_sha256=row["artifact_hashes"]["raw_sha256"],
                go_id=go_id,
                module=row.get("module") or dspec.module,
                d_spec=dspec,
            ))
    if len(sources) != 12:
        raise CaptureRefusal(f"expected 12 sources, got {len(sources)}")
    return tuple(sources)


def verify_c_locators(data: list, expected: tuple[dict, ...]) -> list[dict]:
    """Independently verify each preserved acquisition locator still holds."""
    results: list[dict] = []
    for loc in expected:
        idx = loc["array_index"]
        field = loc["field"]
        expected_value = loc["value"]
        cycle = loc["cycle"]
        row: dict = {
            "array_index": idx,
            "cycle": cycle,
            "field": field,
            "expected_value": expected_value,
            "present": False,
            "actual_value": None,
            "iso_2026_or_2027": False,
            "exact_match": False,
            "boolean_or_null_rejected": False,
        }
        if not isinstance(data, list) or idx < 0 or idx >= len(data):
            results.append(row)
            continue
        item = data[idx]
        if not isinstance(item, dict):
            results.append(row)
            continue
        actual = item.get(field)
        row["actual_value"] = actual
        if isinstance(actual, bool) or actual is None:
            row["boolean_or_null_rejected"] = True
            results.append(row)
            continue
        ok, exact = _iso_date_year_ok(actual)
        row["iso_2026_or_2027"] = ok
        row["present"] = True
        row["exact_match"] = (
            ok and exact == expected_value
            and item.get("cycle") == cycle
        )
        results.append(row)
    return results


def positive_d_evidence(spec: DSpec, report: dict) -> dict:
    """Recompute and record every positive qualification field (not just verdict)."""
    published = report.get("published")
    db = report.get("database_specific") or {}
    review_status = db.get("review_status")
    affected = report.get("affected") or []
    aff0 = affected[0] if affected and isinstance(affected[0], dict) else None
    pkg = (aff0 or {}).get("package") or {}
    ranges = (aff0 or {}).get("ranges") or []
    rng0 = ranges[0] if ranges and isinstance(ranges[0], dict) else None
    events = _normalize_events((rng0 or {}).get("events") or [])
    expected_events = [dict(e) for e in spec.range_events]
    eco = (aff0 or {}).get("ecosystem_specific") or {}
    imp_map = _imports_map(eco.get("imports") or [])
    expected_imports = {path: list(syms) for path, syms in spec.imports}
    import_results = {}
    for path, expected_syms in expected_imports.items():
        actual = imp_map.get(path)
        import_results[path] = {
            "expected_symbols": expected_syms,
            "actual_symbols": actual,
            "match": actual == expected_syms,
            "nonempty": bool(actual),
        }
    has_fixed = any("fixed" in e for e in events)
    evidence = {
        "id": report.get("id"),
        "id_match": report.get("id") == spec.go_id,
        "published": published,
        "publication_2026": (
            isinstance(published, str) and published.startswith("2026")
        ),
        "review_status": review_status,
        "reviewed": review_status == "REVIEWED",
        "selected_affected_index": 0,
        "affected_count": len(affected) if isinstance(affected, list) else 0,
        "ecosystem": pkg.get("ecosystem"),
        "ecosystem_is_go": pkg.get("ecosystem") == "Go",
        "module": pkg.get("name"),
        "module_expected": spec.module,
        "module_match": pkg.get("name") == spec.module,
        "range_type": (rng0 or {}).get("type"),
        "range_type_semver": (rng0 or {}).get("type") == "SEMVER",
        "range_events": events,
        "range_events_expected": expected_events,
        "range_events_match": events == expected_events,
        "has_finite_fixed": has_fixed,
        "imports": import_results,
        "all_imports_match": all(v["match"] for v in import_results.values()),
        # Conjunction: id/module/range/imports all drawn from affected[0].
        "same_affected_object_conjunction": aff0 is not None,
    }
    ok, reasons, _ = qualify_candidate(
        spec, report, http_status=200, redirect_refused=False,
        selected_modules=set(),
    )
    # Re-qualify without module_already_selected for per-record evidence;
    # distinct-module check is applied across the batch separately.
    evidence["qualification_pass_alone"] = ok
    evidence["qualification_reasons_alone"] = reasons
    positive_ok = (
        evidence["id_match"]
        and evidence["publication_2026"]
        and evidence["reviewed"]
        and evidence["ecosystem_is_go"]
        and evidence["module_match"]
        and evidence["range_type_semver"]
        and evidence["range_events_match"]
        and evidence["has_finite_fixed"]
        and evidence["all_imports_match"]
        and evidence["same_affected_object_conjunction"]
    )
    evidence["positive_requalification_pass"] = positive_ok
    return evidence


def type_identity(raw_equal: bool, parsed_equal: bool,
                  field_diffs: list[dict]) -> dict:
    if raw_equal:
        return {
            "content_identity": "exact",
            "raw_bytes_equal": True,
            "parsed_objects_equal": parsed_equal,
            "drift_type": None,
            "field_diffs": [],
            "raw_drift_erased_by_parsed_equality": False,
        }
    if parsed_equal:
        drift_type = "json_key_order_only"
    else:
        drift_type = "json_parsed_diff"
    return {
        "content_identity": "drift",
        "raw_bytes_equal": False,
        "parsed_objects_equal": parsed_equal,
        "drift_type": drift_type,
        "field_diffs": field_diffs,
        "raw_drift_erased_by_parsed_equality": False,
    }


def _parsed_field_diffs_c(acq: object, ref: object) -> list[dict]:
    if acq == ref:
        return []
    # Bounded: only report top-level length / locator-affecting differences.
    diffs: list[dict] = []
    if type(acq) != type(ref):
        return [{"field": "type", "acquisition": type(acq).__name__,
                 "refetch": type(ref).__name__}]
    if isinstance(acq, list) and isinstance(ref, list):
        if len(acq) != len(ref):
            diffs.append({"field": "array_length",
                          "acquisition": len(acq), "refetch": len(ref)})
        for i, (a, r) in enumerate(zip(acq, ref)):
            if a != r:
                diffs.append({"field": f"item[{i}]", "equal": False})
                if len(diffs) >= 20:
                    break
    return diffs


def build_plan(sources: tuple[G2Spec, ...] | None = None,
               ledger_path: Path = LEDGER_PATH) -> dict:
    sources = sources or build_g2_sources(load_ledger(ledger_path))
    ledger_sha = sha256_file(ledger_path)
    entries = []
    for spec in sources:
        acq_path = acquisition_raw_path(spec)
        entry = {
            "logical_slot": spec.logical_slot,
            "capture_url": spec.capture_url,
            "family": spec.family,
            "source_capture_id": spec.source_capture_id,
            "source_kind": spec.source_kind,
            "acquisition_raw_path": str(acq_path.relative_to(REPO)),
            "acquisition_raw_sha256": spec.acquisition_raw_sha256,
            "refetch_raw_path": f"refetch/{spec.logical_slot}/raw.json",
            "refetch_sidecar_path": f"refetch/{spec.logical_slot}/sidecar.json",
        }
        if spec.family == "C":
            entry["product_slug"] = spec.product_slug
            entry["acquisition_locator_count"] = len(spec.acquisition_locators)
        else:
            entry["go_id"] = spec.go_id
            entry["module"] = spec.module
        entries.append(entry)
    body = {
        "schema_version": SCHEMA_VERSION,
        "assignment": "G2",
        "seat": SEAT,
        "max_calls": MAX_CALLS,
        "zero_redirects": True,
        "zero_retries": True,
        "no_index_contact": True,
        "promotion_ledger_sha256": ledger_sha,
        "source_count": len(entries),
        "entries": entries,
    }
    plan = dict(body)
    plan["plan_sha256"] = sha256_bytes(canonical_json(body).encode())
    return plan


def check_g2_create_once(root: Path = G2_ROOT) -> None:
    if (root / "refetch_report.json").exists():
        raise CaptureRefusal(
            f"create-once refusal: {root / 'refetch_report.json'}")
    refetch = root / "refetch"
    if refetch.exists():
        for p in refetch.rglob("*"):
            if p.is_file():
                raise CaptureRefusal(f"create-once refusal: {p}")


def write_plan(root: Path = G2_ROOT, ledger_path: Path = LEDGER_PATH) -> dict:
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


def compare_one(spec: G2Spec, resp: TransportResponse,
                acquisition_body: bytes, plan_sha: str,
                selected_modules_so_far: set[str]) -> dict:
    body = resp.body
    raw_sha = sha256_bytes(body)
    acq_sha = sha256_bytes(acquisition_body)
    if acq_sha != spec.acquisition_raw_sha256:
        raise CaptureRefusal(
            f"acquisition body hash drift before compare: {spec.logical_slot}")
    raw_equal = body == acquisition_body

    try:
        acq_obj = _parse_json(acquisition_body)
        acq_parse_ok = True
    except (json.JSONDecodeError, UnicodeDecodeError):
        acq_obj = None
        acq_parse_ok = False
    try:
        ref_obj = _parse_json(body)
        ref_parse_ok = True
    except (json.JSONDecodeError, UnicodeDecodeError):
        ref_obj = None
        ref_parse_ok = False
    parsed_equal = acq_parse_ok and ref_parse_ok and acq_obj == ref_obj

    row: dict = {
        "logical_slot": spec.logical_slot,
        "capture_url": spec.capture_url,
        "family": spec.family,
        "source_capture_id": spec.source_capture_id,
        "source_kind": spec.source_kind,
        "http_status": resp.status,
        "redirect_refused": resp.redirect_refused,
        "redirect_chain": list(resp.redirect_chain),
        "final_url": resp.url,
        "content_type": resp.headers.get("content-type"),
        "raw_byte_length": len(body),
        "refetch_raw_sha256": raw_sha,
        "acquisition_raw_sha256": acq_sha,
        "json_parse_ok": ref_parse_ok,
        "plan_sha256": plan_sha,
        "retrieved_at_utc": utc_now_iso(),
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
    }

    if spec.family == "C":
        assert spec.c_spec is not None
        verdict, matches, failures = validate_family_c(
            body, spec.c_spec, resp.url if not resp.redirect_refused else spec.capture_url)
        if resp.redirect_refused:
            failures = list(failures) + ["redirect_refused"]
            verdict = "fail"
        if resp.status != 200:
            failures = list(failures) + ["http_not_200"]
            verdict = "fail"
        locator_checks = verify_c_locators(
            ref_obj if isinstance(ref_obj, list) else [],
            spec.acquisition_locators,
        )
        all_locators_hold = (
            bool(locator_checks)
            and all(c["exact_match"] for c in locator_checks)
        )
        field_diffs = (
            [] if parsed_equal
            else _parsed_field_diffs_c(acq_obj, ref_obj)
        )
        typed = type_identity(raw_equal, parsed_equal, field_diffs)
        row.update({
            "product_slug": spec.product_slug,
            "validation_verdict": verdict,
            "validation_failures": failures,
            "requalified_locators": matches,
            "acquisition_locators": list(spec.acquisition_locators),
            "locator_checks": locator_checks,
            "all_acquisition_locators_hold": all_locators_hold,
            "positive_requalification_pass": (
                verdict == "pass" and all_locators_hold
                and not resp.redirect_refused and resp.status == 200
            ),
            **typed,
        })
    else:
        assert spec.d_spec is not None
        if not isinstance(ref_obj, dict):
            evidence = {
                "positive_requalification_pass": False,
                "json_not_object": True,
            }
            ok = False
            reasons = ["json_not_object"]
        else:
            evidence = positive_d_evidence(spec.d_spec, ref_obj)
            # Batch distinct-module check.
            mod = evidence.get("module")
            module_distinct = mod not in selected_modules_so_far
            evidence["module_distinct_in_batch"] = module_distinct
            if not module_distinct:
                evidence["positive_requalification_pass"] = False
            ok, reasons, _ = qualify_candidate(
                spec.d_spec, ref_obj,
                http_status=resp.status,
                redirect_refused=resp.redirect_refused,
                selected_modules=selected_modules_so_far,
            )
            evidence["batch_qualification_pass"] = ok
            evidence["batch_qualification_reasons"] = reasons
        # Bounded diffs for identity fields if parsed differs.
        field_diffs: list[dict] = []
        if not parsed_equal and isinstance(acq_obj, dict) and isinstance(ref_obj, dict):
            for key in ("id", "published"):
                if acq_obj.get(key) != ref_obj.get(key):
                    field_diffs.append({
                        "field": key,
                        "acquisition": acq_obj.get(key),
                        "refetch": ref_obj.get(key),
                    })
            a_db = (acq_obj.get("database_specific") or {}).get("review_status")
            r_db = (ref_obj.get("database_specific") or {}).get("review_status")
            if a_db != r_db:
                field_diffs.append({
                    "field": "database_specific.review_status",
                    "acquisition": a_db, "refetch": r_db,
                })
        typed = type_identity(raw_equal, parsed_equal, field_diffs)
        row.update({
            "go_id": spec.go_id,
            "module_expected": spec.module,
            "positive_evidence": evidence,
            "positive_requalification_pass": evidence.get(
                "positive_requalification_pass", False),
            "batch_qualification_pass": evidence.get(
                "batch_qualification_pass", False),
            **typed,
        })

    row["disclaimer"] = (
        "independent G2 refetch + positive requalification; typed drift is not "
        "a repair; parsed equality does not erase raw drift; no fixture, packet, "
        "oracle, engine, or mechanism claim"
    )
    return row


def write_refetch_pair(spec: G2Spec, resp: TransportResponse,
                       acquisition_body: bytes, plan_sha: str,
                       selected_modules_so_far: set[str],
                       root: Path = REFETCH_ROOT) -> dict:
    adir = root / spec.logical_slot
    adir.mkdir(parents=True, exist_ok=True)
    raw_path = adir / "raw.json"
    sidecar_path = adir / "sidecar.json"
    if raw_path.exists() or sidecar_path.exists():
        raise CaptureRefusal(f"create-once refusal: {adir} not empty")
    row = compare_one(
        spec, resp, acquisition_body, plan_sha, selected_modules_so_far)
    raw_path.write_bytes(resp.body)
    sidecar_path.write_text(canonical_json(row) + "\n")
    return row


def build_report(rows: list[dict], plan: dict, network_calls: int) -> dict:
    d_modules = []
    for r in rows:
        if r["family"] == "D":
            pe = r.get("positive_evidence") or {}
            d_modules.append(pe.get("module"))
    return {
        "schema_version": SCHEMA_VERSION,
        "assignment": "G2",
        "seat": SEAT,
        "generated_at_utc": utc_now_iso(),
        "network_calls": network_calls,
        "max_calls": MAX_CALLS,
        "plan_sha256": plan["plan_sha256"],
        "promotion_ledger_sha256": plan["promotion_ledger_sha256"],
        "source_count": len(rows),
        "content_identity_counts": {
            "exact": sum(1 for r in rows if r.get("content_identity") == "exact"),
            "drift": sum(1 for r in rows if r.get("content_identity") == "drift"),
        },
        "positive_requalification_counts": {
            "pass": sum(1 for r in rows if r.get("positive_requalification_pass")),
            "fail": sum(1 for r in rows if not r.get("positive_requalification_pass")),
        },
        "family_c_pass_count": sum(
            1 for r in rows if r["family"] == "C"
            and r.get("positive_requalification_pass")),
        "family_d_pass_count": sum(
            1 for r in rows if r["family"] == "D"
            and r.get("positive_requalification_pass")),
        "d_modules": d_modules,
        "d_modules_distinct": len(d_modules) == len(set(d_modules)),
        "rows": rows,
        "disclaimer": (
            "independent G2 refetch verification only; no K1/K3/K4 refetch; "
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
                 root: Path = G2_ROOT,
                 ledger_path: Path = LEDGER_PATH,
                 write_plan_if_missing: bool = True) -> dict:
    check_g2_create_once(root)
    root.mkdir(parents=True, exist_ok=True)
    plan_path = root / "plan.json"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
    elif write_plan_if_missing:
        plan = write_plan(root, ledger_path)
    else:
        raise CaptureRefusal("plan.json missing; write plan before contact")

    sources = build_g2_sources(load_ledger(ledger_path))
    if [s.logical_slot for s in sources] != [
            e["logical_slot"] for e in plan["entries"]]:
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
    selected_modules: set[str] = set()
    for spec in sources:
        acq_path = acquisition_raw_path(spec)
        acquisition_body = acq_path.read_bytes()
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

    errors = verify_hashes(root)
    if errors:
        raise CaptureRefusal(f"hash verification failed: {errors}")

    return {
        "mode": "execute",
        "network_calls": ceiling.count,
        "report_sha256": sha256_file(report_path),
        "content_identity_counts": report["content_identity_counts"],
        "positive_requalification_counts": report[
            "positive_requalification_counts"],
        "rows": [
            {
                "logical_slot": r["logical_slot"],
                "content_identity": r["content_identity"],
                "raw_bytes_equal": r["raw_bytes_equal"],
                "positive_requalification_pass": r[
                    "positive_requalification_pass"],
                "http_status": r["http_status"],
                "redirect_refused": r["redirect_refused"],
            }
            for r in rows
        ],
    }


def verify_hashes(root: Path = G2_ROOT) -> list[str]:
    errors: list[str] = []
    refetch = root / "refetch"
    if not refetch.exists():
        return ["missing refetch tree"]
    for adir in sorted(p for p in refetch.iterdir() if p.is_dir()):
        sc_path = adir / "sidecar.json"
        raw_path = adir / "raw.json"
        if not sc_path.exists() or not raw_path.exists():
            errors.append(f"missing pair in {adir}")
            continue
        sc = json.loads(sc_path.read_text())
        actual = sha256_file(raw_path)
        if actual != sc.get("refetch_raw_sha256"):
            errors.append(
                f"hash mismatch {raw_path}: {actual} != "
                f"{sc.get('refetch_raw_sha256')}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="EFC G2 independent K2 refetch + positive requalification")
    parser.add_argument("--write-plan", action="store_true")
    parser.add_argument("--execute", action="store_true")
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
