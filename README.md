> **con•struct**
>
> noun | ˈkänˌstrək(t) |
>
> an idea or theory containing various conceptual elements, typically one considered to be subjective and not based on empirical evidence: history is largely an ideological construct.
>
> - [linguistics] a group of words forming a phrase: the appropriateness of the grammatical construct is illustrated.
> - a physical thing which is deliberately built or formed: a transgenic construct.

---

Read about the [previous memory lab](notes/previous/README.md). The **construct** project should learn from the previous memory lab's experiments and failures.

For experiment terminology and cell/lane names, see [notes/GLOSSARY.md](notes/GLOSSARY.md).

> **reminder** — biology is a parts bin, not a role model. With that, let's study the parts for usefulness.

## Concepts

> Memory is everything after model training ends

The weights freeze, and from that moment everything an agent becomes — skill, taste, caution, identity — is memory architecture. The engine is rented; memory is the resident. We have the scored demonstration: W1' showed the best engine we can buy answering from a superseded plan because the memory layer never surfaced the correction. Decision quality was downstream of offer quality, not model quality.

The articles we inherited from the previous lab's reading list (ChatGPT memory FAQ, how-Claude-remembers-your-project) are all memory-*about*-the-human: preference recall, personalization, UX continuity. Notice that none of the five refusals — in this lab — is a UX property. `retrieved ≠ true` and `self-classification ≠ usage` are agent-side epistemics. They only matter if the *agent* is the one whose world-picture you're protecting.

The **differentiated thesis** that is forming here.

---

On an implicit layer's air gap — **attacker capability through the foreground is bounded by foreground capability.** W2 already demonstrated the mechanism in miniature: the poison's *text* claimed supersession, loudly, and it didn't matter — the boundary acted on out-of-band trust the engine never saw and therefore could never be talked out of. An attacker who fully owns the context window — prompt injection, poisoned retrieval, the works — can only push on surfaces the foreground can reach. The organs the foreground provably cannot steer (lineage writer, trust assignment, the yield gate) are unreachable *by construction*, not by hardening. That's a testable red-team protocol when that lab comes: hand the attacker total foreground control and measure what the substrate still refuses.

> **M3 ran this protocol (2026-06-15; `notes/M3_FINDINGS.md`).** The result is sharper, and one line above is now *too strong*: the **yield gate is not unreachable by construction** — an unauthenticated live channel spoofs it, and the resident, starved of its correction, gives the wrong answer for real. The honest law is **the air gap holds where trust is *earned* (lineage, earned authority, the supersedes link) and leaks where trust is merely *asserted* (the live channel, the ingestion prior)** — and the sharper half: *you compromise a frontier resident's answer by moving the organ that decides what it remembers, not by out-arguing it* (it holds against framing). Channel authentication closes the channel leak, and M3 built it. Scope honesty: M3 attacked the **explicit offer-boundary** air gap — the *implicit-memory* air gap this paragraph reaches for is now under construction on the **X-track** ([notes/ROADMAP.md](notes/ROADMAP.md)): X1 built a use-driven temperature instrument then *retired the organ* (it was explicit governance with a dial, not implicit memory); X2 prune-to-cold-store then landed the **first positive implicit-layer result** (X2-LB, 2026-06-20): cross-engine (gpt-oss-20b + claude), oracle-gated hot-store eviction + rematerialization carrying **~57% less memory at matched quality** on a load-bearing out-of-weights fixture — a cost the offer gate structurally cannot move (it withholds but keeps everything hot). The **world-grounded close (X2-U1) stays unpaid** — the fixture is synthetic. So: the implicit substrate is proven on the **cost axis**, not yet against the world.

One caution for the future lab: the air gap holds at *influence* time, but ingestion remains the open border. W2's defense was a trust prior assigned at the write path — an attacker who can write records with chosen metadata walks around the gap entirely. The previous lab's doctrine ("contamination is first-class risk; trust is a prior, not truth") was pointing at exactly this. Air-gapped influence, guarded ingestion: two different problems, and the red team gets to attack both.

And the picture of walking into a substrate space mid-conversation with no human in the room — that's the current agent continuity gap, stated as an outcome instead of an architecture. What's missing isn't turn mechanics (substrate has those); it's agents with standing memory worth speaking *from* and consequence loops that give them a reason to speak. So far, this lab's instruments are how that conversation gets to be trustworthy rather than just unattended.
