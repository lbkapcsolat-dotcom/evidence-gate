from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
from typing import Any, Callable

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_process_typed_dimensional_closure_gate_v1 as typed_process_gate
import planetary_resource_end_to_end_uncertainty_gate_v1 as e2e_gate
import planetary_resource_process_coefficient_uncertainty_gate_v1 as coefficient_uncertainty_gate
import planetary_resource_process_coefficient_validity_gate_v1 as coefficient_validity_gate
import planetary_resource_process_manifest_version_gate_v1 as manifest_version_gate
import planetary_resource_storage_self_loss_typed_gate_v1 as self_loss_gate
import planetary_resource_storage_host_topology_bind_gate_v1 as storage_topology_gate
import planetary_resource_generic_source_adapter_gate_v1 as generic_adapter_gate
import planetary_resource_generic_source_adapter_conformance_v1 as conformance
import planetary_resource_source_adapter_subsystem_freeze_v1 as source_freeze
import planetary_resource_first_real_source_canary_v1 as water_canary
import planetary_resource_second_real_source_canary_v1 as electricity_canary
import planetary_resource_third_real_source_gas_canary_v1 as gas_canary


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__INTEGRATION_READINESS_FREEZE_V1"
)
MANIFEST_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__INTEGRATION_READINESS_FREEZE.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__INTEGRATION_READINESS_FREEZE_RECEIPT.json"
)


def sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha256(payload: dict[str, Any]) -> str:
    body = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load_manifest() -> dict[str, Any]:
    m = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if m["gate_id"] != GATE_ID:
        raise AssertionError("integration readiness gate id mismatch")
    if m["freeze_status"] != "CORE_FROZEN_FOR_INTEGRATION":
        raise AssertionError("core not declared frozen for integration")
    if m["deferred_nonblocking"] != [
        "STORAGE_PARAMETER_UNCERTAINTY",
        "AUDIT_VECTOR_PROVENANCE_TYPING",
    ]:
        raise AssertionError("deferred nonblocking set changed")
    if m["core_change_policy"] != (
        "NO_NEW_CORE_GAP_WORK_UNLESS_INTEGRATION_FINDS_BREAKAGE"
    ):
        raise AssertionError("core change policy changed")
    if m["next_target"] != "INTEGRATED_MINIMAL_PLANETARY_CORE_V1":
        raise AssertionError("integration next target changed")
    if m["next_target_count"] != 1:
        raise AssertionError("there must be exactly one next target")
    if any(m["fences"].values()):
        raise AssertionError(f"integration freeze fence enabled: {m['fences']!r}")
    return m


def verify_file(path: str, expected: str, label: str) -> str:
    got = sha256_file(path)
    if got != expected:
        raise AssertionError(f"{label} changed: {got} != {expected}")
    return got


def verify_core_kernel(m: dict[str, Any]) -> dict[str, Any]:
    pin = m["pins"]["balance_and_boundary_kernel"]
    got = verify_file(pin["source_path"], pin["sha256"], "core kernel")
    required = pin["required_symbols"]
    missing = [name for name in required if not hasattr(core, name)]
    if missing:
        raise AssertionError(f"required core symbols missing: {missing!r}")
    matrix = core.run_validation_matrix()
    passed = sum(1 for row in matrix if row.passed)
    if len(matrix) != 40 or passed != 40:
        raise AssertionError(f"legacy core matrix changed: {passed}/{len(matrix)}")
    return {
        "source_sha256": got,
        "required_symbols": required,
        "legacy_matrix": {"count": 40, "pass": 40},
    }


def verify_contract_module_and_receipt(
    pin: dict[str, Any],
    run: Callable[[], dict[str, Any]],
    *,
    label: str,
) -> dict[str, str]:
    out = {
        "contract_sha256": verify_file(
            pin["contract_path"], pin["contract_sha256"], f"{label} contract"
        ),
        "module_sha256": verify_file(
            pin["module_path"], pin["module_sha256"], f"{label} module"
        ),
    }
    receipt_sha = canonical_sha256(run())
    if receipt_sha != pin["receipt_sha256"]:
        raise AssertionError(
            f"{label} receipt changed: {receipt_sha} != {pin['receipt_sha256']}"
        )
    out["receipt_sha256"] = receipt_sha
    return out


def verify_successor_pins(m: dict[str, Any]) -> dict[str, Any]:
    pins = m["pins"]
    out = {}
    out["typed_process_coupling"] = verify_contract_module_and_receipt(
        pins["typed_process_coupling"],
        typed_process_gate.run_gate,
        label="typed process coupling",
    )
    out["end_to_end_uncertainty"] = verify_contract_module_and_receipt(
        pins["end_to_end_uncertainty"],
        e2e_gate.run_gate,
        label="end-to-end uncertainty",
    )
    out["process_coefficient_uncertainty"] = verify_contract_module_and_receipt(
        pins["process_coefficient_uncertainty"],
        coefficient_uncertainty_gate.run_gate,
        label="process coefficient uncertainty",
    )
    out["process_coefficient_validity"] = verify_contract_module_and_receipt(
        pins["process_coefficient_validity"],
        coefficient_validity_gate.run_gate,
        label="process coefficient validity",
    )
    out["process_manifest_version_enforcement"] = verify_contract_module_and_receipt(
        pins["process_manifest_version_enforcement"],
        manifest_version_gate.run_gate,
        label="process manifest version",
    )
    out["typed_storage_self_loss"] = verify_contract_module_and_receipt(
        pins["typed_storage_self_loss"],
        self_loss_gate.run_gate,
        label="typed storage self-loss",
    )
    out["storage_host_node_topology_bind"] = verify_contract_module_and_receipt(
        pins["storage_host_node_topology_bind"],
        storage_topology_gate.run_gate,
        label="storage host topology bind",
    )
    return out


def verify_adapter_subsystem(m: dict[str, Any]) -> dict[str, Any]:
    pins = m["pins"]
    generic = pins["generic_source_adapter"]
    con = pins["conformance_harness"]
    subsystem = pins["source_adapter_subsystem_freeze"]

    observed_generic = {
        "contract_sha256": verify_file(
            generic["contract_path"], generic["contract_sha256"], "generic adapter contract"
        ),
        "implementation_sha256": verify_file(
            generic["implementation_path"],
            generic["implementation_sha256"],
            "generic adapter implementation",
        ),
        "bindings_sha256": verify_file(
            generic["bindings_path"], generic["bindings_sha256"], "generic bindings"
        ),
        "gate_sha256": verify_file(
            "planetary_resource_generic_source_adapter_gate_v1.py",
            generic["gate_sha256"],
            "generic adapter gate",
        ),
    }
    generic_receipt_sha = canonical_sha256(generic_adapter_gate.run_gate())
    if generic_receipt_sha != generic["receipt_sha256"]:
        raise AssertionError("generic adapter receipt changed")
    observed_generic["receipt_sha256"] = generic_receipt_sha

    observed_conformance = {
        "schema_sha256": verify_file(
            con["schema_path"], con["schema_sha256"], "conformance schema"
        ),
        "harness_sha256": verify_file(
            con["harness_path"], con["harness_sha256"], "conformance harness"
        ),
        "tests_sha256": verify_file(
            "test_planetary_resource_generic_source_adapter_conformance_v1.py",
            con["tests_sha256"],
            "conformance tests",
        ),
    }
    conformance_receipt_sha = canonical_sha256(conformance.run_harness())
    if conformance_receipt_sha != con["receipt_sha256"]:
        raise AssertionError("conformance receipt changed")
    observed_conformance["receipt_sha256"] = conformance_receipt_sha

    observed_subsystem = {
        "manifest_sha256": verify_file(
            "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__SOURCE_ADAPTER_SUBSYSTEM_FREEZE.json",
            subsystem["manifest_sha256"],
            "source adapter freeze manifest",
        ),
        "verifier_sha256": verify_file(
            "planetary_resource_source_adapter_subsystem_freeze_v1.py",
            subsystem["verifier_sha256"],
            "source adapter freeze verifier",
        ),
        "tests_sha256": verify_file(
            "test_planetary_resource_source_adapter_subsystem_freeze_v1.py",
            subsystem["tests_sha256"],
            "source adapter freeze tests",
        ),
    }
    subsystem_receipt = source_freeze.run_freeze()
    subsystem_receipt_sha = canonical_sha256(subsystem_receipt)
    if subsystem_receipt_sha != subsystem["receipt_sha256"]:
        raise AssertionError("source adapter subsystem freeze receipt changed")
    if subsystem_receipt["proven_binding_count"] != 3:
        raise AssertionError("source adapter subsystem no longer has exactly 3 proven bindings")
    observed_subsystem["receipt_sha256"] = subsystem_receipt_sha

    return {
        "generic_source_adapter": observed_generic,
        "conformance_harness": observed_conformance,
        "source_adapter_subsystem_freeze": observed_subsystem,
    }


def verify_three_real_bindings(m: dict[str, Any]) -> dict[str, Any]:
    pin = m["pins"]["proven_real_source_bindings"]
    runs = {
        "water": water_canary.run_canary(),
        "electricity": electricity_canary.run_canary(),
        "natural_gas": gas_canary.run_canary(),
    }
    raw_paths = {
        "water": "sources/environment_agency/1100TH_flow_mean_15min_2026-10-01T21-30Z.json",
        "electricity": "sources/elexon/INDO_2026-10-01T22-00Z.json",
        "natural_gas": "sources/entsog/DE-TSO-0005_ITP-00188_entry_physical_flow_2026-10-01T21-22Z.html",
    }
    out = {}
    for name, receipt in runs.items():
        raw_sha = sha256_file(raw_paths[name])
        if raw_sha != pin[name]["raw_sha256"]:
            raise AssertionError(f"{name} raw snapshot changed")
        receipt_sha = canonical_sha256(receipt)
        if receipt_sha != pin[name]["receipt_sha256"]:
            raise AssertionError(f"{name} canary receipt changed")
        out[name] = {
            "provider": pin[name]["provider"],
            "variable_id": pin[name]["variable_id"],
            "raw_sha256": raw_sha,
            "receipt_sha256": receipt_sha,
            "status": "PROVEN_BINDING",
        }
    if len(out) != 3:
        raise AssertionError("expected exactly three proven real-source bindings")
    return out


def run_freeze() -> dict[str, Any]:
    m = load_manifest()
    core_pin = verify_core_kernel(m)
    successor_pins = verify_successor_pins(m)
    adapter_pins = verify_adapter_subsystem(m)
    real_bindings = verify_three_real_bindings(m)

    return {
        "schema_version":"EQUILIBRIUM_PRS_INTEGRATION_READINESS_FREEZE_RECEIPT_V1",
        "gate_id":GATE_ID,
        "freeze_manifest_sha256":sha256_file(str(MANIFEST_PATH)),
        "freeze_status":m["freeze_status"],
        "source_bearing_predecessor_head":m["source_bearing_predecessor_head"],
        "verified_core_kernel":core_pin,
        "verified_successor_pins":successor_pins,
        "verified_adapter_pins":adapter_pins,
        "verified_real_source_bindings":real_bindings,
        "proven_real_source_binding_count":len(real_bindings),
        "deferred_nonblocking":m["deferred_nonblocking"],
        "deferred_nonblocking_count":len(m["deferred_nonblocking"]),
        "core_change_policy":m["core_change_policy"],
        "next_target":m["next_target"],
        "next_target_count":m["next_target_count"],
        "new_core_gap_work_allowed_without_integration_breakage":False,
        "provider_work":False,
        "new_source_ingest":False,
        "multi_source_fusion":False,
        "fences":m["fences"],
        "verdict":m["verdict_target"],
    }


def write_receipt() -> tuple[dict[str, Any], str]:
    receipt = run_freeze()
    body = json.dumps(
        receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"
    OUT_PATH.write_text(body, encoding="utf-8")
    sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return receipt, sha


if __name__=="__main__":
    receipt, sha = write_receipt()
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    print("INTEGRATION_READINESS_FREEZE_RECEIPT_SHA256=" + sha)
