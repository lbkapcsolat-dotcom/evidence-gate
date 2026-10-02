import unittest

try:
    import planetary_resource_environment_agency_interval_semantics_external_authority_resolution_v1 as gate
except ModuleNotFoundError:
    gate = None


class EnvironmentAgencyIntervalSemanticsExternalAuthorityResolutionTests(unittest.TestCase):
    def test_final_hold_when_no_authoritative_boundary_rule_exists(self):
        observed = (
            gate.run_gate()["verdict"]
            if gate is not None
            else "MISSING_IMPLEMENTATION"
        )
        self.assertEqual(
            observed,
            "FINAL_HOLD_FOR_EA_SOURCE_FAMILY__NO_AUTHORITATIVE_INTERVAL_BOUNDARY_RULE",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
