import unittest

try:
    import planetary_resource_native_common_support_replacement_and_integration_retry_v1 as gate
except ModuleNotFoundError:
    gate = None


class NativeCommonSupportReplacementAndIntegrationRetryTests(unittest.TestCase):
    def test_gate_holds_if_exact_native_gas_or_freshwater_support_is_unavailable(self):
        observed = (
            gate.run_gate()["verdict"]
            if gate is not None
            else "MISSING_IMPLEMENTATION"
        )
        self.assertEqual(
            observed,
            "HOLD_EXACT_NATIVE_COMMON_SUPPORT_NOT_AVAILABLE",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
