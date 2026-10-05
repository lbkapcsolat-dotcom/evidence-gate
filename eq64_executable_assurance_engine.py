from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Mapping

SCHEMA_VERSION = "EQ64_EXECUTABLE_ASSURANCE_ENGINE_V1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _valid_commit(value: Any) -> bool:
    return isinstance(value, str) and _COMMIT_RE.fullmatch(value) is not None


def _evidence_bundle(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": payload.get("schema_version"),
        "target": copy.deepcopy(payload.get("target")),
        "security": copy.deepcopy(payload.get("security")),
        "regression": copy.deepcopy(payload.get("regression")),
        "readback": copy.deepcopy(payload.get("readback")),
        "claim_guard": copy.deepcopy(payload.get("claim_guard")),
        "engine": copy.deepcopy(payload.get("engine")),
    }


def _evaluate_gates(payload: Mapping[str, Any]) -> tuple[list[int], list[str]]:
    target = payload["target"]
    security = payload["security"]
    regression = payload["regression"]
    readback = payload["readback"]
    claim_guard = payload["claim_guard"]
    reasons: list[str] = []

    target_id_exact = (
        isinstance(target.get("target_id"), str)
        and security.get("target_id") == target.get("target_id")
        and regression.get("target_id") == target.get("target_id")
    )
    if not target_id_exact:
        reasons.append("TARGET_IDENTITY_MISMATCH")

    target_runtime_sha = target.get("runtime_sha256")
    runtime_sha_exact = (
        _valid_sha256(target_runtime_sha)
        and security.get("target_runtime_sha256") == target_runtime_sha
        and regression.get("target_runtime_sha256") == target_runtime_sha
    )
    if not runtime_sha_exact:
        reasons.append("TARGET_RUNTIME_SHA256_MISMATCH")

    target_identity_exact = target_id_exact and runtime_sha_exact

    security_ok = True
    if security.get("status") != "PASS":
        security_ok = False
        reasons.append("SECURITY_BRANCH_NOT_PASS")
    if not security.get("fresh"):
        security_ok = False
        reasons.append("SECURITY_EVIDENCE_STALE")
    if not _valid_sha256(security.get("raw_artifact_sha256")):
        security_ok = False
        reasons.append("SECURITY_ARTIFACT_SHA256_INVALID")
    if not isinstance(security.get("tests_run"), int) or security["tests_run"] < 1:
        security_ok = False
        reasons.append("SECURITY_TEST_COUNT_BELOW_1")
    if (
        not isinstance(security.get("failure_injections"), int)
        or security["failure_injections"] < 3
    ):
        security_ok = False
        reasons.append("SECURITY_FAILURE_INJECTIONS_BELOW_3")

    regression_ok = True
    if regression.get("status") != "PASS":
        regression_ok = False
        reasons.append("REGRESSION_BRANCH_NOT_PASS")
    if not regression.get("fresh"):
        regression_ok = False
        reasons.append("REGRESSION_EVIDENCE_STALE")
    if not _valid_sha256(regression.get("raw_artifact_sha256")):
        regression_ok = False
        reasons.append("REGRESSION_ARTIFACT_SHA256_INVALID")
    if (
        not isinstance(regression.get("tests_run"), int)
        or regression["tests_run"] < 10
    ):
        regression_ok = False
        reasons.append("REGRESSION_TEST_COUNT_BELOW_10")
    if regression.get("same_input_replay_equal") is not True:
        regression_ok = False
        reasons.append("REPLAY_EQUALITY_NOT_PROVEN")

    readback_ok = True
    if readback.get("fresh") is not True:
        readback_ok = False
        reasons.append("READBACK_NOT_FRESH")
    if readback.get("security_artifact_sha256") != security.get("raw_artifact_sha256"):
        readback_ok = False
        reasons.append("READBACK_SECURITY_HASH_MISMATCH")
    if readback.get("regression_artifact_sha256") != regression.get("raw_artifact_sha256"):
        readback_ok = False
        reasons.append("READBACK_REGRESSION_HASH_MISMATCH")

    source_commit_security = security.get("source_commit")
    source_commit_regression = regression.get("source_commit")
    target_version = target.get("version")
    cross_branch_coherent = (
        _valid_commit(source_commit_security)
        and source_commit_security == source_commit_regression
        and source_commit_security == target_version
    )
    if not cross_branch_coherent:
        reasons.append("CROSS_BRANCH_SOURCE_COMMIT_MISMATCH")

    claim_guard_ok = True
    flags = claim_guard.get("overclaim_flags")
    if not isinstance(flags, list) or flags:
        claim_guard_ok = False
        reasons.append("OVERCLAIM_FLAG_PRESENT")
    if claim_guard.get("runtime_admission") is not False:
        claim_guard_ok = False
        reasons.append("RUNTIME_ADMISSION_MUST_REMAIN_FALSE")
    if claim_guard.get("production_readiness") is not False:
        claim_guard_ok = False
        reasons.append("PRODUCTION_READINESS_MUST_REMAIN_FALSE")

    bits = [
        int(target_identity_exact),
        int(security_ok),
        int(regression_ok),
        int(readback_ok),
        int(cross_branch_coherent),
        int(claim_guard_ok),
    ]
    return bits, reasons


def evaluate_assurance(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported schema_version")

    for key in ("target", "security", "regression", "readback", "claim_guard", "engine"):
        if not isinstance(payload.get(key), Mapping):
            raise ValueError(f"{key} must be an object")

    bits, reasons = _evaluate_gates(payload)
    state_index = sum((1 << i) for i, bit in enumerate(bits) if bit)
    decision = "PASS" if state_index == 63 else "HOLD"

    bundle = _evidence_bundle(payload)
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "decision": decision,
        "reasons": reasons if reasons else ["ALL_EQ64_ASSURANCE_GATES_SATISFIED"],
        "eq64": {
            "bit_order": [
                "target_identity_exact",
                "security_branch_pass",
                "regression_branch_pass",
                "artifact_readback_pass",
                "cross_branch_coherent",
                "claim_guard_pass",
            ],
            "bits": bits,
            "state_index": state_index,
            "pass_state": 63,
        },
        "target": copy.deepcopy(payload["target"]),
        "security": copy.deepcopy(payload["security"]),
        "regression": copy.deepcopy(payload["regression"]),
        "readback": copy.deepcopy(payload["readback"]),
        "claim_guard": copy.deepcopy(payload["claim_guard"]),
        "engine": copy.deepcopy(payload["engine"]),
        "evidence_bundle_sha256": sha256_json(bundle),
        "runtime_admission": False,
        "production_readiness": False,
        "global_bind": False,
        "pointer_promotion": False,
        "external_actuation": False,
    }
    receipt["receipt_sha256"] = sha256_json(receipt)
    return receipt


def replay_assurance_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    supplied = receipt.get("receipt_sha256")
    body = copy.deepcopy(dict(receipt))
    body.pop("receipt_sha256", None)
    recomputed_receipt_sha256 = sha256_json(body)

    bundle = {
        "schema_version": body.get("schema_version"),
        "target": body.get("target"),
        "security": body.get("security"),
        "regression": body.get("regression"),
        "readback": body.get("readback"),
        "claim_guard": body.get("claim_guard"),
        "engine": body.get("engine"),
    }
    recomputed_bundle_sha256 = sha256_json(bundle)
    supplied_bundle = body.get("evidence_bundle_sha256")
    valid = (
        body.get("schema_version") == SCHEMA_VERSION
        and isinstance(supplied, str)
        and supplied == recomputed_receipt_sha256
        and supplied_bundle == recomputed_bundle_sha256
    )
    return {
        "valid": valid,
        "receipt_sha256": supplied,
        "recomputed_receipt_sha256": recomputed_receipt_sha256,
        "evidence_bundle_sha256": supplied_bundle,
        "recomputed_evidence_bundle_sha256": recomputed_bundle_sha256,
    }
