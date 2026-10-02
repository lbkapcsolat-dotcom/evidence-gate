import hashlib
import json
import unittest

import planetary_resource_environment_agency_explicit_interval_source_surface_recovery_v1 as gate


class EnvironmentAgencyExplicitIntervalSourceSurfaceRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = gate.run_gate()

    def test_predecessor_is_exactly_pinned(self):
        self.assertEqual(
            self.receipt["predecessor"]["receipt_sha256"],
            "1094ac15a21253b6e867bfd783cdd8daa27750e3a57c821440e624efa36da70b",
        )

    def test_elexon_and_entsog_remain_frozen_satisfied(self):
        frozen = self.receipt["frozen_external_semantics"]
        self.assertTrue(frozen["elexon_recovered"])
        self.assertTrue(frozen["entsog_satisfied"])

    def test_four_primary_ea_surfaces_are_audited(self):
        self.assertEqual(self.receipt["candidate_surface_count"], 4)
        ids = {
            row["id"]
            for row in self.receipt["environment_agency_candidate_surface_audit"]
        }
        self.assertEqual(
            ids,
            {
                "EA_FLOOD_MONITORING_FLOW_MEAN",
                "EA_HYDROLOGY_FLOW_15MIN_INSTANTANEOUS",
                "EA_HYDROLOGY_FLOW_DAILY_MEAN",
                "EA_TIDE_GAUGE_15MIN_MEAN",
            },
        )

    def test_no_eligible_freshwater_flow_interval_surface_found(self):
        self.assertEqual(
            self.receipt["eligible_freshwater_flow_interval_surface_count"], 0
        )
        self.assertFalse(self.receipt["explicit_start_end_surface_found"])
        self.assertFalse(
            self.receipt["authoritative_positive_duration_boundary_rule_found"]
        )

    def test_flood_monitoring_mean_remains_unanchored(self):
        rows = {
            row["id"]: row
            for row in self.receipt["environment_agency_candidate_surface_audit"]
        }
        row = rows["EA_FLOOD_MONITORING_FLOW_MEAN"]
        self.assertFalse(row["explicit_start_time"])
        self.assertFalse(row["explicit_end_time"])
        self.assertFalse(row["authoritative_timestamp_boundary_rule"])
        self.assertFalse(row["eligible"])

    def test_hydrology_15min_flow_is_instantaneous_not_interval(self):
        rows = {
            row["id"]: row
            for row in self.receipt["environment_agency_candidate_surface_audit"]
        }
        row = rows["EA_HYDROLOGY_FLOW_15MIN_INSTANTANEOUS"]
        self.assertEqual(row["official_semantics"]["valueType"], "instantaneous")
        self.assertFalse(row["positive_duration_interval"])
        self.assertFalse(row["eligible"])

    def test_hydrology_daily_mean_has_no_explicit_boundary_anchor(self):
        rows = {
            row["id"]: row
            for row in self.receipt["environment_agency_candidate_surface_audit"]
        }
        row = rows["EA_HYDROLOGY_FLOW_DAILY_MEAN"]
        self.assertEqual(row["official_semantics"]["valueType"], "mean")
        self.assertEqual(row["official_semantics"]["period_seconds"], 86400)
        self.assertFalse(row["explicit_start_time"])
        self.assertFalse(row["explicit_end_time"])
        self.assertFalse(row["authoritative_timestamp_boundary_rule"])
        self.assertFalse(row["eligible"])

    def test_tide_gauge_is_not_substituted_for_freshwater_flow(self):
        rows = {
            row["id"]: row
            for row in self.receipt["environment_agency_candidate_surface_audit"]
        }
        row = rows["EA_TIDE_GAUGE_15MIN_MEAN"]
        self.assertEqual(row["variable_family"], "tidal_water_level")
        self.assertFalse(row["eligible"])

    def test_no_forbidden_inference_or_ingest(self):
        self.assertFalse(self.receipt["new_source_ingest_performed"])
        self.assertEqual(self.receipt["new_source_records_ingested"], 0)
        self.assertFalse(self.receipt["datetime_minus_period_inference_used"])
        self.assertFalse(self.receipt["center_window_inference_used"])
        self.assertFalse(self.receipt["assumed_15_minute_window_used"])

    def test_no_core_or_composition_change(self):
        self.assertFalse(self.receipt["composition_performed"])
        self.assertFalse(self.receipt["core_patch_required"])
        self.assertFalse(self.receipt["new_domain_math_added"])
        self.assertFalse(any(self.receipt["fences"].values()))

    def test_hold_verdict(self):
        self.assertEqual(
            self.receipt["verdict"],
            "HOLD_NO_ELIGIBLE_ENVIRONMENT_AGENCY_FRESHWATER_FLOW_INTERVAL_SURFACE",
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
