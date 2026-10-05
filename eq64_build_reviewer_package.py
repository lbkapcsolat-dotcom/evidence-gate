from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from eq64_executable_assurance_engine import canonical_bytes
from eq64_independent_reproduction_package import write_manifest

PACKAGE_SCHEMA = "EQ64_INDEPENDENT_REPRODUCTION_PACKAGE_V1"

SOURCE_FILES = [
    "eq64_executable_assurance_engine.py",
    "eq64_external_target_canary.py",
    "eq64_comparative_false_pass_experiment.py",
    "eq64_independent_reproduction_package.py",
    "eq64_reviewer_reproduce.py",
]

TARGET_REPO = "https://github.com/lbkapcsolat-dotcom/equilibrium-stability-systems.git"
TARGET_COMMIT = "e3c64f80be032dda6ac30cb38bbed1d41d2fa559"
TARGET_RUNTIME_SHA256 = "725fc590e074e3d3249bbf3e03b07623dc8f6ba7f162a6e2510649f91b80491b"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_package(
    source_root: Path,
    external_authority_dir: Path,
    comparative_dir: Path,
    output_dir: Path,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    for rel in SOURCE_FILES:
        shutil.copy2(source_root / rel, output_dir / rel)

    authority_receipt = _load(external_authority_dir / "eq64_external_assurance_receipt.json")
    experiment = _load(comparative_dir / "eq64_comparative_false_pass_experiment.json")

    expected = {
        "schema_version": PACKAGE_SCHEMA,
        "external_target_repo": TARGET_REPO,
        "external_target_commit": TARGET_COMMIT,
        "external_target_runtime_sha256": TARGET_RUNTIME_SHA256,
        "authority_receipt_sha256": authority_receipt["receipt_sha256"],
        "authority_evidence_bundle_sha256": authority_receipt["evidence_bundle_sha256"],
        "external_security_raw_sha256": authority_receipt["security"]["raw_artifact_sha256"],
        "external_regression_raw_sha256": authority_receipt["regression"]["raw_artifact_sha256"],
        "experiment_sha256": experiment["experiment_sha256"],
        "expected_eq64_state": 63,
        "expected_false_pass_count": 0,
        "expected_fault_detection_count": 20,
        "claim_ceiling": "BOUNDED_REVIEWER_REPRODUCTION_HANDOFF_ONLY",
    }
    (output_dir / "EXPECTED_RESULTS.json").write_bytes(canonical_bytes(expected))

    source_coords = {
        "schema_version": "EQ64_REVIEWER_SOURCE_COORDINATES_V1",
        "external_target": {
            "repository": TARGET_REPO,
            "commit": TARGET_COMMIT,
            "runtime_sha256": TARGET_RUNTIME_SHA256,
        },
        "reviewer_command": (
            "python eq64_reviewer_reproduce.py "
            "--package-root . "
            "--external-target-repo ./external-target "
            "--output REPRODUCTION_RESULT.json"
        ),
    }
    (output_dir / "SOURCE_COORDINATES.json").write_bytes(canonical_bytes(source_coords))

    readme = f"""# EQ64 Independent Reproduction Package V1

## Scope

This package is a bounded reviewer handoff. It is designed so a reviewer does not need the original chat, Drive state, or internal project lineage.

It does **not** claim production readiness, certification, runtime admission, or completed third-party review.

## Prerequisites

- Python 3.12 recommended
- git
- network access only for cloning the frozen public external target

No third-party Python packages are required by the reproduction runner.

## 1. Obtain the frozen external target

    git clone {TARGET_REPO} external-target
    git -C external-target checkout {TARGET_COMMIT}
    git -C external-target status --porcelain

The final command must print nothing.

Pinned composite runtime identity expected by the package:

    {TARGET_RUNTIME_SHA256}

## 2. Run the reproduction

From the root of this package:

    python eq64_reviewer_reproduce.py \
      --package-root . \
      --external-target-repo ./external-target \
      --output REPRODUCTION_RESULT.json

Expected exit code: 0.

## 3. What the runner checks

1. package SHA-256 manifest;
2. exact external target commit and clean checkout;
3. frozen composite runtime identity;
4. external security evidence regeneration;
5. external regression evidence regeneration;
6. independent EQ64 authority join;
7. authority receipt replay validity;
8. deliberate receipt tampering is rejected;
9. authority receipt and evidence bundle match frozen expected hashes;
10. raw security/regression artifact hashes match;
11. the 21-case comparative experiment regenerates the same experiment SHA;
12. EQ64 false-PASS remains 0/20;
13. EQ64 fault detection remains 20/20.

## 4. Interpretation

A successful reproduction means the frozen package reproduced the bounded results on the frozen public target in the reviewer's environment.

It does not mean the reviewer endorses the system, that the results generalize statistically, or that the system is safe for production.

## 5. Reviewer return

Please return only:
- REPRODUCTION_RESULT.json
- operating system and Python version
- deviations from the commands above
- optional signed comment or review notes

Do not send credentials, private environment variables, or unrelated machine information.
"""
    (output_dir / "REVIEWER_README.md").write_text(readme, encoding="utf-8")

    manifest_paths = SOURCE_FILES + [
        "EXPECTED_RESULTS.json",
        "SOURCE_COORDINATES.json",
        "REVIEWER_README.md",
    ]
    manifest = write_manifest(output_dir, manifest_paths, output_dir / "MANIFEST.json")
    return {
        "schema_version": PACKAGE_SCHEMA,
        "manifest_sha256": manifest["manifest_sha256"],
        "file_count": len(manifest_paths),
        "authority_receipt_sha256": expected["authority_receipt_sha256"],
        "experiment_sha256": expected["experiment_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--external-authority-dir", type=Path, required=True)
    parser.add_argument("--comparative-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = build_package(
        args.source_root,
        args.external_authority_dir,
        args.comparative_dir,
        args.output_dir,
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
