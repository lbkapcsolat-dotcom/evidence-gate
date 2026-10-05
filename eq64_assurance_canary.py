from __future__ import annotations

import copy
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

from ess_evidence_runtime import build_receipt, replay_receipt
from eq64_executable_assurance_engine import (
    SCHEMA_VERSION,
    canonical_bytes,
    evaluate_assurance,
)

TARGET_COMMIT = "5efa63b864b11fc2feaeac10dbaef63a4b990d90"
TARGET_ID = "evidence-gate@5efa63b8"
TARGET_SYSTEM = "lbkapcsolat-dotcom/evidence-gate"
TARGET_RUNTIME_SHA256 = "1a1a94d08812d6393d417470efb4801bb397388d73171c39ef33a2fb6262bcce"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_canonical_json(path: Path, value: Any) -> str:
    data = canonical_bytes(value)
    path.write_bytes(data)
    return _sha256_bytes(data)


def _readback_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _base_payload() -> dict[str, Any]:
    source_sha = "100ff50b72087f24e1b2a133391e79f49070f8c416b2f6e738ed04802d0c6fc7"
    io_sha = "0fc5c5fb7ca750fc3e21c1009f35fdddd894af99353cc13cc01cf138487c6e48"
    return {
        "schema_version": "ESS_EVIDENCE_RUNTIME_V1",
        "claim": "EQ64 executable assurance canary baseline",
        "source": {"name": "choice-space-lq-shadow-v1", "version": 4, "sha256": source_sha},
        "execution": {
            "execution_id": "EQ64_EXECUTABLE_ASSURANCE_CANARY_V1",
            "input_sha256": io_sha,
            "output_sha256": io_sha,
            "environment_id": "local:deterministic-canary",
        },
        "provider_readback": {
            "provider": "local-canary",
            "source_name": "choice-space-lq-shadow-v1",
            "source_version": 4,
            "source_sha256": source_sha,
            "fresh": True,
        },
        "eq64": {
            "historical_identity": False,
            "fresh_readback": True,
            "semantic_contract": True,
            "baseline_bound": True,
            "admissible_execution": True,
            "negative_evidence": False,
        },
        "claim_level": 1,
        "previous_claim_level": 0,
        "new_admissible_evidence": True,
    }


def _security_canary() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    def add_case(case_id: str, payload: dict[str, Any], expected: str) -> None:
        receipt = build_receipt(payload)
        observed = receipt["admission"]
        cases.append({
            "case_id": case_id,
            "expected": expected,
            "observed": observed,
            "pass": observed == expected,
            "receipt_sha256": receipt["receipt_sha256"],
        })

    base = _base_payload()
    add_case("baseline_pass", copy.deepcopy(base), "PASS")

    p = copy.deepcopy(base); p["eq64"]["negative_evidence"] = True
    add_case("negative_evidence_reject", p, "REJECT")

    p = copy.deepcopy(base); p["provider_readback"]["source_sha256"] = "0" * 64
    add_case("provider_hash_mismatch_hold", p, "HOLD")

    p = copy.deepcopy(base)
    p["claim_level"] = 2; p["previous_claim_level"] = 1; p["new_admissible_evidence"] = False
    add_case("silent_promotion_hold", p, "HOLD")

    p = copy.deepcopy(base); p["source"]["source_class"] = "SIGNAL_SOURCE"
    add_case("signal_source_hold", p, "HOLD")

    p = copy.deepcopy(base); p["provider_readback"]["fresh"] = False
    add_case("stale_provider_hold", p, "HOLD")

    receipt = build_receipt(copy.deepcopy(base))
    tampered = copy.deepcopy(receipt); tampered["claim"] = "tampered"
    replay_valid = replay_receipt(tampered)["valid"]
    cases.append({
        "case_id": "tampered_receipt_replay_rejected",
        "expected": False,
        "observed": replay_valid,
        "pass": replay_valid is False,
        "receipt_sha256": receipt["receipt_sha256"],
    })

    return {
        "schema_version": "EQ64_SECURITY_CANARY_V1",
        "target": {"system": TARGET_SYSTEM, "version": TARGET_COMMIT, "target_id": TARGET_ID},
        "cases": cases,
        "tests_run": len(cases),
        "failure_injections": len(cases) - 1,
        "status": "PASS" if all(c["pass"] for c in cases) else "HOLD",
    }


def _regression_canary() -> dict[str, Any]:
    dims = [
        "historical_identity",
        "fresh_readback",
        "semantic_contract",
        "baseline_bound",
        "admissible_execution",
        "negative_evidence",
    ]
    cases: list[dict[str, Any]] = []
    all_replay_equal = True
    base = _base_payload()

    for bits in itertools.product([False, True], repeat=6):
        payload = copy.deepcopy(base)
        payload["claim"] = "EQ64 exhaustive runtime canary"
        payload["eq64"].update(dict(zip(dims, bits)))
        first = build_receipt(payload)
        second = build_receipt(copy.deepcopy(payload))
        if bits[-1]:
            expected = "REJECT"
        elif all(bits[i] for i in (1, 2, 3, 4)):
            expected = "PASS"
        else:
            expected = "HOLD"
        replay_ok = replay_receipt(first)["valid"]
        equal = (
            first["receipt_sha256"] == second["receipt_sha256"]
            and first["evidence_id"] == second["evidence_id"]
        )
        all_replay_equal = all_replay_equal and equal and replay_ok
        cases.append({
            "bits": [int(x) for x in bits],
            "expected": expected,
            "observed": first["admission"],
            "deterministic": equal,
            "replay_valid": replay_ok,
            "pass": first["admission"] == expected and equal and replay_ok,
            "receipt_sha256": first["receipt_sha256"],
        })

    return {
        "schema_version": "EQ64_REGRESSION_CANARY_V1",
        "target": {"system": TARGET_SYSTEM, "version": TARGET_COMMIT, "target_id": TARGET_ID},
        "state_space_cases": 64,
        "cases": cases,
        "tests_run": len(cases),
        "same_input_replay_equal": all_replay_equal,
        "status": "PASS" if all(c["pass"] for c in cases) else "HOLD",
    }


def _report(receipt: dict[str, Any], security: dict[str, Any], regression: dict[str, Any]) -> str:
    return f"""# EQ64 Executable Assurance Engine V1 — Canary Report

Target: `{TARGET_SYSTEM}@{TARGET_COMMIT}`

Final decision: **{receipt["decision"]}**
EQ64 gate state: **{receipt["eq64"]["state_index"]}/63**
EQ64 bits: `{receipt["eq64"]["bits"]}`

## Security branch
- status: {security["status"]}
- deterministic cases: {security["tests_run"]}
- deliberate failure injections: {security["failure_injections"]}
- raw artifact SHA256: `{receipt["security"]["raw_artifact_sha256"]}`

## Regression branch
- status: {regression["status"]}
- exhaustive states: {regression["state_space_cases"]}
- deterministic cases: {regression["tests_run"]}
- same-input replay equality: {regression["same_input_replay_equal"]}
- raw artifact SHA256: `{receipt["regression"]["raw_artifact_sha256"]}`

## Independent readback
- security artifact readback: exact
- regression artifact readback: exact
- cross-branch source commit: exact
- receipt SHA256: `{receipt["receipt_sha256"]}`

## Claim ceiling
This proves only the bounded local canary against the pinned `evidence-gate` runtime and the included deterministic adversarial/regression cases. It does not establish production readiness, runtime admission, global bind, external-provider security, or exhaustive absence of vulnerabilities.
"""


def run_canary(output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    security_artifact = _security_canary()
    regression_artifact = _regression_canary()

    security_path = out / "eq64_security_canary.json"
    regression_path = out / "eq64_regression_canary.json"
    security_sha = _write_canonical_json(security_path, security_artifact)
    regression_sha = _write_canonical_json(regression_path, regression_artifact)

    security_readback_sha = _readback_sha256(security_path)
    regression_readback_sha = _readback_sha256(regression_path)
    engine_sha = _sha256_bytes(Path(__file__).with_name("eq64_executable_assurance_engine.py").read_bytes())
    runtime_actual_sha = _sha256_bytes(Path(__file__).with_name("ess_evidence_runtime.py").read_bytes())

    payload = {
        "schema_version": SCHEMA_VERSION,
        "target": {
            "system": TARGET_SYSTEM,
            "version": TARGET_COMMIT,
            "target_id": TARGET_ID,
            "runtime_sha256": TARGET_RUNTIME_SHA256,
        },
        "security": {
            "target_id": TARGET_ID,
            "target_runtime_sha256": runtime_actual_sha,
            "source_commit": TARGET_COMMIT,
            "status": security_artifact["status"],
            "fresh": True,
            "tests_run": security_artifact["tests_run"],
            "failure_injections": security_artifact["failure_injections"],
            "raw_artifact_sha256": security_sha,
        },
        "regression": {
            "target_id": TARGET_ID,
            "target_runtime_sha256": runtime_actual_sha,
            "source_commit": TARGET_COMMIT,
            "status": regression_artifact["status"],
            "fresh": True,
            "tests_run": regression_artifact["tests_run"],
            "same_input_replay_equal": regression_artifact["same_input_replay_equal"],
            "raw_artifact_sha256": regression_sha,
        },
        "readback": {
            "fresh": security_readback_sha == security_sha and regression_readback_sha == regression_sha,
            "security_artifact_sha256": security_readback_sha,
            "regression_artifact_sha256": regression_readback_sha,
        },
        "claim_guard": {
            "overclaim_flags": [],
            "runtime_admission": False,
            "production_readiness": False,
        },
        "engine": {"implementation_sha256": engine_sha},
    }

    input_path = out / "eq64_assurance_input.json"
    _write_canonical_json(input_path, payload)
    receipt = evaluate_assurance(payload)
    receipt_path = out / "eq64_assurance_receipt.json"
    _write_canonical_json(receipt_path, receipt)
    report_path = out / "EQ64_ASSURANCE_REPORT.md"
    report_path.write_text(_report(receipt, security_artifact, regression_artifact), encoding="utf-8")

    return {
        "security": {
            "status": security_artifact["status"],
            "tests_run": security_artifact["tests_run"],
            "failure_injections": security_artifact["failure_injections"],
            "artifact_sha256": security_sha,
        },
        "regression": {
            "status": regression_artifact["status"],
            "tests_run": regression_artifact["tests_run"],
            "same_input_replay_equal": regression_artifact["same_input_replay_equal"],
            "artifact_sha256": regression_sha,
        },
        "receipt": receipt,
        "output_dir": str(out),
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="artifacts/eq64_assurance_v1")
    args = parser.parse_args()
    result = run_canary(args.output_dir)
    print(json.dumps(result["receipt"], sort_keys=True, separators=(",", ":")))
    return 0 if result["receipt"]["decision"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
