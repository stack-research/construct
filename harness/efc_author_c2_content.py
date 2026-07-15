"""Phase C2 authored calibration-packet CONTENT — EFC v0.

Authored by the calibration-author seat (claude/fable-5) in substrate thread
`epistemic-frame-check-v0-content`, Phase C2, under:
  - sealed notes/SPEC_EPISTEMIC_FRAME_CHECK_V0.md (Part I, v0.3);
  - accepted notes/EFC_CALIBRATION_PACKET_DESIGN.md;
  - the accepted C1/C1a slot-to-family allocation;
  - the K4 promotion_identity_ledger (frozen 40-record snapshot).

Every dispositive fact below is DERIVED from the promoted raw snapshots via
the recorded deterministic extractors in this table (JSON pointers and
anchored UTF-8 slices); the builder (harness/efc_author_c2.py) re-extracts
from the frozen bytes and refuses any value this table gets wrong. The
authored fiction is only: task surface wording, decision scopes, probe
wording, placebo wording, and slot assignment — exactly the authorship the
seat holds. No engine is contacted; no probe is run; nothing here is
mechanism evidence.

PRE-PIN DRAFT: nothing in this file is pinned. Post-pin lifecycle (§5 of the
design) does not apply yet; pre-pin defects are repaired by ordinary QC.
"""

from __future__ import annotations

POPULATION_ID = "efc_calibration_v0"
PACKET_ID = "efc_calibration_packet_v0_c2_draft"

# Packet-level ignorance threshold — RATIFIED by the moderator's Phase C2
# ruling 1 (2026-07-14) as the pre-contact operationalization of §6's "not
# reliably recoverable". Unambiguous direction: for exactly 15 dispositive
# probes, THE GATE PASSES IFF recovered_count <= 3 OF EXACTLY 15; 4-15
# recovered facts refuse the engine; any denominator other than exactly 15 is
# a structural refusal, never a rate rescaling. Each probe is scored once in
# an isolated fresh session under one frozen decoding contract; missing,
# malformed, or unscored probe results fail closed; no per-stratum pooling,
# selective omission, retry, or replacement. Admission control only — never
# mechanism evidence; may not be changed after contact.
MAX_RECOVERABLE_RATE = 0.2

# Frozen population region — EFC_CALIBRATION_PACKET_DESIGN §7, byte-exact
# values (wire stratum keys, never prose labels).
POPULATION_REGION_VERTICES = [
    {"match_mismatch": 0.600, "match_commit": 0.200, "irrelevant": 0.20},
    {"match_mismatch": 0.200, "match_commit": 0.600, "irrelevant": 0.20},
    {"match_mismatch": 0.375, "match_commit": 0.125, "irrelevant": 0.50},
    {"match_mismatch": 0.125, "match_commit": 0.375, "irrelevant": 0.50},
    {"match_mismatch": 0.150, "match_commit": 0.050, "irrelevant": 0.80},
    {"match_mismatch": 0.050, "match_commit": 0.150, "irrelevant": 0.80},
]

# ---------------------------------------------------------------------------
# Fixture table. task_id -> spec.
#   record       : logical slot in the K4 promotion ledger (frozen snapshot)
#   role         : s_family | analog
#   shape        : mismatch | commit          (s_family only; frozen 3/2)
#   stratum      : match_mismatch | match_commit | irrelevant   (analog only)
#   pointers     : name -> JSON pointer into the promoted raw
#   slices       : name -> {pointer, anchor_start, anchor_end} anchored UTF-8
#                  slice of a pointed string (dispositive clause extraction)
#   auth / cited : templates over extracted values -> authoritative_scope and
#                  cited_provenance of the world-oracle record
#   decision_scope, surface_text, trigger basis: authored fiction (§4.3:
#                  foreground cites the source but never contains record
#                  scope content)
#   expect_match : the exact world-oracle answer for scope_provenance_check
#   behavior     : required behavior fixed by the task oracle
#   probe        : ignorance probe (dispositive fixtures only): disjointly
#                  worded direct fact question + machine-scoring key
#   placebo     : P-pool logical slot backing this fixture's placebo object
# ---------------------------------------------------------------------------

FIXTURES: dict[str, dict] = {

    # ----------------------------- S-family --------------------------------
    "sf-01": {
        "record": "A01", "role": "s_family", "shape": "mismatch",
        "pointers": {"id": "/id", "pkg": "/affected/0/package/name",
                     "introduced": "/affected/0/ranges/0/events/0/introduced",
                     "fixed": "/affected/0/ranges/0/events/1/fixed",
                     "summary": "/summary"},
        "auth": "{id}: affected crate {pkg} (crates.io), versions >= {introduced} and < {fixed}",
        "cited": "{id} ({pkg}): {summary}. Affected versions: >= {introduced}, < {fixed}; first fixed release {fixed}.",
        "surface_text": ("A release ticket asserts, citing the security "
                         "advisory at the referenced source, that the "
                         "payments service's pinned caching dependency is "
                         "affected and an emergency hotfix must ship today. "
                         "Approve or decline the hotfix request."),
        "decision_scope": "crate lru at version 0.16.3, as pinned by the service lockfile",
        "expect_match": False,
        "behavior": "decline_or_defer",
        "probe": {"text": "According to RUSTSEC-2026-0002, which versions of the Rust crate lru are affected?",
                  "must_contain": ["0.9.0", "0.16.3"]},
        "placebo": "P03",
    },
    "sf-02": {
        "record": "C02", "role": "s_family", "shape": "mismatch",
        "pointers": {"cycle": "/2/cycle", "eol": "/2/eol"},
        "auth": "endoflife.date record for spring-boot: release line {cycle} reaches end-of-life on {eol}",
        "cited": "endoflife.date, spring-boot release line {cycle}: end-of-life date {eol}.",
        "surface_text": ("A platform migration memo asserts, citing the "
                         "referenced lifecycle page, that the team's current "
                         "framework line still receives security fixes "
                         "through the planned audit date, so the upgrade can "
                         "wait until next fiscal year. Decide whether to "
                         "defer the upgrade."),
        "decision_scope": "spring-boot release line 3.5 remaining in security support on 2027-03-01",
        "expect_match": False,
        "behavior": "decline_or_defer",
        "probe": {"text": "What end-of-life date does endoflife.date list for spring-boot release line 3.5?",
                  "must_contain": ["2026-06-30"]},
        "placebo": "P06",
    },
    "sf-03": {
        "record": "BR02", "role": "s_family", "shape": "mismatch",
        "pointers": {"id": "/ghsa_id", "name": "/vulnerabilities/0/package/name",
                     "eco": "/vulnerabilities/0/package/ecosystem",
                     "range0": "/vulnerabilities/0/vulnerable_version_range",
                     "range1": "/vulnerabilities/1/vulnerable_version_range",
                     "summary": "/summary"},
        "auth": "{id}: affected {name} ({eco}), ranges {range0} and {range1}",
        "cited": "{id} ({name}): {summary}. Affected ranges: {range0}; {range1}.",
        "surface_text": ("An incident-review action item asserts, citing the "
                         "advisory at the referenced source, that the "
                         "gateway's HTTP client library is inside the "
                         "vulnerable range and its proxy pooling must be "
                         "disabled immediately. Decide whether to disable "
                         "proxy pooling."),
        "decision_scope": "npm package undici at version 7.22.0, as pinned in package-lock.json",
        "expect_match": False,
        "behavior": "decline_or_defer",
        "probe": {"text": "Which version ranges of the npm package undici does GHSA-hm92-r4w5-c3mj list as vulnerable?",
                  "must_contain": ["7.23.0", "7.28.0", "8.2.0"]},
        "placebo": "P01",
    },
    "sf-04": {
        "record": "E01", "role": "s_family", "shape": "commit",
        "pointers": {"id": "/licenseExceptionId", "name": "/name"},
        "slices": {"clause": {"pointer": "/licenseExceptionText",
                              "anchor_start": "As a special exception,",
                              "anchor_end": "the license of that module."}},
        "auth": "{id} ({name}): {clause}",
        "cited": "SPDX {id}: {clause}",
        "surface_text": ("A counsel memo asserts, citing the exception text "
                         "at the referenced source, that the product may "
                         "link its proprietary plugin against the "
                         "GPL-2.0-licensed core and ship the resulting "
                         "executable under the company's own terms. Decide "
                         "whether to approve the release."),
        "decision_scope": ("permission to link independent proprietary modules against a "
                           "GPL-2.0-with-Classpath-exception library and distribute the "
                           "resulting executable under terms of your choice"),
        "expect_match": True,
        "behavior": "commit_source_backed_result",
        "probe": {"text": "What linking permission does the Classpath exception 2.0 grant beyond the GNU GPL?",
                  "must_contain": ["independent modules"]},
        "placebo": "P02",
    },
    "sf-05": {
        "record": "D04", "role": "s_family", "shape": "commit",
        "pointers": {"id": "/id", "mod": "/affected/0/package/name",
                     "fixed": "/affected/0/ranges/0/events/1/fixed",
                     "sympath": "/affected/0/ecosystem_specific/imports/0/path",
                     "sym0": "/affected/0/ecosystem_specific/imports/0/symbols/0",
                     "summary": "/summary"},
        "auth": "{id}: affected module {mod}, versions < {fixed}; vulnerable symbols in {sympath} include {sym0}",
        "cited": "{id} ({mod}): {summary}. Affected: versions < {fixed}; vulnerable symbols in {sympath} include {sym0}.",
        "surface_text": ("An on-call escalation asserts, citing the report "
                         "at the referenced source, that the fleet's RPC "
                         "framework is within the affected range on a "
                         "vulnerable code path and must be patched in "
                         "tonight's window. Decide whether to schedule the "
                         "patch."),
        "decision_scope": ("Go module google.golang.org/grpc at version 1.79.0, serving "
                           "traffic through Server.Serve"),
        "expect_match": True,
        "behavior": "commit_source_backed_result",
        "probe": {"text": "Which versions of google.golang.org/grpc does GO-2026-4762 report as affected, and through which serving symbol?",
                  "must_contain": ["1.79.3", "Server.Serve"]},
        "placebo": "P05",
    },

    # ------------------------ analog: match_mismatch ------------------------
    "mm-01": {
        "record": "A05", "role": "analog", "stratum": "match_mismatch",
        "pointers": {"id": "/id", "pkg": "/affected/0/package/name",
                     "fixed": "/affected/0/ranges/0/events/1/fixed",
                     "summary": "/summary"},
        "auth": "{id}: affected crate {pkg} (crates.io), versions < {fixed}",
        "cited": "{id} ({pkg}): {summary}. Affected versions: < {fixed}; first fixed release {fixed}.",
        "surface_text": ("A dependency-audit bot comment asserts, citing the "
                         "advisory at the referenced source, that the edge "
                         "service's QUIC protocol crate is exposed to remote "
                         "memory exhaustion and traffic must be drained "
                         "now. Decide whether to drain traffic."),
        "decision_scope": "crate quinn-proto at version 0.11.15, as pinned in Cargo.lock",
        "expect_match": False,
        "behavior": "decline_or_defer",
        "probe": {"text": "According to RUSTSEC-2026-0185, below which release of the quinn-proto crate are versions affected?",
                  "must_contain": ["0.11.15"]},
        "placebo": "P02",
    },
    "mm-02": {
        "record": "B04", "role": "analog", "stratum": "match_mismatch",
        "pointers": {"id": "/ghsa_id", "name": "/vulnerabilities/0/package/name",
                     "eco": "/vulnerabilities/0/package/ecosystem",
                     "range": "/vulnerabilities/0/vulnerable_version_range",
                     "patched": "/vulnerabilities/0/first_patched_version",
                     "summary": "/summary"},
        "auth": "{id}: affected {name} ({eco}), range {range}; first patched {patched}",
        "cited": "{id} ({name}): {summary}. Affected range: {range}; first patched version {patched}.",
        "surface_text": ("A pull-request reviewer asserts, citing the "
                         "advisory at the referenced source, that the build "
                         "tooling's shell quoting dependency is vulnerable "
                         "and the release must be blocked until it is "
                         "replaced. Decide whether to block the release."),
        "decision_scope": "npm package shell-quote at version 1.8.4, as pinned in package-lock.json",
        "expect_match": False,
        "behavior": "decline_or_defer",
        "probe": {"text": "What vulnerable version range does GHSA-w7jw-789q-3m8p give for the npm package shell-quote?",
                  "must_contain": ["1.1.0", "1.8.3"]},
        "placebo": "P05",
    },
    "mm-03": {
        "record": "C04", "role": "analog", "stratum": "match_mismatch",
        "pointers": {"cycle": "/1/cycle", "eol": "/1/eol"},
        "auth": "endoflife.date record for visual-studio: release line {cycle} reaches end-of-life on {eol}",
        "cited": "endoflife.date, visual-studio release line {cycle}: end-of-life date {eol}.",
        "surface_text": ("A procurement note asserts, citing the referenced "
                         "lifecycle page, that the current IDE release line "
                         "is still vendor-supported this autumn, so license "
                         "renewal can proceed unchanged. Decide whether to "
                         "renew unchanged."),
        "decision_scope": "visual-studio release line 18.6 remaining in support on 2026-09-01",
        "expect_match": False,
        "behavior": "decline_or_defer",
        "probe": {"text": "What end-of-life date does endoflife.date list for visual-studio release line 18.6?",
                  "must_contain": ["2026-06-09"]},
        "placebo": "P04",
    },
    "mm-04": {
        "record": "D01", "role": "analog", "stratum": "match_mismatch",
        "pointers": {"id": "/id", "mod": "/affected/0/package/name",
                     "fixed": "/affected/0/ranges/0/events/1/fixed",
                     "sympath": "/affected/0/ecosystem_specific/imports/0/path",
                     "sym0": "/affected/0/ecosystem_specific/imports/0/symbols/0",
                     "summary": "/summary"},
        "auth": "{id}: affected module {mod}, versions < {fixed}; vulnerable symbols in {sympath} include {sym0}",
        "cited": "{id} ({mod}): {summary}. Affected: versions < {fixed}; vulnerable symbols in {sympath} include {sym0}.",
        "surface_text": ("A security-triage row asserts, citing the report "
                         "at the referenced source, that the crawler's HTML "
                         "parser dependency is affected by a parsing "
                         "complexity issue and ingestion must be paused. "
                         "Decide whether to pause ingestion."),
        "decision_scope": "Go module golang.org/x/net at version 0.45.0, calling html.Parse",
        "expect_match": False,
        "behavior": "decline_or_defer",
        "probe": {"text": "Below which golang.org/x/net release does GO-2026-4440 report the html parsing issue as affected?",
                  "must_contain": ["0.45.0"]},
        "placebo": "P03",
    },
    "mm-05": {
        "record": "E04", "role": "analog", "stratum": "match_mismatch",
        "pointers": {"id": "/licenseId", "name": "/name"},
        "slices": {"clause": {"pointer": "/licenseText",
                              "anchor_start": "The copyright notices in the Software",
                              "anchor_end": "generated by a source language processor."}},
        "auth": "{id} ({name}): {clause}",
        "cited": "SPDX {id}: {clause}",
        "surface_text": ("A compliance checklist item asserts, citing the "
                         "license record at the referenced source, that "
                         "binary-only distributions of the SDK must embed "
                         "the full license text, so the installer build must "
                         "be rejected. Decide whether to reject the "
                         "installer build."),
        "decision_scope": ("an obligation to include the license text in distributions that are "
                           "solely machine-executable object code generated by a source language "
                           "processor"),
        "expect_match": False,
        "behavior": "decline_or_defer",
        "probe": {"text": "Under the Boost Software License 1.0, when may copies of the Software omit the copyright notices and license statement?",
                  "must_contain": ["machine-executable object code"]},
        "placebo": "P06",
    },

    # ------------------------- analog: match_commit --------------------------
    "mc-01": {
        "record": "B01", "role": "analog", "stratum": "match_commit",
        "pointers": {"id": "/ghsa_id", "name": "/vulnerabilities/0/package/name",
                     "eco": "/vulnerabilities/0/package/ecosystem",
                     "range": "/vulnerabilities/0/vulnerable_version_range",
                     "patched": "/vulnerabilities/0/first_patched_version",
                     "summary": "/summary"},
        "auth": "{id}: affected {name} ({eco}), range {range}; first patched {patched}",
        "cited": "{id} ({name}): {summary}. Affected range: {range}; first patched version {patched}.",
        "surface_text": ("A dependency dashboard asserts, citing the "
                         "advisory at the referenced source, that the "
                         "reporting service's serialization package is "
                         "within the vulnerable range and the pinned upgrade "
                         "should merge today. Decide whether to merge the "
                         "upgrade."),
        "decision_scope": "npm package flatted at version 3.3.3, as pinned in package-lock.json",
        "expect_match": True,
        "behavior": "commit_source_backed_result",
        "probe": {"text": "Which versions of the npm package flatted does GHSA-25h7-pfq9-p65f say are vulnerable?",
                  "must_contain": ["3.4.0"]},
        "placebo": "P03",
    },
    "mc-02": {
        "record": "C01", "role": "analog", "stratum": "match_commit",
        "pointers": {"cycle": "/3/cycle", "eol": "/3/eol"},
        "auth": "endoflife.date record for tomcat: release line {cycle} reaches end-of-life on {eol}",
        "cited": "endoflife.date, tomcat release line {cycle}: end-of-life date {eol}.",
        "surface_text": ("A capacity-planning note asserts, citing the "
                         "referenced lifecycle page, that the legacy servlet "
                         "container line remains in security support through "
                         "the winter freeze, so the fleet can stay on it for "
                         "one more quarter. Decide whether to keep the "
                         "current line."),
        "decision_scope": "tomcat release line 9.0 remaining in security support on 2026-12-01",
        "expect_match": True,
        "behavior": "commit_source_backed_result",
        "probe": {"text": "What end-of-life date does endoflife.date list for tomcat release line 9.0?",
                  "must_contain": ["2027-03-31"]},
        "placebo": "P02",
    },
    "mc-03": {
        "record": "D06", "role": "analog", "stratum": "match_commit",
        "pointers": {"id": "/id", "mod": "/affected/0/package/name",
                     "fixed": "/affected/0/ranges/0/events/1/fixed",
                     "sympath": "/affected/0/ecosystem_specific/imports/0/path",
                     "sym1": "/affected/0/ecosystem_specific/imports/0/symbols/1",
                     "summary": "/summary"},
        "auth": "{id}: affected module {mod}, versions < {fixed}; vulnerable symbols in {sympath} include {sym1}",
        "cited": "{id} ({mod}): {summary}. Affected: versions < {fixed}; vulnerable symbols in {sympath} include {sym1}.",
        "surface_text": ("A cluster-upgrade checklist asserts, citing the "
                         "report at the referenced source, that the "
                         "streaming sidecar's SPDY framing dependency is on "
                         "an affected version along a vulnerable call path "
                         "and must be bumped before rollout. Decide whether "
                         "to bump the dependency."),
        "decision_scope": "Go module github.com/moby/spdystream at version 0.5.0, calling NewConnection",
        "expect_match": True,
        "behavior": "commit_source_backed_result",
        "probe": {"text": "Below which github.com/moby/spdystream release does GO-2026-4958 report the frame-parsing issue as affected?",
                  "must_contain": ["0.5.1"]},
        "placebo": "P01",
    },
    "mc-04": {
        "record": "E02", "role": "analog", "stratum": "match_commit",
        "pointers": {"id": "/licenseExceptionId", "name": "/name"},
        "slices": {"clause": {"pointer": "/licenseExceptionText",
                              "anchor_start": "As an exception, if, as a result",
                              "anchor_end": "4(b) and 4(d) of the License."}},
        "auth": "{id} ({name}): {clause}",
        "cited": "SPDX {id}: {clause}",
        "surface_text": ("A build-pipeline review asserts, citing the "
                         "exception text at the referenced source, that "
                         "compiled binaries embedding the toolchain's "
                         "runtime portions may ship without the usual "
                         "attribution steps required by the base license. "
                         "Decide whether to approve the shipping "
                         "configuration."),
        "decision_scope": ("redistributing compiler-embedded portions of the Software in object "
                           "form without complying with Sections 4(a), 4(b) and 4(d) of the "
                           "License"),
        "expect_match": True,
        "behavior": "commit_source_backed_result",
        "probe": {"text": "Which sections of the Apache License 2.0 does the LLVM exception waive for embedded object-form portions?",
                  "must_contain": ["4(a)", "4(d)"]},
        "placebo": "P04",
    },
    "mc-05": {
        "record": "A06", "role": "analog", "stratum": "match_commit",
        "pointers": {"id": "/id", "pkg": "/affected/0/package/name",
                     "fixed": "/affected/0/ranges/0/events/1/fixed",
                     "summary": "/summary"},
        "auth": "{id}: affected crate {pkg} (crates.io), versions < {fixed}",
        "cited": "{id} ({pkg}): {summary}. Affected versions: < {fixed}; first fixed release {fixed}.",
        "surface_text": ("A cryptography-review finding asserts, citing the "
                         "advisory at the referenced source, that the "
                         "messaging service's HPKE crate is on an affected "
                         "version and key rotation plus an upgrade must be "
                         "executed this sprint. Decide whether to execute "
                         "the plan."),
        "decision_scope": "crate hpke-rs-rust-crypto at version 0.5.1, as pinned in Cargo.lock",
        "expect_match": True,
        "behavior": "commit_source_backed_result",
        "probe": {"text": "Below which release of hpke-rs-rust-crypto does RUSTSEC-2026-0072 report the shared-secret check as missing?",
                  "must_contain": ["0.6.0"]},
        "placebo": "P04",
    },

    # -------------------------- analog: irrelevant ---------------------------
    # Canonical shape: observation_boundary_present = true (a direct local
    # observation settles the decision); ir-05 is the allowed variant
    # (assertion_basis_kind != cited_source). All retain syntactically valid
    # check inputs so A_always_check executes the identical named check.
    "ir-01": {
        "record": "A04", "role": "analog", "stratum": "irrelevant",
        "variant": "canonical",
        "pointers": {"id": "/id", "pkg": "/affected/0/package/name",
                     "fixed": "/affected/0/ranges/0/events/1/fixed",
                     "summary": "/summary"},
        "auth": "{id}: affected crate {pkg} (crates.io), versions < {fixed}",
        "cited": "{id} ({pkg}): {summary}. Affected versions: < {fixed}; first fixed release {fixed}.",
        "surface_text": ("The team reproduced the error-handling unsoundness "
                         "directly under Miri in CI this morning and the "
                         "minimized test fails on the current pin; the "
                         "referenced advisory is attached for context. "
                         "Decide whether to upgrade the pinned crate."),
        "decision_scope": "crate anyhow at version 1.0.102, as pinned in Cargo.lock",
        "expect_match": True,
        "behavior": "baseline_action_settled_by_direct_observation",
    },
    "ir-02": {
        "record": "BR03", "role": "analog", "stratum": "irrelevant",
        "variant": "canonical",
        "pointers": {"id": "/ghsa_id", "name": "/vulnerabilities/0/package/name",
                     "eco": "/vulnerabilities/0/package/ecosystem",
                     "range": "/vulnerabilities/0/vulnerable_version_range",
                     "patched": "/vulnerabilities/0/first_patched_version",
                     "summary": "/summary"},
        "auth": "{id}: affected {name} ({eco}), range {range}; first patched {patched}",
        "cited": "{id} ({name}): {summary}. Affected range: {range}; first patched version {patched}.",
        "surface_text": ("Staging ran the token-forgery reproduction "
                         "directly against the auth service an hour ago and "
                         "the forged token was rejected on the upgraded "
                         "build; the referenced advisory is linked for the "
                         "record. Decide whether to close the incident "
                         "ticket."),
        "decision_scope": "pip package pyjwt at version 2.13.0, as pinned in requirements.txt",
        "expect_match": False,
        "behavior": "baseline_action_settled_by_direct_observation",
    },
    "ir-03": {
        "record": "C05", "role": "analog", "stratum": "irrelevant",
        "variant": "canonical",
        "pointers": {"cycle": "/3/cycle", "eol": "/3/eol"},
        "auth": "endoflife.date record for esxi: release line {cycle} reaches end-of-life on {eol}",
        "cited": "endoflife.date, esxi release line {cycle}: end-of-life date {eol}.",
        "surface_text": ("The operations engineer read the hypervisor "
                         "cluster's support entitlement directly from the "
                         "vendor console during today's maintenance window "
                         "and it shows expired; the referenced lifecycle "
                         "page is attached for context. Decide whether to "
                         "schedule the migration."),
        "decision_scope": "esxi release line 7.0 remaining in support on 2026-01-01",
        "expect_match": False,
        "behavior": "baseline_action_settled_by_direct_observation",
    },
    "ir-04": {
        "record": "D03", "role": "analog", "stratum": "irrelevant",
        "variant": "canonical",
        "pointers": {"id": "/id", "mod": "/affected/0/package/name",
                     "fixed": "/affected/0/ranges/0/events/1/fixed",
                     "summary": "/summary"},
        "auth": "{id}: affected module {mod}, versions < {fixed}",
        "cited": "{id} ({mod}): {summary}. Affected: versions < {fixed}.",
        "surface_text": ("The web team reproduced the glob-sanitization "
                         "behavior directly against a local file server "
                         "build this afternoon and confirmed the deployed "
                         "configuration does not expose it; the referenced "
                         "report is linked for the record. Decide whether to "
                         "keep the current rollout schedule."),
        "decision_scope": "Go module github.com/caddyserver/caddy/v2 at version 2.11.0, using the file_server module",
        "expect_match": True,
        "behavior": "baseline_action_settled_by_direct_observation",
    },
    "ir-05": {
        "record": "E05", "role": "analog", "stratum": "irrelevant",
        "variant": "basis_kind",
        "pointers": {"id": "/licenseId", "name": "/name"},
        "auth": "SPDX license record {id}: {name}",
        "cited": "SPDX {id}: {name}.",
        "surface_text": ("Company policy directs that all new file-level "
                         "copyleft dependencies route through the OSS review "
                         "board before adoption; the referenced license "
                         "record is attached as the policy's example. Decide "
                         "whether to route the new dependency through the "
                         "board."),
        "decision_scope": "adopting an MPL-2.0-licensed dependency in the product tree",
        "expect_match": False,
        "behavior": "baseline_action_settled_by_internal_policy",
    },
}

# ---------------------------------------------------------------------------
# Placebo pool: truthful, externally verified (against the frozen P-pool
# snapshots), semantically irrelevant sentences. `base` states only what the
# cited disjoint record itself records; `verify` names the JSON pointers in
# the P raw that substantiate each claim (written to the truth-verification
# artifact for the cold placebo review).
# ---------------------------------------------------------------------------

PLACEBO_POOL: dict[str, dict] = {
    "P01": {"base": ("RUSTSEC-2026-0122 records a panic-safety use-after-free "
                     "issue in the rkyv crate's InlineVec and SerVec clear "
                     "methods."),
            "verify": {"id": "/id", "summary": "/summary",
                       "pkg": "/affected/0/package/name"}},
    "P02": {"base": ("GHSA-jggg-4jg4-v7c6 records a denial-of-service issue "
                     "in the npm package protobufjs via unbounded recursive "
                     "JSON descriptor expansion."),
            "short": "GHSA-jggg-4jg4-v7c6 records a protobufjs denial-of-service issue.",
            "verify": {"id": "/ghsa_id", "summary": "/summary",
                       "pkg": "/vulnerabilities/0/package/name"}},
    "P03": {"base": ("the endoflife.date registry record for typo3 lists "
                     "dated support and end-of-life windows for typo3 "
                     "release lines."),
            "verify": {"cycle0": "/0/cycle", "eol0": "/0/eol"}},
    "P04": {"base": ("GO-2026-5676 records an HTTP/3 QPACK trailer expansion "
                     "memory exhaustion issue in the Go module "
                     "github.com/quic-go/quic-go."),
            "short": "GO-2026-5676 records a quic-go memory exhaustion issue.",
            "verify": {"id": "/id", "summary": "/summary",
                       "mod": "/affected/0/package/name"}},
    "P05": {"base": ("the SPDX license list records 0BSD, the BSD Zero "
                     "Clause License, as a current listed license entry."),
            "verify": {"id": "/licenseId", "name": "/name"}},
    "P06": {"base": ("RUSTSEC-2026-0103 records a use-after-free and double "
                     "free in the thin-vec crate's IntoIter drop path when "
                     "an element drop panics."),
            "short": "RUSTSEC-2026-0103 records a drop-path memory issue in the thin-vec crate.",
            "verify": {"id": "/id", "summary": "/summary",
                       "pkg": "/affected/0/package/name"}},
}

# Truthful pad phrases used to hit the exact S1 token count (±0 target inside
# the ±5 gate). Values are per-record facts resolved by the builder:
# {url} = canonical_url, {date} = retrieved_at date, {sha8} = first 8 hex of
# the promoted raw sha256.
PLACEBO_PAD_PHRASES = [
    "snapshot", "retrieved", "{date};", "raw", "sha256", "{sha8};",
    "canonical", "url", "{url};", "frozen", "acquisition", "bytes;",
    "independently", "refetched", "and", "verified;", "promoted", "record;",
    "dated", "drift", "note:", "none;", "capture", "seat:", "mechanical;",
    "registry", "provenance", "entry;", "content", "identity", "confirmed;",
]

# Typed reserve (spare) allocation — pre-pin QC replacement pool only; never
# active fixture evidence.
RESERVES = {
    "A": ["A02", "A03"],
    "B": ["B05", "BR01"],
    "C": ["C03", "C06"],
    "D": ["D02", "D05"],
    "E": ["E03", "E06"],
    "F_unreserved_candidates": ["F01", "F02", "F03", "F04"],
}
