.PHONY: smoke smoke-local smoke-ollama smoke-claude stage-b stage-b-local suite suite-local conformance m1-wire m2-wire m2-test m3-test

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

# M1 inheritance wire: all six authored pairs on mock + cell scorers (wire_test disclosed).
m1-wire:
	uv run --no-project python -m harness.run_m1 --wire-all --score

# M-1 bootstrap-contract conformance. Static checks alone, or pass a manifest:
#   make conformance MANIFEST=runs/bootstrap/<agent>.json
conformance:
	uv run --no-project python -m harness.check_contract $(if $(MANIFEST),--manifest $(MANIFEST))

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
