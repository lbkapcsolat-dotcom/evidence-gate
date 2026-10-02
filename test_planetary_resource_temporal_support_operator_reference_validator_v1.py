import hashlib
import json
import unittest
from fractions import Fraction

import planetary_resource_temporal_support_operator_reference_validator_v1 as gate


class TemporalSupportOperatorReferenceValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = gate.run_gate()
        cls.fx = cls.receipt["fixtures"]

    def test_required_reference_fixture_matrix_passes_without_path_b_activation(self):
        self.assertEqual(
            self.receipt["verdict"],
            "PASS_BOUNDED_TEMPORAL_SUPPORT_OPERATOR_REFERENCE_VALIDATOR",
        )
        self.assertEqual(self.receipt["fixture_count"], 9)
        self.assertEqual(self.receipt["path_b_status"], "LOCKED_NOT_ACTIVATED")

    def test_predecessor_formal_spec_is_exactly_pinned(self):
        p = self.receipt["predecessor"]
        self.assertEqual(
            p["receipt_sha256"],
            "f8c9d8eebacd3fbc19111fe4d9e5600eb6555ce58709666652e06b6beff5ca5a",
        )
        self.assertEqual(
            p["head_sha"],
            "ce1d2d9f4c86c9c2118797768efb6656b9580f94",
        )
        self.assertEqual(
            p["verdict"],
            "PASS_BOUNDED_FORMAL_TEMPORAL_SUPPORT_OPERATOR_SPEC",
        )

    def test_exact_support_identity_passes(self):
        r = self.fx["EXACT_SUPPORT_IDENTITY"]
        self.assertEqual(r["decision"], "PASS_IDENTITY")
        self.assertIsNone(r["hold_code"])
        self.assertEqual((r["value_n"], r["value_d"]), (7, 1))
        self.assertEqual(r["uncertainty_kind"], "EXACT")
        self.assertEqual(r["support_relation"], "EXACT_TARGET_SUPPORT")
        self.assertEqual(r["formula_id"], "IDENTITY_V1")

    def test_two_native_15min_means_form_conservative_30min_mean(self):
        r = self.fx["TWO_15MIN_NATIVE_MEANS_TO_ONE_30MIN_TARGET"]
        self.assertEqual(r["decision"], "PASS_CONSERVATIVE")
        self.assertEqual((r["value_n"], r["value_d"]), (15, 1))
        lhs = Fraction(r["conservation_lhs_n"], r["conservation_lhs_d"])
        rhs = Fraction(r["conservation_rhs_n"], r["conservation_rhs_d"])
        self.assertEqual(lhs, Fraction(27000))
        self.assertEqual(rhs, Fraction(27000))
        self.assertEqual(lhs, rhs)
        self.assertEqual(
            r["formula_id"],
            "TIME_MEAN_PARTITION_WEIGHTED_BY_EXPLICIT_DURATION_V1",
        )

    def test_one_60min_mean_cannot_determine_30min_target(self):
        r = self.fx["ONE_60MIN_MEAN_TO_30MIN_TARGET"]
        self.assertEqual(r["decision"], "HOLD")
        self.assertEqual(
            r["hold_code"],
            "HOLD_TEMPORAL_INFORMATION_INSUFFICIENT",
        )

    def test_partition_gap_and_overlap_fail_closed(self):
        for fixture_id in ("PARTITION_WITH_GAP", "PARTITION_WITH_OVERLAP"):
            r = self.fx[fixture_id]
            self.assertEqual(r["decision"], "HOLD")
            self.assertEqual(
                r["hold_code"],
                "HOLD_TEMPORAL_PARTITION_OVERLAP_OR_GAP",
            )

    def test_unknown_uncertainty_remains_unknown(self):
        r = self.fx["UNKNOWN_UNCERTAINTY"]
        self.assertEqual(r["decision"], "PASS_IDENTITY")
        self.assertEqual(r["uncertainty_kind"], "UNKNOWN")
        self.assertEqual((r["value_n"], r["value_d"]), (9, 1))

    def test_moment_without_covariance_holds(self):
        r = self.fx["MOMENT_WITHOUT_COVARIANCE"]
        self.assertEqual(r["decision"], "HOLD")
        self.assertEqual(
            r["hold_code"],
            "HOLD_TEMPORAL_UNCERTAINTY_OPERATOR",
        )

    def test_incomplete_provenance_holds(self):
        r = self.fx["INCOMPLETE_PROVENANCE"]
        self.assertEqual(r["decision"], "HOLD")
        self.assertEqual(
            r["hold_code"],
            "HOLD_TEMPORAL_PROVENANCE_INCOMPLETE",
        )

    def test_unpinned_operator_version_holds(self):
        r = self.fx["UNPINNED_OPERATOR_VERSION"]
        self.assertEqual(r["decision"], "HOLD")
        self.assertEqual(
            r["hold_code"],
            "HOLD_TEMPORAL_OPERATOR_VERSION_UNPINNED",
        )

    def test_no_real_execution_activation_or_composition_occurs(self):
        p = self.receipt["execution_policy"]
        self.assertTrue(p["path_b_remains_locked"])
        self.assertTrue(p["reference_validator_only"])
        self.assertFalse(p["real_source_transformation"])
        self.assertFalse(p["operator_activation"])
        self.assertFalse(p["real_value_composition"])
        self.assertFalse(self.receipt["real_source_transformation_performed"])
        self.assertFalse(self.receipt["real_value_composition_performed"])
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
