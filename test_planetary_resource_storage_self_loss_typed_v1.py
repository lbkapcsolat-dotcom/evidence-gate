import unittest

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_storage_self_loss_typed_v1 as typed_loss


class StorageSelfLossTypedTests(unittest.TestCase):
    def fixture(self):
        return core.fixture_f06_storage()

    def typed_loss(self, value=0, *, layer=core.ResourceLayer.ELECTRICITY,
                   interval_id="T0", kind=core.QuantityKind.RATE,
                   status=core.EpistemicStatus.OBSERVED,
                   uncertainty=None, evidence_refs=("EV:self-loss",),
                   transform_chain=("self_loss:source",)):
        return core.qv(
            value,
            layer,
            kind=kind,
            interval_id=interval_id,
            status=status,
            uncertainty=uncertainty,
            evidence_refs=evidence_refs,
            transform_chain=transform_chain,
        )

    def test_zero_typed_self_loss_preserves_baseline_104(self):
        st,tb,stock,charge,discharge=self.fixture()
        out=typed_loss.storage_transition_with_typed_self_loss(
            st,tb,stock,charge,discharge,self.typed_loss(0)
        )
        self.assertEqual(out.value,core.F(104))
        self.assertIsInstance(out.uncertainty,core.ExactUncertainty)

    def test_positive_typed_self_loss_reduces_stock(self):
        st,tb,stock,charge,discharge=self.fixture()
        out=typed_loss.storage_transition_with_typed_self_loss(
            st,tb,stock,charge,discharge,self.typed_loss(1)
        )
        self.assertEqual(out.value,core.F(103))

    def test_raw_fraction_self_loss_rejected(self):
        st,tb,stock,charge,discharge=self.fixture()
        with self.assertRaises(typed_loss.TypedSelfLossHold) as cm:
            typed_loss.storage_transition_with_typed_self_loss(
                st,tb,stock,charge,discharge,core.F(1)
            )
        self.assertEqual(cm.exception.code,"HOLD_SELF_LOSS_TYPED_VALUE_REQUIRED")

    def test_negative_self_loss_rejected(self):
        st,tb,stock,charge,discharge=self.fixture()
        with self.assertRaises(typed_loss.TypedSelfLossHold) as cm:
            typed_loss.storage_transition_with_typed_self_loss(
                st,tb,stock,charge,discharge,self.typed_loss(-1)
            )
        self.assertEqual(cm.exception.code,"HOLD_NEGATIVE_SELF_LOSS")

    def test_wrong_layer_rejected(self):
        st,tb,stock,charge,discharge=self.fixture()
        with self.assertRaises(core.HoldError) as cm:
            typed_loss.storage_transition_with_typed_self_loss(
                st,tb,stock,charge,discharge,
                self.typed_loss(1,layer=core.ResourceLayer.FRESHWATER)
            )
        self.assertEqual(cm.exception.code,core.HoldCode.HOLD_UNIT_MISMATCH)

    def test_wrong_kind_rejected(self):
        st,tb,stock,charge,discharge=self.fixture()
        with self.assertRaises(core.HoldError) as cm:
            typed_loss.storage_transition_with_typed_self_loss(
                st,tb,stock,charge,discharge,
                self.typed_loss(1,kind=core.QuantityKind.STOCK)
            )
        self.assertEqual(cm.exception.code,core.HoldCode.HOLD_UNIT_MISMATCH)

    def test_interval_mismatch_rejected(self):
        st,tb,stock,charge,discharge=self.fixture()
        with self.assertRaises(core.HoldError) as cm:
            typed_loss.storage_transition_with_typed_self_loss(
                st,tb,stock,charge,discharge,
                self.typed_loss(1,interval_id="T1")
            )
        self.assertEqual(cm.exception.code,core.HoldCode.HOLD_TIME_BASIS_MISMATCH)

    def test_self_loss_interval_uncertainty_is_included(self):
        st,tb,stock,charge,discharge=self.fixture()
        loss=self.typed_loss(
            1,
            status=core.EpistemicStatus.IMPUTED,
            uncertainty=core.IntervalUncertainty(core.F("-0.5"),core.F("0.5")),
            evidence_refs=("EV:self-loss",),
            transform_chain=("imputation:self-loss",),
        )
        out=typed_loss.storage_transition_with_typed_self_loss(
            st,tb,stock,charge,discharge,loss
        )
        self.assertEqual(out.value,core.F(103))
        self.assertIsInstance(out.uncertainty,core.IntervalUncertainty)
        self.assertEqual(
            (out.uncertainty.lower,out.uncertainty.upper),
            (core.F("-0.5"),core.F("0.5")),
        )
        self.assertEqual(out.status,core.EpistemicStatus.IMPUTED)
        self.assertIn("EV:self-loss",out.evidence_refs)
        self.assertIn("imputation:self-loss",out.transform_chain)
        self.assertEqual(out.space,core.ValueSpace.PHYSICAL)

    def test_self_loss_moment_requires_covariance(self):
        st,tb,stock,charge,discharge=self.fixture()
        loss=self.typed_loss(
            1,
            uncertainty=core.MomentUncertainty(core.F(0),core.F(4)),
        )
        with self.assertRaises(core.HoldError) as cm:
            typed_loss.storage_transition_with_typed_self_loss(
                st,tb,stock,charge,discharge,loss
            )
        self.assertEqual(cm.exception.code,core.HoldCode.HOLD_COVARIANCE_REQUIRED)

    def test_self_loss_moment_with_covariance(self):
        st,tb,stock,charge,discharge=self.fixture()
        loss=self.typed_loss(
            1,
            uncertainty=core.MomentUncertainty(core.F(0),core.F(4)),
        )
        out=typed_loss.storage_transition_with_typed_self_loss(
            st,tb,stock,charge,discharge,loss,
            covariance=[[core.F(4)]],
        )
        self.assertIsInstance(out.uncertainty,core.MomentUncertainty)
        self.assertEqual(out.uncertainty.variance,core.F(4))

    def test_self_loss_empirical_requires_alignment(self):
        st,tb,stock,charge,discharge=self.fixture()
        loss=self.typed_loss(
            1,
            uncertainty=core.EmpiricalUncertainty(
                (core.F("-0.5"),core.F("0.5")),"A"
            ),
        )
        with self.assertRaises(core.HoldError) as cm:
            typed_loss.storage_transition_with_typed_self_loss(
                st,tb,stock,charge,discharge,loss
            )
        self.assertEqual(
            cm.exception.code,core.HoldCode.HOLD_SAMPLE_ALIGNMENT_REQUIRED
        )

    def test_self_loss_empirical_aligned(self):
        st,tb,stock,charge,discharge=self.fixture()
        loss=self.typed_loss(
            1,
            uncertainty=core.EmpiricalUncertainty(
                (core.F("-0.5"),core.F("0.5")),"A"
            ),
        )
        out=typed_loss.storage_transition_with_typed_self_loss(
            st,tb,stock,charge,discharge,loss,
            sample_alignment_ref="A",
        )
        self.assertEqual(
            out.uncertainty.samples,
            (core.F("0.5"),core.F("-0.5")),
        )
        self.assertEqual(out.uncertainty.alignment_ref,"A")


if __name__=="__main__":
    unittest.main(verbosity=2)
