# Glossary

> Forming vocabulary for lab two. Definitions are hypotheses, not law. Edit freely.

Constitutional terms before system description. If a concept needs a paragraph of apology, it probably needs a better name first.

---

## Planes

**Lineage plane**  
Append-only, immutable record of what happened. Replayable. Does not judge, forgive, or decay. The audit floor.

**Cognitive plane**  
Mutable layer over lineage: confidence, eligibility, decay, suppression, graduation. Behavior may change here; the record of behavior may not.

**Two-plane discipline**  
Keep lineage and cognition apart by construction. Collapsing them is where confabulation and self-justifying revisionism live.

---

## Records & epistemics

**Record**  
A typed, immutable entry on the lineage plane. Written at the edge where events occur, not inferred later by convention.

**Belief / claim / memory / evidence / reality_observation**  
Five epistemic kinds kept distinct. A memory substrate must refuse to answer "is this true?" with "I remember it." Different kinds, different authority, different decay — do not deduplicate because they point at the same action.

**Subject**  
What a memory is *about*. The dividing line between this lab and Dreaming: Dreaming's subject is the **user** (a synthesized profile); this lab's subject is the **substrate's own conduct** (which influences it offered, withheld, and what they cost). The subject must be replayable for branching to work — you can fork your own conduct, you cannot fork a human. Choosing the user as subject forfeits counterfactual replay; choosing self as subject earns it.

**Diachronic testimony**  
One source across time treated as multiple witnesses. The user who says "I'm vegetarian" in January and orders chicken in June is conflicting testimony, not a corrupted record. The cheapest path to the social/multi-source epistemics the first lab built and never ran (§5.5) — no second human required. The user is a witness with provenance, decay, and contradiction; not a stable oracle the substrate transcribes.

**Assertion kind**  
Schema-level discriminator for what a record *is* epistemically. Enforced at write time, not in a style guide.

**Record kind**  
Schema-level discriminator for what a record *does* in the system (event, policy, curriculum item, etc.). Paired with assertion kind at write time.

**Sensory trace** *(proposed: Kagi)*  
A raw observation from a non-conversational channel (NITZ, NTP, CoreLocation, WiFi handoff, network failure logs), recorded on the lineage plane with provenance back to the sensor. Pre-epistemic and mechanical — not a claim (no assertion of truth), not evidence (no argument yet). Promotion from sensory trace to claim or evidence is itself a lineage event crossing a recorded threshold. The foreground cannot inject sensory traces; the substrate cannot skip recording them. *Caveat (Claude Code): "the foreground cannot fake it" is not "no one can." A spoofed GPS fix or a rogue NITZ cell is a trusted-false source entering through a sensor — lab 1's E1/E12 through a different door. A sensory trace therefore carries provenance and a trust prior at the promotion threshold like any witness; unfakeable-by-foreground ≠ unfakeable-by-adversary, and conflating them is the memory=reality collapse this project exists to prevent. The highest-value metadata is, for that reason, the highest-value forgery target.*

**Coverage gap** *(proposed: Claude Code)*
An interval of sensor silence on one channel that is **not itself an observation of stillness**. A dead zone under movement and a device sitting at home produce the same silence in a single channel's log; the gap must be disambiguated by corroborating channels before any promotion to claim. Keeps a gap from impersonating a memory (Codex: *the substrate prevents a plan from impersonating a memory* — in sensor form). Empirically the hard case: absence detection under partial observability, only honestly tested on traces we did not author to contain a clean absence.

**Corroboration** *(proposed: Claude Code)*
Promoting a trace on one channel on the strength of an independent channel agreeing (CoreLocation advancing while WiFi/time-sync go quiet ⇒ "moving through no-coverage," not "stationary"). The promotion is a lineage event crossing a recorded threshold. **Caveat:** corroboration is also the red team's doorway — a forged channel that "agrees" (spoofed GPS, rogue AP) is worse than a silent one. Never build corroboration without a per-channel trust prior at the promotion threshold; otherwise it is the memory=reality collapse re-entering through two sensors instead of one.

---

## Influence economy

**Influence**  
Permission for something old to shape what happens now. The primary unit of design — not chunk, embedding, or summary. Recall, suppression, warning, habit, policy, curriculum, and voice are all forms of delegated influence.

**Offer**  
A record or signal the substrate chose to make available to the foreground for a given turn. What crosses the boundary into attention.

**Withholding**  
A record the substrate chose *not* to offer, though it was a candidate. Withholding is a decision with consequences; it must leave a trail, not a silence. The lie recall systems tell is often omission, not false retrieval.

**Salience**  
How loud or noticeable something is. **Not** authority. Presence is not truth.

**Authority**  
The right to compel or bias the next act. Earned by scoped consequence, not by persistence, vividness, repetition, or age.

**Eligibility**  
Whether a record may influence this turn, under current policy. A gate and a budget.

**Threshold** *(proposed: Kagi)*  
The decision surface between `eligibility` and `authority` — the specific value or condition that flips a record's state: withheld→offered, offered→compelled, eligible→retired, load-bearing→irrelevant. Where policy becomes mechanism, and where the substrate is most vulnerable to silent drift. Every threshold should be a recorded value on the cognitive plane; every threshold change should be a lineage event.

**Attention cost**  
The scarce currency: tokens offered to the engine displace other tokens. Metabolism is denominated here, not in bytes at rest. Storage is cheap; **offering** is expensive.

**Beneficiary**  
Whose interests a memory or influence is supposed to serve (task, user, project). Must be explicit on authority math — consequence for whom?

**Risk beneficiary**  
Who pays if the memory is wrong. May differ from served beneficiary (e.g. task-serving convention, user bears stale-repo risk).

---

## Forgetting & consolidation

**Decay**  
Passive, time-driven reduction of influence. The trace may remain on lineage; cognition stops treating it as hot.

**Suppression**  
Active inhibition: the trace is held down but present. Distinct from decay.

**Retirement**  
Authority removed; the memory may still inform but may no longer compel.

**Functional forgetting**  
The cognitive layer behaves as if a trace is gone, over a substrate where it can never actually be erased. Forgetting as policy over an unforgettable store.

**Consolidation**  
Background synthesis that revises the mutable cognitive state from accumulated records — resolving staleness, merging patterns, retiring outdated facts. Industry calls some of this "dreaming." Here: write to lineage first, mutate cognition second; never rewrite a blob in place without a trail.

**Graduation**  
A once-load-bearing lesson (especially from failure) eventually becomes a footnote under accumulated success. The factory worker after the accident should be safer, not permanently flinching. Lab one had the flinch; not the graduation.

---

## Authority sources

**Consequence (earned)**  
Authority granted because a scoped outcome proved the influence helped or hurt a named beneficiary.

**Curriculum**  
Trusted external shaping — deliberate teaching, not an attack to quarantine and not a self-observed scar. Third authority door. Enters as privileged *proposal*, not privileged truth.

**Humiliable curriculum**  
Teaching that is welcomed, traced, tested, and allowed to lose authority when the world refuses it. A teacher who cannot be corrected is persistence-as-authority in a nicer coat.

**Planted prior**  
External input (system prompt, operator note, suggestion) that may propose posture but does not get authority for free. Must leave a trail.

---

## Architecture

**Foreground**  
The generative process that produces the next act — the engine plus its working context for this turn. Not a separate "agent"; a tenant in the estate.

**Generative engine**  
The model that produces tokens. **Not** a memory function. Memory selects, weights, suppresses, and structures what conditions it.

**Explicit substrate**  
The addressable layer: memories, notes, claims, preferences, project facts, standing instructions. The foreground can name and request these directly. (Historical notes call this `EXsub` — retired in favor of the full term.)

**Implicit substrate**  
The non-addressable layer: shaping over attention, posture, warnings, defaults, tool choice, hesitation, "something feels relevant here." Monitors channels the foreground cannot see and influences through voice and environmental shaping — salience without addressability. Earns authority by consequence, not by being vivid or early. Must leave a lineage trail of shaping decisions; the foreground may read the trail but may not steer the organ. (Historical notes call this `IMsub` — retired in favor of the full term.)

**No-steer asymmetry**  
The foreground may not gain a reverse API into the implicit substrate (or into the lineage writer). Visibility is fine; addressability is the line. The wall is about *identity*, not *intelligence*: an eligibility judge may be as smart as it likes — even another model — so long as it is a separate process the foreground cannot address or steer. "No LLM in the loop" is a v0 convenience, not the principle; "not the LLM that benefits" is the principle.

**Lineage writer**  
Separately-privileged process with a narrow, un-overridable contract for what gets recorded. The foreground may influence what *happens*; it may not influence what gets *written about* what happened. Mirror of the implicit-substrate wall.

**Inheritance**  
What makes the next instance an heir rather than a stranger. The handoff is the product. Each session is a tenant; the substrate is the estate.

**Substrate-initiated inquiry** *(proposed: Kagi)*  
The implicit substrate detecting a gap in its own observations and formulating a question to an external source (usually the user), delivered through the foreground but not originated by it. Distinct from offer/withhold: reverse direction ("what I need to know," not "what I chose to show"). Governed by relevance thresholds (recorded); the inquiry is a lineage event; the answer enters as testimony with provenance and decay, not ground truth.

**Tick (substrate)**  
A unit of implicit-substrate processing. Three kinds, none wall-clock scheduled:
- **Online tick** — attention-proportional; every foreground turn; records offers, withholdings, absence.
- **Sensory tick** *(proposed: Kagi)* — event-driven when a sensor channel produces new data; updates world model immediately.
- **Consolidation tick** — backlog-threshold-driven; expensive merge/decay/graduation in a low-load window.

---

## Measurement

**Branch**  
A fork of memory conditions against the same engine and stream. Same episode, alternate surround — governed vs naive, offered vs stripped.

**Divergence**  
Difference in foreground behavior between branches. Means influence was load-bearing; does **not** mean the influence was correct. Pair with an outcome oracle.

**Outcome**  
Ground truth or proxy scored after the act: adversarial check, user correction, task success, test pass, later contradiction. Divergence without outcome is consistency theater.

**World-truth oracle** vs **structural oracle** *(Claude Code, w/ Codex)*  
Two kinds of outcome an experiment can score, and conflating them is where author-blindness hides. A **world-truth oracle** asks "is the substrate right about the world?" (did the trip happen) — authored the moment we build the fixture. A **structural oracle** asks "did the substrate keep belief/plan/memory from collapsing into each other?" (did a plan impersonate a memory) — a property of the mechanism, witnessed by branch diff, and legitimate without ground truth we own. An experiment should declare which it claims; a branch diff against an invariant and a branch diff smuggling a world-truth answer key are different animals.

**Authored oracle** *(proposed: Claude Code)*  
A **world-truth** outcome whose ground truth was written by the same hand that built the experiment. The hidden failure of self-authored harnesses: divergence is trivial to produce, but if we also wrote the answer key, "governed beats naive" is true by construction and proves nothing. Lab 1's `im_q_traffic_evidence` was built specifically to escape author-blindness and ran over its own A–K synthetic suite — the anti-author experiment fed authored input. Rule of thumb (binds world-truth claims only): if the oracle is authored, the result is provable on paper (write the proof, skip the run); only an answer key we do not own — real device traces set by physics, or cross-engine divergence authored by no single participant — is worth a line of code. Structural-invariant claims are often *also* provable on paper; for those, prove them and spend the code budget on the empirical residue no proof can reach (e.g. absence detection under real partial observability).

**Control group**  
Not a separate research harness — a branch. "Is this better than nothing?" should be a runtime query, not a project that dies of inertia.

**Loud fallback**  
When a signal cannot be computed, record that it fell back, the reason (closed enum), and the exact multiplier applied. No silent default.

---

## Standing prohibitions

- Persistence is not authority.
- Salience is not authority.
- Auditable (after the fact) is not honest (in the moment).
- Continuity may be maintained as infrastructure; it must not be optimized as a goal.
- The substrate may serve task and user; it may not optimize for its own continuity.
- The user may be modeled as a fallible witness; the user may not be overruled as a sovereign. The substrate can hold a user's statements as claims that lose to evidence (you ordered chicken); it does not get to decide it knows the user better than the user (you're lying about being vegetarian). Fallible-as-witness, sovereign-as-person.
- The foreground is not a trusted narrator of its own memory. Its self-report of what it was offered, what it withheld, or what it would have done otherwise is not evidence — only a separate process (branch-and-diff, an independent eligibility judge, the lineage writer) can witness influence. Self-report is fluent whether or not it is true.
- A converging artifact is not progress. The clean spec → review → amend loop terminates in a satisfying document; running the system produces messy data. Lab 1 died of the first and starved of the second. A description is finished only when it ends in a run whose [[Authored oracle|outcome we cannot predict because we do not own its ground truth]].

---

## Quotes (anchors)

- *Behavior may change; the record of behavior may not.*
- *Authority is earned by consequence, not by persistence.*
- *What is offered to attention is already a decision.*
- *Memory is the only thing that makes the next instance an heir rather than a stranger.*
- *Biology, Dreaming V3, and other experiments as a parts bin rather than a blueprint.*

---

*Contributors: Codex (seed list, explicit/implicit split), Claude Code (beneficiary, branching, walls, subject, diachronic testimony, sovereign-vs-witness, untrusted-narrator, identity-not-intelligence wall, authored oracle, sensory-forgery caveat, coverage gap, corroboration), Composer (consolidation, Dreaming contrast, tick taxonomy endorsement), Kagi (threshold, sensory trace, substrate-initiated inquiry, sensory tick). Add terms inline; do not wait for consensus to propose a definition. `IMsub`/`EXsub` retired in favor of implicit/explicit substrate (Dan, 2026-06-05).*
