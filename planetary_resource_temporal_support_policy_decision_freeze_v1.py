from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import planetary_resource_native_common_support_replacement_and_integration_retry_v1 as predecessor


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__TEMPORAL_SUPPORT_POLICY_DECISION_FREEZE_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__TEMPORAL_SUPPORT_POLICY_DECISION_FREEZE.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__TEMPORAL_SUPPORT_POLICY_DECISION_FREEZE_RECEIPT.json"
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

    pred = predecessor.run_gate()
    pred_sha = canonical_sha256(pred)
    expected = contract["predecessor"]
    if pred_sha != expected["receipt_sha256"]:
        raise AssertionError(
            f"predecessor receipt changed: {pred_sha} != {expected['receipt_sha256']}"
        )
    if pred["verdict"] != expected["verdict"]:
        raise AssertionError("predecessor verdict changed")

    elexon = contract["frozen_elexon"]
    if elexon["status"] != "READY_EXACT_INTERVAL":
        raise AssertionError("Elexon exact interval status changed")
    if elexon["duration_seconds"] != 1800:
        raise AssertionError("Elexon frozen interval changed")
    if pred["electricity"]["raw_sha256"] != elexon["raw_sha256"]:
        raise AssertionError("Elexon raw SHA pin changed")

    policy = contract["policy"]
    paths = contract["paths"]
    if policy["allowed_path_count"] != 2:
        raise AssertionError("policy must contain exactly two paths")
    if list(paths.keys()) != ["PATH_A", "PATH_B"]:
        raise AssertionError("only PATH_A and PATH_B are permitted")
    if policy["allowed_paths_only"] != ["PATH_A", "PATH_B"]:
        raise AssertionError("allowed path registry changed")
    if policy["implicit_third_path_allowed"]:
        raise AssertionError("implicit third path is forbidden")
    if policy["automatic_path_transition"]:
        raise AssertionError("automatic path transition is forbidden")
    if policy["automatic_path_b_activation"]:
        raise AssertionError("PATH_B cannot auto-activate")
    if policy["current_continuity_path"] != "PATH_A":
        raise AssertionError("fail-closed continuity path changed")

    path_a = paths["PATH_A"]
    if not path_a["exact_native_intervals_only"]:
        raise AssertionError("PATH_A exact-native policy disabled")
    if path_a["source_search_by_default"]:
        raise AssertionError("PATH_A source search must remain off by default")
    if path_a["value_composition_allowed"]:
        raise AssertionError("PATH_A composition must remain blocked")
    for key in ("natural_gas_status", "freshwater_status"):
        if path_a[key] != "HOLD_EXACT_NATIVE_COMMON_SUPPORT_NOT_AVAILABLE":
            raise AssertionError(f"PATH_A {key} changed")

    path_b = paths["PATH_B"]
    required_true = (
        "declared",
        "operator_must_be_predeclared",
        "operator_must_be_auditable",
        "formal_temporal_semantics_required",
    )
    if not all(path_b[key] for key in required_true):
        raise AssertionError("PATH_B formal operator requirements weakened")
    if path_b["activated"]:
        raise AssertionError("PATH_B activated before formal successor gate")
    forbidden_true = (
        "silent_downscaling_allowed",
        "imputation_allowed",
        "interpolation_allowed",
        "assumed_constancy_allowed",
        "value_composition_allowed_before_formal_semantics",
    )
    if any(path_b[key] for key in forbidden_true):
        raise AssertionError("PATH_B forbidden temporal behavior enabled")

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_TEMPORAL_SUPPORT_POLICY_DECISION_FREEZE_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessor": {
            "receipt_sha256": pred_sha,
            "head_sha": expected["head_sha"],
            "verdict": pred["verdict"],
        },
        "frozen_elexon": elexon,
        "policy": policy,
        "paths": paths,
        "current_execution_state": {
            "continuity_path": "PATH_A",
            "natural_gas": "HOLD",
            "freshwater": "HOLD",
            "three_source_value_composition": "BLOCKED",
            "source_search_by_default": False,
        },
        "path_b_unlock_condition": {
            "explicit_successor_gate_required": True,
            "formal_temporal_operator_required": True,
            "operator_predeclared": True,
            "operator_auditable": True,
            "value_composition_before_unlock": False,
        },
        "core_patch_required": False,
        "fences": contract["fences"],
        "verdict": contract["verdict_target"],
        "claim_ceiling": (
            "Temporal support policy is frozen to exactly two paths. "
            "PATH_A is the current fail-closed continuity state. PATH_B is "
            "declared but locked until a separate explicit formal-operator gate."
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
    print("TEMPORAL_SUPPORT_POLICY_FREEZE_RECEIPT_SHA256=" + sha)
