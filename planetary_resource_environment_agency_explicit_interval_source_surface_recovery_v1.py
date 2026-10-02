from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import planetary_resource_source_interval_semantics_recovery_v1 as predecessor


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__ENVIRONMENT_AGENCY_EXPLICIT_INTERVAL_SOURCE_SURFACE_RECOVERY_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__ENVIRONMENT_AGENCY_EXPLICIT_INTERVAL_SOURCE_SURFACE_RECOVERY.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__ENVIRONMENT_AGENCY_EXPLICIT_INTERVAL_SOURCE_SURFACE_RECOVERY_RECEIPT.json"
)


def canonical_sha256(payload: dict[str, Any]) -> str:
    body = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("gate id mismatch")
    if contract["target"] != "ENVIRONMENT_AGENCY_ONLY":
        raise AssertionError("target scope changed")
    if not contract["official_primary_documentation_only"]:
        raise AssertionError("primary-documentation-only fence disabled")
    if any(contract["fences"].values()):
        raise AssertionError(f"forbidden scope enabled: {contract['fences']!r}")
    return contract


def run_gate() -> dict[str, Any]:
    contract = load_contract()

    pred = predecessor.run_gate()
    pred_sha = canonical_sha256(pred)
    expected = contract["predecessor"]["receipt_sha256"]
    if pred_sha != expected:
        raise AssertionError(
            f"predecessor receipt changed: {pred_sha} != {expected}"
        )

    recovery = pred["recovery"]
    if not recovery["elexon_recovered"]:
        raise AssertionError("Elexon recovery regressed")
    if not recovery["entsog_already_satisfied"]:
        raise AssertionError("ENTSOG satisfied state regressed")
    if recovery["environment_agency_recovered"]:
        raise AssertionError(
            "predecessor now says EA recovered; this successor must be replaced"
        )

    candidates = contract["candidate_source_surfaces"]
    if not candidates:
        raise AssertionError("no Environment Agency candidate surfaces recorded")

    eligible = [row for row in candidates if row["eligible"]]
    if eligible:
        raise AssertionError(
            "An eligible Environment Agency interval surface is now recorded; "
            "replace this HOLD gate with a bounded source-admission successor."
        )

    expected_ids = {
        "EA_FLOOD_MONITORING_FLOW_MEAN",
        "EA_HYDROLOGY_FLOW_15MIN_INSTANTANEOUS",
        "EA_HYDROLOGY_FLOW_DAILY_MEAN",
        "EA_TIDE_GAUGE_15MIN_MEAN",
    }
    actual_ids = {row["id"] for row in candidates}
    if actual_ids != expected_ids:
        raise AssertionError(f"candidate audit set changed: {actual_ids!r}")

    hydrology_15 = next(
        row for row in candidates
        if row["id"] == "EA_HYDROLOGY_FLOW_15MIN_INSTANTANEOUS"
    )
    if hydrology_15["positive_duration_interval"]:
        raise AssertionError("instantaneous hydrology flow promoted to interval")

    tide = next(
        row for row in candidates if row["id"] == "EA_TIDE_GAUGE_15MIN_MEAN"
    )
    if tide["variable_family"] == "freshwater_flow":
        raise AssertionError("tide-gauge level silently relabeled as freshwater flow")

    blockers = [
        {
            "surface_id": row["id"],
            "code": row["rejection_code"],
            "url": row["url"],
        }
        for row in candidates
    ]

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_ENVIRONMENT_AGENCY_EXPLICIT_INTERVAL_SOURCE_SURFACE_RECOVERY_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessor": {
            "receipt_sha256": pred_sha,
            "verdict": pred["verdict"],
        },
        "frozen_external_semantics": {
            "elexon_recovered": True,
            "entsog_satisfied": True,
        },
        "environment_agency_candidate_surface_audit": candidates,
        "candidate_surface_count": len(candidates),
        "eligible_freshwater_flow_interval_surface_count": 0,
        "explicit_start_end_surface_found": False,
        "authoritative_positive_duration_boundary_rule_found": False,
        "blockers": blockers,
        "new_source_ingest_performed": False,
        "new_source_records_ingested": 0,
        "datetime_minus_period_inference_used": False,
        "center_window_inference_used": False,
        "assumed_15_minute_window_used": False,
        "composition_performed": False,
        "core_patch_required": False,
        "new_domain_math_added": False,
        "fences": contract["fences"],
        "verdict": contract["verdict_target"],
        "minimum_unblock": (
            "Environment Agency must publish either freshwater-flow observations "
            "with explicit start/end interval bounds or an authoritative rule "
            "binding the timestamp of a positive-duration flow aggregate to a "
            "specific interval boundary. Instantaneous flow observations do not "
            "satisfy the common-window requirement."
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
    print(
        "EA_EXPLICIT_INTERVAL_SOURCE_SURFACE_RECOVERY_RECEIPT_SHA256=" + sha
    )
