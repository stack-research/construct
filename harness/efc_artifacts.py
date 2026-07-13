"""Typed identities and hashes for the EFC artifacts actually implemented —
sealed Part I §3.2/§5.2; brief item 11; corrections B1/B4.

Two identity layers, never conflated (B4):

- **semantic contract hashes** — canonical bytes of each artifact's typed
  contract payload (template data, event order, closed schemas, ceilings);
  these are the identities envelopes and manifests pin;
- **module source hashes** — diagnostic only, reported separately; a module
  hash is never a substitute for a semantic contract hash.

The final check-contract identity is PENDING until the population-pinned
comparison rule artifact exists (B1): only the adapter contract is hashable
here, and no provisional final hash is minted.

Only artifacts that exist in this workspace get an identity. Absent seats'
artifacts (fixture content, oracle snapshots, engine decoding contracts, the
manifest instance, the comparison rule) are deliberately unrepresented:
emitting a hash for an unimplemented artifact would be an invented
placeholder value (design §11).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from harness import efc_contracts as c
from harness.efc_carrier import V0_PREDICATE_FEATURE_BINDINGS
from harness.efc_check import (check_adapter_contract_hash,
                               pending_check_contract_identity)
from harness.efc_controller import CONTROLLER_ID, controller_contract_hash
from harness.efc_packet import packet_loader_contract_hash
from harness.efc_renderer import (RENDERER_ID, foreground_template_hash,
                                  renderer_contract_hash)
from harness.efc_runner import RUNNER_ID, runner_contract_hash

_HARNESS = Path(__file__).resolve().parent


def _module_hash(name: str) -> str:
    return hashlib.sha256((_HARNESS / name).read_bytes()).hexdigest()


def predicate_contract_hash() -> str:
    """Identity of the §2.1 predicate as pinned bindings, not source bytes."""
    return hashlib.sha256(json.dumps(
        V0_PREDICATE_FEATURE_BINDINGS, sort_keys=True,
        separators=(",", ":")).encode("utf-8")).hexdigest()


def implemented_artifact_identities() -> dict:
    return {
        "part_i_spec_sha256": c.PART_I_SPEC_SHA256,
        "renderer": {
            "id": RENDERER_ID,
            "contract_sha256": renderer_contract_hash(),
            "foreground_template_sha256": foreground_template_hash(),
            "module_sha256_diagnostic": _module_hash("efc_renderer.py"),
        },
        "controller": {
            "id": CONTROLLER_ID,
            "contract_sha256": controller_contract_hash(),
            "module_sha256_diagnostic": _module_hash("efc_controller.py"),
        },
        "check": {
            "id": c.CHECK_ID,
            "adapter_contract_sha256": check_adapter_contract_hash(),
            # B1: no final identity until the population-pinned rule exists
            "check_contract_identity": pending_check_contract_identity(),
            "module_sha256_diagnostic": _module_hash("efc_check.py"),
        },
        "extractor": {
            "id": "efc_trigger_v0",
            # the semantic identity is the predicate contract; the source
            # hash is diagnostic only (resolution G)
            "predicate_contract_sha256": predicate_contract_hash(),
            "module_sha256_diagnostic": _module_hash("efc_trigger.py"),
        },
        "packet_loader": {
            "id": "efc_packet_v0",
            "contract_sha256": packet_loader_contract_hash(),
            "module_sha256_diagnostic": _module_hash("efc_packet.py"),
        },
        "runner": {
            "id": RUNNER_ID,
            "contract_sha256": runner_contract_hash(),
            "module_sha256_diagnostic": _module_hash("efc_runner.py"),
        },
    }


if __name__ == "__main__":
    print(json.dumps(implemented_artifact_identities(), indent=2))
