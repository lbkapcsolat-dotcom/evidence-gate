import unittest

try:
    import planetary_resource_temporal_support_operator_reference_validator_v1 as gate
except ModuleNotFoundError:
    gate = None


class TemporalSupportOperatorReferenceValidatorTests(unittest.TestCase):
    def test_required_reference_fixture_matrix_passes_without_path_b_activation(self):
        observed = (
            gate.run_gate()["verdict"]
            if gate is not None
            else "MISSING_IMPLEMENTATION"
        )
        self.assertEqual(
            observed,
            "PASS_BOUNDED_TEMPORAL_SUPPORT_OPERATOR_REFERENCE_VALIDATOR",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
