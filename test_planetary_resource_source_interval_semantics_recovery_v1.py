import hashlib
import json
import unittest

import planetary_resource_source_interval_semantics_recovery_v1 as gate


class SourceIntervalSemanticsRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = gate.run_gate()

    def test_predecessor_receipt_pin(self):
        self.assertEqual(
            self.receipt["predecessor"]["receipt_sha256"],
            "cbb021e22b5df3cb0700ca1c3db4352e82ecba2012d8f519d73f47bec46dd581",
        )

    def test_elexon_is_recovered_from_primary_semantics(self):
        e = self.receipt["elexon"]
        self.assertEqual(e["status"], "PROVEN")
        self.assertTrue(e["indo_average_per_settlement_period"])
        self.assertEqual(e["settlement_period_duration_minutes"], 30)
        self.assertEqual(
            e["settlement_period_start_anchor"],
            "START_TIME_OF_HALF_HOUR_PERIOD",
        )
        self.assertEqual(
            e["authoritative_end_bound_rule"],
            "END_UTC = START_TIME_UTC + 30_MINUTES",
        )
        self.assertEqual(e["pinned_record_start_utc"], "2026-10-01T22:00:00Z")
        self.assertEqual(
            e["authoritative_record_end_utc"],
            "2026-10-01T22:30:00Z",
        )
        self.assertFalse(e["boundary_inferred"])

    def test_ea_remains_unproven_without_boundary_anchor(self):
        ea = self.receipt["environment_agency"]
        self.assertEqual(ea["status"], "HOLD_UNPROVEN")
        self.assertTrue(ea["facts_proven"]["reading_has_datetime"])
        self.assertTrue(
            ea["facts_proven"]["measure_has_period_between_successive_readings"]
        )
        self.assertTrue(ea["facts_proven"]["mean_is_over_measurement_period"])
        self.assertFalse(ea["boundary_inferred"])
        self.assertIn("start, end, or center", ea["missing_proof"])

    def test_recovery_state_is_partial(self):
        r = self.receipt["recovery"]
        self.assertFalse(r["environment_agency_recovered"])
        self.assertTrue(r["elexon_recovered"])
        self.assertTrue(r["entsog_already_satisfied"])
        self.assertFalse(r["all_required_source_semantics_recovered"])

    def test_no_new_ingest_or_composition(self):
        self.assertFalse(self.receipt["new_source_ingest_performed"])
        self.assertEqual(self.receipt["new_source_records_ingested"], 0)
        self.assertFalse(self.receipt["composition_performed"])

    def test_no_core_or_domain_change(self):
        self.assertFalse(self.receipt["core_patch_required"])
        self.assertFalse(self.receipt["new_domain_math_added"])
        self.assertFalse(any(self.receipt["fences"].values()))

    def test_verdict(self):
        self.assertEqual(
            self.receipt["verdict"],
            "HOLD_SOURCE_INTERVAL_SEMANTICS_RECOVERY_PARTIAL__ELEXON_PROVEN__EA_UNPROVEN",
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
