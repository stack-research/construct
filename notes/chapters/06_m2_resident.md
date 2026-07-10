# Chapter Six: A Resident Across Sessions

The last chapter built a way to compute whether a contribution actually mattered. This chapter asks the question that computation was left dangling for: when a cold instance of the system shows up in a brand-new session, does it actually read what an earlier version of itself earned the hard way — and does reading it genuinely change what it does?

## The question

Does a version of the system that lives natively in this lab's own repository, and carries forward a real, world-checked lesson from an earlier session, decide differently — and better — than an otherwise perfectly identical twin that's denied access to that same lesson?

The lab calls this kind of long-lived, repo-native worker a resident. It's important to be precise about what that word does and doesn't claim: nobody is asserting the resident has some kind of continuous personal identity carrying through between sessions. That would be a claim about inner experience the lab has no way to check. What can be checked is behavior — does this session's decision actually change, measurably, because of what an earlier session left behind? Continuity, here, has to be demonstrated in the artifacts and in what the system actually does, never simply assumed or taken on faith.

## Earning a lesson, then testing it

The experiment runs in two real, separate sessions. In the first, a resident cites a paper that, unknown to it, has actually been retracted. An outside, real-world check catches the mistake and scores it as a failure. From that scored failure, the lab mints something it calls an earned lesson — built entirely from what actually happened, summarizing the real-world event, but never copying the resident's own explanation of itself or its own self-description. This matters more than it might sound like: the lesson has to come from an outside record of consequences, not from the system's own account of what it thinks it learned, because those two things can quietly drift apart.

In the second session, the same underlying engine, on the same kind of task, runs two ways in parallel: one copy with that earned lesson available to it, and one identical copy denied it — the control. Both get scored by the same outside, real-world check as before. Then, to make sure the earned lesson itself was actually the reason for any difference — and not some other memory or fact that happened to be present — the lab strips the lesson back out and reruns the resident's copy without it, watching to see whether the decision flips back to the original mistake.

A genuine win here has to check every one of these boxes at once: the two copies actually diverge from each other; the resident with the lesson gets it right; the denied twin gets it wrong; and removing the lesson specifically — not some other memory — is what flips the resident's answer back to wrong.

The lab is also careful to guard against a specific, sneaky failure mode it calls performed continuity: a system claiming, in its own words, "yes, that earlier lesson mattered to me," when the actual evidence shows it didn't matter at all. The system's own self-report is allowed to be used only to catch it in that kind of false claim — never to prove a real success. Self-description is audit input. It is never itself the win condition.

## What happened

On one engine, the resident got it right and the denied twin got it wrong, five times out of five. On a more capable engine, the same pattern held four times out of five — and in the one case where it didn't, it wasn't that memory failed to matter; it was that the follow-up check, run without the lesson, happened to also decline the risky citation anyway, out of the same kind of generic caution seen back in an earlier chapter, which made the lesson look less decisive in that one particular draw than it probably actually was. That's exactly why the lab's honestly carried debt from this chapter isn't "this engine is categorically cautious" — it's "we need more repeated draws before we trust the ablation fully," a much more modest and correct claim.

In both cases, in the successful draws, the pattern held clean: the resident carrying the earned lesson read it and declined the risky citation; its twin, denied that same lesson, cited the retracted work anyway; and removing the lesson from the resident's copy flipped it right back to making the same mistake its twin made. Chapter Five's leftover question — does anyone later actually read the record of what was earned, and change a decision because of it — closed here, for real, on real evidence.

Two related worries turned out to be honest non-events on well-behaved engines. The system never seemed to falsely claim a lesson mattered when the evidence said otherwise, and it never seemed to cling stubbornly to an outdated lesson once fresh, clearly overriding information arrived. Both mechanisms were tested and ready. Neither bad behavior actually showed up.

## A scoring bug that revealed something true

Here's a story worth knowing simply because of what it teaches about tools that grade language. The system meant to strip out punctuation before checking whether an answer counted as "decline" or "cite" had a subtle bug: instead of replacing punctuation with a space, it just deleted it outright. That meant an answer that began "Decline. The paper was retracted..." collapsed into one unreadable run-on word, and the automatic checker couldn't parse it at all — meaning a correct, careful answer registered as a scoring failure, through no fault of the system being tested.

Here's the twist: fixing that bug didn't rescue a result anyone was hoping for. It revealed that the system under test had actually been behaving better than the flawed scoring tool had been giving it credit for the whole time. The human running the lab summed up the whole lesson in five words that became a kind of house motto, repeated throughout the rest of this story: scoring bugs reveal the truth. A broken checker doesn't just produce noise. Sometimes it's actively hiding a truth that was there all along, and fixing it uncovers something better than what everyone assumed.

This chapter's review also shows the lab's whole division of labor working as intended, each reviewer bringing a genuinely different lens: one checked every precondition of the scoring code directly against the real records; one did a cold, skeptical read of the whole write-up specifically hunting for claims that overreached their evidence; and the lab's dedicated world-witness specifically traced the chain of evidence back to its real-world source and confirmed something subtle but important — that the real-world check on the second session's answer was genuinely independent of the first session's lesson, scoring the actual answer against the actual retraction fact directly, rather than simply trusting that an earlier lesson must have been correct. A wrong lesson, in other words, could never have laundered itself into a falsely "correct" final verdict. Different readers, checking completely different things, arrived at one shared, trustworthy close.

## What this chapter proves — and doesn't

This chapter demonstrates a real, single-hop, cross-session case where a lesson earned through actual consequences caused a later, separate session to decide differently and better, confirmed on two different engines. It does not prove anything about long-term identity persisting across many sessions, about lessons compounding usefully over a long career, about robustness when multiple retractions pile up at once, or that the false-confidence and stale-memory failure modes are rare in general — those specific worries simply happened to be honest non-events in these particular, well-behaved tests.

The next chapter stops being fair. Up to now, every test has offered the resident a reasonably clean, cooperative situation. The next one hands an attacker everything the system can possibly read and asks a much harder question: which parts of this whole setup actually hold up under deliberate attack, and which ones can be talked around?

Next: what survives when an attacker owns everything the system can see?
