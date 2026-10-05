import json
import tempfile
import unittest
from pathlib import Path

from eq64_assurance_canary import run_canary
from eq64_executable_assurance_engine import replay_assurance_receipt


class EQ64AssuranceCanaryTests(unittest.TestCase):
    def test_real_runtime_canary_builds_pass_receipt_and_bound_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            result = run_canary(out)
            self.assertEqual(result["receipt"]["decision"], "PASS")
            self.assertEqual(result["security"]["status"], "PASS")
            self.assertGreaterEqual(result["security"]["failure_injections"], 3)
            self.assertGreaterEqual(result["regression"]["tests_run"], 10)
            self.assertTrue(result["regression"]["same_input_replay_equal"])
            self.assertTrue(replay_assurance_receipt(result["receipt"])["valid"])

            security_path = out / "eq64_security_canary.json"
            regression_path = out / "eq64_regression_canary.json"
            input_path = out / "eq64_assurance_input.json"
            receipt_path = out / "eq64_assurance_receipt.json"
            report_path = out / "EQ64_ASSURANCE_REPORT.md"
            for path in (security_path, regression_path, input_path, receipt_path, report_path):
                self.assertTrue(path.exists(), path)

            payload = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["target"]["runtime_sha256"],
                "1a1a94d08812d6393d417470efb4801bb397388d73171c39ef33a2fb6262bcce",
            )
            self.assertEqual(
                payload["readback"]["security_artifact_sha256"],
                payload["security"]["raw_artifact_sha256"],
            )
            self.assertEqual(
                payload["readback"]["regression_artifact_sha256"],
                payload["regression"]["raw_artifact_sha256"],
            )


if __name__ == "__main__":
    unittest.main()
