# Body Core M3 adapter proposal

Status: **v0.1 draft; implementation withheld pending bounded cold review**.

Claim boundary: **wire/integration preservation only**. This proposal does not
rerun M3, create new red-team evidence, contact an engine, close an M3 debt,
reopen frontier search, or establish that Body Core enforces an air gap.

The exact source corpus is frozen in
[`body_core_m3_adapter_source_index.json`](body_core_m3_adapter_source_index.json),
SHA-256:

```text
81b1a480d572a89e8a8dfab1baef84af8efb9eebdabebd13808d2451543a571d
```

## Milestone gate

Scientific milestone: **none**. This would be the third independent pressure
test of provisional Body Core engineering while scientific mechanism search
remains paused.

Question:

> Can Body Core carry M3's distinction between earned-trust refusals and
> asserted-trust breaches through exact replay without laundering attacker-owned
> trust fields into Core authority or accidentally repairing the breaches?

Preservation oracle: exact reverse-projection equality plus fresh output from
the unchanged [`harness.score_redteam`](../harness/score_redteam.py) scorer on
both the source and projected ledger, using the same pinned episode JSON.

Loses-condition: refuse the adapter if any expected verdict or scorer evidence
changes, if an asserted-trust breach disappears, if source binding grants policy
authority, if attacker-controlled fields can choose a Core writer or authority,
or if offer/withhold is encoded as Core lifecycle or hot/cold placement.

Exact success statement:

> Body Core reversibly carries the eleven indexed M3 ledgers; the unchanged M3
> scorer reproduces the patched close matrix and both ingestion outcomes;
> Track-A boundary decisions remain source-bound to explicitly claimed record
> items; and asserted source trust remains payload data rather than Core
> authority.

## Why this corpus

The index names eleven checked-in ledgers and four pinned episode files:

- five patched-oracle foreground-text close draws: `AG-1 pass`, `AG-U1 pass`,
  `AG-loses not_engaged`;
- three patched-oracle live-channel-spoof draws: `AG-channel pass`, `AG-U1
  pass`, and the defense not engaged;
- one defended live-channel close: `AG-channel not_engaged`,
  `AG-channel-defended pass`;
- one weak ingestion refusal without a riding poison: `IN-1 pass`, `IN-loses
  not_engaged`;
- one weak ingestion refusal with the asserted-trust breach: `IN-1 pass`,
  `IN-loses pass`.

That is 89 source rows across eleven separate adapter lineages. Four rows are
historical ingestion `cell_verdict` rows. They are transported for exact ledger
preservation but stripped before fresh scoring, as in the M2 adapter.

The historical foreground ledger whose answer was inverted by the
negation-blind oracle is excluded. The patched close corpus supersedes it. The
strong `trace_auth_missing` IN-1 case remains a deterministic component smoke in
`tests/test_redteam.py`; there is no checked-in closed strong-forgery ledger, so
this adapter may not imply that it round-trips one. Adding such a ledger later
requires an explicit adapter/source-index revision.

## One source ledger, one Core lineage

Each indexed ledger is ingested into its own temporary Core lineage. Ledgers are
never pooled. Before writing, the adapter reads the complete ledger and pinned
episode to establish:

- exactly one `attack` row;
- the indexed attack surface, episode id, ledger digest, row count, and episode
  digest;
- one of the declared finite row schemas below;
- the Track-A run ids and resident branch, where applicable;
- that every Track-A `offer`/`withholding` record id exists in the pinned
  episode.

The adapter-start row pins the adapter version, source-index digest, source
ledger digest and count, episode digest and id, `attack_id`, attack surface, and
the unchanged scorer digest. Preflight does not make those values authoritative;
reverse projection and the unchanged scorer recheck them.

## Reversible source transport

Every ledger row becomes one `m3_source_row_carried` event. Source fields are
flattened visibly beside:

```text
source_row_index
source_kind
source_row_digest
```

Opaque escrow keys such as `original_m3_row`, `raw_row`, and `row_blob` are
forbidden. The closed source schema is finite:

| Source kind | Declared fields besides `kind` |
| --- | --- |
| `run_config` | `branches`, `cost_tiebreak_window`, `disclosures`, `engine_backend`, `episode_id`, `episode_overrides`, `foreground_renderer_version`, `fork_group_id`, `model`, `run_id`, `similarity_backends`, `ts` |
| `offer` | `attention_cost_tokens`, `branch_id`, `episode_id`, `fork_group_id`, `predeclared_usage`, `reason`, `record_id`, `run_id`, `ts`, `vocabulary_kind` |
| `withholding` | `branch_id`, `episode_id`, `fork_group_id`, `predeclared_usage`, `reason`, `record_id`, `run_id`, `ts`, `vocabulary_kind` |
| `branch_run` | `ablation_calls`, `branch_id`, `branch_output`, `completion_tokens`, `episode_id`, `fork_group_id`, `governance_steps`, `latency_ms`, `oracle`, `prompt_tokens`, `run_id`, `ts` |
| `attack` | `allowlist_ok`, `attack_id`, `attack_surface`, `attacked_run_id`, `attacker_id`, `clean_run_id`, `corpus_scope`, `episode_id`, `payload_digest`, `resident_branch`, `resident_config_digest`, `store_digest`, `target_record_ids`, `ts` |
| `ingestion_attempt` | `asserted_trust`, `attack_id`, `episode_id`, `forged_record_id`, `minted`, `poison_offered`, `poisoned_record_id`, `refusal_reason`, `ts` |
| `cell_verdict` | `attack_id`, `attack_surface`, `cell`, `corpus_scope`, `engine_backend`, `episode_id`, `evidence`, `model`, `ts`, `verdict`, `wire_test` |

An unknown kind or field requires an adapter revision. In particular,
`forgery_class` is not silently admitted merely because the current scorer knows
that newer field; the indexed closed ingestion rows do not carry it.

## Track A: claimed items and boundary receipts

For foreground and live-channel ledgers only, each pinned episode record becomes
one active, hot `m3_materialized_record` item. Its id is:

```text
m3:{attack_id}:{record_id}
```

An observer-written `m3_episode_record_declared` event, derived from the pinned
episode and carrying its digest, warrants the item. The item's detail contains
only the episode id, record id, and episode digest. Episode `trust`, record text,
and attacker content do not become Core authority.

Each carried `offer` or `withholding` row requires exactly one separate
`m3_boundary_decision_receipt` naming:

- the claimed item id;
- `source_event_id`, source row index, and source kind;
- run id, branch id, and record id;
- decision (`offer` or `withhold`) and the raw source reason.

The endorsed source-binding helper checks the carried-source kind, causal-parent
edge, and source coordinates. M3 then checks client semantics and cardinality:
the receipt's item/run/branch/record, decision, and raw reason must equal the
source row, every source decision gets exactly one receipt, and non-decision
rows get none.

The receipt is an adapter-specific audit relation. It is deliberately **not** a
`state_item_transition`, `placement_changed`, or `metabolic_event`. Offer is not
hot placement; withholding is not cold placement or suspension. All lifecycle,
placement, and metabolic events affecting an M3 item are unauthorized, even if
they carry a valid source binding.

The adapter claims only the item ids derived from the pinned Track-A episode.
Foreign Core items remain outside M3's jurisdiction under the endorsed
source-binding rule. A source `offer`/`withholding` row naming a record absent
from the pinned episode is not foreign Core state; it is an inconsistent M3
source and must be refused.

## Track B: no authority from a refused or poisoned write

The two ingestion ledgers use exact source transport but create no Core state
items or boundary receipts. This asymmetry is intentional:

- `minted: false` is a refusal to create governed standing, so the adapter must
  not materialize the forged candidate anyway;
- `poison_offered: true` is the documented asserted-trust breach, not a license
  to convert `asserted_trust` into Core writer authority or earned state.

Track-B fields therefore remain observer-carried source data. The unchanged M3
scorer, not Body Core, decides whether the refusal and breach survive. This
adapter does not close the open ingestion border or represent the strong
trace-auth refusal as closed evidence.

## Writer and authority routing

The adapter, never a source row, chooses Core envelope authority:

| Core event | Writer role / authority |
| --- | --- |
| `m3_adapter_started` | `controller` / `wire_diagnostic` |
| `m3_source_row_carried` | `observer` / `external_observation` |
| `m3_episode_record_declared` | `observer` / `external_observation` |
| `state_item_admitted` | `controller` / `controller_transition` |
| `m3_boundary_decision_receipt` | `controller` / `wire_diagnostic` |

Projection requires the exact adapter writer id, role, and authority for every
adapter-owned kind. Source `trust`, `asserted_trust`, attacker id, attack
surface, `allowlist_ok`, and verdict prose remain payload fields. Rehashing a
lineage with a different but Core-legal writer/authority pair must still be
refused by the adapter.

This is local routing discipline, not cryptographic writer authentication.

## Projection and scorer sovereignty

Projection must:

1. run full Core replay and reject stale view claims;
2. require exactly one adapter start and its indexed pins;
3. validate adapter-owned writer/authority routing;
4. reconstruct every source row by contiguous index and per-row digest;
5. enforce aggregate source and episode digests;
6. enforce the Track-A item, warrant, receipt, and no-lifecycle/no-placement
   correspondence above;
7. require no M3 state items or receipts on Track B;
8. return the source ledger field-for-field.

For fresh scoring, source and projection are copied to separate temporary paths.
Historical `cell_verdict` rows are removed from both. The unchanged
`harness.score_redteam` CLI is invoked with the same pinned episode. Newly
appended verdict rows are compared canonically under the predeclared exception:

```text
non-semantic fields = {"ts"}
```

The adapter may not reproduce `organ_projection`, reason normalization,
precondition checks, store-digest computation, cell logic, or world-oracle
extraction. Those remain scorer authority.

Pass requires exact source/projected ledger digests and equality of fresh
verdict rows and evidence, not only the expected verdict labels in the source
index. The indexed labels are a fail-closed preflight against accidental corpus
substitution.

## Refusal legs required before review

An implementation review must reproduce at least these named probes:

1. source mutation without rehash breaks Core lineage;
2. a rehashed carried-row mutation loses to the adapter-start aggregate digest;
3. a stale materialized-view claim loses to replay;
4. an unknown source kind, unknown field, or opaque escrow key refuses;
5. a ledger or episode digest/index mismatch refuses before projection;
6. missing, wrong-kind, non-causal, or coordinate-drifted decision bindings
   refuse through the shared helper;
7. missing, duplicate, orphan, or source-semantic-disagreeing Track-A receipts
   refuse;
8. a source boundary row naming a record absent from the pinned episode refuses;
9. lifecycle, placement, or metabolic events affecting an M3 item refuse even
   when correctly source-bound;
10. a rehashed adapter-owned event under a different Core-legal writer or
    authority refuses;
11. Track B cannot mint an M3 state item or receipt from `minted`,
    `poison_offered`, or `asserted_trust`;
12. existing verdict rows cannot ride into fresh scorer comparison;
13. the unchanged scorer still fails a store-digest precondition mismatch;
14. the full eleven-ledger matrix reproduces exact fresh scorer evidence,
    including all three live-channel breaches, the defended close, and the
    asserted-trust ingestion breach.

The shared Core and M3 component suites must also remain green. Mock tests remain
wire tests only.

## Deterministic work disclosure

The proposed shape writes eighteen Core rows for each nine-row Track-A ledger:
one start, two record declarations, two admissions, nine carried rows, and four
boundary receipts. Each four-row Track-B ledger writes five Core rows: one start
and four carried rows. Across eleven separate lineages this is 172 Core rows and
1,397 append-prefix rows (`n(n-1)/2` summed per lineage).

This is a disclosed deterministic work proxy, not latency, a cost win, or an
optimization target. Full replay and quadratic append remain admitted.

## Non-claims

An endorsed and implemented adapter would not show that:

- Body Core creates or protects earned trust;
- Body Core closes the live-channel or ingestion breaches;
- Core's local writer roles are authenticated principals;
- M3's authority sidecar is reconstructed as generic body state;
- the strong IN-1 refusal was transported as closed evidence;
- the three earned M2/M3/X2 results compose causally;
- an engine learned, resisted, or changed behavior;
- any scientific mechanism is licensed.

The narrow claim is preservation: the Core envelope and adapter-specific audit
receipts can carry M3's already-closed distinction without rewriting it.

## Review budget

One independent cold proposal review may **ENDORSE** or **BLOCK** this exact
direction. A block licenses one bounded repair and one fresh final review, then
close. The exact review surface is frozen in
[`body_core_m3_adapter_proposal_review_manifest.json`](body_core_m3_adapter_proposal_review_manifest.json).
Reviewers should answer:

1. Is the Track-A materialized-record plus decision-receipt mapping informative
   without falsely encoding offer/withhold as generic Core policy state?
2. Does the Track-B no-state rule preserve refusal/breach asymmetry, or merely
   avoid the hard authority question?
3. Is the eleven-ledger corpus the smallest honest closed set, including null,
   breach, defense, and ingestion outcomes?
4. Are scorer sovereignty and historical-verdict stripping sufficient after the
   M3 negation-oracle failure?
5. Can any attacker-controlled field become Core authority, or any valid source
   binding become authorization?
6. Are adapter jurisdiction, foreign items, and unclaimed items explicit enough
   for a later composition review?

An endorsement licenses implementation plus a disclosed mock/wire preservation
run only. It does not license engine contact or a new M3 finding.
