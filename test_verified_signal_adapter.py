import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CANARY = {
    "schema_version": "ESS_NEWSIFY_VERIFIED_SIGNAL_TO_EVIDENCE_ADAPTER_V1",
    "claim": (
        "A cable fire disrupted long-distance rail traffic between Hegyeshalom "
        "and Vienna, with RailJet, RegioJet and EuroCity services restricted "
        "to Hegyeshalom and replacement buses organized."
    ),
    "signal": {
        "id": "ed0943e6-591a-4b6f-9d73-c9d1c6f43464",
        "trend_id": "c831db62-a421-4f6d-aaf1-d0cc22594588",
        "fingerprint": "251c20fc",
        "title": "Cable Fire Halts Rail Service on Key Hungary-Austria Line",
        "source_class": "SIGNAL_SOURCE",
        "observed_at": "2026-10-03T20:58:28.438Z",
        "source_url": None,
    },
    "relevance": {
        "status": "RELEVANT",
        "domain": "CRITICAL_INFRASTRUCTURE",
        "reason": "Cross-border rail disruption is a bounded infrastructure canary.",
    },
    "verification": {
        "status": "VERIFIED",
        "trust_class": "PRIMARY_OPERATOR_SOURCE",
        "source_name": "MÁV-csoport MÁVINFORM",
        "source_url": (
            "https://www.mavcsoport.hu/mavinform/"
            "szunetel-kozlekedes-hegyeshalomnal-ausztria-fele"
        ),
        "published_date": "2026-10-03",
        "source_sha256": "24c96914e262867a82f9dfbabcdab2e27eca0f3fb5814584a28d308419f8ac84",
        "assessment": "supports",
        "contradiction": False,
    },
}


class NewsifyVerifiedSignalAdapterTests(unittest.TestCase):
    def test_verified_primary_source_becomes_evidence_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "canary.json"
            path.write_text(json.dumps(CANARY), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "verified_signal_adapter.py", str(path)],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["classification"]["status"], "SUPPORTED")
        self.assertTrue(result["evidence_candidate"])
        self.assertFalse(result["evidence_authority"])
        self.assertFalse(result["automatic_promotion"])

    def test_irrelevant_signal_is_rejected_before_verification(self):
        payload = json.loads(json.dumps(CANARY))
        payload["relevance"]["status"] = "IRRELEVANT"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "canary.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "verified_signal_adapter.py", str(path)],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["adapter_status"], "REJECT_IRRELEVANT")
        self.assertFalse(result["evidence_candidate"])

    def test_unverified_signal_holds(self):
        payload = json.loads(json.dumps(CANARY))
        payload["verification"]["status"] = "UNVERIFIED"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "canary.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "verified_signal_adapter.py", str(path)],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["adapter_status"], "HOLD_VERIFY_REQUIRED")
        self.assertFalse(result["evidence_candidate"])


if __name__ == "__main__":
    unittest.main()
