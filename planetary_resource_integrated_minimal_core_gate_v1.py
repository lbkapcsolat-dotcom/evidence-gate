from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_integration_readiness_freeze_v1 as freeze_gate
import planetary_resource_integrated_minimal_core_v1 as integrated
import planetary_resource_process_coefficient_validity_v1 as validity
import planetary_resource_process_manifest_version_v1 as process_version
import planetary_resource_storage_host_topology_bind_v1 as storage_topology


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__INTEGRATED_MINIMAL_PLANETARY_CORE_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__INTEGRATED_MINIMAL_PLANETARY_CORE.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__INTEGRATED_MINIMAL_PLANETARY_CORE_RECEIPT.json"
)


def sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha256(payload: dict[str, Any]) -> str:
    body = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _expect_code(expected: str, fn) -> dict[str, Any]:
    try:
        fn()
    except Exception as exc:
        code = getattr(exc, "code", None)
        observed = code.value if hasattr(code, "value") else code
        if observed != expected:
            raise AssertionError(
                f"expected {expected}, got {observed}: {type(exc).__name__}"
            ) from exc
        return {"expected": expected, "observed": observed, "passed": True}
    raise AssertionError(f"expected {expected}, got PASS")


def verify_freeze(contract: dict[str, Any]) -> dict[str, str]:
    p = contract["predecessor"]
    observed = {
        "integration_freeze_manifest_sha256": sha256_file(
            "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__INTEGRATION_READINESS_FREEZE.json"
        ),
        "integration_freeze_verifier_sha256": sha256_file(
            "planetary_resource_integration_readiness_freeze_v1.py"
        ),
        "integration_freeze_tests_sha256": sha256_file(
            "test_planetary_resource_integration_readiness_freeze_v1.py"
        ),
    }
    for key, got in observed.items():
        if got != p[key]:
            raise AssertionError(f"freeze predecessor changed: {key} {got} != {p[key]}")

    freeze_receipt = freeze_gate.run_freeze()
    receipt_sha = canonical_sha256(freeze_receipt)
    if receipt_sha != p["integration_freeze_receipt_sha256"]:
        raise AssertionError("integration-readiness freeze receipt changed")
    observed["integration_freeze_receipt_sha256"] = receipt_sha
    return observed


def run_mutation_checks() -> dict[str, Any]:
    fx = integrated.build_fixture()

    wrong_version = replace(fx["process"], manifest_version="V2")
    version_check = _expect_code(
        "HOLD_PROCESS_MANIFEST_VERSION_MISMATCH",
        lambda: process_version.process_coupling_with_manifest_version(
            wrong_version,
            fx["activity"],
            fx["electricity_nodes"],
            target_layer=core.ResourceLayer.ELECTRICITY,
            requested_interval=fx["requested_interval"],
            expected_process_manifest_version="V1",
        ),
    )

    expired_rows = tuple(
        replace(
            row,
            valid_from="2026-10-01T00:00:00Z",
            valid_to="2026-10-02T12:59:59Z",
        )
        for row in fx["process"].coefficient_rows
    )
    expired_process = replace(fx["process"], coefficient_rows=expired_rows)
    validity_check = _expect_code(
        "HOLD_PROCESS_COEFFICIENT_EXPIRED",
        lambda: process_version.process_coupling_with_manifest_version(
            expired_process,
            fx["activity"],
            fx["electricity_nodes"],
            target_layer=core.ResourceLayer.ELECTRICITY,
            requested_interval=fx["requested_interval"],
            expected_process_manifest_version="V1",
        ),
    )

    bad_topology = storage_topology.ActiveTopologySnapshot(
        layer=core.ResourceLayer.ELECTRICITY,
        manifest_version="V1",
        nodes=(
            core.NodeManifest(
                "E9",
                core.ResourceLayer.ELECTRICITY,
                "ELECTRICITY_ZONE",
                "V1",
            ),
        ),
    )
    topology_check = _expect_code(
        "HOLD_STORAGE_HOST_NODE_MISSING",
        lambda: storage_topology.storage_transition_with_topology_bind(
            fx["storage"],
            bad_topology,
            fx["time_basis"],
            fx["stock"],
            fx["charge"],
            fx["discharge"],
            fx["self_loss"],
        ),
    )

    return {
        "PROCESS_VERSION_MISMATCH_REJECTED": version_check,
        "PROCESS_VALIDITY_EXPIRED_REJECTED": validity_check,
        "STORAGE_HOST_TOPOLOGY_MISMATCH_REJECTED": topology_check,
    }


def run_gate() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("integrated minimal core gate mismatch")
    if contract["integration_mode"] != "FROZEN_SYNTHETIC_PHYSICAL_FIXTURE":
        raise AssertionError("integration mode changed")
    if contract["layers"] != ["ELECTRICITY", "NATURAL_GAS", "FRESHWATER"]:
        raise AssertionError("resource-layer scope changed")
    if any(contract["fences"].values()):
        raise AssertionError(f"scope fence enabled: {contract['fences']!r}")

    freeze = verify_freeze(contract)
    state = integrated.run_integrated_system()

    if state["counts"] != contract["counts"]:
        raise AssertionError("integrated scope counts changed")
    if state["layers"] != contract["layers"]:
        raise AssertionError("integrated resource layers changed")
    if state["interval"]["interval_id"] != contract["interval"]["interval_id"]:
        raise AssertionError("integrated interval changed")

    expected_balances = {
        "ELECTRICITY": "0",
        "NATURAL_GAS": "0",
        "FRESHWATER": "0",
    }
    observed_balances = {
        layer: row["value"] for layer, row in state["balances"].items()
    }
    if observed_balances != expected_balances:
        raise AssertionError(f"nominal balances do not close: {observed_balances!r}")

    if state["storage"]["next_stock"]["value"] != "524":
        raise AssertionError("storage next stock changed")
    if state["storage"]["node_side_delta_rate"]["value"] != "-1/2":
        raise AssertionError("storage node-side balance contribution changed")
    if state["process"]["outputs"]["ELECTRICITY"]["value"] != "4":
        raise AssertionError("electricity process output changed")
    if state["process"]["outputs"]["NATURAL_GAS"]["value"] != "-10":
        raise AssertionError("gas process output changed")

    for layer, row in state["balances"].items():
        if row["uncertainty"]["kind"] == "EXACT":
            raise AssertionError(f"{layer} balance uncertainty was silently lost")
    if state["storage"]["next_stock"]["uncertainty"]["kind"] == "EXACT":
        raise AssertionError("storage uncertainty was silently lost")

    if not state["full_evidence_lineage_preserved"]:
        raise AssertionError("full evidence lineage not preserved")
    if state["real_source_bindings_consumed"]:
        raise AssertionError("real source binding entered synthetic integration")
    if state["new_source_ingest"] or state["real_multi_source_fusion"]:
        raise AssertionError("source-ingest/fusion fence violated")
    if state["core_patch_required"] or state["new_domain_math_added"]:
        raise AssertionError("integration required forbidden core/domain changes")

    mutations = run_mutation_checks()

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_INTEGRATED_MINIMAL_PLANETARY_CORE_RECEIPT_V1",
        "gate_id": GATE_ID,
        "contract_sha256": sha256_file(str(CONTRACT_PATH)),
        "integration_module_sha256": sha256_file(
            "planetary_resource_integrated_minimal_core_v1.py"
        ),
        "verified_integration_freeze": freeze,
        "integrated_state": state,
        "integrated_state_sha256": state["state_sha256"],
        "nominal_balance_closure": observed_balances,
        "mutation_checks": mutations,
        "uncertainty_end_to_end": True,
        "full_evidence_lineage_preserved": True,
        "process_version_guard_exercised": True,
        "process_validity_guard_exercised": True,
        "storage_topology_guard_exercised": True,
        "single_integrated_state_receipt": True,
        "core_patch_required": False,
        "new_domain_math_added": False,
        "new_source_ingest": False,
        "real_multi_source_fusion": False,
        "fences": contract["fences"],
        "verdict": contract["verdict_target"],
    }


def write_receipt() -> tuple[dict[str, Any], str]:
    receipt = run_gate()
    body = json.dumps(
        receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"
    OUT_PATH.write_text(body, encoding="utf-8")
    return receipt, hashlib.sha256(body.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    receipt, sha = write_receipt()
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    print("INTEGRATED_MINIMAL_CORE_RECEIPT_SHA256=" + sha)
