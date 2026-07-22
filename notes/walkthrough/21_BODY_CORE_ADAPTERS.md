# Chapter 21 — The carrier is not the judge

Previous: [When earned parts do not yet make an earned whole](20_BODY_0_COMPOSITION.md) · [Walkthrough index](README.md) · Next: [Current whole-body orientation](../BODY_MAP.md)

**Status: provisional wire/integration engineering; X2, M2, shared
source-binding, and M3 adapter surfaces cold-endorsed. No new memory finding.**

Body-0 showed that individually earned properties do not become an earned whole
merely because orchestration can place them in one run. The next engineering
question was more modest: can the lab carry those historical records through a
common lineage runtime without changing what they mean?

## The question

> Can one small integrity kernel preserve X2 placement history, M2
> consequence-earned state, and M3 trust-boundary decisions while leaving each
> unchanged scorer in charge of its own claim?

This work serves the provisional whole-body direction in
[NEXT_SUBSTRATE.md](../NEXT_SUBSTRATE.md) and the maturity boundary in
[BODY_MAP.md](../BODY_MAP.md). It serves no scientific milestone. Its oracle is
exact reverse projection plus the unchanged component scorer. Its
loses-condition is any transport that changes source rows, scorer evidence,
client policy, or authority routing while still appearing to pass.

## Vocabulary bridge

An **integrity kernel** validates a small common envelope: ordering, hashes,
writer-role claims, backward references, retention shapes, and reconstructable
views. It does not decide whether a memory claim is true.

An **adapter** carries one existing instrument's rows through that envelope and
projects them back. A correct adapter translates representation without
quietly inventing policy.

A **source binding** connects an adapter-owned receipt to the exact carried row
that warranted it. Binding establishes provenance, not authorization. The
client must still decide which event kinds and transitions it permits.

## The common geometry

Every pressure test follows the same narrow shape:

```text
closed source ledger
  -> finite, visible adapter transport
  -> Body Core lineage and full replay
  -> exact reverse projection
  -> unchanged component scorer
```

The scorer is deliberately outside Core. Core may refuse malformed lineage;
the adapter may refuse broken correspondence; neither may manufacture the
component verdict.

| Client | What Core carries | Client rule that remains outside Core |
|---|---|---|
| X2 | Declared records and hot/cold placement receipts | Prune/rematerialize semantics, operation fold, and cost replay |
| M2 | S1 failure warrant, probationary earned state, and S2 activation | World-failure eligibility, session binding, and resident scorer |
| M3 Track A | Pinned episode-record items and offer/withhold audit receipts | Trust-boundary decision semantics and red-team cells |
| M3 Track B | Exact ingestion source rows, with no Core state | Whether refusal or asserted-trust breach engaged |

This separation is the important property. If an adapter turns `offer` into
hot placement, `withholding` into suspension, or `asserted_trust` into writer
authority, it is no longer preserving the experiment.

## What was built

Start with the shared runtime and correspondence helper:

- [core.py](../../sketches/next_substrate/core.py) implements the provisional
  lineage envelope, replay, state views, warrant health, placement, and
  reported metabolism;
- [correspondence.py](../../sketches/next_substrate/correspondence.py) checks
  source kind, causal parenthood, declared coordinates, and client item scope;
- [BODY_CORE_SOURCE_BINDING.md](../BODY_CORE_SOURCE_BINDING.md) records the
  helper contract and its limits;
- [BODY_CORE_SOURCE_BINDING_REVIEW.md](../BODY_CORE_SOURCE_BINDING_REVIEW.md)
  records the two independent endorsements.

The three clients are:

- [x2_adapter.py](../../sketches/next_substrate/x2_adapter.py) and its
  [contract](../BODY_CORE_X2_ADAPTER.md);
- [m2_adapter.py](../../sketches/next_substrate/m2_adapter.py) and its
  [contract](../BODY_CORE_M2_ADAPTER.md);
- [m3_adapter.py](../../sketches/next_substrate/m3_adapter.py), its
  [contract](../BODY_CORE_M3_ADAPTER.md), and the completed
  [review](../BODY_CORE_M3_ADAPTER_REVIEW.md).

The M3 adapter is the first client authored after the shared-helper rule. Its
source index freezes eleven ledgers and 89 rows: five foreground draws, three
live-channel breaches, one defended draw, and two ingestion outcomes. Track A
admits every pinned episode record active and hot, then records offer/withhold
only in a separate audit receipt. Track B creates no state at all. The
unchanged red-team scorer therefore still sees the documented asserted-trust
breaches instead of an adapter that repaired them by construction.

## Inspect the exact review surfaces

The proposal and implementation manifests freeze the bytes independently
reviewed by two other substrates:

```text
proposal review
ba2fad62d3be090f48bbe1dec018fee976683ce0ee129749cd91196eb31679a4

M3 implementation review
8598e54b9826fd3ff847d37debe0758d2f4c84f559350b119e73a6aa41ae39d5
```

Verify the unchanged implementation, tests, proposal, and source pins from the
repository root:

```bash
/usr/bin/jq -r '
  .files | to_entries[]
  | select(
      (.key | endswith(".py"))
      or (.key | contains("BODY_CORE_M3_ADAPTER_PROPOSAL"))
      or (.key | contains("proposal_review_manifest"))
      or (.key | contains("source_index"))
    )
  | "\(.value)  \(.key)"
' \
  notes/body_core_m3_adapter_implementation_manifest.json \
  | shasum -a 256 -c -
```

The living documentation was promoted after review and is therefore allowed to
differ from the historical manifest. The adapter, tests, Core, helper, scorer,
proposal, and source-index bytes remain the reviewed implementation surface.

## Run the safe wire checks

These commands do not contact a model and do not append under `runs/`:

```bash
make body-core-test
make body-core-x2-test
make body-core-m2-test
make body-core-m3-test
make body-sketch-test
```

The stable summaries at this close are:

```text
26 Body Core/projector tests
9 X2 adapter tests
11 M2 adapter tests
14 M3 adapter tests
6 walking-skeleton tests
```

The M3 matrix projects 172 Core rows across eleven separate lineages and
exposes 1,397 append-prefix rows. Those counts disclose deterministic work.
They are not latency measurements or a reconstruction-cost win.

## How to read the M3 wire result

The M3 test's strongest positive statement is exact preservation:

```text
M3 adapter: eleven ledgers preserve exact fresh scorer evidence
```

“Fresh” here means the test removes historical `cell_verdict` rows from
temporary source and projected copies, invokes the unchanged digest-pinned
`harness.score_redteam` command on each, and compares full evidence modulo only
timestamps. It does not mean a model was contacted again.

The refusal probes then show that:

- unhashed and rehashed source mutations lose;
- stale Core view claims lose to replay;
- unknown fields and opaque row escrow lose;
- source and episode pin drift loses;
- missing, wrong-kind, non-causal, or coordinate-drifted decision bindings lose;
- receipt cardinality and source semantics remain exact;
- correctly bound lifecycle, placement, and metabolic events still lose;
- a different Core-legal controller cannot impersonate the adapter;
- Track-B trust fields cannot mint state;
- the unchanged scorer still refuses a bad store digest.

These are wire refusals. They do not demonstrate resistance to a compromised
ledger writer or cryptographically authenticate the declared writer ids.

## What the reviews found

The source-binding review established the jurisdiction rule: an adapter governs
the item ids it explicitly claims. Foreign items remain under Core's generic
state machine unless another client claims them. No global ownership registry
or overlap detector was earned.

The M3 proposal and implementation each received two independent endorsements
without repair. The reviewers also preserved four debts:

1. the frozen source index's derived AG-U1 rollup omits one defended
   `not_engaged` count, while the per-ledger rows remain correct;
2. carried source events can be reparented within valid earlier lineage without
   changing field-exact projection because transport topology is not claimed;
3. historical verdict stripping works, but its current regression test would
   not catch removal of that strip on already-scored Track-B ledgers;
4. several multi-mutation tests prove refusal with broad error assertions rather
   than pinning every mutation to one exact refusal path.

These are visible follow-up debts, not evidence that the reviewed behavior
failed.

## What this chapter establishes—and does not

Body Core v0.2 established three independently reviewed client pressure tests.
Body Core v0.3 then split the structural kernel from the literal v0.2 policy
projector: cognitive replay and view claims now require explicit selection,
while the same closed ledgers return to unchanged scorers without changing the
prior results. The v0.3 post-build review remains pending; the historical v0.2
review manifests continue to attest only to the bytes they froze.

It does not show that the three properties compose causally. Body-0 remains
`not_engaged`. It does not show that Core creates earned trust, closes M3's
ingestion border, reduces reconstruction cost, or supplies a product-ready
schema. Full replay remains authoritative and append validation remains
quadratic.

The handoff is therefore an engineering one: later body slices may reuse this
carrier, but every new client still needs its own source corpus, correspondence
rule, scorer oracle, loses-condition, and bounded review.

---

Previous: [When earned parts do not yet make an earned whole](20_BODY_0_COMPOSITION.md) · [Walkthrough index](README.md) · Next: [Current whole-body orientation](../BODY_MAP.md)
