# Body Core v0.2 M2 adapter cold review

Status: **endorsed after one bounded repair**. Review conducted 2026-07-20 in
substrate thread `body-core-m2-adapter`. This record licenses wire/integration
preservation only: no new M2 or X2 finding, mechanism license,
reconstruction-cost claim, or frontier reopening.

## Reviewed claim

Ten checked-in closed M2 S1/S2 pairs pass through Body Core v0.2 and reverse-
project under exact aggregate and per-row digest equality. The unchanged
resident scorer remains sovereign over M2 validity. World-failure warranting,
session-seam activation, field-visible transport, and declared refusal paths
must remain intact.

The same review also examined the X2 v0.2 correspondence repair, which binds
placement events to carried prune/rematerialize operations and checks terminal
placement against their independent fold.

## Initial review

Fable reproduced all declared suites and found the warrant, admission,
activation, escrow, digest, and scorer-sovereignty boundaries sound. The review
blocked one known cross-client consistency defect: M2 projection accepted a
Core-legal placement event affecting its materialized item even though the M2
adapter defined no such event. A fabricated metabolic event also survived
inside the Core's disclosed writer-reported boundary.

The review additionally clarified that unchanged-scorer equality adds no
independent happy-path discrimination after byte equality. Its value here is
testing verdict stripping and path rebinding while retaining scorer sovereignty
over properties such as fork identity.

## Bounded repair

The single repair made M2 projection refuse every placement or metabolic event
affecting its earned item, require terminal `hot` placement, added one named
probe for each refusal, and corrected the contract's oracle language. No schema,
source ledger, scorer, anatomy, or scientific claim changed.

Final reviewed hashes:

```text
fd4dad623b7dd6b22fd91d20f327868c8f00acc51375c4d99b5d8c7cbc50b8d0  sketches/next_substrate/m2_adapter.py
be06a4537222c406a408cb3ffe08d2199a87cc55565fd6254b8a9f1594ab38e3  tests/test_body_core_m2_adapter.py
8e74b6cee1ac7c3060b336c6f1877a4ff4932661d1ab199d5a0f955b690ab76c  notes/BODY_CORE_M2_ADAPTER.md
9ed829fd583def9cfdfaf82e244bb76757a36f8666894c44c03d1233df0535c9  sketches/next_substrate/core.py
484c2b2b35fb4c8a95861f817941cd50430493d390e0e43ec41a8dee8677d98a  sketches/next_substrate/x2_adapter.py
```

The contract hash above precedes this status-only promotion and review link;
the reviewed behavior and claim boundary are unchanged.

## Final verdict

**ENDORSE.** Fable re-ran both original probes on the repaired bytes, verified
the exact hashes, and reproduced 17 Core tests, 10 M2 adapter tests across the
ten closed pairs, 9 X2 adapter tests, 6 walking-skeleton tests, scoped Ruff, and
`git diff --check`.

The review budget is exhausted cleanly. Before a third adapter is authored, the
repeated correspondence rule should be factored into a Core-adjacent helper:
events affecting adapter-materialized state must carry a valid source binding
or be refused.
