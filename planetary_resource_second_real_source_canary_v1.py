from __future__ import annotations

from dataclasses import asdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any

import planetary_resource_empirical_admission_v1 as admission


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__SECOND_REAL_SOURCE_SINGLE_VARIABLE_ADMISSION_CANARY_V1"
)
MANIFEST_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__SECOND_REAL_SOURCE_CANARY_MANIFEST.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__SECOND_REAL_SOURCE_SINGLE_VARIABLE_ADMISSION_CANARY_RECEIPT.json"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest() -> dict[str, Any]:
    m = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if m["gate_id"] != GATE_ID:
        raise AssertionError("gate_id mismatch")
    if m["counts"] != {"sources": 1, "variables": 1, "nodes": 1, "intervals": 1, "records": 1}:
        raise AssertionError(f"one-only count fence failed: {m['counts']!r}")
    fences = m["fences"]
    required_true = ("different_resource_layer", "first_canary_preserved", "same_admission_contract")
    for key in required_true:
        if fences[key] is not True:
            raise AssertionError(f"{key} must be true")
    required_false = (
        "multi_source_fusion", "aggregation", "eq_score", "ui",
        "runtime_admission", "pointer_promotion", "global_bind", "merge",
    )
    for key in required_false:
        if fences[key] is not False:
            raise AssertionError(f"{key} must be false")
    return m


def parse_and_verify_raw(m: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    source = m["source"]
    raw_path = Path(source["raw_file"])
    raw = raw_path.read_bytes()
    actual_sha = sha256_bytes(raw)
    if actual_sha != source["raw_sha256"]:
        raise AssertionError(
            f"raw SHA256 mismatch actual={actual_sha} expected={source['raw_sha256']}"
        )
    payload = json.loads(raw.decode("utf-8"))
    if list(payload) != ["data"] or len(payload["data"]) != 1:
        raise AssertionError("source snapshot is not exactly one record")
    item = payload["data"][0]
    rec = m["record"]
    pairs = {
        "dataset": item["dataset"],
        "publish_time": item["publishTime"],
        "start_time": item["startTime"],
        "settlement_date": item["settlementDate"],
        "settlement_period": item["settlementPeriod"],
    }
    for key, actual in pairs.items():
        if actual != rec[key]:
            raise AssertionError(f"raw/manifest mismatch {key}: {actual!r} != {rec[key]!r}")
    if Fraction(str(item["demand"])) != Fraction(rec["demand"]):
        raise AssertionError("raw/manifest demand mismatch")
    return raw, payload


def build_candidate(m: dict[str, Any], payload: dict[str, Any]) -> admission.EmpiricalCandidate:
    source = m["source"]
    rec = m["record"]
    a = m["admission"]
    item = payload["data"][0]

    record_locator = (
        source["source_url"]
        + "#INDO/"
        + item["startTime"]
        + f"/SP{item['settlementPeriod']}"
    )
    provenance = admission.ProvenanceRecord(
        source_id=source["source_id"],
        provider=source["provider"],
        dataset_id=source["dataset_id"],
        dataset_version=source["dataset_version"],
        record_locator=record_locator,
        observed_at=rec["start_time"],
        retrieved_at=source["retrieved_at"],
        raw_sha256=source["raw_sha256"],
        citation=source["citation"],
        license_or_terms_ref=source["license_or_terms_ref"],
        access_class=source["access_class"],
    )

    spatial = admission.SpatialMapping(
        method=admission.SpatialMethod(a["spatial_method"]),
        target_node_id=a["target_node_id"],
        target_node_class=a["target_node_class"],
        method_ref=a["spatial_method_ref"],
    )

    temporal = admission.TemporalAlignment(
        method=admission.TemporalMethod(a["temporal_method"]),
        source_interval_id=a["interval_id"],
        target_interval_id=a["interval_id"],
        method_ref=a["temporal_method_ref"],
        interpolation_used=False,
        interpolation_method_ref="",
        imputation_used=False,
        imputation_method_ref="",
    )

    uncertainty = admission.UncertaintyDeclaration(
        kind=admission.UncertaintyKind(a["uncertainty"]["kind"]),
        method_ref=a["uncertainty"]["method_ref"],
    )

    return admission.EmpiricalCandidate(
        variable_id=a["variable_id"],
        value=Fraction(str(item["demand"])),
        source_unit=rec["source_unit"],
        source_layer=a["source_layer"],
        source_quantity_kind=a["source_quantity_kind"],
        source_status=admission.SourceStatus(a["source_status"]),
        provenance=provenance,
        spatial_mapping=spatial,
        temporal_alignment=temporal,
        uncertainty=uncertainty,
        as_of=a["as_of"],
        max_age_seconds=int(a["max_age_seconds"]),
        missingness_reason=a["missingness"]["reason"],
        source_gas_basis="",
        sign_semantics_declared=bool(a["sign_semantics_declared"]),
        transform_chain=(
            "source:elexon_insights_indo_api_v1",
            f"raw_sha256:{source['raw_sha256']}",
            f"publish_time:{rec['publish_time']}",
            f"settlement_period:{rec['settlement_period']}",
        ),
    )


def run_canary() -> dict[str, Any]:
    m = load_manifest()
    raw, payload = parse_and_verify_raw(m)
    candidate = build_candidate(m, payload)
    admitted = admission.admit(candidate)
    a = m["admission"]
    rec = m["record"]
    source = m["source"]
    predecessor = m["predecessor"]

    expected_watts = Fraction(rec["demand"]) * 1_000_000
    if admitted.decision != admission.AdmissionDecision.ADMIT_OBSERVED.value:
        raise AssertionError(f"unexpected decision: {admitted.decision}")
    if Fraction(admitted.canonical_value_n, admitted.canonical_value_d) != expected_watts:
        raise AssertionError("canonical value mismatch")
    if admitted.canonical_unit != "W_e":
        raise AssertionError("canonical unit mismatch")
    if admitted.variable_id != "electricity.consumption_rate":
        raise AssertionError("variable mismatch")
    if admitted.layer != "ELECTRICITY":
        raise AssertionError("second canary did not use a different resource layer")
    if admitted.target_node_id != a["target_node_id"]:
        raise AssertionError("node mismatch")
    if admitted.freshness_age_seconds != int(a["expected_freshness_age_seconds"]):
        raise AssertionError(
            f"freshness mismatch {admitted.freshness_age_seconds} "
            f"!= {a['expected_freshness_age_seconds']}"
        )
    if admitted.uncertainty_kind != "UNKNOWN":
        raise AssertionError("uncertainty must remain UNKNOWN")
    if admitted.output_status != "OBSERVED":
        raise AssertionError("source value must remain OBSERVED")
    if any(x.startswith("interpolation:") for x in admitted.transform_chain):
        raise AssertionError("silent interpolation appeared")
    if any(x.startswith("imputation:") for x in admitted.transform_chain):
        raise AssertionError("silent imputation appeared")

    required_transforms = {
        "unit:MW->W_e",
        "spatial:NODE_LOOKUP",
        "temporal:EXACT_INTERVAL",
    }
    if not required_transforms.issubset(set(admitted.transform_chain)):
        raise AssertionError(f"required transform missing: {admitted.transform_chain!r}")

    first_raw = Path(
        "sources/environment_agency/1100TH_flow_mean_15min_2026-10-01T21-30Z.json"
    ).read_bytes()
    if hashlib.sha256(first_raw).hexdigest() != (
        "c180db17bc02d371f1eebb4667695b715f0ce2f9c2f97bab6893b77f87c97c29"
    ):
        raise AssertionError("first canary raw source was not preserved")

    contract_sha = hashlib.sha256(
        Path("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__EMPIRICAL_DATA_CONTRACT.json").read_bytes()
    ).hexdigest()
    validator_sha = hashlib.sha256(
        Path("planetary_resource_empirical_admission_v1.py").read_bytes()
    ).hexdigest()
    if contract_sha != predecessor["empirical_contract_sha256"]:
        raise AssertionError("empirical contract changed")
    if validator_sha != predecessor["empirical_validator_sha256"]:
        raise AssertionError("empirical validator changed")

    receipt = {
        "schema_version": "EQUILIBRIUM_PRS_SECOND_REAL_SOURCE_CANARY_RECEIPT_V1",
        "gate_id": GATE_ID,
        "counts": m["counts"],
        "predecessor": predecessor,
        "source": {
            "provider": source["provider"],
            "underlying_data_source": source["underlying_data_source"],
            "dataset_id": source["dataset_id"],
            "dataset_name": source["dataset_name"],
            "dataset_version": source["dataset_version"],
            "source_url": source["source_url"],
            "documentation_url": source["documentation_url"],
            "scrape_id": source["scrape_id"],
            "retrieved_at": source["retrieved_at"],
            "raw_file": source["raw_file"],
            "raw_byte_length": len(raw),
            "raw_sha256": source["raw_sha256"],
            "license_or_terms_ref": source["license_or_terms_ref"],
        },
        "record": rec,
        "provenance_complete": True,
        "unit_transform_receipt": {
            "source_unit": rec["source_unit"],
            "canonical_unit": admitted.canonical_unit,
            "factor_n": a["unit_transform"]["factor_n"],
            "factor_d": a["unit_transform"]["factor_d"],
            "source_value": rec["demand"],
            "canonical_value_n": admitted.canonical_value_n,
            "canonical_value_d": admitted.canonical_value_d,
        },
        "spatial_mapping_receipt": {
            "method": a["spatial_method"],
            "method_ref": a["spatial_method_ref"],
            "target_node_id": a["target_node_id"],
            "target_node_class": a["target_node_class"],
            "claim_ceiling": a["spatial_claim_ceiling"],
        },
        "temporal_alignment_receipt": {
            "interval_id": a["interval_id"],
            "method": a["temporal_method"],
            "method_ref": a["temporal_method_ref"],
            "start_time": rec["start_time"],
            "settlement_period": rec["settlement_period"],
            "duration_seconds": 1800,
            "timestamp_semantics": a["timestamp_semantics"],
            "interpolation_used": False,
            "imputation_used": False,
            "aggregation_performed": False,
        },
        "freshness_readback": {
            "observed_at": rec["start_time"],
            "published_at": rec["publish_time"],
            "as_of": a["as_of"],
            "age_seconds": admitted.freshness_age_seconds,
            "max_age_seconds": a["max_age_seconds"],
            "fresh_at_admission": admitted.freshness_age_seconds <= a["max_age_seconds"],
        },
        "uncertainty_declaration": {
            "kind": admitted.uncertainty_kind,
            "source_provided_measurement_uncertainty": False,
            "promotion_to_exact": False,
        },
        "missingness_semantics": {
            "value_present": True,
            "source_status": a["source_status"],
            "zero_is_missing": False,
            "missingness_reason": "",
        },
        "empirical_admission_receipt": asdict(admitted),
        "same_admission_contract": True,
        "first_canary_preserved": True,
        "different_resource_layer": True,
        "no_silent_transform": True,
        "fences": m["fences"],
        "verdict": "PASS_BOUNDED_SECOND_REAL_SOURCE_SINGLE_VARIABLE_ADMIT_OBSERVED",
    }
    return receipt


def write_receipt() -> tuple[dict[str, Any], str]:
    receipt = run_canary()
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    OUT_PATH.write_text(canonical, encoding="utf-8")
    sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return receipt, sha


if __name__ == "__main__":
    receipt, sha = write_receipt()
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    print("SECOND_REAL_SOURCE_CANARY_RECEIPT_SHA256=" + sha)
