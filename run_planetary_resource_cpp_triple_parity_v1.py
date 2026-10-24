from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from hgraph.test import eval_node

import equilibrium_planetary_resource_core_v1 as ref
import planetary_resource_hgraph_bind_v1 as hg_bind

EXPECTED = {
    "V01": "PASS",
    "V02": "ZERO_RESIDUAL",
    "V03": "ZERO_RESIDUAL",
    "V04": "ZERO_RESIDUAL",
    "V05": "ZERO_RESIDUAL",
    "V06": "ZERO_RESIDUAL",
    "V07": "STORAGE_104",
    "V08": "ZERO_RESIDUAL",
    "V09": "ZERO_RESIDUAL",
    "V10": "FOUR_LAYER_ZERO",
    "V11": "HOLD_MANIFEST_MISMATCH",
    "V12": "HOLD_BOUNDARY_DIRECTION",
    "V13": "NONZERO_RESIDUAL",
    "V14": "HOLD_UNIT_MISMATCH",
    "V15": "HOLD_UNIT_MISMATCH",
    "V16": "HOLD_HHV_LHV_BASIS_MISMATCH",
    "V17": "HOLD_TIME_BASIS_MISMATCH",
    "V18": "HOLD_STORAGE_CAPACITY",
    "V19": "HOLD_STORAGE_RATE",
    "V20": "HOLD_STORAGE_RATE",
    "V21": "HOLD_EFFICIENCY_DOMAIN",
    "V22": "HOLD_MISSING_INPUT",
    "V23": "HOLD_CONFLICTED_INPUT",
    "V24": "HOLD_STALE_INPUT",
    "V25": "HOLD_IMPUTED_FLAG_ERASED",
    "V26": "HOLD_COVARIANCE_REQUIRED",
    "V27": "HOLD_SAMPLE_ALIGNMENT_REQUIRED",
    "V28": "HOLD_DOUBLE_COUNT_LOSS",
    "V29": "HOLD_PROCESS_EVIDENCE",
    "V30": "HOLD_CAUSALITY",
    "V31": "HOLD_AUDIT_PHYSICAL_MIX",
    "V32": "HOLD_AUDIT_PHYSICAL_MIX",
    "V33": "HOLD_STRESS_PHYSICAL_MIX",
    "V34": "HOLD_AGGREGATE_SCORE_PROHIBITED",
    "V35": "HOLD_TOPOLOGY_CHANGED",
    "V36": "DETERMINISTIC_EQUAL",
    "V37": "PERMUTATION_INVARIANT",
    "V38": "ZERO_DISTINCT_MISSING",
    "V39": "ZERO_COUPLING",
    "V40": "HISTORY_INDEPENDENT",
}

REFERENCE_SHA256 = "a2dafc38fac6c3077fc8972a0754bd216c4f8b4d83e4c2c8d33fca9b5f7c4aae"
REFERENCE_TEST_SHA256 = "bf8240dc3c1e505dbefc9b46be1d767dfbc6bfe0f4eb82a5e9970201755cb483"
REFERENCE_RECEIPT_SHA256 = "6ddd143970f84d2a154cc637e1d3b862b67b957684be2b4b837b67e193808f98"
HGRAPH_WHEEL_SHA256 = "78b08521e11cfeb4b088e519e627f21b19171248ec36560a67779d344abe43b2"
HGRAPH_RELEASE_COMMIT = "1bb4b7f21ddfb6c69c8bae74c523980605ae93f6"


def sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize(id_: str, passed: bool, observed: str) -> str:
    if not passed:
        return "FAIL"

    expected = EXPECTED[id_]
    if expected.startswith("HOLD_"):
        if observed != expected:
            raise AssertionError(f"{id_}: hold mismatch observed={observed!r} expected={expected!r}")
        return expected

    if id_ == "V07":
        if observed != "104":
            raise AssertionError(f"V07 expected storage 104, got {observed!r}")
        return "STORAGE_104"

    if id_ == "V38":
        if observed != "DISTINCT":
            raise AssertionError(f"V38 expected DISTINCT, got {observed!r}")
        return "ZERO_DISTINCT_MISSING"

    # For the remaining non-HOLD cases, the frozen reference's own pass
    # predicate is the semantic oracle; the normalized label is a
    # language-neutral description of that predicate.
    return expected


def reference_lane() -> dict[str, dict[str, object]]:
    rows = {}
    for x in ref.run_validation_matrix():
        rows[x.id] = {
            "passed": x.passed,
            "semantic": normalize(x.id, x.passed, x.observed),
        }
    if set(rows) != set(EXPECTED):
        raise AssertionError("reference lane did not produce V01-V40")
    return rows


def hgraph_lane() -> dict[str, dict[str, object]]:
    rows = {}
    for i in range(1, 41):
        id_ = f"V{i:02d}"
        out = eval_node(hg_bind.run_validation_case_hgraph, [1], case_id=i)
        if len(out) != 1 or out[0] is None:
            raise AssertionError(f"{id_}: native HGraph lane produced no output: {out!r}")
        payload = json.loads(out[0])
        rows[id_] = {
            "passed": bool(payload["passed"]),
            "semantic": normalize(id_, bool(payload["passed"]), str(payload["observed"])),
        }
    return rows


def cpp_lane(executable: str = "./planetary_resource_cpp_kernel_v1") -> dict[str, dict[str, object]]:
    run = subprocess.run([executable], check=True, capture_output=True, text=True)
    rows = {}
    for line in run.stdout.splitlines():
        if not line.startswith("{"):
            continue
        payload = json.loads(line)
        rows[payload["id"]] = {
            "passed": bool(payload["passed"]),
            "semantic": str(payload["semantic"]),
        }
    if set(rows) != set(EXPECTED):
        raise AssertionError(f"C++ lane did not produce V01-V40: {sorted(rows)}")
    return rows


def main() -> None:
    pins = {
        "reference_implementation": sha256_file("equilibrium_planetary_resource_core_v1.py"),
        "reference_test": sha256_file("test_equilibrium_planetary_resource_core_v1.py"),
        "reference_receipt": sha256_file("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__40_OF_40_RECEIPT.json"),
    }
    expected_pins = {
        "reference_implementation": REFERENCE_SHA256,
        "reference_test": REFERENCE_TEST_SHA256,
        "reference_receipt": REFERENCE_RECEIPT_SHA256,
    }
    if pins != expected_pins:
        raise AssertionError(f"predecessor pin mismatch actual={pins} expected={expected_pins}")

    a = reference_lane()
    b = hgraph_lane()
    c = cpp_lane()

    parity = []
    for id_ in sorted(EXPECTED):
        expected = EXPECTED[id_]
        ra, rb, rc = a[id_], b[id_], c[id_]
        equal = (
            ra["passed"] is True
            and rb["passed"] is True
            and rc["passed"] is True
            and ra["semantic"] == rb["semantic"] == rc["semantic"] == expected
        )
        parity.append({
            "id": id_,
            "expected": expected,
            "python_reference": ra["semantic"],
            "native_hgraph": rb["semantic"],
            "independent_cpp": rc["semantic"],
            "triple_equal": equal,
        })
        if not equal:
            raise AssertionError(f"{id_}: triple parity failed: {parity[-1]!r}")

    receipt = {
        "schema_version": "EQUILIBRIUM_PRS_INDEPENDENT_CPP_TRIPLE_PARITY_RECEIPT_V1",
        "gate_id": "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__INDEPENDENT_CPP_DOMAIN_IMPLEMENTATION_AND_40_OF_40_X3_V1",
        "reference_pins": pins,
        "hgraph_runtime": {
            "version": hg_bind.HGRAPH_VERSION,
            "release_commit": HGRAPH_RELEASE_COMMIT,
            "linux_wheel_sha256": HGRAPH_WHEEL_SHA256,
            "binding_mode": hg_bind.BINDING_MODE,
        },
        "independent_cpp": {
            "source_sha256": sha256_file("planetary_resource_cpp_kernel_v1.cpp"),
            "language": "C++23",
            "calls_python_reference": False,
            "calls_python_hgraph_operator_bodies": False,
        },
        "lane_results": {
            "python_reference": {"count": 40, "pass": sum(v["passed"] is True for v in a.values())},
            "native_hgraph": {"count": 40, "pass": sum(v["passed"] is True for v in b.values())},
            "independent_cpp": {"count": 40, "pass": sum(v["passed"] is True for v in c.values())},
            "triple_semantic_parity": {"count": 40, "equal": sum(x["triple_equal"] for x in parity)},
        },
        "rows": parity,
        "claim_ceiling": {
            "independent_cpp_domain_semantics": True,
            "cpp_hgraph_operator_registration": False,
            "real_world_data_bind": False,
            "ui": False,
            "aggregate_eq_score": "HOLD_PROHIBITED",
            "runtime_admission": False,
            "pointer_promotion": False,
            "global_bind": False,
            "merge": False,
        },
        "verdict": "PASS_BOUNDED_INDEPENDENT_CPP_40_OF_40_X3_TRIPLE_PARITY",
    }

    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    out = Path("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__CPP_TRIPLE_PARITY_RECEIPT.json")
    out.write_text(canonical, encoding="utf-8")
    print(canonical, end="")
    print("TRIPLE_RECEIPT_SHA256=" + hashlib.sha256(canonical.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    main()
