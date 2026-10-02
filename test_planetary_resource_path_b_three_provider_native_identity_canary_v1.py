import unittest

try:
    import planetary_resource_path_b_three_provider_native_identity_canary_v1 as gate
except ModuleNotFoundError:
    gate = None


class PathBThreeProviderNativeIdentityCanaryTests(unittest.TestCase):
    def test_three_real_providers_pass_native_identity_without_common_window(self):
        observed = (
            gate.run_gate()["verdict"]
            if gate is not None
            else "MISSING_IMPLEMENTATION"
        )
        self.assertEqual(
            observed,
            "PASS_BOUNDED_PATH_B_THREE_PROVIDER_NATIVE_IDENTITY_CANARY",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
