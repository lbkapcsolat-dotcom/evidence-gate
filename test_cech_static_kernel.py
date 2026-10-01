import importlib
import unittest


class KernelMixin:
    def _kernel(self):
        try:
            return importlib.import_module("hgraph_cech_static_kernel")
        except ModuleNotFoundError:
            self.fail("hgraph_cech_static_kernel module is missing")


class CechStaticKernelDimensionTests(KernelMixin, unittest.TestCase):
    def test_local_and_global_dimensions_all_degrees(self):
        k = self._kernel()
        expected_local = [
            20, 190, 1140, 4845, 15504, 38760, 77520, 125970, 167960,
            184756, 167960, 125970, 77520, 38760, 15504, 4845, 1140, 190,
            20, 1,
        ]
        self.assertEqual([k.local_dimension(p) for p in range(20)], expected_local)
        self.assertEqual(
            [k.global_dimension(p) for p in range(20)],
            [64 * n for n in expected_local],
        )

    def test_dimension_rejects_out_of_range_degree(self):
        k = self._kernel()
        with self.assertRaises(ValueError):
            k.local_dimension(-1)
        with self.assertRaises(ValueError):
            k.local_dimension(20)


class CechCoboundaryTests(KernelMixin, unittest.TestCase):
    def test_delta_degree_zero_uses_alternating_orientation(self):
        k = self._kernel()
        f = {(1,): 3, (2,): 5, (3,): 11}
        df = k.delta(0, f)
        self.assertEqual(df[(1, 2)], 2)
        self.assertEqual(df[(1, 3)], 8)
        self.assertEqual(df[(2, 3)], 6)

    def test_delta_of_single_edge_has_expected_triangle_signs(self):
        k = self._kernel()
        edge = {(1, 2): 1}
        d_edge = k.delta(1, edge)
        self.assertEqual(d_edge[(1, 2, 3)], 1)
        self.assertEqual(d_edge[(1, 2, 20)], 1)

    def test_delta_top_degree_is_zero(self):
        k = self._kernel()
        top = {tuple(range(1, 21)): 7}
        self.assertEqual(k.delta(19, top), {})


class CechContractingHomotopyTests(KernelMixin, unittest.TestCase):
    def test_h1_inserts_apex_and_vanishes_on_apex_vertex(self):
        k = self._kernel()
        phi = {(1, 2): 7, (2, 3): 9}
        hphi = k.contracting_homotopy(1, phi)
        self.assertEqual(hphi[(1,)], 0)
        self.assertEqual(hphi[(2,)], 7)
        self.assertEqual(hphi[(3,)], 0)

    def test_h2_apex_present_and_absent_targets(self):
        k = self._kernel()
        phi = {(1, 2, 3): 5}
        hphi = k.contracting_homotopy(2, phi)
        self.assertEqual(hphi[(1, 2)], 0)
        self.assertEqual(hphi[(2, 3)], 5)

    def test_h0_projection_is_constant_apex_evaluation(self):
        k = self._kernel()
        f = {(1,): 3, (2,): 11, (20,): -4}
        projection = k.h0_projection(f)
        self.assertEqual(len(projection), 20)
        self.assertTrue(all(projection[(v,)] == 3 for v in range(1, 21)))

    def test_contracting_homotopy_rejects_degree_zero(self):
        k = self._kernel()
        with self.assertRaises(ValueError):
            k.contracting_homotopy(0, {(1,): 1})


def _clean(cochain):
    return {simplex: value for simplex, value in cochain.items() if value != 0}


def _orbit_representatives(p):
    reps = [tuple(range(1, p + 2))]
    if p <= 18:
        reps.append(tuple(range(2, p + 3)))
    return reps


class CechAlgebraIdentityTests(KernelMixin, unittest.TestCase):
    def test_delta_squared_zero_all_degrees_both_orbits(self):
        k = self._kernel()
        for p in range(19):
            for rep in _orbit_representatives(p):
                with self.subTest(p=p, rep=rep):
                    phi = {rep: 1}
                    first = k.delta(p, phi)
                    second = k.delta(p + 1, first)
                    self.assertEqual(_clean(second), {})

    def test_positive_degree_graph_composition_is_identity_all_degrees(self):
        k = self._kernel()
        for p in range(1, 20):
            for rep in _orbit_representatives(p):
                with self.subTest(p=p, rep=rep):
                    phi = {rep: 1}
                    composed = k.positive_degree_homotopy_composition(p, phi)
                    self.assertEqual(_clean(composed), phi)

    def test_h0_reduced_composition_equals_identity_minus_projection(self):
        k = self._kernel()
        for vertex in (1, 2, 20):
            with self.subTest(vertex=vertex):
                f = {(vertex,): 1}
                lhs = _clean(k.h0_reduced_composition(f))
                projection = k.h0_projection(f)
                rhs = _clean({
                    (v,): f.get((v,), 0) - projection[(v,)]
                    for v in range(1, 21)
                })
                self.assertEqual(lhs, rhs)

    def test_orientation_sign_mutant_is_detected(self):
        k = self._kernel()

        def mutant_delta_all_plus(p, cochain):
            from itertools import combinations
            out = {}
            if p == 19:
                return out
            for simplex in combinations(range(1, 21), p + 2):
                out[simplex] = sum(
                    cochain.get(simplex[:j] + simplex[j + 1 :], 0)
                    for j in range(p + 2)
                )
            return out

        phi = {(1,): 1}
        broken = mutant_delta_all_plus(1, mutant_delta_all_plus(0, phi))
        self.assertNotEqual(_clean(broken), {})
        self.assertEqual(_clean(k.delta(1, k.delta(0, phi))), {})


if __name__ == "__main__":
    unittest.main()
