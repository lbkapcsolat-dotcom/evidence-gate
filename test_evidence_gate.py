import unittest

from evidence_gate import EvidenceStatus, classify_claim, classify_payload


class EvidenceGateTests(unittest.TestCase):
    def test_supported_when_support_exists_without_contradiction(self):
        result = classify_claim(
            "The dataset contains 100 rows.",
            [
                {"assessment": "supports"},
                {"assessment": "insufficient"},
            ],
        )
        self.assertEqual(result.status, EvidenceStatus.SUPPORTED)
        self.assertEqual(result.supporting_count, 1)
        self.assertEqual(result.contradicting_count, 0)

    def test_conflicting_when_any_evidence_contradicts(self):
        result = classify_claim(
            "The dataset contains 100 rows.",
            [
                {"assessment": "supports"},
                {"assessment": "contradicts"},
            ],
        )
        self.assertEqual(result.status, EvidenceStatus.CONFLICTING)
        self.assertEqual(result.supporting_count, 1)
        self.assertEqual(result.contradicting_count, 1)

    def test_insufficient_when_no_support_or_contradiction_exists(self):
        result = classify_claim(
            "The dataset contains 100 rows.",
            [{"assessment": "insufficient"}],
        )
        self.assertEqual(result.status, EvidenceStatus.INSUFFICIENT)

    def test_empty_evidence_is_insufficient(self):
        result = classify_payload({"claim": "A claim", "evidence": []})
        self.assertEqual(result.status, EvidenceStatus.INSUFFICIENT)

    def test_unknown_assessment_is_rejected(self):
        with self.assertRaises(ValueError):
            classify_claim("A claim", [{"assessment": "maybe"}])

    def test_signal_source_cannot_directly_support_a_claim(self):
        result = classify_claim(
            "A signal-only claim.",
            [
                {
                    "source": "Newsify:trend-123",
                    "source_class": "SIGNAL_SOURCE",
                    "assessment": "supports",
                }
            ],
        )
        self.assertEqual(result.status, EvidenceStatus.INSUFFICIENT)
        self.assertEqual(result.supporting_count, 0)
        self.assertEqual(result.insufficient_count, 1)


if __name__ == "__main__":
    unittest.main()
