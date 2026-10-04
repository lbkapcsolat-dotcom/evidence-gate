from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from evidence_gate import classify_payload


SCHEMA_VERSION = "ESS_NEWSIFY_VERIFIED_SIGNAL_TO_EVIDENCE_ADAPTER_V1"
_TRUSTED_CLASSES = {
    "PRIMARY_OPERATOR_SOURCE",
    "PRIMARY_OFFICIAL_SOURCE",
    "TRUSTED_INSTITUTIONAL_SOURCE",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _base_result(
    payload: Mapping[str, Any],
    *,
    adapter_status: str,
    evidence: list[dict[str, Any]],
    evidence_candidate: bool,
) -> dict[str, Any]:
    classification = classify_payload(
        {"claim": payload["claim"], "evidence": evidence}
    ).to_dict()
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "adapter_status": adapter_status,
        "claim": payload["claim"],
        "signal": dict(payload["signal"]),
        "relevance": dict(payload["relevance"]),
        "verification": dict(payload["verification"]),
        "evidence": evidence,
        "classification": classification,
        "evidence_candidate": evidence_candidate,
        "evidence_authority": False,
        "automatic_promotion": False,
        "pointer_promotion": False,
        "global_bind": False,
        "runtime_admission": False,
        "production_readiness": False,
        "external_actuation": False,
        "zero_spend": True,
    }
    body["receipt_sha256"] = _sha256(body)
    return body


def adapt(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported schema_version")

    claim = payload.get("claim")
    signal = payload.get("signal")
    relevance = payload.get("relevance")
    verification = payload.get("verification")
    if not isinstance(claim, str) or not claim.strip():
        raise ValueError("claim must be a non-empty string")
    if not isinstance(signal, Mapping):
        raise ValueError("signal must be an object")
    if signal.get("source_class") != "SIGNAL_SOURCE":
        raise ValueError("signal.source_class must be SIGNAL_SOURCE")
    if not isinstance(relevance, Mapping):
        raise ValueError("relevance must be an object")
    if not isinstance(verification, Mapping):
        raise ValueError("verification must be an object")

    signal_evidence = {
        "source": f"Newsify:{signal.get('trend_id') or signal.get('id')}",
        "source_class": "SIGNAL_SOURCE",
        "assessment": "insufficient",
    }

    if relevance.get("status") != "RELEVANT":
        return _base_result(
            payload,
            adapter_status="REJECT_IRRELEVANT",
            evidence=[signal_evidence],
            evidence_candidate=False,
        )

    status = verification.get("status")
    trust_class = verification.get("trust_class")
    source_url = verification.get("source_url")
    source_sha256 = verification.get("source_sha256")
    assessment = verification.get("assessment")

    verified = (
        status == "VERIFIED"
        and trust_class in _TRUSTED_CLASSES
        and isinstance(source_url, str)
        and source_url.startswith("https://")
        and isinstance(source_sha256, str)
        and len(source_sha256) == 64
        and assessment in {"supports", "contradicts", "insufficient"}
    )
    if not verified:
        return _base_result(
            payload,
            adapter_status="HOLD_VERIFY_REQUIRED",
            evidence=[signal_evidence],
            evidence_candidate=False,
        )

    verified_evidence = {
        "source": verification.get("source_name"),
        "source_class": "VERIFIED_SOURCE",
        "source_url": source_url,
        "source_sha256": source_sha256,
        "trust_class": trust_class,
        "assessment": assessment,
    }
    evidence = [signal_evidence, verified_evidence]
    classification = classify_payload({"claim": claim, "evidence": evidence})

    if classification.status.value == "CONFLICTING":
        status_out = "HOLD_CONFLICT"
        candidate = False
    elif classification.status.value == "SUPPORTED":
        status_out = "PASS_VERIFIED_TO_EVIDENCE_CANDIDATE"
        candidate = True
    else:
        status_out = "HOLD_INSUFFICIENT"
        candidate = False

    return _base_result(
        payload,
        adapter_status=status_out,
        evidence=evidence,
        evidence_candidate=candidate,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a verified Newsify signal into a bounded evidence candidate."
    )
    parser.add_argument("input", type=Path)
    args = parser.parse_args()

    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("input JSON must contain an object")
        result = adapt(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))

    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
