import unittest

try:
    import planetary_resource_aligned_real_input_integration_canary_v1 as gate
except ModuleNotFoundError:
    gate = None


class AlignedRealInputIntegrationCanaryTests(unittest.TestCase):
    def test_real_inputs_enter_the_correct_frozen_core_slots(self):
        observed = (
            gate.run_gate()["verdict"]
            if gate is not None
            else "MISSING_IMPLEMENTATION"
        )
        self.assertEqual(
            observed,
            "PASS_BOUNDED_ALIGNED_REAL_INPUT_INTEGRATION_CANARY",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
