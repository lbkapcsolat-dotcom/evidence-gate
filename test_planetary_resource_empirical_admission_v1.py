import unittest

import planetary_resource_empirical_admission_v1 as m


class EmpiricalAdmission36(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = {r.id: r for r in m.run_admission_matrix()}


def _make_test(i):
    def test(self):
        r = self.results[f"A{i:02d}"]
        self.assertTrue(r.passed, f"{r.id} failed: {r.observed}")
    test.__name__ = f"test_A{i:02d}"
    return test


for _i in range(1, 37):
    setattr(EmpiricalAdmission36, f"test_A{_i:02d}", _make_test(_i))


class ContractFreezeChecks(unittest.TestCase):
    def test_variable_dictionary_is_36_explicit_variables(self):
        self.assertEqual(len(m.VARIABLES), 36)
        self.assertEqual(
            sorted({row["layer"] for row in m.VARIABLES.values()}),
            ["CRUDE_OIL", "ELECTRICITY", "FRESHWATER", "NATURAL_GAS"],
        )

    def test_no_external_data_bind_is_hard_false(self):
        scope = m.CONTRACT["scope"]
        self.assertFalse(scope["external_data_ingest"])
        self.assertFalse(scope["nasa_bind"])
        self.assertFalse(scope["rockstrom_bind"])
        self.assertFalse(scope["aggregate_eq_score"])
        self.assertFalse(scope["runtime_admission"])
        self.assertFalse(scope["pointer_promotion"])
        self.assertFalse(scope["global_bind"])
        self.assertFalse(scope["merge"])

    def test_contract_units_match_core_canonical_units(self):
        for row in m.VARIABLES.values():
            layer = m.core.ResourceLayer(row["layer"])
            kind = m.core.QuantityKind(row["quantity_kind"])
            core_unit = m.core.canonical_unit(layer, kind)
            self.assertEqual(row["canonical_unit"], core_unit.symbol)
            if layer is m.core.ResourceLayer.NATURAL_GAS:
                self.assertEqual(row["gas_basis"], core_unit.gas_basis)


if __name__ == "__main__":
    unittest.main(verbosity=2)
