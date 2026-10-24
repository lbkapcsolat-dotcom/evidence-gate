import json
import unittest

import planetary_resource_three_layer_generalization_review_v1 as r


class ThreeLayerGeneralizationReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = r.run_review()

    def test_three_layers_only(self):
        self.assertEqual(
            sorted(self.receipt["canary_views"]),
            ["ELECTRICITY", "FRESHWATER", "NATURAL_GAS"],
        )

    def test_shared_adapter_schema_applies_to_all_three(self):
        for view in self.receipt["canary_views"].values():
            self.assertEqual(view["admission_decision"], "ADMIT_OBSERVED")
            self.assertEqual(view["spatial_method"], "NODE_LOOKUP")
            self.assertEqual(view["temporal_method"], "EXACT_INTERVAL")
            self.assertFalse(view["interpolation_used"])
            self.assertFalse(view["imputation_used"])
            self.assertFalse(view["aggregation_performed"])
            self.assertTrue(view["fresh_at_admission"])
            self.assertEqual(view["uncertainty_kind"], "UNKNOWN")
            self.assertFalse(view["promotion_to_exact"])
            self.assertFalse(view["zero_is_missing"])

    def test_three_distinct_canonical_units(self):
        units={x["canonical_unit"] for x in self.receipt["canary_views"].values()}
        self.assertEqual(units, {"m3/s", "W_e", "W_th"})

    def test_gas_exception_is_explicit(self):
        gas=self.receipt["canary_views"]["NATURAL_GAS"]
        self.assertIn("energy_basis:GCV", gas["transform_chain"])
        self.assertIn("terminology:GCV->HHV", gas["transform_chain"])

    def test_no_provider_specific_physics_engine(self):
        g=self.receipt["generalization_findings"]
        self.assertFalse(g["domain_math_reimplementation_per_source_required"])
        self.assertFalse(g["provider_specific_physics_engine_required"])

    def test_crude_oil_not_required_for_adapter_generalization(self):
        d=self.receipt["crude_oil_decision"]
        self.assertFalse(d["adapter_generalization_requires_oil_canary"])
        self.assertFalse(d["recommended_now"])

    def test_crude_oil_required_for_four_layer_claim_or_oil_admission(self):
        d=self.receipt["crude_oil_decision"]
        self.assertTrue(d["four_layer_real_world_coverage_requires_oil_canary"])
        self.assertTrue(d["before_any_crude_oil_source_admission"])
        self.assertTrue(d["before_claiming_all_four_v1_layers_real_world_tested"])

    def test_no_new_source_ingest_or_fusion(self):
        self.assertFalse(self.receipt["fences"]["new_source_ingest"])
        self.assertFalse(self.receipt["fences"]["multi_source_fusion"])

    def test_deterministic_review(self):
        a=r.run_review()
        b=r.run_review()
        ja=json.dumps(a,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        jb=json.dumps(b,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        self.assertEqual(ja,jb)


if __name__ == "__main__":
    unittest.main(verbosity=2)
