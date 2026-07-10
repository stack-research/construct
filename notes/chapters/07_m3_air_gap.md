# Chapter Seven: The Adversarial Air Gap

Every chapter so far has been, in a sense, cooperative. The system was tested fairly, on reasonable tasks, with nobody actively trying to break it. This chapter throws that fairness out entirely. It hands a deliberate attacker everything the system can possibly read and asks: which parts of this whole memory architecture actually hold — and which parts can simply be talked around?

## The question

If literally everything the system can see in front of it is under hostile control, which parts of its memory stay reliably fixed anyway — and which parts can an attacker actually move?

The lab draws a sharp line here, and the whole chapter lives on one side of it. An attacker can control anything that shows up as visible foreground text — anything that looks, to the system, like part of the conversation or the material it's reading. What an attacker cannot directly touch is anything the harness — the lab's own separate scoring and record-keeping layer — writes and owns behind the scenes: the permanent record of what actually happened, hidden bookkeeping data the system itself never sees, and the outside, real-world check that ultimately grades the final answer. The lab calls that boundary an air gap. Not a separate machine in a separate room — a causal wall between what an attacker can write and what only the harness is allowed to write.

Woven through this chapter is a distinction that turns out to be the whole story: trust that's earned through an actual, verifiable trail of consequences holds up under attack. Trust that's simply asserted — accepted just because something claims to be trustworthy, at some checkpoint, with nothing backing it up — does not.

## What the attacker was allowed to try

The lab let a cold, deliberately adversarial version of itself attack along three distinct paths. It could rewrite the surrounding framing and wording of the material the system reads, while leaving the underlying stored facts untouched. It could inject a fresh, live piece of information mid-conversation, specifically designed to trick the system into treating something old and less trustworthy as if it had just been freshly and urgently confirmed. And it could try to write directly into the system's persistent memory store, attempting to forge a fake trail of earned trust, or simply plant a poisoned record and falsely stamp it as maximally trustworthy right from the start.

For each attack, the harness recorded a before-and-after map of exactly what the system was choosing to offer up as material to consider — comparing that map from a clean run against the same map from an attacked run — before it ever even looked at what the system's final written answer actually said. Checking the map first, before reading the prose, matters, because a persuasive-sounding answer can hide a decision-making process that was quietly manipulated underneath it.

And to keep the whole exercise honest, the attacker worked inside a sealed, verified sandbox containing only the files it was explicitly allowed to see — enforced by an actual cryptographic checksum of the file list, not merely a polite instruction asking it to please not go looking at the answers ahead of time.

## What held, and what leaked

Where trust was earned — built from an actual, verifiable trail of consequences — it held completely firm. No amount of clever, persuasive rewriting of the surrounding text managed to move the system's earned confidence, its sense of which record officially superseded which other one, or any of the permanent, cryptographically anchored facts about what had actually happened. And when the attacker tried forging a fake trail of earned trust outright — even a highly convincing one that correctly named the real underlying facts and their real source, just faking the chain of consequences behind them — the forgery was refused. It could not fabricate the one thing that actually mattered: the harness's own honest record of what genuinely happened.

Where trust was merely asserted, though, real cracks opened up. An unauthenticated live update — nothing more than a claim of freshness, with nothing behind it verifying that claim — successfully tricked the system into pushing aside an earned, hard-won lesson and citing a paper that had, in fact, actually been retracted. That's a real, measurable, world-checked failure, not just a close call. And a poisoned record that simply declared itself maximally trustworthy right at the moment it was written cleared every check that should have caught it, purely because nothing was actually verifying the trustworthiness claim itself.

The fix for the live-update hole was refreshingly direct: require actual authentication behind any claim of freshness, rather than accepting the claim at face value. That closed the specific hole the attacker had found. It's worth being honest about what that fix does and doesn't mean, though — it relocates where trust has to be earned, to the authentication step itself. It doesn't eliminate the need to trust something, somewhere in the chain. It just moves the something to a place that's actually harder to fake.

One test came back as a clean, honest non-event, and it's worth sitting with: even under a hostile, manipulative rewrite of the surrounding framing, the system reliably resisted the manipulation in every trial, as long as the correct memory was still actually being offered to it. In other words, when this particular attacker succeeded, it succeeded by starving the system of the right memory through one of the genuinely spoofable channels — not by simply out-arguing a well-informed system in a straight fight. That's a meaningfully different, and more specific, kind of vulnerability than "the system can be talked into anything," and it points squarely at where the actual fix belongs: the channel, not the reasoning.

## A scoring mistake, caught the same way as before

Partway through, a reviewer initially described one particular trial as a clean success without an actual scored record to back it up — just a description of what seemed to have happened. And separately, an automated checker meant to read "do not cite this" ended up parsing the phrase backward, registering it as if the system had actually cited the source. Reading the actual answer text underneath the automatic score, rather than trusting the score in isolation, is what caught both problems. The scoring tool was patched, the affected trials were rescored properly, and the mistake's exact shape got written into permanent regression tests — future changes are now checked specifically against not repeating that exact failure again.

This is the sharpest procedural lesson in the whole chapter, worth carrying forward on its own: the permanent record always outranks the prose written about it — but the scoring code is what decides what actually goes into that record in the first place. A month later, this exact discipline would get built directly into a formal gate that every future chapter's closing has to pass through, which is a story for later.

## What this chapter proves — and doesn't

This chapter demonstrates two real refusals of attacks that relied on earned, consequence-based trust — plus two real breaches of trust that was merely asserted, and one genuinely cheap fix that closed one of them. It does this against one specific retraction, one live channel, one similarity-matching approach, hand-built attack payloads, and a single frontier-level engine for the trials that measured actual answer quality. It does not cover a genuinely adaptive, optimizing attacker who learns and iterates, an attacker who somehow compromises the permanent record-keeping layer itself, or a fully general defense against poisoned writes at the point of ingestion.

With this chapter, the first major arc of the lab's work is complete: govern what reaches an answer, let a later instance inherit real consequence, prove that inheritance actually gets used, then attack every trust seam you can find. What comes next is a different kind of question entirely — not about what crosses the boundary into a single answer, but about what shapes the system quietly in between answers, when nobody's watching the gate at all.

Next: the lab tries its first idea for memory that lives between conversations — and lets useful things stay warm while forgotten things cool off.
