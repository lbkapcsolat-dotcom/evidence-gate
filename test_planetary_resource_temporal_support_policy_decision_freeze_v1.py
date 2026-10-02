import unittest

try:
    import planetary_resource_temporal_support_policy_decision_freeze_v1 as gate
except ModuleNotFoundError:
    gate = None


class TemporalSupportPolicyDecisionFreezeTests(unittest.TestCase):
    def test_exactly_two_allowed_temporal_paths_are_frozen(self):
        observed = (
            gate.run_gate()["verdict"]
            if gate is not None
            else "MISSING_IMPLEMENTATION"
        )
        self.assertEqual(
            observed,
            "PASS_BOUNDED_TEMPORAL_SUPPORT_POLICY_DECISION_FREEZE",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
