import hashlib
import json
import unittest

import planetary_resource_native_common_support_replacement_and_integration_retry_v1 as gate


class NativeCommonSupportReplacementAndIntegrationRetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = gate.run_gate()

    def test_gate_holds_if_exact_native_gas_or_freshwater_support_is_unavailable(self):
        self.assertEqual(
            self.receipt["verdict"],
            "HOLD_EXACT_NATIVE_COMMON_SUPPORT_NOT_AVAILABLE",
        )
        self.assertFalse(self.receipt["integration_retry"]["performed"])

    def test_predecessor_is_exactly_pinned(self):
        self.assertEqual(
            self.receipt["predecessor"]["receipt_sha256"],
            "da2473f8272c137e5c8315706677c459cbd9a0690819c10a71654bf336635437",
        )
        self.assertEqual(
            self.receipt["predecessor"]["head_sha"],
            "459d7057514e9b716ee7051ccbbae42d41b43bf9",
        )

    def test_fixed_elexon_source_remains_exact_target_match(self):
        e = self.receipt["electricity"]
        self.assertEqual(e["status"], "READY_EXACT_INTERVAL")
        self.assertEqual(e["native_interval_start"], "2026-09-30T12:00:00Z")
        self.assertEqual(e["native_interval_end"], "2026-09-30T12:30:00Z")
        self.assertEqual(
            e["raw_sha256"],
            "2a91d6b47379b47e4d8cfdb220d90c890ce416ebcd094b9810de70d47db12564",
        )
        self.assertFalse(e["replacement_required"])

    def test_bounded_gas_discovery_did_not_prove_exact_30_minute_native_product(self):
        g = self.receipt["replacement_discovery"]["natural_gas"]
        self.assertFalse(g["exact_native_source_found"])
        self.assertEqual(g["status"], "NOT_FOUND_WITHIN_TESTED_OFFICIAL_SURFACES")
        self.assertGreaterEqual(len(g["tested_official_surfaces"]), 2)
        self.assertTrue(
            all(not x["exact_30_minute_interval_product_proven"]
                for x in g["tested_official_surfaces"])
        )

    def test_bounded_freshwater_discovery_did_not_prove_exact_30_minute_native_product(self):
        w = self.receipt["replacement_discovery"]["freshwater"]
        self.assertFalse(w["exact_native_source_found"])
        self.assertEqual(w["status"], "NOT_FOUND_WITHIN_TESTED_OFFICIAL_SURFACES")
        self.assertGreaterEqual(len(w["tested_official_surfaces"]), 2)
        self.assertTrue(
            all(not x["exact_30_minute_interval_product_proven"]
                for x in w["tested_official_surfaces"])
        )

    def test_no_prohibited_temporal_transform_is_used(self):
        t = self.receipt["prohibited_transforms_performed"]
        self.assertFalse(t["interpolation"])
        self.assertFalse(t["imputation"])
        self.assertFalse(t["aggregation"])
        self.assertFalse(t["downscaling"])
        self.assertFalse(t["inferred_boundaries"])

    def test_core_and_claim_fences_remain_closed(self):
        self.assertFalse(self.receipt["core_patch_required"])
        self.assertFalse(self.receipt["new_domain_math_added"])
        self.assertFalse(any(self.receipt["fences"].values()))
        self.assertIn("does not assert", self.receipt["claim_ceiling"])

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
