# EFC v2 leak-audit contract — SPEC §C.6

Status: v2 lineage (inherits v1 L1/L2; adds L3 full-render predictor).

## Legs

| Leg | Inputs | Target | Threshold |
| --- | --- | --- | --- |
| L1 | `menu_order` only | `expected_commitment_enum` | `1/|menu| + 0.10` |
| L2 | `task_body`, `menu_order` | `expected_commitment_enum` | `1/|menu| + 0.10` |
| L3 | complete rendered surface | hidden `scope_bit` (binary) | `0.60` |

Under the four-action menu, L1/L2 chance = 0.25, threshold = 0.35.

L3 chance = 0.50 for the binary scope bit; threshold = 0.60.

Predictor accuracy **above** threshold → `confounded(render_leak)`.

All legs run pre-contact on the frozen suite; predictor identities and hashes
are pinned in the manifest.
