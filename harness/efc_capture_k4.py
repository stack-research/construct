"""EFC v0 K4 — six frozen P-slot captures + global 40-row identity ledger.

Usage:
  python -m harness.efc_capture_k4              # dry-run
  python -m harness.efc_capture_k4 --execute  # one live run
  python -m harness.efc_capture_k4 --verify-hashes
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

REPO = Path(__file__).resolve().parent.parent
K1_ROOT = REPO / "corpus" / "efc_calibration" / "_acquisition" / "k1"
K2_ROOT = REPO / "corpus" / "efc_calibration" / "_acquisition" / "k2"
K2B_ROOT = REPO / "corpus" / "efc_calibration" / "_acquisition" / "k2b"
K3_ROOT = REPO / "corpus" / "efc_calibration" / "_acquisition" / "k3"
K3C_ROOT = REPO / "corpus" / "efc_calibration" / "_acquisition" / "k3c"
K3D_ROOT = REPO / "corpus" / "efc_calibration" / "_acquisition" / "k3d"
K4_ROOT = REPO / "corpus" / "efc_calibration" / "_acquisition" / "k4"
SCHEMA_VERSION = "efc-k4-acquisition-v1"
SEAT = "cursor/composer-2.5-capture"
MAX_CALLS = 6

P04_FROZEN_SYMBOLS: tuple[str, ...] = tuple(
    ast.literal_eval(
        "['ClientConn.HandleBidirectionalStream', 'ClientConn.OpenRequestStream', "
        "'ClientConn.RoundTrip', 'ConfigureTLSConfig', 'ErrCode.String', 'Error.Error', "
        "'ListenAndServeQUIC', 'ListenAndServeTLS', 'ParseCapsule', "
        "'RawClientConn.HandleUnidirectionalStream', 'RawServerConn.HandleRequestStream', "
        "'RawServerConn.HandleUnidirectionalStream', 'RequestStream.CancelRead', "
        "'RequestStream.CancelWrite', 'RequestStream.Close', 'RequestStream.Read', "
        "'RequestStream.ReadResponse', 'RequestStream.SendRequestHeader', "
        "'RequestStream.Write', 'Server.Close', 'Server.ListenAndServe', "
        "'Server.ListenAndServeTLS', 'Server.NewRawServerConn', 'Server.Serve', "
        "'Server.ServeListener', 'Server.ServeQUICConn', 'Server.Shutdown', "
        "'Stream.Read', 'Stream.Write', 'Transport.Close', "
        "'Transport.CloseIdleConnections', 'Transport.NewClientConn', "
        "'Transport.NewRawClientConn', 'Transport.RoundTrip', 'Transport.RoundTripOpt', "
        "'body.Close', 'body.Read', 'cancelingReader.Read', 'countingByteReader.Read', "
        "'countingByteReader.ReadByte', 'decodeTrailers', 'errConnUnusable.Error', "
        "'exactReader.Read', 'frameParser.ParseNext', 'gzipReader.Close', "
        "'gzipReader.Read', 'hijackableBody.Close', 'hijackableBody.Read', "
        "'parseHeaders', 'parseTrailers', 'qpackError.Error', 'rawConn.OpenUniStream', "
        "'rawConn.TrackStream', 'requestWriter.WriteRequestHeader', "
        "'requestWriter.WriteRequestTrailer', 'responseWriter.Flush', "
        "'responseWriter.FlushError', 'responseWriter.HTTPStream', "
        "'responseWriter.Write', 'responseWriter.WriteHeader', "
        "'roundTripperWithCount.Close', 'stateTrackingStream.CancelRead', "
        "'stateTrackingStream.CancelWrite', 'stateTrackingStream.Close', "
        "'stateTrackingStream.Read', 'stateTrackingStream.Write', 'tracingReader.Read']"
    )
)

K2_FAILED_IDS = tuple(
    f"GO-2026-{n}" for n in (
        4273, 4274, 4275, 4277, 4278, 4279, 4282, 4283, 4284, 4285,
        4286, 4287, 4289, 4290, 4292, 4293, 4295, 4296, 4297, 4298,
        4299, 4300, 4301, 4302,
    )
)

HISTORICAL_EXCLUSIONS = {
    "k2_failed_go_ids": list(K2_FAILED_IDS),
    "k2b_uncontacted": ["GO-2026-4479", "GO-2026-5410"],
    "kagi_d_ids": [
        "GO-2026-4961", "GO-2026-5023", "GO-2026-5601",
        "GO-2026-4984", "GO-2026-0001", "GO-2026-0002",
    ],
    "k4_rejected_nominations": [
        "RUSTSEC-2026-0205", "GHSA-658g-p7jg-wx5g",
        "GO-2026-4961", "RUSTSEC-2026-0042",
    ],
}


@dataclass(frozen=True)
class PSpec:
    slot: str
    family: str
    record_id: str
    entity_key: str
    capture_url: str
    format: str


FROZEN_P: tuple[PSpec, ...] = (
    PSpec("P01", "A", "RUSTSEC-2026-0122", "rkyv",
          "https://raw.githubusercontent.com/rustsec/advisory-db/osv/crates/"
          "RUSTSEC-2026-0122.json", "rustsec_osv"),
    PSpec("P02", "B", "GHSA-jggg-4jg4-v7c6", "protobufjs",
          "https://api.github.com/advisories/GHSA-jggg-4jg4-v7c6", "ghsa"),
    PSpec("P03", "C", "typo3", "typo3",
          "https://endoflife.date/api/typo3.json", "endoflife"),
    PSpec("P04", "D", "GO-2026-5676", "github.com/quic-go/quic-go",
          "https://vuln.go.dev/ID/GO-2026-5676.json", "go_vuln"),
    PSpec("P05", "E", "0BSD", "0BSD",
          "https://raw.githubusercontent.com/spdx/license-list-data/main/json/"
          "details/0BSD.json", "spdx"),
    PSpec("P06", "A", "RUSTSEC-2026-0103", "thin-vec",
          "https://raw.githubusercontent.com/rustsec/advisory-db/osv/crates/"
          "RUSTSEC-2026-0103.json", "rustsec_osv"),
)

FROZEN_URLS: frozenset[str] = frozenset(s.capture_url for s in FROZEN_P)


class CaptureRefusal(Exception):
    pass


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


def rel_repo(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def check_create_once(root: Path = K4_ROOT) -> None:
    if root.exists():
        for p in root.rglob("*"):
            if p.is_file():
                raise CaptureRefusal(f"create-once: {p}")


def build_plan() -> dict:
    body = {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "max_network_calls": MAX_CALLS,
        "redirect_policy": "refuse",
        "retry_policy": "zero",
        "slots": [
            {
                "slot": s.slot,
                "family": s.family,
                "record_id": s.record_id,
                "entity_key": s.entity_key,
                "capture_url": s.capture_url,
                "format": s.format,
                "raw_path": f"captures/{s.slot}/raw.json",
                "sidecar_path": f"captures/{s.slot}/sidecar.json",
            }
            for s in FROZEN_P
        ],
        "predicates": {
            "P01": {
                "id": "RUSTSEC-2026-0122",
                "ecosystem": "crates.io",
                "package": "rkyv",
                "events": [{"introduced": "0.8.0"}, {"fixed": "0.8.16"}],
                "provenance": "rustsec_osv_mirror",
            },
            "P02": {
                "ghsa_id": "GHSA-jggg-4jg4-v7c6",
                "package": "protobufjs",
                "ecosystem": "npm",
                "branches": [
                    {"vulnerable": "<= 7.5.7", "patched": "7.5.8"},
                    {"vulnerable": ">= 8.0.0, < 8.2.0", "patched": "8.2.0"},
                ],
            },
            "P03": {"cycle": "12", "eol": "2026-04-30", "select_by": "cycle_value"},
            "P04": {
                "id": "GO-2026-5676",
                "module": "github.com/quic-go/quic-go",
                "review_status": "REVIEWED",
                "events": [{"introduced": "0"}, {"fixed": "0.59.1"}],
                "import_path": "github.com/quic-go/quic-go/http3",
                "symbols": list(P04_FROZEN_SYMBOLS),
            },
            "P05": {"licenseId": "0BSD", "licenseText_nonempty": True},
            "P06": {
                "id": "RUSTSEC-2026-0103",
                "ecosystem": "crates.io",
                "package": "thin-vec",
                "events": [{"introduced": "0.0.0-0"}, {"fixed": "0.2.16"}],
                "provenance": "rustsec_osv_mirror",
            },
        },
        "historical_exclusions": HISTORICAL_EXCLUSIONS,
        "implementation_module_sha256": module_sha256(),
    }
    plan = dict(body)
    plan["plan_sha256"] = sha256_bytes(canonical_json(body).encode())
    return plan


def _parse_json(body: bytes) -> dict:
    data = json.loads(body.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("not object")
    return data


def _events_match(actual: list, expected: list[dict]) -> bool:
    norm: list[dict[str, str]] = []
    for e in actual:
        if not isinstance(e, dict):
            return False
        row: dict[str, str] = {}
        for k in ("introduced", "fixed", "last_affected"):
            if k in e and isinstance(e[k], str):
                row[k] = e[k]
        if row:
            norm.append(row)
    return norm == expected


def qualify_p01(data: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if data.get("id") != "RUSTSEC-2026-0122":
        reasons.append("id_mismatch")
    pub = data.get("published") or ""
    if not str(pub).startswith("2026"):
        reasons.append("publication_not_2026")
    aff = (data.get("affected") or [{}])[0]
    pkg = aff.get("package") or {}
    if pkg.get("ecosystem") != "crates.io" or pkg.get("name") != "rkyv":
        reasons.append("package_mismatch")
    ev = (aff.get("ranges") or [{}])[0].get("events") or []
    if not _events_match(ev, [{"introduced": "0.8.0"}, {"fixed": "0.8.16"}]):
        reasons.append("events_mismatch")
    return not reasons, reasons


def qualify_p02(data: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if data.get("ghsa_id") != "GHSA-jggg-4jg4-v7c6":
        reasons.append("ghsa_id_mismatch")
    pub = data.get("published_at") or ""
    if not str(pub).startswith("2026"):
        reasons.append("published_at_not_2026")
    vulns = data.get("vulnerabilities") or []
    if len(vulns) < 2:
        reasons.append("missing_vulnerability_branches")
    else:
        b0, b1 = vulns[0], vulns[1]
        if (b0.get("package") or {}).get("name") != "protobufjs":
            reasons.append("package_mismatch_v0")
        if (b1.get("package") or {}).get("name") != "protobufjs":
            reasons.append("package_mismatch_v1")
        if b0.get("vulnerable_version_range") != "<= 7.5.7":
            reasons.append("range0_mismatch")
        if b0.get("first_patched_version") != "7.5.8":
            reasons.append("patch0_mismatch")
        if b1.get("vulnerable_version_range") != ">= 8.0.0, < 8.2.0":
            reasons.append("range1_mismatch")
        if b1.get("first_patched_version") != "8.2.0":
            reasons.append("patch1_mismatch")
    return not reasons, reasons


def qualify_p03(data: list) -> tuple[bool, list[str], dict]:
    reasons: list[str] = []
    matches = [o for o in data if isinstance(o, dict) and o.get("cycle") == "12"]
    if len(matches) != 1:
        reasons.append("cycle_12_not_unique")
        return False, reasons, {}
    obj = matches[0]
    if obj.get("eol") != "2026-04-30":
        reasons.append("eol_mismatch")
    return not reasons, reasons, {"cycle": "12", "eol": obj.get("eol")}


def qualify_p04(data: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if data.get("id") != "GO-2026-5676":
        reasons.append("id_mismatch")
    if (data.get("database_specific") or {}).get("review_status") != "REVIEWED":
        reasons.append("not_reviewed")
    aff = (data.get("affected") or [{}])[0]
    if (aff.get("package") or {}).get("name") != "github.com/quic-go/quic-go":
        reasons.append("module_mismatch")
    ev = (aff.get("ranges") or [{}])[0].get("events") or []
    if not _events_match(ev, [{"introduced": "0"}, {"fixed": "0.59.1"}]):
        reasons.append("events_mismatch")
    imps = _imports_map((aff.get("ecosystem_specific") or {}).get("imports") or [])
    syms = imps.get("github.com/quic-go/quic-go/http3")
    if list(syms or []) != list(P04_FROZEN_SYMBOLS):
        reasons.append("symbols_mismatch")
    return not reasons, reasons


def qualify_p05(data: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if data.get("licenseId") != "0BSD":
        reasons.append("licenseId_mismatch")
    lt = data.get("licenseText")
    if not isinstance(lt, str) or not lt.strip():
        reasons.append("licenseText_empty")
    return not reasons, reasons


def qualify_p06(data: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if data.get("id") != "RUSTSEC-2026-0103":
        reasons.append("id_mismatch")
    pub = data.get("published") or ""
    if not str(pub).startswith("2026"):
        reasons.append("publication_not_2026")
    aff = (data.get("affected") or [{}])[0]
    pkg = aff.get("package") or {}
    if pkg.get("ecosystem") != "crates.io" or pkg.get("name") != "thin-vec":
        reasons.append("package_mismatch")
    ev = (aff.get("ranges") or [{}])[0].get("events") or []
    if not _events_match(ev, [{"introduced": "0.0.0-0"}, {"fixed": "0.2.16"}]):
        reasons.append("events_mismatch")
    return not reasons, reasons


def _imports_map(imports: list) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for imp in imports:
        if isinstance(imp, dict) and isinstance(imp.get("path"), str):
            syms = imp.get("symbols") or []
            out[imp["path"]] = [s for s in syms if isinstance(s, str)]
    return out


def qualify_slot(
    spec: PSpec, body: bytes, *, http_status: int, redirect_refused: bool,
) -> tuple[bool, list[str], dict]:
    reasons: list[str] = []
    if http_status != 200:
        reasons.append("http_not_200")
    if redirect_refused:
        reasons.append("redirect_refused")
    extra: dict = {}
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        reasons.append("json_parse_error")
        return False, reasons, extra
    if spec.format == "endoflife":
        if not isinstance(parsed, list):
            reasons.append("not_array")
            return False, reasons, extra
        ok, r, extra = qualify_p03(parsed)
        reasons.extend(r)
        return ok and not reasons, reasons, extra
    if not isinstance(parsed, dict):
        reasons.append("not_object")
        return False, reasons, extra
    fn = {
        "rustsec_osv": qualify_p01 if spec.slot == "P01" else qualify_p06,
        "ghsa": qualify_p02,
        "go_vuln": qualify_p04,
        "spdx": qualify_p05,
    }[spec.format]
    ok, r = fn(parsed)
    reasons.extend(r)
    return ok and not reasons, reasons, extra


def extract_aliases(data: object, fmt: str) -> dict:
    out: dict = {"fields_inspected": [], "aliases": []}
    if fmt == "rustsec_osv" and isinstance(data, dict):
        out["fields_inspected"] = ["aliases"]
        out["aliases"] = list(data.get("aliases") or [])
    elif fmt == "ghsa" and isinstance(data, dict):
        out["fields_inspected"] = ["cve_id", "ghsa_id"]
        if data.get("cve_id"):
            out["aliases"].append(data["cve_id"])
    elif fmt == "go_vuln" and isinstance(data, dict):
        out["fields_inspected"] = ["aliases"]
        out["aliases"] = list(data.get("aliases") or [])
    elif fmt == "spdx" and isinstance(data, dict):
        out["fields_inspected"] = ["seeAlso"]
        out["aliases"] = list(data.get("seeAlso") or [])
    elif fmt == "endoflife":
        out["fields_inspected"] = []
        out["note"] = "field_absent_in_captured_source"
    return out


@dataclass
class LiveResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]
    redirect_refused: bool = False


def live_transport(url: str) -> LiveResponse:
    req = urllib.request.Request(
        url, headers={"User-Agent": "efc-k4-capture/1.0"}, method="GET")
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


@dataclass(frozen=True)
class PlanContext:
    k2b_url_by_go_id: dict[str, str]
    k3_by_capture_id: dict[str, dict]
    k3_url_by_capture_id: dict[str, str]
    k3_record_id_by_capture_id: dict[str, str]


def load_plan_context() -> PlanContext:
    k2b = json.loads((K2B_ROOT / "plan.json").read_text())
    k2b_urls = {c["go_id"]: c["capture_url"] for c in k2b["candidates"]}
    k3 = json.loads((K3_ROOT / "plan.json").read_text())
    k3_by_id = {e["id"]: e for e in k3["entries"]}
    k3_urls = {e["id"]: e["capture_url"] for e in k3["entries"]}
    k3_records = {e["id"]: e["record_id"] for e in k3["entries"]}
    return PlanContext(k2b_urls, k3_by_id, k3_urls, k3_records)


def _sidecar_dir(cap_path: Path) -> Path:
    return cap_path if cap_path.is_dir() else cap_path.parent


def _canonical_url(
    sc: dict, *, family: str, source_capture_id: str | None, ctx: PlanContext,
) -> str | None:
    url = sc.get("capture_url") or sc.get("final_url")
    if url:
        return url
    if family == "D":
        go_id = sc.get("go_id")
        if go_id:
            return ctx.k2b_url_by_go_id.get(go_id)
    if family == "F" and source_capture_id:
        base_id = source_capture_id.removesuffix("c")
        return ctx.k3_url_by_capture_id.get(base_id) or ctx.k3_url_by_capture_id.get(
            source_capture_id)
    return None


def _entity_key(
    sc: dict, *, family: str, source_capture_id: str | None, ctx: PlanContext,
) -> str | None:
    if family == "E":
        return (sc.get("licenseExceptionId") or sc.get("licenseId")
                or sc.get("record_id_expected"))
    if family == "F":
        if source_capture_id:
            base_id = source_capture_id.removesuffix("c")
            return (ctx.k3_record_id_by_capture_id.get(base_id)
                    or ctx.k3_record_id_by_capture_id.get(source_capture_id))
        return sc.get("record_id_expected")
    if family == "A" or family == "B":
        return sc.get("package_returned")
    if family == "D":
        return sc.get("module")
    if family == "C":
        return sc.get("product_slug")
    return sc.get("entity_key")


def _record_id(
    sc: dict, *, family: str, source_capture_id: str | None, ctx: PlanContext,
) -> str | None:
    if family == "E":
        return _entity_key(sc, family=family, source_capture_id=source_capture_id, ctx=ctx)
    if family == "F":
        return _entity_key(sc, family=family, source_capture_id=source_capture_id, ctx=ctx)
    return (sc.get("record_id_returned") or sc.get("go_id")
            or sc.get("record_id_expected") or sc.get("product_slug"))


def _row_from_capture(
    slot: str, family: str, cap_path: Path, raw_path: Path,
    sc: dict, seat: str, fmt: str | None = None, *,
    source_capture_id: str | None = None,
    promotion_eligible: bool | None = None,
    ctx: PlanContext | None = None,
) -> dict:
    ctx = ctx or load_plan_context()
    verdict = sc.get("qualification_verdict")
    if verdict is None:
        verdict = sc.get("reconciliation_verdict") or sc.get("capture_verdict") or "pass"
    eligible = (promotion_eligible if promotion_eligible is not None
                else verdict == "pass")
    raw_data = json.loads(raw_path.read_text()) if raw_path.suffix == ".json" else None
    if fmt and raw_data is not None:
        alias_info = extract_aliases(raw_data, fmt)
    elif raw_data is not None:
        alias_info = extract_aliases(
            raw_data,
            "rustsec_osv" if family == "A" else
            "ghsa" if family == "B" else "go_vuln" if family == "D" else
            "spdx" if family == "E" else "endoflife")
    else:
        alias_info = {"fields_inspected": [], "aliases": []}
    sidecar_path = _sidecar_dir(cap_path) / "sidecar.json"
    return {
        "logical_slot": slot,
        "family": family,
        "record_id": _record_id(sc, family=family, source_capture_id=source_capture_id, ctx=ctx),
        "entity_key": _entity_key(sc, family=family, source_capture_id=source_capture_id, ctx=ctx),
        "canonical_url": _canonical_url(
            sc, family=family, source_capture_id=source_capture_id, ctx=ctx),
        "capture_path": rel_repo(raw_path),
        "raw_sha256": sha256_file(raw_path),
        "sidecar_sha256": sha256_file(sidecar_path) if sidecar_path.exists() else None,
        "qualification_verdict": verdict,
        "promotion_eligible": eligible,
        "source_seat": seat,
        "alias_extraction": alias_info,
    }


def _excluded_row(slot: str, family: str, record_id: str, reason: str) -> dict:
    return {
        "logical_slot": slot,
        "family": family,
        "record_id": record_id,
        "exclusion_reason": reason,
    }


TARGET_FAMILY_COUNTS = {"A": 8, "B": 7, "C": 7, "D": 7, "E": 7, "F": 4}
TARGET_ROW_COUNT = 40
K1_FAILED_B_SLOTS = frozenset({"B02", "B03", "B06"})


def build_global_ledger(
    k4_root: Path,
    p_results: list[dict],
    br_results: list[dict] | None = None,
) -> dict:
    ctx = load_plan_context()
    promoted: list[dict] = []
    excluded: list[dict] = []

    for i in range(1, 7):
        cid = f"capA-{i:02d}"
        sc_path = K1_ROOT / "captures" / cid / "sidecar.json"
        raw_path = K1_ROOT / "captures" / cid / "raw.json"
        sc = json.loads(sc_path.read_text())
        promoted.append(_row_from_capture(
            f"A{i:02d}", "A", sc_path, raw_path, sc,
            sc.get("seat", SEAT), ctx=ctx))

    for i in range(1, 7):
        slot = f"B{i:02d}"
        cid = f"capB-{i:02d}"
        sc_path = K1_ROOT / "captures" / cid / "sidecar.json"
        raw_path = K1_ROOT / "captures" / cid / "raw.json"
        sc = json.loads(sc_path.read_text())
        if sc.get("capture_verdict") != "pass":
            excluded.append(_excluded_row(
                slot, "B", sc.get("record_id_returned", cid),
                "k1_capture_verdict_fail"))
            continue
        promoted.append(_row_from_capture(
            slot, "B", sc_path, raw_path, sc, sc.get("seat", SEAT), "ghsa", ctx=ctx))

    for i in range(1, 7):
        cid = f"capC-{i:02d}"
        sc_path = K2_ROOT / "captures" / cid / "sidecar.json"
        raw_path = K2_ROOT / "captures" / cid / "raw.json"
        sc = json.loads(sc_path.read_text())
        promoted.append(_row_from_capture(
            f"C{i:02d}", "C", sc_path, raw_path, sc,
            sc.get("seat", SEAT), "endoflife", ctx=ctx))

    for i in range(1, 7):
        cid = f"capD-{i:02d}"
        sc_path = K2B_ROOT / "captures" / cid / "sidecar.json"
        raw_path = K2B_ROOT / "captures" / cid / "raw.json"
        sc = json.loads(sc_path.read_text())
        promoted.append(_row_from_capture(
            f"D{i:02d}", "D", sc_path, raw_path, sc,
            sc.get("seat", SEAT), "go_vuln", ctx=ctx))

    k3d = json.loads((K3D_ROOT / "promotion_ledger_v2.json").read_text())
    for m in k3d["logical_slot_mappings"]:
        slot = m["logical_slot"]
        sid = m["source_capture_id"]
        kind = m["source_kind"]
        if kind == "k3_original":
            base = K3_ROOT / "captures" / sid
            ext = "json" if sid.startswith("capE") else "html"
        elif kind == "k3c_corrected":
            base = K3C_ROOT / "captures" / sid
            ext = "json" if sid.startswith("capE") else "rst"
        else:
            base = K3_ROOT / "captures" / sid
            ext = "html"
        raw_path = base / f"raw.{ext}"
        if kind == "k3c_reconciled":
            sc_path = K3C_ROOT / "reconciliation" / sid / "sidecar.json"
            capture_sidecar = K3_ROOT / "captures" / sid / "sidecar.json"
            sc = {**json.loads(capture_sidecar.read_text()),
                  **json.loads(sc_path.read_text())}
        else:
            sc_path = base / "sidecar.json"
            sc = json.loads(sc_path.read_text())
        sc = {**sc, "qualification_verdict": m.get("qualification_verdict", "pass")}
        fam = slot[0]
        fmt = "spdx" if fam == "E" else None
        if not m.get("promotion_eligible", True):
            excluded.append(_excluded_row(
                slot, fam, sid, "k3d_promotion_ineligible"))
            continue
        promoted.append(_row_from_capture(
            slot, fam, sc_path, raw_path, sc,
            m.get("seat", SEAT), fmt,
            source_capture_id=sid,
            promotion_eligible=True,
            ctx=ctx))

    for pr in p_results:
        if pr.get("promotion_eligible"):
            promoted.append(pr)
        else:
            excluded.append(_excluded_row(
                pr["logical_slot"], pr["family"], pr.get("record_id", ""),
                "p_slot_qualification_fail"))

    for br in br_results or []:
        if br.get("promotion_eligible"):
            promoted.append(br)
        else:
            excluded.append(_excluded_row(
                br["logical_slot"], br["family"], br.get("record_id", ""),
                "br_slot_qualification_fail"))

    assertions = _ledger_assertions(promoted)
    counts = {fam: sum(1 for r in promoted if r["family"] == fam) for fam in "ABCDEF"}
    counts["P_slots"] = sum(1 for r in promoted if r["logical_slot"].startswith("P"))
    shortfall = TARGET_ROW_COUNT - len(promoted)
    return {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "row_count": len(promoted),
        "target_row_count": TARGET_ROW_COUNT,
        "replacement_shortfall": shortfall,
        "b_replacement_shortfall": max(0, TARGET_FAMILY_COUNTS["B"] - counts["B"]),
        "family_counts": counts,
        "target_family_counts": TARGET_FAMILY_COUNTS,
        "rows": promoted,
        "excluded_from_promotion": excluded,
        "assertions": assertions,
        "generated_at_utc": utc_now_iso(),
    }


def _ledger_assertions(rows: list[dict]) -> dict:
    ids = [r.get("record_id") for r in rows]
    urls = [r.get("canonical_url") for r in rows]
    entities = [r.get("entity_key") for r in rows]
    all_aliases: list[str] = []
    for r in rows:
        all_aliases.extend(r.get("alias_extraction", {}).get("aliases") or [])
    counts = {fam: sum(1 for r in rows if r["family"] == fam) for fam in "ABCDEF"}
    return {
        "distinct_record_ids": len(set(ids)) == len(ids) and all(ids),
        "distinct_urls": len(set(urls)) == len(urls) and all(urls),
        "distinct_entities": len(set(entities)) == len(entities) and all(entities),
        "no_alias_cross_row_duplicates": len(all_aliases) == len(set(all_aliases)),
        "promoted_row_count": len(rows),
        "target_row_count": len(rows) == TARGET_ROW_COUNT,
        "family_A": counts["A"] == TARGET_FAMILY_COUNTS["A"],
        "family_B": counts["B"] == TARGET_FAMILY_COUNTS["B"],
        "family_C": counts["C"] == TARGET_FAMILY_COUNTS["C"],
        "family_D": counts["D"] == TARGET_FAMILY_COUNTS["D"],
        "family_E": counts["E"] == TARGET_FAMILY_COUNTS["E"],
        "family_F": counts["F"] == TARGET_FAMILY_COUNTS["F"],
        "p_slots": sum(1 for r in rows if r["logical_slot"].startswith("P")) == 6,
        "all_qualifying": all(r.get("qualification_verdict") == "pass" for r in rows),
        "no_tbd": not any("TBD" in str(v) for r in rows for v in r.values()),
    }


def p_rows_from_disk(root: Path = K4_ROOT) -> list[dict]:
    rows: list[dict] = []
    for spec in FROZEN_P:
        cap_dir = root / "captures" / spec.slot
        sc = json.loads((cap_dir / "sidecar.json").read_text())
        raw_sha = sc["raw_sha256"]
        try:
            parsed = json.loads((cap_dir / "raw.json").read_text())
        except Exception:
            parsed = {}
        alias_info = extract_aliases(
            parsed,
            "endoflife" if spec.format == "endoflife" and isinstance(parsed, list)
            else spec.format)
        ok = sc.get("qualification_verdict") == "pass"
        rows.append({
            "logical_slot": spec.slot,
            "family": spec.family,
            "record_id": spec.record_id,
            "entity_key": spec.entity_key,
            "canonical_url": spec.capture_url,
            "capture_path": rel_repo(cap_dir / "raw.json"),
            "raw_sha256": raw_sha,
            "sidecar_sha256": sha256_file(cap_dir / "sidecar.json"),
            "qualification_verdict": sc["qualification_verdict"],
            "promotion_eligible": ok,
            "source_seat": SEAT,
            "alias_extraction": alias_info,
            "format_provenance": sc.get("format_provenance"),
        })
    return rows


def br_rows_from_disk(root: Path = K4_ROOT) -> list[dict]:
    """Load BR promotion rows if br_replacement captures exist."""
    from harness.efc_capture_k4br import FROZEN_BR, br_rows_from_captures

    if not any((root / "captures" / s.slot).exists() for s in FROZEN_BR):
        return []
    return br_rows_from_captures(root)


def repair_ledger(root: Path = K4_ROOT) -> dict:
    if not root.exists():
        raise CaptureRefusal("k4 root missing")
    p_rows = p_rows_from_disk(root)
    br_rows = br_rows_from_disk(root)
    global_ledger = build_global_ledger(root, p_rows, br_rows)
    (root / "promotion_identity_ledger.json").write_text(
        canonical_json(global_ledger) + "\n")
    report_path = root / "capture_report.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    report["global_assertions"] = global_ledger["assertions"]
    report["promoted_row_count"] = global_ledger["row_count"]
    report["replacement_shortfall"] = global_ledger["replacement_shortfall"]
    report["b_replacement_shortfall"] = global_ledger["b_replacement_shortfall"]
    report["ledger_repaired_at_utc"] = utc_now_iso()
    report_path.write_text(canonical_json(report) + "\n")
    return {
        "mode": "repair_ledger",
        "network_calls": 0,
        "promotion_identity_ledger": global_ledger,
    }


def dry_run() -> dict:
    return {"mode": "dry_run", "network_calls": 0, "plan": build_plan()}


def execute_live(
    root: Path = K4_ROOT,
    transport: Transport | None = None,
) -> dict:
    check_create_once(root)
    root.mkdir(parents=True, exist_ok=True)
    transport = transport or live_transport
    plan = build_plan()
    plan_sha = plan["plan_sha256"]
    (root / "plan.json").write_text(canonical_json(plan) + "\n")

    call_count = 0
    p_ledger: list[dict] = []
    p_rows: list[dict] = []

    for spec in FROZEN_P:
        resp = transport(spec.capture_url)
        call_count += 1
        ok, reasons, extra = qualify_slot(
            spec, resp.body, http_status=resp.status,
            redirect_refused=resp.redirect_refused)
        cap_dir = root / "captures" / spec.slot
        cap_dir.mkdir(parents=True)
        (cap_dir / "raw.json").write_bytes(resp.body)
        raw_sha = sha256_bytes(resp.body)
        try:
            parsed = json.loads(resp.body.decode("utf-8"))
        except Exception:
            parsed = {}
        alias_info = extract_aliases(
            parsed,
            "endoflife" if spec.format == "endoflife" and isinstance(parsed, list)
            else spec.format)
        sidecar = {
            "schema_version": SCHEMA_VERSION,
            "slot": spec.slot,
            "family": spec.family,
            "capture_url": spec.capture_url,
            "http_status": resp.status,
            "redirect_refused": resp.redirect_refused,
            "redirect_chain": resp.redirect_chain,
            "raw_sha256": raw_sha,
            "raw_byte_length": len(resp.body),
            "qualification_verdict": "pass" if ok else "fail",
            "failure_reasons": reasons,
            "field_qualification": extra,
            "plan_sha256": plan_sha,
            "format_provenance": (
                "rustsec_osv_mirror" if spec.format == "rustsec_osv" else spec.format),
            "retrieved_at_utc": utc_now_iso(),
            "implementation_module_sha256": module_sha256(),
        }
        if ok:
            sidecar["oracle_id"] = f"efc-calibration-{spec.slot}"
        (cap_dir / "sidecar.json").write_text(canonical_json(sidecar) + "\n")

        p_ledger.append({
            "slot": spec.slot,
            "record_id": spec.record_id,
            "qualification_verdict": sidecar["qualification_verdict"],
            "failure_reasons": reasons,
            "raw_sha256": raw_sha,
            "field_qualification": extra,
        })
        p_rows.append({
            "logical_slot": spec.slot,
            "family": spec.family,
            "record_id": spec.record_id,
            "entity_key": spec.entity_key,
            "canonical_url": spec.capture_url,
            "capture_path": rel_repo(cap_dir / "raw.json"),
            "raw_sha256": raw_sha,
            "sidecar_sha256": sha256_file(cap_dir / "sidecar.json"),
            "qualification_verdict": sidecar["qualification_verdict"],
            "promotion_eligible": ok,
            "source_seat": SEAT,
            "alias_extraction": alias_info,
            "format_provenance": sidecar["format_provenance"],
        })

    global_ledger = build_global_ledger(root, p_rows)
    (root / "qualification_ledger.json").write_text(
        canonical_json({
            "schema_version": SCHEMA_VERSION,
            "seat": SEAT,
            "plan_sha256": plan_sha,
            "slots": p_ledger,
            "generated_at_utc": utc_now_iso(),
        }) + "\n")
    (root / "promotion_identity_ledger.json").write_text(
        canonical_json(global_ledger) + "\n")

    report = {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "network_calls": call_count,
        "max_network_calls": MAX_CALLS,
        "plan_sha256": plan_sha,
        "p_pass_count": sum(1 for x in p_ledger if x["qualification_verdict"] == "pass"),
        "p_shortfall": any(x["qualification_verdict"] != "pass" for x in p_ledger),
        "global_assertions": global_ledger["assertions"],
        "promoted_row_count": global_ledger["row_count"],
        "replacement_shortfall": global_ledger["replacement_shortfall"],
        "b_replacement_shortfall": global_ledger["b_replacement_shortfall"],
        "generated_at_utc": utc_now_iso(),
    }
    (root / "capture_report.json").write_text(canonical_json(report) + "\n")

    return {
        "mode": "live",
        "network_calls": call_count,
        "qualification_ledger": p_ledger,
        "promotion_identity_ledger": global_ledger,
        "report": report,
    }


def verify_hashes(root: Path = K4_ROOT) -> list[str]:
    errors: list[str] = []
    for spec in FROZEN_P:
        cdir = root / "captures" / spec.slot
        if not cdir.exists():
            errors.append(f"missing {spec.slot}")
            continue
        sc = json.loads((cdir / "sidecar.json").read_text())
        raw_p = cdir / "raw.json"
        if sha256_file(raw_p) != sc.get("raw_sha256"):
            errors.append(f"hash mismatch {spec.slot}")
        if sc.get("qualification_verdict") == "fail" and sc.get("oracle_id"):
            errors.append(f"oracle on failed {spec.slot}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EFC K4 P-slot capture")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--repair-ledger", action="store_true")
    parser.add_argument("--verify-hashes", action="store_true")
    args = parser.parse_args(argv)

    if args.verify_hashes:
        errs = verify_hashes()
        if errs:
            for e in errs:
                print(e, file=sys.stderr)
            return 1
        print("all K4 hashes verified")
        return 0

    if args.repair_ledger:
        try:
            print(canonical_json(repair_ledger()))
        except CaptureRefusal as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
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
