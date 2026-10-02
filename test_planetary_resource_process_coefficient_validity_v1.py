import unittest

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_process_coefficient_uncertainty_v1 as pc
import planetary_resource_process_coefficient_validity_v1 as pv


class ProcessCoefficientValidityTests(unittest.TestCase):
    def nodes(self):
        return core.nodes_for(core.ResourceLayer.ELECTRICITY,["E0"])

    def activity(self, uncertainty=None):
        layer=core.ResourceLayer.ELECTRICITY
        return core.QualifiedValue(
            core.F(2),
            core.UnitTag(layer,core.QuantityKind.DIMENSIONLESS,"activity"),
            "T0",
            core.EpistemicStatus.IMPUTED,
            uncertainty or core.ExactUncertainty(),
            ("EV:activity",),
            ("activity:source",),
            (),
            "fresh",
            core.ValueSpace.PHYSICAL,
        )

    def row(self, *, valid_from="2026-10-01T00:00:00Z",
            valid_to="2026-10-03T00:00:00Z", uncertainty=None,
            unit="W_e/activity"):
        return pv.ValidityBoundedProcessCoefficient(
            core.ResourceLayer.ELECTRICITY,
            "E0",
            core.F(3),
            uncertainty or core.ExactUncertainty(),
            "EV:coef",
            unit,
            valid_from,
            valid_to,
        )

    def process(self, row=None):
        return pv.ValidityBoundedProcessManifest(
            "P","PHYSICAL_CONVERSION","activity",(row or self.row(),),
            "SRC","METHOD","V1"
        )

    def requested(self, start="2026-10-02T10:00:00Z",
                  end="2026-10-02T11:00:00Z"):
        return pv.RequestedInterval("T0",start,end)

    def run(self, row=None, **kwargs):
        return pv.process_coupling_with_coefficient_validity(
            self.process(row),
            self.activity(),
            self.nodes(),
            target_layer=core.ResourceLayer.ELECTRICITY,
            requested_interval=self.requested(),
            **kwargs,
        )["E0"]

    def test_full_containment_admitted(self):
        out=self.run()
        self.assertEqual(out.value,core.F(6))
        self.assertEqual(out.status,core.EpistemicStatus.IMPUTED)
        self.assertEqual(out.space,core.ValueSpace.PHYSICAL)
        self.assertIn("EV:coef",out.evidence_refs)

    def test_expired_rejected(self):
        row=self.row(valid_from="2026-09-01T00:00:00Z",valid_to="2026-10-02T10:00:00Z")
        with self.assertRaises(pv.ProcessCoefficientValidityHold) as cm:
            self.run(row)
        self.assertEqual(cm.exception.code,"HOLD_PROCESS_COEFFICIENT_EXPIRED")

    def test_not_yet_valid_rejected(self):
        row=self.row(valid_from="2026-10-02T11:00:00Z",valid_to="2026-10-04T00:00:00Z")
        with self.assertRaises(pv.ProcessCoefficientValidityHold) as cm:
            self.run(row)
        self.assertEqual(cm.exception.code,"HOLD_PROCESS_COEFFICIENT_NOT_YET_VALID")

    def test_partial_left_overlap_rejected(self):
        row=self.row(valid_from="2026-10-02T10:30:00Z",valid_to="2026-10-03T00:00:00Z")
        with self.assertRaises(pv.ProcessCoefficientValidityHold) as cm:
            self.run(row)
        self.assertEqual(cm.exception.code,"HOLD_PROCESS_COEFFICIENT_PARTIAL_INTERVAL_OVERLAP")

    def test_partial_right_overlap_rejected(self):
        row=self.row(valid_from="2026-10-01T00:00:00Z",valid_to="2026-10-02T10:30:00Z")
        with self.assertRaises(pv.ProcessCoefficientValidityHold) as cm:
            self.run(row)
        self.assertEqual(cm.exception.code,"HOLD_PROCESS_COEFFICIENT_PARTIAL_INTERVAL_OVERLAP")

    def test_missing_valid_from_rejected_when_required(self):
        row=self.row(valid_from=None)
        with self.assertRaises(pv.ProcessCoefficientValidityHold) as cm:
            self.run(row)
        self.assertEqual(cm.exception.code,"HOLD_PROCESS_COEFFICIENT_VALIDITY_REQUIRED")

    def test_missing_valid_to_rejected_when_required(self):
        row=self.row(valid_to=None)
        with self.assertRaises(pv.ProcessCoefficientValidityHold) as cm:
            self.run(row)
        self.assertEqual(cm.exception.code,"HOLD_PROCESS_COEFFICIENT_VALIDITY_REQUIRED")

    def test_invalid_validity_window_rejected(self):
        row=self.row(valid_from="2026-10-03T00:00:00Z",valid_to="2026-10-01T00:00:00Z")
        with self.assertRaises(pv.ProcessCoefficientValidityHold) as cm:
            self.run(row)
        self.assertEqual(cm.exception.code,"HOLD_PROCESS_COEFFICIENT_VALIDITY_INVALID")

    def test_naive_timestamp_rejected(self):
        row=self.row(valid_from="2026-10-01T00:00:00")
        with self.assertRaises(pv.ProcessCoefficientValidityHold) as cm:
            self.run(row)
        self.assertEqual(cm.exception.code,"HOLD_PROCESS_COEFFICIENT_VALIDITY_INVALID")

    def test_requested_interval_id_must_match_activity(self):
        requested=pv.RequestedInterval("T1","2026-10-02T10:00:00Z","2026-10-02T11:00:00Z")
        with self.assertRaises(core.HoldError) as cm:
            pv.process_coupling_with_coefficient_validity(
                self.process(),self.activity(),self.nodes(),
                target_layer=core.ResourceLayer.ELECTRICITY,
                requested_interval=requested,
            )
        self.assertEqual(cm.exception.code,core.HoldCode.HOLD_TIME_BASIS_MISMATCH)

    def test_coefficient_uncertainty_preserved(self):
        row=self.row(
            uncertainty=core.IntervalUncertainty(core.F(-1),core.F(1))
        )
        out=self.run(row)
        self.assertIsInstance(out.uncertainty,core.IntervalUncertainty)
        self.assertEqual(
            (out.uncertainty.lower,out.uncertainty.upper),
            (core.F(-2),core.F(2)),
        )

    def test_dimensional_unit_check_preserved(self):
        row=self.row(unit="m3/s/activity")
        with self.assertRaises(Exception):
            self.run(row)

    def test_validity_visible_in_transform_chain(self):
        out=self.run()
        self.assertTrue(any(x.startswith("requested_interval:") for x in out.transform_chain))
        self.assertTrue(any(x.startswith("coefficient_validity:") for x in out.transform_chain))

    def test_validity_optional_only_when_explicitly_disabled(self):
        row=self.row(valid_from=None,valid_to=None)
        out=self.run(row,validity_required=False)
        self.assertEqual(out.value,core.F(6))


if __name__=="__main__":
    unittest.main(verbosity=2)
