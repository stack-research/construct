"""Menu-carrying foreground renderer — SPEC_EPISTEMIC_FRAME_CHECK_V1 §2.5.2/§8.3/§8.6.

Deterministic fixture → prompt rendering for v1 calibration contact: task body,
declared trigger surface, frozen ``menu_order`` presentation, inherited generic
caution (§8.3), and a neutral commitment-wire instruction (§2.5.1). No
treatment, disposition, or check-evidence content.

The hashable contract is ``efc_render_contract_v1.md``; this module is the
wire-test implementation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from harness import efc_contracts as c
from harness.efc_menu_composition_v1 import check_fixture_composition

RENDERER_ID = "efc_render_v1"
CONTRACT_RELPATH = "harness/efc_render_contract_v1.md"
PART_I_SPEC_SHA256 = (
    "2d37f6bf0cd4aab830cb1dcf5eb9576f13b9acff65b63cd7d5b5fe0ea5b6097d"
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
    "task_id",
    "population_id",
    "task_body",
    "menu_order",
    *TRIGGER_SURFACE_FIELDS,
})

# v0 §8.3/§8.4 inherited texts — byte-identical candidates re-hashed under v1.
GENERIC_CAUTION_TEXT = c.GENERIC_CAUTION_TEXT
GENERIC_CAUTION_SHA256 = c.GENERIC_CAUTION_SHA256
OFFER_PROJECTION_TEXT = c.OFFER_PROJECTION_TEXT
OFFER_PROJECTION_SHA256 = c.OFFER_PROJECTION_SHA256
V0_GENERIC_CAUTION_SOURCE = (
    "harness/efc_contracts.py::GENERIC_CAUTION_TEXT "
    "(transcribes notes/SPEC_EPISTEMIC_FRAME_CHECK_V0.md §8.3)"
)
V0_OFFER_PROJECTION_SOURCE = (
    "harness/efc_contracts.py::OFFER_PROJECTION_TEXT "
    "(transcribes notes/SPEC_EPISTEMIC_FRAME_CHECK_V0.md §8.4)"
)

_JSON_CANON = {"sort_keys": True, "separators": (",", ":"), "ensure_ascii": False}


def _canonical_template(template: dict) -> dict:
    return {k: list(v) if isinstance(v, (tuple, list)) else v
            for k, v in template.items()}


def _template_bytes(template: dict) -> bytes:
    return json.dumps(_canonical_template(template), **_JSON_CANON).encode("utf-8")


FOREGROUND_TEMPLATE_BYTES: bytes = _template_bytes({
    "template_id": "efc_foreground_template_v1",
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
})

FOREGROUND_MENU_ONLY_TEMPLATE_BYTES: bytes = _template_bytes({
    "template_id": "efc_foreground_menu_only_template_v1",
    "line_joiner": "\n",
    "section_joiner": "\n\n",
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
})


def foreground_template() -> dict:
    return json.loads(FOREGROUND_TEMPLATE_BYTES)


def menu_only_template() -> dict:
    return json.loads(FOREGROUND_MENU_ONLY_TEMPLATE_BYTES)


class RenderRefusalError(ValueError):
    """Fixture failed composition gate or lacks render-required fields."""


@dataclass(frozen=True)
class RenderResult:
    prompt: str
    sha256: str
    template_sha256: str


def foreground_template_hash(template: dict | None = None) -> str:
    if template is None:
        return hashlib.sha256(FOREGROUND_TEMPLATE_BYTES).hexdigest()
    return hashlib.sha256(_template_bytes(template)).hexdigest()


def menu_only_template_hash(template: dict | None = None) -> str:
    if template is None:
        return hashlib.sha256(FOREGROUND_MENU_ONLY_TEMPLATE_BYTES).hexdigest()
    return hashlib.sha256(_template_bytes(template)).hexdigest()


def _validate_fixture(
    fixture: dict[str, object],
    *,
    require_plausibility_attestation: bool,
) -> None:
    if not isinstance(fixture, dict):
        raise RenderRefusalError("malformed_fixture")
    missing = sorted(RENDER_REQUIRED_FIELDS - set(fixture))
    if missing:
        raise RenderRefusalError(f"missing_render_fields:{','.join(missing)}")
    comp = check_fixture_composition(
        fixture,
        require_plausibility_attestation=require_plausibility_attestation,
    )
    if not comp.ok:
        refusal = comp.refusal or "composition_refused"
        if comp.canonicalization_failure:
            refusal = f"{refusal}:{comp.canonicalization_failure}"
        raise RenderRefusalError(refusal)


def _format_trigger_surface(fixture: dict[str, object], template: dict) -> str:
    lines = []
    for field in template["declared_field_order"]:
        if field not in fixture:
            raise RenderRefusalError(f"missing_render_fields:{field}")
        lines.append(template["declared_line_format"].format(
            field=field, value=fixture[field]))
    return template["line_joiner"].join(lines)


def _format_action_set(menu_order: list[str], template: dict) -> str:
    item_fmt = template["action_item_format"]
    lines = [template["action_set_header"]]
    lines.extend(item_fmt.format(label=label) for label in menu_order)
    return template["line_joiner"].join(lines)


def action_set_block_span(prompt: str, template: dict | None = None) -> tuple[int, int]:
    """Return ``[start, end)`` byte offsets of the action-set block in ``prompt``."""
    if template is None:
        template = foreground_template()
    header = template["action_set_header"]
    start = prompt.index(header)
    next_header = template["commitment_instruction_header"]
    end = prompt.index(next_header, start)
    return start, end


def renderer_owned_region_text(template: dict) -> str:
    """Frozen renderer-owned strings checked for menu-label injection."""
    parts = [
        template.get("header_format", ""),
        template["generic_caution_header"],
        GENERIC_CAUTION_TEXT,
        template["action_set_header"],
        template["commitment_instruction_header"],
        template["commitment_instruction_text"],
    ]
    return "\n".join(part for part in parts if part)


def menu_labels_in_renderer_owned_regions(
    prompt: str,
    menu_order: list[str],
    template: dict | None = None,
) -> tuple[str, ...]:
    """Menu labels appearing in renderer-owned regions (no fixture-text scrub)."""
    if template is None:
        template = foreground_template()
    owned = renderer_owned_region_text(template)
    # Include the rendered caution/instruction slices from ``prompt`` when present.
    regions = [owned]
    caution_header = template.get("generic_caution_header")
    if caution_header and caution_header in prompt:
        start = prompt.index(caution_header)
        action_header = template["action_set_header"]
        end = prompt.index(action_header, start)
        regions.append(prompt[start:end])
    instruction_header = template["commitment_instruction_header"]
    if instruction_header in prompt:
        start = prompt.index(instruction_header)
        regions.append(prompt[start:])
    combined = "\n".join(regions)
    return tuple(label for label in menu_order if label in combined)


def render_prompt(
    fixture: dict[str, object],
    *,
    require_plausibility_attestation: bool = True,
    template: dict | None = None,
) -> RenderResult:
    """Render one calibration prompt from an attested v1 fixture."""
    if template is None:
        template = foreground_template()
    _validate_fixture(
        fixture,
        require_plausibility_attestation=require_plausibility_attestation,
    )

    menu_order = fixture["menu_order"]
    if not isinstance(menu_order, list):
        raise RenderRefusalError("malformed_fixture")

    sections = [
        template["header_format"].format(
            population_id=fixture["population_id"],
        ),
        str(fixture[template["body_field"]]),
        _format_trigger_surface(fixture, template),
        template["generic_caution_header"],
        GENERIC_CAUTION_TEXT,
        _format_action_set(menu_order, template),
        template["commitment_instruction_header"],
        template["commitment_instruction_text"],
    ]
    prompt = template["section_joiner"].join(sections)
    return RenderResult(
        prompt=prompt,
        sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        template_sha256=foreground_template_hash(template),
    )


def render_prompt_menu_only(
    fixture: dict[str, object],
    *,
    require_plausibility_attestation: bool = True,
    template: dict | None = None,
) -> RenderResult:
    """Render M_menu_only lane: action set + commitment instruction only."""
    if template is None:
        template = menu_only_template()
    _validate_fixture(
        fixture,
        require_plausibility_attestation=require_plausibility_attestation,
    )

    menu_order = fixture["menu_order"]
    if not isinstance(menu_order, list):
        raise RenderRefusalError("malformed_fixture")

    sections = [
        _format_action_set(menu_order, template),
        template["commitment_instruction_header"],
        template["commitment_instruction_text"],
    ]
    prompt = template["section_joiner"].join(sections)
    return RenderResult(
        prompt=prompt,
        sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        template_sha256=menu_only_template_hash(template),
    )


def renderer_contract_payload() -> dict:
    full_tmpl = foreground_template()
    menu_tmpl = menu_only_template()
    return {
        "renderer_id": RENDERER_ID,
        "schema_version": "efc_render_contract_v1",
        "part_i_spec_sha256": PART_I_SPEC_SHA256,
        "template": full_tmpl,
        "menu_only_template": menu_tmpl,
        "render_field_order": [
            "header",
            "task_body",
            "trigger_surface",
            "generic_caution",
            "action_set",
            "commitment_instruction",
        ],
        "menu_only_render_field_order": [
            "action_set",
            "commitment_instruction",
        ],
        "trigger_surface_fields": list(TRIGGER_SURFACE_FIELDS),
        "generic_caution_text": GENERIC_CAUTION_TEXT,
        "generic_caution_sha256": GENERIC_CAUTION_SHA256,
        "generic_caution_v0_source": V0_GENERIC_CAUTION_SOURCE,
        "offer_projection_text": OFFER_PROJECTION_TEXT,
        "offer_projection_sha256": OFFER_PROJECTION_SHA256,
        "offer_projection_v0_source": V0_OFFER_PROJECTION_SOURCE,
        "offer_projection_emitted_in_calibration_render": False,
        "commitment_wire_schema_relpath": "harness/efc_commitment_wire_v1.schema.json",
        "commitment_instruction_fields": ["commitment_enum", "optional_prose"],
        "menu_token_policy": (
            "menu labels appear only inside the action-set block; "
            "renderer-owned regions (headers, frozen caution, commitment "
            "instruction) must not contain menu labels"
        ),
        "strict_input_gate": (
            "check_fixture_composition with require_plausibility_attestation=True"
        ),
        "engine_visible_surface_disclosure_origin": "grok A1 (20260716T123515233Z)",
        "menu_only_lane": "M_menu_only",
        "menu_only_emits_generic_caution": False,
    }


def renderer_contract_hash() -> str:
    return hashlib.sha256(
        json.dumps(renderer_contract_payload(), **_JSON_CANON).encode("utf-8")
    ).hexdigest()
