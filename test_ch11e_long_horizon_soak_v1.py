from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
import importlib.util
import unittest


MODULE = "run_ch11e_long_horizon_soak_v1"


class TestCH11ELongHorizonSoak(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.find_spec(MODULE)
        assert spec is not None, "CH11E production module is missing"
        cls.m = importlib.import_module(MODULE)

    def _row(self, *, ts: str, sha: str = "a" * 64, value: str = "1", provider=True, schema=True, semantic=True, age=10, max_age=7200):
        return {
            "selected_timestamp": ts,
            "live_raw_sha256": sha,
            "value_fingerprint": value,
            "provider_identity": provider,
            "schema_identity": schema,
            "semantic_identity": semantic,
            "freshness_age_seconds": age,
            "max_age_seconds": max_age,
        }

    def test_monotonic_value_change_is_expected_drift(self):
        prev = self._row(ts="2026-10-05T20:00:00Z", sha="a"*64, value="1")
        cur = self._row(ts="2026-10-05T21:00:00Z", sha="b"*64, value="2")
        out = self.m.classify_temporal_transition(prev, cur)
        self.assertEqual(out["classification"], "EXPECTED_VALUE_DRIFT")
        self.assertTrue(out["pass"])

    def test_timestamp_regression_fails_closed(self):
        prev = self._row(ts="2026-10-05T21:00:00Z")
        cur = self._row(ts="2026-10-05T20:00:00Z")
        out = self.m.classify_temporal_transition(prev, cur)
        self.assertEqual(out["classification"], "HOLD_TIMESTAMP_REGRESSION")
        self.assertFalse(out["pass"])

    def test_schema_drift_fails_closed(self):
        prev = self._row(ts="2026-10-05T20:00:00Z")
        cur = self._row(ts="2026-10-05T21:00:00Z", schema=False)
        out = self.m.classify_temporal_transition(prev, cur)
        self.assertEqual(out["classification"], "HOLD_SCHEMA_DRIFT")
        self.assertFalse(out["pass"])

    def test_stale_data_fails_closed(self):
        prev = self._row(ts="2026-10-05T20:00:00Z")
        cur = self._row(ts="2026-10-05T21:00:00Z", age=7201, max_age=7200)
        out = self.m.classify_temporal_transition(prev, cur)
        self.assertEqual(out["classification"], "HOLD_STALE_DATA")
        self.assertFalse(out["pass"])

    def test_recovery_ledger_distinguishes_not_observed_from_recovered(self):
        none = self.m.summarize_recovery([{"attempt_history": {"water": [{"result": "SUCCESS", "attempt": 1}]}}])
        self.assertEqual(none["status"], "IN_RUN_RECOVERY_NOT_EMPIRICALLY_OBSERVED")

        recovered = self.m.summarize_recovery([{"attempt_history": {"water": [
            {"result": "ERROR", "attempt": 1, "transient": True, "http_status": 502},
            {"result": "SUCCESS", "attempt": 2, "http_status": 200},
        ]}}])
        self.assertEqual(recovered["status"], "OBSERVED_REAL_TRANSIENT_FAILURE_WITH_IN_RUN_RECOVERY")

    def test_five_round_four_hour_span_passes_bounded_soak_without_fake_recovery_claim(self):
        start = datetime(2026, 10, 5, 20, 0, tzinfo=timezone.utc)
        rounds = []
        for i in range(5):
            ts = (start + timedelta(hours=i)).isoformat().replace("+00:00", "Z")
            rounds.append({
                "round": i + 1,
                "round_started_at": ts,
                "round_completed_at": ts,
                "attempt_history": {
                    "water": [{"result": "SUCCESS", "attempt": 1, "http_status": 200}],
                    "electricity": [{"result": "SUCCESS", "attempt": 1, "http_status": 200}],
                    "natural_gas": [{"result": "SUCCESS", "attempt": 1, "http_status": 200}],
                },
                "source_observations": {
                    "water": self._row(ts=ts, sha=(hex(i+1)[2:] * 64)[:64], value=str(i)),
                    "electricity": self._row(ts=ts, sha=(hex(i+2)[2:] * 64)[:64], value=str(i)),
                    "natural_gas": self._row(ts=ts, sha=(hex(i+3)[2:] * 64)[:64], value=str(i)),
                },
            })
        receipt = self.m.adjudicate_soak(rounds)
        self.assertEqual(receipt["verdict"], "PASS_CH11E__LONG_HORIZON_LIVE_READ_ONLY_SOAK__RECOVERY_PATH_NOT_OBSERVED__ZERO_WRITE_ZERO_ACTUATION")
        self.assertFalse(receipt["claim_ceiling"]["continuous_ingestion"])
        self.assertFalse(receipt["claim_ceiling"]["runtime_admission"])

    def test_short_span_holds(self):
        start = datetime(2026, 10, 5, 20, 0, tzinfo=timezone.utc)
        rounds = []
        for i in range(5):
            ts = (start + timedelta(minutes=i)).isoformat().replace("+00:00", "Z")
            rounds.append({
                "round": i + 1,
                "round_started_at": ts,
                "round_completed_at": ts,
                "attempt_history": {},
                "source_observations": {},
            })
        receipt = self.m.adjudicate_soak(rounds)
        self.assertEqual(receipt["verdict"], "HOLD_CH11E__LONG_HORIZON_NOT_YET_OBSERVED")


if __name__ == "__main__":
    unittest.main()
