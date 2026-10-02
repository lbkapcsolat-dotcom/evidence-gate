import hashlib
import json
import unittest

import planetary_resource_formal_temporal_support_operator_spec_v1 as gate


class FormalTemporalSupportOperatorSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = gate.run_gate()

    def test_formal_path_b_operator_spec_is_frozen_without_activation(self):
        self.assertEqual(
            self.receipt["verdict"],
            "PASS_BOUNDED_FORMAL_TEMPORAL_SUPPORT_OPERATOR_SPEC",
        )
        self.assertEqual(self.receipt["target_path"], "PATH_B")
        self.assertEqual(
            self.receipt["path_b_status"],
            "DECLARED_LOCKED_NOT_ACTIVATED",
        )

    def test_predecessor_policy_freeze_is_exactly_pinned(self):
        p = self.receipt["predecessor"]
        self.assertEqual(
            p["receipt_sha256"],
            "5cfbb2feb2b7485e5f791f062794929e134981277d6c29679b7cbc12219fb6b9",
        )
        self.assertEqual(
            p["head_sha"],
            "d288163e42aa8f752502bb4290c44600f399653f",
        )
        self.assertEqual(
            p["verdict"],
            "PASS_BOUNDED_TEMPORAL_SUPPORT_POLICY_DECISION_FREEZE",
        )

    def test_operator_signature_and_support_domains_are_explicit(self):
        spec = self.receipt["operator_spec"]
        self.assertEqual(
            spec["operator_spec_id"],
            "TEMPORAL_SUPPORT_TO_TARGET_WINDOW_OPERATOR_V1",
        )
        self.assertEqual(spec["operator_version"], "V1")
        self.assertEqual(spec["execution_status"], "SPEC_ONLY_NOT_EXECUTABLE")
        self.assertFalse(spec["signature"]["operator_execution_defined"])
        self.assertEqual(
            spec["source_support_domain"]["allowed_support_relations"],
            [
                "EXACT_TARGET_SUPPORT",
                "FINER_NATIVE_MEAN_PARTITION_EXACTLY_COVERS_TARGET",
            ],
        )
        self.assertFalse(
            spec["source_support_domain"]["containment_only_is_admissible"]
        )
        self.assertFalse(
            spec["source_support_domain"]["coarse_to_fine_is_admissible"]
        )

    def test_admissibility_preconditions_are_all_required(self):
        adm = self.receipt["operator_spec"]["admissibility_preconditions"]
        self.assertTrue(all(adm.values()))
        self.assertTrue(adm["partition_must_cover_target_exactly_without_gaps"])
        self.assertTrue(
            adm[
                "partition_cells_must_be_source_native_time_means_for_conservative_mean_operator"
            ]
        )
        self.assertTrue(adm["path_b_activation_is_separate_gate"])

    def test_conservative_time_mean_partition_formula_is_frozen(self):
        c = self.receipt["operator_spec"]["conservation_semantics"]
        part = c["CONSERVATIVE_TIME_MEAN_PARTITION"]
        self.assertTrue(part["admissible_for_physical_value"])
        self.assertEqual(
            part["formula"],
            "x_target = SUM_i(x_i * delta_t_i) / delta_t_target",
        )
        self.assertEqual(
            part["conservation_statement"],
            "x_target * delta_t_target = SUM_i(x_i * delta_t_i)",
        )
        self.assertFalse(part["silent_constancy_assumption"])
        self.assertFalse(part["interpolation"])
        self.assertFalse(part["imputation"])
        self.assertFalse(part["downscaling"])

    def test_nonconservative_or_information_insufficient_path_fails_closed(self):
        c = self.receipt["operator_spec"]["conservation_semantics"]
        noncons = c["NONCONSERVATIVE_OR_INFORMATION_INSUFFICIENT"]
        self.assertFalse(noncons["admissible_for_physical_value"])
        self.assertEqual(noncons["physical_action"], "HOLD")
        self.assertIn(
            "COARSE_MEAN_TO_STRICT_SUBINTERVAL",
            noncons["examples"],
        )

    def test_uncertainty_contract_never_erases_unknown_or_required_dependence(self):
        u = self.receipt["operator_spec"]["uncertainty_propagation"]
        self.assertEqual(u["UNKNOWN"], "UNKNOWN_PROPAGATES")
        self.assertEqual(u["MOMENT"], "REQUIRE_COVARIANCE_OR_HOLD")
        self.assertEqual(
            u["EMPIRICAL"],
            "REQUIRE_SAMPLE_ALIGNMENT_REFERENCE_OR_HOLD",
        )
        self.assertFalse(u["uncertainty_narrowing_without_evidence"])
        self.assertFalse(u["unknown_to_exact_allowed"])

    def test_provenance_transform_record_is_auditable(self):
        p = self.receipt["operator_spec"]["provenance_transform_record"]
        required = set(p["required_fields"])
        for field in (
            "operator_spec_id",
            "operator_version",
            "policy_receipt_sha256",
            "variable_id",
            "resource_layer",
            "source_raw_sha256_set",
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
            self.assertIn(field, required)
        self.assertTrue(p["transform_chain_append_required"])
        self.assertTrue(p["raw_evidence_refs_must_be_preserved"])

    def test_fail_closed_registry_contains_critical_temporal_holds(self):
        holds = self.receipt["operator_spec"]["fail_closed_conditions"]
        for code in (
            "HOLD_TEMPORAL_INFORMATION_INSUFFICIENT",
            "HOLD_TEMPORAL_TARGET_NOT_EXACT_UNION",
            "HOLD_TEMPORAL_PARTITION_OVERLAP_OR_GAP",
            "HOLD_TEMPORAL_NONCONSERVATIVE_PHYSICAL_ADMISSION_FORBIDDEN",
            "HOLD_TEMPORAL_UNCERTAINTY_OPERATOR",
            "HOLD_TEMPORAL_PROVENANCE_INCOMPLETE",
            "HOLD_TEMPORAL_OPERATOR_VERSION_UNPINNED",
            "HOLD_PATH_B_NOT_ACTIVATED",
        ):
            self.assertIn(code, holds)

    def test_execution_activation_composition_and_fences_remain_closed(self):
        state = self.receipt["execution_state"]
        self.assertFalse(state["operator_executed"])
        self.assertFalse(state["path_b_activated"])
        self.assertFalse(state["value_composition_performed"])
        self.assertTrue(state["formal_spec_only"])
        self.assertEqual(
            self.receipt["physical_value_admission_status"],
            "BLOCKED_UNTIL_SEPARATE_OPERATOR_ACTIVATION_GATE",
        )
        self.assertFalse(any(self.receipt["forbidden_behavior"].values()))
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
