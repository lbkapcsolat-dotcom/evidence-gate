from __future__ import annotations

from datetime import timedelta
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any

import planetary_resource_temporal_support_operator_executable_kernel_v1 as kernel


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PATH_B_REAL_SOURCE_IDENTITY_ACTIVATION_CANARY_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PATH_B_REAL_SOURCE_IDENTITY_ACTIVATION_CANARY.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PATH_B_REAL_SOURCE_IDENTITY_ACTIVATION_CANARY_RECEIPT.json"
)


def canonical_sha256(payload: dict[str, Any]) -> str:
    body = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def verified_raw(source: dict[str, Any]) -> tuple[bytes, str]:
    path = Path(source["raw_path"])
    raw = path.read_bytes()
    if len(raw) != int(source["raw_bytes"]):
        raise AssertionError(
            f"Elexon raw byte length changed: {len(raw)} != {source['raw_bytes']}"
        )
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != source["raw_sha256"]:
        raise AssertionError(
            f"Elexon raw SHA256 changed: {actual_sha} != {source['raw_sha256']}"
        )
    return raw, actual_sha


def run_gate() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("gate id mismatch")
    if any(contract["fences"].values()):
        raise AssertionError("forbidden fence enabled")
    if any(contract["forbidden_behavior"].values()):
        raise AssertionError("forbidden canary behavior enabled")
    if not all(contract["requirements"].values()):
        raise AssertionError("required canary condition disabled")

    pred = kernel.run_gate()
    expected = contract["predecessor"]
    pred_sha = canonical_sha256(pred)
    if pred_sha != expected["receipt_sha256"]:
        raise AssertionError(
            f"executable-kernel receipt changed: {pred_sha} != "
            f"{expected['receipt_sha256']}"
        )
    if pred["verdict"] != expected["verdict"]:
        raise AssertionError("executable-kernel verdict changed")

    operator = contract["operator"]
    if pred["formal_spec"]["operator_spec_id"] != operator["operator_spec_id"]:
        raise AssertionError("operator spec id changed")
    if pred["formal_spec"]["operator_version"] != operator["operator_version"]:
        raise AssertionError("operator version changed")
    if operator["allowed_relation"] != "EXACT_TARGET_SUPPORT":
        raise AssertionError("identity canary relation changed")
    if operator["partition_aggregation_allowed"]:
        raise AssertionError("partition aggregation enabled in identity canary")

    activation = contract["activation"]
    if activation["target_path"] != "PATH_B":
        raise AssertionError("canary may activate PATH_B only")
    if activation["scope"] != "CANARY_LOCAL_IDENTITY_ONLY":
        raise AssertionError("activation scope changed")
    if not activation["active_during_canary"]:
        raise AssertionError("local canary activation disabled")
    if activation["global_activation"]:
        raise AssertionError("global PATH_B activation forbidden")
    if activation["runtime_admission"]:
        raise AssertionError("runtime admission forbidden")

    source = contract["source"]
    raw, raw_sha = verified_raw(source)
    payload = json.loads(raw.decode("utf-8"))

    target = contract["target_window"]
    target_start = kernel.dt(target["start_utc"])
    target_end = kernel.dt(target["end_utc"])
    if int((target_end - target_start).total_seconds()) != target["duration_seconds"]:
        raise AssertionError("target window duration changed")

    rows = [
        row for row in payload["data"]
        if row["startTime"] == target["start_utc"]
    ]
    if len(rows) != 1:
        raise AssertionError(f"expected one Elexon target record, got {len(rows)}")
    row = rows[0]
    source_start = kernel.dt(row["startTime"])
    source_end = source_start + timedelta(seconds=target["duration_seconds"])
    if source_start != target_start or source_end != target_end:
        raise AssertionError("Elexon source support is not exact target support")

    value = Fraction(int(row[source["record_field"]]))
    fixture = {
        "fixture_id": "REAL_ELEXON_IDENTITY_CANARY",
        "operator_version": operator["operator_version"],
        "provenance_complete": True,
        "uncertainty_kind": source["uncertainty_kind"],
        "covariance_provided": False,
        "cells": [
            {
                "start_utc": target["start_utc"],
                "end_utc": target["end_utc"],
                "value_n": value.numerator,
                "value_d": value.denominator,
                "native_time_mean": True,
            }
        ],
    }

    formal = kernel.formal_spec.run_gate()
    result = kernel.execute_kernel(
        fixture,
        target_start=target_start,
        target_end=target_end,
        formal_receipt=formal,
    )
    if result["decision"] != "PASS_IDENTITY":
        raise AssertionError(
            f"real Elexon identity canary did not pass: {result['decision']}"
        )
    if result["support_relation"] != "EXACT_TARGET_SUPPORT":
        raise AssertionError("kernel selected non-identity support relation")
    if result["formula_id"] != "IDENTITY_V1":
        raise AssertionError("kernel selected non-identity formula")
    if (result["value_n"], result["value_d"]) != (
        value.numerator,
        value.denominator,
    ):
        raise AssertionError("identity output changed source value")
    if result["uncertainty"]["kind"] != "UNKNOWN":
        raise AssertionError("UNKNOWN source uncertainty was not preserved")

    transform_record = {
        "operator_spec_id": operator["operator_spec_id"],
        "operator_version": operator["operator_version"],
        "kernel_receipt_sha256": pred_sha,
        "activation_scope": activation["scope"],
        "variable_id": source["variable_id"],
        "provider": source["provider"],
        "dataset": source["dataset"],
        "source_url": source["source_url"],
        "source_raw_path": source["raw_path"],
        "source_raw_bytes": len(raw),
        "source_raw_sha256": raw_sha,
        "source_record_start_utc": row["startTime"],
        "source_record_field": source["record_field"],
        "source_unit": source["source_unit"],
        "source_value_n": value.numerator,
        "source_value_d": value.denominator,
        "source_uncertainty_kind": source["uncertainty_kind"],
        "source_support_start_utc": target["start_utc"],
        "source_support_end_utc": target["end_utc"],
        "target_support_start_utc": target["start_utc"],
        "target_support_end_utc": target["end_utc"],
        "support_relation": result["support_relation"],
        "formula_id": result["formula_id"],
        "output_value_n": result["value_n"],
        "output_value_d": result["value_d"],
        "output_uncertainty_kind": result["uncertainty"]["kind"],
        "partition_aggregation_performed": False,
        "interpolation_performed": False,
        "imputation_performed": False,
        "coarse_to_fine_performed": False,
        "cross_source_composition_performed": False,
        "gas_input_used": False,
        "freshwater_input_used": False,
        "hold_codes": [],
    }
    if transform_record["source_raw_sha256"] != source["raw_sha256"]:
        raise AssertionError("real raw SHA provenance bind failed")
    if (
        transform_record["source_value_n"],
        transform_record["source_value_d"],
    ) != (
        transform_record["output_value_n"],
        transform_record["output_value_d"],
    ):
        raise AssertionError("transform record does not preserve identity")

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_PATH_B_REAL_SOURCE_IDENTITY_ACTIVATION_CANARY_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessor": {
            "receipt_sha256": pred_sha,
            "head_sha": expected["head_sha"],
            "verdict": pred["verdict"],
        },
        "operator": operator,
        "activation": {
            **activation,
            "canary_result": "PASS_IDENTITY",
            "post_canary_global_state": "LOCKED_NOT_GLOBALLY_ACTIVATED",
        },
        "source": {
            "provider": source["provider"],
            "dataset": source["dataset"],
            "variable_id": source["variable_id"],
            "source_url": source["source_url"],
            "raw_path": source["raw_path"],
            "raw_bytes": len(raw),
            "raw_sha256": raw_sha,
            "record_start_utc": row["startTime"],
            "record_field": source["record_field"],
            "record_value_n": value.numerator,
            "record_value_d": value.denominator,
            "source_unit": source["source_unit"],
            "uncertainty_kind": source["uncertainty_kind"],
        },
        "target_window": target,
        "kernel_result": {
            "decision": result["decision"],
            "hold_code": result["hold_code"],
            "value_n": result["value_n"],
            "value_d": result["value_d"],
            "uncertainty": result["uncertainty"],
            "support_relation": result["support_relation"],
            "formula_id": result["formula_id"],
        },
        "output_equals_input_exactly": True,
        "unknown_uncertainty_preserved": True,
        "real_raw_sha256_provenance_bound": True,
        "operator_transform_record": transform_record,
        "partition_aggregation_performed": False,
        "gas_input_used": False,
        "freshwater_input_used": False,
        "cross_source_composition_performed": False,
        "coarse_to_fine_performed": False,
        "interpolation_performed": False,
        "imputation_performed": False,
        "core_patch_required": False,
        "fences": contract["fences"],
        "verdict": contract["verdict_target"],
        "claim_ceiling": (
            "PATH_B activated only inside one Elexon exact-support identity canary. "
            "No global PATH_B activation, partition aggregation, cross-source composition, "
            "runtime admission, or production claim occurred."
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
    print("PATH_B_REAL_SOURCE_IDENTITY_CANARY_RECEIPT_SHA256=" + sha)
