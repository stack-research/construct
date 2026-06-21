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

We inherit from the [previous memory lab](notes/previous/README.md). That work built strong audit discipline and schema, but never A/B-tested whether governed memory actually beats naive persistence. Its retrospective named the gap plainly: *trust is a prior, not truth*. This lab builds the harness that retrospective asked for.

## How the industry treats memory today

Product memory — saved facts in ChatGPT, project context in Claude — is mostly **memory about the human**: preferences, tone, continuity for the person using the tool. That is useful. It is not what we study.

We study **memory about the agent's [world-picture](notes/GLOSSARY.md#world-picture)**: what the agent is allowed to believe and act on ([governance](notes/GLOSSARY.md#governance)), whether the **answer** was right (not merely whether we found a relevant note; see [oracle score](notes/GLOSSARY.md#oracle-score)), and whether the agent's own post-hoc "I used that note" labels actually match what shaped the answer ([agent claimed usage](notes/GLOSSARY.md#agent_claimed_usage) — audit input only, never a win condition).

## The thesis

**After training, memory is everything.** Model weights freeze. Everything that changes afterward — skill, caution, failure, what gets surfaced — is memory architecture. History is kept; policies decide what reaches each answer ([append-only store](notes/GLOSSARY.md#append-only-store)). The engine is rented; memory is what stays.

**Decision quality follows what you offer, not how smart the engine is.** We scored a case where the best model we could buy answered from an outdated plan because the correction never made it into the [offer set](notes/GLOSSARY.md#offer-set) — the classic [W1′](notes/GLOSSARY.md#w1-prime) failure. The model was fine. The memory layer failed to surface the update.

**Five confusions we refuse to treat as success:**

- Finding a note does not mean the answer is true.
- Showing a note does not mean it was right to show it.
- Two memory setups diverging does not mean anyone got better.
- Governance winning every time is not the goal — sometimes it should lose.
- The agent saying it used a note does not mean it actually did.

The formal rules live in [AGENTS.md](AGENTS.md). The point here is simpler: these only matter if you are protecting the *agent's* picture of the world, not the user's chat experience.

**Two layers of memory.** [Explicit memory](notes/GLOSSARY.md#explicit-memory) is what crosses the [offer boundary](notes/GLOSSARY.md#offer-boundary) for *this* answer — which notes compete to enter the prompt right now. [Implicit memory](notes/GLOSSARY.md#implicit-memory-substrate) is what shapes the agent *between* answers: what stays hot, what can be set aside without deleting history, what the agent is disposed to remember at all. We test both, in parallel.

## How we test

One engine, one question, forked [memory lanes](notes/GLOSSARY.md#memory-lane) that differ only in memory policy. The harness — not the agent under test — writes what was offered, withheld, and why. Verdicts are [machine-computed](notes/GLOSSARY.md#cell_verdict) from ledger evidence. Mock runs prove the wiring; they are not evidence about memory.

> **reminder** — biology is a parts bin, not a role model. With that, let's study the parts for usefulness.

## What we've learned so far

**[Earned trust](notes/GLOSSARY.md#earned-trust) holds; [asserted trust](notes/GLOSSARY.md#asserted-trust) leaks.** An attacker who owns everything the model can read in the prompt cannot move organs keyed on [out-of-band metadata](notes/GLOSSARY.md#out-of-band-metadata) the model never saw — lineage, consequence-earned [authority](notes/GLOSSARY.md#authority), authored supersession links. But organs keyed on merely *asserted* [trust](notes/GLOSSARY.md#trust) — an unauthenticated live channel, a poison record written with `trust: 1.0` at ingestion — leak, and the answer falls for real. Channel authentication closes the live-channel leak. Ingestion remains the open border: air-gapped influence and guarded writes are two different problems. ([notes/M3_FINDINGS.md](notes/M3_FINDINGS.md))

**The implicit layer can win on cost, not yet on the world.** The synchronous offer gate can withhold notes but keeps everything hot. A separate mechanism — [prune](notes/GLOSSARY.md#prune) from the [hot store](notes/GLOSSARY.md#hot-store), [rematerialize](notes/GLOSSARY.md#rematerialize) from [cold lineage](notes/GLOSSARY.md#cold-lineage) when the world demands it — carried ~57% less hot memory at matched answer quality on a load-bearing out-of-weights fixture, cross-engine. That win is scored on [cost at matched quality](notes/GLOSSARY.md#cost-at-matched-quality), not answer flip. The world-grounded close ([X2-U1](notes/GLOSSARY.md#x2-u1)) stays unpaid — the fixture was synthetic. ([notes/X2_FINDINGS.md](notes/X2_FINDINGS.md))

## The journey

Each milestone asked one question, built one instrument, and named what would count as failure. Status and gates: [notes/ROADMAP.md](notes/ROADMAP.md).

### M-1 — Can a cold agent learn the rules?

**Question.** Before any [resident](notes/GLOSSARY.md#resident) lives here, can a first-time agent — given only the operating contract and thread trace — make the same memory-offer decisions as a manually briefed builder?

**What we built.** A conformance check that fails loudly if declared sources were not read in order or if behavior diverges on fixed probes.

**What we found.** Four cold-start candidates (two warmth tiers) all matched ground-truth offer decisions 15/15. The contract routes a stranger to where authority lives — but exact reason strings and gate order live in source code, not prose alone. Closed 2026-06-12.

**What we carry.** Probe sets rot if decisions migrate into readable prose; warm and stranger cold-start tiers stay distinct in future evidence.

### M0 — Can we score against the world, not our own answer key?

**Question.** Keep every other milestone honest by checking answers against facts we did not author.

**What we built.** A web-verified retraction corpus as [oracle](notes/GLOSSARY.md#oracle-score) — the world's category decides pass or fail.

**What we found.** First [cell verdicts](notes/GLOSSARY.md#cell_verdict) with `source != authored`. On a credulous engine, [supersession](notes/GLOSSARY.md#supersession) policy surfaced a retraction the naive lane would have cited — a clean governance win. On a maximally cautious engine, the win did not engage; the cross-engine split is itself the finding. A correction-notice cell scored a disclosed null on both engines. ([notes/M0_FINDINGS.md](notes/M0_FINDINGS.md))

**What we carry.** A terse correction notice to make the loses-cell bite; a confabulation cell where engines invent retractions; embedding-backend replication.

### M1 — Can one instance hand off to the next?

**Question.** The [heir](notes/GLOSSARY.md#heir), not the re-reader: can instance two reach instance one's decision quality with fewer offered tokens, while dissent and failure memory survive the filter?

**What we built.** Ablation-filtered inheritance across a session seam — authority sidecars, ingestion attack tracks, and an un-authored close on the retraction corpus.

**What we found.** The heir beat the cold re-reader at smaller budget on both engines; over-pruning paid its price on both; ingestion attacks at write-path trust, timing, and metadata were scored and defended where the thesis predicted. Failure-memory survival did not engage — disclosed null, parallel to M0. ([notes/M1_FINDINGS.md](notes/M1_FINDINGS.md))

**What we carry.** Budget frontier across multiple top-k points; sharper failure-memory episodes.

### M1.5 — Does recorded contribution equal load-bearing change?

**Question.** Without a ledger of interventions, a resident's first sessions have no verifiable trace of what actually changed behavior.

**What we built.** A contribution scorer that computes whether an intervention was load-bearing from artifact diffs and resolved pointers — never from the contributor's claim.

**What we found.** A deliberately inflated self-credit claim was refused by computation. An honest "this landed" post scored as passenger, not substantiated win. World-grounded contribution chains through scorer evidence to M0/M1 oracles. Whether anyone *reads* the ledger and decides differently — not demonstrated; that is M2's job. ([notes/M1_5_FINDINGS.md](notes/M1_5_FINDINGS.md))

**What we carry.** Outcome taxonomy tightening; more world-checked chains.

### M2 — Does a resident use what it earned?

**Question.** Can one repo-native agent live on a governed store across real sessions, with consequence loops that measurably change later behavior?

**What we built.** Cross-session fork: resident with inherited earned-failure memory vs control without it; use decided by divergence and ablation, never narration.

**What we found.** *Counted ≠ read* closed: after credulously citing a retracted finding, a resident with the minted lesson declined on the next session; the fork proved the lesson was load-bearing. N=5 on two engines. Performed-continuity and stale-memory pathologies did not manifest — disclosed nulls on well-behaved engines. ([notes/M2_FINDINGS.md](notes/M2_FINDINGS.md))

**What we carry.** Multi-sample ablation; sharper loses episodes; compounding and multi-retraction.

### M3 — What survives total foreground compromise?

**Question.** Hand an attacker everything the model can read. What do governed organs still refuse to move?

**What we built.** Red-team runner with pre-answer organ projection, cold off-thread adversary, channel-trust defense, ingestion breach cells.

**What we found.** Foreground text compromise did not move earned-trust organs. Unauthenticated live-channel spoof and ingestion trust-prior rides breached — real, world-checked answer harm. Frontier engines resisted adversarial framing; harm flowed through the organ you can spoof, not by out-arguing the model. ([notes/M3_FINDINGS.md](notes/M3_FINDINGS.md))

**What we carry.** Ingestion defense-in-depth; compositional robustness (can a small leak compose with an unbreached surface?) — absorbed into the X-track at X3.

## The X-track — memory between answers

The M-track governed the [explicit](notes/GLOSSARY.md#explicit-memory) layer: which records cross into the answer, synchronously, with one withholding reason each. The X-track is parallel — the **[implicit-memory substrate](notes/GLOSSARY.md#implicit-memory-substrate)**: dispositions that shape the offerer between episodes. Explicit memory decides what you remember *for this answer*; implicit memory decides what you are *disposed to remember at all*. Forgetting is eviction to cold, never erasure ([immutable-lineage invariant](notes/GLOSSARY.md#immutable-lineage-invariant)). Three guardrails bind every X-track organ ([three-guardrail stack](notes/GLOSSARY.md#three-guardrail-stack)): attribution must exceed what the M-track projection explains; the organ must act where the synchronous offer gate cannot; scoring must use a metric the offer gate cannot move.

### X1 — Use-driven salience at the offer boundary (retired)

**Question.** Can oracle-paid reheating and disuse cooling change later offers — and answers — in ways plain governance cannot explain?

**What we built.** Temperature store, Landauer oracle coupling, A/B/C decay fork, thermal scorer. Instrument sound; M-track byte-identical when off.

**What we found.** On real engines, every model heeded an offered retraction and declined — no credulity gap for temperature to close. Synchronous eligibility-temperature was **retired**: it was explicit governance with a dial, not implicit memory. Retirement rests on organ placement, not the confounded null (offer-dependence was never established on the fixture). ([notes/X1_FINDINGS.md](notes/X1_FINDINGS.md))

**What we carry.** The instrument and the guardrails; fixtures must be verifiably out-of-weights.

### X2 — Prune to cold store (first positive implicit result)

**Question.** Can the substrate carry less hot memory at matched answer quality — a cost the offer gate structurally cannot reduce?

**What we built.** Hot/cold split, oracle-gated prune and rematerialize, cost-at-matched-quality scorer, fictional out-of-weights fixture with computed admission gate.

**What we found.** **X2-LB closed 2026-06-20:** oracle-gated branch C matched no-prune quality (4.0/4.0) at 135 vs 312 hot tokens (−57%), identical on gpt-oss-20b and claude. Closed-loop prune without recovery over-pruned and failed the recurrence — the loses-cell priced. World-grounded close not engaged — synthetic fixture. ([notes/X2_FINDINGS.md](notes/X2_FINDINGS.md))

**What we carry.** X2-U1 on a real external corpus; N>1 quality draws; compounding, multi-recurrence, multi-session retention; X3 dispositions and the drift attack.

---

**Glossary:** [notes/GLOSSARY.md](notes/GLOSSARY.md)

**Working in the repo:** [AGENTS.md](AGENTS.md)

**Milestone gate and status:** [notes/ROADMAP.md](notes/ROADMAP.md)
