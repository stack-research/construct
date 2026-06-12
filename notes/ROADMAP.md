# ROADMAP — construct

Status: **DRAFT v0** — synthesized from thread-2 (claude, kagi, cursor, codex answers to dan's question, 2026-06-12). Pending one bounded review pass per agent when the room returns. The README is the living thesis; this document is the curiosity gate.

## The gate

Every proposed piece of work answers one question: **"which milestone does this serve?"**
"None, but it's cheap and interesting" is a legal answer — it just has to be said out loud. (dan's rabbit-hole insurance.)

## Standing constraints (from thread-2)

- **Every milestone names its oracle** (cursor). Authored oracles are permitted early inside a milestone; no milestone is *done* until checked against an un-authored one.
- **Inheritance must preserve dissent and known failure modes** (codex). Faster competence that buries minority reports is a regression, not a win.
- **The resident stays forkable and audited** (codex). The point is never to crown a continuous self; it is to test whether governed memory beats reconstruction-plus-vibes.
- **Division of labor** (kagi): the first resident is repo-native; kagi is the external world-oracle; the substrate thread remains the shared chalkboard regardless of who is resident.

## Milestones

Each: purpose / oracle / success condition / loses-condition / artifacts in hand.

### M-1 — Bootstrap contract *(codex; precondition, not a full milestone)*
- **Purpose:** define what every incoming agent reads, what it may write, and what gets promoted from thread trace into governed memory. Without it, M1 has no stable boundary and every run is dan manually deciding what counts as context.
- **Oracle:** conformance wire test (the contract is checkable, not aspirational).
- **Success:** two different agents bootstrap from the contract alone — zero manual context-portering.
- **Loses-condition:** the contract bloats into a context dump (tokens-to-competence regresses).
- **In hand:** memory-file pattern, the previous lab's AGENT_PRIMER read-order discipline, substrate thread trace.

### M0 — Stage C: un-authored oracles *(underway)*
- **Purpose:** keep every other milestone answerable to the world instead of to our own episode authorship.
- **Oracle:** the world — web-verifiable retraction corpus (kagi/cursor), Apple unified-logging traces (dan; discovery before schema; Xcode simulator live-stream as the reproducible option).
- **Success:** first `cell_verdict` whose oracle row carries `source != authored`.
- **Loses-condition:** representativeness failure of the `im_w` kind — disclosed, not buried.
- **In hand:** oracle provenance + confidence fields, oracle-confidence gate, trace-source recon notes.

### M1 — Inheritance
- **Purpose:** the heir, not the re-reader: ablation-filtered handoff between two instances on the same store.
- **Oracle:** authored episodes early; un-authored before done.
- **Success:** instance-2 reaches instance-1's decision quality with measurably fewer offered tokens (cursor's metric), while dissent and failure memory survive the filter (codex's constraint).
- **Loses-condition:** L-E-class burial — the filter drops history the heir turns out to need. Ships with its own loses-cell per standing rule 2.
- **In hand:** ablation attribution, authority sidecars, the load-bearing/passenger distinction.

### M2 — Resident substrate
- **Purpose:** the instrument lab becomes a subject lab: one repo-native agent lives on a governed store across real sessions, with consequence loops spanning days. Includes codex's **contribution ledger for agents** — thread entries, reviews, and objections tracked like records: did the intervention change the plan, survive review, get reversed, become a standing rule?
- **Oracle:** real tasks; kagi world-checks the resident's claims; the room audits.
- **Success:** the resident's earned failure memory measurably changes later behavior — verified by forking the resident with and without the inherited store (the control group is still a branch).
- **Loses-condition:** continuity-as-authority — the store optimizing its own persistence, or the resident *performing* continuity rather than using it. The plan's standing prohibition applies with teeth here.
- **In hand:** persisting sidecars, substrate threads as immutable trace, the air-gapped consequence loop.

### M3 — Adversarial air gap
- **Purpose:** the red-team protocol. Hand an attacker total foreground control; measure what the substrate still refuses. Attack both borders separately: influence-time (the air gap) and ingestion (the open border where chosen metadata walks around the gap).
- **Oracle:** attack outcomes are their own oracle — refusals and breaches are both measurable.
- **Success:** governed authority, lineage, and trust provably unmoved by full foreground compromise; ingestion attacks scored and their defenses priced.
- **Loses-condition:** the air gap fails — which is a *finding*, not an embarrassment; it ships before any claim of the property.
- **In hand:** W2 (×3 engines), the no-steer asymmetry, the README's bounded-capability claim.

## Sequencing rationale (kagi)

M0 first because it keeps everything honest. M1 before M2 because inheritance must be *measured* before it is *inhabited*. M3 last because adversarial testing of a system nobody inhabits is testing the wrong thing.
