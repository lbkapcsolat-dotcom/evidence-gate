import hashlib
import json
import unittest

import planetary_resource_temporally_aligned_three_source_snapshot_set_v1 as gate


class TemporallyAlignedThreeSourceSnapshotSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = gate.run_gate()

    def test_predecessor_hold_is_exactly_pinned(self):
        self.assertEqual(
            self.receipt["predecessor"]["receipt_sha256"],
            "eb28b3eb2a495497a53fe416e30dda9c72a090b3766f955f926c6a4616ee9e26",
        )
        self.assertEqual(
            self.receipt["predecessor"]["verdict"],
            "HOLD_NO_COMMON_FROZEN_COMPOSITION_WINDOW",
        )

    def test_existing_three_bindings_revalidate(self):
        rows = self.receipt["revalidated_existing_bindings"]
        self.assertEqual(set(rows), {"freshwater", "electricity", "natural_gas"})
        for row in rows.values():
            self.assertEqual(row["decision"], "ADMIT_OBSERVED")
            self.assertEqual(row["uncertainty_kind"], "UNKNOWN")
            self.assertTrue(row["raw_sha256"])

    def test_environment_agency_explicit_interval_anchor_is_unproven(self):
        codes = {x["code"] for x in self.receipt["blockers"]}
        self.assertIn(
            "HOLD_ENVIRONMENT_AGENCY_INTERVAL_ANCHOR_UNPROVEN",
            codes,
        )

    def test_elexon_strict_explicit_end_bound_is_unproven(self):
        codes = {x["code"] for x in self.receipt["blockers"]}
        self.assertIn(
            "HOLD_ELEXON_EXPLICIT_END_BOUND_NOT_SOURCE_FIELD",
            codes,
        )

    def test_entsog_source_surface_has_explicit_period_bounds(self):
        sem = self.receipt["source_semantics_preflight"]["entsog"]
        self.assertTrue(sem["existing_record_has_period_from"])
        self.assertTrue(sem["existing_record_has_period_to"])
        self.assertTrue(sem["eligible_for_explicit_bounds"])

    def test_fail_closed_before_new_ingest(self):
        self.assertFalse(
            self.receipt["explicit_interval_bounds_proven_for_all_three"]
        )
        self.assertFalse(
            self.receipt["positive_duration_common_window_proven"]
        )
        self.assertEqual(self.receipt["new_source_records_ingested"], 0)
        self.assertFalse(self.receipt["new_source_ingest_performed"])
        self.assertFalse(self.receipt["composition_performed"])

    def test_no_forbidden_transforms_or_core_change(self):
        self.assertFalse(self.receipt["interpolation_performed"])
        self.assertFalse(self.receipt["imputation_performed"])
        self.assertFalse(self.receipt["cross_interval_aggregation_performed"])
        self.assertFalse(self.receipt["new_domain_math_added"])
        self.assertFalse(self.receipt["core_patch_required"])
        self.assertFalse(any(self.receipt["fences"].values()))

    def test_provenance_and_uncertainty_preserved(self):
        self.assertTrue(self.receipt["sha256_preserved"])
        self.assertTrue(self.receipt["source_provenance_preserved"])
        self.assertTrue(self.receipt["unknown_uncertainty_preserved"])

    def test_verdict_is_semantics_hold(self):
        self.assertEqual(
            self.receipt["verdict"],
            "HOLD_SOURCE_INTERVAL_SEMANTICS_UNPROVEN",
        )

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
