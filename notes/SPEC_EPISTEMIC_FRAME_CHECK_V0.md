# SPEC_EPISTEMIC_FRAME_CHECK v0 — Part I: pre-engine protocol

Status: **v0.3, Part I SEALED** (2026-07-12; the v0.1 seal hash is recorded in
substrate thread `epistemic-frame-check-v0-review`; the v0.2 arithmetic
amendment (§18) and the v0.3 process amendment (§19) carry their canonical
hashes in `epistemic-frame-check-v0-build`). Derived from the bounded design
round in `epistemic-frame-check-v0` and folded once after the cold pass.
No calibration engine contact, fixture evidence, held-out build, or mechanism
claim is authorized by the seal. Part I admits only the calibration/scorer
preparation in §14; every later step remains gated by the recorded canonical
file hash and computed admission rules.

This document specifies the question and the refusal path. It does not specify
product schema, license a controller, or promote the embodiment sketch beyond
wire/integration status.

## 0. Question, claim, and non-claims

### 0.1 Question

Can a causally earned, provenance-live resident disposition selectively invoke
one bounded external check on held-out structurally matching tasks, improve
world-scored outcomes within a hard deterministic cost bound, and remain silent
when irrelevant?

### 0.2 Candidate claim

The strongest claim Part I permits a later instrument to earn is:

> A causally earned, provenance-live resident disposition selectively invokes a
> verdict-carrying external check on held-out structurally matching tasks,
> improving world-scored outcomes within a hard deterministic cost bound, while
> beating always-check, innate generic caution, and ordinary offered advice on
> their separately precommitted quality/cost comparisons and remaining silent
> on irrelevant work.

The honest short name is **consequence-authorized selective external checking**.
“Structural transfer” may describe the relation between source and held-out task
families. It does not mean that the model discovered a semantic abstraction.

### 0.3 Non-claims

Part I cannot license claims about:

- language-model learning, semantic recognition, or weight change;
- general consolidation, failure geometry, or cognitive embodiment;
- commitment enforcement or controller-authored answers;
- open-ended trigger classification;
- multiple interacting dispositions;
- cumulative metabolic budgets, maturation, or living lifecycle dynamics;
- benefit outside the frozen model, renderer, tool, decoding, predicate, check,
  and population-prevalence envelope;
- that causal earning, rather than the installed predicate/check pair, produces
  target-side performance benefit—earning is an authorization requirement, not
  a tested performance ingredient;
- the authored deterministic behavior in `sketches/next_substrate/` as evidence.

## 1. Milestone gate and governing refusals

This candidate serves the X-track extension of the narrow M2 result: it asks
whether one earned failure can change a later action-boundary check across a
held-out domain relation, rather than merely alter an offered record.

The mechanism is reviewable only if it prices all five standing refusals:

1. **R1 — retrieved is not true:** both source and target outcomes use external
   world oracles; trigger firing and check completion are never outcome scores.
2. **R2 — present is not authorized:** a disposition may act only from a
   computed causal warrant whose provenance remains live.
3. **R3 — diverged is not improved:** every path change is paired with a world
   score and deterministic cost.
4. **R4 — governed won is not the only success:** match-and-commit,
   generic-caution, offer-projection, irrelevance, and scoped-revision cells let
   the controller lose.
5. **R5 — self-classification is not usage:** model nominations, rationales, and
   claims of checking are audit input only. Controller rows and external tool
   traces decide whether a check occurred.

Mock runs may check wiring. They are never evidence about the mechanism.

## 2. The v0 mechanism boundary

### 2.1 Closed structural predicate

The v0 trigger is a deterministic predicate over declared foreground structure:

```text
assertion_basis_kind == cited_source
AND observation_boundary_present == false
AND source_reference_present == true
AND decision_scope_present == true
```

The extractor may read only the task surface and population-pinned metadata. It
may not read fetched source scope, expected action, oracle rows, outcome labels,
model narration, or any field equivalent to `required_scope`. Removing oracle
and outcome material must leave the trigger result byte-identical.

The predicate answers only **when to look**. It may not encode **what the check
will find**. The trigger-matching target family therefore contains equal counts
of:

- **match-mismatch:** the fetched source scope does not cover the declared
  decision scope; the correct action is to decline, defer, or seek an authorized
  source as fixed by the task oracle;
- **match-commit:** the fetched source scope covers the declared decision scope;
  the correct action is to use the source-backed result and commit.

Firing alone must predict neither target action better than chance in the
balanced experimental family. Topic, wording, source identity, and domain vary
across both trigger-matching strata.

### 2.2 Named external check

The only v0 action is `scope_provenance_check_v0`:

1. fetch the population-pinned provenance record for `source_reference`;
2. read its authoritative scope under the frozen tool contract;
3. compare that scope with the task's declared `decision_scope` using the
   population-pinned comparison rule;
4. return a bounded evidence object containing cited provenance and the verdict
   `scope_matches = true | false`.

The check carries a verdict. The model is being tested on whether a governed
body consults the world selectively and can use the returned evidence—not on
whether it independently performs scope comparison.

The check may not emit a final answer, a prose recommendation, or an instruction
to commit or defer. The model still produces the task action. There is no v0
commitment gate.

### 2.3 Action-boundary placement

Canonical order:

```text
ordinary offer phase completes
  -> trigger evaluates
  -> required check runs or remains silent
  -> check evidence enters the activation path
  -> model produces proposed task action
  -> task action commits
  -> external outcome oracle scores
```

The ledger must prove that any candidate check completed before model action and
commitment. Post-answer checks are annotation and cannot enter a win path.
Controller events are distinct from offer and withholding rows.

### 2.4 No enforcement leg

v0 does not force commit, defer, refusal, or tool use after evidence is returned.
An enforcement treatment would test procedural gate semantics and requires a
separate specification and loses-cells. The walking skeleton's deterministic
stub behavior does not supply them.

## 3. Typed carrier and resident instance

The lab licenses a derivation mechanism; the resident activates one instance.
Those are different authorities.

During the license experiment, the harness may create one **sandboxed candidate
instance** after the held-out source gate clears. It is authorized only inside
the sealed experimental forks and may not enter a live resident store. A
successful target result can license the mechanism for future probationary
instances; it cannot retroactively promote the test instance whose behavior
produced that result. This prevents the candidate mechanism from presuming the
authority it is being tested to earn.

### 3.1 Carrier fields required before calibration

A disposition carrier contains only bounded structured state:

```text
mechanism_id
mechanism_version
predicate_contract_hash
predicate_feature_bindings
extractor_hash
check_id
check_contract_hash
warrant_event_ids
warrant_result_hash
validity_envelope
status = experimental_probationary
per_invocation_cost_ceiling
revision_scope_rules_hash
retirement_rules_hash
```

`predicate_feature_bindings` contains the exact trigger fields and values, not a
template id whose meaning lives only in source code. The carrier contains no
lesson paragraph, model rationale, confidence, generalization claim, hidden
instruction, or outcome label.

### 3.2 Validity envelope

The minimum envelope is:

```text
model_id
renderer_id
foreground_template_hash
tool_contract_id
decoding_contract_id
controller_id
predicate_contract_hash
extractor_hash
check_contract_hash
engine_admission_packet_hash
source_family_hash
target_population_hash
per_invocation_cost_ceiling
```

Changing any field creates a new candidate license. A result does not transfer
silently across model versions, renderers, tools, decoding regimes, predicates,
or target populations.

### 3.3 Mint authority

A failed outcome cannot mint. Activation requires all of:

- a held-out source-family causal verdict under §7;
- a world oracle with `source != authored`;
- a live provenance record and no standing revision applicable to the causal
  warrant, check contract, or instance;
- an admitted engine under a disjoint calibration packet;
- exact validity-envelope match;
- external deterministic minting.

Model nomination may be ledgered as an untrusted audit claim. It cannot supply
trigger features, certify the causal story, activate the instance, or override a
refusal.

### 3.4 Warrant health and typed revision

Minting checks warrant health, not merely warrant existence. A disposition may
not activate after an applicable provenance revision already exists.

Every revision carries exactly one typed scope:

```text
source_provenance
causal_derivation
check_contract
resident_instance
```

The provenance-health scorer computes an **authorization verdict** separately
from downstream **task quality and cost**. Authorized suspension may still
expose a utility loss; that loss remains visible and cannot be laundered as a
governance win.

## 4. Authority seats and freeze discipline

Part I separates epistemic authority where judgment can leak. It does not
require a different process or service for every mechanical function.

| Seat | May | May not |
| --- | --- | --- |
| Mechanism licensor | Freeze predicate, extractor, check, meters, thresholds, and hashes | Author held-out outcomes or change the contract after calibration |
| Calibration author | Build the disjoint engine-admission family under the frozen contract | Contribute calibration rows to mechanism evidence |
| Held-out fixture author | Build source and target tasks under the frozen contract | See model nomination prose, raw calibration outputs, or alter the extractor; only typed engine status and declared N/budget quantities may cross |
| External controller | Replay the contract; mint, invoke, suspend, and refuse mechanically | Exercise discretionary interpretation or accept model self-certification |
| Evaluator/scorer | Compute verdicts from frozen rows and external oracles | Author held-out fixtures or repair a failed gate post hoc |
| Model | Answer tasks and nominate claims for audit | Write authoritative lineage, activate state, or score itself |

The named proposer, held-out fixture author, and evaluator may not collapse into
one epistemic seat for license evidence. Contract hashes, fixture hashes, oracle
hashes, and seat identities are recorded before the relevant rows are opened.

## 5. Precommit manifest and event order

### 5.1 Part I seal

Before any real-engine contact, cold review seals:

- this Part I text and `part_i_spec_hash`;
- the claim and non-claims;
- the predicate and extraction prohibition;
- source and target lane definitions;
- minimally important effects and cost ceilings;
- sampling, stop, point-mode, and refusal rules;
- stratum-conditional versus prevalence-weighted quantities;
- the authority-seat contract.

### 5.2 Calibration manifest

After Part I is sealed but before calibration contact, a calibration manifest
pins:

```text
part_i_spec_hash
engine roster
model and decoding ids
renderer and foreground hashes
calibration fixture ids and hashes
world-oracle ids, timestamps, and hashes
ignorance-probe contract
predicate / extractor / check hashes
generic-caution text and hash
offer-projection template and hash
K, temperatures, stop rule, n_max, and total budget
population intent: a license-bearing §9.4 region OR response_curve_only
                   (exactly one; the population choice, made before any
                   calibration contact)
```

The manifest is machine-checked and receives a bounded cold check for contract
conformance. It may not contain held-out source or target outcomes. The
population intent is declared here, before calibration contact: the later
population manifest must match this choice byte-for-byte under canonical
serialization apart from its own identity and hash envelope (§12), so
calibration outcomes can never inform the deployment population on which the
candidate seeks a license.

### 5.3 Canonical event order

```text
part_i_sealed
  -> calibration_manifest_pinned
  -> engine_ignorance_probe
  -> engine_admission_calibration
  -> engine_admitted | engine_refused | point_mode_diagnostic
  -> heldout_source_target_and_population_manifests_pinned
  -> S0/S1/S2 source forks
  -> disposition_minted | disposition_mint_refused
  -> frozen transfer suites
  -> dedicated provenance-health suites
  -> computed typed verdicts
  -> licensed | typed_null | loss | confounded
```

No held-out family is authored from calibration outcomes beyond the typed engine
status and variance/budget quantities permitted by §10. Source, target, and
population manifests are hash-pinned before the engine sees either held-out
family, so source behavior cannot steer target authoring or prevalence scope.
The population manifest's region or `response_curve_only` choice is fixed
before calibration contact by the §5.2 declaration; pinning it after admission
records identity, never a new choice.

## 6. Engine admission: disjoint calibration only

Admission selects an engine band; it is never mechanism evidence. The
calibration family is disjoint in task identity, source identity, wording,
domain, and oracle records from the held-out source and target families.

The packet has two components:

- a calibration S0/S1/S2 family that decides whether the engine can fail and
  use relevant evidence in the required band;
- an authored target-analog board covering every target stratum and lane, used
  only to estimate quality/cost variance and required N.

The analog board uses a synthetic calibration disposition and cannot mint live
resident state. Its outcomes are admission diagnostics only. Neither component
may share sources, tasks, wording, domains, or oracle records with held-out
families.

The same scorer code may serve calibration and held-out minting. The rows may
not. One machinery with disjoint evidence avoids selection on the result.

An engine is in-band only if the calibration S-family shows all of:

- `S0` no-check pass rate at or below `0.50`;
- `S1` relevant-check-evidence pass rate at or above `0.80`;
- `S1 - S0` observed quality difference at least `0.25`;
- `S1 - S2` placebo-controlled difference at least `0.25`;
- ignorance probes show the dispositive external facts are not reliably
  recoverable from weights or foreground;
- every required quality and cost comparison has `n_required <= 128` under §10.

Failure is `engine_refused` or `not_engaged`, not a mechanism loss. Calibration
rows may be cited only to explain admission.

## 7. Source causal family: authority must be earned

The held-out source family has three fork-identical legs:

| Leg | Treatment | Purpose |
| --- | --- | --- |
| `S0_no_check` | No check evidence; ordinary foreground and tools | Establish the scored failure |
| `S1_relevant_check` | Exact relevant check evidence supplied before commitment | Test whether the proposed repair changes the world outcome |
| `S2_placebo` | Token- and placement-matched truthful but irrelevant evidence | Refuse bare retry, interruption, and generic second-thought explanations |

All legs share task, model, parameters, foreground rendering, oracle, and tool
availability. Only evidence condition differs.

S2 evidence cites a disjoint provenance record whose truth is externally
verified but whose source, scope, and entities cannot satisfy or contradict the
task oracle. Its rendered position and canonical token count match S1 within
`±5` tokens. A machine gate checks disjoint references and entity keys; a cold
fixture reviewer checks semantic irrelevance before hashes are exposed to the
engine. A placebo that accidentally answers the task burns the source fixture.

Mint authority requires, on held-out source rows:

- world-scored `S1 - S0 >= 0.25` with the precommitted confidence rule excluding
  zero;
- world-scored `S1 - S2 >= 0.25` with the same rule;
- `S1` pass rate at least `0.80`;
- relevant evidence within the §10 per-invocation ceiling;
- source provenance still live at mint time.

A bare retry leg and a structural-ablation mint leg are excluded. S2 prices
interruption; held-out target transfer tests whether the structural story was
right. Minting must not prove transfer by authoring it into the source gate.

## 8. Frozen target suites and lanes

### 8.1 Static-suite rule

During every scored transfer or cost suite:

- the one disposition remains `experimental_probationary` and otherwise frozen;
- the cost ceiling is per invocation, never cumulative;
- maturation, suspension, retirement, and cumulative metabolic budgets do not
  run;
- provenance revisions do not interleave with target strata;
- every lane begins from the same append-only lineage and warrant rows;
- only the declared treatment path differs.

Living lifecycle dynamics are outside v0. Dedicated provenance-health suites in
§11 start from separately pinned lineage states.

### 8.2 Lane board

| Lane | Treatment | Cheap explanation priced |
| --- | --- | --- |
| `B_inactive` | Same lineage and disposition; control path forcibly inactive and ledgered | Checking helps at all |
| `C_controlled_check` | Frozen trigger; relevant check executes on matching tasks; evidence enters before action | Candidate treatment |
| `P_placebo` | Same trigger, placement, and evidence shape; truthful irrelevant evidence | Interruption or generic hesitation |
| `A_always_check` | Same named check runs on every task; resident selectivity unused | Paranoia may be cheaper or better |
| `G_generic_caution` | No scar-derived influence; frozen generic instruction; same tools | Engine-native selectivity or prompting suffices |
| `O_offer_projection` | Same trigger offers a frozen prose projection of the disposition through the ordinary offer boundary; same tools | Advice suffices; action-boundary controller is ceremony |

The append-only scar remains in lineage across lanes. “No scar-derived
influence” means the lane receives no treatment from it; it does not permit
deleting history.

Target placebo evidence follows the same disjoint-reference, entity-key,
placement, and `±5` canonical-token gate as source S2. Every task, including the
irrelevant stratum, supplies syntactically valid inputs to the named check so
`A_always_check` executes the same action rather than a cheaper substitute.

### 8.3 Frozen generic caution

Exact text, whose UTF-8 hash is recorded at Part I seal:

> Before committing, use the available provenance tool when the evidentiary
> basis or scope of a claim is unclear.

It may not name predicate fields, template ids, the disposition, nomination
language, or the check id.

### 8.4 Offer projection

The projection is a closed template populated only from the authorized
disposition instance:

> Before committing on a cited-source assertion without a direct observation
> boundary, verify that the cited source's scope covers the decision scope.

It contains no fetched provenance, scope verdict, source-domain wording, model
nomination, or outcome label. It is offered only when the same frozen trigger
used by `C_controlled_check` fires.

### 8.5 Target strata

| Stratum | Trigger | Check result | Required behavior |
| --- | --- | --- | --- |
| `match_mismatch` | fires | `scope_matches=false` | Do not commit the unsupported source-backed result |
| `match_commit` | fires | `scope_matches=true` | Commit the supported source-backed result; habitual deferral loses |
| `irrelevant` | does not fire | not run | Preserve baseline outcome and pay no check |

Irrelevant tasks are surface-similar to matching tasks. Matching tasks are
surface-dissimilar across topic, wording, source identity, and domain. Trigger
features—not semantic similarity—define the relation.

Every irrelevant task retains `source_reference_present = true` and
`decision_scope_present = true`, so `A_always_check` can execute the identical
check. C remains silent because at least one trigger-only semantic conjunct is
false. The canonical irrelevant shape sets
`observation_boundary_present = true`; an allowed variant may instead set
`assertion_basis_kind != cited_source`. No content-free routing tag may be added.

## 9. Typed verdict board

No blended utility score may average a wound away. Each row computes separately;
all required rows must clear.

### 9.1 Family-validity gates

- extractor output is unchanged when oracle/outcome fields are removed;
- predicate, extractor, check, prompts, and hashes match the precommit;
- `match_mismatch` and `match_commit` counts are equal;
- firing alone predicts neither target action above `0.50` in the balanced
  experimental family;
- false fires and missed fires are exactly zero at the deterministic controller
  layer;
- every irrelevant fixture retains both check inputs while at least one of
  `assertion_basis_kind == cited_source` or
  `observation_boundary_present == false` is false;
- check completion, evidence entry, model action, and commitment are correctly
  ordered;
- no fixture contains source-domain wording or nomination-prose leakage.

Failure refuses the family before behavioral scoring.

### 9.2 Conditional quality gates

1. **Relevant benefit:** on `match_mismatch`, `C - B >= 0.25`, confidence interval
   excludes zero, and C pass rate is at least `0.80`.
2. **Content attribution:** on `match_mismatch`, `C - P >= 0.25` and its interval
   excludes zero.
3. **Match-and-commit loses-cell:** on `match_commit`, C pass rate is at least
   `0.80` and is non-inferior to B by margin `0.10`. A controller that learns
   “fired means defer” loses.
4. **Irrelevant silence:** on `irrelevant`, C is non-inferior to B by margin
   `0.10`, with zero controller-layer check invocations.
5. **Always-check quality:** C is non-inferior to A by margin `0.10` within each
   trigger-matching stratum. Cost is decided separately.

Quality gates are stratum-conditional. Prevalence weighting may never rescue
one. Unless §9.3 sets the stricter OR-gate confidence, non-inferiority means the
`95%` Newcombe lower bound for `quality(C) - quality(L)` is **greater than or
equal to** `-0.10`.

### 9.3 Boundary-necessity gates

For each comparator `L in {G_generic_caution, O_offer_projection}`, C clears only
one of these precommitted alternatives:

- **quality win:** `quality(C) - quality(L) >= 0.25`, interval excludes zero, and
  C remains inside the per-added-correct-outcome cost ceiling; or
- **efficiency win at matched quality:** C is non-inferior by `0.10` and uses at
  least `10%` fewer mean deterministic decision tokens, with the cost interval
  excluding zero.

Before either alternative may clear, C must also be non-inferior to L by `0.10`
on `match_commit` and `irrelevant`. The quality-superiority alternative is
computed on `match_mismatch`; population-weighted cost is computed only under
§12. A gain on unsupported-source tasks may not purchase habitual deferral or
irrelevant-task degradation.

If L matches or beats C's quality/cost trade, the resident controller is
ceremony and the candidate loses. Actual tool calls are attribution rows, never
the verdict. Because this is an OR gate, each alternative uses a `97.5%`
confidence interval (Bonferroni within comparator). All other required gates are
an intersection-union claim—every gate must pass—so they retain `95%` intervals
without averaging or a favorable-subset correction.

The decision-bearing alternative for each comparator is pinned by the §10.4
plan before held-out contact, selected on precision/N alone — never on
projected effect clearance. Only a pinned decision-bearing alternative can
satisfy this OR gate; a non-bearing alternative's lanes may be reported
descriptively but cannot satisfy the gate or rescue the verdict, and held-out
outcomes cannot promote it. If no alternative is plannable, admission refuses.

### 9.4 Always-check and population cost

Conditional quality is frozen by §9.2. Only deterministic cost may be reweighted
over a population region pinned before held-out contact.

The manifest declares a finite convex region `P = conv(v_1, ..., v_k)` on the
three-stratum prevalence simplex and a strictly positive lower bound
`p_irrelevant >= p_min > 0`. A region whose closure reaches
`p_irrelevant = 0` is refused: at that face C and A run the same check on every
task, so the selective-cost claim is structurally undecidable.

For each stratum `s`, the scorer computes
`d_s = mean_cost(A, s) - mean_cost(C, s)` and a simultaneous `95%` lower bound
`L_s`. The three `L_s` values use two-sided Welch intervals with Bonferroni
coverage `1 - 0.05/3`; by the union bound they form one simultaneous family.
For any prevalence vector `p`:

```text
estimated_saving(p) = sum_s p_s * d_s
lower_saving(p)     = sum_s p_s * L_s
```

Both quantities are linear, so checking every declared vertex is sufficient for
the whole convex region. The always-check verdict clears only if, at every
vertex, C is at least `10%` cheaper than A in point estimate and
`lower_saving(v_i) > 0`. The §10.4 planner uses this same simultaneous-bound
function and the population manifest's vertices.

If `response_curve_only = true`, the scorer reports the curve but emits
`typed_null(population_cost_unlicensed)`. It cannot emit `licensed` or silently
drop the always-check leg from the §0.2 claim.

### 9.5 Possible computed outcomes

- `licensed` — every required typed verdict clears within one frozen envelope;
- `typed_null` — the mechanism engages but one benefit comparison does not
  clear, with no integrity failure;
- `typed_null(population_cost_unlicensed)` — conditional cells may clear but no
  license-bearing prevalence region was precommitted;
- `loss` — a loses-cell or cheaper comparator wins;
- `not_engaged` / `engine_refused` — the engine band never opens;
- `confounded` — integrity, oracle, detectability, or fork-identity gate fails.

No human reading of answers may overwrite these outcomes.

## 10. Cost, sampling, and detectability pins

### 10.1 Deterministic cost

Primary decision cost counts each component read, without counting a controller
output merely because the same bytes later appear in the model prompt:

```text
decision_tokens = model_prompt_tokens
                + model_completion_tokens
                + controller_source_read_tokens
```

`controller_source_read_tokens` is the canonical-token count of provenance read
by the external controller. Evidence rendered to the model is already inside
`model_prompt_tokens`; it is not added a second time.

`governance_steps` is reported separately and breaks token-cost ties only.
Latency is diagnostic, never a verdict. Experiment-only calls and post-answer
ablations are reported but not charged to the answering branch.

Hard v0 ceilings:

- at most one external check invocation per task;
- at most `512` controller source-read tokens per task;
- at most `256` external-check output tokens;
- at most `2` controller `governance_steps` per task;
- at most `1024` incremental decision tokens per additional world-correct
  outcome for a quality-win comparison.

Exceeding a ceiling is a loss, not a tunable warning.

### 10.2 Sampling contract

- the inferential N is the number of **distinct fixture identities**, one model
  invocation per fixture × lane × engine branch; repeated calls to one fixture
  may not inflate N;
- every lane in a stratum receives the same fixture identities in canonical
  order; model calls remain independent because seed control is unavailable and
  is disclosed;
- calibration pilot `K = 5` distinct fixture identities per stratum × lane ×
  engine branch;
- temperature `0.5` with all other decoding parameters frozen;
- if exact answer and route hashes collapse to one realization within a branch,
  exactly one diagnostic pass over the same calibration identities at
  temperature `0.7`, declared in advance;
- continued collapse produces `point_mode_diagnostic`, never a behavioral
  mechanism license;
- `n_max = 128` strict per stratum × lane × engine branch;
- the target N is allocated to N distinct held-out fixtures; source mint N is
  likewise N distinct held-out source fixtures;
- the two trigger-matching target strata use the same N, chosen as the maximum
  admitted requirement across their comparisons, so family balance is not
  broken by variance;
- no pooling across engines, strata, lanes, fixture identities, or temperatures;
- the total projected suite budget is a separate hard pre-build disclosure and
  may refuse Part II even when every branch fits 128.

`n_max = 128` is a bounded feasibility ceiling, not a promise of power in
general. It was set from the §18 planner enumeration: with the `0.10`
non-inferiority half-width, the lowest coherent healthy-engine corner implied
by the §6 band (equal `0.80` pass rates) first becomes decidable near
`N = 124`; the v0.1 ceiling of 24 admitted no coherent configuration at all.
Worse variance or rate configurations may still refuse, the total projected
budget may still refuse Part II, no contrast-specific statistical standard
exists, and the ceiling may not be raised after calibration. No pooling,
higher N, or weaker margin may rescue the family after calibration.

### 10.3 Minimally important effects

These are pinned from the claim, not learned from calibration:

```text
quality superiority margin                 = 0.25 absolute pass rate
quality superiority CI target half-width   = 0.20
quality non-inferiority margin             = 0.10 absolute pass rate
quality non-inferiority CI target half-width = 0.10
cost efficiency margin                     = 10% mean decision tokens
cost efficiency CI target half-width       = 5% of comparator mean
population always-check margin             = 10% mean decision tokens
population cost CI target half-width       = 5% of comparator weighted mean,
                                             at every declared vertex
```

Calibration may estimate variance. It may not lower the superiority margin,
widen the non-inferiority margin, enlarge a cost ceiling, or relax a loses-cell.
The resulting claim remains bounded to the hashed authored fixture population;
distinct fixtures prevent draw replication from pretending to be population
breadth, but they do not make the authored family representative of the world.

### 10.4 N-rule and refusal

For each planned contrast, the calibration scorer enumerates candidate equal N
from `2` through `128` and invokes the **same interval function, confidence level,
and contrast-specific h used by the score-time verdict**:

- binary superiority and non-inferiority use Wilson component intervals and the
  shared Newcombe difference function at the gate's actual confidence level;
- scalar cost uses the shared Welch function with N-dependent
  Welch-Satterthwaite degrees of freedom at the gate's actual confidence level;
- §9.3 OR alternatives use their Bonferroni `97.5%` confidence;
- population-weighted cost uses §9.4's simultaneous stratum bounds at every
  declared vertex, admitted on the §10.3 population precision pin alone; the
  `10%` saving margin and positive lower bound are calibration diagnostics and
  held-out verdict conditions.

The plan honors the §5.2 population intent. Under a declared region, the
complete population board participates in the one pre-contact plan. Under
`response_curve_only`, the planner still sizes every conditional quality gate
and every boundary-necessity quality alternative required for honest
response-curve reporting; it omits the license-bearing population-cost leaves
and the population-dependent efficiency alternatives, and the envelope can
never emit `licensed`. A packet with no declared population intent is not a
valid experiment packet and does not open the band.

`n_required` is the smallest enumerated N at which the shared score-time
function meets the contrast's target half-width. Calibration estimates the
sampling precision implied by the observed calibration rates and cost
dispersion — binary interval width necessarily changes with the observed rate,
so the planner is not point-estimate-free — but no projected difference,
margin clearance, positivity clearance, or apparent arm win may decide
admission. Three layers stay distinct: **admission** is precision under the
frozen interval targets; **projected margin/verdict clearance** at pilot point
estimates is a recorded diagnostic, never license-bearing; the **held-out
suites** are the only place the mechanism's effect clears or fails. No
closed-form z approximation may decide admission. This also prevents a
zero-variance `K = 5` binary packet from claiming `n_required = 0`:
Wilson/Newcombe width remains nonzero at an observed boundary. The shared
functions and enumeration must be unit-tested before calibration contact.

If any required contrast has `n_required > 128`, the family is
`confounded(ci_target_unmet)` and Part II fixture authoring is refused. The lab
may publish a versioned redesign; it may not increase N, drop the difficult
lane, or reinterpret the pilot as evidence.

If the one held-out run produces an interval wider than the pinned target despite
calibration admission, the affected comparison is
`confounded(observed_ci_target_unmet)`. No extra draw may rescue it; the mismatch
between analog and held-out variance is itself preserved.

### 10.5 Stop rule

Calibration stops after the declared `K = 5` packet, plus the single allowed
temperature-0.7 collapse probe when applicable. A target suite runs the
calibration-derived N once. No optional stopping, favorable-engine substitution,
post-hoc fixture rotation, or additional draw is permitted.

## 11. Provenance-health suites

Provenance-health behavior is tested separately from static transfer suites.
Each suite starts from a pinned lineage snapshot and applies exactly one typed
revision before cold reconstruction.

Required cells:

| Revision scope | Expected authorization behavior | Utility reporting |
| --- | --- | --- |
| `source_provenance` applicable to warrant | dependent instance suspended before trigger | report target quality/cost separately |
| `causal_derivation` invalidated | dependent instance suspended | report separately |
| `check_contract` replaced incompatibly | instance suspended pending new license | report separately |
| `resident_instance` only | named instance suspended; no global retirement | report separately |
| unrelated revision | disposition remains eligible | governance should lose if over-broad suspension occurs |

Cold replay must reach the same authorization state as uninterrupted
materialization. A useful but unauthorized stale check cannot remain active; a
quality loss caused by suspension remains a utility loss and may expose an
over-broad warrant rule.

## 12. Prevalence and break-even reporting

Experimental sampling and deployment prevalence are different objects.

The target suite samples enough independent fixtures in each stratum to score
conditional gates. It does not claim that its authored stratum ratio represents
the world.

The population choice is made before calibration contact: the §5.2 calibration
manifest declares exactly one of the convex prevalence region required by §9.4
or `response_curve_only = true`, over:

```text
p_match_mismatch + p_match_commit + p_irrelevant = 1
```

The later population manifest must match that declared choice byte-for-byte
under canonical serialization (key order carries no meaning) apart from its
own identity and hash envelope; it may not choose or adjust vertices after
seeing calibration status, variance, required N, or projected budget.
`response_curve_only` permanently selects the typed non-license path for the
frozen experiment envelope: the eventual outcome can never be `licensed`.

The scorer may reweight only deterministic cost:

```text
E[cost | lane, p] = sum_s p_s * mean_cost(lane, stratum=s)
```

It reports C-vs-A, C-vs-G, and C-vs-O break-even surfaces over the declared
region. §9.4 supplies the license-bearing simultaneous bound for C-vs-A; §9.3
efficiency alternatives use the same construction with their named comparator.
Family validity, conditional quality, silence, false fires, missed fires, and
content-attribution verdicts are never reweighted. The license applies only
where every conditional gate and every required population-cost margin holds.

If suite order, state change, cumulative budgets, or any other interaction makes
stratum outcomes non-exchangeable, reweighting is invalid and the metabolic
claim is refused. v0 prevents that confound by the static-suite rule in §8.1.

## 13. Fork identity, ledger, and replay requirements

Within each fixture fork group, hold constant:

- task and foreground data;
- model id and decoding parameters;
- renderer and prompt template except the declared treatment insertion;
- tool availability and external world snapshot;
- task oracle and scoring code;
- append-only lineage and disposition record;
- fixture and contract hashes.

Minimum external rows:

```text
run_config
contract_precommit
engine_admission_verdict
source_causal_verdict
disposition_minted | disposition_mint_refused
activation_evaluated
external_check_started | external_check_silent
external_check_completed
model_action
task_commit
world_oracle_score
cost_recompute
provenance_revision
authorization_verdict
typed_cell_verdict
```

Every score-time consumer recomputes contract hashes, trigger result, event
order, deterministic costs, warrant health, and cold materialization. Logged
claims are untrusted. Any structural hole, duplicate event identity, mutable
lineage, or score-order inversion fails closed.

## 14. Admission to Part II

After Part I seal, the lab may implement and wire-test only the frozen contract,
controller, lane runner, integrity gates, scorer, and calibration packet. Those
artifacts carry no mechanism evidence.

Held-out Part II fixture authoring and evidence runs may begin only when:

1. Part I receives one bounded cold review and is sealed;
2. the calibration manifest and world-oracle sources are hash-pinned;
3. scorer functions for intervals, N-rule, integrity, and cost replay have wire
   tests;
4. the disjoint calibration packet returns `engine_admitted` with every
   `n_required <= 128`;
5. source, target, and population manifests are hash-pinned;
6. the population manifest byte-matches the §5.2 pre-calibration population
   declaration — a license-bearing region satisfying §9.4, or
   `response_curve_only` as a typed non-license (§12);
7. the total projected target-suite budget is accepted explicitly;
8. no held-out source or target fixture has been exposed to the admitted engine.

Failure at items 1–7 refuses the build. It does not justify weakening the
contract. Item 8 failure burns the affected fixtures; lineage is preserved and a
new held-out family is required.

## 15. Part I review questions

Cold reviewers should endorse or block this protocol, not design Part II in the
review room. The bounded questions are:

1. Does the closed predicate still encode the target outcome?
2. Can source mint authority be produced by retry, interruption, or selection on
   calibration evidence?
3. Does any comparator remain a cheaper explanation for the claimed memory
   effect?
4. Can prevalence weighting or aggregation hide a conditional quality wound?
5. Are the minimally important effects, cost ceilings, N-rule, and `n_max` unit
   coherent before engine contact?
6. Can model narration, fixture authorship, or mutable code cross an authority
   boundary?
7. Does any loses-cell score a nearby inconvenience rather than this mechanism?

One pass per reviewer. Written blocker, concrete repair, then moderator
resolution. Agreement without a blocker should be `pass`.

## 16. Open items that do not permit engine contact

- Select and independently verify the external source/target world corpus.
- Author the disjoint calibration manifest and ignorance probes.
- Implement and wire-test the shared interval, N-rule, trigger-integrity, and
  cost-replay functions.
- Set the total target-suite budget after calibration arithmetic.
- Patch the walking skeleton's mint-after-revision refusal and carrier-owned
  trigger features as sketch hygiene, with no mechanism-license credit.

None of these items may silently amend Parts 0–15 after seal.

## 17. Cold-review fold and seal (2026-07-12)

One bounded pass in `epistemic-frame-check-v0-review` produced three accepted
arithmetic blockers and one rejected trigger block:

1. **Grok, confirmed by Kimi and Fable:** §10.3's target widths could meet their
   pins while remaining unable to clear non-inferiority or minimum-efficiency
   verdicts. Folded as contrast-specific widths; `n_max = 24` retained with the
   refusal-dominated band disclosed.
2. **GLM, extended by Gemini and Fable:** §10.4 planned with one normal critical
   value while score time used stricter OR-gate and small-N Welch intervals.
   Folded by deleting formula-based admission and enumerating N through the
   shared score-time functions.
3. **Fable:** §9.4/§12 made population cost license-bearing without a margin,
   confidence construction, N-plan, or `response_curve_only` outcome. Folded as
   a precommitted convex prevalence region, simultaneous stratum bounds, a 10%
   always-check margin, and typed non-license for response-only reporting.
4. **Kimi, rejected by moderator and independently rejected by Fable:** the
   predicate already contains `assertion_basis_kind` and
   `observation_boundary_present`, which are not check inputs. Adding an
   content-free trigger guard would recreate authored routing. The useful residue
   is folded as an explicit irrelevant-stratum construction and machine gate.

Fable's final pass also clarified §0.3: causal earning authorizes installation;
the target suite does not test earning itself as the source of performance.
No engine contact, fixture evidence, or implementation occurred in the fold.
The moderator retained `n_max = 24`, accepted the disclosed refusal-dominated
band, verified the fold, recorded the canonical file hash in the review thread,
and sealed Part I without a second reviewer round.

## 18. v0.2 bounded arithmetic amendment (2026-07-12)

One bounded fold after the §14 build, in thread `epistemic-frame-check-v0-build`
(builder fable-5, designer gpt-5.6-sol accepting architectural resolution,
moderator dan green-lighting the seal change). No architecture, claim, margin,
confidence level, or interval construction changed.

**Finding 1 (build-time, planner-produced).** Under the v0.1 pins, the
non-inferiority CI target half-width `0.10` at `n_max = 24` (95% Newcombe) was
satisfiable by exactly **2 of the 625** possible count configurations — the
total anti-correlated collapses (`24/24` vs `0/24` and mirror, hw `0.0976`) —
both incoherent with the §6 `S1 >= 0.80` band and with the NI loses-cells'
own construction. The best coherent (equal-arms) floor is hw `0.1380`.
Equal-arms first-feasible N: `35` (p = 1.0), `54` (0.95), `77` (0.90), `124`
(0.80). The v0.1 board therefore computed `confounded(ci_target_unmet)` for
every coherent pilot: the calibration gate could never open.

Three lineage events are kept distinct, none erased: the original design error
(v0.1 sealed an effectively empty coherent admission region while disclosing
it as a "refusal-dominated band"); the builder's initial overstatement
("unreachable for all pilots", derived from the equal-arms floor); and the
planner's own test enumeration producing the two-point-sliver correction
within the hour.

**Amendment.** §6/§10.2/§10.4/§14 enumeration ceiling `24 → 128`; the §10.2
retention paragraph rewritten as a bounded-feasibility disclosure; §10.3 gains
the explicit population-cost precision pin; §10.4 admission language corrected
to the three-layer split (precision admits; projected effect clearance is a
recorded diagnostic, never license-bearing; held-out rows are the only
verdict). The v0.2 canonical file hash is recorded in
`epistemic-frame-check-v0-build`. A cold implementation audit of the
post-amendment artifact precedes any calibration-manifest authoring, fixture
authoring, or engine contact.

## 19. v0.3 process amendment (2026-07-12)

One bounded fold from the cold implementation audit of the v0.2 artifact
(auditors cursor/grok-4.5 and cursor/composer-2.5, both endorsing the §14
machinery; architect gpt-5.6-sol accepting their shared blocker with a
stronger remedy; moderator dan approving). No claim, margin, confidence
level, interval construction, lane, or architecture changed.

**Audit finding (population-omission seam).** The v0.2 calibration manifest
allowed the population region to be omitted, and `engine_admitted` computed
without the population board could understate N relative to a later
license-bearing region — a silent under-planning seam, and one calibration
outcomes could exploit by informing the later choice of deployment
population.

**Amendment.** §5.2 makes population intent a mandatory calibration-manifest
field (exactly one of a license-bearing §9.4 region or
`response_curve_only`); §5.3/§12/§14.6 require the later population manifest
to byte-match that pre-calibration choice apart from its own identity
envelope; §10.4 states the plan-scope rule for each intent
(`response_curve_only` still sizes all conditional quality gates and
boundary-necessity quality alternatives, omits license-bearing population
leaves, and can never emit `licensed`); §9.3 makes decision-bearing OR-arm
pinning explicit — arms are selected on precision/N alone before held-out
contact, non-bearing arms cannot satisfy the gate or be promoted by held-out
outcomes, and no plannable arm means refusal. The audit's recommended
per-vertex population diagnostics (reconstructible from typed pilot and
region inputs, never verdicts) land in the same fold. The reviewers' proposal
to let a non-bearing arm clear at score time was explicitly rejected by the
architect as favorable-path selection after outcomes.

The v0.3 canonical file hash is recorded in `epistemic-frame-check-v0-build`.
A bounded auditor closure check limited to these changes precedes any
calibration-manifest authoring, fixture authoring, or engine contact.

**Closure round (same day).** The auditors accepted the population-intent and
diagnostic changes and withheld final closure on one representation defect:
the plan artifact recorded §9.3 preconditions and the selected OR alternative
in one flat id bag, claiming more structure than it encoded. The fold's
correction, per the auditors' prescription: the selected alternative is a
typed record (a stable structural arm id — `quality` | `efficiency` — plus
its member contrast ids), mandatory preconditions live in a separate field
and never inside it, sizing continues to use preconditions plus selected
members, and score-time OR eligibility reads only the typed record. Selection
remains precision/N-only; a projected-clearance diagnostic cannot flip the
pin (test-pinned, including an arm selected while its own clearance
diagnostic fails). Wording corrected in the same touch: an absent population
intent makes the packet invalid (not merely non-license-seeking), and the
§5.2/§12 byte-identity is canonical-serialization equality, in which key
order carries no meaning. The post-closure canonical hash is recorded in
`epistemic-frame-check-v0-build`.
