.PHONY: smoke smoke-local smoke-ollama smoke-claude stage-b stage-b-local suite suite-local conformance

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
