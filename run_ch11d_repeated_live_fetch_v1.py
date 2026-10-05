from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError

import fetch_ch11c_live_readonly_sources_v1 as fetcher
import run_ch11c_live_readonly_source_refresh_v1 as validator

GATE_ID = "CH11D__REPEATED_LIVE_REFRESH_TEMPORAL_DRIFT_FAILURE_RECOVERY_V1"
ROUND_ROOT = Path("ch11d_rounds")
ROUND_INDEX = Path("CH11D__ROUND_INDEX_V1.json")
ROUND_COUNT = 3
MIN_SEPARATION_SECONDS = 60
MAX_ATTEMPTS_PER_SOURCE = 3
RETRY_BACKOFF_SECONDS = (0, 15, 30)
TRANSIENT_HTTP_CODES = {429, 502, 503, 504}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_write(path: Path, payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return sha256_bytes(body.encode("utf-8"))


def utc_now_z() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def is_transient(exc: Exception) -> bool:
    if isinstance(exc, HTTPError):
        return exc.code in TRANSIENT_HTTP_CODES
    if isinstance(exc, URLError):
        return True
    return isinstance(exc, TimeoutError)


def validate_round(manifest_path: Path, receipt_path: Path) -> dict[str, Any]:
    validator.FETCH_MANIFEST = manifest_path
    validator.OUT_PATH = receipt_path
    manifest, rows = validator.fetch_rows()
    receipt = validator.pass_receipt(manifest, rows)
    canonical_write(receipt_path, receipt)
    if (
        receipt["verdict"]
        != "PASS_CH11C__LIVE_READ_ONLY_SOURCE_REFRESH_3_OF_3__ZERO_WRITE_ZERO_ACTUATION"
    ):
        raise AssertionError(f"round validator did not PASS: {receipt['verdict']}")
    return receipt


def fetch_source_with_retry(
    opener,
    *,
    source_id: str,
    url: str,
    sources_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    fetcher.OUT_DIR = sources_dir

    for attempt_no in range(1, MAX_ATTEMPTS_PER_SOURCE + 1):
        if attempt_no > 1:
            time.sleep(RETRY_BACKOFF_SECONDS[attempt_no - 1])

        attempt_at = utc_now_z()
        try:
            row = fetcher.fetch_one(
                opener,
                source_id,
                url,
                attempt_at,
            )
            attempts.append(
                {
                    "attempt": attempt_no,
                    "attempted_at": attempt_at,
                    "result": "SUCCESS",
                    "http_status": row["http_status"],
                }
            )
            row["attempt_count"] = attempt_no
            row["recovered_after_transient_failure"] = attempt_no > 1
            return row, attempts
        except Exception as exc:
            transient = is_transient(exc)
            status = exc.code if isinstance(exc, HTTPError) else None
            attempts.append(
                {
                    "attempt": attempt_no,
                    "attempted_at": attempt_at,
                    "result": "ERROR",
                    "error_type": type(exc).__name__,
                    "http_status": status,
                    "error": str(exc),
                    "transient": transient,
                }
            )
            if not transient or attempt_no >= MAX_ATTEMPTS_PER_SOURCE:
                spec = fetcher.ALLOWLIST[source_id]
                return (
                    {
                        "source_id": source_id,
                        "provider": spec["provider"],
                        "role": spec["role"],
                        "method": "GET",
                        "requested_url": url,
                        "fetched_at": attempt_at,
                        "ok": False,
                        "error": f"{type(exc).__name__}:{exc}",
                        "external_write": False,
                        "request_body_bytes": 0,
                        "attempt_count": attempt_no,
                        "recovered_after_transient_failure": False,
                    },
                    attempts,
                )

    raise AssertionError("unreachable retry path")


def fetch_round(round_no: int) -> dict[str, Any]:
    round_dir = ROUND_ROOT / f"round_{round_no}"
    sources_dir = round_dir / "sources"
    manifest_path = round_dir / "fetch_manifest.json"
    receipt_path = round_dir / "validation_receipt.json"

    round_started_at = utc_now_z()
    now = datetime.now(timezone.utc)
    urls = fetcher.source_urls(now)
    opener = fetcher.build_opener(fetcher.AllowlistRedirectHandler())

    rows: list[dict[str, Any]] = []
    attempt_history: dict[str, list[dict[str, Any]]] = {}

    for source_id in ("water", "electricity", "natural_gas"):
        row, attempts = fetch_source_with_retry(
            opener,
            source_id=source_id,
            url=urls[source_id],
            sources_dir=sources_dir,
        )
        rows.append(row)
        attempt_history[source_id] = attempts

    successful_fetch_count = sum(1 for row in rows if row.get("http_status") == 200)
    manifest = {
        "schema_version": "CH11C_LIVE_FETCH_MANIFEST_V1",
        "gate_id": fetcher.GATE_ID,
        "network_policy": {
            "read_only": True,
            "allowed_method": "GET",
            "request_body_bytes": 0,
            "credentials_used": False,
            "external_write": False,
            "external_actuation": False,
            "new_source_registration": False,
        },
        "allowlist": fetcher.ALLOWLIST,
        "fetch_count": len(rows),
        "successful_fetch_count": successful_fetch_count,
        "round_started_at": round_started_at,
        "round_completed_at": utc_now_z(),
        "bounded_retry_policy": {
            "max_attempts_per_source": MAX_ATTEMPTS_PER_SOURCE,
            "transient_http_codes": sorted(TRANSIENT_HTTP_CODES),
            "retry_backoff_seconds": list(RETRY_BACKOFF_SECONDS),
        },
        "attempt_history": attempt_history,
        "rows": rows,
    }
    canonical_write(manifest_path, manifest)

    if successful_fetch_count != 3:
        raise AssertionError(
            f"round {round_no} live fetch incomplete after bounded retry: "
            f"{successful_fetch_count}/3"
        )

    receipt = validate_round(manifest_path, receipt_path)

    return {
        "round": round_no,
        "round_started_at": round_started_at,
        "round_completed_at": manifest["round_completed_at"],
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "receipt_path": str(receipt_path),
        "receipt_sha256": sha256_file(receipt_path),
        "attempt_history": attempt_history,
        "source_files": {
            row["source_id"]: {
                "path": row["local_capture"],
                "sha256": row["sha256"],
                "byte_length": row["byte_length"],
                "attempt_count": row["attempt_count"],
                "recovered_after_transient_failure": row[
                    "recovered_after_transient_failure"
                ],
            }
            for row in rows
        },
        "validation_verdict": receipt["verdict"],
    }


def main() -> None:
    ROUND_ROOT.mkdir(parents=True, exist_ok=True)
    rounds: list[dict[str, Any]] = []

    for round_no in range(1, ROUND_COUNT + 1):
        if round_no > 1:
            time.sleep(MIN_SEPARATION_SECONDS)
        row = fetch_round(round_no)
        rounds.append(row)
        print(
            "CH11D_ROUND="
            + json.dumps(row, sort_keys=True, separators=(",", ":")),
            flush=True,
        )

    transient_failures = [
        {
            "round": round_row["round"],
            "source_id": source_id,
            "attempt": attempt,
        }
        for round_row in rounds
        for source_id, attempts in round_row["attempt_history"].items()
        for attempt in attempts
        if attempt["result"] == "ERROR" and attempt.get("transient") is True
    ]

    payload = {
        "schema_version": "CH11D_ROUND_INDEX_V2",
        "gate_id": GATE_ID,
        "round_count": ROUND_COUNT,
        "minimum_separation_seconds": MIN_SEPARATION_SECONDS,
        "rounds": rounds,
        "transport_recovery": {
            "transient_failure_count": len(transient_failures),
            "transient_failures": transient_failures,
            "all_rounds_completed": True,
        },
        "network_boundary": {
            "method": "GET",
            "request_body_bytes": 0,
            "credentials_used": False,
            "external_write": False,
            "external_actuation": False,
            "continuous_ingestion": False,
            "bounded_retry_only": True,
        },
    }
    sha = canonical_write(ROUND_INDEX, payload)
    print("CH11D_ROUND_INDEX_SHA256=" + sha, flush=True)


if __name__ == "__main__":
    main()
