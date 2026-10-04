import json
import unittest
from pathlib import Path

from newsify_multi_signal_router import route_batch


SCHEMA = "ESS_NEWSIFY_MULTI_SIGNAL_ROUTER__DEDUP_RELEVANCE_VERIFICATION_QUEUE_AND_CONTRADICTION_PROPAGATION_V1"


def sig(sid, trend, fp, title, content="", claim_key=None):
    item = {
        "id": sid,
        "trendId": trend,
        "newsItemsFingerprint": fp,
        "title": title,
        "content": content,
        "sourceUrl": None,
    }
    if claim_key:
        item["claim_key"] = claim_key
    return item


class NewsifyMultiSignalRouterTests(unittest.TestCase):
    def test_dedup_relevance_queue_and_verified_candidate(self):
        payload = {
            "schema_version": SCHEMA,
            "signals": [
                sig("1", "sports-1", "fp-a", "Messi friendly match"),
                sig("2", "rail-1", "fp-b", "Cable fire halts rail service", "RailJet replacement buses"),
                sig("3", "rail-1", "fp-c", "Duplicate rail trend", "same trend id"),
                sig("4", "ai-1", "fp-d", "AI agent security and MCP supply-chain risk"),
            ],
            "verifications": [
                {
                    "signal_id": "2",
                    "claim_key": "rail-disruption",
                    "status": "VERIFIED",
                    "trust_class": "PRIMARY_OPERATOR_SOURCE",
                    "source_name": "MAV",
                    "source_url": "https://example.com/mav",
                    "source_sha256": "a" * 64,
                    "assessment": "supports",
                }
            ],
        }
        result = route_batch(payload)
        by_id = {row["signal_id"]: row for row in result["routes"]}
        self.assertEqual(by_id["1"]["route_status"], "REJECT_IRRELEVANT")
        self.assertEqual(by_id["2"]["route_status"], "EVIDENCE_CANDIDATE")
        self.assertTrue(by_id["2"]["evidence_candidate"])
        self.assertEqual(by_id["3"]["route_status"], "DUPLICATE")
        self.assertEqual(by_id["4"]["route_status"], "VERIFY_REQUIRED")
        self.assertEqual(result["verification_queue"], ["4"])

    def test_duplicate_fingerprint_is_rejected_even_when_trend_id_differs(self):
        payload = {
            "schema_version": SCHEMA,
            "signals": [
                sig("1", "t1", "same-fp", "NASA satellite update"),
                sig("2", "t2", "same-fp", "NASA satellite update copied"),
            ],
            "verifications": [],
        }
        result = route_batch(payload)
        self.assertEqual(result["routes"][1]["route_status"], "DUPLICATE")

    def test_contradiction_propagates_to_same_claim_key(self):
        payload = {
            "schema_version": SCHEMA,
            "signals": [
                sig("1", "t1", "fp1", "AI agent security incident", claim_key="claim-x"),
                sig("2", "t2", "fp2", "Cybersecurity follow-up", claim_key="claim-x"),
            ],
            "verifications": [
                {
                    "signal_id": "1",
                    "claim_key": "claim-x",
                    "status": "VERIFIED",
                    "trust_class": "PRIMARY_OFFICIAL_SOURCE",
                    "source_name": "Official A",
                    "source_url": "https://example.com/a",
                    "source_sha256": "b" * 64,
                    "assessment": "supports",
                },
                {
                    "signal_id": "2",
                    "claim_key": "claim-x",
                    "status": "VERIFIED",
                    "trust_class": "PRIMARY_OFFICIAL_SOURCE",
                    "source_name": "Official B",
                    "source_url": "https://example.com/b",
                    "source_sha256": "c" * 64,
                    "assessment": "contradicts",
                },
            ],
        }
        result = route_batch(payload)
        self.assertEqual(result["conflict_claim_keys"], ["claim-x"])
        self.assertTrue(all(r["route_status"] == "HOLD_CONFLICT" for r in result["routes"]))
        self.assertTrue(all(not r["evidence_candidate"] for r in result["routes"]))

    def test_untrusted_or_unverified_sources_stay_in_verification_queue(self):
        payload = {
            "schema_version": SCHEMA,
            "signals": [
                sig("1", "t1", "fp1", "AI Act governance update"),
            ],
            "verifications": [
                {
                    "signal_id": "1",
                    "claim_key": "ai-act",
                    "status": "UNVERIFIED",
                    "trust_class": "SECONDARY_BLOG",
                    "source_name": "Blog",
                    "source_url": "https://example.com/blog",
                    "source_sha256": "d" * 64,
                    "assessment": "supports",
                }
            ],
        }
        result = route_batch(payload)
        self.assertEqual(result["routes"][0]["route_status"], "VERIFY_REQUIRED")
        self.assertEqual(result["verification_queue"], ["1"])

    def test_router_is_nonpromoting(self):
        payload = {
            "schema_version": SCHEMA,
            "signals": [sig("1", "t1", "fp1", "NASA satellite update")],
            "verifications": [],
        }
        result = route_batch(payload)
        self.assertFalse(result["evidence_authority"])
        self.assertFalse(result["automatic_promotion"])
        self.assertFalse(result["pointer_promotion"])
        self.assertFalse(result["global_bind"])
        self.assertFalse(result["runtime_admission"])
        self.assertFalse(result["production_readiness"])

    def test_live_hu_batch_routes_one_candidate_and_one_verification_queue(self):
        payload = json.loads(
            Path("examples/newsify_multi_signal_live_canary_20261004.json")
            .read_text(encoding="utf-8")
        )
        result = route_batch(payload)
        by_id = {row["signal_id"]: row for row in result["routes"]}
        self.assertEqual(
            by_id["ed0943e6-591a-4b6f-9d73-c9d1c6f43464"]["route_status"],
            "EVIDENCE_CANDIDATE",
        )
        self.assertEqual(
            by_id["d1f90dea-ea8d-4931-b46d-06ad0693907a"]["route_status"],
            "VERIFY_REQUIRED",
        )
        self.assertEqual(
            result["verification_queue"],
            ["d1f90dea-ea8d-4931-b46d-06ad0693907a"],
        )
        self.assertEqual(result["counts"]["REJECT_IRRELEVANT"], 4)


if __name__ == "__main__":
    unittest.main()
