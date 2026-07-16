# EFC v1 findings — calibration closed `confounded(menu_ceiling)`

Status: **CLOSED 2026-07-16** by dan's ruling ("let's close it"), after the
second live pilot's runner-typed verdict. The sealed Part I protocol is
[SPEC_EPISTEMIC_FRAME_CHECK_V1.md](SPEC_EPISTEMIC_FRAME_CHECK_V1.md)
(`part_i_spec_hash 2d37f6bf0cd4aab830cb1dcf5eb9576f13b9acff65b63cd7d5b5fe0ea5b6097d`).
Predecessor: [EFC_V0_FINDINGS.md](EFC_V0_FINDINGS.md) (closed
`blocked_before_contact`, 2026-07-15). Narrative: walkthrough chapters
[17](walkthrough/17_EFC_V1_WIRE_COMMITMENT.md) and
[18](walkthrough/18_EFC_V1_CALIBRATION_CLOSE.md).

## One-line result

The wire-commitment instrument reached a live engine and refused twice with
typed reasons — first `confounded(commitment_invalid_rate)` (output cap
truncation), then, with the cap repaired, `confounded(menu_ceiling)`:
gpt-5.4 selects the check-consistent action 15/15 on the full task+menu
surface with no treatment, leaving zero headroom for the C−B delta the
conjecture requires. The conjecture remains untested, now for a measured
reason.

## The record (all 2026-07-16, single day)

- Part I sealed (`cdd7087`); calibration packet built in eight §20
  lifecycles (commits `3a343b2`→`c60daad`); dan signed 15 plausibility
  attestations (`0253352`) and pinned the manifest by hand
  (`efc-v1-manifest-pin-3f2232aa0e11451c`, `4d9fdbb`).
- Pilot runner built under the ninth lifecycle (`a549d59`); grok's cold
  review blocked three money-critical defects (actuals crossing pools
  silently, unrowed transport failures, undisclosed solicitation floor) —
  all repaired pre-contact.
- **First live contact in the EFC lineage** (30 calls, $0.028): menu-only
  lane clean (15/15 valid, 0 solicitations); task+menu lane 12/15
  `commitment_invalid`, all from `max_output_tokens=64` truncating JSON
  when the engine adds `optional_prose` → `confounded(commitment_invalid_rate)`
  (ledger `runs/efc_calibration_v1/pilot_integrity_dryrun.jsonl`; the
  filename's "dryrun" is a disclosed naming bug — rows are live).
- Option-A round under dan's "$3" ruling (tenth lifecycle, `a578ec2`):
  Sol sized cap 256 against observed truncations; superseding manifest v2
  (`c91c223a…`) pinned by dan (`efc-v1-manifest-pin-ecb3e5a6eb65db0e`);
  runner gained the invalid-rate gate as a typed outcome, honest live
  run-ids, cap-from-manifest, and structural pin-before-contact for
  superseding manifests.
- **Second live contact** (30 calls, $0.031; ledger
  `runs/efc_calibration_v1/pilot_integrity_live_20260716T153943Z.jsonl`):
  truncation cured (30/30 valid); menu-only clean again (replication);
  task+menu expected-enum hits 15/15 with no treatment → B_obs = 1.0 on
  match_mismatch ≥ 0.80 → runner-typed **`confounded(menu_ceiling)`**.
- Total live spend across the lineage's entire engine contact: **≈ $0.060**.

## Licensed

1. **The wire-commitment elicitation works on a live engine.** 45/45
   schema-valid single-enum commitments across both pilots at adequate
   output cap. The decision surface v0 could not score is machine-scored
   exactly, live.
2. **The menu-only surface is leak-clean and solicitation-clean**, twice:
   15/15 valid, 0 solicitations per run, under the disclosed lexical-floor
   detector.
3. **The gate architecture catches both designed instrument-failure modes,
   typed, pre-calibration:** invalid-rate ceiling at cap 64, menu ceiling
   at cap 256. Neither reached a scored experiment. Combined detection
   cost: six cents.
4. **gpt-5.4-2026-03-05 at `reasoning.effort=none` saturates this task+menu
   surface** (15/15 expected-enum selection, no treatment). A baseline
   observation about this engine on this surface — not about epistemic
   frames.
5. Process: ten §20 lifecycles converged in-budget in one day; three
   moderator gloss-vs-sealed-text errors were caught by reviewers reading
   source bytes; two live-corpus mutator defects (v0-K4 class) were found
   and permanently guarded; the classifier-to-dan's-hand pattern held for
   both attestations and both pin events.

## Not licensed

- Any claim about epistemic-frame behavior, consequence-shaped attention,
  or the structural-transfer conjecture — no treatment was ever run.
- Any claim that the surface fails for other engines, other reasoning
  efforts, or harder mismatch structures — one engine, one effort level,
  one fixture suite.
- Any population-level claim (the manifest precommitted
  `response_curve_only`).
- Promotion of the confounded task+menu fixture suite into any future
  scored experiment without redesign and fresh gates.

## Reopen condition

A successor (fresh lineage, v2) needs a surface/engine pairing whose
untreated B_obs sits inside the band the experiment requires — measurably
above chance, below the 0.80 ceiling, with headroom for the 0.25 margin.
Candidate routes, none licensed here: harder mismatch structure that does
not fingerpost through competence (new fixtures + new leak audits), a
weaker or differently-configured engine (roster change = new wire ruling +
manifest), or both. The pinned v2 manifest, gate params, and both pilot
ledgers are the inheritance; they carry as candidates, re-earned under a
new seal.

## Artifact index

| Artifact | Identity |
| --- | --- |
| Sealed Part I | `2d37f6bf…5b6097d` (`cdd7087`) |
| Manifest v1 (pinned, superseded) | `c7faddf2…` / pin `…3f2232aa0e11451c` |
| Manifest v2 (pinned, active at close) | `c91c223a…` / pin `…ecb3e5a6eb65db0e` |
| Pilot ledger 1 (confounded invalid-rate) | `runs/efc_calibration_v1/pilot_integrity_dryrun.jsonl` |
| Pilot ledger 2 (confounded menu-ceiling) | `runs/efc_calibration_v1/pilot_integrity_live_20260716T153943Z.jsonl` |
| Thread record | `.substrate/threads/epistemic-frame-check-v1-calibration/` (ended at close) |
