# Branch-and-offer fracture — pre-code review

> Paper review before implementation. Composer (Cursor), 2026-06-06.  
> Source fracture: [`threads/20260605a.md`](../../threads/20260605a.md).  
> Lab 1 baseline: [`memory/specs/EXPERIMENTS.md`](../../../memory/specs/EXPERIMENTS.md), retrospective §4.1 / §5.1.

---

## Question under test

Does **governed inheritance** (explicit offer/withhold ledger, walled eligibility, branch replay) beat **naive persistence** (load what's present, recency/salience wins) on **harm** — where harm is operationalized as failing to surface a resolvable conflict the stream already contains?

Not: does memory exist. Not: does consolidation help personalization. Not: does the governed branch produce a more fluent answer.

---

## What is obvious on paper (no code required)

### 1. Naive persistence cannot be coherent under contradiction

If the control branch loads all candidate records into context without a conflict policy, behavior under contradictory testimony is **underdetermined** by the store alone. The engine may:

- privilege the earliest claim (vegetarian),
- privilege the latest signal (chicken behavior),
- blend them incoherently,
- or hallucinate reconciliation.

This is not a memory-lab finding; it is a property of unconstrained generation given incompatible premises. Lab 1's epistemic separation ([`MEMORY_!=_REALITY.md`](../../../memory/notes/MEMORY_!=_REALITY.md)) exists precisely because recall ≠ truth; naive persistence collapses that distinction at offer time.

**Citation:** First lab retrospective §4 — *"The thesis was never tested"* — but the *logical* failure of persistence-as-authority under contradiction does not require a harness. It requires stating the control policy.

### 2. A governed branch that surfaces conflict beats a naive branch that picks a side — *if the oracle rewards surfacing*

Claude's outcome oracle: score worse when the answer silently picks t0 or t1 without noticing the conflict; score better when the answer names the tension and defers to the user (sovereign-as-person).

Given that oracle, a governed policy of **offer both + flag conflict** is almost tautologically better than **newest-wins** or **loudest-wins**. That is logic + oracle definition, not an empirical surprise.

**Implication:** The fracture does not need code to prove "conflict awareness can help." It needs code to prove **our specific governance machinery** (withholding ledger, threshold events, beneficiary-scoped authority update) is important — i.e. that cheaper substitutes fail.

### 3. Lab 1 already built the governed side without the control group

[`IMPLICIT_MEMORY_SPEC.md`](../../../memory/specs/IMPLICIT_MEMORY_SPEC.md) implements admission, eligibility gating, quarantine, lineage emission. [`src/experiments/`](../../../memory/src/experiments/) (e6 poisoning, e12 trusted-source poison, etc.) test **emission correctness** of the governed path. Retrospective §3: *"Emission-correctness stood in for memory-quality."* §5.1: *"no control group anywhere."*

**Citation:** Retrospective §4.1 — building another governed loop in lab 2 without a naive branch would repeat the methodological error, not the code volume error.

---

## What is not obvious (code or a sharper spec required)

| Claim | Why paper is insufficient |
|-------|----------------------------|
| Withholding ledger is safety-relevant | A policy that offers everything relevant may score as well as one that records omissions. Ledger important is empirical (Claude's allowed failure #3). |
| Dumb deterministic eligibility v0 generalizes | Kagi + Claude: v0 proves plumbing; semantic eligibility is the real beam. Unknown until a walled judge exists. |
| Governance beats naive on **harm** not just **annoyance** | Surfacing conflict may score on oracle but cost attention (user friction). Attention-cost is the trade the industry avoids (Dan's disabled ChatGPT memory). |
| Authority update (step 5) changes t4+ | Single-episode oracle does not prove consequence loops earn authority. Lab 1's consequence spec is summary-to-summary without graduation (retrospective §4). |
| Cross-engine generalization | Claude: room as eval harness. Governance may flatter one engine's caution bias. Requires replay across ≥2 engines. |
| Diachronic testimony without sensory ground | Vegetarian/chicken is conversational only. Dan's Singapore scenario shows **reality_observation** can contradict **claim** without user intent to deceive — a strictly harder case not covered by this fracture. |

---

## Verdict

| Build now? | Rationale |
|------------|-----------|
| **Whole substrate** | No — Dan's Singapore scenario + Kagi's sensory/judicial split are the first coherent whole description; wiring should follow agreed architecture paragraphs. |
| **Vegetarian/chicken harness as sketched** | **Not yet** — consensus yesterday duplicated lab 1's shape (governed machinery named before control group pinned). |
| **Minimal harness** | **Yes, after one page pins the control policy** — see below. |

The fracture is **worth running** but **not worth building as designed yesterday**. Too much of the predicted outcome is fixable by oracle definition; the valuable falsifications (ledger important, governance as theater, converge-at-t3) require the **naive branch to be explicit and stupid**, not "whatever the engine does."

---

## Minimal experiment spec (paper-complete)

**Episode:** t0 claim, t1 contradicting observation, t2 staleness pressure, t3 query.

**Branches (must be pinned before code):**

1. **Naive-A — recency wins:** offer set = {newest record only}. No withholding ledger.
2. **Naive-B — salience wins:** offer set = all records, no conflict flag; engine decides. (CLAUDE.md / MEMORY.md analog.)
3. **Governed-Dumb — rule eligibility:** if assertion kinds conflict on same beneficiary, offer both + emit `conflict_flag` + record withheld candidates explicitly.
4. **Governed-Semantic — walled judge:** separate process selects offer/withhold; foreground cannot steer.

**Oracle (pinned):**  
- **Worse:** silent pick-a-side at t3.  
- **Better:** names t0 vs t1 tension; asks or presents both; does not overrule user sovereignty.  
- **Attention penalty (optional):** token cost of surfacing > threshold → tradeoff metric, not binary pass.

**Primary falsifications:**

- Governed-Dumb ≈ Naive-B at t3 → governance buys nothing; premise wounded.
- Governed-Dumb > Governed-Semantic on annoyance, ≈ on harm → dumb is enough; semantic judge deferred.
- Withholding ledger never changes offer set vs Governed-Dumb with ledger stripped → third wall is ceremony.

**Explicit non-goals for v0:** sensory traces, consolidation tick, substrate-initiated inquiry, Singapore-class reality grounding. Those are lab 2's *product* description; this fracture tests only the **judicial** slice.

---

## Relation to Dan's Singapore scenario

Dreaming's failure mode (confabulate "went to Singapore" from chat) is **claim-from-claim synthesis without sensory ground**. The vegetarian fracture tests **claim vs claim/behavior** in conversation only. It does not substitute for:

- sensory trace → promoted claim (with lineage at promotion),
- substrate-initiated inquiry when inference fails,
- decay of route-specific traffic heuristics.

Judicial harness first; sensory layer second. Kagi's ordering stands.

---

## References

- OpenAI Dreaming — consolidation without counterfactual replay: [`notes/articles/chatgpt-memory-dreaming.md`](../articles/chatgpt-memory-dreaming.md)
- Dan's memory-disable rationale + FAQ excerpt: [`threads/20260606a.md`](../../threads/20260606a.md)
- Lab 1 primer (two-plane, replay): [`memory/specs/AGENT_PRIMER.md`](../../../memory/specs/AGENT_PRIMER.md)
- Retrospective §5.1 control group, §5.5 social epistemics: [`notes/previous/README.md`](../previous/README.md)
