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


if __name__ == "__main__":
    unittest.main()
