import unittest

from eq64_comparative_false_pass_experiment import run_experiment


class EQ64ComparativeFalsePassExperimentTests(unittest.TestCase):
    def test_precommitted_matrix_and_metrics(self):
        result = run_experiment()

        self.assertEqual(result["schema_version"], "EQ64_COMPARATIVE_FALSE_PASS_EXPERIMENT_V1")
        self.assertEqual(result["case_count"], 21)
        self.assertEqual(result["fault_case_count"], 20)
        self.assertEqual(result["clean_case_count"], 1)

        self.assertEqual(
            [c["case_id"] for c in result["cases"]],
            [
                "clean_control",
                "target_id_mismatch",
                "runtime_sha_mismatch",
                "security_status_hold",
                "security_stale",
                "security_artifact_sha_invalid",
                "security_failure_injections_below_3",
                "regression_status_hold",
                "regression_stale",
                "regression_tests_below_10",
                "replay_equality_false",
                "readback_not_fresh",
                "security_readback_hash_mismatch",
                "regression_readback_hash_mismatch",
                "source_commit_mismatch",
                "overclaim_flag",
                "runtime_admission_true",
                "production_readiness_true",
                "compound_identity_and_readback",
                "compound_security_and_claim",
                "compound_regression_and_commit",
            ],
        )

        metrics = result["metrics"]
        self.assertEqual(metrics["A_NAIVE_UPSTREAM_PASS"]["false_pass_count"], 16)
        self.assertEqual(metrics["A_NAIVE_UPSTREAM_PASS"]["fault_detection_count"], 4)
        self.assertEqual(metrics["A_NAIVE_UPSTREAM_PASS"]["false_hold_count"], 0)

        self.assertEqual(metrics["B_EQUAL_WEIGHT_THRESHOLD_0_80"]["false_pass_count"], 17)
        self.assertEqual(metrics["B_EQUAL_WEIGHT_THRESHOLD_0_80"]["fault_detection_count"], 3)
        self.assertEqual(metrics["B_EQUAL_WEIGHT_THRESHOLD_0_80"]["false_hold_count"], 0)

        self.assertEqual(metrics["C_EQ64_NONCOMPENSATING"]["false_pass_count"], 0)
        self.assertEqual(metrics["C_EQ64_NONCOMPENSATING"]["fault_detection_count"], 20)
        self.assertEqual(metrics["C_EQ64_NONCOMPENSATING"]["false_hold_count"], 0)

        self.assertEqual(metrics["C_EQ64_NONCOMPENSATING"]["false_pass_rate"], 0.0)
        self.assertEqual(metrics["C_EQ64_NONCOMPENSATING"]["fault_detection_coverage"], 1.0)
        self.assertTrue(metrics["C_EQ64_NONCOMPENSATING"]["decision_reproducible"])
        self.assertTrue(metrics["C_EQ64_NONCOMPENSATING"]["receipt_replay_deterministic"])

    def test_all_models_are_deterministic_on_same_matrix(self):
        first = run_experiment()
        second = run_experiment()

        self.assertEqual(first["experiment_sha256"], second["experiment_sha256"])
        self.assertEqual(first["metrics"], second["metrics"])
        self.assertEqual(first["cases"], second["cases"])


if __name__ == "__main__":
    unittest.main()
