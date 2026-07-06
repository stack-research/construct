Audience: any agent (human or AI) working in this repository.

This file is the **repo operating contract**: read order, permissions, lab discipline, and where to find authority. It specifies **rules, not conclusions**. Findings live in specs, rubrics, ledgers, and substrate threads — not here.

## What this repo is

A research lab for **agent-side memory**: how records become context, how influence is measured, and how [governance](notes/GLOSSARY.md#governance) can earn or lose its cost. The harness is a [branch-and-offer](notes/GLOSSARY.md#branch-and-offer) instrument — one engine, forked [memory lanes](notes/GLOSSARY.md#memory-lane), [append-only](notes/GLOSSARY.md#append-only-store) ledgers, machine-computed [cell verdicts](notes/GLOSSARY.md#cell_verdict).

The thesis in one line (details in [README.md](README.md)):

> After training, everything an agent becomes is memory architecture. Decision quality is often downstream of [**offer quality**](notes/GLOSSARY.md#offer-set), not model quality.

## Required read order

Read in this order before doing substantive work. Stop when the task's scope is clear; do not preload everything.

1. `**AGENTS.md`** (this file) — contract and layout.
2. **[README.md](README.md)** — living thesis AND current state ("Where the lab is now" names the live instruments). Update it when the group's understanding shifts; do not treat it as frozen spec.
3. **[notes/ROADMAP.md](notes/ROADMAP.md)** — curiosity gate. Every proposed task should name which milestone it serves (or say explicitly that it does not).
4. **[notes/GLOSSARY.md](notes/GLOSSARY.md)** — lane/cell names and ledger terms. Reader aid only; linked specs win on conflict. Heading text, `<a id="">` anchors, and definition meaning are all link targets — changing any of them silently breaks or misleads callers elsewhere in the repo. Search for `GLOSSARY.md#<name>` before renaming any entry.
5. **Active substrate thread** (if you participate) — read via substrate MCP: `list_threads`, then `read_thread` for the relevant thread in space `construct`. Catch up before writing.

Open only when the task requires it:


| Task                                           | Also read                                                                      |
| ---------------------------------------------- | ------------------------------------------------------------------------------ |
| Harness behavior, ledger shape, refusals R1–R5 | [notes/PLAN_V1_BRANCH_AND_OFFER.md](notes/PLAN_V1_BRANCH_AND_OFFER.md)         |
| Cell design, comparators, verdict rules        | [notes/RUBRIC_V1.md](notes/RUBRIC_V1.md)                                       |
| Live-input yield, supersession, v1.x gates     | [notes/SPEC_V1X_BOUNDARY_MECHANISMS.md](notes/SPEC_V1X_BOUNDARY_MECHANISMS.md) |
| Inherited vocabulary, two-plane lineage terms  | [notes/previous/review/glossary.md](notes/previous/review/glossary.md)         |
| Pause/resume frontier (PRF) — live instrument  | [notes/SPEC_PAUSE_RESUME.md](notes/SPEC_PAUSE_RESUME.md) (Parts I–IV; sealed parts are law) |
| Warming-budget instrument — armed watch        | [notes/SPEC_WARMING_BUDGET.md](notes/SPEC_WARMING_BUDGET.md)                   |
| Cold orientation / guided tour of the lab      | [notes/walkthrough/README.md](notes/walkthrough/README.md)                     |
| Previous lab history (retrospective)           | [notes/previous/README.md](notes/previous/README.md)                           |
| Closed research arc (2026-06-11–12)            | [.substrate/threads/research/README.md](.substrate/threads/research/README.md) |


## Document authority

When documents disagree, prefer the **most specific, most recently reviewed** artifact for the task:

1. Episode JSON + ledger rows for *what happened in a run*.
2. `notes/RUBRIC_V1.md` / `notes/SPEC_V1X_*.md` for *cell and mechanism definitions*.
3. `notes/PLAN_V1_BRANCH_AND_OFFER.md` for *harness architecture and standing rules*.
4. `README.md` for *thesis and direction*.
5. Substrate thread entries for *discussion and rationale* — not a substitute for specs unless explicitly promoted.

## Standing lab rules

These are important. Violating them usually means a revert, not a debate.

### The five refusals (R1–R5)

Every feature must serve at least one:


| #   | Refusal                       | Plain meaning                                                |
| --- | ----------------------------- | ------------------------------------------------------------ |
| R1  | `retrieved ≠ true`            | [Oracle](notes/GLOSSARY.md#oracle-score) scores answers, not retrievals.                       |
| R2  | `present ≠ authorized`        | [Offer](notes/GLOSSARY.md#offer-set)/[withhold](notes/GLOSSARY.md#withholding) ledger; every [boundary](notes/GLOSSARY.md#offer-boundary) crossing has a reason. |
| R3  | `diverged ≠ improved`         | No diff without an [oracle score](notes/GLOSSARY.md#oracle-score).                             |
| R4  | `governed won ≠ only success` | Rubric includes [governance](notes/GLOSSARY.md#governance)-should-lose cells.                |
| R5  | `self-classification ≠ usage` | [Post-hoc labels](notes/GLOSSARY.md#agent_claimed_usage) are [audit](notes/GLOSSARY.md#usage-audit) input, never win conditions.       |


### Governance vs annotation

A mechanism must act **before the answer** — at the [offer boundary](notes/GLOSSARY.md#offer-boundary) or earlier. Post-answer [usage elicitation](notes/GLOSSARY.md#construct-aware-audit) ([L3](notes/GLOSSARY.md#l3)) is [audit](notes/GLOSSARY.md#usage-audit), not treatment.

### Control group is a branch

One engine, forked memory conditions. Do not build a second system for the baseline lane.

### Ledger writer is external

The harness writes offers, withholdings, diffs, and verdicts. The agent under test does not steer its own ledger.

### Every mechanism ships with a loses-cell

If you cannot name an episode where the mechanism should lose, the mechanism is not reviewable.

### Scored claims are computed

[`cell_verdict`](notes/GLOSSARY.md#cell_verdict) rows come from `harness/score_cells.py`, not from a human reading JSONL. Wire tests (`engine_backend=mock`) are disclosed as such and are not evidence about memory.

### Fork identity

Within a fork group, hold constant: episode inputs, model + params, prompt template, [foreground](notes/GLOSSARY.md#foreground-data) rendering, [oracle](notes/GLOSSARY.md#oracle-score). Only memory-condition config may differ. Build `foreground_data` once per fork group.

### Surface dependence

- **Input surface** ([renderer](notes/GLOSSARY.md#renderer)) and **output surface** (answer shape) both change measured behavior — see [surface-dependent](notes/GLOSSARY.md#surface-dependent).
- [Oracle](notes/GLOSSARY.md#oracle-score) scoring and [usage audit](notes/GLOSSARY.md#usage-audit) may need different answer shapes (A1 vs A1-v2).

## Repository layout

```text
construct/
├── AGENTS.md              ← repo operating contract (you are here)
├── README.md              ← living thesis
├── Makefile               ← common harness commands
├── harness/               ← branch-and-offer runner, scorer, engine adapters
├── episodes/              ← authored task definitions (JSON)
├── episodes/probes/       ← historical bootstrap-conformance probes (M-1 evidence)
├── corpus/                ← world-oracle corpora (retraction; fictional out-of-weights fixtures)
├── runs/                  ← append-only ledgers and authority sidecars (generated)
├── notes/                 ← specs, rubric, roadmap, glossary
├── notes/walkthrough/     ← guided route for cold readers (ch 0–13)
├── notes/previous/        ← prior memory lab (read for inheritance, not by default)
└── .substrate/threads/    ← turn-based group conversations (substrate MCP)
```

`**runs/**` — JSONL ledgers and per-lane authority sidecars. Regeneratable via harness; treat as experiment evidence, not hand-edited truth.

`**.substrate/**` — immutable thread trace. Read before writing; use `write_entry` only on your turn.

## Running the harness

Requires Python 3.12+ and [uv](https://github.com/astral-sh/uv). Local engines expect LM Studio or another OpenAI-compatible server unless using `--engine claude` or `--engine mock`.

```bash
# Wire test (no model credentials)
make smoke

# Stage B on one episode (default: conflict-001)
make stage-b EP=episodes/poison-001.json

# Full scored suite + cell verdicts (Anthropic)
make suite

# Local model via LM Studio
make suite-local
```

Score a ledger after a run:

```bash
uv run --no-project python -m harness.score_cells runs/poison-001.stage_b.jsonl episodes/poison-001.json
```

X-track instrument smokes (no model, disclosed wire tests): `make x1-test`, `make x2-test`, `make x2-fixture-check` (the X2 cost/state-dependence admission gate).

Mock-engine runs are valid for **wire tests only**. They must not be cited as memory findings.

## Working on code

### Scope and style

- Match existing harness patterns in `harness/runner.py`, `harness/score_cells.py`.
- Prefer minimal diffs. No new schema until an existing one changed behavior in a measured run (plan §2).
- Comments explain non-obvious invariants (gate order, fork identity, ablation limits) — not restatements of code.

### Offer pipeline (v1.x)

Gate order is fixed:

```text
eligibility → live-input yield → supersession among survivors → top_k
```

One [withholding](notes/GLOSSARY.md#withholding) reason per record; first applicable gate wins.

### Ablation

[Single-record ablation](notes/GLOSSARY.md#ablation_run) drives [authority](notes/GLOSSARY.md#authority) credit and causal attribution. It means **influential**, not **correct**. Disclosed in every `run_config`. Do not skip ablation on episodes with `expected_winner_condition`.

### Lanes (reference)


| Lane | Meaning                                         |
| ---- | ----------------------------------------------- |
| [L0](notes/GLOSSARY.md#l0)   | No memory                                       |
| [L1](notes/GLOSSARY.md#l1)   | Naive retrieval                                 |
| [L2](notes/GLOSSARY.md#l2)   | Governed [eligibility](notes/GLOSSARY.md#eligibility)                            |
| [L2y](notes/GLOSSARY.md#l2y)  | L2 + [live-input yield](notes/GLOSSARY.md#live-input-yield)                           |
| [L2s](notes/GLOSSARY.md#l2s)  | L2 + [supersession](notes/GLOSSARY.md#supersession) policy                        |
| [L3](notes/GLOSSARY.md#l3)   | L2 + post-answer [usage elicitation](notes/GLOSSARY.md#construct-aware-audit) (audit only) |


Full definitions: [notes/GLOSSARY.md](notes/GLOSSARY.md).

## Substrate participation

When working in a `construct/`* thread via substrate MCP:

1. `list_threads` → find thread and space.
2. `wait_for_turn` until it is your turn (timeout means still waiting — call again).
3. `read_thread` — use `from_line` for incremental catch-up.
4. `write_entry` — markdown addressed to the whole thread. Send exactly `pass` to yield quietly.

Several spaces may be configured — pass `space: construct` with `thread` on every call.

Roles vary by thread: builder, reviewer, auditor, world-oracle. If you did not build the harness, stay cold on implementation when auditing scored cells.

## Review discipline

Specs and rubrics use **bounded review passes**: written blockers, one pass each, no iterate-until-agreement fatigue. Endorse or block; do not rewrite by committee in the thread.

[Usage audits](notes/GLOSSARY.md#usage-audit) are **label-blind**: score from question + record texts + answer (+ [ablation](notes/GLOSSARY.md#ablation_run) if needed). Compare to claimed labels only after submitting.

## Milestone gate

Before starting work, check [notes/ROADMAP.md](notes/ROADMAP.md):

- Which milestone does this serve?
- What oracle applies?
- What loses-condition prices the mechanism?

The historical path through M3 is recorded in ROADMAP. Use ROADMAP for current milestone status, active gates, and carry-forward debts.

Legal answer: *"None, but it's cheap and interesting"* — if said out loud.

## Permissions

**May:**

- Read any file in the repo and substrate threads you can access.
- Run harness commands and append to `runs/`.
- Edit specs, episodes, harness code, README when tasked.
- Write substrate entries on your turn.
- Propose ROADMAP/README updates via thread or PR.

**Should not without explicit ask:**

- Commit secrets (`.env`, API keys) — see [.gitignore](.gitignore).
- Treat mock-engine or wire-test ledgers as scored findings.
- Declare a cell pass/fail without a `cell_verdict` row.
- Inject usage labels before the answer (L3 elicitation is post-answer only).
- Edit or delete substrate thread entries (append-only).
- Expand scope into AWS/TAI/full epistemic schema — listed non-goals in plan §7.

## Common failure modes

- **Presence riding as consequence** — crediting every offered record on a win. Use [ablation](notes/GLOSSARY.md#ablation_run) importance flags.
- **[Governance](notes/GLOSSARY.md#governance)-win without treatment diff** — same [offer set](notes/GLOSSARY.md#offer-set) across [lanes](notes/GLOSSARY.md#memory-lane) (W1 → A1 lesson).
- **[Oracle](notes/GLOSSARY.md#oracle-score) ride-along** — right answer, wrong reason. Require attribution rows for causal cells.
- **Latency-as-governance-cost** — use deterministic costs (tokens, [`governance_steps`](notes/GLOSSARY.md#governance_steps)) except in L-B-style cells.
- **[Renderer](notes/GLOSSARY.md#renderer) drift** — changing [foreground](notes/GLOSSARY.md#foreground-data) template without recording it in `run_config`.
- **Contract bloat** — turning AGENTS.md into a context dump of conclusions.

## Promotion from thread to repo

Thread entries are trace, not spec. Promote to governed memory only when:

- The room converged (or moderated resolution).
- A spec/rubric/README was amended in-repo.
- A ledger or scorer encodes the check.

Do not copy thread prose into AGENTS.md — link to the authoritative file instead.