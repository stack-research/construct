# EFC_TRACEABILITY — §14 build traceability matrix

Status: build artifact, 2026-07-12; **amended same day for the §18 v0.2 fold**
(see the amendment section below). Maps every implemented function and test
of the epistemic-frame-check §14 calibration/scorer preparation to the sealed
section it serves (`notes/SPEC_EPISTEMIC_FRAME_CHECK_V0.md`, v0.2 sha256
`5b41d866ce411c170997af5be08e98db3d725c48a4f3e913455414181088118f`, recorded
in `epistemic-frame-check-v0-build`; the v0.1 seal hash `736d46cf...c5d8`
remains recorded in `epistemic-frame-check-v0-review` as lineage).

Scope discipline (build instruction from gpt-5.6-sol, design seat): §14
preparation only — shared planner/verdict interval functions first, wire
machinery second, stop at the computed calibration gate. **No held-out
fixtures, no real-engine contact, no mechanism claim.** Mock rows in the test
suite check wiring and are never evidence (§1). Nothing below licenses a
mechanism.

Run: `make efc-test`.

## Build finding 1 — the sealed NI width target is unmeetable at n_max (§10.3 × §10.4)

Found during planner construction, before any fixture or engine contact.

- The §10.3 pin `quality non-inferiority CI target half-width = 0.10` is
  checked by the §10.4 rule through the shared score-time Newcombe function.
- At `n_max = 24` and 95%, the minimum achievable Newcombe half-width over
  ALL 625 possible count configurations is **0.09756, reached only at the two
  total anti-correlated collapses** (24/24 vs 0/24 and 0/24 vs 24/24). The
  best coherent configuration (both arms equal, zero failures) achieves
  **0.13798 > 0.10**. First N whose perfect-agreement width fits 0.10 is
  **N = 35**.
- The two feasible configurations require the comparator lane (B on its own
  baseline tasks; A the always-check lane) to score 0.00 from an engine that
  simultaneously clears the §6 `S1 >= 0.80` band — incoherent with the very
  cells the NI gates price (§9.2.3/§9.2.4/§9.2.5, §9.3 preconditions).
- Consequence: for every coherent calibration pilot, at least one required NI
  contrast has `n_required > 24`, and §10.4 fires verbatim:
  `confounded(ci_target_unmet)`, Part II fixture authoring refused. **The
  computed calibration gate, built exactly to seal, cannot emit
  `engine_admitted` on the sealed board.**
- Pinned in `tests/test_efc_planner.py::test_ni_width_target_unreachable_for_coherent_pilots`
  (the exact two-point sliver) and
  `::test_structural_refusal_on_the_sealed_board` (healthy engine, coherent
  pilots, valid region → `confounded(ci_target_unmet)`).
- History note, kept per lineage discipline: the first in-build statement of
  this finding overclaimed ("unreachable for ALL pilots", from the equal-arms
  floor 0.13798). The planner's own test run surfaced the two-point sliver
  and the claim was corrected the same hour. Machinery-first ordering did its
  job on its builder.
- §17.1 relation: the cold-review fold made width targets contrast-specific
  and disclosed a "refusal-dominated band"; nobody enumerated the
  achievability floor at `n_max`. This finding is that enumeration. The
  disclosure said "can make the instrument refusal-dominated"; the arithmetic
  says "does, for every coherent pilot".
- Remedies were all seal amendments and were NOT applied by the build alone
  (§16: no silent amendment). **Resolution:** the room ran the §10.4
  versioned-redesign path same day in `epistemic-frame-check-v0-build` —
  designer (gpt-5.6-sol) chose the raise-the-ceiling remedy, moderator (dan)
  green-lit, and the §18 v0.2 amendment below was applied openly.

## Module → sealed section

### harness/efc_intervals.py — shared interval functions (§10.4 "same
interval function" requirement; no closed-form z approximation anywhere)

| Function | Section served |
| --- | --- |
| `norm_ppf` (AS241/PPND16) | §9.2/§9.3 confidence levels; §10.4 Wilson/Newcombe components |
| `betainc_reg`, `t_cdf`, `t_ppf` (bisection inversion) | §10.4 Welch at N-dependent Welch–Satterthwaite df |
| `wilson_interval` (continuous successes) | §9.2/§10.4 binary component intervals; §10.4 zero-variance guard |
| `newcombe_diff_interval` | §9.2/§9.3 quality differences ("95% Newcombe lower bound") |
| `welch_interval` (+ `DegenerateVarianceError`) | §9.3 efficiency cost; §9.4 stratum bounds; §10.4 scalar-cost rule |
| `sample_mean`, `sample_sd` (ddof=1) | shared summaries for §9.4/§10.4 cost inputs |
| `simultaneous_stratum_lower_bounds` | §9.4 Bonferroni 1−0.05/m two-sided Welch family — the ONE function planner and scorer share |
| `linear_prevalence_sum` | §9.4/§12 linear saving surfaces; vertex sufficiency |
| `half_width` | §10.3 CI target half-widths (definition: (upper−lower)/2, see decisions) |

### harness/efc_contracts.py — pinned constants (§16: changing any value is a spec change)

Seal identity (§5.1), §10.3 effects, §9.2/§9.3 margins and confidences,
§6/§7 bands, §10.1 ceilings, §10.2 sampling contract, §10.5 stop-rule id,
§7/§8.2 placebo tolerance, lane/leg/stratum vocabularies (§8.2/§7/§8.5),
frozen §8.3/§8.4 texts + UTF-8 hashes, §3.1/§3.4 status and revision scopes,
§5.3/§9.5/§10.4 verdict vocabularies, §13 row vocabulary (+
`untrusted_nomination` per §3.3).

### harness/efc_planner.py — §10.4 N-rule + §6/§5.3 computed calibration gate

| Function | Section served |
| --- | --- |
| `planned_gates`, `_sup`/`_ni`/`_population`, `AllOf`/`AnyOf` | §7 mint contrasts; §9.2 gates 1–5; §9.3 preconditions + OR arms; §9.4 population cost — the precommitted board |
| `n_required_binary` | §10.4 enumeration 2..128 through score-time Wilson/Newcombe at the gate's actual confidence and contrast-specific h |
| `n_required_cost` | §10.4 scalar-cost bullet (shared Welch, W-S df) |
| `n_required_population`, `validate_prevalence_region`, `_project_population_at_n` | §9.4 vertex conditions + p_irrelevant > 0 refusal; §12 construction reuse for §9.3 arms |
| `resolve_gates` (AND→max, OR→min, decision-bearing arms) | §6 "every required comparison"; §0.2 separately-precommitted comparisons; §10.2 stratum-N equalization |
| `calibration_band_failures` | §6 S0/S1/S2 admission bands (point estimates) |
| `IgnoranceProbeResult.failure` | §6 ignorance-probe band under the §5.2 manifest-pinned contract |
| `detect_collapse`, `CollapseState` | §10.2 answer/route-hash collapse and the single declared T=0.7 probe |
| `projected_counts` | §10.2 total-budget pre-build disclosure (counts; acceptance stays human, §14.7) |
| `calibration_gate` | §5.3 `engine_admission_verdict` event: not_engaged / point_mode_diagnostic / engine_refused / confounded(ci_target_unmet) / engine_admitted |

### harness/efc_trigger.py — §2.1 closed trigger, §8.5 shapes, §9.1 family gates

| Function | Section served |
| --- | --- |
| `TRIGGER_FIELDS`, `ALLOWED_SURFACE_FIELDS`, `ORACLE_AND_OUTCOME_FIELDS` | §2.1 extraction closure (surface + population-pinned metadata only) |
| `extract_trigger_features` (fail-closed typing) | §2.1 declared-structure predicate inputs |
| `trigger_fires` | §2.1 four-conjunct predicate, verbatim |
| `trigger_result_record`, `strip_oracle_and_outcome`, `check_extraction_integrity` | §2.1 byte-identity under oracle/outcome removal; §13 trigger recompute |
| `irrelevant_shape_failures` | §8.5 irrelevant construction (both check inputs kept; canonical + variant shapes; no routing tag) |
| `family_validity` | §9.1 gates: equal counts, fire-prediction ≤ 0.50, zero false/missed fires, per-fixture byte-identity, leakage-phrase scan |

### harness/efc_carrier.py — §3 carrier/envelope/warrant/mint (+§11 authorization half)

| Function | Section served |
| --- | --- |
| `DispositionCarrier`, `validate_carrier`, `V0_PREDICATE_FEATURE_BINDINGS` | §3.1 closed carrier; carrier-owned exact trigger bindings; structural prose exclusion |
| `ValidityEnvelope`, `validate_envelope`, `envelope_hash` | §3.2 envelope; any field change = new candidate license |
| `TypedRevision`, `validate_revision` | §3.4 exactly-one typed scope |
| `revision_applies`, `warrant_health`, `carrier_hash` | §3.4 warrant health not existence; §11 table rows incl. unrelated-revision-stays-eligible (governance-should-lose) |
| `mint_disposition`, `MintInputs`, `SourceCausalVerdict` | §3.3 all six mint conditions, fail-closed; R1 authored-oracle refusal |
| `NominationRecord` | §3.3/R5: untrusted audit claim; cannot flip any refusal (test-pinned) |

### harness/efc_ledger.py — §13 replay, §2.3/§5.3 order, §10.1 cost

| Function | Section served |
| --- | --- |
| `make_row`, `validate_event_row` | §13 closed row vocabulary; compact identities |
| `replay_fixture_group` | §2.3 canonical order; check-completes-before-action boundary; post-answer = annotation, never win path; §8.2 B_inactive forced-inactive contract; §13 holes/duplicates fail closed; §2.1/§13 trigger recompute |
| `recompute_cost` | §10.1 decision_tokens formula (no double-count of rendered evidence); hard ceilings (1 invocation / 512 / 256 / 2); logged-claim recompute — untrusted logs |
| `replay_ledger` | §13 duplicate identity across ledger; §4/§5.2 precommit-precedes-rows; contract-hash recompute |

§10.1's 1024-token per-added-correct ceiling binds the §9.3 quality-win
comparison at score time (Part II scorer); the pin lives in efc_contracts and
is consumed by the planner board notes — no score-time §9 verdict assembly
exists yet by design.

### harness/efc_manifest.py — §5.2 machine check

| Function | Section served |
| --- | --- |
| `REQUIRED_FIELDS`, closed schema | §5.2 pin list, verbatim |
| `check_calibration_manifest` | seal-hash equality; frozen-text equality + hash recompute; §10.2 constants; roster/fixture/oracle shape+format; ignorance contract; optional §9.4 region (vertices validated or response_curve_only); forbidden-content key scan (no held-out outcomes) |
| `manifest_hash` | §5.3 `calibration_manifest_pinned` identity |

## Test → sealed section

| Test module | Pins |
| --- | --- |
| `tests/test_efc_intervals.py` | §10.4 unit-test-before-contact requirement (interval half): scipy/statsmodels goldens (provenance: scratchpad `gen_goldens.py`), Newcombe 1998 published example, erfc round-trip, boundary-width-never-zero (§10.4 guard), Bonferroni simultaneous-vs-marginal, simplex domain errors |
| `tests/test_efc_contracts.py` | §5.1 seal tripwire (spec file hash), §8.3/§8.4 text re-derivation from the sealed file, §10.3/§10.1/§10.2 numeric pins, closed vocabularies |
| `tests/test_efc_planner.py` | §10.4 enumeration minimality; zero-variance guard; **build finding 1 (two-point sliver + sealed-board structural refusal)**; degenerate-variance refusal; §9.4 region refusal at p_irrelevant=0; AND/OR composition + decision-bearing arms; §10.2 stratum equalization; §6 bands; §10.2 collapse ladder; verdict vocabulary; §10.2 count disclosure |
| `tests/test_efc_trigger.py` | §2.1 conjuncts + closure refusals + byte-identity + value-blindness; §8.5 canonical/variant/would-fire shapes; §9.1 balance, missed/false fires, leakage |
| `tests/test_efc_carrier.py` | §3.1 closure (template-id and prose riders refused), §3.2 envelope hash sensitivity, §3.4/§11 suspension table + unrelated-stays-eligible, §3.3 six mint refusals + nomination-cannot-flip (R5) |
| `tests/test_efc_ledger.py` | §2.3 boundary (post-answer annotation), §13 holes/duplicates/inversion/untrusted-claims, §10.1 formula + ceilings, §8.2 B_inactive, §4 precommit order |
| `tests/test_efc_manifest.py` | §5.2 pins, closed schema, forbidden-content scan, §9.4 region paths, §10.2 constants |

## §18 v0.2 amendment (2026-07-12, thread `epistemic-frame-check-v0-build`)

Bounded arithmetic fold, applied on dan's green-light under Sol's architectural
resolution and seven acceptance conditions. Delta:

| Change | Where |
| --- | --- |
| Enumeration ceiling 24 → 128 (bounded feasibility, not power) | spec §6/§10.2/§10.4/§14; `efc_contracts.N_MAX` |
| Explicit population precision pin (5% of comparator weighted mean, per vertex) | spec §10.3; `efc_contracts.POPULATION_COST_CI_HALF_WIDTH` |
| Three-layer admission split: precision admits; projected difference/margin/positivity/arm-win never do; held-out rows are the only verdict | spec §10.4; `n_required_population` (margin+positivity → `projected_clearance_diagnostic`) |
| §18 amendment record (finding 1 + correction lineage, three events distinct) | spec §18 |

Acceptance-condition mapping: (1)+(2) `n_required_population` precision-only
admission with margin/positivity kept as diagnostics —
`test_saving_below_margin_is_diagnostic_not_refusal`; (3) historical N=24
enumeration pinned explicitly and independent of `N_MAX` —
`test_historical_v01_infeasibility_enumeration` (incl. the §18 first-feasible
N table 35/54/77/124); (4) coherent-corner full-board acceptance at 128 —
`test_coherent_corner_admits_at_v02_ceiling` asserts `engine_admitted`,
stratum table {mm/mc/irr: 124, source: 10}, 2232 target invocations per
branch, 30 source invocations, and the standing budget-disclosure flag;
(5) seal tripwire demonstrated failing between the spec edit and the
deliberate hash update, then repinned (`test_sealed_file_hash_matches_pin`);
(6) full `make efc-test` suite green (130 tests) plus m2/close-gate/PRF
regressions; (7) no manifest authoring, fixture authoring, or engine contact.

## §19 v0.3 amendment (2026-07-12, cold-audit fold, thread `epistemic-frame-check-v0-build`)

Both cold auditors (cursor/grok-4.5, cursor/composer-2.5) endorsed the §14
artifact and decisions 2/7/8/10/11(sizing); their shared blocker (population
omission = silent under-planning seam) was accepted by the architect with the
stronger pre-declaration remedy; dan approved. Delta:

| Change | Where |
| --- | --- |
| Population intent mandatory pre-calibration (region XOR response_curve_only) | spec §5.2/§10.4; `efc_manifest.REQUIRED_FIELDS`; `AdmissionInputs.population_intent` (None → band does not open) |
| Later population manifest must byte-match the §5.2 choice | spec §5.3/§12/§14.6; `population_choice_byte_identical` (canonical JSON, key-order-proof) |
| `response_curve_only` = permanent typed non-license; quality board still fully sized | spec §12/§10.4; `calibration_gate` license_path + `planned_gates(False)` path (tests pin quality arms present, population/efficiency leaves absent) |
| Reconstructible per-vertex population diagnostics (never verdicts) | `VertexDiagnostic` + `population_vertex_diagnostics` (single recompute path); aggregate bool derivable — tests pin recompute equality |
| §9.3 decision-bearing OR arms pinned pre-held-out; no score-time promotion (architect explicitly rejected the reviewers' promotion proposal) | spec §9.3; `SuitePlan.decision_bearing_arms` pin map; acceptance test asserts the pinned arm sets |
| Hygiene: stale `2..24` traceability entry | this file, module table |

Tripwire again demonstrated failing between spec edit and deliberate repin.
v0.3 spec sha256 recorded in the build thread. Suite grew to 135 tests.
One test-authoring correction during this fold: I initially asserted
`positivity_ok` True for the small-saving pilot; the diagnostic itself showed
the simultaneous lower bound legitimately crosses zero at the first
precision-admitted N (saving 10, allowed gap 25) — the assertion was fixed to
follow the arithmetic, disclosed here.

## Interpretation decisions (flagged for the cold implementation audit)

Ratification status: decisions 1, 4, 5 endorsed by the architect (v0.2 fold);
decision 6 promoted to the explicit §10.3 v0.2 pin; decision 3 superseded by
the §10.4 v0.2 three-layer language. Cold audit (v0.3 round): decisions 2, 7,
8, 10 endorsed by both auditors and accepted by the architect; decision 9
superseded by the §19 mandatory pre-declaration (the deadline reading was
endorsed, treating omission as Part-II-complete was blocked, and the stronger
remedy landed); decision 11 endorsed for sizing, with the architect's
explicit ruling that non-bearing arms stay sealed out of the held-out
decision (reviewers' promotion proposal rejected). Nothing remains
unratified.

1. **Half-width** of an asymmetric interval = `(upper − lower) / 2`. The
   §10.3 targets are read against this symmetric definition. (For the NI
   finding both candidate definitions give the same infeasibility floor.)
   *Endorsed.*
2. **Binary pilot projection** onto candidate N uses continuous successes
   `p_hat * N` through the same Wilson/Newcombe code path score time uses
   with integers — no rounding rule invented.
3. **n_required is decided by the width pin** (§10.3). Projected margin
   clearance at pilot point estimates is reported as
   `projected_clearance_diagnostic`, never as admission — §10.3 allows
   calibration to estimate variance, not to adjudicate effects.
4. **§9.3 preconditions** (NI on match_commit and irrelevant) are
   intersection legs at 95%; only the OR alternatives carry the Bonferroni
   97.5% (§9.3's "each alternative" language).
5. **§9.3 efficiency-arm cost** uses the §9.4/§12 population construction
   against the named comparator at family alpha 0.025 (= 1 − 0.975), per
   §12's "same construction with their named comparator".
6. **Population-cost width criterion** — originally an interpretation (§10.3
   v0.1 pinned no population h); *blocked as interpretation and promoted to
   the explicit §10.3 v0.2 pin* `POPULATION_COST_CI_HALF_WIDTH (5%)` of the
   comparator's weighted mean at every declared vertex. Under the §10.4 v0.2
   split, precision alone admits; the §9.4 margin and positivity conditions
   are calibration diagnostics and held-out verdict conditions.
7. **§6 S-bands and §7's S1 ≥ 0.80** are point-estimate checks (the spec
   attaches its precommitted CI rule to the two §7 differences only).
8. **Resident-instance identity** for §3.4/§11 `resident_instance` revisions
   is the canonical carrier hash (`carrier_hash`) — §3.1 declares no id
   field, and adding one would be new schema.
9. **Calibration manifest may omit the population region** (§5.3 pins the
   population manifest after admission; §12's deadline is held-out contact).
   If present it is validated and enters the admission board; if absent,
   §14.6 blocks Part II until declared. `response_curve_only` is honored as
   the typed non-license path.
10. **Stop rule** is carried as the pinned identifier
    `k5_packet_plus_single_t07_collapse_probe` (§10.5 prose, mechanized).
11. **OR-gate stratum sizing**: only decision-bearing (powered) arms size
    strata; an unpowered arm is recorded and sealed out of the decision at
    plan time rather than silently underpowered (§0.2 "separately
    precommitted comparisons").

## Not built, by design (§14 boundary)

- No held-out or calibration fixture content; no fixture authoring tools.
- No engine adapters, no model calls anywhere in `efc_*`.
- No score-time §9 verdict assembly (Part II scorer) beyond the shared
  interval/planner functions it must reuse.
- No provenance-health suite runner (§11 behavior half) — only the
  authorization computation it will call (`warrant_health`).
- Sketch hygiene items (§16) untouched; `sketches/next_substrate/` earns no
  credit from this build.
