import copy
import unittest

from ess_evidence_runtime import (
    Admission,
    build_receipt,
    replay_receipt,
)


BASE = {
    "schema_version": "ESS_EVIDENCE_RUNTIME_V1",
    "claim": "K_LQ_NEW_BASELINE_V4_20260918 is admissible as the current NEW_BASELINE.",
    "source": {
        "name": "choice-space-lq-shadow-v1",
        "version": 4,
        "sha256": "100ff50b72087f24e1b2a133391e79f49070f8c416b2f6e738ed04802d0c6fc7",
    },
    "execution": {
        "execution_id": "K_LQ_NEW_BASELINE_V4_20260918",
        "input_sha256": "0fc5c5fb7ca750fc3e21c1009f35fdddd894af99353cc13cc01cf138487c6e48",
        "output_sha256": "0fc5c5fb7ca750fc3e21c1009f35fdddd894af99353cc13cc01cf138487c6e48",
        "environment_id": "supabase:vuzphrlgkgxswjnexszw",
    },
    "provider_readback": {
        "provider": "supabase",
        "source_name": "choice-space-lq-shadow-v1",
        "source_version": 4,
        "source_sha256": "100ff50b72087f24e1b2a133391e79f49070f8c416b2f6e738ed04802d0c6fc7",
        "fresh": True,
    },
    "eq64": {
        "historical_identity": False,
        "fresh_readback": True,
        "semantic_contract": True,
        "baseline_bound": True,
        "admissible_execution": True,
        "negative_evidence": False,
    },
    "claim_level": 1,
    "previous_claim_level": 0,
    "new_admissible_evidence": True,
}


class ESSEvidenceRuntimeTests(unittest.TestCase):
    def test_k_lq_new_baseline_passes_without_rewriting_history(self):
        receipt = build_receipt(BASE)
        self.assertEqual(receipt["admission"], Admission.PASS.value)
        self.assertFalse(receipt["eq64"]["historical_identity"])
        self.assertEqual(receipt["historical_pre_step8_identity"], "HOLD_UNRECOVERED")

    def test_historical_restore_claim_holds_when_identity_is_missing(self):
        payload = copy.deepcopy(BASE)
        payload["claim_level"] = 2
        payload["eq64"]["baseline_bound"] = False
        payload["new_admissible_evidence"] = False
        receipt = build_receipt(payload)
        self.assertEqual(receipt["admission"], Admission.HOLD.value)

    def test_negative_evidence_rejects(self):
        payload = copy.deepcopy(BASE)
        payload["eq64"]["negative_evidence"] = True
        receipt = build_receipt(payload)
        self.assertEqual(receipt["admission"], Admission.REJECT.value)

    def test_silent_promotion_holds(self):
        payload = copy.deepcopy(BASE)
        payload["claim_level"] = 2
        payload["previous_claim_level"] = 1
        payload["new_admissible_evidence"] = False
        receipt = build_receipt(payload)
        self.assertEqual(receipt["admission"], Admission.HOLD.value)
        self.assertIn("NO_SILENT_PROMOTION", receipt["reasons"])

    def test_receipt_is_deterministic(self):
        a = build_receipt(BASE)
        b = build_receipt(copy.deepcopy(BASE))
        self.assertEqual(a["evidence_id"], b["evidence_id"])
        self.assertEqual(a["receipt_sha256"], b["receipt_sha256"])

    def test_replay_detects_tampering(self):
        receipt = build_receipt(BASE)
        tampered = copy.deepcopy(receipt)
        tampered["claim"] = "tampered"
        self.assertFalse(replay_receipt(tampered)["valid"])

    def test_provider_readback_mismatch_holds(self):
        payload = copy.deepcopy(BASE)
        payload["provider_readback"]["source_sha256"] = "0" * 64
        receipt = build_receipt(payload)
        self.assertEqual(receipt["admission"], Admission.HOLD.value)


if __name__ == "__main__":
    unittest.main()
