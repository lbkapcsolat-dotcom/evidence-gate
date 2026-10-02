from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import planetary_resource_aligned_real_input_integration_canary_v1 as predecessor


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__NATIVE_COMMON_SUPPORT_SOURCE_REPLACEMENT_AND_INTEGRATION_RETRY_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__NATIVE_COMMON_SUPPORT_SOURCE_REPLACEMENT_AND_INTEGRATION_RETRY.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__NATIVE_COMMON_SUPPORT_SOURCE_REPLACEMENT_AND_INTEGRATION_RETRY_RECEIPT.json"
)


def canonical_sha256(payload: dict[str, Any]) -> str:
    body = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def run_gate() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("gate id mismatch")
    if any(contract["fences"].values()):
        raise AssertionError("forbidden fence enabled")
    if not all(contract["requirements"].values()):
        raise AssertionError("required gate condition disabled")

    pred = predecessor.run_gate()
    pred_sha = canonical_sha256(pred)
    if pred_sha != contract["predecessor"]["receipt_sha256"]:
        raise AssertionError("predecessor receipt changed")
    if pred["verdict"] != (
        "HOLD_BOUNDED_ALIGNED_REAL_INPUT_INTEGRATION_TEMPORAL_SUPPORT_MISMATCH"
    ):
        raise AssertionError("unexpected predecessor verdict")

    fixed = contract["fixed_electricity"]
    target = contract["target_window"]
    if (
        fixed["native_interval_start"] != target["start_utc"]
        or fixed["native_interval_end"] != target["end_utc"]
        or fixed["status"] != "READY_EXACT_INTERVAL"
    ):
        raise AssertionError("fixed Elexon exact window changed")

    discovery = contract["bounded_discovery"]
    gas_ready = any(
        item["exact_30_minute_interval_product_proven"]
        for item in discovery["natural_gas"]
    )
    water_ready = any(
        item["exact_30_minute_interval_product_proven"]
        for item in discovery["freshwater"]
    )
    rerun = gas_ready and water_ready

    if rerun:
        raise AssertionError(
            "contract says exact replacements exist but no pinned replacement bytes are present"
        )

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_NATIVE_COMMON_SUPPORT_SOURCE_REPLACEMENT_AND_INTEGRATION_RETRY_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessor": {
            "receipt_sha256": pred_sha,
            "verdict": pred["verdict"],
            "head_sha": contract["predecessor"]["head_sha"],
        },
        "target_window": target,
        "electricity": {
            **fixed,
            "replacement_required": False,
        },
        "replacement_discovery": {
            "natural_gas": {
                "exact_native_source_found": gas_ready,
                "tested_official_surfaces": discovery["natural_gas"],
                "status": "NOT_FOUND_WITHIN_TESTED_OFFICIAL_SURFACES",
            },
            "freshwater": {
                "exact_native_source_found": water_ready,
                "tested_official_surfaces": discovery["freshwater"],
                "status": "NOT_FOUND_WITHIN_TESTED_OFFICIAL_SURFACES",
            },
        },
        "integration_retry": {
            "performed": rerun,
            "reason_not_performed": (
                "Both replacement sources must have native intervals exactly equal "
                "to the fixed 30-minute target before physical integration may rerun."
            ),
        },
        "temporal_rules": contract["temporal_rules"],
        "prohibited_transforms_performed": {
            "interpolation": False,
            "imputation": False,
            "aggregation": False,
            "downscaling": False,
            "inferred_boundaries": False,
        },
        "core_patch_required": False,
        "new_domain_math_added": False,
        "fences": contract["fences"],
        "verdict": contract["verdict_if_missing"],
        "claim_ceiling": (
            "Bounded official-source discovery only. This does not assert that no "
            "exact 30-minute gas or freshwater source exists anywhere; it asserts "
            "that no admissible replacement was proven in the tested official surfaces."
        ),
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
    print("NATIVE_COMMON_SUPPORT_RETRY_RECEIPT_SHA256=" + sha)
