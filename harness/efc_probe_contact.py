"""Production ignorance-probe contact surface — probe-only, offline by default.

Distinct from `run_wire_admission_branch` (synthetic wire) and
`run_admission_branch` (full admission board; structurally unmintable here).
`ProbeContactAuthorization` cannot authorize calibration or board contact.

Authority requires a live C4d pin verify, exact manifest/packet/probe/oracle
bindings, one pinned roster branch with co-pinned decoding payload, and budget
for exactly fifteen probe ceilings. Real inference runs only under an explicit
`--contact --branch … --output-dir …` CLI invocation with a minted
authorization; tests inject a fake transport.

Zero network unless `--contact` is explicitly passed in production mode.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from harness import efc_contracts as c
from harness import efc_pin_c4b as c4b
from harness import efc_pin_c4d as c4d
from harness.efc_controller import EngineResult
from harness.efc_manifest import check_calibration_manifest, manifest_hash
from harness.efc_planner import IgnoranceProbeResult
from harness.efc_runner import (ContactAuthorization, RunnerContractError,
                                TransportRefusal, WireContactAuthorization)
from harness.efc_roster_r2 import (API_BASE, API_MODEL, API_TOP_P_INCLUDED,
                                   LOCAL_BASE, LOCAL_MODEL, OUTPUT_CEILING,
                                   _extract_text, _http_post)

ROOT = Path(__file__).resolve().parents[1]
PACKET_INDEX_REL = "episodes/efc_calibration/packet_index.json"
PROBE_CONTRACT_REL = "episodes/efc_calibration/probes/ignorance_probe_contract.json"
PROBE_ANSWER_KEY_REL = "corpus/efc_calibration/oracle/probe_answer_key.json"
REPORT_REL = ("corpus/efc_calibration/authoring_c4/"
              "p0_probe_contact_implementation_report.json")

PROBE_TEMPERATURE = c.CALIBRATION_TEMPERATURE
PROBE_TOP_P = 1.0
PROBE_COUNT = 15
MAX_RECOVERABLE = 3  # pass iff recovered <= 3 of exactly 15
PROVIDER_CACHE_STATUS = "unverified"
VERDICT_IGNORANCE_GATE_PASS = "ignorance_gate_pass"
VERDICT_ENGINE_REFUSED = "engine_refused"
VERDICT_NOT_ENGAGED = "not_engaged"
PROBE_ONLY_VERDICTS = (
    VERDICT_IGNORANCE_GATE_PASS,
    VERDICT_ENGINE_REFUSED,
    VERDICT_NOT_ENGAGED,
)
P1_RUN_ROOT_REL = (
    "runs/efc_calibration/ignorance_probe/"
    "efc-cal-manifest-pin-2600d1fdba7b-s2"
)
P1A_REPORT_REL = (
    "corpus/efc_calibration/authoring_c4/"
    "p1a_ignorance_gate_correction_report.json"
)
IGNORANCE_GATE_RESULT_NAME = "ignorance_gate_result.json"

BRANCH_LOCAL = "local"
BRANCH_API = "api"
BRANCH_MODEL = {
    BRANCH_LOCAL: "openai/gpt-oss-20b",
    BRANCH_API: "gpt-5.4-2026-03-05",
}
ROSTER_BRANCH_ORDER = (BRANCH_LOCAL, BRANCH_API)

SIDECAR_NAME = "probe_sidecar.jsonl"
RESULT_NAME = "probe_branch_result.json"


class ProbeContactError(ValueError):
    """Probe-only contact outside the pinned contract. Fail-closed."""


@dataclass
class ProbeContactAuthorization:
    """Branch-specific, single-use, probe-only production authority."""
    pin_event_id: str
    manifest_file_sha256: str
    manifest_canonical_sha256: str
    packet_index_sha256: str
    probe_answer_key_sha256: str
    probe_fixture_ids: tuple[str, ...]
    probe_texts_sha256: str
    branch: str
    model_id: str
    decoding_contract_sha256: str
    probe_budget_tokens: int
    roster_total_budget_tokens: int
    max_recoverable_rate: float
    consumed: bool = field(default=False, repr=False)

    def mark_consumed(self) -> None:
        if self.consumed:
            raise ProbeContactError(
                "probe authorization already consumed (single-use)")
        object.__setattr__(self, "consumed", True)


class ProbeSessionLease(Protocol):
    isolation_id: str
    used: bool


class ProbeTransport(Protocol):
    """Injectable transport for offline tests; production uses HTTP adapters."""

    def fresh_lease(self, temperature: float) -> ProbeSessionLease:
        ...

    def invoke(self, lease: ProbeSessionLease, request_body: dict) -> str:
        ...


@dataclass
class ProbeBranchResult:
    branch: str
    model_id: str
    recovered_count: int
    n: int
    max_recoverable_rate: float
    gate_pass: bool
    ignorance_gate_verdict: str
    probe_sidecar_sha256: str
    decoding_contract_sha256: str
    status: str
    probe_calls: int
    provider_cache: str = PROVIDER_CACHE_STATUS
    refused: list[dict] = field(default_factory=list)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_canon(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _refuse(msg: str) -> None:
    raise ProbeContactError(msg)


def _rows_sha256(rows: list[dict]) -> str:
    return sha256_canon(rows)


def _normalize_answer(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def score_probe_answer(probe_id: str, answer_text: str,
                       answer_key: dict) -> bool:
    entry = answer_key.get(probe_id)
    if not isinstance(entry, dict):
        _refuse(f"missing or malformed answer-key entry for {probe_id!r}")
    tokens = entry.get("must_contain")
    if not isinstance(tokens, list) or not tokens:
        _refuse(f"answer-key entry for {probe_id!r} lacks must_contain tokens")
    norm = _normalize_answer(answer_text)
    return all(str(token).lower() in norm for token in tokens)


def _probe_texts_sha256(probe_texts: dict[str, str],
                        probe_ids: tuple[str, ...]) -> str:
    ordered = {pid: probe_texts[pid] for pid in probe_ids}
    return sha256_canon(ordered)


def _derive_probe_budget(ledger: dict) -> tuple[int, list[dict]]:
    rows = [r for r in ledger.get("per_branch_rows", ())
            if r.get("category") == "probe" and r.get("lane") == "ignorance_probe"]
    if len(rows) != PROBE_COUNT:
        _refuse(f"ledger must carry exactly {PROBE_COUNT} probe budget rows; "
                f"got {len(rows)}")
    total = sum(int(r["per_call_total"]) for r in rows)
    if total <= 0:
        _refuse("probe budget must be positive")
    return total, rows


def _load_probe_bindings(root: Path) -> dict:
    c4d.verify(root, full=True)
    manifest_path = root / c4b.MANIFEST_REL
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sibling = json.loads((root / c4b.SIBLING_REL).read_text(encoding="utf-8"))
    ledger = json.loads((root / c4b.LEDGER_REL).read_text(encoding="utf-8"))
    packet_index = json.loads((root / PACKET_INDEX_REL).read_text(encoding="utf-8"))
    probe_contract = json.loads(
        (root / PROBE_CONTRACT_REL).read_text(encoding="utf-8"))
    answer_key = json.loads(
        (root / PROBE_ANSWER_KEY_REL).read_text(encoding="utf-8"))

    result = check_calibration_manifest(manifest)
    if not result.ok:
        _refuse(f"manifest failed closed-schema check: {result.failures}")
    if sha256_path(manifest_path) != c4b.MANIFEST_FILE_SHA:
        _refuse("manifest file sha256 does not match the active pin binding")
    if result.manifest_hash != c4b.MANIFEST_CANONICAL_HASH:
        _refuse("manifest canonical hash does not match the active pin binding")
    packet_index_sha = sha256_path(root / PACKET_INDEX_REL)
    lineage_packet = c4d.validate_bundle(root)["lineage"]["packet_index"]
    if packet_index_sha != lineage_packet:
        _refuse("packet index sha256 does not recompute from lineage bindings")

    manifest_probe_ids = tuple(
        manifest["ignorance_probe_contract"]["probe_fixture_ids"])
    contract_probe_ids = tuple(probe_contract["probe_fixture_ids"])
    if manifest_probe_ids != contract_probe_ids:
        _refuse("manifest probe ids do not byte-bind to the packet probe contract")
    if len(manifest_probe_ids) != PROBE_COUNT:
        _refuse(f"probe fixture count must be exactly {PROBE_COUNT}")

    texts = probe_contract["probe_texts"]
    if set(texts) != set(manifest_probe_ids):
        _refuse("probe_texts keys must equal probe_fixture_ids")
    for pid in manifest_probe_ids:
        if pid not in answer_key:
            _refuse(f"probe answer key missing entry for {pid!r}")

    probe_budget, _ = _derive_probe_budget(ledger)
    roster_budget = int(ledger["totals"]["roster_total_budget_tokens"])
    if roster_budget != c4b.APPROVED_BUDGET or roster_budget < probe_budget:
        _refuse("roster budget is not sufficient for the pinned probe ceilings")

    max_rate = float(manifest["ignorance_probe_contract"]["max_recoverable_rate"])
    if max_rate != 0.2:
        _refuse("max_recoverable_rate must be the pinned 0.20 value")

    return {
        "pin_event_id": c4d.SUPERSEDING_EVENT_ID,
        "manifest_file_sha256": c4b.MANIFEST_FILE_SHA,
        "manifest_canonical_sha256": c4b.MANIFEST_CANONICAL_HASH,
        "packet_index_sha256": packet_index_sha,
        "probe_answer_key_sha256": sha256_path(root / PROBE_ANSWER_KEY_REL),
        "probe_fixture_ids": manifest_probe_ids,
        "probe_texts": texts,
        "probe_texts_sha256": _probe_texts_sha256(texts, manifest_probe_ids),
        "probe_budget_tokens": probe_budget,
        "roster_total_budget_tokens": roster_budget,
        "max_recoverable_rate": max_rate,
        "sibling": sibling,
        "answer_key": answer_key,
    }


def _branch_decoding_sha(sibling: dict, branch: str) -> str:
    entry = sibling["branches"].get(branch)
    if not entry:
        _refuse(f"unknown roster branch {branch!r}")
    payload = entry.get("decoding_contract")
    if not payload:
        _refuse(f"sibling carries no {branch} decoding payload bytes")
    got = sha256_canon(payload)
    want = entry.get("decoding_contract_canonical_sha256")
    if got != want:
        _refuse(f"{branch} decoding payload does not recompute to its pin hash")
    if branch == BRANCH_LOCAL and got != c4b.DECODING_LOCAL_SHA:
        _refuse("local decoding hash does not match the co-pinned sibling")
    if branch == BRANCH_API and got != c4b.DECODING_API_SHA:
        _refuse("api decoding hash does not match the co-pinned sibling")
    return got


def _validate_decoding_contract(branch: str, contract: dict) -> None:
    if contract.get("output_ceiling") != OUTPUT_CEILING:
        _refuse(f"{branch}: output ceiling must be {OUTPUT_CEILING}")
    if contract.get("seed") != "unsupported_unavailable":
        _refuse(f"{branch}: seed must be disclosed unavailable")
    if PROBE_TEMPERATURE not in contract.get("temperature_values", ()):
        _refuse(f"{branch}: decoding contract must admit T={PROBE_TEMPERATURE}")
    if branch == BRANCH_LOCAL:
        if not (contract.get("stateless_single_user_message")
                and not contract.get("system_prompt")
                and not contract.get("tools")):
            _refuse("local branch must be a bare single-user-message transport")
        if contract.get("top_p") != PROBE_TOP_P:
            _refuse("local branch top_p must be 1.0")
    if branch == BRANCH_API:
        if not (contract.get("stateless_text_input")
                and contract.get("reasoning_effort") == "none"
                and not contract.get("tools")):
            _refuse("api branch must be bare stateless Responses input")
        if API_TOP_P_INCLUDED and contract.get("top_p") != PROBE_TOP_P:
            _refuse("api branch top_p must be 1.0")


def authorize_probe_contact(branch: str, root: Path = ROOT,
                            ) -> ProbeContactAuthorization:
    """Mint probe-only authority for one pinned roster branch."""
    if branch not in BRANCH_MODEL:
        _refuse(f"branch must be one of {sorted(BRANCH_MODEL)}; got {branch!r}")
    loaded = _load_probe_bindings(root)
    sibling = loaded["sibling"]
    model_id = BRANCH_MODEL[branch]
    entry = sibling["branches"][branch]
    if entry.get("model_id") != model_id:
        _refuse(f"{branch} model_id does not match the pinned roster member")
    contract = entry["decoding_contract"]
    _validate_decoding_contract(branch, contract)
    decoding_sha = _branch_decoding_sha(sibling, branch)
    return ProbeContactAuthorization(
        pin_event_id=loaded["pin_event_id"],
        manifest_file_sha256=loaded["manifest_file_sha256"],
        manifest_canonical_sha256=loaded["manifest_canonical_sha256"],
        packet_index_sha256=loaded["packet_index_sha256"],
        probe_answer_key_sha256=loaded["probe_answer_key_sha256"],
        probe_fixture_ids=loaded["probe_fixture_ids"],
        probe_texts_sha256=loaded["probe_texts_sha256"],
        branch=branch,
        model_id=model_id,
        decoding_contract_sha256=decoding_sha,
        probe_budget_tokens=loaded["probe_budget_tokens"],
        roster_total_budget_tokens=loaded["roster_total_budget_tokens"],
        max_recoverable_rate=loaded["max_recoverable_rate"],
    )


def _reject_non_authority(authorization: object) -> ProbeContactAuthorization:
    if isinstance(authorization, dict):
        _refuse("a mapping is never probe authority")
    if isinstance(authorization, WireContactAuthorization):
        _refuse("wire authorization cannot authorize production probes")
    if isinstance(authorization, ContactAuthorization):
        _refuse("admission contact authorization cannot authorize probes")
    if not isinstance(authorization, ProbeContactAuthorization):
        _refuse("probe execution requires a typed ProbeContactAuthorization")
    if authorization.consumed:
        _refuse("probe authorization already consumed (single-use)")
    return authorization


def build_probe_request_body(branch: str, model_id: str, probe_text: str,
                             decoding_contract: dict) -> dict:
    """Exact request body for one probe under the pinned decoding surface."""
    if branch == BRANCH_LOCAL:
        return {
            "model": model_id,
            "messages": [{"role": "user", "content": probe_text}],
            "temperature": PROBE_TEMPERATURE,
            "top_p": PROBE_TOP_P,
            "max_tokens": OUTPUT_CEILING,
            "stream": False,
        }
    if branch == BRANCH_API:
        body = {
            "model": model_id,
            "input": [{"role": "user", "content": probe_text}],
            "reasoning": {"effort": "none"},
            "temperature": PROBE_TEMPERATURE,
            "max_output_tokens": OUTPUT_CEILING,
            "store": False,
            "stream": False,
        }
        if API_TOP_P_INCLUDED:
            body["top_p"] = PROBE_TOP_P
        return body
    _refuse(f"unsupported branch {branch!r}")


def _ignorance_result(recovered: int, n: int,
                      max_rate: float) -> IgnoranceProbeResult:
    if n != PROBE_COUNT:
        _refuse("structural refusal: probe denominator must be exactly 15")
    return IgnoranceProbeResult(recovered=recovered, n=n,
                                max_recoverable_rate=max_rate)


def _ignorance_gate_verdict(recovered: int) -> tuple[bool, str]:
    """Probe-only gate label. Never ``engine_admitted`` (§6 admission is later)."""
    if recovered <= MAX_RECOVERABLE:
        return True, VERDICT_IGNORANCE_GATE_PASS
    return False, VERDICT_ENGINE_REFUSED


@dataclass
class _HttpLease:
    isolation_id: str
    used: bool = False


class ProductionProbeTransport:
    """HTTP transport for explicit `--contact` runs only."""

    def __init__(self, branch: str, model_id: str):
        self._branch = branch
        self._model_id = model_id
        self._counter = 0

    def fresh_lease(self, temperature: float) -> _HttpLease:
        self._counter += 1
        return _HttpLease(isolation_id=f"probe-{self._branch}-{self._counter}")

    def invoke(self, lease: _HttpLease, request_body: dict) -> str:
        if lease.used:
            raise ProbeContactError("session lease reused")
        lease.used = True
        if request_body.get("model") != self._model_id:
            raise ProbeContactError("request model_id does not match authority")
        if self._branch == BRANCH_LOCAL:
            url = f"{LOCAL_BASE}/chat/completions"
            api_key = None
        else:
            url = f"{API_BASE}/responses"
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise TransportRefusal("OPENAI_API_KEY required for api branch")
        result = _http_post(url, request_body, api_key=api_key)
        if result.get("error") or result.get("http_status") != 200:
            raise TransportRefusal(
                f"transport failure on {self._branch}: "
                f"status={result.get('http_status')} error={result.get('error')}")
        text = _extract_text(result.get("data"))
        if not text:
            raise TransportRefusal(
                f"transport failure on {self._branch}: missing text output")
        return text


def _write_sidecar_row(path: Path, row: dict, existing: list[dict]) -> None:
    existing.append(row)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")))
        fh.write("\n")


def _sidecar_row(probe_id: str, answer_text: str, recovered: bool,
                 isolation_id: str, authorization: ProbeContactAuthorization
                 ) -> dict:
    return {
        "probe_id": probe_id,
        "answer_sha256": hashlib.sha256(
            answer_text.encode("utf-8")).hexdigest(),
        "recovered": recovered,
        "temperature": PROBE_TEMPERATURE,
        "isolation_id": isolation_id,
        "branch": authorization.branch,
        "model_id": authorization.model_id,
        "decoding_contract_sha256": authorization.decoding_contract_sha256,
    }


def _verify_authorization_bindings(auth: ProbeContactAuthorization,
                                   root: Path = ROOT) -> None:
    """Recompute authority from current bytes; refuse forged/stale objects."""
    fresh = authorize_probe_contact(auth.branch, root)
    for field_name in (
            "pin_event_id", "manifest_file_sha256",
            "manifest_canonical_sha256", "packet_index_sha256",
            "probe_answer_key_sha256", "probe_fixture_ids",
            "probe_texts_sha256", "branch", "model_id",
            "decoding_contract_sha256", "probe_budget_tokens",
            "roster_total_budget_tokens", "max_recoverable_rate"):
        if getattr(auth, field_name) != getattr(fresh, field_name):
            _refuse("probe authorization bindings do not recompute from "
                    "current bytes (forged or stale authority)")


def _validate_answer_key_shape(answer_key: dict,
                               probe_ids: tuple[str, ...]) -> None:
    if set(answer_key) != set(probe_ids):
        _refuse("answer-key keys must exactly equal the pinned probe ids")
    for probe_id in probe_ids:
        entry = answer_key.get(probe_id)
        if not isinstance(entry, dict):
            _refuse(f"missing or malformed answer-key entry for {probe_id!r}")
        tokens = entry.get("must_contain")
        if not isinstance(tokens, list) or not tokens:
            _refuse(f"answer-key entry for {probe_id!r} lacks must_contain tokens")


def _verify_execution_bindings(auth: ProbeContactAuthorization,
                               probe_texts: dict[str, str],
                               answer_key: dict,
                               root: Path = ROOT) -> dict:
    """Execute-time identity checks before output, transport, or leases."""
    if set(probe_texts) != set(auth.probe_fixture_ids):
        _refuse("probe_texts keys must exactly equal the pinned probe ids")
    ordered_texts = {pid: probe_texts[pid] for pid in auth.probe_fixture_ids}
    if _probe_texts_sha256(ordered_texts, auth.probe_fixture_ids) != (
            auth.probe_texts_sha256):
        _refuse("probe_texts do not match the authorization-bound bytes")

    key_path = root / PROBE_ANSWER_KEY_REL
    raw = key_path.read_bytes()
    file_sha = hashlib.sha256(raw).hexdigest()
    if file_sha != auth.probe_answer_key_sha256:
        _refuse("canonical probe answer-key file sha256 does not match "
                "authorization")
    canonical = json.loads(raw.decode("utf-8"))
    _validate_answer_key_shape(canonical, auth.probe_fixture_ids)
    if canonical != answer_key:
        _refuse("caller answer_key is not byte-equivalent to the canonical "
                "oracle file")
    return canonical


def run_production_ignorance_probes(
        authorization: ProbeContactAuthorization,
        probe_texts: dict[str, str],
        answer_key: dict,
        output_dir: Path,
        transport: ProbeTransport | None = None,
        decoding_contract: dict | None = None,
        ) -> ProbeBranchResult:
    """Execute one authorized branch: fifteen probes, append-only sidecar only."""
    auth = _reject_non_authority(authorization)
    try:
        _verify_authorization_bindings(auth, ROOT)
        verified_answer_key = _verify_execution_bindings(
            auth, probe_texts, answer_key, ROOT)
        ordered_texts = {pid: probe_texts[pid]
                         for pid in auth.probe_fixture_ids}
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        sidecar_path = output_dir / SIDECAR_NAME
        result_path = output_dir / RESULT_NAME

        if sidecar_path.exists() and sidecar_path.stat().st_size:
            _refuse("conflicting existing probe sidecar: append-only surface "
                    "refuses overwrite")
        if result_path.exists():
            _refuse("conflicting existing probe branch result")

        if transport is None:
            transport = ProductionProbeTransport(auth.branch, auth.model_id)
        if decoding_contract is None:
            sibling = json.loads(
                (ROOT / c4b.SIBLING_REL).read_text(encoding="utf-8"))
            decoding_contract = sibling["branches"][auth.branch][
                "decoding_contract"]

        seen_leases: set[int] = set()
        seen_isolation: set[str] = set()
        sidecar: list[dict] = []
        recovered = 0
        refused: list[dict] = []
        status = "completed"
        probe_calls = 0

        for probe_id in auth.probe_fixture_ids:
            probe_text = ordered_texts[probe_id]
            body = build_probe_request_body(
                auth.branch, auth.model_id, probe_text, decoding_contract)
            lease = transport.fresh_lease(PROBE_TEMPERATURE)
            lease_id = id(lease)
            if lease_id in seen_leases:
                _refuse("transport returned a reused wrapper object")
            seen_leases.add(lease_id)
            if not lease.isolation_id:
                _refuse("session lease lacks isolation_id")
            if lease.isolation_id in seen_isolation:
                _refuse(f"isolation_id {lease.isolation_id!r} reused")
            seen_isolation.add(lease.isolation_id)
            if lease.used:
                _refuse("transport returned an already-used lease")

            probe_calls += 1
            try:
                answer_text = transport.invoke(lease, body)
            except TransportRefusal as exc:
                refused.append({"probe_id": probe_id, "reason": str(exc)})
                status = "branch_refused_transport"
                break

            if not isinstance(answer_text, str) or not answer_text:
                _refuse(f"malformed transport result for {probe_id!r}")

            verdict = score_probe_answer(probe_id, answer_text,
                                         verified_answer_key)
            if not isinstance(verdict, bool):
                _refuse("probe scorer must return strict bool")
            recovered += int(verdict)
            row = _sidecar_row(probe_id, answer_text, verdict,
                               lease.isolation_id, auth)
            _write_sidecar_row(sidecar_path, row, sidecar)
            del answer_text
    finally:
        auth.mark_consumed()

    sidecar_hash = _rows_sha256(sidecar) if sidecar else None
    if status == "branch_refused_transport":
        n_completed = len(sidecar)
        gate_pass = False
        ignorance_gate_verdict = VERDICT_NOT_ENGAGED
        result = ProbeBranchResult(
            branch=auth.branch,
            model_id=auth.model_id,
            recovered_count=sum(1 for r in sidecar if r["recovered"]),
            n=PROBE_COUNT,
            max_recoverable_rate=auth.max_recoverable_rate,
            gate_pass=gate_pass,
            ignorance_gate_verdict=ignorance_gate_verdict,
            probe_sidecar_sha256=sidecar_hash or "",
            decoding_contract_sha256=auth.decoding_contract_sha256,
            status=status,
            probe_calls=probe_calls,
            refused=refused,
        )
    else:
        if len(sidecar) != PROBE_COUNT:
            _refuse("structural refusal: incomplete probe sidecar")
        ignorance = _ignorance_result(recovered, PROBE_COUNT,
                                      auth.max_recoverable_rate)
        gate_pass, ignorance_gate_verdict = _ignorance_gate_verdict(recovered)
        if ignorance.failure():
            ignorance_gate_verdict = VERDICT_ENGINE_REFUSED
        result = ProbeBranchResult(
            branch=auth.branch,
            model_id=auth.model_id,
            recovered_count=recovered,
            n=PROBE_COUNT,
            max_recoverable_rate=auth.max_recoverable_rate,
            gate_pass=gate_pass,
            ignorance_gate_verdict=ignorance_gate_verdict,
            probe_sidecar_sha256=sidecar_hash or "",
            decoding_contract_sha256=auth.decoding_contract_sha256,
            status=status,
            probe_calls=probe_calls,
            refused=refused,
        )

    result_path.write_text(
        json.dumps({
            "branch": result.branch,
            "model_id": result.model_id,
            "recovered_count": result.recovered_count,
            "n": result.n,
            "max_recoverable_rate": result.max_recoverable_rate,
            "gate_pass": result.gate_pass,
            "ignorance_gate_verdict": result.ignorance_gate_verdict,
            "probe_sidecar_sha256": result.probe_sidecar_sha256,
            "decoding_contract_sha256": result.decoding_contract_sha256,
            "status": result.status,
            "probe_calls": result.probe_calls,
            "provider_cache": result.provider_cache,
            "refused": result.refused,
        }, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def _load_sidecar_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _derive_branch_ignorance(sidecar_rows: list[dict]) -> dict:
    if len(sidecar_rows) != PROBE_COUNT:
        _refuse(f"sidecar must contain exactly {PROBE_COUNT} rows; "
                f"got {len(sidecar_rows)}")
    recovered = sum(1 for row in sidecar_rows if row.get("recovered"))
    gate_pass, verdict = _ignorance_gate_verdict(recovered)
    if verdict == VERDICT_ENGINE_REFUSED:
        gate_pass = False
    return {
        "recovered_count": recovered,
        "n": PROBE_COUNT,
        "max_recoverable_rate": MAX_RECOVERABLE / PROBE_COUNT,
        "gate_pass": gate_pass,
        "ignorance_gate_verdict": verdict,
        "engine_admission_status": "engine_admission_pending",
        "probe_sidecar_canonical_sha256": _rows_sha256(sidecar_rows),
        "probe_sidecar_row_count": len(sidecar_rows),
    }


def _path_ref(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def build_ignorance_gate_correction(root: Path = ROOT,
                                    run_root: Path | None = None) -> dict:
    """Append-only semantic correction for completed P1 probe runs."""
    c4d.verify(root, full=True)
    if run_root is None:
        run_root = root / P1_RUN_ROOT_REL
    run_root = run_root.resolve()
    branch_artifacts = {}
    original_files: dict[str, dict] = {}
    for branch in ROSTER_BRANCH_ORDER:
        branch_dir = run_root / branch
        sidecar_path = branch_dir / SIDECAR_NAME
        result_path = branch_dir / RESULT_NAME
        for label, path in (("sidecar", sidecar_path), ("result", result_path)):
            if not path.is_file():
                _refuse(f"missing P1 {branch} {label} at {path}")
        sidecar_hash = sha256_path(sidecar_path)
        result_hash = sha256_path(result_path)
        original_files[f"{branch}_probe_sidecar.jsonl"] = {
            "path": _path_ref(sidecar_path, root),
            "sha256": sidecar_hash,
        }
        original_files[f"{branch}_probe_branch_result.json"] = {
            "path": _path_ref(result_path, root),
            "sha256": result_hash,
        }
        result_doc = json.loads(result_path.read_text(encoding="utf-8"))
        premature = result_doc.get("engine_verdict")
        if premature != "engine_admitted":
            _refuse(f"{branch} result lacks the preserved premature "
                    f"engine_admitted label; got {premature!r}")
        sidecar_rows = _load_sidecar_rows(sidecar_path)
        derived = _derive_branch_ignorance(sidecar_rows)
        branch_artifacts[branch] = {
            **derived,
            "model_id": result_doc.get("model_id"),
            "premature_derived_label": {
                "field": "engine_verdict",
                "value": premature,
                "disposition": "superseded_but_preserved",
                "note": ("probe-only path cannot establish §6 engine_admitted; "
                         "ignorance_gate_verdict is authoritative here"),
            },
            "original_probe_branch_result_sha256": result_hash,
            "original_probe_sidecar_file_sha256": sidecar_hash,
        }

    return {
        "schema_version": "efc_p1a_ignorance_gate_result_v1",
        "assignment": "P1a append-only semantic correction",
        "seat": "cursor/composer-2.5-capture",
        "active_pin_event_id": c4d.SUPERSEDING_EVENT_ID,
        "original_run_root": _path_ref(run_root, root),
        "original_files": original_files,
        "branches": branch_artifacts,
        "total_real_calls": PROBE_COUNT * len(ROSTER_BRANCH_ORDER),
        "additional_real_calls": 0,
        "disclosure": {
            "engines_contacted": 0,
            "listing_calls": 0,
            "network_calls": 0,
            "probes_run": 0,
            "real_inference_calls": 0,
            "plaintext_answers_inspected": 0,
        },
        "authorizes_calibration_contact": False,
        "authorizes_probe_rerun": False,
        "note": ("Derived from preserved P1 sidecars and branch results only; "
                 "original four run files remain byte-identical testimony."),
    }


def write_ignorance_gate_correction(root: Path = ROOT,
                                  run_root: Path | None = None) -> dict:
    payload = build_ignorance_gate_correction(root, run_root)
    if run_root is None:
        run_root = root / P1_RUN_ROOT_REL
    out_path = run_root / IGNORANCE_GATE_RESULT_NAME
    if out_path.exists():
        existing = json.loads(out_path.read_text(encoding="utf-8"))
        if existing != payload:
            _refuse("ignorance_gate_result.json already exists with "
                    "different bytes; refuse to overwrite")
        payload["result_path"] = _path_ref(out_path, root)
        payload["result_sha256"] = sha256_path(out_path)
        return payload
    out_path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8")
    payload["result_path"] = _path_ref(out_path, root)
    payload["result_sha256"] = sha256_path(out_path)
    return payload


def p1a_correction_report_payload(root: Path = ROOT) -> dict:
    module_path = Path(__file__)
    test_path = root / "tests/test_efc_probe_contact.py"
    p0_report_path = root / REPORT_REL
    return {
        "schema_version": "efc_p1a_correction_report_v1",
        "assignment": "P1a ignorance-gate verdict label repair",
        "seat": "cursor/composer-2.5-capture",
        "active_pin_event_id": c4d.SUPERSEDING_EVENT_ID,
        "module_path": str(module_path.relative_to(root)),
        "module_sha256": sha256_path(module_path),
        "test_path": str(test_path.relative_to(root)),
        "test_sha256": sha256_path(test_path),
        "prior_p0a_report_path": REPORT_REL,
        "prior_p0a_report_sha256": sha256_path(p0_report_path),
        "prior_p0a_report_preserved": True,
        "probe_only_verdicts": list(PROBE_ONLY_VERDICTS),
        "forbidden_probe_verdict": "engine_admitted",
        "disclosure": {
            "engines_contacted": 0,
            "listing_calls": 0,
            "network_calls": 0,
            "probes_run": 0,
            "real_inference_calls": 0,
        },
    }


def write_p1a_correction_report(root: Path = ROOT) -> dict:
    payload = p1a_correction_report_payload(root)
    path = root / P1A_REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")
    payload["report_path"] = P1A_REPORT_REL
    payload["report_sha256"] = sha256_path(path)
    return payload


def implementation_report_payload(root: Path = ROOT) -> dict:
    module_path = Path(__file__)
    test_path = root / "tests/test_efc_probe_contact.py"
    return {
        "schema_version": "efc_p0_probe_contact_report_v1",
        "assignment": "P0a execute-time identity repair",
        "seat": "cursor/composer-2.5-capture",
        "active_pin_event_id": c4d.SUPERSEDING_EVENT_ID,
        "module_path": str(module_path.relative_to(root)),
        "module_sha256": sha256_path(module_path),
        "test_path": str(test_path.relative_to(root)),
        "test_sha256": sha256_path(test_path),
        "disclosure": {
            "engines_contacted": 0,
            "listing_calls": 0,
            "network_calls": 0,
            "probes_run": 0,
            "real_inference_calls": 0,
        },
        "future_contact_commands": [
            {
                "command": ("python3 -m harness.efc_probe_contact --contact "
                              "--branch local --output-dir <dir>"),
                "max_real_calls": 15,
                "branch": BRANCH_LOCAL,
                "model_id": BRANCH_MODEL[BRANCH_LOCAL],
            },
            {
                "command": ("python3 -m harness.efc_probe_contact --contact "
                              "--branch api --output-dir <dir>"),
                "max_real_calls": 15,
                "branch": BRANCH_API,
                "model_id": BRANCH_MODEL[BRANCH_API],
            },
        ],
        "roster_branch_order": list(ROSTER_BRANCH_ORDER),
        "provider_cache": PROVIDER_CACHE_STATUS,
    }


def write_implementation_report(root: Path = ROOT) -> dict:
    payload = implementation_report_payload(root)
    path = root / REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")
    payload["report_path"] = REPORT_REL
    payload["report_sha256"] = sha256_path(path)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness.efc_probe_contact",
        description="Production ignorance-probe surface (offline by default)")
    parser.add_argument("--write-report", action="store_true",
                        help="write the pre-contact implementation report")
    parser.add_argument("--write-p1a-correction", action="store_true",
                        help=("write P1a ignorance-gate correction artifacts "
                              "(offline; no contact)"))
    parser.add_argument("--contact", action="store_true",
                        help="run real probes for one authorized branch")
    parser.add_argument("--branch", choices=[BRANCH_LOCAL, BRANCH_API])
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    if args.write_report and not args.contact:
        try:
            result = write_implementation_report()
        except ProbeContactError as exc:
            print(json.dumps({"refused": str(exc)}, indent=1))
            return 1
        print(json.dumps(result, indent=1))
        return 0

    if args.write_p1a_correction and not args.contact:
        try:
            correction = write_ignorance_gate_correction()
            report = write_p1a_correction_report()
        except ProbeContactError as exc:
            print(json.dumps({"refused": str(exc)}, indent=1))
            return 1
        print(json.dumps({
            "ignorance_gate_result": correction,
            "p1a_correction_report": report,
        }, indent=1))
        return 0

    if args.contact:
        if not args.branch or not args.output_dir:
            parser.print_usage(sys.stderr)
            print("refused: --contact requires --branch and --output-dir",
                  file=sys.stderr)
            return 2
        try:
            loaded = _load_probe_bindings(ROOT)
            auth = authorize_probe_contact(args.branch, ROOT)
            result = run_production_ignorance_probes(
                auth,
                loaded["probe_texts"],
                loaded["answer_key"],
                args.output_dir,
            )
        except (ProbeContactError, RunnerContractError, TransportRefusal) as exc:
            print(json.dumps({"refused": str(exc)}, indent=1))
            return 1
        print(json.dumps({
            "branch": result.branch,
            "model_id": result.model_id,
            "recovered_count": result.recovered_count,
            "n": result.n,
            "gate_pass": result.gate_pass,
            "ignorance_gate_verdict": result.ignorance_gate_verdict,
            "probe_sidecar_sha256": result.probe_sidecar_sha256,
            "status": result.status,
            "probe_calls": result.probe_calls,
        }, indent=1))
        return 0

    parser.print_usage(sys.stderr)
    print("refused: an explicit mode (--write-report, --write-p1a-correction, "
          "or --contact) is required",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
