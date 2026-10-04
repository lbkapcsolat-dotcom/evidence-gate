from __future__ import annotations

import importlib.metadata
import json
import unittest

import _hgraph
from hgraph.test import eval_node

import equilibrium_planetary_resource_core_v1 as ref
import planetary_resource_hgraph_bind_v1 as hg_bind


class PlanetaryResourceHGraphCrossParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = {r.id: r for r in ref.run_validation_matrix()}
        if len(cls.reference) != 40 or not all(r.passed for r in cls.reference.values()):
            raise AssertionError("reference matrix is not 40/40 PASS")
        if importlib.metadata.version("hgraph") != hg_bind.HGRAPH_VERSION:
            raise AssertionError("unexpected hgraph version")
        if not getattr(_hgraph, "__file__", ""):
            raise AssertionError("native _hgraph extension is not loaded")


def _make_test(i: int):
    def test(self):
        case_id = f"V{i:02d}"
        expected_r = self.reference[case_id]
        expected = {
            "id": expected_r.id,
            "passed": expected_r.passed,
            "observed": expected_r.observed,
        }
        out = eval_node(hg_bind.run_validation_case_hgraph, [1], case_id=i)
        self.assertEqual(len(out), 1, f"{case_id}: unexpected tick count {out!r}")
        self.assertIsNotNone(out[0], f"{case_id}: HGraph produced no value")
        observed = json.loads(out[0])
        self.assertEqual(observed, expected, f"{case_id}: HGraph/reference mismatch")
        self.assertTrue(observed["passed"], f"{case_id}: semantic validation failed")
    test.__name__ = f"test_V{i:02d}_cross_parity"
    return test


for _i in range(1, 41):
    setattr(PlanetaryResourceHGraphCrossParity, f"test_V{_i:02d}_cross_parity", _make_test(_i))


if __name__ == "__main__":
    unittest.main(verbosity=2)
