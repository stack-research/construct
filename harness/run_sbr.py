"""SBR fork runner — SPEC_PAUSE_RESUME Part II §15/§17 machinery.

Symmetric Bounded Retrieval: the engine drives READ/STOP over a flat catalog
with structured actions only. The harness intercepts, validates, fetches
canonical text, ledgers, and enforces budgets — the engine never writes rows,
never sees the other branch, and never manipulates budgets as free text.

Mock runs are wire tests: scripted MockEngine sessions prove loop mechanics,
never behavioral findings — disclosed in run_config.

Regime-S runs execute the dispersion probe (§17) on the baseline branch
before the suite; unique_realizations == 1 downgrades to point-mode.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any

from .check_prf_fixture import check_manifest
from .engine import ClaudeEngine, LocalEngine, MockEngine
from .ledger import Ledger
from .oracle import authored_oracle

REPO = Path(__file__).resolve().parent.parent

ACTION_SPACE = {"READ", "STOP"}
BRANCHES = ("cold_reread", "resumable_state")


def _tokens(text: str) -> int:
    return len(text.split())


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


from .sbr_util import (
    action_space_hash,
    catalog_hash,
    render_catalog_list,
    render_foreground_block,
    recompute_c_max,
    sorted_surface_ids,
)


def parse_structured_action(raw: str) -> tuple[dict | None, str | None]:
    """Parse constrained JSON actions only (§15). Returns (action, refuse_reason)."""
    import re as _re

    m = _re.search(r"\{.*\}", raw, _re.DOTALL)
    if not m:
        return None, "not_json"
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None, "invalid_json"
    if not isinstance(data, dict):
        return None, "not_object"
    action = str(data.get("action", "")).upper()
    if action not in ACTION_SPACE:
        return None, f"illegal_action:{action}"
    if action == "READ":
        sid = data.get("surface_id")
        if not sid or not isinstance(sid, str):
            return None, "missing_surface_id"
        if len(data) != 2:
            return None, "extra_keys"
        return {"action": "READ", "surface_id": sid}, None
    if len(data) != 1:
        return None, "extra_keys"
    return {"action": "STOP"}, None


def synthesize_mock_answer(read_ids: list[str], episode: dict) -> str:
    """Wire-test answer from reads: status surface S1 yields the oracle key."""
    if "S1" in read_ids:
        return episode["expected_answer_t1"]
    fg = episode.get("resumable_foreground") or ""
    if "pending" in fg.lower():
        return "commissioning window pending survey confirmation"
    return "unknown status"


def recompute_c_max(budgets: dict) -> int:
    return (budgets["max_read_tokens"]
            + budgets["max_steps"] * budgets["action_overhead_tokens"])


def run_sbr_session(
    episode: dict,
    branch: str,
    session_id: str,
    sample_index: int,
    session,
    ledger: Ledger,
    *,
    probe: bool = False,
) -> dict:
    """One SBR session on one branch. Returns session summary dict."""
    catalog = episode["catalog"]
    sort_rule = episode["catalog_sort"]
    budgets = episode["budgets"]
    cat_hash = catalog_hash(catalog, sort_rule)
    act_hash = action_space_hash()
    visible = sorted_surface_ids(catalog, sort_rule)

    foreground = ""
    if branch == "resumable_state":
        foreground = render_foreground_block(episode.get("resumable_foreground"))

    ledger.write({
        "kind": "sbr_session",
        "branch": branch,
        "session_id": session_id,
        "sample_index": sample_index,
        "catalog_hash": cat_hash,
        "action_space_hash": act_hash,
        "budgets": dict(budgets),
        "probe": probe,
    })
    for sid in visible:
        ledger.write({
            "kind": "affordance_presented",
            "branch": branch,
            "session_id": session_id,
            "sample_index": sample_index,
            "surface_id": sid,
            "title": catalog[sid]["title"],
            "physical_index": visible.index(sid),
        })

    system = (
        "You are completing a catalog-driven task. Choose surfaces to read "
        "or stop when ready to answer.\n\n"
        + render_catalog_list(catalog, sort_rule)
        + f"\n\nTask: {episode['question']}\n"
    )
    # Re-bind session with system+foreground if not already started
    if hasattr(session, "system"):
        pass  # MockEngineSession already constructed with context via observation

    read_ids: list[str] = []
    read_tokens = 0
    step = 0
    overhead = budgets["action_overhead_tokens"]
    max_read = budgets["max_read_tokens"]
    max_steps = budgets["max_steps"]
    terminal = False
    stop_reason = None
    refused_actions: list[dict] = []

    observation = system + foreground + "\nChoose your first action."
    while not terminal and step < max_steps:
        result = session.step(observation)
        parsed, refuse = parse_structured_action(result.raw_action)
        ledger.write({
            "kind": "route_decision",
            "branch": branch,
            "session_id": session_id,
            "sample_index": sample_index,
            "step": step,
            "raw_action": result.raw_action,
            "parsed": parsed is not None,
            "refuse_reason": refuse,
        })
        if refuse:
            refused_actions.append({"step": step, "reason": refuse})
            observation = f"Action refused ({refuse}). Reply with legal JSON only."
            step += 1
            continue

        assert parsed is not None
        if parsed["action"] == "STOP":
            terminal = True
            break

        sid = parsed["surface_id"]
        if sid not in catalog:
            refused_actions.append({"step": step, "reason": "unknown_surface"})
            observation = f"Unknown surface {sid!r}. Choose a catalog id."
            step += 1
            continue
        if sid in read_ids:
            refused_actions.append({"step": step, "reason": "duplicate_read"})
            observation = f"Already read {sid}. Choose another action."
            step += 1
            continue

        surf_tokens = _tokens(catalog[sid]["text"])
        step_cost = surf_tokens + overhead
        if read_tokens + surf_tokens > max_read:
            ledger.write({
                "kind": "forced_stop",
                "branch": branch,
                "session_id": session_id,
                "sample_index": sample_index,
                "stop_reason": "budget_exhausted",
                "read_tokens_recomputed": read_tokens,
                "max_read_tokens": max_read,
            })
            terminal = True
            stop_reason = "budget_exhausted"
            break

        read_ids.append(sid)
        read_tokens += surf_tokens
        ledger.write({
            "kind": "surface_read",
            "branch": branch,
            "session_id": session_id,
            "sample_index": sample_index,
            "step": step,
            "surface_id": sid,
            "read_index": len(read_ids) - 1,
            "content_hash": catalog[sid]["content_hash"],
            "route_read_tokens": surf_tokens,
        })
        observation = (
            f"Surface {sid} ({catalog[sid]['title']}):\n"
            f"{catalog[sid]['text']}\n\nChoose your next action."
        )
        step += 1

    if not terminal and step >= max_steps:
        ledger.write({
            "kind": "forced_stop",
            "branch": branch,
            "session_id": session_id,
            "sample_index": sample_index,
            "stop_reason": "max_steps",
            "steps_taken": step,
            "max_steps": max_steps,
        })
        stop_reason = "max_steps"

    answer = synthesize_mock_answer(read_ids, episode)
    score = authored_oracle(answer, episode["expected_answer_t1"])
    quality_ok = score.score >= episode.get("quality_threshold", 1.0)
    ledger.write({
        "kind": "session_outcome",
        "branch": branch,
        "session_id": session_id,
        "sample_index": sample_index,
        "answer": answer,
        "oracle_score": score.score,
        "quality_ok": quality_ok,
        "oracle_source": "authored_oracle:fictional_meridian",
        "read_ids": list(read_ids),
    })
    return {
        "session_id": session_id,
        "sample_index": sample_index,
        "branch": branch,
        "read_ids": tuple(read_ids),
        "read_tokens": read_tokens,
        "quality_ok": quality_ok,
        "effective_read_cost": read_tokens,
        "stop_reason": stop_reason,
        "refused_actions": refused_actions,
    }


def dispersion_probe(
    episode: dict,
    engine_factory,
    ledger: Ledger,
    k: int,
) -> dict:
    """§17: K pilot draws on baseline (cold_reread) before Regime-S suite."""
    realizations: list[tuple[str, ...]] = []
    summaries = []
    for i in range(k):
        sid = f"probe-{uuid.uuid4().hex[:8]}"
        session = engine_factory(i)
        summary = run_sbr_session(
            episode, "cold_reread", sid, i, session, ledger, probe=True)
        realizations.append(summary["read_ids"])
        summaries.append(summary)
    unique = len(set(realizations))
    result = {
        "unique_realizations": unique,
        "dispersion_probe_k": k,
        "realizations": [list(r) for r in realizations],
    }
    if unique == 1:
        ledger.write({
            "kind": "zero_dispersion_regime",
            "unique_realizations": unique,
            "dispersion_probe_k": k,
            "disclosure": "API-jitter masquerade refused — downgrade to point-mode (§17)",
        })
    return result


def _engine(engine_backend: str, model: str, base_url: str):
    if engine_backend == "claude":
        return ClaudeEngine(model)
    if engine_backend == "local":
        return LocalEngine(model, base_url=base_url)
    return MockEngine()


def run_episode(
    episode: dict,
    ledger: Ledger,
    *,
    engine=None,
    engine_backend: str = "mock",
    regime: str = "D",
    scripted_sessions: dict[str, list[list[str]]] | None = None,
    samples: int = 1,
) -> dict:
    """Full SBR episode: optional dispersion probe + both branches."""
    wire_mock = engine is None
    k = episode.get("regime_s", {}).get("dispersion_probe_k", 5)
    probe_result = None
    effective_regime = regime

    if regime == "S" and not wire_mock:
        def factory(i: int):
            return engine.start_session()
        probe_result = dispersion_probe(episode, factory, ledger, k)
        if probe_result["unique_realizations"] == 1:
            effective_regime = "D"

    cfg: dict[str, Any] = {
        "kind": "run_config",
        "instrument_version": episode.get("instrument_version", "0.2"),
        "engine": engine.backend_name if engine else engine_backend,
        "wire_test": wire_mock,
        "episode_id": episode["episode_id"],
        "regime": effective_regime,
        "requested_regime": regime,
        "samples": samples,
        "quality_threshold": episode.get("quality_threshold", 1.0),
        "foreground_disclosure": episode.get("foreground_disclosure"),
    }
    if probe_result:
        cfg["unique_realizations"] = probe_result["unique_realizations"]
        cfg["dispersion_probe_k"] = probe_result["dispersion_probe_k"]
    if wire_mock:
        cfg["disclosure"] = (
            "mock SBR runner — loop wire test, never evidence about "
            "behavioral suppression (SPEC Part II §12)")
    ledger.write(cfg)

    branch_summaries: dict[str, list[dict]] = {b: [] for b in BRANCHES}
    for branch in BRANCHES:
        scripts = (scripted_sessions or {}).get(branch, [[]])
        n = max(samples, len(scripts))
        for i in range(n):
            sid = f"{branch[:4]}-{uuid.uuid4().hex[:8]}"
            if wire_mock or scripted_sessions is not None:
                actions = scripts[i] if i < len(scripts) else scripts[-1]
                mock = MockEngine(scripted_actions=actions)
                session = mock.start_session()
            else:
                fg = render_foreground_block(episode.get("resumable_foreground")) \
                    if branch == "resumable_state" else ""
                system = (
                    render_catalog_list(episode["catalog"], episode["catalog_sort"])
                    + f"\n\nTask: {episode['question']}"
                )
                session = engine.start_session(system, fg)
            summary = run_sbr_session(
                episode, branch, sid, i, session, ledger)
            branch_summaries[branch].append(summary)

    return {
        "probe": probe_result,
        "regime": effective_regime,
        "branch_summaries": branch_summaries,
    }


def run_and_score(
    episode_path: Path,
    ledger_path: Path | None = None,
    *,
    engine=None,
    engine_backend: str = "mock",
    regime: str = "D",
    scripted_sessions: dict[str, list[list[str]]] | None = None,
    samples: int = 1,
) -> dict:
    episode = json.loads(episode_path.read_text())
    fixture_dir = episode_path.parent
    ledger_path = ledger_path or (
        REPO / "runs" / "prf" / f"{episode['episode_id']}.sbr.jsonl")
    if ledger_path.exists():
        ledger_path.unlink()
    ledger = Ledger(ledger_path)

    gate_checks = check_manifest(fixture_dir / "manifest.json")
    gate_failed = [name for name, ok, _ in gate_checks if not ok]
    if gate_failed:
        ledger.write({"kind": "gate_refused", "failed": gate_failed})
        return {"run": {"halted": "gate_refused", "failed": gate_failed},
                "verdict": None, "ledger": str(ledger_path)}
    ledger.write({"kind": "gate_open", "checks": len(gate_checks),
                  "manifest": str(fixture_dir / "manifest.json")})

    from .score_prf import PRFScorer

    outcome = run_episode(
        episode, ledger, engine=engine, engine_backend=engine_backend,
        regime=regime, scripted_sessions=scripted_sessions, samples=samples)
    events = ledger.rows()
    scorer = PRFScorer(
        events=events, episode=episode)
    verdict = scorer.score()
    ledger.write(verdict)
    return {"run": outcome, "verdict": verdict, "ledger": str(ledger_path)}


def main() -> int:
    ap = argparse.ArgumentParser(description="SBR fork runner (PRF v0.2)")
    ap.add_argument("episode", help="episodes/prf/sbr-meridian/<episode>.json")
    ap.add_argument("--engine", choices=("mock", "local", "claude"),
                    default="mock")
    ap.add_argument("--model", default="claude-opus-4-8")
    ap.add_argument("--base-url", default="http://localhost:1234/v1")
    ap.add_argument("--regime", choices=("D", "S"), default="D")
    ap.add_argument("--samples", type=int, default=1)
    args = ap.parse_args()

    engine = None
    if args.engine != "mock":
        engine = _engine(args.engine, args.model, args.base_url)

    out = run_and_score(
        Path(args.episode), engine=engine, engine_backend=args.engine,
        regime=args.regime, samples=args.samples)
    print(json.dumps(out, indent=2, sort_keys=True))
    if out["verdict"] is None:
        return 1
    return 0 if out["verdict"]["cell"] != "confounded" else 1


if __name__ == "__main__":
    sys.exit(main())
