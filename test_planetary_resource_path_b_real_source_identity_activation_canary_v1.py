import unittest

try:
    import planetary_resource_path_b_real_source_identity_activation_canary_v1 as gate
except ModuleNotFoundError:
    gate = None


class PathBRealSourceIdentityActivationCanaryTests(unittest.TestCase):
    def test_real_elexon_identity_canary_activates_path_b_locally_only(self):
        observed = (
            gate.run_gate()["verdict"]
            if gate is not None
            else "MISSING_IMPLEMENTATION"
        )
        self.assertEqual(
            observed,
            "PASS_BOUNDED_PATH_B_REAL_SOURCE_IDENTITY_ACTIVATION_CANARY",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
