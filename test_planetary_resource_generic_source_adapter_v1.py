import dataclasses
import json
import unittest

import planetary_resource_generic_source_adapter_v1 as generic
import planetary_resource_generic_source_bindings_v1 as bindings
import planetary_resource_generic_source_adapter_gate_v1 as gate


class GenericSourceAdapterContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = gate.run_gate()

    def test_three_of_three_receipt_equality(self):
        self.assertTrue(self.receipt["three_of_three_equal"])
        self.assertEqual(
            sorted(self.receipt["receipt_equality"]),
            ["electricity", "gas", "water"],
        )

    def test_water_receipt_equality(self):
        self.assertTrue(self.receipt["receipt_equality"]["water"]["equal"])

    def test_electricity_receipt_equality(self):
        self.assertTrue(self.receipt["receipt_equality"]["electricity"]["equal"])

    def test_gas_receipt_equality(self):
        self.assertTrue(self.receipt["receipt_equality"]["gas"]["equal"])

    def test_shared_output_type(self):
        for builder in (
            bindings.water_binding,
            bindings.electricity_binding,
            bindings.gas_binding,
        ):
            spec, record = builder()
            out = generic.adapt(spec, record)
            self.assertTrue(dataclasses.is_dataclass(out))
            self.assertEqual(out.schema_version, "EQUILIBRIUM_PRS_EMPIRICAL_SOURCE_ADMISSION_V1")

    def test_provider_specific_domain_math_is_absent(self):
        self.assertFalse(self.receipt["provider_specific_domain_math"])
        self.assertFalse(self.receipt["provider_specific_physics_engine"])

    def test_no_new_source_ingest(self):
        self.assertFalse(self.receipt["new_source_ingest"])
        self.assertFalse(self.receipt["fences"]["new_source_ingest"])

    def test_scope_fences(self):
        for key in (
            "multi_source_fusion",
            "eq_score",
            "ui",
            "runtime_admission",
            "pointer_promotion",
            "global_bind",
            "merge",
        ):
            self.assertFalse(self.receipt["fences"][key], key)

    def test_generic_interface_is_deterministic(self):
        a=gate.run_gate()
        b=gate.run_gate()
        ja=json.dumps(a,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        jb=json.dumps(b,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        self.assertEqual(ja,jb)

    def test_gas_pre_contract_adapter_is_declarative(self):
        spec, record = bindings.gas_binding()
        t=spec.pre_contract_transform
        self.assertTrue(t.enabled)
        self.assertEqual(t.from_unit,"kWh/h")
        self.assertEqual(t.to_unit,"kW_HHV")
        self.assertEqual((t.factor_n,t.factor_d),(1,1))
        self.assertEqual(t.to_gas_basis,"HHV")
        self.assertTrue(t.evidence_ref)
        self.assertEqual(record.source_unit,"kWh/h")


if __name__ == "__main__":
    unittest.main(verbosity=2)
