import unittest

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_end_to_end_uncertainty_v1 as e2e
import planetary_resource_process_coefficient_uncertainty_v1 as pc


class ProcessCoefficientUncertaintyTests(unittest.TestCase):
    def nodes(self):
        return core.nodes_for(core.ResourceLayer.ELECTRICITY,["E0"])

    def activity(self, *, uncertainty=None, status=core.EpistemicStatus.OBSERVED):
        layer=core.ResourceLayer.ELECTRICITY
        return core.QualifiedValue(
            core.F(2),
            core.UnitTag(layer,core.QuantityKind.DIMENSIONLESS,"activity"),
            "T0",
            status,
            uncertainty or core.ExactUncertainty(),
            ("EV:activity",),
            ("activity:source",),
            (),
            "fresh",
            core.ValueSpace.PHYSICAL,
        )

    def manifest(self, *, coefficient=3, uncertainty=None, unit="W_e/activity",
                 evidence="EV:coef", rows=None):
        layer=core.ResourceLayer.ELECTRICITY
        if rows is None:
            rows=(
                pc.UncertainProcessCoefficient(
                    layer,"E0",core.F(coefficient),
                    uncertainty or core.ExactUncertainty(),
                    evidence,unit
                ),
            )
        return pc.UncertainProcessManifest(
            "P","PHYSICAL_CONVERSION","activity",tuple(rows),"SRC","METHOD"
        )

    def test_exact_exact_stays_exact(self):
        out=pc.process_coupling_with_coefficient_uncertainty(
            self.manifest(),self.activity(),self.nodes(),
            target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0"
        )["E0"]
        self.assertEqual(out.value,core.F(6))
        self.assertIsInstance(out.uncertainty,core.ExactUncertainty)

    def test_exact_activity_interval_coefficient_scales(self):
        out=pc.process_coupling_with_coefficient_uncertainty(
            self.manifest(
                uncertainty=core.IntervalUncertainty(core.F(-1),core.F(1))
            ),
            self.activity(),
            self.nodes(),
            target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0"
        )["E0"]
        self.assertEqual(
            (out.uncertainty.lower,out.uncertainty.upper),
            (core.F(-2),core.F(2)),
        )

    def test_interval_activity_interval_coefficient_uses_bilinear_bounds(self):
        out=pc.process_coupling_with_coefficient_uncertainty(
            self.manifest(
                uncertainty=core.IntervalUncertainty(
                    core.F("-0.5"),core.F("0.5")
                )
            ),
            self.activity(
                uncertainty=core.IntervalUncertainty(core.F(-1),core.F(1))
            ),
            self.nodes(),
            target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0"
        )["E0"]
        self.assertEqual(
            (out.uncertainty.lower,out.uncertainty.upper),
            (core.F("-3.5"),core.F("4.5")),
        )

    def test_exact_activity_moment_coefficient_propagates_variance(self):
        out=pc.process_coupling_with_coefficient_uncertainty(
            self.manifest(
                uncertainty=core.MomentUncertainty(core.F(0),core.F(4))
            ),
            self.activity(),
            self.nodes(),
            target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0"
        )["E0"]
        self.assertEqual(out.uncertainty.mean,core.F(0))
        self.assertEqual(out.uncertainty.variance,core.F(16))

    def test_dual_moment_requires_joint_covariance_evidence(self):
        with self.assertRaises(core.HoldError) as cm:
            pc.process_coupling_with_coefficient_uncertainty(
                self.manifest(
                    uncertainty=core.MomentUncertainty(core.F(0),core.F(4))
                ),
                self.activity(
                    uncertainty=core.MomentUncertainty(core.F(0),core.F(1))
                ),
                self.nodes(),
                target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0"
            )
        self.assertEqual(cm.exception.code,core.HoldCode.HOLD_COVARIANCE_REQUIRED)

    def test_dual_moment_with_explicit_joint_moments(self):
        joint=pc.JointMomentProductEvidence(
            covariance_delta_activity_coefficient=core.F(0),
            e_delta_activity_sq_delta_coefficient=core.F(0),
            e_delta_activity_delta_coefficient_sq=core.F(0),
            e_delta_activity_sq_delta_coefficient_sq=core.F(4),
            evidence_ref="EV:joint-moments",
        )
        out=pc.process_coupling_with_coefficient_uncertainty(
            self.manifest(
                uncertainty=core.MomentUncertainty(core.F(0),core.F(4))
            ),
            self.activity(
                uncertainty=core.MomentUncertainty(core.F(0),core.F(1))
            ),
            self.nodes(),
            target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0",
            joint_moment_by_node={"E0":joint},
        )["E0"]
        self.assertEqual(out.uncertainty.mean,core.F(0))
        self.assertEqual(out.uncertainty.variance,core.F(29))
        self.assertIn("EV:joint-moments",out.evidence_refs)

    def test_dual_empirical_requires_alignment(self):
        with self.assertRaises(core.HoldError) as cm:
            pc.process_coupling_with_coefficient_uncertainty(
                self.manifest(
                    uncertainty=core.EmpiricalUncertainty(
                        (core.F("-0.5"),core.F("0.5")),"A"
                    )
                ),
                self.activity(
                    uncertainty=core.EmpiricalUncertainty(
                        (core.F(-1),core.F(1)),"A"
                    )
                ),
                self.nodes(),
                target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0"
            )
        self.assertEqual(
            cm.exception.code,core.HoldCode.HOLD_SAMPLE_ALIGNMENT_REQUIRED
        )

    def test_dual_empirical_aligned_samplewise_product(self):
        out=pc.process_coupling_with_coefficient_uncertainty(
            self.manifest(
                uncertainty=core.EmpiricalUncertainty(
                    (core.F("-0.5"),core.F("0.5")),"A"
                )
            ),
            self.activity(
                uncertainty=core.EmpiricalUncertainty(
                    (core.F(-1),core.F(1)),"A"
                )
            ),
            self.nodes(),
            target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0",
            sample_alignment_ref_by_node={"E0":"A"},
        )["E0"]
        self.assertEqual(
            out.uncertainty.samples,
            (core.F("-3.5"),core.F("4.5")),
        )

    def test_mixed_nonexact_families_fail_closed(self):
        with self.assertRaises(core.HoldError) as cm:
            pc.process_coupling_with_coefficient_uncertainty(
                self.manifest(
                    uncertainty=core.IntervalUncertainty(core.F(-1),core.F(1))
                ),
                self.activity(
                    uncertainty=core.MomentUncertainty(core.F(0),core.F(1))
                ),
                self.nodes(),
                target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0"
            )
        self.assertEqual(cm.exception.code,core.HoldCode.HOLD_UNCERTAINTY_OPERATOR)

    def test_multiple_uncertain_coefficients_same_node_fail_closed(self):
        layer=core.ResourceLayer.ELECTRICITY
        rows=(
            pc.UncertainProcessCoefficient(
                layer,"E0",core.F(1),
                core.IntervalUncertainty(core.F(-1),core.F(1)),
                "EV:c1","W_e/activity",
            ),
            pc.UncertainProcessCoefficient(
                layer,"E0",core.F(2),
                core.IntervalUncertainty(core.F("-0.5"),core.F("0.5")),
                "EV:c2","W_e/activity",
            ),
        )
        with self.assertRaises(pc.ProcessCoefficientUncertaintyHold) as cm:
            pc.process_coupling_with_coefficient_uncertainty(
                self.manifest(rows=rows),self.activity(),self.nodes(),
                target_layer=layer,interval_id="T0"
            )
        self.assertEqual(
            cm.exception.code,
            "HOLD_PROCESS_COEFFICIENT_CROSS_COVARIANCE_REQUIRED",
        )

    def test_coefficient_evidence_and_activity_metadata_preserved(self):
        out=pc.process_coupling_with_coefficient_uncertainty(
            self.manifest(
                uncertainty=core.IntervalUncertainty(core.F(-1),core.F(1))
            ),
            self.activity(status=core.EpistemicStatus.IMPUTED),
            self.nodes(),
            target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0"
        )["E0"]
        self.assertEqual(out.status,core.EpistemicStatus.IMPUTED)
        self.assertEqual(out.space,core.ValueSpace.PHYSICAL)
        self.assertEqual(out.freshness,"fresh")
        self.assertIn("EV:activity",out.evidence_refs)
        self.assertIn("EV:coef",out.evidence_refs)
        self.assertIn("SRC",out.evidence_refs)
        self.assertIn("METHOD",out.evidence_refs)
        self.assertIn("activity:source",out.transform_chain)

    def test_dimensional_unit_check_preserved(self):
        with self.assertRaises(Exception):
            pc.process_coupling_with_coefficient_uncertainty(
                self.manifest(unit="m3/s/activity"),
                self.activity(),
                self.nodes(),
                target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0"
            )

    def test_e2e_balance_includes_coefficient_uncertainty(self):
        layer=core.ResourceLayer.ELECTRICITY
        process_map=pc.process_coupling_with_coefficient_uncertainty(
            self.manifest(
                uncertainty=core.IntervalUncertainty(core.F(-1),core.F(1))
            ),
            self.activity(),
            self.nodes(),
            target_layer=layer,interval_id="T0"
        )
        out=e2e.resource_balance_with_uncertainty(
            layer=layer,interval_id="T0",nodes=self.nodes(),internal_edges=[],
            B=[[]],production=[core.qv(0,layer)],demand=[core.qv(6,layer)],
            loss=[core.qv(0,layer)],internal_flow=[],
            process_contribution=process_map,
        )["E0"]
        self.assertEqual(out.value,core.F(0))
        self.assertEqual(
            (out.uncertainty.lower,out.uncertainty.upper),
            (core.F(-2),core.F(2)),
        )

    def test_unknown_coefficient_uncertainty_remains_unknown(self):
        out=pc.process_coupling_with_coefficient_uncertainty(
            self.manifest(uncertainty=core.UnknownUncertainty()),
            self.activity(),self.nodes(),
            target_layer=core.ResourceLayer.ELECTRICITY,interval_id="T0"
        )["E0"]
        self.assertIsInstance(out.uncertainty,core.UnknownUncertainty)


if __name__=="__main__":
    unittest.main(verbosity=2)
