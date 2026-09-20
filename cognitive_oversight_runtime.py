from __future__ import annotations

import copy
import hashlib
import json
from enum import IntEnum
from typing import Any, Mapping

SCHEMA_VERSION = "ESS_COGNITIVE_OVERSIGHT_RUNTIME_V1"
POLICY_VERSION = "COGNITIVE_OVERSIGHT_STATE_CONTRACT_V1"


class DecisionRank(IntEnum):
    HOLD = 0
    HUMAN_FIRST = 1
    DUAL_CHECK = 2
    SCAFFOLD = 3
    ASSIST = 4
    AUTO = 5


INTERACTION_MODES = (
    "AUTO",
    "SUBSTITUTE",
    "ASSIST",
    "SCAFFOLD",
    "HUMAN_FIRST",
    "DUAL_CHECK",
)

OUTPUT_BY_RANK = {r.value: r.name for r in DecisionRank}
VALID_RANGES = {
    "task_complexity": {0, 1, 2},
    "delegation_depth": {0, 1, 2},
    "retained_practice": {0, 1},
    "verification_capacity": {0, 1, 2},
    "evidence_confidence": {0, 1, 2},
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _validate_state(state: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "task_complexity",
        "delegation_depth",
        "retained_practice",
        "verification_capacity",
        "interaction_mode",
        "evidence_confidence",
    }
    missing = sorted(required - set(state))
    extra = sorted(set(state) - required)
    if missing:
        raise ValueError(f"missing fields: {','.join(missing)}")
    if extra:
        raise ValueError(f"unexpected fields: {','.join(extra)}")
    out = dict(state)
    for field, allowed in VALID_RANGES.items():
        value = out[field]
        if type(value) is not int or value not in allowed:
            raise ValueError(f"{field} must be one of {sorted(allowed)}")
    if out["interaction_mode"] not in INTERACTION_MODES:
        raise ValueError("interaction_mode must be one of " + ",".join(INTERACTION_MODES))
    return out


def evaluate_state(state: Mapping[str, Any]) -> dict[str, Any]:
    s = _validate_state(state)
    rank = DecisionRank.AUTO.value
    gates: list[str] = []

    def cap(value: int, reason: str) -> None:
        nonlocal rank
        new_rank = min(rank, value)
        if new_rank != rank:
            gates.append(reason)
        rank = new_rank

    if s["evidence_confidence"] == 0:
        cap(DecisionRank.HOLD.value, "LOW_OR_UNKNOWN_EVIDENCE")
    if s["task_complexity"] == 2 and s["verification_capacity"] == 0:
        cap(DecisionRank.HOLD.value, "HIGH_COMPLEXITY_WITHOUT_INDEPENDENT_VERIFICATION")
    if s["task_complexity"] == 2:
        cap(DecisionRank.SCAFFOLD.value, "HIGH_TASK_COMPLEXITY")
    if s["delegation_depth"] == 2:
        cap(DecisionRank.DUAL_CHECK.value, "FULL_SUBSTITUTION")
    if s["retained_practice"] == 0:
        cap(DecisionRank.DUAL_CHECK.value, "RETAINED_PRACTICE_NOT_PRESERVED_OR_UNKNOWN")
    if s["verification_capacity"] == 0:
        cap(DecisionRank.HUMAN_FIRST.value, "VERIFICATION_UNAVAILABLE")
    elif s["verification_capacity"] == 1:
        cap(DecisionRank.SCAFFOLD.value, "VERIFICATION_PARTIAL")

    mode_caps = {
        "SUBSTITUTE": (DecisionRank.DUAL_CHECK.value, "INTERACTION_SUBSTITUTE"),
        "ASSIST": (DecisionRank.ASSIST.value, "INTERACTION_ASSIST"),
        "SCAFFOLD": (DecisionRank.SCAFFOLD.value, "INTERACTION_SCAFFOLD"),
        "HUMAN_FIRST": (DecisionRank.HUMAN_FIRST.value, "INTERACTION_HUMAN_FIRST"),
        "DUAL_CHECK": (DecisionRank.DUAL_CHECK.value, "INTERACTION_DUAL_CHECK"),
    }
    if s["interaction_mode"] in mode_caps:
        limit, reason = mode_caps[s["interaction_mode"]]
        cap(limit, reason)

    return {
        "decision": OUTPUT_BY_RANK[rank],
        "decision_rank": rank,
        "gates": gates or ["NO_ADDITIONAL_CAP"],
        "state": s,
    }


def build_receipt(state: Mapping[str, Any]) -> dict[str, Any]:
    result = evaluate_state(state)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "state": copy.deepcopy(result["state"]),
        "decision": result["decision"],
        "decision_rank": result["decision_rank"],
        "gates": list(result["gates"]),
        "claim_ceiling": "DETERMINISTIC_INTERACTION_POLICY_ENGINE__NOT_PSYCHOMETRIC_MEASUREMENT__NOT_HEALTH_INFERENCE",
        "authority_bind": False,
        "runtime_admission": False,
        "production_promotion": False,
        "external_actuation": False,
        "zero_spend": True,
    }
    receipt["state_sha256"] = _sha256(receipt["state"])
    receipt["receipt_sha256"] = _sha256(receipt)
    return receipt


def replay_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    supplied = receipt.get("receipt_sha256")
    body = copy.deepcopy(dict(receipt))
    body.pop("receipt_sha256", None)
    recomputed = _sha256(body)
    try:
        expected = build_receipt(body["state"])
    except (KeyError, TypeError, ValueError):
        expected = None
    valid = isinstance(supplied, str) and supplied == recomputed and expected is not None and expected == receipt
    return {
        "valid": valid,
        "receipt_sha256": supplied,
        "recomputed_receipt_sha256": recomputed,
        "state_sha256": body.get("state_sha256"),
        "recomputed_state_sha256": _sha256(body.get("state")) if "state" in body else None,
    }


def project_eq64(bits: Mapping[str, Any]) -> dict[str, Any]:
    dims = (
        "task_bounded",
        "delegation_bounded",
        "practice_preserved",
        "independent_verification",
        "human_check_preserving_mode",
        "evidence_adequate",
    )
    missing = [d for d in dims if d not in bits]
    extra = [d for d in bits if d not in dims]
    if missing:
        raise ValueError("missing EQ64 bits: " + ",".join(missing))
    if extra:
        raise ValueError("unexpected EQ64 bits: " + ",".join(extra))
    if any(type(bits[d]) is not bool for d in dims):
        raise ValueError("EQ64 values must be booleans")
    b = {d: bits[d] for d in dims}
    if not b["evidence_adequate"]:
        decision = "HOLD"
    elif not b["independent_verification"]:
        decision = "HUMAN_FIRST"
    elif not (b["delegation_bounded"] and b["practice_preserved"] and b["human_check_preserving_mode"]):
        decision = "DUAL_CHECK"
    elif not b["task_bounded"]:
        decision = "SCAFFOLD"
    else:
        decision = "ASSIST"
    return {"bits": b, "decision": decision}
