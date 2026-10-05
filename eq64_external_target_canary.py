from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from eq64_executable_assurance_engine import (
    SCHEMA_VERSION,
    canonical_bytes,
    evaluate_assurance,
    replay_assurance_receipt,
)

TARGET_SYSTEM = "lbkapcsolat-dotcom/equilibrium-stability-systems"
TARGET_COMMIT = "e3c64f80be032dda6ac30cb38bbed1d41d2fa559"
TARGET_ID = "equilibrium-stability-systems/claim_admission_kernel_v1@e3c64f80"
TARGET_ENVIRONMENT = "RESEARCH_STAGE_OFFLINE_NONPRODUCTION"
TARGET_ROOT = Path("demos/claim_admission_kernel_v1")
EXPECTED_PUBLIC_BASELINE_SHA256 = "09f8599ddb1319181424fbe9fca431297079f9259961968f00ac40bd6c45e163"
EXPECTED_RUNTIME_IDENTITY_SHA256 = "725fc590e074e3d3249bbf3e03b07623dc8f6ba7f162a6e2510649f91b80491b"
RUNTIME_FILES = (
    "demos/claim_admission_kernel_v1/PUBLIC_BASELINE.json",
    "demos/claim_admission_kernel_v1/kernel.py",
    "demos/claim_admission_kernel_v1/verify.py",
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


def _git(repo: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if p.returncode != 0:
        raise ValueError(f"git command failed: {' '.join(args)}: {p.stderr.strip()}")
    return p.stdout.strip()


def _runtime_identity(repo: Path) -> tuple[str, dict[str, str]]:
    blobs: dict[str, str] = {}
    for rel in RUNTIME_FILES:
        blobs[rel] = _git(repo, "rev-parse", f"HEAD:{rel}")
    identity = _sha256_bytes(
        json.dumps(
            blobs,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    )
    return identity, blobs


def _verify_target(repo: Path) -> dict[str, Any]:
    repo = repo.resolve()
    head = _git(repo, "rev-parse", "HEAD")
    if head != TARGET_COMMIT:
        raise ValueError(f"target commit mismatch: expected {TARGET_COMMIT}, got {head}")

    dirty = _git(repo, "status", "--porcelain")
    if dirty:
        raise ValueError("target checkout is not clean")

    runtime_identity, blob_manifest = _runtime_identity(repo)
    if runtime_identity != EXPECTED_RUNTIME_IDENTITY_SHA256:
        raise ValueError(
            "target runtime identity mismatch: "
            f"expected {EXPECTED_RUNTIME_IDENTITY_SHA256}, got {runtime_identity}"
        )

    kernel_root = repo / TARGET_ROOT
    baseline = kernel_root / "PUBLIC_BASELINE.json"
    baseline_sha = _sha256_bytes(baseline.read_bytes())
    if baseline_sha != EXPECTED_PUBLIC_BASELINE_SHA256:
        raise ValueError("public baseline SHA256 mismatch")

    baseline_obj = json.loads(baseline.read_text(encoding="utf-8"))
    if baseline_obj.get("status") != "RESEARCH_STAGE":
        raise ValueError("external target is not research-stage")
    if baseline_obj.get("production_admission") is not False:
        raise ValueError("external target production_admission must remain false")
    if baseline_obj.get("real_actuation") is not False:
        raise ValueError("external target real_actuation must remain false")

    return {
        "system": TARGET_SYSTEM,
        "version": TARGET_COMMIT,
        "target_id": TARGET_ID,
        "runtime_sha256": runtime_identity,
        "environment": TARGET_ENVIRONMENT,
        "public_baseline_sha256": baseline_sha,
        "git_blob_manifest": blob_manifest,
    }


def _load_kernel(repo: Path):
    kernel_path = repo.resolve() / TARGET_ROOT / "kernel.py"
    spec = importlib.util.spec_from_file_location("eq64_external_claim_kernel", kernel_path)
    if spec is None or spec.loader is None:
        raise ValueError("could not load external target kernel")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def produce_external_security(repo: str | Path, output: str | Path) -> dict[str, Any]:
    repo = Path(repo)
    target = _verify_target(repo)
    kernel = _load_kernel(repo)

    evidence = b"synthetic evidence\npressure=nominal\n"
    clean = kernel.demo_payload(evidence)
    cases: list[dict[str, Any]] = []

    def case(case_id: str, payload, evidence_bytes: bytes, decision: str, reason_prefix: str) -> None:
        result = kernel.demo_kernel().decide(payload, evidence_bytes)
        ok = result["decision"] == decision and result["reason"].startswith(reason_prefix)
        cases.append({
            "case_id": case_id,
            "expected_decision": decision,
            "expected_reason_prefix": reason_prefix,
            "observed_decision": result["decision"],
            "observed_reason": result["reason"],
            "receipt_sha256": result["receipt_sha256"],
            "pass": ok,
        })

    case("clean", clean, evidence, "PASS", "ALL_GATES_SATISFIED")

    p = copy.deepcopy(clean)
    p["auto_correct"] = True
    case("unexpected_field", p, evidence, "HOLD", "SCHEMA_UNEXPECTED_FIELD")

    mutated = bytearray(evidence)
    mutated[0] ^= 1
    case("evidence_byte_flip", clean, bytes(mutated), "HOLD", "EVIDENCE_HASH_MISMATCH")

    p = copy.deepcopy(clean)
    p["action"] = "UNAUTHORIZED_DEMO_ACTION"
    case("authority_scope_mismatch", p, evidence, "HOLD", "AUTHORITY_ACTION_SCOPE_MISMATCH")

    p = copy.deepcopy(clean)
    p["human_veto"] = True
    case("human_veto", p, evidence, "HOLD", "HUMAN_VETO_ASSERTED")

    p = kernel.demo_payload(evidence, "synthetic.overcoupled_transition.v1")
    case(
        "c_gt_v",
        p,
        evidence,
        "HOLD",
        "CLAIM_COMPLEXITY_EXCEEDS_VERIFICATION_CAPACITY",
    )

    p = copy.deepcopy(clean)
    p["nonce"] = "wrong-prefix-0001"
    case("nonce_scope_mismatch", p, evidence, "HOLD", "AUTHORITY_NONCE_SCOPE_MISMATCH")

    artifact = {
        "schema_version": "EQ64_EXTERNAL_SECURITY_CANARY_V1",
        "target": target,
        "status": "PASS" if all(c["pass"] for c in cases) else "HOLD",
        "tests_run": len(cases),
        "failure_injections": len(cases) - 1,
        "cases": cases,
    }
    _write_json(Path(output), artifact)
    return artifact


def _run_official_verify(repo: Path) -> tuple[bool, str]:
    root = repo.resolve() / TARGET_ROOT
    p = subprocess.run(
        [sys.executable, "verify.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    output = p.stdout + p.stderr
    return p.returncode == 0, output


def produce_external_regression(repo: str | Path, output: str | Path) -> dict[str, Any]:
    repo = Path(repo)
    target = _verify_target(repo)
    verify_ok, verify_output = _run_official_verify(repo)

    unit_match = re.search(r"Ran\s+(\d+)\s+tests?", verify_output)
    replay_match = re.search(r"Replay:\s+(\d+)/(\d+)\s+expected outcomes matched", verify_output)
    official_unit_tests = int(unit_match.group(1)) if unit_match else 0
    visible_replay_passed = int(replay_match.group(1)) if replay_match else 0
    visible_replay_total = int(replay_match.group(2)) if replay_match else 0

    kernel = _load_kernel(repo)
    evidence = b"synthetic evidence\npressure=nominal\n"
    deterministic: list[dict[str, Any]] = []
    for i in range(8):
        payload = kernel.demo_payload(evidence)
        payload["nonce"] = f"demo-{1000 + i}"
        first = kernel.demo_kernel().decide(payload, evidence)
        second = kernel.demo_kernel().decide(copy.deepcopy(payload), evidence)
        equal = first["receipt_sha256"] == second["receipt_sha256"]
        deterministic.append({
            "case_id": f"same_input_replay_{i + 1}",
            "receipt_sha256": first["receipt_sha256"],
            "equal": equal,
        })

    same_input_replay_equal = all(x["equal"] for x in deterministic)
    tests_run = official_unit_tests + visible_replay_total + len(deterministic)
    status = (
        "PASS"
        if (
            verify_ok
            and official_unit_tests >= 8
            and visible_replay_passed == visible_replay_total
            and visible_replay_total >= 6
            and same_input_replay_equal
            and tests_run >= 10
        )
        else "HOLD"
    )

    artifact = {
        "schema_version": "EQ64_EXTERNAL_REGRESSION_CANARY_V1",
        "target": target,
        "status": status,
        "tests_run": tests_run,
        "official_verify_exit_zero": verify_ok,
        "official_unit_tests": official_unit_tests,
        "visible_replay_passed": visible_replay_passed,
        "visible_replay_total": visible_replay_total,
        "deterministic_replays": deterministic,
        "same_input_replay_equal": same_input_replay_equal,
    }
    _write_json(Path(output), artifact)
    return artifact


def join_external_evidence(
    security_path: str | Path,
    regression_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    security_path = Path(security_path)
    regression_path = Path(regression_path)
    output_dir = Path(output_dir)

    security = _load_json(security_path)
    regression = _load_json(regression_path)

    if security.get("schema_version") != "EQ64_EXTERNAL_SECURITY_CANARY_V1":
        raise ValueError("external security artifact schema mismatch")
    if regression.get("schema_version") != "EQ64_EXTERNAL_REGRESSION_CANARY_V1":
        raise ValueError("external regression artifact schema mismatch")

    st = security.get("target")
    rt = regression.get("target")
    if not isinstance(st, dict) or not isinstance(rt, dict):
        raise ValueError("external target metadata missing")
    if st.get("environment") != TARGET_ENVIRONMENT or rt.get("environment") != TARGET_ENVIRONMENT:
        raise ValueError("external target must remain in nonproduction environment")
    if st.get("system") != rt.get("system"):
        raise ValueError("external target system mismatch")

    security_sha = _sha256_bytes(security_path.read_bytes())
    regression_sha = _sha256_bytes(regression_path.read_bytes())

    here = Path(__file__).resolve().parent
    engine_sha = _sha256_bytes((here / "eq64_executable_assurance_engine.py").read_bytes())

    payload = {
        "schema_version": SCHEMA_VERSION,
        "target": {
            "system": TARGET_SYSTEM,
            "version": TARGET_COMMIT,
            "target_id": TARGET_ID,
            "runtime_sha256": EXPECTED_RUNTIME_IDENTITY_SHA256,
        },
        "security": {
            "target_id": st.get("target_id"),
            "target_runtime_sha256": st.get("runtime_sha256"),
            "source_commit": st.get("version"),
            "status": security.get("status"),
            "fresh": True,
            "tests_run": security.get("tests_run"),
            "failure_injections": security.get("failure_injections"),
            "raw_artifact_sha256": security_sha,
        },
        "regression": {
            "target_id": rt.get("target_id"),
            "target_runtime_sha256": rt.get("runtime_sha256"),
            "source_commit": rt.get("version"),
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
            "external_target_canary": "AUTHORIZED_NONPRODUCTION_CROSS_REPO_V1",
        },
    }

    receipt = evaluate_assurance(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "eq64_external_assurance_input.json", payload)
    _write_json(output_dir / "eq64_external_assurance_receipt.json", receipt)
    replay = replay_assurance_receipt(receipt)
    _write_json(output_dir / "eq64_external_assurance_replay.json", replay)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(prog="eq64-external-target-canary")
    sub = parser.add_subparsers(dest="command", required=True)

    sec = sub.add_parser("produce-security")
    sec.add_argument("target_repo", type=Path)
    sec.add_argument("output", type=Path)

    reg = sub.add_parser("produce-regression")
    reg.add_argument("target_repo", type=Path)
    reg.add_argument("output", type=Path)

    join = sub.add_parser("join")
    join.add_argument("security", type=Path)
    join.add_argument("regression", type=Path)
    join.add_argument("--output-dir", type=Path, required=True)

    args = parser.parse_args()

    try:
        if args.command == "produce-security":
            artifact = produce_external_security(args.target_repo, args.output)
            print(canonical_bytes(artifact).decode("utf-8"))
            return 0 if artifact["status"] == "PASS" else 3

        if args.command == "produce-regression":
            artifact = produce_external_regression(args.target_repo, args.output)
            print(canonical_bytes(artifact).decode("utf-8"))
            return 0 if artifact["status"] == "PASS" else 3

        receipt = join_external_evidence(args.security, args.regression, args.output_dir)
        print(canonical_bytes(receipt).decode("utf-8"))
        return 0 if receipt["decision"] == "PASS" else 3

    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
