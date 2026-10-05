import json
import tempfile
import unittest
from pathlib import Path

from eq64_external_target_canary import (
    EXPECTED_RUNTIME_IDENTITY_SHA256,
    join_external_evidence,
)
from eq64_executable_assurance_engine import replay_assurance_receipt

COMMIT = "e3c64f80be032dda6ac30cb38bbed1d41d2fa559"
RUNTIME = EXPECTED_RUNTIME_IDENTITY_SHA256
TARGET_ID = "equilibrium-stability-systems/claim_admission_kernel_v1@e3c64f80"


def security_artifact():
    return {
        "schema_version": "EQ64_EXTERNAL_SECURITY_CANARY_V1",
        "target": {
            "system": "lbkapcsolat-dotcom/equilibrium-stability-systems",
            "version": COMMIT,
            "target_id": TARGET_ID,
            "runtime_sha256": RUNTIME,
            "environment": "RESEARCH_STAGE_OFFLINE_NONPRODUCTION",
        },
        "status": "PASS",
        "tests_run": 6,
        "failure_injections": 5,
    }


def regression_artifact():
    return {
        "schema_version": "EQ64_EXTERNAL_REGRESSION_CANARY_V1",
        "target": {
            "system": "lbkapcsolat-dotcom/equilibrium-stability-systems",
            "version": COMMIT,
            "target_id": TARGET_ID,
            "runtime_sha256": RUNTIME,
            "environment": "RESEARCH_STAGE_OFFLINE_NONPRODUCTION",
        },
        "status": "PASS",
        "tests_run": 16,
        "same_input_replay_equal": True,
    }


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")), encoding="utf-8")


class EQ64ExternalTargetCanaryTests(unittest.TestCase):
    def test_matching_external_artifacts_join_to_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            s = root / "security.json"
            r = root / "regression.json"
            write(s, security_artifact())
            write(r, regression_artifact())

            receipt = join_external_evidence(s, r, root / "authority")
            self.assertEqual(receipt["decision"], "PASS")
            self.assertEqual(receipt["eq64"]["state_index"], 63)
            self.assertTrue(replay_assurance_receipt(receipt)["valid"])
            self.assertEqual(receipt["target"]["system"], "lbkapcsolat-dotcom/equilibrium-stability-systems")
            self.assertFalse(receipt["runtime_admission"])
            self.assertFalse(receipt["production_readiness"])

    def test_runtime_byte_mismatch_holds(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            s = root / "security.json"
            r = root / "regression.json"
            sec = security_artifact()
            reg = regression_artifact()
            reg["target"]["runtime_sha256"] = "b" * 64
            write(s, sec)
            write(r, reg)

            receipt = join_external_evidence(s, r, root / "authority")
            self.assertEqual(receipt["decision"], "HOLD")
            self.assertIn("TARGET_RUNTIME_SHA256_MISMATCH", receipt["reasons"])

    def test_commit_mismatch_holds(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            s = root / "security.json"
            r = root / "regression.json"
            sec = security_artifact()
            reg = regression_artifact()
            reg["target"]["version"] = "f" * 40
            write(s, sec)
            write(r, reg)

            receipt = join_external_evidence(s, r, root / "authority")
            self.assertEqual(receipt["decision"], "HOLD")
            self.assertIn("CROSS_BRANCH_SOURCE_COMMIT_MISMATCH", receipt["reasons"])

    def test_wrong_security_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            s = root / "security.json"
            r = root / "regression.json"
            sec = security_artifact()
            sec["schema_version"] = "WRONG"
            write(s, sec)
            write(r, regression_artifact())
            with self.assertRaisesRegex(ValueError, "external security artifact schema"):
                join_external_evidence(s, r, root / "authority")

    def test_wrong_environment_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            s = root / "security.json"
            r = root / "regression.json"
            sec = security_artifact()
            sec["target"]["environment"] = "PRODUCTION"
            write(s, sec)
            write(r, regression_artifact())
            with self.assertRaisesRegex(ValueError, "nonproduction environment"):
                join_external_evidence(s, r, root / "authority")


if __name__ == "__main__":
    unittest.main()
