from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Any

import planetary_resource_environment_agency_interval_semantics_external_authority_resolution_v1 as predecessor


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__ALTERNATE_FRESHWATER_EXPLICIT_INTERVAL_SOURCE_DISCOVERY_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__ALTERNATE_FRESHWATER_EXPLICIT_INTERVAL_SOURCE_DISCOVERY.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__ALTERNATE_FRESHWATER_EXPLICIT_INTERVAL_SOURCE_DISCOVERY_RECEIPT.json"
)

NS = {
    "gml": "http://www.opengis.net/gml/3.2",
    "om": "http://www.opengis.net/om/2.0",
    "wml2": "http://www.opengis.net/waterml/2.0",
    "xlink": "http://www.w3.org/1999/xlink",
}


def canonical_sha256(payload: dict[str, Any]) -> str:
    body = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def run_gate() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("gate id mismatch")
    if contract["target"] != "FRESHWATER_ONLY":
        raise AssertionError("target scope changed")
    if not contract["official_primary_sources_only"]:
        raise AssertionError("official-primary-only fence disabled")
    if any(contract["fences"].values()):
        raise AssertionError(f"forbidden scope enabled: {contract['fences']!r}")

    pred = predecessor.run_gate()
    pred_sha = canonical_sha256(pred)
    expected_pred = contract["predecessor"]["receipt_sha256"]
    if pred_sha != expected_pred:
        raise AssertionError(
            f"predecessor receipt changed: {pred_sha} != {expected_pred}"
        )
    if pred["source_family_status"] != "FINAL_HOLD":
        raise AssertionError("EA FINAL_HOLD predecessor changed")

    source = contract["selected_source"]
    raw_path = Path(source["raw_path"])
    raw = raw_path.read_bytes()
    raw_sha = hashlib.sha256(raw).hexdigest()
    if len(raw) != source["raw_bytes"]:
        raise AssertionError(f"raw byte length changed: {len(raw)}")
    if raw_sha != source["raw_sha256"]:
        raise AssertionError(f"raw SHA256 changed: {raw_sha}")

    root = ET.fromstring(raw)
    begin = root.findtext(".//gml:beginPosition", namespaces=NS)
    end = root.findtext(".//gml:endPosition", namespaces=NS)
    if not begin or not end:
        raise AssertionError("source-explicit interval bounds missing")
    duration_seconds = int((_dt(end) - _dt(begin)).total_seconds())
    if duration_seconds <= 0:
        raise AssertionError("interval duration is not positive")

    procedure = root.find(".//om:procedure", NS)
    observed = root.find(".//om:observedProperty", NS)
    feature = root.find(".//om:featureOfInterest", NS)
    uom = root.find(".//wml2:uom", NS)
    time_node = root.find(".//wml2:MeasurementTVP/wml2:time", NS)
    value_node = root.find(".//wml2:MeasurementTVP/wml2:value", NS)
    interpolation = root.find(".//wml2:interpolationType", NS)

    xlink_href = "{http://www.w3.org/1999/xlink}href"
    xlink_title = "{http://www.w3.org/1999/xlink}title"

    if observed is None or observed.attrib.get(xlink_title) != "Water Course Discharge":
        raise AssertionError("freshwater discharge property missing")
    if procedure is None or not procedure.attrib.get(xlink_href, "").endswith(
        "/Pat4_C_B_1_DailyMean"
    ):
        raise AssertionError("daily-mean discharge procedure changed")
    if feature is None or not feature.attrib.get(xlink_href, "").endswith("/410713"):
        raise AssertionError("station provenance changed")
    if uom is None or uom.attrib.get("code") != "cumec":
        raise AssertionError("discharge-rate unit changed")
    if time_node is None or time_node.text != begin:
        raise AssertionError("published value timestamp is not interval start")
    if value_node is None or value_node.text != source["value"]:
        raise AssertionError("published discharge value changed")

    requirements = contract["requirements"]
    if not all(requirements.values()):
        raise AssertionError("structural admission requirement disabled")

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_ALTERNATE_FRESHWATER_EXPLICIT_INTERVAL_SOURCE_DISCOVERY_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessor": {
            "receipt_sha256": pred_sha,
            "ea_source_family_status": pred["source_family_status"],
        },
        "selected_source": {
            "provider": source["provider"],
            "surface": source["surface"],
            "station_id": source["station_id"],
            "station_title": feature.attrib.get(xlink_title),
            "procedure_id": source["procedure_id"],
            "procedure_title": procedure.attrib.get(xlink_title),
            "observed_property": observed.attrib.get(xlink_title),
            "raw_path": source["raw_path"],
            "raw_bytes": len(raw),
            "raw_sha256": raw_sha,
            "unit_code": uom.attrib.get("code"),
            "unit_semantics": source["unit_semantics"],
            "published_value": value_node.text,
            "published_time": time_node.text,
            "interval_start": begin,
            "interval_end": end,
            "interval_duration_seconds": duration_seconds,
            "source_native_aggregation": source["source_native_aggregation"],
            "source_waterml_interpolation_metadata":
                interpolation.attrib.get(xlink_href) if interpolation is not None else None,
            "source_waterml_interpolation_title":
                interpolation.attrib.get(xlink_title) if interpolation is not None else None,
        },
        "structural_checks": {
            "flow_rate_or_equivalent_freshwater_rate": True,
            "explicit_interval_start": True,
            "explicit_interval_end": True,
            "positive_duration_interval": duration_seconds > 0,
            "source_provenance": True,
            "raw_bytes_preserved": True,
            "sha256_preserved": True,
            "boundary_inference_used": False,
            "interpolation_performed_by_equilibrium": False,
            "imputation_performed_by_equilibrium": False,
            "source_native_aggregation_preserved_without_recalculation": True,
        },
        "structurally_admissible_replacement_source_count": 1,
        "composition_performed": False,
        "core_patch_required": False,
        "new_domain_math_added": False,
        "fences": contract["fences"],
        "verdict": contract["verdict_target"],
        "claim_ceiling": (
            "Source discovery only. This does not prove three-source temporal "
            "alignment, empirical composition, runtime admission, or production use."
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
    print("ALTERNATE_FRESHWATER_SOURCE_DISCOVERY_RECEIPT_SHA256=" + sha)
