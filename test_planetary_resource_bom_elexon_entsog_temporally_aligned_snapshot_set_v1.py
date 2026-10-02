import hashlib
import json
import unittest

import planetary_resource_bom_elexon_entsog_temporally_aligned_snapshot_set_v1 as gate


class BomElexonEntsogTemporallyAlignedSnapshotSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = gate.run_gate()

    def test_positive_duration_three_way_intersection_is_proven(self):
        self.assertEqual(
            self.receipt["verdict"],
            "PASS_BOUNDED_BOM_ELEXON_ENTSOG_TEMPORALLY_ALIGNED_SNAPSHOT_SET",
        )
        w = self.receipt["three_way_intersection"]
        self.assertEqual(w["start_utc"], "2026-09-30T12:00:00Z")
        self.assertEqual(w["end_utc"], "2026-09-30T12:30:00Z")
        self.assertEqual(w["duration_seconds"], 1800)
        self.assertTrue(w["positive_duration"])

    def test_predecessor_is_exactly_pinned(self):
        self.assertEqual(
            self.receipt["predecessor"]["receipt_sha256"],
            "236dcdcf8669a9a64251722af55c31eda04cee9f7bd30383cdafe883bdfea42a",
        )

    def test_bom_source_window_contains_common_window(self):
        s = self.receipt["sources"]["freshwater"]
        self.assertEqual(s["provider"], "Australian Bureau of Meteorology")
        self.assertEqual(s["interval_start"], "2026-09-30T00:00:00.000+10:00")
        self.assertEqual(s["interval_end"], "2026-10-01T00:00:00.000+10:00")
        self.assertEqual(s["published_value"], "0.378")

    def test_elexon_exact_half_hour_record_selected(self):
        s = self.receipt["sources"]["electricity"]
        self.assertEqual(s["provider"], "Elexon Insights Solution")
        self.assertEqual(s["record"]["startTime"], "2026-09-30T12:00:00Z")
        self.assertEqual(s["record"]["publishTime"], "2026-09-30T12:30:00Z")
        self.assertEqual(s["record"]["settlementPeriod"], 27)
        self.assertEqual(s["record"]["initialDemandOutturn"], 21575)
        self.assertEqual(s["interval_end"], "2026-09-30T12:30:00Z")
        self.assertEqual(
            s["end_bound_basis"],
            "ELEXON_SETTLEMENT_PERIOD_START_PLUS_30_MINUTES",
        )

    def test_entsog_exact_hour_record_selected(self):
        s = self.receipt["sources"]["natural_gas"]
        self.assertEqual(s["provider"], "ENTSOG Transparency Platform")
        self.assertEqual(s["interval_start"], "2026-09-30T12:00:00Z")
        self.assertEqual(s["interval_end"], "2026-09-30T13:00:00Z")
        self.assertEqual(s["unit"], "kWh/h")
        self.assertEqual(s["value"], "26823568")
        self.assertEqual(s["flow_status"], "Provisional")

    def test_raw_sources_are_exactly_pinned(self):
        expected = {
            "freshwater": (2735, "1fe8f1416b69377160ed6c9fced011785a46e7cb52eac46ce783a424c3e7ee14"),
            "electricity": (278348, "2a91d6b47379b47e4d8cfdb220d90c890ce416ebcd094b9810de70d47db12564"),
            "natural_gas": (9519, "889e9bf2e6365893bfed18a50291a0d130559fa1e38484c71d8e278e82f64be5"),
        }
        for name, (size, sha) in expected.items():
            source = self.receipt["sources"][name]
            self.assertEqual(source["raw_bytes"], size)
            self.assertEqual(source["raw_sha256"], sha)
            self.assertTrue(source["source_url"].startswith("https://"))

    def test_unknown_uncertainty_preserved_for_all_three(self):
        self.assertTrue(self.receipt["unknown_uncertainty_preserved"])
        for source in self.receipt["sources"].values():
            self.assertEqual(source["uncertainty_kind"], "UNKNOWN")

    def test_no_forbidden_temporal_transform(self):
        t = self.receipt["transforms"]
        self.assertFalse(t["interpolation_performed"])
        self.assertFalse(t["imputation_performed"])
        self.assertFalse(t["cross_interval_aggregation_performed"])
        self.assertFalse(t["boundary_inference_used"])
        self.assertTrue(t["exact_record_selection_only"])

    def test_source_provenance_is_preserved(self):
        self.assertTrue(self.receipt["source_provenance_preserved"])
        for source in self.receipt["sources"].values():
            self.assertIn("source_url", source)
            self.assertIn("raw_path", source)

    def test_no_composition_core_or_domain_change(self):
        self.assertFalse(self.receipt["composition_performed"])
        self.assertFalse(self.receipt["core_patch_required"])
        self.assertFalse(self.receipt["new_domain_math_added"])
        self.assertFalse(any(self.receipt["fences"].values()))

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
