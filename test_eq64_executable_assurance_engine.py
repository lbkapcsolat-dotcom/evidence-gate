import copy
import itertools
import unittest

from eq64_executable_assurance_engine import evaluate_assurance, replay_assurance_receipt


A = "a" * 64
B = "b" * 64
C = "c" * 64
COMMIT = "5efa63b864b11fc2feaeac10dbaef63a4b990d90"

BASE = {
    "schema_version": "EQ64_EXECUTABLE_ASSURANCE_ENGINE_V1",
    "target": {
        "system": "lbkapcsolat-dotcom/evidence-gate",
        "version": COMMIT,
        "target_id": "evidence-gate@5efa63b8",
        "runtime_sha256": "1a1a94d08812d6393d417470efb4801bb397388d73171c39ef33a2fb6262bcce",
    },
    "security": {
        "target_id": "evidence-gate@5efa63b8",
        "target_runtime_sha256": "1a1a94d08812d6393d417470efb4801bb397388d73171c39ef33a2fb6262bcce",
        "source_commit": COMMIT,
        "status": "PASS",
        "fresh": True,
        "tests_run": 5,
        "failure_injections": 3,
        "raw_artifact_sha256": A,
    },
    "regression": {
        "target_id": "evidence-gate@5efa63b8",
        "target_runtime_sha256": "1a1a94d08812d6393d417470efb4801bb397388d73171c39ef33a2fb6262bcce",
        "source_commit": COMMIT,
        "status": "PASS",
        "fresh": True,
        "tests_run": 64,
        "same_input_replay_equal": True,
        "raw_artifact_sha256": B,
    },
    "readback": {
        "fresh": True,
        "security_artifact_sha256": A,
        "regression_artifact_sha256": B,
    },
    "claim_guard": {
        "overclaim_flags": [],
        "runtime_admission": False,
        "production_readiness": False,
    },
    "engine": {"implementation_sha256": C},
}


def payload_for_bits(bits):
    p = copy.deepcopy(BASE)
    b0, b1, b2, b3, b4, b5 = bits
    if not b0:
        p["security"]["target_id"] = "different-target"
    if not b1:
        p["security"]["status"] = "HOLD"
    if not b2:
        p["regression"]["status"] = "HOLD"
    if not b3:
        p["readback"]["security_artifact_sha256"] = "d" * 64
    if not b4:
        p["regression"]["source_commit"] = "e" * 40
    if not b5:
        p["claim_guard"]["overclaim_flags"] = ["PRODUCTION_READY"]
    return p


class EQ64ExecutableAssuranceEngineTests(unittest.TestCase):
    def test_all_64_gate_states_have_exact_eq64_index_and_only_63_passes(self):
        seen = set()
        for bits in itertools.product([False, True], repeat=6):
            receipt = evaluate_assurance(payload_for_bits(bits))
            expected_index = sum((1 << i) for i, value in enumerate(bits) if value)
            self.assertEqual(receipt["eq64"]["bits"], [int(x) for x in bits], bits)
            self.assertEqual(receipt["eq64"]["state_index"], expected_index, bits)
            self.assertEqual(receipt["decision"], "PASS" if all(bits) else "HOLD", bits)
            seen.add(expected_index)
        self.assertEqual(seen, set(range(64)))

    def test_pass_receipt_is_deterministic(self):
        a = evaluate_assurance(BASE)
        b = evaluate_assurance(copy.deepcopy(BASE))
        self.assertEqual(a["receipt_sha256"], b["receipt_sha256"])
        self.assertEqual(a["evidence_bundle_sha256"], b["evidence_bundle_sha256"])

    def test_replay_accepts_untampered_receipt(self):
        receipt = evaluate_assurance(BASE)
        self.assertTrue(replay_assurance_receipt(receipt)["valid"])

    def test_replay_rejects_tampered_receipt(self):
        receipt = evaluate_assurance(BASE)
        receipt["decision"] = "HOLD"
        self.assertFalse(replay_assurance_receipt(receipt)["valid"])

    def test_target_runtime_sha_mismatch_holds(self):
        p = copy.deepcopy(BASE)
        p["security"]["target_runtime_sha256"] = "f" * 64
        r = evaluate_assurance(p)
        self.assertEqual(r["decision"], "HOLD")
        self.assertIn("TARGET_RUNTIME_SHA256_MISMATCH", r["reasons"])

    def test_target_mismatch_holds(self):
        p = copy.deepcopy(BASE)
        p["regression"]["target_id"] = "other"
        r = evaluate_assurance(p)
        self.assertEqual(r["decision"], "HOLD")
        self.assertIn("TARGET_IDENTITY_MISMATCH", r["reasons"])

    def test_security_failure_injection_floor_is_three(self):
        p = copy.deepcopy(BASE)
        p["security"]["failure_injections"] = 2
        r = evaluate_assurance(p)
        self.assertEqual(r["decision"], "HOLD")
        self.assertIn("SECURITY_FAILURE_INJECTIONS_BELOW_3", r["reasons"])

    def test_regression_requires_at_least_ten_deterministic_tests(self):
        p = copy.deepcopy(BASE)
        p["regression"]["tests_run"] = 9
        r = evaluate_assurance(p)
        self.assertEqual(r["decision"], "HOLD")
        self.assertIn("REGRESSION_TEST_COUNT_BELOW_10", r["reasons"])

    def test_regression_requires_same_input_replay_equality(self):
        p = copy.deepcopy(BASE)
        p["regression"]["same_input_replay_equal"] = False
        r = evaluate_assurance(p)
        self.assertEqual(r["decision"], "HOLD")
        self.assertIn("REPLAY_EQUALITY_NOT_PROVEN", r["reasons"])

    def test_security_readback_hash_mismatch_holds(self):
        p = copy.deepcopy(BASE)
        p["readback"]["security_artifact_sha256"] = "f" * 64
        r = evaluate_assurance(p)
        self.assertEqual(r["decision"], "HOLD")
        self.assertIn("READBACK_SECURITY_HASH_MISMATCH", r["reasons"])

    def test_regression_readback_hash_mismatch_holds(self):
        p = copy.deepcopy(BASE)
        p["readback"]["regression_artifact_sha256"] = "f" * 64
        r = evaluate_assurance(p)
        self.assertEqual(r["decision"], "HOLD")
        self.assertIn("READBACK_REGRESSION_HASH_MISMATCH", r["reasons"])

    def test_stale_security_or_regression_evidence_holds(self):
        for branch in ("security", "regression"):
            with self.subTest(branch=branch):
                p = copy.deepcopy(BASE)
                p[branch]["fresh"] = False
                r = evaluate_assurance(p)
                self.assertEqual(r["decision"], "HOLD")
                self.assertIn(branch.upper() + "_EVIDENCE_STALE", r["reasons"])

    def test_stale_readback_holds(self):
        p = copy.deepcopy(BASE)
        p["readback"]["fresh"] = False
        r = evaluate_assurance(p)
        self.assertEqual(r["decision"], "HOLD")
        self.assertIn("READBACK_NOT_FRESH", r["reasons"])

    def test_cross_branch_commit_mismatch_holds(self):
        p = copy.deepcopy(BASE)
        p["regression"]["source_commit"] = "f" * 40
        r = evaluate_assurance(p)
        self.assertEqual(r["decision"], "HOLD")
        self.assertIn("CROSS_BRANCH_SOURCE_COMMIT_MISMATCH", r["reasons"])

    def test_overclaim_flag_holds(self):
        p = copy.deepcopy(BASE)
        p["claim_guard"]["overclaim_flags"] = ["GLOBAL_BIND"]
        r = evaluate_assurance(p)
        self.assertEqual(r["decision"], "HOLD")
        self.assertIn("OVERCLAIM_FLAG_PRESENT", r["reasons"])

    def test_runtime_admission_and_production_readiness_must_remain_false(self):
        for key, reason in (
            ("runtime_admission", "RUNTIME_ADMISSION_MUST_REMAIN_FALSE"),
            ("production_readiness", "PRODUCTION_READINESS_MUST_REMAIN_FALSE"),
        ):
            with self.subTest(key=key):
                p = copy.deepcopy(BASE)
                p["claim_guard"][key] = True
                r = evaluate_assurance(p)
                self.assertEqual(r["decision"], "HOLD")
                self.assertIn(reason, r["reasons"])

    def test_invalid_hash_shape_holds_instead_of_crashing(self):
        p = copy.deepcopy(BASE)
        p["security"]["raw_artifact_sha256"] = "not-a-sha"
        r = evaluate_assurance(p)
        self.assertEqual(r["decision"], "HOLD")
        self.assertIn("SECURITY_ARTIFACT_SHA256_INVALID", r["reasons"])

    def test_unsupported_schema_fails_closed(self):
        p = copy.deepcopy(BASE)
        p["schema_version"] = "WRONG"
        with self.assertRaisesRegex(ValueError, "unsupported schema_version"):
            evaluate_assurance(p)


if __name__ == "__main__":
    unittest.main()
