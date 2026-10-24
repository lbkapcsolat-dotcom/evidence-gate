import hashlib
import json
from pathlib import Path
import unittest

import planetary_resource_third_real_source_gas_canary_v1 as c


class ThirdRealSourceGasCanary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = c.run_canary()

    def test_one_source_variable_node_interval(self):
        self.assertEqual(
            self.receipt["counts"],
            {
                "measurement_sources":1,
                "variables":1,
                "nodes":1,
                "intervals":1,
                "records":1,
                "normative_support_refs":3,
            },
        )

    def test_natural_gas_layer(self):
        a=self.receipt["empirical_admission_receipt"]
        self.assertEqual(a["layer"],"NATURAL_GAS")
        self.assertEqual(a["variable_id"],"natural_gas.import_rate")

    def test_raw_source_bytes(self):
        p=Path(self.receipt["measurement_source"]["raw_file"])
        self.assertEqual(len(p.read_bytes()),931)
        self.assertEqual(
            hashlib.sha256(p.read_bytes()).hexdigest(),
            "a7f15400b518ec51ac0f6a97696bd7cd261e64730d1a348dc1a2ad0be0956928",
        )

    def test_source_unit_is_kwh_per_hour(self):
        self.assertEqual(self.receipt["record"]["unit"],"kWh/h")

    def test_explicit_gcv_hhv_basis(self):
        e=self.receipt["energy_basis_receipt"]
        self.assertEqual(e["source_energy_basis"],"GCV")
        self.assertEqual(e["core_basis_label"],"HHV")
        self.assertTrue(e["gcv_to_hhv_terminology_evidence"])

    def test_no_volume_to_energy_conversion(self):
        e=self.receipt["energy_basis_receipt"]
        self.assertFalse(e["volume_to_energy_conversion_performed"])
        self.assertFalse(e["numeric_calorific_value_used"])

    def test_admit_observed(self):
        a=self.receipt["empirical_admission_receipt"]
        self.assertEqual(a["decision"],"ADMIT_OBSERVED")
        self.assertEqual(
            (a["canonical_value_n"],a["canonical_value_d"]),
            (28669751000,1),
        )
        self.assertEqual(a["canonical_unit"],"W_th")

    def test_two_stage_unit_transform(self):
        u=self.receipt["unit_transform_receipt"]
        self.assertEqual(u["source_stage"]["from"],"kWh/h_GCV")
        self.assertEqual(u["source_stage"]["to"],"kW_HHV")
        self.assertEqual((u["source_stage"]["factor_n"],u["source_stage"]["factor_d"]),(1,1))
        self.assertEqual((u["contract_stage"]["factor_n"],u["contract_stage"]["factor_d"]),(1000,1))

    def test_source_local_spatial_mapping(self):
        s=self.receipt["spatial_mapping_receipt"]
        self.assertEqual(s["method"],"NODE_LOOKUP")
        self.assertEqual(s["target_node_class"],"GAS_ZONE")
        self.assertEqual(
            s["claim_ceiling"],
            "SOURCE_LOCAL_ENTSOG_ENTRY_FLOW_ONLY__NOT_GERMAN_TOTAL_GAS_IMPORT",
        )

    def test_exact_interval_no_aggregation(self):
        t=self.receipt["temporal_alignment_receipt"]
        self.assertEqual(t["method"],"EXACT_INTERVAL")
        self.assertFalse(t["aggregation_performed"])
        self.assertFalse(t["interpolation_used"])
        self.assertFalse(t["imputation_used"])

    def test_freshness(self):
        f=self.receipt["freshness_readback"]
        self.assertEqual(f["age_seconds"],6685)
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

    def test_water_and_electricity_preserved(self):
        self.assertTrue(self.receipt["water_canary_preserved"])
        self.assertTrue(self.receipt["electricity_canary_preserved"])

    def test_same_empirical_contract(self):
        self.assertTrue(self.receipt["same_admission_contract"])

    def test_scope_fences(self):
        f=self.receipt["fences"]
        for key in (
            "multi_source_fusion","aggregation","eq_score","ui",
            "runtime_admission","pointer_promotion","global_bind","merge",
        ):
            self.assertFalse(f[key],key)

    def test_deterministic_receipt(self):
        a=c.run_canary()
        b=c.run_canary()
        ja=json.dumps(a,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        jb=json.dumps(b,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        self.assertEqual(ja,jb)


if __name__ == "__main__":
    unittest.main(verbosity=2)
