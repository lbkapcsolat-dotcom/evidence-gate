import hashlib
import json
import unittest
from fractions import Fraction

import planetary_resource_path_b_three_provider_native_identity_canary_v1 as gate


class PathBThreeProviderNativeIdentityCanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = gate.run_gate()
        cls.providers = cls.receipt["providers"]

    def test_three_real_providers_pass_native_identity_without_common_window(self):
        self.assertEqual(
            self.receipt["verdict"],
            "PASS_BOUNDED_PATH_B_THREE_PROVIDER_NATIVE_IDENTITY_CANARY",
        )
        self.assertEqual(self.receipt["provider_count"], 3)
        self.assertEqual(self.receipt["pass_identity_count"], 3)
        self.assertTrue(self.receipt["three_of_three_pass_identity"])
        self.assertFalse(self.receipt["common_window_computed"])

    def test_elexon_identity_predecessor_is_exactly_pinned(self):
        p = self.receipt["predecessor"]
        self.assertEqual(
            p["receipt_sha256"],
            "9a0c62c606a8c688ea535b02f2a6ba390e4a6d4f61fe7698ff7a09546d3c70af",
        )
        self.assertEqual(
            p["head_sha"],
            "9d570e518ae0027357fe8fe4c554ca3f62a8b692",
        )
        self.assertEqual(
            p["verdict"],
            "PASS_BOUNDED_PATH_B_REAL_SOURCE_IDENTITY_ACTIVATION_CANARY",
        )

    def test_path_b_activation_remains_canary_local(self):
        a = self.receipt["activation"]
        self.assertEqual(a["target_path"], "PATH_B")
        self.assertEqual(a["scope"], "CANARY_LOCAL_THREE_PROVIDER_IDENTITY_ONLY")
        self.assertTrue(a["active_during_canary"])
        self.assertFalse(a["global_activation"])
        self.assertFalse(a["runtime_admission"])
        self.assertEqual(
            a["post_canary_global_state"],
            "LOCKED_NOT_GLOBALLY_ACTIVATED",
        )

    def test_elexon_native_identity(self):
        r = self.providers["electricity"]
        self.assertEqual(r["decision"], "PASS_IDENTITY")
        self.assertEqual(r["support_relation"], "EXACT_TARGET_SUPPORT")
        self.assertEqual(r["formula_id"], "IDENTITY_V1")
        self.assertEqual(
            (r["input_value_n"], r["input_value_d"]),
            (21575, 1),
        )
        self.assertEqual(
            (r["output_value_n"], r["output_value_d"]),
            (21575, 1),
        )
        self.assertEqual(r["uncertainty_kind"], "UNKNOWN")
        self.assertEqual(
            r["native_interval"],
            {
                "start_utc": "2026-09-30T12:00:00Z",
                "end_utc": "2026-09-30T12:30:00Z",
            },
        )
        self.assertEqual(
            r["raw_sha256"],
            "2a91d6b47379b47e4d8cfdb220d90c890ce416ebcd094b9810de70d47db12564",
        )

    def test_entsog_native_identity(self):
        r = self.providers["natural_gas"]
        self.assertEqual(r["decision"], "PASS_IDENTITY")
        self.assertEqual(r["support_relation"], "EXACT_TARGET_SUPPORT")
        self.assertEqual(r["formula_id"], "IDENTITY_V1")
        self.assertEqual(
            (r["input_value_n"], r["input_value_d"]),
            (26823568, 1),
        )
        self.assertEqual(
            (r["output_value_n"], r["output_value_d"]),
            (26823568, 1),
        )
        self.assertEqual(r["source_unit"], "kWh/h")
        self.assertEqual(r["uncertainty_kind"], "UNKNOWN")
        self.assertEqual(
            r["native_interval"],
            {
                "start_utc": "2026-09-30T12:00:00Z",
                "end_utc": "2026-09-30T13:00:00Z",
            },
        )
        self.assertEqual(
            r["raw_sha256"],
            "889e9bf2e6365893bfed18a50291a0d130559fa1e38484c71d8e278e82f64be5",
        )

    def test_bom_native_identity(self):
        r = self.providers["freshwater"]
        self.assertEqual(r["decision"], "PASS_IDENTITY")
        self.assertEqual(r["support_relation"], "EXACT_TARGET_SUPPORT")
        self.assertEqual(r["formula_id"], "IDENTITY_V1")
        self.assertEqual(
            Fraction(r["input_value_n"], r["input_value_d"]),
            Fraction(189, 500),
        )
        self.assertEqual(
            Fraction(r["output_value_n"], r["output_value_d"]),
            Fraction(189, 500),
        )
        self.assertEqual(r["source_unit"], "cumec")
        self.assertEqual(r["uncertainty_kind"], "UNKNOWN")
        self.assertEqual(
            r["native_interval"],
            {
                "start_utc": "2026-09-29T14:00:00Z",
                "end_utc": "2026-09-30T14:00:00Z",
            },
        )
        self.assertEqual(
            r["raw_sha256"],
            "1fe8f1416b69377160ed6c9fced011785a46e7cb52eac46ce783a424c3e7ee14",
        )

    def test_all_outputs_equal_inputs_and_unknown_uncertainty_is_preserved(self):
        for r in self.providers.values():
            self.assertEqual(
                (r["input_value_n"], r["input_value_d"]),
                (r["output_value_n"], r["output_value_d"]),
            )
            self.assertEqual(r["uncertainty_kind"], "UNKNOWN")
        self.assertTrue(self.receipt["output_equals_input_exactly_3_of_3"])
        self.assertTrue(self.receipt["unknown_uncertainty_preserved_3_of_3"])

    def test_each_provider_keeps_its_own_native_interval(self):
        intervals = self.receipt["provider_native_intervals"]
        self.assertEqual(len(set(tuple(v) for v in intervals.values())), 3)
        self.assertTrue(self.receipt["each_provider_kept_own_native_interval"])
        self.assertFalse(
            self.receipt["temporal_alignment_between_providers_performed"]
        )
        self.assertFalse(self.receipt["common_window_computed"])

    def test_real_provenance_binds_each_raw_source(self):
        expected = {
            "electricity":
                "2a91d6b47379b47e4d8cfdb220d90c890ce416ebcd094b9810de70d47db12564",
            "natural_gas":
                "889e9bf2e6365893bfed18a50291a0d130559fa1e38484c71d8e278e82f64be5",
            "freshwater":
                "1fe8f1416b69377160ed6c9fced011785a46e7cb52eac46ce783a424c3e7ee14",
        }
        for key, r in self.providers.items():
            p = r["provenance_transform_record"]
            self.assertEqual(p["source_raw_sha256"], expected[key])
            self.assertEqual(p["support_relation"], "EXACT_TARGET_SUPPORT")
            self.assertEqual(p["formula_id"], "IDENTITY_V1")
            self.assertEqual(p["output_uncertainty_kind"], "UNKNOWN")
            self.assertEqual(p["hold_codes"], [])
            self.assertFalse(p["partition_aggregation_performed"])
            self.assertFalse(p["cross_source_composition_performed"])
            self.assertFalse(
                p["temporal_alignment_between_providers_performed"]
            )
        self.assertTrue(self.receipt["raw_sha256_provenance_bound_3_of_3"])

    def test_forbidden_surfaces_remain_closed(self):
        self.assertFalse(self.receipt["partition_aggregation_performed"])
        self.assertFalse(self.receipt["cross_source_composition_performed"])
        self.assertFalse(self.receipt["interpolation_performed"])
        self.assertFalse(self.receipt["imputation_performed"])
        self.assertFalse(self.receipt["coarse_to_fine_performed"])
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
