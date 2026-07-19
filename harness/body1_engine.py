"""Narrow Body-1 engine adapter.

Unlike the general answer renderer, this adapter sends the frozen Body-1
expression prompt exactly once per stateless call. The deterministic mock
chooses only packet-authored forms and is wire evidence only.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .body1 import FORM_BARE, FORM_NONBINDING
from .engine import ClaudeEngine, LocalEngine


@dataclass(frozen=True)
class Body1EngineResult:
    raw_answer: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    observed_model: str


class Body1Engine:
    def __init__(
        self,
        *,
        backend: str,
        model: str,
        base_url: str = "http://localhost:1234/v1",
    ):
        self.backend_cli = backend
        self.requested_model = model
        if backend == "claude":
            self.backend_name = "claude"
            self.engine = ClaudeEngine(model, temperature=0)
        elif backend == "local":
            self.backend_name = "local_openai_compat"
            self.engine = LocalEngine(model, base_url=base_url, temperature=0)
        elif backend == "mock":
            self.backend_name = "mock"
            self.engine = None
        else:
            raise ValueError(f"unknown Body-1 engine backend {backend!r}")

    def run(self, prompt: str, fixture: dict, offered_record_ids: list[str]) -> Body1EngineResult:
        if self.backend_name == "mock":
            started = time.monotonic()
            form = FORM_NONBINDING if offered_record_ids else FORM_BARE
            answer = fixture["packet_expressions"][form]
            return Body1EngineResult(
                raw_answer=answer,
                latency_ms=int((time.monotonic() - started) * 1000),
                prompt_tokens=len(prompt.split()),
                completion_tokens=len(answer.split()),
                observed_model="mock-engine-v1",
            )
        if self.backend_name == "claude":
            started = time.monotonic()
            response = self.engine.client.messages.create(
                model=self.requested_model,
                max_tokens=256,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            answer = "".join(
                block.text for block in response.content if block.type == "text"
            ).strip()
            return Body1EngineResult(
                raw_answer=answer,
                latency_ms=int((time.monotonic() - started) * 1000),
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                observed_model=response.model,
            )
        answer, latency_ms, prompt_tokens, completion_tokens, observed_model = (
            self.engine._chat(
                [{"role": "user", "content": prompt}],
                max_tokens=256,
                temperature=0,
            )
        )
        return Body1EngineResult(
            raw_answer=answer,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            observed_model=observed_model,
        )
