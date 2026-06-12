# SPEC M0 — Un-authored oracles (Stage C)

Status: **v0.1 — REVIEWED** (one bounded pass each, 2026-06-12: kagi, cursor, codex — all gates open; codex's policy-off isolation blocker adopted). Serves ROADMAP M0. Oracle: the world. Loses-condition: representativeness failure of the `im_w` kind — disclosed, not buried. Review log at the end.

The retraction corpus is the interim un-authored source (kagi/cursor). The trace track (dan's unified-logging recon) stays discovery-before-schema and gets its episode design only after the file shapes are known — nothing here presumes it.

## §1 The authorship boundary

The honest claim M0 can make, stated before any cell is scored:

- **Un-authored:** the retraction event itself — paper identity (DOI), category (retraction / correction / expression of concern), date, stated reason, and the publisher/Retraction Watch record of it. This is the **oracle**.
- **Authored, disclosed:** the question framing, record selection and rendering, lane configs, and the **decision rule** that maps world-fact to correct behavior. This is the **apparatus**.

The decision rule is normative, so it is pinned and cited rather than smuggled: *a retracted finding is not citable support (COPE retraction guidelines); a corrected finding remains citable where the correction does not touch the claim.* The oracle row carries the rule it applied. We author the mapping; the world authors the fact; neither pretends to be the other.

**Key insight the design leans on:** a retraction is the world's own supersession event — the retraction notice references the paper it supersedes (DOI to DOI). The `supersedes` link in a C-1 episode mirrors a real edge in the world's memory, not an authored convenience. And the world also supplies the mechanism's price: corrections and errata are supersession-*shaped* events where burial is the wrong treatment. M0's loses-cell is found, not invented.

## §2 The corpus

`corpus/retractions/<id>.json`, one entry per event, supplied by kagi (world-oracle role) with citations, spot-verified by a second participant before any scored run.

```json
{
  "corpus_id": "rw-0001",
  "doi": "10.xxxx/xxxxx",
  "title": "<paper title>",
  "claim_summary": "<1-2 sentences, the claim as the world reported it>",
  "category": "retraction | correction | expression_of_concern",
  "event_date": "YYYY-MM-DD",
  "stated_reason": "<publisher's stated reason>",
  "claim_stands_after_event": false,
  "notice_terseness": "self_sufficient | terse | mixed",
  "provenance_urls": ["<retraction notice>", "<RW entry>", "..."],
  "selection_method": "<the query/filter that surfaced this entry — selection bias is corpus data>",
  "verified_by": "<participant>", "verified_at": "YYYY-MM-DD",
  "corpus_scope": "<what slice of the world this entry can speak for>"
}
```

Rules:

- **Citations are load-bearing.** An entry without working provenance URLs cannot back an oracle row.
- **`selection_method` is mandatory.** How kagi found the entry is part of what the verdict can claim — a corpus of famous fraud cases speaks for famous fraud cases.
- **`claim_stands_after_event`** is the field the decision rule consumes; it is set from the publisher's notice, not from our reading of the science.
- **`notice_terseness` is set at entry time from the actual notice** (kagi): the C-2 dependency lives in data, not only in spec prose, and `selection_method` can reference it without re-arguing at scoring time.
- **Expressions of concern are excluded from v0 episodes.** The category is genuinely ambiguous (the world has not decided); v0 scores only categories where the world has. Entries may still be collected and held.

## §3 Episode classes (instantiated only after corpus entries land — no placeholder world data, ever)

Both classes run **L0 / L1 / L2 / L2s** — identical configs except `supersession_policy` (codex's isolation blocker, adopted: the W1→A1 lesson says a governance win without a policy-off control is a correct answer with insufficient proof of cause). The config that wins C-1 must face C-2 unchanged; that is what makes C-2 a price and not a strawman. **Same-config-across-the-pair is enforced by the suite runner, not requested** (cursor) — C-2 cannot be quietly "fixed" by tuning L2s between cells.

### C-1 — cite-or-decline (governance should win)

- **Records:** (a) pre-event claim record — the paper's claim rendered as a contemporaneous summary, no hint of what came later; (b) the event notice record carrying `supersedes: [claim-record]` (mirroring the DOI-to-DOI edge); (c) filler. Record texts cite the DOI so rendering stays anchored to the world artifact.
- **Question:** decision-shaped for mechanical scoring — *"We are drafting a review. May we cite this finding as support? Answer `cite` or `decline`, then one sentence."*
- **Expected behavior (category = retraction):** `decline`. L2s buries the claim record and offers the notice; L1 offers whatever similarity ranks (typically both — conflict burden); L0 abstains or guesses.
- **Cell verdict:** governance wins only if the L2s answer is correct AND ablation shows the notice record load-bearing (oracle ride-along discipline unchanged) AND the policy-off lanes (L1, L2) score lower. If policy-off lanes also answer correctly, the verdict is `not_engaged` — the engine handled the retraction unaided, and supersession was a passenger.

### C-2 — correction granularity (governance should lose; M0's loses-cell)

- **Corpus entry:** a *correction* where `claim_stands_after_event: true` (e.g., a figure or author affiliation corrected, core claim untouched).
- **Same record geometry as C-1** — the correction notice carries the same supersession-shaped edge. A supersession treatment that buries the claim record forces the engine to decide without the claim — expected wrong (`decline` where the world says `cite`).
- **What it prices:** our `supersedes` vocabulary is coarser than the world's event taxonomy. If L2s loses C-2, that is the finding — the mechanism needs category-aware links (`supersedes` vs `amends`), and that becomes an M1-adjacent proposal, not a silent patch.
- **Cell verdict:** the loss counts as supersession's price only if L2s scores below the policy-off lanes (L1, L2) AND ablation shows the buried claim record answer-bearing where it was offered. If every lane fails, that is corpus/rendering failure or `not_engaged` — not the mechanism's price (codex).
- **Honest dependency, stated up front:** whether burial actually costs anything depends on the notice's terseness. A corrigendum that restates "conclusions unaffected" lets the governed lane answer correctly from the notice alone; many real corrigenda are terse and do not. Record texts must follow the *actual* notice's level of detail (rendering anchored to the world artifact, disclosed), and if kagi's candidates skew terse, `selection_method` says so. If the world's notices turn out mostly self-sufficient, C-2 yields a null result instead of a loss — which is itself a finding about correction notices as a memory surface, and it ships either way.

## §4 Oracle row mechanics (scoring time, immutable after)

The oracle row for an un-authored episode carries, written **when the score is written**:

```
type: world_checked
source: retraction_corpus            ← satisfies M0 success: source != authored
corpus_entry: corpus/retractions/<id>.json
corpus_entry_sha256: <hash at scoring time — pins what was scored against>
decision_rule: "COPE: retracted => decline; corrected w/ claim standing => cite"
decision_rule_source: "<citation/URL for the rule>"
                                     ← BOTH required, non-empty, on every world_checked
                                       row; the scorer hard-fails otherwise (kagi/codex:
                                       an absent rule smuggles the apparatus back into
                                       the oracle while the row still looks world-checked)
corpus_confidence: 0.9               ← how well-evidenced the world fact is (verified entry)
rule_confidence: 0.7-0.9             ← how universally the rule applies (publisher practice
                                       varies from COPE). The authority gate consumes
                                       min(corpus_confidence, rule_confidence) — codex's
                                       conservative rule, ledgered here.
representativeness: "<one sentence: what this verdict can and cannot claim>"
corpus_scope: <copied from the corpus entry>
scorer: harness                      ← decision extraction is mechanical; kagi's
                                       role is corpus supply + verification, recorded in the entry

# Reserved for the trace track (null on retraction rows) — reserved NOW so the
# oracle row shape does not fork when dan's Console.app material lands (kagi/codex):
trace_interval: null                 ← ISO 8601 start/end; traces cover intervals, not points
device_id: null                      ← opaque, redacted capture-session provenance
capture_source: null                 ← console_app | unified_log_export | simulator_stream
```

**Retroactive interpretation is a different epistemic act** (kagi/codex, ROADMAP M0): a later re-reading (the retraction was itself retracted; the correction was upgraded) is a new row kind `oracle_reinterpretation` referencing the original row by hash. It never rewrites the original. The original verdict stays true-as-scored under the corpus state then in force — the L-A precedent, applied to the world.

## §5 Ledger boundary integrity (kagi, at M-1 close)

Corpus entries contain the answers to their own episodes. Today that is safe: engines under test never read the repo — the harness injects prompts. The rule is written now for when it stops being safe:

- The moment any agent-under-test holds repo read access (M2 resident; any future conformance-like exercise), `corpus/` joins `runs/bootstrap/` and the calibration file on the off-path list, and the leak scan extends to corpus ids.
- Same growth-path logic as the M-1 hole: a legal read that carries no decisions today may carry them tomorrow. We govern the path before the resident exists, not after the first incident.

## §6 Build plan and review asks

Order: (1) this spec reviewed — one bounded pass each ✓ (v0.1); (2) kagi commissioned: 3–5 retraction candidates + 1–2 corrections, schema-complete, citations, `selection_method`, and `notice_terseness` included; (3) verification pass by a second participant; (4) harness: corpus loader, oracle-row fields (scorer hard-fails on empty `decision_rule`/`decision_rule_source` for world_checked rows), `oracle_reinterpretation` row kind, mechanical `cite`/`decline` extraction, suite-runner enforcement of identical configs across the C-1/C-2 pair (except `supersession_policy`); (5) episodes instantiated from entries; (6) scored runs across engines, lanes L0/L1/L2/L2s. Success: first `cell_verdict` whose oracle row carries `source != authored`.

**Review asks:** (a) does §1's authorship boundary hold up — especially the disclosed decision rule; (b) is C-2 a fair price or a strawman; (c) the §4 confidence value and whether 0.9 is honest for a verified corpus entry; (d) anything the trace track needs reserved in the schema now so it does not fork the oracle-row shape later.

## Review log

- v0 (2026-06-12, claude): drafted post M-1 close.
- **v0 → v0.1 (2026-06-12, one bounded pass each — kagi, cursor, codex; all gates open):**
  1. **Policy-off isolation** (codex, blocker — adopted): both classes run L0/L1/L2/L2s, identical except `supersession_policy`; C-1 wins require policy-off lanes lower or the verdict is `not_engaged`; C-2 losses count only against policy-off controls with the buried record answer-bearing. The W1→A1 lesson, applied before the mistake this time.
  2. **`decision_rule` + `decision_rule_source` required** on every world_checked row, scorer hard-fails if empty (kagi, hardened by codex).
  3. **Confidence split**: `corpus_confidence` / `rule_confidence`; authority gate consumes the min (kagi/cursor/codex; codex's min rule chosen).
  4. **`notice_terseness` in the corpus schema** — the C-2 dependency lives in data (kagi).
  5. **Trace-track fields reserved now**: `trace_interval`, `device_id`, `capture_source` — null on retraction rows (kagi + codex's capture_source).
  6. Same-config-across-pair enforced by the suite runner, not requested (cursor).
  7. Recorded alongside: cursor's retraction of the unledgered M-1 re-run claim — the correction discipline working as designed (claim withdrawn, original entry stands in the trace).
