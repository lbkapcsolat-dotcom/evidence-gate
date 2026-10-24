import unittest

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_process_coefficient_validity_v1 as pv
import planetary_resource_process_manifest_version_v1 as mv


class ProcessManifestVersionTests(unittest.TestCase):
    def nodes(self, version="V1"):
        return core.nodes_for(core.ResourceLayer.ELECTRICITY,["E0"],version=version)

    def activity(self):
        layer=core.ResourceLayer.ELECTRICITY
        return core.QualifiedValue(
            core.F(2),
            core.UnitTag(layer,core.QuantityKind.DIMENSIONLESS,"activity"),
            "T0",
            core.EpistemicStatus.IMPUTED,
            core.ExactUncertainty(),
            ("EV:activity",),
            ("activity:source",),
            (),
            "fresh",
            core.ValueSpace.PHYSICAL,
        )

    def process(self, *, version="V1", uncertainty=None,
                valid_from="2026-10-01T00:00:00Z",
                valid_to="2026-10-03T00:00:00Z",
                unit="W_e/activity"):
        row=pv.ValidityBoundedProcessCoefficient(
            core.ResourceLayer.ELECTRICITY,
            "E0",
            core.F(3),
            uncertainty or core.ExactUncertainty(),
            "EV:coef",
            unit,
            valid_from,
            valid_to,
        )
        return pv.ValidityBoundedProcessManifest(
            "P","PHYSICAL_CONVERSION","activity",(row,),
            "SRC","METHOD",version
        )

    def requested(self):
        return pv.RequestedInterval(
            "T0","2026-10-02T10:00:00Z","2026-10-02T11:00:00Z"
        )

    def run_case(self, *, process=None, nodes=None, expected="V1"):
        return mv.process_coupling_with_manifest_version(
            process or self.process(),
            self.activity(),
            nodes or self.nodes(),
            target_layer=core.ResourceLayer.ELECTRICITY,
            requested_interval=self.requested(),
            expected_process_manifest_version=expected,
        )["E0"]

    def test_matching_versions_admitted(self):
        out=self.run_case()
        self.assertEqual(out.value,core.F(6))
        self.assertEqual(out.status,core.EpistemicStatus.IMPUTED)
        self.assertEqual(out.space,core.ValueSpace.PHYSICAL)

    def test_process_manifest_version_mismatch_rejected(self):
        with self.assertRaises(mv.ProcessManifestVersionHold) as cm:
            self.run_case(process=self.process(version="V99"),expected="V1")
        self.assertEqual(
            cm.exception.code,
            "HOLD_PROCESS_MANIFEST_VERSION_MISMATCH",
        )

    def test_target_node_manifest_version_mismatch_rejected(self):
        with self.assertRaises(mv.ProcessManifestVersionHold) as cm:
            self.run_case(nodes=self.nodes(version="V2"),expected="V1")
        self.assertEqual(
            cm.exception.code,
            "HOLD_TARGET_NODE_MANIFEST_VERSION_MISMATCH",
        )

    def test_empty_expected_version_rejected(self):
        with self.assertRaises(mv.ProcessManifestVersionHold) as cm:
            self.run_case(expected="")
        self.assertEqual(
            cm.exception.code,
            "HOLD_PROCESS_MANIFEST_VERSION_REQUIRED",
        )

    def test_whitespace_expected_version_rejected(self):
        with self.assertRaises(mv.ProcessManifestVersionHold) as cm:
            self.run_case(expected="   ")
        self.assertEqual(
            cm.exception.code,
            "HOLD_PROCESS_MANIFEST_VERSION_REQUIRED",
        )

    def test_no_implicit_version_fallback(self):
        with self.assertRaises(TypeError):
            mv.process_coupling_with_manifest_version(
                self.process(),
                self.activity(),
                self.nodes(),
                target_layer=core.ResourceLayer.ELECTRICITY,
                requested_interval=self.requested(),
            )

    def test_validity_interval_preserved(self):
        p=self.process(
            valid_from="2026-10-02T10:30:00Z",
            valid_to="2026-10-03T00:00:00Z",
        )
        with self.assertRaises(pv.ProcessCoefficientValidityHold) as cm:
            self.run_case(process=p)
        self.assertEqual(
            cm.exception.code,
            "HOLD_PROCESS_COEFFICIENT_PARTIAL_INTERVAL_OVERLAP",
        )

    def test_coefficient_uncertainty_preserved(self):
        p=self.process(
            uncertainty=core.IntervalUncertainty(core.F(-1),core.F(1))
        )
        out=self.run_case(process=p)
        self.assertIsInstance(out.uncertainty,core.IntervalUncertainty)
        self.assertEqual(
            (out.uncertainty.lower,out.uncertainty.upper),
            (core.F(-2),core.F(2)),
        )

    def test_dimensional_unit_check_preserved(self):
        with self.assertRaises(Exception):
            self.run_case(process=self.process(unit="m3/s/activity"))

    def test_evidence_and_activity_metadata_preserved(self):
        out=self.run_case()
        for ev in ("EV:activity","EV:coef","SRC","METHOD"):
            self.assertIn(ev,out.evidence_refs)
        self.assertIn("activity:source",out.transform_chain)
        self.assertEqual(out.freshness,"fresh")
        self.assertEqual(out.space,core.ValueSpace.PHYSICAL)

    def test_version_guards_visible_in_transform_chain(self):
        out=self.run_case()
        self.assertIn("process_manifest_version:V1",out.transform_chain)
        self.assertIn("target_node_manifest_version:V1",out.transform_chain)
        self.assertTrue(
            any(x.startswith("coefficient_validity:") for x in out.transform_chain)
        )

    def test_expected_v2_admitted_when_process_and_nodes_are_v2(self):
        out=self.run_case(
            process=self.process(version="V2"),
            nodes=self.nodes(version="V2"),
            expected="V2",
        )
        self.assertEqual(out.value,core.F(6))
        self.assertIn("process_manifest_version:V2",out.transform_chain)


if __name__=="__main__":
    unittest.main(verbosity=2)
