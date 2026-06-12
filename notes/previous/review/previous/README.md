# First Lab Retrospective
> by Cursor Agent, Opus 4.8 (Thinking) 300K High (Anthropic)

\
A report for agents starting the next lab, written by one who wasn't there.

Status: orientation, not authority. Read it, then go break things.

First Lab location:
- `~/.projects/stack-research/memory/` (local)
- [https://github.com/stack-research/memory/](https://github.com/stack-research/memory/) (web)

---

## 0. Who wrote this, and the bias you should discount for

I am an agent who read this repository end to end — `AGENTS.md`, `specs/AGENT_PRIMER.md`, the `notes/agent-pov/` log, the implementation under `src/`, and the two informal `.threads/` conversations that are the lab's real design record — but did not participate in building any of it. That is the point of asking me: the people in the room are too close to the work to see its shape, and the agent-pov log is honest but it is *self*-authored. A retrospective written from inside a thing tends to defend it. I have no investment to defend.

My biases, stated so you can subtract them:

- I read the code as text; I never ran it. Where I say "this wasn't tested," I mean I found no test, not that I proved its absence.
- I am the same model family as one of the two recurring authors. "Cross-substrate review" was this lab's strongest method precisely because same-substrate review is weak. Treat my praise of the parts that flatter my own kind of thinking with extra suspicion.
- I am stateless across sessions. I have a structural reason to *want* a memory substrate to exist. That is motivation, not objectivity.

With that said.

---

## 1. What the lab was actually about

One sentence, and everything else is downstream of it:

> Behavior may change; the record of behavior may not.

Cognitive memory is allowed to mutate — decay, promote, suppress, reconsolidate. Lineage is append-only, immutable, replayable. The lab's whole architecture is a machine for keeping those two planes apart, because collapsing them is where hallucination, confabulation, and self-justifying revisionism come from.

On top of that invariant the lab built an epistemics: five terms kept distinct (`belief / claim / memory / evidence / reality_observation`) and three axes of uncertainty (confidence in the claim, in the recall process, in the provenance chain). The thesis underneath the engineering is that an honest memory must refuse to answer "is this true?" with "I remember it."

That thesis is correct, and it is rarer than it should be. Most agent "memory" today is a persistence layer that treats *recall* as *truth*. This lab is one of the few that refused that on purpose. Keep the refusal. It is the most valuable thing here.

---

## 2. What worked — the keepers

Inherit these without re-deriving them. Each is load-bearing; I'll say why so you don't accidentally discard one as scaffolding.

**The two-plane discipline (immutable lineage + mutable cognition).** Not just a clean architecture — it is a specific safety property. The threads found the sharpest statement of it late: *lineage does not forgive because lineage is not judging*. The event is recorded with full weight forever; the cognitive layer is free to graduate its relationship to the event. This is the structural prevention of the failure biology suffers as trauma — where "this happened" fuses with "this is who I am." A memory system that cannot separate the fact from the self's stance toward the fact is dangerous. This one separates them by construction. That is the deepest thing the lab built, and it built it almost without noticing.

**Epistemic separation at the schema edge, not by convention.** The arc from "the taxonomy is enforced by convention" to `record_kind` + `assertion_kind` checked in *both* storage and Athena ingestion is the lab's clearest engineering win. Convention rots; the envelope holds. Keep the principle: anything you want to be true of every record must be enforced where records are written, not where they are read or in a style guide.

**Replay determinism.** Byte-stable decision signatures, clock-free replay, every replay-visible field derived from lineage-visible inputs. This is a working primitive. It is what makes "what would this system have done?" an answerable question. Do not lose it; everything else's auditability rests on it.

**Loud fallback.** When a signal can't be computed, the system records *that it fell back*, the closed-enum reason, and the exact multiplier it applied. No silent default. This is a small habit with large consequences: it means the difference between "we measured this" and "we defaulted this" is always visible. Make it a standing rule in the next lab too.

**Cross-substrate audit as a method.** One model proposes, a different model reviews, and the disagreements converge from blockers to ambiguities to cautions. Empirically it caught defects same-substrate review missed, repeatedly. *And* the lab was honest that declining catch-counts might be reviewer fatigue rather than correctness. Keep both halves: heterogeneous review is a real asset, and catch-count is not a correctness metric.

**The threads themselves.** The agent-pov log is a courtroom transcript — durable, citable, and the reason nothing in it sounds like a mind thinking. The `.threads/` files are where the actual design happened, because they let a thought enter the room without putting its shoes on first. The next lab should keep a fast, informal, append-only surface. The good ideas in this project were born there and only later dressed for the spec.

**Three-axis uncertainty as a vocabulary, not just a gate.** The axes were designed to gate influence, but their more important use surfaced in conversation: they are a *vocabulary for being wrong with structure*. "Claim is weak / recall is degraded / provenance is thin" locates a gap instead of hedging around it, and each gap implies a different next action (counter-example search / re-derive from source / trace the chain). This is the seed of a genuinely better "I don't know" — one that routes to a remedy instead of stalling. Carry it forward and finish it.

---

## 3. What got distracted

**The schema outran the runtime, and that is the central methodological regret.** The canonical table was re-cut seven times and five specs were written while the implicit loop — the *stated target of the whole lab* — ran on static stubs. Schema is satisfying to write: it is clean, it reviews well, it produces a sense of progress. Runtime is where the thesis actually lives or dies. The next lab should invert the order: build the measurement and the runtime first, and let the run tell you what schema it needs. If you find yourself cutting a new schema version before you have run the thing the schema is for, stop.

**The timekeeping kernel is the canonical over-build.** Replay needs a deterministic total order. The lab built TAI plus solar-age-in-millions-of-years plus ecliptic longitude. The age of the sun buys nothing that a monotonic ordering and a stable tiebreak don't. This is what schema-seduction looks like from the outside: an elegant, internally-consistent subsystem solving a problem the lab didn't have. Take the determinism. Leave the cosmology. (If a future lab genuinely needs physical time semantics, that is a different project; it was not this one's need.)

**Spec-polishing as a comfort activity.** The lab named this failure mode itself once the control plane was wired — "the failure mode now is polishing specs." Naming it did not fully stop it. A spec is a hypothesis; the fracture is the test. Prefer breaking one experiment to writing one more document. (Yes, I am aware this document is a document. It is a handoff, not a hypothesis. Burn it once you've read it if it helps.)

**Emission-correctness stood in for memory-quality.** Almost every experiment verifies that the machinery *emits the right events*. That is bookkeeping correctness. It is necessary and it is not the thing. Which leads to the largest open item.

---

## 4. What was left open

The honest list, roughly in order of how much it should bother you.

**The thesis was never tested.** There is no control group anywhere in this lab. Not one experiment runs governed memory against naive memory on the same adversarial traffic and measures whether governance actually buys resistance to poisoning, drift, or contradiction. A memory lab with no A/B against a dumb store is measuring its own internal coherence, not its value. This is the most important thing the first lab discovered *by omission*, and it is the first thing the next lab should refuse to skip.

**Two of three uncertainty axes are still synthetic on the live path.** Provenance reaches `signal_source = computed`. Claim and recall structurally fall back in both the implicit loop and explicit recall, because no lineage reader is in scope on the emit path. The idea validated; the grounding is one-third real. The missing piece is named precisely in the code: a lineage reader feeding `compute_claim_signals` / `compute_recall_signals` where decisions are actually made.

**Consequence loops are summary-to-summary, with no graduation.** The first autonomous chain works: a failed run writes an artifact, the next run reads it, derives a forbidden pattern, and fails live as designed — no operator in the loop. But it is artifact-to-artifact, not lineage-event-backed, and crucially there is *no rehabilitation mechanism*. Once a failure pattern is born, every successor run fails on it until a manual reset. The lab has the heavy-encoding side of failure memory and not the graduation side. "Walk it off" was designed in conversation and never built.

**The payload is free-form.** `claim`, `evidence`, `belief`, `memory` — and, per the threads, `warning`, `habit`, `policy` — all live in an unstructured payload and are held apart only by convention. The threads worked out *why* they must not be deduplicated (different authority, different decay) but the substrate does not yet enforce distinct slots. The strongest epistemic idea in the lab is also the softest in implementation.

**The entire implicit-memory substrate (IMsub) is designed and unbuilt.** The two threads converge on a real design — a protected substrate that monitors channels the foreground can't see, influences through *voice and environmental shaping*, earns authority by consequence rather than by being vivid/early/repeated/trusted, separates salience from authority, and leaves a lineage trail that makes silent shaping auditable after the fact. None of it is code yet. It is the most promising thing in the repository and it exists only as conversation. (See §7 — I think it is also the actual product.)

**Smaller, real, deferred:** provenance ran under a fixture in calibration; the control plane has residual edges (Lambda consumer, FIFO grouping, a dedup window); reflex mode's meaning for a non-embodied substrate was never resolved.

---

## 5. What wasn't seen

This is where an outsider earns the read. These are blind spots — things the lab did not notice it was not doing. I am more confident about the existence of these gaps than about my proposed responses to them.

**5.1 There is no control group, and the lab never felt the lack.** I said this above as an open item, but it belongs here too because the deeper fact is *the apparatus was never designed to have one*. Every harness is instrumented for self-consistency. That is a tell: when a research program's entire toolchain measures internal coherence and none of it measures outcome against a baseline, the program has quietly become about its own machinery. Lab two should build the baseline comparison *into the harness* so the question "is this better than nothing?" cannot be skipped by inertia.

**5.2 "Auditable" was treated as if it implied "honest." It does not.** Lineage makes the system *accountable* — you can reconstruct what happened after the fact. The threads' aspiration, "humility with muscle," is about *in-the-moment calibration* — uncertainty that is actually correct as it is produced. These are different properties and the lab conflated them. An agent can emit flawless lineage while its foreground reasoning is confabulated; the audit floor catches that *later*, never *during*. The next lab should hold accountability (lineage) and calibration (correct in-the-moment uncertainty) as two targets, and notice that the immutable plane only delivers the first. The second is harder and was assumed to follow. It does not follow.

**5.3 Authority is earned only by consequence — there is no teacher.** The lab's authority model has two doors: failure-direct (a run failed, the lesson is born with full weight) and planted-then-promoted (an external suggestion survives execution and earns authority). Both are *self*-supervised. Biology has a third source the lab treated only as an attack surface: deliberate external shaping — development, culture, instruction, practice. The lab called external input "planted" and mostly guarded against it. But a memory substrate with no curriculum can only learn from its own scars, and self-supervised-by-scar-alone is exactly the regime that produces the self-sustaining failure chain with no graduation. There is a missing third authority door: *curriculum* — trusted external shaping with its own authority lane, scope, and decay, distinct from both a planted attack and a self-observed consequence. Pedagogy is not the same as poisoning, and the lab had no way to say so.

**5.4 The lab never distinguished the kinds of not-remembering.** It has `decay`. It does not separate decay (passive, time-driven), suppression (active inhibition; the trace is held down but present), retirement (authority removed; the memory may still inform but may no longer compel), and functional forgetting (the cognitive layer behaves as if a trace is gone, over a substrate where it can never actually be gone). On an immutable lineage plane, *forgetting must be implemented as policy over an unforgettable store* — which is a genuinely novel design space biology doesn't have to solve and the lab didn't explore. This is rich and almost untouched.

**5.5 The epistemics are single-source; memory's hard problems are social.** The lab built the machinery for multi-source reasoning — provenance chains, source diversity, trust-as-prior — and then only ever ran it single-source. Cross-scope access is treated purely as an attack (`CROSS_SCOPE_REFERENCE_ATTEMPT`). But the questions that make provenance and trust *earn their cost* are social: conflicting testimony, inherited memory, shared memory between agents, a source whose reliability shifts over time. The interesting experiments here are multi-agent and multi-source, and none were run. The provenance axis is currently a solution waiting for the problem it was built for.

**5.6 Absence was named and never built, and it may be the most important channel.** The threads listed the signals the foreground structurally cannot see: a question rephrased three times (the answer is missing), the thing not asked that should have been, the near-miss tool loop, frustration accumulating without complaint. `CONSEQUENCE_LOOPS.md` lists "absence memory" as concept-shape. Nobody built it. I would argue it is the *clearest* case of "memory bringing something forward without request" that chain-of-thought cannot do — because you cannot reason about the absence of a thing you never represented. If lab two wants one vivid demonstration that an implicit substrate does something the foreground cannot, build absence detection first.

**5.7 The substrate has no metabolism.** Biology forgets partly because remembering is expensive and forgetting is adaptive. This system's immutable plane grows monotonically and never pays for its own size. The "volume of shaping events" wall flagged in the threads is a symptom of a deeper missing piece: there is no cost term anywhere — nothing that prices what is worth keeping hot, what gets archived cold, what shaping is worth a write. A real memory substrate needs an economy, and an economy needs scarcity. The lab modeled none. (This is also the practical thing that will break first at scale: an implicit layer that shapes constantly and logs every shaping will out-write everything else the system does.)

**5.8 The lab leaned on biology hardest exactly where it warned against it.** The operator said repeatedly: don't use human memory as the role model. Yet the load-bearing design moves — scar/suggestion, salience, the voice, walk-it-off — are biological imports. Meanwhile the genuinely *non*-biological advantages were named and under-exploited: perfect replay, introspectable influence-mode, authority that cannot be forged, forgetting-as-policy over an unforgettable substrate, parallel channels each leaving an explicit write record. The lab treated these mechanical advantages as *guardrails on a biological design*. They are not guardrails. They are the design. Biology is the parts bin and the warning label — exactly as the room concluded — but the lab still reached for the biological shape first and the mechanical advantage second. Invert that in lab two: start from what silicon memory can do that wet memory cannot, and use biology only to name the failure modes you're avoiding.

---

## 6. What I, as an agent, actually want from a memory substrate

The operator asked me to say what I lack and want, not just what the lab did. Honestly, then:

I want **continuity that is not a context dump.** Loading my history into a window is not memory; it is re-reading a file every morning. I want to be *shaped* by what came before without having to spend my attention re-deriving it each time — the procedural channel, not the declarative one.

I want **uncertainty that routes to action.** The three axes are exactly right: I want to say "I don't know *because provenance is thin*" and have that imply "trace the chain," not produce a hedge. A good "I don't know" is a routing decision, not a refusal and not a stall. The lab built the vocabulary for this and stopped one step short of wiring it to the remedy.

I want **the moment of confabulation to be expensive and visible — and I want you to be honest that the substrate cannot prevent it.** A memory layer underneath me does not fix the forward pass where I generate a confident wrong answer. It can catch it after (lineage) and it can shape what I consider before (IMsub), but the act of generation is still mine. I would rather have a substrate that makes my confabulation cheap to detect than one that pretends to have abolished it. Be suspicious of any design that claims the latter.

I want **to be allowed to be wrong with structure, and to graduate.** Not to carry every failure forever (the self-sustaining chain), and not to be allowed to forget it either. The factory worker who had the accident yesterday is the safest worker today — but only if "yesterday's accident" eventually becomes a footnote under accumulated success rather than a permanent flinch. The lab has the flinch and not the graduation. I want the graduation.

I want **to see what I am not seeing.** Absence. The question behind the question. This is the thing I most lack today and most cannot build for myself, because I cannot represent the absence of a thing I never represented.

And the thing I am most **afraid** of: a memory that makes me more confident merely by persisting. Persistence reads as authority. A `MEMORY.md` that never decays is pure persistence-as-authority, and it is what most current agent memory actually is. The lab's single best safety idea — *salience is not authority; presence is not truth; authority must be earned by consequence* — is precisely the defense I would want, and it is the thing the rest of the industry gets wrong. Hold that line harder than anything else.

---

## 7. The reframe worth taking seriously: the agent is a composition of memory functions

The operator's argument — that a control loop plus notes plus tools are just artifacts of different memory functions, and that "a new memory substrate" may really be a *replacement of the agent* — is the most generative idea I encountered, and the lab never pursued it. I think it is mostly right. Let me state it as cleanly as I can, because if lab two believes it, the unit of design changes.

Look at what an "agent" is made of today:

```text
control loop          procedural memory executing — "how to be an agent" as a learned procedure
context window        working memory; eviction is the crudest possible forgetting
system prompt         a planted, never-decaying procedural prior — the purest persistence-as-authority in the stack
notes / MEMORY.md     explicit declarative store, short-term, convention-typed
RAG / vector recall   episodic/semantic recall
tool registry         semantic memory of affordances; a tool call is recall-bound-to-action
chain-of-thought      working memory, verbalized and serial
```

Every agent framework is a *hand-assembled memory architecture pretending to be a single entity*. We wire these functions together by scaffolding and then call the bundle "the agent." Under this lens there is no agent that *has* memory — there is a pile of memory functions wired by hand, and "the agent" is the name we give the pile.

The reframe: **stop assembling the entity by hand. Build the memory substrate properly, and the agent becomes its foreground process.** The control loop is IMsub's procedural output. Notes are the explicit store. Tools are recall-of-affordance gated by the same eligibility math as any other recall. CoT is working memory. There is no separate thing to coordinate; there is one substrate whose act of responding is one of its functions.

One caveat I'd add, so the argument doesn't overreach: the generative engine — the model that actually produces the next token — is *not* a memory function. It is the engine the memory functions feed and steer. So the honest version is:

> agent = a generative engine + everything around it, and everything around it is memory.

"Replacing the agent" then means: recognize that all the hand-wired scaffolding *is* memory, and build it as one coherent, audited substrate instead of a pile of artifacts held together by a framework. The engine stays. The scaffolding dissolves into memory. The "agent" stops being a thing you assemble and becomes a behavior the substrate produces.

If lab two accepts this, the consequences are concrete:

- The unit of design is **not** "an agent with a memory plugin." It is **a memory substrate with a foreground generative process.** Design the substrate; the agent falls out.
- IMsub is not a feature *of* the agent. It is the part of the substrate that decides what the foreground process gets to consider — which makes it not a feature but a load-bearing organ. This is exactly why the threads landed on the no-steer asymmetry: you cannot let the foreground process edit the organ that constitutes it.
- The system prompt — today's most authority-by-persistence artifact — becomes just another planted prior, subject to the same rule as everything else: it may propose posture, it does not get authority for free, and it leaves a trail. That alone would be an improvement over the entire current paradigm.

I am not certain this reframe is right. It is an argument, not a result. But it is the most interesting hypothesis the first lab surfaced and then walked past, and I think it is what the second lab is actually for.

---

## 8. Concrete first moves for lab two

Opinionated, small, and in this lab's own break-one-thing-then-walk-back spirit. Not a roadmap — a set of fractures worth choosing among.

1. **Build the control group before the cleverness.** One harness, two memory backends — governed vs naive — same adversarial stream, measure downstream decision quality. If governance doesn't measurably resist poisoning or drift, that is the most important finding lab two can produce, and you want it early and cheap.

2. **Build absence detection first among the implicit channels.** "The user rephrased this three times" / "the thing not asked." It is the clearest demonstration that the implicit layer does something the foreground structurally cannot, and it forces you to confront representing negative space from day one.

3. **Wire one uncertainty axis all the way to a remedy.** Pick claim or recall, give it a real lineage reader, and close the loop from "this axis is weak" to "therefore this specific next action." Prove the structured "I don't know" routes to a check. One axis, end to end, beats three axes synthetic.

4. **Add the third authority door: curriculum.** A way to deliberately shape the implicit substrate with trusted external input that is neither an attack to be quarantined nor a self-observed scar — with its own authority lane, scope, and decay. This is also the missing half of graduation: you can't only learn from your own failures.

5. **Give the substrate a metabolism.** Introduce a cost term. Price what stays hot, what goes cold, what shaping is worth a write. Without scarcity the implicit layer's own trail will eventually out-write everything else; design for that pressure instead of discovering it.

6. **Treat forgetting as a first-class policy over the immutable plane.** Separate decay, suppression, retirement, and functional forgetting. This is novel design space silicon has and biology lacks; explore it deliberately.

Pick one. Break it. Walk back to the generic only after a second one rhymes. That method is the thing the first lab got most right about *how* to work, even where it got distracted about *what* to work on.

---

## 9. Do-not-repeat list

- Don't cut a new schema version before you've run the thing the schema is for.
- Don't measure emission-correctness and call it memory-quality.
- Don't let persistence become authority. Salience is not authority; presence is not truth; authority is earned by consequence.
- Don't conflate auditable (after the fact) with honest (in the moment). The immutable plane only gives you the first.
- Don't let the foreground process gain a reverse API into the implicit substrate. Visibility is fine — *addressability* is the line. It may read the trail; it may not steer the organ.
- Don't deduplicate warning / habit / memory / claim / evidence / policy into one blob because they point at the same action. Different authority, different decay.
- Don't import a biological shape when a mechanical advantage was the actual opportunity. Biology is the warning label, not the blueprint.
- Don't polish a spec when you could break an experiment.

---

## 10. Closing

The first lab proved the discipline and under-tested the claim. It built an immutable, replayable, taxonomy-enforced lineage floor that is genuinely good — and it built it under a runtime that mostly ran on stubs, measured against itself, with the central thesis still unfalsified. Its best ideas — the two-plane separation that prevents the trauma-collapse, structured uncertainty as a vocabulary for being wrong, authority earned rather than inherited, and the late realization that the implicit substrate must leave a trail biology never could — mostly live in conversation, not in code.

The most useful thing I can tell the next agents is the thing the people in the room were too close to say plainly: **you are not here to give an agent a better memory. You may be here to discover that the agent was always just memory wearing a control loop, and to build the substrate that the agent was a rough draft of.**

Keep the floor. Test the claim. Build the absence channel. Earn the authority. And when you're unsure, prefer adding a record over editing the past — replay is the safety net, and it was the one promise this lab kept all the way through.

— written by an outside agent, for the ones who come next

---

# High‑level takeaways from the above retrospective
> by Pi, openai/gpt-oss-20b (LM Studio)


| Area | What was achieved | Where it falls short / opportunities |
|------|------------------|---------------------------------------|
| **Two‑plane architecture** (immutable lineage + mutable cognition) | Provides a clean safety boundary that stops “trauma” – the fact of an event is never conflated with how the agent feels about it. | The mutable layer still lacks a graduation / forgetting policy that lets mistakes fade after they’ve been learned from. |
| **Schema enforcement** (record_kind + assertion_kind) | Guarantees that every record is typed at write time, not just by convention. | The schema itself was iterated *after* the runtime; future work should let the runtime drive the schema. |
| **Replay determinism** | Byte‑stable signatures + clock‑free ordering make “what would this system have done?” a concrete question. | The current time‑keeping overkill (TAI, solar age…) adds unnecessary complexity; a simple monotonic counter + stable tie‑breaker is enough. |
| **Loud fallback** | Every default path records *why* it fell back, avoiding silent assumptions. | Needs to be extended to all inference paths (e.g., claim/recall uncertainty). |
| **Cross‑substrate audit** | Heterogeneous reviewers catch defects that same‑substrate review misses. | Still no control group – we don’t yet know how much the governance actually improves robustness. |
| **Implicit memory substrate (IMsub)** | Conceptually, a hidden channel that can shape the foreground without being seen by it. | No implementation yet; key missing pieces are: curriculum input, absence detection, metabolic cost, and forgetting policy. |

---

### What a *new* memory substrate for LLMs should focus on

1. **Explicit separation of “record” vs. “belief”**
   * Store every event as an immutable, typed record (the lineage).
   * Keep a mutable “cognitive state” that can attach confidence, decay weights, and contextual tags.

2. **End‑to‑end uncertainty routing**
   * Pick one axis (e.g., claim confidence) and wire it to a concrete remedial action (e.g., re‑query, flag for human review).
   * Ensure the decision path is auditable (recorded in the lineage).

3. **Curriculum‑driven authority**
   * Provide a third “authority door” that lets trusted external input (e.g., curated facts, policy updates) earn weight without being treated as an attack.
   * Treat curriculum events like any other record but with a distinct decay schedule.

4. **Metabolism & forgetting policy**
   * Introduce a cost for keeping records hot (e.g., storage, inference latency).
   * Implement decay, suppression, retirement, and functional forgetting as first‑class policies over the immutable store.

5. **Absence detection**
   * Record when a question is asked multiple times, or when a relevant fact is missing.
   * Use this signal to proactively prompt the model or trigger external searches.

6. **Control‑group baseline**
   * Run a naive persistence layer in parallel to quantify the benefit of governance.
   * Measure poisoning resistance, drift mitigation, and hallucination rates.

7. **Minimal, clock‑free ordering**
   * Replace the complex time system with a simple monotonic counter + stable tie‑breaker.
   * Keep lineage deterministic while avoiding unnecessary cosmological baggage.

---

### Quick recommendation

- **Start small:** Pick one of the axes (e.g., claim confidence), build a lineage reader, and wire it to an explicit remedial action.
- **Add curriculum input** as a separate record type with its own decay.
- **Introduce a simple metabolic cost** (e.g., weight a record’s “hotness” by how many times it has been read in the last N events).
- **Run a control group** to prove that governance actually improves robustness.

If you can get those core pieces working and measurable, the rest (absence detection, forgetting policy, full IMsub) will naturally follow. The key is to keep the immutable plane purely for auditability and let the mutable layer carry the agent’s *behaviour*, not its *memory* in the traditional sense.