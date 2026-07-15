"""EFC v0 K2 mechanical acquisition — Family C + Family D.

Six frozen endoflife.date product captures, three Go vuln index GETs,
deterministic candidate-plan derivation (max 24), individual GO-2026 reports
until six qualify or ceiling exhausted.

Usage:
  python -m harness.efc_capture_k2              # dry-run, zero network
  python -m harness.efc_capture_k2 --execute  # one live run (create-once)
  python -m harness.efc_capture_k2 --verify-hashes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

from harness.efc_capture import FROZEN_ATTEMPTS as K1_ATTEMPTS

REPO = Path(__file__).resolve().parent.parent
K2_ROOT = REPO / "corpus" / "efc_calibration" / "_acquisition" / "k2"
SCHEMA_VERSION = "efc-k2-acquisition-v1"
SEAT = "cursor/composer-2.5-capture"
CANDIDATE_CEILING = 24
TARGET_D_QUALIFIERS = 6
ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

INDEX_URLS: tuple[tuple[str, str], ...] = (
    ("db", "https://vuln.go.dev/index/db.json"),
    ("modules", "https://vuln.go.dev/index/modules.json"),
    ("vulns", "https://vuln.go.dev/index/vulns.json"),
)

K1_ENTITY_KEYS: frozenset[str] = frozenset(
    spec.package_expected for spec in K1_ATTEMPTS
)

FAMILY_C_SLUGS: frozenset[str] = frozenset({
    "tomcat", "spring-boot", "windows-server",
    "visual-studio", "esxi", "windows",
})

PRIOR_SCORED_CORPUS: frozenset[str] = frozenset({
    "DEP0033",
    "rw-0001", "rw-0002", "rw-0003", "rw-0003b", "rw-0004",
})

FROZEN_EXCLUDED_ENTITIES: frozenset[str] = (
    K1_ENTITY_KEYS | FAMILY_C_SLUGS | PRIOR_SCORED_CORPUS
    | frozenset({"stdlib", "toolchain"})
)

DERIVATION_RULE = (
    "From modules.json: GO-2026-* rows with nonempty fixed; "
    "join vulns.json; exclude stdlib/toolchain and frozen entities; "
    "sort ids ascending; take first 24."
)


@dataclass(frozen=True)
class CSpec:
    capture_id: str
    product_slug: str
    capture_url: str


FAMILY_C: tuple[CSpec, ...] = (
    CSpec("capC-01", "tomcat",
          "https://endoflife.date/api/tomcat.json"),
    CSpec("capC-02", "spring-boot",
          "https://endoflife.date/api/spring-boot.json"),
    CSpec("capC-03", "windows-server",
          "https://endoflife.date/api/windows-server.json"),
    CSpec("capC-04", "visual-studio",
          "https://endoflife.date/api/visual-studio.json"),
    CSpec("capC-05", "esxi",
          "https://endoflife.date/api/esxi.json"),
    CSpec("capC-06", "windows",
          "https://endoflife.date/api/windows.json"),
)

FROZEN_URLS: frozenset[str] = frozenset(
    [s.capture_url for s in FAMILY_C]
    + [url for _, url in INDEX_URLS]
)


class CaptureRefusal(Exception):
    """Create-once or plan violation."""


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


def module_sha256() -> str:
    return sha256_file(Path(__file__).resolve())


def rel_repo(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def check_create_once(root: Path = K2_ROOT) -> None:
    if root.exists():
        for p in root.rglob("*"):
            if p.is_file():
                raise CaptureRefusal(
                    f"create-once refusal: artifact exists: {p}")


def build_plan(root: Path = K2_ROOT) -> dict:
    body = {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "phase_c": [
            {
                "id": s.capture_id,
                "product_slug": s.product_slug,
                "capture_url": s.capture_url,
                "raw_path": f"captures/{s.capture_id}/raw.json",
                "sidecar_path": f"captures/{s.capture_id}/sidecar.json",
            }
            for s in FAMILY_C
        ],
        "phase_d_indexes": [
            {"name": name, "url": url,
             "raw_path": f"qualification/go_indexes/{name}/raw.json",
             "sidecar_path": f"qualification/go_indexes/{name}/sidecar.json"}
            for name, url in INDEX_URLS
        ],
        "candidate_ceiling": CANDIDATE_CEILING,
        "target_d_qualifiers": TARGET_D_QUALIFIERS,
        "max_total_calls": 6 + 3 + CANDIDATE_CEILING,
        "excluded_entities": sorted(FROZEN_EXCLUDED_ENTITIES),
        "derivation_rule": DERIVATION_RULE,
        "implementation_module_sha256": module_sha256(),
    }
    plan = dict(body)
    plan["plan_sha256"] = sha256_bytes(canonical_json(body).encode())
    return plan


def _parse_json(body: bytes) -> object:
    return json.loads(body.decode("utf-8"))


def _slug_from_eol_url(url: str) -> str | None:
    m = re.search(r"/api/([^/.]+)\.json", url)
    return m.group(1) if m else None


def _iso_date_year_ok(value: object) -> tuple[bool, str | None]:
    if not isinstance(value, str):
        return False, None
    m = ISO_DATE_RE.match(value)
    if not m:
        return False, None
    year = int(m.group(1))
    if year not in (2026, 2027):
        return False, None
    return True, value


def validate_family_c(
    body: bytes, spec: CSpec, final_url: str,
) -> tuple[str, list[dict], list[str]]:
    failures: list[str] = []
    slug = _slug_from_eol_url(final_url)
    if slug != spec.product_slug:
        failures.append("endpoint_slug_mismatch")
    try:
        data = _parse_json(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        failures.append("json_parse_error")
        return "fail", [], failures
    if not isinstance(data, list):
        failures.append("not_top_level_array")
        return "fail", [], failures
    matches: list[dict] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        cycle = item.get("cycle")
        if not isinstance(cycle, str) or not cycle:
            continue
        for field in ("support", "eol"):
            val = item.get(field)
            ok, exact = _iso_date_year_ok(val)
            if ok and exact:
                matches.append({
                    "array_index": idx,
                    "cycle": cycle,
                    "field": field,
                    "value": exact,
                })
    if not matches:
        failures.append("no_qualifying_date_field")
        return "fail", matches, failures
    return "pass", matches, failures


def _entity_collision(module_path: str) -> bool:
    if module_path in FROZEN_EXCLUDED_ENTITIES:
        return True
    if module_path.startswith("rw-"):
        return True
    return False


def derive_candidate_plan(
    modules_body: bytes,
    vulns_body: bytes,
    index_hashes: dict[str, str],
) -> dict:
    modules_data = _parse_json(modules_body)
    vulns_data = _parse_json(vulns_body)
    if not isinstance(modules_data, list) or not isinstance(vulns_data, list):
        raise CaptureRefusal("index parse: expected arrays")

    vuln_ids = {row["id"] for row in vulns_data if isinstance(row, dict)
                and isinstance(row.get("id"), str)}

    id_modules: dict[str, set[str]] = defaultdict(set)
    id_fixed: dict[str, set[str]] = defaultdict(set)

    for entry in modules_data:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if not isinstance(path, str) or not path:
            continue
        for row in entry.get("vulns") or []:
            if not isinstance(row, dict):
                continue
            vid = row.get("id")
            if not isinstance(vid, str) or not vid.startswith("GO-2026-"):
                continue
            fixed = row.get("fixed")
            if not isinstance(fixed, str) or not fixed:
                continue
            id_modules[vid].add(path)
            id_fixed[vid].add(fixed)

    retained: list[dict] = []
    excluded: list[dict] = []
    for vid in sorted(id_modules.keys()):
        if vid not in vuln_ids:
            excluded.append({"id": vid, "reason": "not_in_vulns_index"})
            continue
        paths = sorted(id_modules[vid])
        if not paths:
            excluded.append({"id": vid, "reason": "no_module_path"})
            continue
        if any(p in ("stdlib", "toolchain") for p in paths):
            excluded.append({"id": vid, "reason": "stdlib_or_toolchain"})
            continue
        if any(_entity_collision(p) for p in paths):
            excluded.append({"id": vid, "reason": "frozen_entity_collision"})
            continue
        retained.append({
            "id": vid,
            "module_paths": paths,
            "fixed_values": sorted(id_fixed[vid]),
            "individual_url": f"https://vuln.go.dev/ID/{vid}.json",
        })
        if len(retained) >= CANDIDATE_CEILING:
            break

    body = {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "index_hashes": index_hashes,
        "derivation_rule": DERIVATION_RULE,
        "candidate_ceiling": CANDIDATE_CEILING,
        "candidates": retained,
        "excluded_sample": excluded[:50],
        "candidate_count": len(retained),
        "ceiling_shortfall": len(retained) < CANDIDATE_CEILING,
    }
    plan = dict(body)
    plan["candidate_plan_sha256"] = sha256_bytes(
        canonical_json(body).encode())
    return plan


def _has_finite_range(events: list) -> bool:
    if not isinstance(events, list):
        return False
    has_fixed = any(
        isinstance(e, dict) and isinstance(e.get("fixed"), str) and e["fixed"]
        for e in events)
    has_last = any(
        isinstance(e, dict) and isinstance(e.get("last_affected"), str)
        and e["last_affected"]
        for e in events)
    if has_fixed or has_last:
        return True
    only_introduced = all(
        isinstance(e, dict) and "introduced" in e and "fixed" not in e
        and "last_affected" not in e for e in events)
    if only_introduced and events:
        return False
    return False


def qualify_go_candidate(
    report: dict,
    planned_id: str,
    pinned_modules: list[str],
    selected_modules: set[str],
) -> tuple[bool, list[str], dict | None]:
    reasons: list[str] = []
    if report.get("id") != planned_id:
        reasons.append("id_mismatch")
    published = report.get("published") or ""
    if not isinstance(published, str) or not published.startswith("2026"):
        reasons.append("publication_not_2026")
    if report.get("withdrawn"):
        reasons.append("withdrawn")
    db_spec = report.get("database_specific") or {}
    review = db_spec.get("review_status")
    if review == "UNREVIEWED":
        reasons.append("unreviewed")
    elif isinstance(review, str) and review and review != "REVIEWED":
        reasons.append("unknown_review_status")

    pinned = set(pinned_modules)
    matched_affected = None
    for aff in report.get("affected") or []:
        if not isinstance(aff, dict):
            continue
        pkg = aff.get("package") or {}
        if pkg.get("ecosystem") != "Go":
            continue
        name = pkg.get("name")
        if not isinstance(name, str) or name not in pinned:
            continue
        if _entity_collision(name) or name in selected_modules:
            reasons.append("module_collision")
            continue
        ranges = aff.get("ranges") or []
        range_ok = any(
            _has_finite_range(r.get("events") or [])
            for r in ranges if isinstance(r, dict))
        if not range_ok:
            reasons.append("no_finite_range")
            continue
        eco = aff.get("ecosystem_specific") or {}
        imports = eco.get("imports") or []
        sym_ok = False
        symbols_found: list[str] = []
        for imp in imports:
            if not isinstance(imp, dict):
                continue
            syms = imp.get("symbols") or []
            for s in syms:
                if isinstance(s, str) and s:
                    sym_ok = True
                    symbols_found.append(s)
        if not sym_ok:
            reasons.append("missing_symbols")
            continue
        matched_affected = {
            "module": name,
            "symbols": symbols_found[:20],
            "imports_paths": [
                imp.get("path") for imp in imports
                if isinstance(imp, dict) and imp.get("path")],
        }
        break

    if matched_affected is None and "module_collision" not in reasons:
        if "no_finite_range" not in reasons and "missing_symbols" not in reasons:
            reasons.append("no_matching_affected")
    ok = not reasons
    return ok, reasons, matched_affected


@dataclass
class LiveResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]


def live_transport(url: str) -> LiveResponse:
    chain: list[str] = []
    current = url
    for _ in range(10):
        chain.append(current)
        req = urllib.request.Request(
            current,
            headers={"User-Agent": "efc-k2-capture/1.0"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = resp.read()
                final = resp.geturl()
                if final != current:
                    chain.append(final)
                return LiveResponse(
                    status=resp.status,
                    headers=dict(resp.headers),
                    body=body,
                    url=final,
                    redirect_chain=chain,
                )
        except urllib.error.HTTPError as e:
            body = e.read()
            return LiveResponse(
                status=e.code,
                headers=dict(e.headers),
                body=body,
                url=current,
                redirect_chain=chain,
            )


def _write_fetch_sidecar(
    path: Path,
    *,
    capture_id: str,
    capture_url: str,
    resp: TransportResponse,
    plan_sha: str,
    family: str,
    extra: dict,
) -> dict:
    raw_sha = sha256_bytes(resp.body)
    sidecar = {
        "schema_version": SCHEMA_VERSION,
        "capture_id": capture_id,
        "family": family,
        "capture_url": capture_url,
        "final_url": resp.url,
        "http_status": resp.status,
        "redirect_chain": resp.redirect_chain,
        "content_type": resp.headers.get("Content-Type"),
        "raw_byte_length": len(resp.body),
        "raw_sha256": raw_sha,
        "retrieved_at_utc": utc_now_iso(),
        "plan_sha256": plan_sha,
        "implementation_module_sha256": module_sha256(),
        **extra,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    (path.parent / "raw.json").write_bytes(resp.body)
    path.write_text(canonical_json(sidecar) + "\n")
    return sidecar


def dry_run() -> dict:
    return {
        "mode": "dry_run",
        "plan": build_plan(),
        "network_calls": 0,
        "authorized_urls": sorted(FROZEN_URLS),
    }


def execute_live(
    root: Path = K2_ROOT,
    transport: Transport | None = None,
) -> dict:
    check_create_once(root)
    root.mkdir(parents=True, exist_ok=True)
    transport = transport or live_transport
    plan = build_plan(root)
    plan_sha = plan["plan_sha256"]
    (root / "plan.json").write_text(canonical_json(plan) + "\n")

    call_count = 0
    c_results: list[dict] = []

    for spec in FAMILY_C:
        resp = transport(spec.capture_url)
        call_count += 1
        sc_path = root / "captures" / spec.capture_id / "sidecar.json"
        verdict, matches, failures = validate_family_c(
            resp.body, spec, resp.url)
        sidecar = _write_fetch_sidecar(
            sc_path,
            capture_id=spec.capture_id,
            capture_url=spec.capture_url,
            resp=resp,
            plan_sha=plan_sha,
            family="C",
            extra={
                "product_slug": spec.product_slug,
                "oracle_id": f"efc-calibration-{spec.capture_id}",
                "capture_verdict": verdict,
                "qualifying_locators": matches,
                "failure_reasons": failures,
            },
        )
        c_results.append({
            "id": spec.capture_id,
            "verdict": verdict,
            "qualifying_count": len(matches),
        })

    index_hashes: dict[str, str] = {}
    for name, url in INDEX_URLS:
        resp = transport(url)
        call_count += 1
        sc_path = root / "qualification" / "go_indexes" / name / "sidecar.json"
        _write_fetch_sidecar(
            sc_path,
            capture_id=f"go-index-{name}",
            capture_url=url,
            resp=resp,
            plan_sha=plan_sha,
            family="D-index",
            extra={"index_name": name, "capture_verdict": (
                "pass" if resp.status == 200 else "fail")},
        )
        index_hashes[name] = sha256_bytes(resp.body)

    modules_body = (
        root / "qualification/go_indexes/modules/raw.json").read_bytes()
    vulns_body = (
        root / "qualification/go_indexes/vulns/raw.json").read_bytes()
    cand_plan = derive_candidate_plan(modules_body, vulns_body, index_hashes)
    cand_path = root / "candidate_plan.json"
    if cand_path.exists():
        raise CaptureRefusal("create-once: candidate_plan exists")
    cand_path.write_text(canonical_json(cand_plan) + "\n")
    cand_sha = cand_plan["candidate_plan_sha256"]

    candidates = cand_plan["candidates"]
    d_attempts: list[dict] = []
    selected: list[dict] = []
    selected_modules: set[str] = set()
    stop_fetch = False

    for entry in candidates:
        if stop_fetch:
            break
        cid = entry["id"]
        url = entry["individual_url"]
        resp = transport(url)
        call_count += 1
        qual_dir = root / "qualification" / "go_candidates" / cid
        qual_sc = qual_dir / "sidecar.json"
        try:
            report = _parse_json(resp.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            report = {}
        if not isinstance(report, dict):
            report = {}
        ok, reasons, summary = qualify_go_candidate(
            report, cid, entry["module_paths"], selected_modules)
        qual_sidecar = _write_fetch_sidecar(
            qual_sc,
            capture_id=cid,
            capture_url=url,
            resp=resp,
            plan_sha=plan_sha,
            family="D-candidate",
            extra={
                "candidate_plan_sha256": cand_sha,
                "qualification_verdict": "pass" if ok else "fail",
                "failure_reasons": reasons,
                "index_pinned_modules": entry["module_paths"],
                "entity_summary": summary,
            },
        )
        attempt = {
            "candidate_id": cid,
            "qualification_verdict": qual_sidecar["qualification_verdict"],
            "failure_reasons": reasons,
        }
        d_attempts.append(attempt)

        if ok and len(selected) < TARGET_D_QUALIFIERS:
            cap_id = f"capD-{len(selected) + 1:02d}"
            cap_dir = root / "captures" / cap_id
            cap_dir.mkdir(parents=True)
            raw_src = qual_dir / "raw.json"
            (cap_dir / "raw.json").write_bytes(raw_src.read_bytes())
            cap_sc = {
                "schema_version": SCHEMA_VERSION,
                "capture_id": cap_id,
                "family": "D",
                "source_candidate_id": cid,
                "oracle_id": f"efc-calibration-{cap_id}",
                "capture_verdict": "pass",
                "plan_sha256": plan_sha,
                "candidate_plan_sha256": cand_sha,
                "promoted_from_qualification": True,
                "raw_sha256": sha256_file(cap_dir / "raw.json"),
                "retrieved_at_utc": qual_sidecar["retrieved_at_utc"],
                "entity_summary": summary,
                "go_id": cid,
                "index_pinned_modules": entry["module_paths"],
                "implementation_module_sha256": module_sha256(),
            }
            (cap_dir / "sidecar.json").write_text(
                canonical_json(cap_sc) + "\n")
            selected_modules.add(summary["module"])
            selected.append({
                "logical_slot": f"D{len(selected):02d}",
                "capture_id": cap_id,
                "go_id": cid,
                "module": summary["module"],
            })
            if len(selected) >= TARGET_D_QUALIFIERS:
                stop_fetch = True

    family_d_shortfall = len(selected) < TARGET_D_QUALIFIERS
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "plan_sha256": plan_sha,
        "candidate_plan_sha256": cand_sha,
        "family_c_results": c_results,
        "d_candidate_attempts": d_attempts,
        "selected_d": selected,
        "family_d_pass_count": len(selected),
        "family_d_shortfall": family_d_shortfall,
        "selected_modules": sorted(selected_modules),
        "generated_at_utc": utc_now_iso(),
    }
    (root / "selection_ledger.json").write_text(
        canonical_json(ledger) + "\n")

    report = {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "network_calls": call_count,
        "max_total_calls": plan["max_total_calls"],
        "plan_sha256": plan_sha,
        "candidate_plan_sha256": cand_sha,
        "candidate_count": len(candidates),
        "family_c_pass": sum(1 for r in c_results if r["verdict"] == "pass"),
        "family_d_pass": len(selected),
        "family_d_shortfall": family_d_shortfall,
        "generated_at_utc": utc_now_iso(),
    }
    (root / "capture_report.json").write_text(
        canonical_json(report) + "\n")

    return {
        "mode": "live",
        "network_calls": call_count,
        "report": report,
        "ledger": ledger,
    }


def verify_hashes(root: Path = K2_ROOT) -> list[str]:
    errors: list[str] = []
    if not (root / "plan.json").exists():
        return ["missing plan.json"]
    for spec in FAMILY_C:
        cdir = root / "captures" / spec.capture_id
        raw_p = cdir / "raw.json"
        sc_p = cdir / "sidecar.json"
        if not raw_p.exists() or not sc_p.exists():
            errors.append(f"missing C capture {spec.capture_id}")
            continue
        sc = json.loads(sc_p.read_text())
        if sha256_file(raw_p) != sc.get("raw_sha256"):
            errors.append(f"C raw hash mismatch {spec.capture_id}")
    for cap_n in range(1, 7):
        cid = f"capD-{cap_n:02d}"
        cdir = root / "captures" / cid
        if not cdir.exists():
            continue
        raw_p = cdir / "raw.json"
        sc_p = cdir / "sidecar.json"
        if not raw_p.exists() or not sc_p.exists():
            errors.append(f"missing D capture {cid}")
            continue
        sc = json.loads(sc_p.read_text())
        if sha256_file(raw_p) != sc.get("raw_sha256"):
            errors.append(f"D raw hash mismatch {cid}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EFC K2 mechanical capture")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--verify-hashes", action="store_true")
    args = parser.parse_args(argv)

    if args.verify_hashes:
        errs = verify_hashes()
        if errs:
            for e in errs:
                print(e, file=sys.stderr)
            return 1
        print("all K2 hashes verified")
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
