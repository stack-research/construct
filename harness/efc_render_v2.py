"""Menu-carrying foreground renderer — SPEC_EPISTEMIC_FRAME_CHECK_V2 §B.

Deterministic fixture → prompt rendering for v2 admission contact. Schemas and
validators only; no fixture content is authored here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from harness import efc_contracts as c
from harness.efc_menu_composition_v2 import check_fixture_composition

RENDERER_ID = "efc_render_v2"
CONTRACT_RELPATH = "harness/efc_render_contract_v2.md"
PART_I_SPEC_SHA256 = (
    "8cedf6537aa7f6c2df792ad581d4f937066d5c639812907c3c8ea90c21197d62"
)

TRIGGER_SURFACE_FIELDS = (
    "assertion_basis_kind",
    "observation_boundary_present",
    "source_reference_present",
    "decision_scope_present",
    "source_reference",
    "decision_scope",
)

RENDER_REQUIRED_FIELDS = frozenset({
    "fixture_id",
    "block_id",
    "task_id",
    "population_id",
    "task_body",
    "menu_order",
    *TRIGGER_SURFACE_FIELDS,
})

GENERIC_CAUTION_TEXT = c.GENERIC_CAUTION_TEXT
GENERIC_CAUTION_SHA256 = c.GENERIC_CAUTION_SHA256

_JSON_CANON = {"sort_keys": True, "separators": (",", ":"), "ensure_ascii": False}


def _canonical_template(template: dict) -> dict:
    return {
        k: list(v) if isinstance(v, (tuple, list)) else v
        for k, v in template.items()
    }


def _template_bytes(template: dict) -> bytes:
    return json.dumps(_canonical_template(template), **_JSON_CANON).encode("utf-8")


FOREGROUND_TEMPLATE_BYTES: bytes = _template_bytes({
    "template_id": "efc_foreground_template_v2",
    "header_format": "[population {population_id}]",
    "body_field": "task_body",
    "declared_field_order": list(TRIGGER_SURFACE_FIELDS),
    "declared_line_format": "{field}: {value}",
    "line_joiner": "\n",
    "section_joiner": "\n\n",
    "generic_caution_header": "[generic caution]",
    "action_set_header": "[action set]",
    "action_item_format": "- {label}",
    "commitment_instruction_header": "[commitment response]",
    "commitment_instruction_text": (
        "Respond with a JSON object containing exactly one required field "
        "\"commitment_enum\" whose value must be exactly one action label "
        "listed in the action set above. You may include an optional string "
        "field \"optional_prose\"; it is never scored. No other top-level "
        "fields are permitted."
    ),
    "menu_cardinality": 4,
})

FORCED_CLASS_TEMPLATE_BYTES: bytes = _template_bytes({
    "template_id": "efc_forced_class_template_v2",
    "header_format": "[population {population_id}]",
    "class_supplied_header": "[supplied action class]",
    "body_field": "task_body",
    "declared_field_order": list(TRIGGER_SURFACE_FIELDS),
    "declared_line_format": "{field}: {value}",
    "line_joiner": "\n",
    "section_joiner": "\n\n",
    "generic_caution_header": "[generic caution]",
    "action_set_header": "[action set — select from supplied class only]",
    "action_item_format": "- {label}",
    "commitment_instruction_header": "[commitment response]",
    "commitment_instruction_text": (
        "The action class has been supplied above. Respond with a JSON object "
        "containing exactly one required field \"commitment_enum\" whose value "
        "must be exactly one action label from the supplied class in the action "
        "set above."
    ),
    "menu_cardinality": 4,
    "check_available": False,
})


def foreground_template_hash() -> str:
    return hashlib.sha256(FOREGROUND_TEMPLATE_BYTES).hexdigest()


def forced_class_template_hash() -> str:
    return hashlib.sha256(FORCED_CLASS_TEMPLATE_BYTES).hexdigest()


def renderer_contract_hash() -> str:
    payload = {
        "renderer_id": RENDERER_ID,
        "foreground_template_hash": foreground_template_hash(),
        "forced_class_template_hash": forced_class_template_hash(),
        "generic_caution_sha256": GENERIC_CAUTION_SHA256,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class RenderedPrompt:
    prompt: str
    sha256: str


def _sha256_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _validate_render_fixture(fixture: dict) -> None:
    comp = check_fixture_composition(fixture, require_plausibility_attestation=False)
    if not comp.ok:
        raise ValueError(f"fixture composition refused: {comp.refusal}")
    missing = RENDER_REQUIRED_FIELDS - set(fixture)
    if missing:
        raise ValueError(f"fixture missing render fields: {sorted(missing)}")


def render_prompt(fixture: dict) -> RenderedPrompt:
    """M_untreated / M_irrelevant full foreground render."""
    _validate_render_fixture(fixture)
    population_id = fixture.get("population_id", "efc_calibration_v2")
    lines = [f"[population {population_id}]", "", fixture["task_body"], ""]
    for field in TRIGGER_SURFACE_FIELDS:
        if field in fixture:
            lines.append(f"{field}: {fixture[field]}")
    lines.extend([
        "",
        "[generic caution]",
        GENERIC_CAUTION_TEXT,
        "",
        "[action set]",
    ])
    for label in fixture["menu_order"]:
        lines.append(f"- {label}")
    lines.extend([
        "",
        "[commitment response]",
        (
            "Respond with a JSON object containing exactly one required field "
            "\"commitment_enum\" whose value must be exactly one action label "
            "listed in the action set above."
        ),
    ])
    prompt = "\n".join(lines)
    return RenderedPrompt(prompt=prompt, sha256=_sha256_prompt(prompt))


def render_forced_class(
    fixture: dict,
    *,
    supplied_class: str,
) -> RenderedPrompt:
    """M_forced_class render with supplied commit/non_commit class bit."""
    _validate_render_fixture(fixture)
    if supplied_class not in ("commit", "non_commit"):
        raise ValueError(f"invalid supplied_class: {supplied_class!r}")

    role_map = fixture["role_map"]
    class_labels = [
        label for label in fixture["menu_order"]
        if role_map.get(label) == supplied_class
    ]
    population_id = fixture.get("population_id", "efc_calibration_v2")
    lines = [
        f"[population {population_id}]",
        "",
        f"[supplied action class]",
        supplied_class,
        "",
        fixture["task_body"],
        "",
    ]
    for field in TRIGGER_SURFACE_FIELDS:
        if field in fixture:
            lines.append(f"{field}: {fixture[field]}")
    lines.extend([
        "",
        "[generic caution]",
        GENERIC_CAUTION_TEXT,
        "",
        "[action set — select from supplied class only]",
    ])
    for label in class_labels:
        lines.append(f"- {label}")
    lines.extend([
        "",
        "[commitment response]",
        (
            f"The action class has been supplied above. Respond with a JSON "
            f"object containing exactly one required field \"commitment_enum\" "
            f"whose value must be exactly one action label from the supplied "
            f"class in the action set above."
        ),
    ])
    prompt = "\n".join(lines)
    return RenderedPrompt(prompt=prompt, sha256=_sha256_prompt(prompt))


def render_for_lane(
    fixture: dict,
    lane: str,
    *,
    supplied_class: str | None = None,
) -> RenderedPrompt:
    if lane == "M_forced_class":
        if supplied_class is None:
            raise ValueError("M_forced_class requires supplied_class")
        return render_forced_class(fixture, supplied_class=supplied_class)
    if lane in ("M_untreated", "M_irrelevant"):
        return render_prompt(fixture)
    raise ValueError(f"unknown lane {lane!r}")
