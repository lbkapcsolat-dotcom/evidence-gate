from __future__ import annotations

import copy
import hashlib
import json
from enum import Enum
from typing import Any, Mapping


class Admission(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    REJECT = "REJECT"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _identity_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": payload["schema_version"],
        "source": payload["source"],
        "execution": payload["execution"],
        "provider_readback": payload["provider_readback"],
    }


def _source_readback_matches(payload: Mapping[str, Any]) -> bool:
    source = payload["source"]
    rb = payload["provider_readback"]
    return (
        rb.get("source_name") == source.get("name")
        and rb.get("source_version") == source.get("version")
        and rb.get("source_sha256") == source.get("sha256")
    )


def _admit(payload: Mapping[str, Any]) -> tuple[Admission, list[str]]:
    eq = payload["eq64"]
    reasons: list[str] = []

    if eq.get("negative_evidence"):
        return Admission.REJECT, ["NEGATIVE_EVIDENCE"]

    if not payload["provider_readback"].get("fresh"):
        reasons.append("PROVIDER_READBACK_NOT_FRESH")
    if not _source_readback_matches(payload):
        reasons.append("SOURCE_VERSION_SHA_READBACK_MISMATCH")
    if not eq.get("fresh_readback"):
        reasons.append("EQ64_FRESH_READBACK_MISSING")
    if not eq.get("semantic_contract"):
        reasons.append("SEMANTIC_CONTRACT_NOT_PROVEN")
    if not eq.get("baseline_bound"):
        reasons.append("BASELINE_BIND_MISSING")
    if not eq.get("admissible_execution"):
        reasons.append("EXECUTION_PROVENANCE_NOT_ADMISSIBLE")

    promoted = payload["claim_level"] > payload["previous_claim_level"]
    if promoted and not payload["new_admissible_evidence"]:
        reasons.append("NO_SILENT_PROMOTION")

    if reasons:
        return Admission.HOLD, reasons
    return Admission.PASS, ["ALL_V1_ADMISSION_GATES_SATISFIED"]


def build_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != "ESS_EVIDENCE_RUNTIME_V1":
        raise ValueError("unsupported schema_version")

    admission, reasons = _admit(payload)
    evidence_id = _sha256(_identity_payload(payload))

    receipt: dict[str, Any] = {
        "schema_version": "ESS_EVIDENCE_RUNTIME_V1",
        "evidence_id": evidence_id,
        "claim": payload["claim"],
        "source": copy.deepcopy(payload["source"]),
        "execution": copy.deepcopy(payload["execution"]),
        "provider_readback": copy.deepcopy(payload["provider_readback"]),
        "eq64": copy.deepcopy(payload["eq64"]),
        "claim_level": payload["claim_level"],
        "previous_claim_level": payload["previous_claim_level"],
        "new_admissible_evidence": payload["new_admissible_evidence"],
        "admission": admission.value,
        "reasons": reasons,
        "historical_pre_step8_identity": (
            "VERIFIED" if payload["eq64"].get("historical_identity") else "HOLD_UNRECOVERED"
        ),
        "production_effective": False,
        "runtime_admission": False,
        "canonical_bind": False,
        "production_promotion": False,
        "new_global_bind": False,
        "external_actuation": False,
        "zero_spend": True,
    }
    receipt["receipt_sha256"] = _sha256(receipt)
    return receipt


def replay_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    supplied = receipt.get("receipt_sha256")
    body = copy.deepcopy(dict(receipt))
    body.pop("receipt_sha256", None)
    recomputed = _sha256(body)

    identity = {
        "schema_version": body.get("schema_version"),
        "source": body.get("source"),
        "execution": body.get("execution"),
        "provider_readback": body.get("provider_readback"),
    }
    recomputed_evidence_id = _sha256(identity)
    valid = (
        isinstance(supplied, str)
        and supplied == recomputed
        and body.get("evidence_id") == recomputed_evidence_id
    )
    return {
        "valid": valid,
        "receipt_sha256": supplied,
        "recomputed_receipt_sha256": recomputed,
        "evidence_id": body.get("evidence_id"),
        "recomputed_evidence_id": recomputed_evidence_id,
    }
