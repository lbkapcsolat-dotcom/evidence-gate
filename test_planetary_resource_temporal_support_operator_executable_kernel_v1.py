import unittest

try:
    import planetary_resource_temporal_support_operator_executable_kernel_v1 as gate
except ModuleNotFoundError:
    gate = None


class TemporalSupportOperatorExecutableKernelTests(unittest.TestCase):
    def test_executable_kernel_replays_reference_matrix_without_path_b_activation(self):
        observed = (
            gate.run_gate()["verdict"]
            if gate is not None
            else "MISSING_IMPLEMENTATION"
        )
        self.assertEqual(
            observed,
            "PASS_BOUNDED_TEMPORAL_SUPPORT_OPERATOR_EXECUTABLE_KERNEL",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
