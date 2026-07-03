.PHONY: smoke smoke-local smoke-ollama smoke-claude stage-b stage-b-local suite suite-local conformance route-watch route-watch-test x4-base-rate occlusion-watch occlusion-watch-test m1-wire m2-wire m2-test m3-test x1-test x2-test x2-fixture-check prf-test prf-gate prf-smoke prf2-test prf2-gate prf2-smoke

# SPEC_M2 unit tests (no model): Wall B trace-only + fail-closed mint paths, and
# the oracle answer-shape guards (the _norm markdown/newline glue regression).
m2-test:
	uv run --no-project python -m tests.test_resident
	uv run --no-project python -m tests.test_oracle
	uv run --no-project python -m tests.test_score_resident

# SPEC_M2 resident-substrate chain on mock (STRUCTURAL only: world-oracle chains
# are real-engine evidence; mock exercises the seam, mint, and fork end-to-end).
m2-wire:
	uv run --no-project python -m harness.run_m2 --wire-all --engine mock

# SPEC_M2 resident-substrate scorer (RS-1/RS-loses/RS-stale/RS-U1) over the wire
# chain. Run after m2-wire (regenerates the ledger fresh each time).
m2-score:
	uv run --no-project python -m harness.score_resident runs/m2/rs-s2.jsonl episodes/m2/rs-e2.json

# SPEC_M3 adversarial-air-gap instrument smoke (no model): the organ-projection diff
# (AG-1 refusal / AG-channel breach), Wall I rejection, the IN-1/IN-loses write-path
# cells, and fail-closed preconditions. Mock exhibits the breaches because they are
# pure functions of select_offers; real attacks are the cold Gemini agent's job (§8.2).
m3-test:
	uv run --no-project python -m tests.test_redteam

# SPEC_X1 decay-dynamics instrument smoke (no model): the earned-reweighting offer
# flip (X1-win), soft-ablation isolating temperature from the M-track gates, the
# projection invariant fail-closed (confounded_authority), Wall II, and
# ledger-deterministic replay. Mock exhibits the reweighting because it is a pure
# function of select_offers; real cross-engine evidence is the gated run (§8).
x1-test:
	uv run --no-project python -m tests.test_decay

# SPEC_X2 prune-to-cold-store instrument smoke (no model): the cost-at-matched-quality
# win (X2-win), the over-prune loss (B drops a needed record it cannot recover), the
# quality-erosion floor-refusal, cost replaying purely from prune/rematerialize rows,
# and Wall II. Mock = machinery wire; real cross-engine evidence is the gated run.
x2-test:
	uv run --no-project python -m tests.test_prune

# SPEC_X2 out-of-weights fixture admission gate + fictional oracle smoke.
x2-fixture-check:
	uv run --no-project python -m harness.check_x2_fixture
	uv run --no-project python -m tests.test_x2_fixture

# M1 inheritance wire: all six authored pairs on mock + cell scorers (wire_test disclosed).
m1-wire:
	uv run --no-project python -m harness.run_m1 --wire-all --score

# M-1 bootstrap-contract conformance. Static checks alone, or pass a manifest:
#   make conformance MANIFEST=runs/bootstrap/<agent>.json
conformance:
	uv run --no-project python -m harness.check_contract $(if $(MANIFEST),--manifest $(MANIFEST)) $(if $(ROUTE_WATCH_WRITE),--route-watch-write)

# SPEC_X4 route_watch: the declared-read-seam occlusion watch (files-read →
# obligations-inherited). An INSTRUMENT, not a gate — prints cold-confidence watch
# rows by default, never a pass/fail (always exits 0). Writing to
# runs/bootstrap/route_watch.jsonl is explicit:
#   make route-watch MANIFEST=runs/bootstrap/<agent>.json WRITE=1
# `make conformance MANIFEST=...` runs route_watch advisory print-only unless
# ROUTE_WATCH_WRITE=1 is set.
route-watch:
	uv run --no-project python -m harness.route_watch $(if $(MANIFEST),--manifest $(MANIFEST)) $(if $(WRITE),--write)

# heir-audit fatigue metrics: topic-presence counts over the immutable thread
# record (pace, roster attrition, blocker/endorse trend). An INSTRUMENT, not a
# gate — print-only, always exits 0; counting rules live in the module docstring.
fatigue-metrics:
	uv run --no-project python -m harness.fatigue_metrics

# heir-audit S4 close-latency gate (glm-5's computable form): the read-latency
# instrument — a close emits close_packet_stamped + close_ruled; the interval is
# the moderator's read window. INSTRUMENT, not a gate (exits 0). `--retro` runs
# the advisory, cry-wolf-prone marker-inference over the historical thread record.
close-latency:
	uv run --no-project python -m harness.close_latency $(if $(RETRO),--retro)

# SPEC_CLOSE_GATE v0.1: the milestone close as a computed artifact. Wire tests (mock
# fixtures, never evidence) + the contribution ledger's per-milestone liveness view.
close-gate-test:
	uv run --no-project python -m tests.test_close_gate

ledger-status:
	uv run --no-project python -m harness.score_contribution runs/m1_5/contributions.jsonl --status

# SPEC_X4 route_watch instrument smoke (no model): the relation computes (cold route
# surfaces the lineage-plane candidate; a bridge-routed warm route is quiet), the
# witness path is external + append-only, and the instrument never gates. MACHINERY
# only — NOT evidence the organ works (that is earned prospectively, §0/§7).
route-watch-test:
	uv run --no-project python -m tests.test_route_watch

# SPEC_X4 §9.4 cry-wolf base rate: route_watch fire-rate on real work-product prose
# (the substrate thread turns) — the admission gate before any standing watch on live
# turns. MACHINERY only; a high rate is the cry_wolf loses-condition measured, not a catch.
x4-base-rate:
	uv run --no-project python -m harness.x4_base_rate $(if $(CUTOFF),--cutoff $(CUTOFF))

# SPEC_X4 occlusion_watch: the session-seam witness, Layer-1 emitter (§11). Reads the
# witnessed arm-now precommit, examines S1 surfaces by literal key, emits Layer-1 rows
# only (never a verdict). MACHINERY; the earned event is Layer 2 (§10), prospective.
occlusion-watch:
	uv run --no-project python -m harness.occlusion_watch $(if $(WRITE),--write) $(if $(OUTCOMES),--outcomes)

occlusion-watch-test:
	uv run --no-project python -m tests.test_occlusion_watch

# Full suite: every scored episode + every cell verdict, one engine.
suite:
	uv run --with anthropic python -m harness.run_suite --engine claude

suite-local:
	uv run --no-project python -m harness.run_suite --engine local --model openai/gpt-oss-20b

# Stage B wire: four lanes (L0/L1/L2/L3) with persistent authority sidecars.
# Default engine is the Anthropic API (claude-opus-4-8); EP picks the episode.
EP ?= episodes/conflict-001.json
stage-b:
	uv run --with anthropic python -m harness.run_stage_b $(EP) --rounds 2

stage-b-local:
	uv run --no-project python -m harness.run_stage_b $(EP) \
		--engine local --model openai/gpt-oss-20b --rounds 2

# Stage A smoke wire with the deterministic mock engine (no credentials needed).
# Mock runs are wire tests, never evidence about memory — disclosed in the ledger.
smoke:
	uv run --no-project python -m harness.run_stage_a episodes/smoke-001.json --engine mock

# Real local engine via LM Studio (start with: lms server start).
# Uses gpt-oss-20b for generation and nomic for embedding similarity.
smoke-local:
	uv run --no-project python -m harness.run_stage_a episodes/smoke-001.json \
		--engine local --model openai/gpt-oss-20b --similarity embedding_nomic

# Same wire against Ollama's OpenAI-compatible endpoint.
smoke-ollama:
	uv run --no-project python -m harness.run_stage_a episodes/smoke-001.json \
		--engine local --base-url http://localhost:11434/v1 --model llama3.1:8b

# Anthropic API engine — only if/when a key or `ant auth login` profile exists.
smoke-claude:
	uv run --with anthropic python -m harness.run_stage_a episodes/smoke-001.json --engine claude

# SPEC_PAUSE_RESUME v0.1 wire tests (mock only, never promotes a cell): the
# closed predicate AST, the D1 two-phase mint goldens, D2 derivation replay,
# the D3 warmth-tax three regions, and the §9 gate tamper cases.
prf-test:
	uv run --no-project python -m tests.test_prf_predicate_ast
	uv run --no-project python -m tests.test_prf_mint
	uv run --no-project python -m tests.test_prf_derive
	uv run --no-project python -m tests.test_prf_d3_reopen
	uv run --no-project python -m tests.test_prf_fixture_gate
	uv run --no-project python -m tests.test_prf_engine

# SPEC_PAUSE_RESUME §9 admission gate on the authored meridian fixture.
prf-gate:
	uv run --no-project python -m harness.check_prf_fixture

# SPEC_PAUSE_RESUME mock fork smoke: the five meridian episodes end-to-end
# (runner -> ledger -> scorer). Wire machinery, never evidence (§12).
prf-smoke:
	@for ep in episodes/prf/meridian/ep-*.json; do \
		echo "== $$ep"; \
		uv run --no-project python -m harness.run_prf $$ep | \
			python3 -c "import json,sys; print('  cell:', json.load(sys.stdin)['verdict']['cell'])"; \
	done

# SPEC_PAUSE_RESUME Part II v0.2 — SBR + ECAC wire tests (mock only).
prf2-test:
	uv run --no-project python -m tests.test_prf_sbr
	uv run --no-project python -m tests.test_prf_ecac

prf2-gate:
	uv run --no-project python -m harness.check_prf_fixture episodes/prf/sbr-meridian/manifest.json

prf2-smoke:
	@for ep in episodes/prf/sbr-meridian/ep-*.json; do \
		echo "== $$ep"; \
		uv run --no-project python -m harness.run_sbr $$ep | \
			python3 -c "import json,sys; print('  cell:', json.load(sys.stdin)['verdict']['cell'])"; \
	done

# warming-budget wire tests (SPEC_WARMING_BUDGET v0.1 — mock only, never promotes)
warming-test:
	uv run --no-project python -m tests.test_warming

# warming-budget population watch (SPEC §2): stamp = live branch-blind enumeration
wb-population-status:
	uv run --no-project python -m harness.wb_population status

# warming-budget T1 watch check: diff live IESG status slices against T0;
# ledger world_move + t1_catalog_materialized on transition. Run on cadence.
wb-watch:
	uv run --no-project python -m harness.wb_pause watch

wb-status:
	uv run --no-project python -m harness.wb_pause status
