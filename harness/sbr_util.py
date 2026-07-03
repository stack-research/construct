"""Shared SBR helpers (SPEC_PAUSE_RESUME Part II §15/§16).

Factored out so run_sbr and score_prf do not circular-import.
"""

from __future__ import annotations

import hashlib
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


def render_foreground_block(text: str | None) -> str:
    if not text:
        return ""
    return f"Resume note (recorded matter-of-fact):\n{text}\n\n"


def recompute_c_max(budgets: dict) -> int:
    return (budgets["max_read_tokens"]
            + budgets["max_steps"] * budgets["action_overhead_tokens"])
