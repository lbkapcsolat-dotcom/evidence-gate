from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

from evidence_bound_authority import SQLiteSingleUseStore
from evidence_bound_hardening import ExecutionStore

NOW = "2026-09-29T16:00:00Z"
RECEIPT_AT = "2026-09-29T16:00:01Z"
EFFECT = {"fixture": "local-effect", "value": 1}


def wait_for_start(path: str) -> None:
    marker = Path(path)
    deadline = time.time() + 10.0
    while not marker.exists():
        if time.time() > deadline:
            raise TimeoutError("start marker not observed")
        time.sleep(0.01)


def consume_worker(argv: list[str]) -> int:
    _, auth_db, single_use_id, t_hash, start_marker = argv
    wait_for_start(start_marker)
    store = SQLiteSingleUseStore(auth_db)
    ok = store.consume(single_use_id, t_hash, NOW)
    print("CONSUMED" if ok else "REPLAY_REJECTED", flush=True)
    return 0


def crash_worker(argv: list[str]) -> int:
    _, auth_db, execution_db, single_use_id, t_hash, crash_point = argv
    auth_store = SQLiteSingleUseStore(auth_db)
    if not auth_store.consume(single_use_id, t_hash, NOW):
        print("AUTHORIZATION_REUSE_REJECTED", flush=True)
        return 3

    store = ExecutionStore(execution_db)
    store.create_consumed(t_hash, single_use_id, NOW)

    if crash_point == "after_consume":
        os._exit(70)

    if not store.begin_execution(t_hash, NOW):
        return 4

    if crash_point == "during_execution":
        conn = sqlite3.connect(execution_db, timeout=10.0, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("BEGIN IMMEDIATE")
        effect_json = json.dumps(EFFECT, sort_keys=True, separators=(",", ":"))
        conn.execute(
            """
            INSERT INTO local_effects
            (t_hash, effect_json, effect_hash, committed_at)
            VALUES (?, ?, ?, ?)
            """,
            (t_hash, effect_json, "UNCOMMITTED_FIXTURE", NOW),
        )
        os._exit(71)

    store.commit_local_effect(t_hash, EFFECT, NOW)

    if crash_point == "after_effect_before_receipt":
        os._exit(72)

    store.commit_success_receipt(t_hash, RECEIPT_AT)

    if crash_point == "after_receipt_commit":
        os._exit(73)

    return 0


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: worker.py <consume|crash> ...")
    command = sys.argv[1]
    if command == "consume":
        return consume_worker(sys.argv[1:])
    if command == "crash":
        return crash_worker(sys.argv[1:])
    raise SystemExit("unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
