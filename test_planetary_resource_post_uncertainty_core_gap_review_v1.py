import json
import unittest

import planetary_resource_post_uncertainty_core_gap_review_v1 as r


class PostUncertaintyCoreGapReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=r.run_review()

    def test_predecessors_pinned(self):
        pins=self.receipt["verified_predecessor_pins"]
        self.assertEqual(
            pins["typed_process_receipt_sha256"],
            "aba5715cd942f8da3d533c37e8d5c64de2f8d1d937cec47508fa1c22c4971fe5",
        )
        self.assertEqual(
            pins["e2e_uncertainty_receipt_sha256"],
            "e7c131d890aedf397afa5065c74bcbab9b0d57febb6cb2386720fe4f2d1b5dbd",
        )

    def test_all_five_requested_areas_reviewed(self):
        self.assertEqual(
            set(self.receipt["observed_review"]),
            {
                "remaining_storage_semantics",
                "self_loss_typing",
                "audit_vector_typing",
                "boundary_uncertainty_completeness",
                "process_metadata_completeness",
            },
        )

    def test_negative_self_loss_is_currently_accepted(self):
        s=self.receipt["observed_review"]["self_loss_typing"]
        self.assertTrue(s["negative_self_loss_accepted"])
        self.assertTrue(s["negative_self_loss_increases_stock"])
        self.assertEqual(s["baseline_next_stock"],"104")
        self.assertEqual(s["negative_self_loss_next_stock"],"105")

    def test_self_loss_is_outside_uncertainty_metadata(self):
        s=self.receipt["observed_review"]["self_loss_typing"]
        self.assertTrue(s["self_loss_is_raw_fraction_parameter"])
        self.assertTrue(s["self_loss_has_no_qv_metadata"])
        self.assertTrue(s["self_loss_excluded_from_uncertainty_contributors"])

    def test_boundary_uncertainty_is_complete_for_v1_flow_path(self):
        b=self.receipt["observed_review"]["boundary_uncertainty_completeness"]
        self.assertEqual((b["interval_lower"],b["interval_upper"]),("-1","1"))
        self.assertTrue(b["boundary_evidence_preserved"])

    def test_audit_vector_still_separate(self):
        a=self.receipt["observed_review"]["audit_vector_typing"]
        self.assertTrue(a["returns_tuple"])
        self.assertFalse(a["has_provenance_fields"])
        self.assertTrue(a["aggregate_score_prohibited"])

    def test_process_metadata_gap_recorded(self):
        p=self.receipt["observed_review"]["process_metadata_completeness"]
        self.assertFalse(p["coefficient_has_uncertainty_field"])
        self.assertFalse(p["coefficient_has_valid_from_field"])
        self.assertFalse(p["coefficient_has_valid_to_field"])
        self.assertTrue(p["mismatched_process_manifest_version_accepted"])

    def test_exactly_one_next_capability(self):
        self.assertEqual(self.receipt["selected_capability_count"],1)
        n=self.receipt["next_single_unproven_core_capability"]
        self.assertEqual(n["id"],"STORAGE_SELF_LOSS_TYPED_PHYSICAL_RATE_V1")
        self.assertTrue(n["implementation_not_authorized_by_this_review"])

    def test_scope_fences(self):
        for key in (
            "provider_work","new_source_ingest","multi_source_fusion","eq_score",
            "ui","runtime_admission","pointer_promotion","global_bind","merge",
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
