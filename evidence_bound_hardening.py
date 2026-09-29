from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from evidence_bound_authority import canonical_bytes

PHASES = (
    "CONSUMED",
    "EXECUTING",
    "EFFECT_COMMITTED",
    "RECEIPTED",
    "FAILED_TERMINAL",
)

RECEIPT_DOMAIN = b"ESS.HARDENING.RECEIPT.V1\x00"
EFFECT_DOMAIN = b"ESS.HARDENING.LOCAL_EFFECT.V1\x00"
EXTERNAL_IDEMPOTENCY_DOMAIN = b"ESS.EXTERNAL.IDEMPOTENCY.V1\x00"
EXTERNAL_PAYLOAD_DOMAIN = b"ESS.EXTERNAL.PAYLOAD.V1\x00"


def _hash(domain: bytes, value: Any) -> str:
    return hashlib.sha256(domain + canonical_bytes(value)).hexdigest()


def external_idempotency_key(t_hash: str) -> str:
    if len(t_hash) != 64:
        raise ValueError("t_hash must be a sha256 hex digest")
    bytes.fromhex(t_hash)
    return hashlib.sha256(
        EXTERNAL_IDEMPOTENCY_DOMAIN + bytes.fromhex(t_hash)
    ).hexdigest()


def _receipt_hash(body: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        RECEIPT_DOMAIN + canonical_bytes(dict(body))
    ).hexdigest()


@dataclass(frozen=True)
class RecoveryResult:
    phase: str
    status: str
    receipt: dict[str, Any] | None


class ExecutionStore:
    """Reference-only local crash-consistency state machine."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS execution_state (
                    t_hash TEXT PRIMARY KEY,
                    single_use_id TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS local_effects (
                    t_hash TEXT PRIMARY KEY,
                    effect_json TEXT NOT NULL,
                    effect_hash TEXT NOT NULL,
                    committed_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS execution_receipts (
                    t_hash TEXT PRIMARY KEY,
                    receipt_json TEXT NOT NULL,
                    receipt_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS external_intents (
                    t_hash TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    payload_hash TEXT NOT NULL,
                    state TEXT NOT NULL,
                    remote_effect_id TEXT,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def create_consumed(self, t_hash: str, single_use_id: str, at: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO execution_state (t_hash, single_use_id, phase, updated_at)
                VALUES (?, ?, 'CONSUMED', ?)
                """,
                (t_hash, single_use_id, at),
            )

    def transition(self, t_hash: str, expected: str, target: str, at: str) -> bool:
        if target not in PHASES:
            raise ValueError("unsupported target phase")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(
                """
                UPDATE execution_state
                SET phase = ?, updated_at = ?
                WHERE t_hash = ? AND phase = ?
                """,
                (target, at, t_hash, expected),
            )
            if cur.rowcount != 1:
                conn.execute("ROLLBACK")
                return False
            conn.execute("COMMIT")
            return True
        finally:
            conn.close()

    def begin_execution(self, t_hash: str, at: str) -> bool:
        return self.transition(t_hash, "CONSUMED", "EXECUTING", at)

    def commit_local_effect(
        self,
        t_hash: str,
        effect: Mapping[str, Any],
        at: str,
    ) -> str:
        effect_body = dict(effect)
        effect_json = canonical_bytes(effect_body).decode("utf-8")
        effect_hash = _hash(EFFECT_DOMAIN, effect_body)

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT phase FROM execution_state WHERE t_hash = ?",
                (t_hash,),
            ).fetchone()
            if row is None or row[0] != "EXECUTING":
                conn.execute("ROLLBACK")
                raise RuntimeError("local effect requires EXECUTING phase")
            conn.execute(
                """
                INSERT INTO local_effects
                (t_hash, effect_json, effect_hash, committed_at)
                VALUES (?, ?, ?, ?)
                """,
                (t_hash, effect_json, effect_hash, at),
            )
            conn.execute(
                """
                UPDATE execution_state
                SET phase = 'EFFECT_COMMITTED', updated_at = ?
                WHERE t_hash = ?
                """,
                (at, t_hash),
            )
            conn.execute("COMMIT")
            return effect_hash
        finally:
            conn.close()

    def _build_receipt(
        self,
        *,
        t_hash: str,
        single_use_id: str,
        status: str,
        phase: str,
        effect_hash: str | None,
        at: str,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema_version": "ESS_CRASH_RECOVERY_RECEIPT_V1",
            "authorization_transcript_hash": t_hash,
            "single_use_id": single_use_id,
            "status": status,
            "phase": phase,
            "effect_hash": effect_hash,
            "created_at": at,
            "runtime_admission": False,
            "external_actuation": False,
            "zero_spend": True,
        }
        body["receipt_sha256"] = _receipt_hash(body)
        return body

    def _insert_receipt_and_phase(
        self,
        *,
        t_hash: str,
        receipt: Mapping[str, Any],
        target_phase: str,
        at: str,
    ) -> dict[str, Any]:
        receipt_json = canonical_bytes(dict(receipt)).decode("utf-8")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                """
                SELECT receipt_json FROM execution_receipts WHERE t_hash = ?
                """,
                (t_hash,),
            ).fetchone()
            if existing is not None:
                conn.execute("ROLLBACK")
                return json.loads(existing[0])
            conn.execute(
                """
                INSERT INTO execution_receipts
                (t_hash, receipt_json, receipt_sha256, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (t_hash, receipt_json, receipt["receipt_sha256"], at),
            )
            conn.execute(
                """
                UPDATE execution_state
                SET phase = ?, updated_at = ?
                WHERE t_hash = ?
                """,
                (target_phase, at, t_hash),
            )
            conn.execute("COMMIT")
            return dict(receipt)
        finally:
            conn.close()

    def commit_success_receipt(self, t_hash: str, at: str) -> dict[str, Any]:
        state = self.read_state(t_hash)
        if state is None:
            raise RuntimeError("unknown execution")
        if state["phase"] != "EFFECT_COMMITTED":
            existing = self.read_receipt(t_hash)
            if existing is not None:
                return existing
            raise RuntimeError("success receipt requires EFFECT_COMMITTED")
        effect = self.read_effect(t_hash)
        if effect is None:
            raise RuntimeError("EFFECT_COMMITTED without local effect")
        receipt = self._build_receipt(
            t_hash=t_hash,
            single_use_id=state["single_use_id"],
            status="SUCCESS_LOCAL_EFFECT_COMMITTED",
            phase="RECEIPTED",
            effect_hash=effect["effect_hash"],
            at=at,
        )
        return self._insert_receipt_and_phase(
            t_hash=t_hash,
            receipt=receipt,
            target_phase="RECEIPTED",
            at=at,
        )

    def read_state(self, t_hash: str) -> dict[str, str] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT t_hash, single_use_id, phase, updated_at
                FROM execution_state WHERE t_hash = ?
                """,
                (t_hash,),
            ).fetchone()
        if row is None:
            return None
        return {
            "t_hash": row[0],
            "single_use_id": row[1],
            "phase": row[2],
            "updated_at": row[3],
        }

    def read_effect(self, t_hash: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT effect_json, effect_hash, committed_at
                FROM local_effects WHERE t_hash = ?
                """,
                (t_hash,),
            ).fetchone()
        if row is None:
            return None
        return {
            "effect": json.loads(row[0]),
            "effect_hash": row[1],
            "committed_at": row[2],
        }

    def effect_count(self, t_hash: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM local_effects WHERE t_hash = ?",
                (t_hash,),
            ).fetchone()
        return int(row[0])

    def read_receipt(self, t_hash: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT receipt_json FROM execution_receipts WHERE t_hash = ?
                """,
                (t_hash,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def receipt_count(self, t_hash: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM execution_receipts WHERE t_hash = ?",
                (t_hash,),
            ).fetchone()
        return int(row[0])

    def recover(self, t_hash: str, at: str) -> RecoveryResult:
        state = self.read_state(t_hash)
        if state is None:
            return RecoveryResult("UNKNOWN", "HOLD_UNKNOWN_EXECUTION", None)

        existing = self.read_receipt(t_hash)
        if existing is not None:
            return RecoveryResult(state["phase"], "RECEIPT_ALREADY_PRESENT", existing)

        effect = self.read_effect(t_hash)
        phase = state["phase"]

        if phase in ("CONSUMED", "EXECUTING"):
            if effect is not None:
                return RecoveryResult(
                    phase,
                    "HOLD_INCONSISTENT_EFFECT_WITHOUT_COMMIT_PHASE",
                    None,
                )
            receipt = self._build_receipt(
                t_hash=t_hash,
                single_use_id=state["single_use_id"],
                status="FAILED_NO_EFFECT_COMMITTED",
                phase="FAILED_TERMINAL",
                effect_hash=None,
                at=at,
            )
            stored = self._insert_receipt_and_phase(
                t_hash=t_hash,
                receipt=receipt,
                target_phase="FAILED_TERMINAL",
                at=at,
            )
            return RecoveryResult("FAILED_TERMINAL", "FAILURE_RECEIPT_CREATED", stored)

        if phase == "EFFECT_COMMITTED":
            if effect is None:
                return RecoveryResult(
                    phase,
                    "HOLD_INCONSISTENT_COMMIT_WITHOUT_EFFECT",
                    None,
                )
            receipt = self.commit_success_receipt(t_hash, at)
            return RecoveryResult("RECEIPTED", "SUCCESS_RECEIPT_RECOVERED", receipt)

        if phase == "FAILED_TERMINAL":
            receipt = self._build_receipt(
                t_hash=t_hash,
                single_use_id=state["single_use_id"],
                status="FAILED_NO_EFFECT_COMMITTED",
                phase="FAILED_TERMINAL",
                effect_hash=None,
                at=at,
            )
            stored = self._insert_receipt_and_phase(
                t_hash=t_hash,
                receipt=receipt,
                target_phase="FAILED_TERMINAL",
                at=at,
            )
            return RecoveryResult("FAILED_TERMINAL", "FAILURE_RECEIPT_RECOVERED", stored)

        if phase == "RECEIPTED":
            return RecoveryResult(
                "RECEIPTED",
                "HOLD_RECEIPTED_STATE_WITHOUT_RECEIPT",
                None,
            )

        return RecoveryResult(phase, "HOLD_UNKNOWN_PHASE", None)

    def record_external_intent(
        self,
        *,
        t_hash: str,
        payload: Mapping[str, Any],
        at: str,
    ) -> str:
        key = external_idempotency_key(t_hash)
        payload_hash = _hash(EXTERNAL_PAYLOAD_DOMAIN, dict(payload))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO external_intents
                (t_hash, idempotency_key, payload_hash, state, remote_effect_id, updated_at)
                VALUES (?, ?, ?, 'INTENT_RECORDED', NULL, ?)
                """,
                (t_hash, key, payload_hash, at),
            )
        return key

    def update_external_state(
        self,
        *,
        t_hash: str,
        state: str,
        at: str,
        remote_effect_id: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE external_intents
                SET state = ?, remote_effect_id = ?, updated_at = ?
                WHERE t_hash = ?
                """,
                (state, remote_effect_id, at, t_hash),
            )

    def read_external_intent(self, t_hash: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT idempotency_key, payload_hash, state, remote_effect_id, updated_at
                FROM external_intents WHERE t_hash = ?
                """,
                (t_hash,),
            ).fetchone()
        if row is None:
            return None
        return {
            "idempotency_key": row[0],
            "payload_hash": row[1],
            "state": row[2],
            "remote_effect_id": row[3],
            "updated_at": row[4],
        }


class SimulatedExternalAdapter:
    """SQLite-backed remote simulator. It never performs a real external call."""

    def __init__(
        self,
        path: str | Path,
        *,
        queryable: bool,
        supports_idempotency: bool = True,
    ):
        self.path = str(path)
        self.queryable = queryable
        self.supports_idempotency = supports_idempotency
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS remote_effects (
                    idempotency_key TEXT PRIMARY KEY,
                    payload_hash TEXT NOT NULL,
                    remote_effect_id TEXT NOT NULL,
                    dispatch_count INTEGER NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def dispatch(
        self,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        lose_ack: bool = False,
    ) -> dict[str, Any]:
        payload_hash = _hash(EXTERNAL_PAYLOAD_DOMAIN, dict(payload))
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT payload_hash, remote_effect_id, dispatch_count
                FROM remote_effects WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            if row is None:
                remote_effect_id = "remote-" + idempotency_key[:20]
                conn.execute(
                    """
                    INSERT INTO remote_effects
                    (idempotency_key, payload_hash, remote_effect_id, dispatch_count)
                    VALUES (?, ?, ?, 1)
                    """,
                    (idempotency_key, payload_hash, remote_effect_id),
                )
                dispatch_count = 1
            else:
                if not self.supports_idempotency:
                    conn.execute("ROLLBACK")
                    return {"status": "HOLD_NO_IDEMPOTENCY_CONTRACT"}
                if row[0] != payload_hash:
                    conn.execute("ROLLBACK")
                    return {"status": "HOLD_IDEMPOTENCY_PAYLOAD_CONFLICT"}
                remote_effect_id = row[1]
                dispatch_count = int(row[2])
            conn.execute("COMMIT")
        finally:
            conn.close()

        if lose_ack:
            return {
                "status": "ACK_LOST",
                "remote_effect_id": None,
                "dispatch_count": dispatch_count,
            }
        return {
            "status": "ACK",
            "remote_effect_id": remote_effect_id,
            "dispatch_count": dispatch_count,
        }

    def lookup(self, idempotency_key: str) -> dict[str, Any] | None:
        if not self.queryable:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload_hash, remote_effect_id, dispatch_count
                FROM remote_effects WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
        if row is None:
            return None
        return {
            "payload_hash": row[0],
            "remote_effect_id": row[1],
            "dispatch_count": int(row[2]),
        }

    def effect_count(self, idempotency_key: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM remote_effects WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
        return int(row[0])


@dataclass(frozen=True)
class ExternalResult:
    status: str
    idempotency_key: str
    remote_effect_id: str | None


class ExternalCoordinator:
    def __init__(self, store: ExecutionStore):
        self.store = store

    def dispatch(
        self,
        *,
        t_hash: str,
        payload: Mapping[str, Any],
        adapter: SimulatedExternalAdapter,
        at: str,
        lose_ack: bool,
    ) -> ExternalResult:
        key = self.store.record_external_intent(
            t_hash=t_hash,
            payload=payload,
            at=at,
        )
        result = adapter.dispatch(
            idempotency_key=key,
            payload=payload,
            lose_ack=lose_ack,
        )
        if result["status"] == "ACK":
            self.store.update_external_state(
                t_hash=t_hash,
                state="REMOTE_ACKED",
                at=at,
                remote_effect_id=result["remote_effect_id"],
            )
            return ExternalResult("REMOTE_ACKED", key, result["remote_effect_id"])

        if result["status"] == "ACK_LOST":
            self.store.update_external_state(
                t_hash=t_hash,
                state="AMBIGUOUS_REMOTE",
                at=at,
            )
            return ExternalResult("AMBIGUOUS_REMOTE", key, None)

        self.store.update_external_state(
            t_hash=t_hash,
            state=result["status"],
            at=at,
        )
        return ExternalResult(result["status"], key, None)

    def reconcile(
        self,
        *,
        t_hash: str,
        adapter: SimulatedExternalAdapter,
        at: str,
    ) -> ExternalResult:
        intent = self.store.read_external_intent(t_hash)
        if intent is None:
            return ExternalResult("HOLD_NO_EXTERNAL_INTENT", "", None)

        key = intent["idempotency_key"]
        if intent["state"] == "REMOTE_ACKED":
            return ExternalResult("REMOTE_ACKED", key, intent["remote_effect_id"])

        if intent["state"] != "AMBIGUOUS_REMOTE":
            return ExternalResult(
                "HOLD_EXTERNAL_STATE_" + intent["state"],
                key,
                intent["remote_effect_id"],
            )

        remote = adapter.lookup(key)
        if remote is None:
            self.store.update_external_state(
                t_hash=t_hash,
                state="HOLD_AMBIGUOUS_REMOTE_NO_BLIND_RETRY",
                at=at,
            )
            return ExternalResult(
                "HOLD_AMBIGUOUS_REMOTE_NO_BLIND_RETRY",
                key,
                None,
            )

        self.store.update_external_state(
            t_hash=t_hash,
            state="REMOTE_ACK_RECOVERED",
            at=at,
            remote_effect_id=remote["remote_effect_id"],
        )
        return ExternalResult(
            "REMOTE_ACK_RECOVERED",
            key,
            remote["remote_effect_id"],
        )
