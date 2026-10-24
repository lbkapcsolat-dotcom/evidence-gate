from __future__ import annotations

from fractions import Fraction

from planetary_resource_generic_source_adapter_v1 import (
    GenericAdapterSpec,
    GenericSourceRecord,
    PreContractTransform,
)

import planetary_resource_first_real_source_canary_v1 as water
import planetary_resource_second_real_source_canary_v1 as electricity
import planetary_resource_third_real_source_gas_canary_v1 as gas


def water_binding() -> tuple[GenericAdapterSpec, GenericSourceRecord]:
    m = water.load_manifest()
    _, payload = water.parse_and_verify_raw(m)
    source = m["source"]
    rec = m["record"]
    a = m["admission"]
    item = payload["items"][0]

    spec = GenericAdapterSpec(
        source_id=source["source_id"],
        provider=source["provider"],
        dataset_id=source["dataset_id"],
        dataset_version=source["dataset_version"],
        retrieved_at=source["retrieved_at"],
        raw_file=source["raw_file"],
        raw_sha256=source["raw_sha256"],
        citation=source["citation"],
        license_or_terms_ref=source["license_or_terms_ref"],
        access_class=source["access_class"],
        variable_id=a["variable_id"],
        source_layer=a["source_layer"],
        source_quantity_kind=a["source_quantity_kind"],
        source_status=a["source_status"],
        target_node_id=a["target_node_id"],
        target_node_class=a["target_node_class"],
        spatial_method=a["spatial_method"],
        spatial_method_ref=a["spatial_method_ref"],
        interval_id=a["interval_id"],
        temporal_method=a["temporal_method"],
        temporal_method_ref=a["temporal_method_ref"],
        as_of=a["as_of"],
        max_age_seconds=int(a["max_age_seconds"]),
        uncertainty_kind=a["uncertainty"]["kind"],
        uncertainty_method_ref=a["uncertainty"]["method_ref"],
        missingness_reason=a["missingness"]["reason"],
        source_gas_basis=a["source_gas_basis"],
        sign_semantics_declared=bool(a["sign_semantics_declared"]),
        base_transform_chain=(
            "source:environment_agency_flood_monitoring_api_v0.9",
            f"raw_sha256:{source['raw_sha256']}",
            f"record:{rec['record_locator']}",
        ),
    )
    record = GenericSourceRecord(
        value=Fraction(str(item["value"])),
        source_unit=rec["source_unit"],
        record_locator=rec["record_locator"],
        observed_at=rec["observed_at"],
    )
    return spec, record


def electricity_binding() -> tuple[GenericAdapterSpec, GenericSourceRecord]:
    m = electricity.load_manifest()
    _, payload = electricity.parse_and_verify_raw(m)
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

    spec = GenericAdapterSpec(
        source_id=source["source_id"],
        provider=source["provider"],
        dataset_id=source["dataset_id"],
        dataset_version=source["dataset_version"],
        retrieved_at=source["retrieved_at"],
        raw_file=source["raw_file"],
        raw_sha256=source["raw_sha256"],
        citation=source["citation"],
        license_or_terms_ref=source["license_or_terms_ref"],
        access_class=source["access_class"],
        variable_id=a["variable_id"],
        source_layer=a["source_layer"],
        source_quantity_kind=a["source_quantity_kind"],
        source_status=a["source_status"],
        target_node_id=a["target_node_id"],
        target_node_class=a["target_node_class"],
        spatial_method=a["spatial_method"],
        spatial_method_ref=a["spatial_method_ref"],
        interval_id=a["interval_id"],
        temporal_method=a["temporal_method"],
        temporal_method_ref=a["temporal_method_ref"],
        as_of=a["as_of"],
        max_age_seconds=int(a["max_age_seconds"]),
        uncertainty_kind=a["uncertainty"]["kind"],
        uncertainty_method_ref=a["uncertainty"]["method_ref"],
        missingness_reason=a["missingness"]["reason"],
        source_gas_basis="",
        sign_semantics_declared=bool(a["sign_semantics_declared"]),
        base_transform_chain=(
            "source:elexon_insights_indo_api_v1",
            f"raw_sha256:{source['raw_sha256']}",
            f"publish_time:{rec['publish_time']}",
            f"settlement_period:{rec['settlement_period']}",
        ),
    )
    record = GenericSourceRecord(
        value=Fraction(str(item["demand"])),
        source_unit=rec["source_unit"],
        record_locator=record_locator,
        observed_at=rec["start_time"],
    )
    return spec, record


def gas_binding() -> tuple[GenericAdapterSpec, GenericSourceRecord]:
    m = gas.load_manifest()
    gas.verify_energy_basis_evidence(m)
    _, row = gas.parse_and_verify_raw(m)
    source = m["measurement_source"]
    rec = m["record"]
    a = m["admission"]

    spec = GenericAdapterSpec(
        source_id=source["source_id"],
        provider=source["provider"],
        dataset_id="ENTSOG_TRANSPARENCY_PLATFORM_OPERATIONALDATA_PHYSICAL_FLOW",
        dataset_version="TP_OPERATIONALDATA_V1",
        retrieved_at=source["retrieved_at"],
        raw_file=source["raw_file"],
        raw_sha256=source["raw_sha256"],
        citation=source["citation"],
        license_or_terms_ref="https://transparency.entsog.eu/",
        access_class=source["access_class"],
        variable_id=a["variable_id"],
        source_layer=a["source_layer"],
        source_quantity_kind=a["source_quantity_kind"],
        source_status=a["source_status"],
        target_node_id=a["target_node_id"],
        target_node_class=a["target_node_class"],
        spatial_method=a["spatial_method"],
        spatial_method_ref=a["spatial_method_ref"],
        interval_id=a["interval_id"],
        temporal_method=a["temporal_method"],
        temporal_method_ref=a["temporal_method_ref"],
        as_of=a["as_of"],
        max_age_seconds=int(a["max_age_seconds"]),
        uncertainty_kind=a["uncertainty"]["kind"],
        uncertainty_method_ref=a["uncertainty"]["method_ref"],
        missingness_reason=a["missingness"]["reason"],
        source_gas_basis="",
        sign_semantics_declared=bool(a["sign_semantics_declared"]),
        base_transform_chain=(
            "source:entsog_transparency_platform_physical_flow",
            f"raw_sha256:{source['raw_sha256']}",
            "energy_basis:GCV",
            "terminology:GCV->HHV",
        ),
        pre_contract_transform=PreContractTransform(
            enabled=True,
            from_unit="kWh/h",
            to_unit="kW_HHV",
            factor_n=1,
            factor_d=1,
            to_gas_basis="HHV",
            evidence_ref=(
                "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
                "__GAS_ENERGY_BASIS_EVIDENCE.json"
            ),
            chain_tokens=(
                "source_unit_adapter:kWh/h_GCV->kW_HHV:factor=1",
                "volume_to_energy_conversion:false",
                "calorific_value_assumption:false",
            ),
        ),
    )
    record = GenericSourceRecord(
        value=Fraction(row["value"]),
        source_unit=rec["unit"],
        record_locator=source["source_url"] + "#" + rec["id"],
        observed_at=a["observed_at_for_freshness"],
    )
    return spec, record
