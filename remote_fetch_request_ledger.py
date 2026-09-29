from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Callable, Union


class RemoteFetchError(Exception): pass
class ReceiptValidationError(RemoteFetchError): pass
class ReceiptReplayError(ReceiptValidationError): pass
class ReceiptStaleError(ReceiptValidationError): pass
class ReceiptFutureDatedError(ReceiptValidationError): pass
class ReceiptRouteMismatchError(ReceiptValidationError): pass
class ReceiptObjectMismatchError(ReceiptValidationError): pass
class IntegrityMismatchError(ReceiptValidationError): pass
class LedgerCorruptError(RemoteFetchError): pass
class FailClosedNoPayloadError(RemoteFetchError): pass


class ConnectorFailureKind(str, Enum):
    TIMEOUT = "TIMEOUT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    PARTIAL_DOWNLOAD = "PARTIAL_DOWNLOAD"
    MISSING_OBJECT = "MISSING_OBJECT"
    STALE_CACHE = "STALE_CACHE"
    RECEIPT_MISSING = "RECEIPT_MISSING"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ExpectedObject:
    route_key: str
    drive_id: str
    object_name: str
    file_size_bytes: int
    raw_sha256: str


@dataclass(frozen=True)
class FetchReceipt:
    request_id: str
    route_key: str
    drive_id: str
    object_name: str
    file_size_bytes: int
    raw_sha256: str
    fetched_at: str
    success: bool


@dataclass(frozen=True)
class ConnectorSuccess:
    receipt: FetchReceipt
    payload: bytes


@dataclass(frozen=True)
class ConnectorFailure:
    kind: ConnectorFailureKind
    message: str = ""


ConnectorResult = Union[ConnectorSuccess, ConnectorFailure]


@dataclass(frozen=True)
class Resolution:
    route_key: str
    request_id: str
    payload: bytes
    ledger_digest: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_ts(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReceiptValidationError("invalid fetched_at") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ReceiptValidationError("fetched_at must be timezone-aware")
    return dt.astimezone(timezone.utc)


class AppendOnlyRequestLedger:
    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.rows: list[dict] = []
        self.by_request: dict[str, dict] = {}
        self._load()

    @staticmethod
    def digest(core: dict) -> str:
        raw = json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def _load(self) -> None:
        if not self.path.exists():
            return
        prev = "0" * 64
        seq = 1
        with self.path.open("r", encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                if not line.endswith("\n"):
                    raise LedgerCorruptError(f"line {n}: missing newline")
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise LedgerCorruptError(f"line {n}: invalid json") from exc
                required = {"seq","request_id","route_key","drive_id","object_name",
                            "file_size_bytes","raw_sha256","receipt_timestamp",
                            "first_seen_at","previous_digest","entry_digest"}
                if required - set(row):
                    raise LedgerCorruptError(f"line {n}: missing fields")
                if row["seq"] != seq or row["previous_digest"] != prev:
                    raise LedgerCorruptError(f"line {n}: chain mismatch")
                core = {k: row[k] for k in row if k != "entry_digest"}
                if self.digest(core) != row["entry_digest"]:
                    raise LedgerCorruptError(f"line {n}: digest mismatch")
                if row["request_id"] in self.by_request:
                    raise LedgerCorruptError(f"line {n}: duplicate request_id")
                self.rows.append(row)
                self.by_request[row["request_id"]] = row
                prev = row["entry_digest"]
                seq += 1

    def append(self, receipt: FetchReceipt, now: datetime) -> str:
        if receipt.request_id in self.by_request:
            raise ReceiptReplayError("request_id replay rejected")
        prev = self.rows[-1]["entry_digest"] if self.rows else "0" * 64
        core = {
            "seq": len(self.rows) + 1,
            "request_id": receipt.request_id,
            "route_key": receipt.route_key,
            "drive_id": receipt.drive_id,
            "object_name": receipt.object_name,
            "file_size_bytes": receipt.file_size_bytes,
            "raw_sha256": receipt.raw_sha256,
            "receipt_timestamp": receipt.fetched_at,
            "first_seen_at": now.astimezone(timezone.utc).isoformat(),
            "previous_digest": prev,
        }
        row = dict(core)
        row["entry_digest"] = self.digest(core)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self.rows.append(row)
        self.by_request[receipt.request_id] = row
        return row["entry_digest"]


def validate_success(
    result: ConnectorSuccess,
    expected: ExpectedObject,
    ledger: AppendOnlyRequestLedger,
    now: datetime,
    max_age: timedelta = timedelta(minutes=10),
    future_skew: timedelta = timedelta(seconds=30),
) -> str:
    r = result.receipt
    if not r.success:
        raise ReceiptValidationError("success=false")
    if r.route_key != expected.route_key:
        raise ReceiptRouteMismatchError("route mismatch")
    if r.drive_id != expected.drive_id or r.object_name != expected.object_name:
        raise ReceiptObjectMismatchError("object mismatch")
    if r.file_size_bytes != expected.file_size_bytes or r.raw_sha256 != expected.raw_sha256:
        raise IntegrityMismatchError("receipt size/sha mismatch")

    fetched = parse_ts(r.fetched_at)
    now = now.astimezone(timezone.utc)
    if fetched > now + future_skew:
        raise ReceiptFutureDatedError("future receipt")
    if now - fetched > max_age:
        raise ReceiptStaleError("stale receipt")
    if r.request_id in ledger.by_request:
        raise ReceiptReplayError("request_id replay rejected")
    if len(result.payload) != expected.file_size_bytes:
        raise IntegrityMismatchError("payload size mismatch")
    if sha256_bytes(result.payload) != expected.raw_sha256:
        raise IntegrityMismatchError("payload sha mismatch")
    return ledger.append(r, now)


def typed(value: object) -> ConnectorResult:
    if isinstance(value, (ConnectorSuccess, ConnectorFailure)):
        return value
    raise FailClosedNoPayloadError("untyped connector result")


def resolve_fail_closed(
    direct_fetch: Callable[[], ConnectorResult],
    fallback_fetch: Callable[[], ConnectorResult],
    direct_expected: ExpectedObject,
    fallback_expected: ExpectedObject,
    ledger: AppendOnlyRequestLedger,
    now: datetime,
) -> Resolution:
    direct_error: Exception | None = None
    try:
        d = typed(direct_fetch())
        if isinstance(d, ConnectorFailure):
            raise RemoteFetchError(d.kind.value)
        digest = validate_success(d, direct_expected, ledger, now)
        return Resolution(direct_expected.route_key, d.receipt.request_id, d.payload, digest)
    except RemoteFetchError as exc:
        direct_error = exc

    try:
        f = typed(fallback_fetch())
        if isinstance(f, ConnectorFailure):
            raise RemoteFetchError(f.kind.value)
        digest = validate_success(f, fallback_expected, ledger, now)
        return Resolution(fallback_expected.route_key, f.receipt.request_id, f.payload, digest)
    except RemoteFetchError as exc:
        raise FailClosedNoPayloadError(
            f"no payload; direct={type(direct_error).__name__}; fallback={type(exc).__name__}"
        ) from exc
