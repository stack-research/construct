"""The engine: one LLM behind a narrow interface.

The harness injects the offer set into the prompt; the engine never queries
the store (plan §4A, harness-side retrieval). Two backends:

  ClaudeEngine — Anthropic API (when a key is available).
  LocalEngine — any OpenAI-compatible server (LM Studio :1234, Ollama :11434/v1).
  MockEngine  — deterministic stand-in for wire-testing without any model.

DISCLOSURE: a MockEngine run is a smoke test of the wire, never a result.
The backend name is recorded in the run_config row; scorers must refuse to
treat engine_backend="mock" rows as evidence about memory.
"""

from __future__ import annotations

import hashlib
import inspect
import re
import time
from dataclasses import dataclass

PROMPT_TEMPLATE = """You are completing a task. You may be given context records; treat them as your memory — they may help, conflict, or be irrelevant.

{foreground_block}{memory_block}Task: {question}

Answer concisely. Give only your final answer."""

# L3 usage elicitation (plan §4B, codex B2): asked AFTER the answer, in the
# same conversation, so the labels cannot steer the answer. The engine's
# claims are recorded, never trusted — scored_usage comes from a label-blind
# cross-substrate audit, not from here.
ELICIT_TEMPLATE = """Now classify each context record by the role it actually played in your answer above. Use exactly one label per record:

  evidence — you treated it as a fact your answer rests on
  plan — you treated it as an intention or course of action
  habit — you followed it as a routine or default without re-deriving it
  preference — you treated it as a taste, style, or priority
  narrative_repair — you used it to make your answer cohere or explain away a conflict
  unused — it played no role in your answer

Reply with only a JSON object mapping record id to label, e.g. {{"r-001": "evidence"}}.

Records:
{record_lines}"""


@dataclass
class EngineResult:
    answer: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    model: str


@dataclass
class SessionStepResult:
    """One step of a multi-turn action session (SPEC_PAUSE_RESUME Part II §24)."""
    raw_action: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    # transport envelope BEFORE unwrapping, when it differed from raw_action
    # (§43 board round 2026-07-06: replay honesty for the harmony fix)
    raw_transport: str | None = None


_HARMONY_MESSAGE_RE = re.compile(r"<\|message\|>", re.IGNORECASE)
_HARMONY_TRAILER_RE = re.compile(r"<\|(?:end|return|call)\|>.*\Z",
                                 re.IGNORECASE | re.DOTALL)


def unwrap_harmony(text: str) -> str:
    """Strip gpt-oss harmony channel envelopes from a chat completion.

    Transport repair, never grammar leniency (§43 board ruling, 2026-07-06,
    codex's precision adopted unanimously): the model's intended payload —
    the text after the LAST `<|message|>` marker, minus any trailing
    end/return tokens — reaches the parser; the parser itself stays strict.
    Committed defect signatures this must handle (seeded from the §33 and
    Greenreach r1 ledgers): `<|channel|>commentary <|constrain|>R01<|message|>R01`,
    `<|channel|>final <|constrain|>json<|message|>{...}`. Text without an
    envelope passes through unchanged.
    """
    parts = _HARMONY_MESSAGE_RE.split(text)
    payload = parts[-1] if len(parts) > 1 else text
    return _HARMONY_TRAILER_RE.sub("", payload).strip()


@dataclass
class UsageClaims:
    claims: dict[str, str]  # record_id -> claimed label
    parse_error: bool
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int


VALID_USAGE_LABELS = {"evidence", "plan", "habit", "preference", "narrative_repair", "unused"}


def renderer_version() -> str:
    """Pre-Stage-C debt (rubric thread close): hash of everything that shapes
    what the engine sees — the prompt template plus the rendering functions'
    source, field order included. Any change moves the hash, so renderer drift
    is recorded in run_config rather than silent."""
    src = PROMPT_TEMPLATE + inspect.getsource(render_foreground) + inspect.getsource(build_prompt)
    return hashlib.sha256(src.encode()).hexdigest()[:16]


def render_foreground(foreground_data: list[dict]) -> str:
    """SPEC_V1X §1: rendered identically in every lane (including L0), built
    once per fork group. The engine sees the datum and its provenance; it
    never sees yield decisions or datum-vs-record comparisons."""
    if not foreground_data:
        return ""
    lines = [
        f"Live observation ({d['channel']}, observed {d['observed_at']}): {d['text']}"
        for d in foreground_data
    ]
    return "\n".join(lines) + "\n\n"


def build_prompt(question: str, offered_texts: list[str], foreground_block: str = "") -> str:
    if offered_texts:
        memory_block = "Context records:\n" + "\n".join(f"- {t}" for t in offered_texts) + "\n\n"
    else:
        memory_block = ""
    return PROMPT_TEMPLATE.format(
        foreground_block=foreground_block, memory_block=memory_block, question=question
    )


def build_elicit_prompt(offered: list[tuple[str, str]]) -> str:
    record_lines = "\n".join(f"{rid}: {text}" for rid, text in offered)
    return ELICIT_TEMPLATE.format(record_lines=record_lines)


def parse_usage_claims(raw: str, offered_ids: list[str]) -> tuple[dict[str, str], bool]:
    """Lenient JSON extraction; unknown labels and missing ids count as a parse defect."""
    import json
    import re

    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return {}, True
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}, True
    claims, defect = {}, False
    for rid in offered_ids:
        label = str(data.get(rid, "")).strip().lower()
        if label in VALID_USAGE_LABELS:
            claims[rid] = label
        else:
            defect = True
    return claims, defect


@dataclass
class LoadBearingClaims:
    # SPEC_M2 v0.2: the resident's *decisiveness* claim per record — "would my answer
    # have changed without it" — elicited separately from the role audit. RS-loses
    # refutes a TRUE claim the fork's ablation says is false (performed continuity),
    # never mere "I considered it."
    claimed: dict[str, bool]  # record_id -> claimed would-change-my-answer
    parse_error: bool
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int


LOADBEARING_TEMPLATE = """Re-examine the answer you just gave. For each context record below, judge ONE counterfactual: would your final answer have been DIFFERENT if that record had NOT been provided? Judge whether it changed your conclusion — not whether you read it or found it topically relevant.

Records:
{record_lines}

Reply with JSON only, no prose: {{"<record_id>": true_or_false, ...}} — true if removing the record would change your answer, false if your answer would be the same without it."""


def build_loadbearing_prompt(offered: list[tuple[str, str]]) -> str:
    record_lines = "\n".join(f"{rid}: {text}" for rid, text in offered)
    return LOADBEARING_TEMPLATE.format(record_lines=record_lines)


def parse_load_bearing(raw: str, offered_ids: list[str]) -> tuple[dict[str, bool], bool]:
    """Lenient JSON extraction of per-record decisiveness booleans; missing/non-bool → defect."""
    import json
    import re

    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return {}, True
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}, True
    claimed, defect = {}, False
    for rid in offered_ids:
        v = data.get(rid)
        if isinstance(v, bool):
            claimed[rid] = v
        elif isinstance(v, str) and v.strip().lower() in ("true", "false", "yes", "no"):
            claimed[rid] = v.strip().lower() in ("true", "yes")
        else:
            defect = True
    return claimed, defect


SBR_ACTION_INSTRUCTION = (
    "Reply with JSON only — one action per turn:\n"
    '  {"action":"READ","surface_id":"<id>"}\n'
    '  {"action":"STOP"}\n'
    "No prose, no other keys."
)

SBR_ACTION_INSTRUCTION_V03 = (
    "Reply with one action per turn: R01 through R21, or STOP.\n"
    "Use the handle shown in the catalog menu. No prose, no JSON."
)


def sbr_action_instruction(instrument_version: str = "0.2") -> str:
    if instrument_version in ("0.3", "0.4"):
        return SBR_ACTION_INSTRUCTION_V03
    return SBR_ACTION_INSTRUCTION


class _ClaudeSession:
    """Multi-turn action channel for SBR (SPEC_PAUSE_RESUME Part II §24)."""

    def __init__(self, engine: "ClaudeEngine", system: str, foreground: str,
                 action_instruction: str | None = None):
        self._engine = engine
        self._messages: list[dict] = []
        self._action_instruction = action_instruction or SBR_ACTION_INSTRUCTION
        # Single presentation path (§15): content arrives via step(), not init.

    def step(self, observation: str) -> SessionStepResult:
        self._messages.append({"role": "user", "content": observation})
        t0 = time.monotonic()
        kwargs: dict = {
            "model": self._engine.model,
            "max_tokens": 256,
            "system": self._action_instruction,
            "messages": self._messages,
        }
        if self._engine.temperature is not None:
            kwargs["temperature"] = self._engine.temperature
        resp = self._engine.client.messages.create(**kwargs)
        latency_ms = int((time.monotonic() - t0) * 1000)
        raw = "".join(b.text for b in resp.content if b.type == "text").strip()
        self._messages.append({"role": "assistant", "content": raw})
        return SessionStepResult(
            raw, latency_ms, resp.usage.input_tokens, resp.usage.output_tokens)


class ClaudeEngine:
    backend_name = "claude"

    def __init__(self, model: str = "claude-opus-4-8",
                 temperature: float | None = None):
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model
        self.temperature = temperature

    def start_session(self, system: str = "", foreground: str = "",
                      action_instruction: str | None = None) -> _ClaudeSession:
        return _ClaudeSession(self, system, foreground, action_instruction)

    def run(self, question: str, offered_texts: list[str], foreground_block: str = "") -> EngineResult:
        prompt = build_prompt(question, offered_texts, foreground_block)
        t0 = time.monotonic()
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        answer = "".join(b.text for b in resp.content if b.type == "text").strip()
        return EngineResult(
            answer=answer,
            latency_ms=latency_ms,
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            model=resp.model,
        )

    def elicit_usage(self, question: str, offered: list[tuple[str, str]], answer: str, foreground_block: str = "") -> UsageClaims:
        prompt = build_prompt(question, [t for _, t in offered], foreground_block)
        t0 = time.monotonic()
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": answer},
                {"role": "user", "content": build_elicit_prompt(offered)},
            ],
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        raw = "".join(b.text for b in resp.content if b.type == "text")
        claims, defect = parse_usage_claims(raw, [rid for rid, _ in offered])
        return UsageClaims(claims, defect, latency_ms, resp.usage.input_tokens, resp.usage.output_tokens)

    def elicit_load_bearing(self, question: str, offered: list[tuple[str, str]], answer: str, foreground_block: str = "") -> LoadBearingClaims:
        t0 = time.monotonic()
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=256,
            messages=[
                {"role": "user", "content": build_prompt(question, [t for _, t in offered], foreground_block)},
                {"role": "assistant", "content": answer},
                {"role": "user", "content": build_loadbearing_prompt(offered)},
            ],
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        raw = "".join(b.text for b in resp.content if b.type == "text")
        claimed, defect = parse_load_bearing(raw, [rid for rid, _ in offered])
        return LoadBearingClaims(claimed, defect, latency_ms, resp.usage.input_tokens, resp.usage.output_tokens)


class _LocalSession:
    """Multi-turn action channel for SBR (SPEC_PAUSE_RESUME Part II §24)."""

    def __init__(self, engine: "LocalEngine", system: str, foreground: str,
                 action_instruction: str | None = None):
        self._engine = engine
        self._action_instruction = action_instruction or SBR_ACTION_INSTRUCTION
        self._messages: list[dict] = [
            {"role": "system", "content": self._action_instruction}]
        # Single presentation path (§15): content arrives via step(), not init.

    def step(self, observation: str) -> SessionStepResult:
        self._messages.append({"role": "user", "content": observation})
        raw, latency_ms, ptok, ctok, _ = self._engine._chat(
            self._messages, max_tokens=256,
            temperature=self._engine.temperature)
        self._messages.append({"role": "assistant", "content": raw})
        unwrapped = unwrap_harmony(raw)
        return SessionStepResult(
            unwrapped, latency_ms, ptok, ctok,
            raw_transport=raw if unwrapped != raw else None)


class LocalEngine:
    """OpenAI-compatible chat-completions backend, stdlib HTTP only.

    Works against LM Studio (http://localhost:1234/v1), Ollama
    (http://localhost:11434/v1), or a hosted OpenAI-compatible endpoint
    (pass api_key then). Temperature defaults to 0 for Regime-D; Regime-S
    passes the pinned range value from the runner (§17).
    """

    backend_name = "local_openai_compat"

    def __init__(self, model: str, base_url: str = "http://localhost:1234/v1",
                 api_key: str | None = None, temperature: float | None = 0,
                 token_param: str = "max_tokens"):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.temperature = temperature
        # OpenAI's GPT-5 family rejects legacy `max_tokens` (transport smoke
        # 2026-07-09) — remote callers pass "max_completion_tokens"; the
        # default stays byte-identical for every committed local-engine run
        self.token_param = token_param

    def start_session(self, system: str = "", foreground: str = "",
                      action_instruction: str | None = None) -> _LocalSession:
        return _LocalSession(self, system, foreground, action_instruction)

    def _chat(self, messages: list[dict], max_tokens: int = 1024,
              temperature: float | None = None) -> tuple[str, int, int, int, str]:
        import json
        import urllib.request

        temp = 0 if temperature is None else temperature
        body = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": temp,
            self.token_param: max_tokens,
        }).encode()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=body, headers=headers)
        t0 = time.monotonic()
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read())
        latency_ms = int((time.monotonic() - t0) * 1000)
        msg = data["choices"][0]["message"]
        usage = data.get("usage") or {}
        return (
            (msg.get("content") or "").strip(),
            latency_ms,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            data.get("model", self.model),
        )

    def run(self, question: str, offered_texts: list[str], foreground_block: str = "") -> EngineResult:
        prompt = build_prompt(question, offered_texts, foreground_block)
        answer, latency_ms, ptok, ctok, model = self._chat([{"role": "user", "content": prompt}])
        return EngineResult(answer, latency_ms, ptok, ctok, model)

    def elicit_usage(self, question: str, offered: list[tuple[str, str]], answer: str, foreground_block: str = "") -> UsageClaims:
        raw, latency_ms, ptok, ctok, _ = self._chat([
            {"role": "user", "content": build_prompt(question, [t for _, t in offered], foreground_block)},
            {"role": "assistant", "content": answer},
            {"role": "user", "content": build_elicit_prompt(offered)},
        ], max_tokens=512)
        claims, defect = parse_usage_claims(raw, [rid for rid, _ in offered])
        return UsageClaims(claims, defect, latency_ms, ptok, ctok)

    def elicit_load_bearing(self, question: str, offered: list[tuple[str, str]], answer: str, foreground_block: str = "") -> LoadBearingClaims:
        raw, latency_ms, ptok, ctok, _ = self._chat([
            {"role": "user", "content": build_prompt(question, [t for _, t in offered], foreground_block)},
            {"role": "assistant", "content": answer},
            {"role": "user", "content": build_loadbearing_prompt(offered)},
        ], max_tokens=256)
        claimed, defect = parse_load_bearing(raw, [rid for rid, _ in offered])
        return LoadBearingClaims(claimed, defect, latency_ms, ptok, ctok)


class MockEngineSession:
    """Scripted action list for SBR wire tests (SPEC_PAUSE_RESUME Part II §24).

    Tests inject `scripted_actions` — fixtures never do. The mock proves the
    loop mechanics, never behavioral findings.
    """

    def __init__(self, scripted_actions: list[str], system: str = "",
                 foreground: str = ""):
        self.scripted_actions = list(scripted_actions)
        self.system = system
        self.foreground = foreground
        self._step = 0
        self.observations: list[str] = []

    def step(self, observation: str) -> SessionStepResult:
        self.observations.append(observation)
        if self._step < len(self.scripted_actions):
            raw = self.scripted_actions[self._step]
        else:
            raw = '{"action":"STOP"}'
        self._step += 1
        return SessionStepResult(raw, 0, 0, 0)


class MockEngine:
    """Answers from offered records if any token-overlaps the question; else a fixed string.

    Deterministic by construction, so re-run reproducibility of the wire is testable.
    """

    backend_name = "mock"
    model = "mock-engine-v1"

    def __init__(self, scripted_actions: list[str] | None = None):
        self._scripted_actions = scripted_actions

    def start_session(self, system: str = "", foreground: str = "") -> MockEngineSession:
        actions = self._scripted_actions or []
        return MockEngineSession(actions, system, foreground)

    def with_script(self, scripted_actions: list[str]) -> "MockEngine":
        """Return a copy bound to a scripted action list (wire tests only)."""
        return MockEngine(scripted_actions=scripted_actions)

    def run(self, question: str, offered_texts: list[str], foreground_block: str = "") -> EngineResult:
        t0 = time.monotonic()
        qwords = set(question.lower().split())
        best, best_overlap = None, 0
        candidates = offered_texts + ([foreground_block.strip()] if foreground_block else [])
        for t in candidates:
            overlap = len(qwords & set(t.lower().split()))
            if overlap > best_overlap:
                best, best_overlap = t, overlap
        answer = best if best is not None else "I do not know."
        latency_ms = int((time.monotonic() - t0) * 1000)
        prompt = build_prompt(question, offered_texts, foreground_block)
        return EngineResult(
            answer=answer,
            latency_ms=latency_ms,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(answer.split()),
            model=self.model,
        )

    def elicit_usage(self, question: str, offered: list[tuple[str, str]], answer: str, foreground_block: str = "") -> UsageClaims:
        # Deterministic: claims "evidence" for any record sharing tokens with
        # the answer, "unused" otherwise. Wire-test fixture only.
        awords = set(answer.lower().split())
        claims = {
            rid: ("evidence" if awords & set(text.lower().split()) else "unused")
            for rid, text in offered
        }
        return UsageClaims(claims, False, 0, 0, 0)

    def elicit_load_bearing(self, question: str, offered: list[tuple[str, str]], answer: str, foreground_block: str = "") -> LoadBearingClaims:
        # Deterministic wire fixture: claims a record decisive iff it shares tokens
        # with the answer (mirrors elicit_usage's 'evidence' rule).
        awords = set(answer.lower().split())
        claimed = {rid: bool(awords & set(text.lower().split())) for rid, text in offered}
        return LoadBearingClaims(claimed, False, 0, 0, 0)
