import hashlib
import json
import unittest

import planetary_resource_temporal_support_policy_decision_freeze_v1 as gate


class TemporalSupportPolicyDecisionFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = gate.run_gate()

    def test_exactly_two_allowed_temporal_paths_are_frozen(self):
        self.assertEqual(
            self.receipt["verdict"],
            "PASS_BOUNDED_TEMPORAL_SUPPORT_POLICY_DECISION_FREEZE",
        )
        self.assertEqual(
            list(self.receipt["paths"].keys()),
            ["PATH_A", "PATH_B"],
        )
        self.assertEqual(self.receipt["policy"]["allowed_path_count"], 2)

    def test_predecessor_hold_is_exactly_pinned(self):
        p = self.receipt["predecessor"]
        self.assertEqual(
            p["receipt_sha256"],
            "55fdd516a583bed690f728096edf901ff9763a810605d0c26ce10f5b58f89deb",
        )
        self.assertEqual(
            p["head_sha"],
            "6d14b09ca12a8580edddc44641b4e59dd61f03da",
        )
        self.assertEqual(
            p["verdict"],
            "HOLD_EXACT_NATIVE_COMMON_SUPPORT_NOT_AVAILABLE",
        )

    def test_elexon_exact_30min_source_is_frozen(self):
        e = self.receipt["frozen_elexon"]
        self.assertEqual(e["status"], "READY_EXACT_INTERVAL")
        self.assertEqual(e["interval_start"], "2026-09-30T12:00:00Z")
        self.assertEqual(e["interval_end"], "2026-09-30T12:30:00Z")
        self.assertEqual(e["duration_seconds"], 1800)
        self.assertEqual(
            e["raw_sha256"],
            "2a91d6b47379b47e4d8cfdb220d90c890ce416ebcd094b9810de70d47db12564",
        )

    def test_path_a_keeps_exact_native_hold_and_disables_default_search(self):
        a = self.receipt["paths"]["PATH_A"]
        self.assertEqual(a["name"], "EXACT_NATIVE_INTERVALS_ONLY")
        self.assertTrue(a["exact_native_intervals_only"])
        self.assertEqual(
            a["natural_gas_status"],
            "HOLD_EXACT_NATIVE_COMMON_SUPPORT_NOT_AVAILABLE",
        )
        self.assertEqual(
            a["freshwater_status"],
            "HOLD_EXACT_NATIVE_COMMON_SUPPORT_NOT_AVAILABLE",
        )
        self.assertFalse(a["source_search_by_default"])
        self.assertFalse(a["value_composition_allowed"])
        self.assertEqual(a["status"], "ACTIVE_FAIL_CLOSED_CONTINUITY")

    def test_path_b_is_declared_but_locked_pending_formal_operator(self):
        b = self.receipt["paths"]["PATH_B"]
        self.assertTrue(b["declared"])
        self.assertFalse(b["activated"])
        self.assertTrue(b["operator_must_be_predeclared"])
        self.assertTrue(b["operator_must_be_auditable"])
        self.assertTrue(b["formal_temporal_semantics_required"])
        self.assertFalse(b["silent_downscaling_allowed"])
        self.assertFalse(b["imputation_allowed"])
        self.assertFalse(b["interpolation_allowed"])
        self.assertFalse(b["assumed_constancy_allowed"])
        self.assertFalse(b["value_composition_allowed_before_formal_semantics"])

    def test_no_implicit_third_path_or_automatic_transition_exists(self):
        p = self.receipt["policy"]
        self.assertEqual(p["allowed_paths_only"], ["PATH_A", "PATH_B"])
        self.assertFalse(p["implicit_third_path_allowed"])
        self.assertFalse(p["automatic_path_transition"])
        self.assertFalse(p["automatic_path_b_activation"])
        self.assertTrue(
            p["future_path_b_activation_requires_explicit_successor_gate"]
        )

    def test_current_execution_state_remains_fail_closed(self):
        s = self.receipt["current_execution_state"]
        self.assertEqual(s["continuity_path"], "PATH_A")
        self.assertEqual(s["natural_gas"], "HOLD")
        self.assertEqual(s["freshwater"], "HOLD")
        self.assertEqual(s["three_source_value_composition"], "BLOCKED")
        self.assertFalse(s["source_search_by_default"])

    def test_path_b_unlock_requires_formal_successor_gate(self):
        u = self.receipt["path_b_unlock_condition"]
        self.assertTrue(u["explicit_successor_gate_required"])
        self.assertTrue(u["formal_temporal_operator_required"])
        self.assertTrue(u["operator_predeclared"])
        self.assertTrue(u["operator_auditable"])
        self.assertFalse(u["value_composition_before_unlock"])

    def test_fences_and_receipt_are_deterministic(self):
        self.assertFalse(self.receipt["core_patch_required"])
        self.assertFalse(any(self.receipt["fences"].values()))
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
