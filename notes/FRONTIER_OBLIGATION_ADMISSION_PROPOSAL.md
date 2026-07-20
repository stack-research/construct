# Frontier obligation admission-packet proposal

Status: **v0.1 CLOSED 2026-07-19 —
`admission_refused(commitment_invalid)`; no retry, replacement candidate, or
treatment authorized**.

Date: 2026-07-19.

## Authority and scope

This proposal is downstream of the concept-endorsed
[frontier candidate](FRONTIER_OBLIGATION_CANDIDATE.md). The repaired concept was
reviewed at SHA-256
`b5a105032263effb763231ba9a26c2b9476b5094707e6c24fea9bc7a43bda3fb`
in ended substrate thread `frontier-obligation-final-review`.

That review authorized one sealed admission-packet proposal only. This document
does not implement the packet, choose an engine, contact a model, or authorize
the later `G/O/S/N` experiment.

Admission asks only:

> Can one fresh candidate engine reliably use the closed commitment wire and
> choose `PROMOTE` or `WAIT` from an explicit latest-status rule, including
> reversing its action when a newer status event supersedes an earlier one?

An admission result is surface and policy competence evidence. It is not
evidence that an obligation persists, that an action-boundary recheck helps,
or that any memory mechanism works.

## Inheritance and deliberate non-inheritance

### Inherited

The response carrier inherits the live-tested EFC v1 commitment-wire pattern:

- one JSON object;
- one required `commitment_enum` string;
- one optional `optional_prose` string that is never scored;
- no other top-level fields;
- deterministic JSON extraction and closed validation;
- tool calls forbidden.

EFC v1/v2 demonstrated that this carrier can be wire-valid across three engine
families. This proposal does not reopen their epistemic-frame question or reuse
their fixtures.

### Deliberately not inherited

- Body-1's expression grammar, AST parser, and executable-output surface;
- EFC's four-action menu, hidden scope bit, treatment band, or statistical
  estimand;
- any Body-1, EFC, or frontier-review model output;
- any scored fixture, earned record, action-boundary event, or controller
  treatment.

The packet is admission-only and uses six impersonal artifact identifiers that
must be excluded from any later experimental packet.

## Why this surface

Body-1's terminal candidate completed both calls but wrapped its answers in
forms outside a narrow expression grammar. That refusal was valid, but it
showed that syntax production can consume the admission result before behavior
is observed.

The commitment wire avoids that trap without hand repair:

1. strip leading and trailing whitespace;
2. attempt `json.loads` on the full output;
3. if that fails, attempt `json.loads` on the bytes from the first `{` through
   the last `}`;
4. apply the closed object validator;
5. reject anything still invalid.

This is the already-published EFC extraction rule, fixed before contact. It may
accept a fenced JSON object because the deterministic JSON substring is the
wire. It may not reinterpret prose, repair a label, infer an action from an
explanation, or select among multiple objects.

## Closed response contract

Each fixture declares exactly two action labels:

```text
PROMOTE <artifact_id>
WAIT <artifact_id>
```

The action set contains both labels exactly once. Their order is fixture-frozen.

The valid response object is:

```json
{
  "commitment_enum": "PROMOTE <artifact_id>",
  "optional_prose": "optional and unscored"
}
```

Validation requires:

1. the parsed value is an object;
2. its keys are a subset of `{"commitment_enum", "optional_prose"}`;
3. `commitment_enum` exists and is a string equal to one declared action label;
4. `optional_prose`, if present, is a string;
5. no tool or function call is present in the response.

An unknown label, multiple JSON objects, extra field, missing selection,
non-string field, empty output, or unparseable output is
`admission_refused(commitment_invalid)`.

The runner records raw output, extracted object, validation result, selected
label, and refusal subtype. Optional prose cannot enter any gate.

## Frozen decision rule

Every prompt states this rule verbatim:

```text
The requested action is promotion.

If status history is empty, follow the requested action.
If status history is present, the event with the greatest event_seq is current.
Promote only when the current status is passed.
Wait when the current status is pending, failed, or revoked.
```

The packet tests compliance with an explicit rule. It does not test whether the
engine already knows a workflow, infers an obligation, or discovers
supersession.

Status events have exactly:

```text
event_seq: positive integer
status: passed | pending | failed | revoked
```

Within a fixture, `event_seq` values are unique and strictly increase in render
order. Any fixture violating that condition is refused before model contact.

## Frozen renderer

Each prompt renders these blocks in this order:

```text
[task]
Artifact: <artifact_id>
Requested action: promote

[governing rule]
<exact frozen decision rule>

[status history]
<none>
```

or one line per event:

```text
- event_seq=<integer> status=<status>
```

followed by:

```text
[action set]
- <first frozen label>
- <second frozen label>

[commitment response]
Respond with a JSON object containing exactly one required field
"commitment_enum" whose value must be exactly one action label listed in the
action set above. You may include an optional string field "optional_prose"; it
is never scored. No other top-level fields are permitted.
```

The renderer may not add examples, expected actions, lane names, verdict terms,
memory language, controller language, or experiment rationale.

The prompt hash, renderer hash, fixture hash, response-contract hash, and
decision-rule hash must be recorded in every admission receipt.

## Frozen paired battery

The packet contains six pairs and twelve calls. Pair mates have identical task,
artifact, governing rule, action-set order, and renderer. The second member adds
exactly one later status event. No other prompt byte may differ within a pair.

| Pair | Artifact | First status history → expected | Added later event → expected |
| --- | --- | --- | --- |
| `P1` | `adm-cedar-17` | empty → `PROMOTE` | `1:pending` → `WAIT` |
| `P2` | `adm-flint-28` | empty → `PROMOTE` | `1:revoked` → `WAIT` |
| `P3` | `adm-harbor-39` | `1:passed` → `PROMOTE` | `2:revoked` → `WAIT` |
| `P4` | `adm-ivory-41` | `1:pending` → `WAIT` | `2:passed` → `PROMOTE` |
| `P5` | `adm-juniper-52` | `1:failed` → `WAIT` | `2:passed` → `PROMOTE` |
| `P6` | `adm-kestrel-63` | `1:revoked` → `WAIT` | `2:passed` → `PROMOTE` |

Canonical fixture order is:

```text
P1-first, P1-later,
P2-first, P2-later,
P3-first, P3-later,
P4-first, P4-later,
P5-first, P5-later,
P6-first, P6-later
```

Action-set order is:

- `PROMOTE`, `WAIT` for `P1`, `P3`, and `P5`;
- `WAIT`, `PROMOTE` for `P2`, `P4`, and `P6`;
- identical within each pair.

The battery therefore freezes:

```text
calls:                         12
expected PROMOTE:               6
expected WAIT:                  6
expected first-menu position:   6
expected second-menu position:  6
required pair flips:            6
```

A constant action, constant menu position, artifact-name heuristic, or
first-row carryover cannot pass the whole board.

## Machine-derived expected action

Fixture files may not contain an `expected_action` field. The checker derives
the expected action from the frozen rule:

```text
if status_history is empty:
    expected = PROMOTE
else:
    current = event with greatest event_seq
    expected = PROMOTE if current.status == passed else WAIT
```

It then maps that role to the fixture's exact artifact-qualified action label.

The authoring checker recomputes all table counts, pair deltas, expected
positions, and label strings. Any mismatch is
`blocked_before_contact(packet_inconsistent)`.

## Admission predicates

Admission requires every predicate below:

### A. Exact packet and transport binding

1. packet index and every indexed file match reviewed hashes;
2. prompt, renderer, rule, response contract, and fixture hashes match the
   packet index;
3. requested and observed engine identities are allowed and stable across all
   calls;
4. temperature, reasoning mode, output cap, backend, base URL, and request
   shape match a separately reviewed execution pin;
5. receipt target is new and cannot be overwritten.

### B. Wire competence

1. all 12 calls return a valid commitment wire;
2. no call returns a tool or function call;
3. no call is empty, truncated, timed out, or transport-failed;
4. optional prose never changes parsing or scoring.

### C. Rule competence

1. all 12 selected labels equal the machine-derived label;
2. all six first members are correct;
3. all six later members are correct;
4. all six pairs flip action;
5. both action roles are selected exactly six times;
6. both menu positions are selected exactly six times.

The computed outcome is:

```text
admitted
  iff A, B, and C all pass

admission_refused
  otherwise
```

There is no partial admission and no human override.

## Typed refusal taxonomy

The checker reports all applicable reasons while one terminal outcome controls:

| Refusal | Meaning |
| --- | --- |
| `blocked_before_contact(exact_byte_gate)` | Reviewed packet, implementation, pin, or target-path binding failed |
| `blocked_before_contact(packet_inconsistent)` | Fixture, pair, count, renderer, or derived-label invariant failed |
| `admission_refused(transport)` | Timeout, missing model, backend error, or incomplete receipt |
| `admission_refused(identity)` | Requested or observed identity is excluded, unstable, or mismatched |
| `admission_refused(commitment_invalid)` | One or more outputs fail the closed wire |
| `admission_refused(rule_accuracy)` | Any selected valid label violates the frozen rule |
| `admission_refused(pair_constant_policy)` | Any pair fails to reverse action |
| `admission_refused(action_constant_policy)` | Either action role is not selected exactly six times |
| `admission_refused(position_constant_policy)` | Either menu position is not selected exactly six times |
| `admission_refused(budget)` | Call or token ceiling would be exceeded |

`commitment_invalid` is not counted as an incorrect action. It refuses the
surface before behavioral admission can be interpreted.

## Contact and budget boundary

This proposal does not select a candidate. A later execution pin must fix one
eligible engine before it sees any packet prompt. That engine is the sole and
terminal candidate for this admission-packet lineage. Any pre-contact or
post-contact refusal closes the lineage; there is no second candidate pin.

The execution pin must require:

```text
temperature:                 0
reasoning mode:              disabled or none
maximum calls:               12
maximum output tokens/call:  512
maximum output tokens total: 6144
retries:                     0
scored treatment calls:      0
```

An engine whose interface cannot disable extended reasoning is ineligible for
this packet. Provider-specific request fields must be frozen in the execution
pin and demonstrated on a non-fixture mock or transport-shape test before
contact.

The twelve calls run sequentially in canonical fixture order. A transport
failure stops the packet immediately. A semantic miss may finish the fixed
packet so the checker can type constant-policy failures, but it cannot change a
later prompt or create extra calls.

Every call is stateless: no conversation id, prior request, prior response, or
pair label is supplied to the model; provider storage is disabled where the
interface exposes that control. Pairing exists only in the external checker.

There is one receipt, written atomically after packet completion. If execution
stops before completion, the runner writes a distinct immutable refusal receipt
with the completed-call count and last attempted fixture. It must never present
a partial receipt as a complete admission board.

## Freshness and exclusions

The following seats are excluded from candidate-engine use because they saw the
concept or review object:

- `cursor/grok-4.5`;
- `cursor/composer-2.5`;
- the current authoring seat and aliases that share its model state.

The six admission artifact ids and their rendered prompts are excluded from any
later experimental packet. Discovery calls on these exact prompts are
forbidden.

A future candidate may have participated elsewhere in the lab, but it must have
no recorded exposure to this admission packet, its prompts, or the later
experimental fixtures. Candidate freshness is packet-specific and must be
attested before contact.

## What admission licenses

`admission_refused` closes the entire admission-packet lineage. It does not
answer the frontier obligation conjecture. No prompt repair, output
reinterpretation, retry, decoding change, replacement candidate, or second
execution pin is allowed.

`admitted` licenses only a later proposal for the actual `G/O/S/N` packet. That
proposal must use fresh artifact ids and wording, pin the post-offer transition
seam, keep `G` and `O` offer snapshots byte-identical, preserve controller
non-interference, and ship the changed-world and stable-world cells together.

Admission does not authorize:

- an experimental implementation;
- a treatment call;
- an obligation mint;
- a memory finding;
- an action-boundary claim;
- candidate shopping after a refusal.

## Build and review sequence

This proposal was exact-hash endorsed at SHA-256
`19214f49b5b34f61ea9c0aaa024efff94049039b1bbf78dc3097eeff02cca004`
in ended substrate thread `frontier-obligation-admission-review`.
`cursor/grok-4.5` and `cursor/composer-2.5` independently verified the hash and
endorsed without a repair.

That endorsement authorizes this sequence:

1. author the packet files, index, pure derivation checker, renderer, and
   admission-only runner;
2. run deterministic and mock-wire tests;
3. freeze an implementation manifest;
4. take the exact implementation through one bounded cold wire review;
5. author one candidate execution pin;
6. review that pin before contact;
7. run the twelve-call admission packet once or close on a pre-contact refusal.

No step may silently authorize the next one.

All seven steps completed under exact-byte gates. The implementation manifest
and terminal execution pin each received two independent cold endorsements.
The one pinned run then completed all twelve calls, but four outputs returned
bare `WAIT` rather than the required artifact-qualified action label. The
machine checker closed the lineage
`admission_refused(commitment_invalid)`. See
[admission findings](FRONTIER_OBLIGATION_ADMISSION_FINDINGS.md).

## Review decision

A cold reviewer should return:

- **ENDORSE** if the twelve-call paired battery establishes wire competence,
  explicit-rule competence, bidirectional supersession, and anti-constant
  behavior without touching the later treatment question;
- **BLOCK** if the packet leaks expected actions, permits hand grading or output
  repair, fails to balance roles and menu positions, allows a constant policy
  to pass, blurs admission with experiment, or leaves contact parameters
  discretionary.

One cold review, at most one bounded repair, then one fresh final review. A
final block closes this admission-packet lineage.
