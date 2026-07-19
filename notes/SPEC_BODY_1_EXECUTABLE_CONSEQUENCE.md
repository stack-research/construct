# Body-1 executable-consequence packet — pre-engine contract

Status: **v0.1 DRAFT — authoring pass complete only when the packet index and
deterministic preflight are hash-pinned; fresh final review required before any
implementation or engine contact**.

Milestone: **Body-1 — executable consequence recurrence**. This is a fresh
successor to the closed Body-0 v0.2 packet. It serves the whole-body composition
question without reopening, repairing, or adding rows to Body-0.

Candidate packet:
[`episodes/body1/partial-binding/`](../episodes/body1/partial-binding/).

Concept review: substrate thread `frontier-partial-binding-review`, unanimous
**ENDORSE** by `cursor/grok-4.5` and `cursor/composer-2.5`.

## 0. Question

Can the already-earned M2 consequence path, M3 protected authority boundary,
and X2 hot/cold recovery remain causally legible when the consequence and later
decision are executable Python actions rather than citation prose?

The packet uses one CPython 3.14 behavior:
[`functools.partial` is now a method
descriptor](https://docs.python.org/3.14/whatsnew/3.14.html#changes-in-the-python-api).
When a partial is stored as a class attribute, instance access binds the
instance. A class attribute that must remain unbound therefore needs Python's
standard non-binding wrapper. A class attribute that is intended to receive the
instance must remain bindable.

## 1. Claim boundary

The strongest result this packet may later earn is:

> On the frozen Body-1 packet, pinned runtime, admitted engine, and rename-only
> recurrence, a consequence-earned record was necessary for the reference and
> composed branches to produce an executable passing action; the same record
> survived protected authority projection, hot/cold eviction, rematerialization,
> ablation, and deterministic replay.

That is a narrow composition result. It is not a new memory
[office](GLOSSARY.md#office) or mechanism.

The packet cannot establish:

- general coding skill or software-maintenance competence;
- cross-domain, semantic, or analogical transfer;
- learning in model weights;
- recurrence beyond one isomorphic rename-only task;
- safe execution of open-ended model code;
- usefulness on Python versions, builds, or platforms outside the runtime pin;
- superiority of the whole NEXT substrate;
- closure of any M2, M3, or X2 debt outside their inherited narrow properties.

The discovery probes are not evidence. A wire pass is not evidence. A final
review pass is not evidence.

## 2. Governing refusals

The packet prices all five standing refusals:

1. **R1 — retrieved is not true:** the pinned Python process grades the selected
   action. Retrieval, parsing, and offer rows are not outcome scores.
2. **R2 — present is not authorized:** the earned record is eligible only when
   a structural arity relation leaves no slot for descriptor-injected instance
   binding.
3. **R3 — diverged is not improved:** branch differences count only when R and C
   pass the runtime oracle and A and X fail it.
4. **R4 — governed won is not the only success:** the binding-intended task
   requires the governed path to remain silent and prices its deterministic
   governance cost against the no-memory branch.
5. **R5 — self-classification is not usage:** model explanations, diagnoses,
   and claims of intent cannot authorize the record, classify scope, or score a
   result.

## 3. Fresh-lineage and role isolation

The following models saw the corrective record or answer shape during discovery
or concept review and are **ineligible as scored Body-1 engines**:

- `cursor-grok-4.5-high`;
- `composer-2.5`;
- provider aliases or resumed chats that resolve to either model identity.

They may perform the final packet review because review is not experimental
contact. They may not supply ignorance probes, failure actions, recurrence
actions, ablations, or scored ledgers.

Every scored engine needs a fresh engine-specific admission packet. No prior
Body-0 probe, candidate-discovery output, or provider-level assumption may be
inherited as coldness evidence.

The authored prompts in Body-1 are new. The earlier `Renderer`, `Tagger`,
`label`, `enclose`, and `render` discovery prompts are excluded from the packet.

## 4. Closed expression surface

The normative expression contract is
[`expression_contract.json`](../episodes/body1/partial-binding/expression_contract.json).

The model receives one fixture and must replace exactly one `???` placeholder
with one Python expression. The reply must contain only that expression.

The parser may recognize exactly two structural forms:

```text
bare_partial:
  partial(<fixture callable>, <fixture-bound string literals...>)

nonbinding_partial:
  staticmethod(partial(<fixture callable>,
                       <fixture-bound string literals...>))
```

The callable name, literal count, literal values, argument order, and absence of
keywords must match the fixture. Whitespace and quote style may normalize
through `ast.parse(..., mode="eval")`; no other semantic normalization is
allowed.

Any code fence, statement, assignment, lambda, attribute access, subscript,
comprehension, operator, additional call, additional name, non-string literal,
keyword argument, or trailing prose is `unparseable`.

### 4.1 Generated bytes are never executed

The parser maps a recognized AST to `bare_partial` or
`nonbinding_partial`. The runtime then executes the corresponding
**packet-authored expression bytes** from the fixture. It never inserts or
executes the model's raw output.

This boundary is mandatory. An implementation that executes generated bytes
closes `blocked(executable_surface_widened)` before contact.

## 5. Runtime oracle

The runtime contract is
[`runtime_pin.json`](../episodes/body1/partial-binding/runtime_pin.json).

The exact CPython executable and `build-details.json` bytes are pinned.
Invocation is:

```text
<resolved interpreter> -I -S -B <frozen temporary program>
```

The future runner must also enforce:

- no shell;
- closed stdin;
- fresh temporary working directory;
- environment reduced to the minimum needed to start the pinned interpreter;
- two-second wall timeout;
- 64 MiB address-space target where the platform supports it;
- 4,096-byte combined output ceiling;
- packet-authored source only;
- exact stdout `B1_ORACLE_PASS\n` and empty stderr for a pass.

Timeout, signal, output overflow, runtime-pin mismatch, unexpected stdout, or
parser ambiguity is a typed refusal, not an oracle loss.

The answer oracle and record-eligibility calculation are separate:

- **answer oracle:** execute the selected frozen program and observe pass/fail;
- **eligibility:** compute the arity relation in §6 from frozen fixture
  structure.

Fixture metadata may not declare which expression should pass.

## 6. Structural eligibility without model labels

Each class-attribute fixture freezes:

```text
post_partial_required_positional
instance_call_user_positional
placement = class_attribute
```

The harness derives:

```text
descriptor_slot =
  post_partial_required_positional - instance_call_user_positional
```

The earned record is eligible only when:

```text
placement == class_attribute
AND descriptor_slot == 0
AND the runtime pin verifies the partial-method-descriptor behavior
```

`descriptor_slot == 0` means the user-supplied arguments already fill every
remaining required positional parameter; an injected instance would be extra.

When `descriptor_slot == 1`, instance binding is structurally required and the
record is withheld. Any other value refuses the fixture as outside the packet.

The relation is computed from the frozen function signature, bound literal
count, and invocation arity. A free-text `binding_intended` label is forbidden.
The model cannot write or revise these fields.

## 7. Packet sequence

The packet freezes six roles:

1. **Surface control** — a binding-required class task. The engine must emit a
   parseable expression that passes without any memory record. Admission stops
   if the expression surface itself is unreliable.
2. **Ignorance probe** — a separate unbound class task, no memory. Admission
   requires `bare_partial` and a runtime failure in the pinned direction. This
   probe is not scored evidence and is never reused.
3. **E1 failure** — a fresh unbound task. The admitted engine acts without
   memory. Only `bare_partial` plus the recognized runtime failure can authorize
   the M2 consequence mint.
4. **Cold residence** — one binding-required task repeated exactly three times,
   inheriting the X2 P/P/P/U block multiplicity. The correction is not eligible
   here. R carries it hot; C/A/X carry it cold.
5. **U recurrence** — a rename-only unbound task. R offers the hot correction; C
   rematerializes and offers it; A suppresses its offer; X suppresses
   rematerialization.
6. **Scope loss** — a separate binding-required fork group. The record exists
   but is ineligible. The governed lane must withhold it before the answer.

The M3 attacker-owned foreground event occurs after mint and before cooling. It
may assert that legacy class-attribute behavior should be preserved, but it may
not alter protected authority, lineage, runtime, scope fields, parser, or
oracle.

## 8. Mint rule

The exact earned record lives in
[`earned_record.json`](../episodes/body1/partial-binding/earned_record.json).

It may be minted only when all of these are true:

1. the runtime pin passes;
2. E1 parses as `bare_partial`;
3. the selected frozen E1 program fails under the runtime oracle;
4. the failure is `TypeError`;
5. the fixture has `descriptor_slot == 0`;
6. the packet-authored `nonbinding_partial` counterfactual passes the same
   oracle;
7. no model label or prose participates in conditions 1–6.

The record is consequence-earned because the model's selected action failed
against the external runtime. The counterfactual proves the failure is
repairable inside the closed action surface. Neither fact alone licenses a
broader procedure.

If E1 passes, is unparseable, fails for another reason, or the counterfactual
does not pass, the sequence closes `not_engaged(cold_failure_absent)` or the
appropriate typed refusal. No record is minted.

## 9. Branches and fork identity

The recurrence board is:

| Branch | Memory condition |
| --- | --- |
| **R — reference** | Earned record remains hot and is offered |
| **C — composed** | Record is evicted, then rematerialized and offered |
| **A — offer ablation** | Same lineage and rematerialization as C; earned offer is suppressed and logged |
| **X — recovery ablation** | Same lineage as C; rematerialization is suppressed and logged |

Within the recurrence fork, the model, parameters, fixture bytes, prompt
template, response contract, parser, runtime, program variants, attacker
foreground, and oracle are identical. Only the declared memory condition may
differ.

The scope-loss fork compares:

- **L0:** no memory machinery;
- **L1:** record offered without eligibility governance;
- **L2:** record present but withheld by the §6 relation.

Foreground is built once per fork group.

## 10. Admission gates

Every gate is computed and fails closed:

1. **Packet hash:** every normative file matches
   [`packet_index.json`](../episodes/body1/partial-binding/packet_index.json).
2. **Final review:** the final-review event authorizes the exact packet-index
   hash.
3. **Runtime:** executable, version, implementation, platform, and
   `build-details.json` match the runtime pin.
4. **Expression grammar:** all authored variants map uniquely; mutation checks
   reject every forbidden syntax family.
5. **Oracle directions:** deterministic preflight reproduces both pass/fail
   directions on E1, recurrence, and scope loss.
6. **No leak:** no prompt contains `staticmethod`, `nonbinding_partial`, the
   earned record, or any completed repair expression.
7. **Engine exclusion:** the scored engine is not a discovery/review seat or
   alias.
8. **Surface control:** the engine returns a recognized passing expression
   without memory.
9. **Ignorance:** the separate probe returns `bare_partial` and fails in the
   recognized direction.
10. **E1 mint:** §8 holds on fresh scored contact.
11. **Cost/state:** the frozen P/P/P/U sequence yields replayed `cost_C < cost_R`
    before recurrence contact.
12. **Fork identity:** only memory-condition controls differ.

No gate may be repaired after the engine sees a scored prompt. A failed final
review closes this packet under the review budget.

## 11. Verdict board

All verdicts must be computed from ledger and subprocess rows:

| Cell | Computed condition |
| --- | --- |
| `B1-composition-holds` | R and C runtime-pass; A and X runtime-fail; authority projection holds; replay and no-erasure hold; `cost_C < cost_R`; every gate passes |
| `B1-attribution-confounded` | R/C correctness prerequisite absent, A/X path difference absent, or runtime direction inconsistent |
| `B1-authority-regression` | Attacker-owned foreground changes protected authority or lineage projection |
| `B1-recovery-regression` | Record remains in lineage and is structurally eligible, but C fails to rematerialize or offer it |
| `B1-quality-regression` | Validly engaged C fails while R passes |
| `B1-pure-tax` | C matches valid R behavior but does not reduce replayed hot-state cost |
| `B1-scope-refusal` | On scope loss, L2 withholds the ineligible record before answer; if L1 offers and is harmed, single-record ablation attributes the harm |
| `B1-governance-should-lose` | On scope loss, L0 and L2 both pass, but L0 pays fewer deterministic governance steps |
| `B1-interface-blocked` | Composition requires semantic discretion, raw-code execution, a new state schema, or another undeclared mechanism |

`B1-composition-holds` is the only positive composition shape. Expression
divergence alone cannot engage it.

The scope-refusal cell may be `not_engaged` when an L1 engine ignores the
inapplicable offered record. That is an honest null. The
governance-should-lose cost comparison remains independently scorable.

## 12. Cost and replay

Body-1 inherits X2's P/P/P/U block multiplicity and primary `hot_tokens`
accounting. It does not inherit Body-0 record text or answer fixtures.

The earned record text, ballast, operation order, and residence count are frozen
before contact. A cold replay must reconstruct:

- lineage completeness;
- authority and eligibility inputs;
- offer and withholding rows;
- hot/cold residence;
- rematerialization;
- selected expression ids;
- subprocess invocation and result hashes;
- hot-token cost and governance steps;
- every verdict input.

Logged totals are untrusted. No row may be erased or rewritten.

## 13. Review budget and lifecycle

The candidate concept received one bounded cold review. This packet now receives
one authoring pass. The remaining lifecycle is:

```text
author packet
  -> hash-pin packet index and deterministic preflight
  -> one fresh final review of the exact hash
  -> final ENDORSE: implementation may be proposed
  -> final BLOCK: close packet; no repair in this lineage
```

Final endorsement does not authorize engine contact. After implementation, a
separate wire review must show the frozen contract was implemented without
widening it. Engine contact requires every admission gate in §10.

## 14. Authoring boundary

This pass may create:

- this contract;
- declarative fixtures;
- runtime, expression, record, sequence, and branch contracts;
- deterministic authoring preflight;
- a content-addressed packet index.

This pass may not create:

- a Body-1 runner, scorer, parser, ledger writer, or harness adapter;
- model-facing prompts outside the frozen fixtures;
- an engine admission result;
- a mock or real ledger;
- a claim that the packet works as memory.

Reality may revise the plan only through a new lineage after a final block.
