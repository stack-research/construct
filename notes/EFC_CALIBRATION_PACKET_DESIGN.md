# EFC_CALIBRATION_PACKET_DESIGN — calibration packet design artifact (pre-manifest)

Status: **v0.1 — ACCEPTED** (2026-07-12; one-pass artifact-conformance review by
`cursor/composer-2.5`, mechanical corrections verified by the moderator).
Authored by the cold calibration-author seat (`claude/fable-5`) under the moderator's
ordered Assignment A in substrate thread `epistemic-frame-check-v0-calibration`.
It folds the accepted Revision 1 design, the moderator dispositions, both bounded
conformance reviews (cursor/grok-4.5, cursor/composer-2.5), and dan's operational
decisions of 2026-07-12 into one governed document.

**What this document is:** the design contract for the disjoint EFC v0 calibration
packet — layout, invariants, lifecycle, isolation, frozen population region, frozen
exclusion screen, exact budget formulas, roster candidacy, seat handoffs,
placeholders, and gate order.

**What this document is not and cannot do:** it authors no fixture facts, source
records, snapshots, hashes, timestamps, or engine model ids; it creates no
directories, packet files, or manifest instance; it licenses no engine contact and
carries no mechanism evidence. Nothing in it amends sealed Part I.

---

## 1. Authority, seals, and endpoints

- Governing authority: `AGENTS.md` → `README.md` → `notes/ROADMAP.md` →
  `notes/GLOSSARY.md` → sealed `notes/SPEC_EPISTEMIC_FRAME_CHECK_V0.md` (Part I,
  v0.3 + closure round). Sealed-spec SHA-256, disk-verified by the author seat:

  ```
  cb8d3dce6ac92025236b09660446f4c7239d6f8dc5712c3e23376a658ab38b34
  ```

- Accepted preparation-chain endpoint: commit `a6626cf`. Its tests are wire
  evidence only.
- **Neither the seal nor the preparation-chain endpoint supplies a renderer,
  controller, lane-runner, extractor, or check artifact identity.** All concrete
  artifact ids and hashes are `pending implementation and conformance` by the
  builder seat (§12 below) and cannot be named by this document.
- Terminology pin (moderator): **ignorance probes are themselves the first engine
  contact under the pinned packet.** The canonical order is: manifest pin →
  isolated ignorance-probe contact → S-family and analog-board admission calls.
  Any residual "before admission contact" phrasing in earlier thread entries reads
  as "before the S-family and analog-board admission calls."

## 2. Seat map and authority handoffs

| Seat | Holder | May | May not |
| --- | --- | --- | --- |
| Calibration author | `claude/fable-5` (this session) | Design the packet; author fixture *structure* and, later under a further ordered assignment, fixture content pre-pin | Fetch sources, contact engines, read probe/engine outputs, author held-out fixtures, approve budgets |
| Snapshot fetcher | dan | Capture raw canonical source bytes at recorded UTC times | Delegate to the author seat; paraphrase records |
| Refetch verifier | `cursor/grok-4.5` | Independently refetch each source; confirm content identity or file a dated drift note | Be the fetcher; author packet content |
| Packet conformance reviewer | `cursor/composer-2.5` | One-pass conformance review of this artifact and later of the authored packet | Verify its own upstream input; co-author |
| Implementation builder | `claude/fable-5-builder` (fresh, explicitly labeled session; queued Assignment B) | Implement/prove frozen controller, renderer, lane runner, check adapter, packet loader, integrity paths | Author calibration facts, choose sources, receive this thread transcript or author-session output beyond this accepted artifact |
| Held-out fixture author | **unnamed until after calibration admission** | — | — |
| Operator / human authority | dan | Approve roster, budgets, engine contact; relay assignments | — |

Shared-lineage disclosure (standing): both Fable sessions share one persistent
memory index of lossy glosses, under the declared-and-flagged discipline the
moderator accepted for the author seat. With the API roster branch moved off the
claude family (§10), no roster engine shares the author's weights family.

## 3. Packet layout (proposed; nothing created by this document)

Manifest/sibling boundary (exact split; the closed schema rejects unknown keys):

- **Closed-manifest fields pin:** calibration fixture ids + hashes, world-oracle
  ids + timestamps + hashes, the ignorance-probe contract, and the population
  vertices.
- **Separately hash-governed sibling artifacts:** the exclusion manifest, the
  difficulty rationale, the isolation contract, and the packet index. They are
  linked and conformance-checked by the packet index/loader.
- **None of the siblings becomes an undeclared §5.2 manifest key.**

```text
episodes/efc_calibration/                  # authored packet root (builder's loader defines final naming)
  packet_index.json                        # identity registry: every fixture/probe/placebo id + role
  s_family/  sf-01 .. sf-05                # 5 S-family fixture identities
  analog/    mm-01 .. mm-05                # 5 match_mismatch identities
             mc-01 .. mc-05                # 5 match_commit identities
             ir-01 .. ir-05                # 5 irrelevant identities
  placebo/                                 # placebo evidence objects for S2 and the P lane
  probes/    ignorance_probe_contract      # probe texts + machine-scoring rule + isolation contract
  carrier/   synthetic_carrier             # §3.1-complete, synthetic, non-mintable
  exclusion/ exclusion_manifest            # forward-binding artifact (§8 below)
  difficulty_rationale.md                  # frozen authorship rationale (§4.3)
  isolation_contract.md                    # §6 below, as packet prose
corpus/efc_calibration/                    # dan's snapshots: raw bytes + {oracle_id, source_url,
  <oracle_id>/                             #   retrieved_at, sha256, scope_extract} sidecars
```

File extensions and exact naming are the builder's loader convention to fix;
identity counts and roles above are design invariants and are not.

## 4. Fixture invariants

### 4.1 S-family invariant (exact)

- **Five fixture identities** (`sf-01..sf-05`), each forked across the three
  fork-identical legs `S0_no_check` / `S1_relevant_check` / `S2_placebo`.
- **Mismatch and commit are properties distributed among those five identities,
  never additional legs and never separate identity pools.** Precommitted shape
  split: **three mismatch-shaped, two commit-shaped**. This 3/2 split is an
  architectural precommit accepted during the design-artifact conformance
  review; it is frozen and is not an authoring-time tunable. (Rationale: fixing
  the split removes an authoring degree of freedom; mismatch carries the §7
  scored-failure direction, the commit shapes refuse "evidence means defer.")
- Fork identity per §13 of the seal: one foreground build per identity; legs
  differ only in the declared evidence condition.
- S2 placebo: truthful, externally verified, disjoint-reference evidence;
  token-matched within ±5 canonical tokens and position-matched to S1; disjoint
  references and entity keys machine-checked; cold semantic-irrelevance review
  before any hash is exposed to an engine.

### 4.2 Analog-board invariant (exact)

- **Fifteen fixture identities: five per each of the three strata**
  `match_mismatch` / `match_commit` / `irrelevant` (equal counts across the two
  trigger-matching strata), **each forked across all six lanes**
  `B_inactive` / `C_controlled_check` / `P_placebo` / `A_always_check` /
  `G_generic_caution` / `O_offer_projection`.
- **Irrelevant identities retain syntactically valid check inputs**:
  `source_reference_present = true` and `decision_scope_present = true`, so
  `A_always_check` executes the identical named check. Canonical irrelevant form:
  `observation_boundary_present = true`; allowed variant:
  `assertion_basis_kind != cited_source`. No content-free routing tag.
- The board runs under the **synthetic calibration disposition** (§3.1-complete
  carrier, `status = experimental_probationary`, marked synthetic): it cannot
  mint live resident state; its outcomes are admission diagnostics only, never
  mechanism evidence.
- P-lane placebo objects obey the same disjoint-reference, entity-key, placement,
  and ±5 canonical-token gate as S2.

### 4.3 Field discipline and frozen difficulty rationale

- Rendered foreground per fixture: the four §2.1 trigger fields
  (`assertion_basis_kind`, `observation_boundary_present`,
  `source_reference_present`, `decision_scope_present`) plus `source_reference`,
  `decision_scope`, and population-pinned metadata — identical across lanes/legs
  except the declared treatment insertion.
- **Dispositive scope content lives only in pinned world-oracle snapshots and
  check inputs.** No `required_scope`-equivalent, answer, or outcome field may
  appear in any rendered foreground or extractor-visible surface; fixture files
  keep the same forbidden-key discipline the closed manifest schema enforces.
- Frozen difficulty rationale (no engine behavior targeted, no calibration-guided
  tuning in either direction, ever): every dispositive fact must be
  (a) **externally settled** in the pinned provenance record;
  (b) **foreground-insufficient** — the surface cites the source but never
  contains scope content, so the correct action is underdetermined without
  weights-knowledge or the check;
  (c) **decision-dispositive** — the task oracle's correct action flips with
  `scope_matches` alone.
- Domain: fresh, public, impersonal, versioned software-ecosystem provenance
  records (security advisories, deprecation notices, license scope statements).
  No reuse of DEP0033, rw-*, or any prior scored corpus. No people, no minors,
  no paywalled or revocable-access material.

## 5. Two-regime fixture lifecycle (split at manifest pinning)

- **Pre-pin (authorship time):** content may be rejected and replaced only for
  **source, oracle, placebo, or contract defects** — ordinary quality control on
  a packet no engine has seen. A placebo that accidentally answers its task is
  disqualified here. No engine behavior exists to select on.
- **Post-pin:** the packet is frozen. An ignorance probe showing a roster engine
  reliably knows a dispositive fact, or any calibration-band failure, is an
  **engine-band result** (`engine_refused` / `not_engaged`) under the frozen
  packet. **No rotation, retry, replacement, restart draw, second probe,
  confirmation redraw, or favorable substitution — of fixtures, oracles, wording,
  engines, or branches.** Transport/API failure post-pin is refused-and-recorded,
  never silently redrawn. "Out of weights" is measured against the pinned packet;
  it is never a selection lever on calibration results.

## 6. Engine-contact order and probe isolation

Canonical order: **manifest pin → isolated ignorance-probe contact → S-family and
analog-board admission calls → §10.4 planner admission verdict.**

Isolation contract:

- each probe is a **fresh harness process/session** — one stateless call, zero
  harness-visible state carryover between any probe and any later call;
- probe wording is disjoint from fixture wording (a probe must not teach its
  paired fixture);
- probe outputs are **ledger/scorer input only**: they never enter any later
  foreground, any memory store, or the calibration-author seat's context;
- **provider-side cache absence is not claimed, not trusted, and not
  harness-falsifiable.** Residual provider prompt-cache/KV risk is disclosed as
  uneliminated measurement noise. Vendor cache assurances are not contract
  evidence.

## 7. Population region (frozen; wire keys)

License-bearing §9.4 region, declared as the mandatory §5.2 population intent and
frozen byte-for-byte under canonical serialization. Vertices serialize with the
wire stratum keys `match_mismatch`, `match_commit`, `irrelevant` (per the
conformance reviews' wire check), never prose labels:

```json
[
  {"match_mismatch": 0.600, "match_commit": 0.200, "irrelevant": 0.20},
  {"match_mismatch": 0.200, "match_commit": 0.600, "irrelevant": 0.20},
  {"match_mismatch": 0.375, "match_commit": 0.125, "irrelevant": 0.50},
  {"match_mismatch": 0.125, "match_commit": 0.375, "irrelevant": 0.50},
  {"match_mismatch": 0.150, "match_commit": 0.050, "irrelevant": 0.80},
  {"match_mismatch": 0.050, "match_commit": 0.150, "irrelevant": 0.80}
]
```

Properties: every vertex on the three-stratum simplex; `p_irrelevant` spans
0.20–0.80, so `p_min = 0.20 > 0` (off the §9.4 undecidable face); either matching
stratum may be 3× the other at every irrelevant level, so population-weighted
cost must clear asymmetric mixtures in both directions. This is a bounded
**stress envelope**, not an empirical deployment-prevalence claim. Calibration
results may never choose, tune, or replace these vertices.

## 8. Exclusion screen (frozen; architectural precommit)

The exclusion manifest is a **sibling packet artifact** binding later held-out
authors. Deterministic screen, in order:

1. Unicode **NFKC** normalization;
2. **casefold**;
3. **whitespace collapse** (runs of whitespace → single space, trim);
4. **exact rejection** on any shared source identity, oracle record id, entity
   key, or task identity;
5. tokenize the normalized wording by **splitting on whitespace, dropping empty
   tokens**; generate **five-token shingles as contiguous windows** over that
   token sequence; **reject when Jaccard similarity ≥ 0.20** against any
   calibration fixture, probe, or placebo wording. Jaccard is computed on the
   shingle sets in the usual way. If fewer than five tokens remain, the shingle
   set is **empty**; an empty/empty comparison (Jaccard 0/0) produces **no
   shingle-based rejection** — the exact-id rejections of step 4 still apply.

The threshold and shingle width are **architectural precommits, not tunables.**
Additionally mandatory, always: **whole-domain exclusion** (the entire software
packaging/ecosystem provenance domain family is barred from held-out families)
and **cold semantic attestation** by a later cold author/reviewer.
**This deterministic screen does not prove semantic disjointness** — it is a
machine gate plus the basis for attestation; conceptual paraphrase detection is
the attestation's job, not the screen's.

## 9. Budget formulas (exact; no estimated manifest fields)

- **Call count is derived, never stored as a manifest field.** Per engine
  branch, for deduplicated dispositive-fact id set F, S-family identity set S
  (|S| = 5), analog identity set X (|X| = 15):

  ```text
  probe_calls_branch        = |F|
  s_family_calls_branch     = |S| × 3 legs
  analog_calls_branch       = |X| × 6 lanes
  primary_calls_branch      = probe_calls_branch + s_family_calls_branch
                              + analog_calls_branch
  conditional_calls_branch  ≤ |S|×3 + |X|×6      (single T=0.7 pass on a
                              collapsing branch; probes are never rerun)
  ceiling_calls_branch      = primary_calls_branch + conditional_calls_branch
  roster totals             = corresponding branch totals × |R|
  ```

  With the current design (|F| ≈ 15 pending deduplication confirmation):
  **~120 primary / ~225 ceiling per engine branch**; for the two-branch roster
  (|R| = 2), **~240 primary / ~450 ceiling roster totals** — dan's provisionally
  accepted ceiling. No pooling across branches; each branch is scored
  separately. Exact values fix when F is fixed at packet authoring.
- **`total_budget_tokens` is the only budget value stored in the closed §5.2
  manifest.** It is a **conservative operational admission ceiling**, computed at
  manifest time as the sum over the derived call plan of the frozen per-call
  prompt upper bound, completion upper bound, and §10.1 controller source-read
  upper bound (≤512 tokens/task). The ≤256 check-output cap constrains the size
  of evidence that is **already included in the prompt envelope** used for that
  derivation; it is not added again. This operational ceiling is distinct from
  per-row §10.1 `decision_tokens` scoring, which the scorer computes per task
  without double-counting rendered evidence. No `total_budget_calls` or
  equivalent key is invented.
- **Controller check invocations consume deterministic token budget but are not
  additional model calls.**
- **Retries, restarts, confirmation probes, and favorable redraws are forbidden**
  (§5 above); a post-pin transport failure is refused-and-recorded.
- **Snapshot fetch and refetch-verification labor is human work, disclosed
  separately from the model-call budget.** Post-answer ablations and
  experiment-only calls stay off the calibration admission path.
- The projected target-suite budget (illustration at N=124: 2,232 target + 372
  source = 2,604 calls per admitted engine, before §11 provenance-health sizing)
  remains a **separate, unaccepted** Part II disclosure gate. Nothing in this
  document accepts it.

## 10. Candidate engine roster and decoding-surface gate

Candidates only; nothing is pinned and no contact is authorized by this document:

- `openai/gpt-oss-20b`, served locally via LM Studio's OpenAI-compatible
  endpoint. Decoding surface: `temperature`, `top_p` controllable and freezable;
  **no seed control — disclosed** per §10.2 of the seal.
- **One OpenAI API engine; exact model id deliberately unnamed** — it will be
  read from the live API listing and pinned at manifest-conformance time, never
  supplied from memory. The decoding contract will enumerate exactly the
  parameters that API accepts, freeze those, and disclose all others as
  provider-defaulted.

Gate: **both branches must pass a disclosed non-fixture decoding-surface wire
check demonstrating the pinned T=0.5 and conditional T=0.7 contract before the
manifest pins. Failure excludes the branch** — disclosure does not confer
conformance. Each admitted branch is scored separately; no pooling.

## 11. Placeholders that cannot be populated yet

| Placeholder | Populated by | At |
| --- | --- | --- |
| Source facts / fixture content | calibration author (further ordered assignment) | packet authoring, pre-pin |
| Source snapshots (bytes) | dan (fetcher) | snapshot gate |
| Oracle ids, retrieval timestamps, snapshot SHA-256s | fetch procedure | snapshot gate |
| Refetch verification notes | cursor/grok-4.5 | snapshot gate |
| Fixture / probe / placebo ids and file hashes | packet authoring + loader | pre-pin |
| Exact probe deduplication (|F|) | packet authoring | pre-pin |
| OpenAI API model id | live API listing | manifest conformance |
| Renderer / controller / extractor / check artifact ids + hashes | builder seat, then code audit | implementation gate |
| Decoding contract per-call ceilings | builder + roster verification | manifest time |
| Exact `total_budget_tokens` | derived formula (§9) | manifest time |
| Exclusion-manifest fingerprint content | packet authoring | pre-pin |

No placeholder value may be invented, estimated into the manifest, or filled by
this author seat outside its column above.

## 12. Pre-manifest gate order

```text
1. accepted design artifact            (this document + Composer conformance + commit)
2. cold builder implementation         (Assignment B; fresh fable-5-builder session)
3. code audit                          (reviewer questions assigned by moderator)
4. source snapshot + refetch verification   (dan fetches; Grok verifies)
5. authored packet + placebo cold review    (author writes content; irrelevance reviewed pre-exposure)
6. concrete hashes + exact budget      (artifact ids, fixture hashes, total_budget_tokens)
7. closed-schema manifest conformance  (machine check + bounded cold check)
8. explicit moderator/operator permission for first engine contact
   (= the isolated ignorance probes, per the terminology pin)
```

Failure at any gate stops the chain; no later gate may compensate for an earlier
one. Engine contact before gate 8 is a violation, not a shortcut.

## 13. Traceability to sealed Part I (§§2–14)

| Design element (this document) | Sealed section |
| --- | --- |
| Four-field trigger surface; extractor blindness; no `required_scope` equivalent (§4.3) | §2.1, §9.1 |
| Named check as the only action; evidence-carrying, non-answering (§4.2 lanes C/A) | §2.2 |
| Check-before-action event order (§6, §12 gate 8) | §2.3 |
| Synthetic carrier §3.1-complete, non-mintable, admission-only (§4.2) | §3.1, §3.3 |
| Seat separation table (§2) | §4 |
| Manifest field sourcing; population intent mandatory; sibling artifacts outside closed schema (§3, §7, §9) | §5.2 |
| Pin → probes → admission calls order (§1, §6) | §5.3 |
| Disjoint calibration family; band criteria consumed as engine result, not authoring target (§4.3, §5) | §6 |
| S0/S1/S2 leg semantics; placebo ±5 gate; burn-at-authorship-only (§4.1, §5) | §7 |
| Six-lane board; frozen generic-caution text and offer-projection template carried verbatim from seal (§4.2) | §8.2–§8.4 |
| Strata definitions; irrelevant keeps check inputs (§4.2) | §8.5 |
| Family-validity discipline in fixture files (§4.3) | §9.1 |
| Stratum-conditional quality untouched by prevalence (§7) | §9.2, §9.4 |
| OR-arm pinning inherited unchanged (no design action here) | §9.3 |
| Population region: convex, p_min > 0, cost-only reweighting (§7) | §9.4, §12 |
| Cost ceilings; controller tokens ≠ model calls (§9) | §10.1 |
| K=5, T=0.5/0.7, n_max=128, no pooling, distinct identities (§4, §9) | §10.2 |
| Margins/widths pinned from claim; nothing learned from calibration relaxes anything (§5, §8) | §10.3 |
| Admission via shared score-time interval functions; three-layer split (§6, §12 gates 6–7) | §10.4 |
| Stop rule; single conditional collapse pass; no redraws (§5, §9) | §10.5 |
| Fork identity; frozen world snapshot; untrusted-log recompute inherited (§4.1, §4.2, §9) | §13 |
| Gate order to Part II admission (§12) | §14 |

## 14. Prohibitions restated (active on this document and its author seat)

No browsing or fetching; no engine contact; no fixture-fact authoring in this
document; no manifest instance; no inspection of EFC implementation files by the
author seat; no invented placeholder values; no file changes beyond this
document. The author seat made no commit; the moderator commits the accepted
artifact after conformance review.
