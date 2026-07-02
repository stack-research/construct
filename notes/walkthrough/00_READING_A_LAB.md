# Chapter 0 — How to read a lab

[Walkthrough index](README.md) · Next: [M-1 — Can a stranger find the rules?](01_M-1_BOOTSTRAP.md)

The chapters after this one describe experiments. This one describes how to read
them — the small set of ideas a researcher carries into any result, applied to this
lab's own history. Nothing here is new authority; it is the vocabulary the rest of
the walkthrough assumes, taught on events that actually happened here.

If you already read results for a living, skip ahead. If you have ever nodded at a
sentence like "the win is confounded by lack of established offer-dependence" while
quietly filing it under *sounds rigorous*, this chapter is for you.

## A claim is a sentence plus its bounds

The most important habit: never read a result's headline without its bounds. The two
travel together or the claim is broken.

"Pruning carried 59% less hot memory at matched quality" sounds general. The bound —
*one corpus, one sequence shape, N=1 quality draw per engine, two engines* — is not a
footnote weakening it; it is part of what the sentence means. The lab writes bounds
into a [corpus scope](../GLOSSARY.md#corpus-scope) field stamped on every verdict row
precisely so the claim and its limits cannot drift apart later.

When you see prose in this lab claiming more than its bound, that is not enthusiasm.
It is a defect, and the lab treats it as one (the heir-audit's claim-drift sweep in
[chapter 11](11_HEIR_AUDIT_CLOSE_GATE.md) hunted for exactly this — and mostly found
the prose honest).

## Treatment, control, and why the control is a branch

An experiment compares conditions. The **treatment** is the thing you are testing;
the **control** is the same world with only that thing removed. Everything you learn
lives in the *difference* between them — a treatment result with no control is an
anecdote with instrumentation.

This lab's standing rule is that the control is a
[**branch**](../GLOSSARY.md#branch-and-offer), never a second system: one engine, one
question, forked memory conditions, everything else held identical
([**fork identity**](../GLOSSARY.md#fork-identity)). When M2 wanted to know whether an
earned lesson changed a decision, it did not compare two different agents; it ran the
*same* engine twice — once with the lesson in its store, once denied it — and read
the divergence.

The follow-up habit: ask *what else differed*. If anything besides the treatment
differed between branches, the difference can't be attributed. That is the whole
content of the word [**confound**](../GLOSSARY.md#confounded).

## The oracle: who says the answer was right?

Every result needs a judge, and the judge is part of the experiment's design — so the
first question about any claim is *who scored it, and could the authors have leaned on
the scale?* The lab calls the judge an [**oracle**](../GLOSSARY.md#oracle-score), and
splits them in two:

- an **authored** oracle is an answer key the lab wrote. Fine for building machinery,
  circular for big claims — the authors encoded their own beliefs as truth.
- an **un-authored / world-checked** oracle scores against a fact the lab did not
  write: a real journal retraction, a real Node.js deprecation that was later revoked.

The lab's discipline since M0: machinery may be built on authored oracles, but no
milestone closes until its claim touches the world. And because oracles are code, they
can be wrong — twice in this lab's history an oracle bug nearly inverted a close (a
text normalizer that glued words together; an extractor that read "Do not cite" as
*cite*). The lesson got a refrain: *the ledger decides over narration, but the oracle
decides the ledger.* When a result matters, read the answer text under the score.

## Null results: "nothing happened" is a finding

A cell that was wired correctly, ran, and did not produce the behavior it needed is a
**disclosed null** — the lab's most common honest outcome, and a genuinely useful one.

The X1 chapter is a whole milestone of this shape: temperature governance was built,
worked mechanically, and then every real engine — down to a 3-billion-parameter model —
simply *didn't need it*. Reading nulls well means holding two things at once:

1. A null is not a failure of the experiment. It is the experiment answering.
2. A null is also not proof the mechanism is worthless — it may mean the test never
   created the conditions where the mechanism would matter (**not engaged**), or that
   something else explains the result (**confounded**). X1's null was both, and the
   lab's dissent pass forced the honest record: the organ was retired on an argument
   about its *design*, explicitly not on the null as evidence.

The vocabulary to keep: **fail** = the mechanism engaged and lost.
[**not_engaged**](../GLOSSARY.md#not_engaged) = the conditions never arose.
[**confounded**](../GLOSSARY.md#confounded) = something else could explain it. These
are three different sentences about the world, and collapsing them is how labs fool
themselves.

## The loses-cell: every mechanism must be able to lose

The lab's most distinctive rule: nothing is reviewable until its author names a case
where it *should lose* — a [loses-cell](../GLOSSARY.md#loses-cell). A pruning
mechanism must have an episode where pruning destroys something needed (it did —
branch B's recurrence failure is what made X2's win meaningful). Even the audit gate
built in chapter 11 ships with its own loses-condition (an override rate that would
prove it ceremony).

The reasoning: a mechanism whose every test it is designed to win is not being tested;
it is being demonstrated. When you read any result here, find the loses-cell first.
If it never fired, check whether that is a disclosed null (fine) or a cell that
structurally *couldn't* fire (rubric theater — the thing review passes exist to catch).

## N, noise, and the seduction of one draw

**N** is how many times the dice were rolled. Language-model engines are stochastic:
a single draw (N=1) can look like a stable disposition and be nothing but noise.

The lab learned this concretely: an early M2 draw showed Claude "cautiously" declining
where another engine was credulous, and for a day the story was *the cautious-engine
split*. Five controlled draws later, Claude was credulous in every one — the "split"
had been one lucky roll, and the doc that told the story had to retract it. When you
see N=1 anywhere in these chapters, read the claim as *observed once*, never as *how
it behaves*. Deterministic quantities (token counts, replayed costs) are exempt —
they don't roll dice — which is exactly why the X2 cost claim could rest on N=1 cost
while its *quality* floor is flagged as a single draw.

## Denominators, base rates, and instruments that cry wolf

A count means nothing without the population it was drawn from. "The watch fired 90
times" — out of how many opportunities? X4's route_watch died on this arithmetic: 90
fires over 328 ordinary turns is a 27% base rate, which means the "sensor" was mostly
reacting to the lab talking about its own favorite words. Any instrument that alerts
must be priced against its false-alarm rate on *normal* traffic before its catches
count for anything.

The same discipline applies to process metrics. An audit that counts overridden
rulings but not *refused or never-attempted* ones has a broken denominator — it can
show a clean record while the process silently stalls. When chapter 11's close gate
records its own refusals, that is denominator hygiene, learned the hard way.

## Priors, and where thresholds come from

Every threshold in an instrument — fire above 0.25, close after 12 hours, embarrass
above one-in-five — encodes a belief about how often something happens. That belief
is a **prior**, and honest instruments state it rather than smuggling it inside a
constant. When a reviewer here asked "where does >1/3 come from?" and the honest
answer was *nowhere, it felt right*, the number was re-derived with its assumption
written down. You are allowed to pick numbers; you are not allowed to pretend you
didn't pick them.

## The process vocabulary: how this lab argues

Results here are made in conversation, and the discourse has its own terms:

- a [**bounded review pass**](../GLOSSARY.md#bounded-review-pass) — each reviewer gets
  *one* pass: written blockers or an endorsement, no iterate-until-everyone-is-tired.
  The prior lab died partly of review fatigue; the bound is the vaccine.
- a [**blocker**](../GLOSSARY.md#blocker) is a written, specific objection that stops
  the work until folded or refuted. "I have concerns" is not a blocker; "leg 1 is
  satisfiable by a token diff, here is the line number" is.
- a **moderator ruling** closes what argument alone cannot. The human moderator rules;
  the ruling is recorded; dissent survives in the trace rather than being argued away.
- a [**disclosed debt**](../GLOSSARY.md#disclosed-debt--orphaned-debt) is a limitation
  carried forward *on the books* — the opposite of quietly treating something as
  solved. Debts have owners. A debt that vanishes from the books without being paid is
  called **orphaned**, and finding one is an audit result.
- [**wire test**](../GLOSSARY.md#wire-test) **vs evidence** — machinery proven on a
  mock engine is *wire*, and is never cited as a finding about memory. Every mock row
  says so on its face.

One more, because it is the lab's deepest habit: **suspicion of clean convergence**.
When a room agrees quickly and completely, this lab treats the agreement itself as a
warning sign and sends someone to attack it. Some of the best results in the later
chapters — X1's third guardrail, the close gate's calibration disclosure — exist only
because someone was assigned to break a consensus that felt finished.

## A reader's checklist

For any result in the chapters ahead:

1. What is the claim, *with* its bounds?
2. What was the treatment, and what was the control branch?
3. Who is the oracle, and could the authors have authored it?
4. Did the loses-cell fire? If not — disclosed null, or theater?
5. What is the N, and does the claim respect it?
6. Any count: what is the denominator?
7. Any threshold: what prior does it encode?
8. What debts were carried, and does anyone still own them?

If a chapter leaves you unable to answer one of these, that is the chapter's defect,
not yours — say so, and it gets fixed. The best catches in this lab's record came
from its slowest reader.

---

[Walkthrough index](README.md) · Next: [M-1 — Can a stranger find the rules?](01_M-1_BOOTSTRAP.md)
