import unittest

try:
    import planetary_resource_formal_temporal_support_operator_spec_v1 as gate
except ModuleNotFoundError:
    gate = None


class FormalTemporalSupportOperatorSpecTests(unittest.TestCase):
    def test_formal_path_b_operator_spec_is_frozen_without_activation(self):
        observed = (
            gate.run_gate()["verdict"]
            if gate is not None
            else "MISSING_IMPLEMENTATION"
        )
        self.assertEqual(
            observed,
            "PASS_BOUNDED_FORMAL_TEMPORAL_SUPPORT_OPERATOR_SPEC",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
