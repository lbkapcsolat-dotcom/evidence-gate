import json
import tempfile
import unittest
from pathlib import Path

from eq64_independent_reproduction_package import (
    build_manifest,
    verify_manifest,
    verify_tamper_rejection,
)


class EQ64IndependentReproductionPackageTests(unittest.TestCase):
    def test_manifest_verifies_and_detects_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.txt").write_text("alpha\n", encoding="utf-8")
            (root / "b.txt").write_text("beta\n", encoding="utf-8")

            manifest = build_manifest(root, ["a.txt", "b.txt"])
            self.assertTrue(verify_manifest(root, manifest))

            (root / "b.txt").write_text("tampered\n", encoding="utf-8")
            self.assertFalse(verify_manifest(root, manifest))

    def test_receipt_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "receipt.json"
            receipt = {
                "schema_version": "EQ64_EXECUTABLE_ASSURANCE_ENGINE_V1",
                "decision": "PASS",
                "reasons": ["ALL_EQ64_ASSURANCE_GATES_SATISFIED"],
                "eq64": {"bits": [1,1,1,1,1,1], "state_index": 63, "pass_state": 63},
                "target": {},
                "security": {},
                "regression": {},
                "readback": {},
                "claim_guard": {},
                "engine": {},
                "evidence_bundle_sha256": "0" * 64,
                "runtime_admission": False,
                "production_readiness": False,
                "global_bind": False,
                "pointer_promotion": False,
                "external_actuation": False,
            }
            import hashlib
            from eq64_executable_assurance_engine import canonical_bytes
            receipt["receipt_sha256"] = hashlib.sha256(canonical_bytes(receipt)).hexdigest()
            path.write_text(json.dumps(receipt), encoding="utf-8")
            self.assertTrue(verify_tamper_rejection(path))


if __name__ == "__main__":
    unittest.main()
