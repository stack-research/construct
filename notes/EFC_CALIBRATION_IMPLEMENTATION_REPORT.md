# EFC builder implementation report — Assignment B, A–G integration round

Seat: `claude/fable-5-builder`, resumed in the same materialized workspace
`materialize-efc-builder-a9ed60f` (non-git). Date: 2026-07-12. This report
supersedes all earlier reports and responds to the moderator consolidation
"ACCEPT WITH REQUIRED FIXES" — this round applies the enumerated A–G text
(now received in full; the previous round's inferred mapping is obsolete and
its divergences are corrected here).

Standing disclosures unchanged: builder seat only; no calibration facts,
sources, manifest instances, engine or network contact, or mechanism claims;
all material conspicuously fictional; the session-visible persistent-memory
index remains empty (no memory-derived steering); sealed Part I hash
re-verified `cb8d3dce6ac92025236b09660446f4c7239d6f8dc5712c3e23376a658ab38b34`.
Part I and the accepted design are unchanged.

## 1. A–G as applied

### A — no production comparison execution before the rule exists

- The callable executor protocol is renamed WIRE-ONLY:
  `WireComparisonRule`, `validate_wire_comparison_rule`,
  `wire_rule_contract_hash` (`harness/efc_check.py`). Nothing named
  "production" or "pinned" survives.
- The previous round's `PinnedComparisonRuleArtifact`,
  `pinned_rule_artifact_hash`, `bind_rule_to_artifact`, and the
  artifact-based `check_contract_payload/hash` minting APIs are **deleted**:
  no API can mint a final production `check_contract_hash` from any callable
  or declarative dict. `check_contract_hash(*_, **_)` refuses
  unconditionally with the pending explanation.
- Artifact identity remains typed-pending
  (`pending_check_contract_identity`), and real-contact authorization is
  structurally impossible (see B). No comparison-rule language or
  interpreter was invented.

### B — wire execution split from contact execution

`harness/efc_runner.py` now has two unmistakable surfaces:

1. `run_wire_admission_branch` — synthetic/mock only, `surface: "wire"` in
   its run_config, taking the wire rule executor, a
   `WireContactAuthorization` (minted by `authorize_wire_contact`), an
   injected pinned wire detector, and the manifest whose bytes must
   recompute to the authorized hash.
2. `run_admission_branch` — the production contact surface. It demands a
   typed `ContactAuthorization`; `authorize_engine_contact` **refuses
   unconditionally** while the check contract is pending, and even a
   hand-forged `ContactAuthorization` cannot run (no production engine
   adapter exists here). A nonempty dict is never authority on either
   surface.

`authorize_wire_contact` performs the shared structural binding against the
ONE existing §5.2 manifest schema (no second schema): machine-check ok,
bytes-recompute-to-checked-hash, fixture id+sha256 byte-binding, probe-id
binding, renderer/template identity match. Population intent and positive
budget are enforced by `check_calibration_manifest` itself, which the
binding requires to have passed. The production constructor's full future
checklist (final non-pending check contract, exact model/decoding identity,
pinned answer+route detector) is documented at the refusal site.

### C — complete admission assembly in wire form

- `derive_pilots_from_runs(report, packet, manifest) -> Pilots`
  deterministically aggregates the primary board: binary successes from
  `world_oracle_score.passed`; cost samples from **replayed**
  `decision_tokens` (`efc_ledger.recompute_cost` over the group rows —
  logged claims are not trusted; a replay mismatch refuses); population
  `StratumCostPilot` summaries per named lane comparison against the pinned
  manifest vertices. Every contrast id required by `planned_gates` must be
  derivable; a missing lane/stratum sample refuses with "incomplete analog
  contrast map".
- `emit_admission_verdict` calls the existing
  `calibration_gate(AdmissionInputs(...))` and appends ONE legal run-level
  `engine_admission_verdict` row (existing §13 vocabulary) carrying the
  computed verdict + reasons, stratum-N plan and projected-count disclosure,
  OR selections, projected-clearance diagnostics (explicitly
  diagnostics-only), the probe-sidecar hash + aggregate counts, and the
  collapse-ledger pin. On a transport-refused branch the row carries the
  typed refusal instead of any partial board. Projected clearance cannot
  select admission (planner unchanged; adversarially test-pinned).
- The branch report's S-band/ignorance/collapse values are no longer called
  complete admission input anywhere; the wire surface finishes with the
  computed verdict row.

### D — collapse stays injected and pending

- The answer-only `default_collapse_detector` is **deleted from the
  harness**. `run_wire_admission_branch` requires an injected
  `PinnedCollapseDetector` whose identity/hash the wire authorization pins;
  a bare callable refuses at both authorization and run time.
- The conspicuously fictional wire detector now lives in
  `tests/efc_wire_fixtures.py`, its contract text stating it is an
  answer-only stand-in and never the pending answer+route production rule.
  The route projection was not invented; production contact refuses until it
  is separately pinned (see B).
- The T=0.7 pass uses exactly the primary S/analog identities, exactly once,
  never probes; its rows carry the `t07.` pass namespace in a separate
  append-only `collapse_rows` ledger, replay separately through the
  untrusting §13 replay (with placebo pins), and are hash-pinned; the
  admission verdict row records `collapse_rows_sha256` and both collapse
  flags. No unaudited pass exists.

### E — probe audit without plaintext leakage

- No new §13 event type. Each probe lands in the protected append-only
  sidecar as `{probe_id, answer_sha256, recovered, temperature,
  isolation_id}`; the ordered sidecar is hashed
  (`probe_sidecar_sha256`), and hash + aggregate counts ride the final
  `engine_admission_verdict` row — including on the typed transport-refusal
  path.
- Plaintext responses are scorer-local ephemeral: only the hash is retained,
  and tests assert the response text appears in no sidecar, ledger row, or
  later prompt.
- The probe scorer must return a strict bool and the probe session must
  return the typed `EngineResult` shape; both refusals are tested.

### F — isolation claims stay honest

- Every session lease must carry an operator/adapter-issued compact
  `isolation_id`; uniqueness is tracked alongside wrapper object identity
  (strong references held), so distinct Python wrappers sharing an
  isolation_id refuse.
- isolation_ids are recorded in the probe sidecar (protected audit surface),
  never in prompts.
- The runner contract payload states in words that fresh provider
  process/client isolation is an **operator-bound pre-contact obligation**
  the pure harness cannot prove; provider cache remains `unverified`. No
  stronger claim is made anywhere.

### G — semantic identities

- `runner_contract_payload/hash` added: phase order, transport-terminal
  policy, session lease policy (incl. the operator-bound obligation),
  required injected collapse detector, both temperatures, ledger separation,
  and the wire/contact split. Included in artifact identities.
- The extractor's source hash is now reported as
  `module_sha256_diagnostic`; the semantic `predicate_contract_sha256` is
  retained separately.
- `FOREGROUND_TEMPLATE` mutable aliasing is replaced by
  `FOREGROUND_TEMPLATE_BYTES` (immutable canonical bytes — the exact hashed
  bytes) plus `foreground_template()` copy-on-read. Mutating a returned copy
  changes nothing behind the stable hash; a mutated alias also cannot render
  a foreground built under the canonical template (`template_sha256`
  re-verified at render time).
- `placebo_position_gate = "structural_single_insertion_point"` is explicit
  in the renderer, controller, check-adapter, packet-loader, and runner
  contract payloads, and a test proves relevant and placebo evidence use the
  identical insertion function at the identical position.

### Preserved behavior (assignment item 2)

B2 loader semantics/tests unchanged and passing (42 tests). B5 placebo
semantics/tests unchanged and passing; `efc_ledger` untouched this round
(18 tests). B3 phase order, terminal transport refusal, no-retry guard, and
derived counts carry forward inside the reworked wire surface.

## 2. Mandated negative tests (assignment item 3)

| Mandated test | Implementation |
| --- | --- |
| arbitrary dict cannot authorize contact | `test_efc_runner.py::TestContactSurfaceSplit::test_arbitrary_dict_cannot_authorize_contact` (production surface, wire surface, and bare-mapping manifest result) |
| pending rule/collapse identities refuse contact authorization | `test_pending_identities_make_production_contact_impossible` (unconditional production refusal + forged-object refusal), `test_pending_collapse_identity_refuses_wire_authorization` |
| manifest/packet hash or identity mismatch refuses | `test_manifest_packet_fixture_mismatch_refuses`, `test_manifest_probe_binding_refuses`, `test_manifest_bytes_must_recompute_to_checked_hash`, `test_authorization_binds_to_this_packet`, `test_runtime_rule_and_manifest_must_match_authorization`, `test_wrong_template_identity_refuses` |
| callable wire rule cannot mint production hash | `test_efc_check.py::test_no_production_check_contract_hash_exists` (callable, dict, and no-argument all refuse; identity typed-pending) |
| incomplete analog contrast map refuses admission assembly | `test_efc_runner.py::TestAdmissionVerdictRow::test_incomplete_contrast_map_refuses_assembly` (+ `test_refused_branch_refuses_pilot_derivation`, positive `test_pilots_derived_from_replayed_runs`, `test_verdict_row_emitted_and_legal`) |
| projected-clearance diagnostics cannot change admission selection | `TestPrecisionOnlySelection::test_clearance_diagnostic_does_not_steer_selection` |
| T=0.7 rows namespaced, separately replayable, hash-pinned | `TestCollapseLedger::test_t07_rows_are_namespaced_and_separate`, `test_t07_ledger_separately_replayable`, `test_t07_ledger_hash_pinned_in_verdict_row` (+ same-identity/single-pass/no-probe-rerun pins) |
| probe sidecar hashes and bool/type constraints | `TestProbeSidecar::test_sidecar_is_typed_and_hash_pinned`, `test_probe_response_text_not_retained`, `test_non_bool_probe_scorer_fails_closed`, `test_untyped_probe_result_fails_closed` |
| reused `isolation_id` refuses even with distinct Python wrappers | `TestIsolationIdentity::test_reused_isolation_id_refused_across_distinct_wrappers` (+ missing-id, reused-object, once-guard) |
| mutable-template alias attempts cannot change behavior behind a stable hash | `test_efc_renderer.py::test_canonical_template_is_copy_on_read`, `test_mutated_alias_cannot_ride_a_stale_hash_at_render`, `test_template_hash_is_of_the_canonical_bytes` |

## 3. Test record (assignment item 4)

Complete EFC suite, all 12 modules passing: intervals, contracts, planner,
trigger, carrier, manifest, ledger (18) — pre-existing suites unchanged —
plus renderer (17), check (13), controller (20), packet (42), runner (39):
131 tests in the builder's five modules. `harness.efc_artifacts` smokes
clean.

Non-EFC regressions: identical outcome set to all prior rounds — every
runnable suite passes; the same ten modules fail only on files deliberately
absent from this materialization (episodes/prf/*, episodes/x1–x2, corpus/,
sketches/, notes/previous/). No regression is attributable to this change
set.

## 4. Changed-file bundle (assignment item 5)

`builder_out/changed_files/` — 13 files, hashes in
`builder_out/changed_files.sha256`, verified byte-identical to the tree:

- `harness/efc_check.py` (resolution A; B1/B4 carried)
- `harness/efc_renderer.py` (resolution G; B4 carried)
- `harness/efc_controller.py` (resolution G gate; B5 carried; wire-rule
  naming)
- `harness/efc_packet.py` (resolution G gate; B2 carried; wire-rule naming)
- `harness/efc_runner.py` (resolutions B/C/D/E/F/G; B3 carried)
- `harness/efc_artifacts.py` (resolutions A/G)
- `harness/efc_ledger.py` (unchanged this round; carried from the B5
  extension, its pre-existing tests passing)
- `tests/efc_wire_fixtures.py` + the five `tests/test_efc_*.py` modules

`builder_out/MATERIALIZE_AUDIT.json` remains byte-identical to the
materialized input. Writes stayed inside `harness/`, `tests/`,
`builder_out/` (runtime `__pycache__` aside). Makefile untouched. Nothing
copied into construct; nothing committed.

## 5. Gates that remain pending for other seats (assignment item 6)

1. **Population-pinned comparison rule artifact + deterministic
   interpreter + conformance proof** — separately reviewed, later. Until
   then: no production `check_contract_hash`, typed-pending artifact
   identity, and `authorize_engine_contact` refuses unconditionally
   (resolution A/B).
2. **Pinned §10.2 answer+route collapse detector** — the route projection is
   not invented here; real contact refuses until it is separately pinned
   (resolution D).
3. **Production engine adapter, exact model/decoding identity, and the
   decoding-surface wire check** — design §10; the contact surface refuses
   without them.
4. **Fixture content, source snapshots, oracle ids/timestamps/hashes,
   refetch verification, probe deduplication (|F|)** — calibration author,
   dan (fetcher), cursor/grok-4.5 (refetch verifier), per design §11.
5. **Manifest instance authoring + closed-schema conformance** (design §12
   gates 6–7) — the wire manifest in tests is fictional machinery material
   with a placeholder check-contract hash.
6. **Moderator/operator permission for first engine contact** (design §12
   gate 8).
7. **Makefile `efc-test` extension** to the five new modules — moderator,
   after bundle acceptance.
8. **Grok/Composer closure pass limited to A–G**, then the moderator's
   apply/traceability/commit — per the closure plan; this bundle is its
   input.
9. **`notes/EFC_TRACEABILITY.md` fold** — the §2 table plus the prior
   rounds' traceability material; `notes/` is not writable here. The
   moderator's note is acknowledged: the untracked implementation report
   copied into construct is an operator handoff, and this regenerated report
   is the candidate replacement, not yet accepted authority.

## 6. Sealed-contract contradictions

None found in any round; Part I was not weakened or amended.
