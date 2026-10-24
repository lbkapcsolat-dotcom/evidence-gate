from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


POLICY_VERSION = "drive-evidence-adapter-v1"
_ALLOWED_RETRIEVAL_STATUS = {"ok", "not_found", "unavailable", "error"}


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _normalize_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _normalize_sha256(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if len(normalized) != 64:
        return None
    try:
        int(normalized, 16)
    except ValueError:
        return None
    return normalized


def assess_drive_artifact(
    requirement: Mapping[str, Any],
    record: Mapping[str, Any] | None,
) -> tuple[str, str, list[str]]:
    drive_file_id = _require_string(
        requirement.get("drive_file_id"), "requirement.drive_file_id"
    )
    expected = requirement.get("expected")
    if not isinstance(expected, Mapping) or not expected:
        raise ValueError(
            f"required artifact {drive_file_id} must declare at least one expected constraint"
        )

    if record is None:
        return (
            "insufficient",
            "no retrieval record was supplied for the required Drive file",
            ["record_missing"],
        )

    retrieval_status = record.get("retrieval_status")
    if not isinstance(retrieval_status, str):
        return (
            "insufficient",
            "retrieval_status is missing or not a string",
            ["retrieval_status_missing"],
        )

    retrieval_status = retrieval_status.strip().lower()
    if retrieval_status not in _ALLOWED_RETRIEVAL_STATUS:
        return (
            "insufficient",
            f"unrecognized retrieval_status={retrieval_status}",
            ["retrieval_status_unknown"],
        )

    if retrieval_status == "not_found":
        return (
            "contradicts",
            "Drive retrieval explicitly established that the required file was not found",
            ["not_found"],
        )

    if retrieval_status in {"unavailable", "error"}:
        return (
            "insufficient",
            f"Drive retrieval could not establish file identity (status={retrieval_status})",
            [retrieval_status],
        )

    mismatches: list[str] = []
    missing_checks: list[str] = []

    def compare_string(field: str, actual_key: str | None = None) -> None:
        if field not in expected:
            return
        key = actual_key or field
        exp = expected.get(field)
        act = record.get(key)
        if not isinstance(exp, str) or not exp.strip():
            raise ValueError(f"expected.{field} must be a non-empty string")
        if not isinstance(act, str) or not act.strip():
            missing_checks.append(field)
            return
        if act.strip() != exp.strip():
            mismatches.append(field)

    compare_string("name")
    compare_string("mime_type")

    if "size_bytes" in expected:
        exp_size = _normalize_int(expected.get("size_bytes"))
        if exp_size is None:
            raise ValueError("expected.size_bytes must be a non-negative integer")
        act_size = _normalize_int(record.get("size_bytes"))
        if act_size is None:
            missing_checks.append("size_bytes")
        elif act_size != exp_size:
            mismatches.append("size_bytes")

    if "sha256" in expected:
        exp_hash = _normalize_sha256(expected.get("sha256"))
        if exp_hash is None:
            raise ValueError(
                "expected.sha256 must be a 64-character hexadecimal SHA256"
            )
        act_hash = _normalize_sha256(record.get("sha256"))
        if act_hash is None:
            missing_checks.append("sha256")
        elif act_hash != exp_hash:
            mismatches.append("sha256")

    if "parent_id" in expected:
        exp_parent = expected.get("parent_id")
        if not isinstance(exp_parent, str) or not exp_parent.strip():
            raise ValueError("expected.parent_id must be a non-empty string")
        parents = record.get("parent_ids")
        if not isinstance(parents, list) or not all(
            isinstance(x, str) for x in parents
        ):
            missing_checks.append("parent_id")
        elif exp_parent.strip() not in [x.strip() for x in parents]:
            mismatches.append("parent_id")

    if mismatches:
        return (
            "contradicts",
            "one or more declared Drive identity constraints do not match",
            [f"mismatch:{x}" for x in mismatches],
        )

    if missing_checks:
        return (
            "insufficient",
            "one or more required identity checks could not be evaluated",
            [f"missing:{x}" for x in missing_checks],
        )

    return (
        "supports",
        "Drive artifact exists and all declared identity constraints match",
        [],
    )


def adapt_drive_evidence_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    scope_name = _require_string(payload.get("scope_name"), "scope_name")
    required = payload.get("required_artifacts")
    records = payload.get("drive_records")

    if not isinstance(required, list) or not required:
        raise ValueError("required_artifacts must be a non-empty list")
    if not isinstance(records, list):
        raise ValueError("drive_records must be a list")

    requirements: list[Mapping[str, Any]] = []
    required_ids: set[str] = set()
    for index, item in enumerate(required):
        if not isinstance(item, Mapping):
            raise ValueError(f"required_artifacts[{index}] must be an object")
        file_id = _require_string(
            item.get("drive_file_id"),
            f"required_artifacts[{index}].drive_file_id",
        )
        if file_id in required_ids:
            raise ValueError(f"duplicate required Drive file id: {file_id}")
        required_ids.add(file_id)
        requirements.append(item)

    by_id: dict[str, Mapping[str, Any]] = {}
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ValueError(f"drive_records[{index}] must be an object")
        file_id = _require_string(
            record.get("drive_file_id"),
            f"drive_records[{index}].drive_file_id",
        )
        if file_id in by_id:
            raise ValueError(f"duplicate Drive retrieval record: {file_id}")
        by_id[file_id] = record

    evidence: list[dict[str, Any]] = []
    for requirement in requirements:
        file_id = requirement["drive_file_id"]
        record = by_id.get(file_id)
        assessment, reason, details = assess_drive_artifact(
            requirement, record
        )
        evidence.append(
            {
                "source": f"google-drive:file:{file_id}",
                "assessment": assessment,
                "adapter": POLICY_VERSION,
                "reason": reason,
                "details": details,
                "drive_file_id": file_id,
                "expected": dict(requirement["expected"]),
                "raw": dict(record) if record is not None else None,
            }
        )

    claim = (
        f"All {len(requirements)} required Google Drive artifacts for "
        f"{scope_name} exist and match their declared identity constraints."
    )

    return {
        "claim": claim,
        "evidence": evidence,
        "adapter": {
            "name": "drive_evidence_adapter",
            "policy_version": POLICY_VERSION,
            "scope_name": scope_name,
            "required_artifact_count": len(requirements),
            "retrieval_record_count": len(records),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert normalized Google Drive retrieval records "
            "into Evidence Gate input."
        )
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()

    try:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("input JSON must contain an object")
        adapted = adapt_drive_evidence_payload(raw)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))

    rendered = json.dumps(adapted, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
