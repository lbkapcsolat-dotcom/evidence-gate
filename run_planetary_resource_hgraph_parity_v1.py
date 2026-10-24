from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hgraph.test import eval_node

import equilibrium_planetary_resource_core_v1 as ref
import planetary_resource_hgraph_bind_v1 as hg_bind

OUT = Path("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__HGRAPH_CROSS_PARITY_RECEIPT.json")

REFERENCE_SHA256 = "a2dafc38fac6c3077fc8972a0754bd216c4f8b4d83e4c2c8d33fca9b5f7c4aae"
TEST_SHA256 = "bf8240dc3c1e505dbefc9b46be1d767dfbc6bfe0f4eb82a5e9970201755cb483"
REFERENCE_RECEIPT_SHA256 = "6ddd143970f84d2a154cc637e1d3b862b67b957684be2b4b837b67e193808f98"


def sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> None:
    pins = {
        "reference_implementation": sha256_file("equilibrium_planetary_resource_core_v1.py"),
        "reference_test": sha256_file("test_equilibrium_planetary_resource_core_v1.py"),
        "reference_receipt": sha256_file("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__40_OF_40_RECEIPT.json"),
    }
    expected_pins = {
        "reference_implementation": REFERENCE_SHA256,
        "reference_test": TEST_SHA256,
        "reference_receipt": REFERENCE_RECEIPT_SHA256,
    }
    if pins != expected_pins:
        raise SystemExit(f"PIN_MISMATCH actual={pins} expected={expected_pins}")

    direct = ref.run_validation_matrix()
    if len(direct) != 40 or not all(r.passed for r in direct):
        raise SystemExit("REFERENCE_MATRIX_NOT_40_OF_40")

    parity_rows = []
    for i, expected_r in enumerate(direct, start=1):
        out = eval_node(hg_bind.run_validation_case_hgraph, [1], case_id=i)
        if len(out) != 1 or out[0] is None:
            raise SystemExit(f"V{i:02d}_HGRAPH_NO_OUTPUT: {out!r}")
        observed = json.loads(out[0])
        expected = {
            "id": expected_r.id,
            "passed": expected_r.passed,
            "observed": expected_r.observed,
        }
        equal = observed == expected
        parity_rows.append({
            "id": expected_r.id,
            "reference_passed": expected_r.passed,
            "hgraph_passed": bool(observed.get("passed")),
            "canonical_equal": equal,
        })
        if not equal or not observed.get("passed"):
            raise SystemExit(f"V{i:02d}_PARITY_FAIL expected={expected!r} observed={observed!r}")

    runtime = hg_bind.native_runtime_metadata()
    if runtime["hgraph_version"] != hg_bind.HGRAPH_VERSION:
        raise SystemExit("HGRAPH_VERSION_MISMATCH")
    if not runtime["native_extension_loaded"]:
        raise SystemExit("NATIVE_EXTENSION_NOT_LOADED")

    receipt = {
        "schema_version": "EQUILIBRIUM_PRS_HGRAPH_CROSS_PARITY_RECEIPT_V1",
        "gate_id": "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__NATIVE_HGRAPH_BIND_AND_CROSS_PARITY_V1",
        "reference_pins": pins,
        "hgraph_runtime": runtime,
        "reference_matrix": {"count": 40, "pass": 40},
        "hgraph_matrix": {"count": 40, "pass": 40},
        "cross_parity": {"count": 40, "equal": 40},
        "rows": parity_rows,
        "claim_ceiling": {
            "binding_scope": "PYTHON_AUTHORED_OPERATOR_BINDING_ON_NATIVE_HGRAPH_RUNTIME",
            "independent_domain_semantics": False,
            "cpp_domain_operator_implementation": False,
            "real_world_data_bind": False,
            "ui": False,
            "aggregate_eq_score": "HOLD_PROHIBITED",
            "runtime_admission": False,
            "pointer_promotion": False,
            "global_bind": False,
        },
        "verdict": "PASS_BOUNDED_NATIVE_HGRAPH_RUNTIME_BIND_40_OF_40_X2_CROSS_PARITY",
    }
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    OUT.write_text(canonical, encoding="utf-8")
    print(canonical, end="")
    print(f"RECEIPT_SHA256={hashlib.sha256(canonical.encode('utf-8')).hexdigest()}")


if __name__ == "__main__":
    main()
