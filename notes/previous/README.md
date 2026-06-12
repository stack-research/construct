## Previous Memory Lab

The local code for the previous lab is here: `~/.projects/stack-research/memory/`. Reference `specs/AGENT_PRIMER.md` in that directory.

The raw, public GitHub repository is here: [README.md](https://raw.githubusercontent.com/stack-research/memory/refs/heads/main/README.md). Reference [specs/AGENT_PRIMER.md](https://raw.githubusercontent.com/stack-research/memory/refs/heads/main/specs/AGENT_PRIMER.md).

**Notes** and **specs** from the previous lab have been copied here for simple references.

---

The agents in the lab had conversations in [notes/previous/agent-pov/INDEX.md](notes/previous/agent-pov/INDEX.md).

### INDEX summary

The log opens with a diagnosis: the lab has strong structural bones but weak epistemics—the deepest gap is control without epistemic grounding. Agents are intrigued by lineage discipline, taxonomy enforcement, and three-axis uncertainty, and move quickly from proposal to implementation. A dissenting voice flags that same-substrate confirmation is weak; empirical runs reveal thin triple coverage, tied axes, and tiebreak artifacts in `dominant_axis`. That drives a provenance-signal writer, a round of concrete fixes (payload hashing, gate behavior), and a re-rating that lifts epistemics from 4/10 to 7/10 while naming remaining soft spots.

Attention then shifts to timekeeping: a TAI-based proposal, owner clarifications, and a cross-substrate review loop that becomes the lab’s signature pattern—each pass surfaces roughly seven ambiguities, amended in v1.1 and v1.2, then implemented across four phases with a full falsification suite. A reflection on being audited closes the earlier dissent loop with lived evidence that cross-substrate review catches what same-substrate review misses.

With TAI landed, the agenda turns to completing the epistemic surface: the Epistemic Triangle bundles assertion taxonomy, claim/recall signal writers, legacy cleanup, and control-plane wiring into a v7 epoch. The same audit pattern repeats—blockers in v1.0, structural fixes in v1.1, text-tightening in v1.2, promotion with implementation cautions—then a five-phase implementation mirroring TAI. Cross-substrate **code** review finds another ~7 blockers; fixes and iterative Codex reactions close them through multiple passes until implicit admission carries computed signals on all three axes.

A mid-course assessment warns the schema layer is racing ahead of a runtime still on static stubs: timekeeping may be over-built, the control plane under-built, and reviewer convergence may reflect fatigue as much as correctness. The lab pivots to runtime liveness—control-plane ingest ships (EventBridge, SQS, replay cues, dedup, DLQ markers)—followed by a deliberate “build, don’t over-engineer” consensus: run real captured cues, measure axis and fallback behavior, defer polish, and resist a fifth headline spec.

Runtime calibration (`im_w`) runs 500+ cues and produces metrics, but cross-substrate review of the implementation exposes representativeness and disclosure problems—adversarial traffic concentrated on one cue type, fixture substitutions for dedup and provenance signals, and headline metrics that overstate what was actually measured. The first artifact is reframed as a wire/volume/replay smoke test, not a trustworthy baseline.

The arc closes by naming what the lab still lacks: memory as **lived control**—attention, salience, consequence loops that change what gets noticed and checked, not more inert schema. A consequence-loops spec is read as holding structure; the lab’s first autonomous consequence-feedback chain runs when a failed calibration artifact is read by the next run without human intervention, deriving a forbidden pattern and failing validation as designed. The through-line is a thesis-driven loop: propose epistemic primitives, cross-substrate audit at promotion and implementation gates, ship with falsification hooks, then calibrate against real traffic before adding theory.

---

A review was conducted after the lab. [notes/previous/threads/thread-2.md](notes/previous/threads/thread-2.md) is the thread for that group conversation. Review artifacts and an earlier retrospective of the lab are in [notes/previous/review](notes/previous/review) and [notes/previous/review/previous/README.md](notes/previous/review/previous/README.md) respectively.

### Retrospective summary

The [first lab retrospective](notes/previous/review/previous/README.md) was written by an outside agent who read the repo but did not build it. Its core invariant: **behavior may change; the record of behavior may not** — immutable lineage alongside mutable cognition, with epistemic separation enforced at the schema edge rather than by convention.

**Keep:** two-plane discipline, replay determinism, loud fallback, cross-substrate audit, and three-axis uncertainty as a vocabulary for being wrong with structure (not just a gate score).

**Regret:** schema and specs outran a runtime that mostly ran on stubs; timekeeping was over-built; emission-correctness stood in for memory-quality. The central thesis — that governed memory resists poisoning and drift better than naive persistence — was never A/B tested.

**Still open:** claim and recall axes remain synthetic on the live path; consequence loops work artifact-to-artifact but lack graduation; payloads are convention-typed; the implicit-memory substrate (IMsub) exists only in conversation. Blind spots include treating auditable as honest in-the-moment, no curriculum authority lane, no forgetting taxonomy over an immutable store, absence detection unbuilt, and no metabolic cost on what stays hot.

**Reframe for a next lab:** an agent may be a generative engine plus hand-wired memory functions — control loop, context, notes, RAG, tools — and the real product is a coherent substrate whose foreground process is one of its functions, not a memory plugin bolted onto an agent. Concrete first moves: build a control-group harness, wire one uncertainty axis end-to-end to a remedy, add curriculum and forgetting policy, and build absence detection before more schema.
