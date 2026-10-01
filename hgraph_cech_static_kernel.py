from __future__ import annotations

from itertools import combinations
from math import comb
from typing import Mapping

LOCAL_SIMPLEX_VERTEX_COUNT = 20
GLOBAL_COMPONENT_COUNT = 64
CANONICAL_VERTICES = tuple(range(1, LOCAL_SIMPLEX_VERTEX_COUNT + 1))
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
    """Alternating Cech coboundary on the ordered 20-vertex simplex.

    Missing cochain entries are interpreted as zero. The returned mapping
    is dense on the target local simplex basis, except at top degree where
    C^20 is zero and the result is empty.
    """
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
