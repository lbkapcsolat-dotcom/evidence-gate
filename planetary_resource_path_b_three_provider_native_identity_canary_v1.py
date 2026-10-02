from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fractions import Fraction
import csv
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any
import xml.etree.ElementTree as ET

import planetary_resource_path_b_real_source_identity_activation_canary_v1 as predecessor
import planetary_resource_temporal_support_operator_executable_kernel_v1 as kernel


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PATH_B_THREE_PROVIDER_NATIVE_IDENTITY_CANARY_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PATH_B_THREE_PROVIDER_NATIVE_IDENTITY_CANARY.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PATH_B_THREE_PROVIDER_NATIVE_IDENTITY_CANARY_RECEIPT.json"
)

NS = {
    "gml": "http://www.opengis.net/gml/3.2",
    "wml2": "http://www.opengis.net/waterml/2.0",
}


def canonical_sha256(payload: dict[str, Any]) -> str:
    body = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def verified_raw(source: dict[str, Any]) -> tuple[bytes, str]:
    raw = Path(source["raw_path"]).read_bytes()
    if len(raw) != int(source["raw_bytes"]):
        raise AssertionError(
            f"raw byte length changed for {source['raw_path']}: "
            f"{len(raw)} != {source['raw_bytes']}"
        )
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != source["raw_sha256"]:
        raise AssertionError(
            f"raw SHA256 changed for {source['raw_path']}: "
            f"{actual_sha} != {source['raw_sha256']}"
        )
    return raw, actual_sha


def parse_elexon(source: dict[str, Any]) -> dict[str, Any]:
    raw, raw_sha = verified_raw(source)
    payload = json.loads(raw.decode("utf-8"))
    rows = [
        row for row in payload["data"]
        if row["startTime"] == source["target_start_utc"]
    ]
    if len(rows) != 1:
        raise AssertionError(f"expected one Elexon target record, got {len(rows)}")
    row = rows[0]
    start = kernel.dt(row["startTime"])
    end = start + timedelta(seconds=int(source["authoritative_duration_seconds"]))
    value = Fraction(int(row[source["record_field"]]))
    return {
        "provider": source["provider"],
        "dataset": source["dataset"],
        "resource_layer": source["resource_layer"],
        "variable_id": source["variable_id"],
        "source_url": source["source_url"],
        "raw_path": source["raw_path"],
        "raw_bytes": len(raw),
        "raw_sha256": raw_sha,
        "interval_start_utc": iso_utc(start),
        "interval_end_utc": iso_utc(end),
        "value": value,
        "source_unit": source["source_unit"],
        "uncertainty_kind": source["uncertainty_kind"],
        "native_time_mean_flag": source["native_time_mean_flag"],
        "record_locator": {
            "startTime": row["startTime"],
            "record_field": source["record_field"],
        },
    }


def parse_entsog(source: dict[str, Any]) -> dict[str, Any]:
    raw, raw_sha = verified_raw(source)
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    pattern = re.compile(
        r"Physical Flowhour"
        r"(?P<from>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \+00:00)"
        r"(?P<to>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \+00:00)"
    )
    target_start = kernel.dt(source["target_period_from_utc"])
    target_end = kernel.dt(source["target_period_to_utc"])
    selected = None
    selected_start = selected_end = None
    for row in rows:
        match = pattern.search(row["id"])
        if not match:
            continue
        start = datetime.strptime(
            match.group("from"), "%Y-%m-%d %H:%M:%S %z"
        )
        end = datetime.strptime(
            match.group("to"), "%Y-%m-%d %H:%M:%S %z"
        )
        if (
            start == target_start
            and end == target_end
            and row["operatorKey"] == source["operator_key"]
            and row["pointKey"] == source["point_key"]
            and row["directionKey"] == source["direction"]
        ):
            selected = row
            selected_start, selected_end = start, end
            break
    if selected is None or selected_start is None or selected_end is None:
        raise AssertionError("exact ENTSOG native interval record missing")
    if selected["unit"] != source["source_unit"]:
        raise AssertionError("ENTSOG source unit changed")
    value = Fraction(int(selected["value"]))
    return {
        "provider": source["provider"],
        "dataset": source["dataset"],
        "resource_layer": source["resource_layer"],
        "variable_id": source["variable_id"],
        "source_url": source["source_url"],
        "raw_path": source["raw_path"],
        "raw_bytes": len(raw),
        "raw_sha256": raw_sha,
        "interval_start_utc": iso_utc(selected_start),
        "interval_end_utc": iso_utc(selected_end),
        "value": value,
        "source_unit": selected["unit"],
        "uncertainty_kind": source["uncertainty_kind"],
        "native_time_mean_flag": source["native_time_mean_flag"],
        "record_locator": {
            "record_id": selected["id"],
            "operatorKey": selected["operatorKey"],
            "pointKey": selected["pointKey"],
            "directionKey": selected["directionKey"],
        },
    }


def parse_bom(source: dict[str, Any]) -> dict[str, Any]:
    raw, raw_sha = verified_raw(source)
    root = ET.fromstring(raw)
    start_text = root.findtext(".//gml:beginPosition", namespaces=NS)
    end_text = root.findtext(".//gml:endPosition", namespaces=NS)
    value_text = root.findtext(
        ".//wml2:MeasurementTVP/wml2:value", namespaces=NS
    )
    uom = root.find(".//wml2:uom", namespaces=NS)
    if not start_text or not end_text or value_text is None or uom is None:
        raise AssertionError("BOM explicit native interval/value/unit missing")
    if uom.attrib.get("code") != source["source_unit"]:
        raise AssertionError("BOM source unit changed")
    start = datetime.fromisoformat(start_text)
    end = datetime.fromisoformat(end_text)
    if end <= start:
        raise AssertionError("BOM native interval is not positive duration")
    value = Fraction(value_text)
    return {
        "provider": source["provider"],
        "dataset": source["dataset"],
        "resource_layer": source["resource_layer"],
        "variable_id": source["variable_id"],
        "source_url": source["source_url"],
        "raw_path": source["raw_path"],
        "raw_bytes": len(raw),
        "raw_sha256": raw_sha,
        "interval_start_utc": iso_utc(start),
        "interval_end_utc": iso_utc(end),
        "value": value,
        "source_unit": source["source_unit"],
        "uncertainty_kind": source["uncertainty_kind"],
        "native_time_mean_flag": source["native_time_mean_flag"],
        "record_locator": {
            "station_id": source["station_id"],
            "observed_property": source["observed_property"],
            "published_value": value_text,
        },
    }


def execute_identity(
    source_key: str,
    source: dict[str, Any],
    *,
    formal_receipt: dict[str, Any],
    operator_version: str,
) -> dict[str, Any]:
    start = kernel.dt(source["interval_start_utc"])
    end = kernel.dt(source["interval_end_utc"])
    fixture = {
        "fixture_id": "REAL_" + source_key.upper() + "_NATIVE_IDENTITY_CANARY",
        "operator_version": operator_version,
        "provenance_complete": True,
        "uncertainty_kind": source["uncertainty_kind"],
        "covariance_provided": False,
        "cells": [
            {
                "start_utc": source["interval_start_utc"],
                "end_utc": source["interval_end_utc"],
                "value_n": source["value"].numerator,
                "value_d": source["value"].denominator,
                "native_time_mean": source["native_time_mean_flag"],
            }
        ],
    }
    result = kernel.execute_kernel(
        fixture,
        target_start=start,
        target_end=end,
        formal_receipt=formal_receipt,
    )
    if result["decision"] != "PASS_IDENTITY":
        raise AssertionError(f"{source_key}: identity decision failed")
    if result["support_relation"] != "EXACT_TARGET_SUPPORT":
        raise AssertionError(f"{source_key}: support relation changed")
    if result["formula_id"] != "IDENTITY_V1":
        raise AssertionError(f"{source_key}: identity formula changed")
    if (result["value_n"], result["value_d"]) != (
        source["value"].numerator,
        source["value"].denominator,
    ):
        raise AssertionError(f"{source_key}: identity output changed input")
    if result["uncertainty"]["kind"] != "UNKNOWN":
        raise AssertionError(f"{source_key}: UNKNOWN uncertainty was not preserved")

    provenance = {
        "operator_spec_id": formal_receipt["operator_spec"]["operator_spec_id"],
        "operator_version": operator_version,
        "activation_scope": "CANARY_LOCAL_THREE_PROVIDER_IDENTITY_ONLY",
        "provider_key": source_key,
        "provider": source["provider"],
        "dataset": source["dataset"],
        "resource_layer": source["resource_layer"],
        "variable_id": source["variable_id"],
        "source_url": source["source_url"],
        "source_raw_path": source["raw_path"],
        "source_raw_bytes": source["raw_bytes"],
        "source_raw_sha256": source["raw_sha256"],
        "source_interval_start_utc": source["interval_start_utc"],
        "source_interval_end_utc": source["interval_end_utc"],
        "target_interval_start_utc": source["interval_start_utc"],
        "target_interval_end_utc": source["interval_end_utc"],
        "source_unit": source["source_unit"],
        "source_value_n": source["value"].numerator,
        "source_value_d": source["value"].denominator,
        "source_uncertainty_kind": source["uncertainty_kind"],
        "support_relation": result["support_relation"],
        "formula_id": result["formula_id"],
        "output_value_n": result["value_n"],
        "output_value_d": result["value_d"],
        "output_uncertainty_kind": result["uncertainty"]["kind"],
        "partition_aggregation_performed": False,
        "cross_source_composition_performed": False,
        "temporal_alignment_between_providers_performed": False,
        "interpolation_performed": False,
        "imputation_performed": False,
        "coarse_to_fine_performed": False,
        "hold_codes": [],
        "record_locator": source["record_locator"],
    }
    return {
        "decision": result["decision"],
        "hold_code": result["hold_code"],
        "support_relation": result["support_relation"],
        "formula_id": result["formula_id"],
        "input_value_n": source["value"].numerator,
        "input_value_d": source["value"].denominator,
        "output_value_n": result["value_n"],
        "output_value_d": result["value_d"],
        "uncertainty_kind": result["uncertainty"]["kind"],
        "native_interval": {
            "start_utc": source["interval_start_utc"],
            "end_utc": source["interval_end_utc"],
        },
        "source_unit": source["source_unit"],
        "raw_sha256": source["raw_sha256"],
        "provenance_transform_record": provenance,
    }


def run_gate() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("gate id mismatch")
    if any(contract["fences"].values()):
        raise AssertionError("forbidden fence enabled")
    if any(contract["forbidden_behavior"].values()):
        raise AssertionError("forbidden behavior enabled")
    if not all(contract["requirements"].values()):
        raise AssertionError("required three-provider condition disabled")

    pred = predecessor.run_gate()
    expected = contract["predecessor"]
    pred_sha = canonical_sha256(pred)
    if pred_sha != expected["receipt_sha256"]:
        raise AssertionError(
            f"Elexon identity predecessor changed: {pred_sha} != "
            f"{expected['receipt_sha256']}"
        )
    if pred["verdict"] != expected["verdict"]:
        raise AssertionError("Elexon identity predecessor verdict changed")

    operator = contract["operator"]
    if operator["allowed_relation"] != "EXACT_TARGET_SUPPORT":
        raise AssertionError("three-provider canary relation changed")
    if operator["partition_aggregation_allowed"]:
        raise AssertionError("partition aggregation enabled")

    activation = contract["activation"]
    if activation["target_path"] != "PATH_B":
        raise AssertionError("activation path changed")
    if activation["scope"] != "CANARY_LOCAL_THREE_PROVIDER_IDENTITY_ONLY":
        raise AssertionError("activation scope changed")
    if not activation["active_during_canary"]:
        raise AssertionError("local PATH_B activation disabled")
    if activation["global_activation"] or activation["runtime_admission"]:
        raise AssertionError("activation escaped canary boundary")

    source_cfg = contract["sources"]
    parsed = {
        "electricity": parse_elexon(source_cfg["electricity"]),
        "natural_gas": parse_entsog(source_cfg["natural_gas"]),
        "freshwater": parse_bom(source_cfg["freshwater"]),
    }
    intervals = {
        key: (value["interval_start_utc"], value["interval_end_utc"])
        for key, value in parsed.items()
    }
    if len(set(intervals.values())) != 3:
        raise AssertionError("provider-native intervals unexpectedly collapsed")

    formal = kernel.formal_spec.run_gate()
    if formal["operator_spec"]["operator_spec_id"] != operator["operator_spec_id"]:
        raise AssertionError("operator spec id changed")
    if formal["operator_spec"]["operator_version"] != operator["operator_version"]:
        raise AssertionError("operator version changed")

    results = {
        key: execute_identity(
            key,
            value,
            formal_receipt=formal,
            operator_version=operator["operator_version"],
        )
        for key, value in parsed.items()
    }
    if len(results) != 3:
        raise AssertionError("three-provider result count changed")
    if not all(r["decision"] == "PASS_IDENTITY" for r in results.values()):
        raise AssertionError("not all providers passed identity")
    if not all(
        (r["input_value_n"], r["input_value_d"])
        == (r["output_value_n"], r["output_value_d"])
        for r in results.values()
    ):
        raise AssertionError("one provider changed value under identity")
    if not all(r["uncertainty_kind"] == "UNKNOWN" for r in results.values()):
        raise AssertionError("UNKNOWN uncertainty was not preserved 3/3")
    for key, result in results.items():
        if result["raw_sha256"] != source_cfg[key]["raw_sha256"]:
            raise AssertionError(f"{key}: raw SHA provenance bind changed")

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_PATH_B_THREE_PROVIDER_NATIVE_IDENTITY_CANARY_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessor": {
            "receipt_sha256": pred_sha,
            "head_sha": expected["head_sha"],
            "verdict": pred["verdict"],
        },
        "operator": operator,
        "activation": {
            **activation,
            "canary_result": "PASS_3_OF_3_IDENTITY",
            "post_canary_global_state": "LOCKED_NOT_GLOBALLY_ACTIVATED",
        },
        "providers": results,
        "provider_count": 3,
        "pass_identity_count": 3,
        "three_of_three_pass_identity": True,
        "each_provider_kept_own_native_interval": True,
        "provider_native_intervals": intervals,
        "common_window_computed": False,
        "temporal_alignment_between_providers_performed": False,
        "output_equals_input_exactly_3_of_3": True,
        "unknown_uncertainty_preserved_3_of_3": True,
        "raw_sha256_provenance_bound_3_of_3": True,
        "partition_aggregation_performed": False,
        "cross_source_composition_performed": False,
        "interpolation_performed": False,
        "imputation_performed": False,
        "coarse_to_fine_performed": False,
        "core_patch_required": False,
        "fences": contract["fences"],
        "verdict": contract["verdict_target"],
        "claim_ceiling": (
            "Three real providers passed native exact-support identity independently. "
            "No common window, cross-source temporal alignment, partition aggregation, "
            "cross-source composition, runtime admission, or global PATH_B activation occurred."
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
    print("PATH_B_THREE_PROVIDER_NATIVE_IDENTITY_CANARY_RECEIPT_SHA256=" + sha)
