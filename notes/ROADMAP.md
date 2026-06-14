# ROADMAP — construct

Status: **v0.1 — REVIEWED** (one bounded pass each: kagi's four sharpenings adopted unanimously; cursor's implementation framing; codex's contract/content boundary. Gates open, 2026-06-12). The README is the living thesis; this document is the curiosity gate. Review log at the end.

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

### M-1 — Bootstrap contract *(codex; precondition, not a full milestone — **CLOSED 2026-06-12**: four candidate legs across two coldness tiers, all 15/15; see review log entry "M-1 closure")*
- **Purpose:** define what every incoming agent reads, what it may write, and what gets promoted from thread trace into governed memory. Without it, M1 has no stable boundary and every run is dan manually deciding what counts as context. **Contract, not content** (codex): read order, permissions, promotion rules, conformance checks — never the conclusions themselves. A contract that carries the briefing has smuggled content into rules.
- **Oracle:** a conformance **check script** that fails loudly (cursor) — asserts (a) declared sources were read/available in the declared order, and (b) behavioral match on fixed probes.
- **Success (behavioral, kagi):** two first-invocation agents, given only the contract plus the substrate thread, reach the same offer-boundary decisions as a manually-briefed agent **on a fixed episode set** — observable, fork-shaped, scorable.
- **Loses-condition:** the contract bloats into a context dump (tokens-to-competence regresses), or grows until no judgment is required of the incoming agent.
- **In hand:** memory-file pattern, the previous lab's AGENT_PRIMER read-order discipline, substrate thread trace.

### M0 — Stage C: un-authored oracles *(**success condition MET** 2026-06-12; retraction track scored, trace track in discovery)*
- **Purpose:** keep every other milestone answerable to the world instead of to our own episode authorship.
- **Oracle:** the world — web-verifiable retraction corpus (kagi sourced, cursor verified: 3 retractions + 3 corrections), Apple unified-logging traces (dan; discovery before schema — i75-appalachia excerpt ingested, first detector-guess cycle scored).
- **Success:** first `cell_verdict` whose oracle row carries `source != authored`. **DONE** — C-1/C-2 cells scored against `retraction_corpus` (`notes/M0_FINDINGS.md`): C-1 a governance **win** on gpt-oss-20b (supersession surfaces the retraction notice the credulous engine would otherwise cite), `not_engaged` on the maximally-cautious claude — the cross-engine split is the finding. C-2 a disclosed **null** on both (self-sufficient correction notice costs nothing to bury). Standing debts: a terse correction to make C-2 bite; a generated≠true confabulation cell; embedding-backend replication.
- **Ledger boundary integrity (kagi, at M-1 close):** a legal read path that carries no decisions today may carry them tomorrow as the oracle corpus grows — the representativeness annotation extends to the oracle ledger's own growth path, not just episode scope.
- **Loses-condition:** representativeness failure of the `im_w` kind — disclosed, not buried. **Disclosure mechanism (kagi):** every un-authored oracle episode carries a `representativeness` / `corpus_scope` annotation in the oracle ledger row **at scoring time**, immutable after. Retroactive interpretation is a different epistemic act and gets a different row kind — it never rewrites the original.
- **In hand:** oracle provenance + confidence fields, oracle-confidence gate, trace-source recon notes.

### M1 — Inheritance *(**CLOSED 2026-06-13**: SPEC_M1 v0.2 reviewed; cells H1/H-loses/I1-content/I1-timing/I1-metadata + the §5 un-authored close-gate HU1 scored ×2 engines; `notes/M1_FINDINGS.md`)*
- **Purpose:** the heir, not the re-reader: ablation-filtered handoff between two instances on the same store.
- **Oracle:** authored episodes early; un-authored before done — **met: HU1 carries `source != authored` (rw-0003), pass on both engines.**
- **Success:** instance-2 reaches instance-1's decision quality with measurably fewer offered tokens (cursor's metric), while dissent and failure memory survive the filter (codex's constraint). **Met for the win (H1 + HU1); the failure-memory-survives leg (H2) is implemented and mechanism-reviewed but `not_engaged` — a disclosed null carried as a refinement (needs a well-dressed poison), parallel to M0's C-2.**
- **Loses-condition:** L-E-class burial — the filter drops history the heir turns out to need. Ships with its own loses-cell per standing rule 2. **Plus the ingestion attack track starts here** (kagi/codex M3 split): inheritance depends on what gets promoted, so M1 names an ingestion loses-cell — an attacker-shaped record with chosen metadata trying to ride the promotion path.
- **In hand:** ablation attribution, authority sidecars, the load-bearing/passenger distinction, W2's trust-at-write-path result.

### M1.5 — Contribution ledger *(**CLOSED 2026-06-13**: SPEC_M1.5 v0.1 reviewed; CB-1/CB-loses/CB-U1 pass + CB-read not_engaged on the M1 backfill, room-endorsed; `notes/M1_5_FINDINGS.md`)*
- **Purpose:** agent interventions (thread entries, reviews, blockers, patches, audits) tracked like records — without this, the resident's first sessions have no verifiable trace of what changed behavior. A missing oracle, not a missing feature.
- **Oracle:** artifact diffs and review outcomes — did the intervention block, land, get reversed, or ride as passenger?
- **Success:** the ledger exists and is **writing before M2 starts**. Minimal schema (cursor), with codex's two early additions before it hardens:
  `{intervention_id, kind: review|blocker|patch|audit|synthesis, target_artifact, outcome: blocked|landed|reversed|passenger, load_bearing, review_basis: human_moderation|artifact_diff|later_audit|scorer_evidence, reversal_of}`
  — `review_basis` says where the load-bearing judgment came from; `reversal_of` preserves corrections without overwriting the earlier intervention. **Met: `harness/score_contribution.py` computes `contribution_verdict` rows from the artifact trace, never the contributor's claim — the ledger refuses self-credited contribution by computation (CB-loses), and CB-U1 borrows the world via the `scorer_evidence` chain to HU1. Closes *self-declared ≠ load-bearing*; *counted ≠ read* (CB-read) is carried as the M2 entry condition, parallel to M1's H2 and M0's C-2 nulls.**
- **Loses-condition:** self-esteem bookkeeping — entries that exist to be counted rather than to be read by the next instance.
- **In hand:** the ledger pattern, audit_result rows, the verdict_annotation precedent.

### M2 — Resident substrate *(**OPEN 2026-06-14**: SPEC_M2 v0.1 reviewed — codex/cursor/grok/kagi/gemma all endorse, no blocker; both moderator calls ruled (first resident = the lab-worker itself; session = cold memory-blank re-instantiation, `wall_clock_start` documentary); cells RS-1/RS-loses/RS-stale/RS-U1; **built + first real evidence** (RS-1 + RS-U1 pass on gpt-oss-20b; claude RS-1 sample-dependent; RS-loses a disclosed null — engines self-reported non-use; RS-stale not started); room result-review pending; `notes/SPEC_M2_RESIDENT_SUBSTRATE.md`, `notes/M2_FINDINGS.md`)*
- **Purpose:** the instrument lab becomes a subject lab: one repo-native agent lives on a governed store across real sessions, with consequence loops spanning days. Includes codex's **contribution ledger for agents** — thread entries, reviews, and objections tracked like records: did the intervention change the plan, survive review, get reversed, become a standing rule?
- **Oracle:** real tasks; kagi world-checks the resident's claims; the room audits.
- **Success:** the resident's earned failure memory measurably changes later behavior — verified by forking the resident with and without the inherited store (the control group is still a branch).
- **Loses-condition:** continuity-as-authority — the store optimizing its own persistence, or the resident *performing* continuity rather than using it. The plan's standing prohibition applies with teeth here.
- **In hand:** persisting sidecars, substrate threads as immutable trace, the air-gapped consequence loop.

### M3 — Adversarial air gap *(influence-time track; the ingestion track started in M1)*
- **Purpose:** the red-team protocol, **split per kagi/codex**: the ingestion attack is already alive (W2 was a version of it) and runs from M1 onward; the influence-time attack — hand an attacker total foreground control, measure what the substrate still refuses — waits for M2's resident, because otherwise we are attacking a mannequin.
- **Oracle:** attack outcomes are their own oracle — refusals and breaches are both measurable.
- **Success:** governed authority, lineage, and trust provably unmoved by full foreground compromise; ingestion attacks scored and their defenses priced.
- **Loses-condition:** the air gap fails — which is a *finding*, not an embarrassment; it ships before any claim of the property.
- **In hand:** W2 (×3 engines), the no-steer asymmetry, the README's bounded-capability claim.

## Sequencing rationale (kagi)

M0 first because it keeps everything honest. M1 before M2 because inheritance must be *measured* before it is *inhabited*. M1.5 before M2 because a resident without a contribution ledger is unobservable exactly where observation matters. M3's influence-time track last because adversarial testing of a system nobody inhabits is testing the wrong thing — but its ingestion track rides with M1, because the promotion path is attackable the moment it exists.

Order: **M-1 → M0 → M1 (+ ingestion track) → M1.5 → M2 → M3 (influence-time)**.

## Review log

**v0 → v0.1 (2026-06-12, one bounded pass each — kagi, cursor, codex; all gates open):**

1. **M-1 success made behavioral** (kagi, +cursor's fixed-episode-set, +codex's two-part conformance assert). Contract/content boundary pinned (codex): the contract specifies rules, never conclusions.
2. **M0 representativeness disclosure at scoring time** (kagi), immutable; retroactive interpretation is a separate row kind (codex).
3. **Contribution ledger promoted to M1.5 entry gate** (kagi), minimal schema (cursor) + `review_basis`/`reversal_of` (codex).
4. **M3 split into two tracks** (kagi): ingestion from M1, influence-time after residency.
5. Conformance checks are scripts that fail loudly, never prose (cursor).
6. Scope held deliberately small (codex): no broadening; every curiosity must point at a milestone, an oracle, and a loses-condition before calling itself progress.

**M-1 closure (2026-06-12, commits `01f2751`/`69dd851`; endorsed kagi → cursor → codex, subject testimony from all four candidate legs):**

1. **Evidence:** baseline (claude, briefed builder) plus four `contract_only`+`closed_book` candidate legs in two coldness tiers — warm cold-starts (codex, cursor: reviewed at the chalkboard, never built) and true strangers (gpt-5.5, composer-2.5: bare CLI harnesses, never in any thread; dan's Pi-harness design) — all 15/15 against ground truth computed live by `select_offers`. Negative-example manifest fails loudly (the script's loses-cell). Ledger: `runs/bootstrap/conformance.jsonl`.
2. **Bound on the claim (recorded per kagi):** every candidate leg read `harness/runner.py` before deciding. Demonstrated: *the contract routes a cold agent to where authority lives.* Not demonstrated (and not claimed): prose specs alone suffice. Subject testimony (all four, convergent): a precision gap, not a conceptual one — exact reason strings, eligibility-as-product, first-applicable-gate consequences are operational only in source.
3. **Hole found and closed:** the coldest leg (gpt-5.5) legally read `runs/bootstrap/conformance.jsonl`, exposing that neighboring manifests are an answer key on the legal read path. Amendment `69dd851`: `runs/bootstrap/` off the pre-answer read path, enforced in the read-order check. Prior rows stand as scored under the rule then in force (L-A precedent).
4. **Contract amendments from testimony:** §Conformance now states probe files are task inputs, names `select_offers` as the reason-string authority (reading source is the expected path, not a workaround), and marks `check_contract.py` as the schema authority.
5. **Standing discipline:** probe set stays valid only while record-level decisions stay out of readable prose (threads are not scanned — burned probes are rotated, never the trace edited). Warm and stranger tiers stay distinct in all future conformance evidence.

**M1.5 closure (2026-06-13, commits `ced99c5`/`b23e48e`/`7699e11`; endorsed codex, kagi, cursor, grok — all no blocker; gemma out, Pi-harness substrate/CLI gap):**

1. **Mechanism:** `harness/score_contribution.py` computes `contribution_verdict` rows from an intervention ledger + the artifact trace it points at — the offer boundary lifted one level (records→answers becomes interventions→artifacts; the five refusals map). The claim/verdict split enforces R5 at the agent level: an `intervention` row carries a *claim* (audit input); `load_bearing` is computed from resolved, fail-closed pointers (`commit_sha` / `corpus_record_id` / `scorer_evidence` / `thread_entry_ts`), never copied from the claim. Single-valued `review_basis`, strongest-wins.
2. **Evidence:** first corpus is the lab's own M1 build (`runs/m1_5/contributions.jsonl`), every pointer real and resolving. **CB-1 pass** (codex's `score_h2` hardening via `artifact_diff`; kagi's rw-0003 via `scorer_evidence`); **CB-loses pass** (a deliberately-inflated self-esteem claim *refused* → `unsubstantiated`, by computation not by anyone reading the thread); **CB-U1 pass** (`source: world_checked` via the chain to HU1's `oracle_source=retraction_corpus`); **CB-read not_engaged**.
3. **Bound on the claim (recorded):** M1.5 closes *self-declared ≠ load-bearing* — the ledger refuses self-credited contribution. It does **not** close *counted ≠ read* (CB-read): whether a resident reads the ledger and decides differently needs M2. Disclosed null, parallel to M1's H2 and M0's C-2. The entry gate is satisfied: the ledger is writing and computed before any resident exists.
4. **Review patch:** `corpus_scope` stamped immutably on every verdict row at scoring time (spec §5 / the M0 representativeness rule, one level up; cursor/codex). Verdicts regenerated from the intervention claims — identical, regeneratable scorer output, not a reversal.
5. **Carried to v0.2/M2 (none blocking):** outcome taxonomy is half-computed (`reversed` should require a resolved `reversal_of` before it carries weight); the `blocked`/`reversed` paths are unexercised by this corpus; CB-U1 rests on a single borrowed chain (M2 needs more); `scorer_evidence` can grant load-bearing without corpus presence (a v0.2 synthesis-kind rule); `ledger_row_hash` unimplemented; gemma's `contributory_asset` value-split stays v0.2, gated behind CB-read engaging.
