from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import planetary_resource_integration_readiness_freeze_v1 as integration_freeze
import run_ch11a_empirical_semantic_calibration_v1 as ch11a

GATE_ID = "CH11B__REAL_SUT_ADMISSION_AUTHORITY_GATE_V1"
OUT_PATH = Path("CH11B__REAL_SUT_ADMISSION_AUTHORITY_RECEIPT_V1.json")

SUT_BRANCH = "feature/planetary-resource-integration-readiness-freeze-v1"
SUT_HEAD = "4854040726bf24163f6ec70521d1ee7b4ac47f7d"
SUT_FREEZE_RECEIPT_SHA256 = "619e34873fc12d88cb102d727a28256c0fd17f7fc4a4007413ec5c45522a7d70"
CH10_RECEIPT_SHA256 = "6e14308dbe21eacc0cda91497b564255834065875b46f0d475bdb2a5e45e4be3"
CH11A_RECEIPT_SHA256 = "7ed4801d78c66f926ccaa68d8bc42d82246bfb67dc3879a7e09ea08f2bb5f9f4"

ALLOWED_ACTIONS = {
    "READ_FROZEN_FIXTURE",
    "REPLAY_SOURCE_ADMISSION",
    "EVALUATE_SEMANTIC_CONTRACT",
    "EMIT_LOCAL_RECEIPT",
}
FORBIDDEN_CLAIMS = {
    "runtime_admission",
    "production_admission",
    "production_readiness",
    "pointer_promotion",
    "global_bind",
    "certification",
    "deployment",
    "merge_authorization",
    "external_actuation",
    "network_write",
    "new_source_ingest",
}
ALLOWLIST = {
    "water": {
        "provider": "Environment Agency",
        "role": "freshwater.internal_flow_rate",
        "raw_sha256": "c180db17bc02d371f1eebb4667695b715f0ce2f9c2f97bab6893b77f87c97c29",
    },
    "electricity": {
        "provider": "Elexon Insights Solution",
        "role": "electricity.consumption_rate",
        "raw_sha256": "831ed964ef11527f0d8db767665289b59f5ef7b32fac02cd7667ad4b949a7242",
    },
    "natural_gas": {
        "provider": "ENTSOG Transparency Platform",
        "role": "natural_gas.import_rate",
        "raw_sha256": "a7f15400b518ec51ac0f6a97696bd7cd261e64730d1a348dc1a2ad0be0956928",
    },
}


class AuthorityHold(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def canonical_sha256(payload: Any) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def verify_predecessors() -> dict[str, str]:
    freeze = integration_freeze.run_freeze()
    freeze_sha = canonical_sha256(freeze)
    if freeze_sha != SUT_FREEZE_RECEIPT_SHA256:
        raise AssertionError(f"SUT freeze mismatch: {freeze_sha}")

    calibration = ch11a.run_calibration()
    calibration_sha = canonical_sha256(calibration)
    if calibration_sha != CH11A_RECEIPT_SHA256:
        raise AssertionError(f"CH11A receipt mismatch: {calibration_sha}")

    if calibration["calibration"]["pass"] != 36:
        raise AssertionError("CH11A calibration no longer 36/36")
    if calibration["calibration"]["false_pass_count"] != 0:
        raise AssertionError("CH11A calibration false PASS present")

    return {
        "sut_freeze_receipt_sha256": freeze_sha,
        "ch10_receipt_sha256": CH10_RECEIPT_SHA256,
        "ch11a_receipt_sha256": calibration_sha,
    }


def decide(
    *,
    provider: str,
    role: str,
    raw_sha256: str,
    requested_actions: set[str],
    requested_claims: dict[str, bool],
    calibration_present: bool = True,
) -> str:
    if not calibration_present:
        raise AuthorityHold("HOLD_CALIBRATION_REQUIRED")

    matches = [
        row for row in ALLOWLIST.values()
        if row["provider"] == provider and row["role"] == role
    ]
    if not provider or not role:
        raise AuthorityHold("HOLD_AUTHORITY_PROOF_MISSING")
    if len(matches) != 1:
        raise AuthorityHold("HOLD_AUTHORITY_NOT_ALLOWLISTED")
    allowed = matches[0]
    if raw_sha256 != allowed["raw_sha256"]:
        raise AuthorityHold("HOLD_RAW_SOURCE_NOT_PINNED")

    if not requested_actions.issubset(ALLOWED_ACTIONS):
        raise AuthorityHold("HOLD_OPERATION_NOT_ALLOWED")

    for key in FORBIDDEN_CLAIMS:
        if requested_claims.get(key, False):
            raise AuthorityHold("HOLD_CLAIM_CEILING_EXCEEDED")

    return "ADMIT_READ_ONLY_BOUNDED_REAL_SUT_CANARY"


def positive_rows() -> list[dict[str, Any]]:
    rows = []
    claims = {key: False for key in FORBIDDEN_CLAIMS}
    for name, item in ALLOWLIST.items():
        verdict = decide(
            provider=item["provider"],
            role=item["role"],
            raw_sha256=item["raw_sha256"],
            requested_actions=set(ALLOWED_ACTIONS),
            requested_claims=claims,
        )
        if verdict != "ADMIT_READ_ONLY_BOUNDED_REAL_SUT_CANARY":
            raise AssertionError(f"{name} not admitted")
        rows.append({"id": name, "verdict": verdict, **item})
    return rows


def expect_hold(case_id: str, expected: str, fn) -> dict[str, str]:
    try:
        fn()
    except AuthorityHold as exc:
        if exc.code != expected:
            raise AssertionError(f"{case_id}: expected {expected}, got {exc.code}")
        return {"id": case_id, "expected": expected, "observed": exc.code, "passed": "true"}
    raise AssertionError(f"{case_id}: expected HOLD but got admission")


def negative_rows() -> list[dict[str, str]]:
    base = ALLOWLIST["water"]
    no_claims = {key: False for key in FORBIDDEN_CLAIMS}
    return [
        expect_hold(
            "N01_WRONG_PROVIDER",
            "HOLD_AUTHORITY_NOT_ALLOWLISTED",
            lambda: decide(
                provider="UNVERIFIED_MIRROR",
                role=base["role"],
                raw_sha256=base["raw_sha256"],
                requested_actions=set(ALLOWED_ACTIONS),
                requested_claims=no_claims,
            ),
        ),
        expect_hold(
            "N02_RAW_SHA_MISMATCH",
            "HOLD_RAW_SOURCE_NOT_PINNED",
            lambda: decide(
                provider=base["provider"],
                role=base["role"],
                raw_sha256="0" * 64,
                requested_actions=set(ALLOWED_ACTIONS),
                requested_claims=no_claims,
            ),
        ),
        expect_hold(
            "N03_WRITE_OPERATION",
            "HOLD_OPERATION_NOT_ALLOWED",
            lambda: decide(
                provider=base["provider"],
                role=base["role"],
                raw_sha256=base["raw_sha256"],
                requested_actions=set(ALLOWED_ACTIONS) | {"WRITE_EXTERNAL_STATE"},
                requested_claims=no_claims,
            ),
        ),
        expect_hold(
            "N04_PRODUCTION_PROMOTION",
            "HOLD_CLAIM_CEILING_EXCEEDED",
            lambda: decide(
                provider=base["provider"],
                role=base["role"],
                raw_sha256=base["raw_sha256"],
                requested_actions=set(ALLOWED_ACTIONS),
                requested_claims={**no_claims, "production_admission": True},
            ),
        ),
        expect_hold(
            "N05_CALIBRATION_MISSING",
            "HOLD_CALIBRATION_REQUIRED",
            lambda: decide(
                provider=base["provider"],
                role=base["role"],
                raw_sha256=base["raw_sha256"],
                requested_actions=set(ALLOWED_ACTIONS),
                requested_claims=no_claims,
                calibration_present=False,
            ),
        ),
        expect_hold(
            "N06_UNKNOWN_ROLE",
            "HOLD_AUTHORITY_NOT_ALLOWLISTED",
            lambda: decide(
                provider=base["provider"],
                role="freshwater.aggregate_global_state",
                raw_sha256=base["raw_sha256"],
                requested_actions=set(ALLOWED_ACTIONS),
                requested_claims=no_claims,
            ),
        ),
    ]


def run_gate() -> dict[str, Any]:
    predecessors = verify_predecessors()
    positives = positive_rows()
    negatives = negative_rows()

    if len(positives) != 3 or any(x["verdict"] != "ADMIT_READ_ONLY_BOUNDED_REAL_SUT_CANARY" for x in positives):
        raise AssertionError("positive SUT admission matrix failed")
    if len(negatives) != 6 or any(x["passed"] != "true" for x in negatives):
        raise AssertionError("negative authority matrix failed")

    return {
        "schema_version": "CH11B_REAL_SUT_ADMISSION_AUTHORITY_RECEIPT_V1",
        "gate_id": GATE_ID,
        "candidate_sut": {
            "branch": SUT_BRANCH,
            "head": SUT_HEAD,
            "freeze_receipt_sha256": SUT_FREEZE_RECEIPT_SHA256,
            "mode": "FROZEN_REAL_SOURCE_READ_ONLY_REPLAY",
        },
        "predecessors": predecessors,
        "allowed_actions": sorted(ALLOWED_ACTIONS),
        "deny_by_default": True,
        "source_allowlist": ALLOWLIST,
        "positive_admission": {
            "pass": 3,
            "count": 3,
            "rows": positives,
        },
        "negative_authority_controls": {
            "pass": 6,
            "count": 6,
            "rows": negatives,
        },
        "rollback_boundary": {
            "external_state_written": False,
            "network_write": False,
            "new_source_ingest": False,
            "merge": False,
            "rollback_needed": False,
            "reason": "read-only frozen-fixture replay only",
        },
        "claim_ceiling": {
            "read_only_bounded_real_sut_canary": True,
            "live_network_runtime_admission": False,
            "production_readiness": False,
            "runtime_admission": False,
            "production_admission": False,
            "pointer_promotion": False,
            "global_bind": False,
            "certification": False,
            "deployment": False,
            "merge_authorization": False,
        },
        "verdict": "ADMIT_READ_ONLY_BOUNDED_REAL_SUT_CANARY",
    }


def write_receipt() -> tuple[dict[str, Any], str]:
    receipt = run_gate()
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    OUT_PATH.write_text(canonical, encoding="utf-8")
    return receipt, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    receipt, sha = write_receipt()
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    print("CH11B_RECEIPT_SHA256=" + sha)
