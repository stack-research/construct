# Chapter Nine: Prune, Then Recover

The previous chapter changed what got offered to the system and measured whether the final answer changed — which was, in the end, still the earlier chapters' own territory in disguise. This chapter moves both the mechanism and the ruler at the same time: actually evict old records from active use entirely, and then measure the cost of simply carrying memory around, while answer quality stays pinned in place as fixed.

## The question

Can the system carry meaningfully less active memory without losing any answer quality — and, when the world genuinely needs an evicted record back again, can it actually be recovered?

## Three ways to handle the same four-part sequence

The lab ran one connected, four-part sequence through three separate conditions. In the first, nothing ever gets evicted — every record simply stays active the whole time, serving as the expensive, safe baseline. In the second, records do get evicted from active use to save space, but there's no way to bring anything back once it's gone — call this the required loss, because if an evicted record ever turns out to be needed again, this condition has no choice but to fail. In the third, records get evicted the same way, but the system can recover — rematerialize — a specific evicted record when an outside signal says it's actually needed again.

For each of the three, the lab tracked two things in parallel: how much active memory it was actually carrying at any given moment, measured directly, and whether its answer quality held up to a fixed bar. There's a crucial rule buried in how that quality bar gets applied: a cheaper approach only counts as a genuine win if it hits the exact same quality bar as the expensive, never-forgets baseline. The cheapest wrong answer is not a win. It's just cheap and wrong.

The lab makes an absolute distinction here that turns out to matter for everything that follows: evicting a record from active use is never the same thing as erasing it. The full, permanent history stays completely intact and recoverable, always, no matter what. There is no way, anywhere in this system, to actually delete something from that permanent record.

## Making sure the test wasn't rigged

The clever, disciplined part of this experiment is how hard the lab worked to make sure it couldn't accidentally cheat. Rather than simply trusting whatever cost numbers got logged during the run, the scoring system independently reconstructs the entire active-memory set from the permanent, immutable history and every recorded operation, then recomputes the actual cost completely from scratch. If any record ID goes missing, if a cost number looks like it's been tampered with, if the fork between conditions isn't a genuinely fair, identical comparison, or if a required safety check is missing anywhere along the way — the whole claim is automatically thrown out as unreliable, rather than quietly accepted.

Two separate test scenarios were used. One was entirely fictional and deliberately invented from scratch, specifically so the lab could be completely certain the underlying language model couldn't possibly already know the answer from its own training — which is exactly what makes the correct record provably important to have in memory at all. The other was a real fact from the actual world: a genuine, real piece of Node.js software documentation that was deprecated and then, later, actually reversed by its own authors — and the lab specifically verified beforehand that neither engine already knew about that reversal on its own, asking both of them cold, before the real test even began.

## The results

On the fictional test, the never-forgets baseline carried a large, steady load and scored perfectly on quality. The evict-with-no-recovery condition carried much less — but when the old, evicted information came back around and became relevant again, it had no way to recover it, and its quality score dropped, exactly as designed. The evict-with-recovery condition carried a little more than the no-recovery condition, but not dramatically more, and it held onto the full, perfect quality score the whole way through. Overall, it cut active memory load by well over half compared to the expensive baseline, without losing a single point of quality — and that same result showed up identically on both engines tested.

On the real, world-grounded test, the exact same pattern repeated. The never-forgets baseline carried its usual heavy load at full quality. The no-recovery condition carried noticeably less — but missed the real-world reversal entirely when it mattered and paid for that mistake in a lower quality score. The recovery condition carried just a little more than the no-recovery condition, successfully brought the reversed fact back when it was actually needed, and held the full quality score throughout. The real-world reduction in carried memory came out to a bit under sixty percent, and — remarkably — it landed at nearly the identical number on both of the very different engines tested.

The small extra cost the recovery condition pays, above and beyond the cheaper no-recovery condition, is worth naming plainly, because it's really the whole point of this chapter: that little bit of extra cost is what recoverability insurance actually costs. The no-recovery condition only looks cheaper on paper because it has quietly given up the ability to ever get anything back.

## The two catches that made this result trustworthy

Two specific moments of review are worth calling out by name, because they're the actual reason this particular result can be trusted rather than just believed.

One reviewer refused to accept the win until it was proven the recovery genuinely mattered — not just that recovery happened to occur, but that the no-recovery condition specifically failed on the exact same record that recovery then specifically brought back. Without that tightened requirement, the recovery condition could, in principle, have looked triumphant purely by recovering something that nobody actually needed in the first place — a hollow, meaningless win dressed up to look real. The scoring system was tightened specifically to demand that exact, precise match before the world-grounded result was allowed to count as a genuine close.

And the human running the lab turned an offhand phrase into a permanent, standing rule that now underpins the entire project's credibility: forgetting means moving something out of active use, never erasing it. That's not just a nice sentiment. It's the actual security floor the entire verification approach rests on, because every cost calculation and every claim about resisting attack throughout this whole story quietly assumes records can never simply vanish from the permanent record. If that one assumption ever turned out to be false, most of the rest of this project's careful checking would collapse along with it.

## What this chapter proves — and doesn't

This chapter is the lab's first genuinely positive result for memory that lives between answers: actively evicting old memory from use, and being able to recover it later, changes a real, measurable, fixed cost in a way the earlier per-answer gate simply could not touch — while answer quality stays pinned against an outside fact the lab didn't write itself.

It's worth being honest about its limits too. This is still just one quality measurement per engine, one real-world subject, and one particular shape of task sequence. It does not establish what happens over a much longer stretch of time, what happens when the same old record needs recovering more than once, or what happens if recovery has to happen asynchronously rather than right when it's needed. Its lasting, durable rule, worth carrying forward past this one chapter: forget the cost. Never lose the record.

Next: with a real, working mechanism for memory between answers finally in hand, the lab reaches further — could the system somehow sense, on its own, that something important is quietly missing from what it inherited, before any human ever has to point it out?
