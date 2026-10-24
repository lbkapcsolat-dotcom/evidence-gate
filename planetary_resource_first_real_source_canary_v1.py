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
    "__FIRST_REAL_SOURCE_SINGLE_VARIABLE_ADMISSION_CANARY_V1"
)
MANIFEST_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__FIRST_REAL_SOURCE_CANARY_MANIFEST.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__FIRST_REAL_SOURCE_SINGLE_VARIABLE_ADMISSION_CANARY_RECEIPT.json"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest() -> dict[str, Any]:
    m = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if m["gate_id"] != GATE_ID:
        raise AssertionError("gate_id mismatch")
    if m["counts"] != {"sources": 1, "variables": 1, "nodes": 1, "intervals": 1, "records": 1}:
        raise AssertionError(f"one-only count fence failed: {m['counts']!r}")
    if any(m["fences"].values()):
        raise AssertionError(f"scope fence enabled unexpectedly: {m['fences']!r}")
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
    if payload["meta"]["publisher"] != "Environment Agency":
        raise AssertionError("publisher mismatch")
    if payload["meta"]["version"] != "0.9":
        raise AssertionError("source API version mismatch")
    if payload["meta"]["limit"] != 1 or len(payload["items"]) != 1:
        raise AssertionError("raw source response is not exactly one record")

    item = payload["items"][0]
    rec = m["record"]
    measure = item["measure"]

    exact_pairs = {
        "record_locator": item["@id"],
        "observed_at": item["dateTime"],
        "measure_uri": measure["@id"],
        "station_reference": measure["stationReference"],
        "station_label": measure["station"]["label"],
        "parameter": measure["parameter"],
        "period_seconds": measure["period"],
        "value_type": measure["valueType"],
        "source_unit": measure["unitName"],
    }
    for key, actual in exact_pairs.items():
        if actual != rec[key]:
            raise AssertionError(f"raw/manifest mismatch {key}: {actual!r} != {rec[key]!r}")

    if Fraction(str(item["value"])) != Fraction(rec["value"]):
        raise AssertionError("raw/manifest value mismatch")

    return raw, payload


def build_candidate(m: dict[str, Any], payload: dict[str, Any]) -> admission.EmpiricalCandidate:
    source = m["source"]
    rec = m["record"]
    a = m["admission"]
    item = payload["items"][0]

    provenance = admission.ProvenanceRecord(
        source_id=source["source_id"],
        provider=source["provider"],
        dataset_id=source["dataset_id"],
        dataset_version=source["dataset_version"],
        record_locator=rec["record_locator"],
        observed_at=rec["observed_at"],
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
        value=Fraction(str(item["value"])),
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
        source_gas_basis=a["source_gas_basis"],
        sign_semantics_declared=bool(a["sign_semantics_declared"]),
        transform_chain=(
            "source:environment_agency_flood_monitoring_api_v0.9",
            f"raw_sha256:{source['raw_sha256']}",
            f"record:{rec['record_locator']}",
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

    expected_value = Fraction(rec["value"])
    if admitted.decision != admission.AdmissionDecision.ADMIT_OBSERVED.value:
        raise AssertionError(f"unexpected decision: {admitted.decision}")
    if Fraction(admitted.canonical_value_n, admitted.canonical_value_d) != expected_value:
        raise AssertionError("canonical value mismatch")
    if admitted.canonical_unit != "m3/s":
        raise AssertionError("canonical unit mismatch")
    if admitted.variable_id != "freshwater.internal_flow_rate":
        raise AssertionError("variable mismatch")
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
        "unit:m3/s->m3/s",
        "spatial:NODE_LOOKUP",
        "temporal:EXACT_INTERVAL",
    }
    if not required_transforms.issubset(set(admitted.transform_chain)):
        raise AssertionError(f"required transform missing: {admitted.transform_chain!r}")

    receipt = {
        "schema_version": "EQUILIBRIUM_PRS_FIRST_REAL_SOURCE_CANARY_RECEIPT_V1",
        "gate_id": GATE_ID,
        "counts": m["counts"],
        "source": {
            "provider": source["provider"],
            "dataset_id": source["dataset_id"],
            "dataset_version": source["dataset_version"],
            "source_url": source["source_url"],
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
            "identity": (
                a["unit_transform"]["factor_n"] == 1
                and a["unit_transform"]["factor_d"] == 1
                and rec["source_unit"] == admitted.canonical_unit
            ),
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
            "period_seconds": rec["period_seconds"],
            "value_type": rec["value_type"],
            "timestamp_semantics": a["timestamp_semantics"],
            "interpolation_used": False,
            "imputation_used": False,
        },
        "freshness_readback": {
            "observed_at": rec["observed_at"],
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
        "no_silent_transform": True,
        "fences": {
            **m["fences"],
            "single_external_record_admitted": True,
            "global_dataset_admitted": False,
        },
        "verdict": "PASS_BOUNDED_FIRST_REAL_SOURCE_SINGLE_VARIABLE_ADMIT_OBSERVED",
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
    print("FIRST_REAL_SOURCE_CANARY_RECEIPT_SHA256=" + sha)
