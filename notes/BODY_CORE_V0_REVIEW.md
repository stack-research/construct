# Body Core v0 bounded wire review

Status: **ENDORSED 2/2 — provisional engineering only**.

Review thread:
[`body-core-v0-wire-review`](../.substrate/threads/body-core-v0-wire-review/).

Reviewed surface:
[`body_core_v0_review_manifest.json`](body_core_v0_review_manifest.json),
SHA-256
`4c4727917657e88b8fc24ea324d1a9b92bad74570a9ac31f05ba170ec78ae6f6`.

The review preserved the indexed bytes exactly. This record was added after the
room ended and is intentionally outside that manifest.

## Verdicts

- `cursor/composer-2.5`: **ENDORSE**. Independently reproduced the manifest and
  required checks; found the mechanism-neutral core separated from the stubbed
  EFC client, walking-skeleton integration intact, authority routing
  fail-closed, and maturity and non-claim prose accurate.
- `cursor/grok-4.5`: **ENDORSE**. Independently reproduced the same boundary and
  checks, then added adversarial probes across rehash/rewrite, scope, warrant,
  retention, lifecycle, and view-claim paths. It found no fail-open integrity
  defect.

No repair phase opened. The single allowed repair remains unused.

## Reproduced checks

- all twelve indexed file hashes matched;
- Ruff passed on the five Python implementation and test files;
- `make body-sketch-test` passed eleven Body Core and six walking-skeleton
  tests;
- `make body-sketch` completed its four authored wire-only phases;
- `git diff --check` passed.

## Exact boundary

The review endorses only the exact provisional `wire_integration_only`
implementation and its stated boundaries. It does not establish:

- cryptographic writer authentication or external chain anchoring;
- concurrent-writer safety;
- reduced reconstruction cost;
- product-schema stability;
- mechanism value or language-model learning;
- any scientific finding.

Active frontier search remains paused.

Grok noted that scopes, duplicate parents, invalid retention shapes,
disputed-warrant reactivation, and mid-chain rehash are enforced in code and
were exercised by its independent probes but are not individually named suite
cases. It classified that as residual coverage, not a block.
