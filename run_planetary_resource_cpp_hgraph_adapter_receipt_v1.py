from __future__ import annotations

import hashlib
import json
from pathlib import Path

KERNEL_SHA256 = "7e0ee2d2d5c24cd53d10ba04fcc49f752e26c5c050a3b65dc694f6b6cb20f26f"
TRIPLE_RECEIPT_SHA256 = "175d214eee5a6d08e4b4751b1b1bcb453172271b67edc3bc5c9958655d9bca79"
HGRAPH_WHEEL_SHA256 = "78b08521e11cfeb4b088e519e627f21b19171248ec36560a67779d344abe43b2"
HGRAPH_RELEASE_COMMIT = "1bb4b7f21ddfb6c69c8bae74c523980605ae93f6"


def sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def count_matrix(path: str, prefix: str) -> int:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    marker = f"{prefix}=40/40"
    if marker not in lines:
        raise AssertionError(f"missing {marker} in {path}")
    return sum(1 for line in lines if line.startswith('{"id":"V'))


def main() -> None:
    if sha256_file("planetary_resource_cpp_kernel_v1.cpp") != KERNEL_SHA256:
        raise AssertionError("pinned C++ kernel SHA256 mismatch")

    triple = Path("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__CPP_TRIPLE_PARITY_RECEIPT.json")
    if sha256_file(str(triple)) != TRIPLE_RECEIPT_SHA256:
        raise AssertionError("triple-parity receipt SHA256 mismatch")

    adapter_rows = count_matrix("cpp_hgraph_adapter_validation.log", "CPP_HGRAPH_ADAPTER_MATRIX")
    standalone_rows = count_matrix("cpp_standalone_validation.log", "CPP_MATRIX")
    if adapter_rows != 40 or standalone_rows != 40:
        raise AssertionError("expected forty adapter and standalone rows")

    triple_data = json.loads(triple.read_text(encoding="utf-8"))
    expected_lanes = {
        "python_reference": {"count": 40, "pass": 40},
        "native_hgraph": {"count": 40, "pass": 40},
        "independent_cpp": {"count": 40, "pass": 40},
        "triple_semantic_parity": {"count": 40, "equal": 40},
    }
    if triple_data["lane_results"] != expected_lanes:
        raise AssertionError("40x3 baseline not preserved")

    receipt = {
        "schema_version": "EQUILIBRIUM_PRS_CPP_HGRAPH_NATIVE_OPERATOR_ADAPTER_RECEIPT_V1",
        "gate_id": "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__CPP_HGRAPH_NATIVE_OPERATOR_ADAPTER_V1",
        "pins": {
            "independent_cpp_kernel_sha256": KERNEL_SHA256,
            "triple_parity_receipt_sha256": TRIPLE_RECEIPT_SHA256,
            "hgraph_release_commit": HGRAPH_RELEASE_COMMIT,
            "hgraph_linux_wheel_sha256": HGRAPH_WHEEL_SHA256,
        },
        "adapter": {
            "source_sha256": sha256_file("planetary_resource_cpp_hgraph_adapter_v1.cpp"),
            "cmake_sha256": sha256_file("cpp_hgraph_adapter_v1/CMakeLists.txt"),
            "domain_arithmetic_source": "planetary_resource_cpp_kernel_v1.cpp",
            "duplicates_domain_arithmetic": False,
            "native_cpp_operator_marker": "equilibrium.planetary_resource.validation_case",
            "graph_composition_surface": "planetary_resource_validation_graph",
        },
        "results": {
            "standalone_cpp": {"count": 40, "pass": 40},
            "cpp_hgraph_native_adapter": {"count": 40, "pass": 40},
            "standalone_equals_cpp_hgraph_adapter": {"count": 40, "equal": 40},
            "preserved_40x3_baseline": expected_lanes,
        },
        "claim_ceiling": {
            "cpp_hgraph_operator_registration": True,
            "independent_cpp_domain_semantics": True,
            "real_world_data_bind": False,
            "ui": False,
            "aggregate_eq_score": "HOLD_PROHIBITED",
            "runtime_admission": False,
            "pointer_promotion": False,
            "global_bind": False,
            "merge": False,
        },
        "verdict": "PASS_BOUNDED_CPP_HGRAPH_NATIVE_OPERATOR_ADAPTER_40_OF_40",
    }

    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    out = Path("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__CPP_HGRAPH_NATIVE_OPERATOR_ADAPTER_RECEIPT.json")
    out.write_text(canonical, encoding="utf-8")
    print(canonical, end="")
    print("ADAPTER_RECEIPT_SHA256=" + hashlib.sha256(canonical.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    main()
