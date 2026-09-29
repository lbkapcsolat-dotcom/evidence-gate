from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

SCHEMA_VERSION = "ESS_AUTHORIZATION_TRANSCRIPT_V1"
RECEIPT_SCHEMA_VERSION = "ESS_EXECUTION_RECEIPT_V1"

ACTION_DOMAIN = b"ESS.ACTION.COMMITMENT.V1\x00"
AUTHORITY_DOMAIN = b"ESS.AUTHORITY.COMMITMENT.V1\x00"
EVIDENCE_DOMAIN = b"ESS.EVIDENCE.COMMITMENT.V1\x00"
TRANSCRIPT_DOMAIN = b"ESS.AUTHORIZATION.TRANSCRIPT.V1\x00"
RESULT_DOMAIN = b"ESS.RESULT.COMMITMENT.V1\x00"
STATE_DOMAIN = b"ESS.STATE.COMMITMENT.V1\x00"
RECEIPT_DOMAIN = b"ESS.EXECUTION.RECEIPT.V1\x00"


def _validate_json(value: Any) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        raise ValueError("floats are not permitted in canonical ESS objects")
    if isinstance(value, list):
        for item in value:
            _validate_json(item)
        return
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise ValueError("canonical ESS object keys must be strings")
        for item in value.values():
            _validate_json(item)
        return
    raise ValueError(f"unsupported canonical ESS value type: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    _validate_json(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.sha256(domain + canonical_bytes(value)).hexdigest()


def action_commitment(action: Mapping[str, Any]) -> str:
    return _commit(ACTION_DOMAIN, dict(action))


def authority_commitment(authority: Mapping[str, Any]) -> str:
    return _commit(AUTHORITY_DOMAIN, dict(authority))


def evidence_commitment(evidence: Mapping[str, Any]) -> str:
    return _commit(EVIDENCE_DOMAIN, dict(evidence))


def _parse_utc(ts: str) -> datetime:
    if not isinstance(ts, str) or not ts.endswith("Z"):
        raise ValueError("timestamps must be RFC3339 UTC strings ending in Z")
    parsed = datetime.fromisoformat(ts[:-1] + "+00:00")
    if parsed.tzinfo != timezone.utc:
        parsed = parsed.astimezone(timezone.utc)
    return parsed


def make_transcript(
    *,
    action: Mapping[str, Any],
    authority: Mapping[str, Any],
    evidence: Mapping[str, Any],
    human_principal_id: str,
    signer_key_id: str,
    not_before: str,
    not_after: str,
    single_use_id: str,
    context_id: str,
) -> dict[str, Any]:
    nb = _parse_utc(not_before)
    na = _parse_utc(not_after)
    if na <= nb:
        raise ValueError("not_after must be later than not_before")
    if not single_use_id:
        raise ValueError("single_use_id is required")
    transcript = {
        "schema_version": SCHEMA_VERSION,
        "action_commitment": action_commitment(action),
        "authority_commitment": authority_commitment(authority),
        "evidence_commitment": evidence_commitment(evidence),
        "human_principal_id": human_principal_id,
        "signer_key_id": signer_key_id,
        "signature_scheme": "Ed25519",
        "not_before": not_before,
        "not_after": not_after,
        "single_use_id": single_use_id,
        "context_id": context_id,
    }
    canonical_bytes(transcript)
    return transcript


def transcript_hash(transcript: Mapping[str, Any]) -> str:
    if transcript.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported authorization transcript schema")
    return hashlib.sha256(
        TRANSCRIPT_DOMAIN + canonical_bytes(dict(transcript))
    ).hexdigest()


def sign_transcript(private_key: Ed25519PrivateKey, transcript: Mapping[str, Any]) -> str:
    digest = bytes.fromhex(transcript_hash(transcript))
    return base64.b64encode(private_key.sign(digest)).decode("ascii")


def verify_transcript_signature(
    public_key: Ed25519PublicKey,
    transcript: Mapping[str, Any],
    signature_b64: str,
) -> bool:
    try:
        signature = base64.b64decode(signature_b64, validate=True)
        public_key.verify(signature, bytes.fromhex(transcript_hash(transcript)))
        return True
    except (InvalidSignature, ValueError):
        return False


@dataclass(frozen=True)
class Decision:
    status: str
    transcript_hash: str
    single_use_id: str


class SQLiteSingleUseStore:
    """Durable reference store. No external actuation and no runtime admission."""

    _ALLOWED_TRANSITIONS = {
        "CONSUMED": {"EXECUTING", "FAILED_TERMINAL"},
        "EXECUTING": {"EFFECT_COMMITTED", "FAILED_TERMINAL"},
        "EFFECT_COMMITTED": {"RECEIPTED", "FAILED_TERMINAL"},
        "RECEIPTED": set(),
        "FAILED_TERMINAL": set(),
    }

    def __init__(self, path: str | Path):
        self.path = str(path)
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS consumed_authorizations (
                    single_use_id TEXT PRIMARY KEY,
                    transcript_hash TEXT NOT NULL,
                    consumed_at TEXT NOT NULL,
                    phase TEXT NOT NULL DEFAULT 'CONSUMED',
                    idempotency_key TEXT,
                    effect_result_json TEXT,
                    pre_state_json TEXT,
                    post_state_json TEXT,
                    receipt_json TEXT,
                    failure_reason TEXT
                )
                """
            )
            self._migrate_columns(conn)
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    @staticmethod
    def _migrate_columns(conn: sqlite3.Connection) -> None:
        existing = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(consumed_authorizations)").fetchall()
        }
        required = {
            "phase": "TEXT NOT NULL DEFAULT 'CONSUMED'",
            "idempotency_key": "TEXT",
            "effect_result_json": "TEXT",
            "pre_state_json": "TEXT",
            "post_state_json": "TEXT",
            "receipt_json": "TEXT",
            "failure_reason": "TEXT",
        }
        for name, declaration in required.items():
            if name not in existing:
                conn.execute(
                    f"ALTER TABLE consumed_authorizations ADD COLUMN {name} {declaration}"
                )

    def consume(self, single_use_id: str, t_hash: str, consumed_at: str) -> bool:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    """
                    INSERT INTO consumed_authorizations
                    (single_use_id, transcript_hash, consumed_at, phase, idempotency_key)
                    VALUES (?, ?, ?, 'CONSUMED', ?)
                    """,
                    (single_use_id, t_hash, consumed_at, t_hash),
                )
            except sqlite3.IntegrityError:
                conn.execute("ROLLBACK")
                return False
            conn.execute("COMMIT")
            return True
        finally:
            conn.close()

    def read(self, single_use_id: str) -> dict[str, str] | None:
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT single_use_id, transcript_hash, consumed_at
                FROM consumed_authorizations
                WHERE single_use_id = ?
                """,
                (single_use_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return {
            "single_use_id": row[0],
            "transcript_hash": row[1],
            "consumed_at": row[2],
        }

    def read_execution(self, single_use_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT single_use_id, transcript_hash, consumed_at, phase,
                       idempotency_key, effect_result_json, pre_state_json,
                       post_state_json, receipt_json, failure_reason
                FROM consumed_authorizations
                WHERE single_use_id = ?
                """,
                (single_use_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None

        def decoded(value: str | None) -> Any:
            return None if value is None else json.loads(value)

        return {
            "single_use_id": row[0],
            "transcript_hash": row[1],
            "consumed_at": row[2],
            "phase": row[3],
            "idempotency_key": row[4],
            "effect_result": decoded(row[5]),
            "pre_state": decoded(row[6]),
            "post_state": decoded(row[7]),
            "receipt": decoded(row[8]),
            "failure_reason": row[9],
        }

    def transition(self, single_use_id: str, expected_phase: str, new_phase: str) -> bool:
        if new_phase not in self._ALLOWED_TRANSITIONS.get(expected_phase, set()):
            return False
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                """
                UPDATE consumed_authorizations
                SET phase = ?
                WHERE single_use_id = ? AND phase = ?
                """,
                (new_phase, single_use_id, expected_phase),
            )
            if cursor.rowcount != 1:
                conn.execute("ROLLBACK")
                return False
            conn.execute("COMMIT")
            return True
        finally:
            conn.close()

    def record_effect_committed(
        self,
        *,
        single_use_id: str,
        effect_result: Mapping[str, Any],
        pre_state: Mapping[str, Any],
        post_state: Mapping[str, Any],
    ) -> bool:
        effect_json = canonical_bytes(dict(effect_result)).decode("utf-8")
        pre_json = canonical_bytes(dict(pre_state)).decode("utf-8")
        post_json = canonical_bytes(dict(post_state)).decode("utf-8")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                """
                UPDATE consumed_authorizations
                SET phase = 'EFFECT_COMMITTED',
                    effect_result_json = ?,
                    pre_state_json = ?,
                    post_state_json = ?
                WHERE single_use_id = ? AND phase = 'EXECUTING'
                """,
                (effect_json, pre_json, post_json, single_use_id),
            )
            if cursor.rowcount != 1:
                conn.execute("ROLLBACK")
                return False
            conn.execute("COMMIT")
            return True
        finally:
            conn.close()

    def record_receipt(self, *, single_use_id: str, receipt: Mapping[str, Any]) -> bool:
        receipt_json = canonical_bytes(dict(receipt)).decode("utf-8")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                """
                UPDATE consumed_authorizations
                SET phase = 'RECEIPTED', receipt_json = ?
                WHERE single_use_id = ? AND phase = 'EFFECT_COMMITTED'
                """,
                (receipt_json, single_use_id),
            )
            if cursor.rowcount != 1:
                conn.execute("ROLLBACK")
                return False
            conn.execute("COMMIT")
            return True
        finally:
            conn.close()

    def fail_terminal(self, *, single_use_id: str, reason: str) -> bool:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT phase FROM consumed_authorizations WHERE single_use_id = ?",
                (single_use_id,),
            ).fetchone()
            if row is None:
                conn.execute("ROLLBACK")
                return False
            phase = str(row[0])
            if "FAILED_TERMINAL" not in self._ALLOWED_TRANSITIONS.get(phase, set()):
                conn.execute("ROLLBACK")
                return False
            cursor = conn.execute(
                """
                UPDATE consumed_authorizations
                SET phase = 'FAILED_TERMINAL', failure_reason = ?
                WHERE single_use_id = ? AND phase = ?
                """,
                (reason, single_use_id, phase),
            )
            if cursor.rowcount != 1:
                conn.execute("ROLLBACK")
                return False
            conn.execute("COMMIT")
            return True
        finally:
            conn.close()


def validate_and_consume(
    *,
    transcript: Mapping[str, Any],
    signature_b64: str,
    public_key: Ed25519PublicKey,
    current_action: Mapping[str, Any],
    current_authority: Mapping[str, Any] | None,
    current_evidence: Mapping[str, Any],
    now: str,
    store: SQLiteSingleUseStore,
) -> Decision:
    t_hash = transcript_hash(transcript)
    single_use_id = str(transcript.get("single_use_id", ""))

    if current_authority is None:
        return Decision("HOLD_UNKNOWN_AUTHORITY", t_hash, single_use_id)

    if transcript.get("action_commitment") != action_commitment(current_action):
        return Decision("HOLD_ACTION_MISMATCH", t_hash, single_use_id)

    if transcript.get("authority_commitment") != authority_commitment(current_authority):
        return Decision("HOLD_AUTHORITY_MISMATCH", t_hash, single_use_id)

    if transcript.get("evidence_commitment") != evidence_commitment(current_evidence):
        return Decision("HOLD_EVIDENCE_MISMATCH", t_hash, single_use_id)

    now_dt = _parse_utc(now)
    if now_dt < _parse_utc(str(transcript["not_before"])):
        return Decision("HOLD_NOT_YET_VALID", t_hash, single_use_id)
    if now_dt > _parse_utc(str(transcript["not_after"])):
        return Decision("HOLD_EXPIRED", t_hash, single_use_id)

    if not verify_transcript_signature(public_key, transcript, signature_b64):
        return Decision("HOLD_INVALID_HUMAN_SIGNATURE", t_hash, single_use_id)

    if not store.consume(single_use_id, t_hash, now):
        return Decision("HOLD_REPLAY_CONSUMED", t_hash, single_use_id)

    return Decision("PASS_CONSUMED", t_hash, single_use_id)


def build_execution_receipt(
    *,
    transcript: Mapping[str, Any],
    execution_status: str,
    result: Mapping[str, Any],
    pre_state: Mapping[str, Any],
    post_state: Mapping[str, Any],
    executed_at: str,
) -> dict[str, Any]:
    _parse_utc(executed_at)
    receipt: dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "authorization_transcript_hash": transcript_hash(transcript),
        "single_use_id": transcript["single_use_id"],
        "action_commitment": transcript["action_commitment"],
        "authority_commitment": transcript["authority_commitment"],
        "evidence_commitment": transcript["evidence_commitment"],
        "execution_status": execution_status,
        "result_commitment": _commit(RESULT_DOMAIN, dict(result)),
        "pre_state_commitment": _commit(STATE_DOMAIN, dict(pre_state)),
        "post_state_commitment": _commit(STATE_DOMAIN, dict(post_state)),
        "executed_at": executed_at,
        "runtime_admission": False,
        "external_actuation": False,
        "zero_spend": True,
    }
    receipt["receipt_sha256"] = hashlib.sha256(
        RECEIPT_DOMAIN + canonical_bytes(receipt)
    ).hexdigest()
    return receipt


class InjectedCrash(RuntimeError):
    def __init__(self, phase: str):
        super().__init__(f"injected crash after {phase}")
        self.phase = phase


class AcknowledgementLost(RuntimeError):
    pass


class AmbiguousRemoteState(RuntimeError):
    pass


@dataclass(frozen=True)
class RemoteLookup:
    status: str
    result: dict[str, Any] | None


@dataclass(frozen=True)
class ExecutionOutcome:
    status: str
    phase: str | None
    receipt: dict[str, Any] | None = None


class SimulatedExternalAdapter:
    """SQLite-backed external-effect simulator. It never performs real external actuation."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS remote_effects (
                    idempotency_key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    committed_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idempotency_key TEXT NOT NULL,
                    behavior TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ambiguous_remote_state (
                    idempotency_key TEXT PRIMARY KEY
                )
                """
            )
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def apply_effect(
        self,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        committed_at: str,
        behavior: str = "normal",
    ) -> dict[str, Any]:
        if behavior not in {"normal", "ack_loss", "ambiguous"}:
            raise ValueError("unsupported simulated adapter behavior")

        payload_json = canonical_bytes(dict(payload)).decode("utf-8")
        result = {
            "ok": True,
            "idempotency_key": idempotency_key,
            "effect_commitment": _commit(b"ESS.SIMULATED.EFFECT.V1\\x00", dict(payload)),
        }
        result_json = canonical_bytes(result).decode("utf-8")

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO attempts (idempotency_key, behavior) VALUES (?, ?)",
                (idempotency_key, behavior),
            )
            if behavior == "ambiguous":
                conn.execute(
                    """
                    INSERT OR IGNORE INTO ambiguous_remote_state (idempotency_key)
                    VALUES (?)
                    """,
                    (idempotency_key,),
                )
                conn.execute("COMMIT")
                raise AmbiguousRemoteState("simulated remote state is ambiguous")

            conn.execute(
                """
                INSERT OR IGNORE INTO remote_effects
                (idempotency_key, payload_json, result_json, committed_at)
                VALUES (?, ?, ?, ?)
                """,
                (idempotency_key, payload_json, result_json, committed_at),
            )
            row = conn.execute(
                "SELECT result_json FROM remote_effects WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            conn.execute("COMMIT")
        finally:
            conn.close()

        committed_result = json.loads(str(row[0]))
        if behavior == "ack_loss":
            raise AcknowledgementLost("simulated acknowledgement loss after commit")
        return committed_result

    def lookup_effect(self, idempotency_key: str) -> RemoteLookup:
        conn = self._connect()
        try:
            ambiguous = conn.execute(
                """
                SELECT 1 FROM ambiguous_remote_state
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            if ambiguous is not None:
                return RemoteLookup("AMBIGUOUS", None)
            row = conn.execute(
                """
                SELECT result_json FROM remote_effects
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return RemoteLookup("ABSENT", None)
        return RemoteLookup("COMMITTED", json.loads(str(row[0])))

    def read_effect(self, idempotency_key: str) -> dict[str, Any] | None:
        lookup = self.lookup_effect(idempotency_key)
        if lookup.status != "COMMITTED":
            return None
        assert lookup.result is not None
        return {
            "idempotency_key": idempotency_key,
            "result": lookup.result,
        }

    def attempt_count(self, idempotency_key: str) -> int:
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM attempts
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
        finally:
            conn.close()
        return int(row[0])

    def effect_count(self, idempotency_key: str) -> int:
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM remote_effects
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
        finally:
            conn.close()
        return int(row[0])


def _maybe_crash(crash_at: str | None, phase: str) -> None:
    if crash_at == phase:
        raise InjectedCrash(phase)


def _persist_receipt_from_state(
    *,
    transcript: Mapping[str, Any],
    store: SQLiteSingleUseStore,
    state: Mapping[str, Any],
    executed_at: str,
) -> ExecutionOutcome:
    effect_result = state.get("effect_result")
    pre_state = state.get("pre_state")
    post_state = state.get("post_state")
    if not isinstance(effect_result, dict) or not isinstance(pre_state, dict) or not isinstance(post_state, dict):
        store.fail_terminal(
            single_use_id=str(state["single_use_id"]),
            reason="MISSING_EFFECT_STATE_FOR_RECEIPT",
        )
        return ExecutionOutcome("HOLD_FAILED_TERMINAL", "FAILED_TERMINAL")

    receipt = build_execution_receipt(
        transcript=transcript,
        execution_status="SIMULATED_EFFECT_COMMITTED",
        result=effect_result,
        pre_state=pre_state,
        post_state=post_state,
        executed_at=executed_at,
    )
    if not store.record_receipt(
        single_use_id=str(state["single_use_id"]),
        receipt=receipt,
    ):
        return ExecutionOutcome("HOLD_STATE_TRANSITION", state.get("phase"))
    return ExecutionOutcome("PASS_RECEIPTED", "RECEIPTED", receipt)


def execute_reference_effect(
    *,
    transcript: Mapping[str, Any],
    signature_b64: str,
    public_key: Ed25519PublicKey,
    current_action: Mapping[str, Any],
    current_authority: Mapping[str, Any] | None,
    current_evidence: Mapping[str, Any],
    now: str,
    store: SQLiteSingleUseStore,
    adapter: SimulatedExternalAdapter,
    effect_payload: Mapping[str, Any],
    pre_state: Mapping[str, Any],
    post_state: Mapping[str, Any],
    crash_at: str | None = None,
    adapter_behavior: str = "normal",
) -> ExecutionOutcome:
    decision = validate_and_consume(
        transcript=transcript,
        signature_b64=signature_b64,
        public_key=public_key,
        current_action=current_action,
        current_authority=current_authority,
        current_evidence=current_evidence,
        now=now,
        store=store,
    )
    if decision.status != "PASS_CONSUMED":
        state = store.read_execution(decision.single_use_id)
        return ExecutionOutcome(
            decision.status,
            None if state is None else str(state["phase"]),
        )

    single_use_id = decision.single_use_id
    t_hash = decision.transcript_hash
    _maybe_crash(crash_at, "CONSUMED")

    if not store.transition(single_use_id, "CONSUMED", "EXECUTING"):
        return ExecutionOutcome("HOLD_STATE_TRANSITION", "CONSUMED")
    _maybe_crash(crash_at, "EXECUTING")

    try:
        effect_result = adapter.apply_effect(
            idempotency_key=t_hash,
            payload=effect_payload,
            committed_at=now,
            behavior=adapter_behavior,
        )
    except AcknowledgementLost:
        return ExecutionOutcome("HOLD_ACK_LOST", "EXECUTING")
    except AmbiguousRemoteState:
        return ExecutionOutcome("HOLD_AMBIGUOUS_REMOTE_STATE", "EXECUTING")

    if not store.record_effect_committed(
        single_use_id=single_use_id,
        effect_result=effect_result,
        pre_state=pre_state,
        post_state=post_state,
    ):
        return ExecutionOutcome("HOLD_STATE_TRANSITION", "EXECUTING")
    _maybe_crash(crash_at, "EFFECT_COMMITTED")

    state = store.read_execution(single_use_id)
    assert state is not None
    outcome = _persist_receipt_from_state(
        transcript=transcript,
        store=store,
        state=state,
        executed_at=now,
    )
    if outcome.status == "PASS_RECEIPTED":
        _maybe_crash(crash_at, "RECEIPTED")
    return outcome


def recover_reference_execution(
    *,
    transcript: Mapping[str, Any],
    store: SQLiteSingleUseStore,
    adapter: SimulatedExternalAdapter,
    effect_payload: Mapping[str, Any],
    pre_state: Mapping[str, Any],
    post_state: Mapping[str, Any],
    executed_at: str,
) -> ExecutionOutcome:
    single_use_id = str(transcript.get("single_use_id", ""))
    t_hash = transcript_hash(transcript)
    state = store.read_execution(single_use_id)
    if state is None:
        return ExecutionOutcome("HOLD_NOT_CONSUMED", None)

    if state["transcript_hash"] != t_hash or state["idempotency_key"] != t_hash:
        store.fail_terminal(
            single_use_id=single_use_id,
            reason="TRANSCRIPT_OR_IDEMPOTENCY_BINDING_MISMATCH",
        )
        return ExecutionOutcome("HOLD_FAILED_TERMINAL", "FAILED_TERMINAL")

    phase = str(state["phase"])
    if phase == "RECEIPTED":
        receipt = state.get("receipt")
        return ExecutionOutcome(
            "PASS_RECEIPTED",
            "RECEIPTED",
            receipt if isinstance(receipt, dict) else None,
        )
    if phase == "FAILED_TERMINAL":
        return ExecutionOutcome("HOLD_FAILED_TERMINAL", "FAILED_TERMINAL")

    if phase == "CONSUMED":
        if not store.transition(single_use_id, "CONSUMED", "EXECUTING"):
            return ExecutionOutcome("HOLD_STATE_TRANSITION", "CONSUMED")
        effect_result = adapter.apply_effect(
            idempotency_key=t_hash,
            payload=effect_payload,
            committed_at=executed_at,
            behavior="normal",
        )
        if not store.record_effect_committed(
            single_use_id=single_use_id,
            effect_result=effect_result,
            pre_state=pre_state,
            post_state=post_state,
        ):
            return ExecutionOutcome("HOLD_STATE_TRANSITION", "EXECUTING")
        phase = "EFFECT_COMMITTED"

    elif phase == "EXECUTING":
        remote = adapter.lookup_effect(t_hash)
        if remote.status != "COMMITTED" or remote.result is None:
            reason = (
                "AMBIGUOUS_REMOTE_STATE"
                if remote.status == "AMBIGUOUS"
                else "REMOTE_STATE_ABSENT_AFTER_EXECUTING"
            )
            store.fail_terminal(single_use_id=single_use_id, reason=reason)
            return ExecutionOutcome("HOLD_FAILED_TERMINAL", "FAILED_TERMINAL")
        if not store.record_effect_committed(
            single_use_id=single_use_id,
            effect_result=remote.result,
            pre_state=pre_state,
            post_state=post_state,
        ):
            return ExecutionOutcome("HOLD_STATE_TRANSITION", "EXECUTING")
        phase = "EFFECT_COMMITTED"

    if phase == "EFFECT_COMMITTED":
        state = store.read_execution(single_use_id)
        assert state is not None
        return _persist_receipt_from_state(
            transcript=transcript,
            store=store,
            state=state,
            executed_at=executed_at,
        )

    return ExecutionOutcome("HOLD_UNKNOWN_EXECUTION_PHASE", phase)
