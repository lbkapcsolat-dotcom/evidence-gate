import unittest

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_storage_host_topology_bind_v1 as sh


class StorageHostTopologyBindTests(unittest.TestCase):
    def fixture(self, *, storage_version="V1", node_version="V1",
                node_layer=core.ResourceLayer.ELECTRICITY,
                topology_layer=core.ResourceLayer.ELECTRICITY):
        st,tb,stock,charge,discharge=core.fixture_f06_storage()
        st=core.StorageManifest(
            st.storage_id,st.layer,st.host_node_id,st.capacity,
            st.max_charge_rate,st.max_discharge_rate,
            st.eta_charge,st.eta_discharge,storage_version
        )
        topology=sh.ActiveTopologySnapshot(
            topology_layer,
            node_version,
            (core.NodeManifest("E0",node_layer,"ELECTRICITY_ZONE",node_version),),
        )
        loss=core.QualifiedValue(
            core.F(1),
            core.canonical_unit(st.layer,core.QuantityKind.RATE),
            tb.interval_id,
            core.EpistemicStatus.IMPUTED,
            core.IntervalUncertainty(core.F("-0.5"),core.F("0.5")),
            ("EV:self-loss",),
            ("imputation:self-loss",),
            (),
            "fresh",
            core.ValueSpace.PHYSICAL,
        )
        return st,topology,tb,stock,charge,discharge,loss

    def run_case(self, **kwargs):
        st,tp,tb,stock,charge,discharge,loss=self.fixture(**kwargs)
        return sh.storage_transition_with_topology_bind(
            st,tp,tb,stock,charge,discharge,loss
        )

    def test_valid_host_bind_admitted(self):
        out=self.run_case()
        self.assertEqual(out.value,core.F(103))
        self.assertIsInstance(out.uncertainty,core.IntervalUncertainty)
        self.assertEqual(
            (out.uncertainty.lower,out.uncertainty.upper),
            (core.F("-0.5"),core.F("0.5")),
        )
        self.assertEqual(out.status,core.EpistemicStatus.IMPUTED)
        self.assertIn("EV:self-loss",out.evidence_refs)
        self.assertEqual(out.space,core.ValueSpace.PHYSICAL)
        self.assertIn("storage_host_node:E0",out.transform_chain)
        self.assertIn("active_topology_manifest_version:V1",out.transform_chain)

    def test_active_topology_required(self):
        st,tp,tb,stock,charge,discharge,loss=self.fixture()
        with self.assertRaises(sh.StorageTopologyHold) as cm:
            sh.storage_transition_with_topology_bind(
                st,None,tb,stock,charge,discharge,loss
            )
        self.assertEqual(cm.exception.code,"HOLD_ACTIVE_TOPOLOGY_BIND_REQUIRED")

    def test_missing_host_rejected(self):
        st,tp,tb,stock,charge,discharge,loss=self.fixture()
        tp=sh.ActiveTopologySnapshot(
            tp.layer,tp.manifest_version,
            (core.NodeManifest("E9",tp.layer,"ELECTRICITY_ZONE",tp.manifest_version),),
        )
        with self.assertRaises(sh.StorageTopologyHold) as cm:
            sh.storage_transition_with_topology_bind(
                st,tp,tb,stock,charge,discharge,loss
            )
        self.assertEqual(cm.exception.code,"HOLD_STORAGE_HOST_NODE_MISSING")

    def test_wrong_layer_topology_rejected(self):
        st,tp,tb,stock,charge,discharge,loss=self.fixture(
            topology_layer=core.ResourceLayer.FRESHWATER,
            node_layer=core.ResourceLayer.FRESHWATER,
        )
        with self.assertRaises(sh.StorageTopologyHold) as cm:
            sh.storage_transition_with_topology_bind(
                st,tp,tb,stock,charge,discharge,loss
            )
        self.assertEqual(cm.exception.code,"HOLD_STORAGE_HOST_NODE_LAYER_MISMATCH")

    def test_wrong_layer_node_rejected(self):
        st,tp,tb,stock,charge,discharge,loss=self.fixture(
            node_layer=core.ResourceLayer.FRESHWATER
        )
        with self.assertRaises(sh.StorageTopologyHold) as cm:
            sh.storage_transition_with_topology_bind(
                st,tp,tb,stock,charge,discharge,loss
            )
        self.assertEqual(cm.exception.code,"HOLD_STORAGE_HOST_NODE_LAYER_MISMATCH")

    def test_storage_manifest_version_mismatch_rejected(self):
        st,tp,tb,stock,charge,discharge,loss=self.fixture(
            storage_version="V2",node_version="V1"
        )
        with self.assertRaises(sh.StorageTopologyHold) as cm:
            sh.storage_transition_with_topology_bind(
                st,tp,tb,stock,charge,discharge,loss
            )
        self.assertEqual(cm.exception.code,"HOLD_STORAGE_HOST_NODE_VERSION_MISMATCH")

    def test_topology_node_version_mismatch_rejected(self):
        st,tp,tb,stock,charge,discharge,loss=self.fixture(node_version="V2")
        tp=sh.ActiveTopologySnapshot(
            tp.layer,"V1",
            (core.NodeManifest("E0",tp.layer,"ELECTRICITY_ZONE","V2"),),
        )
        with self.assertRaises(sh.StorageTopologyHold) as cm:
            sh.storage_transition_with_topology_bind(
                st,tp,tb,stock,charge,discharge,loss
            )
        self.assertEqual(cm.exception.code,"HOLD_ACTIVE_TOPOLOGY_VERSION_MISMATCH")

    def test_typed_self_loss_rejection_preserved(self):
        st,tp,tb,stock,charge,discharge,loss=self.fixture()
        bad=core.qv(-1,st.layer,interval_id=tb.interval_id)
        with self.assertRaises(Exception):
            sh.storage_transition_with_topology_bind(
                st,tp,tb,stock,charge,discharge,bad
            )

    def test_storage_uncertainty_covariance_rule_preserved(self):
        st,tp,tb,stock,charge,discharge,loss=self.fixture()
        loss=core.qv(
            1,st.layer,interval_id=tb.interval_id,
            uncertainty=core.MomentUncertainty(core.F(0),core.F(4))
        )
        with self.assertRaises(core.HoldError) as cm:
            sh.storage_transition_with_topology_bind(
                st,tp,tb,stock,charge,discharge,loss
            )
        self.assertEqual(cm.exception.code,core.HoldCode.HOLD_COVARIANCE_REQUIRED)

    def test_evidence_metadata_preserved(self):
        out=self.run_case()
        self.assertIn("EV:self-loss",out.evidence_refs)
        self.assertIn("imputation:self-loss",out.transform_chain)
        self.assertEqual(out.freshness,"fresh")
        self.assertEqual(out.space,core.ValueSpace.PHYSICAL)

    def test_v2_bind_admitted_when_all_versions_match(self):
        out=self.run_case(storage_version="V2",node_version="V2")
        self.assertEqual(out.value,core.F(103))
        self.assertIn("active_topology_manifest_version:V2",out.transform_chain)


if __name__=="__main__":
    unittest.main(verbosity=2)
