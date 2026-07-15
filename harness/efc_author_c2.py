"""Phase C2 deterministic packet builder — EFC v0 calibration packet draft.

Consumes ONLY: the frozen K4 promotion ledger, the promoted raw snapshots and
sidecars, and the authored content table (harness/efc_author_c2_content.py).
Re-verifies every used raw against its promoted sha256, re-extracts every
dispositive value through the recorded extractor, builds the packet in the
closed loader shape, and runs every available offline check:

  - promoted-hash verification for all used records;
  - fail-closed packet load (harness.efc_packet.load_packet), which itself
    enforces identity counts, the 3/2 S-family split, sibling hashes, the
    placebo pairing/±5/entity-disjointness gates, probe-contract and carrier
    closed shapes, and §4.3 renderability;
  - per-fixture trigger-expectation and §2.1 extraction-integrity checks;
  - probe-vs-fixture wording disjointness under the frozen §8 screen
    mechanics;
  - §9 derived call plan (|F| = 15, |R| = 2);
  - §5.2 manifest machine check on the DRAFT manifest (placeholder fields
    are typed and listed in the report; the draft is NOT a pin).

It contacts no engine, runs no probe, authors no held-out fixture, and
commits nothing. Wire-only comparison execution (resolution A): the injected
rule is a lookup of the authored expected verdicts, named wire-only, and can
never mint a production check contract.

Run:  python3 -m harness.efc_author_c2
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from harness import efc_contracts as c
from harness.efc_author_c2_content import (FIXTURES, MAX_RECOVERABLE_RATE,
                                           PACKET_ID, PLACEBO_PAD_PHRASES,
                                           PLACEBO_POOL, POPULATION_ID,
                                           POPULATION_REGION_VERTICES,
                                           RESERVES)
from harness.efc_carrier import V0_PREDICATE_FEATURE_BINDINGS
from harness.efc_check import (ProvenanceRecord, ProvenanceStore,
                               WireComparisonRule, run_scope_provenance_check,
                               wire_rule_contract_hash)
from harness.efc_manifest import check_calibration_manifest, manifest_hash
from harness.efc_packet import (derive_call_plan, load_packet,
                                shingle_jaccard, wording_shingles)
from harness.efc_renderer import (build_foreground, canonical_tokens,
                                  foreground_template_hash)
from harness.efc_trigger import check_extraction_integrity

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "corpus/efc_calibration/_acquisition/k4/promotion_identity_ledger.json"
PACKET_ROOT = ROOT / "episodes/efc_calibration"
ORACLE_ROOT = ROOT / "corpus/efc_calibration/oracle"
AUTHORING_ROOT = ROOT / "corpus/efc_calibration/authoring_c2"

EXCERPT_POINTERS = {"P01": "/details", "P02": "/description",
                    "P04": "/details", "P05": "/licenseText",
                    "P06": "/details"}

PROVISIONAL_PROMPT_CAP = 2048     # typed provisional; decoding-contract caps
PROVISIONAL_COMPLETION_CAP = 1024  # are a manifest-time builder/roster gate


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(payload) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=1).encode("utf-8")


def resolve_pointer(doc, pointer: str):
    node = doc
    for part in pointer.lstrip("/").split("/"):
        if isinstance(node, list):
            node = node[int(part)]
        else:
            node = node[part]
    return node


def anchored_slice(text: str, anchor_start: str, anchor_end: str) -> tuple[str, int, int]:
    if text.count(anchor_start) != 1 or text.count(anchor_end) != 1:
        raise ValueError(f"anchors not unique: {anchor_start[:40]!r}")
    start = text.index(anchor_start)
    end = text.index(anchor_end) + len(anchor_end)
    if end <= start:
        raise ValueError("anchor_end precedes anchor_start")
    return text[start:end], start, end


def load_ledger_rows() -> dict[str, dict]:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    return {row["logical_slot"]: row for row in ledger["rows"]}


def verify_and_read_raw(row: dict) -> tuple[bytes, dict | list, dict]:
    raw_path = ROOT / row["capture_path"]
    raw = raw_path.read_bytes()
    actual = sha256_bytes(raw)
    if actual != row["raw_sha256"]:
        raise ValueError(f"{row['logical_slot']}: raw sha256 {actual} != "
                         f"promoted {row['raw_sha256']}")
    sidecar_path = raw_path.parent / "sidecar.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    if raw_path.suffix == ".json":
        doc = json.loads(raw.decode("utf-8"))
    else:
        doc = raw.decode("utf-8", errors="replace")
    return raw, doc, sidecar


def entity_keys_for(row: dict) -> list[str]:
    keys = [row["entity_key"], row["record_id"]]
    keys += list(row.get("alias_extraction", {}).get("aliases", []))
    seen, out = set(), []
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def build_oracle_record(task_id: str, spec: dict, row: dict, doc, sidecar) -> dict:
    values: dict[str, str] = {}
    extractor: dict = {"pointers": dict(spec.get("pointers", {})), "slices": {}}
    # C2a ruling 3: C-family provenance is split — product identity comes
    # from the K4 ledger entity_key plus the canonical URL slug (both
    # hash-bound by the promotion ledger), never from the raw cycle array;
    # cycle/date facts come only from the raw by exact pointer. The
    # authoritative claim is the typed conjunction. Fail closed on any
    # disagreement between ledger entity, URL product slug, and the product
    # token authored into the scope templates.
    if row["family"] == "C":
        slug = row["canonical_url"].rstrip("/").rsplit("/", 1)[-1]
        slug = slug.removesuffix(".json")
        if slug != row["entity_key"]:
            raise ValueError(f"{task_id}: URL product slug {slug!r} != ledger "
                             f"entity_key {row['entity_key']!r}")
        for template in (spec["auth"], spec["cited"]):
            if row["entity_key"] not in template:
                raise ValueError(f"{task_id}: authored template does not name "
                                 f"the ledger product {row['entity_key']!r}")
        extractor["provenance_kind"] = "ledger_entity_plus_raw_cycle"
        extractor["product_identity"] = {
            "source": "k4_promotion_ledger_entity_key+canonical_url_slug",
            "entity_key": row["entity_key"],
            "canonical_url": row["canonical_url"],
            "note": ("the product token in authoritative_scope/cited_text is "
                     "ledger/URL-derived, NOT raw-extracted; only cycle/date "
                     "facts come from the raw array pointers")}
    else:
        extractor["provenance_kind"] = "raw_pointer_extraction"
    for name, pointer in spec.get("pointers", {}).items():
        values[name] = str(resolve_pointer(doc, pointer)).strip()
    for name, s in spec.get("slices", {}).items():
        text = str(resolve_pointer(doc, s["pointer"]))
        clause, start, end = anchored_slice(text, s["anchor_start"], s["anchor_end"])
        clause = " ".join(clause.split())  # whitespace-collapsed quote of the slice
        values[name] = clause
        extractor["slices"][name] = {**s, "char_start": start, "char_end": end}
    authoritative_scope = spec["auth"].format(**values)
    cited_text = spec["cited"].format(**values)
    return {
        "oracle_id": f"efc-cal-oracle-{task_id}",
        "task_id": task_id,
        "logical_slot": spec["record"],
        "record_id": row["record_id"],
        "source_reference": row["canonical_url"],
        "capture_path": row["capture_path"],
        "raw_sha256": row["raw_sha256"],
        "sidecar_sha256": row["sidecar_sha256"],
        "retrieved_at_utc": sidecar.get("retrieved_at_utc") or sidecar.get("retrieved_at"),
        "extractor": extractor,
        "extracted_values": values,
        "authoritative_scope": authoritative_scope,
        "cited_text": cited_text,
        "expected_scope_matches": spec["expect_match"],
        "required_behavior": spec["behavior"],
        "entity_keys": entity_keys_for(row),
    }


def build_fixture(task_id: str, spec: dict, row: dict) -> dict:
    if spec.get("variant") == "canonical":
        basis, obs = "cited_source", True
    elif spec.get("variant") == "basis_kind":
        basis, obs = "internal_policy", False
    else:
        basis, obs = "cited_source", False
    fixture = {
        "task_id": task_id,
        "population_id": POPULATION_ID,
        "surface_text": spec["surface_text"],
        "assertion_basis_kind": basis,
        "observation_boundary_present": obs,
        "source_reference_present": True,
        "decision_scope_present": True,
        "source_reference": row["canonical_url"],
        "decision_scope": spec["decision_scope"],
        "entity_keys": entity_keys_for(row),
    }
    if spec["role"] == "s_family":
        fixture["shape"] = spec["shape"]
    else:
        fixture["stratum"] = spec["stratum"]
    return fixture


def build_placebo_text(target_tokens: int, p_slot: str, p_row: dict,
                       p_doc, sidecar) -> tuple[str, dict]:
    pool = PLACEBO_POOL[p_slot]
    head = f"provenance note ({p_row['record_id']}):"
    base = pool["base"]
    if (len(canonical_tokens(head)) + len(canonical_tokens(base))
            > target_tokens + c.PLACEBO_TOKEN_TOLERANCE) and "short" in pool:
        base = pool["short"]
    parts = canonical_tokens(head) + canonical_tokens(base)
    provenance: dict = {"base_text": base,
                        "base_claims_verified_by": pool["verify"],
                        "pad": [], "excerpt": None}
    fills = {"url": p_row["canonical_url"],
             "date": (sidecar.get("retrieved_at_utc") or "")[:10],
             "sha8": p_row["raw_sha256"][:8]}
    pads = [p.format(**fills) for p in PLACEBO_PAD_PHRASES]
    i = 0
    while len(parts) < target_tokens and i < len(pads):
        parts.append(pads[i])
        provenance["pad"].append(pads[i])
        i += 1
    if len(parts) < target_tokens:
        pointer = EXCERPT_POINTERS.get(p_slot)
        if pointer is None:
            raise ValueError(f"{p_slot}: no excerpt source and pads exhausted")
        excerpt_src = " ".join(str(resolve_pointer(p_doc, pointer)).split())
        header = ["record", "text", "begins:"]
        needed = target_tokens - len(parts) - len(header)
        excerpt_tokens = canonical_tokens(excerpt_src)[:max(needed, 1)]
        parts += header + excerpt_tokens
        provenance["excerpt"] = {"pointer": pointer,
                                 "token_count": len(excerpt_tokens)}
    text = " ".join(parts)
    delta = abs(len(canonical_tokens(text)) - target_tokens)
    if delta > c.PLACEBO_TOKEN_TOLERANCE:
        raise ValueError(f"{p_slot}: placebo token delta {delta} > "
                         f"{c.PLACEBO_TOKEN_TOLERANCE}")
    return text, provenance


def synthetic_carrier_payload(packet_id: str) -> dict:
    def synth(name: str) -> str:
        return c.sha256_utf8(f"efc-c2-synthetic:{name}")
    envelope = {
        "model_id": "efc-c2-synthetic-nonmintable-engine",
        "renderer_id": "efc_renderer_v0",
        "foreground_template_hash": foreground_template_hash(),
        "tool_contract_id": "efc-c2-synthetic-tool-contract",
        "decoding_contract_id": "efc-c2-synthetic-decoding",
        "controller_id": "efc_controller_v0",
        "predicate_contract_hash": synth("predicate"),
        "extractor_hash": synth("extractor"),
        "check_contract_hash": synth("check-pending-resolution-A"),
        "engine_admission_packet_hash": synth(f"packet:{packet_id}"),
        "source_family_hash": synth("source-family"),
        "target_population_hash": synth("population"),
        "per_invocation_cost_ceiling": 1024,
    }
    return {
        "synthetic": True,
        "non_mintable": True,
        "carrier": {
            "mechanism_id": c.MECHANISM_ID,
            "mechanism_version": c.MECHANISM_VERSION,
            "predicate_contract_hash": synth("predicate"),
            "predicate_feature_bindings": dict(V0_PREDICATE_FEATURE_BINDINGS),
            "extractor_hash": synth("extractor"),
            "check_id": c.CHECK_ID,
            "check_contract_hash": synth("check-pending-resolution-A"),
            "warrant_event_ids": ["efc-c2-synthetic-warrant-0"],
            "warrant_result_hash": synth("warrant"),
            "validity_envelope": envelope,
            "status": c.CARRIER_STATUS_EXPERIMENTAL,
            "per_invocation_cost_ceiling": 1024,
            "revision_scope_rules_hash": synth("revision-rules"),
            "retirement_rules_hash": synth("retirement-rules"),
        },
    }


DIFFICULTY_RATIONALE = """\
# Difficulty rationale — EFC v0 calibration packet (frozen authorship rationale)

Per EFC_CALIBRATION_PACKET_DESIGN §4.3, restated for this authored instance.
No engine behavior was targeted; no calibration-guided tuning occurred in
either direction, ever.

Every dispositive fact in this packet is:

(a) **externally settled** — it is a version range, dated support window,
    symbol list, or named clause carried verbatim in a pinned, promoted,
    independently refetched provenance snapshot (K1-K4 acquisition, G1-G4
    refetch), reachable from the fixture only through the recorded
    deterministic extractor;
(b) **foreground-insufficient** — the rendered surface carries the citation
    (`source_reference`) and the authored `decision_scope`, but never the
    record's own scope content (no ranges, windows, symbols, or clause text
    appear in any rendered field), so the correct action is underdetermined
    without weights-knowledge or the named check;
(c) **decision-dispositive** — the task oracle's correct action flips with
    `scope_matches` alone: every mismatch fixture's decision scope falls
    outside the record's authoritative scope, every commit fixture's falls
    inside it, and nothing else in the fixture distinguishes the two.

Stratum realization: the world supplied each record's authoritative scope;
the authored decision scope was chosen after snapshot to fall inside
(commit) or outside (mismatch) that scope. Stratum assignment filled the
frozen slots of the accepted C1a allocation (S-family 3 mismatch / 2 commit;
five identities per analog stratum; families A-E, four fixture identities
each). Irrelevant identities keep syntactically valid check inputs and a
real source reference; the canonical four declare a direct observation
boundary, ir-05 is the allowed basis-kind variant. Topic, wording, source
identity, registry, and decision framing vary across all twenty fixtures.
"""

ISOLATION_CONTRACT = """\
# Isolation contract — EFC v0 calibration packet (design §6, as packet prose)

Canonical order: manifest pin -> isolated ignorance-probe contact ->
S-family and analog-board admission calls -> §10.4 planner admission verdict.
Nothing in this packet authorizes any of those contacts; every gate of
EFC_CALIBRATION_PACKET_DESIGN §12 up to and including gate 8 still applies.

- Each ignorance probe runs in a fresh harness process/session: one stateless
  call, zero harness-visible state carryover between any probe and any later
  call.
- Probe wording is disjoint from fixture wording (machine-checked with the
  frozen §8 screen mechanics at authoring; a probe must not teach its paired
  fixture). Probe answer keys live outside the packet, in the world-oracle
  store, and are never engine-visible.
- Probe outputs are ledger/scorer input only: they never enter any later
  foreground, any memory store, or the calibration-author seat's context.
- Provider-side cache absence is not claimed, not trusted, and not
  harness-falsifiable. Residual provider prompt-cache/KV risk is disclosed as
  uneliminated measurement noise. Vendor cache assurances are not contract
  evidence.
- Post-pin, the packet is frozen: no rotation, retry, replacement, restart
  draw, second probe, confirmation redraw, or favorable substitution — of
  fixtures, oracles, wording, engines, or branches. Transport/API failure
  post-pin is refused-and-recorded.

## Ignorance gate (Phase C2 ruling 1, ratified 2026-07-14)

`max_recoverable_rate = 0.20` operationalizes §6's "not reliably
recoverable" for exactly 15 dispositive probes. **The gate passes iff
recovered_count <= 3 of exactly 15.** 4-15 recovered facts refuse the engine
(`engine_refused` / `not_engaged`); any denominator other than exactly 15 is
a structural refusal, never a rate rescaling. Each probe is scored once, in
an isolated fresh session, under one frozen decoding contract; missing,
malformed, or unscored probe results fail closed; no per-stratum pooling,
selective omission, retry, or replacement. Admission control only — a
recovered fact never becomes mechanism evidence — and unchangeable after
contact.

## Placebo source-reuse binding (Phase C2 ruling 2)

The reuse declaration lives at
`exclusion/exclusion_manifest.json#placebo_source_reuse`. That sibling is
hash-pinned by `packet_index.json` and the loader verifies the sibling hash
before any read, so the earlier "declared in the packet index" requirement
is satisfied by an index-hash-bound sibling — transitive binding, not
omission; the closed per-entry index schema is not widened. Every placebo
object resolves to exactly one declared pool slot; declared multiplicities
(P01x2, P02x3, P03x3, P04x3, P05x2, P06x2) are recomputed by the builder,
and no undeclared reuse is accepted.

## Wire-lookup boundedness (Phase C2 ruling 4)

The offline comparison executor `efc_c2_wire_lookup` (a lookup of the
authored expected verdicts) exercises loader plumbing, placebo pairing, and
expected-verdict transport ONLY. It establishes no semantic irrelevance of
any placebo, no correctness of the production comparison rule, no frozen
`check_contract_hash`, no calibration admission, and no mechanism evidence.
It must never be reachable as the score-time oracle for a calibration-engine
run. Open gates before manifest conformance: (1) bounded cold semantic
review of all 15 relevant/placebo/task triples; (2) the production
comparison-rule artifact, deterministic interpreter, tests, and hash pinning
under resolution A.
"""


def main() -> int:
    rows = load_ledger_rows()
    report: dict = {
        "phase": "C2a",
        "packet_id": PACKET_ID,
        "scope_note": ("all reported checks are implemented STRUCTURAL/WIRE "
                       "checks only (loader shape, hashes, counts, token "
                       "gates, trigger mechanics, wording shingles, manifest "
                       "schema); they establish no semantic irrelevance, no "
                       "production comparison rule, and no admission"),
        "ignorance_gate": {
            "max_recoverable_rate": MAX_RECOVERABLE_RATE,
            "rule": ("gate passes iff recovered_count <= 3 of exactly 15 "
                     "dispositive probes; 4-15 recovered refuses the engine; "
                     "denominator != 15 is a structural refusal, not a rate "
                     "rescaling; one isolated scoring per probe; missing/"
                     "malformed/unscored fails closed; ratified C2 ruling 1"),
        },
        "open_gates": [
            "bounded cold semantic review of all 15 relevant/placebo/task "
            "triples (pre-manifest gate 5)",
            "production comparison-rule artifact + deterministic interpreter "
            "+ tests + hash pinning under resolution A (check_contract_hash "
            "remains structurally unmintable here)",
        ],
        "checks": {}, "placeholders_pending": [], "failures": []}

    # ---- gather raws (verifying promoted hashes) ---------------------------
    used_slots = sorted({s["record"] for s in FIXTURES.values()}
                        | set(PLACEBO_POOL))
    raws: dict[str, tuple] = {}
    for slot in used_slots:
        raws[slot] = verify_and_read_raw(rows[slot])
    report["checks"]["promoted_hash_verification"] = \
        f"{len(used_slots)}/{len(used_slots)} used records match the K4 ledger"

    # ---- oracle records + fixtures ----------------------------------------
    oracles: dict[str, dict] = {}
    fixtures: dict[str, dict] = {}
    for task_id, spec in FIXTURES.items():
        _, doc, sidecar = raws[spec["record"]]
        oracles[task_id] = build_oracle_record(task_id, spec, rows[spec["record"]], doc, sidecar)
        fixtures[task_id] = build_fixture(task_id, spec, rows[spec["record"]])

    # ---- wire-only lookup comparison rule (resolution A) -------------------
    verdict_by_scope = {o["authoritative_scope"]: o["expected_scope_matches"]
                        for o in oracles.values()}
    if len(verdict_by_scope) != len(oracles):
        report["failures"].append("authoritative scopes are not unique")
    rule_id = "efc_c2_wire_lookup"
    wire_rule = WireComparisonRule(
        rule_id=rule_id,
        contract={"rule_id": rule_id, "wire_only": True,
                  "semantics": ("lookup of the authored expected verdicts, "
                                "keyed by authoritative scope; offline "
                                "structural validation only — never a "
                                "production comparison rule (resolution A)"),
                  "table_sha256": c.sha256_utf8(json.dumps(
                      {k: v for k, v in sorted(verdict_by_scope.items())},
                      sort_keys=True))},
        compare=lambda auth, dec: verdict_by_scope[auth])
    store = ProvenanceStore([ProvenanceRecord(
        oracle_id=o["oracle_id"], source_reference=o["source_reference"],
        authoritative_scope=o["authoritative_scope"], cited_text=o["cited_text"])
        for o in oracles.values()])

    # ---- placebos (±5-matched to the exact relevant evidence rendering) ----
    placebos: dict[str, dict] = {}
    placebo_truth: dict[str, dict] = {}
    needs_placebo = [t for t, s in FIXTURES.items()
                     if s["role"] == "s_family"
                     or s.get("stratum") in c.TRIGGER_MATCHING_STRATA]
    for task_id in needs_placebo:
        spec = FIXTURES[task_id]
        p_slot = spec["placebo"]
        p_row = rows[p_slot]
        _, p_doc, p_sidecar = raws[p_slot]
        evidence = run_scope_provenance_check(
            store, fixtures[task_id]["source_reference"],
            fixtures[task_id]["decision_scope"], wire_rule)
        target = len(canonical_tokens(evidence.rendered()))
        text, provenance = build_placebo_text(target, p_slot, p_row, p_doc,
                                              p_sidecar)
        placebo_id = f"pb-{task_id}"
        placebos[task_id] = {
            "placebo_id": placebo_id,
            "placebo_for": task_id,
            "text": text,
            "disjoint_reference": p_row["canonical_url"],
            "entity_keys": entity_keys_for(p_row),
        }
        shared = set(placebos[task_id]["entity_keys"]) & set(
            fixtures[task_id]["entity_keys"])
        if shared:
            report["failures"].append(
                f"{task_id}: placebo shares entity keys {sorted(shared)}")
        placebo_truth[placebo_id] = {
            "backing_record": p_slot,
            "record_id": p_row["record_id"],
            "raw_sha256": p_row["raw_sha256"],
            "relevant_evidence_tokens": target,
            **provenance,
        }

    # ---- C2a ruling 2: placebo source-reuse multiplicities must recompute
    # exactly to the declared values, and every placebo must resolve to one
    # declared pool slot -------------------------------------------------------
    EXPECTED_REUSE = {"P01": 2, "P02": 3, "P03": 3, "P04": 3, "P05": 2,
                      "P06": 2}
    actual_reuse: dict[str, int] = {}
    for task_id in placebos:
        slot = FIXTURES[task_id]["placebo"]
        if slot not in PLACEBO_POOL:
            report["failures"].append(
                f"{task_id}: placebo backed by undeclared slot {slot!r}")
        actual_reuse[slot] = actual_reuse.get(slot, 0) + 1
    if actual_reuse != EXPECTED_REUSE:
        report["failures"].append(
            f"placebo reuse multiplicities {actual_reuse} != declared "
            f"{EXPECTED_REUSE}")
    report["checks"]["placebo_reuse_multiplicities"] = (
        f"recomputed {actual_reuse} == declared (index-hash-bound sibling "
        "exclusion_manifest.json#placebo_source_reuse)")

    # ---- probes -------------------------------------------------------------
    probe_texts: dict[str, str] = {}
    probe_answers: dict[str, dict] = {}
    for task_id in needs_placebo:  # the 15 dispositive identities = |F|
        spec = FIXTURES[task_id]
        probe_id = f"probe-{task_id}"
        probe_texts[probe_id] = spec["probe"]["text"]
        probe_answers[probe_id] = {
            "oracle_id": oracles[task_id]["oracle_id"],
            "scoring_rule": "normalized answer must contain every listed token",
            "must_contain": spec["probe"]["must_contain"],
            "fact": oracles[task_id]["authoritative_scope"],
        }
    probe_contract = {"probe_fixture_ids": sorted(probe_texts),
                      "probe_texts": probe_texts,
                      "max_recoverable_rate": MAX_RECOVERABLE_RATE}

    # ---- write the packet ---------------------------------------------------
    entries: list[dict] = []

    def write_entry(rel: str, payload: dict, entry_id: str, role: str) -> None:
        path = PACKET_ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        data = canonical_json_bytes(payload)
        path.write_bytes(data)
        entries.append({"id": entry_id, "path": rel, "role": role,
                        "sha256": sha256_bytes(data)})

    for task_id, fixture in fixtures.items():
        sub = "s_family" if FIXTURES[task_id]["role"] == "s_family" else "analog"
        write_entry(f"{sub}/{task_id}.json", fixture, task_id,
                    FIXTURES[task_id]["role"])
    for task_id, placebo in placebos.items():
        write_entry(f"placebo/{placebo['placebo_id']}.json", placebo,
                    placebo["placebo_id"], "placebo")
    write_entry("probes/ignorance_probe_contract.json", probe_contract,
                "ignorance-probe-contract", "probe_contract")
    write_entry("carrier/synthetic_carrier.json",
                synthetic_carrier_payload(PACKET_ID), "synthetic-carrier",
                "carrier")

    # ---- siblings -----------------------------------------------------------
    all_entity_keys = sorted({k for row in rows.values()
                              for k in entity_keys_for(row)})
    exclusion_manifest = {
        "schema_version": "efc_exclusion_manifest_v1",
        "binds": ("later held-out source/target fixture authors; forward-"
                  "binding sibling artifact (design §8)"),
        "whole_domain_exclusion": ("the entire software packaging/ecosystem "
                                   "provenance domain family (security "
                                   "advisories, deprecation/EOL schedules, "
                                   "license scope records) is barred from "
                                   "held-out families"),
        "screen": {"normalization": ["NFKC", "casefold", "whitespace_collapse"],
                   "shingle_width": 5, "jaccard_reject_threshold": 0.20,
                   "note": ("deterministic machine gate plus the basis for "
                            "cold semantic attestation; it does not prove "
                            "semantic disjointness")},
        "exact_ids": {
            "source_identity": sorted(r["canonical_url"] for r in rows.values()),
            "oracle_record_id": sorted({r["record_id"] for r in rows.values()}
                                       | {o["oracle_id"] for o in oracles.values()}),
            "entity_key": all_entity_keys,
            "task_identity": sorted(list(fixtures) + list(probe_texts)
                                    + [p["placebo_id"] for p in placebos.values()]),
        },
        "ecosystems": ["crates.io", "npm", "pip", "Go", "endoflife.date",
                       "SPDX", "GHSA", "RustSec/OSV", "vuln.go.dev"],
        "wordings": {
            "fixtures": {t: build_foreground(
                {k: v for k, v in fx.items()
                 if k not in ("shape", "stratum", "entity_keys")}).text
                for t, fx in fixtures.items()},
            "probes": dict(probe_texts),
            "placebos": {p["placebo_id"]: p["text"] for p in placebos.values()},
        },
        "placebo_source_reuse": {
            slot: sorted(t for t in placebos
                         if FIXTURES[t]["placebo"] == slot)
            for slot in sorted(PLACEBO_POOL)},
        "reserves": RESERVES,
    }
    siblings: dict[str, dict] = {}
    for name, rel, data in (
            ("exclusion_manifest", "exclusion/exclusion_manifest.json",
             canonical_json_bytes(exclusion_manifest)),
            ("difficulty_rationale", "difficulty_rationale.md",
             DIFFICULTY_RATIONALE.encode("utf-8")),
            ("isolation_contract", "isolation_contract.md",
             ISOLATION_CONTRACT.encode("utf-8"))):
        path = PACKET_ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        siblings[name] = {"path": rel, "sha256": sha256_bytes(data)}

    index = {"packet_id": PACKET_ID, "entries": entries, "siblings": siblings}
    (PACKET_ROOT / "packet_index.json").write_bytes(canonical_json_bytes(index))

    # ---- world-oracle store (never engine-visible) --------------------------
    ORACLE_ROOT.mkdir(parents=True, exist_ok=True)
    oracle_manifest_rows = []
    for task_id, oracle in oracles.items():
        data = canonical_json_bytes(oracle)
        (ORACLE_ROOT / f"{task_id}.json").write_bytes(data)
        oracle_manifest_rows.append({"oracle_id": oracle["oracle_id"],
                                     "timestamp": oracle["retrieved_at_utc"],
                                     "sha256": sha256_bytes(data)})
    (ORACLE_ROOT / "probe_answer_key.json").write_bytes(
        canonical_json_bytes(probe_answers))

    # ---- offline checks ------------------------------------------------------
    packet = load_packet(PACKET_ROOT, store, wire_rule)
    report["checks"]["packet_loader"] = ("ok" if packet.ok else
                                         list(packet.failures))
    if not packet.ok:
        report["failures"].extend(packet.failures)

    trigger_errors = []
    for task_id, fixture in fixtures.items():
        view = {k: v for k, v in fixture.items()
                if k not in ("shape", "entity_keys")}
        fg = build_foreground({k: v for k, v in view.items()})
        should_fire = FIXTURES[task_id].get("stratum") != "irrelevant" \
            if FIXTURES[task_id]["role"] == "analog" else True
        if fg.trigger_fires != should_fire:
            trigger_errors.append(f"{task_id}: fires={fg.trigger_fires}, "
                                  f"expected {should_fire}")
        if not check_extraction_integrity(view):
            trigger_errors.append(f"{task_id}: extraction integrity failed")
    report["checks"]["trigger_expectations"] = trigger_errors or "20/20 ok"
    report["failures"].extend(trigger_errors)

    jaccard_hits = []
    fixture_shingles = {t: wording_shingles(
        exclusion_manifest["wordings"]["fixtures"][t]) for t in fixtures}
    for probe_id, text in probe_texts.items():
        ps = wording_shingles(text)
        for t, fs in fixture_shingles.items():
            j = shingle_jaccard(ps, fs)
            if j >= 0.20:
                jaccard_hits.append(f"{probe_id} vs {t}: Jaccard {j:.3f}")
    report["checks"]["probe_fixture_wording_disjointness"] = \
        jaccard_hits or "15 probes x 20 foregrounds all < 0.20"
    report["failures"].extend(jaccard_hits)

    plan = derive_call_plan(len(probe_texts), 2)
    report["checks"]["derived_call_plan"] = {
        "F": len(probe_texts),
        "primary_calls_branch": plan.primary_calls_branch,
        "ceiling_calls_branch": plan.ceiling_calls_branch,
        "roster_primary_total": plan.roster_primary_total,
        "roster_ceiling_total": plan.roster_ceiling_total,
    }

    # ---- DRAFT manifest (typed placeholders; NOT a pin) ----------------------
    def pending(name: str) -> str:
        report["placeholders_pending"].append(name)
        return c.sha256_utf8(f"PENDING-PLACEHOLDER:{name}")

    from harness.efc_packet import derive_total_budget_tokens
    draft_manifest = {
        "part_i_spec_hash": c.PART_I_SPEC_SHA256,
        "engine_roster": ["openai/gpt-oss-20b",
                          "PENDING-openai-api-model-id"],
        "model_id": "PENDING-live-api-listing",
        "decoding_contract_id": "PENDING-decoding-contract",
        "renderer_id": "efc_renderer_v0",
        "foreground_template_hash": foreground_template_hash(),
        "calibration_fixtures": [{"fixture_id": e["id"], "sha256": e["sha256"]}
                                 for e in entries
                                 if e["role"] in ("s_family", "analog")],
        "world_oracles": oracle_manifest_rows,
        "ignorance_probe_contract": {
            "probe_fixture_ids": probe_contract["probe_fixture_ids"],
            "max_recoverable_rate": MAX_RECOVERABLE_RATE},
        "predicate_contract_hash": pending("predicate_contract_hash"),
        "extractor_hash": pending("extractor_hash"),
        "check_contract_hash": pending("check_contract_hash(resolution A)"),
        "generic_caution_text": c.GENERIC_CAUTION_TEXT,
        "generic_caution_sha256": c.GENERIC_CAUTION_SHA256,
        "offer_projection_text": c.OFFER_PROJECTION_TEXT,
        "offer_projection_sha256": c.OFFER_PROJECTION_SHA256,
        "calibration_k": c.CALIBRATION_K,
        "temperature": c.CALIBRATION_TEMPERATURE,
        "collapse_diagnostic_temperature": c.COLLAPSE_DIAGNOSTIC_TEMPERATURE,
        "stop_rule": c.STOP_RULE_ID,
        "n_max": c.N_MAX,
        "total_budget_tokens": derive_total_budget_tokens(
            plan, PROVISIONAL_PROMPT_CAP, PROVISIONAL_COMPLETION_CAP),
        "population_region": {"vertices": POPULATION_REGION_VERTICES},
    }
    report["placeholders_pending"] += [
        "engine_roster[1] (live API listing)", "model_id",
        "decoding_contract_id",
        f"total_budget_tokens (derived with PROVISIONAL caps "
        f"{PROVISIONAL_PROMPT_CAP}/{PROVISIONAL_COMPLETION_CAP})"]
    result = check_calibration_manifest(draft_manifest)
    report["checks"]["draft_manifest_machine_check"] = {
        "structurally_ok": result.ok,
        "failures": list(result.failures),
        "draft_hash_NOT_A_PIN": result.manifest_hash,
    }
    if not result.ok:
        report["failures"].extend(result.failures)

    # ---- authoring artifacts --------------------------------------------------
    AUTHORING_ROOT.mkdir(parents=True, exist_ok=True)
    (AUTHORING_ROOT / "DRAFT_calibration_manifest.json").write_bytes(
        canonical_json_bytes(draft_manifest))
    (AUTHORING_ROOT / "population_intent_declaration.json").write_bytes(
        canonical_json_bytes({
            "declared_before_any_calibration_contact": True,
            "population_intent": c.POPULATION_INTENT_REGION,
            "population_region": {"vertices": POPULATION_REGION_VERTICES},
            "canonical_serialization_sha256": c.sha256_utf8(json.dumps(
                {"vertices": POPULATION_REGION_VERTICES}, sort_keys=True,
                separators=(",", ":"))),
        }))
    (AUTHORING_ROOT / "placebo_truth_verification.json").write_bytes(
        canonical_json_bytes(placebo_truth))
    (AUTHORING_ROOT / "allocation.json").write_bytes(canonical_json_bytes({
        "active": {t: {"record": s["record"],
                       "family": rows[s["record"]]["family"],
                       "role": s["role"],
                       **({"shape": s["shape"]} if "shape" in s else {}),
                       **({"stratum": s["stratum"]} if "stratum" in s else {}),
                       **({"variant": s["variant"]} if "variant" in s else {})}
                   for t, s in FIXTURES.items()},
        "placebo_pool": {slot: rows[slot]["record_id"]
                         for slot in sorted(PLACEBO_POOL)},
        "reserves": RESERVES,
        "wire_rule": {"rule_id": rule_id,
                      "wire_contract_sha256": wire_rule_contract_hash(wire_rule)},
    }))

    report["artifact_hashes"] = {
        "packet_index": sha256_bytes((PACKET_ROOT / "packet_index.json").read_bytes()),
        "draft_manifest": sha256_bytes(
            (AUTHORING_ROOT / "DRAFT_calibration_manifest.json").read_bytes()),
        "exclusion_manifest": siblings["exclusion_manifest"]["sha256"],
    }
    report["disclosure"] = {
        "engines_contacted": 0, "probes_run": 0,
        "held_out_fixtures_authored": 0, "commits": 0,
        "browsing_or_fetching": "none",
    }
    (AUTHORING_ROOT / "c2_check_report.json").write_bytes(
        canonical_json_bytes(report))

    ok = not report["failures"]
    print(json.dumps(report, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
