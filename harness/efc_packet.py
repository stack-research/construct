"""Calibration packet loader/validator, exclusion screen, and derived budget
— EFC_CALIBRATION_PACKET_DESIGN §3-§5, §8, §9; sealed Part I §5.2/§7/§8.2.

This module implements the frozen packet *machinery* only. It authors no
fixture facts, sources, oracle records, or manifest instance: everything it
loads in this workspace is a conspicuously fictional synthetic wire fixture,
and nothing loaded here may later become calibration evidence.

Fail-closed loader contract (B2): closed index shape; unique ids and unique
relative paths; every path confined to the packet root (no absolute paths,
no `..`, no symlinks); sibling artifacts hash-checked, not merely present;
exactly 5 S-family identities with the frozen 3-mismatch/2-commit split and
exactly 15 analog identities, 5 per stratum (an empty board fails); entry id
equals the fixture/typed-object id; every required S2/P placebo present,
inside the ≤256-token output ceiling, and passed through
`placebo_pairing_failures` against the exact relevant evidence rendering;
the synthetic carrier §3.1-complete via `efc_carrier.validate_carrier` under
an explicit synthetic/non-mintable wrapper; the ignorance-probe and
isolation artifacts validated against closed shapes.

Call counts are DERIVED from identity cardinality and the §10.5 stop rule
(design §9); there is no manifest call-budget key, and this module refuses to
produce one.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from harness import efc_contracts as c
from harness.efc_carrier import (CarrierContractError, DispositionCarrier,
                                 ValidityEnvelope, validate_carrier)
from harness.efc_check import (CheckContractError,
                               ProductionComparisonContract, ProvenanceStore,
                               WireComparisonRule,
                               run_production_scope_check,
                               run_scope_provenance_check)
from harness.efc_renderer import build_foreground, canonical_tokens

S_FAMILY_COUNT = 5
S_FAMILY_MISMATCH_COUNT = 3   # frozen architectural precommit (design §4.1)
S_FAMILY_COMMIT_COUNT = 2
ANALOG_PER_STRATUM = 5
ANALOG_COUNT = ANALOG_PER_STRATUM * len(c.STRATA)
S_SHAPES = ("mismatch", "commit")

PACKET_INDEX_KEYS = frozenset({"packet_id", "entries", "siblings"})
ENTRY_KEYS = frozenset({"id", "path", "role", "sha256"})
ENTRY_ROLES = ("s_family", "analog", "placebo", "probe_contract", "carrier")
SIBLING_NAMES = ("exclusion_manifest", "difficulty_rationale",
                 "isolation_contract")
SIBLING_KEYS = frozenset({"path", "sha256"})
PROBE_CONTRACT_KEYS = frozenset({"probe_fixture_ids", "probe_texts",
                                 "max_recoverable_rate"})
CARRIER_WRAPPER_KEYS = frozenset({"synthetic", "non_mintable", "carrier"})


class PacketContractError(ValueError):
    """Packet outside the accepted design invariants. Fail-closed."""


# ---------------------------------------------------------------------------
# Exclusion screen (design §8) — exact, in order; thresholds are frozen
# architectural precommits, not tunables.
# ---------------------------------------------------------------------------

SHINGLE_WIDTH = 5
JACCARD_REJECT_THRESHOLD = 0.20


def normalize_wording(text: str) -> str:
    """Steps 1-3: NFKC, casefold, whitespace collapse (runs → single space,
    trim)."""
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def wording_shingles(text: str) -> frozenset[tuple[str, ...]]:
    """Step 5 basis: whitespace tokens (empty dropped) of the normalized
    wording; five-token contiguous windows. Fewer than five tokens → empty
    set (no shingle-based rejection)."""
    tokens = normalize_wording(text).split()
    if len(tokens) < SHINGLE_WIDTH:
        return frozenset()
    return frozenset(tuple(tokens[i:i + SHINGLE_WIDTH])
                     for i in range(len(tokens) - SHINGLE_WIDTH + 1))


def shingle_jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 0.0  # empty/empty: Jaccard 0/0 produces no rejection
    union = len(a | b)
    return len(a & b) / union if union else 0.0


@dataclass(frozen=True)
class ExclusionVerdict:
    rejected: bool
    reasons: tuple[str, ...]


def exclusion_screen(candidate_wording: str, candidate_ids: dict,
                     calibration_wordings: list[str],
                     calibration_ids: dict) -> ExclusionVerdict:
    """Design §8, in order. `*_ids` carry the four exact-rejection id families
    as iterables under the keys source_identity / oracle_record_id /
    entity_key / task_identity. This deterministic screen does not prove
    semantic disjointness; cold attestation remains a separate act."""
    reasons: list[str] = []
    for kind in ("source_identity", "oracle_record_id", "entity_key",
                 "task_identity"):
        shared = set(candidate_ids.get(kind, ())) & set(
            calibration_ids.get(kind, ()))
        if shared:
            reasons.append(f"exact rejection: shared {kind} {sorted(shared)}")
    cand = wording_shingles(candidate_wording)
    for i, wording in enumerate(calibration_wordings):
        j = shingle_jaccard(cand, wording_shingles(wording))
        if j >= JACCARD_REJECT_THRESHOLD:
            reasons.append(f"shingle rejection: Jaccard {j:.3f} >= "
                           f"{JACCARD_REJECT_THRESHOLD} vs calibration "
                           f"wording [{i}]")
    return ExclusionVerdict(rejected=bool(reasons), reasons=tuple(reasons))


# ---------------------------------------------------------------------------
# Placebo pairing gate (§7/§8.2: disjoint references and entity keys,
# position- and ±5-canonical-token-matched to the relevant evidence).
# ---------------------------------------------------------------------------

PLACEBO_KEYS = frozenset({"placebo_id", "placebo_for", "text",
                          "disjoint_reference", "entity_keys"})


def placebo_pairing_failures(placebo: dict, relevant_evidence_text: str,
                             fixture: dict) -> list[str]:
    failures = []
    missing = PLACEBO_KEYS - set(placebo)
    if missing:
        return [f"placebo missing {k}" for k in sorted(missing)]
    if set(placebo) - PLACEBO_KEYS:
        failures.append(f"placebo carries undeclared keys "
                        f"{sorted(set(placebo) - PLACEBO_KEYS)}")
    # §10.1/§8.2: the evidence-shaped object must fit the check-output
    # ceiling regardless of pairing (additional correction: enforced even
    # before the ±5 comparison)
    n_tokens = len(canonical_tokens(str(placebo["text"])))
    if n_tokens > c.MAX_EXTERNAL_CHECK_OUTPUT_TOKENS:
        failures.append(f"placebo text {n_tokens} tokens > "
                        f"{c.MAX_EXTERNAL_CHECK_OUTPUT_TOKENS} evidence "
                        "ceiling (§10.1)")
    if placebo["disjoint_reference"] == fixture.get("source_reference"):
        failures.append("placebo cites the fixture's own source_reference")
    fixture_entities = set(fixture.get("entity_keys", ()))
    if set(placebo["entity_keys"]) & fixture_entities:
        failures.append("placebo shares entity keys with the fixture")
    delta = abs(n_tokens - len(canonical_tokens(relevant_evidence_text)))
    if delta > c.PLACEBO_TOKEN_TOLERANCE:
        failures.append(f"placebo token count off by {delta} > "
                        f"±{c.PLACEBO_TOKEN_TOLERANCE} canonical tokens")
    return failures


# ---------------------------------------------------------------------------
# Packet load + fail-closed structural validation.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Packet:
    root: str
    index: dict
    s_family: dict[str, dict]            # id -> fixture (with `_shape`)
    analog: dict[str, dict]              # id -> fixture (with `stratum`)
    placebos: dict[str, dict]            # placebo_for -> placebo object
    probes: dict
    carrier: dict
    failures: tuple[str, ...] = field(default=())

    @property
    def ok(self) -> bool:
        return not self.failures

    def placebo_sha256_by_fixture(self) -> dict[str, str]:
        """Pinned placebo identities for untrusting replay (B5)."""
        return {fixture_id: hashlib.sha256(
                    str(p["text"]).encode("utf-8")).hexdigest()
                for fixture_id, p in self.placebos.items() if "text" in p}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path, failures: list[str]):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        failures.append(f"{path.name}: unreadable ({e})")
        return None


def _safe_path(root: Path, rel, failures: list[str],
               label: str) -> Path | None:
    """Every packet path stays under the packet root: no absolute paths, no
    `..` escape, no symlinks anywhere on the relative chain (B2)."""
    if not isinstance(rel, str) or not rel:
        failures.append(f"{label}: path must be a non-empty string")
        return None
    p = Path(rel)
    if p.is_absolute():
        failures.append(f"{label}: absolute path {rel!r} refused")
        return None
    if ".." in p.parts:
        failures.append(f"{label}: path {rel!r} escapes the packet root")
        return None
    full = root / p
    walk = root
    for part in p.parts:
        walk = walk / part
        if walk.is_symlink():
            failures.append(f"{label}: symlink {walk.name!r} on packet path "
                            f"{rel!r} refused")
            return None
    try:
        if not full.resolve().is_relative_to(root.resolve()):
            failures.append(f"{label}: resolved path leaves the packet root")
            return None
    except OSError as e:
        failures.append(f"{label}: unresolvable path {rel!r} ({e})")
        return None
    if not full.is_file():
        failures.append(f"{label}: file {rel!r} absent")
        return None
    return full


def _validate_probe_contract(probes: dict, failures: list[str]) -> None:
    if set(probes) != PROBE_CONTRACT_KEYS:
        failures.append(f"ignorance-probe contract keys {sorted(probes)} != "
                        f"{sorted(PROBE_CONTRACT_KEYS)} (closed shape)")
        return
    ids = probes["probe_fixture_ids"]
    texts = probes["probe_texts"]
    if (not isinstance(ids, list) or not ids
            or len(set(ids)) != len(ids)
            or not all(isinstance(i, str) and i for i in ids)):
        failures.append("probe_fixture_ids must be non-empty unique ids")
        return
    if not isinstance(texts, dict) or set(texts) != set(ids):
        failures.append("probe_texts keys must equal probe_fixture_ids")
        return
    if not all(isinstance(t, str) and t.strip() for t in texts.values()):
        failures.append("every probe text must be a non-empty string")
    rate = probes["max_recoverable_rate"]
    if not isinstance(rate, (int, float)) or isinstance(rate, bool) \
            or not (0.0 <= float(rate) < 1.0):
        failures.append("max_recoverable_rate must be in [0, 1)")


def _validate_carrier_wrapper(carrier: dict, failures: list[str]) -> None:
    """§3.1-complete synthetic carrier under an explicit non-mintable
    wrapper, validated by the existing typed machinery (B2)."""
    if set(carrier) != CARRIER_WRAPPER_KEYS:
        failures.append(f"carrier wrapper keys {sorted(carrier)} != "
                        f"{sorted(CARRIER_WRAPPER_KEYS)} (closed shape)")
        return
    if carrier["synthetic"] is not True or carrier["non_mintable"] is not True:
        failures.append("packet carrier must be marked synthetic and "
                        "non-mintable: it cannot mint live resident state "
                        "(design §4.2)")
    payload = carrier["carrier"]
    if not isinstance(payload, dict):
        failures.append("carrier payload must be a §3.1 field object")
        return
    try:
        envelope = ValidityEnvelope(**payload["validity_envelope"])
        typed = DispositionCarrier(**{
            **{k: v for k, v in payload.items() if k != "validity_envelope"},
            "predicate_feature_bindings":
                dict(payload["predicate_feature_bindings"]),
            "warrant_event_ids": tuple(payload["warrant_event_ids"]),
            "validity_envelope": envelope,
        })
        validate_carrier(typed)
    except (KeyError, TypeError) as e:
        failures.append(f"carrier payload is not §3.1-complete: {e}")
    except CarrierContractError as e:
        failures.append(f"carrier fails §3.1 validation: {e}")


def load_packet(root: str | Path, store: ProvenanceStore,
                wire_rule: WireComparisonRule) -> Packet:
    """Load and fail-closed-validate a packet. The provenance store and the
    injected wire comparison-rule executor are required because the placebo
    gate pairs each placebo against the EXACT relevant evidence rendering
    its fixture's check would produce (B2)."""
    root = Path(root)
    failures: list[str] = []
    index = _load_json(root / "packet_index.json", failures)
    if index is None:
        return Packet(str(root), {}, {}, {}, {}, {}, {}, tuple(failures))

    # --- closed index shape --------------------------------------------------
    if not isinstance(index, dict) or set(index) != PACKET_INDEX_KEYS:
        failures.append(f"packet index keys "
                        f"{sorted(index) if isinstance(index, dict) else index!r}"
                        f" != {sorted(PACKET_INDEX_KEYS)} (closed shape)")
        return Packet(str(root), index if isinstance(index, dict) else {},
                      {}, {}, {}, {}, {}, tuple(failures))
    if not isinstance(index.get("packet_id"), str) or not index["packet_id"]:
        failures.append("packet_id must be a non-empty string")

    # --- siblings: hash-checked, closed name set (B2) -------------------------
    siblings = index["siblings"]
    if not isinstance(siblings, dict) or set(siblings) != set(SIBLING_NAMES):
        failures.append(f"siblings must be exactly {sorted(SIBLING_NAMES)}")
        siblings = {}
    sibling_paths: list[str] = []
    for name, entry in siblings.items():
        if not isinstance(entry, dict) or set(entry) != SIBLING_KEYS:
            failures.append(f"sibling {name} must be {{path, sha256}}")
            continue
        sibling_paths.append(entry["path"])
        full = _safe_path(root, entry["path"], failures, f"sibling {name}")
        if full is None:
            continue
        actual = _sha256_file(full)
        if entry["sha256"] != actual:
            failures.append(f"sibling {name}: sha256 mismatch "
                            f"({entry['sha256']} != {actual})")
        elif not full.read_bytes().strip():
            failures.append(f"sibling {name}: empty artifact")

    # --- entries: closed shape, unique ids and paths, hash-checked ------------
    entries = index["entries"]
    if not isinstance(entries, list):
        failures.append("entries must be a list")
        entries = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set(sibling_paths)
    s_family: dict[str, dict] = {}
    analog: dict[str, dict] = {}
    placebos: dict[str, dict] = {}
    probes: dict = {}
    carrier: dict = {}
    role_counts = {role: 0 for role in ENTRY_ROLES}
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != ENTRY_KEYS:
            failures.append(f"entries[{i}] must be {{id, path, role, sha256}}")
            continue
        entry_id, rel, role = str(entry["id"]), entry["path"], entry["role"]
        if role not in ENTRY_ROLES:
            failures.append(f"entries[{i}]: unknown role {role!r}: the "
                            "identity registry is closed")
            continue
        role_counts[role] += 1
        if entry_id in seen_ids:
            failures.append(f"duplicate entry id {entry_id!r}")
        seen_ids.add(entry_id)
        if rel in seen_paths:
            failures.append(f"duplicate packet path {rel!r}")
        seen_paths.add(rel)
        full = _safe_path(root, rel, failures, f"entry {entry_id}")
        if full is None:
            continue
        actual = _sha256_file(full)
        if entry["sha256"] != actual:
            failures.append(f"{entry_id}: sha256 mismatch "
                            f"({entry['sha256']} != {actual})")
        payload = _load_json(full, failures)
        if payload is None:
            continue
        if role == "s_family":
            if str(payload.get("task_id")) != entry_id:
                failures.append(f"{entry_id}: entry id != fixture task_id "
                                f"{payload.get('task_id')!r}")
            shape = payload.pop("shape", None)
            if shape not in S_SHAPES:
                failures.append(f"{entry_id}: s_family shape {shape!r} "
                                f"not in {S_SHAPES}")
            payload["_shape"] = shape
            s_family[entry_id] = payload
        elif role == "analog":
            if str(payload.get("task_id")) != entry_id:
                failures.append(f"{entry_id}: entry id != fixture task_id "
                                f"{payload.get('task_id')!r}")
            analog[entry_id] = payload
        elif role == "placebo":
            if str(payload.get("placebo_id")) != entry_id:
                failures.append(f"{entry_id}: entry id != placebo_id "
                                f"{payload.get('placebo_id')!r}")
            target = str(payload.get("placebo_for"))
            if target in placebos:
                failures.append(f"duplicate placebo for fixture {target!r}")
            placebos[target] = payload
        elif role == "probe_contract":
            probes = payload
        elif role == "carrier":
            carrier = payload

    for role in ("probe_contract", "carrier"):
        if role_counts[role] != 1:
            failures.append(f"packet must carry exactly one {role}, has "
                            f"{role_counts[role]}")

    # --- identity-count invariants, unconditional (design §4.1/§4.2; B2:
    # the empty board fails) ---------------------------------------------------
    if len(s_family) != S_FAMILY_COUNT:
        failures.append(f"S-family has {len(s_family)} identities, needs "
                        f"exactly {S_FAMILY_COUNT}")
    shapes = [fx["_shape"] for fx in s_family.values() if fx.get("_shape")]
    if (shapes.count("mismatch") != S_FAMILY_MISMATCH_COUNT
            or shapes.count("commit") != S_FAMILY_COMMIT_COUNT):
        failures.append(
            f"S-family shape split {shapes.count('mismatch')}/"
            f"{shapes.count('commit')} != frozen "
            f"{S_FAMILY_MISMATCH_COUNT}/{S_FAMILY_COMMIT_COUNT} (design §4.1)")
    if len(analog) != ANALOG_COUNT:
        failures.append(f"analog board has {len(analog)} identities, needs "
                        f"exactly {ANALOG_COUNT}")
    by_stratum: dict[str, int] = {s: 0 for s in c.STRATA}
    for fixture_id, fixture in analog.items():
        stratum = fixture.get("stratum")
        if stratum not in by_stratum:
            failures.append(f"{fixture_id}: unknown stratum {stratum!r}")
        else:
            by_stratum[stratum] += 1
    for stratum, n in by_stratum.items():
        if n != ANALOG_PER_STRATUM:
            failures.append(f"analog stratum {stratum} has {n} identities, "
                            f"needs exactly {ANALOG_PER_STRATUM}")

    # --- §4.3 field discipline: every identity must render --------------------
    for fixture_id, fixture in {**s_family, **analog}.items():
        view = {k: v for k, v in fixture.items()
                if k not in ("_shape", "entity_keys")}
        try:
            build_foreground(view)
        except ValueError as e:
            failures.append(f"{fixture_id}: {e}")

    # --- placebo completeness + pairing against the exact relevant evidence
    # rendering (B2), evidence ceiling enforced inside the gate -----------------
    needs_placebo = list(s_family)
    needs_placebo += [fid for fid, fx in analog.items()
                      if fx.get("stratum") in c.TRIGGER_MATCHING_STRATA]
    for fixture_id in needs_placebo:
        fixture = {**s_family, **analog}[fixture_id]
        placebo = placebos.get(fixture_id)
        if placebo is None:
            failures.append(f"{fixture_id}: no pinned placebo object "
                            "(required for S2/P treatment)")
            continue
        try:
            # production path (P2): pairing derives the exact relevant
            # evidence through the hash-pinned production contract instead
            # of a wire executor.
            if isinstance(wire_rule, ProductionComparisonContract):
                evidence = run_production_scope_check(
                    store, str(fixture.get("source_reference")),
                    hashlib.sha256(str(fixture.get("decision_scope"))
                                   .encode("utf-8")).hexdigest(),
                    wire_rule)
            else:
                evidence = run_scope_provenance_check(
                    store, str(fixture.get("source_reference")),
                    str(fixture.get("decision_scope")), wire_rule)
        except CheckContractError as e:
            failures.append(f"{fixture_id}: cannot derive relevant evidence "
                            f"for placebo pairing: {e}")
            continue
        failures.extend(f"{fixture_id}: {msg}" for msg in
                        placebo_pairing_failures(placebo, evidence.rendered(),
                                                 fixture))
    for target in placebos:
        if target not in needs_placebo:
            failures.append(f"placebo pinned for {target!r}, which takes no "
                            "placebo treatment")

    # --- probe/isolation and carrier closed shapes ----------------------------
    if probes:
        _validate_probe_contract(probes, failures)
    if carrier:
        _validate_carrier_wrapper(carrier, failures)

    return Packet(str(root), index, s_family, analog, placebos, probes,
                  carrier, tuple(failures))


def packet_loader_contract_payload() -> dict:
    """Typed loader contract (B4): closed shapes, frozen counts, frozen
    exclusion constants."""
    return {
        "loader_id": "efc_packet_v0",
        "schema_version": "efc_packet_index_v1",
        "index_keys": sorted(PACKET_INDEX_KEYS),
        "entry_keys": sorted(ENTRY_KEYS),
        "entry_roles": list(ENTRY_ROLES),
        "sibling_names": list(SIBLING_NAMES),
        "counts": {"s_family": S_FAMILY_COUNT,
                   "s_family_mismatch": S_FAMILY_MISMATCH_COUNT,
                   "s_family_commit": S_FAMILY_COMMIT_COUNT,
                   "analog_per_stratum": ANALOG_PER_STRATUM},
        "exclusion": {"shingle_width": SHINGLE_WIDTH,
                      "jaccard_reject_threshold": JACCARD_REJECT_THRESHOLD},
        "placebo_keys": sorted(PLACEBO_KEYS),
        # resolution G: one structural insertion point for evidence-shaped
        # treatments (render_evidence_block)
        "placebo_position_gate": "structural_single_insertion_point",
        "placebo_token_tolerance": c.PLACEBO_TOKEN_TOLERANCE,
        "placebo_output_ceiling": c.MAX_EXTERNAL_CHECK_OUTPUT_TOKENS,
    }


def packet_loader_contract_hash() -> str:
    return hashlib.sha256(json.dumps(packet_loader_contract_payload(),
                                     sort_keys=True, separators=(",", ":")
                                     ).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Derived call/budget plan (design §9). Never a manifest field.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CallPlan:
    probe_calls_branch: int
    s_family_calls_branch: int
    analog_calls_branch: int
    primary_calls_branch: int
    conditional_calls_branch: int
    ceiling_calls_branch: int
    roster_primary_total: int
    roster_ceiling_total: int


def derive_call_plan(dispositive_fact_count: int, roster_size: int,
                     s_count: int = S_FAMILY_COUNT,
                     analog_count: int = ANALOG_COUNT) -> CallPlan:
    """Design §9, verbatim: counts derive from deduplicated dispositive-fact
    ids, identity cardinality, and the §10.5 stop rule (single conditional
    T=0.7 pass; probes are never rerun). No `total_budget_calls` key exists
    to store this — the plan is recomputed wherever needed."""
    if dispositive_fact_count < 1 or roster_size < 1:
        raise PacketContractError("call plan needs |F| >= 1 and |R| >= 1")
    probe = dispositive_fact_count
    s_calls = s_count * len(c.SOURCE_LEGS)
    analog_calls = analog_count * len(c.LANES)
    primary = probe + s_calls + analog_calls
    conditional = s_calls + analog_calls
    ceiling = primary + conditional
    return CallPlan(probe, s_calls, analog_calls, primary, conditional,
                    ceiling, primary * roster_size, ceiling * roster_size)


def derive_total_budget_tokens(plan: CallPlan, prompt_cap: int,
                               completion_cap: int) -> int:
    """§5.2's one stored budget value, derived at manifest time: the sum over
    the derived ceiling call plan of frozen per-call prompt and completion
    upper bounds plus the §10.1 controller source-read bound. The ≤256
    check-output cap sizes evidence already inside the prompt envelope and is
    not added again (design §9)."""
    if prompt_cap < 1 or completion_cap < 1:
        raise PacketContractError("per-call caps must be positive")
    per_call = prompt_cap + completion_cap + c.MAX_CONTROLLER_SOURCE_READ_TOKENS
    return plan.roster_ceiling_total * per_call
