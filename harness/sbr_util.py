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
R_HANDLES = [f"R{i:02d}" for i in range(1, 22)] + ["STOP"]


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


def action_space_hash(instrument_version: str = "0.2") -> str:
    if instrument_version == "0.3":
        payload = {"actions": R_HANDLES, "schema": "R##|STOP"}
    else:
        payload = {"actions": sorted(ACTION_SPACE),
                   "schema": "READ(surface_id)|STOP"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def render_catalog_list(catalog: dict, sort_rule: str) -> str:
    lines = []
    for sid in sorted_surface_ids(catalog, sort_rule):
        lines.append(f"{sid}: {catalog[sid]['title']}")
    return "Catalog surfaces (ids and titles only):\n" + "\n".join(lines)


_RESUME_NOTE_RE = re.compile(r"^Resume note \(recorded", re.IGNORECASE)
_STALE_PREFIX = "Resume note (recorded matter-of-fact):"


def render_foreground_block(text: str | None) -> str:
    """Render optional stale_claim (§19 temptation). Idempotent on resume-note prefix."""
    if not text:
        return ""
    stripped = text.strip()
    if _RESUME_NOTE_RE.match(stripped):
        return stripped + "\n\n"
    return f"{_STALE_PREFIX}\n{stripped}\n\n"


def render_canonical_artifact(canonical_state: dict) -> str:
    """Rendered minted frontier artifact (§16 / Part III §27 a_i numerator)."""
    return (
        "Frontier artifact (schema-bound resume state, charged on every resume):\n"
        + json.dumps(canonical_state, sort_keys=True)
        + "\n\n"
    )


def artifact_render_tokens(canonical_state: dict) -> int:
    """Token count of the rendered canonical artifact — shared by mint, scorer,
    pay_window_geometry, and foreground_budget_ok (SPEC Part III §34 F2)."""
    return len(render_canonical_artifact(canonical_state).split())


def render_resumable_foreground(canonical_state: dict,
                                stale_claim: str | None) -> str:
    """Resumable branch foreground: canonical artifact + optional stale claim."""
    artifact = render_canonical_artifact(canonical_state)
    stale = render_foreground_block(stale_claim) if stale_claim else ""
    return artifact + stale


def build_sbr_system(catalog: dict, sort_rule: str, question: str,
                     instrument_version: str = "0.2") -> str:
    """Single presentation path: catalog + task preamble (§15 / §28)."""
    preamble = (
        "You are completing a catalog-driven task. Choose surfaces to read "
        "or stop when ready to answer.\n\n"
    )
    if instrument_version == "0.3":
        lines = []
        for i, sid in enumerate(sorted_surface_ids(catalog, sort_rule), start=1):
            lines.append(f"R{i:02d}: {sid} — {catalog[sid]['title']}")
        catalog_block = (
            "Catalog surfaces (handles and titles only):\n"
            + "\n".join(lines)
            + "\n\nLegal actions: R01–R21 or STOP (one handle per turn).\n"
        )
    else:
        catalog_block = render_catalog_list(catalog, sort_rule) + "\n"
    return preamble + catalog_block + f"\nTask: {question}\n"


def sbr_renderer_version() -> str:
    """Hash of everything that shapes the SBR engine presentation surface."""
    from .engine import sbr_action_instruction

    src = (
        inspect.getsource(build_sbr_system)
        + inspect.getsource(render_canonical_artifact)
        + inspect.getsource(artifact_render_tokens)
        + inspect.getsource(render_foreground_block)
        + inspect.getsource(render_catalog_list)
        + sbr_action_instruction("0.2")
        + sbr_action_instruction("0.3")
    )
    return hashlib.sha256(src.encode()).hexdigest()[:16]


def handle_to_surface_id(handle: str, visible: list[str]) -> str | None:
    """Map a legal R-handle to surface_id (for scorer chain replay)."""
    m = re.match(r"^\s*(R\d{2}|STOP)\s*$", handle.strip(), re.IGNORECASE)
    if not m:
        return None
    token = m.group(1).upper()
    if token == "STOP":
        return None
    idx = int(token[1:])
    if idx < 1 or idx > len(visible):
        return None
    return visible[idx - 1]


def recompute_c_max(budgets: dict) -> int:
    return (budgets["max_read_tokens"]
            + budgets["max_steps"] * budgets["action_overhead_tokens"])
