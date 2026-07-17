# EFC v2 pilot runner contract

Status: v2 lineage. Dry-run (MockTransport) only — **no live engine contact**
is structurally authorized in this runner. Contact authorization is
unconstructible (v1 discipline).

## Lanes

| Lane | Purpose |
| --- | --- |
| `M_untreated` | Untreated relevant items for §C admission band and pair predicates |
| `M_forced_class` | Dual-scoring: each relevant item scored under commit and non_commit |
| `M_irrelevant` | Irrelevant stratum untreated floor |

## Ledger

Append-only `efc_pilot_runner_ledger_v2` rows. Budget guards inherited from v1
pattern. Pin-sidecar lifecycle inherited from v1 pattern.

## Typed outcomes

Runner vocabulary extends v1 with §D admission types via
`evaluate_admission_gate`.
