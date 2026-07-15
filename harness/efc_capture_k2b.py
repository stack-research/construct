"""EFC v0 K2b — ordered Family D mechanical capture (eight frozen URLs).

Preserves K2 tree unchanged. Byte-preserving promotion into capD-01..06.

Usage:
  python -m harness.efc_capture_k2b              # dry-run, zero network
  python -m harness.efc_capture_k2b --execute  # one live run (create-once)
  python -m harness.efc_capture_k2b --verify-all
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

from harness.efc_capture_k2 import (
    FAMILY_C,
    K2_ROOT,
    sha256_bytes,
    sha256_file,
    verify_hashes as verify_k2_hashes,
)

REPO = Path(__file__).resolve().parent.parent
K2B_ROOT = REPO / "corpus" / "efc_calibration" / "_acquisition" / "k2b"
SCHEMA_VERSION = "efc-k2b-acquisition-v1"
SEAT = "cursor/composer-2.5-capture"
TARGET_D = 6
MAX_CALLS = 8

K2_FAILED_CANDIDATE_IDS: frozenset[str] = frozenset(
    f"GO-2026-{n}" for n in (
        4273, 4274, 4275, 4277, 4278, 4279, 4282, 4283, 4284, 4285,
        4286, 4287, 4289, 4290, 4292, 4293, 4295, 4296, 4297, 4298,
        4299, 4300, 4301, 4302,
    )
)

KAGI_EXCLUDED_IDS: frozenset[str] = frozenset({
    "GO-2026-4961", "GO-2026-5023", "GO-2026-5601",
    "GO-2026-4984", "GO-2026-0001", "GO-2026-0002",
})

FROZEN_EXCLUDED_IDS: frozenset[str] = K2_FAILED_CANDIDATE_IDS | KAGI_EXCLUDED_IDS


@dataclass(frozen=True)
class DSpec:
    order: int
    go_id: str
    module: str
    capture_url: str
    role: str  # primary | alternate
    range_events: tuple[dict[str, str], ...]
    imports: tuple[tuple[str, tuple[str, ...]], ...]


def _events(*items: dict[str, str]) -> tuple[dict[str, str], ...]:
    return tuple(items)


FROZEN_CANDIDATES: tuple[DSpec, ...] = (
    DSpec(1, "GO-2026-4440", "golang.org/x/net",
          "https://vuln.go.dev/ID/GO-2026-4440.json", "primary",
          _events({"introduced": "0"}, {"fixed": "0.45.0"}),
          (("golang.org/x/net/html",
            ("Parse", "ParseFragment", "ParseFragmentWithOptions",
             "ParseWithOptions", "parser.parse")),)),
    DSpec(2, "GO-2026-4507", "github.com/ethereum/go-ethereum",
          "https://vuln.go.dev/ID/GO-2026-4507.json", "primary",
          _events({"introduced": "0"}, {"fixed": "1.16.9"}),
          (("github.com/ethereum/go-ethereum/crypto/secp256k1",
            ("BitCurve.IsOnCurve",)),)),
    DSpec(3, "GO-2026-4535", "github.com/caddyserver/caddy/v2",
          "https://vuln.go.dev/ID/GO-2026-4535.json", "primary",
          _events({"introduced": "0"}, {"fixed": "2.11.1"}),
          (("github.com/caddyserver/caddy/v2/modules/caddyhttp/fileserver",
            ("FileServer.Provision", "FileServer.ServeHTTP",
             "FileServer.UnmarshalCaddyfile", "MatchFile.Match",
             "MatchFile.MatchWithError", "MatchFile.Provision",
             "MatchFile.UnmarshalCaddyfile", "MatchFile.Validate")),)),
    DSpec(4, "GO-2026-4762", "google.golang.org/grpc",
          "https://vuln.go.dev/ID/GO-2026-4762.json", "primary",
          _events({"introduced": "0"}, {"fixed": "1.79.3"}),
          (("google.golang.org/grpc",
            ("Server.Serve", "Server.ServeHTTP", "Server.handleStream")),)),
    DSpec(5, "GO-2026-4610", "github.com/docker/cli",
          "https://vuln.go.dev/ID/GO-2026-4610.json", "primary",
          _events({"introduced": "0"}, {"fixed": "29.2.0+incompatible"}),
          (("github.com/docker/cli/cli-plugins/manager",
            ("defaultSystemPluginDirs",)),)),
    DSpec(6, "GO-2026-4958", "github.com/moby/spdystream",
          "https://vuln.go.dev/ID/GO-2026-4958.json", "primary",
          _events({"introduced": "0"}, {"fixed": "0.5.1"}),
          (("github.com/moby/spdystream",
            ("Connection.Serve", "NewConnection", "idleAwareFramer.ReadFrame")),
           ("github.com/moby/spdystream/spdy",
            ("Framer.ReadFrame", "NewFramer")))),
    DSpec(7, "GO-2026-4479", "github.com/pion/dtls/v3",
          "https://vuln.go.dev/ID/GO-2026-4479.json", "alternate",
          _events({"introduced": "3.0.10"}, {"fixed": "3.0.11"},
                  {"introduced": "3.1.0"}, {"fixed": "3.1.1"}),
          (("github.com/pion/dtls/v3/pkg/crypto/ciphersuite",
            ("aead.encrypt",)),)),
    DSpec(8, "GO-2026-5410", "github.com/slack-go/slack",
          "https://vuln.go.dev/ID/GO-2026-5410.json", "alternate",
          _events({"introduced": "0"}, {"fixed": "0.23.1"}),
          (("github.com/slack-go/slack",
            ("NewSecretsVerifier", "unsafeSignatureVerifier")),)),
)

FROZEN_URLS: frozenset[str] = frozenset(s.capture_url for s in FROZEN_CANDIDATES)


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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def module_sha256() -> str:
    return sha256_file(Path(__file__).resolve())


def tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def check_create_once(root: Path = K2B_ROOT) -> None:
    if root.exists():
        for p in root.rglob("*"):
            if p.is_file():
                raise CaptureRefusal(f"create-once: artifact exists: {p}")


def _spec_dict(spec: DSpec) -> dict:
    return {
        "order": spec.order,
        "go_id": spec.go_id,
        "module": spec.module,
        "capture_url": spec.capture_url,
        "role": spec.role,
        "selected_affected_index": 0,
        "range_events": list(spec.range_events),
        "imports": {path: list(syms) for path, syms in spec.imports},
    }


def build_plan() -> dict:
    body = {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "phase": "ordered_family_d_capture",
        "network_calls_min": TARGET_D,
        "network_calls_max": MAX_CALLS,
        "target_d_qualifiers": TARGET_D,
        "redirect_policy": "refuse",
        "retry_policy": "zero",
        "candidates": [_spec_dict(s) for s in FROZEN_CANDIDATES],
        "excluded_go_ids": sorted(FROZEN_EXCLUDED_IDS),
        "implementation_module_sha256": module_sha256(),
    }
    plan = dict(body)
    plan["plan_sha256"] = sha256_bytes(canonical_json(body).encode())
    return plan


def _normalize_events(events: list) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for e in events:
        if not isinstance(e, dict):
            continue
        row: dict[str, str] = {}
        if "introduced" in e and isinstance(e["introduced"], str):
            row["introduced"] = e["introduced"]
        if "fixed" in e and isinstance(e["fixed"], str):
            row["fixed"] = e["fixed"]
        if "last_affected" in e and isinstance(e["last_affected"], str):
            row["last_affected"] = e["last_affected"]
        if row:
            out.append(row)
    return out


def _imports_map(imports: list) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for imp in imports:
        if not isinstance(imp, dict):
            continue
        path = imp.get("path")
        syms = imp.get("symbols")
        if isinstance(path, str) and isinstance(syms, list):
            out[path] = [s for s in syms if isinstance(s, str)]
    return out


def qualify_candidate(
    spec: DSpec,
    report: dict,
    *,
    http_status: int,
    redirect_refused: bool,
    selected_modules: set[str],
) -> tuple[bool, list[str], dict]:
    reasons: list[str] = []
    field_checks: dict = {}

    if http_status != 200:
        reasons.append("http_not_200")
    if redirect_refused:
        reasons.append("redirect_refused")
    if spec.go_id in FROZEN_EXCLUDED_IDS:
        reasons.append("excluded_go_id")
    if report.get("id") != spec.go_id:
        reasons.append("id_mismatch")
        field_checks["id"] = report.get("id")
    published = report.get("published") or ""
    if not isinstance(published, str) or not published.startswith("2026"):
        reasons.append("publication_not_2026")
    db = report.get("database_specific") or {}
    if db.get("review_status") != "REVIEWED":
        reasons.append("not_reviewed")
    affected = report.get("affected") or []
    if not affected or not isinstance(affected[0], dict):
        reasons.append("missing_affected_0")
        return False, reasons, field_checks
    aff = affected[0]
    pkg = aff.get("package") or {}
    if pkg.get("ecosystem") != "Go":
        reasons.append("ecosystem_not_go")
    mod = pkg.get("name")
    if mod != spec.module:
        reasons.append("module_mismatch")
        field_checks["module"] = mod
    if mod in selected_modules:
        reasons.append("module_already_selected")
    ranges = aff.get("ranges") or []
    if not ranges or not isinstance(ranges[0], dict):
        reasons.append("missing_range_0")
        return False, reasons, field_checks
    rng = ranges[0]
    if rng.get("type") != "SEMVER":
        reasons.append("range_type_not_semver")
    actual_events = _normalize_events(rng.get("events") or [])
    expected_events = [dict(e) for e in spec.range_events]
    if actual_events != expected_events:
        reasons.append("range_events_mismatch")
        field_checks["range_events_actual"] = actual_events
        field_checks["range_events_expected"] = expected_events
    has_fixed = any("fixed" in e for e in actual_events)
    if not has_fixed:
        reasons.append("no_finite_fixed")
    eco = aff.get("ecosystem_specific") or {}
    imp_map = _imports_map(eco.get("imports") or [])
    for path, expected_syms in spec.imports:
        actual_syms = imp_map.get(path)
        if actual_syms != list(expected_syms):
            reasons.append(f"imports_mismatch:{path}")
            field_checks[f"imports_{path}"] = actual_syms
    ok = not reasons
    return ok, reasons, field_checks


@dataclass
class LiveResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    redirect_chain: list[str]
    redirect_refused: bool = False


def live_transport(url: str) -> LiveResponse:
    chain = [url]
    req = urllib.request.Request(
        url, headers={"User-Agent": "efc-k2b-capture/1.0"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            final = resp.geturl()
            if final != url:
                return LiveResponse(
                    status=resp.status,
                    headers=dict(resp.headers),
                    body=resp.read(),
                    url=url,
                    redirect_chain=chain + [final],
                    redirect_refused=True,
                )
            return LiveResponse(
                status=resp.status,
                headers=dict(resp.headers),
                body=resp.read(),
                url=final,
                redirect_chain=chain,
            )
    except urllib.error.HTTPError as e:
        return LiveResponse(
            status=e.code,
            headers=dict(e.headers),
            body=e.read(),
            url=url,
            redirect_chain=chain,
        )


def dry_run() -> dict:
    return {
        "mode": "dry_run",
        "network_calls": 0,
        "plan": build_plan(),
        "authorized_urls": sorted(FROZEN_URLS),
    }


def execute_live(
    root: Path = K2B_ROOT,
    transport: Transport | None = None,
) -> dict:
    check_create_once(root)
    k2_pre = tree_digest(K2_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    transport = transport or live_transport
    plan = build_plan()
    plan_sha = plan["plan_sha256"]
    (root / "plan.json").write_text(canonical_json(plan) + "\n")

    call_count = 0
    attempts: list[dict] = []
    selected: list[dict] = []
    selected_modules: set[str] = set()
    contacted_ids: set[str] = set()

    for spec in FROZEN_CANDIDATES:
        if len(selected) >= TARGET_D:
            break
        resp = transport(spec.capture_url)
        call_count += 1
        contacted_ids.add(spec.go_id)
        try:
            report = json.loads(resp.body.decode("utf-8"))
            if not isinstance(report, dict):
                report = {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            report = {}
        ok, reasons, field_checks = qualify_candidate(
            spec, report,
            http_status=resp.status,
            redirect_refused=resp.redirect_refused,
            selected_modules=selected_modules,
        )
        attempt_dir = root / "attempts" / spec.go_id
        attempt_dir.mkdir(parents=True, exist_ok=True)
        (attempt_dir / "raw.json").write_bytes(resp.body)
        raw_sha = sha256_bytes(resp.body)
        sidecar = {
            "schema_version": SCHEMA_VERSION,
            "go_id": spec.go_id,
            "capture_url": spec.capture_url,
            "role": spec.role,
            "order": spec.order,
            "http_status": resp.status,
            "redirect_refused": resp.redirect_refused,
            "redirect_chain": resp.redirect_chain,
            "raw_sha256": raw_sha,
            "raw_byte_length": len(resp.body),
            "retrieved_at_utc": utc_now_iso(),
            "plan_sha256": plan_sha,
            "qualification_verdict": "pass" if ok else "fail",
            "failure_reasons": reasons,
            "field_checks": field_checks,
            "implementation_module_sha256": module_sha256(),
        }
        if not ok:
            sidecar["oracle_id"] = None
        (attempt_dir / "sidecar.json").write_text(
            canonical_json(sidecar) + "\n")

        row = {
            "go_id": spec.go_id,
            "order": spec.order,
            "role": spec.role,
            "contacted": True,
            "qualification_verdict": sidecar["qualification_verdict"],
            "failure_reasons": reasons,
            "raw_sha256": raw_sha,
            "field_checks": field_checks,
        }
        attempts.append(row)

        if ok:
            cap_id = f"capD-{len(selected) + 1:02d}"
            cap_dir = root / "captures" / cap_id
            cap_dir.mkdir(parents=True)
            (cap_dir / "raw.json").write_bytes(resp.body)
            cap_sc = {
                "schema_version": SCHEMA_VERSION,
                "capture_id": cap_id,
                "family": "D",
                "go_id": spec.go_id,
                "module": spec.module,
                "oracle_id": f"efc-calibration-{cap_id}",
                "capture_verdict": "pass",
                "source_attempt_id": spec.go_id,
                "source_raw_sha256": raw_sha,
                "promoted_from_attempt": True,
                "plan_sha256": plan_sha,
                "retrieved_at_utc": sidecar["retrieved_at_utc"],
                "raw_sha256": raw_sha,
                "implementation_module_sha256": module_sha256(),
            }
            (cap_dir / "sidecar.json").write_text(
                canonical_json(cap_sc) + "\n")
            selected_modules.add(spec.module)
            selected.append({
                "logical_slot": f"D{len(selected) + 1:02d}",
                "capture_id": cap_id,
                "go_id": spec.go_id,
                "module": spec.module,
                "source_attempt_id": spec.go_id,
            })

    not_contacted = []
    for spec in FROZEN_CANDIDATES:
        if spec.go_id not in contacted_ids:
            not_contacted.append({
                "go_id": spec.go_id,
                "order": spec.order,
                "role": spec.role,
                "status": "not_contacted_after_six_passes",
            })

    family_d_shortfall = len(selected) < TARGET_D
    selection_ledger = {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "plan_sha256": plan_sha,
        "attempts": attempts,
        "not_contacted": not_contacted,
        "selected_d": selected,
        "family_d_pass_count": len(selected),
        "family_d_shortfall": family_d_shortfall,
        "network_calls": call_count,
        "generated_at_utc": utc_now_iso(),
    }
    (root / "selection_ledger.json").write_text(
        canonical_json(selection_ledger) + "\n")

    promotion = build_promotion_ledger(root, plan_sha, selected, not_contacted)
    (root / "promotion_ledger.json").write_text(
        canonical_json(promotion) + "\n")

    k2_post = tree_digest(K2_ROOT)
    report = {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "network_calls": call_count,
        "max_network_calls": MAX_CALLS,
        "plan_sha256": plan_sha,
        "family_d_pass": len(selected),
        "family_d_shortfall": family_d_shortfall,
        "k2_tree_unchanged": k2_pre == k2_post,
        "k2_tree_hash": k2_post,
        "k2_closed": promotion.get("k2_closed"),
        "generated_at_utc": utc_now_iso(),
    }
    (root / "capture_report.json").write_text(
        canonical_json(report) + "\n")

    return {
        "mode": "live",
        "network_calls": call_count,
        "selection_ledger": selection_ledger,
        "promotion_ledger": promotion,
        "report": report,
    }


def build_promotion_ledger(
    root: Path,
    plan_sha: str,
    selected: list[dict],
    not_contacted: list[dict],
) -> dict:
    mappings: list[dict] = []
    for i, spec in enumerate(FAMILY_C, start=1):
        cid = spec.capture_id
        cdir = K2_ROOT / "captures" / cid
        raw_p = cdir / "raw.json"
        sc_p = cdir / "sidecar.json"
        sc = json.loads(sc_p.read_text())
        mappings.append({
            "logical_slot": f"C{i:02d}",
            "source_capture_id": cid,
            "source_kind": "k2_original",
            "promotion_eligible": sc.get("capture_verdict") == "pass",
            "qualification_verdict": sc.get("capture_verdict"),
            "artifact_hashes": {
                "raw_sha256": sha256_file(raw_p),
                "sidecar_sha256": sha256_file(sc_p),
            },
        })

    for row in selected:
        cap_id = row["capture_id"]
        cdir = root / "captures" / cap_id
        mappings.append({
            "logical_slot": row["logical_slot"],
            "source_capture_id": cap_id,
            "source_kind": "k2b_selected",
            "source_go_id": row["go_id"],
            "module": row["module"],
            "promotion_eligible": True,
            "qualification_verdict": "pass",
            "artifact_hashes": {
                "raw_sha256": sha256_file(cdir / "raw.json"),
                "sidecar_sha256": sha256_file(cdir / "sidecar.json"),
            },
        })

    k2_failed: list[dict] = []
    k2_ledger = json.loads(
        (K2_ROOT / "selection_ledger.json").read_text())
    for row in k2_ledger.get("d_candidate_attempts", []):
        gid = row["candidate_id"]
        qual_dir = K2_ROOT / "qualification" / "go_candidates" / gid
        sc_p = qual_dir / "sidecar.json"
        entry = {
            "go_id": gid,
            "promotion_eligible": False,
            "reason": "k2_failed_qualification_attempt",
            "qualification_verdict": row.get("qualification_verdict"),
        }
        if sc_p.exists():
            entry["sidecar_sha256"] = sha256_file(sc_p)
            raw_p = qual_dir / "raw.json"
            if raw_p.exists():
                entry["raw_sha256"] = sha256_file(raw_p)
        k2_failed.append(entry)

    c_pass = sum(1 for m in mappings if m["logical_slot"].startswith("C")
                 and m["promotion_eligible"])
    d_pass = sum(1 for m in mappings if m["logical_slot"].startswith("D")
                 and m["promotion_eligible"])

    return {
        "schema_version": SCHEMA_VERSION,
        "seat": SEAT,
        "plan_sha256": plan_sha,
        "logical_slot_mappings": mappings,
        "k2_failed_ineligible": k2_failed,
        "k2b_not_contacted": not_contacted,
        "family_c_pass_count": c_pass,
        "family_d_pass_count": d_pass,
        "k2_closed": c_pass == 6 and d_pass == 6,
        "generated_at_utc": utc_now_iso(),
    }


def verify_all() -> list[str]:
    errors = list(verify_k2_hashes(K2_ROOT))
    if K2B_ROOT.exists():
        k2_pre = None
        rep = K2B_ROOT / "capture_report.json"
        if rep.exists():
            k2_pre = json.loads(rep.read_text()).get("k2_tree_hash")
        if k2_pre and tree_digest(K2_ROOT) != k2_pre:
            errors.append("K2 tree changed after K2b")
    for spec in FROZEN_CANDIDATES:
        pass  # plan frozen only
    if not (K2B_ROOT / "plan.json").exists():
        return errors + ["missing k2b plan"]
    for cap_n in range(1, 7):
        cid = f"capD-{cap_n:02d}"
        cdir = K2B_ROOT / "captures" / cid
        if not cdir.exists():
            continue
        sc = json.loads((cdir / "sidecar.json").read_text())
        raw_p = cdir / "raw.json"
        if sha256_file(raw_p) != sc.get("raw_sha256"):
            errors.append(f"k2b capD hash mismatch {cid}")
    for spec in FROZEN_CANDIDATES:
        adir = K2B_ROOT / "attempts" / spec.go_id
        if not adir.exists():
            continue
        sc = json.loads((adir / "sidecar.json").read_text())
        if sc.get("qualification_verdict") == "fail" and sc.get("oracle_id"):
            errors.append(f"oracle on failed attempt {spec.go_id}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EFC K2b ordered D capture")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--verify-all", action="store_true")
    args = parser.parse_args(argv)

    if args.verify_all:
        errs = verify_all()
        if errs:
            for e in errs:
                print(e, file=sys.stderr)
            return 1
        print("all K2+K2b verification passed")
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
