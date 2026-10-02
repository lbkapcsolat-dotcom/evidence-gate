from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import planetary_resource_environment_agency_explicit_interval_source_surface_recovery_v1 as predecessor


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__ENVIRONMENT_AGENCY_INTERVAL_SEMANTICS_EXTERNAL_AUTHORITY_RESOLUTION_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__ENVIRONMENT_AGENCY_INTERVAL_SEMANTICS_EXTERNAL_AUTHORITY_RESOLUTION.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__ENVIRONMENT_AGENCY_INTERVAL_SEMANTICS_EXTERNAL_AUTHORITY_RESOLUTION_RECEIPT.json"
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
    if any(contract["fences"].values()):
        raise AssertionError(f"forbidden scope enabled: {contract['fences']!r}")
    if set(contract["accepted_authority_classes"]) != {
        "OFFICIAL_EA_PRIMARY_DOCUMENT",
        "OFFICIAL_EA_SCHEMA",
        "OFFICIAL_EA_WRITTEN_CLARIFICATION",
    }:
        raise AssertionError("authority class fence changed")
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

    authority_rows = contract["authority_audit"]
    if not authority_rows:
        raise AssertionError("authority audit is empty")
    if any(row["accepted_boundary_rule"] for row in authority_rows):
        raise AssertionError(
            "An authoritative EA interval-boundary rule is now recorded; "
            "replace FINAL_HOLD with an explicit recovery successor."
        )

    written = contract["written_clarification"]
    if written["official_ea_written_clarification_present_in_audited_evidence"]:
        raise AssertionError(
            "Official EA written clarification is now present; adjudicate it "
            "before retaining FINAL_HOLD."
        )

    resolved = contract["question"]["resolved_answer"]
    if resolved != "NO_AUTHORITATIVE_CLASSIFICATION_FOUND":
        raise AssertionError("authority-resolution answer changed")

    requirements = contract["requirements"]
    if not all(requirements.values()):
        raise AssertionError("strict authority-resolution requirement disabled")

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_ENVIRONMENT_AGENCY_INTERVAL_SEMANTICS_EXTERNAL_AUTHORITY_RESOLUTION_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessor": {
            "receipt_sha256": pred_sha,
            "verdict": pred["verdict"],
        },
        "accepted_authority_classes": contract["accepted_authority_classes"],
        "authority_audit": authority_rows,
        "official_ea_written_clarification_present": False,
        "question": contract["question"],
        "authoritative_boundary_rule_obtained": False,
        "period_start_proven": False,
        "period_end_proven": False,
        "period_center_proven": False,
        "other_explicit_boundary_proven": False,
        "frozen_external_semantics": contract["frozen_external_semantics"],
        "new_source_ingest_performed": False,
        "new_source_records_ingested": 0,
        "assumption_used": False,
        "empirical_inference_used": False,
        "composition_performed": False,
        "core_patch_required": False,
        "new_domain_math_added": False,
        "source_family_status": "FINAL_HOLD",
        "source_family_reentry_condition": (
            "Only new official Environment Agency primary documentation, "
            "official schema semantics, or written EA clarification that "
            "explicitly classifies the flow-mean dateTime boundary may reopen "
            "this source family."
        ),
        "fences": contract["fences"],
        "verdict": contract["verdict_target"],
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
    print("EA_EXTERNAL_AUTHORITY_RESOLUTION_RECEIPT_SHA256=" + sha)
