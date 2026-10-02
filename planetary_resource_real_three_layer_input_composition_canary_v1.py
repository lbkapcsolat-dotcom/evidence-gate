from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

import planetary_resource_integrated_minimal_core_gate_v1 as integrated_gate
import planetary_resource_first_real_source_canary_v1 as water_canary
import planetary_resource_second_real_source_canary_v1 as electricity_canary
import planetary_resource_third_real_source_gas_canary_v1 as gas_canary


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__REAL_THREE_LAYER_INPUT_COMPOSITION_CANARY_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__REAL_THREE_LAYER_INPUT_COMPOSITION_CANARY.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__REAL_THREE_LAYER_INPUT_COMPOSITION_CANARY_RECEIPT.json"
)

WATER_MANIFEST = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__FIRST_REAL_SOURCE_CANARY_MANIFEST.json"
)
ELECTRICITY_MANIFEST = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__SECOND_REAL_SOURCE_CANARY_MANIFEST.json"
)
GAS_MANIFEST = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__THIRD_REAL_SOURCE_GAS_CANARY_MANIFEST.json"
)


def canonical_sha256(payload: dict[str, Any]) -> str:
    body = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _admitted_value(receipt: dict[str, Any]) -> dict[str, Any]:
    a = receipt["empirical_admission_receipt"]
    return {
        "variable_id": a["variable_id"],
        "canonical_value_n": a["canonical_value_n"],
        "canonical_value_d": a["canonical_value_d"],
        "canonical_unit": a["canonical_unit"],
        "target_node_id": a["target_node_id"],
        "uncertainty_kind": a["uncertainty_kind"],
        "output_status": a["output_status"],
        "transform_chain": a["transform_chain"],
    }


def run_canary() -> dict[str, Any]:
    contract = _load(CONTRACT_PATH)
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("gate id mismatch")
    if any(contract["fences"].values()):
        raise AssertionError(f"forbidden scope enabled: {contract['fences']!r}")

    predecessor = integrated_gate.run_gate()
    predecessor_sha = canonical_sha256(predecessor)
    expected_predecessor = contract["predecessor"]
    if predecessor["integrated_state_sha256"] != expected_predecessor["integrated_state_sha256"]:
        raise AssertionError("integrated state SHA256 changed")
    if predecessor_sha != expected_predecessor["integrated_receipt_sha256"]:
        raise AssertionError(
            f"integrated receipt SHA256 changed: {predecessor_sha} "
            f"!= {expected_predecessor['integrated_receipt_sha256']}"
        )

    receipts = {
        "freshwater": water_canary.run_canary(),
        "electricity": electricity_canary.run_canary(),
        "natural_gas": gas_canary.run_canary(),
    }
    for name, receipt in receipts.items():
        got = canonical_sha256(receipt)
        expected = contract["proven_bindings"][name]["canary_receipt_sha256"]
        if got != expected:
            raise AssertionError(f"{name} canary receipt changed: {got} != {expected}")
        admitted = receipt["empirical_admission_receipt"]
        pin = contract["proven_bindings"][name]
        if admitted["variable_id"] != pin["variable_id"]:
            raise AssertionError(f"{name} variable changed")
        if admitted["uncertainty_kind"] != "UNKNOWN":
            raise AssertionError(f"{name} uncertainty was silently promoted")
        if admitted["decision"] != "ADMIT_OBSERVED":
            raise AssertionError(f"{name} is no longer an admitted observed value")

    water = _load(WATER_MANIFEST)
    electricity = _load(ELECTRICITY_MANIFEST)
    gas = _load(GAS_MANIFEST)

    gas_end = _dt(gas["record"]["period_to_utc"])
    electricity_start = _dt(electricity["record"]["start_time"])
    gas_electricity_positive_overlap_seconds = max(
        0, int((gas_end - electricity_start).total_seconds())
    )

    water_semantics = water["admission"]["timestamp_semantics"]
    water_explicit_interval_bounds_available = (
        "NO_INFERRED_START_BOUNDARY" not in water_semantics
        and "start_time" in water["record"]
        and "end_time" in water["record"]
    )

    blockers: list[dict[str, Any]] = []
    if gas_electricity_positive_overlap_seconds <= 0:
        blockers.append(
            {
                "code": "HOLD_GAS_ELECTRICITY_NO_POSITIVE_DURATION_OVERLAP",
                "gas_period_to_utc": gas["record"]["period_to_utc"],
                "electricity_start_utc": electricity["record"]["start_time"],
                "positive_overlap_seconds": gas_electricity_positive_overlap_seconds,
                "reason": (
                    "The pinned ENTSOG interval ends exactly when the pinned "
                    "Elexon interval starts; a boundary touch is not a "
                    "positive-duration common composition window."
                ),
            }
        )
    if not water_explicit_interval_bounds_available:
        blockers.append(
            {
                "code": "HOLD_WATER_INTERVAL_BOUNDARY_NOT_EXPLICIT",
                "observed_at": water["record"]["observed_at"],
                "period_seconds": water["record"]["period_seconds"],
                "timestamp_semantics": water_semantics,
                "reason": (
                    "The proven water binding explicitly forbids inferring a "
                    "start boundary from the 15-minute mean record."
                ),
            }
        )

    common_window_proven = len(blockers) == 0
    if common_window_proven:
        raise AssertionError(
            "A common exact window is now provable; this frozen HOLD canary "
            "must be replaced by an explicit mapping implementation."
        )

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_REAL_THREE_LAYER_INPUT_COMPOSITION_CANARY_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessor": {
            "integrated_state_sha256": predecessor["integrated_state_sha256"],
            "integrated_receipt_sha256": predecessor_sha,
            "process_version_guard_preserved":
                predecessor["process_version_guard_exercised"],
            "process_validity_guard_preserved":
                predecessor["process_validity_guard_exercised"],
            "storage_topology_guard_preserved":
                predecessor["storage_topology_guard_exercised"],
        },
        "revalidated_proven_bindings": {
            name: {
                "provider": contract["proven_bindings"][name]["provider"],
                "variable_id": contract["proven_bindings"][name]["variable_id"],
                "raw_sha256": contract["proven_bindings"][name]["raw_sha256"],
                "canary_receipt_sha256": canonical_sha256(receipt),
                "admitted_value": _admitted_value(receipt),
            }
            for name, receipt in receipts.items()
        },
        "temporal_evidence": {
            "natural_gas": {
                "start_utc": gas["record"]["period_from_utc"],
                "end_utc": gas["record"]["period_to_utc"],
                "temporal_method": gas["admission"]["temporal_method"],
            },
            "electricity": {
                "start_utc": electricity["record"]["start_time"],
                "interval_id": electricity["admission"]["interval_id"],
                "timestamp_semantics": electricity["admission"]["timestamp_semantics"],
                "temporal_method": electricity["admission"]["temporal_method"],
            },
            "freshwater": {
                "observed_at": water["record"]["observed_at"],
                "period_seconds": water["record"]["period_seconds"],
                "timestamp_semantics": water_semantics,
                "temporal_method": water["admission"]["temporal_method"],
            },
            "gas_electricity_positive_overlap_seconds":
                gas_electricity_positive_overlap_seconds,
        },
        "blockers": blockers,
        "common_window_proven": False,
        "mapping_performed": False,
        "real_values_entered_integrated_balance": False,
        "new_source_ingest": False,
        "interpolation_performed": False,
        "imputation_performed": False,
        "aggregation_performed": False,
        "inferred_interval_boundary_used": False,
        "uncertainty_preserved": True,
        "source_provenance_preserved": True,
        "core_patch_required": False,
        "new_domain_math_added": False,
        "fences": contract["fences"],
        "verdict": contract["hold_verdict"],
        "minimum_unblock": (
            "Acquire a new, explicitly bounded three-layer snapshot set whose "
            "source intervals share a positive-duration common window; keep "
            "the frozen core and composition math unchanged."
        ),
    }


def write_receipt() -> tuple[dict[str, Any], str]:
    receipt = run_canary()
    body = json.dumps(
        receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"
    OUT_PATH.write_text(body, encoding="utf-8")
    return receipt, hashlib.sha256(body.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    receipt, sha = write_receipt()
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    print("REAL_THREE_LAYER_INPUT_COMPOSITION_CANARY_RECEIPT_SHA256=" + sha)
