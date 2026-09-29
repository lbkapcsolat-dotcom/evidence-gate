import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from evidence_bound_authority import SQLiteSingleUseStore
from evidence_bound_hardening import (
    ExecutionStore,
    ExternalCoordinator,
    SimulatedExternalAdapter,
    external_idempotency_key,
)


NOW = "2026-09-29T16:00:00Z"
RECOVERY_AT = "2026-09-29T16:05:00Z"
T_HASH = hashlib.sha256(b"ESS-V6-V8-FIXTURE").hexdigest()
SINGLE_USE_ID = "su-v6-v8-fixture-001"
PAYLOAD = {"operation": "simulated_remote_write", "value": 7}


class CrashAndExternalHardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.worker = Path(__file__).with_name("evidence_bound_hardening_worker.py")

    def tearDown(self):
        self.tmp.cleanup()

    def run_consumer(self, auth_db: Path, start_marker: Path):
        return subprocess.Popen(
            [
                sys.executable,
                str(self.worker),
                "consume",
                str(auth_db),
                SINGLE_USE_ID,
                T_HASH,
                str(start_marker),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_process_level_concurrent_consumers_exactly_one_wins(self):
        auth_db = self.root / "concurrent.sqlite3"
        SQLiteSingleUseStore(auth_db)
        marker = self.root / "go"

        p1 = self.run_consumer(auth_db, marker)
        p2 = self.run_consumer(auth_db, marker)
        marker.write_text("go", encoding="utf-8")

        out1, err1 = p1.communicate(timeout=20)
        out2, err2 = p2.communicate(timeout=20)
        self.assertEqual(p1.returncode, 0, err1)
        self.assertEqual(p2.returncode, 0, err2)

        results = sorted([out1.strip(), out2.strip()])
        self.assertEqual(results, ["CONSUMED", "REPLAY_REJECTED"])

    def test_hard_process_restart_rejects_identical_replay(self):
        auth_db = self.root / "restart.sqlite3"
        SQLiteSingleUseStore(auth_db)

        marker1 = self.root / "go1"
        p1 = self.run_consumer(auth_db, marker1)
        marker1.write_text("go", encoding="utf-8")
        out1, err1 = p1.communicate(timeout=20)
        self.assertEqual(p1.returncode, 0, err1)
        self.assertEqual(out1.strip(), "CONSUMED")

        marker2 = self.root / "go2"
        p2 = self.run_consumer(auth_db, marker2)
        marker2.write_text("go", encoding="utf-8")
        out2, err2 = p2.communicate(timeout=20)
        self.assertEqual(p2.returncode, 0, err2)
        self.assertEqual(out2.strip(), "REPLAY_REJECTED")

    def _run_crash(self, crash_point: str):
        auth_db = self.root / f"{crash_point}-auth.sqlite3"
        execution_db = self.root / f"{crash_point}-exec.sqlite3"
        SQLiteSingleUseStore(auth_db)
        ExecutionStore(execution_db)

        proc = subprocess.run(
            [
                sys.executable,
                str(self.worker),
                "crash",
                str(auth_db),
                str(execution_db),
                SINGLE_USE_ID,
                T_HASH,
                crash_point,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertIn(proc.returncode, (70, 71, 72, 73))

        auth = SQLiteSingleUseStore(auth_db)
        self.assertFalse(auth.consume(SINGLE_USE_ID, T_HASH, RECOVERY_AT))

        store = ExecutionStore(execution_db)
        first = store.recover(T_HASH, RECOVERY_AT)
        receipt_before = first.receipt
        second = store.recover(T_HASH, RECOVERY_AT)

        self.assertIsNotNone(receipt_before)
        self.assertEqual(receipt_before, second.receipt)
        self.assertEqual(receipt_before["authorization_transcript_hash"], T_HASH)
        self.assertFalse(receipt_before["runtime_admission"])
        self.assertFalse(receipt_before["external_actuation"])
        self.assertTrue(receipt_before["zero_spend"])
        self.assertEqual(store.receipt_count(T_HASH), 1)
        self.assertLessEqual(store.effect_count(T_HASH), 1)

        return store, first, second

    def test_crash_after_consume_recovers_failure_without_effect(self):
        store, first, _ = self._run_crash("after_consume")
        self.assertEqual(first.phase, "FAILED_TERMINAL")
        self.assertEqual(first.status, "FAILURE_RECEIPT_CREATED")
        self.assertEqual(store.effect_count(T_HASH), 0)

    def test_crash_during_execution_rolls_back_uncommitted_effect(self):
        store, first, _ = self._run_crash("during_execution")
        self.assertEqual(first.phase, "FAILED_TERMINAL")
        self.assertEqual(store.effect_count(T_HASH), 0)

    def test_crash_after_effect_before_receipt_recovers_success_receipt(self):
        store, first, _ = self._run_crash("after_effect_before_receipt")
        self.assertEqual(first.phase, "RECEIPTED")
        self.assertEqual(first.status, "SUCCESS_RECEIPT_RECOVERED")
        self.assertEqual(store.effect_count(T_HASH), 1)

    def test_crash_after_receipt_commit_is_idempotent(self):
        store, first, second = self._run_crash("after_receipt_commit")
        self.assertEqual(first.phase, "RECEIPTED")
        self.assertEqual(first.status, "RECEIPT_ALREADY_PRESENT")
        self.assertEqual(first.receipt, second.receipt)
        self.assertEqual(store.effect_count(T_HASH), 1)

    def test_external_idempotency_key_is_bound_to_transcript_hash(self):
        key1 = external_idempotency_key(T_HASH)
        other = hashlib.sha256(b"other-transcript").hexdigest()
        key2 = external_idempotency_key(other)
        self.assertNotEqual(key1, key2)
        self.assertEqual(key1, external_idempotency_key(T_HASH))

    def test_ack_loss_is_reconciled_without_duplicate_remote_effect(self):
        execution_db = self.root / "external-queryable.sqlite3"
        remote_db = self.root / "remote-queryable.sqlite3"
        store = ExecutionStore(execution_db)
        adapter = SimulatedExternalAdapter(remote_db, queryable=True)
        coordinator = ExternalCoordinator(store)

        dispatched = coordinator.dispatch(
            t_hash=T_HASH,
            payload=PAYLOAD,
            adapter=adapter,
            at=NOW,
            lose_ack=True,
        )
        self.assertEqual(dispatched.status, "AMBIGUOUS_REMOTE")
        self.assertEqual(adapter.effect_count(dispatched.idempotency_key), 1)

        recovered = coordinator.reconcile(
            t_hash=T_HASH,
            adapter=adapter,
            at=RECOVERY_AT,
        )
        self.assertEqual(recovered.status, "REMOTE_ACK_RECOVERED")
        self.assertIsNotNone(recovered.remote_effect_id)
        self.assertEqual(adapter.effect_count(dispatched.idempotency_key), 1)

    def test_unprovable_remote_state_holds_and_never_blind_retries(self):
        execution_db = self.root / "external-unprovable.sqlite3"
        remote_db = self.root / "remote-unprovable.sqlite3"
        store = ExecutionStore(execution_db)
        adapter = SimulatedExternalAdapter(remote_db, queryable=False)
        coordinator = ExternalCoordinator(store)

        dispatched = coordinator.dispatch(
            t_hash=T_HASH,
            payload=PAYLOAD,
            adapter=adapter,
            at=NOW,
            lose_ack=True,
        )
        self.assertEqual(dispatched.status, "AMBIGUOUS_REMOTE")
        self.assertEqual(adapter.effect_count(dispatched.idempotency_key), 1)

        recovered = coordinator.reconcile(
            t_hash=T_HASH,
            adapter=adapter,
            at=RECOVERY_AT,
        )
        self.assertEqual(
            recovered.status,
            "HOLD_AMBIGUOUS_REMOTE_NO_BLIND_RETRY",
        )
        self.assertEqual(adapter.effect_count(dispatched.idempotency_key), 1)

        intent = store.read_external_intent(T_HASH)
        self.assertEqual(intent["state"], "HOLD_AMBIGUOUS_REMOTE_NO_BLIND_RETRY")


if __name__ == "__main__":
    unittest.main()
