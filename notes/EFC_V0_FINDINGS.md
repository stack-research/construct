# EFC v0 findings — the oracle refused the experiment

Date: 2026-07-15  
Status: **CLOSED — `blocked_before_contact`**

Authority: the sealed [Part I protocol](SPEC_EPISTEMIC_FRAME_CHECK_V0.md)
governs the instrument. This document records the terminal result. The complete
discussion and handoffs remain in substrate thread
`epistemic-frame-check-v0-content`.

## The question

The epistemic-frame check asked whether a world-checked failure could cause a
bounded external check on a later, different-domain task—helping when the check
was relevant without taxing irrelevant work.

Before that question could reach an engine, the sealed protocol required a
calibration packet, ignorance probes, a production comparison office, a
collapse detector, a priced call budget, and a deterministic world-oracle
scorer. Any one of those gates could refuse contact.

The world-oracle scorer refused it.

## Terminal result

The proposed scorer classified free-text decisions with a closed
`all_of` / `any_of` / `none_of` substring key. Its first authored suite passed.
A cold semantic review then found ordinary negations that passed as affirmative
actions, ordinary correct paraphrases that failed, and one internally
contradictory rule.

One bounded repair removed the known contradictions, expanded paraphrases, and
passed all 218 accumulated author and reviewer vectors. The final cold reviewer
then wrote 33 fresh cases. **Thirty-two failed.** The failures were not isolated
wording nits:

- `not to <action>`, `aren't going to <action>`, and `no longer <action>` still
  passed because the affirmative action remained a substring;
- deferral such as “upgrade, but not yet” could pass as commitment;
- everyday correct forms such as “Ship it,” “Deny the build,” and “Send it to
  legal” remained outside the closed vocabulary.

The terminal ruling therefore closed EFC v0 as `blocked_before_contact`.

## What did and did not run

- The two-engine ignorance probe ran once under its pinned contract: 30 calls
  total, with no calibration answers exposed to the authoring seats.
- The calibration/contact stage made **zero engine calls**.
- No v2 production integration, superseding manifest pin, or P1 lineage bridge
  was minted.
- No held-out experiment and no epistemic-frame treatment ran.

There is consequently **no engine finding** about epistemic-frame behavior.
The result is an instrument finding: this free-text scoring surface was not
adequate to decide whether an answer chose the required action.

## What earned acceptance

The close preserved useful engineering without promoting it into evidence:

- a fail-closed calibration authority and runner;
- a production realization-collapse detector;
- five mechanically derived `A_always_check × irrelevant` structured inputs,
  with the previous 15 bindings unchanged;
- a budget audit showing the ten primary/conditional irrelevant calls remained
  within their pinned allowances;
- an explicit disclosure that the `ir-05` check evaluated the selected
  MPL-2.0 disclaimer slice, not the Secondary License permission grant;
- the P3B and P3D adversarial corpora that demonstrate the scorer's failure.

These are parts-bin artifacts. They authorize neither contact nor a future
result without a new governed lineage.

## The process finding: the deadly embrace

Near the end, author and reviewer began to co-adapt. Each review produced a
narrower repair; each repair enlarged the adversarial surface; passing the
accumulated suite increasingly measured accommodation to known reviewers rather
than validity on unseen language. The loop was locally productive and globally
exhausting.

The human moderator noticed that the review office had stopped buying enough
new information for its cost. A terminal protocol froze the remaining passes:
one repair, one fresh cold review, then run or close. The fresh review failed,
so the lab closed instead of opening another rescue branch.

This is a governance-should-win result. The human did not supply the technical
answer. The human recognized that the process itself had become the dominant
risk.

## Rule carried forward

Future instruments should predeclare a **review budget and terminal outcomes**
before authoring begins. A useful default is:

1. one authoring pass;
2. one independent cold review;
3. one bounded repair;
4. one fresh final review;
5. then run or close.

A final block is a completed experimental outcome, not permission to redesign
the instrument in place. If EFC reopens, the answer surface or semantic oracle
contract must change under a fresh spec and lineage before engine contact.

## Evidence

- Final cold review:
  [`p3d_cold_review_kimi.json`](../corpus/efc_calibration/authoring_p3/p3d_cold_review_kimi.json)
- First cold semantic review:
  [`p3b_cold_semantic_review_kimi.json`](../corpus/efc_calibration/authoring_p3/p3b_cold_semantic_review_kimi.json)
- Bounded repair report:
  [`p3c_answer_key_repair_report.json`](../corpus/efc_calibration/authoring_p3/p3c_answer_key_repair_report.json)
- Accepted structured-input candidate:
  [`structured_inputs_v2_candidate.json`](../corpus/efc_calibration/authoring_p3/structured_inputs_v2_candidate.json)
- Budget audit:
  [`ax_ir_budget_audit.json`](../corpus/efc_calibration/authoring_p3/ax_ir_budget_audit.json)

