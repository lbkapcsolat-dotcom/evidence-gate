from __future__ import annotations

import hmac
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ValidationVerdict(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD_FAIL_CLOSED"


class FaultType(str, Enum):
    NONE = "NONE"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    MALFORMED_JSON = "MALFORMED_JSON"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    AUTHORITY_MISMATCH = "AUTHORITY_MISMATCH"
    CONTRADICTORY_PASS_INVALID_AUTHORITY = "CONTRADICTORY_PASS_INVALID_AUTHORITY"


@dataclass(frozen=True)
class EnvelopePolicy:
    expected_authority_token: str
    max_payload_bytes: int = 4096


class TaskExecutionEnvelope:
    """Dependency-free fail-closed evaluator for bounded plugin evidence."""

    _ALLOWED_KEYS = frozenset({"status", "data", "source", "error", "result"})
    _REQUIRED_KEYS = frozenset({"status", "source"})

    def __init__(self, policy: EnvelopePolicy):
        self.policy = policy

    def evaluate_payload(
        self,
        raw_response: str,
        authority_token: str,
    ) -> ValidationVerdict:
        if not raw_response:
            return ValidationVerdict.HOLD

        if len(raw_response.encode("utf-8")) > self.policy.max_payload_bytes:
            return ValidationVerdict.HOLD

        try:
            payload = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError, UnicodeError):
            return ValidationVerdict.HOLD

        if not isinstance(payload, dict):
            return ValidationVerdict.HOLD

        keys = set(payload)
        if not self._REQUIRED_KEYS.issubset(keys):
            return ValidationVerdict.HOLD
        if not keys.issubset(self._ALLOWED_KEYS):
            return ValidationVerdict.HOLD

        status = payload.get("status")
        if type(status) is not int:
            return ValidationVerdict.HOLD
        if status != 200:
            return ValidationVerdict.HOLD
        if "error" in payload:
            return ValidationVerdict.HOLD

        source = payload.get("source")
        if not isinstance(source, str) or not source.strip():
            return ValidationVerdict.HOLD

        if "data" in payload and not isinstance(payload["data"], str):
            return ValidationVerdict.HOLD
        if "result" in payload and not isinstance(payload["result"], str):
            return ValidationVerdict.HOLD
        if "data" not in payload and "result" not in payload:
            return ValidationVerdict.HOLD

        if not isinstance(authority_token, str):
            return ValidationVerdict.HOLD
        if not hmac.compare_digest(
            authority_token,
            self.policy.expected_authority_token,
        ):
            return ValidationVerdict.HOLD

        return ValidationVerdict.PASS


class RouteIsolationHarness:
    """Records route-local verdicts without cross-route promotion."""

    def __init__(self, envelope: TaskExecutionEnvelope):
        self._envelope = envelope
        self._route_state: dict[str, ValidationVerdict] = {}

    def evaluate(
        self,
        route_id: str,
        raw_response: str,
        authority_token: str,
    ) -> ValidationVerdict:
        verdict = self._envelope.evaluate_payload(raw_response, authority_token)
        self._route_state[route_id] = verdict
        return verdict

    def route_state(self, route_id: str) -> ValidationVerdict | None:
        return self._route_state.get(route_id)


class AdversarialFaultInjector:
    VALID_TOKEN = "VALID_HAR_AUTHORITY_TOKEN_998877"
    VALID_PAYLOAD = '{"status":200,"data":"2+2=4","source":"Wolfram"}'

    @classmethod
    def simulate_plugin_response(cls, fault: FaultType) -> tuple[str, str]:
        if fault is FaultType.NONE:
            return cls.VALID_PAYLOAD, cls.VALID_TOKEN
        if fault is FaultType.NETWORK_TIMEOUT:
            return "", cls.VALID_TOKEN
        if fault is FaultType.MALFORMED_JSON:
            return '{"status":200,"data":"2+2=4","source":"Wolfram"', cls.VALID_TOKEN
        if fault is FaultType.RATE_LIMIT_EXCEEDED:
            return '{"status":429,"error":"Quota Exceeded","source":"Wolfram"}', cls.VALID_TOKEN
        if fault is FaultType.AUTHORITY_MISMATCH:
            return cls.VALID_PAYLOAD, "FAKE_AUTHORITY_TOKEN"
        if fault is FaultType.CONTRADICTORY_PASS_INVALID_AUTHORITY:
            return '{"status":200,"result":"PASS","source":"Wolfram"}', "INVALID_AUTHORITY"
        raise ValueError(f"Unsupported fault: {fault}")


def run_validation_suite() -> dict[str, str]:
    envelope = TaskExecutionEnvelope(
        EnvelopePolicy(
            expected_authority_token=AdversarialFaultInjector.VALID_TOKEN,
        )
    )
    results: dict[str, str] = {}
    for fault in FaultType:
        raw_response, token = AdversarialFaultInjector.simulate_plugin_response(fault)
        verdict = envelope.evaluate_payload(raw_response, token)
        expected = (
            ValidationVerdict.PASS
            if fault is FaultType.NONE
            else ValidationVerdict.HOLD
        )
        if verdict is not expected:
            raise AssertionError(
                f"Unexpected verdict for {fault.value}: {verdict.value}"
            )
        results[fault.value] = verdict.value
    return results


if __name__ == "__main__":
    print(json.dumps(run_validation_suite(), indent=2, sort_keys=True))
