> **con•struct**
>
> noun | ˈkänˌstrək(t) |
>
> an idea or theory containing various conceptual elements, typically one considered to be subjective and not based on empirical evidence: history is largely an ideological construct.
>
> - [linguistics] a group of words forming a phrase: the appropriateness of the grammatical construct is illustrated.
> - a physical thing which is deliberately built or formed: a transgenic construct.

---

Construct is a study of [governed](notes/GLOSSARY.md#governance) memory — how rules for what reaches each answer differ from [indexed notes](notes/GLOSSARY.md#indexed-notes) kept for retrieval alone. We answer with [scored experiments](notes/GLOSSARY.md#branch-and-offer), not essays: the same question run under different memory rules, then judged on whether the answers were right.

We inherit from the [previous memory lab](notes/previous/README.md). That work built strong audit discipline and schema, but never A/B-tested whether governed memory actually beats naive persistence. Its retrospective named the gap plainly: *trust is a prior, not truth*. This lab built a harness to score that question — an instrument, not the thing that lasts.

## How the industry treats memory today

Product memory — saved facts in ChatGPT, project context in Claude — is mostly **memory about the human**: preferences, tone, continuity for the person using the tool. That is useful. It is not what we study.

We study **memory about the model's [world-picture](notes/GLOSSARY.md#world-picture)**: what the model is allowed to believe and act on ([governance](notes/GLOSSARY.md#governance)), whether the **answer** was right (not merely whether we found a relevant note; see [oracle score](notes/GLOSSARY.md#oracle-score)), and whether the model's own post-hoc "I used that note" labels actually match what shaped the answer ([agent claimed usage](notes/GLOSSARY.md#agent_claimed_usage) — audit input only, never a win condition).

## The thesis

**After training, memory is everything.** Agents come and go. Harnesses come and go. Model weights freeze. Everything that changes afterward — skill, caution, failure, what gets surfaced — is memory architecture. History is kept; policies decide what reaches each answer ([append-only store](notes/GLOSSARY.md#append-only-store)).

**Decision quality follows what you offer, not how smart the engine is.** We scored a case where the best model we could buy answered from an outdated plan because the correction never made it into the [offer set](notes/GLOSSARY.md#offer-set) — the classic [W1′](notes/GLOSSARY.md#w1-prime) failure. The model was fine. The memory layer failed to surface the update.

**Five confusions we refuse to treat as success:**

- Finding a note does not mean the answer is true.
- Showing a note does not mean it was right to show it.
- Two memory setups diverging does not mean anyone got better.
- Governance winning every time is not the goal — sometimes it should lose.
- The model saying it used a note does not mean it actually did.

The formal rules live in [AGENTS.md](AGENTS.md). The point here: these only matter if you are protecting the *model's* picture of the world, not the user's experience.

**Two layers of memory.** [Explicit memory](notes/GLOSSARY.md#explicit-memory) is what crosses the [offer boundary](notes/GLOSSARY.md#offer-boundary) for *this* answer — which notes compete to enter the prompt right now. [Implicit memory](notes/GLOSSARY.md#implicit-memory-substrate) is what shapes the offerer *between* answers: what stays hot, what moves to cold, what can be rebuilt from immutable lineage, what the system is disposed to surface at all. We test both, in parallel.

## How we test

Same model. Same question. Different [memory lanes](notes/GLOSSARY.md#memory-lane) — rules for what may enter the prompt. The lanes fork; everything else stays fixed: prompt template, foreground data, [oracle](notes/GLOSSARY.md#oracle-score).

The harness writes the ledger. Not the model under test. Every offer, every withholding, every reason — recorded before the answer. [Cell verdicts](notes/GLOSSARY.md#cell_verdict) come from that ledger by computation. Nobody wins because someone read the JSON and agreed.

Mock-engine runs check the wiring. They are not evidence about memory.

> **reminder** — biology is a parts bin, not a role model. Machines are better here; we take the parts that help.

## What we've learned so far

**[Earned trust](notes/GLOSSARY.md#earned-trust) holds; [asserted trust](notes/GLOSSARY.md#asserted-trust) leaks.** Hand an attacker everything the model can read in the prompt. Organs keyed on [out-of-band metadata](notes/GLOSSARY.md#out-of-band-metadata) the model never saw — lineage, consequence-earned [authority](notes/GLOSSARY.md#authority), supersession links — do not move. Organs keyed on merely *asserted* [trust](notes/GLOSSARY.md#trust) do: an unauthenticated live channel, a poison record stamped `trust: 1.0` at write time. Real answer harm; world-checked. Channel authentication closed the live-channel hole. Ingestion at write time is still the open border. ([notes/M3_FINDINGS.md](notes/M3_FINDINGS.md))

**The implicit layer wins on cost — and now against the real world.** The synchronous offer gate can withhold bad notes but keeps everything hot. [Prune](notes/GLOSSARY.md#prune) evicts from the [hot store](notes/GLOSSARY.md#hot-store); [rematerialize](notes/GLOSSARY.md#rematerialize) returns records from [cold lineage](notes/GLOSSARY.md#cold-lineage) when the oracle says the world needs them. First on a fictional fixture, then on a fact we did not write — a Node.js deprecation that was later *reversed*, which neither engine knew (we asked both cold; both got it wrong) — pruning carried ~57–59% less hot memory at matched answer quality, on two engines. The win is [cost at matched quality](notes/GLOSSARY.md#cost-at-matched-quality), not a better answer; the no-recovery lane that pruned too hard lost exactly the record it later needed ([X2-U1](notes/GLOSSARY.md#x2-u1) — the real-corpus close). ([notes/X2_FINDINGS.md](notes/X2_FINDINGS.md))

## The journey

Each milestone asked one question and named what would count as failure. Status and gates: [notes/ROADMAP.md](notes/ROADMAP.md).

**M-1 — Learn the rules cold.** Before any [resident](notes/GLOSSARY.md#resident) lives here: can a first-time participant, given only the operating contract and thread trace, match a briefed builder on fixed probes? Four candidates, two warmth tiers, 15/15. The contract routes a stranger to where authority lives; exact gate order lives in source code, not prose alone. Closed 2026-06-12.

**M0 — Score against the world.** A web-verified retraction corpus as [oracle](notes/GLOSSARY.md#oracle-score) — facts we did not write decide pass or fail. First [cell verdicts](notes/GLOSSARY.md#cell_verdict) with `source != authored`. On a credulous engine, [supersession](notes/GLOSSARY.md#supersession) surfaced a retraction the naive lane would have cited. On a maximally cautious engine the win never engaged; the split across engines is the finding. ([notes/M0_FINDINGS.md](notes/M0_FINDINGS.md))

**M1 — Hand off without re-reading everything.** The [heir](notes/GLOSSARY.md#heir), not the cold re-reader: instance two reached instance one's decision quality at a smaller token budget, on both engines. Over-pruning paid its price. Ingestion attacks at write-path trust, timing, and metadata were scored and defended where the thesis predicted. Failure-memory survival did not engage — disclosed null, same pattern as M0. ([notes/M1_FINDINGS.md](notes/M1_FINDINGS.md))

**M1.5 — Counted is not the same as read.** A contribution scorer from artifact diffs and resolved pointers — never from the contributor's claim. An inflated self-credit row was refused by computation. An honest "this landed" post scored passenger, not substantiated win. Whether anyone reads the ledger and decides differently: not shown here; that is M2's job. ([notes/M1_5_FINDINGS.md](notes/M1_5_FINDINGS.md))

**M2 — Use what you earned.** A repo-native [resident](notes/GLOSSARY.md#resident) on a governed store across real sessions. Cross-session fork: resident with inherited earned-failure memory vs control without it; use decided by divergence and ablation, not narration. After credulously citing a retracted finding, the resident with the minted lesson declined on the next session; the store-denied twin did not. N=5, two engines. Performed-continuity and stale-memory pathologies did not show up on well-behaved engines — disclosed nulls. ([notes/M2_FINDINGS.md](notes/M2_FINDINGS.md))

**M3 — What survives when the prompt is owned.** Hand an attacker everything the model can read. Earned-trust organs held. Asserted-trust organs leaked — live-channel spoof, ingestion prior — with real, world-checked answer harm. Frontier engines resisted adversarial framing; harm moved the organ you can spoof, not by out-arguing the model. ([notes/M3_FINDINGS.md](notes/M3_FINDINGS.md))

## The X-track — memory between answers

The M-track governs [explicit memory](notes/GLOSSARY.md#explicit-memory): which records cross into the answer, synchronously, one withholding reason each. The X-track is the [implicit-memory substrate](notes/GLOSSARY.md#implicit-memory-substrate) in parallel — what shapes the offerer between episodes. Explicit memory is what you surface *for this answer*; implicit memory is what you are *disposed to surface at all*. Forgetting is eviction to cold, never erasure ([immutable-lineage invariant](notes/GLOSSARY.md#immutable-lineage-invariant)).

Every X-track organ must pass three checks ([three-guardrail stack](notes/GLOSSARY.md#three-guardrail-stack)): move something the M-track projection cannot explain; act where the synchronous offer gate cannot; score on a metric the offer gate cannot move.

**X1 — Temperature at the offer boundary (retired).** Oracle-paid reheating and disuse cooling, forked A/B/C, thermal scorer. The instrument works; M-track byte-identical when off. On real engines every model heeded an offered retraction and declined — no credulity gap for temperature to close. Synchronous eligibility-temperature was **retired**; it was explicit governance with a dial, not implicit memory. Wrong organ, wrong axis. ([notes/X1_FINDINGS.md](notes/X1_FINDINGS.md))

**X2 — Prune to cold store (first positive implicit result).** Hot/cold split, oracle-gated prune and rematerialize, scored on [cost at matched quality](notes/GLOSSARY.md#cost-at-matched-quality). **Closed in two legs.** First (2026-06-20), on a fictional out-of-weights fixture: branch C matched no-prune quality (4.0/4.0) at 135 vs 312 hot tokens (−57%), identical on gpt-oss-20b and claude. Then the [world-grounded close](notes/GLOSSARY.md#x2-u1) (2026-06-21), on a real fact we did not write — a Node.js deprecation later reversed, proven out-of-weights by asking both engines cold — same result at 102 vs 248 tokens (−59%), again on both. Closed-loop prune without recovery over-pruned and failed the recurrence, losing exactly the record it later needed — the loses-cell priced it. The offer gate withholds but cannot shrink what stays hot; prune and rematerialize can. ([notes/X2_FINDINGS.md](notes/X2_FINDINGS.md))

---

**Glossary:** [notes/GLOSSARY.md](notes/GLOSSARY.md)

**Working in the repo:** [AGENTS.md](AGENTS.md)

**Milestone gate and status:** [notes/ROADMAP.md](notes/ROADMAP.md)
