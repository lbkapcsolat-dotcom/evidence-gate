import json
import unittest

import planetary_resource_source_adapter_subsystem_freeze_v1 as f


class SourceAdapterSubsystemFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=f.run_freeze()

    def test_subsystem_frozen(self):
        self.assertEqual(
            self.receipt["subsystem_status"],
            "FROZEN_BOUNDED_RETURN_TO_CORE",
        )

    def test_three_proven_bindings_pinned(self):
        self.assertEqual(self.receipt["proven_binding_count"],3)
        self.assertEqual(
            sorted(self.receipt["proven_bindings"]),
            ["electricity","natural_gas","water"],
        )
        self.assertTrue(all(x["conformant"] for x in self.receipt["proven_bindings"].values()))
        self.assertTrue(all(x["generic_receipt_equal"] for x in self.receipt["proven_bindings"].values()))

    def test_future_provider_path_is_single_and_explicit(self):
        self.assertEqual(
            self.receipt["future_provider_path"],
            ["BINDING","CONFORMANCE","EMPIRICAL_ADMISSION"],
        )
        self.assertTrue(
            self.receipt["future_provider_rules"]["no_direct_empirical_admission_without_conformance"]
        )

    def test_crude_oil_deferred(self):
        c=self.receipt["crude_oil"]
        self.assertEqual(c["canary_status"],"DEFERRED")
        self.assertFalse(c["provider_implementation_now"])
        self.assertEqual(
            c["resume_condition"],
            [
                "FIRST_REAL_CRUDE_OIL_SOURCE_ADMISSION",
                "FOUR_LAYER_REAL_WORLD_COVERAGE_CLAIM",
            ],
        )

    def test_return_to_core(self):
        r=self.receipt["return_to_core"]
        self.assertEqual(r["provider_subsystem_work_now"],"STOP")
        self.assertEqual(r["next_work_domain"],"PLANETARY_RESOURCE_CORE")
        self.assertTrue(r["adapter_changes_require_new_explicit_gate"])

    def test_no_new_source_ingest(self):
        self.assertFalse(self.receipt["new_source_ingest"])

    def test_scope_fences(self):
        for key in (
            "new_source_ingest","multi_source_fusion","eq_score","ui",
            "runtime_admission","pointer_promotion","global_bind","merge",
        ):
            self.assertFalse(self.receipt["fences"][key],key)

    def test_deterministic_freeze_receipt(self):
        a=f.run_freeze()
        b=f.run_freeze()
        ja=json.dumps(a,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        jb=json.dumps(b,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        self.assertEqual(ja,jb)


if __name__=="__main__":
    unittest.main(verbosity=2)
