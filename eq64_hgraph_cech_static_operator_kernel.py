from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from math import comb
from typing import Callable, Mapping

KERNEL_ID = "EQ64__HGRAPH_CECH_STATIC_OPERATOR_KERNEL_V1"
PREDECESSOR_ID = "EQ64__Q6_Q3_CECH_ALL_HIGHER_EXACTNESS_AND_CONTRACTING_HOMOTOPY_V1"

COEFFICIENT_SYSTEM = "FUNCTION_SHEAF_R"
LOCAL_VERTEX_COUNT = 20
GLOBAL_COMPONENT_COUNT = 64
VERTICES = tuple(range(1, LOCAL_VERTEX_COUNT + 1))
APEX_VERTEX = 1
ORIENTATION = "CANONICAL_ASCENDING_VERTEX_ORDER_1_TO_20"
MIN_DEGREE = 0
MAX_DEGREE = LOCAL_VERTEX_COUNT - 1

Scalar = int | Fraction
Simplex = tuple[int, ...]
LocalCochain = dict[Simplex, Fraction]
GlobalKey = tuple[int, Simplex]
GlobalCochain = dict[GlobalKey, Fraction]


def _q(value: Scalar) -> Fraction:
    return value if isinstance(value, Fraction) else Fraction(value)


def validate_degree(p: int) -> None:
    if not isinstance(p, int) or not MIN_DEGREE <= p <= MAX_DEGREE:
        raise ValueError(f"degree must be in {MIN_DEGREE}..{MAX_DEGREE}")


def validate_simplex(simplex: Simplex, *, expected_size: int | None = None) -> None:
    if not isinstance(simplex, tuple):
        raise ValueError("simplex must be a tuple")
    if expected_size is not None and len(simplex) != expected_size:
        raise ValueError(f"simplex size must be {expected_size}")
    if any(v not in VERTICES for v in simplex):
        raise ValueError("simplex vertex outside frozen domain 1..20")
    if tuple(sorted(simplex)) != simplex or len(set(simplex)) != len(simplex):
        raise ValueError("simplex must use strictly increasing frozen orientation")


def simplices(p: int) -> tuple[Simplex, ...]:
    validate_degree(p)
    return tuple(combinations(VERTICES, p + 1))


def local_dimension(p: int) -> int:
    validate_degree(p)
    return comb(LOCAL_VERTEX_COUNT, p + 1)


def global_dimension(p: int) -> int:
    return GLOBAL_COMPONENT_COUNT * local_dimension(p)


def expected_delta_rank(p: int) -> int:
    validate_degree(p)
    if p == MAX_DEGREE:
        return 0
    return comb(LOCAL_VERTEX_COUNT - 1, p + 1)


def expected_local_cohomology_dimension(p: int) -> int:
    validate_degree(p)
    return 1 if p == 0 else 0


def expected_global_cohomology_dimension(p: int) -> int:
    return GLOBAL_COMPONENT_COUNT * expected_local_cohomology_dimension(p)


def normalize_local(cochain: Mapping[Simplex, Scalar], p: int) -> LocalCochain:
    validate_degree(p)
    out: LocalCochain = {}
    for simplex, value in cochain.items():
        validate_simplex(simplex, expected_size=p + 1)
        q = _q(value)
        if q:
            out[simplex] = q
    return out


def basis_cochain(p: int, simplex: Simplex, value: Scalar = 1) -> LocalCochain:
    validate_simplex(simplex, expected_size=p + 1)
    q = _q(value)
    return {} if q == 0 else {simplex: q}


def add_local(*cochains: Mapping[Simplex, Scalar]) -> LocalCochain:
    out: LocalCochain = {}
    for cochain in cochains:
        for simplex, value in cochain.items():
            q = out.get(simplex, Fraction(0)) + _q(value)
            if q:
                out[simplex] = q
            elif simplex in out:
                del out[simplex]
    return out


def scale_local(cochain: Mapping[Simplex, Scalar], scalar: Scalar) -> LocalCochain:
    factor = _q(scalar)
    if factor == 0:
        return {}
    out: LocalCochain = {}
    for simplex, value in cochain.items():
        q = _q(value) * factor
        if q:
            out[simplex] = q
    return out


def delta_local(p: int, cochain: Mapping[Simplex, Scalar]) -> LocalCochain:
    """Pure Čech coboundary δ_p with ascending orientation.

    Sparse implementation: each source p-simplex contributes only to
    (p+1)-simplices obtained by inserting one missing frozen vertex.
    """
    validate_degree(p)
    normalized = normalize_local(cochain, p)
    if p == MAX_DEGREE:
        return {}
    out: LocalCochain = {}
    vertex_set = set(VERTICES)
    for face, value in normalized.items():
        missing = vertex_set.difference(face)
        for vertex in missing:
            target = tuple(sorted(face + (vertex,)))
            j = target.index(vertex)
            contribution = value if j % 2 == 0 else -value
            total = out.get(target, Fraction(0)) + contribution
            if total:
                out[target] = total
            elif target in out:
                del out[target]
    return out


def homotopy_local(p: int, cochain: Mapping[Simplex, Scalar]) -> LocalCochain:
    """Apex contraction h_p: C^p -> C^(p-1), p>=1."""
    validate_degree(p)
    if p == 0:
        raise ValueError("h_0 is not part of the frozen kernel")
    normalized = normalize_local(cochain, p)
    out: LocalCochain = {}
    for source, value in normalized.items():
        if source and source[0] == APEX_VERTEX:
            target = source[1:]
            if value:
                out[target] = value
    return out


def projection0_local(cochain: Mapping[Simplex, Scalar]) -> LocalCochain:
    """Π_0 = iota∘epsilon, constant cochain with apex value."""
    normalized = normalize_local(cochain, 0)
    value = normalized.get((APEX_VERTEX,), Fraction(0))
    if value == 0:
        return {}
    return {(v,): value for v in VERTICES}


def identity_local(p: int, cochain: Mapping[Simplex, Scalar]) -> LocalCochain:
    return normalize_local(cochain, p)


ApplyFn = Callable[[Mapping[Simplex, Scalar]], LocalCochain]


@dataclass(frozen=True)
class LinearOperator:
    name: str
    source_degree: int
    target_degree: int
    apply_fn: ApplyFn

    def __call__(self, cochain: Mapping[Simplex, Scalar]) -> LocalCochain:
        return self.apply_fn(cochain)


def delta_operator(p: int) -> LinearOperator:
    validate_degree(p)
    if p == MAX_DEGREE:
        return LinearOperator("delta_19", p, p + 1, lambda c: {})
    return LinearOperator(f"delta_{p}", p, p + 1, lambda c: delta_local(p, c))


def homotopy_operator(p: int) -> LinearOperator:
    validate_degree(p)
    if p == 0:
        raise ValueError("h_0 is not part of the frozen kernel")
    return LinearOperator(f"h_{p}", p, p - 1, lambda c: homotopy_local(p, c))


def projection0_operator() -> LinearOperator:
    return LinearOperator("Pi_0", 0, 0, projection0_local)


def identity_operator(p: int) -> LinearOperator:
    validate_degree(p)
    return LinearOperator(f"I_{p}", p, p, lambda c: identity_local(p, c))


def compose(left: LinearOperator, right: LinearOperator) -> LinearOperator:
    """Return left∘right, rejecting graph-degree mismatches."""
    if right.target_degree != left.source_degree:
        raise ValueError(
            f"operator degree mismatch: {left.name}∘{right.name}: "
            f"{right.target_degree}!={left.source_degree}"
        )
    return LinearOperator(
        name=f"({left.name}∘{right.name})",
        source_degree=right.source_degree,
        target_degree=left.target_degree,
        apply_fn=lambda c: left(right(c)),
    )


def add_operators(*operators: LinearOperator) -> LinearOperator:
    if not operators:
        raise ValueError("at least one operator is required")
    source = operators[0].source_degree
    target = operators[0].target_degree
    if any(op.source_degree != source or op.target_degree != target for op in operators):
        raise ValueError("operator sum requires identical source and target degrees")
    return LinearOperator(
        name="(" + "+".join(op.name for op in operators) + ")",
        source_degree=source,
        target_degree=target,
        apply_fn=lambda c: add_local(*(op(c) for op in operators)),
    )


def subtract_operators(left: LinearOperator, right: LinearOperator) -> LinearOperator:
    if left.source_degree != right.source_degree or left.target_degree != right.target_degree:
        raise ValueError("operator subtraction requires identical source and target degrees")
    return LinearOperator(
        name=f"({left.name}-{right.name})",
        source_degree=left.source_degree,
        target_degree=left.target_degree,
        apply_fn=lambda c: add_local(left(c), scale_local(right(c), -1)),
    )


def contraction_operator(p: int) -> LinearOperator:
    """δh+hδ on positive degrees."""
    validate_degree(p)
    if p == 0:
        raise ValueError("positive degree required")
    left = compose(delta_operator(p - 1), homotopy_operator(p))
    if p == MAX_DEGREE:
        right = LinearOperator("zero_top", p, p, lambda c: {})
    else:
        right = compose(homotopy_operator(p + 1), delta_operator(p))
    return add_operators(left, right)


def degree0_reduced_identity_operator() -> LinearOperator:
    """I_0 - Π_0, equal to h_1 δ_0."""
    return subtract_operators(identity_operator(0), projection0_operator())


def degree0_homotopy_operator() -> LinearOperator:
    return compose(homotopy_operator(1), delta_operator(0))


def apply_global_componentwise(
    p: int,
    cochain: Mapping[GlobalKey, Scalar],
    operator: LinearOperator,
) -> GlobalCochain:
    validate_degree(p)
    if operator.source_degree != p:
        raise ValueError("global operator source degree mismatch")
    by_component: dict[int, LocalCochain] = {}
    for (component, simplex), value in cochain.items():
        if not 0 <= component < GLOBAL_COMPONENT_COUNT:
            raise ValueError("component must be in 0..63")
        validate_simplex(simplex, expected_size=p + 1)
        by_component.setdefault(component, {})[simplex] = _q(value)
    out: GlobalCochain = {}
    for component, local in by_component.items():
        for simplex, value in operator(local).items():
            if value:
                out[(component, simplex)] = value
    return out


def deterministic_probe(p: int, seed: int = 0) -> LocalCochain:
    """Deterministic sparse exact probe, no randomness and no floats."""
    validate_degree(p)
    all_simplices = simplices(p)
    if not all_simplices:
        return {}
    indices = {
        0,
        len(all_simplices) // 4,
        len(all_simplices) // 2,
        (3 * len(all_simplices)) // 4,
        len(all_simplices) - 1,
    }
    out: LocalCochain = {}
    for k, idx in enumerate(sorted(indices)):
        numerator = ((idx + 1) * (seed + 3) + (k + 1) * 5) % 17 - 8
        if numerator == 0:
            numerator = k + 1
        out[all_simplices[idx]] = Fraction(numerator, (k % 3) + 1)
    return out


def kernel_metadata() -> dict[str, object]:
    return {
        "kernel_id": KERNEL_ID,
        "predecessor_id": PREDECESSOR_ID,
        "coefficient_system": COEFFICIENT_SYSTEM,
        "local_vertex_count": LOCAL_VERTEX_COUNT,
        "global_component_count": GLOBAL_COMPONENT_COUNT,
        "vertex_order": list(VERTICES),
        "apex_vertex": APEX_VERTEX,
        "orientation": ORIENTATION,
        "cech_degrees": [MIN_DEGREE, MAX_DEGREE],
        "operator_set": ["delta", "h", "Pi"],
        "graph_composition_first": True,
        "state_lifecycle_logic": False,
        "dynamic_topology": False,
        "runtime_admission": False,
        "global_bind": False,
        "zero_spend": True,
    }
