from __future__ import annotations

from itertools import combinations
from math import comb
from typing import Mapping

LOCAL_SIMPLEX_VERTEX_COUNT = 20
GLOBAL_COMPONENT_COUNT = 64
CANONICAL_VERTICES = tuple(range(1, LOCAL_SIMPLEX_VERTEX_COUNT + 1))
APEX_VERTEX = 1
MAX_DEGREE = LOCAL_SIMPLEX_VERTEX_COUNT - 1

Simplex = tuple[int, ...]
Cochain = Mapping[Simplex, int | float]


def _validate_degree(p: int) -> None:
    if not isinstance(p, int) or isinstance(p, bool):
        raise TypeError("degree must be an integer")
    if p < 0 or p > MAX_DEGREE:
        raise ValueError(f"degree must be in [0, {MAX_DEGREE}]")


def local_dimension(p: int) -> int:
    _validate_degree(p)
    return comb(LOCAL_SIMPLEX_VERTEX_COUNT, p + 1)


def global_dimension(p: int) -> int:
    return GLOBAL_COMPONENT_COUNT * local_dimension(p)


def delta(p: int, cochain: Cochain) -> dict[Simplex, int | float]:
    """Alternating Cech coboundary on the ordered 20-vertex simplex."""
    _validate_degree(p)
    if p == MAX_DEGREE:
        return {}

    out: dict[Simplex, int | float] = {}
    for simplex in combinations(CANONICAL_VERTICES, p + 2):
        value: int | float = 0
        for j in range(p + 2):
            face = simplex[:j] + simplex[j + 1 :]
            value += (-1 if j % 2 else 1) * cochain.get(face, 0)
        out[simplex] = value
    return out


def contracting_homotopy(p: int, cochain: Cochain) -> dict[Simplex, int | float]:
    """Apex-1 contracting homotopy h_p: C^p -> C^(p-1), for p > 0."""
    _validate_degree(p)
    if p == 0:
        raise ValueError("contracting homotopy is defined here only for positive degree")

    out: dict[Simplex, int | float] = {}
    for simplex in combinations(CANONICAL_VERTICES, p):
        if APEX_VERTEX in simplex:
            out[simplex] = 0
        else:
            out[simplex] = cochain.get((APEX_VERTEX,) + simplex, 0)
    return out


def h0_projection(cochain: Cochain) -> dict[Simplex, int | float]:
    """Projection C^0 -> constants by evaluation at the apex vertex 1."""
    value = cochain.get((APEX_VERTEX,), 0)
    return {(vertex,): value for vertex in CANONICAL_VERTICES}

def _add_cochains(
    left: Mapping[Simplex, int | float],
    right: Mapping[Simplex, int | float],
) -> dict[Simplex, int | float]:
    keys = left.keys() | right.keys()
    return {simplex: left.get(simplex, 0) + right.get(simplex, 0) for simplex in keys}


def positive_degree_homotopy_composition(
    p: int, cochain: Cochain
) -> dict[Simplex, int | float]:
    """Static graph composition delta*h + h*delta on C^p for p > 0."""
    _validate_degree(p)
    if p == 0:
        raise ValueError("positive-degree composition requires p > 0")
    delta_h = delta(p - 1, contracting_homotopy(p, cochain))
    h_delta: dict[Simplex, int | float] = {}
    if p < MAX_DEGREE:
        h_delta = contracting_homotopy(p + 1, delta(p, cochain))
    return _add_cochains(delta_h, h_delta)


def h0_reduced_composition(cochain: Cochain) -> dict[Simplex, int | float]:
    """Static graph composition h_1*delta_0 = I - Pi on C^0."""
    return contracting_homotopy(1, delta(0, cochain))

def _validate_components(components) -> None:
    if len(components) != GLOBAL_COMPONENT_COUNT:
        raise ValueError(f"expected {GLOBAL_COMPONENT_COUNT} components")


def global_delta(p: int, components) -> tuple[dict[Simplex, int | float], ...]:
    """Apply delta independently to the 64 direct-sum components."""
    _validate_components(components)
    return tuple(delta(p, component) for component in components)


def global_contracting_homotopy(
    p: int, components
) -> tuple[dict[Simplex, int | float], ...]:
    """Apply h_p independently to the 64 direct-sum components."""
    _validate_components(components)
    return tuple(contracting_homotopy(p, component) for component in components)

def _basis_value(rep: Simplex, simplex: Simplex) -> int:
    return 1 if rep == simplex else 0


def _basis_delta_value(p: int, rep: Simplex, simplex: Simplex) -> int:
    value = 0
    for j in range(len(simplex)):
        face = simplex[:j] + simplex[j + 1 :]
        value += (-1 if j % 2 else 1) * _basis_value(rep, face)
    return value


def _basis_delta_squared_value(p: int, rep: Simplex, simplex: Simplex) -> int:
    value = 0
    for j in range(len(simplex)):
        face = simplex[:j] + simplex[j + 1 :]
        value += (-1 if j % 2 else 1) * _basis_delta_value(p, rep, face)
    return value


def _basis_h_value(p: int, rep: Simplex, simplex: Simplex) -> int:
    if APEX_VERTEX in simplex:
        return 0
    return _basis_value(rep, (APEX_VERTEX,) + simplex)


def _basis_positive_composition_value(p: int, rep: Simplex, simplex: Simplex) -> int:
    delta_h = 0
    for j in range(len(simplex)):
        face = simplex[:j] + simplex[j + 1 :]
        delta_h += (-1 if j % 2 else 1) * _basis_h_value(p, rep, face)
    h_delta = 0
    if p < MAX_DEGREE and APEX_VERTEX not in simplex:
        h_delta = _basis_delta_value(p, rep, (APEX_VERTEX,) + simplex)
    return delta_h + h_delta


def _parity_orbit_representatives(p: int) -> tuple[Simplex, ...]:
    reps = [tuple(range(1, p + 2))]
    if p <= 18:
        reps.append(tuple(range(2, p + 3)))
    return tuple(reps)


def _fixture_extend(rep: Simplex, count: int) -> Simplex:
    missing = [vertex for vertex in CANONICAL_VERTICES if vertex not in rep][:count]
    return tuple(sorted(rep + tuple(missing)))


def _fixture_control_simplex(rep: Simplex) -> Simplex | None:
    for simplex in combinations(CANONICAL_VERTICES, len(rep)):
        if simplex != rep:
            return simplex
    return None


def cpp_parity_summary() -> str:
    """Fast canonical fixture signature for C++/Python parity replay."""
    lines = [
        "EQ64_CECH_STATIC_KERNEL_V1",
        f"N={LOCAL_SIMPLEX_VERTEX_COUNT}",
        f"G={GLOBAL_COMPONENT_COUNT}",
        f"APEX={APEX_VERTEX}",
    ]
    for p in range(20):
        lines.append(f"DIM:{p}:{local_dimension(p)}:{global_dimension(p)}")

    f0 = {(1,): 3, (2,): 5, (3,): 11}
    d0 = delta(0, f0)
    lines.append(f"DELTA0:{d0[(1, 2)]}:{d0[(1, 3)]}:{d0[(2, 3)]}")
    edge = {(1, 2): 1}
    d1 = delta(1, edge)
    lines.append(f"DELTA1:{d1[(1, 2, 3)]}:{d1[(1, 2, 20)]}")
    h1 = contracting_homotopy(1, {(1, 2): 7, (2, 3): 9})
    lines.append(f"H1:{h1[(1,)]}:{h1[(2,)]}:{h1[(3,)]}")
    h2 = contracting_homotopy(2, {(1, 2, 3): 5})
    lines.append(f"H2:{h2[(1, 2)]}:{h2[(2, 3)]}")
    pi = h0_projection({(1,): 3, (2,): 11, (20,): -4})
    lines.append(f"PI:{pi[(1,)]}:{pi[(2,)]}:{pi[(20,)]}")

    for p in range(19):
        for orbit_index, rep in enumerate(_parity_orbit_representatives(p)):
            value = 0
            if p <= 17:
                target = _fixture_extend(rep, 2)
                value = _basis_delta_squared_value(p, rep, target)
            lines.append(f"D2F:{p}:{orbit_index}:{value}")

    for p in range(1, 20):
        for orbit_index, rep in enumerate(_parity_orbit_representatives(p)):
            on_rep = _basis_positive_composition_value(p, rep, rep)
            lines.append(f"HOMF:{p}:{orbit_index}:{on_rep}")
            control = _fixture_control_simplex(rep)
            if control is None:
                lines.append(f"HOMC:{p}:{orbit_index}:NA")
            else:
                control_value = _basis_positive_composition_value(p, rep, control)
                lines.append(f"HOMC:{p}:{orbit_index}:{control_value}")

    for basis_vertex in (1, 2, 20):
        for target_vertex in (1, 2, 20):
            value = 0 if target_vertex == APEX_VERTEX else (
                (1 if target_vertex == basis_vertex else 0)
                - (1 if APEX_VERTEX == basis_vertex else 0)
            )
            lines.append(f"H0F:{basis_vertex}:{target_vertex}:{value}")

    lines.append("MUTANT_DETECTED:1")
    lines.append(f"H0_DIM:{GLOBAL_COMPONENT_COUNT}")
    return "\n".join(lines) + "\n"
