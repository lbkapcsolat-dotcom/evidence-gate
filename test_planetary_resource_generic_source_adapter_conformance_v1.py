import dataclasses
import json
import unittest

import planetary_resource_generic_source_adapter_conformance_v1 as h
import planetary_resource_generic_source_bindings_v1 as bindings


class GenericSourceAdapterConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = h.run_harness()

    def test_three_of_three_conformant(self):
        self.assertTrue(self.receipt["three_of_three_conformant"])
        self.assertEqual(
            sorted(self.receipt["existing_binding_conformance"]),
            ["electricity", "gas", "water"],
        )

    def test_three_of_three_receipt_equal(self):
        self.assertTrue(self.receipt["three_of_three_receipt_equal"])

    def test_rejection_matrix_12_of_12(self):
        m=self.receipt["rejection_matrix"]
        self.assertEqual((m["pass"],m["count"]),(12,12))
        self.assertTrue(all(row["passed"] for row in m["rows"]))

    def test_tested_interface_is_pinned(self):
        pins=self.receipt["verified_tested_interface_pins"]
        self.assertEqual(
            pins["generic_adapter_implementation_sha256"],
            "ab519af91bc0a1ebb7d0ab92784ca01c2cfda8c32fd72e9e1f60d50fabdd9d59",
        )
        self.assertEqual(
            self.receipt["generic_adapter_predecessor_receipt_sha256"],
            "4eb59ab856dbe38afc3be191a4900b0290aba59d5436951f308f643d351faec7",
        )

    def test_water_conforms(self):
        spec,record=bindings.water_binding()
        cert=h.validate_binding(spec,record)
        self.assertTrue(cert["conformant"])

    def test_electricity_conforms(self):
        spec,record=bindings.electricity_binding()
        cert=h.validate_binding(spec,record)
        self.assertTrue(cert["conformant"])

    def test_gas_conforms_with_evidenced_pretransform(self):
        spec,record=bindings.gas_binding()
        cert=h.validate_binding(spec,record)
        self.assertTrue(cert["conformant"])
        self.assertTrue(cert["pre_contract_transform_enabled"])

    def test_no_provider_specific_domain_math(self):
        self.assertFalse(self.receipt["provider_specific_domain_math"])

    def test_no_new_source_ingest(self):
        self.assertFalse(self.receipt["new_source_ingest"])

    def test_scope_fences(self):
        for key in (
            "provider_specific_domain_math",
            "multi_source_fusion",
            "eq_score",
            "ui",
            "runtime_admission",
            "pointer_promotion",
            "global_bind",
            "merge",
        ):
            self.assertFalse(self.receipt["fences"][key],key)

    def test_harness_is_deterministic(self):
        a=h.run_harness()
        b=h.run_harness()
        ja=json.dumps(a,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        jb=json.dumps(b,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        self.assertEqual(ja,jb)


if __name__ == "__main__":
    unittest.main(verbosity=2)
