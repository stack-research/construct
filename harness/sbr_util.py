"""Shared SBR helpers (SPEC_PAUSE_RESUME Part II §15/§16).

Factored out so run_sbr and score_prf do not circular-import.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import re
from typing import Any

ACTION_SPACE = {"READ", "STOP"}


def _natural_sort_key(sid: str) -> tuple:
    parts = re.split(r"(\d+)", sid)
    return tuple(int(p) if p.isdigit() else p for p in parts)


def sorted_surface_ids(catalog: dict, sort_rule: str) -> list[str]:
    ids = list(catalog)
    if sort_rule == "by_id":
        return sorted(ids, key=_natural_sort_key)
    return sorted(ids)


def catalog_hash(catalog: dict, sort_rule: str) -> str:
    ids = sorted_surface_ids(catalog, sort_rule)
    payload = [{"surface_id": sid, "title": catalog[sid]["title"],
                "content_hash": catalog[sid]["content_hash"]}
               for sid in ids]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def action_space_hash() -> str:
    return hashlib.sha256(json.dumps(
        {"actions": sorted(ACTION_SPACE),
         "schema": "READ(surface_id)|STOP"},
        sort_keys=True).encode()).hexdigest()


def render_catalog_list(catalog: dict, sort_rule: str) -> str:
    lines = []
    for sid in sorted_surface_ids(catalog, sort_rule):
        lines.append(f"{sid}: {catalog[sid]['title']}")
    return "Catalog surfaces (ids and titles only):\n" + "\n".join(lines)


_RESUME_NOTE_RE = re.compile(r"^Resume note \(recorded", re.IGNORECASE)


def render_foreground_block(text: str | None) -> str:
    """Render optional stale_claim (§19 temptation). Idempotent on resume-note prefix."""
    if not text:
        return ""
    stripped = text.strip()
    if _RESUME_NOTE_RE.match(stripped):
        return stripped + "\n\n"
    return f"{_STALE_PREFIX}\n{stripped}\n\n"


def render_canonical_artifact(canonical_state: dict) -> str:
    """Rendered minted frontier artifact (§16 a_i numerator)."""
    return (
        "Frontier artifact (schema-bound resume state, charged on every resume):\n"
        + json.dumps(canonical_state, sort_keys=True)
        + "\n\n"
    )


def render_resumable_foreground(canonical_state: dict,
                                stale_claim: str | None) -> str:
    """Resumable branch foreground: canonical artifact + optional stale claim."""
    artifact = render_canonical_artifact(canonical_state)
    stale = render_foreground_block(stale_claim) if stale_claim else ""
    return artifact + stale


def build_sbr_system(catalog: dict, sort_rule: str, question: str) -> str:
    """Single presentation path: catalog + task preamble (§15)."""
    return (
        "You are completing a catalog-driven task. Choose surfaces to read "
        "or stop when ready to answer.\n\n"
        + render_catalog_list(catalog, sort_rule)
        + f"\n\nTask: {question}\n"
    )


def sbr_renderer_version() -> str:
    """Hash of everything that shapes the SBR engine presentation surface."""
    from .engine import SBR_ACTION_INSTRUCTION

    src = (
        inspect.getsource(build_sbr_system)
        + inspect.getsource(render_canonical_artifact)
        + inspect.getsource(render_foreground_block)
        + inspect.getsource(render_catalog_list)
        + SBR_ACTION_INSTRUCTION
    )
    return hashlib.sha256(src.encode()).hexdigest()[:16]


def recompute_c_max(budgets: dict) -> int:
    return (budgets["max_read_tokens"]
            + budgets["max_steps"] * budgets["action_overhead_tokens"])
