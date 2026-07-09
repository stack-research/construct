"""Phase-0 admission packet runner (fourth-family pins P-A1'..P-A7, 2026-07-09).

Answers ONE question per candidate engine, before any Regime-S contact and
before any fourth-family authoring: does this engine's COLD free-route
behavior on the existing sealed Greenreach v0.4 baseline make the pay-window
arithmetically detectable at n_max=24?

The packet is an admission gate, never evidence (C3 discipline, P-A6): it
gates the cold branch only, says nothing about resumable routing, and no
Regime-S claim may cite it. Every scored quantity is either computed by the
same code path the live instrument uses (pilot_n_rule, run_sbr_session's
conjunctive quality, recompute_a_i's shared version fork) or ledgered
verbatim so any seat can recompute it from the row (P-A7).

Predicate (P-A1', all four legs required for `admitted`):
  outer   cold_pass_rate >= 0.8 over ALL K pilot draws          (P-A2)
  (1)     mean_decoy_reads_on_successes >= 5                    (P-A3)
  (2')    n_required <= n_max, per-branch, via pilot_n_rule     (P-A4)
  (3)     est. mean_eff(cold) - (a_i + 3*L_bar) > ci_halfwidth
`admission_marginal` = inequalities (1)+(2')+(3) pass but the outer gate
fails — disclosed, never admitted.

Documentation-only closed form (grok's missed-pin #2 — NEVER scored from):
  var_H = ((n_s-1)/(K-1)) * s2_D + (K/(K-1)) * p_hat*(1-p_hat)*(D_bar-c_max)^2
The K/(K-1) Bessel factor is why the population bound diverges at K=5.
"""
from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from .ledger import Ledger
from .mint_frontier_state import recompute_a_i
from .run_sbr import (REPO, check_manifest, dispersion_probe, pilot_n_rule,
                      run_calibration_gate, run_mint_spine,
                      run_sbr_ignorance_probe, _engine, _tokens)
from .sbr_util import recompute_c_max

PIN_ROUND = "fourth-family pins P-A1'..P-A7 (adopted 2026-07-09)"


def admission_metrics(episode: dict, summaries: list[dict],
                      a_i: int) -> dict:
    """Compute every P-A quantity from pilot summaries. Pure; wire-testable."""
    regime_s = episode.get("regime_s", {})
    k_total = len(summaries)
    c_max = recompute_c_max(episode["budgets"])
    h = regime_s.get("ci_halfwidth_tokens", 100)
    n_max = regime_s.get("n_max", 24)
    dispositive = set(episode["dispositive_leg_ids"])

    # P-A2: denominator is ALL pilot draws; refusals/illegal actions are
    # non-passes by construction (quality_ok=false).
    successes = [s for s in summaries if s["quality_ok"]]
    pass_rate = len(successes) / k_total

    # cost vector exactly as run_episode builds it (quality-priced at c_max)
    costs = [s["read_tokens"] if s["quality_ok"] else c_max
             for s in summaries]
    pilot_variance, n_required, ci_target_unmet = pilot_n_rule(
        costs, h, n_max)

    # P-A3: decoy reads condition on quality_ok=true draws only
    decoy_reads = [
        sum(1 for sid in s["read_ids"] if sid not in dispositive)
        for s in successes]
    mean_decoy_reads = (
        sum(decoy_reads) / len(decoy_reads) if decoy_reads else None)

    # (3) effect size against canonical-render tokens (P-A5): L_bar from the
    # catalog's canonical surface tokens, a_i from the shared version fork
    # (recompute_a_i — the caller derives it; review F1 killed the 0.2-only
    # counter here).
    # priced the way run_sbr_session prices reads — _tokens over the surface
    # TEXT, never the authored tokens field (grok's next-second-way warning,
    # discharged same-day: the authored field is gate-checked metadata, the
    # recompute is what the instrument charges)
    l_bar = (sum(_tokens(episode["catalog"][leg]["text"])
                 for leg in dispositive) / len(dispositive))
    d_bar = (sum(s["read_tokens"] for s in successes) / len(successes)
             if successes else None)
    mean_eff_cold_est = (pass_rate * d_bar + (1 - pass_rate) * c_max
                         if d_bar is not None else float(c_max))
    resumable_floor = a_i + 3 * l_bar
    effect_est = mean_eff_cold_est - resumable_floor

    legs = {
        "outer_pass_rate": pass_rate >= 0.8,
        "ineq1_decoy_reads": (mean_decoy_reads is not None
                              and mean_decoy_reads >= 5),
        "ineq2_n_required": not ci_target_unmet,
        "ineq3_effect_size": effect_est > h,
    }
    inner = all(v for k, v in legs.items() if k != "outer_pass_rate")
    return {
        "pilot_k": k_total,
        "cold_pass_rate": pass_rate,
        "pilot_cost_vector": costs,        # P-A7: verbatim, recomputable
        "pilot_variance": pilot_variance,  # Bessel var_H (pilot_n_rule)
        "n_required": n_required,
        "n_max": n_max,
        "ci_halfwidth_tokens": h,
        "ci_target_unmet": ci_target_unmet,
        "n_rule_scope": "per-branch (P-A4); this row is the cold branch",
        "mean_decoy_reads_on_successes": mean_decoy_reads,
        "decoy_reads_definition": (
            "count of non-dispositive reads per success (includes ballast, "
            "not only decoy siblings) — review F3 naming disclosure"),
        "decoy_reads_per_success": decoy_reads,
        "success_cost_mean": d_bar,
        "a_i": a_i,
        "l_bar_canonical": l_bar,
        "resumable_floor": resumable_floor,
        "mean_eff_cold_est": mean_eff_cold_est,
        "effect_size_est": effect_est,
        "legs": legs,
        "verdict": ("admitted" if legs["outer_pass_rate"] and inner
                    else "admission_marginal" if inner
                    else "admission_refused"),
    }


def run_admission_packet(episode_path: Path, *, engine=None,
                         engine_label: str = "mock",
                         ledger_path: Path | None = None,
                         scripted_factory=None,
                         skip_probe: bool = False) -> dict:
    """One admission packet: probe -> gate -> mint -> calibration -> K pilot
    -> admission_packet row. `scripted_factory(i)` supplies wire-test
    sessions; a real engine supplies its own."""
    episode = json.loads(episode_path.read_text())
    fixture_dir = episode_path.parent
    population = json.loads((fixture_dir / "population.json").read_text())
    freeze_manifest = json.loads(
        (fixture_dir / "freeze_manifest.json").read_text())
    k = episode.get("regime_s", {}).get("dispersion_probe_k", 5)

    # slash-bearing model ids (openai/gpt-oss-20b) must not nest the default
    # ledger under runs/prf/ where flat *.jsonl scans miss it (review, codex)
    safe_label = engine_label.replace("/", "-")
    ledger_path = ledger_path or (
        REPO / "runs" / "prf" /
        f"{episode['episode_id']}.admission-{safe_label}.jsonl")
    if ledger_path.exists():
        raise SystemExit(
            f"refusing to overwrite {ledger_path} — write beside, never over")
    ledger = Ledger(ledger_path)

    gate_checks = check_manifest(fixture_dir / "manifest.json")
    gate_failed = [name for name, ok, _ in gate_checks if not ok]
    if gate_failed:
        ledger.write({"kind": "gate_refused", "failed": gate_failed})
        return {"halted": "gate_refused", "failed": gate_failed,
                "ledger": str(ledger_path)}
    ledger.write({"kind": "gate_open", "checks": len(gate_checks),
                  "pin_round": PIN_ROUND})

    # probe-before-contact is family law; the admission packet runs it LIVE
    # and ledgers the result (composer's attested-not-computed catch) — it
    # never trusts a handed-in attestation. The QUESTION AND MARKERS are
    # fixture-owned (review F1, codex/gemini: the meridian default tests the
    # wrong fictional world in both directions) — a real engine is refused
    # outright when the fixture supplies no probe contract.
    if engine is not None and not skip_probe:
        manifest = json.loads((fixture_dir / "manifest.json").read_text())
        contract = manifest.get("probe_contract") or episode.get(
            "probe_contract")
        if not (contract and contract.get("question")
                and contract.get("prior_knowledge_markers")):
            ledger.write({"kind": "admission_refused",
                          "reason": "probe_contract_missing",
                          "disclosure": "fixture supplies no ignorance-probe "
                                        "contract; refusing rather than "
                                        "probing the wrong world"})
            return {"halted": "admission_refused",
                    "reason": "probe_contract_missing",
                    "ledger": str(ledger_path)}
        probe = run_sbr_ignorance_probe(
            engine, engine_label=engine_label,
            question=contract["question"],
            markers=tuple(contract["prior_knowledge_markers"]))
        ledger.write({"kind": "admission_ignorance_probe",
                      "probe_contract_source": "fixture", **probe})
        if probe["knew"] is not False:
            ledger.write({"kind": "admission_refused",
                          "reason": "ignorance_probe"})
            return {"halted": "admission_refused",
                    "reason": "ignorance_probe", "ledger": str(ledger_path)}

    mint = run_mint_spine(episode, population, freeze_manifest, ledger)
    if mint.get("halted"):
        return {**mint, "ledger": str(ledger_path)}
    canonical_state = mint["canonical_state"]
    a_i = recompute_a_i(canonical_state,
                        episode.get("instrument_version", "0.2"))

    # §30-2 calibration precondition — precondition, NEVER evidence (C3)
    if engine is not None:
        cal = run_calibration_gate(episode, canonical_state, ledger,
                                   engine=engine, engine_label=engine_label)
        if not cal.get("passed"):
            ledger.write({"kind": "admission_refused",
                          "reason": "calibration_gate"})
            return {"halted": "admission_refused",
                    "reason": "calibration_gate",
                    "ledger": str(ledger_path)}

    if scripted_factory is not None:
        factory = scripted_factory
    else:
        from .engine import sbr_action_instruction
        instr = sbr_action_instruction(
            episode.get("instrument_version", "0.4"))

        def factory(i: int):
            return engine.start_session(action_instruction=instr)

    probe_result = dispersion_probe(
        episode, factory, ledger, k, canonical_state=canonical_state,
        elicit_answer=(engine is not None))

    metrics = admission_metrics(episode, probe_result["summaries"], a_i)
    row = {
        "kind": "admission_packet",
        "engine": engine_label,
        "episode_id": episode["episode_id"],
        "instrument_version": episode.get("instrument_version"),
        "pin_round": PIN_ROUND,
        "unique_realizations": probe_result["unique_realizations"],
        # self-auditing sampling params (review, composer F1/codex)
        "temperature": (getattr(engine, "temperature", None)
                        if engine is not None else 0.0),
        "temperature_range": episode.get("regime_s", {}).get(
            "temperature_range"),
        # P-A6: this packet gates the COLD branch only; C3 applies.
        "resumable_routing_untested": True,
        "scope_disclosure": (
            "admission gate, never evidence — gates cold-branch "
            "detectability only; says nothing about resumable free-route "
            "behavior; no Regime-S claim may cite this row (P-A6/C3)"),
        "variance_note": (
            "pilot_variance is the Bessel-corrected sample estimator "
            "(pilot_n_rule, the run_sbr code path); the closed-form "
            "population bound UNDERSTATES it by K/(K-1) on the fail-mass "
            "term at pilot scale — documentation only, never scored"),
        "wire_test": engine is None,
        **metrics,
    }
    if engine is None:
        row["disclosure"] = ("mock admission runner — wire test, never an "
                             "admission")
    ledger.write(row)
    return {"packet": row, "ledger": str(ledger_path)}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="PRF Phase-0 admission packet (pins P-A1'..P-A7)")
    ap.add_argument("episode",
                    help="episodes/prf/greenreach-release/ep-*.json")
    ap.add_argument("--engine", choices=("mock", "local", "claude"),
                    default="mock")
    # NO default model: the candidate engine is an ARMING decision (dan's,
    # per the fold routing) — a default would quietly pre-commit it
    # (review, gemini). Required whenever --engine is not mock.
    ap.add_argument("--model", default=None)
    ap.add_argument("--base-url", default="http://localhost:1234/v1")
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--ledger", default=None)
    args = ap.parse_args()

    engine = None
    label = "mock"
    if args.engine != "mock":
        if not args.model:
            ap.error("--model is required with a real engine (no default: "
                     "the candidate engine is an arming decision)")
        episode = json.loads(Path(args.episode).read_text())
        rng = episode.get("regime_s", {}).get("temperature_range")
        temp = args.temperature
        if temp is None and rng:
            temp = (float(rng[0]) + float(rng[1])) / 2.0
        if temp is not None and rng and not (rng[0] <= temp <= rng[1]):
            ap.error(f"--temperature {temp} outside pinned range {rng}")
        if args.engine == "local" and "localhost" not in args.base_url:
            # remote OpenAI-compatible endpoint (dan's GPT-5 ruling
            # 2026-07-09): key from env only — never a flag, never ledgered
            from .engine import LocalEngine
            import os
            key = os.environ.get("OPENAI_API_KEY")
            if not key:
                ap.error("OPENAI_API_KEY not set for a remote endpoint")
            engine = LocalEngine(args.model, base_url=args.base_url,
                                 api_key=key, temperature=temp,
                                 token_param="max_completion_tokens")
        else:
            engine = _engine(args.engine, args.model, args.base_url,
                             temperature=temp)
        label = args.model

    out = run_admission_packet(
        Path(args.episode), engine=engine, engine_label=label,
        ledger_path=Path(args.ledger) if args.ledger else None)
    print(json.dumps(out, indent=2, sort_keys=True))
    packet = out.get("packet")
    return 0 if packet and packet["verdict"] == "admitted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
