import unittest
import planetary_resource_integrated_minimal_core_v1 as integrated

class IntegratedMinimalPlanetaryCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = integrated.run_integrated_system()

    def test_scope_and_layers(self):
        self.assertEqual(self.state["layers"], ["ELECTRICITY","NATURAL_GAS","FRESHWATER"])
        self.assertEqual(self.state["counts"]["resource_layers"], 3)
        self.assertEqual(self.state["counts"]["nodes"], 3)
        self.assertEqual(self.state["counts"]["frozen_intervals"], 1)
        self.assertEqual(self.state["counts"]["storages"], 1)
        self.assertEqual(self.state["counts"]["boundary_edges"], 1)
        self.assertEqual(self.state["counts"]["cross_layer_processes"], 1)

    def test_storage(self):
        s=self.state["storage"]
        self.assertEqual(s["host_node_id"],"E0")
        self.assertEqual(s["next_stock"]["value"],"524")
        self.assertEqual(s["node_side_delta_rate"]["value"],"-1/2")
        self.assertEqual(s["next_stock"]["uncertainty"]["kind"],"INTERVAL")
        self.assertIn("active_topology_manifest_version:V1",s["next_stock"]["transform_chain"])

    def test_boundary(self):
        b=self.state["boundary"]
        self.assertEqual(b["direction"],"IMPORT")
        self.assertEqual(b["flow"]["value"],"20")
        self.assertEqual(b["flow"]["gas_basis"],"HHV")

    def test_process(self):
        p=self.state["process"]
        self.assertEqual(p["target_layers"],["ELECTRICITY","NATURAL_GAS"])
        self.assertEqual(p["outputs"]["ELECTRICITY"]["value"],"4")
        self.assertEqual(p["outputs"]["NATURAL_GAS"]["value"],"-10")
        for layer in ("ELECTRICITY","NATURAL_GAS"):
            self.assertEqual(p["outputs"][layer]["uncertainty"]["kind"],"INTERVAL")
            chain=p["outputs"][layer]["transform_chain"]
            self.assertTrue(any(x.startswith("coefficient_validity:") for x in chain))
            self.assertIn("process_manifest_version:V1",chain)
            self.assertIn("target_node_manifest_version:V1",chain)

    def test_balances_close_with_uncertainty(self):
        for layer,b in self.state["balances"].items():
            self.assertEqual(b["value"],"0",layer)
            self.assertEqual(b["uncertainty"]["kind"],"INTERVAL",layer)

    def test_evidence_lineage(self):
        self.assertTrue(self.state["full_evidence_lineage_preserved"])
        self.assertTrue(set(self.state["input_evidence_refs"]).issubset(set(self.state["output_evidence_refs"])))

    def test_scope_fences(self):
        self.assertFalse(self.state["real_source_bindings_consumed"])
        self.assertFalse(self.state["new_source_ingest"])
        self.assertFalse(self.state["real_multi_source_fusion"])
        self.assertFalse(self.state["core_patch_required"])
        self.assertFalse(self.state["new_domain_math_added"])

    def test_deterministic_state(self):
        other=integrated.run_integrated_system()
        self.assertEqual(self.state["state_sha256"],other["state_sha256"])
        self.assertEqual(self.state,other)

if __name__=="__main__":
    unittest.main(verbosity=2)
