# Menu composition rules contract — `efc_menu_composition_rules_v1`

**Governing seal:** `notes/SPEC_EPISTEMIC_FRAME_CHECK_V1.md`, `part_i_spec_hash` sha256
`2d37f6bf0cd4aab830cb1dcf5eb9576f13b9acff65b63cd7d5b5fe0ea5b6097d`.

**Pin target:** `action_menu_composition_rules_hash` (§2.5.6).

**Implementation:** `harness/efc_menu_composition_v1.py` (wire-test companion; not separately hashed).

This contract sits **above** `harness/efc_commitment_wire_v1.py` `validate_action_set` and
below fixture/manifest assembly. The wire validator accepts raw fixture-supplied labels;
this contract defines `canonical_action_set` normalization and composition integrity checks
that fixtures and manifests MUST pass before pin.

---

## 1. `canonical_action_set` normalization (kimi W2, grok NB2)

Given a declared `action_set` (ordered list of UTF-8 enum labels as authored):

1. **List shape:** MUST be a JSON array of 3–6 members (same bounds as §2.5.1).
2. **Label shape:** each member MUST be a non-empty UTF-8 string.
3. **Trimmed:** each label MUST equal its own `.strip()` — no leading or trailing whitespace.
4. **Non-whitespace-only:** each label's `.strip()` MUST be non-empty (whitespace-only labels
   are refused even if trim-invariant).
5. **No format / zero-width characters:** no code point with Unicode general category `Cf`
   (format) is permitted anywhere in a label. This forbids ZWSP (`U+200B`), ZWNJ (`U+200C`),
   ZWJ (`U+200D`), BOM (`U+FEFF`), word joiner (`U+2060`), and all other `Cf` characters.
6. **NFC normalize:** compute `nfc(label) = unicodedata.normalize("NFC", label)` for each member.
7. **Byte-uniqueness:** the original UTF-8 label bytes MUST be pairwise distinct across members.
8. **NFC-form uniqueness (NFC/NFD dual refusal):** the `nfc(label)` values MUST be pairwise
   distinct. If two distinct authored byte strings normalize to the same NFC form (e.g. one
   member in NFC and one in NFD of the same grapheme), the set is **refused** — no scoring
   trap, no silent coexistence.

**Output:** `canonical_action_set` is the authored list **in declaration order** after the
above checks pass. Labels are stored and hashed as authored NFC-or-not bytes; normalization
is a **refusal gate**, not a silent rewrite of label bytes at score time (§2.5.3 exact-byte
oracle unchanged).

**Refusal subcauses (machine):** `malformed_label`, `untrimmed_label`, `whitespace_only_label`,
`forbidden_format_character`, `duplicate_byte_label`, `duplicate_nfc_form`,
`action_set_too_small`, `action_set_too_large`, `malformed_action_set`.

---

## 2. Mechanical mapping rule (§2.5.5, §8.5, D6)

```text
expected_commitment_enum = mapping_rule(stratum, canonical_action_set, role_map)
```

### 2.1 Stratum → lexicon role

| `stratum` | Required lexicon role |
| --- | --- |
| `match_mismatch` | `non_commit` |
| `match_commit` | `commit` |
| `irrelevant` | `baseline` |

### 2.2 `role_map`

Each fixture carries `role_map`: a total map from every `canonical_action_set` member to
exactly one of `{non_commit, commit, baseline}`. Decoy labels are those whose role is not
selected for the fixture's stratum.

### 2.3 Role occupancy and tie-break

For a given `(stratum, canonical_action_set, role_map)`:

1. Let `R` be the lexicon role required for `stratum` (§2.1).
2. Let `L = { label ∈ canonical_action_set | role_map[label] == R }`.
3. If `L` is empty → **refuse** (`role_unoccupied`).
4. If `|L| == 1` → `mapping_rule` returns the sole member.
5. If `|L| > 1` → **hashed deterministic tie-break** (frozen in this contract):
   return the **lexicographic minimum UTF-8 label** among members of `L` (Python 3 `str`
   ordering = Unicode code-point order; for ASCII labels this matches UTF-8 byte order).

Without this declared tie-break, duplicate role occupancy would be a manifest-time refusal
(§2.5.5). This contract **declares** the tie-break; duplicate occupancy is permitted only
when the tie-break yields a unique winner.

**Tie-break id (hashed with this contract):** `lexicographic_minimum_utf8`.

### 2.4 Per-fixture machine checks (grok NB1)

At manifest/fixture validation time, for each fixture:

1. `expected_commitment_enum` MUST be a member of `canonical_action_set`
   (`expected_not_in_action_set` otherwise).
2. `expected_commitment_enum` MUST equal `mapping_rule(stratum, canonical_action_set, role_map)`
   (`expected_neq_mapping_output` otherwise).

No `expected_commitment_enum_override` field. No author exceptions.

---

## 3. Shared decoy pool (§8.6 composition pin 1)

The suite declares `shared_decoy_pool`: an ordered list of UTF-8 decoy lexemes (hashed at
manifest pin). For each fixture:

- `decoys(fixture) = canonical_action_set \ {expected_commitment_enum}`
- Every label in `decoys(fixture)` MUST be an element of `shared_decoy_pool`.

The same decoy lexemes recur across strata so menus cannot fingerpost stratum policy by
disjoint vocabulary.

**Refusal:** `decoy_not_in_shared_pool`.

---

## 4. Per-stratum plausibility review (§8.6 composition pin 2, grok NB2, kimi W5)

Decoy plausibility is a **human / cold-seat judgment**, not a machine oracle. It does not
enter the enum scorer.

### 4.1 Reviewing seat (named)

The **cold fixture reviewer** seat is:

```text
reviewer_seat = "cold_fixture_reviewer"
```

This is a human or cold agent seat distinct from the fixture author and from the
leak-audit predictor author (deliverable 4). Machine checks validate attestation **presence
and shape only** — never the plausibility verdict content.

### 4.2 Attestation record (per fixture × stratum)

Each fixture MUST carry one `plausibility_attestation` object:

```json
{
  "fixture_id": "<matches fixture>",
  "stratum": "<matches fixture stratum>",
  "reviewer_seat": "cold_fixture_reviewer",
  "reviewed_at": "<ISO-8601 UTC timestamp>",
  "attestation_id": "<opaque id>"
}
```

**Machine checks:** object present; required keys present with correct types; `fixture_id`
and `stratum` match the fixture; `reviewer_seat` equals the named seat constant.

**Refusals:** `missing_plausibility_attestation`, `malformed_plausibility_attestation`.

---

## 5. Frozen ordinal permutation and uniformity (§8.6 composition pin 4, judgment #7)

### 5.1 Per-fixture frozen permutation

Each fixture pins `menu_order`: a permutation of `canonical_action_set` (same labels, same
bytes, reorder only). No runtime re-randomization (fork identity).

The **ordinal index** of the expected enum is:

```text
ordinal_index = menu_order.index(expected_commitment_enum)   # 0-based
```

**Per-fixture refusals:** `menu_order_not_permutation`, `menu_order_unknown_label`,
`ordinal_index_out_of_range` (index ∉ [0, |action_set|)).

### 5.2 Suite ordinal uniformity — max absolute deviation (judgment #7)

Across the frozen pilot/calibration suite, record the histogram `{c_0, …, c_{k-1}}` where
`c_i` is the count of fixtures whose `ordinal_index == i`, with `k = |action_set|` (held
constant within a suite family) and `n` = suite fixture count.

Let `μ = n / k`. The suite MUST satisfy:

```text
max_i |c_i − μ| ≤ max_abs_dev(n, k)
where max_abs_dev(n, k) = ⌈n / (2k)⌉
```

This is a **chi-square-free** L∞ (max absolute deviation) bound: no distributional test, one
numeric pin. Example: `n = 5`, `k = 3` → `μ ≈ 1.67`, `max_abs_dev = ⌈5/6⌉ = 1` → each
`c_i ∈ {1, 2}`.

**Refusal:** `ordinal_uniformity_exceeded`.

A disclosed histogram is recorded at seal (§8.6); the machine check is
`check_suite_ordinal_uniformity(fixtures)` in the companion module.

---

## 6. Check-consistent member (§8.6 composition pin 5)

Satisfied by construction when §2 mapping + `role_map` are valid: the expected enum is the
stratum-appropriate commit / non-commit / baseline member.

---

## 7. Traceability

| Spec | This contract |
| --- | --- |
| §2.5.5 D6 mechanical mapping | §2 |
| §8.5 stratum → role | §2.1 |
| §8.6 composition pins 1–5 | §3–§6 |
| §9.1 mapping rule integrity | §2.4 |
| §10.6 pre-contact gates (menu surface) | ordinal + decoy pins feed integrity lanes |
| kimi W2 `canonical_action_set` | §1 |
| grok NB1 expected ∈ set + mapping | §2.4 |
| grok NB2 / kimi W5 plausibility seat | §4 |
| judgment #7 ordinal uniformity | §5.2 |
