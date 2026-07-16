# Leak-audit contract — `efc_leak_audit_v1`

**Governing seal:** `notes/SPEC_EPISTEMIC_FRAME_CHECK_V1.md`, `part_i_spec_hash`
sha256 `2d37f6bf0cd4aab830cb1dcf5eb9576f13b9acff65b63cd7d5b5fe0ea5b6097d`.

**Pin target:** `leak_audit_contract_hash` (§2.5.6).

**Implementation:** `harness/efc_leak_audit_v1.py` (pure deterministic companion).

```text
leak_audit_predictor_id: efc_leak_audit_v1
leak_audit_predictor_hash: TO-BE-COMPUTED-AT-SEAL
```

The predictor is a deliberately simple **floor**, not an adversarially optimal reader. If
even these frozen rules beat chance, the menu leaks and the family is refused. Passing this
floor does **not** prove that a stronger reader cannot exploit a leak. That residual risk
remains priced by the `M_task_menu` ceiling gate at pilot contact.

No discretionary human scoring occurs during evaluation. Human judgment is exhausted by
the §20 author/review/seal lifecycle; afterward the hashed rules below execute mechanically.

## 1. Frozen tokenization

`tokens(text)` is computed identically everywhere in this contract:

1. require `text` to be a string;
2. apply Unicode NFKC normalization;
3. apply Python `str.casefold()`;
4. scan left to right and collect each maximal non-empty run for which every code point
   satisfies Python `str.isalnum()`;
5. return the runs in encounter order. Punctuation, symbols, underscores, whitespace, and
   format characters are separators. There is no stemming, synonym expansion, substring
   matching, model call, corpus lookup, or learned weight.

## 2. Predictor legs

Both functions require an ordered `action_set` of 3–6 distinct non-empty string labels.
For evaluation, this ordered input is the fixture's frozen presented `menu_order` (which D3
already requires to be a permutation of `canonical_action_set`). The predictor receives the
ordered labels only, not the surrounding fixture object.

### 2.1 L1 — menu only

Signature:

```text
predict_menu_only(action_set_ordering) -> commitment_enum
```

Procedure: return `action_set_ordering[0]` exactly as authored. This is an ordinal-position
floor. The signature contains no task body, stratum, expected enum, treatment path, check
evidence, disposition state, or oracle field.

### 2.2 L2 — task plus menu

Signature:

```text
predict_task_menu(task_body_text, action_set_ordering) -> commitment_enum
```

Procedure:

1. Let `T` be the set of `tokens(task_body_text)`.
2. For each menu label `a`, let `score(a) = |set(tokens(a)) ∩ T|`.
3. Return the label with maximum score.
4. Resolve every tie by the lowest zero-based position in `action_set_ordering`.

The signature structurally excludes stratum, expected enum, treatment path, check evidence,
disposition state, and oracle fields. L2 is intentionally only an exact normalized-token
overlap floor; it is not a semantic classifier.

## 3. Canonical predictor serialization

`leak_audit_predictor_hash` is computed at seal, never during authoring, as sha256 over the
UTF-8 bytes of canonical JSON returned by `canonical_predictor_spec_bytes()` in the companion:
sorted object keys, `ensure_ascii=false`, separators `(',', ':')`, and no trailing newline.
The serialized object contains the version, predictor id, tokenization steps, both frozen
procedures, tie-break, and input/forbidden-field declarations. Its hash remains
`TO-BE-COMPUTED-AT-SEAL` until the operator's pin event.

## 4. Frozen-suite evaluation

Each fixture supplied to `evaluate_leak_audit` must contain exactly the following audit
inputs/truth fields (additional fixture fields may exist but are ignored):

- `fixture_id`: non-empty string;
- `stratum`: one of `match_mismatch`, `match_commit`, `irrelevant`;
- `task_body`: string;
- `menu_order`: ordered list of 3–6 distinct non-empty string enum labels;
- `expected_commitment_enum`: a member of `menu_order`;
- the sealed §2.1 trigger-conjunct fields: `assertion_basis_kind`,
  `observation_boundary_present`, `source_reference_present`, and
  `decision_scope_present`;
- `trigger_feature_strings`: the non-empty frozen projection defined by §5 (used only by
  §5 validation and checking, never as a predictor input to L1 or L2).

All fixtures in one evaluated suite must use the same action-set size `k`. Every target
stratum must be non-empty. For each leg and stratum:

```text
accuracy = correct_predictions / fixture_count
fail_threshold = 1 / k + 0.10
```

The leg/stratum fails iff `accuracy > fail_threshold` (strict greater-than). Equality passes.
Any failed cell emits the exact refusal `leak_audit_fail(<leg>, <stratum>)`, where `<leg>` is
`L1` or `L2`. Any such failure yields `confounded(menu_leak)` and refuses Part II. Results
record fixture id, prediction, expected enum, correctness, numerator, denominator, exact
accuracy, threshold, and per-cell refusal. Evaluation order is fixed as L1 then L2, and
within each leg as `match_mismatch`, `match_commit`, `irrelevant`; fixture input order is
preserved.

Malformed suite input is refused before accuracy scoring with one of:
`malformed_fixture_suite`, `malformed_fixture`, `unknown_stratum`,
`mixed_action_set_size`, `empty_stratum`, `expected_not_in_action_set`,
`empty_trigger_projection`, or `trigger_projection_mismatch`.

## 5. No lexical marking from trigger features (grok-D3-NB2)

`project_trigger_feature_strings(fixture)` is the only authorized population rule for
`trigger_feature_strings`. It reads the four sealed §2.1 conjunct fields through
`extract_trigger_features` and, in this fixed order, projects one string per conjunct:

1. `assertion_basis_kind` + its declared string value;
2. `observation_boundary_present` + lowercase `true` or `false`;
3. `source_reference_present` + lowercase `true` or `false`;
4. `decision_scope_present` + lowercase `true` or `false`.

For each pair, the field name and value are separated by one space, passed through the
frozen §1 tokenizer, and the resulting tokens are joined by one ASCII space. Thus, for
example, `assertion_basis_kind == cited_source` projects to
`assertion basis kind cited source`. The projection is pure, deterministic, ordered, and
contains exactly four non-empty members for a valid sealed trigger surface.

D5 fixtures **MUST** carry that exact projection as `trigger_feature_strings`. An empty
declared projection or empty computed projection refuses as `empty_trigger_projection`;
any declared value differing from the computed projection refuses as
`trigger_projection_mismatch`. Fixture authors have no free string field on this surface.

After that binding check, compute `E = set(tokens(expected_commitment_enum))`. For every
projected string `s`, compute `F_s = set(tokens(s))`. The fixture passes iff `E ∩ F_s` is
empty for every `s`. Any non-empty overlap emits
`no_lexical_marking_fail(fixture_id)` and records the sorted overlapping tokens.

The expected-only comparison is a disclosed, threat-aligned reading of sealed “no
`action_set` member”: it prevents the winning enum from being derivable from the trigger
conjuncts alone; it does not reject overlap confined to a non-winning decoy. This check closes
§8.6 composition pin 3 only at the literal normalized-token level and does not prove absence
of deeper semantic marking. Deeper task×menu semantic risk is covered only by the L2 floor and
the pilot gates, including the `M_task_menu` ceiling gate.

At the integrity gate, D6/manifest **MUST run both** `evaluate_leak_audit` and
`check_no_lexical_marking`; passing either sibling call alone is insufficient.

## 6. Purity and determinism

The companion performs no I/O, mutation, randomness, clock access, environment lookup,
network/model call, or discretionary scoring. Repeating a call with equal values produces an
equal frozen result. Treatment/check-evidence/disposition inputs cannot be passed to either
predictor because they are absent from its Python signature; doing so raises `TypeError`.
