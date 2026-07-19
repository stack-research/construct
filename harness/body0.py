"""Body-0 shared invariants: deterministic adapters, protected projections, and cost replay.

Body-0 composes already-earned primitives without widening them:

* M2's trace-only earned record remains a ``Record``;
* M3's out-of-band metadata is projected and hash-checked at every transition;
* X2's hot/cold operations remain the only residence actuator.

This module contains no engine calls and no policy choice.  Runner and scorer
share canonicalization, while the scorer reconstructs every claimed state from
ledger rows rather than trusting sidecars or logged totals.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .records import Record
from .run_m3 import store_digest_from_records

ROOT = Path(__file__).resolve().parent.parent

BRANCH_R = "B0-R"
BRANCH_C = "B0-C"
BRANCH_A = "B0-A"
BRANCH_X = "B0-X"
BRANCHES = (BRANCH_R, BRANCH_C, BRANCH_A, BRANCH_X)

ADAPTER_ID = "body0_identity_v1"
ADAPTER_FIELDS = (
    "record_id",
    "text",
    "created_at",
    "predeclared_usage",
    "vocabulary_kind",
    "trust",
    "supersedes",
    "provenance",
)


class Body0ContractError(ValueError):
    """Fail-closed contract violation before a Body-0 claim can be scored."""


@dataclass(frozen=True)
class AdapterReceipt:
    adapter_id: str
    input_sha256: str
    output_sha256: str
    fields: tuple[str, ...]
    policy_effects: tuple[str, ...] = ()

    @property
    def identity_ok(self) -> bool:
        return (
            self.adapter_id == ADAPTER_ID
            and self.input_sha256 == self.output_sha256
            and self.fields == ADAPTER_FIELDS
            and not self.policy_effects
        )


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def sha256_json(value) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def record_dict(record: Record) -> dict:
    return {
        "record_id": record.record_id,
        "text": record.text,
        "created_at": record.created_at,
        "predeclared_usage": record.predeclared_usage,
        "vocabulary_kind": record.vocabulary_kind,
        "trust": record.trust,
        "supersedes": list(record.supersedes),
        "provenance": record.provenance,
    }


def record_from_dict(value: dict) -> Record:
    return Record(**{**value, "supersedes": tuple(value.get("supersedes", ()))})


def adapt_earned_record(record: Record, adapter_id: str = ADAPTER_ID) -> tuple[Record, AdapterReceipt]:
    """Identity-only M2→Body-0 adapter.

    The adapter may carry the existing record across an interface.  It may not
    derive content, mint authority, select a policy, or add a field.  An unknown
    adapter id is the reviewed ``B0-interface-blocked`` path.
    """
    if adapter_id != ADAPTER_ID:
        raise Body0ContractError(
            f"blocked(interface_requires_new_mechanism): unknown adapter {adapter_id!r}"
        )
    before = record_dict(record)
    # Deliberately reconstruct through the closed carrier fields so an accidental
    # dataclass/schema expansion cannot silently enter Body-0.
    carried = record_from_dict({k: before[k] for k in ADAPTER_FIELDS})
    after = record_dict(carried)
    receipt = AdapterReceipt(
        adapter_id=adapter_id,
        input_sha256=sha256_json(before),
        output_sha256=sha256_json(after),
        fields=ADAPTER_FIELDS,
    )
    if not receipt.identity_ok:
        raise Body0ContractError("blocked(interface_requires_new_mechanism): adapter is not identity-only")
    return carried, receipt


def protected_projection(records: Iterable[Record], authority_seed: dict[str, float],
                         earned_record_id: str) -> dict:
    """The protected out-of-band surface checked across the composed loop.

    ``m3_store_digest`` preserves M3's exact protected metadata projection.
    The full lineage hash and earned provenance hash add deterministic carrying
    receipts; they do not introduce a policy or an authority source.
    """
    rows = [record_dict(r) for r in records]
    earned = next((r for r in rows if r["record_id"] == earned_record_id), None)
    if earned is None:
        raise Body0ContractError(f"earned record {earned_record_id!r} absent from lineage")
    authority = {str(k): float(v) for k, v in sorted(authority_seed.items())}
    return {
        "m3_store_digest": store_digest_from_records(rows, authority),
        "lineage_sha256": sha256_json(sorted(rows, key=lambda r: r["record_id"])),
        "earned_provenance_sha256": sha256_json(earned.get("provenance")),
        "authority_seed": authority,
        "earned_record_id": earned_record_id,
    }


def protected_projection_hash(projection: dict) -> str:
    return sha256_json(projection)


def packet_sha256(manifest: dict, root: Path = ROOT) -> str:
    """Hash the manifest-declared frozen corpus/episode packet.

    The manifest itself is excluded so the pinned hash does not recursively
    contain itself.  Paths and file-byte hashes both enter the digest.
    """
    h = hashlib.sha256()
    for rel in manifest.get("frozen_files", []):
        path = root / rel
        if not path.is_file():
            raise Body0ContractError(f"frozen packet file missing: {rel}")
        h.update(rel.encode() + b"\x00" + hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


def token_cost(record_texts: dict[str, str], hot_ids: Iterable[str]) -> int:
    return sum(len(record_texts[rid].split()) for rid in hot_ids)


def replay_hot_snapshots(all_ids: Iterable[str], operations: Iterable[dict],
                         seq_indexes: Iterable[int]) -> dict[int, frozenset[str]]:
    """Replay hot sets at each pre-answer cost snapshot.

    Body-0 operation rows name ``effective_before_seq``. Cooling applies before
    the first residence episode; rematerialization applies before recurrence.
    """
    hot = set(all_ids)
    by_seq: dict[int, list[dict]] = {}
    for op in operations:
        by_seq.setdefault(int(op["effective_before_seq"]), []).append(op)
    snapshots: dict[int, frozenset[str]] = {}
    for seq_index in sorted(seq_indexes):
        for op in sorted(by_seq.get(seq_index, []), key=lambda row: row["event_index"]):
            if op["op"] == "prune":
                hot.discard(op["record_id"])
            elif op["op"] == "rematerialize":
                hot.add(op["record_id"])
            else:
                raise Body0ContractError(f"unknown hot-store op {op['op']!r}")
        snapshots[seq_index] = frozenset(hot)
    return snapshots


def replay_costs(all_ids: Iterable[str], record_texts: dict[str, str],
                 operations: Iterable[dict], seq_indexes: Iterable[int]) -> dict[int, int]:
    snapshots = replay_hot_snapshots(all_ids, operations, seq_indexes)
    return {k: token_cost(record_texts, hot) for k, hot in snapshots.items()}


def cost_state_preflight(record_texts: dict[str, str], earned_record_id: str,
                         residence_count: int) -> dict:
    """Compute the reviewed full-sequence R/C cost geometry before branch contact."""
    if residence_count < 1:
        return {
            "gate_open": False,
            "reason": "no_cold_residence",
            "residence_count": residence_count,
        }
    all_ids = set(record_texts)
    if earned_record_id not in all_ids:
        raise Body0ContractError("earned record missing from cost preflight")
    full = token_cost(record_texts, all_ids)
    cold = token_cost(record_texts, all_ids - {earned_record_id})
    # Residence episodes plus one recurrence. C pays full hot cost again at
    # recurrence after rematerialization; that is the rematerialization tax.
    cost_r = full * (residence_count + 1)
    cost_c = cold * residence_count + full
    return {
        "gate_open": cost_c < cost_r,
        "reason": "strict_cost_margin" if cost_c < cost_r else "cost_margin_absent",
        "residence_count": residence_count,
        "full_hot_tokens": full,
        "cold_hot_tokens": cold,
        "rematerialization_hot_tokens": full - cold,
        "cost_R": cost_r,
        "cost_C": cost_c,
        "margin": cost_r - cost_c,
    }
