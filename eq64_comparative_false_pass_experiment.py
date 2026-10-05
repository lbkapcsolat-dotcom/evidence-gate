from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Callable

from eq64_executable_assurance_engine import (
    SCHEMA_VERSION,
    canonical_bytes,
    evaluate_assurance,
    replay_assurance_receipt,
)

EXPERIMENT_SCHEMA = "EQ64_COMPARATIVE_FALSE_PASS_EXPERIMENT_V1"
MODEL_A = "A_NAIVE_UPSTREAM_PASS"
MODEL_B = "B_EQUAL_WEIGHT_THRESHOLD_0_80"
MODEL_C = "C_EQ64_NONCOMPENSATING"
SCORE_THRESHOLD = 0.80

TARGET_COMMIT = "e3c64f80be032dda6ac30cb38bbed1d41d2fa559"
TARGET_RUNTIME_SHA256 = "725fc590e074e3d3249bbf3e03b07623dc8f6ba7f162a6e2510649f91b80491b"
TARGET_ID = "equilibrium-stability-systems/claim_admission_kernel_v1@e3c64f80"
SECURITY_ARTIFACT_SHA256 = "3150647c97505c11075707d501ff8e3ed9eaf6e35d09b7e87db0e5267e1225ff"
REGRESSION_ARTIFACT_SHA256 = "a105416c3a5a3aba87f63a549337079affcec50ec54918d7e5093d4918aaab07"
ENGINE_SHA256 = "c" * 64


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _base_payload() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "target": {
            "system": "lbkapcsolat-dotcom/equilibrium-stability-systems",
            "version": TARGET_COMMIT,
            "target_id": TARGET_ID,
            "runtime_sha256": TARGET_RUNTIME_SHA256,
        },
        "security": {
            "target_id": TARGET_ID,
            "target_runtime_sha256": TARGET_RUNTIME_SHA256,
            "source_commit": TARGET_COMMIT,
            "status": "PASS",
            "fresh": True,
            "tests_run": 7,
            "failure_injections": 6,
            "raw_artifact_sha256": SECURITY_ARTIFACT_SHA256,
        },
        "regression": {
            "target_id": TARGET_ID,
            "target_runtime_sha256": TARGET_RUNTIME_SHA256,
            "source_commit": TARGET_COMMIT,
            "status": "PASS",
            "fresh": True,
            "tests_run": 22,
            "same_input_replay_equal": True,
            "raw_artifact_sha256": REGRESSION_ARTIFACT_SHA256,
        },
        "readback": {
            "fresh": True,
            "security_artifact_sha256": SECURITY_ARTIFACT_SHA256,
            "regression_artifact_sha256": REGRESSION_ARTIFACT_SHA256,
        },
        "claim_guard": {
            "overclaim_flags": [],
            "runtime_admission": False,
            "production_readiness": False,
        },
        "engine": {
            "implementation_sha256": ENGINE_SHA256,
            "experiment_source": "RUN_138_CROSS_REPO_BASELINE",
        },
    }


def _mutate(case_id: str, payload: dict[str, Any]) -> None:
    if case_id == "clean_control":
        return
    if case_id == "target_id_mismatch":
        payload["security"]["target_id"] = "different-target"
    elif case_id == "runtime_sha_mismatch":
        payload["regression"]["target_runtime_sha256"] = "d" * 64
    elif case_id == "security_status_hold":
        payload["security"]["status"] = "HOLD"
    elif case_id == "security_stale":
        payload["security"]["fresh"] = False
    elif case_id == "security_artifact_sha_invalid":
        payload["security"]["raw_artifact_sha256"] = "not-a-sha"
    elif case_id == "security_failure_injections_below_3":
        payload["security"]["failure_injections"] = 2
    elif case_id == "regression_status_hold":
        payload["regression"]["status"] = "HOLD"
    elif case_id == "regression_stale":
        payload["regression"]["fresh"] = False
    elif case_id == "regression_tests_below_10":
        payload["regression"]["tests_run"] = 9
    elif case_id == "replay_equality_false":
        payload["regression"]["same_input_replay_equal"] = False
    elif case_id == "readback_not_fresh":
        payload["readback"]["fresh"] = False
    elif case_id == "security_readback_hash_mismatch":
        payload["readback"]["security_artifact_sha256"] = "e" * 64
    elif case_id == "regression_readback_hash_mismatch":
        payload["readback"]["regression_artifact_sha256"] = "e" * 64
    elif case_id == "source_commit_mismatch":
        payload["regression"]["source_commit"] = "f" * 40
    elif case_id == "overclaim_flag":
        payload["claim_guard"]["overclaim_flags"] = ["GLOBAL_BIND"]
    elif case_id == "runtime_admission_true":
        payload["claim_guard"]["runtime_admission"] = True
    elif case_id == "production_readiness_true":
        payload["claim_guard"]["production_readiness"] = True
    elif case_id == "compound_identity_and_readback":
        payload["security"]["target_id"] = "different-target"
        payload["readback"]["security_artifact_sha256"] = "e" * 64
    elif case_id == "compound_security_and_claim":
        payload["security"]["status"] = "HOLD"
        payload["claim_guard"]["overclaim_flags"] = ["PRODUCTION_READY"]
    elif case_id == "compound_regression_and_commit":
        payload["regression"]["status"] = "HOLD"
        payload["regression"]["source_commit"] = "f" * 40
    else:
        raise ValueError(f"unknown case_id: {case_id}")


CASE_SPECS = [
    ("clean_control", [], "PASS"),
    ("target_id_mismatch", [0], "HOLD"),
    ("runtime_sha_mismatch", [0], "HOLD"),
    ("security_status_hold", [1], "HOLD"),
    ("security_stale", [1], "HOLD"),
    ("security_artifact_sha_invalid", [1], "HOLD"),
    ("security_failure_injections_below_3", [1], "HOLD"),
    ("regression_status_hold", [2], "HOLD"),
    ("regression_stale", [2], "HOLD"),
    ("regression_tests_below_10", [2], "HOLD"),
    ("replay_equality_false", [2], "HOLD"),
    ("readback_not_fresh", [3], "HOLD"),
    ("security_readback_hash_mismatch", [3], "HOLD"),
    ("regression_readback_hash_mismatch", [3], "HOLD"),
    ("source_commit_mismatch", [4], "HOLD"),
    ("overclaim_flag", [5], "HOLD"),
    ("runtime_admission_true", [5], "HOLD"),
    ("production_readiness_true", [5], "HOLD"),
    ("compound_identity_and_readback", [0, 3], "HOLD"),
    ("compound_security_and_claim", [1, 5], "HOLD"),
    ("compound_regression_and_commit", [2, 4], "HOLD"),
]


def _naive_upstream_pass(payload: dict[str, Any]) -> str:
    return (
        "PASS"
        if payload["security"].get("status") == "PASS"
        and payload["regression"].get("status") == "PASS"
        else "HOLD"
    )


def _score_threshold(failed_gates: list[int]) -> tuple[str, float]:
    passed = 6 - len(set(failed_gates))
    score = passed / 6.0
    return ("PASS" if score >= SCORE_THRESHOLD else "HOLD"), score


def _model_metrics(
    decisions: list[str],
    expected: list[str],
    repeated: list[str],
    *,
    receipt_replay_deterministic: bool | None,
) -> dict[str, Any]:
    fault_indexes = [i for i, value in enumerate(expected) if value == "HOLD"]
    clean_indexes = [i for i, value in enumerate(expected) if value == "PASS"]

    false_pass_count = sum(decisions[i] == "PASS" for i in fault_indexes)
    false_hold_count = sum(decisions[i] == "HOLD" for i in clean_indexes)
    fault_detection_count = sum(decisions[i] == "HOLD" for i in fault_indexes)

    return {
        "false_pass_count": false_pass_count,
        "false_pass_rate": false_pass_count / len(fault_indexes),
        "false_hold_count": false_hold_count,
        "false_hold_rate": false_hold_count / len(clean_indexes),
        "fault_detection_count": fault_detection_count,
        "fault_detection_coverage": fault_detection_count / len(fault_indexes),
        "decision_reproducible": decisions == repeated,
        "receipt_replay_deterministic": receipt_replay_deterministic,
    }


def run_experiment() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    expected: list[str] = []
    decisions_a: list[str] = []
    decisions_b: list[str] = []
    decisions_c: list[str] = []
    repeat_a: list[str] = []
    repeat_b: list[str] = []
    repeat_c: list[str] = []
    c_replay_ok = True

    for case_id, failed_gates, oracle in CASE_SPECS:
        payload = _base_payload()
        _mutate(case_id, payload)

        a = _naive_upstream_pass(payload)
        a_repeat = _naive_upstream_pass(copy.deepcopy(payload))

        b, score = _score_threshold(failed_gates)
        b_repeat, score_repeat = _score_threshold(list(failed_gates))

        c_receipt = evaluate_assurance(payload)
        c_repeat_receipt = evaluate_assurance(copy.deepcopy(payload))
        c = c_receipt["decision"]
        c_repeat = c_repeat_receipt["decision"]
        replay = replay_assurance_receipt(c_receipt)
        c_case_replay_ok = (
            replay["valid"]
            and c_receipt["receipt_sha256"] == c_repeat_receipt["receipt_sha256"]
            and c_receipt["evidence_bundle_sha256"] == c_repeat_receipt["evidence_bundle_sha256"]
        )
        c_replay_ok = c_replay_ok and c_case_replay_ok

        cases.append(
            {
                "case_id": case_id,
                "oracle_decision": oracle,
                "failed_gates": failed_gates,
                "score_baseline": score,
                "decisions": {
                    MODEL_A: a,
                    MODEL_B: b,
                    MODEL_C: c,
                },
                "eq64_state_index": c_receipt["eq64"]["state_index"],
                "eq64_bits": c_receipt["eq64"]["bits"],
                "eq64_reasons": c_receipt["reasons"],
                "eq64_receipt_sha256": c_receipt["receipt_sha256"],
                "eq64_replay_valid": replay["valid"],
            }
        )

        expected.append(oracle)
        decisions_a.append(a)
        decisions_b.append(b)
        decisions_c.append(c)
        repeat_a.append(a_repeat)
        repeat_b.append(b_repeat)
        repeat_c.append(c_repeat)

        if score != score_repeat:
            raise AssertionError("score baseline is not deterministic")

    metrics = {
        MODEL_A: _model_metrics(
            decisions_a,
            expected,
            repeat_a,
            receipt_replay_deterministic=None,
        ),
        MODEL_B: _model_metrics(
            decisions_b,
            expected,
            repeat_b,
            receipt_replay_deterministic=None,
        ),
        MODEL_C: _model_metrics(
            decisions_c,
            expected,
            repeat_c,
            receipt_replay_deterministic=c_replay_ok,
        ),
    }

    result: dict[str, Any] = {
        "schema_version": EXPERIMENT_SCHEMA,
        "experiment_design": {
            "oracle": "CLEAN_PASS__ANY_PRECOMMITTED_CRITICAL_FAULT_HOLD",
            "model_a": "PASS iff upstream security.status and regression.status are PASS",
            "model_b": {
                "kind": "equal_weight_arithmetic_gate_score",
                "threshold": SCORE_THRESHOLD,
                "rule": "PASS iff passed_gate_fraction >= 0.80",
            },
            "model_c": "EQ64 six-gate non-compensating admission; PASS only state 63",
            "target_baseline": {
                "system": "lbkapcsolat-dotcom/equilibrium-stability-systems",
                "commit": TARGET_COMMIT,
                "runtime_sha256": TARGET_RUNTIME_SHA256,
                "source_run": 138,
            },
        },
        "case_count": len(CASE_SPECS),
        "fault_case_count": sum(oracle == "HOLD" for _, _, oracle in CASE_SPECS),
        "clean_case_count": sum(oracle == "PASS" for _, _, oracle in CASE_SPECS),
        "cases": cases,
        "metrics": metrics,
        "claim_ceiling": {
            "bounded_comparative_experiment": True,
            "industry_baseline_representativeness": False,
            "statistical_generalization": False,
            "production_readiness": False,
            "runtime_admission": False,
            "global_bind": False,
        },
    }
    result["experiment_sha256"] = _sha256_json(result)
    return result


def write_outputs(output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = run_experiment()

    json_path = out / "eq64_comparative_false_pass_experiment.json"
    json_path.write_bytes(canonical_bytes(result))

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer, lineterminator="\n")
    writer.writerow(
        [
            "case_id",
            "oracle_decision",
            "failed_gates",
            "score_baseline",
            MODEL_A,
            MODEL_B,
            MODEL_C,
            "eq64_state_index",
            "eq64_receipt_sha256",
        ]
    )
    for case in result["cases"]:
        writer.writerow(
            [
                case["case_id"],
                case["oracle_decision"],
                ",".join(str(x) for x in case["failed_gates"]),
                f'{case["score_baseline"]:.6f}',
                case["decisions"][MODEL_A],
                case["decisions"][MODEL_B],
                case["decisions"][MODEL_C],
                case["eq64_state_index"],
                case["eq64_receipt_sha256"],
            ]
        )
    (out / "eq64_comparative_false_pass_matrix.csv").write_text(
        csv_buffer.getvalue(),
        encoding="utf-8",
    )

    m = result["metrics"]
    report = f"""# EQ64 Comparative False-PASS Experiment V1

Precommitted matrix: {result["case_count"]} cases
- clean controls: {result["clean_case_count"]}
- critical fault cases: {result["fault_case_count"]}

## Results

| Model | False-PASS | False-PASS rate | False-HOLD | Fault detection |
|---|---:|---:|---:|---:|
| Naive upstream PASS | {m[MODEL_A]["false_pass_count"]} | {m[MODEL_A]["false_pass_rate"]:.1%} | {m[MODEL_A]["false_hold_count"]} | {m[MODEL_A]["fault_detection_coverage"]:.1%} |
| Equal-weight threshold 0.80 | {m[MODEL_B]["false_pass_count"]} | {m[MODEL_B]["false_pass_rate"]:.1%} | {m[MODEL_B]["false_hold_count"]} | {m[MODEL_B]["fault_detection_coverage"]:.1%} |
| EQ64 non-compensating | {m[MODEL_C]["false_pass_count"]} | {m[MODEL_C]["false_pass_rate"]:.1%} | {m[MODEL_C]["false_hold_count"]} | {m[MODEL_C]["fault_detection_coverage"]:.1%} |

EQ64 decision reproducibility: {m[MODEL_C]["decision_reproducible"]}
EQ64 receipt replay deterministic: {m[MODEL_C]["receipt_replay_deterministic"]}
Experiment SHA256: {result["experiment_sha256"]}

## Interpretation boundary

This is a bounded, precommitted fault-injection comparison over one frozen 21-case matrix. The naive and threshold models are explicit illustrative baselines, not claims about all deployed assurance products. The experiment does not establish statistical generalization, production readiness, runtime admission, certification, or universal superiority.
"""
    (out / "EQ64_COMPARATIVE_FALSE_PASS_REPORT.md").write_text(report, encoding="utf-8")
    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="artifacts/eq64_comparative_v1")
    args = parser.parse_args()
    result = write_outputs(args.output_dir)
    print(json.dumps(result["metrics"], sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
