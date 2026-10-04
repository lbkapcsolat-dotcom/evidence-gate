import copy
import multiprocessing
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import evidence_bound_authority as eba

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



def _process_consume_worker(db_path, start_event, output_queue):
    start_event.wait()
    store = eba.SQLiteSingleUseStore(db_path)
    output_queue.put(store.consume("su-process-0001", "t-process-0001", NOW))


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


    def _execution_fixture(self):
        remote_db = Path(self.tmp.name) / "simulated-remote.sqlite3"
        return (
            eba.SQLiteSingleUseStore(self.db),
            eba.SimulatedExternalAdapter(remote_db),
        )

    def _execute_reference_effect(self, *, store, adapter, crash_at=None, adapter_behavior="normal"):
        return eba.execute_reference_effect(
            transcript=self.transcript,
            signature_b64=self.signature,
            public_key=self.public_key,
            current_action=ACTION,
            current_authority=AUTHORITY,
            current_evidence=EVIDENCE,
            now=NOW,
            store=store,
            adapter=adapter,
            effect_payload={"target": "fixture-001", "value": 1},
            pre_state={"value": 0},
            post_state={"value": 1},
            crash_at=crash_at,
            adapter_behavior=adapter_behavior,
        )

    def _recover_reference_effect(self, *, store, adapter):
        return eba.recover_reference_execution(
            transcript=self.transcript,
            store=store,
            adapter=adapter,
            effect_payload={"target": "fixture-001", "value": 1},
            pre_state={"value": 0},
            post_state={"value": 1},
            executed_at=NOW,
        )

    def test_process_level_concurrent_consumers_exactly_one_wins(self):
        ctx = multiprocessing.get_context("spawn")
        start_event = ctx.Event()
        output_queue = ctx.Queue()
        a = ctx.Process(target=_process_consume_worker, args=(str(self.db), start_event, output_queue))
        b = ctx.Process(target=_process_consume_worker, args=(str(self.db), start_event, output_queue))
        a.start()
        b.start()
        start_event.set()
        results = [output_queue.get(timeout=10), output_queue.get(timeout=10)]
        a.join(timeout=10)
        b.join(timeout=10)
        self.assertEqual(a.exitcode, 0)
        self.assertEqual(b.exitcode, 0)
        self.assertEqual(sorted(results), [False, True])

    def test_hard_process_restart_preserves_single_use_consumption(self):
        script = (
            "from evidence_bound_authority import SQLiteSingleUseStore;"
            "import sys;"
            "s=SQLiteSingleUseStore(sys.argv[1]);"
            "print('1' if s.consume('su-hard-restart','t-hard-restart','2026-09-29T15:30:00Z') else '0')"
        )
        first = subprocess.run(
            [sys.executable, "-c", script, str(self.db)],
            check=True,
            capture_output=True,
            text=True,
        )
        second = subprocess.run(
            [sys.executable, "-c", script, str(self.db)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(first.stdout.strip(), "1")
        self.assertEqual(second.stdout.strip(), "0")

    def test_crash_after_consumed_recovers_without_authorization_reuse(self):
        store, adapter = self._execution_fixture()
        with self.assertRaises(eba.InjectedCrash):
            self._execute_reference_effect(store=store, adapter=adapter, crash_at="CONSUMED")
        self.assertEqual(store.read_execution(self.transcript["single_use_id"])["phase"], "CONSUMED")

        recovered = self._recover_reference_effect(store=store, adapter=adapter)
        self.assertEqual(recovered.status, "PASS_RECEIPTED")
        self.assertEqual(recovered.phase, "RECEIPTED")
        self.assertEqual(adapter.effect_count(transcript_hash(self.transcript)), 1)
        self.assertEqual(self.validate(store=store).status, "HOLD_REPLAY_CONSUMED")

    def test_crash_after_executing_fails_closed_without_blind_retry(self):
        store, adapter = self._execution_fixture()
        with self.assertRaises(eba.InjectedCrash):
            self._execute_reference_effect(store=store, adapter=adapter, crash_at="EXECUTING")
        self.assertEqual(store.read_execution(self.transcript["single_use_id"])["phase"], "EXECUTING")

        recovered = self._recover_reference_effect(store=store, adapter=adapter)
        self.assertEqual(recovered.status, "HOLD_FAILED_TERMINAL")
        self.assertEqual(recovered.phase, "FAILED_TERMINAL")
        self.assertEqual(adapter.attempt_count(transcript_hash(self.transcript)), 0)
        self.assertEqual(adapter.effect_count(transcript_hash(self.transcript)), 0)

    def test_crash_after_effect_committed_recovers_receipt_without_duplicate_effect(self):
        store, adapter = self._execution_fixture()
        with self.assertRaises(eba.InjectedCrash):
            self._execute_reference_effect(store=store, adapter=adapter, crash_at="EFFECT_COMMITTED")
        self.assertEqual(store.read_execution(self.transcript["single_use_id"])["phase"], "EFFECT_COMMITTED")

        recovered = self._recover_reference_effect(store=store, adapter=adapter)
        self.assertEqual(recovered.status, "PASS_RECEIPTED")
        self.assertEqual(recovered.receipt["authorization_transcript_hash"], transcript_hash(self.transcript))
        self.assertEqual(adapter.attempt_count(transcript_hash(self.transcript)), 1)
        self.assertEqual(adapter.effect_count(transcript_hash(self.transcript)), 1)

    def test_crash_after_receipted_returns_persisted_receipt(self):
        store, adapter = self._execution_fixture()
        with self.assertRaises(eba.InjectedCrash):
            self._execute_reference_effect(store=store, adapter=adapter, crash_at="RECEIPTED")
        before = store.read_execution(self.transcript["single_use_id"])
        self.assertEqual(before["phase"], "RECEIPTED")

        recovered = self._recover_reference_effect(store=store, adapter=adapter)
        self.assertEqual(recovered.status, "PASS_RECEIPTED")
        self.assertEqual(recovered.receipt, before["receipt"])
        self.assertEqual(adapter.effect_count(transcript_hash(self.transcript)), 1)

    def test_ack_loss_recovers_by_readback_without_blind_retry(self):
        store, adapter = self._execution_fixture()
        outcome = self._execute_reference_effect(
            store=store,
            adapter=adapter,
            adapter_behavior="ack_loss",
        )
        self.assertEqual(outcome.status, "HOLD_ACK_LOST")
        self.assertEqual(outcome.phase, "EXECUTING")
        self.assertEqual(adapter.attempt_count(transcript_hash(self.transcript)), 1)
        self.assertEqual(adapter.effect_count(transcript_hash(self.transcript)), 1)

        recovered = self._recover_reference_effect(store=store, adapter=adapter)
        self.assertEqual(recovered.status, "PASS_RECEIPTED")
        self.assertEqual(adapter.attempt_count(transcript_hash(self.transcript)), 1)
        self.assertEqual(adapter.effect_count(transcript_hash(self.transcript)), 1)

    def test_ambiguous_remote_state_fails_terminal_without_retry(self):
        store, adapter = self._execution_fixture()
        outcome = self._execute_reference_effect(
            store=store,
            adapter=adapter,
            adapter_behavior="ambiguous",
        )
        self.assertEqual(outcome.status, "HOLD_AMBIGUOUS_REMOTE_STATE")
        self.assertEqual(outcome.phase, "EXECUTING")
        self.assertEqual(adapter.attempt_count(transcript_hash(self.transcript)), 1)

        recovered = self._recover_reference_effect(store=store, adapter=adapter)
        self.assertEqual(recovered.status, "HOLD_FAILED_TERMINAL")
        self.assertEqual(recovered.phase, "FAILED_TERMINAL")
        self.assertEqual(adapter.attempt_count(transcript_hash(self.transcript)), 1)
        self.assertEqual(adapter.effect_count(transcript_hash(self.transcript)), 0)

    def test_idempotency_key_is_exact_transcript_hash(self):
        store, adapter = self._execution_fixture()
        outcome = self._execute_reference_effect(store=store, adapter=adapter)
        t_hash = transcript_hash(self.transcript)
        self.assertEqual(outcome.status, "PASS_RECEIPTED")
        remote = adapter.read_effect(t_hash)
        self.assertIsNotNone(remote)
        self.assertEqual(remote["idempotency_key"], t_hash)
        self.assertEqual(outcome.receipt["authorization_transcript_hash"], t_hash)
        self.assertFalse(outcome.receipt["external_actuation"])
        self.assertFalse(outcome.receipt["runtime_admission"])


if __name__ == "__main__":
    unittest.main()
