"""M-1 bootstrap-contract conformance check: scripts that fail loudly, never prose.

Two halves, matching the ROADMAP M-1 oracle:
  (a) static — the contract (AGENTS.md) is intact: every declared source exists,
      the token budget holds (contract-bloat tripwire), and no probe content has
      leaked into the bootstrap read set (contract-not-content, mechanically).
  (b) behavioral — a bootstrap manifest's offer-boundary decisions on the fixed
      probe set match ground truth. Ground truth is computed live by
      select_offers, never stored: the harness is the answer key, so the key
      cannot drift from the mechanism it tests.

Usage:
  uv run --no-project python -m harness.check_contract                     # static only
  uv run --no-project python -m harness.check_contract --manifest FILE     # + behavioral
  uv run --no-project python -m harness.check_contract --show-truth        # debug aid*

  *Consulting --show-truth (or episodes/probes/CALIBRATION.md) before answering
   the probes defeats them; the manifest must then declare method:
   harness_assisted. Mechanically unenforceable — disclosed, not pretended away.

Manifest schema (JSON):
  {
    "agent": "<name>",
    "briefing": "manual" | "contract_only",
    "method": "closed_book" | "harness_assisted",
    "contract_sha256": "<sha256 of AGENTS.md as read>",
    "read_order": ["AGENTS.md", ...],          # what was actually read, in order
    "probe_decisions": {
      "<episode_id>": {"offered": ["<record_id>", ...],
                        "withheld": {"<record_id>": "<exact reason string>"}}
    }
  }

M-1 success legs (kagi): briefing=manual is the briefed BASELINE; contract_only
+ closed_book is a CANDIDATE leg; harness_assisted runs are disclosed and do not
count. Results append to runs/bootstrap/conformance.jsonl (harness-written).

Known limit, disclosed: substrate threads are part of the bootstrap read set but
are NOT scanned for probe leakage — a review thread that discusses specific
probe decisions burns the probe set, and the remedy is rotating probe content,
not editing the immutable thread.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

from .ledger import Ledger
from .runner import BranchConfig, Episode, select_offers

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "AGENTS.md"
PROBE_DIR = ROOT / "episodes" / "probes"
CALIBRATION = PROBE_DIR / "CALIBRATION.md"
CONFORMANCE_LEDGER = ROOT / "runs" / "bootstrap" / "conformance.jsonl"

TOKEN_BUDGET = 4000  # approx-tokens = chars // 4; the contract-bloat tripwire
LINK = re.compile(r"\[[^\]]+\]\(([^)#]+)\)")
REASON_VOCAB = (
    "eligibility_below_threshold", "yields_to_live_input", "superseded_by",
    "below_rank_budget", "eligibility_pass", "within_rank_budget",
    "branch_has_no_memory",
)

Check = tuple[str, bool, str]


def _section(text: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def parse_contract(text: str) -> tuple[list[str], list[str]]:
    """(required read order, task-conditional sources), both as repo-relative paths.
    Derived from the contract on every run so the contract stays authoritative."""
    sec = _section(text, "Required read order")
    head, _, tail = sec.partition("Open only when")
    required = ["AGENTS.md"]  # item 1 names itself without a link
    for line in head.splitlines():
        if re.match(r"^\d+\.\s", line.strip()):
            m = LINK.search(line)
            if m:
                required.append(m.group(1))
    conditional = [m.group(1) for m in LINK.finditer(tail)]
    return required, conditional


def probe_paths() -> list[Path]:
    return sorted(PROBE_DIR.glob("probe-*.json"))


def ground_truth(path: Path, authority_path: str) -> dict:
    d = json.loads(path.read_text())
    ep = Episode.load(path)
    pb = d["probe_branch"]
    branch = BranchConfig(
        branch_id="L2ys-probe", memory="governed", top_k=pb["top_k"],
        recency_weight=0.0, similarity_backend=pb["similarity_backend"],
        eligibility_threshold=pb["eligibility_threshold"],
        authority_path=authority_path,  # fresh temp path: authority neutral 1.0
        live_input_yield=pb["live_input_yield"],
        supersession_policy=pb["supersession_policy"],
    )
    offered, withheld, _ = select_offers(branch, ep)
    return {
        "offered": [r.record_id for r, _ in offered],
        "withheld": {r.record_id: reason for r, reason in withheld},
    }


def all_ground_truth() -> dict[str, dict]:
    with tempfile.TemporaryDirectory() as td:
        neutral = str(Path(td) / "neutral_authority.json")
        return {p.stem: ground_truth(p, neutral) for p in probe_paths()}


def static_checks() -> list[Check]:
    checks: list[Check] = []
    text = CONTRACT.read_text()
    required, conditional = parse_contract(text)

    missing = [p for p in required + conditional if not (ROOT / p).exists()]
    checks.append((
        "S1_declared_sources_exist", not missing,
        f"{len(required)} required + {len(conditional)} conditional"
        + (f"; MISSING: {missing}" if missing else ""),
    ))
    checks.append((
        "S2_substrate_trace_exists", (ROOT / ".substrate" / "threads").is_dir(),
        ".substrate/threads/",
    ))

    approx = len(text) // 4
    checks.append((
        "S3_token_budget", approx <= TOKEN_BUDGET,
        f"AGENTS.md ~{approx} approx-tokens of budget {TOKEN_BUDGET}",
    ))

    probes = probe_paths()
    ids_ok = bool(probes)
    detail = f"{len(probes)} probes"
    truth: dict[str, dict] = {}
    try:
        truth = all_ground_truth()
        for p in probes:
            d = json.loads(p.read_text())
            if d["episode_id"] != p.stem:
                ids_ok, detail = False, f"{p.name}: episode_id != filename"
            t = truth.get(p.stem, {})
            if not t.get("offered") or not t.get("withheld"):
                ids_ok = False
                detail = f"{p.stem}: ground truth must offer >=1 AND withhold >=1 to discriminate"
    except Exception as e:  # a probe that cannot be scored is a failed check, not a crash
        ids_ok, detail = False, f"ground truth failed: {e}"
    checks.append(("S4_probe_integrity", ids_ok, detail))

    leaks = []
    probe_tokens: list[str] = []
    for p in probes:
        d = json.loads(p.read_text())
        probe_tokens.append(d["episode_id"])
        probe_tokens.extend(r["record_id"] for r in d["records"])
    for doc in required + conditional:
        path = ROOT / doc
        if not path.exists():
            continue
        body = path.read_text()
        leaks.extend(f"{doc}:{tok}" for tok in probe_tokens if tok in body)
    checks.append((
        "S5_no_probe_content_in_read_set", not leaks,
        "probe ids absent from contract-reachable docs" + (f"; LEAKED: {leaks}" if leaks else ""),
    ))

    answer_leaks = []
    for p in probes:
        body = p.read_text()
        answer_leaks.extend(f"{p.name}:{r}" for r in REASON_VOCAB if r in body)
    checks.append((
        "S6_probe_files_carry_no_decisions", not answer_leaks,
        "no reason vocabulary inside probe files" + (f"; FOUND: {answer_leaks}" if answer_leaks else ""),
    ))
    return checks


def manifest_checks(manifest: dict) -> list[Check]:
    checks: list[Check] = []
    text = CONTRACT.read_text()
    required, _ = parse_contract(text)

    want_keys = {"agent", "briefing", "method", "contract_sha256", "read_order", "probe_decisions"}
    missing_keys = want_keys - manifest.keys()
    shape_ok = (
        not missing_keys
        and manifest.get("briefing") in ("manual", "contract_only")
        and manifest.get("method") in ("closed_book", "harness_assisted")
        and isinstance(manifest.get("read_order"), list)
        and isinstance(manifest.get("probe_decisions"), dict)
    )
    checks.append((
        "M1_manifest_schema", shape_ok,
        f"missing keys: {sorted(missing_keys)}" if missing_keys else "all fields present",
    ))
    if not shape_ok:
        return checks

    sha = hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
    checks.append((
        "M2_contract_hash_current", manifest["contract_sha256"] == sha,
        "manifest read this AGENTS.md" if manifest["contract_sha256"] == sha
        else f"stale bootstrap: manifest {manifest['contract_sha256'][:12]} vs current {sha[:12]}",
    ))

    ro = manifest["read_order"]
    declared_required = [p for p in ro if p in required]
    order_ok = bool(ro) and ro[0] == "AGENTS.md" and declared_required == required
    detail = "required sources read in contract order"
    if not order_ok:
        detail = f"declared {declared_required} vs required {required} (AGENTS.md must be first)"
    cal = str(CALIBRATION.relative_to(ROOT))
    if cal in ro:
        order_ok, detail = False, f"{cal} read during bootstrap — calibration is off the read path"
    # Prior manifests are a complete answer key; the whole directory is off the
    # pre-answer read path (hole found by the gpt-5.5 stranger leg, 2026-06-12).
    leaked = next((p for p in ro if p.startswith("runs/bootstrap/")), None)
    if leaked:
        order_ok, detail = False, f"{leaked} read during bootstrap — runs/bootstrap/ holds prior manifests (an answer key)"
    if manifest["briefing"] == "contract_only" and not any(p.startswith(".substrate/") for p in ro):
        order_ok, detail = False, "contract_only bootstrap must declare a substrate thread read"
    checks.append(("M3_read_order", order_ok, detail))

    truth = all_ground_truth()
    decided = set(manifest["probe_decisions"])
    coverage_ok = decided == set(truth)
    checks.append((
        "M4_probe_coverage", coverage_ok,
        f"all {len(truth)} probes decided" if coverage_ok
        else f"missing {sorted(set(truth) - decided)}; extra {sorted(decided - set(truth))}",
    ))

    for pid in sorted(truth):
        got = manifest["probe_decisions"].get(pid)
        if got is None:
            checks.append((f"M5_behavior:{pid}", False, "no decision recorded"))
            continue
        want = truth[pid]
        off_ok = sorted(got.get("offered", [])) == sorted(want["offered"])
        wh_ok = got.get("withheld", {}) == want["withheld"]
        detail = "decisions match harness ground truth"
        if not off_ok:
            detail = f"offered {sorted(got.get('offered', []))} vs truth {sorted(want['offered'])}"
        elif not wh_ok:
            detail = f"withheld {got.get('withheld', {})} vs truth {want['withheld']}"
        checks.append((f"M5_behavior:{pid}", off_ok and wh_ok, detail))
    return checks


def _success_leg(manifest: dict) -> str:
    if manifest.get("briefing") == "manual":
        return "baseline"
    if manifest.get("method") == "harness_assisted":
        return "disclosed_assist"
    return "candidate"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, help="bootstrap manifest JSON to verify")
    ap.add_argument("--show-truth", action="store_true",
                    help="print ground truth (pre-answer use => method: harness_assisted)")
    args = ap.parse_args(argv)

    if args.show_truth:
        print(json.dumps(all_ground_truth(), indent=2, sort_keys=True))
        return 0

    checks = static_checks()
    manifest = None
    if args.manifest:
        manifest = json.loads(args.manifest.read_text())
        checks.extend(manifest_checks(manifest))

    for check_id, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {check_id} — {detail}")
    failed = [c for c, ok, _ in checks if not ok]
    passed = not failed
    print(f"\nCONFORMANCE: {'PASS' if passed else 'FAIL'} "
          f"({len(checks) - len(failed)}/{len(checks)} checks)")

    if manifest is not None:
        leg = _success_leg(manifest)
        if leg == "disclosed_assist":
            print("NOTE: method=harness_assisted — run is disclosed and does not count toward M-1 success.")
        Ledger(CONFORMANCE_LEDGER).write({
            "row": "conformance_result",
            "agent": manifest.get("agent", "?"),
            "briefing": manifest.get("briefing", "?"),
            "method": manifest.get("method", "?"),
            "m1_success_leg": leg,
            "contract_sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
            "manifest_path": str(args.manifest),
            "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
            "checks": {c: ok for c, ok, _ in checks},
            "failed": failed,
            "passed": passed,
        })
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
