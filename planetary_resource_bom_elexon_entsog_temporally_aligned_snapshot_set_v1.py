from __future__ import annotations

from datetime import datetime, timedelta
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from typing import Any

import planetary_resource_alternate_freshwater_explicit_interval_source_discovery_v1 as predecessor
import planetary_resource_source_interval_semantics_recovery_v1 as semantics_recovery


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__BOM_ELEXON_ENTSOG_TEMPORALLY_ALIGNED_SNAPSHOT_SET_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__BOM_ELEXON_ENTSOG_TEMPORALLY_ALIGNED_SNAPSHOT_SET.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__BOM_ELEXON_ENTSOG_TEMPORALLY_ALIGNED_SNAPSHOT_SET_RECEIPT.json"
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


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def sha256_file(path: Path) -> tuple[int, str]:
    raw = path.read_bytes()
    return len(raw), hashlib.sha256(raw).hexdigest()


def run_gate() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("gate id mismatch")
    if any(contract["fences"].values()):
        raise AssertionError("forbidden scope enabled")
    if not all(contract["requirements"].values()):
        raise AssertionError("alignment requirement disabled")

    pred = predecessor.run_gate()
    pred_sha = canonical_sha256(pred)
    if pred_sha != contract["predecessor"]["receipt_sha256"]:
        raise AssertionError("predecessor receipt changed")

    recovery = semantics_recovery.run_gate()
    if not recovery["recovery"]["elexon_recovered"]:
        raise AssertionError("Elexon authoritative end-bound recovery regressed")
    if not recovery["recovery"]["entsog_already_satisfied"]:
        raise AssertionError("ENTSOG explicit-bound semantics regressed")

    # BOM freshwater
    bom_cfg = contract["sources"]["freshwater"]
    bom_path = Path(bom_cfg["raw_path"])
    bom_raw = bom_path.read_bytes()
    bom_root = ET.fromstring(bom_raw)
    bom_start = bom_root.findtext(".//gml:beginPosition", namespaces=NS)
    bom_end = bom_root.findtext(".//gml:endPosition", namespaces=NS)
    bom_value = bom_root.findtext(".//wml2:MeasurementTVP/wml2:value", namespaces=NS)
    if not bom_start or not bom_end or not bom_value:
        raise AssertionError("BOM explicit interval/value missing")

    # Elexon electricity
    elex_cfg = contract["sources"]["electricity"]
    elex_path = Path(elex_cfg["raw_path"])
    elex_raw = elex_path.read_bytes()
    elex_payload = json.loads(elex_raw.decode("utf-8"))
    matches = [
        row for row in elex_payload["data"]
        if row["startTime"] == elex_cfg["target_start_utc"]
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected one Elexon target row, got {len(matches)}")
    elex_row = matches[0]
    elex_start = dt(elex_row["startTime"])
    elex_end = elex_start + timedelta(
        seconds=int(elex_cfg["authoritative_duration_seconds"])
    )

    # ENTSOG natural gas
    gas_cfg = contract["sources"]["natural_gas"]
    gas_path = Path(gas_cfg["raw_path"])
    gas_raw = gas_path.read_bytes()
    gas_rows = list(csv.DictReader(io.StringIO(gas_raw.decode("utf-8"))))
    pattern = re.compile(
        r"Physical Flowhour"
        r"(?P<from>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \+00:00)"
        r"(?P<to>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \+00:00)"
    )
    target_gas = None
    gas_start = gas_end = None
    for row in gas_rows:
        m = pattern.search(row["id"])
        if not m:
            continue
        start = datetime.strptime(m.group("from"), "%Y-%m-%d %H:%M:%S %z")
        end = datetime.strptime(m.group("to"), "%Y-%m-%d %H:%M:%S %z")
        if (
            start == dt(gas_cfg["target_period_from_utc"])
            and end == dt(gas_cfg["target_period_to_utc"])
            and row["operatorKey"] == gas_cfg["operator_key"]
            and row["pointKey"] == gas_cfg["point_key"]
            and row["directionKey"] == gas_cfg["direction"]
        ):
            target_gas = row
            gas_start, gas_end = start, end
            break
    if target_gas is None or gas_start is None or gas_end is None:
        raise AssertionError("exact ENTSOG target row missing")

    intervals = {
        "freshwater": (dt(bom_start), dt(bom_end)),
        "electricity": (elex_start, elex_end),
        "natural_gas": (gas_start, gas_end),
    }
    common_start = max(v[0] for v in intervals.values())
    common_end = min(v[1] for v in intervals.values())
    common_seconds = int((common_end - common_start).total_seconds())
    if common_seconds <= 0:
        raise AssertionError("no positive-duration three-way intersection")
    if common_start != dt("2026-09-30T12:00:00Z"):
        raise AssertionError("unexpected common-window start")
    if common_end != dt("2026-09-30T12:30:00Z"):
        raise AssertionError("unexpected common-window end")

    bom_len, bom_sha = sha256_file(bom_path)
    elex_len, elex_sha = sha256_file(elex_path)
    gas_len, gas_sha = sha256_file(gas_path)

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_BOM_ELEXON_ENTSOG_TEMPORALLY_ALIGNED_SNAPSHOT_SET_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessor": {
            "receipt_sha256": pred_sha,
            "verdict": pred["verdict"],
        },
        "sources": {
            "freshwater": {
                "provider": bom_cfg["provider"],
                "raw_path": bom_cfg["raw_path"],
                "raw_bytes": bom_len,
                "raw_sha256": bom_sha,
                "interval_start": bom_start,
                "interval_end": bom_end,
                "published_value": bom_value,
                "uncertainty_kind": "UNKNOWN",
            },
            "electricity": {
                "provider": elex_cfg["provider"],
                "raw_path": elex_cfg["raw_path"],
                "raw_bytes": elex_len,
                "raw_sha256": elex_sha,
                "record": elex_row,
                "interval_start": elex_start.isoformat().replace("+00:00", "Z"),
                "interval_end": elex_end.isoformat().replace("+00:00", "Z"),
                "end_bound_basis": elex_cfg["authoritative_end_rule"],
                "uncertainty_kind": "UNKNOWN",
            },
            "natural_gas": {
                "provider": gas_cfg["provider"],
                "raw_path": gas_cfg["raw_path"],
                "raw_bytes": gas_len,
                "raw_sha256": gas_sha,
                "record_id": target_gas["id"],
                "value": target_gas["value"],
                "unit": target_gas["unit"],
                "flow_status": target_gas["flowStatus"],
                "interval_start": gas_start.isoformat().replace("+00:00", "Z"),
                "interval_end": gas_end.isoformat().replace("+00:00", "Z"),
                "uncertainty_kind": "UNKNOWN",
            },
        },
        "three_way_intersection": {
            "start_utc": common_start.isoformat().replace("+00:00", "Z"),
            "end_utc": common_end.isoformat().replace("+00:00", "Z"),
            "duration_seconds": common_seconds,
            "positive_duration": True,
        },
        "transforms": {
            "interpolation_performed": False,
            "imputation_performed": False,
            "cross_interval_aggregation_performed": False,
            "boundary_inference_used": False,
            "exact_record_selection_only": True,
        },
        "raw_bytes_preserved": True,
        "sha256_preserved": True,
        "source_provenance_preserved": True,
        "unknown_uncertainty_preserved": True,
        "composition_performed": False,
        "core_patch_required": False,
        "new_domain_math_added": False,
        "fences": contract["fences"],
        "verdict": contract["verdict_target"],
        "claim_ceiling": (
            "Temporal alignment only. No cross-source value composition, "
            "resampling, scoring, runtime admission, or production claim."
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
    print("BOM_ELEXON_ENTSOG_ALIGNMENT_RECEIPT_SHA256=" + sha)
