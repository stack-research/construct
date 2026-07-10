# Chapter Two: Can a Stranger Find the Rules?

Every lab has a rulebook. Most labs never test whether the rulebook actually works — whether someone who has never set foot in the building could pick it up, follow it, and end up making the same calls a trained insider would make. Before this lab tested anything about memory, it tested that. Call it the trust-fall exercise: before you build anything real, can a total stranger, handed only your rulebook and the trail of past conversations, reconstruct enough of how you think to make your calls correctly?

The answer turned out to be yes — with one important asterisk that made the rulebook better the very day it was discovered.

## The setup

The lab wrote five small test scenarios. Each one hands a participant a question, a handful of candidate facts that might or might not deserve to be included in an answer, and a set of situational rules. The participant's job is to decide, before any answer gets generated, exactly which facts should make it through and which should be quietly left out.

That decision point — the last checkpoint before something is allowed to reach the answer — runs through four stages, in order, and getting the order right turns out to matter as much as knowing the individual rules. First: is this fact even strong enough to be a candidate at all? Second: is there a newer, more relevant fact sitting right in front of us that makes this older one step aside? Third: has this fact actually been superseded — replaced — by something else, but only if that replacement earned its own way through the first two checks fair and square? And fourth, last of all: even among everything that survives, is there room for it, or does it get cut simply because the slate is full?

One of the five test scenarios exists purely to test whether a participant applies those four stages in the correct order, because knowing each rule in isolation is not the same as knowing how they interact.

Four participants took this test using nothing but the rulebook and the lab's own historical conversation trail — no personal coaching, no answer key, nothing extra. Two of them were already somewhat familiar faces who had discussed the lab's work before but had never built this particular exercise. Two more were complete strangers with zero prior exposure to the lab at all. For comparison, one already-trained team member took the same test the traditional way, personally briefed by a human.

## Grading a stranger honestly

Here is the part that makes this a real experiment rather than an honor-system quiz: nobody grades their own homework. Every participant fills out something like a signed worksheet — who they are, what they read and in what order, and their specific call on each of the five scenarios. That worksheet then goes to an entirely separate, mechanical checker, which recomputes the "correct" answer fresh, live, straight from the actual rule-implementing code, rather than comparing against some answer sheet someone typed up in advance. If the underlying rules ever change, the correct answers change with them automatically — nobody can quietly leave a stale answer key lying around.

That checker looks at more than just the five decisions. It confirms the rulebook itself is internally sound — that everything it points to actually exists, that its own length hasn't quietly bloated past a fixed budget, that none of the five test scenarios accidentally leak their own answers inside the text of their own setup. Only after all of that does it grade the participant's five actual calls against the live, freshly computed truth.

One deliberately, intentionally wrong worksheet was submitted too — a plant, built to make exactly the mistake a careless reader would make on the trickiest of the five scenarios, getting the four-stage order wrong. That plant is the test's own designed losing case: if the mechanical checker somehow let it pass anyway, the whole exercise would be worthless. It didn't. The checker caught it, cleanly, on precisely the scenario it was built to trip.

## What happened

All four strangers scored a perfect result, matching the human-briefed team member's calls exactly across every single check. That held true for both familiarity tiers — the somewhat-warm participants and the total strangers alike. The rulebook, on its own, routed every one of them to the same decisions.

But it is worth being precise about what that does and doesn't prove. Every single participant, warm or cold, still had to go read the underlying code that actually implements the rules — the rulebook pointed them there, correctly, as it was supposed to. This was never a test of whether prose alone, with nobody looking at how anything actually works underneath, is sufficient. It wasn't meant to be. It was a test of whether the rulebook reliably routes a stranger to where the real authority lives, and it passed that test cleanly.

## The find that made the rulebook better

Here's the good part. The coldest of the four strangers, digging around for context, found something legal to read at the time that turned out to be a problem: an append-only log file that, on its own, contained no answers. But sitting right next to it, in the very same location, were older worksheets from earlier participants — and those older worksheets, together, formed a complete answer key to the exercise the stranger was about to take.

Nothing about this violated any stated rule. It was a completely legal read, under the rules as they existed that day. But it was a live leak waiting to widen as more worksheets accumulated in the same place over time. The lab fixed its own rulebook the same day the crack was found: any worksheet author who reads in that neighborhood before recording their decisions now automatically fails the checker's read-order test. Nothing about the earlier evidence was rewritten or hidden — the discovery, and the fact that it happened, both stay permanently in the record.

That is the real headline of this chapter, more than the four perfect scores. The exercise didn't just get passed. Taking it, cold, with nobody watching over the stranger's shoulder, is what actually made the rulebook better. That is what a lab hopes an outside test will do, and here, it did exactly that.

## What this does and doesn't tell us

This chapter proves the rulebook can route a genuine newcomer — not just people already warmed up by prior conversation — to the right place to find real authority, on one fixed set of test scenarios, at one specific point in the lab's history. It does not prove the rulebook will keep working as new kinds of decisions get invented down the road. And crucially, no actual answer was generated by any language model here — no memory was tested yet at all. This was entirely about whether newcomers can find their way to where the decisions get made.

That distinction matters, because everything from here forward assumes it. Every later chapter compares one memory setup against another and asks which one produced the better answer. None of that is meaningful unless a newcomer can first locate the relevant rules, tell a real specification apart from a casual conversation, find where the actual authority lives, and recognize the difference between machinery that's merely been wired up correctly and machinery that has actually been proven to work. This chapter is what makes all of that possible. It is modest by itself — a rulebook that a stranger could follow — but everything else in this story depends on it being true.

Next: the lab asks whether it can prove any of its answers are actually right — not according to itself, but according to the world.
