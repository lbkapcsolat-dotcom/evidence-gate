import hashlib
import json
from pathlib import Path
import unittest

import planetary_resource_first_real_source_canary_v1 as c


class FirstRealSourceCanary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = c.run_canary()
        cls.manifest = c.load_manifest()

    def test_one_source_only(self):
        self.assertEqual(self.receipt["counts"]["sources"], 1)

    def test_one_variable_only(self):
        self.assertEqual(self.receipt["counts"]["variables"], 1)
        self.assertEqual(self.receipt["record"]["parameter"], "flow")
        self.assertEqual(
            self.receipt["empirical_admission_receipt"]["variable_id"],
            "freshwater.internal_flow_rate",
        )

    def test_one_node_only(self):
        self.assertEqual(self.receipt["counts"]["nodes"], 1)
        self.assertEqual(
            self.receipt["spatial_mapping_receipt"]["target_node_id"],
            "EA_1100TH_FARMOOR_SOURCE_LOCAL_FLOW_ACCOUNTING_UNIT",
        )

    def test_one_interval_only(self):
        self.assertEqual(self.receipt["counts"]["intervals"], 1)
        self.assertEqual(self.receipt["record"]["period_seconds"], 900)

    def test_raw_source_sha256_exact(self):
        p = Path(self.receipt["source"]["raw_file"])
        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(
            actual,
            "c180db17bc02d371f1eebb4667695b715f0ce2f9c2f97bab6893b77f87c97c29",
        )
        self.assertEqual(self.receipt["source"]["raw_byte_length"], 1688)

    def test_admit_observed(self):
        self.assertEqual(
            self.receipt["empirical_admission_receipt"]["decision"],
            "ADMIT_OBSERVED",
        )
        self.assertEqual(
            (self.receipt["empirical_admission_receipt"]["canonical_value_n"],
             self.receipt["empirical_admission_receipt"]["canonical_value_d"]),
            (104, 125),
        )

    def test_unit_transform_identity(self):
        self.assertTrue(self.receipt["unit_transform_receipt"]["identity"])
        self.assertEqual(self.receipt["unit_transform_receipt"]["canonical_unit"], "m3/s")

    def test_spatial_claim_is_source_local_only(self):
        self.assertEqual(self.receipt["spatial_mapping_receipt"]["method"], "NODE_LOOKUP")
        self.assertEqual(
            self.receipt["spatial_mapping_receipt"]["claim_ceiling"],
            "SOURCE_LOCAL_GAUGE_ACCOUNTING_UNIT_ONLY__NOT_THAMES_BASIN_AGGREGATE",
        )

    def test_temporal_alignment_exact_without_hidden_interpolation(self):
        t = self.receipt["temporal_alignment_receipt"]
        self.assertEqual(t["method"], "EXACT_INTERVAL")
        self.assertFalse(t["interpolation_used"])
        self.assertFalse(t["imputation_used"])

    def test_freshness_readback(self):
        f = self.receipt["freshness_readback"]
        self.assertEqual(f["age_seconds"], 3953)
        self.assertTrue(f["fresh_at_admission"])

    def test_uncertainty_remains_unknown(self):
        u = self.receipt["uncertainty_declaration"]
        self.assertEqual(u["kind"], "UNKNOWN")
        self.assertFalse(u["promotion_to_exact"])

    def test_missingness_is_explicitly_not_invoked(self):
        m = self.receipt["missingness_semantics"]
        self.assertTrue(m["value_present"])
        self.assertEqual(m["source_status"], "OBSERVED")
        self.assertFalse(m["zero_is_missing"])

    def test_no_silent_transform(self):
        self.assertTrue(self.receipt["no_silent_transform"])

    def test_scope_fences(self):
        fences = self.receipt["fences"]
        self.assertTrue(fences["single_external_record_admitted"])
        self.assertFalse(fences["global_dataset_admitted"])
        for key in (
            "multi_source_fusion", "global_dataset_bind", "eq_score", "ui",
            "runtime_admission", "pointer_promotion", "global_bind", "merge",
        ):
            self.assertFalse(fences[key], key)

    def test_deterministic_receipt(self):
        a = c.run_canary()
        b = c.run_canary()
        ca = json.dumps(a, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        cb = json.dumps(b, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.assertEqual(ca, cb)


if __name__ == "__main__":
    unittest.main(verbosity=2)
