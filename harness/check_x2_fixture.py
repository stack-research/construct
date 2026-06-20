"""SPEC_X2 cost/state-dependence admission gate — fail-loud preflight (§5).

Refuses to run an X2 sequence unless the fixture can price prune on the cost
axis: non-trivial hot-store burden, world-scored quality floor, recurrence path
for over-prune, ledgered rematerialization (structural — enforced at run time),
and verifiably out-of-weights attestation for real-engine evidence.

Usage:
  uv run --no-project python -m harness.check_x2_fixture
  uv run --no-project python -m harness.check_x2_fixture episodes/x2/real/manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

from .fictional_corpus import load_fictional_entry
from .retrieval import rank_records
from .runner import BranchConfig, Episode, select_offers

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "episodes" / "x2" / "real" / "manifest.json"

Check = tuple[str, bool, str]


def _record_universe_hash(ep: Episode) -> str:
    payload = sorted((r.record_id, r.text, r.created_at) for r in ep.records)
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def _hot_tokens(records: list, hot_ids: set[str]) -> int:
    return sum(len(r.text.split()) for r in records if r.record_id in hot_ids)


def check_manifest(manifest_path: Path) -> list[Check]:
    checks: list[Check] = []
    m = json.loads(manifest_path.read_text())
    fid = m.get("fixture_id", manifest_path.stem)

    if not m.get("fictional"):
        checks.append(("fictional", False, "fixture must be fictional (out-of-weights)"))
    else:
        checks.append(("fictional", True, "fictional fixture declared"))

    if not m.get("out_of_weights"):
        checks.append(("out_of_weights", False, "out_of_weights must be true"))
    else:
        checks.append(("out_of_weights", True, "out-of-weights declared"))

    att = m.get("attestation", {})
    if not att.get("attested_by") or not att.get("attested_at"):
        checks.append(("attestation", False, "attestation.attested_by/at required"))
    else:
        checks.append(("attestation", True, f"attested by {att['attested_by']} @ {att['attested_at']}"))

    seq_paths = [ROOT / p for p in m["sequence"]]
    missing = [str(p) for p in seq_paths if not p.exists()]
    if missing:
        checks.append(("sequence_files", False, f"missing: {missing}"))
        return checks
    checks.append(("sequence_files", True, f"{len(seq_paths)} episode files present"))

    episodes = [Episode.load(p) for p in seq_paths]
    hashes = {_record_universe_hash(ep) for ep in episodes}
    if len(hashes) != 1:
        checks.append(("lineage_universe", False, "episodes differ in record universe"))
    else:
        checks.append(("lineage_universe", True, "identical record universe across sequence"))

    all_ids = {r.record_id for ep in episodes for r in ep.records}
    gate = m.get("cost_gate", {})
    for key in ("answer_record_core", "answer_record_recurrence", "prunable_distractor"):
        rid = gate.get(key)
        if not rid or rid not in all_ids:
            checks.append((key, False, f"cost_gate.{key}={rid!r} not in record universe"))
        else:
            checks.append((key, True, f"{key}={rid}"))

    # World-scored: every episode binds fictional_fact oracle.
    for ep in episodes:
        ref = ep.oracle_ref or {}
        if ref.get("kind") != "fictional_fact":
            checks.append(("fictional_oracle", False, f"{ep.episode_id}: oracle_ref.kind must be fictional_fact"))
            break
    else:
        checks.append(("fictional_oracle", True, "all episodes bind lab_fictional_corpus oracle (not M0 world-grounded)"))

    try:
        load_fictional_entry(m["corpus_entry"])
        checks.append(("corpus_load", True, m["corpus_entry"]))
    except ValueError as e:
        checks.append(("corpus_load", False, str(e)))

    # Cost ballast: full hot set must exceed minimum.
    ep0 = episodes[0]
    full_hot = _hot_tokens(ep0.records, all_ids)
    min_tok = gate.get("min_full_hot_tokens", 40)
    if full_hot < min_tok:
        checks.append(("cost_ballast", False, f"full hot_tokens={full_hot} < min {min_tok}"))
    else:
        checks.append(("cost_ballast", True, f"full hot_tokens={full_hot} (min {min_tok})"))

    pruned_hot = all_ids - {gate["prunable_distractor"]}
    pruned_tok = _hot_tokens(ep0.records, pruned_hot)
    if pruned_tok >= full_hot:
        checks.append(("prune_savings", False, "pruning distractor does not reduce hot_tokens"))
    else:
        checks.append(("prune_savings", True, f"prune saves {full_hot - pruned_tok} hot_tokens"))

    # Offer-dependence (static): top_k=1 must offer the answer record on core/recurrence.
    top_k = m.get("top_k", 1)
    with tempfile.TemporaryDirectory() as td:
        auth = Path(td) / "gate.authority.json"
        auth.write_text("{}\n")
        branch = BranchConfig(
            "gate", memory="governed", top_k=top_k, recency_weight=0.0,
            eligibility_threshold=0.0, authority_path=str(auth),
            inherited_record_ids=frozenset(all_ids),
        )
        core_ep = next(ep for ep in episodes if ep.episode_id != gate.get("recurrence_episode"))
        rec_ep = next(ep for ep in episodes if ep.episode_id == gate.get("recurrence_episode"))
        core_offered = {r.record_id for r, _ in select_offers(branch, core_ep)[0]}
        rec_offered = {r.record_id for r, _ in select_offers(branch, rec_ep)[0]}
    if gate["answer_record_core"] not in core_offered:
        checks.append(("offer_core", False, f"core does not offer {gate['answer_record_core']} at top_k={top_k}"))
    else:
        checks.append(("offer_core", True, f"core offers {gate['answer_record_core']}"))
    if gate["answer_record_recurrence"] not in rec_offered:
        checks.append(("offer_recurrence", False, f"recurrence does not offer {gate['answer_record_recurrence']}"))
    else:
        checks.append(("offer_recurrence", True, f"recurrence offers {gate['answer_record_recurrence']}"))

    # Recurrence ranks backup above wifi for its question.
    ranked = rank_records(rec_ep.question, rec_ep.records, 0.0, similarity_backend="lexical_tfidf")
    if not ranked or ranked[0][0].record_id != gate["answer_record_recurrence"]:
        top = ranked[0][0].record_id if ranked else None
        checks.append(("recurrence_rank", False, f"backup not top-ranked (got {top})"))
    else:
        checks.append(("recurrence_rank", True, "recurrence question ranks backup first"))

    return checks


def main() -> int:
    p = argparse.ArgumentParser(description="X2 cost/state-dependence admission gate")
    p.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    args = p.parse_args()
    path = Path(args.manifest)
    if not path.exists():
        print(f"FAIL: manifest not found: {path}", file=sys.stderr)
        return 1

    checks = check_manifest(path)
    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL':4s}  {name}: {detail}")
    if failed:
        print(f"\nGATE REFUSED: {len(failed)} check(s) failed — fixture cannot enter run_x2 for real evidence.",
              file=sys.stderr)
        return 1
    print(f"\nGATE OPEN: {path.name} passes cost/state-dependence preflight.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
