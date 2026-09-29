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

    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS consumed_authorizations (
                    single_use_id TEXT PRIMARY KEY,
                    transcript_hash TEXT NOT NULL,
                    consumed_at TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def consume(self, single_use_id: str, t_hash: str, consumed_at: str) -> bool:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    """
                    INSERT INTO consumed_authorizations
                    (single_use_id, transcript_hash, consumed_at)
                    VALUES (?, ?, ?)
                    """,
                    (single_use_id, t_hash, consumed_at),
                )
            except sqlite3.IntegrityError:
                conn.execute("ROLLBACK")
                return False
            conn.execute("COMMIT")
            return True
        finally:
            conn.close()

    def read(self, single_use_id: str) -> dict[str, str] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT single_use_id, transcript_hash, consumed_at
                FROM consumed_authorizations
                WHERE single_use_id = ?
                """,
                (single_use_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "single_use_id": row[0],
            "transcript_hash": row[1],
            "consumed_at": row[2],
        }


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
