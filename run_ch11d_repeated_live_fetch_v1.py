from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any

import fetch_ch11c_live_readonly_sources_v1 as fetcher
import run_ch11c_live_readonly_source_refresh_v1 as validator

GATE_ID = "CH11D__REPEATED_LIVE_REFRESH_TEMPORAL_DRIFT_FAILURE_RECOVERY_V1"
ROUND_ROOT = Path("ch11d_rounds")
ROUND_INDEX = Path("CH11D__ROUND_INDEX_V1.json")
ROUND_COUNT = 3
MIN_SEPARATION_SECONDS = 60


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_write(path: Path, payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    path.write_text(body, encoding="utf-8")
    return sha256_bytes(body.encode("utf-8"))


def validate_round(manifest_path: Path, receipt_path: Path) -> dict[str, Any]:
    validator.FETCH_MANIFEST = manifest_path
    validator.OUT_PATH = receipt_path
    manifest, rows = validator.fetch_rows()
    receipt = validator.pass_receipt(manifest, rows)
    canonical_write(receipt_path, receipt)
    if receipt["verdict"] != "PASS_CH11C__LIVE_READ_ONLY_SOURCE_REFRESH_3_OF_3__ZERO_WRITE_ZERO_ACTUATION":
        raise AssertionError(f"round validator did not PASS: {receipt['verdict']}")
    return receipt


def fetch_round(round_no: int) -> dict[str, Any]:
    round_dir = ROUND_ROOT / f"round_{round_no}"
    sources_dir = round_dir / "sources"
    manifest_path = round_dir / "fetch_manifest.json"
    receipt_path = round_dir / "validation_receipt.json"

    fetcher.OUT_DIR = sources_dir
    fetcher.MANIFEST_PATH = manifest_path
    fetcher.main()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("successful_fetch_count") != 3:
        raise AssertionError(
            f"round {round_no} live fetch incomplete: "
            f"{manifest.get('successful_fetch_count')}/3"
        )
    receipt = validate_round(manifest_path, receipt_path)

    fetched_at_values = sorted({row["fetched_at"] for row in manifest["rows"]})
    if len(fetched_at_values) != 1:
        raise AssertionError(f"round {round_no} has inconsistent fetched_at values")

    return {
        "round": round_no,
        "fetched_at": fetched_at_values[0],
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "receipt_path": str(receipt_path),
        "receipt_sha256": sha256_file(receipt_path),
        "source_files": {
            row["source_id"]: {
                "path": row["local_capture"],
                "sha256": row["sha256"],
                "byte_length": row["byte_length"],
            }
            for row in manifest["rows"]
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
            + json.dumps(row, sort_keys=True, separators=(",", ":"))
        )

    payload = {
        "schema_version": "CH11D_ROUND_INDEX_V1",
        "gate_id": GATE_ID,
        "round_count": ROUND_COUNT,
        "minimum_separation_seconds": MIN_SEPARATION_SECONDS,
        "rounds": rounds,
        "network_boundary": {
            "method": "GET",
            "request_body_bytes": 0,
            "credentials_used": False,
            "external_write": False,
            "external_actuation": False,
            "continuous_ingestion": False,
        },
    }
    sha = canonical_write(ROUND_INDEX, payload)
    print("CH11D_ROUND_INDEX_SHA256=" + sha)


if __name__ == "__main__":
    main()
