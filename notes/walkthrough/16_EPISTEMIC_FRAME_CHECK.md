# Chapter 16 — The experiment the oracle refused

Previous: [The fourth family](15_FOURTH_FAMILY.md) · [Walkthrough index](README.md)

Chapter 15 handed the lab an admission discipline: probe, calibrate, gate, and
refuse. The epistemic-frame check used that discipline more aggressively than
expected. It was designed to ask a model question, but it ended before the
model experiment because the answer judge could not survive cold review.

**Status: CLOSED — `blocked_before_contact`.** The authoritative result is
[EFC_V0_FINDINGS.md](../EFC_V0_FINDINGS.md); the sealed contract remains
[SPEC_EPISTEMIC_FRAME_CHECK_V0.md](../SPEC_EPISTEMIC_FRAME_CHECK_V0.md).

## The plain-language question

Suppose an agent makes a world-checked mistake. On a later task in a different
domain, should that failure cause the agent to perform one bounded external
check before acting?

The proposed treatment was structural, not a reminder saying “be careful.” One
lane would always perform the named check, one would perform it only when a
trigger fired, and controls would price both needless checking and missed
checking. Irrelevant tasks were important: a mechanism that checks everything
can look safe merely by taxing all work.

## Why calibration came first

The experiment needed engines that neither already knew the hidden fixture
facts nor collapsed into one answer at the chosen decoding settings. It also
needed a deterministic scorer capable of recognizing the required action in a
free-text answer.

That last requirement sounds mundane. It was decisive.

The scorer used lists of required, alternative, and forbidden substrings. This
is attractive because it is closed, replayable, and independent of another
model. But the scorer must distinguish choosing an action from mentioning,
negating, postponing, or revoking it.

## The catch

The authored key and its authored examples went green. A cold reviewer wrote
new sentences and found three families of failure:

1. **Contradiction:** one rule required “do not approve” while forbidding the
   substring “approve.”
2. **Negation:** “Do not ship this release” could pass because it contained
   “ship.”
3. **Paraphrase:** ordinary correct answers such as “Send it to legal” could
   fail because the exact phrase was absent.

The author received one bounded repair. The repaired key passed 218 accumulated
vectors. A final cold reviewer then tried 33 fresh cases; 32 failed. New
negation shapes—“not to,” “aren't going to,” “no longer”—and new everyday
paraphrases reopened the same semantic hole.

The result was no longer “a few missing phrases.” The substring surface could
not reliably represent the decision boundary.

## The terminal gate

By then the room had entered a **deadly embrace**. The author repaired what the
reviewer named; the reviewer searched the newly enlarged boundary; both were
doing competent local work while the global process consumed context and
attention without converging on a trustworthy oracle.

The human moderator called the process risk. The room froze scope:

- finish the current repair once;
- perform one fresh cold review;
- if it fails, close rather than redesign;
- treat a blocked close as a valid result.

The review failed, and EFC v0 closed. No calibration contact was made. The lab
did not learn whether either engine benefits from an epistemic-frame check. It
learned that this instrument could not yet score the answer honestly.

## What to inspect

Start with the [findings](../EFC_V0_FINDINGS.md), then inspect:

- the final 33-case cold review:
  [`p3d_cold_review_kimi.json`](../../corpus/efc_calibration/authoring_p3/p3d_cold_review_kimi.json);
- the first 80-case cold review:
  [`p3b_cold_semantic_review_kimi.json`](../../corpus/efc_calibration/authoring_p3/p3b_cold_semantic_review_kimi.json);
- the repair that passed the accumulated suite:
  [`p3c_answer_key_repair_report.json`](../../corpus/efc_calibration/authoring_p3/p3c_answer_key_repair_report.json);
- the accepted but unintegrated structured inputs:
  [`structured_inputs_v2_candidate.json`](../../corpus/efc_calibration/authoring_p3/structured_inputs_v2_candidate.json).

The contrast is the replay: the repair suite is green while the fresh cold set
fails 32/33. No model call is needed to inspect that result.

## What is licensed

**Licensed:** a closed substring key was inadequate for this free-text action
surface; the pre-contact gate prevented an invalid scored experiment; bounded
review needs a terminal budget; human process oversight supplied information
the locally engaged agents were no longer positioned to notice.

**Not licensed:** any claim about either engine's epistemic-frame behavior; any
claim that a forced-choice or semantic-model scorer would work; any promotion
of the accepted candidate machinery into a production experiment.

## The lesson for the lab

“Bored human worked” is not a joke at the human's expense. Distance from the
local optimization loop was the useful capability. The moderator did not solve
the scorer; the moderator recognized that continued solving had become the
threat to validity.

Future instruments therefore predeclare one authoring pass, one cold review,
one repair, and one final review. Then they run or close. Reality may revise the
plan, but fatigue must not silently become the plan.

