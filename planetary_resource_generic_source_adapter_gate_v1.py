from __future__ import annotations

from dataclasses import asdict
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

import planetary_resource_first_real_source_canary_v1 as water
import planetary_resource_second_real_source_canary_v1 as electricity
import planetary_resource_third_real_source_gas_canary_v1 as gas
import planetary_resource_generic_source_adapter_v1 as generic
import planetary_resource_generic_source_bindings_v1 as bindings


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__GENERIC_SOURCE_ADAPTER_CONTRACT_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__GENERIC_SOURCE_ADAPTER_CONTRACT.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__GENERIC_SOURCE_ADAPTER_CONTRACT_RECEIPT.json"
)

EXPECTED_CANARY_RECEIPT_SHA256 = {
    "water": "697857c063c2cd6d7514e2b9dd79c46d7fe59a5efe0588579e9c4fd306b12c93",
    "electricity": "9a996daea1a702e1654264a13cc72d0dcba760f8945528b24ce854c2392bca29",
    "gas": "f0629b99245af4dacea863f91b71faf5938b10ed6e1c7069f4c1f829b5a1c406",
}

EXPECTED_FROZEN_HASHES = {
    "empirical_contract": (
        "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__EMPIRICAL_DATA_CONTRACT.json",
        "592570140b8465cc4e9c38c84a9da5c1f6be73e9894bc1aad0a99e6ad023e9b3",
    ),
    "empirical_validator": (
        "planetary_resource_empirical_admission_v1.py",
        "3fc420678148149cdfca9fae03088b2f54e5987bf29278d1e94497534a4151c2",
    ),
    "water_raw": (
        "sources/environment_agency/1100TH_flow_mean_15min_2026-10-01T21-30Z.json",
        "c180db17bc02d371f1eebb4667695b715f0ce2f9c2f97bab6893b77f87c97c29",
    ),
    "electricity_raw": (
        "sources/elexon/INDO_2026-10-01T22-00Z.json",
        "831ed964ef11527f0d8db767665289b59f5ef7b32fac02cd7667ad4b949a7242",
    ),
    "gas_raw": (
        "sources/entsog/DE-TSO-0005_ITP-00188_entry_physical_flow_2026-10-01T21-22Z.html",
        "a7f15400b518ec51ac0f6a97696bd7cd261e64730d1a348dc1a2ad0be0956928",
    ),
}


def sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_receipt_sha256(receipt: dict[str, Any]) -> str:
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _contract() -> dict[str, Any]:
    c = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if c["gate_id"] != GATE_ID:
        raise AssertionError("generic adapter contract gate mismatch")
    if c["proven_bindings"] != [
        "ENVIRONMENT_AGENCY_FRESHWATER",
        "ELEXON_ELECTRICITY",
        "ENTSOG_NATURAL_GAS",
    ]:
        raise AssertionError("generic adapter contract bindings mismatch")
    if any(c["fences"].values()):
        raise AssertionError(f"scope fence changed: {c['fences']!r}")
    return c


def _verify_no_provider_specific_domain_math() -> None:
    adapter_source = inspect.getsource(generic)
    bindings_source = inspect.getsource(bindings)
    forbidden = (
        "resource_balance_residual",
        "storage_transition",
        "process_coupling",
        "aggregate_eq_score",
        "stress_model",
    )
    for token in forbidden:
        if token in adapter_source or token in bindings_source:
            raise AssertionError(f"provider-specific domain math token present: {token}")

    if "equilibrium_planetary_resource_core_v1" in adapter_source:
        raise AssertionError("generic adapter must not import the domain core directly")
    if "admission.admit(candidate)" not in adapter_source:
        raise AssertionError("generic adapter must terminate at unchanged empirical admission")


def run_gate() -> dict[str, Any]:
    contract = _contract()
    _verify_no_provider_specific_domain_math()

    preserved_hashes: dict[str, str] = {}
    for name, (path, expected) in EXPECTED_FROZEN_HASHES.items():
        got = sha256_file(path)
        if got != expected:
            raise AssertionError(f"{name} changed: {got} != {expected}")
        preserved_hashes[name] = got

    existing = {
        "water": water.run_canary(),
        "electricity": electricity.run_canary(),
        "gas": gas.run_canary(),
    }
    for name, receipt in existing.items():
        got = canonical_receipt_sha256(receipt)
        if got != EXPECTED_CANARY_RECEIPT_SHA256[name]:
            raise AssertionError(f"{name} canary receipt changed: {got}")

    specs_records = {
        "water": bindings.water_binding(),
        "electricity": bindings.electricity_binding(),
        "gas": bindings.gas_binding(),
    }

    equality: dict[str, dict[str, Any]] = {}
    for name, (spec, record) in specs_records.items():
        generic_receipt = generic.adapt(spec, record)
        generic_dict = asdict(generic_receipt)
        existing_dict = existing[name]["empirical_admission_receipt"]
        equal = generic_dict == existing_dict
        if not equal:
            raise AssertionError(
                f"{name} generic empirical receipt differs from existing canary receipt"
            )
        equality[name] = {
            "equal": True,
            "generic_empirical_receipt_sha256": hashlib.sha256(
                json.dumps(
                    generic_dict,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest(),
            "existing_canary_receipt_sha256": EXPECTED_CANARY_RECEIPT_SHA256[name],
            "provider": spec.provider,
            "variable_id": generic_dict["variable_id"],
            "canonical_unit": generic_dict["canonical_unit"],
            "target_node_id": generic_dict["target_node_id"],
        }

    receipt = {
        "schema_version": "EQUILIBRIUM_PRS_GENERIC_SOURCE_ADAPTER_CONTRACT_RECEIPT_V1",
        "gate_id": GATE_ID,
        "generic_contract_sha256": sha256_file(str(CONTRACT_PATH)),
        "generic_adapter_sha256": sha256_file("planetary_resource_generic_source_adapter_v1.py"),
        "generic_bindings_sha256": sha256_file("planetary_resource_generic_source_bindings_v1.py"),
        "preserved_hashes": preserved_hashes,
        "receipt_equality": equality,
        "three_of_three_equal": all(x["equal"] for x in equality.values()),
        "provider_specific_domain_math": False,
        "provider_specific_physics_engine": False,
        "new_source_ingest": False,
        "shared_interface": contract["interface"],
        "provider_binding_scope": contract["provider_binding_scope"],
        "fences": contract["fences"],
        "verdict": contract["verdict_target"],
    }
    return receipt


def write_receipt() -> tuple[dict[str, Any], str]:
    receipt = run_gate()
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    OUT_PATH.write_text(canonical, encoding="utf-8")
    sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return receipt, sha


if __name__ == "__main__":
    receipt, sha = write_receipt()
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    print("GENERIC_SOURCE_ADAPTER_RECEIPT_SHA256=" + sha)
