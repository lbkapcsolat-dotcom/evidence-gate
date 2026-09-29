import copy
import tempfile
import threading
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from evidence_bound_authority import (
    SQLiteSingleUseStore,
    build_execution_receipt,
    canonical_bytes,
    make_transcript,
    sign_transcript,
    transcript_hash,
    validate_and_consume,
)


ACTION = {
    "tool": "ess.reference.local",
    "operation": "set_state",
    "target": "fixture-001",
    "value": {"mode": "TEST_ONLY"},
}
AUTHORITY = {
    "principal": "human:fixture-reviewer",
    "permissions": ["ess.reference.local:set_state"],
    "delegation_state": "DIRECT",
    "revocation_generation": 7,
    "valid": True,
}
EVIDENCE = {
    "evidence_ids": ["ev-001", "ev-002"],
    "predicate": "2_OF_2_VALID",
    "fresh": True,
}

NOT_BEFORE = "2026-09-29T14:00:00Z"
NOT_AFTER = "2026-09-29T18:00:00Z"
NOW = "2026-09-29T15:30:00Z"


class EvidenceBoundAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "single_use.sqlite3"
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.transcript = make_transcript(
            action=ACTION,
            authority=AUTHORITY,
            evidence=EVIDENCE,
            human_principal_id="human:fixture-reviewer",
            signer_key_id="fixture-ed25519-key-1",
            not_before=NOT_BEFORE,
            not_after=NOT_AFTER,
            single_use_id="su-fixture-0001",
            context_id="ESS-V5-REFERENCE",
        )
        self.signature = sign_transcript(self.private_key, self.transcript)

    def tearDown(self):
        self.tmp.cleanup()

    def validate(self, *, action=ACTION, authority=AUTHORITY, evidence=EVIDENCE, store=None):
        return validate_and_consume(
            transcript=self.transcript,
            signature_b64=self.signature,
            public_key=self.public_key,
            current_action=action,
            current_authority=authority,
            current_evidence=evidence,
            now=NOW,
            store=store or SQLiteSingleUseStore(self.db),
        )

    def test_canonical_transcript_is_deterministic(self):
        reordered = dict(reversed(list(self.transcript.items())))
        self.assertEqual(canonical_bytes(self.transcript), canonical_bytes(reordered))
        self.assertEqual(transcript_hash(self.transcript), transcript_hash(reordered))

    def test_action_mutation_fails_closed(self):
        mutated = copy.deepcopy(ACTION)
        mutated["target"] = "fixture-OTHER"
        self.assertEqual(self.validate(action=mutated).status, "HOLD_ACTION_MISMATCH")

    def test_authority_mutation_fails_closed(self):
        mutated = copy.deepcopy(AUTHORITY)
        mutated["permissions"] = []
        self.assertEqual(self.validate(authority=mutated).status, "HOLD_AUTHORITY_MISMATCH")

    def test_evidence_mutation_fails_closed(self):
        mutated = copy.deepcopy(EVIDENCE)
        mutated["fresh"] = False
        self.assertEqual(self.validate(evidence=mutated).status, "HOLD_EVIDENCE_MISMATCH")

    def test_replay_is_rejected(self):
        store = SQLiteSingleUseStore(self.db)
        self.assertEqual(self.validate(store=store).status, "PASS_CONSUMED")
        self.assertEqual(self.validate(store=store).status, "HOLD_REPLAY_CONSUMED")

    def test_post_revocation_authority_is_stale(self):
        revoked = copy.deepcopy(AUTHORITY)
        revoked["revocation_generation"] = 8
        revoked["valid"] = False
        self.assertEqual(self.validate(authority=revoked).status, "HOLD_AUTHORITY_MISMATCH")

    def test_unknown_authority_fails_closed(self):
        self.assertEqual(self.validate(authority=None).status, "HOLD_UNKNOWN_AUTHORITY")

    def test_human_signature_is_bound_to_transcript(self):
        tampered = copy.deepcopy(self.transcript)
        tampered["context_id"] = "TAMPERED"
        decision = validate_and_consume(
            transcript=tampered,
            signature_b64=self.signature,
            public_key=self.public_key,
            current_action=ACTION,
            current_authority=AUTHORITY,
            current_evidence=EVIDENCE,
            now=NOW,
            store=SQLiteSingleUseStore(self.db),
        )
        self.assertEqual(decision.status, "HOLD_INVALID_HUMAN_SIGNATURE")

    def test_receipt_links_back_to_exact_transcript(self):
        receipt = build_execution_receipt(
            transcript=self.transcript,
            execution_status="REFERENCE_EFFECT_COMMITTED",
            result={"ok": True},
            pre_state={"value": 0},
            post_state={"value": 1},
            executed_at=NOW,
        )
        self.assertEqual(receipt["authorization_transcript_hash"], transcript_hash(self.transcript))
        self.assertFalse(receipt["runtime_admission"])
        self.assertFalse(receipt["external_actuation"])

    def test_two_concurrent_consumers_exactly_one_wins(self):
        barrier = threading.Barrier(2, timeout=5.0)
        results = []
        lock = threading.Lock()

        def worker():
            store = SQLiteSingleUseStore(self.db)
            barrier.wait(timeout=5.0)
            status = self.validate(store=store).status
            with lock:
                results.append(status)

        a = threading.Thread(target=worker)
        b = threading.Thread(target=worker)
        a.start()
        b.start()
        a.join()
        b.join()

        self.assertEqual(sorted(results), ["HOLD_REPLAY_CONSUMED", "PASS_CONSUMED"])

    def test_consumed_state_survives_store_reopen(self):
        first_store = SQLiteSingleUseStore(self.db)
        self.assertEqual(self.validate(store=first_store).status, "PASS_CONSUMED")
        reopened_store = SQLiteSingleUseStore(self.db)
        self.assertEqual(self.validate(store=reopened_store).status, "HOLD_REPLAY_CONSUMED")
        row = reopened_store.read(self.transcript["single_use_id"])
        self.assertIsNotNone(row)
        self.assertEqual(row["transcript_hash"], transcript_hash(self.transcript))


if __name__ == "__main__":
    unittest.main()
