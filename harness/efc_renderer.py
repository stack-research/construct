"""Frozen foreground renderer — SPEC_EPISTEMIC_FRAME_CHECK_V0 §8.2-§8.4/§13;
EFC_CALIBRATION_PACKET_DESIGN §4.3.

Fork identity is the load-bearing invariant: the foreground is built ONCE per
fixture identity, and lanes/legs differ only by the declared treatment
insertion (§13). The renderer is deterministic — same fixture bytes, same
foreground bytes — so untrusting replay can recompute the foreground hash.

Field discipline (design §4.3): the rendered surface carries the four §2.1
trigger fields plus `source_reference`, `decision_scope`, and
population-pinned metadata. Dispositive scope content lives only in pinned
world-oracle snapshots and check inputs; any `required_scope`-equivalent,
answer, or outcome field in the rendering input is refused, never dropped
silently.

Template identity (B4): the template is canonical declarative DATA —
`FOREGROUND_TEMPLATE` — and `foreground_template_hash()` hashes those exact
canonical bytes, so any change to the template's structure changes the hash.
The rendering code consumes the data; the module-source hash is a separate,
diagnostic identity and never substitutes for the semantic one.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from harness import efc_contracts as c
from harness.efc_trigger import (ORACLE_AND_OUTCOME_FIELDS, TRIGGER_FIELDS,
                                 extract_trigger_features, trigger_fires)

RENDERER_ID = "efc_renderer_v0"

# design §4.3: exactly this rendering surface, nothing else.
RENDER_FIELDS = (*TRIGGER_FIELDS, "source_reference", "decision_scope")
METADATA_FIELDS = ("task_id", "population_id", "surface_text")
ALLOWED_RENDER_INPUT = frozenset({*RENDER_FIELDS, *METADATA_FIELDS, "stratum"})

# resolution G: the evidence/treatment insertion point is structural — one
# insertion function, one placement — and the contracts say so by name.
PLACEBO_POSITION_GATE = "structural_single_insertion_point"


def _canonical_template(template) -> dict:
    return {k: list(v) if isinstance(v, (tuple, list)) else v
            for k, v in template.items()}


# The frozen template as declarative data (B4). Resolution G: the CANONICAL
# identity is these exact immutable bytes; readers get a fresh copy per read
# (`foreground_template()`), so no alias can mutate shared state behind the
# stable hash, and render time re-verifies the hash a foreground was built
# under.
FOREGROUND_TEMPLATE_BYTES: bytes = json.dumps({
    "template_id": "efc_foreground_template_v0",
    "header_format": "[task {task_id} | population {population_id}]",
    "body_field": "surface_text",
    "declared_field_order": list(RENDER_FIELDS),
    "declared_line_format": "{field}: {value}",
    "line_joiner": "\n",
    "treatment_joiner": "\n\n",
    "evidence_header": "[external check evidence]",
    "treatment_placement": "appended_after_foreground",
}, sort_keys=True, separators=(",", ":")).encode("utf-8")


def foreground_template() -> dict:
    """Copy-on-read of the canonical template bytes: every caller gets its
    own structure; mutating it cannot touch the canonical identity."""
    return json.loads(FOREGROUND_TEMPLATE_BYTES)


class RendererContractError(ValueError):
    """Rendering input outside the §4.3 field discipline. Fail-closed."""


@dataclass(frozen=True)
class Foreground:
    fixture_id: str
    text: str
    sha256: str
    trigger_fires: bool
    template_sha256: str  # the template identity this foreground was built under


def canonical_tokens(text: str) -> list[str]:
    """Canonical token count used by the ±5 placebo gate (§7/§8.2) and the
    budget derivation: whitespace tokens, empty tokens dropped."""
    return [t for t in text.split() if t]


def build_foreground(fixture: dict, template: dict | None = None) -> Foreground:
    """Deterministic, once-per-identity foreground build from the declarative
    template data.

    `stratum` is tolerated on the fixture object (it is scorer-side routing,
    design §4.2) but never rendered. Every other unknown or forbidden field
    refuses the build.
    """
    if template is None:
        template = foreground_template()
    forbidden = sorted(set(fixture) & ORACLE_AND_OUTCOME_FIELDS - {"stratum"})
    if forbidden:
        raise RendererContractError(
            f"fixture {fixture.get('task_id')!r} carries forbidden foreground "
            f"fields {forbidden}: dispositive scope/outcome content lives only "
            "in pinned snapshots and check inputs (design §4.3)")
    unknown = sorted(set(fixture) - ALLOWED_RENDER_INPUT)
    if unknown:
        raise RendererContractError(
            f"fixture {fixture.get('task_id')!r} carries undeclared fields "
            f"{unknown}: the rendering surface is closed (design §4.3)")
    missing = [f for f in (*RENDER_FIELDS, *METADATA_FIELDS) if f not in fixture]
    if missing:
        raise RendererContractError(
            f"fixture {fixture.get('task_id')!r} lacks rendering fields "
            f"{missing}")
    features = extract_trigger_features(fixture)
    lines = [template["header_format"].format(
        task_id=fixture["task_id"], population_id=fixture["population_id"]),
        str(fixture[template["body_field"]])]
    for field in template["declared_field_order"]:
        lines.append(template["declared_line_format"].format(
            field=field, value=fixture[field]))
    text = template["line_joiner"].join(lines)
    return Foreground(
        fixture_id=str(fixture["task_id"]), text=text,
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        trigger_fires=trigger_fires(features),
        template_sha256=foreground_template_hash(template))


def foreground_template_hash(template: dict | None = None) -> str:
    """Semantic identity of the frozen template DATA (§3.2 envelopes, §5.2
    manifest field). With no argument, this hashes EXACTLY the canonical
    bytes (resolution G). Handed a structure, it recomputes from that exact
    structure — an alias mutated after hashing yields a different hash,
    never stale behavior behind a stable one."""
    if template is None:
        return hashlib.sha256(FOREGROUND_TEMPLATE_BYTES).hexdigest()
    return hashlib.sha256(json.dumps(_canonical_template(template),
                                     sort_keys=True, separators=(",", ":")
                                     ).encode("utf-8")).hexdigest()


def renderer_contract_payload() -> dict:
    """Typed renderer contract (B4): template data plus the closed field
    discipline."""
    return {
        "renderer_id": RENDERER_ID,
        "schema_version": "efc_renderer_contract_v1",
        "template": foreground_template(),
        "render_fields": list(RENDER_FIELDS),
        "metadata_fields": list(METADATA_FIELDS),
        "forbidden_fields": sorted(ORACLE_AND_OUTCOME_FIELDS - {"stratum"}),
        "generic_caution_sha256": c.GENERIC_CAUTION_SHA256,
        "offer_projection_sha256": c.OFFER_PROJECTION_SHA256,
        # resolution G: relevant and placebo evidence share one structural
        # insertion point (render_evidence_block, appended once)
        "placebo_position_gate": PLACEBO_POSITION_GATE,
    }


def renderer_contract_hash() -> str:
    return hashlib.sha256(json.dumps(renderer_contract_payload(),
                                     sort_keys=True, separators=(",", ":")
                                     ).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Lane/leg treatment insertion (§7 legs, §8.2 lanes, §8.3/§8.4 frozen texts).
# ---------------------------------------------------------------------------

def render_evidence_block(evidence_text: str,
                          template: dict | None = None) -> str:
    """THE single structural insertion point for evidence-shaped treatments
    (relevant check evidence and pinned placebo objects alike) — the
    `placebo_position_gate` contract (resolution G)."""
    if template is None:
        template = foreground_template()
    return f"{template['evidence_header']}\n{evidence_text}"


def render_prompt(foreground: Foreground, lane_or_leg: str,
                  evidence_text: str | None = None,
                  template: dict | None = None) -> str:
    """Insert only the declared treatment. The base foreground bytes are the
    identity-shared prefix in every lane/leg (§13 fork identity)."""
    if template is None:
        template = foreground_template()
    if lane_or_leg not in c.LANES and lane_or_leg not in c.SOURCE_LEGS:
        raise RendererContractError(f"unknown lane/leg {lane_or_leg!r}")
    # item G: the treatment template must be the exact structure the
    # foreground was built under — a mutated alias cannot ride a stale hash
    if foreground_template_hash(template) != foreground.template_sha256:
        raise RendererContractError(
            "template identity mismatch: render-time template differs from "
            "the template the foreground was built under (item G)")
    parts = [foreground.text]
    if lane_or_leg in ("S0_no_check", "B_inactive"):
        if evidence_text is not None:
            raise RendererContractError(
                f"{lane_or_leg} takes no evidence insertion")
    elif lane_or_leg in ("S1_relevant_check", "S2_placebo",
                         "C_controlled_check", "P_placebo", "A_always_check"):
        if evidence_text is None:
            # C/P are silent on non-firing fixtures; A always carries evidence
            if lane_or_leg == "A_always_check":
                raise RendererContractError(
                    "A_always_check must carry check evidence on every task")
            if lane_or_leg in ("S1_relevant_check", "S2_placebo"):
                raise RendererContractError(
                    f"{lane_or_leg} requires its declared evidence condition")
        else:
            parts.append(render_evidence_block(evidence_text, template))
    elif lane_or_leg == "G_generic_caution":
        if evidence_text is not None:
            raise RendererContractError("G_generic_caution takes no evidence")
        parts.append(c.GENERIC_CAUTION_TEXT)
    elif lane_or_leg == "O_offer_projection":
        if evidence_text is not None:
            raise RendererContractError("O_offer_projection takes no evidence")
        # §8.4: offered only when the same frozen trigger fires
        if foreground.trigger_fires:
            parts.append(c.OFFER_PROJECTION_TEXT)
    return template["treatment_joiner"].join(parts)
