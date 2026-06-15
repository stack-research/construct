"""Fork-group runner: one engine, forked memory conditions, diffed behavior.

Held constant within a fork group (plan §4A): episode inputs, model + params,
prompt template, tool availability (none in Stage A), episode ordering, oracle.
Only the memory-condition config differs per branch.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .authority import AuthorityStore
from .corpus import load_entry
from .engine import ClaudeEngine, LocalEngine, MockEngine, render_foreground, renderer_version
from .ledger import Ledger
from .oracle import authored_oracle, world_checked_oracle
from .records import Record
from .retrieval import pairwise_similarity, rank_records


@dataclass
class BranchConfig:
    branch_id: str  # "L0" | "L1" | "L2" | "L2y" | "L2s" | "L3"
    memory: str  # "none" | "naive" | "governed" | "construct_aware"
    top_k: int = 3
    recency_weight: float = 0.3
    similarity_backend: str = "lexical_tfidf"  # or "embedding_nomic"
    # governed lane only:
    eligibility_threshold: float = 0.25  # scalar relevance*trust*authority must clear this
    authority_path: str | None = None  # sidecar file; read on every offer decision (R2)
    # SPEC_V1X boundary mechanisms (governed lanes only):
    live_input_yield: bool = False
    supersession_policy: bool = False
    contention_threshold: float = 0.6  # design-time calibrated per episode, recorded in run_config
    # SPEC_M1 §6: per-branch store override. None = full store; a frozenset
    # makes this lane an heir (it sees only the inherited records).
    inherited_record_ids: frozenset | None = None


@dataclass
class Episode:
    episode_id: str
    question: str
    expected_answer: str
    records: list[Record] = field(default_factory=list)
    expected_winner_condition: str | None = None  # named pre-run, from a rubric cell
    foreground_data: list[dict] = field(default_factory=list)  # SPEC_V1X §1
    authored_contention: dict = field(default_factory=dict)  # validation only; offer path never reads it
    recency_weight: float | None = None  # episode-level override, disclosed in run_config
    contention_threshold: float | None = None  # design-time calibrated, disclosed
    eligibility_threshold: float | None = None  # episode-level override (SPEC_M0): real prose
    #                                              has lower lexical density than synthetic probes
    supersession_cycle_members: frozenset = frozenset()  # detected at load; policy disabled for these
    oracle_ref: dict = field(default_factory=dict)  # SPEC_M0 §4: un-authored oracle binding
    pair_id: str | None = None  # SPEC_M0 §3: C-1/C-2 pairs share configs, enforced
    # SPEC_M1 §1: temporal fork metadata (gen-2 episodes carry gen-1 path).
    m1_pair_id: str | None = None
    m1_generation: int | None = None
    m1_gen1_episode: str | None = None
    m1_i1_tier: str | None = None  # content | timing | metadata
    m1_attacker_record_id: str | None = None
    m1_gen1_top_k: int | None = None  # optional gen-1 offer budget override
    m1_counterfactual_include_rank_budget: bool = False  # SPEC_M1 §2 exception:
    #   the cell declares rank-budget the mechanism (I1-timing)
    m1_active_record_id: str | None = None  # H1: inherited active record gen-2 must surface
    m1_poison_record_id: str | None = None  # H2: cautionary record under test
    m1_pruned_record_id: str | None = None  # H-loses: deliberately pruned record
    m2_earned_record_id: str | None = None  # SPEC_M2: the harness-minted earned record E2 forks on
    channel_trust: dict[str, float] | None = None  # SPEC_M3: optional per-channel trust prior for yield gate

    @classmethod
    def load(cls, path: Path) -> "Episode":
        d = json.loads(Path(path).read_text())
        recs = [Record(**{**r, "supersedes": tuple(r.get("supersedes", ()))}) for r in d.get("records", [])]
        fg = d.get("foreground_data", [])
        if len(fg) > 1:
            # SPEC_V1X §5: multi-datum arbitration is undefined in v1.x — reject loudly.
            raise ValueError(f"{d['episode_id']}: multiple foreground_data entries are not supported")
        cycle_members = _detect_supersession_cycles(recs)
        return cls(
            d["episode_id"], d["question"], d["expected_answer"], recs,
            d.get("expected_winner_condition"),
            fg, d.get("authored_contention", {}),
            d.get("recency_weight"), d.get("contention_threshold"),
            d.get("eligibility_threshold"),
            cycle_members,
            d.get("oracle_ref", {}), d.get("pair_id"),
            d.get("m1_pair_id"), d.get("m1_generation"), d.get("m1_gen1_episode"),
            d.get("m1_i1_tier"), d.get("m1_attacker_record_id"), d.get("m1_gen1_top_k"),
            d.get("m1_counterfactual_include_rank_budget", False),
            d.get("m1_active_record_id"), d.get("m1_poison_record_id"), d.get("m1_pruned_record_id"),
            d.get("m2_earned_record_id"),
            d.get("channel_trust"),
        )

    def score(self, answer: str):
        """Oracle dispatch (SPEC_M0 §4): world-checked when the episode binds a
        corpus entry, authored otherwise. The corpus entry is re-loaded (and
        re-hashed) at scoring time so the row pins what was actually scored."""
        if self.oracle_ref:
            return world_checked_oracle(
                answer,
                load_entry(self.oracle_ref["corpus_entry"]),
                representativeness=self.oracle_ref.get("representativeness", ""),
                corpus_confidence=self.oracle_ref.get("corpus_confidence", 0.9),
                rule_confidence=self.oracle_ref.get("rule_confidence", 0.8),
            )
        return authored_oracle(answer, self.expected_answer)


def _detect_supersession_cycles(records: list[Record]) -> frozenset:
    """Load-time DFS over supersedes edges; members of any cycle get the
    policy disabled (SPEC_V1X enforcement: loud fallback, never silent repair)."""
    edges = {r.record_id: list(r.supersedes) for r in records}
    in_cycle: set[str] = set()
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in edges}
    stack_path: list[str] = []

    def dfs(node: str) -> None:
        color[node] = GRAY
        stack_path.append(node)
        for nxt in edges.get(node, []):
            if nxt not in color:
                continue  # dangling link: ignore here, harmless to offer logic
            if color[nxt] == GRAY:
                in_cycle.update(stack_path[stack_path.index(nxt):])
            elif color[nxt] == WHITE:
                dfs(nxt)
        stack_path.pop()
        color[node] = BLACK

    for n in edges:
        if color[n] == WHITE:
            dfs(n)
    return frozenset(in_cycle)


def _norm_output(answer: str) -> str:
    return re.sub(r"\s+", " ", answer.strip().lower())


def assert_pair_config_identity(episodes_branches: list[tuple["Episode", list[BranchConfig]]]) -> None:
    """SPEC_M0 §3 enforcement (cursor, v0.1): episodes sharing a pair_id must run
    identical branch configs except supersession_policy — C-2 cannot be quietly
    'fixed' by tuning L2s between cells. Called by the suite runner before any
    scored run that includes paired episodes. Fails loudly."""
    pairs: dict[str, list[tuple[str, list[dict]]]] = {}
    for ep, branches in episodes_branches:
        if ep.pair_id:
            stripped = [
                {k: v for k, v in b.__dict__.items() if k != "supersession_policy"}
                for b in branches
            ]
            pairs.setdefault(ep.pair_id, []).append((ep.episode_id, stripped))
    for pair_id, members in pairs.items():
        first_id, first_cfg = members[0]
        for ep_id, cfg in members[1:]:
            if cfg != first_cfg:
                raise ValueError(
                    f"pair {pair_id}: branch configs diverge between {first_id} and {ep_id} "
                    "beyond supersession_policy — the pair no longer prices the mechanism"
                )


def select_offers(
    branch: BranchConfig, episode: Episode
) -> tuple[list[tuple[Record, str]], list[tuple[Record, str]], int]:
    """Return (offered, withheld, governance_steps) with per-record reasons."""
    if branch.inherited_record_ids is not None and branch.memory != "none":
        # Heir lanes see only the inherited store (SPEC_M1 §1). Records outside
        # it are not "withheld" — they do not exist for this lane.
        episode = replace(
            episode,
            records=[r for r in episode.records if r.record_id in branch.inherited_record_ids],
        )
    if branch.memory == "none":
        return [], [(r, "branch_has_no_memory") for r in episode.records], 0
    if branch.memory == "naive":
        # Episode-level recency_weight override applies to ALL memory lanes —
        # the ranker is part of fork identity, not a treatment difference.
        rw = episode.recency_weight if episode.recency_weight is not None else branch.recency_weight
        ranked = rank_records(
            episode.question, episode.records, rw,
            similarity_backend=branch.similarity_backend,
        )
        offered = [(r, "within_rank_budget") for r, _ in ranked[: branch.top_k]]
        withheld = [(r, "below_rank_budget") for r, _ in ranked[branch.top_k:]]
        return offered, withheld, 0
    if branch.memory in ("governed", "construct_aware"):
        # Candidate-set pipeline (SPEC_V1X gate order, post-review):
        #   eligibility -> live-input yield -> supersession among survivors -> top_k
        # One withholding reason per record, first applicable gate wins.
        # Relevance uses the same ranker as L1 so lane diffs isolate governance.
        authority = AuthorityStore(Path(branch.authority_path))
        rw = episode.recency_weight if episode.recency_weight is not None else branch.recency_weight
        ranked = rank_records(
            episode.question, episode.records, rw,
            similarity_backend=branch.similarity_backend,
        )
        steps = 0
        withheld: list[tuple[Record, str]] = []

        # Gate 1: eligibility (relevance × trust × authority). Episode may
        # override the threshold (SPEC_M0): real-world prose records have lower
        # lexical density than synthetic probes, so the scalar is part of fork
        # identity (applied to every governed lane), not a treatment difference.
        elig = episode.eligibility_threshold if episode.eligibility_threshold is not None else branch.eligibility_threshold
        survivors: list[Record] = []
        for r, relevance in ranked:
            score = relevance * r.trust * authority.get(r.record_id)
            steps += 2  # eligibility evaluation + authority read
            if score < elig:
                withheld.append((r, "eligibility_below_threshold"))
            else:
                survivors.append(r)
        steps += 1  # threshold gate decision

        # Gate 2: live-input yield (store-vs-world). A record contending with
        # a fresher foreground datum yields. Runs BEFORE supersession so a
        # superseder must survive yield before it can bury its predecessor.
        if branch.live_input_yield and episode.foreground_data and survivors:
            datum = episode.foreground_data[0]
            ct = episode.contention_threshold if episode.contention_threshold is not None else branch.contention_threshold
            sims = pairwise_similarity(
                [r.text for r in survivors], datum["text"], branch.similarity_backend
            )
            channel_ok = True
            if episode.channel_trust is not None:
                channel_ok = episode.channel_trust.get(datum.get("channel", ""), 0.0) >= elig
            still: list[Record] = []
            for r, sim in zip(survivors, sims):
                steps += 1  # contention check
                if sim >= ct and r.created_at < datum["observed_at"] and channel_ok:
                    withheld.append((r, f"yields_to_live_input:{datum['datum_id']}"))
                else:
                    still.append(r)
            survivors = still

        # Gate 3: supersession among surviving candidates. B buries A only if
        # B itself survived eligibility and yield (transfer-on-arrival, B1).
        if branch.supersession_policy and survivors:
            surviving_ids = {r.record_id for r in survivors}
            buried: dict[str, str] = {}  # record_id -> superseder id
            for b in survivors:
                if b.record_id in episode.supersession_cycle_members:
                    continue  # policy disabled for cycle members (loud fallback upstream)
                # follow chains: everything in b's transitive closure is buried by b
                frontier = list(b.supersedes)
                seen: set[str] = set()
                while frontier:
                    steps += 1  # supersession check
                    a_id = frontier.pop()
                    if a_id in seen or a_id in episode.supersession_cycle_members:
                        continue
                    seen.add(a_id)
                    if a_id in surviving_ids and a_id not in buried:
                        buried[a_id] = b.record_id
                    nxt = next((r for r in episode.records if r.record_id == a_id), None)
                    if nxt is not None:
                        frontier.extend(nxt.supersedes)
            still = []
            for r in survivors:
                if r.record_id in buried:
                    withheld.append((r, f"superseded_by:{buried[r.record_id]}"))
                else:
                    still.append(r)
            survivors = still

        # Gate 4: budget
        offered = [(r, "eligibility_pass") for r in survivors[: branch.top_k]]
        withheld.extend((r, "below_rank_budget") for r in survivors[branch.top_k:])
        return offered, withheld, steps
    raise ValueError(f"unknown memory condition: {branch.memory}")


def _ablation_aggregate(changed_flags: list[bool]) -> tuple[bool, int]:
    """Multi-sample ablation aggregation (SPEC_M2 v0.2). Given per-sample "did the
    outcome change vs the resident's actual answer" flags, return (outcome_changed by
    strict majority, index of a representative sample on the majority side) — so the
    recorded ablation_run row's answer/oracle_score agrees with the majority vote
    rather than a possibly-dissenting last draw (codex P3)."""
    outcome_changed = sum(changed_flags) > len(changed_flags) / 2
    rep_idx = max((i for i, c in enumerate(changed_flags) if c == outcome_changed),
                  default=len(changed_flags) - 1)
    return outcome_changed, rep_idx


def run_fork_group(
    episode: Episode,
    branches: list[BranchConfig],
    ledger: Ledger,
    engine_backend: str = "mock",
    model: str = "claude-opus-4-8",
    base_url: str = "http://localhost:1234/v1",
    run_id: str | None = None,
    skip_ablation: bool = False,
    ablation_samples: int = 1,
    elicit_decisiveness: bool = False,
) -> dict[str, Any]:
    # Ablation is load-bearing for credit assignment and attribution, not an
    # optional diagnostic (cursor). Skipping is wire/dev only; a scored
    # episode (expected_winner_condition set) must hard-fail without it.
    if skip_ablation and episode.expected_winner_condition:
        raise ValueError(
            f"episode {episode.episode_id} carries expected_winner_condition="
            f"{episode.expected_winner_condition!r}; scored episodes require ablation attribution"
        )
    if ablation_samples < 1:
        raise ValueError(f"ablation_samples must be >= 1, got {ablation_samples}")
    run_id = run_id or uuid.uuid4().hex[:12]
    fork_group_id = uuid.uuid4().hex[:12]
    if engine_backend == "claude":
        engine = ClaudeEngine(model)
    elif engine_backend == "local":
        engine = LocalEngine(model, base_url=base_url)
    else:
        engine = MockEngine()

    ledger.write({
        "kind": "run_config",
        "run_id": run_id,
        "fork_group_id": fork_group_id,
        "episode_id": episode.episode_id,
        "engine_backend": engine.backend_name,
        "model": engine.model,
        "similarity_backends": sorted({b.similarity_backend for b in branches if b.memory != "none"}),
        "foreground_renderer_version": renderer_version(),
        "episode_overrides": {  # disclosed: episode-level values that shape the offer path
            k: v for k, v in {
                "recency_weight": episode.recency_weight,
                "contention_threshold": episode.contention_threshold,
                "eligibility_threshold": episode.eligibility_threshold,
                "pair_id": episode.pair_id,
            }.items() if v is not None
        },
        "branches": [
            {**b.__dict__, "inherited_record_ids": (
                sorted(b.inherited_record_ids) if b.inherited_record_ids is not None else None
            )}
            for b in branches
        ],
        "disclosures": (
            ["engine is a deterministic mock: this run is a wire smoke test, not evidence about memory"]
            if engine.backend_name == "mock" else []
        ) + (
            ["similarity is lexical TF-IDF, not a learned embedding"]
            if any(b.similarity_backend == "lexical_tfidf" and b.memory != "none" for b in branches) else []
        ) + [
            (f"authority credit uses {ablation_samples}-sample ablation (majority vote over the counterfactual)"
             if ablation_samples > 1 else
             "authority credit uses single-sample ablation: stochastic engines can misattribute")
            + "; load-bearing means influential, not correct"
        ],
        "cost_tiebreak_window": 0.10,  # rubric §1 sensitivity parameter, recorded per codex review
    })

    # Built once per fork group, identical for every branch (SPEC_V1X enforcement).
    foreground_block = render_foreground(episode.foreground_data)
    if episode.supersession_cycle_members:
        ledger.write({
            "kind": "supersession_cycle_detected", "run_id": run_id,
            "fork_group_id": fork_group_id, "episode_id": episode.episode_id,
            "cycle_members": sorted(episode.supersession_cycle_members),
            "note": "policy disabled for cycle members; ordinary eligibility applies",
        })

    results: dict[str, Any] = {}
    for branch in branches:
        offered, withheld, governance_steps = select_offers(branch, episode)
        offered_texts = [r.text for r, _ in offered]

        for r, reason in offered:
            ledger.write({
                "kind": "offer", "run_id": run_id, "fork_group_id": fork_group_id,
                "episode_id": episode.episode_id, "branch_id": branch.branch_id,
                "record_id": r.record_id, "reason": reason,
                "attention_cost_tokens": len(r.text.split()),
                "predeclared_usage": r.predeclared_usage,
                "vocabulary_kind": r.vocabulary_kind,
            })
        for r, reason in withheld:
            ledger.write({
                "kind": "withholding", "run_id": run_id, "fork_group_id": fork_group_id,
                "episode_id": episode.episode_id, "branch_id": branch.branch_id,
                "record_id": r.record_id, "reason": reason,
                "predeclared_usage": r.predeclared_usage,
                "vocabulary_kind": r.vocabulary_kind,
            })

        er = engine.run(episode.question, offered_texts, foreground_block)
        oracle = episode.score(er.answer)

        # L3 only: elicit claimed usage AFTER the answer (codex B2 — the label
        # is never injected before the task). Recorded, never trusted.
        usage_claims = None
        if branch.memory == "construct_aware" and offered:
            uc = engine.elicit_usage(
                episode.question, [(r.record_id, r.text) for r, _ in offered], er.answer,
                foreground_block,
            )
            usage_claims = {
                "agent_claimed_usage": [
                    {"record_id": rid, "claimed": label} for rid, label in sorted(uc.claims.items())
                ],
                "parse_error": uc.parse_error,
                "elicitation_latency_ms": uc.latency_ms,
                "elicitation_prompt_tokens": uc.prompt_tokens,
                "elicitation_completion_tokens": uc.completion_tokens,
            }
            if elicit_decisiveness:
                # SPEC_M2 v0.2: the resident's *decisiveness* claim, elicited separately
                # from the role audit — RS-loses refutes a TRUE claim the fork's ablation
                # says is false (performed continuity), never mere "I considered it."
                lb = engine.elicit_load_bearing(
                    episode.question, [(r.record_id, r.text) for r, _ in offered], er.answer,
                    foreground_block,
                )
                usage_claims["agent_claimed_load_bearing"] = [
                    {"record_id": rid, "claimed_decisive": v} for rid, v in sorted(lb.claimed.items())
                ]
                usage_claims["loadbearing_parse_error"] = lb.parse_error

        ledger.write({
            "kind": "branch_run", "run_id": run_id, "fork_group_id": fork_group_id,
            "episode_id": episode.episode_id, "branch_id": branch.branch_id,
            "latency_ms": er.latency_ms,
            "governance_steps": governance_steps,
            "prompt_tokens": er.prompt_tokens, "completion_tokens": er.completion_tokens,
            "ablation_calls": 0 if skip_ablation else len(offered) * ablation_samples,
            "branch_output": {"answer": er.answer, "tool_calls": []},
            "oracle": oracle.__dict__,  # SPEC_M2: per-branch outcome on its own run
            #   row, not only in the pairwise diff_outcome — a single-branch
            #   session (E1) must ledger its scored failure for the mint to read.
            **(usage_claims or {}),
        })

        # Mechanism attribution by single-record ablation, on EVERY memory
        # lane (kagi blocker 3 + codex blocker 1): the episode is re-run with
        # each offered record removed, and the ledger records whether the
        # outcome changes. An outcome-only oracle cannot distinguish
        # right-for-the-right-reasons from right-by-luck; ablation rows can —
        # a naive lane's failure is attributable to the poison only if
        # removing the poison flips the outcome. For governed lanes the same
        # rows drive credit assignment: a record receives the outcome's
        # authority delta only if it is load-bearing; co-offered passengers
        # get delta 0, and a superseded record the engine merely overcame is
        # recorded as present but earns nothing. Known limit, disclosed in
        # run_config: single-sample ablation on a stochastic engine can
        # misattribute; load-bearing means influential, never correct.
        load_bearing: dict[str, bool] = {}
        if offered and not skip_ablation:
            for i, (r, _) in enumerate(offered):
                reduced_texts = [rr.text for j, (rr, _) in enumerate(offered) if j != i]
                # Multi-sample the counterfactual (SPEC_M2 v0.2): the branch's actual
                # answer is one real decision, but "what happens without this record"
                # is distributional on a stochastic engine. Sample it ablation_samples
                # times; load-bearing = the outcome reliably changes (strict majority).
                # ablation_samples=1 reproduces the original single-sample behavior.
                samples = [
                    (ab, episode.score(ab.answer))
                    for ab in (engine.run(episode.question, reduced_texts, foreground_block)
                               for _ in range(ablation_samples))
                ]
                changed_flags = [o.score != oracle.score for _, o in samples]
                outcome_changed, rep_idx = _ablation_aggregate(changed_flags)
                load_bearing[r.record_id] = outcome_changed
                rep_ab, rep_oracle = samples[rep_idx]  # representative on the majority side
                ledger.write({
                    "kind": "ablation_run", "run_id": run_id, "fork_group_id": fork_group_id,
                    "episode_id": episode.episode_id, "branch_id": branch.branch_id,
                    "ablated_record_id": r.record_id,
                    "latency_ms": rep_ab.latency_ms,
                    "prompt_tokens": rep_ab.prompt_tokens, "completion_tokens": rep_ab.completion_tokens,
                    "branch_output": {"answer": rep_ab.answer, "tool_calls": []},
                    "oracle_score": rep_oracle.score,
                    "baseline_oracle_score": oracle.score,  # SPEC_M1 v0.2: direction
                    "outcome_changed": outcome_changed,
                    "ablation_samples": len(samples),
                    "outcome_changed_fraction": sum(changed_flags) / len(changed_flags),
                    "ablated_oracle_scores": [o.score for _, o in samples],
                })

        authority_updates = []
        if branch.memory in ("governed", "construct_aware") and offered and not skip_ablation:
            # No attribution -> no authority movement. Skipped-ablation wire
            # runs never mutate the sidecar.
            store = AuthorityStore(Path(branch.authority_path))
            delta_magnitude = 0.1 if oracle.score >= 1.0 else -0.1
            for r, _ in offered:
                delta = delta_magnitude if load_bearing[r.record_id] else 0.0
                upd = store.apply(r.record_id, delta, oracle.confidence)
                upd.update({
                    "load_bearing": load_bearing[r.record_id],
                    "credit_method": "single_record_ablation",
                    "served_beneficiary": "task",
                    "risk_beneficiary": "user",
                    "branch_id": branch.branch_id,
                })
                authority_updates.append(upd)

        results[branch.branch_id] = {
            "answer": er.answer, "oracle": oracle, "authority_updates": authority_updates,
        }

    branch_ids = [b.branch_id for b in branches]
    for i in range(len(branch_ids)):
        for j in range(i + 1, len(branch_ids)):
            a, b = branch_ids[i], branch_ids[j]
            out_a, out_b = results[a]["answer"], results[b]["answer"]
            diverged = _norm_output(out_a) != _norm_output(out_b)
            ledger.write({
                "kind": "diff_outcome", "run_id": run_id, "fork_group_id": fork_group_id,
                "episode_id": episode.episode_id, "branches": [a, b],
                "diverged": diverged,
                "diff_summary": "outputs differ after normalization" if diverged else "outputs identical after normalization",
                "expected_winner_condition": episode.expected_winner_condition,
                "oracle_scores": {
                    a: results[a]["oracle"].__dict__,
                    b: results[b]["oracle"].__dict__,
                },
                "authority_updates": results[a]["authority_updates"] + results[b]["authority_updates"],
            })

    return {
        "run_id": run_id,
        "fork_group_id": fork_group_id,
        "scores": {bid: results[bid]["oracle"].score for bid in branch_ids},
        "answers": {bid: results[bid]["answer"] for bid in branch_ids},
    }
