from fractions import Fraction
import unittest

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_process_typed_dimensional_closure_v1 as typed


class TypedProcessClosureTests(unittest.TestCase):
    def activity(self, *, uncertainty=None, status=core.EpistemicStatus.OBSERVED,
                 evidence_refs=("EV:activity",), transform_chain=("activity:source",)):
        return core.QualifiedValue(
            core.F(2),
            core.UnitTag(core.ResourceLayer.ELECTRICITY,core.QuantityKind.DIMENSIONLESS,"activity"),
            "T0",
            status,
            uncertainty or core.IntervalUncertainty(core.F(1),core.F(3)),
            evidence_refs,
            transform_chain,
            (),
            "fresh",
            core.ValueSpace.PHYSICAL,
        )

    def process(self, unit="W_e/activity", coefficient=core.F(3)):
        return core.ProcessManifest(
            "P","PHYSICAL_CONVERSION","activity",
            (core.ProcessCoefficient(core.ResourceLayer.ELECTRICITY,"E0",coefficient,"EV:coef",unit),),
            "SRC:process","METHOD:process"
        )

    def test_typed_process_value_and_canonical_unit(self):
        nodes=core.nodes_for(core.ResourceLayer.ELECTRICITY,["E0"])
        out=typed.process_coupling_typed(self.process(),self.activity(),nodes,target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0")
        v=out["E0"]
        self.assertEqual(v.value,core.F(6))
        self.assertEqual(v.unit,core.canonical_unit(core.ResourceLayer.ELECTRICITY,core.QuantityKind.RATE))

    def test_activity_unit_mismatch_rejected(self):
        nodes=core.nodes_for(core.ResourceLayer.ELECTRICITY,["E0"])
        bad=core.ProcessManifest("P","PHYSICAL_CONVERSION","declared",(core.ProcessCoefficient(core.ResourceLayer.ELECTRICITY,"E0",core.F(1),"EV","W_e/declared"),),"SRC","METHOD")
        with self.assertRaises(typed.TypedProcessHold) as cm:
            typed.process_coupling_typed(bad,self.activity(),nodes,target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0")
        self.assertEqual(cm.exception.code,"HOLD_PROCESS_ACTIVITY_UNIT_MISMATCH")

    def test_coefficient_unit_mismatch_rejected(self):
        nodes=core.nodes_for(core.ResourceLayer.ELECTRICITY,["E0"])
        with self.assertRaises(typed.TypedProcessHold) as cm:
            typed.process_coupling_typed(self.process("m3/s/activity"),self.activity(),nodes,target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0")
        self.assertEqual(cm.exception.code,"HOLD_PROCESS_COEFFICIENT_DIMENSION_MISMATCH")

    def test_raw_fraction_process_injection_rejected(self):
        f=core.fixture_f01()
        with self.assertRaises(typed.TypedProcessHold) as cm:
            typed.resource_balance_residual_typed(**f,process_contribution={"E0":Fraction(1)})
        self.assertEqual(cm.exception.code,"HOLD_PROCESS_TYPED_VALUE_REQUIRED")

    def test_target_unit_mismatch_rejected(self):
        f=core.fixture_f01()
        bad=core.qv(1,core.ResourceLayer.FRESHWATER)
        with self.assertRaises(typed.TypedProcessHold) as cm:
            typed.resource_balance_residual_typed(**f,process_contribution={"E0":bad})
        self.assertEqual(cm.exception.code,"HOLD_PROCESS_TARGET_UNIT_MISMATCH")

    def test_metadata_preserved(self):
        nodes=core.nodes_for(core.ResourceLayer.ELECTRICITY,["E0"])
        a=self.activity(status=core.EpistemicStatus.IMPUTED,transform_chain=("imputation:model-x",))
        out=typed.process_coupling_typed(self.process(),a,nodes,target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0")["E0"]
        self.assertEqual(out.status,a.status)
        self.assertEqual(out.space,a.space)
        self.assertEqual(out.freshness,a.freshness)
        self.assertEqual(out.hold_codes,a.hold_codes)
        self.assertIn("EV:activity",out.evidence_refs)
        self.assertIn("EV:coef",out.evidence_refs)
        self.assertIn("SRC:process",out.evidence_refs)
        self.assertIn("METHOD:process",out.evidence_refs)

    def test_interval_uncertainty_scaled(self):
        nodes=core.nodes_for(core.ResourceLayer.ELECTRICITY,["E0"])
        out=typed.process_coupling_typed(self.process(coefficient=core.F(-2)),self.activity(),nodes,target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0")["E0"]
        self.assertIsInstance(out.uncertainty,core.IntervalUncertainty)
        self.assertEqual((out.uncertainty.lower,out.uncertainty.upper),(core.F(-6),core.F(-2)))

    def test_moment_uncertainty_scaled(self):
        a=self.activity(uncertainty=core.MomentUncertainty(core.F(5),core.F(4)))
        nodes=core.nodes_for(core.ResourceLayer.ELECTRICITY,["E0"])
        out=typed.process_coupling_typed(self.process(coefficient=core.F(3)),a,nodes,target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0")["E0"]
        self.assertEqual((out.uncertainty.mean,out.uncertainty.variance),(core.F(15),core.F(36)))

    def test_empirical_uncertainty_scaled(self):
        a=self.activity(uncertainty=core.EmpiricalUncertainty((core.F(1),core.F(2)),"A"))
        nodes=core.nodes_for(core.ResourceLayer.ELECTRICITY,["E0"])
        out=typed.process_coupling_typed(self.process(coefficient=core.F(4)),a,nodes,target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0")["E0"]
        self.assertEqual(out.uncertainty.samples,(core.F(4),core.F(8)))
        self.assertEqual(out.uncertainty.alignment_ref,"A")

    def test_typed_process_balance_closes(self):
        layer=core.ResourceLayer.ELECTRICITY
        nodes=core.nodes_for(layer,["E0"])
        p=core.ProcessManifest("P","PHYSICAL_CONVERSION","activity",(core.ProcessCoefficient(layer,"E0",core.F(5),"EV","W_e/activity"),),"SRC","METHOD")
        a=core.QualifiedValue(core.F(1),core.UnitTag(layer,core.QuantityKind.DIMENSIONLESS,"activity"),"T0")
        contribution=typed.process_coupling_typed(p,a,nodes,target_layer=layer,interval_id="T0")
        args=dict(layer=layer,interval_id="T0",nodes=nodes,internal_edges=[],B=[[]],
                  production=[core.qv(0,layer)],demand=[core.qv(5,layer)],loss=[core.qv(0,layer)],internal_flow=[])
        r=typed.resource_balance_residual_typed(**args,process_contribution=contribution)
        self.assertEqual(r,{"E0":core.F(0)})

    def test_gas_output_uses_hhv_canonical_rate(self):
        layer=core.ResourceLayer.NATURAL_GAS
        nodes=core.nodes_for(layer,["G0"])
        p=core.ProcessManifest("G","PHYSICAL_CONVERSION","activity",(core.ProcessCoefficient(layer,"G0",core.F(-2),"EV","W_th/activity"),),"SRC","METHOD")
        a=core.QualifiedValue(core.F(1),core.UnitTag(layer,core.QuantityKind.DIMENSIONLESS,"activity"),"T0")
        v=typed.process_coupling_typed(p,a,nodes,target_layer=layer,interval_id="T0")["G0"]
        self.assertEqual(v.unit.gas_basis,"HHV")


if __name__=="__main__":
    unittest.main(verbosity=2)
