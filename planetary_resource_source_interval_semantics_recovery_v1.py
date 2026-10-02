from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import planetary_resource_temporally_aligned_three_source_snapshot_set_v1 as predecessor
import planetary_resource_second_real_source_canary_v1 as electricity_canary


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__SOURCE_INTERVAL_SEMANTICS_RECOVERY_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__SOURCE_INTERVAL_SEMANTICS_RECOVERY.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__SOURCE_INTERVAL_SEMANTICS_RECOVERY_RECEIPT.json"
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
    if any(contract["fences"].values()):
        raise AssertionError(f"forbidden scope enabled: {contract['fences']!r}")
    if not contract["requirements"]["official_primary_documentation_only"]:
        raise AssertionError("primary documentation fence disabled")
    if not contract["requirements"]["no_inferred_boundaries"]:
        raise AssertionError("boundary inference fence disabled")
    return contract


def run_gate() -> dict[str, Any]:
    contract = load_contract()

    predecessor_receipt = predecessor.run_gate()
    predecessor_sha = canonical_sha256(predecessor_receipt)
    expected_sha = contract["predecessor"]["receipt_sha256"]
    if predecessor_sha != expected_sha:
        raise AssertionError(
            f"predecessor receipt changed: {predecessor_sha} != {expected_sha}"
        )

    elexon_receipt = electricity_canary.run_canary()
    elexon_admission = elexon_receipt["empirical_admission_receipt"]
    if elexon_admission["variable_id"] != "electricity.consumption_rate":
        raise AssertionError("pinned Elexon binding changed")
    if elexon_admission["uncertainty_kind"] != "UNKNOWN":
        raise AssertionError("Elexon uncertainty changed")

    targets = contract["targets"]
    ea = targets["environment_agency"]
    elexon = targets["elexon"]

    if ea["explicit_boundary_anchor_found"]:
        raise AssertionError(
            "EA boundary anchor is now claimed proven; update the recovery gate "
            "with the new official primary evidence before changing verdict."
        )

    if not elexon["authoritative_end_bound_found"]:
        raise AssertionError("Elexon authoritative end-bound proof disappeared")
    if elexon["end_bound_rule"] != "END_UTC = START_TIME_UTC + 30_MINUTES":
        raise AssertionError("Elexon end-bound rule changed")

    source_start = elexon_receipt["record"]["start_time"]
    if source_start != "2026-10-01T22:00:00Z":
        raise AssertionError("pinned Elexon source start changed")
    authoritative_end = "2026-10-01T22:30:00Z"

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_SOURCE_INTERVAL_SEMANTICS_RECOVERY_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessor": {
            "receipt_sha256": predecessor_sha,
            "verdict": predecessor_receipt["verdict"],
        },
        "environment_agency": {
            "status": ea["status"],
            "required_proof": ea["required_proof"],
            "official_primary_sources": ea["official_primary_sources"],
            "facts_proven": {
                "reading_has_datetime": True,
                "measure_has_period_between_successive_readings": True,
                "mean_is_over_measurement_period": True,
            },
            "missing_proof": (
                "No official primary source found that defines whether reading "
                "dateTime is the start, end, or center boundary of a mean period."
            ),
            "boundary_inferred": False,
        },
        "elexon": {
            "status": elexon["status"],
            "required_proof": elexon["required_proof"],
            "official_primary_sources": elexon["official_primary_sources"],
            "indo_average_per_settlement_period": True,
            "settlement_period_duration_minutes": 30,
            "settlement_period_start_anchor": "START_TIME_OF_HALF_HOUR_PERIOD",
            "authoritative_end_bound_rule": elexon["end_bound_rule"],
            "pinned_record_start_utc": source_start,
            "authoritative_record_end_utc": authoritative_end,
            "boundary_inferred": False,
            "proof_basis": (
                "The record start is the start time of the half-hour Settlement "
                "Period; Elexon BSC defines that period as 30 minutes and defines "
                "its end exactly 30 minutes after the starting spot time."
            ),
        },
        "recovery": {
            "environment_agency_recovered": False,
            "elexon_recovered": True,
            "entsog_already_satisfied": True,
            "all_required_source_semantics_recovered": False,
        },
        "new_source_ingest_performed": False,
        "new_source_records_ingested": 0,
        "composition_performed": False,
        "core_patch_required": False,
        "new_domain_math_added": False,
        "fences": contract["fences"],
        "verdict": contract["verdict_target"],
        "minimum_unblock": (
            "Obtain an Environment Agency primary source that explicitly anchors "
            "reading dateTime to the start/end/center of the mean measurement "
            "period, or use an Environment Agency source surface that directly "
            "publishes both interval bounds."
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
    print("SOURCE_INTERVAL_SEMANTICS_RECOVERY_RECEIPT_SHA256=" + sha)
