from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any, Mapping


SCHEMA_VERSION = (
    "ESS_NEWSIFY_MULTI_SIGNAL_ROUTER__DEDUP_RELEVANCE_VERIFICATION_QUEUE_"
    "AND_CONTRADICTION_PROPAGATION_V1"
)

_TRUSTED_CLASSES = {
    "PRIMARY_OPERATOR_SOURCE",
    "PRIMARY_OFFICIAL_SOURCE",
    "TRUSTED_INSTITUTIONAL_SOURCE",
}

_RELEVANCE_RULES = {
    "AI_AGENT_SECURITY": (
        "ai agent",
        "agentic",
        "model context protocol",
        "mcp ",
        "mcp-",
        "cybersecurity",
        "prompt injection",
        "supply-chain",
        "supply chain",
        "ai security",
        "security incident",
    ),
    "AI_GOVERNANCE_STANDARDS": (
        "ai act",
        "artificial intelligence",
        "trustworthy ai",
        "ai governance",
        "formal verification",
        "standardization",
        "standards",
    ),
    "EARTH_OBSERVATION": (
        "nasa",
        "esa ",
        "satellite",
        "earth observation",
        "climate model",
    ),
    "CRITICAL_INFRASTRUCTURE": (
        "rail",
        "railway",
        "cable fire",
        "power grid",
        "electricity grid",
        "natural gas",
        "water utility",
        "critical infrastructure",
    ),
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


def _signal_id(signal: Mapping[str, Any]) -> str:
    value = signal.get("id")
    if not isinstance(value, str) or not value:
        raise ValueError("every signal requires a non-empty id")
    return value


def _relevance(signal: Mapping[str, Any]) -> tuple[bool, list[str]]:
    text = " ".join(
        str(signal.get(key) or "")
        for key in ("title", "content", "trendTitle")
    ).lower()
    domains = [
        domain
        for domain, terms in _RELEVANCE_RULES.items()
        if any(term in text for term in terms)
    ]
    return bool(domains), domains


def _valid_verification(record: Mapping[str, Any]) -> bool:
    sha = record.get("source_sha256")
    return (
        record.get("status") == "VERIFIED"
        and record.get("trust_class") in _TRUSTED_CLASSES
        and isinstance(record.get("source_url"), str)
        and record["source_url"].startswith("https://")
        and isinstance(sha, str)
        and len(sha) == 64
        and record.get("assessment")
        in {"supports", "contradicts", "insufficient"}
    )


def route_batch(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported schema_version")

    signals = payload.get("signals")
    verifications = payload.get("verifications", [])
    if not isinstance(signals, list):
        raise ValueError("signals must be a list")
    if not isinstance(verifications, list):
        raise ValueError("verifications must be a list")

    verification_by_signal: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in verifications:
        if not isinstance(record, Mapping):
            raise ValueError("verification records must be objects")
        sid = record.get("signal_id")
        if isinstance(sid, str):
            verification_by_signal[sid].append(record)

    routes: list[dict[str, Any]] = []
    seen_trends: set[str] = set()
    seen_fingerprints: set[str] = set()
    verification_queue: list[str] = []
    conflict_claim_keys: set[str] = set()

    for signal in signals:
        if not isinstance(signal, Mapping):
            raise ValueError("signals must contain objects")
        sid = _signal_id(signal)
        trend_id = str(signal.get("trendId") or "")
        fingerprint = str(signal.get("newsItemsFingerprint") or "")

        duplicate = (
            (bool(trend_id) and trend_id in seen_trends)
            or (bool(fingerprint) and fingerprint in seen_fingerprints)
        )
        if trend_id:
            seen_trends.add(trend_id)
        if fingerprint:
            seen_fingerprints.add(fingerprint)

        related = verification_by_signal.get(sid, [])
        claim_key = str(
            signal.get("claim_key")
            or next(
                (
                    r.get("claim_key")
                    for r in related
                    if isinstance(r.get("claim_key"), str) and r.get("claim_key")
                ),
                None,
            )
            or trend_id
            or sid
        )

        relevant, domains = _relevance(signal)
        row: dict[str, Any] = {
            "signal_id": sid,
            "trend_id": trend_id or None,
            "fingerprint": fingerprint or None,
            "claim_key": claim_key,
            "relevance_domains": domains,
            "evidence_candidate": False,
        }

        if duplicate:
            row["route_status"] = "DUPLICATE"
            routes.append(row)
            continue

        if not relevant:
            row["route_status"] = "REJECT_IRRELEVANT"
            routes.append(row)
            continue

        valid = [r for r in related if _valid_verification(r)]
        if not valid:
            row["route_status"] = "VERIFY_REQUIRED"
            verification_queue.append(sid)
            routes.append(row)
            continue

        assessments = {str(r.get("assessment")) for r in valid}
        if "contradicts" in assessments:
            row["route_status"] = "HOLD_CONFLICT"
            conflict_claim_keys.add(claim_key)
        elif "supports" in assessments:
            row["route_status"] = "EVIDENCE_CANDIDATE"
            row["evidence_candidate"] = True
        else:
            row["route_status"] = "HOLD_INSUFFICIENT"
        routes.append(row)

    if conflict_claim_keys:
        for row in routes:
            if (
                row["claim_key"] in conflict_claim_keys
                and row["route_status"] not in {"DUPLICATE", "REJECT_IRRELEVANT"}
            ):
                row["route_status"] = "HOLD_CONFLICT"
                row["evidence_candidate"] = False
        verification_queue = [
            sid
            for sid in verification_queue
            if next(
                (r for r in routes if r["signal_id"] == sid),
                {},
            ).get("claim_key")
            not in conflict_claim_keys
        ]

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "routes": routes,
        "verification_queue": verification_queue,
        "conflict_claim_keys": sorted(conflict_claim_keys),
        "counts": {
            status: sum(1 for row in routes if row["route_status"] == status)
            for status in (
                "DUPLICATE",
                "REJECT_IRRELEVANT",
                "VERIFY_REQUIRED",
                "EVIDENCE_CANDIDATE",
                "HOLD_INSUFFICIENT",
                "HOLD_CONFLICT",
            )
        },
        "evidence_authority": False,
        "automatic_promotion": False,
        "pointer_promotion": False,
        "global_bind": False,
        "runtime_admission": False,
        "production_readiness": False,
        "external_actuation": False,
        "zero_spend": True,
    }
    result["receipt_sha256"] = _sha256(result)
    return result
