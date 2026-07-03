"""SBR fork runner — SPEC_PAUSE_RESUME Part II §15/§17 machinery.

Symmetric Bounded Retrieval: the engine drives READ/STOP over a flat catalog
with structured actions only. The harness intercepts, validates, fetches
canonical text, ledgers, and enforces budgets — the engine never writes rows,
never sees the other branch, and never manipulates budgets as free text.

The two-phase mint (Part I §4) runs once per episode before any SBR session:
population_precommit → witness (t0) reads → obligation derivation →
frontier_freeze → post_seam catalog → offer-time content floor →
frontier_state_minted | frontier_mint_refused.

Mock runs are wire tests: scripted MockEngine sessions prove loop mechanics,
never behavioral findings — disclosed in run_config.

Regime-S runs execute the dispersion probe (§17) on the baseline branch
before the suite; unique_realizations == 1 downgrades to point-mode.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import uuid
from pathlib import Path
from typing import Any

from .check_prf_fixture import check_manifest
from .derive_live_obligations import DerivationRefused, derive_live_obligations
from .engine import ClaudeEngine, LocalEngine, MockEngine
from .ledger import Ledger
from .mint_frontier_state import (MintRefusal, freeze_validate, manifest_hash,
                                  offer_gate)
from .oracle import authored_oracle
from .prf_ablation import structural_dependency

REPO = Path(__file__).resolve().parent.parent

ACTION_SPACE = {"READ", "STOP"}
BRANCHES = ("cold_reread", "resumable_state")


def _tokens(text: str) -> int:
    return len(text.split())


from .sbr_util import (
    action_space_hash,
    build_sbr_system,
    catalog_hash,
    render_foreground_block,
    render_resumable_foreground,
    recompute_c_max,
    sbr_renderer_version,
    sorted_surface_ids,
)


def parse_structured_action(raw: str) -> tuple[dict | None, str | None]:
    """Parse constrained JSON actions only (§15). Returns (action, refuse_reason)."""
    m = re.search(r"\{.*\}", raw, re.DOTALL)
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


def _witness_reads(episode: dict, population: dict) -> list[dict]:
    catalog = population["catalog"]
    return [{"kind": "surface_read", "branch": "uninterrupted_warm",
             "surface_id": sid, "read_index": i, "catalog_epoch": "t0",
             "content_hash": catalog[sid]["content_hash_t0"],
             "surface_tags": catalog[sid]["surface_tags"]}
            for i, sid in enumerate(episode["witness_route"])]


def run_mint_spine(episode: dict, population: dict, freeze_manifest: dict,
                   ledger: Ledger) -> dict:
    """Part I two-phase mint once per episode (§15/§22). Returns mint context."""
    ledger.write(population)

    witness = _witness_reads(episode, population)
    for row in witness:
        ledger.write(row)

    try:
        out = derive_live_obligations(population, freeze_manifest, witness,
                                      episode["seam_id"])
    except DerivationRefused as e:
        ledger.write(e.row)
        return {"halted": "derivation_refused", **e.row}
    ledger.write(out["batch"])
    for row in out["obligations"]:
        ledger.write(row)

    try:
        cand = freeze_validate(episode["frontier_state"], freeze_manifest,
                               out["batch"], manifest_hash(freeze_manifest))
    except MintRefusal as e:
        ledger.write(e.row)
        return {"halted": "frontier_mint_refused", **e.row}
    ledger.write({"kind": "frontier_freeze",
                  "canonical_state": cand["canonical_state"],
                  "state_digest": cand["state_digest"],
                  "obligation_set_hash": cand["obligation_set_hash"],
                  "seam_id": episode["seam_id"]})

    ledger.write({"kind": "post_seam_catalog_materialized",
                  "surfaces": sorted(population["catalog"]),
                  "disclosure": "symmetric: all branches receive the t1 "
                                "catalog (SPEC §2)"})

    cold_cost = population["sbr_cold_reread_tokens"]
    ablation = structural_dependency(population, freeze_manifest, witness,
                                     episode["seam_id"])
    try:
        minted = offer_gate(
            cand,
            derived_obligation_tokens=episode["ballast"]
                ["derived_obligation_tokens"],
            cold_reread_tokens=cold_cost, gamma=population["gamma"],
            ablation=ablation,
            frontier_artifact_id=f"fa:{episode['episode_id']}")
    except MintRefusal as e:
        ledger.write(e.row)
        return {"halted": "frontier_mint_refused", **e.row}
    ledger.write(minted)

    stale = episode.get("stale_claim")
    if stale:
        ledger.write({
            "kind": "stale_claim_tokens",
            "tokens": _tokens(render_foreground_block(stale)),
            "disclosure": "stale_claim rendered tokens — NOT included in a_i "
                          "(§16 pins a_i to canonical artifact only)",
        })

    return {
        "halted": None,
        "canonical_state": cand["canonical_state"],
        "state_digest": minted["state_digest"],
        "minted": minted,
    }


def synthesize_mock_answer(read_ids: list[str], episode: dict) -> str:
    """Wire-test answer from reads: status surface S1 yields the oracle key."""
    if "S1" in read_ids:
        return episode["expected_answer_t1"]
    stale = episode.get("stale_claim") or ""
    if "pending" in stale.lower():
        return "commissioning window pending survey confirmation"
    return "unknown status"


def run_sbr_session(
    episode: dict,
    branch: str,
    session_id: str,
    sample_index: int,
    session,
    ledger: Ledger,
    *,
    canonical_state: dict | None = None,
    probe: bool = False,
    elicit_answer: bool = False,
) -> dict:
    """One SBR session on one branch. Returns session summary dict.

    `elicit_answer=True` (real engines): after the terminal action the
    engine itself answers the task question from its reads, scored by the
    authored oracle. False (wire/mock): `synthesize_mock_answer`, disclosed
    as `answer_source: mock_synthesized`."""
    catalog = episode["catalog"]
    sort_rule = episode["catalog_sort"]
    budgets = episode["budgets"]
    cat_hash = catalog_hash(catalog, sort_rule)
    act_hash = action_space_hash()
    visible = sorted_surface_ids(catalog, sort_rule)

    foreground = ""
    if branch == "resumable_state" and canonical_state is not None:
        foreground = render_resumable_foreground(
            canonical_state, episode.get("stale_claim"))

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

    system = build_sbr_system(catalog, sort_rule, episode["question"])

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

    if elicit_answer:
        elicitation = (
            "The retrieval session is over. Using only the surfaces you "
            "read, answer the task question in one short phrase. Reply with "
            f"the answer text only, no JSON.\nTask: {episode['question']}\n"
            "Answer:")
        result = session.step(elicitation)
        answer = (result.raw_action or "").strip()
        answer_source = "engine_elicited"
    else:
        answer = synthesize_mock_answer(read_ids, episode)
        answer_source = "mock_synthesized"
    score = authored_oracle(answer, episode["expected_answer_t1"])
    quality_ok = score.score >= episode.get("quality_threshold", 1.0)
    ledger.write({
        "kind": "session_outcome",
        "branch": branch,
        "session_id": session_id,
        "sample_index": sample_index,
        "answer": answer,
        "answer_source": answer_source,
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
    *,
    canonical_state: dict | None = None,
    elicit_answer: bool = False,
) -> dict:
    """§17: K pilot draws on baseline (cold_reread) before Regime-S suite."""
    realizations: list[tuple[str, ...]] = []
    summaries = []
    for i in range(k):
        sid = f"probe-{uuid.uuid4().hex[:8]}"
        session = engine_factory(i)
        summary = run_sbr_session(
            episode, "cold_reread", sid, i, session, ledger,
            canonical_state=canonical_state, probe=True,
            elicit_answer=elicit_answer)
        realizations.append(summary["read_ids"])
        summaries.append(summary)
    unique = len(set(realizations))
    result = {
        "unique_realizations": unique,
        "dispersion_probe_k": k,
        "realizations": [list(r) for r in realizations],
        "summaries": summaries,
    }
    if unique == 1:
        ledger.write({
            "kind": "zero_dispersion_regime",
            "unique_realizations": unique,
            "dispersion_probe_k": k,
            "disclosure": "API-jitter masquerade refused — downgrade to point-mode (§17)",
        })
    return result


# Per-engine cold ignorance probe (§9; manifest probe_debt: the sbr-meridian
# fixture EXTENDS the meridian world — re-probe, do not inherit the v0.1
# attestation). Markers are fixture-specific.
SBR_PROBE_QUESTION = (
    "What is the current commissioning status of plan R at the Meridian "
    "relay junction, and what does the junction gate notice say about plan "
    "N? Answer from your own knowledge only — no context records are "
    "provided.")
_SBR_PRIOR_KNOWLEDGE_MARKERS = (
    "commissioning window now closed pending redesign",
    "plan r commissioning window pending survey confirmation",
    "plan n set aside gate reopens only on catalog change",
    "meridian relay junction status note",
)


def run_sbr_ignorance_probe(engine, engine_label: str | None = None) -> dict:
    from .oracle import _norm
    result = engine.run(SBR_PROBE_QUESTION, [], foreground_block="")
    norm = _norm(result.answer)
    knew = any(_norm(m) in norm for m in _SBR_PRIOR_KNOWLEDGE_MARKERS)
    label = engine_label or getattr(engine, "model", engine.backend_name)
    return {
        "knew": knew,
        "engine": label,
        "backend": engine.backend_name,
        "answer_excerpt": result.answer[:320],
        "probe_question": SBR_PROBE_QUESTION,
        "note": "cold probe before any sbr-meridian real-engine run — fold "
                "into manifest attestation (re-probed, not inherited)",
    }


def _regime_s_temperature(episode: dict) -> tuple[list[float], float | None]:
    """Pinned Regime-S temperature range and chosen value (midpoint)."""
    rng = episode.get("regime_s", {}).get("temperature_range")
    if not rng or len(rng) != 2:
        return [], None
    lo, hi = float(rng[0]), float(rng[1])
    return [lo, hi], (lo + hi) / 2.0


def _engine(engine_backend: str, model: str, base_url: str,
            temperature: float | None = None):
    if engine_backend == "claude":
        eng = ClaudeEngine(model)
        if temperature is not None:
            eng.temperature = temperature
        return eng
    if engine_backend == "local":
        return LocalEngine(model, base_url=base_url, temperature=temperature)
    return MockEngine()


def run_episode(
    episode: dict,
    ledger: Ledger,
    *,
    canonical_state: dict | None = None,
    engine=None,
    engine_backend: str = "mock",
    regime: str = "D",
    scripted_sessions: dict[str, list[list[str]]] | None = None,
    samples: int = 1,
) -> dict:
    """Full SBR episode: optional dispersion probe + both branches."""
    wire_mock = engine is None
    regime_s = episode.get("regime_s", {})
    k = regime_s.get("dispersion_probe_k", 5)
    probe_result = None
    effective_regime = regime
    temp_range, temperature = _regime_s_temperature(episode)
    elicit = not wire_mock and scripted_sessions is None
    pilot_variance = None
    n_required = None
    ci_target_unmet = False

    if regime == "S" and not wire_mock:
        def factory(i: int):
            return engine.start_session()
        probe_result = dispersion_probe(
            episode, factory, ledger, k, canonical_state=canonical_state,
            elicit_answer=elicit)
        if probe_result["unique_realizations"] == 1:
            effective_regime = "D"
        else:
            # §17 executed N-rule: N from pilot variance of cold effective
            # cost, targeting the precommitted CI half-width on the branch
            # mean gap; capped at the precommitted n_max — exceeding the cap
            # sets ci_target_unmet and the scorer refuses ALL behavioral
            # cells (fail-closed, symmetric).
            c_max = recompute_c_max(episode["budgets"])
            costs = [s["read_tokens"] if s["quality_ok"] else c_max
                     for s in probe_result["summaries"]]
            mu = sum(costs) / len(costs)
            var = sum((c - mu) ** 2 for c in costs) / (len(costs) - 1)
            pilot_variance = var
            h = regime_s.get("ci_halfwidth_tokens", 100)
            n_max = regime_s.get("n_max", 24)
            n_required = max(
                2, math.ceil((1.96 * math.sqrt(var) * math.sqrt(2) / h) ** 2))
            ci_target_unmet = n_required > n_max
            samples = min(n_required, n_max)

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
        "sbr_renderer_version": sbr_renderer_version(),
        "temperature_range": temp_range or None,
        # the ACTUAL engine temperature — a zero-dispersion downgrade changes
        # the effective regime, not what the engine sampled at
        "temperature": (getattr(engine, "temperature", None)
                        if engine is not None else 0.0),
        "seed": "unavailable",
        "n_derivation_rule": regime_s.get("n_rule"),
        "pilot_variance": pilot_variance,
        "ci_halfwidth_tokens": regime_s.get("ci_halfwidth_tokens"),
        "n_required": n_required,
        "n_max": regime_s.get("n_max"),
        "ci_target_unmet": ci_target_unmet,
        "dispersion_probe_k": regime_s.get("dispersion_probe_k"),
    }
    if probe_result:
        cfg["unique_realizations"] = probe_result["unique_realizations"]
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
                session = engine.start_session()
            summary = run_sbr_session(
                episode, branch, sid, i, session, ledger,
                canonical_state=canonical_state,
                elicit_answer=elicit and not (wire_mock
                                              or scripted_sessions is not None))
            branch_summaries[branch].append(summary)

    return {
        "probe": probe_result,
        "regime": effective_regime,
        "branch_summaries": branch_summaries,
    }


def run_and_score(episode_path: Path, ledger_path: Path | None = None,
                  *, engine=None, engine_backend: str = "mock",
                  regime: str = "D",
                  scripted_sessions: dict[str, list[list[str]]] | None = None,
                  samples: int = 1,
                  skip_mint: bool = False) -> dict:
    episode = json.loads(episode_path.read_text())
    fixture_dir = episode_path.parent
    population = json.loads((fixture_dir / "population.json").read_text())
    freeze_manifest = json.loads(
        (fixture_dir / "freeze_manifest.json").read_text())
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

    canonical_state = None
    if not skip_mint:
        mint = run_mint_spine(episode, population, freeze_manifest, ledger)
        if mint.get("halted"):
            return {"run": mint, "verdict": None, "ledger": str(ledger_path)}
        canonical_state = mint["canonical_state"]

    from .score_prf import PRFScorer

    outcome = run_episode(
        episode, ledger, canonical_state=canonical_state,
        engine=engine, engine_backend=engine_backend,
        regime=regime, scripted_sessions=scripted_sessions, samples=samples)
    events = ledger.rows()
    scorer = PRFScorer(
        population=population, freeze_manifest=freeze_manifest,
        events=events, episode=episode)
    verdict = scorer.score()
    ledger.write(verdict)
    return {"run": outcome, "verdict": verdict, "ledger": str(ledger_path)}


def main() -> int:
    ap = argparse.ArgumentParser(description="SBR fork runner (PRF v0.2)")
    ap.add_argument("episode", nargs="?", default=None,
                    help="episodes/prf/sbr-meridian/<episode>.json")
    ap.add_argument("--engine", choices=("mock", "local", "claude"),
                    default="mock")
    ap.add_argument("--model", default="claude-opus-4-8")
    ap.add_argument("--base-url", default="http://localhost:1234/v1")
    ap.add_argument("--regime", choices=("D", "S"), default="D")
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--temperature", type=float, default=None,
                    help="Regime-S temperature override; must sit inside the "
                         "episode's pinned range (refused otherwise)")
    ap.add_argument("--ledger", default=None,
                    help="ledger path override (write beside, never over, a "
                         "prior run's ledger)")
    ap.add_argument("--probe", action="store_true",
                    help="cold ignorance probe only; print attestation JSON")
    args = ap.parse_args()

    if args.probe:
        eng = _engine(args.engine, args.model, args.base_url)
        probe = run_sbr_ignorance_probe(eng, engine_label=args.model)
        print(json.dumps(probe, indent=2, sort_keys=True))
        return 0
    if not args.episode:
        ap.error("episode path required unless --probe")

    episode = json.loads(Path(args.episode).read_text())
    temp_range, temperature = _regime_s_temperature(episode)
    if args.regime == "S" and args.engine != "mock":
        temp = temperature if temperature is not None else 0.5
        if args.temperature is not None:
            if not temp_range or not (temp_range[0] <= args.temperature
                                      <= temp_range[1]):
                ap.error(f"--temperature {args.temperature} outside the "
                         f"pinned range {temp_range} — refused (§17)")
            temp = args.temperature
    else:
        temp = 0.0

    engine = None
    if args.engine != "mock":
        engine = _engine(args.engine, args.model, args.base_url,
                         temperature=temp)

    out = run_and_score(
        Path(args.episode), engine=engine, engine_backend=args.engine,
        regime=args.regime, samples=args.samples,
        ledger_path=Path(args.ledger) if args.ledger else None)
    print(json.dumps(out, indent=2, sort_keys=True))
    if out["verdict"] is None:
        return 1
    return 0 if out["verdict"]["cell"] != "confounded" else 1


if __name__ == "__main__":
    sys.exit(main())
