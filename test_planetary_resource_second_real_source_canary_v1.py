import hashlib
import json
from pathlib import Path
import unittest

import planetary_resource_second_real_source_canary_v1 as c


class SecondRealSourceCanary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = c.run_canary()

    def test_one_source_variable_node_interval(self):
        self.assertEqual(
            self.receipt["counts"],
            {"sources":1,"variables":1,"nodes":1,"intervals":1,"records":1},
        )

    def test_different_resource_layer(self):
        self.assertTrue(self.receipt["different_resource_layer"])
        self.assertEqual(self.receipt["empirical_admission_receipt"]["layer"], "ELECTRICITY")

    def test_variable(self):
        self.assertEqual(
            self.receipt["empirical_admission_receipt"]["variable_id"],
            "electricity.consumption_rate",
        )

    def test_raw_sha256(self):
        p=Path(self.receipt["source"]["raw_file"])
        self.assertEqual(len(p.read_bytes()),168)
        self.assertEqual(
            hashlib.sha256(p.read_bytes()).hexdigest(),
            "831ed964ef11527f0d8db767665289b59f5ef7b32fac02cd7667ad4b949a7242",
        )

    def test_admit_observed(self):
        a=self.receipt["empirical_admission_receipt"]
        self.assertEqual(a["decision"],"ADMIT_OBSERVED")
        self.assertEqual((a["canonical_value_n"],a["canonical_value_d"]),(22557000000,1))

    def test_unit_transform(self):
        u=self.receipt["unit_transform_receipt"]
        self.assertEqual(u["source_unit"],"MW")
        self.assertEqual(u["canonical_unit"],"W_e")
        self.assertEqual((u["factor_n"],u["factor_d"]),(1000000,1))

    def test_spatial_mapping_source_local(self):
        s=self.receipt["spatial_mapping_receipt"]
        self.assertEqual(s["method"],"NODE_LOOKUP")
        self.assertEqual(s["target_node_class"],"ELECTRICITY_ZONE")
        self.assertEqual(
            s["claim_ceiling"],
            "ELEXON_INDO_NATIONAL_DEMAND_ACCOUNTING_ONLY__NOT_TOTAL_FINAL_ELECTRICITY_CONSUMPTION",
        )

    def test_temporal_exact_no_aggregation(self):
        t=self.receipt["temporal_alignment_receipt"]
        self.assertEqual(t["method"],"EXACT_INTERVAL")
        self.assertEqual(t["duration_seconds"],1800)
        self.assertFalse(t["aggregation_performed"])
        self.assertFalse(t["interpolation_used"])
        self.assertFalse(t["imputation_used"])

    def test_freshness(self):
        f=self.receipt["freshness_readback"]
        self.assertEqual(f["age_seconds"],2714)
        self.assertTrue(f["fresh_at_admission"])

    def test_uncertainty_unknown(self):
        u=self.receipt["uncertainty_declaration"]
        self.assertEqual(u["kind"],"UNKNOWN")
        self.assertFalse(u["promotion_to_exact"])

    def test_missingness(self):
        m=self.receipt["missingness_semantics"]
        self.assertTrue(m["value_present"])
        self.assertEqual(m["source_status"],"OBSERVED")
        self.assertFalse(m["zero_is_missing"])

    def test_same_empirical_contract(self):
        self.assertTrue(self.receipt["same_admission_contract"])

    def test_first_canary_preserved(self):
        self.assertTrue(self.receipt["first_canary_preserved"])

    def test_scope_fences(self):
        f=self.receipt["fences"]
        for key in ("multi_source_fusion","aggregation","eq_score","ui","runtime_admission","pointer_promotion","global_bind","merge"):
            self.assertFalse(f[key],key)

    def test_deterministic_receipt(self):
        a=c.run_canary()
        b=c.run_canary()
        ja=json.dumps(a,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        jb=json.dumps(b,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        self.assertEqual(ja,jb)


if __name__ == "__main__":
    unittest.main(verbosity=2)
