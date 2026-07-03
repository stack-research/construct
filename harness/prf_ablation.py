"""§4c-1 ablation — the COMPUTED structural-dependency leg, shared by the
offer-time mint and the fixture gate so they agree by construction
(build-review fix #2/#3, 2026-07-03).

The build review (codex/composer/hermes/gemini/glm, unanimous) killed the
attested `ablation_witness_adequate` flag and gemini's cut decided the honest
v0.1 shape:

  Leg 1 — structural dependency (computed, HERE, hard gate): withholding the
    obligation-covered surfaces from the witness route must CHANGE the derived
    obligation batch (`obligation_set_hash` mismatch). Unchanged batch =
    obligations are ghost rules = decorative -> the offer-time mint refuses
    `frontier_mint_refused(fixture_obligations_decorative)`.

  Leg 2 — empirical adequacy (DISCLOSED real-engine debt, mock-bypassed):
    whether the witness's downstream continuation quality actually degrades
    without those reads is model-dependent; the mock layer cannot compute it.
    v0.1 mock conservatively assumes the ablated witness is inadequate (it
    never refuses on this leg) and discloses that in `run_config`. The leg
    lifts to a computed check only under the §6 determinism policy with a real
    engine + live oracle. No minted row claims adequacy.

cursor's checkpoint-based adequacy simulation was reviewed and NOT shipped:
under ablation the batch shrinks, the checkpoint trivializes, and every
genuinely causal episode would be refused (gemini's paradox, glm's audit).
"""

from __future__ import annotations

from .derive_live_obligations import derive_live_obligations

ADEQUACY_DEBT_DISCLOSURE = (
    "ablation empirical-adequacy leg is a real-engine debt: mock assumes the "
    "ablated witness is inadequate and never refuses on that leg "
    "(SPEC_PAUSE_RESUME §4c-1 leg 2)")


def structural_dependency(population: dict, freeze_manifest: dict,
                          witness_rows: list[dict], seam_id: str) -> dict:
    """Derive twice — full witness route, then the route with every
    obligation-covered surface withheld — and compare batch hashes. Everything
    in the result is computed; nothing is read from the episode."""
    dry = derive_live_obligations(population, freeze_manifest, witness_rows,
                                  seam_id)
    covered = sorted({sid for o in dry["obligations"]
                      for sid in o["source_read_ids"]})
    ablated_rows = [r for r in witness_rows
                    if r["surface_id"] not in covered]
    ablated = derive_live_obligations(population, freeze_manifest,
                                      ablated_rows, seam_id)
    dry_hash = dry["batch"]["obligation_set_hash"]
    ablated_hash = ablated["batch"]["obligation_set_hash"]
    return {
        "dry_obligation_set_hash": dry_hash,
        "ablated_obligation_set_hash": ablated_hash,
        "structural_dependency_ok": dry_hash != ablated_hash,
        "covered_surfaces": covered,
        "adequacy_leg": "real_engine_debt_mock_bypassed",
    }
