import unittest

try:
    import planetary_resource_bom_elexon_entsog_temporally_aligned_snapshot_set_v1 as gate
except ModuleNotFoundError:
    gate = None


class BomElexonEntsogTemporallyAlignedSnapshotSetTests(unittest.TestCase):
    def test_positive_duration_three_way_intersection_is_proven(self):
        observed = (
            gate.run_gate()["verdict"]
            if gate is not None
            else "MISSING_IMPLEMENTATION"
        )
        self.assertEqual(
            observed,
            "PASS_BOUNDED_BOM_ELEXON_ENTSOG_TEMPORALLY_ALIGNED_SNAPSHOT_SET",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
