from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping


class EvidenceStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTING = "CONFLICTING"


_ALLOWED_ASSESSMENTS = {"supports", "contradicts", "insufficient"}


@dataclass(frozen=True)
class Classification:
    claim: str
    status: EvidenceStatus
    supporting_count: int
    contradicting_count: int
    insufficient_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "status": self.status.value,
            "supporting_count": self.supporting_count,
            "contradicting_count": self.contradicting_count,
            "insufficient_count": self.insufficient_count,
        }


def classify_claim(claim: str, evidence: Iterable[Mapping[str, Any]]) -> Classification:
    """Classify a claim from explicit evidence assessments.

    Rules are intentionally conservative and deterministic:
    - any contradiction -> CONFLICTING
    - otherwise, at least one support -> SUPPORTED
    - otherwise -> INSUFFICIENT
    """
    if not isinstance(claim, str) or not claim.strip():
        raise ValueError("claim must be a non-empty string")

    supporting = 0
    contradicting = 0
    insufficient = 0

    for index, item in enumerate(evidence):
        assessment = item.get("assessment")
        if not isinstance(assessment, str):
            raise ValueError(f"evidence[{index}].assessment must be a string")

        normalized = assessment.strip().lower()
        if normalized not in _ALLOWED_ASSESSMENTS:
            allowed = ", ".join(sorted(_ALLOWED_ASSESSMENTS))
            raise ValueError(
                f"evidence[{index}].assessment must be one of: {allowed}"
            )

        if normalized == "supports":
            supporting += 1
        elif normalized == "contradicts":
            contradicting += 1
        else:
            insufficient += 1

    if contradicting > 0:
        status = EvidenceStatus.CONFLICTING
    elif supporting > 0:
        status = EvidenceStatus.SUPPORTED
    else:
        status = EvidenceStatus.INSUFFICIENT

    return Classification(
        claim=claim.strip(),
        status=status,
        supporting_count=supporting,
        contradicting_count=contradicting,
        insufficient_count=insufficient,
    )


def classify_payload(payload: Mapping[str, Any]) -> Classification:
    claim = payload.get("claim")
    evidence = payload.get("evidence", [])

    if not isinstance(evidence, list):
        raise ValueError("evidence must be a list")

    return classify_claim(claim, evidence)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify a claim as SUPPORTED, INSUFFICIENT, or CONFLICTING."
    )
    parser.add_argument("input", type=Path, help="Path to an input JSON file")
    args = parser.parse_args()

    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("input JSON must contain an object")
        result = classify_payload(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
