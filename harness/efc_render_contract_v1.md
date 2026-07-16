# Rendering contract — `efc_render_v1`

**Governing seal:** `notes/SPEC_EPISTEMIC_FRAME_CHECK_V1.md`, `part_i_spec_hash`
sha256 `2d37f6bf0cd4aab830cb1dcf5eb9576f13b9acff65b63cd7d5b5fe0ea5b6097d`.

**Pin targets:** `renderer_id`, `foreground_template_hash`,
`menu_only_template_hash`, `renderer_contract_hash` (§3.2 validity envelope,
§5.2 manifest).

**Implementation:** `harness/efc_render_v1.py` (pure deterministic companion).

```text
renderer_id: efc_render_v1
foreground_template_hash: TO-BE-COMPUTED-AT-SEAL
menu_only_template_hash: TO-BE-COMPUTED-AT-SEAL
renderer_contract_hash: TO-BE-COMPUTED-AT-SEAL
```

## 1. Scope

v1 calibration rendering emits **two** scored foreground modes per attested
fixture:

### 1.1 Full calibration render (`render_prompt`)

- population header (no fixture or task identifier);
- task body;
- declared trigger-surface presentation (§2.1 fields plus `source_reference` and
  `decision_scope` values — same closed surface discipline as v0 foreground);
- the frozen §8.3 generic-caution text (byte-identical v0 candidate);
- the action menu in **exactly** the fixture's frozen `menu_order`;
- a neutral commitment-wire instruction eliciting the pinned schema shape
  (`harness/efc_commitment_wire_v1.schema.json`).

### 1.2 Menu-only render (`render_prompt_menu_only`) — lane `M_menu_only`

- the action menu in **exactly** the fixture's frozen `menu_order`;
- the same neutral commitment-wire instruction.

**Excluded from menu-only render:** task body, trigger surface, generic caution,
population header, and every other section. Generic caution is omitted because
caution alone solicits the provenance tool and would confound the
`M_menu_only` checking-rate gate at §10.6.1.

**Excluded from both modes:** treatment insertions, disposition prose,
check-evidence blocks, offer-projection insertion (§8.4 comparator lane only),
oracle/outcome fields, and any per-fixture expected-enum hint.

## 2. Engine-visible surface vs leak-audit surface

**Origin:** grok cold review A1 (`20260716T123515233Z__cursor/grok-4.5.md`).

The assembled full-render prompt (header, task body, trigger surface, generic
caution, action set, commitment instruction) is a **strictly larger** surface
than the L1/L2 leak-audit inputs (`task_body` + `action_set_ordering` per
§8.6). The trigger surface **necessarily** encodes stratum by experimental
design — strata are defined over it. This residual under-approximation relative
to the leak audit is **priced** by the `M_task_menu` ceiling gate at pilot
contact, which sees the **full** rendered prompt.

**Fixture-identifier policy (moderator ruling on A1, option ii + disclosure):**
`task_id` and `fixture_id` are **removed** from every engine-visible rendered
region. The scored foreground carries **no** fixture identifier; the runner
correlates episodes via out-of-band request metadata, never prompt text.

## 3. Inherited texts (byte-identity claim)

| Text | v0 source | v0 sha256 (UTF-8) | Emitted in calibration render |
| --- | --- | --- | --- |
| Generic caution §8.3 | `harness/efc_contracts.py::GENERIC_CAUTION_TEXT` transcribing `notes/SPEC_EPISTEMIC_FRAME_CHECK_V0.md` §8.3 | `b25af70799fad818b054781a56851504369fe35d8e1cb0534ed8ada29b46e877` | **yes** (full render only) — verbatim between `[generic caution]` header and action set |
| Offer projection §8.4 | `harness/efc_contracts.py::OFFER_PROJECTION_TEXT` transcribing `notes/SPEC_EPISTEMIC_FRAME_CHECK_V0.md` §8.4 | `e62ae334735ece7e87f853abc48f880c1e3978f0fe48208388bc95e24704642b` | **no** — recorded in contract payload for v1 re-hash; comparator lanes insert it later |

Both strings are re-hashed under this v1 contract at seal; candidate-stable if
byte-identical to v0.3.

## 4. Field order and joiners

Sections are joined with `\n\n` (`section_joiner`). Within a section, lines use
`\n` (`line_joiner`).

### 4.1 Full render

| # | Section | Source |
| --- | --- | --- |
| 1 | Header | `[population {population_id}]` — **no** `task_id` or `fixture_id` |
| 2 | Task body | fixture `task_body` |
| 3 | Trigger surface | one `{field}: {value}` line per field in order: `assertion_basis_kind`, `observation_boundary_present`, `source_reference_present`, `decision_scope_present`, `source_reference`, `decision_scope` |
| 4 | Generic caution | header `[generic caution]` then §8.3 text verbatim |
| 5 | Action set | header `[action set]` then one `- {label}` line per fixture `menu_order` entry **in list order** |
| 6 | Commitment instruction | header `[commitment response]` then frozen instruction text |

### 4.2 Menu-only render

| # | Section | Source |
| --- | --- | --- |
| 1 | Action set | header `[action set]` then one `- {label}` line per fixture `menu_order` entry **in list order** |
| 2 | Commitment instruction | header `[commitment response]` then frozen instruction text |

Boolean trigger fields render as Python `str(bool)` (`True` / `False`) in the
full render only.

## 5. Frozen commitment instruction

Exact UTF-8 text (no placeholders, no menu labels):

```text
Respond with a JSON object containing exactly one required field "commitment_enum" whose value must be exactly one action label listed in the action set above. You may include an optional string field "optional_prose"; it is never scored. No other top-level fields are permitted.
```

Requirements (§2.5.1):

- names the wire fields `commitment_enum` and `optional_prose` matching the pinned schema;
- does **not** name, hint at, or favor any particular action label;
- does **not** repeat any menu label token outside the action-set block.

## 6. Menu-token policy

Each label in fixture `menu_order` MUST appear in the rendered prompt **only**
inside the `[action set]` block (from its header through the line before
`[commitment response]`). The instruction section references "the action set
above" without embedding label strings.

Conformance checks assert menu labels are **absent** from renderer-owned
regions only: section headers, the frozen generic-caution body, and the frozen
commitment-instruction text. Fixture-authored text (`task_body`, trigger-field
values) is **not** scrubbed before the check — incidental substring overlap in
authored content is not a renderer injection.

## 7. Strict input gate

Before rendering, the implementation MUST run
`check_fixture_composition(fixture, require_plausibility_attestation=True)`.
Any refusal (missing/malformed attestation, composition failure) is a render
refusal — fail-closed, no partial prompt.

## 8. Determinism guarantee

For fixed canonical template bytes and fixed attested fixture bytes, each render
mode returns byte-identical UTF-8 prompt text and an identical sha256 on every
call. Template identity is the immutable `FOREGROUND_TEMPLATE_BYTES` and
`FOREGROUND_MENU_ONLY_TEMPLATE_BYTES` objects; `foreground_template_hash()` and
`menu_only_template_hash()` hash those exact bytes.

## 9. Canonical template serialization

`foreground_template_hash`, `menu_only_template_hash`, and
`renderer_contract_hash` are sha256 over UTF-8 canonical JSON: sorted object
keys, `ensure_ascii=false`, separators `(',', ':')`, no trailing newline. The
implementation uses `ensure_ascii=False` in all canonical dumps (A4 alignment).
