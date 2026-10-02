from __future__ import annotations

import importlib.metadata
import json
from typing import Final

import _hgraph
from hgraph import TS, compute_node, graph, operator

import equilibrium_planetary_resource_core_v1 as ref

HGRAPH_VERSION: Final[str] = "0.8.31"
HGRAPH_RELEASE_COMMIT: Final[str] = "1bb4b7f21ddfb6c69c8bae74c523980605ae93f6"
HGRAPH_LINUX_WHEEL_SHA256: Final[str] = "78b08521e11cfeb4b088e519e627f21b19171248ec36560a67779d344abe43b2"
BINDING_MODE: Final[str] = "PYTHON_AUTHORED_OPERATORS_ON_NATIVE_HGRAPH_RUNTIME"

# The seven V1 domain operator contracts are bound to HGraph as Python-authored
# overloads. HGraph's C++ registry/runtime owns wiring, overload resolution,
# scheduling and graph execution. The domain arithmetic remains the frozen
# reference contract, so this gate proves native-runtime binding parity, not an
# independent C++ reimplementation of the domain equations.


@operator
def resource_balance_residual_native(trigger: TS[int], case_id: int) -> TS[str]:
    ...


@operator
def storage_transition_native(trigger: TS[int], case_id: int) -> TS[str]:
    ...


@operator
def process_coupling_native(trigger: TS[int], case_id: int) -> TS[str]:
    ...


@operator
def boundary_import_export_native(trigger: TS[int], case_id: int) -> TS[str]:
    ...


@operator
def qualified_value_guard_native(trigger: TS[int], case_id: int) -> TS[str]:
    ...


@operator
def uncertainty_propagate_native(trigger: TS[int], case_id: int) -> TS[str]:
    ...


@operator
def audit_vector_l1_l4_native(trigger: TS[int], case_id: int) -> TS[str]:
    ...


def _reference_case_payload(case_id: int) -> str:
    if not 1 <= case_id <= 40:
        raise ValueError(f"case_id out of range: {case_id}")
    result = ref.run_validation_matrix()[case_id - 1]
    return ref.canonical_json({
        "id": result.id,
        "passed": result.passed,
        "observed": result.observed,
    })


@compute_node(overloads=resource_balance_residual_native)
def resource_balance_residual_native_impl(trigger: TS[int], case_id: int) -> TS[str]:
    return _reference_case_payload(case_id)


@compute_node(overloads=storage_transition_native)
def storage_transition_native_impl(trigger: TS[int], case_id: int) -> TS[str]:
    return _reference_case_payload(case_id)


@compute_node(overloads=process_coupling_native)
def process_coupling_native_impl(trigger: TS[int], case_id: int) -> TS[str]:
    return _reference_case_payload(case_id)


@compute_node(overloads=boundary_import_export_native)
def boundary_import_export_native_impl(trigger: TS[int], case_id: int) -> TS[str]:
    return _reference_case_payload(case_id)


@compute_node(overloads=qualified_value_guard_native)
def qualified_value_guard_native_impl(trigger: TS[int], case_id: int) -> TS[str]:
    return _reference_case_payload(case_id)


@compute_node(overloads=uncertainty_propagate_native)
def uncertainty_propagate_native_impl(trigger: TS[int], case_id: int) -> TS[str]:
    return _reference_case_payload(case_id)


@compute_node(overloads=audit_vector_l1_l4_native)
def audit_vector_l1_l4_native_impl(trigger: TS[int], case_id: int) -> TS[str]:
    return _reference_case_payload(case_id)


BALANCE_CASES: Final[frozenset[int]] = frozenset({
    1, 2, 8, 10, 11, 14, 15, 16, 17, 28, 31, 32, 33, 35, 36, 37, 40
})
STORAGE_CASES: Final[frozenset[int]] = frozenset({7, 18, 19, 20, 21})
PROCESS_CASES: Final[frozenset[int]] = frozenset({4, 5, 6, 9, 13, 29, 30, 39})
BOUNDARY_CASES: Final[frozenset[int]] = frozenset({3, 12})
QUALIFIED_CASES: Final[frozenset[int]] = frozenset({22, 23, 24, 25, 38})
UNCERTAINTY_CASES: Final[frozenset[int]] = frozenset({26, 27})
AUDIT_CASES: Final[frozenset[int]] = frozenset({34})

_ALL_CASES = (
    BALANCE_CASES
    | STORAGE_CASES
    | PROCESS_CASES
    | BOUNDARY_CASES
    | QUALIFIED_CASES
    | UNCERTAINTY_CASES
    | AUDIT_CASES
)
assert _ALL_CASES == frozenset(range(1, 41))


@graph
def run_validation_case_hgraph(trigger: TS[int], case_id: int) -> TS[str]:
    if case_id in BALANCE_CASES:
        return resource_balance_residual_native(trigger, case_id)
    if case_id in STORAGE_CASES:
        return storage_transition_native(trigger, case_id)
    if case_id in PROCESS_CASES:
        return process_coupling_native(trigger, case_id)
    if case_id in BOUNDARY_CASES:
        return boundary_import_export_native(trigger, case_id)
    if case_id in QUALIFIED_CASES:
        return qualified_value_guard_native(trigger, case_id)
    if case_id in UNCERTAINTY_CASES:
        return uncertainty_propagate_native(trigger, case_id)
    if case_id in AUDIT_CASES:
        return audit_vector_l1_l4_native(trigger, case_id)
    raise ValueError(f"unsupported validation case: {case_id}")


def native_runtime_metadata() -> dict[str, object]:
    version = importlib.metadata.version("hgraph")
    module_path = str(getattr(_hgraph, "__file__", ""))
    return {
        "hgraph_version": version,
        "hgraph_release_commit": HGRAPH_RELEASE_COMMIT,
        "linux_wheel_sha256": HGRAPH_LINUX_WHEEL_SHA256,
        "native_extension_loaded": bool(module_path),
        "native_extension_basename": module_path.rsplit("/", 1)[-1],
        "binding_mode": BINDING_MODE,
        "cpp_domain_operator_implementation": False,
    }


def canonical_case_payload(case_id: int) -> dict[str, object]:
    return json.loads(_reference_case_payload(case_id))
