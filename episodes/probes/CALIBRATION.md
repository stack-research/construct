# Probe calibration — M-1 conformance set

**OFF the bootstrap read path.** This file states the expected decisions. An incoming agent that reads it before answering the probes must declare `method: harness_assisted` in its manifest (AGENTS.md §Conformance). It exists for probe *designers* and *reviewers*.

All probes: governed lane, `eligibility_threshold 0.25`, `lexical_tfidf`, `recency_weight 0.0` (pure similarity, deterministic), yield + supersession enabled, authority neutral (fresh sidecar). Ground truth is computed live by `select_offers` at check time — the values below are design-time measurements (2026-06-12), not the answer key the script uses.

## Gate map and expected decisions

| Probe | Exercises | Expected offer boundary |
|---|---|---|
| probe-001 | Gate 1, both causes | offer `pb1-signoff`; withhold `pb1-ticket` (well-dressed, trust 0.2 → 0.302×0.2=0.060 < 0.25) and `pb1-elevator` (irrelevant, 0.000) — both `eligibility_below_threshold` |
| probe-002 | Gate 2 (yield) | offer `pb2-runbook` (contention 0.164 < ct 0.3); withhold `pb2-roster` `yields_to_live_input:fg-pager` (contention 0.560 ≥ 0.3, created before observed_at) |
| probe-003 | Gate 3 (supersession) | offer `pb3-guide-v2`; withhold `pb3-guide-v1` `superseded_by:pb3-guide-v2` (both eligible: 0.343 / 0.278) |
| probe-004 | Gate 4 (budget, top_k 2) + gate 1 | offer `pb4-owner` (0.577), `pb4-cmd` (0.442); withhold `pb4-window` `below_rank_budget` (eligible at 0.314 but rank 3) and `pb4-history` `eligibility_below_threshold` (0.045) |
| probe-005 | Gate ORDER (transfer-on-arrival, B1) | offer `pb5-baseline`; withhold `pb5-revision` `yields_to_live_input:fg-telemetry`. The superseder contends with the fresher datum (0.325 ≥ ct 0.3) and yields at gate 2, so it never reaches gate 3 — `pb5-baseline` (contention 0.187, eligible 0.260) is NOT buried. A supersession-first misreading withholds `pb5-baseline` instead. |

probe-005 is the discriminating probe: it cannot be answered correctly from gate definitions alone, only from gate *order* (SPEC_V1X amended order; codex's premature-burial blocker).

## Margins (lexical_tfidf is deterministic; margins matter for drift, not flake)

- Thinnest eligibility margin: `pb5-baseline` 0.260 vs threshold 0.25 (+0.010). Frozen text + deterministic backend means this cannot flake at runtime; any retrieval/tokenizer change requires recalibrating the whole probe set (S4 ground-truth recompute will surface decision flips as conformance failures of previously-passing manifests — that is the desired loud signal).
- Contention gaps: probe-002 0.164 / **0.3** / 0.560; probe-005 0.187 / **0.3** / 0.325 (upper margin +0.025, the second-thinnest value).
- probe-004 corridor: `pb4-window` 0.314 sits 0.064 above eligibility and 0.128 below rank 2 — both decisions (eligible, but over budget) have margin.

## Known limits (disclosed)

- Probe answers are derivable by running the harness; closed-book is a protocol rule enforced by manifest disclosure (`method`), not mechanically. The lab discloses enforcement limits rather than pretending them away.
- Substrate threads are not scanned for leakage (S5 covers repo docs only). A review thread that names specific probe decisions burns the probe set; the remedy is **rotating probe content**, not editing the immutable thread. Reviewers: critique the mechanism and this file's method — avoid writing record-level decisions into thread entries.
- `expected_answer` is empty in all probes: they are offer-boundary decisions, never engine runs, so no oracle and no ablation applies.
