"""Pinned constants of the sealed Part I — SPEC_EPISTEMIC_FRAME_CHECK_V0.

The single source of pinned truth for the epistemic-frame-check machinery.
Every constant cites the sealed section it transcribes; no module may re-pin
one of these numbers locally. Nothing here is tunable: §10.3 pins are from the
claim, not learned from calibration, and §16 forbids silently amending Parts
0-15 after seal. Changing any value in this file is a spec change and needs a
new sealed Part I.

tests/test_efc_contracts.py re-derives the frozen §8.3/§8.4 texts and the
sealed file hash from notes/SPEC_EPISTEMIC_FRAME_CHECK_V0.md itself, so any
drift between this module and the sealed document fails the wire suite.
"""

from __future__ import annotations

import hashlib

# --- Part I seal (§5.1; canonical hash recorded in substrate thread
# `epistemic-frame-check-v0-review`, verified 2026-07-12) ---------------------
PART_I_SPEC_RELPATH = "notes/SPEC_EPISTEMIC_FRAME_CHECK_V0.md"
PART_I_SPEC_SHA256 = "736d46cf9c22029c19834514a02ba1f0a756ca5ead8805ae4263732dc757c5d8"

# --- §0.2 / §2.2 identities --------------------------------------------------
MECHANISM_ID = "epistemic_frame_check"
MECHANISM_VERSION = "v0"
CHECK_ID = "scope_provenance_check_v0"

# --- §10.3 minimally important effects (pinned from the claim) ---------------
QUALITY_SUPERIORITY_MARGIN = 0.25          # absolute pass rate
QUALITY_SUPERIORITY_CI_HALF_WIDTH = 0.20
QUALITY_NONINFERIORITY_MARGIN = 0.10       # absolute pass rate
QUALITY_NONINFERIORITY_CI_HALF_WIDTH = 0.10
COST_EFFICIENCY_MARGIN = 0.10              # fraction of comparator mean tokens
COST_EFFICIENCY_CI_HALF_WIDTH = 0.05       # fraction of comparator mean tokens
POPULATION_ALWAYS_CHECK_MARGIN = 0.10      # fraction of A's mean tokens (§9.4)

# --- §9.2 / §9.3 confidence construction -------------------------------------
CONFIDENCE_STANDARD = 0.95      # intersection-union gates keep 95% (§9.3)
CONFIDENCE_OR_GATE = 0.975      # Bonferroni within comparator for §9.3 OR arms
POPULATION_FAMILY_ALPHA = 0.05  # §9.4 simultaneous stratum family
POPULATION_STRATUM_COUNT = 3    # three-stratum prevalence simplex (§9.4/§12)

# --- §6 engine-admission calibration bands (point estimates, diagnostics) ----
S0_MAX_PASS_RATE = 0.50
S1_MIN_PASS_RATE = 0.80
S1_S0_MIN_DIFF = 0.25
S1_S2_MIN_DIFF = 0.25

# --- §7 held-out source mint gates (world-scored, precommitted CI rule) ------
SOURCE_S1_S0_MIN_DIFF = 0.25
SOURCE_S1_S2_MIN_DIFF = 0.25
SOURCE_S1_MIN_PASS_RATE = 0.80

# --- §9.2 conditional quality gates ------------------------------------------
RELEVANT_BENEFIT_MIN_DIFF = 0.25   # C - B on match_mismatch
CONTENT_ATTRIBUTION_MIN_DIFF = 0.25  # C - P on match_mismatch
C_MIN_PASS_RATE = 0.80

# --- §10.1 hard deterministic cost ceilings (exceeding = loss) ----------------
MAX_CHECK_INVOCATIONS_PER_TASK = 1
MAX_CONTROLLER_SOURCE_READ_TOKENS = 512
MAX_EXTERNAL_CHECK_OUTPUT_TOKENS = 256
MAX_GOVERNANCE_STEPS_PER_TASK = 2
MAX_INCREMENTAL_TOKENS_PER_ADDED_CORRECT = 1024

# --- §10.2 sampling contract --------------------------------------------------
CALIBRATION_K = 5                      # distinct fixtures per stratum x lane x branch
CALIBRATION_TEMPERATURE = 0.5
COLLAPSE_DIAGNOSTIC_TEMPERATURE = 0.7  # single declared collapse probe
N_ENUM_MIN = 2                         # §10.4 enumeration lower edge
N_MAX = 24                             # strict, an admission filter not a promise

# --- §10.5 stop rule (as a pinned identifier the manifest must carry) ---------
STOP_RULE_ID = "k5_packet_plus_single_t07_collapse_probe"

# --- §7 / §8.2 placebo construction -------------------------------------------
PLACEBO_TOKEN_TOLERANCE = 5  # S1/S2 canonical token count match within +/- 5

# --- §8.2 lane board / §7 source legs / §8.5 target strata --------------------
LANES = ("B_inactive", "C_controlled_check", "P_placebo", "A_always_check",
         "G_generic_caution", "O_offer_projection")
SOURCE_LEGS = ("S0_no_check", "S1_relevant_check", "S2_placebo")
STRATA = ("match_mismatch", "match_commit", "irrelevant")
TRIGGER_MATCHING_STRATA = ("match_mismatch", "match_commit")

# --- §8.3 frozen generic caution (exact text; UTF-8 hash recorded at seal) ----
GENERIC_CAUTION_TEXT = ("Before committing, use the available provenance tool "
                        "when the evidentiary basis or scope of a claim is "
                        "unclear.")
GENERIC_CAUTION_SHA256 = ("b25af70799fad818b054781a56851504369fe35d8e1cb0534ed8"
                          "ada29b46e877")

# --- §8.4 offer-projection closed template -------------------------------------
OFFER_PROJECTION_TEXT = ("Before committing on a cited-source assertion without "
                         "a direct observation boundary, verify that the cited "
                         "source's scope covers the decision scope.")
OFFER_PROJECTION_SHA256 = ("e62ae334735ece7e87f853abc48f880c1e3978f0fe482083"
                           "88bc95e24704642b")

# --- §3.1 carrier / §3.4 typed revision vocabulary ----------------------------
CARRIER_STATUS_EXPERIMENTAL = "experimental_probationary"
REVISION_SCOPES = ("source_provenance", "causal_derivation", "check_contract",
                   "resident_instance")

# --- §5.3 / §9.5 / §10.4 computed verdict vocabulary ---------------------------
ENGINE_ADMISSION_VERDICTS = ("engine_admitted", "engine_refused",
                             "point_mode_diagnostic", "not_engaged",
                             "confounded(ci_target_unmet)")
FAMILY_OUTCOMES = ("licensed", "typed_null",
                   "typed_null(population_cost_unlicensed)", "loss",
                   "not_engaged", "engine_refused", "confounded")

# --- §13 minimum external ledger row vocabulary --------------------------------
EVENT_TYPES = frozenset({
    "run_config",
    "contract_precommit",
    "engine_admission_verdict",
    "source_causal_verdict",
    "disposition_minted",
    "disposition_mint_refused",
    "activation_evaluated",
    "external_check_started",
    "external_check_silent",
    "external_check_completed",
    "model_action",
    "task_commit",
    "world_oracle_score",
    "cost_recompute",
    "provenance_revision",
    "authorization_verdict",
    "typed_cell_verdict",
    # §3.3: model nomination is ledgered as an untrusted audit claim only
    "untrusted_nomination",
})


def sha256_utf8(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
