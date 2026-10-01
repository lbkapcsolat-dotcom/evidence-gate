import importlib
import unittest


class CechStaticKernelDimensionTests(unittest.TestCase):
    def _kernel(self):
        try:
            return importlib.import_module("hgraph_cech_static_kernel")
        except ModuleNotFoundError:
            self.fail("hgraph_cech_static_kernel module is missing")

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


if __name__ == "__main__":
    unittest.main()
