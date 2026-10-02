import hashlib
import json
import unittest

try:
    import planetary_resource_alternate_freshwater_explicit_interval_source_discovery_v1 as gate
except ModuleNotFoundError:
    gate = None


class AlternateFreshwaterExplicitIntervalSourceDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = gate.run_gate() if gate is not None else None

    def test_one_structurally_admissible_replacement_source_is_found(self):
        observed = (
            self.receipt["verdict"]
            if self.receipt is not None
            else "MISSING_IMPLEMENTATION"
        )
        self.assertEqual(
            observed,
            "PASS_BOUNDED_ALTERNATE_FRESHWATER_EXPLICIT_INTERVAL_SOURCE_DISCOVERY",
        )

    def test_predecessor_final_hold_is_exactly_pinned(self):
        self.assertEqual(
            self.receipt["predecessor"]["receipt_sha256"],
            "ffb19d37f292fcbeb207c17c261f15dfaa9ab8b484571e81d31f591a69bf93d3",
        )
        self.assertEqual(
            self.receipt["predecessor"]["ea_source_family_status"],
            "FINAL_HOLD",
        )

    def test_raw_source_bytes_and_sha256_are_exact(self):
        s = self.receipt["selected_source"]
        self.assertEqual(s["raw_bytes"], 2735)
        self.assertEqual(
            s["raw_sha256"],
            "1fe8f1416b69377160ed6c9fced011785a46e7cb52eac46ce783a424c3e7ee14",
        )

    def test_source_is_watercourse_discharge_rate(self):
        s = self.receipt["selected_source"]
        self.assertEqual(s["provider"], "Australian Bureau of Meteorology")
        self.assertEqual(s["station_id"], "410713")
        self.assertEqual(s["observed_property"], "Water Course Discharge")
        self.assertEqual(s["unit_code"], "cumec")
        self.assertEqual(s["unit_semantics"], "cubic metres per second")
        self.assertEqual(s["published_value"], "0.378")

    def test_interval_bounds_are_source_explicit_and_positive(self):
        s = self.receipt["selected_source"]
        self.assertEqual(
            s["interval_start"], "2026-09-30T00:00:00.000+10:00"
        )
        self.assertEqual(
            s["interval_end"], "2026-10-01T00:00:00.000+10:00"
        )
        self.assertEqual(s["published_time"], s["interval_start"])
        self.assertEqual(s["interval_duration_seconds"], 86400)

    def test_no_equilibrium_interpolation_imputation_or_boundary_inference(self):
        c = self.receipt["structural_checks"]
        self.assertFalse(c["boundary_inference_used"])
        self.assertFalse(c["interpolation_performed_by_equilibrium"])
        self.assertFalse(c["imputation_performed_by_equilibrium"])
        self.assertTrue(
            c["source_native_aggregation_preserved_without_recalculation"]
        )

    def test_all_structural_requirements_are_satisfied(self):
        c = self.receipt["structural_checks"]
        self.assertTrue(c["flow_rate_or_equivalent_freshwater_rate"])
        self.assertTrue(c["explicit_interval_start"])
        self.assertTrue(c["explicit_interval_end"])
        self.assertTrue(c["positive_duration_interval"])
        self.assertTrue(c["source_provenance"])
        self.assertTrue(c["raw_bytes_preserved"])
        self.assertTrue(c["sha256_preserved"])
        self.assertEqual(
            self.receipt["structurally_admissible_replacement_source_count"], 1
        )

    def test_source_native_waterml_metadata_is_preserved_not_recomputed(self):
        s = self.receipt["selected_source"]
        self.assertEqual(s["source_native_aggregation"], "DAILY_TIME_WEIGHTED_MEAN")
        self.assertTrue(
            s["source_waterml_interpolation_metadata"].endswith("/ConstSucc")
        )
        self.assertEqual(
            s["source_waterml_interpolation_title"],
            "Constant in succeeding interval",
        )

    def test_no_core_domain_or_composition_change(self):
        self.assertFalse(self.receipt["composition_performed"])
        self.assertFalse(self.receipt["core_patch_required"])
        self.assertFalse(self.receipt["new_domain_math_added"])
        self.assertFalse(any(self.receipt["fences"].values()))

    def test_claim_ceiling_remains_source_discovery_only(self):
        self.assertIn("Source discovery only", self.receipt["claim_ceiling"])
        self.assertIn("does not prove three-source temporal alignment", self.receipt["claim_ceiling"])

    def test_deterministic_receipt(self):
        a = gate.run_gate()
        b = gate.run_gate()
        ja = json.dumps(a, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        jb = json.dumps(b, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.assertEqual(ja, jb)
        self.assertEqual(
            hashlib.sha256((ja + "\n").encode()).hexdigest(),
            hashlib.sha256((jb + "\n").encode()).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
