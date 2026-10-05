from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

GATE_ID = "CH11E__LONG_HORIZON_LIVE_READ_ONLY_SOAK_AND_TEMPORAL_RESILIENCE_V1"
REQUIRED_ROUNDS = 5
MIN_HORIZON_SECONDS = 4 * 3600
SOURCE_IDS = ("water", "electricity", "natural_gas")


def parse_utc(value: str) -> datetime:
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    return datetime.fromisoformat(v).astimezone(timezone.utc)


def canonical_sha256(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def classify_temporal_transition(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    if current.get("provider_identity") is not True:
        return {"pass": False, "classification": "HOLD_PROVIDER_DRIFT"}
    if current.get("schema_identity") is not True:
        return {"pass": False, "classification": "HOLD_SCHEMA_DRIFT"}
    if current.get("semantic_identity") is not True:
        return {"pass": False, "classification": "HOLD_SEMANTIC_DRIFT"}

    age = int(current.get("freshness_age_seconds", 10**18))
    max_age = int(current.get("max_age_seconds", -1))
    if max_age < 0 or age > max_age:
        return {"pass": False, "classification": "HOLD_STALE_DATA", "age": age, "max_age": max_age}

    prev_ts = parse_utc(str(previous["selected_timestamp"]))
    cur_ts = parse_utc(str(current["selected_timestamp"]))
    if cur_ts < prev_ts:
        return {"pass": False, "classification": "HOLD_TIMESTAMP_REGRESSION"}

    sha_changed = current.get("live_raw_sha256") != previous.get("live_raw_sha256")
    value_changed = current.get("value_fingerprint") != previous.get("value_fingerprint")

    if cur_ts > prev_ts and (sha_changed or value_changed):
        cls = "EXPECTED_VALUE_DRIFT"
    elif cur_ts > prev_ts:
        cls = "EXPECTED_TIMESTAMP_ADVANCE"
    elif sha_changed or value_changed:
        cls = "EXPECTED_REVISION_OR_BYTE_DRIFT"
    else:
        cls = "NO_CHANGE"
    return {"pass": True, "classification": cls}


def summarize_recovery(rounds: list[dict[str, Any]]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    recoveries: list[dict[str, Any]] = []
    for round_row in rounds:
        for source_id, attempts in round_row.get("attempt_history", {}).items():
            saw_transient = False
            for attempt in attempts:
                if attempt.get("result") == "ERROR" and attempt.get("transient") is True:
                    saw_transient = True
                    failures.append({"round": round_row.get("round"), "source_id": source_id, **attempt})
                elif attempt.get("result") == "SUCCESS" and saw_transient:
                    recoveries.append({"round": round_row.get("round"), "source_id": source_id, **attempt})
                    saw_transient = False
    if recoveries:
        status = "OBSERVED_REAL_TRANSIENT_FAILURE_WITH_IN_RUN_RECOVERY"
    elif failures:
        status = "TRANSIENT_FAILURE_OBSERVED_WITHOUT_IN_RUN_RECOVERY"
    else:
        status = "IN_RUN_RECOVERY_NOT_EMPIRICALLY_OBSERVED"
    return {"status": status, "transient_failures": failures, "recoveries": recoveries}


def build_source_observations(receipt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = receipt.get("live_source_refresh", {}).get("rows", [])
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        source_id = str(row.get("source_id", ""))
        record = row.get("selected_record", {})
        if source_id == "water":
            ts = record.get("observed_at")
        elif source_id == "electricity":
            ts = record.get("start_time")
        elif source_id == "natural_gas":
            ts = record.get("period_to_utc")
        else:
            continue
        if not ts:
            raise ValueError(f"selected timestamp missing for {source_id}")
        out[source_id] = {
            "selected_timestamp": str(ts),
            "live_raw_sha256": str(row.get("live_raw_sha256", "")),
            "value_fingerprint": canonical_sha256(record),
            "provider_identity": row.get("provider_identity") is True,
            "schema_identity": row.get("schema_identity") is True,
            "semantic_identity": row.get("semantic_identity") is True,
            "freshness_age_seconds": int(row.get("freshness_age_seconds", 10**18)),
            "max_age_seconds": int(row.get("max_age_seconds", -1)),
        }
    return out


def execute_soak(*, fetch_round_fn, receipt_loader, replay_fn, sleeper, separation_seconds: int = 3600) -> list[dict[str, Any]]:
    rounds: list[dict[str, Any]] = []
    for round_no in range(1, REQUIRED_ROUNDS + 1):
        if round_no > 1:
            sleeper(separation_seconds)
        row = dict(fetch_round_fn(round_no))
        receipt = receipt_loader(row["receipt_path"])
        row["source_observations"] = build_source_observations(receipt)
        row["replay_validation_equal"] = bool(replay_fn(row))
        rounds.append(row)
    return rounds


def _hold(verdict: str, *, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "CH11E_LONG_HORIZON_SOAK_RECEIPT_V1",
        "gate_id": GATE_ID,
        "verdict": verdict,
        "detail": detail or {},
        "external_state_written": False,
        "external_actuation": False,
        "claim_ceiling": {
            "bounded_long_horizon_live_read_only_soak": False,
            "continuous_ingestion": False,
            "runtime_admission": False,
            "production_readiness": False,
            "production_admission": False,
            "network_write": False,
            "external_actuation": False,
            "pointer_promotion": False,
            "global_bind": False,
            "certification": False,
            "merge_authorization": False,
        },
    }


def adjudicate_soak(rounds: list[dict[str, Any]]) -> dict[str, Any]:
    if len(rounds) != REQUIRED_ROUNDS:
        return _hold("HOLD_CH11E__LONG_HORIZON_NOT_YET_OBSERVED", detail={"round_count": len(rounds)})

    start = parse_utc(str(rounds[0]["round_started_at"]))
    end = parse_utc(str(rounds[-1]["round_started_at"]))
    span_seconds = int((end - start).total_seconds())
    if span_seconds < MIN_HORIZON_SECONDS:
        return _hold("HOLD_CH11E__LONG_HORIZON_NOT_YET_OBSERVED", detail={"span_seconds": span_seconds})

    if any(row.get("replay_validation_equal") is False for row in rounds):
        return _hold("HOLD_CH11E__DETERMINISTIC_REPLAY_MISMATCH")

    drift_ledger: list[dict[str, Any]] = []
    for source_id in SOURCE_IDS:
        observations = [row.get("source_observations", {}).get(source_id) for row in rounds]
        if any(obs is None for obs in observations):
            return _hold("HOLD_CH11E__SOURCE_SLOT_MISSING", detail={"source_id": source_id})
        for idx in range(1, len(observations)):
            outcome = classify_temporal_transition(observations[idx - 1], observations[idx])
            drift_ledger.append({"source_id": source_id, "from_round": idx, "to_round": idx + 1, **outcome})
            if not outcome["pass"]:
                return _hold(f"HOLD_CH11E__{outcome['classification'].removeprefix('HOLD_')}", detail=drift_ledger[-1])

    recovery = summarize_recovery(rounds)
    if recovery["status"] == "TRANSIENT_FAILURE_OBSERVED_WITHOUT_IN_RUN_RECOVERY":
        return _hold("HOLD_CH11E__TRANSIENT_FAILURE_NOT_RECOVERED", detail=recovery)

    if recovery["status"] == "OBSERVED_REAL_TRANSIENT_FAILURE_WITH_IN_RUN_RECOVERY":
        verdict = "PASS_CH11E__LONG_HORIZON_LIVE_READ_ONLY_SOAK__IN_RUN_RECOVERY_OBSERVED__ZERO_WRITE_ZERO_ACTUATION"
    else:
        verdict = "PASS_CH11E__LONG_HORIZON_LIVE_READ_ONLY_SOAK__RECOVERY_PATH_NOT_OBSERVED__ZERO_WRITE_ZERO_ACTUATION"

    return {
        "schema_version": "CH11E_LONG_HORIZON_SOAK_RECEIPT_V1",
        "gate_id": GATE_ID,
        "verdict": verdict,
        "round_count": len(rounds),
        "horizon_seconds": span_seconds,
        "source_slot_count": len(rounds) * len(SOURCE_IDS),
        "drift_ledger": drift_ledger,
        "recovery_ledger": recovery,
        "external_state_written": False,
        "external_actuation": False,
        "claim_ceiling": {
            "bounded_long_horizon_live_read_only_soak": True,
            "continuous_ingestion": False,
            "runtime_admission": False,
            "production_readiness": False,
            "production_admission": False,
            "network_write": False,
            "external_actuation": False,
            "pointer_promotion": False,
            "global_bind": False,
            "certification": False,
            "merge_authorization": False,
        },
    }


def canonical_write(path, payload: dict[str, Any]) -> str:
    from pathlib import Path
    p = Path(path)
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load_json_path(path) -> dict[str, Any]:
    from pathlib import Path
    return json.loads(Path(path).read_text(encoding="utf-8"))


def real_replay_validation(round_row: dict[str, Any]) -> bool:
    from pathlib import Path
    import run_ch11d_repeated_live_fetch_v1 as ch11d

    manifest_path = Path(round_row["manifest_path"])
    original_path = Path(round_row["receipt_path"])
    replay_path = original_path.with_name("validation_receipt_replay.json")
    ch11d.validate_round(manifest_path, replay_path)
    return original_path.read_bytes() == replay_path.read_bytes()


def run_live_soak() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from pathlib import Path
    import time
    import run_ch11d_repeated_live_fetch_v1 as ch11d

    ch11d.ROUND_ROOT = Path("ch11e_rounds")
    rounds = execute_soak(
        fetch_round_fn=ch11d.fetch_round,
        receipt_loader=load_json_path,
        replay_fn=real_replay_validation,
        sleeper=time.sleep,
        separation_seconds=3600,
    )
    receipt = adjudicate_soak(rounds)
    return rounds, receipt


def main() -> None:
    from pathlib import Path
    import sys

    out_path = Path("CH11E__LONG_HORIZON_SOAK_RECEIPT_V1.json")
    index_path = Path("CH11E__SOAK_INDEX_V1.json")
    try:
        rounds, receipt = run_live_soak()
        index = {
            "schema_version": "CH11E_SOAK_INDEX_V1",
            "gate_id": GATE_ID,
            "required_rounds": REQUIRED_ROUNDS,
            "minimum_horizon_seconds": MIN_HORIZON_SECONDS,
            "rounds": rounds,
            "network_boundary": {
                "method": "GET",
                "request_body_bytes": 0,
                "credentials_used": False,
                "external_write": False,
                "external_actuation": False,
                "continuous_ingestion": False,
                "bounded_retry_only": True,
                "max_attempts_per_source": 3,
                "transient_http_codes": [429, 502, 503, 504],
            },
        }
        canonical_write(index_path, index)
    except Exception as exc:
        receipt = _hold(
            "HOLD_CH11E__LIVE_FETCH_OR_VALIDATION_FAILURE",
            detail={"error_type": type(exc).__name__, "error": str(exc)},
        )

    sha = canonical_write(out_path, receipt)
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    print("CH11E_RECEIPT_SHA256=" + sha)
    sys.exit(0 if str(receipt.get("verdict", "")).startswith("PASS_CH11E__") else 2)


if __name__ == "__main__":
    main()
