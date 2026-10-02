import unittest

try:
    import planetary_resource_alternate_freshwater_explicit_interval_source_discovery_v1 as gate
except ModuleNotFoundError:
    gate = None


class AlternateFreshwaterExplicitIntervalSourceDiscoveryTests(unittest.TestCase):
    def test_one_structurally_admissible_replacement_source_is_found(self):
        observed = (
            gate.run_gate()["verdict"]
            if gate is not None
            else "MISSING_IMPLEMENTATION"
        )
        self.assertEqual(
            observed,
            "PASS_BOUNDED_ALTERNATE_FRESHWATER_EXPLICIT_INTERVAL_SOURCE_DISCOVERY",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
