from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import planetary_resource_real_three_layer_input_composition_canary_v1 as predecessor
import planetary_resource_first_real_source_canary_v1 as water_canary
import planetary_resource_second_real_source_canary_v1 as electricity_canary
import planetary_resource_third_real_source_gas_canary_v1 as gas_canary


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__TEMPORALLY_ALIGNED_THREE_SOURCE_SNAPSHOT_SET_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__TEMPORALLY_ALIGNED_THREE_SOURCE_SNAPSHOT_SET.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__TEMPORALLY_ALIGNED_THREE_SOURCE_SNAPSHOT_SET_RECEIPT.json"
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
    return contract


def run_gate() -> dict[str, Any]:
    contract = load_contract()

    predecessor_receipt = predecessor.run_canary()
    predecessor_sha = canonical_sha256(predecessor_receipt)
    expected_sha = contract["predecessor"]["receipt_sha256"]
    if predecessor_sha != expected_sha:
        raise AssertionError(
            f"predecessor HOLD receipt changed: {predecessor_sha} != {expected_sha}"
        )

    revalidated = {
        "freshwater": water_canary.run_canary(),
        "electricity": electricity_canary.run_canary(),
        "natural_gas": gas_canary.run_canary(),
    }

    sem = contract["source_semantics_preflight"]
    blockers: list[dict[str, Any]] = []

    ea = sem["environment_agency"]
    if not ea["explicit_timestamp_anchor_to_period_boundary_documented"]:
        blockers.append(
            {
                "code": "HOLD_ENVIRONMENT_AGENCY_INTERVAL_ANCHOR_UNPROVEN",
                "source": "ENVIRONMENT_AGENCY",
                "official_reference_url": ea["official_reference_url"],
                "period_semantics": ea["period_semantics"],
                "datetime_semantics": ea["datetime_semantics"],
                "mean_semantics": ea["mean_semantics"],
                "existing_binding_timestamp_semantics":
                    ea["existing_binding_timestamp_semantics"],
                "reason": (
                    "The official reference exposes reading dateTime, period and "
                    "mean semantics but does not document whether dateTime is the "
                    "start, end or center boundary of the mean period. The existing "
                    "proven binding explicitly forbids inferring a start boundary."
                ),
            }
        )

    elexon = sem["elexon"]
    if not elexon["existing_record_has_explicit_end_time"]:
        blockers.append(
            {
                "code": "HOLD_ELEXON_EXPLICIT_END_BOUND_NOT_SOURCE_FIELD",
                "source": "ELEXON",
                "official_reference_url": elexon["official_reference_url"],
                "dataset": elexon["dataset"],
                "reason": (
                    "The proven INDO record carries startTime and half-hour "
                    "settlement semantics, but the pinned record does not carry "
                    "an explicit end-time field. This strict gate requires both "
                    "interval bounds to be source-explicit before ingest."
                ),
            }
        )

    entsog = sem["entsog"]
    if not (
        entsog["existing_record_has_period_from"]
        and entsog["existing_record_has_period_to"]
        and entsog["eligible_for_explicit_bounds"]
    ):
        blockers.append(
            {
                "code": "HOLD_ENTSOG_EXPLICIT_BOUNDS_UNPROVEN",
                "source": "ENTSOG",
                "official_reference_url": entsog["official_reference_url"],
            }
        )

    if not blockers:
        raise AssertionError(
            "All three source interval semantics now satisfy strict explicit "
            "bounds; replace this preflight HOLD with bounded ingest."
        )

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_TEMPORALLY_ALIGNED_THREE_SOURCE_SNAPSHOT_SET_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessor": {
            "receipt_sha256": predecessor_sha,
            "verdict": predecessor_receipt["verdict"],
        },
        "revalidated_existing_bindings": {
            name: {
                "canary_receipt_sha256": canonical_sha256(receipt),
                "decision": receipt["empirical_admission_receipt"]["decision"],
                "uncertainty_kind":
                    receipt["empirical_admission_receipt"]["uncertainty_kind"],
                "raw_sha256": (
                    receipt.get("measurement_source", receipt.get("source", {}))
                    .get("raw_sha256")
                ),
            }
            for name, receipt in revalidated.items()
        },
        "source_semantics_preflight": sem,
        "blockers": blockers,
        "explicit_interval_bounds_proven_for_all_three": False,
        "positive_duration_common_window_proven": False,
        "new_source_records_ingested": 0,
        "new_source_ingest_performed": False,
        "reason_new_ingest_not_performed": (
            "Source-interval semantics preflight failed before network ingest. "
            "Downloading more records from the same unresolved schemas would "
            "not prove strict interval bounds."
        ),
        "raw_bytes_preservation_scope": "EXISTING_PROVEN_BINDINGS_UNCHANGED",
        "sha256_preserved": True,
        "source_provenance_preserved": True,
        "unknown_uncertainty_preserved": all(
            receipt["empirical_admission_receipt"]["uncertainty_kind"] == "UNKNOWN"
            for receipt in revalidated.values()
        ),
        "interpolation_performed": False,
        "imputation_performed": False,
        "cross_interval_aggregation_performed": False,
        "composition_performed": False,
        "new_domain_math_added": False,
        "core_patch_required": False,
        "fences": contract["fences"],
        "verdict": contract["hold_verdict"],
        "minimum_unblock": [
            (
                "Environment Agency: obtain authoritative semantics that bind "
                "reading dateTime to an explicit mean-period boundary, or use "
                "an Environment Agency source surface that publishes start/end."
            ),
            (
                "Elexon: obtain a source-explicit end bound for INDO or an "
                "authoritative schema statement making the half-hour end bound "
                "part of the source contract."
            ),
            (
                "Then ingest exactly one aligned snapshot per source and prove "
                "a positive-duration three-way intersection before composition."
            ),
        ],
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
    print("TEMPORALLY_ALIGNED_THREE_SOURCE_SNAPSHOT_SET_RECEIPT_SHA256=" + sha)
