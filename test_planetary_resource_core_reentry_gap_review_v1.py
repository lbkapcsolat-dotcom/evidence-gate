import json
import unittest

import planetary_resource_core_reentry_gap_review_v1 as r


class CoreReentryGapReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=r.run_review()

    def test_adapter_subsystem_is_pinned_frozen(self):
        self.assertEqual(
            self.receipt["verified_pins"]["source_adapter_freeze_receipt_sha256"],
            "7509be3fbb45e9949d159a67b16c648edecb1f606e998d572731ed1d255a150f",
        )
        self.assertFalse(self.receipt["provider_work"])

    def test_all_six_requested_areas_reviewed(self):
        self.assertEqual(
            set(self.receipt["observed_review"]),
            {
                "balance_kernel","storage_kernel","process_coupling",
                "boundary_flow","uncertainty_path","audit_vector",
            },
        )

    def test_process_gap_is_observed(self):
        p=self.receipt["observed_review"]["process_coupling"]
        self.assertTrue(p["wrong_coefficient_unit_accepted"])
        self.assertTrue(p["activity_unit_mismatch_accepted"])
        self.assertTrue(p["returns_untyped_numeric_mapping"])

    def test_balance_process_ingress_is_untyped(self):
        self.assertTrue(
            self.receipt["observed_review"]["balance_kernel"]
            ["raw_untyped_process_injection_accepted"]
        )

    def test_boundary_path_remains_fail_closed(self):
        self.assertTrue(
            self.receipt["observed_review"]["boundary_flow"]
            ["negative_directed_flow_rejected"]
        )

    def test_uncertainty_path_is_standalone_not_end_to_end(self):
        u=self.receipt["observed_review"]["uncertainty_path"]
        self.assertTrue(u["interval_path"])
        self.assertTrue(u["moment_path"])
        self.assertTrue(u["empirical_path"])
        self.assertTrue(u["balance_output_is_raw_fraction"])

    def test_audit_score_remains_prohibited(self):
        self.assertTrue(
            self.receipt["observed_review"]["audit_vector"]
            ["aggregate_score_prohibited"]
        )

    def test_exactly_one_next_capability_selected(self):
        self.assertEqual(self.receipt["selected_capability_count"],1)
        n=self.receipt["next_single_unproven_core_capability"]
        self.assertEqual(
            n["id"],
            "PROCESS_COUPLING_TYPED_DIMENSIONAL_CLOSURE_V1",
        )
        self.assertTrue(n["implementation_not_authorized_by_this_review"])

    def test_scope_fences(self):
        for key in (
            "provider_work","new_source_ingest","multi_source_fusion",
            "eq_score","ui","runtime_admission","pointer_promotion",
            "global_bind","merge",
        ):
            self.assertFalse(self.receipt["fences"][key],key)

    def test_deterministic_review(self):
        a=r.run_review()
        b=r.run_review()
        ja=json.dumps(a,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        jb=json.dumps(b,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        self.assertEqual(ja,jb)


if __name__=="__main__":
    unittest.main(verbosity=2)
