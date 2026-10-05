from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from fractions import Fraction
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys
from typing import Any

import planetary_resource_empirical_admission_v1 as admission

GATE_ID = "CH11C__LIVE_READ_ONLY_SOURCE_REFRESH_CANARY_V1"
FETCH_MANIFEST = Path("CH11C__LIVE_FETCH_MANIFEST_V1.json")
OUT_PATH = Path("CH11C__LIVE_READ_ONLY_SOURCE_REFRESH_RECEIPT_V1.json")

CH11B_RECEIPT_SHA256 = "48868d28ec28eaa5f5dd2cda8236bcd142822af0b0ed2055e35ccabab339a62f"
CH11A_RECEIPT_SHA256 = "7ed4801d78c66f926ccaa68d8bc42d82246bfb67dc3879a7e09ea08f2bb5f9f4"
CH10_RECEIPT_SHA256 = "6e14308dbe21eacc0cda91497b564255834065875b46f0d475bdb2a5e45e4be3"

FROZEN_RAW_SHA = {
    "water": "c180db17bc02d371f1eebb4667695b715f0ce2f9c2f97bab6893b77f87c97c29",
    "electricity": "831ed964ef11527f0d8db767665289b59f5ef7b32fac02cd7667ad4b949a7242",
    "natural_gas": "a7f15400b518ec51ac0f6a97696bd7cd261e64730d1a348dc1a2ad0be0956928",
}

FROZEN_MANIFESTS = {
    "water": Path("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__FIRST_REAL_SOURCE_CANARY_MANIFEST.json"),
    "electricity": Path("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__SECOND_REAL_SOURCE_CANARY_MANIFEST.json"),
    "natural_gas": Path("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__THIRD_REAL_SOURCE_GAS_CANARY_MANIFEST.json"),
}


class Ch11cHold(ValueError):
    def __init__(self, source_id: str, code: str, detail: str = ""):
        self.source_id = source_id
        self.code = code
        self.detail = detail
        super().__init__(f"{source_id}:{code}:{detail}" if detail else f"{source_id}:{code}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_sha256(payload: Any) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    return sha256_bytes(body.encode("utf-8"))


def parse_utc(value: str) -> datetime:
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    dt = datetime.fromisoformat(v)
    if dt.tzinfo is None:
        raise ValueError("timezone missing")
    return dt.astimezone(timezone.utc)


def fraction_from_any(value: Any) -> Fraction:
    return Fraction(str(value))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_rows() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = load_json(FETCH_MANIFEST)
    if manifest.get("gate_id") != GATE_ID:
        raise Ch11cHold("manifest", "HOLD_FETCH_MANIFEST_GATE_MISMATCH")
    policy = manifest.get("network_policy", {})
    required_policy = {
        "read_only": True,
        "allowed_method": "GET",
        "request_body_bytes": 0,
        "credentials_used": False,
        "external_write": False,
        "external_actuation": False,
        "new_source_registration": False,
    }
    if policy != required_policy:
        raise Ch11cHold("manifest", "HOLD_NETWORK_POLICY_MISMATCH")
    rows = {row["source_id"]: row for row in manifest.get("rows", [])}
    if set(rows) != {"water", "electricity", "natural_gas"}:
        raise Ch11cHold("manifest", "HOLD_FETCH_SOURCE_SET_MISMATCH")
    for source_id, row in rows.items():
        if row.get("method") != "GET":
            raise Ch11cHold(source_id, "HOLD_NON_GET_METHOD")
        if row.get("request_body_bytes") != 0:
            raise Ch11cHold(source_id, "HOLD_REQUEST_BODY_PRESENT")
        if row.get("external_write") is not False:
            raise Ch11cHold(source_id, "HOLD_EXTERNAL_WRITE_FLAG")
        if row.get("http_status") != 200:
            raise Ch11cHold(source_id, "HOLD_LIVE_FETCH_FAILED", row.get("error", "no HTTP 200"))
        path = Path(row["local_capture"])
        if not path.is_file():
            raise Ch11cHold(source_id, "HOLD_CAPTURE_MISSING")
        raw = path.read_bytes()
        if len(raw) != row["byte_length"] or sha256_bytes(raw) != row["sha256"]:
            raise Ch11cHold(source_id, "HOLD_CAPTURE_HASH_MISMATCH")
    return manifest, rows


def build_water(row: dict[str, Any]) -> dict[str, Any]:
    source_id = "water"
    raw = Path(row["local_capture"]).read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise Ch11cHold(source_id, "HOLD_SCHEMA_DRIFT_JSON", str(exc))

    meta = payload.get("meta", {})
    if meta.get("publisher") != "Environment Agency":
        raise Ch11cHold(source_id, "HOLD_PROVIDER_IDENTITY_MISMATCH")
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise Ch11cHold(source_id, "HOLD_NO_LIVE_RECORD")

    fetched_at = parse_utc(row["fetched_at"])
    admissible = []
    for item in items:
        measure = item.get("measure", {})
        if not isinstance(measure, dict):
            continue
        try:
            observed = parse_utc(str(item["dateTime"]))
        except Exception:
            continue
        if observed > fetched_at:
            continue
        if (
            measure.get("stationReference") == "1100TH"
            and measure.get("parameter") == "flow"
            and int(measure.get("period")) == 900
            and measure.get("valueType") == "mean"
            and measure.get("unitName") == "m3/s"
        ):
            admissible.append((observed, item, measure))
    if not admissible:
        raise Ch11cHold(source_id, "HOLD_SCHEMA_OR_RECORD_IDENTITY_MISMATCH")
    observed, item, measure = max(admissible, key=lambda x: x[0])
    age = int((fetched_at - observed).total_seconds())

    frozen = load_json(FROZEN_MANIFESTS[source_id])
    a = frozen["admission"]
    if age > int(a["max_age_seconds"]):
        raise Ch11cHold(source_id, "HOLD_STALE_INPUT", f"age={age}")

    interval_id = f"EA_1100TH_LIVE_{observed.isoformat()}"
    candidate = admission.EmpiricalCandidate(
        variable_id="freshwater.internal_flow_rate",
        value=fraction_from_any(item["value"]),
        source_unit="m3/s",
        source_layer="FRESHWATER",
        source_quantity_kind="RATE",
        source_status=admission.SourceStatus.OBSERVED,
        provenance=admission.ProvenanceRecord(
            source_id="EA_FLOOD_MONITORING_LIVE_1100TH_FLOW_MEAN_15MIN",
            provider="Environment Agency",
            dataset_id="Flood Monitoring Real Time API",
            dataset_version=str(meta.get("version", "0.9")),
            record_locator=str(item.get("@id", "")),
            observed_at=observed.isoformat().replace("+00:00", "Z"),
            retrieved_at=row["fetched_at"],
            raw_sha256=row["sha256"],
            citation="Environment Agency Flood Monitoring Real Time API, station 1100TH Farmoor, live refresh",
            license_or_terms_ref=frozen["source"]["license_or_terms_ref"],
            access_class="PUBLIC",
        ),
        spatial_mapping=admission.SpatialMapping(
            method=admission.SpatialMethod(a["spatial_method"]),
            target_node_id=a["target_node_id"],
            target_node_class=a["target_node_class"],
            method_ref=a["spatial_method_ref"],
        ),
        temporal_alignment=admission.TemporalAlignment(
            method=admission.TemporalMethod.EXACT_INTERVAL,
            source_interval_id=interval_id,
            target_interval_id=interval_id,
            method_ref="EA_SOURCE_PERIOD_900S_VALUE_TYPE_MEAN_LIVE_V1",
        ),
        uncertainty=admission.UncertaintyDeclaration(
            kind=admission.UncertaintyKind.UNKNOWN,
            method_ref="",
        ),
        as_of=row["fetched_at"],
        max_age_seconds=int(a["max_age_seconds"]),
        missingness_reason="",
        source_gas_basis="",
        sign_semantics_declared=True,
        transform_chain=(
            "source:environment_agency_flood_monitoring_live",
            f"live_raw_sha256:{row['sha256']}",
            "unit:m3/s",
            "period_seconds:900",
            "value_type:mean",
        ),
    )
    admitted = admission.admit(candidate)
    return {
        "source_id": source_id,
        "provider": "Environment Agency",
        "role": "freshwater.internal_flow_rate",
        "live_raw_sha256": row["sha256"],
        "frozen_raw_sha256": FROZEN_RAW_SHA[source_id],
        "live_bytes_differ_from_frozen": row["sha256"] != FROZEN_RAW_SHA[source_id],
        "selected_record": {
            "record_locator": str(item.get("@id", "")),
            "observed_at": observed.isoformat().replace("+00:00", "Z"),
            "value": str(item["value"]),
            "unit": "m3/s",
            "period_seconds": 900,
            "value_type": "mean",
        },
        "freshness_age_seconds": age,
        "max_age_seconds": int(a["max_age_seconds"]),
        "schema_identity": True,
        "provider_identity": True,
        "semantic_identity": True,
        "admission_receipt": asdict(admitted),
    }


def build_electricity(row: dict[str, Any]) -> dict[str, Any]:
    source_id = "electricity"
    raw = Path(row["local_capture"]).read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise Ch11cHold(source_id, "HOLD_SCHEMA_DRIFT_JSON", str(exc))
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise Ch11cHold(source_id, "HOLD_NO_LIVE_RECORD")

    fetched_at = parse_utc(row["fetched_at"])
    admissible = []
    for item in data:
        if item.get("dataset") != "INDO":
            continue
        try:
            observed = parse_utc(str(item["startTime"]))
            publish = parse_utc(str(item["publishTime"]))
            demand = fraction_from_any(item["demand"])
        except Exception:
            continue
        if observed <= fetched_at and publish <= fetched_at:
            admissible.append((observed, publish, demand, item))
    if not admissible:
        raise Ch11cHold(source_id, "HOLD_SCHEMA_OR_RECORD_IDENTITY_MISMATCH")
    observed, publish, demand, item = max(admissible, key=lambda x: x[0])
    age = int((fetched_at - observed).total_seconds())

    frozen = load_json(FROZEN_MANIFESTS[source_id])
    a = frozen["admission"]
    if age > int(a["max_age_seconds"]):
        raise Ch11cHold(source_id, "HOLD_STALE_INPUT", f"age={age}")

    interval_id = f"ELEXON_INDO_LIVE_{observed.isoformat()}_SP{item.get('settlementPeriod')}"
    candidate = admission.EmpiricalCandidate(
        variable_id="electricity.consumption_rate",
        value=demand,
        source_unit="MW",
        source_layer="ELECTRICITY",
        source_quantity_kind="RATE",
        source_status=admission.SourceStatus.OBSERVED,
        provenance=admission.ProvenanceRecord(
            source_id="ELEXON_INDO_LIVE_REFRESH",
            provider="Elexon Insights Solution",
            dataset_id="INDO",
            dataset_version="ELEXON_INSIGHTS_API_V1",
            record_locator=row["final_url"] + f"#INDO/{item['startTime']}/SP{item.get('settlementPeriod')}",
            observed_at=observed.isoformat().replace("+00:00", "Z"),
            retrieved_at=row["fetched_at"],
            raw_sha256=row["sha256"],
            citation="Elexon Insights Solution, Initial National Demand outturn (INDO), live refresh",
            license_or_terms_ref=frozen["source"]["license_or_terms_ref"],
            access_class="PUBLIC",
        ),
        spatial_mapping=admission.SpatialMapping(
            method=admission.SpatialMethod(a["spatial_method"]),
            target_node_id=a["target_node_id"],
            target_node_class=a["target_node_class"],
            method_ref=a["spatial_method_ref"],
        ),
        temporal_alignment=admission.TemporalAlignment(
            method=admission.TemporalMethod.EXACT_INTERVAL,
            source_interval_id=interval_id,
            target_interval_id=interval_id,
            method_ref="ELEXON_INDO_SETTLEMENT_PERIOD_HALF_HOUR_AVERAGE_LIVE_V1",
        ),
        uncertainty=admission.UncertaintyDeclaration(
            kind=admission.UncertaintyKind.UNKNOWN,
            method_ref="",
        ),
        as_of=row["fetched_at"],
        max_age_seconds=int(a["max_age_seconds"]),
        missingness_reason="",
        source_gas_basis="",
        sign_semantics_declared=True,
        transform_chain=(
            "source:elexon_insights_indo_live",
            f"live_raw_sha256:{row['sha256']}",
            f"publish_time:{publish.isoformat()}",
            f"settlement_period:{item.get('settlementPeriod')}",
        ),
    )
    admitted = admission.admit(candidate)
    return {
        "source_id": source_id,
        "provider": "Elexon Insights Solution",
        "role": "electricity.consumption_rate",
        "live_raw_sha256": row["sha256"],
        "frozen_raw_sha256": FROZEN_RAW_SHA[source_id],
        "live_bytes_differ_from_frozen": row["sha256"] != FROZEN_RAW_SHA[source_id],
        "selected_record": {
            "dataset": item["dataset"],
            "publish_time": publish.isoformat().replace("+00:00", "Z"),
            "start_time": observed.isoformat().replace("+00:00", "Z"),
            "settlement_period": item.get("settlementPeriod"),
            "demand": str(item["demand"]),
            "unit": "MW",
        },
        "freshness_age_seconds": age,
        "max_age_seconds": int(a["max_age_seconds"]),
        "schema_identity": True,
        "provider_identity": True,
        "semantic_identity": True,
        "admission_receipt": asdict(admitted),
    }


def gas_csv_text(raw: bytes) -> str:
    text = raw.decode("utf-8")
    if "<body>" in text and "</body>" in text:
        return text.split("<body>", 1)[1].split("</body>", 1)[0]
    return text


def gas_utc_interval(row: dict[str, str]) -> tuple[datetime, datetime]:
    matches = re.findall(r"(20\d\d-\d\d-\d\d \d\d:\d\d:\d\d \+00:00)", row.get("id", ""))
    if len(matches) < 2:
        raise ValueError("UTC timestamps absent from ENTSOG id")
    start = datetime.strptime(matches[0], "%Y-%m-%d %H:%M:%S %z").astimezone(timezone.utc)
    end = datetime.strptime(matches[1], "%Y-%m-%d %H:%M:%S %z").astimezone(timezone.utc)
    return start, end


def build_gas(row: dict[str, Any]) -> dict[str, Any]:
    source_id = "natural_gas"
    raw = Path(row["local_capture"]).read_bytes()
    try:
        rows = list(csv.DictReader(io.StringIO(gas_csv_text(raw))))
    except Exception as exc:
        raise Ch11cHold(source_id, "HOLD_SCHEMA_DRIFT_CSV", str(exc))
    if not rows:
        raise Ch11cHold(source_id, "HOLD_NO_LIVE_RECORD")

    fetched_at = parse_utc(row["fetched_at"])
    admissible = []
    for item in rows:
        if (
            item.get("indicator") != "Physical Flow"
            or item.get("periodType") != "hour"
            or item.get("operatorKey") != "DE-TSO-0005"
            or item.get("pointKey") != "ITP-00188"
            or item.get("directionKey") != "entry"
            or item.get("unit") != "kWh/h"
        ):
            continue
        try:
            start, end = gas_utc_interval(item)
            value = fraction_from_any(item["value"])
        except Exception:
            continue
        if end <= fetched_at:
            admissible.append((end, start, value, item))
    if not admissible:
        raise Ch11cHold(source_id, "HOLD_SCHEMA_OR_RECORD_IDENTITY_MISMATCH")
    end, start, value, item = max(admissible, key=lambda x: x[0])
    age = int((fetched_at - end).total_seconds())

    frozen = load_json(FROZEN_MANIFESTS[source_id])
    a = frozen["admission"]
    if age > int(a["max_age_seconds"]):
        raise Ch11cHold(source_id, "HOLD_STALE_INPUT", f"age={age}")
    if not item.get("flowStatus"):
        raise Ch11cHold(source_id, "HOLD_FLOW_STATUS_MISSING")

    interval_id = f"ENTSOG_DE_TSO_0005_ITP_00188_ENTRY_LIVE_{start.isoformat()}_{end.isoformat()}"
    candidate = admission.EmpiricalCandidate(
        variable_id="natural_gas.import_rate",
        value=value,
        source_unit="kW_HHV",
        source_layer="NATURAL_GAS",
        source_quantity_kind="RATE",
        source_status=admission.SourceStatus.OBSERVED,
        provenance=admission.ProvenanceRecord(
            source_id="ENTSOG_GUD_DORNUM_NETRA_ENTRY_PHYSICAL_FLOW_LIVE",
            provider="ENTSOG Transparency Platform",
            dataset_id="ENTSOG_TRANSPARENCY_PLATFORM_OPERATIONALDATA_PHYSICAL_FLOW",
            dataset_version="TP_OPERATIONALDATA_V1",
            record_locator=row["final_url"] + "#" + item["id"],
            observed_at=end.isoformat().replace("+00:00", "Z"),
            retrieved_at=row["fetched_at"],
            raw_sha256=row["sha256"],
            citation="ENTSOG Transparency Platform, Physical Flow, Gasunie Deutschland, Dornum / NETRA (GUD), entry, live refresh",
            license_or_terms_ref="https://transparency.entsog.eu/",
            access_class="PUBLIC",
        ),
        spatial_mapping=admission.SpatialMapping(
            method=admission.SpatialMethod(a["spatial_method"]),
            target_node_id=a["target_node_id"],
            target_node_class=a["target_node_class"],
            method_ref=a["spatial_method_ref"],
        ),
        temporal_alignment=admission.TemporalAlignment(
            method=admission.TemporalMethod.EXACT_INTERVAL,
            source_interval_id=interval_id,
            target_interval_id=interval_id,
            method_ref="ENTSOG_PERIOD_FROM_TO_EXPLICIT_UTC_ID_LIVE_V1",
        ),
        uncertainty=admission.UncertaintyDeclaration(
            kind=admission.UncertaintyKind.UNKNOWN,
            method_ref="",
        ),
        as_of=row["fetched_at"],
        max_age_seconds=int(a["max_age_seconds"]),
        missingness_reason="",
        source_gas_basis="HHV",
        sign_semantics_declared=True,
        transform_chain=(
            "source:entsog_transparency_platform_physical_flow_live",
            f"live_raw_sha256:{row['sha256']}",
            "energy_basis:GCV",
            "terminology:GCV->HHV",
            "source_unit_adapter:kWh/h_GCV->kW_HHV:factor=1",
            "volume_to_energy_conversion:false",
            "calorific_value_assumption:false",
        ),
    )
    admitted = admission.admit(candidate)
    return {
        "source_id": source_id,
        "provider": "ENTSOG Transparency Platform",
        "role": "natural_gas.import_rate",
        "live_raw_sha256": row["sha256"],
        "frozen_raw_sha256": FROZEN_RAW_SHA[source_id],
        "live_bytes_differ_from_frozen": row["sha256"] != FROZEN_RAW_SHA[source_id],
        "selected_record": {
            "id": item["id"],
            "period_from_utc": start.isoformat().replace("+00:00", "Z"),
            "period_to_utc": end.isoformat().replace("+00:00", "Z"),
            "operator_key": item["operatorKey"],
            "operator_label": item.get("operatorLabel", "").strip(),
            "point_key": item["pointKey"],
            "point_label": item.get("pointLabel", ""),
            "direction": item["directionKey"],
            "indicator": item["indicator"],
            "unit": item["unit"],
            "value": item["value"],
            "flow_status": item["flowStatus"],
        },
        "freshness_age_seconds": age,
        "max_age_seconds": int(a["max_age_seconds"]),
        "schema_identity": True,
        "provider_identity": True,
        "semantic_identity": True,
        "energy_basis_continuity": "GCV->HHV_LABEL_ONLY_FACTOR_1",
        "admission_receipt": asdict(admitted),
    }


def pass_receipt(manifest: dict[str, Any], rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    results = [
        build_water(rows["water"]),
        build_electricity(rows["electricity"]),
        build_gas(rows["natural_gas"]),
    ]
    for result in results:
        if result["admission_receipt"]["decision"] != admission.AdmissionDecision.ADMIT_OBSERVED.value:
            raise Ch11cHold(result["source_id"], "HOLD_SOURCE_ADMISSION_NOT_OBSERVED")

    return {
        "schema_version": "CH11C_LIVE_READ_ONLY_SOURCE_REFRESH_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessors": {
            "ch10_receipt_sha256": CH10_RECEIPT_SHA256,
            "ch11a_receipt_sha256": CH11A_RECEIPT_SHA256,
            "ch11b_receipt_sha256": CH11B_RECEIPT_SHA256,
        },
        "fetch_manifest_sha256": sha256_file(FETCH_MANIFEST),
        "network_policy": manifest["network_policy"],
        "live_source_refresh": {
            "pass": 3,
            "count": 3,
            "rows": results,
        },
        "no_silent_transform": True,
        "external_state_written": False,
        "external_actuation": False,
        "continuous_ingestion_enabled": False,
        "claim_ceiling": {
            "live_read_only_source_refresh_3_of_3": True,
            "bounded_semantic_continuity": True,
            "continuous_ingestion": False,
            "live_network_runtime_admission": False,
            "runtime_admission": False,
            "production_readiness": False,
            "production_admission": False,
            "external_actuation": False,
            "network_write": False,
            "pointer_promotion": False,
            "global_bind": False,
            "certification": False,
            "deployment": False,
            "merge_authorization": False,
        },
        "verdict": "PASS_CH11C__LIVE_READ_ONLY_SOURCE_REFRESH_3_OF_3__ZERO_WRITE_ZERO_ACTUATION",
    }


def hold_receipt(manifest: dict[str, Any] | None, exc: Exception) -> dict[str, Any]:
    if isinstance(exc, Ch11cHold):
        source_id, code, detail = exc.source_id, exc.code, exc.detail
    else:
        source_id, code, detail = "internal", "HOLD_CH11C_VALIDATION_EXCEPTION", f"{type(exc).__name__}:{exc}"
    return {
        "schema_version": "CH11C_LIVE_READ_ONLY_SOURCE_REFRESH_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessors": {
            "ch10_receipt_sha256": CH10_RECEIPT_SHA256,
            "ch11a_receipt_sha256": CH11A_RECEIPT_SHA256,
            "ch11b_receipt_sha256": CH11B_RECEIPT_SHA256,
        },
        "fetch_manifest_sha256": sha256_file(FETCH_MANIFEST) if FETCH_MANIFEST.exists() else None,
        "network_policy": manifest.get("network_policy") if manifest else None,
        "hold": {"source_id": source_id, "code": code, "detail": detail},
        "external_state_written": False,
        "external_actuation": False,
        "claim_ceiling": {
            "live_read_only_source_refresh_3_of_3": False,
            "live_network_runtime_admission": False,
            "runtime_admission": False,
            "production_admission": False,
            "network_write": False,
            "pointer_promotion": False,
            "global_bind": False,
        },
        "verdict": f"HOLD_CH11C__{source_id.upper()}__{code}",
    }


def main() -> None:
    manifest = None
    try:
        manifest, rows = fetch_rows()
        receipt = pass_receipt(manifest, rows)
        exit_code = 0
    except Exception as exc:
        receipt = hold_receipt(manifest, exc)
        exit_code = 2

    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    OUT_PATH.write_text(canonical, encoding="utf-8")
    print(canonical, end="")
    print("CH11C_RECEIPT_SHA256=" + sha256_bytes(canonical.encode("utf-8")))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
