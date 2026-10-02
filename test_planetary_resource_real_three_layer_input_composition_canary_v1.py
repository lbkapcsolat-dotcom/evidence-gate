import hashlib
import json
import unittest

import planetary_resource_real_three_layer_input_composition_canary_v1 as canary


class RealThreeLayerInputCompositionCanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = canary.run_canary()

    def test_exact_predecessor_pins(self):
        p = self.receipt["predecessor"]
        self.assertEqual(
            p["integrated_state_sha256"],
            "116967bace6297b8d7e7ff8886aa1cbaea6f883339c96c7ff342d1f8488a7fc0",
        )
        self.assertEqual(
            p["integrated_receipt_sha256"],
            "bef3b597d8c27e49c591c245e4745ba23e9f8fa3e7aa8d2a2def95ca213cc367",
        )

    def test_three_proven_bindings_revalidated(self):
        r = self.receipt["revalidated_proven_bindings"]
        self.assertEqual(set(r), {"freshwater", "electricity", "natural_gas"})
        self.assertEqual(
            r["freshwater"]["canary_receipt_sha256"],
            "697857c063c2cd6d7514e2b9dd79c46d7fe59a5efe0588579e9c4fd306b12c93",
        )
        self.assertEqual(
            r["electricity"]["canary_receipt_sha256"],
            "9a996daea1a702e1654264a13cc72d0dcba760f8945528b24ce854c2392bca29",
        )
        self.assertEqual(
            r["natural_gas"]["canary_receipt_sha256"],
            "f0629b99245af4dacea863f91b71faf5938b10ed6e1c7069f4c1f829b5a1c406",
        )

    def test_gas_and_electricity_have_no_positive_duration_overlap(self):
        self.assertEqual(
            self.receipt["temporal_evidence"][
                "gas_electricity_positive_overlap_seconds"
            ],
            0,
        )
        codes = {b["code"] for b in self.receipt["blockers"]}
        self.assertIn(
            "HOLD_GAS_ELECTRICITY_NO_POSITIVE_DURATION_OVERLAP", codes
        )

    def test_water_interval_start_is_not_inferred(self):
        codes = {b["code"] for b in self.receipt["blockers"]}
        self.assertIn("HOLD_WATER_INTERVAL_BOUNDARY_NOT_EXPLICIT", codes)
        self.assertFalse(self.receipt["inferred_interval_boundary_used"])

    def test_fail_closed_before_real_mapping(self):
        self.assertFalse(self.receipt["common_window_proven"])
        self.assertFalse(self.receipt["mapping_performed"])
        self.assertFalse(self.receipt["real_values_entered_integrated_balance"])
        self.assertEqual(
            self.receipt["verdict"],
            "HOLD_NO_COMMON_FROZEN_COMPOSITION_WINDOW",
        )

    def test_no_forbidden_temporal_transform(self):
        self.assertFalse(self.receipt["interpolation_performed"])
        self.assertFalse(self.receipt["imputation_performed"])
        self.assertFalse(self.receipt["aggregation_performed"])
        self.assertFalse(self.receipt["new_source_ingest"])

    def test_predecessor_guards_preserved(self):
        p = self.receipt["predecessor"]
        self.assertTrue(p["process_version_guard_preserved"])
        self.assertTrue(p["process_validity_guard_preserved"])
        self.assertTrue(p["storage_topology_guard_preserved"])

    def test_uncertainty_and_provenance_preserved(self):
        self.assertTrue(self.receipt["uncertainty_preserved"])
        self.assertTrue(self.receipt["source_provenance_preserved"])
        for row in self.receipt["revalidated_proven_bindings"].values():
            self.assertEqual(row["admitted_value"]["uncertainty_kind"], "UNKNOWN")
            self.assertTrue(row["admitted_value"]["transform_chain"])

    def test_no_core_or_domain_change(self):
        self.assertFalse(self.receipt["core_patch_required"])
        self.assertFalse(self.receipt["new_domain_math_added"])
        self.assertFalse(any(self.receipt["fences"].values()))

    def test_deterministic_receipt(self):
        a = canary.run_canary()
        b = canary.run_canary()
        ja = json.dumps(a, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        jb = json.dumps(b, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.assertEqual(ja, jb)
        self.assertEqual(
            hashlib.sha256((ja + "\n").encode()).hexdigest(),
            hashlib.sha256((jb + "\n").encode()).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
