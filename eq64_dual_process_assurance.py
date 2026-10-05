from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from eq64_assurance_canary import _regression_canary, _security_canary
from eq64_executable_assurance_engine import (
    SCHEMA_VERSION,
    canonical_bytes,
    evaluate_assurance,
    replay_assurance_receipt,
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(value)
    path.write_bytes(data)
    return _sha256_bytes(data)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("artifact must be a JSON object")
    return value


def produce_security(output_path: str | Path) -> dict[str, Any]:
    artifact = _security_canary()
    _write_json(Path(output_path), artifact)
    return artifact


def produce_regression(output_path: str | Path) -> dict[str, Any]:
    artifact = _regression_canary()
    _write_json(Path(output_path), artifact)
    return artifact


def join_evidence(
    security_path: str | Path,
    regression_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    security_path = Path(security_path)
    regression_path = Path(regression_path)
    output_dir = Path(output_dir)

    security = _load_json(security_path)
    regression = _load_json(regression_path)

    if security.get("schema_version") != "EQ64_SECURITY_CANARY_V1":
        raise ValueError("security artifact schema mismatch")
    if regression.get("schema_version") != "EQ64_REGRESSION_CANARY_V1":
        raise ValueError("regression artifact schema mismatch")

    security_target = security.get("target")
    regression_target = regression.get("target")
    if not isinstance(security_target, dict):
        raise ValueError("security target missing")
    if not isinstance(regression_target, dict):
        raise ValueError("regression target missing")

    security_sha = _sha256_bytes(security_path.read_bytes())
    regression_sha = _sha256_bytes(regression_path.read_bytes())

    here = Path(__file__).resolve().parent
    runtime_sha = _sha256_bytes((here / "ess_evidence_runtime.py").read_bytes())
    engine_sha = _sha256_bytes((here / "eq64_executable_assurance_engine.py").read_bytes())

    payload = {
        "schema_version": SCHEMA_VERSION,
        "target": {
            "system": security_target.get("system"),
            "version": security_target.get("version"),
            "target_id": security_target.get("target_id"),
            "runtime_sha256": runtime_sha,
        },
        "security": {
            "target_id": security_target.get("target_id"),
            "target_runtime_sha256": runtime_sha,
            "source_commit": security_target.get("version"),
            "status": security.get("status"),
            "fresh": True,
            "tests_run": security.get("tests_run"),
            "failure_injections": security.get("failure_injections"),
            "raw_artifact_sha256": security_sha,
        },
        "regression": {
            "target_id": regression_target.get("target_id"),
            "target_runtime_sha256": runtime_sha,
            "source_commit": regression_target.get("version"),
            "status": regression.get("status"),
            "fresh": True,
            "tests_run": regression.get("tests_run"),
            "same_input_replay_equal": regression.get("same_input_replay_equal"),
            "raw_artifact_sha256": regression_sha,
        },
        "readback": {
            "fresh": True,
            "security_artifact_sha256": security_sha,
            "regression_artifact_sha256": regression_sha,
        },
        "claim_guard": {
            "overclaim_flags": [],
            "runtime_admission": False,
            "production_readiness": False,
        },
        "engine": {
            "implementation_sha256": engine_sha,
            "evidence_join": "DUAL_PROCESS_ARTIFACT_JOIN_V1",
        },
    }

    receipt = evaluate_assurance(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "eq64_assurance_input.json", payload)
    _write_json(output_dir / "eq64_assurance_receipt.json", receipt)

    replay = replay_assurance_receipt(receipt)
    _write_json(output_dir / "eq64_assurance_replay.json", replay)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(prog="eq64-dual-process")
    sub = parser.add_subparsers(dest="command", required=True)

    sec = sub.add_parser("produce-security")
    sec.add_argument("output", type=Path)

    reg = sub.add_parser("produce-regression")
    reg.add_argument("output", type=Path)

    join = sub.add_parser("join")
    join.add_argument("security", type=Path)
    join.add_argument("regression", type=Path)
    join.add_argument("--output-dir", type=Path, required=True)

    args = parser.parse_args()

    try:
        if args.command == "produce-security":
            artifact = produce_security(args.output)
            print(canonical_bytes(artifact).decode("utf-8"))
            return 0 if artifact["status"] == "PASS" else 3
        if args.command == "produce-regression":
            artifact = produce_regression(args.output)
            print(canonical_bytes(artifact).decode("utf-8"))
            return 0 if artifact["status"] == "PASS" else 3

        receipt = join_evidence(args.security, args.regression, args.output_dir)
        print(canonical_bytes(receipt).decode("utf-8"))
        return 0 if receipt["decision"] == "PASS" else 3

    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
