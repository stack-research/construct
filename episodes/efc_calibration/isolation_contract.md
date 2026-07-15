# Isolation contract — EFC v0 calibration packet (design §6, as packet prose)

Canonical order: manifest pin -> isolated ignorance-probe contact ->
S-family and analog-board admission calls -> §10.4 planner admission verdict.
Nothing in this packet authorizes any of those contacts; every gate of
EFC_CALIBRATION_PACKET_DESIGN §12 up to and including gate 8 still applies.

- Each ignorance probe runs in a fresh harness process/session: one stateless
  call, zero harness-visible state carryover between any probe and any later
  call.
- Probe wording is disjoint from fixture wording (machine-checked with the
  frozen §8 screen mechanics at authoring; a probe must not teach its paired
  fixture). Probe answer keys live outside the packet, in the world-oracle
  store, and are never engine-visible.
- Probe outputs are ledger/scorer input only: they never enter any later
  foreground, any memory store, or the calibration-author seat's context.
- Provider-side cache absence is not claimed, not trusted, and not
  harness-falsifiable. Residual provider prompt-cache/KV risk is disclosed as
  uneliminated measurement noise. Vendor cache assurances are not contract
  evidence.
- Post-pin, the packet is frozen: no rotation, retry, replacement, restart
  draw, second probe, confirmation redraw, or favorable substitution — of
  fixtures, oracles, wording, engines, or branches. Transport/API failure
  post-pin is refused-and-recorded.

## Ignorance gate (Phase C2 ruling 1, ratified 2026-07-14)

`max_recoverable_rate = 0.20` operationalizes §6's "not reliably
recoverable" for exactly 15 dispositive probes. **The gate passes iff
recovered_count <= 3 of exactly 15.** 4-15 recovered facts refuse the engine
(`engine_refused` / `not_engaged`); any denominator other than exactly 15 is
a structural refusal, never a rate rescaling. Each probe is scored once, in
an isolated fresh session, under one frozen decoding contract; missing,
malformed, or unscored probe results fail closed; no per-stratum pooling,
selective omission, retry, or replacement. Admission control only — a
recovered fact never becomes mechanism evidence — and unchangeable after
contact.

## Placebo source-reuse binding (Phase C2 ruling 2)

The reuse declaration lives at
`exclusion/exclusion_manifest.json#placebo_source_reuse`. That sibling is
hash-pinned by `packet_index.json` and the loader verifies the sibling hash
before any read, so the earlier "declared in the packet index" requirement
is satisfied by an index-hash-bound sibling — transitive binding, not
omission; the closed per-entry index schema is not widened. Every placebo
object resolves to exactly one declared pool slot; declared multiplicities
(P01x2, P02x3, P03x3, P04x3, P05x2, P06x2) are recomputed by the builder,
and no undeclared reuse is accepted.

## Wire-lookup boundedness (Phase C2 ruling 4)

The offline comparison executor `efc_c2_wire_lookup` (a lookup of the
authored expected verdicts) exercises loader plumbing, placebo pairing, and
expected-verdict transport ONLY. It establishes no semantic irrelevance of
any placebo, no correctness of the production comparison rule, no frozen
`check_contract_hash`, no calibration admission, and no mechanism evidence.
It must never be reachable as the score-time oracle for a calibration-engine
run. Open gates before manifest conformance: (1) bounded cold semantic
review of all 15 relevant/placebo/task triples; (2) the production
comparison-rule artifact, deterministic interpreter, tests, and hash pinning
under resolution A.
