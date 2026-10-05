from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from eq64_comparative_false_pass_experiment import run_experiment
from eq64_executable_assurance_engine import canonical_bytes, replay_assurance_receipt
from eq64_external_target_canary import (
    join_external_evidence,
    produce_external_regression,
    produce_external_security,
)
from eq64_independent_reproduction_package import verify_manifest, verify_tamper_rejection


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def reproduce(package_root: Path, external_target_repo: Path) -> dict[str, Any]:
    package_root = package_root.resolve()
    external_target_repo = external_target_repo.resolve()

    manifest = _load(package_root / "MANIFEST.json")
    manifest_valid = verify_manifest(package_root, manifest)
    if not manifest_valid:
        raise ValueError("reviewer package manifest verification failed")

    expected = _load(package_root / "EXPECTED_RESULTS.json")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        security_path = tmp_root / "security.json"
        regression_path = tmp_root / "regression.json"
        authority_dir = tmp_root / "authority"

        security = produce_external_security(external_target_repo, security_path)
        regression = produce_external_regression(external_target_repo, regression_path)
        receipt = join_external_evidence(security_path, regression_path, authority_dir)

        replay = replay_assurance_receipt(receipt)
        tamper_rejected = verify_tamper_rejection(authority_dir / "eq64_external_assurance_receipt.json")
        experiment = run_experiment()

        checks = {
            "manifest_valid": manifest_valid,
            "security_status_pass": security.get("status") == "PASS",
            "regression_status_pass": regression.get("status") == "PASS",
            "authority_decision_pass": receipt.get("decision") == "PASS",
            "authority_eq64_state_63": receipt.get("eq64", {}).get("state_index") == 63,
            "authority_replay_valid": replay.get("valid") is True,
            "tampered_receipt_rejected": tamper_rejected,
            "authority_receipt_matches_expected": (
                receipt.get("receipt_sha256") == expected.get("authority_receipt_sha256")
            ),
            "authority_bundle_matches_expected": (
                receipt.get("evidence_bundle_sha256") == expected.get("authority_evidence_bundle_sha256")
            ),
            "security_artifact_matches_expected": (
                hashlib.sha256(security_path.read_bytes()).hexdigest()
                == expected.get("external_security_raw_sha256")
            ),
            "regression_artifact_matches_expected": (
                hashlib.sha256(regression_path.read_bytes()).hexdigest()
                == expected.get("external_regression_raw_sha256")
            ),
            "experiment_matches_expected": (
                experiment.get("experiment_sha256") == expected.get("experiment_sha256")
            ),
            "eq64_false_pass_zero": (
                experiment["metrics"]["C_EQ64_NONCOMPENSATING"]["false_pass_count"] == 0
            ),
            "eq64_fault_detection_complete": (
                experiment["metrics"]["C_EQ64_NONCOMPENSATING"]["fault_detection_count"] == 20
            ),
        }

        result = {
            "schema_version": "EQ64_INDEPENDENT_REPRODUCTION_RESULT_V1",
            "checks": checks,
            "all_checks_pass": all(checks.values()),
            "authority_receipt_sha256": receipt.get("receipt_sha256"),
            "authority_evidence_bundle_sha256": receipt.get("evidence_bundle_sha256"),
            "experiment_sha256": experiment.get("experiment_sha256"),
            "external_target_commit": expected.get("external_target_commit"),
            "claim_ceiling": {
                "reviewer_package_reproduced": all(checks.values()),
                "third_party_human_review_completed": False,
                "production_readiness": False,
                "runtime_admission": False,
                "certification": False,
                "global_bind": False,
            },
        }
        body = dict(result)
        result["reproduction_result_sha256"] = _sha256_json(body)
        return result


def main() -> int:
    parser = argparse.ArgumentParser(prog="eq64-reviewer-reproduce")
    parser.add_argument("--package-root", type=Path, default=Path("."))
    parser.add_argument("--external-target-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("REPRODUCTION_RESULT.json"))
    args = parser.parse_args()

    try:
        result = reproduce(args.package_root, args.external_target_repo)
        args.output.write_bytes(canonical_bytes(result))
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0 if result["all_checks_pass"] else 3
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
