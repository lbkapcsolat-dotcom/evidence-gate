from __future__ import annotations

import importlib.metadata
import json
from itertools import permutations, product
from typing import Final

import _hgraph
from hgraph import TS, compute_node, graph, operator

HGRAPH_VERSION: Final[str] = "0.8.31"
HGRAPH_RELEASE_COMMIT: Final[str] = "1bb4b7f21ddfb6c69c8bae74c523980605ae93f6"
HGRAPH_LINUX_WHEEL_SHA256: Final[str] = "78b08521e11cfeb4b088e519e627f21b19171248ec36560a67779d344abe43b2"
BINDING_MODE: Final[str] = "PYTHON_AUTHORED_OPERATOR_ON_NATIVE_HGRAPH_RUNTIME"


def _permutation_parity(p: tuple[int, int, int]) -> int:
    inversions = sum(1 for i in range(3) for j in range(i + 1, 3) if p[i] > p[j])
    return 1 if inversions % 2 == 0 else -1


def build_rotations() -> tuple[tuple[int, ...], ...]:
    out: list[tuple[int, ...]] = []
    for perm_raw in permutations(range(3)):
        perm = tuple(int(v) for v in perm_raw)
        parity = _permutation_parity(perm)
        for sx, sy, sz in product((-1, 1), repeat=3):
            signs = (sx, sy, sz)
            if parity * sx * sy * sz != 1:
                continue
            r = [0] * 6
            for face in range(6):
                axis = face // 2
                face_sign = 1 if face % 2 == 0 else -1
                out_axis = perm[axis]
                out_sign = face_sign * signs[axis]
                r[face] = 2 * out_axis + (0 if out_sign == 1 else 1)
            out.append(tuple(r))
    if len(out) != 24 or len(set(out)) != 24:
        raise RuntimeError("rotation set must contain exactly 24 unique proper cube rotations")
    return tuple(out)


ROTATIONS: Final[tuple[tuple[int, ...], ...]] = build_rotations()


def _coordinate_bit(state: int, coordinate: int) -> bool:
    return bool((state >> (5 - coordinate)) & 1)


def _set_coordinate_bit(state: int, coordinate: int) -> int:
    return state | (1 << (5 - coordinate))


def apply_rotation(state: int, rotation: tuple[int, ...]) -> int:
    if not 0 <= state <= 63:
        raise ValueError("state must be in [0,63]")
    out = 0
    for coordinate in range(6):
        if _coordinate_bit(state, coordinate):
            out = _set_coordinate_bit(out, rotation[coordinate])
    return out


def canonical_record(state: int) -> dict[str, int]:
    if not 0 <= state <= 63:
        raise ValueError("state must be in [0,63]")
    orbit = {apply_rotation(state, r) for r in ROTATIONS}
    stabilizer = sum(1 for r in ROTATIONS if apply_rotation(state, r) == state)
    if not orbit:
        raise RuntimeError("empty orbit")
    if len(orbit) * stabilizer != 24:
        raise RuntimeError("orbit-stabilizer violation")
    return {
        "x": state,
        "canonical": min(orbit),
        "orbit_size": len(orbit),
        "stabilizer_size": stabilizer,
    }


def canonical_record_json(state: int) -> str:
    return json.dumps(canonical_record(state), separators=(",", ":"), ensure_ascii=False)


def orbit_profile() -> tuple[int, ...]:
    seen: set[int] = set()
    sizes: list[int] = []
    for state in range(64):
        if state in seen:
            continue
        orbit = {apply_rotation(state, r) for r in ROTATIONS}
        seen.update(orbit)
        sizes.append(len(orbit))
    return tuple(sorted(sizes))


def canonical_label_count() -> int:
    return len({canonical_record(state)["canonical"] for state in range(64)})


@operator
def babai_eq64_canonical_record_python(trigger: TS[int], state: int) -> TS[str]:
    ...


@compute_node(overloads=babai_eq64_canonical_record_python)
def babai_eq64_canonical_record_python_impl(trigger: TS[int], state: int) -> TS[str]:
    return canonical_record_json(state)


@graph
def run_babai_eq64_canonical_record_hgraph(trigger: TS[int], state: int) -> TS[str]:
    return babai_eq64_canonical_record_python(trigger, state)


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
    }
