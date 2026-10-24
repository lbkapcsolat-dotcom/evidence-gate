from __future__ import annotations

from dataclasses import asdict
from fractions import Fraction
import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any

import planetary_resource_empirical_admission_v1 as admission


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__THIRD_REAL_SOURCE_NATURAL_GAS_SINGLE_VARIABLE_ADMISSION_CANARY_V1"
)
MANIFEST_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__THIRD_REAL_SOURCE_GAS_CANARY_MANIFEST.json"
)
BASIS_EVIDENCE_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__GAS_ENERGY_BASIS_EVIDENCE.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__THIRD_REAL_SOURCE_NATURAL_GAS_SINGLE_VARIABLE_ADMISSION_CANARY_RECEIPT.json"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest() -> dict[str, Any]:
    m = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if m["gate_id"] != GATE_ID:
        raise AssertionError("gate_id mismatch")
    expected_counts = {
        "measurement_sources": 1,
        "variables": 1,
        "nodes": 1,
        "intervals": 1,
        "records": 1,
        "normative_support_refs": 3,
    }
    if m["counts"] != expected_counts:
        raise AssertionError(f"one-only count fence failed: {m['counts']!r}")
    required_true = (
        "preserve_water_canary",
        "preserve_electricity_canary",
        "same_admission_contract",
        "one_measurement_source_only",
        "no_volume_to_energy_conversion",
        "no_silent_calorific_value_assumption",
    )
    for key in required_true:
        if m["fences"][key] is not True:
            raise AssertionError(f"{key} must be true")
    for key in (
        "multi_source_fusion",
        "aggregation",
        "eq_score",
        "ui",
        "runtime_admission",
        "pointer_promotion",
        "global_bind",
        "merge",
    ):
        if m["fences"][key] is not False:
            raise AssertionError(f"{key} must be false")
    return m


def verify_energy_basis_evidence(m: dict[str, Any]) -> dict[str, Any]:
    e = json.loads(BASIS_EVIDENCE_PATH.read_text(encoding="utf-8"))
    if e["measurement_source_count"] != 1:
        raise AssertionError("support evidence must not add a measurement source")
    if e["support_authority_count"] != 3 or len(e["evidence"]) != 3:
        raise AssertionError("expected exactly three support authority references")
    roles = {x["role"]: x for x in e["evidence"]}
    required = {"SOURCE_UNIT_SEMANTICS", "ENERGY_BASIS", "GCV_TO_HHV_LABEL_EQUIVALENCE"}
    if set(roles) != required:
        raise AssertionError(f"energy-basis support roles mismatch: {set(roles)!r}")
    if "kWh/d or kWh/h" not in roles["SOURCE_UNIT_SEMANTICS"]["section_claim"]:
        raise AssertionError("ENTSOG physical-flow source-unit evidence missing")
    if "GCV" not in roles["ENERGY_BASIS"]["section_claim"]:
        raise AssertionError("GCV energy basis evidence missing")
    if "higher" not in roles["GCV_TO_HHV_LABEL_EQUIVALENCE"]["section_claim"].lower():
        raise AssertionError("gross/higher terminology evidence missing")
    if e["inference_limits"] != {
        "infer_calorific_value_numeric": False,
        "volume_to_energy_conversion": False,
        "infer_lhv": False,
        "measurement_uncertainty_assumed": False,
    }:
        raise AssertionError("energy-basis inference fence changed")
    if m["energy_basis"]["source_energy_basis"] != "GCV":
        raise AssertionError("source basis must be explicit GCV")
    if m["energy_basis"]["core_basis_label"] != "HHV":
        raise AssertionError("core basis label must remain HHV")
    return e


def parse_and_verify_raw(m: dict[str, Any]) -> tuple[bytes, dict[str, str]]:
    source = m["measurement_source"]
    raw_path = Path(source["raw_file"])
    raw = raw_path.read_bytes()
    if len(raw) != source["raw_byte_length"]:
        raise AssertionError("raw byte length mismatch")
    actual_sha = sha256_bytes(raw)
    if actual_sha != source["raw_sha256"]:
        raise AssertionError(
            f"raw SHA256 mismatch actual={actual_sha} expected={source['raw_sha256']}"
        )

    text = raw.decode("utf-8")
    start = text.index("<body>") + len("<body>")
    end = text.index("</body>")
    csv_text = text[start:end]
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    if len(rows) != 1:
        raise AssertionError(f"expected one ENTSOG data row, got {len(rows)}")
    row = rows[0]

    rec = m["record"]
    exact = {
        "id": row["id"],
        "indicator": row["indicator"],
        "periodType": row["periodType"],
        "operatorKey": row["operatorKey"],
        "tsoEicCode": row["tsoEicCode"],
        "operatorLabel": row["operatorLabel"],
        "pointKey": row["pointKey"],
        "pointLabel": row["pointLabel"],
        "tsoItemIdentifier": row["tsoItemIdentifier"],
        "directionKey": row["directionKey"],
        "unit": row["unit"],
        "value": row["value"],
        "lastUpdateDateTime": row["lastUpdateDateTime"],
        "flowStatus": row["flowStatus"],
    }
    expected = {
        "id": rec["id"],
        "indicator": source["indicator"],
        "periodType": source["period_type"],
        "operatorKey": source["operator_key"],
        "tsoEicCode": source["tso_eic_code"],
        "operatorLabel": source["operator_label"],
        "pointKey": source["point_key"],
        "pointLabel": source["point_label"],
        "tsoItemIdentifier": source["tso_item_identifier"],
        "directionKey": source["direction"],
        "unit": rec["unit"],
        "value": rec["value"],
        "lastUpdateDateTime": rec["last_update_source_display"],
        "flowStatus": rec["flow_status"],
    }
    if exact != expected:
        raise AssertionError(f"raw/manifest record mismatch: {exact!r} != {expected!r}")
    return raw, row


def build_candidate(m: dict[str, Any], row: dict[str, str]) -> admission.EmpiricalCandidate:
    source = m["measurement_source"]
    rec = m["record"]
    a = m["admission"]

    if rec["unit"] != "kWh/h":
        raise AssertionError("source unit must be exactly kWh/h")
    if m["energy_basis"]["source_energy_basis"] != "GCV":
        raise AssertionError("GCV basis is required")
    if m["energy_basis"]["volume_to_energy_conversion_performed"]:
        raise AssertionError("volume-to-energy conversion is prohibited")
    if m["energy_basis"]["calorific_value_assumed"]:
        raise AssertionError("silent calorific-value assumption is prohibited")

    # Source adapter only changes the semantic unit label. Numerically:
    # 1 kWh/h = 1 kW. Because EU gas-energy publication is GCV-based and
    # ISO terminology maps gross to higher, kWh/h_GCV is represented as
    # kW_HHV for the unchanged empirical contract.
    adapted_value = Fraction(row["value"])

    provenance = admission.ProvenanceRecord(
        source_id=source["source_id"],
        provider=source["provider"],
        dataset_id="ENTSOG_TRANSPARENCY_PLATFORM_OPERATIONALDATA_PHYSICAL_FLOW",
        dataset_version="TP_OPERATIONALDATA_V1",
        record_locator=source["source_url"] + "#" + rec["id"],
        observed_at=a["observed_at_for_freshness"],
        retrieved_at=source["retrieved_at"],
        raw_sha256=source["raw_sha256"],
        citation=source["citation"],
        license_or_terms_ref="https://transparency.entsog.eu/",
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
        value=adapted_value,
        source_unit=a["source_unit_adapter"],
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
            "source:entsog_transparency_platform_physical_flow",
            f"raw_sha256:{source['raw_sha256']}",
            "energy_basis:GCV",
            "terminology:GCV->HHV",
            "source_unit_adapter:kWh/h_GCV->kW_HHV:factor=1",
            "volume_to_energy_conversion:false",
            "calorific_value_assumption:false",
        ),
    )


def verify_predecessors(m: dict[str, Any]) -> None:
    p = m["predecessor"]

    raw1 = Path(
        "sources/environment_agency/1100TH_flow_mean_15min_2026-10-01T21-30Z.json"
    ).read_bytes()
    if hashlib.sha256(raw1).hexdigest() != (
        "c180db17bc02d371f1eebb4667695b715f0ce2f9c2f97bab6893b77f87c97c29"
    ):
        raise AssertionError("water canary raw source changed")

    raw2 = Path("sources/elexon/INDO_2026-10-01T22-00Z.json").read_bytes()
    if hashlib.sha256(raw2).hexdigest() != (
        "831ed964ef11527f0d8db767665289b59f5ef7b32fac02cd7667ad4b949a7242"
    ):
        raise AssertionError("electricity canary raw source changed")

    contract_sha = hashlib.sha256(
        Path("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__EMPIRICAL_DATA_CONTRACT.json").read_bytes()
    ).hexdigest()
    validator_sha = hashlib.sha256(
        Path("planetary_resource_empirical_admission_v1.py").read_bytes()
    ).hexdigest()
    if contract_sha != p["empirical_contract_sha256"]:
        raise AssertionError("empirical contract changed")
    if validator_sha != p["empirical_validator_sha256"]:
        raise AssertionError("empirical validator changed")


def run_canary() -> dict[str, Any]:
    m = load_manifest()
    basis = verify_energy_basis_evidence(m)
    verify_predecessors(m)
    raw, row = parse_and_verify_raw(m)
    candidate = build_candidate(m, row)
    admitted = admission.admit(candidate)

    source = m["measurement_source"]
    rec = m["record"]
    a = m["admission"]

    expected_watts = Fraction(rec["value"]) * 1000

    if admitted.decision != admission.AdmissionDecision.ADMIT_OBSERVED.value:
        raise AssertionError(f"unexpected decision: {admitted.decision}")
    if Fraction(admitted.canonical_value_n, admitted.canonical_value_d) != expected_watts:
        raise AssertionError("canonical W_th value mismatch")
    if admitted.canonical_unit != "W_th":
        raise AssertionError("canonical unit must be W_th")
    if admitted.variable_id != "natural_gas.import_rate":
        raise AssertionError("variable mismatch")
    if admitted.layer != "NATURAL_GAS":
        raise AssertionError("layer mismatch")
    if admitted.freshness_age_seconds != int(a["expected_freshness_age_seconds"]):
        raise AssertionError(
            f"freshness mismatch {admitted.freshness_age_seconds} "
            f"!= {a['expected_freshness_age_seconds']}"
        )
    if admitted.uncertainty_kind != "UNKNOWN":
        raise AssertionError("uncertainty must remain UNKNOWN")
    if admitted.output_status != "OBSERVED":
        raise AssertionError("source value must remain OBSERVED")

    chain = set(admitted.transform_chain)
    if "source_unit_adapter:kWh/h_GCV->kW_HHV:factor=1" not in chain:
        raise AssertionError("source unit adapter transform missing")
    if "unit:kW_HHV->W_th" not in chain:
        raise AssertionError("empirical contract unit transform missing")
    if "energy_basis:GCV" not in chain or "terminology:GCV->HHV" not in chain:
        raise AssertionError("energy basis transform chain incomplete")
    if any(x.startswith("interpolation:") for x in chain):
        raise AssertionError("silent interpolation appeared")
    if any(x.startswith("imputation:") for x in chain):
        raise AssertionError("silent imputation appeared")
    if "volume_to_energy_conversion:false" not in chain:
        raise AssertionError("volume conversion fence missing")
    if "calorific_value_assumption:false" not in chain:
        raise AssertionError("calorific-value assumption fence missing")

    receipt = {
        "schema_version": "EQUILIBRIUM_PRS_THIRD_REAL_SOURCE_GAS_CANARY_RECEIPT_V1",
        "gate_id": GATE_ID,
        "counts": m["counts"],
        "predecessor": m["predecessor"],
        "measurement_source": {
            "provider": source["provider"],
            "operator_label": source["operator_label"],
            "point_label": source["point_label"],
            "direction": source["direction"],
            "indicator": source["indicator"],
            "source_url": source["source_url"],
            "scrape_id": source["scrape_id"],
            "retrieved_at": source["retrieved_at"],
            "raw_file": source["raw_file"],
            "raw_byte_length": len(raw),
            "raw_sha256": source["raw_sha256"],
            "flow_status": rec["flow_status"],
        },
        "record": rec,
        "provenance_complete": True,
        "energy_basis_receipt": {
            "source_energy_unit": "kWh/h",
            "source_energy_basis": "GCV",
            "core_basis_label": "HHV",
            "gcv_to_hhv_terminology_evidence": True,
            "volume_to_energy_conversion_performed": False,
            "numeric_calorific_value_used": False,
            "support_authorities": [x["authority"] for x in basis["evidence"]],
        },
        "unit_transform_receipt": {
            "source_stage": {
                "from": "kWh/h_GCV",
                "to": "kW_HHV",
                "factor_n": 1,
                "factor_d": 1,
            },
            "contract_stage": {
                "from": "kW_HHV",
                "to": admitted.canonical_unit,
                "factor_n": 1000,
                "factor_d": 1,
            },
            "source_value": rec["value"],
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
            "period_from_utc": rec["period_from_utc"],
            "period_to_utc": rec["period_to_utc"],
            "interval_id": a["interval_id"],
            "method": a["temporal_method"],
            "method_ref": a["temporal_method_ref"],
            "interpolation_used": False,
            "imputation_used": False,
            "aggregation_performed": False,
        },
        "freshness_readback": {
            "observed_at": a["observed_at_for_freshness"],
            "as_of": a["as_of"],
            "age_seconds": admitted.freshness_age_seconds,
            "max_age_seconds": a["max_age_seconds"],
            "fresh_at_admission": admitted.freshness_age_seconds <= a["max_age_seconds"],
            "semantics": a["freshness_semantics"],
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
        "water_canary_preserved": True,
        "electricity_canary_preserved": True,
        "same_admission_contract": True,
        "no_silent_transform": True,
        "fences": m["fences"],
        "verdict": "PASS_BOUNDED_THIRD_REAL_SOURCE_NATURAL_GAS_ADMIT_OBSERVED_GCV_HHV",
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
    print("THIRD_REAL_SOURCE_GAS_CANARY_RECEIPT_SHA256=" + sha)
