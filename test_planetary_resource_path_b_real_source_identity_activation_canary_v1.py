import hashlib
import json
import unittest

import planetary_resource_path_b_real_source_identity_activation_canary_v1 as gate


class PathBRealSourceIdentityActivationCanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = gate.run_gate()

    def test_real_elexon_identity_canary_activates_path_b_locally_only(self):
        self.assertEqual(
            self.receipt["verdict"],
            "PASS_BOUNDED_PATH_B_REAL_SOURCE_IDENTITY_ACTIVATION_CANARY",
        )
        activation = self.receipt["activation"]
        self.assertEqual(activation["target_path"], "PATH_B")
        self.assertEqual(activation["scope"], "CANARY_LOCAL_IDENTITY_ONLY")
        self.assertTrue(activation["active_during_canary"])
        self.assertFalse(activation["global_activation"])
        self.assertFalse(activation["runtime_admission"])
        self.assertEqual(
            activation["post_canary_global_state"],
            "LOCKED_NOT_GLOBALLY_ACTIVATED",
        )

    def test_executable_kernel_predecessor_is_exactly_pinned(self):
        p = self.receipt["predecessor"]
        self.assertEqual(
            p["receipt_sha256"],
            "3383f715a41126f7218b79e52d1ca7bcd6946effa9b70fa5a1af237b2f38e18b",
        )
        self.assertEqual(
            p["head_sha"],
            "801bbf18be64995f7f5ebef155bf310dc35da231",
        )
        self.assertEqual(
            p["verdict"],
            "PASS_BOUNDED_TEMPORAL_SUPPORT_OPERATOR_EXECUTABLE_KERNEL",
        )

    def test_real_elexon_raw_bytes_and_sha_are_bound(self):
        s = self.receipt["source"]
        self.assertEqual(s["provider"], "Elexon Insights Solution")
        self.assertEqual(s["dataset"], "INDO")
        self.assertEqual(
            s["variable_id"],
            "electricity.consumption_rate",
        )
        self.assertEqual(
            s["raw_path"],
            "sources/elexon/INDO_outturn_alignment_window_2026-09-30.json",
        )
        self.assertEqual(s["raw_bytes"], 278348)
        self.assertEqual(
            s["raw_sha256"],
            "2a91d6b47379b47e4d8cfdb220d90c890ce416ebcd094b9810de70d47db12564",
        )
        self.assertEqual(s["record_start_utc"], "2026-09-30T12:00:00Z")
        self.assertEqual(s["record_field"], "initialDemandOutturn")
        self.assertEqual((s["record_value_n"], s["record_value_d"]), (21575, 1))
        self.assertEqual(s["source_unit"], "MW")
        self.assertEqual(s["uncertainty_kind"], "UNKNOWN")

    def test_target_support_is_exact_30_minutes(self):
        target = self.receipt["target_window"]
        self.assertEqual(target["start_utc"], "2026-09-30T12:00:00Z")
        self.assertEqual(target["end_utc"], "2026-09-30T12:30:00Z")
        self.assertEqual(target["duration_seconds"], 1800)

        result = self.receipt["kernel_result"]
        self.assertEqual(result["decision"], "PASS_IDENTITY")
        self.assertIsNone(result["hold_code"])
        self.assertEqual(result["support_relation"], "EXACT_TARGET_SUPPORT")
        self.assertEqual(result["formula_id"], "IDENTITY_V1")

    def test_identity_output_equals_real_input_exactly(self):
        source = self.receipt["source"]
        result = self.receipt["kernel_result"]
        self.assertEqual(
            (result["value_n"], result["value_d"]),
            (source["record_value_n"], source["record_value_d"]),
        )
        self.assertEqual((result["value_n"], result["value_d"]), (21575, 1))
        self.assertTrue(self.receipt["output_equals_input_exactly"])

    def test_unknown_uncertainty_is_preserved(self):
        self.assertEqual(
            self.receipt["kernel_result"]["uncertainty"]["kind"],
            "UNKNOWN",
        )
        self.assertTrue(self.receipt["unknown_uncertainty_preserved"])

    def test_real_operator_transform_record_binds_raw_source_and_identity(self):
        r = self.receipt["operator_transform_record"]
        self.assertEqual(
            r["operator_spec_id"],
            "TEMPORAL_SUPPORT_TO_TARGET_WINDOW_OPERATOR_V1",
        )
        self.assertEqual(r["operator_version"], "V1")
        self.assertEqual(
            r["kernel_receipt_sha256"],
            "3383f715a41126f7218b79e52d1ca7bcd6946effa9b70fa5a1af237b2f38e18b",
        )
        self.assertEqual(
            r["source_raw_sha256"],
            "2a91d6b47379b47e4d8cfdb220d90c890ce416ebcd094b9810de70d47db12564",
        )
        self.assertEqual(r["support_relation"], "EXACT_TARGET_SUPPORT")
        self.assertEqual(r["formula_id"], "IDENTITY_V1")
        self.assertEqual(
            (r["source_value_n"], r["source_value_d"]),
            (r["output_value_n"], r["output_value_d"]),
        )
        self.assertEqual(r["source_uncertainty_kind"], "UNKNOWN")
        self.assertEqual(r["output_uncertainty_kind"], "UNKNOWN")
        self.assertEqual(r["hold_codes"], [])
        self.assertTrue(self.receipt["real_raw_sha256_provenance_bound"])

    def test_forbidden_surfaces_remain_closed(self):
        self.assertFalse(self.receipt["partition_aggregation_performed"])
        self.assertFalse(self.receipt["gas_input_used"])
        self.assertFalse(self.receipt["freshwater_input_used"])
        self.assertFalse(self.receipt["cross_source_composition_performed"])
        self.assertFalse(self.receipt["coarse_to_fine_performed"])
        self.assertFalse(self.receipt["interpolation_performed"])
        self.assertFalse(self.receipt["imputation_performed"])
        self.assertFalse(self.receipt["core_patch_required"])
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
