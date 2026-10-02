import hashlib
import json
import unittest

import planetary_resource_aligned_real_input_integration_canary_v1 as gate


class AlignedRealInputIntegrationCanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = gate.run_gate()

    def test_common_window_integration_fails_closed_on_temporal_support_mismatch(self):
        self.assertEqual(
            self.receipt["verdict"],
            "HOLD_BOUNDED_ALIGNED_REAL_INPUT_INTEGRATION_TEMPORAL_SUPPORT_MISMATCH",
        )
        common = self.receipt["common_window_integration"]
        self.assertFalse(common["admitted"])
        self.assertEqual(common["ready_sources"], ["electricity"])
        self.assertEqual(common["blocked_sources"], ["natural_gas", "freshwater"])
        self.assertEqual(common["hold_code"], "HOLD_TEMPORAL_METHOD_INVALID")

    def test_predecessor_receipt_is_exactly_pinned(self):
        self.assertEqual(
            self.receipt["predecessor"]["receipt_sha256"],
            "37c126d316fb6bec50fb9357dfd485ea7b5f31c4f523508891567f785e21f672",
        )
        self.assertEqual(
            self.receipt["predecessor"]["head_sha"],
            "2c317726519317a65ce95728d08f8a837aa9b32b",
        )

    def test_elexon_maps_only_to_electricity_demand(self):
        s = self.receipt["slot_mappings"]["electricity"]
        self.assertEqual(s["variable_id"], "electricity.consumption_rate")
        self.assertEqual(s["slot"], "DEMAND")
        self.assertEqual(s["canonical_value_n"], 21_575_000_000)
        self.assertEqual(s["canonical_value_d"], 1)
        self.assertEqual(s["canonical_unit"], "W_e")
        effect = self.receipt["source_native_core_effects"]["electricity"]["E0"]
        self.assertEqual((effect["value_n"], effect["value_d"]), (-21_575_000_000, 1))
        self.assertEqual(effect["uncertainty_kind"], "UNKNOWN")

    def test_entsog_maps_only_to_gas_boundary_import(self):
        s = self.receipt["slot_mappings"]["natural_gas"]
        self.assertEqual(s["variable_id"], "natural_gas.import_rate")
        self.assertEqual(s["slot"], "BOUNDARY_IMPORT")
        self.assertEqual(s["canonical_value_n"], 26_823_568_000)
        self.assertEqual(s["canonical_value_d"], 1)
        self.assertEqual(s["canonical_unit"], "W_th")
        self.assertEqual(s["gas_basis"], "HHV")
        effect = self.receipt["source_native_core_effects"]["natural_gas"]["G0"]
        self.assertEqual((effect["value_n"], effect["value_d"]), (26_823_568_000, 1))
        self.assertEqual(effect["uncertainty_kind"], "UNKNOWN")

    def test_bom_maps_only_to_directed_freshwater_internal_edge(self):
        s = self.receipt["slot_mappings"]["freshwater"]
        self.assertEqual(s["variable_id"], "freshwater.internal_flow_rate")
        self.assertEqual(s["slot"], "INTERNAL_FLOW")
        self.assertFalse(s["relabel_as_production_or_demand"])
        self.assertEqual((s["canonical_value_n"], s["canonical_value_d"]), (189, 500))
        self.assertEqual(s["canonical_unit"], "m3/s")
        effects = self.receipt["source_native_core_effects"]["freshwater"]
        self.assertEqual((effects["W0"]["value_n"], effects["W0"]["value_d"]), (-189, 500))
        self.assertEqual((effects["W1"]["value_n"], effects["W1"]["value_d"]), (189, 500))
        self.assertEqual(effects["W0"]["uncertainty_kind"], "UNKNOWN")
        self.assertEqual(effects["W1"]["uncertainty_kind"], "UNKNOWN")

    def test_fixture_only_water_topology_extension_uses_frozen_incidence_kernel(self):
        t = self.receipt["topology_extension"]
        self.assertTrue(t["integration_fixture_only"])
        self.assertFalse(t["core_patch"])
        self.assertEqual(t["nodes"], ["W0", "W1"])
        self.assertEqual(
            t["edge"],
            {
                "edge_id": "W_REAL_INTERNAL_0",
                "source_node_id": "W0",
                "target_node_id": "W1",
            },
        )
        self.assertEqual(t["incidence_matrix"], [["-1"], ["1"]])
        self.assertTrue(t["structurally_valid"])

    def test_frozen_exact_interval_guard_accepts_only_elexon(self):
        temporal = self.receipt["temporal_support_guard"]
        self.assertEqual(
            temporal["electricity"]["decision"],
            "READY_EXACT_INTERVAL",
        )
        for key in ("natural_gas", "freshwater"):
            self.assertEqual(temporal[key]["decision"], "HOLD")
            self.assertEqual(
                temporal[key]["hold_code"],
                "HOLD_TEMPORAL_METHOD_INVALID",
            )

    def test_raw_sha_provenance_and_unknown_uncertainty_are_preserved(self):
        expected = {
            "electricity": "2a91d6b47379b47e4d8cfdb220d90c890ce416ebcd094b9810de70d47db12564",
            "natural_gas": "889e9bf2e6365893bfed18a50291a0d130559fa1e38484c71d8e278e82f64be5",
            "freshwater": "1fe8f1416b69377160ed6c9fced011785a46e7cb52eac46ce783a424c3e7ee14",
        }
        for key, sha in expected.items():
            source = self.receipt["slot_mappings"][key]
            self.assertEqual(source["raw_sha256"], sha)
            self.assertTrue(source["source_url"].startswith("https://"))
            self.assertEqual(source["uncertainty_kind"], "UNKNOWN")
        self.assertTrue(self.receipt["raw_sha256_preserved"])
        self.assertTrue(self.receipt["source_provenance_preserved"])
        self.assertTrue(self.receipt["unknown_uncertainty_preserved"])

    def test_no_prohibited_temporal_or_cross_source_transform_occurs(self):
        t = self.receipt["transforms"]
        self.assertFalse(t["interpolation_performed"])
        self.assertFalse(t["imputation_performed"])
        self.assertFalse(t["cross_interval_aggregation_performed"])
        self.assertFalse(t["implicit_downscaling_performed"])
        self.assertFalse(t["cross_source_arithmetic_performed"])

    def test_claim_ceiling_and_fences_remain_closed(self):
        self.assertFalse(self.receipt["core_patch_required"])
        self.assertFalse(self.receipt["new_domain_math_added"])
        self.assertTrue(self.receipt["integrated_real_input_receipt_emitted"])
        self.assertTrue(self.receipt["version_validity_topology_guard_replay_required"])
        self.assertFalse(any(self.receipt["fences"].values()))

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
