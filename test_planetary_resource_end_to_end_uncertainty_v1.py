import unittest

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_process_typed_dimensional_closure_v1 as typed
import planetary_resource_end_to_end_uncertainty_v1 as e2e


class EndToEndUncertaintyTests(unittest.TestCase):
    def one_node_args(self, prod, demand, *, process=None):
        layer=core.ResourceLayer.ELECTRICITY
        nodes=core.nodes_for(layer,["E0"])
        return dict(
            layer=layer,interval_id="T0",nodes=nodes,internal_edges=[],B=[[]],
            production=[prod],demand=[demand],loss=[core.qv(0,layer)],internal_flow=[],
            process_contribution=process,
        )

    def test_balance_interval_includes_typed_process(self):
        layer=core.ResourceLayer.ELECTRICITY
        nodes=core.nodes_for(layer,["E0"])
        activity=core.QualifiedValue(
            core.F(2),core.UnitTag(layer,core.QuantityKind.DIMENSIONLESS,"activity"),"T0",
            core.EpistemicStatus.IMPUTED,
            core.IntervalUncertainty(core.F("-0.5"),core.F("0.5")),
            ("EV:activity",),("imputation:p",),(),"fresh",core.ValueSpace.PHYSICAL,
        )
        proc=core.ProcessManifest(
            "P","PHYSICAL_CONVERSION","activity",
            (core.ProcessCoefficient(layer,"E0",core.F(1),"EV:coef","W_e/activity"),),
            "SRC","METHOD",
        )
        pc=typed.process_coupling_typed(proc,activity,nodes,target_layer=layer,interval_id="T0")
        prod=core.qv(10,layer,uncertainty=core.IntervalUncertainty(core.F(-1),core.F(1)),evidence_refs=("EV:prod",))
        demand=core.qv(12,layer)
        out=e2e.resource_balance_with_uncertainty(**self.one_node_args(prod,demand,process=pc))["E0"]
        self.assertEqual(out.value,0)
        self.assertIsInstance(out.uncertainty,core.IntervalUncertainty)
        self.assertEqual((out.uncertainty.lower,out.uncertainty.upper),(core.F("-1.5"),core.F("1.5")))
        self.assertEqual(out.status,core.EpistemicStatus.IMPUTED)
        self.assertIn("EV:prod",out.evidence_refs)
        self.assertIn("EV:coef",out.evidence_refs)
        self.assertEqual(out.space,core.ValueSpace.PHYSICAL)

    def test_balance_moment_requires_covariance(self):
        layer=core.ResourceLayer.ELECTRICITY
        p=core.qv(10,layer,uncertainty=core.MomentUncertainty(core.F(0),core.F(1)))
        d=core.qv(10,layer,uncertainty=core.MomentUncertainty(core.F(0),core.F(4)))
        with self.assertRaises(core.HoldError) as cm:
            e2e.resource_balance_with_uncertainty(**self.one_node_args(p,d))
        self.assertEqual(cm.exception.code,core.HoldCode.HOLD_COVARIANCE_REQUIRED)

    def test_balance_moment_with_covariance(self):
        layer=core.ResourceLayer.ELECTRICITY
        p=core.qv(10,layer,uncertainty=core.MomentUncertainty(core.F(0),core.F(1)))
        d=core.qv(10,layer,uncertainty=core.MomentUncertainty(core.F(0),core.F(4)))
        out=e2e.resource_balance_with_uncertainty(
            **self.one_node_args(p,d),
            covariance_by_node={"E0":[[core.F(1),core.F(0)],[core.F(0),core.F(4)]]},
        )["E0"]
        self.assertIsInstance(out.uncertainty,core.MomentUncertainty)
        self.assertEqual(out.uncertainty.variance,core.F(5))

    def test_balance_empirical_requires_alignment(self):
        layer=core.ResourceLayer.ELECTRICITY
        p=core.qv(10,layer,uncertainty=core.EmpiricalUncertainty((core.F(-1),core.F(1)),"A"))
        d=core.qv(10,layer,uncertainty=core.EmpiricalUncertainty((core.F("-0.5"),core.F("0.5")),"A"))
        with self.assertRaises(core.HoldError) as cm:
            e2e.resource_balance_with_uncertainty(**self.one_node_args(p,d))
        self.assertEqual(cm.exception.code,core.HoldCode.HOLD_SAMPLE_ALIGNMENT_REQUIRED)

    def test_balance_empirical_aligned(self):
        layer=core.ResourceLayer.ELECTRICITY
        p=core.qv(10,layer,uncertainty=core.EmpiricalUncertainty((core.F(-1),core.F(1)),"A"))
        d=core.qv(10,layer,uncertainty=core.EmpiricalUncertainty((core.F("-0.5"),core.F("0.5")),"A"))
        out=e2e.resource_balance_with_uncertainty(
            **self.one_node_args(p,d),
            sample_alignment_ref_by_node={"E0":"A"},
        )["E0"]
        self.assertEqual(out.uncertainty.samples,(core.F("-0.5"),core.F("0.5")))

    def test_storage_interval_propagation(self):
        st,tb,stock,charge,discharge=core.fixture_f06_storage()
        stock=core.QualifiedValue(stock.value,stock.unit,"T0",uncertainty=core.IntervalUncertainty(core.F(-2),core.F(2)))
        charge=core.QualifiedValue(charge.value,charge.unit,"T0",uncertainty=core.IntervalUncertainty(core.F(-1),core.F(1)))
        out=e2e.storage_transition_with_uncertainty(st,tb,stock,charge,discharge)
        self.assertEqual(out.value,core.F(104))
        self.assertEqual((out.uncertainty.lower,out.uncertainty.upper),(core.F("-2.9"),core.F("2.9")))
        self.assertEqual(out.status,core.EpistemicStatus.DERIVED)

    def test_storage_moment_requires_covariance(self):
        st,tb,stock,charge,discharge=core.fixture_f06_storage()
        stock=core.QualifiedValue(stock.value,stock.unit,"T0",uncertainty=core.MomentUncertainty(core.F(0),core.F(4)))
        charge=core.QualifiedValue(charge.value,charge.unit,"T0",uncertainty=core.MomentUncertainty(core.F(0),core.F(1)))
        with self.assertRaises(core.HoldError) as cm:
            e2e.storage_transition_with_uncertainty(st,tb,stock,charge,discharge)
        self.assertEqual(cm.exception.code,core.HoldCode.HOLD_COVARIANCE_REQUIRED)

    def test_storage_moment_with_covariance(self):
        st,tb,stock,charge,discharge=core.fixture_f06_storage()
        stock=core.QualifiedValue(stock.value,stock.unit,"T0",uncertainty=core.MomentUncertainty(core.F(0),core.F(4)))
        charge=core.QualifiedValue(charge.value,charge.unit,"T0",uncertainty=core.MomentUncertainty(core.F(0),core.F(1)))
        out=e2e.storage_transition_with_uncertainty(
            st,tb,stock,charge,discharge,
            covariance=[[core.F(4),core.F(1)],[core.F(1),core.F(1)]],
        )
        self.assertEqual(out.uncertainty.variance,core.F("6.61"))

    def test_storage_empirical_requires_alignment(self):
        st,tb,stock,charge,discharge=core.fixture_f06_storage()
        stock=core.QualifiedValue(stock.value,stock.unit,"T0",uncertainty=core.EmpiricalUncertainty((core.F(-1),core.F(1)),"A"))
        charge=core.QualifiedValue(charge.value,charge.unit,"T0",uncertainty=core.EmpiricalUncertainty((core.F(-1),core.F(1)),"A"))
        with self.assertRaises(core.HoldError) as cm:
            e2e.storage_transition_with_uncertainty(st,tb,stock,charge,discharge)
        self.assertEqual(cm.exception.code,core.HoldCode.HOLD_SAMPLE_ALIGNMENT_REQUIRED)

    def test_unknown_remains_unknown(self):
        layer=core.ResourceLayer.ELECTRICITY
        p=core.qv(10,layer,uncertainty=core.UnknownUncertainty())
        d=core.qv(10,layer)
        out=e2e.resource_balance_with_uncertainty(**self.one_node_args(p,d))["E0"]
        self.assertIsInstance(out.uncertainty,core.UnknownUncertainty)

    def test_mixed_nonexact_families_fail_closed(self):
        layer=core.ResourceLayer.ELECTRICITY
        p=core.qv(10,layer,uncertainty=core.IntervalUncertainty(core.F(-1),core.F(1)))
        d=core.qv(10,layer,uncertainty=core.MomentUncertainty(core.F(0),core.F(1)))
        with self.assertRaises(core.HoldError) as cm:
            e2e.resource_balance_with_uncertainty(**self.one_node_args(p,d))
        self.assertEqual(cm.exception.code,core.HoldCode.HOLD_UNCERTAINTY_OPERATOR)

    def test_exact_only_remains_exact(self):
        layer=core.ResourceLayer.ELECTRICITY
        out=e2e.resource_balance_with_uncertainty(
            **self.one_node_args(core.qv(10,layer),core.qv(10,layer))
        )["E0"]
        self.assertIsInstance(out.uncertainty,core.ExactUncertainty)


if __name__=="__main__":
    unittest.main(verbosity=2)
