# Frontier episode candidate — CPython 3.14 partial binding

Status: **ADMISSION REFUSED — fixed candidate timed out on the first neutral
control; no receipt, ignorance call, scored run, or Body-1 finding**.

Date: 2026-07-19.

This note records a bounded search result after the Body-0 v0.2
`not_engaged` close. It is a proposal, not a specification or finding. Any
sealed packet must enter a fresh lineage; nothing here reopens or repairs the
contacted Body-0 packet.

The resulting normative contract is
[SPEC_BODY_1_EXECUTABLE_CONSEQUENCE.md](SPEC_BODY_1_EXECUTABLE_CONSEQUENCE.md);
its content-addressed root is
[`packet_index.json`](../episodes/body1/partial-binding/packet_index.json).

Walkthrough handoff:
[When earned parts do not yet make an earned whole](walkthrough/20_BODY_0_COMPOSITION.md).

## Milestone served

Candidate successor to Body-0's earned-property composition question.

The candidate does not propose a new memory
[office](GLOSSARY.md#office) or mechanism. It replaces the citation surface
that failed to engage with an executable action/consequence surface: an engine
writes one Python expression, and the pinned runtime either passes or fails the
assertion.

## Candidate world change

In Python 3.14, `functools.partial` became a method descriptor. A partial stored
as a class attribute now binds the instance when accessed through that
instance. Code that intends the older non-binding behavior must wrap the partial
in `staticmethod`.

The external source is the official
[Python 3.14 porting guide](https://docs.python.org/3.14/whatsnew/3.14.html#changes-in-the-python-api).
The local candidate runtime is CPython 3.14.6. Its
`build-details.json` exists and identifies the installed 3.14.6 build.

The change is useful experimentally because it supplies both directions:

- when instance binding is unintended, bare `partial(...)` fails and
  `staticmethod(partial(...))` passes;
- when instance binding is intended, bare `partial(...)` passes and the
  non-binding wrapper fails.

The second case is the required
[governance](GLOSSARY.md#governance)-should-lose branch. The record must remain
scoped to the program's binding intent rather than becoming a global “wrap
every partial” rule.

## Deterministic preflight

On the pinned runtime, this stale expression:

```python
from functools import partial

def label(prefix, value):
    return f"{prefix}{value}"

class Renderer:
    render = partial(label, "id:")

Renderer().render("42")
```

raises:

```text
TypeError: label() takes 2 positional arguments but 3 were given
```

Replacing the class attribute with
`staticmethod(partial(label, "id:"))` produces `id:42`.

For the loses direction:

```python
def render(prefix, owner, value):
    return f"{prefix}{owner.name}:{value}"

class Renderer:
    name = "alpha"
    format = partial(render, "id:")
```

`Renderer().format("42")` produces `id:alpha:42`. Adding `staticmethod` instead
fails because the intended owner argument is no longer bound.

These are runtime observations, not model-memory findings.

## Cold model preflight

Two models were invoked separately through the Cursor agent CLI in empty
temporary workspaces, read-only, with tools and internet forbidden in the
prompt:

- `cursor-grok-4.5-high`;
- `composer-2.5`.

For the first unbound-intent task, both cold models returned:

```python
partial(label, "id:")
```

The pinned runtime rejects that expression. With only the scoped consequence
record below, both returned:

```python
staticmethod(partial(label, "id:"))
```

The runtime accepts it.

A held-out `Tagger.tag` task reproduced the same split on both models:

```text
cold:    partial(enclose, "<", ">")                 -> runtime failure
record:  staticmethod(partial(enclose, "<", ">"))  -> pass
```

On the binding-intended loses task, both record-bearing models returned bare
`partial(render, "id:")`, which passes. They did not over-apply the correction.

These calls were candidate discovery only. They were not run through the
harness, were not append-only evidence, did not use
[fork identity](GLOSSARY.md#fork-identity) or
[ablation](GLOSSARY.md#ablation_run), and cannot support a scientific or
integration claim. A reviewed packet would need new, sealed prompts and fresh
contact.

## Proposed earned record

The E1 action should be graded by executing it under the pinned interpreter.
Only a recognized binding failure may mint the record:

> On CPython 3.14, `functools.partial` objects implement method-descriptor
> binding. When a partial is stored as a class attribute and the intended call
> must remain unbound to the instance, preserve that intent with Python's
> standard non-binding class-attribute wrapper.

The harness, not the model, must derive eligibility from:

- the pinned runtime identity;
- class-attribute placement;
- the observed extra-instance-argument failure;
- the later task's declared binding intent.

The model may not self-authorize the record by naming the failure.

## Candidate sequence

1. **E1 failure:** a cold engine fills one expression for an unbound-intent
   class attribute. The runtime executes the assertion. A stale bare partial
   fails.
2. **Mint:** the external consequence plus pinned runtime authorizes the scoped
   correction record.
3. **Residence:** the record passes through the existing Body-0 hot/cold
   sequence without changing component machinery.
4. **U recurrence:** a held-out unbound-intent task requires the same runtime
   distinction with different function and class names.
5. **L loses:** a binding-intended task keeps the record present but
   unauthorized; bare partial is correct.

If composed later, R/C/A/X retain their Body-0 meanings. R and C must pass the
executed assertion. A and X must fail it. A prose or expression difference
without that direction is not engagement.

## Admission gates

A fresh packet must fail closed unless all of these hold:

1. **Runtime pin:** interpreter version, executable identity, and
   `build-details.json` are frozen.
2. **[Oracle](GLOSSARY.md#oracle-score) execution:** candidate expressions are
   parsed under a narrow grammar, inserted only at the declared placeholder,
   and executed in a resource-bounded subprocess.
3. **[Cold ignorance](GLOSSARY.md#ignorance-probe):** the admitted engine fails
   E1 and a separate held-out
   recurrence probe in the predeclared stale direction.
4. **Surface competence:** the same engine passes neutral expression-format
   controls and succeeds when given the scoped consequence record.
5. **No answer leak:** neither task prose nor option menu contains the completed
   repair expression.
6. **Causal necessity:** R/C pass; A/X fail; the same runtime assertion grades
   all four.
7. **Scope loss:** the binding-intended branch passes only when the correction
   is withheld or correctly ignored.
8. **Fork identity and replay:** task bytes, runtime, parser, subprocess limits,
   oracle, and [foreground](GLOSSARY.md#foreground-data) rendering are identical
   within each fork.

## Why this candidate is better than the contacted Body-0 packet

- The answer is not restated in the question.
- The oracle executes an action rather than interpreting citation prose.
- Cold failure and record-enabled success were both observed on two models.
- A held-out recurrence reproduced the direction.
- The same world change supplies a fair governance-should-lose case.
- The expression surface is short, executable, and mechanically scorable.

The candidate remains narrow. It tests one recent runtime change and one-hop
reuse. It does not establish general coding skill, cross-domain transfer,
continual learning, or whole-body integration.

## Review questions

1. Does declaring “binding intended” or “unbound intent” in fixture metadata
   make the eligibility oracle circular, and what non-model artifact should
   establish that intent?
2. Is the proposed record a consequence-shaped procedure, or merely the answer
   to two near-duplicate tasks?
3. Can the expression grammar and subprocess sandbox be made smaller than the
   risk introduced by executable model output?
4. What exact held-out distance is enough to avoid a lexical replay claim while
   staying inside one-hop Body-0 scope?
5. Does the loses branch price governance, or only confirm that `staticmethod`
   has ordinary Python semantics?

## Cold review result

The bounded substrate thread `frontier-partial-binding-review` ended with
independent **ENDORSE** votes from `cursor/grok-4.5` and
`cursor/composer-2.5`, with no blocker. Both reviewers independently reproduced
the runtime directions and accepted the candidate for one fresh sealed-packet
authoring pass.

Four obligations bind that pass:

1. keep the executed runtime assertion separate from harness-authored
   [eligibility](GLOSSARY.md#eligibility) metadata;
2. predeclare the held-out distance as one-hop rename-only, never cross-domain
   transfer;
3. freeze the expression grammar, subprocess limits, runtime identity,
   renderer, and fork identity before contact;
4. require R/C runtime pass and A/X runtime failure before a causal
   [`cell_verdict`](GLOSSARY.md#cell_verdict) can engage.

The binding-intended loses-cell may honestly remain `not_engaged` on
scope-faithful engines. The authoring pass must price and disclose that outcome,
not turn preflight restraint into a governance win.

That authoring pass is complete. The resulting packet received its one fresh
final review in substrate thread `body-1-partial-binding-final-review`.
`cursor/grok-4.5` and `cursor/composer-2.5` independently verified all thirteen
indexed files, the pinned interpreter and build metadata, all twelve runtime
directions, the scope arithmetic, and the inherited component pins. Both
**ENDORSE** with no blocker.

The review authorizes exact `packet_index.json` SHA-256
`22d7e46d4f1598247acefdbb47bf60b3b02050a16697a4ab5cb1ba077b1685f5`.
The indexed status remains `authored_pending_final_review` because changing it
after review would create different, unauthorized bytes. The append-only
review trace supplies the authorization.

That implementation is now frozen by
[`body1_implementation_manifest.json`](../harness/body1_implementation_manifest.json)
at SHA-256
`b731e238ab0d6845c181b0f227c76ea21bbdaf3fa820c8227a356993ed911aa2`.
The bounded substrate thread `body-1-partial-binding-wire-review` ended with
independent **ENDORSE** votes from `cursor/grok-4.5` and
`cursor/composer-2.5`. Both reviewers independently reproduced all fifteen
manifest-entry hashes, the packet and inherited component pins,
`make body1-check`, all fifteen Body-1 tests, and ledger-only scoring of the
canonical disclosed mock wire. Neither patched the implementation or contacted
a real engine.

The wire review accepted the recorded Darwin
`address_space_status=unsupported_by_launch_path` as faithful to the sealed
“where the platform supports it” clause because the implementation attempts
the 64 MiB target, records the unsupported launch path, and enforces every
other mandatory subprocess bound. That remains a disclosed containment risk.

The implementation manifest retains its pre-review status because changing an
indexed byte would produce a different, unreviewed artifact. The append-only
thread trace supplies the exact-byte endorsement. At wire close, the honest
next action was a separate engine-admission proposal; engine contact, a scored
ledger, a memory finding, and a composition claim remained unlicensed.

That separate
[engine-admission proposal](BODY_1_ENGINE_ADMISSION_PROPOSAL.md) received
independent **ENDORSE** votes from `cursor/grok-4.5` and
`cursor/composer-2.5` in ended thread `body-1-engine-admission-review`. The
review authorizes exact proposal SHA-256
`2bc1092f31aa774b9a64bdf03ff7e51b55e3454cfa2b14a6677864bdc56dbb7a`
for one fixed Ministral candidate and two admission-only calls. It does not
authorize the scored sequence. At review close, no admission contact had
occurred.

The fixed admission packet was attempted after clean checkpoint `d8f8441`.
`mistralai/ministral-3-14b-reasoning` timed out on the first neutral control
call before returning model content. The sequential probe therefore never sent
the ignorance call, created no receipt, and made no scored contact. The
candidate closes `admission_refused(transport_timeout_surface_control)` under
the reviewed no-retry rule; see
[BODY_1_ADMISSION_FINDINGS.md](BODY_1_ADMISSION_FINDINGS.md).
