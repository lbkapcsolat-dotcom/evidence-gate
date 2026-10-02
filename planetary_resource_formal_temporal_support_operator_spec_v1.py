from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import planetary_resource_temporal_support_policy_decision_freeze_v1 as predecessor


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__FORMAL_TEMPORAL_SUPPORT_OPERATOR_SPEC_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__FORMAL_TEMPORAL_SUPPORT_OPERATOR_SPEC.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__FORMAL_TEMPORAL_SUPPORT_OPERATOR_SPEC_RECEIPT.json"
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
    if contract["target_path"] != "PATH_B":
        raise AssertionError("formal spec may target PATH_B only")
    if any(contract["fences"].values()):
        raise AssertionError("forbidden fence enabled")

    pred = predecessor.run_gate()
    expected = contract["predecessor"]
    pred_sha = canonical_sha256(pred)
    if pred_sha != expected["receipt_sha256"]:
        raise AssertionError(
            f"predecessor receipt changed: {pred_sha} != {expected['receipt_sha256']}"
        )
    if pred["verdict"] != expected["verdict"]:
        raise AssertionError("predecessor verdict changed")
    if pred["paths"]["PATH_B"]["activated"]:
        raise AssertionError("PATH_B was activated before formal spec")
    if pred["policy"]["current_continuity_path"] != "PATH_A":
        raise AssertionError("PATH_A fail-closed continuity changed")

    spec = contract["operator_spec"]
    if spec["operator_spec_id"] != "TEMPORAL_SUPPORT_TO_TARGET_WINDOW_OPERATOR_V1":
        raise AssertionError("operator spec id changed")
    if spec["operator_version"] != "V1":
        raise AssertionError("operator version changed")
    if spec["execution_status"] != "SPEC_ONLY_NOT_EXECUTABLE":
        raise AssertionError("operator spec became executable")
    if spec["signature"]["operator_execution_defined"]:
        raise AssertionError("execution semantics are forbidden in this gate")

    src = spec["source_support_domain"]
    if src["interval_convention"] != "HALF_OPEN_[START,END)":
        raise AssertionError("source interval convention changed")
    if src["allowed_support_relations"] != [
        "EXACT_TARGET_SUPPORT",
        "FINER_NATIVE_MEAN_PARTITION_EXACTLY_COVERS_TARGET",
    ]:
        raise AssertionError("support relation registry changed")
    for key in (
        "containment_only_is_admissible",
        "coarse_to_fine_is_admissible",
        "instantaneous_samples_as_interval_means_are_admissible",
    ):
        if src[key]:
            raise AssertionError(f"forbidden source support relation enabled: {key}")

    target = spec["target_support_domain"]
    if target["interval_convention"] != "HALF_OPEN_[START,END)":
        raise AssertionError("target interval convention changed")
    if not all(
        target[k]
        for k in (
            "explicit_start_required",
            "explicit_end_required",
            "positive_duration_required",
        )
    ):
        raise AssertionError("target support requirements weakened")

    adm = spec["admissibility_preconditions"]
    if not all(adm.values()):
        raise AssertionError("admissibility precondition weakened")

    conservation = spec["conservation_semantics"]
    identity = conservation["IDENTITY_EXACT_SUPPORT"]
    partition = conservation["CONSERVATIVE_TIME_MEAN_PARTITION"]
    noncons = conservation["NONCONSERVATIVE_OR_INFORMATION_INSUFFICIENT"]
    if not identity["admissible_for_physical_value"]:
        raise AssertionError("identity support unexpectedly blocked")
    if not partition["admissible_for_physical_value"]:
        raise AssertionError("conservative partition operator unexpectedly blocked")
    if partition["formula"] != (
        "x_target = SUM_i(x_i * delta_t_i) / delta_t_target"
    ):
        raise AssertionError("conservative formula changed")
    if partition["conservation_statement"] != (
        "x_target * delta_t_target = SUM_i(x_i * delta_t_i)"
    ):
        raise AssertionError("conservation identity changed")
    for key in (
        "silent_constancy_assumption",
        "interpolation",
        "imputation",
        "downscaling",
    ):
        if partition[key]:
            raise AssertionError(f"forbidden partition behavior enabled: {key}")
    if noncons["admissible_for_physical_value"]:
        raise AssertionError("nonconservative result cannot enter physical space")
    if noncons["physical_action"] != "HOLD":
        raise AssertionError("nonconservative result must fail closed")

    uncertainty = spec["uncertainty_propagation"]
    if uncertainty["UNKNOWN"] != "UNKNOWN_PROPAGATES":
        raise AssertionError("unknown uncertainty propagation changed")
    if uncertainty["MOMENT"] != "REQUIRE_COVARIANCE_OR_HOLD":
        raise AssertionError("moment uncertainty guard changed")
    if uncertainty["EMPIRICAL"] != "REQUIRE_SAMPLE_ALIGNMENT_REFERENCE_OR_HOLD":
        raise AssertionError("empirical uncertainty guard changed")
    if uncertainty["uncertainty_narrowing_without_evidence"]:
        raise AssertionError("uncertainty narrowing without evidence enabled")
    if uncertainty["unknown_to_exact_allowed"]:
        raise AssertionError("UNKNOWN to EXACT promotion enabled")

    provenance = spec["provenance_transform_record"]
    required_fields = set(provenance["required_fields"])
    mandatory = {
        "operator_spec_id",
        "operator_version",
        "policy_receipt_sha256",
        "variable_id",
        "resource_layer",
        "quantity_kind",
        "source_raw_sha256_set",
        "source_cell_intervals",
        "target_interval",
        "support_relation",
        "conservation_mode",
        "formula_id",
        "unit_transform_chain",
        "input_uncertainty_kinds",
        "output_uncertainty_kind",
        "input_evidence_refs",
        "hold_codes",
    }
    if not mandatory.issubset(required_fields):
        raise AssertionError("provenance transform record incomplete")
    if not provenance["transform_chain_append_required"]:
        raise AssertionError("transform-chain append requirement disabled")
    if not provenance["raw_evidence_refs_must_be_preserved"]:
        raise AssertionError("raw evidence preservation disabled")

    holds = spec["fail_closed_conditions"]
    required_holds = {
        "HOLD_TEMPORAL_INFORMATION_INSUFFICIENT",
        "HOLD_TEMPORAL_TARGET_NOT_EXACT_UNION",
        "HOLD_TEMPORAL_PARTITION_OVERLAP_OR_GAP",
        "HOLD_TEMPORAL_NONCONSERVATIVE_PHYSICAL_ADMISSION_FORBIDDEN",
        "HOLD_TEMPORAL_UNCERTAINTY_OPERATOR",
        "HOLD_TEMPORAL_PROVENANCE_INCOMPLETE",
        "HOLD_TEMPORAL_OPERATOR_VERSION_UNPINNED",
        "HOLD_PATH_B_NOT_ACTIVATED",
    }
    if not required_holds.issubset(set(holds)):
        raise AssertionError("fail-closed registry incomplete")

    state = contract["execution_state"]
    if state != {
        "operator_executed": False,
        "path_b_activated": False,
        "value_composition_performed": False,
        "formal_spec_only": True,
    }:
        raise AssertionError("spec-only execution state changed")
    if any(contract["forbidden_behavior"].values()):
        raise AssertionError("forbidden temporal behavior enabled")

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_FORMAL_TEMPORAL_SUPPORT_OPERATOR_SPEC_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessor": {
            "receipt_sha256": pred_sha,
            "head_sha": expected["head_sha"],
            "verdict": pred["verdict"],
        },
        "target_path": "PATH_B",
        "operator_spec": spec,
        "execution_state": state,
        "forbidden_behavior": contract["forbidden_behavior"],
        "path_b_status": "DECLARED_LOCKED_NOT_ACTIVATED",
        "physical_value_admission_status": "BLOCKED_UNTIL_SEPARATE_OPERATOR_ACTIVATION_GATE",
        "core_patch_required": False,
        "fences": contract["fences"],
        "verdict": contract["verdict_target"],
        "claim_ceiling": (
            "Formal operator semantics are specified only. No temporal operator "
            "was executed, PATH_B was not activated, and no value composition occurred."
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
    print("FORMAL_TEMPORAL_SUPPORT_OPERATOR_SPEC_RECEIPT_SHA256=" + sha)
