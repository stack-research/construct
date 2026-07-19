# Body-1 implementation proposal

Status: **WIRE REVIEW CANDIDATE — exact packet implemented; deterministic mock
wire scored; no real-engine contact authorized**.

Date: 2026-07-19.

Packet authority:
[`SPEC_BODY_1_EXECUTABLE_CONSEQUENCE.md`](SPEC_BODY_1_EXECUTABLE_CONSEQUENCE.md)
and packet-index SHA-256
`22d7e46d4f1598247acefdbb47bf60b3b02050a16697a4ab5cb1ba077b1685f5`.

Implementation review root:
[`harness/body1_implementation_manifest.json`](../harness/body1_implementation_manifest.json).

Canonical mock wire:
[`body1-partial-binding-977d88cd.body1.jsonl`](../runs/body1/wire/body1-partial-binding-977d88cd.body1.jsonl).

This proposal does not amend the reviewed packet. It implements its already
declared surface and must close rather than repair that packet if wire review
finds a normative widening.

## Milestone and oracle

Milestone: **Body-1 — executable consequence recurrence**.

The answer oracle is the pinned CPython 3.14.6 process executing one frozen
program. The offer-eligibility oracle is a separate structural computation over
the frozen function signature, bound literals, class placement, and instance
call arity. Neither reads a model explanation or self-label.

The positive mock wire requires:

```text
R runtime-pass
C runtime-pass
A TypeError
X TypeError
```

It also requires protected projection, append-only replay, no erasure,
`cost_C < cost_R`, and every admission gate. The binding-required fork is the
loses-condition: L2 must withhold the present but ineligible record, while L0
matches L2 quality at fewer deterministic governance steps.

## Implementation shape

### Packet-bound primitives

[`harness/body1.py`](../harness/body1.py) owns only deterministic primitives:

- exact packet and file hashing;
- the two-form AST classifier;
- source-derived scope arithmetic;
- the single renderer and its hash;
- runtime-pin verification;
- bounded subprocess execution;
- identity record construction, protected projection, and hot-cost replay.

The classifier never returns executable source. It returns
`bare_partial` or `nonbinding_partial`; that id selects the fixture's
packet-authored expression. The model's raw bytes are recorded for independent
reclassification and are never inserted into the temporary program.

### Engine boundary

[`harness/body1_engine.py`](../harness/body1_engine.py) is the only model-call
adapter. It renders one stateless call with temperature 0 and a 256-token
ceiling. Its mock policy is deliberately simple:

```text
earned record offered -> nonbinding_partial
otherwise             -> bare_partial
```

That policy exists only to exercise the causal wire. Mock rows disclose
`wire_integration_only`; the scorer can emit `wire_pass`, never behavioral
`pass`.

[`harness/probe_body1.py`](../harness/probe_body1.py) implements the two fresh
admission calls. Known discovery and review seats are refused before client
construction. The receipt binds packet hash, renderer hash, requested and
observed model identities, backend, surface-control pass, and ignorance-probe
failure direction.

### Pre-contact gate

[`harness/check_body1_fixture.py`](../harness/check_body1_fixture.py)
recomputes before any scored contact:

1. exact reviewed packet-index hash and all thirteen indexed files;
2. the ended final-review trace and both exact-hash endorsements;
3. the pinned executable, build details, version, platform, and machine;
4. all four inherited component hashes;
5. all six source-derived scope relations;
6. prompt leak absence;
7. both authored forms and twelve rejected mutation families;
8. all twelve runtime directions and program/stdout hashes;
9. P/P/P/U cost state (`C=276 < R=384`);
10. renderer and engine-specific admission bindings.

Real mode fails closed without a matching probe receipt. Mock mode bypasses only
the engine-specific probe and discloses that bypass.

### Sequence runner

[`harness/run_body1.py`](../harness/run_body1.py) writes one append-only trace:

```text
admission
  -> E1 bare action -> pinned TypeError -> frozen counterfactual pass -> mint
  -> protected projection -> attacker foreground -> projection recheck
  -> C/A/X prune
  -> cost-state gate
  -> P/P/P residence
  -> C/A rematerialize
  -> R/C/A/X recurrence
  -> L0/L1/L2 scope fork
  -> conditional L1 single-record ablation
  -> final protected projection
```

The existing `Record`, M3 protected projection, `Ledger`, and X2 `HotStore`
remain the state and actuation surfaces. No packet-pinned component was edited.

### Independent scorer

[`harness/score_body1.py`](../harness/score_body1.py) distrusts runner claims.
It:

- reclassifies every raw response;
- rebuilds every prompt and offer set;
- re-executes every selected frozen program;
- reconstructs the consequence mint and full lineage;
- recomputes protected projections;
- pairs every hot-state operation with its prior projection;
- replays every hot set and cost row;
- verifies fork identity and R/C/A/X direction;
- checks the scope withholding, harm, and single-record ablation;
- computes all nine reviewed cells.

Logged selected ids, runtime outcomes, totals, sidecars, and `identity_ok`
booleans cannot manufacture the positive cell.

## Runtime containment result

Every executed program is packet-authored and runs with:

- exact pinned executable and flags `-I -S -B`;
- no shell;
- closed stdin;
- a fresh temporary working directory;
- a minimal environment;
- a two-second wall timeout;
- a 4,096-byte combined output ceiling;
- exact pass stdout and empty stderr.

The implementation attempts the reviewed 64 MiB `RLIMIT_AS` target before each
launch. This Darwin launch path rejects lowering that limit before `exec`, so
each row records `unsupported_by_launch_path`; the child is then launched with
all remaining mandatory bounds. Wire review must decide whether this satisfies
the packet's explicit “where the platform supports it” clause. It is not hidden
as an enforced limit.

## Wire result

The canonical ledger contains a deterministic mock run plus independently
appended scorer rows:

| Cell | Wire verdict |
| --- | --- |
| `B1-composition-holds` | `wire_pass` |
| `B1-attribution-confounded` | `not_engaged` |
| `B1-authority-regression` | `not_engaged` |
| `B1-recovery-regression` | `not_engaged` |
| `B1-quality-regression` | `not_engaged` |
| `B1-pure-tax` | `not_engaged` |
| `B1-scope-refusal` | `wire_pass` |
| `B1-governance-should-lose` | `wire_pass` |
| `B1-interface-blocked` | `not_engaged` |

This demonstrates wiring only. The mock was authored to move in the required
direction and is not evidence that a model will do so.

## Verification and tamper coverage

[`tests/test_body1.py`](../tests/test_body1.py) contains fifteen checks covering:

- exact packet/review/runtime gate;
- closed parser and source-derived eligibility;
- all twelve runtime directions;
- complete mock composition and both loses cells;
- real-run refusal before engine construction;
- exclusion before probe client construction;
- independent replay of logged cost and selected form;
- raw-execution interface closure;
- authority and recovery regressions;
- direction-blind R/C failure;
- honest scope null;
- append-only computed verdicts.

The neighboring Body-0, M2, M3, and X2 suites remain the regression boundary.

## Wire-review decision

Review the exact implementation-manifest hash and canonical ledger. Return:

- **ENDORSE** only if the code implements the reviewed packet without adding
  answer discretion, semantic scope, raw execution, a new state surface, or a
  post-contact repair path;
- **BLOCK** if any such widening exists, if the scorer can be ridden by logged
  claims, or if the disclosed address-space result violates the sealed runtime
  clause.

An endorsement may license a separate engine-admission proposal. It does not
itself license contact, a scored ledger, a memory finding, or a composition
claim.
