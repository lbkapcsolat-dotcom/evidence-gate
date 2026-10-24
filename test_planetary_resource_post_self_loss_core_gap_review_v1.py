import json
import unittest

import planetary_resource_post_self_loss_core_gap_review_v1 as r


class PostSelfLossCoreGapReviewTests(unittest.TestCase):
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
        self.assertEqual(
            pins["typed_self_loss_receipt_sha256"],
            "7a769a23db4d7ac5edbbf4921f954856cecced3b7eda65ff4ea846a8b4f60091",
        )

    def test_all_six_requested_areas_reviewed(self):
        self.assertEqual(
            set(self.receipt["observed_review"]),
            {
                "storage_host_node_scope",
                "storage_parameter_uncertainty",
                "process_coefficient_uncertainty",
                "process_coefficient_validity_interval",
                "process_manifest_version_enforcement",
                "audit_vector_provenance_typing",
            },
        )

    def test_storage_host_scope_gap_observed(self):
        s=self.receipt["observed_review"]["storage_host_node_scope"]
        self.assertTrue(s["arbitrary_nonexistent_host_node_id_accepted"])
        self.assertFalse(s["transition_receives_topology_nodes"])

    def test_storage_parameter_uncertainty_gap_observed(self):
        s=self.receipt["observed_review"]["storage_parameter_uncertainty"]
        self.assertTrue(s["all_reviewed_parameters_raw_fraction"])
        self.assertFalse(s["manifest_has_parameter_uncertainty_field"])

    def test_process_coefficient_uncertainty_gap_observed(self):
        p=self.receipt["observed_review"]["process_coefficient_uncertainty"]
        self.assertFalse(p["coefficient_has_uncertainty_field"])
        self.assertTrue(p["exact_activity_output_uncertainty_is_exact"])
        self.assertTrue(p["coefficient_evidence_preserved"])

    def test_process_coefficient_validity_gap_observed(self):
        p=self.receipt["observed_review"]["process_coefficient_validity_interval"]
        self.assertFalse(p["has_valid_from"])
        self.assertFalse(p["has_valid_to"])
        self.assertFalse(p["has_interval_id"])

    def test_process_manifest_version_gap_observed(self):
        p=self.receipt["observed_review"]["process_manifest_version_enforcement"]
        self.assertTrue(p["mismatched_manifest_version_accepted"])
        self.assertEqual(p["process_manifest_version"],"V99")
        self.assertEqual(p["target_node_manifest_version"],"V1")

    def test_audit_vector_remains_separate_untyped(self):
        a=self.receipt["observed_review"]["audit_vector_provenance_typing"]
        self.assertTrue(a["returns_bare_tuple"])
        self.assertFalse(a["has_evidence_refs"])
        self.assertFalse(a["has_uncertainty"])
        self.assertTrue(a["aggregate_score_prohibited"])

    def test_exactly_one_next_capability_selected(self):
        self.assertEqual(self.receipt["selected_capability_count"],1)
        n=self.receipt["next_single_unproven_core_capability"]
        self.assertEqual(
            n["id"],
            "PROCESS_COEFFICIENT_UNCERTAINTY_PROPAGATION_V1",
        )
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
