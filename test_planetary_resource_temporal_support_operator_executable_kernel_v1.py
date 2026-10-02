import hashlib
import json
import unittest
from fractions import Fraction

import planetary_resource_temporal_support_operator_executable_kernel_v1 as gate


class TemporalSupportOperatorExecutableKernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = gate.run_gate()
        cls.replay = cls.receipt["reference_replay"]

    def test_executable_kernel_replays_reference_matrix_without_path_b_activation(self):
        self.assertEqual(
            self.receipt["verdict"],
            "PASS_BOUNDED_TEMPORAL_SUPPORT_OPERATOR_EXECUTABLE_KERNEL",
        )
        self.assertEqual(self.receipt["reference_replay_count"], 9)
        self.assertTrue(self.receipt["reference_replay_9_of_9"])
        self.assertEqual(self.receipt["path_b_status"], "LOCKED_NOT_ACTIVATED")

    def test_reference_validator_and_formal_spec_are_exactly_pinned(self):
        predecessor = self.receipt["predecessor"]
        self.assertEqual(
            predecessor["receipt_sha256"],
            "152ecba00cfcb9e22f767b654bd04631222fb73a3d4666d9ce4e635647267973",
        )
        self.assertEqual(
            predecessor["head_sha"],
            "cc0ddb1eabc19941348e7639fb5506a5863596ad",
        )
        formal = self.receipt["formal_spec"]
        self.assertEqual(
            formal["receipt_sha256"],
            "f8c9d8eebacd3fbc19111fe4d9e5600eb6555ce58709666652e06b6beff5ca5a",
        )
        self.assertEqual(
            formal["operator_spec_id"],
            "TEMPORAL_SUPPORT_TO_TARGET_WINDOW_OPERATOR_V1",
        )
        self.assertEqual(formal["operator_version"], "V1")
        self.assertEqual(
            formal["policy_receipt_sha256"],
            "5cfbb2feb2b7485e5f791f062794929e134981277d6c29679b7cbc12219fb6b9",
        )

    def test_all_nine_reference_outcomes_match_frozen_expected_results(self):
        expected = {
            "EXACT_SUPPORT_IDENTITY": ("PASS_IDENTITY", None),
            "TWO_15MIN_NATIVE_MEANS_TO_ONE_30MIN_TARGET": (
                "PASS_CONSERVATIVE",
                None,
            ),
            "ONE_60MIN_MEAN_TO_30MIN_TARGET": (
                "HOLD",
                "HOLD_TEMPORAL_INFORMATION_INSUFFICIENT",
            ),
            "PARTITION_WITH_GAP": (
                "HOLD",
                "HOLD_TEMPORAL_PARTITION_OVERLAP_OR_GAP",
            ),
            "PARTITION_WITH_OVERLAP": (
                "HOLD",
                "HOLD_TEMPORAL_PARTITION_OVERLAP_OR_GAP",
            ),
            "UNKNOWN_UNCERTAINTY": ("PASS_IDENTITY", None),
            "MOMENT_WITHOUT_COVARIANCE": (
                "HOLD",
                "HOLD_TEMPORAL_UNCERTAINTY_OPERATOR",
            ),
            "INCOMPLETE_PROVENANCE": (
                "HOLD",
                "HOLD_TEMPORAL_PROVENANCE_INCOMPLETE",
            ),
            "UNPINNED_OPERATOR_VERSION": (
                "HOLD",
                "HOLD_TEMPORAL_OPERATOR_VERSION_UNPINNED",
            ),
        }
        self.assertEqual(set(self.replay), set(expected))
        for fixture_id, (decision, hold_code) in expected.items():
            self.assertEqual(self.replay[fixture_id]["decision"], decision)
            self.assertEqual(self.replay[fixture_id]["hold_code"], hold_code)

    def test_identity_and_conservative_paths_use_exact_rational_arithmetic(self):
        identity = self.replay["EXACT_SUPPORT_IDENTITY"]
        self.assertEqual((identity["value_n"], identity["value_d"]), (7, 1))
        self.assertEqual(identity["formula_id"], "IDENTITY_V1")

        conservative = self.replay[
            "TWO_15MIN_NATIVE_MEANS_TO_ONE_30MIN_TARGET"
        ]
        self.assertEqual(
            (conservative["value_n"], conservative["value_d"]),
            (15, 1),
        )
        lhs = Fraction(
            conservative["conservation_lhs_n"],
            conservative["conservation_lhs_d"],
        )
        rhs = Fraction(
            conservative["conservation_rhs_n"],
            conservative["conservation_rhs_d"],
        )
        self.assertEqual(lhs, Fraction(27000))
        self.assertEqual(rhs, Fraction(27000))
        self.assertEqual(lhs, rhs)
        self.assertTrue(self.receipt["conservation_identity_exact"])
        self.assertEqual(
            self.receipt["kernel"]["arithmetic"],
            "EXACT_RATIONAL_FRACTION",
        )

    def test_unknown_is_not_promoted_and_interval_uncertainty_propagates(self):
        unknown = self.replay["UNKNOWN_UNCERTAINTY"]
        self.assertEqual(unknown["uncertainty"]["kind"], "UNKNOWN")

        probe = self.receipt["interval_uncertainty_probe"]
        self.assertEqual(probe["decision"], "PASS_CONSERVATIVE")
        self.assertEqual((probe["value_n"], probe["value_d"]), (15, 1))
        interval = probe["uncertainty"]
        self.assertEqual(interval["kind"], "INTERVAL")
        self.assertEqual(
            (interval["lower_n"], interval["lower_d"]),
            (27, 2),
        )
        self.assertEqual(
            (interval["upper_n"], interval["upper_d"]),
            (33, 2),
        )

    def test_all_required_mutation_guards_pass(self):
        mutations = self.receipt["mutation_checks"]
        self.assertEqual(
            set(mutations),
            {
                "GAP",
                "OVERLAP",
                "COARSE_TO_FINE",
                "UNKNOWN_TO_EXACT",
                "MISSING_COVARIANCE",
                "MISSING_PROVENANCE",
                "UNPINNED_VERSION",
            },
        )
        self.assertTrue(self.receipt["mutation_checks_7_of_7"])
        self.assertTrue(all(item["passed"] for item in mutations.values()))
        self.assertEqual(
            mutations["COARSE_TO_FINE"]["observed"],
            "HOLD_TEMPORAL_INFORMATION_INSUFFICIENT",
        )
        self.assertEqual(
            mutations["UNKNOWN_TO_EXACT"]["observed"],
            "UNKNOWN",
        )

    def test_successful_kernel_result_emits_auditable_provenance_record(self):
        record = self.replay[
            "TWO_15MIN_NATIVE_MEANS_TO_ONE_30MIN_TARGET"
        ]["provenance_transform_record"]
        for field in (
            "operator_spec_id",
            "operator_version",
            "policy_receipt_sha256",
            "variable_id",
            "resource_layer",
            "quantity_kind",
            "source_raw_sha256_set",
            "source_url_set",
            "source_cell_intervals",
            "target_interval",
            "support_relation",
            "conservation_mode",
            "formula_id",
            "unit_transform_chain",
            "input_uncertainty_kinds",
            "output_uncertainty_kind",
            "input_evidence_refs",
            "hold_codes",
        ):
            self.assertIn(field, record)
        self.assertEqual(record["operator_version"], "V1")
        self.assertEqual(record["hold_codes"], [])
        self.assertEqual(
            record["support_relation"],
            "FINER_NATIVE_MEAN_PARTITION_EXACTLY_COVERS_TARGET",
        )
        self.assertTrue(self.receipt["provenance_transform_record_emitted"])
        self.assertTrue(self.receipt["fail_closed_hold_codes_enforced"])

    def test_path_b_and_real_world_surfaces_remain_closed(self):
        kernel = self.receipt["kernel"]
        self.assertEqual(
            kernel["status"],
            "EXECUTABLE_ISOLATED_SYNTHETIC_ONLY",
        )
        self.assertTrue(kernel["path_b_remains_locked"])
        self.assertTrue(kernel["synthetic_fixture_execution_only"])
        self.assertFalse(kernel["real_source_input_allowed"])
        self.assertFalse(kernel["real_value_composition_allowed"])
        self.assertFalse(self.receipt["real_source_input_used"])
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
