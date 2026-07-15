"""EFC v0 K3 mechanical snapshot capture — Families E and F.

Ten frozen GET attempts (six SPDX JSON + four HTML deprecation records).
No calibration engine contact, no search, no retry, no redirect follow.

Usage:
  python -m harness.efc_capture_k3              # dry-run, zero network
  python -m harness.efc_capture_k3 --execute  # one live run (create-once)
  python -m harness.efc_capture_k3 --verify-hashes
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
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Protocol

REPO = Path(__file__).resolve().parent.parent
K3_ROOT = REPO / "corpus" / "efc_calibration" / "_acquisition" / "k3"
SCHEMA_VERSION = "efc-k3-acquisition-v1"
SEAT = "cursor/composer-2.5-capture"
MAX_CALLS = 10

_BLOCK_TAGS = frozenset({
    "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt",
    "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2",
    "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol",
    "p", "pre", "section", "table", "tbody", "td", "th", "thead", "tr", "ul",
})


@dataclass(frozen=True)
class K3Spec:
    capture_id: str
    family: str
    capture_url: str
    record_id: str
    entity_kind: str  # exception | license | html
    raw_name: str


FAMILY_E: tuple[K3Spec, ...] = (
    K3Spec("capE-01", "E",
           "https://raw.githubusercontent.com/spdx/license-list-data/main/json/exceptions/Classpath-exception-2.0.json",
           "Classpath-exception-2.0", "exception", "raw.json"),
    K3Spec("capE-02", "E",
           "https://raw.githubusercontent.com/spdx/license-list-data/main/json/exceptions/LLVM-exception.json",
           "LLVM-exception", "exception", "raw.json"),
    K3Spec("capE-03", "E",
           "https://raw.githubusercontent.com/spdx/license-list-data/main/json/exceptions/Bootloader-exception.json",
           "Bootloader-exception", "exception", "raw.json"),
    K3Spec("capE-04", "E",
           "https://raw.githubusercontent.com/spdx/license-list-data/main/json/BSL-1.0.json",
           "BSL-1.0", "license", "raw.json"),
    K3Spec("capE-05", "E",
           "https://raw.githubusercontent.com/spdx/license-list-data/main/json/MPL-2.0.json",
           "MPL-2.0", "license", "raw.json"),
    K3Spec("capE-06", "E",
           "https://raw.githubusercontent.com/spdx/license-list-data/main/json/EPL-2.0.json",
           "EPL-2.0", "license", "raw.json"),
)

FAMILY_F: tuple[K3Spec, ...] = (
    K3Spec("capF-01", "F",
           "https://kubernetes.io/docs/reference/using-api/deprecation-guide/",
           "kubernetes-deprecation-v1.32-flowcontrol", "html", "raw.html"),
    K3Spec("capF-02", "F",
           "https://docs.djangoproject.com/en/6.0/releases/5.0/",
           "django-5.0-pytz-removal", "html", "raw.html"),
    K3Spec("capF-03", "F",
           "https://flask.palletsprojects.com/en/3.1.x/changes/",
           "flask-2.3.0-env-removal", "html", "raw.html"),
    K3Spec("capF-04", "F",
           "https://guides.rubyonrails.org/7_2_release_notes.html",
           "rails-7.2-dependency-loading-removal", "html", "raw.html"),
)

FROZEN_ATTEMPTS: tuple[K3Spec, ...] = FAMILY_E + FAMILY_F
FROZEN_URLS: frozenset[str] = frozenset(s.capture_url for s in FROZEN_ATTEMPTS)


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


def capture_dir(spec: K3Spec, root: Path = K3_ROOT) -> Path:
    return root / "captures" / spec.capture_id


def extract_dir(spec: K3Spec, root: Path = K3_ROOT) -> Path:
    return root / "extracts" / spec.capture_id


def build_plan(root: Path = K3_ROOT) -> dict:
    entries = []
    for spec in FROZEN_ATTEMPTS:
        cdir = capture_dir(spec, root)
        row = {
            "id": spec.capture_id,
            "family": spec.family,
            "entity_kind": spec.entity_kind,
            "record_id": spec.record_id,
            "capture_url": spec.capture_url,
            "expected_format": "json" if spec.family == "E" else "html",
            "raw_path": str((cdir / spec.raw_name).relative_to(root)),
            "sidecar_path": str((cdir / "sidecar.json").relative_to(root)),
        }
        if spec.family == "F":
            edir = extract_dir(spec, root)
            row["extract_paths"] = {
                "normalized": str((edir / "normalized.txt").relative_to(root)),
                "section": str((edir / "section.txt").relative_to(root)),
                "extract": str((edir / "extract.json").relative_to(root)),
            }
        entries.append(row)
    plan_body = {
        "schema_version": SCHEMA_VERSION,
        "attempt_count": len(FROZEN_ATTEMPTS),
        "max_network_calls": MAX_CALLS,
        "request_method": "GET",
        "redirect_policy": "refuse",
        "retry_policy": "zero",
        "implementation_module_sha256": module_sha256(),
        "entries": entries,
    }
    plan = dict(plan_body)
    plan["plan_sha256"] = sha256_bytes(canonical_json(plan_body).encode())
    return plan


def refuse_unknown_url(url: str) -> None:
    if url not in FROZEN_URLS:
        raise CaptureRefusal(f"unknown or unauthorized URL: {url}")


def check_create_once(root: Path = K3_ROOT) -> None:
    if root.exists():
        for p in root.rglob("*"):
            if p.is_file():
                raise CaptureRefusal(
                    f"create-once refusal: artifact already exists: {p}")


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
    refuse_unknown_url(url)
    opener = urllib.request.build_opener(_RefuseRedirect())
    req = urllib.request.Request(
        url,
        headers={"Accept": "*/*", "User-Agent": "efc-k3-capture/1"},
    )
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


def _parse_json(body: bytes) -> tuple[dict | None, str | None]:
    try:
        data = json.loads(body.decode("utf-8"))
        if not isinstance(data, dict):
            return None, "json_not_object"
        return data, None
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return None, f"json_parse_error:{type(e).__name__}"


def _field_or_absent(data: dict, key: str) -> object:
    return data[key] if key in data else None


def validate_family_e(spec: K3Spec, data: dict | None, http_ok: bool,
                      parse_err: str | None, redirect_refused: bool,
                      ) -> tuple[str, list[str], dict]:
    failures: list[str] = []
    meta: dict = {}
    if redirect_refused:
        failures.append("redirect_refused")
    if not http_ok:
        failures.append("http_failure")
    if parse_err:
        failures.append(parse_err)
    if data is None:
        return "fail", failures, meta

    if spec.entity_kind == "exception":
        if data.get("licenseId"):
            failures.append("license_id_on_exception_record")
        exc_id = data.get("licenseExceptionId")
        meta["licenseExceptionId"] = exc_id
        meta["licenseExceptionName"] = _field_or_absent(data, "licenseExceptionName")
        meta["licenseListVersion"] = _field_or_absent(data, "licenseListVersion")
        text = data.get("licenseExceptionText")
        meta["licenseExceptionText_present"] = bool(
            isinstance(text, str) and text.strip())
        if exc_id != spec.record_id:
            failures.append("record_id_mismatch")
        if not (isinstance(text, str) and text.strip()):
            failures.append("missing_exception_text")
    else:
        if data.get("licenseExceptionId"):
            failures.append("exception_id_on_license_record")
        lic_id = data.get("licenseId")
        meta["licenseId"] = lic_id
        meta["licenseName"] = _field_or_absent(data, "licenseName")
        meta["licenseListVersion"] = _field_or_absent(data, "licenseListVersion")
        text = data.get("licenseText")
        meta["licenseText_present"] = bool(
            isinstance(text, str) and text.strip())
        if lic_id != spec.record_id:
            failures.append("record_id_mismatch")
        if not (isinstance(text, str) and text.strip()):
            failures.append("missing_license_text")

    return ("pass" if not failures else "fail"), failures, meta


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip_depth += 1
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript") and self._skip_depth:
            self._skip_depth -= 1
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def text(self) -> str:
        return "".join(self._parts)


def html_to_text(html_bytes: bytes) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    parser.close()
    return parser.text()


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for line in text.split("\n"):
        collapsed = re.sub(r"[ \t]+", " ", line).strip()
        if collapsed:
            lines.append(collapsed)
    return "\n".join(lines)


def _section_between(text: str, start_marker: str,
                     end_markers: tuple[str, ...]) -> str | None:
    idx = text.find(start_marker)
    if idx < 0:
        return None
    chunk = text[idx:]
    end = len(chunk)
    for em in end_markers:
        pos = chunk.find(em, len(start_marker))
        if pos > 0:
            end = min(end, pos)
    return chunk[:end].strip()


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _subsection_after(text: str, start_marker: str, sub_marker: str,
                      end_markers: tuple[str, ...]) -> str | None:
    start = text.find(start_marker)
    if start < 0:
        return None
    sub = text.find(sub_marker, start + len(start_marker))
    if sub < 0:
        return None
    chunk = text[sub:]
    end = len(chunk)
    for em in end_markers:
        pos = chunk.find(em, len(sub_marker))
        if pos > 0:
            end = min(end, pos)
    return chunk[:end].strip()


def _find_statement(section: str, required: str) -> str | None:
    if required in section:
        return required
    collapsed = _collapse_ws(section)
    if required in collapsed:
        return required
    if (required + ".") in collapsed:
        return required
    for line in section.split("\n"):
        if line.strip().rstrip(".") == required:
            return required
    return None


def extract_family_f(spec: K3Spec, html_bytes: bytes) -> tuple[dict, list[str]]:
    """Return (extract_payload, failure_reasons)."""
    failures: list[str] = []
    raw_text = html_to_text(html_bytes)
    normalized = normalize_text(raw_text)
    extract: dict = {
        "capture_id": spec.capture_id,
        "normalized_text_sha256": sha256_bytes(normalized.encode("utf-8")),
    }

    if spec.capture_id == "capF-01":
        locator = "heading:Removed APIs by release -> flowcontrol v1beta3/v1.32"
        ra = normalized.find("Removed APIs by release")
        fc_idx = normalized.find("flowcontrol.apiserver.k8s.io/v1beta3")
        if ra < 0 or fc_idx < 0 or fc_idx < ra:
            failures.append("missing_bounded_section")
            bounded = ""
        else:
            bounded = normalized[ra:fc_idx + 400]
        collapsed = _collapse_ws(bounded)
        needles = (
            "flowcontrol.apiserver.k8s.io/v1beta3",
            "FlowSchema",
            "PriorityLevelConfiguration",
            "no longer served",
            "v1.32",
        )
        if not all(n in collapsed for n in needles):
            failures.append("missing_required_statement")
        matched = None
        if all(n in collapsed for n in needles):
            idx = collapsed.find("flowcontrol.apiserver.k8s.io/v1beta3")
            end_marker = "no longer served as of v1.32."
            end = collapsed.find(end_marker, idx)
            if end >= 0:
                matched = collapsed[idx:end + len(end_marker)]
            elif idx >= 0:
                v = collapsed.find("v1.32", idx)
                period = collapsed.find(".", v) if v >= 0 else -1
                matched = collapsed[idx:period + 1] if period > idx else collapsed[idx:]
        if matched is None and not failures:
            failures.append("missing_exact_statement")
        extract.update({
            "locator_method": locator,
            "heading_anchor": "Removed APIs by release / v1.32 / flowcontrol v1beta3",
            "matched_statement": matched,
            "named_surface": "flowcontrol.apiserver.k8s.io/v1beta3 FlowSchema PriorityLevelConfiguration",
            "framework_version": "v1.32",
            "relation": "no_longer_served",
        })

    elif spec.capture_id == "capF-02":
        section = _section_between(
            normalized,
            "Features removed in 5.0",
            ("Features deprecated in 5.0", "Features removed in 4."),
        )
        required = "Support for pytz timezones is removed."
        matched = _find_statement(section or "", required)
        if section is None:
            failures.append("missing_bounded_section")
        if matched != required:
            failures.append("missing_exact_statement")
        extract.update({
            "locator_method": "heading:Features removed in 5.0",
            "heading_anchor": "Features removed in 5.0",
            "matched_statement": matched,
            "named_surface": "pytz timezone support",
            "framework_version": "5.0",
            "relation": "removed",
        })
        bounded = section or ""

    elif spec.capture_id == "capF-03":
        section = _section_between(
            normalized,
            "Version 2.3.0",
            ("Version 2.2.", "Version 2.4."),
        )
        required = (
            "The FLASK_ENV environment variable, ENV config key, "
            "and app.env property are removed."
        )
        bounded = section or ""
        if section is None or "Remove previously deprecated code" not in bounded:
            failures.append("missing_bounded_section")
        matched = _find_statement(bounded, required)
        if matched != required:
            failures.append("missing_exact_statement")
        date_ok = "2023-04-25" in bounded
        if not date_ok:
            failures.append("wrong_official_record_date")
        extract.update({
            "locator_method": "heading:Version 2.3.0 -> Remove previously deprecated code",
            "heading_anchor": "Version 2.3.0",
            "matched_statement": matched if matched == required else None,
            "named_surface": "FLASK_ENV; ENV; app.env",
            "framework_version": "2.3.0",
            "official_record_date": "2023-04-25" if date_ok else None,
            "relation": "removed",
        })

    elif spec.capture_id == "capF-04":
        required = "Remove deprecated Rails.config.enable_dependency_loading"
        stmt_key = "Rails.config.enable_dependency_loading"
        stmt_pos = normalized.find(stmt_key)
        railties_positions = [m.start() for m in re.finditer("Railties", normalized)]
        rt = max((p for p in railties_positions if p < stmt_pos), default=-1)
        rm = normalized.find("Removals", rt) if rt >= 0 else -1
        bounded = normalized[rt:stmt_pos + 120] if rt >= 0 and stmt_pos >= 0 else ""
        search_in = bounded
        matched = _find_statement(search_in, required)
        if "7.2" not in normalized[:800]:
            failures.append("wrong_version_context")
        if rt < 0 or rm < 0 or stmt_pos < rm:
            failures.append("missing_bounded_section")
        if matched != required:
            failures.append("missing_exact_statement")
        extract.update({
            "locator_method": "heading:Railties -> Removals (content section)",
            "heading_anchor": "Railties / Removals",
            "matched_statement": matched,
            "named_surface": "Rails.config.enable_dependency_loading",
            "framework_version": "7.2",
            "relation": "removed",
        })
    else:
        failures.append("unknown_capture_id")
        bounded = ""

    section_text = bounded if spec.capture_id in {
        "capF-01", "capF-02", "capF-03", "capF-04"} else ""
    extract["section_text_sha256"] = sha256_bytes(
        section_text.encode("utf-8")) if section_text else None
    return extract, failures


def validate_family_f(spec: K3Spec, html_bytes: bytes, http_ok: bool,
                      redirect_refused: bool) -> tuple[str, list[str], dict]:
    failures: list[str] = []
    if redirect_refused:
        failures.append("redirect_refused")
    if not http_ok:
        failures.append("http_failure")
    extract: dict = {}
    if http_ok and not redirect_refused:
        try:
            extract, ext_failures = extract_family_f(spec, html_bytes)
            failures.extend(ext_failures)
        except Exception as e:
            failures.append(f"html_parse_error:{type(e).__name__}")
    verdict = "pass" if not failures else "fail"
    return verdict, failures, extract


def build_sidecar(spec: K3Spec, plan_sha: str, resp: TransportResponse,
                  body: bytes, qualification: dict) -> dict:
    sc = {
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
        "plan_sha256": plan_sha,
        "implementation_module_sha256": module_sha256(),
        "capture_verdict": qualification.get("verdict", "fail"),
        "failure_reasons": qualification.get("failure_reasons", []),
    }
    if spec.family == "E":
        sc.update(qualification.get("meta", {}))
    else:
        sc["extract_summary"] = {
            k: qualification.get("extract", {}).get(k)
            for k in (
                "locator_method", "heading_anchor", "matched_statement",
                "named_surface", "framework_version", "relation",
                "official_record_date", "normalized_text_sha256",
                "section_text_sha256",
            )
        }
    return sc


def write_family_e(spec: K3Spec, root: Path, plan_sha: str,
                   resp: TransportResponse) -> dict:
    body = resp.body
    data, parse_err = _parse_json(body)
    http_ok = 200 <= resp.status < 300 and not resp.redirect_refused
    verdict, failures, meta = validate_family_e(
        spec, data, http_ok, parse_err, resp.redirect_refused)
    cdir = capture_dir(spec, root)
    cdir.mkdir(parents=True, exist_ok=True)
    raw_path = cdir / spec.raw_name
    sidecar_path = cdir / "sidecar.json"
    if raw_path.exists() or sidecar_path.exists():
        raise CaptureRefusal(f"create-once refusal: {cdir}")
    raw_path.write_bytes(body)
    qual = {"verdict": verdict, "failure_reasons": failures, "meta": meta}
    sidecar = build_sidecar(spec, plan_sha, resp, body, qual)
    sidecar_path.write_text(canonical_json(sidecar) + "\n")
    return sidecar


def write_family_f(spec: K3Spec, root: Path, plan_sha: str,
                   resp: TransportResponse) -> dict:
    body = resp.body
    http_ok = 200 <= resp.status < 300 and not resp.redirect_refused
    verdict, failures, extract = validate_family_f(
        spec, body, http_ok, resp.redirect_refused)
    cdir = capture_dir(spec, root)
    edir = extract_dir(spec, root)
    cdir.mkdir(parents=True, exist_ok=True)
    edir.mkdir(parents=True, exist_ok=True)
    raw_path = cdir / spec.raw_name
    sidecar_path = cdir / "sidecar.json"
    norm_path = edir / "normalized.txt"
    sect_path = edir / "section.txt"
    ext_path = edir / "extract.json"
    for p in (raw_path, sidecar_path, norm_path, sect_path, ext_path):
        if p.exists():
            raise CaptureRefusal(f"create-once refusal: {p}")
    raw_path.write_bytes(body)
    if http_ok and not resp.redirect_refused:
        normalized = normalize_text(html_to_text(body))
        norm_path.write_bytes(normalized.encode("utf-8"))
        _, ext_failures = extract_family_f(spec, body)
        section_text = ""
        if spec.capture_id == "capF-01":
            ra = normalized.find("Removed APIs by release")
            fc_idx = normalized.find("flowcontrol.apiserver.k8s.io/v1beta3")
            section_text = normalized[ra:fc_idx + 400] if ra >= 0 and fc_idx > ra else ""
        elif spec.capture_id == "capF-02":
            section_text = _section_between(
                normalized, "Features removed in 5.0",
                ("Features deprecated in 5.0",)) or ""
        elif spec.capture_id == "capF-03":
            section_text = _section_between(
                normalized, "Version 2.3.0",
                ("Version 2.2.", "Version 2.4.")) or ""
        elif spec.capture_id == "capF-04":
            stmt_pos = normalized.find("Rails.config.enable_dependency_loading")
            rt = max((m.start() for m in re.finditer("Railties", normalized)
                      if m.start() < stmt_pos), default=-1)
            section_text = normalized[rt:stmt_pos + 120] if rt >= 0 and stmt_pos >= 0 else ""
        sect_path.write_bytes(section_text.encode("utf-8"))
        extract["section_text_sha256"] = sha256_bytes(
            section_text.encode("utf-8")) if section_text else None
        ext_path.write_text(canonical_json(extract) + "\n")
    else:
        norm_path.write_text("", encoding="utf-8")
        sect_path.write_text("", encoding="utf-8")
        ext_path.write_text(canonical_json({"capture_id": spec.capture_id}) + "\n")
    qual = {"verdict": verdict, "failure_reasons": failures, "extract": extract}
    sidecar = build_sidecar(spec, plan_sha, resp, body, qual)
    sidecar_path.write_text(canonical_json(sidecar) + "\n")
    return sidecar


def run_attempt(spec: K3Spec, transport: Transport, root: Path,
                plan_sha: str) -> dict:
    refuse_unknown_url(spec.capture_url)
    resp = transport(spec.capture_url)
    if spec.family == "E":
        return write_family_e(spec, root, plan_sha, resp)
    return write_family_f(spec, root, plan_sha, resp)


def build_capture_report(root: Path, plan: dict, call_count: int) -> dict:
    attempts: list[dict] = []
    e_verdicts: dict[str, str] = {}
    f_verdicts: dict[str, str] = {}
    for spec in FROZEN_ATTEMPTS:
        sc_path = capture_dir(spec, root) / "sidecar.json"
        row: dict = {"id": spec.capture_id, "family": spec.family,
                     "capture_url": spec.capture_url}
        if sc_path.exists():
            sc = json.loads(sc_path.read_text())
            row.update({
                "http_status": sc.get("http_status"),
                "redirect_refused": sc.get("redirect_refused"),
                "raw_sha256": sc.get("raw_sha256"),
                "raw_byte_length": sc.get("raw_byte_length"),
                "verdict": sc.get("capture_verdict"),
                "failure_reasons": sc.get("failure_reasons", []),
            })
            if spec.family == "E":
                e_verdicts[spec.capture_id] = sc.get("capture_verdict", "fail")
            else:
                f_verdicts[spec.capture_id] = sc.get("capture_verdict", "fail")
        else:
            row["status"] = "not_executed"
        attempts.append(row)
    e_pass = sum(1 for v in e_verdicts.values() if v == "pass")
    f_pass = sum(1 for v in f_verdicts.values() if v == "pass")
    return {
        "schema_version": SCHEMA_VERSION,
        "plan_sha256": plan["plan_sha256"],
        "network_calls": call_count,
        "max_network_calls": MAX_CALLS,
        "attempts": attempts,
        "family_e_verdicts": e_verdicts,
        "family_f_verdicts": f_verdicts,
        "family_e_pass_count": e_pass,
        "family_f_pass_count": f_pass,
        "family_e_shortfall": e_pass < len(FAMILY_E),
        "family_f_shortfall": f_pass < len(FAMILY_F),
        "generated_at_utc": utc_now_iso(),
        "seat": SEAT,
    }


def verify_hashes(root: Path = K3_ROOT) -> list[str]:
    errors: list[str] = []
    for spec in FAMILY_E + FAMILY_F:
        cdir = capture_dir(spec, root)
        raw_path = cdir / spec.raw_name
        sc_path = cdir / "sidecar.json"
        if not raw_path.exists() or not sc_path.exists():
            errors.append(f"missing capture artifacts for {spec.capture_id}")
            continue
        sc = json.loads(sc_path.read_text())
        if sha256_file(raw_path) != sc.get("raw_sha256"):
            errors.append(f"raw hash mismatch {spec.capture_id}")
    for spec in FAMILY_F:
        sc_path = capture_dir(spec, root) / "sidecar.json"
        if not sc_path.exists():
            continue
        sc = json.loads(sc_path.read_text())
        edir = extract_dir(spec, root)
        norm_path = edir / "normalized.txt"
        if norm_path.exists():
            nh = sha256_file(norm_path)
            expected = (sc.get("extract_summary") or {}).get(
                "normalized_text_sha256")
            ext_path = edir / "extract.json"
            if ext_path.exists():
                ext = json.loads(ext_path.read_text())
                expected = ext.get("normalized_text_sha256")
                if expected and norm_path.stat().st_size > 0:
                    if expected != nh:
                        errors.append(
                            f"normalized hash mismatch extract/sidecar {spec.capture_id}")
    return errors


def dry_run(root: Path = K3_ROOT) -> dict:
    return {"mode": "dry_run", "plan": build_plan(root), "network_calls": 0}


def execute_live(root: Path = K3_ROOT, transport: Transport | None = None) -> dict:
    check_create_once(root)
    root.mkdir(parents=True, exist_ok=True)
    plan = build_plan(root)
    (root / "plan.json").write_text(canonical_json(plan) + "\n")
    plan_sha = plan["plan_sha256"]
    transport = transport or live_transport
    results: list[dict] = []
    call_count = 0
    for spec in FROZEN_ATTEMPTS:
        resp = transport(spec.capture_url)
        call_count += 1
        if spec.family == "E":
            sidecar = write_family_e(spec, root, plan_sha, resp)
        else:
            sidecar = write_family_f(spec, root, plan_sha, resp)
        results.append({
            "id": spec.capture_id,
            "verdict": sidecar.get("capture_verdict"),
        })
    report = build_capture_report(root, plan, call_count)
    (root / "capture_report.json").write_text(canonical_json(report) + "\n")
    return {"mode": "live", "network_calls": call_count,
            "results": results, "report": report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EFC K3 mechanical snapshot capture")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--verify-hashes", action="store_true")
    parser.add_argument("--root", type=Path, default=K3_ROOT)
    args = parser.parse_args(argv)

    if args.verify_hashes:
        errs = verify_hashes(args.root)
        if errs:
            for e in errs:
                print(e, file=sys.stderr)
            return 1
        print("all K3 hashes verified")
        return 0

    if args.execute:
        try:
            outcome = execute_live(args.root)
        except CaptureRefusal as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        print(canonical_json(outcome))
        return 0

    print(canonical_json(dry_run(args.root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
