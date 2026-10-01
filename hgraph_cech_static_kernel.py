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
