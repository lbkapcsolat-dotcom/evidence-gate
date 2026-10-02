import hashlib
import json
import unittest

try:
    import planetary_resource_environment_agency_interval_semantics_external_authority_resolution_v1 as gate
except ModuleNotFoundError:
    gate = None


class EnvironmentAgencyIntervalSemanticsExternalAuthorityResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = gate.run_gate() if gate is not None else None

    def test_final_hold_when_no_authoritative_boundary_rule_exists(self):
        observed = (
            self.receipt["verdict"]
            if self.receipt is not None
            else "MISSING_IMPLEMENTATION"
        )
        self.assertEqual(
            observed,
            "FINAL_HOLD_FOR_EA_SOURCE_FAMILY__NO_AUTHORITATIVE_INTERVAL_BOUNDARY_RULE",
        )

    def test_predecessor_receipt_is_exactly_pinned(self):
        self.assertEqual(
            self.receipt["predecessor"]["receipt_sha256"],
            "b06b7a528c4f32631f116b92b8cb11387c066608ea68c3fae1b8fda7f3902f4f",
        )

    def test_only_accepted_authority_classes_are_used(self):
        self.assertEqual(
            set(self.receipt["accepted_authority_classes"]),
            {
                "OFFICIAL_EA_PRIMARY_DOCUMENT",
                "OFFICIAL_EA_SCHEMA",
                "OFFICIAL_EA_WRITTEN_CLARIFICATION",
            },
        )

    def test_no_authoritative_boundary_classification_was_obtained(self):
        self.assertFalse(self.receipt["authoritative_boundary_rule_obtained"])
        self.assertFalse(self.receipt["period_start_proven"])
        self.assertFalse(self.receipt["period_end_proven"])
        self.assertFalse(self.receipt["period_center_proven"])
        self.assertFalse(self.receipt["other_explicit_boundary_proven"])
        self.assertEqual(
            self.receipt["question"]["resolved_answer"],
            "NO_AUTHORITATIVE_CLASSIFICATION_FOUND",
        )

    def test_official_written_clarification_is_absent_from_audited_evidence(self):
        self.assertFalse(
            self.receipt["official_ea_written_clarification_present"]
        )

    def test_elexon_and_entsog_remain_frozen(self):
        frozen = self.receipt["frozen_external_semantics"]
        self.assertTrue(frozen["elexon_recovered"])
        self.assertTrue(frozen["entsog_satisfied"])

    def test_no_assumption_inference_ingest_or_composition(self):
        self.assertFalse(self.receipt["assumption_used"])
        self.assertFalse(self.receipt["empirical_inference_used"])
        self.assertFalse(self.receipt["new_source_ingest_performed"])
        self.assertEqual(self.receipt["new_source_records_ingested"], 0)
        self.assertFalse(self.receipt["composition_performed"])

    def test_no_core_or_domain_change(self):
        self.assertFalse(self.receipt["core_patch_required"])
        self.assertFalse(self.receipt["new_domain_math_added"])
        self.assertFalse(any(self.receipt["fences"].values()))

    def test_source_family_is_closed_until_new_authority_evidence(self):
        self.assertEqual(self.receipt["source_family_status"], "FINAL_HOLD")
        self.assertIn(
            "Only new official Environment Agency",
            self.receipt["source_family_reentry_condition"],
        )

    def test_deterministic_receipt(self):
        a = gate.run_gate()
        b = gate.run_gate()
        ja = json.dumps(a, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        jb = json.dumps(b, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.assertEqual(ja, jb)
        self.assertEqual(
            hashlib.sha256((ja + "\n").encode()).hexdigest(),
            hashlib.sha256((jb + "\n").encode()).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
