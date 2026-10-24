import json
import unittest

import planetary_resource_integration_readiness_freeze_v1 as f


class IntegrationReadinessFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=f.run_freeze()

    def test_core_frozen_for_integration(self):
        self.assertEqual(self.receipt["freeze_status"],"CORE_FROZEN_FOR_INTEGRATION")

    def test_core_kernel_40_of_40(self):
        self.assertEqual(self.receipt["verified_core_kernel"]["legacy_matrix"],{"count":40,"pass":40})

    def test_all_required_successor_pins_verified(self):
        self.assertEqual(
            set(self.receipt["verified_successor_pins"]),
            {
                "typed_process_coupling",
                "end_to_end_uncertainty",
                "process_coefficient_uncertainty",
                "process_coefficient_validity",
                "process_manifest_version_enforcement",
                "typed_storage_self_loss",
                "storage_host_node_topology_bind",
            },
        )

    def test_adapter_and_conformance_frozen(self):
        self.assertEqual(
            set(self.receipt["verified_adapter_pins"]),
            {
                "generic_source_adapter",
                "conformance_harness",
                "source_adapter_subsystem_freeze",
            },
        )

    def test_three_real_bindings_pinned(self):
        self.assertEqual(self.receipt["proven_real_source_binding_count"],3)
        self.assertEqual(sorted(self.receipt["verified_real_source_bindings"]),["electricity","natural_gas","water"])

    def test_exactly_two_deferred_nonblocking_items(self):
        self.assertEqual(self.receipt["deferred_nonblocking_count"],2)
        self.assertEqual(
            self.receipt["deferred_nonblocking"],
            ["STORAGE_PARAMETER_UNCERTAINTY","AUDIT_VECTOR_PROVENANCE_TYPING"],
        )

    def test_core_gap_stop_rule(self):
        self.assertEqual(
            self.receipt["core_change_policy"],
            "NO_NEW_CORE_GAP_WORK_UNLESS_INTEGRATION_FINDS_BREAKAGE",
        )
        self.assertFalse(self.receipt["new_core_gap_work_allowed_without_integration_breakage"])

    def test_single_next_target(self):
        self.assertEqual(self.receipt["next_target_count"],1)
        self.assertEqual(self.receipt["next_target"],"INTEGRATED_MINIMAL_PLANETARY_CORE_V1")

    def test_scope_fences(self):
        for key in (
            "provider_work","new_source_ingest","multi_source_fusion","eq_score",
            "ui","runtime_admission","pointer_promotion","global_bind","merge",
        ):
            self.assertFalse(self.receipt["fences"][key],key)

    def test_deterministic_receipt(self):
        a=f.run_freeze()
        b=f.run_freeze()
        ja=json.dumps(a,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        jb=json.dumps(b,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        self.assertEqual(ja,jb)


if __name__=="__main__":
    unittest.main(verbosity=2)
