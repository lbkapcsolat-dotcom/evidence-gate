from __future__ import annotations
from collections import Counter
from typing import Iterable, List, Sequence, Tuple

N = 6
STATE_COUNT = 1 << N
TOP = STATE_COUNT - 1

# Reconstructed, not historical-source recovery.
# Genomic bits: R,P,S,W,D,E.
# System bits: SOURCE,ENGINE,MOTORBINDING,BOUNDARY,GUARDRAIL,FORMALIZATION.

def bit(x: int, i: int) -> int:
    return (x >> i) & 1

def mk(bits: Sequence[int]) -> int:
    return sum((1 if b else 0) << i for i, b in enumerate(bits))

def phi(x: int) -> int:
    R, P, S, W, D, E = [bit(x, i) for i in range(6)]
    return mk([R & P, W, D, S, E, R & P & S & W & D & E])

def L(y: int) -> int:
    source, engine, motor, boundary, guard, formal = [bit(y, i) for i in range(6)]
    return mk([
        source | formal,
        source | formal,
        boundary | formal,
        engine | formal,
        motor | formal,
        guard | formal,
    ])

def leq(a: int, b: int) -> bool:
    return (a & ~b) == 0

def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()

def all_states() -> range:
    return range(STATE_COUNT)

def strict_chains(vertices: Iterable[int], length: int) -> List[Tuple[int, ...]]:
    vertices = tuple(sorted(vertices))
    if length == 1:
        return [(v,) for v in vertices]
    prev = strict_chains(vertices, length - 1)
    out: List[Tuple[int, ...]] = []
    for ch in prev:
        last = ch[-1]
        for v in vertices:
            if v != last and leq(last, v):
                out.append(ch + (v,))
    return out

def all_order_complex_chains() -> List[Tuple[int, ...]]:
    return [ch for length in range(1, 8) for ch in strict_chains(all_states(), length)]

def cubical_edges() -> List[Tuple[int, int]]:
    out = []
    for x in all_states():
        for i in range(N):
            y = x ^ (1 << i)
            if x < y:
                out.append((x, y))
    return out

def diagonal_counterexamples() -> List[Tuple[int, int, int, int, int]]:
    return [(a, b, phi(a), phi(b), hamming(phi(a), phi(b)))
            for a, b in cubical_edges() if hamming(phi(a), phi(b)) > 1]

def image_vertices() -> set[int]:
    return {phi(x) for x in all_states()}

def rel_chains(K: set[int], A: set[int], n: int) -> List[Tuple[int, ...]]:
    return [ch for ch in strict_chains(K, n + 1) if not set(ch).issubset(A)]

def boundary_columns(K: set[int], A: set[int], n: int):
    dom = rel_chains(K, A, n)
    cod = rel_chains(K, A, n - 1) if n > 0 else []
    idx = {ch: i for i, ch in enumerate(cod)}
    cols = []
    for ch in dom:
        v = 0
        for i in range(len(ch)):
            face = ch[:i] + ch[i + 1:]
            if face and not set(face).issubset(A):
                v ^= 1 << idx[face]
        cols.append(v)
    return cod, dom, cols

def gf2_rank(cols: Sequence[int]) -> int:
    piv = {}
    for v in cols:
        x = v
        while x:
            p = x.bit_length() - 1
            if p in piv:
                x ^= piv[p]
            else:
                piv[p] = x
                break
    return len(piv)

def gf2_kernel_basis(cols: Sequence[int]) -> List[int]:
    piv = {}
    basis = []
    for i, v in enumerate(cols):
        x = v
        combo = 1 << i
        while x:
            p = x.bit_length() - 1
            if p in piv:
                pv, pc = piv[p]
                x ^= pv
                combo ^= pc
            else:
                piv[p] = (x, combo)
                break
        if x == 0:
            basis.append(combo)
    return basis

def apply_linear(cols: Sequence[int], combo: int) -> int:
    out = 0
    x = combo
    while x:
        lsb = x & -x
        i = lsb.bit_length() - 1
        out ^= cols[i]
        x ^= lsb
    return out

def chain_map_columns(KG: set[int], AG: set[int], KS: set[int], AS: set[int], n: int):
    dom = rel_chains(KG, AG, n)
    cod = rel_chains(KS, AS, n)
    idx = {ch: i for i, ch in enumerate(cod)}
    cols = []
    for ch in dom:
        image = tuple(phi(v) for v in ch)
        cols.append(0 if len(set(image)) < len(image) else 1 << idx[image])
    return dom, cod, cols

def metrics() -> dict:
    image = image_vertices()
    fibers = Counter(phi(x) for x in all_states())
    chains = all_order_complex_chains()
    degenerate = sum(1 for ch in chains if len({phi(v) for v in ch}) < len(ch))

    KS = image - {0}
    AS = image - {0, TOP}
    KG = {x for x in all_states() if phi(x) != 0}
    AG = {x for x in all_states() if phi(x) not in (0, TOP)}

    dims = {}
    ranks = {}
    for name, K, A in [('G', KG, AG), ('S', KS, AS)]:
        dims[name] = [len(rel_chains(K, A, n)) for n in range(6)]
        ranks[name] = [0] + [gf2_rank(boundary_columns(K, A, n)[2]) for n in range(1, 6)]

    _, _, d4G = boundary_columns(KG, AG, 4)
    kernel = gf2_kernel_basis(d4G)
    _, _, F4 = chain_map_columns(KG, AG, KS, AS, 4)
    mapped = [apply_linear(F4, k) for k in kernel]
    nonzero_support = sorted({m.bit_count() for m in mapped if m})

    return {
        'galois_violations': sum(leq(L(s), g) != leq(s, phi(g)) for s in all_states() for g in all_states()),
        'phi_monotone_violations': sum(leq(a, b) and not leq(phi(a), phi(b)) for a in all_states() for b in all_states()),
        'L_monotone_violations': sum(leq(a, b) and not leq(L(a), L(b)) for a in all_states() for b in all_states()),
        'unit_violations': sum(not leq(s, phi(L(s))) for s in all_states()),
        'counit_violations': sum(not leq(L(phi(g)), g) for g in all_states()),
        'fiber_count': len(fibers),
        'max_fiber_size': max(fibers.values()),
        'chain_counts_dim_0_to_6': [len(strict_chains(all_states(), l)) for l in range(1, 8)],
        'strict_chain_count': len(chains),
        'normalized_degenerate_images': degenerate,
        'cubical_edges': len(cubical_edges()),
        'cubical_diagonal_counterexamples': diagonal_counterexamples(),
        'A_S': len(AS), 'K_S': len(KS), 'A_G': len(AG), 'K_G': len(KG),
        'relative_chain_dims': dims,
        'boundary_ranks': ranks,
        'H4_G': dims['G'][4] - ranks['G'][4] - ranks['G'][5],
        'H4_S': dims['S'][4] - ranks['S'][4] - ranks['S'][5],
        'induced_H4_rank': gf2_rank(mapped),
        'generator_image_supports': nonzero_support,
    }

EXPECTED = {
    'galois_violations': 0,
    'phi_monotone_violations': 0,
    'L_monotone_violations': 0,
    'unit_violations': 0,
    'counit_violations': 0,
    'fiber_count': 32,
    'max_fiber_size': 3,
    'chain_counts_dim_0_to_6': [64, 665, 2702, 5460, 5880, 3240, 720],
    'strict_chain_count': 18731,
    'normalized_degenerate_images': 8284,
    'cubical_edges': 192,
    'cubical_diagonal_counterexamples': [
        (31, 63, 15, 63, 2),
        (47, 63, 27, 63, 2),
        (55, 63, 29, 63, 2),
        (59, 63, 23, 63, 2),
        (61, 63, 30, 63, 2),
        (62, 63, 30, 63, 2),
    ],
    'A_S': 30, 'K_S': 31, 'A_G': 60, 'K_G': 61,
    'relative_chain_dims': {'G': [1, 60, 480, 1260, 1320, 480], 'S': [1, 30, 150, 240, 120, 0]},
    'boundary_ranks': {'G': [0, 1, 59, 421, 839, 480], 'S': [0, 1, 29, 121, 119, 0]},
    'H4_G': 1, 'H4_S': 1, 'induced_H4_rank': 1,
    'generator_image_supports': [120],
}

if __name__ == '__main__':
    import json
    observed = metrics()
    print(json.dumps(observed, indent=2))
    assert observed == EXPECTED
