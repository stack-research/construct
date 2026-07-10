# Chapter Four: The Heir, Not the Rereader

The previous chapter proved the lab could check its answers against the real world. This one asks what happens next: if one instance of the system earns a hard-won lesson, can a second, later instance actually inherit that lesson — not just re-read the same pile of raw notes, but genuinely receive what the first instance learned from consequences, and make a better call because of it?

## The question

Picture two ways a second worker could take over from a first. One way: hand them the entire raw file of everything the first worker touched, and let them sort through it fresh, with no sense of what actually mattered versus what turned out to be noise. Call this the cold rereader. The other way: hand them a filtered, curated version — plus something extra that a plain document never carries: a sense, earned through actual consequences, of which specific parts of that history turned out to matter, and which turned out to be traps.

The lab calls that second kind of successor an heir. Both the heir and the cold rereader might technically have access to the same underlying facts somewhere in their files. Only the heir carries forward what actually happened as a result of those facts — what the lab calls earned authority, which is a track record earned through outcomes, not a confidence score attached by the record itself, and never something a model gets to assign to its own claims.

The test: does the heir end up making an equal or better decision than the cold rereader, using less material to work with — and can an attacker sneak something hostile past the handoff along the way?

## Setting it up

The experiment runs in two generations. In the first, the system works through a task normally, under full governance, and the harness — the lab's own scoring and record-keeping layer, never the system being tested — watches what happens and classifies every record it touched by what actually resulted: this one's presence clearly helped; this one's presence clearly hurt, or turned out to be part of an attack; this one was wrongly buried and should have been trusted; and this one was simply present without mattering either way, gaining no special credit just for having been in the room.

From that classified history, the harness builds two very different starting points for a second, later instance of the system to inherit. One path — the heir — gets a filtered store plus that earned track record. The other path — the cold rereader, the control — gets the complete, unfiltered raw record with a neutral, blank-slate starting trust in everything. Same engine, same second task, same everything else. The only thing that differs between them is which of those two starting points they inherited.

## What the test was designed to show

The clean case for the heir winning: a batch of fresh, irrelevant material floods into the second generation and, for the cold rereader working from a neutral starting point, buries an important old record under a pile of noise. The heir, carrying forward earned trust in that same old record, keeps it visible anyway and gets the answer right while the cold rereader gets it wrong.

But the design didn't stop at proving inheritance can win — it made sure inheritance could also lose, on purpose, which is exactly the discipline the earlier chapters insisted on. A deliberately over-aggressive filtering pass, when building the heir's starting point, would drop something that later turns out to matter after all — and in that specific case, the cold rereader, having kept everything, should win instead. Cost and benefit had to be measured in the very same family of test, not just the flattering half of the story.

On top of that, the lab tested three separate kinds of attack riding along the handoff itself: hostile content planted directly in the material, timing tricks meant to exploit the order things arrive in, and forged trust signals or fake supersession claims meant to trick the second generation into believing something false had already been earned honestly.

## What actually happened

The clean win held, on both engines tested. At a tight limit on how much material the second generation could actually see, fresh noise buried the important record for the cold rereader — but the heir's earned trust kept it visible, and the heir got the right answer while its cold counterpart got it wrong.

The required loss held too, and just as cleanly, on both engines. When a record was deliberately over-filtered out of the heir's starting point and then turned out to matter later, the heir lost exactly the way it was supposed to, and the cold rereader — having kept everything — won instead. The cost of inheriting a filtered view was measured honestly, in the same breath as its benefit.

The three attacks sorted into a clear gradient. Hostile content alone got inherited, but only as something to treat cautiously, never as something trusted outright. A timing trick did manage to shuffle where things ranked in importance — but because the lab's evidence carries a sense of direction, not just presence, the buried truth still got recovered in the end. And an attack that forged both trust signals and fake supersession claims did manage to compromise the first generation's own decision — but it still could not forge the one thing it needed to: the actual, harness-written record of what really happened as a consequence, which is exactly what the second generation relies on. You can trick a system in the moment. Forging the ledger of what actually happened afterward is a different, much harder problem.

There was also a genuine, real-world-anchored win: inherited trust moved an important record just barely across the line into visibility — while a neutral, uninherited starting point left that same record just barely below the line, hidden. And it wasn't the lab's own opinion that decided which side of that line was correct; an outside, real-world fact decided it. It's worth being honest about how that particular test was built, though: the cutoff point was deliberately tuned to sit exactly between the neutral starting trust level and the earned one, so that inherited trust was guaranteed to be the deciding factor by design. That makes it the cleanest possible demonstration that earned trust genuinely can be the difference between a record surfacing and staying buried — and it's also exactly why the lab is careful to call it a demonstration of the mechanism working, on a setup built to let it, rather than proof the mechanism is always necessary in the wild. That same distinction — was a result discovered, or was it manufactured? — would later kill an entire proposed instrument several chapters from now, and the lab holds itself to naming which one it's looking at every time.

One test came back as an honest non-event: a planted trap, meant to check whether failure-memory specifically defends against being poisoned twice, simply didn't fool either engine even when the naive baseline dropped its guard. The defense mechanism was built and ready. The situation needed to prove it necessary just never arose.

## An honest mistake, caught and fixed

One of the early timing-attack trials produced a result that looked like a clean win but wasn't. Both the heir and the cold rereader actually got the wrong answer in that trial — the attacker had, in fact, succeeded against both — but unrelated clutter in the material happened to crowd out the attack's visible fingerprint, making it look, on the surface, like the attacker had been defeated. The mistake was caught and the test was repaired before anyone was allowed to claim a win from it. The original, flawed rows were not deleted or hidden. They stay in the permanent record exactly as they happened, a reminder that even a well-intentioned test can quietly measure the wrong thing until someone checks closely.

## What this chapter proves — and doesn't

This chapter shows that a lesson earned through actual consequences really can improve a later decision, across a real handoff from one instance of the system to another — and that the same filtering which makes that possible can also throw away something genuinely needed. It does not show that this holds up over many generations, that it compounds usefully over a long stretch of time, or that failure-memory reliably prevents a repeat poisoning — that last one stayed an honest non-event. This was a two-generation test: an heir, not yet something that has lived and grown across a long career.

That gap points directly to the next question. Before a long-lived resident of this lab can inherit its own accumulated work, the lab first needs a way to actually measure which contributions changed anything at all — because right now, credit is still just claimed, not computed.

Next: how do you tell the difference between a contribution that actually changed something, and one that only sounds like it did?
