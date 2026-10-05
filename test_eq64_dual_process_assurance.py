import copy
import json
import tempfile
import unittest
from pathlib import Path

from eq64_dual_process_assurance import (
    join_evidence,
    produce_regression,
    produce_security,
)
from eq64_executable_assurance_engine import replay_assurance_receipt


class EQ64DualProcessAssuranceTests(unittest.TestCase):
    def test_separate_security_and_regression_artifacts_join_to_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            security_path = root / "security.json"
            regression_path = root / "regression.json"
            out = root / "authority"

            security = produce_security(security_path)
            regression = produce_regression(regression_path)
            receipt = join_evidence(security_path, regression_path, out)

            self.assertEqual(security["schema_version"], "EQ64_SECURITY_CANARY_V1")
            self.assertEqual(regression["schema_version"], "EQ64_REGRESSION_CANARY_V1")
            self.assertEqual(receipt["decision"], "PASS")
            self.assertEqual(receipt["eq64"]["state_index"], 63)
            self.assertTrue(replay_assurance_receipt(receipt)["valid"])
            self.assertTrue((out / "eq64_assurance_receipt.json").exists())
            self.assertTrue((out / "eq64_assurance_input.json").exists())

    def test_target_id_mismatch_holds_at_authority_join(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            security_path = root / "security.json"
            regression_path = root / "regression.json"
            produce_security(security_path)
            regression = produce_regression(regression_path)
            regression["target"]["target_id"] = "different-target"
            regression_path.write_text(
                json.dumps(regression, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )

            receipt = join_evidence(security_path, regression_path, root / "authority")
            self.assertEqual(receipt["decision"], "HOLD")
            self.assertIn("TARGET_IDENTITY_MISMATCH", receipt["reasons"])

    def test_source_commit_mismatch_holds_at_authority_join(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            security_path = root / "security.json"
            regression_path = root / "regression.json"
            produce_security(security_path)
            regression = produce_regression(regression_path)
            regression["target"]["version"] = "f" * 40
            regression_path.write_text(
                json.dumps(regression, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )

            receipt = join_evidence(security_path, regression_path, root / "authority")
            self.assertEqual(receipt["decision"], "HOLD")
            self.assertIn("CROSS_BRANCH_SOURCE_COMMIT_MISMATCH", receipt["reasons"])

    def test_security_schema_role_confusion_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            security_path = root / "security.json"
            regression_path = root / "regression.json"
            regression = produce_regression(regression_path)
            security_path.write_text(
                json.dumps(regression, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "security artifact schema"):
                join_evidence(security_path, regression_path, root / "authority")

    def test_regression_schema_role_confusion_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            security_path = root / "security.json"
            regression_path = root / "regression.json"
            security = produce_security(security_path)
            regression_path.write_text(
                json.dumps(security, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "regression artifact schema"):
                join_evidence(security_path, regression_path, root / "authority")


if __name__ == "__main__":
    unittest.main()
