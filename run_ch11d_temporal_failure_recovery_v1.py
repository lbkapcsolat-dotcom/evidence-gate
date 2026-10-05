from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import run_ch11c_live_readonly_source_refresh_v1 as ch11c

GATE_ID = "CH11D__REPEATED_LIVE_REFRESH_TEMPORAL_DRIFT_FAILURE_RECOVERY_V1"
ROUND_INDEX = Path("CH11D__ROUND_INDEX_V1.json")
OUT_PATH = Path("CH11D__REPEATED_LIVE_TEMPORAL_RECOVERY_RECEIPT_V1.json")
FAILURE_DIR = Path("ch11d_failure_recovery")
PRIOR_TRANSPORT_FAILURE = Path("CH11D__PRIOR_TRANSPORT_FAILURE_EVIDENCE_V1.json")

CH11C_RECEIPT_SHA256 = "dc5947907efd9d38ae5ae495c612b698dd285fe95380e4b25547cb04a6dd9cd2"
EXPECTED_CH11C_FETCHER_SHA256 = "48de908711683ed449f2812542fac11e990d64f93043a6151abd56427c791863"
EXPECTED_CH11C_VALIDATOR_SHA256 = "fe4e766461b248dd29d221348cf116c02c11f6e8ceecdbf1c0515dc5ea52ea3b"
PRIOR_HOLD_ARTIFACT_DIGEST = "sha256:a097133f153013550c6448073640d9214c245a5ebab99cc3fc52344afbff87bb"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_utc(value: str) -> datetime:
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    return datetime.fromisoformat(v).astimezone(timezone.utc)


def canonical_write(path: Path, payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return sha256_bytes(body.encode("utf-8"))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def selected_time(source_id: str, row: dict[str, Any]) -> datetime:
    record = row["selected_record"]
    if source_id == "water":
        return parse_utc(record["observed_at"])
    if source_id == "electricity":
        return parse_utc(record["start_time"])
    if source_id == "natural_gas":
        return parse_utc(record["period_to_utc"])
    raise AssertionError(source_id)


def verify_prior_transport_failure() -> dict[str, Any]:
    prior = load_json(PRIOR_TRANSPORT_FAILURE)
    if prior.get("schema_version") != "CH11D_PRIOR_TRANSPORT_FAILURE_EVIDENCE_V1":
        raise AssertionError("prior transport failure evidence schema mismatch")
    failure = prior.get("observed_failure", {})
    if failure.get("round") != 2:
        raise AssertionError("prior failure round changed")
    if failure.get("source_id") != "natural_gas":
        raise AssertionError("prior failure source changed")
    if failure.get("error") != "HTTP 502 Bad Gateway":
        raise AssertionError("prior failure code changed")
    if prior["github"]["artifact_digest"] != PRIOR_HOLD_ARTIFACT_DIGEST:
        raise AssertionError("prior HOLD artifact digest changed")
    if prior.get("external_write") is not False or prior.get("external_actuation") is not False:
        raise AssertionError("prior failure evidence violates no-write boundary")
    return prior


def validate_round_index(index: dict[str, Any]) -> list[dict[str, Any]]:
    if index.get("schema_version") != "CH11D_ROUND_INDEX_V2":
        raise AssertionError("round index schema mismatch")
    if index.get("round_count") != 3 or len(index.get("rounds", [])) != 3:
        raise AssertionError("exactly three rounds are required")
    if index.get("minimum_separation_seconds") != 60:
        raise AssertionError("minimum separation must remain 60 seconds")

    boundary = index.get("network_boundary", {})
    expected_boundary = {
        "method": "GET",
        "request_body_bytes": 0,
        "credentials_used": False,
        "external_write": False,
        "external_actuation": False,
        "continuous_ingestion": False,
        "bounded_retry_only": True,
    }
    if boundary != expected_boundary:
        raise AssertionError(f"network boundary changed: {boundary!r}")

    rounds = index["rounds"]
    round_starts = [parse_utc(r["round_started_at"]) for r in rounds]
    for i in range(1, len(round_starts)):
        delta = int((round_starts[i] - round_starts[i - 1]).total_seconds())
        if delta < 60:
            raise AssertionError(f"round separation too small: {delta}s")

    for r in rounds:
        manifest_path = Path(r["manifest_path"])
        receipt_path = Path(r["receipt_path"])
        if sha256_file(manifest_path) != r["manifest_sha256"]:
            raise AssertionError(f"round {r['round']} manifest hash mismatch")
        if sha256_file(receipt_path) != r["receipt_sha256"]:
            raise AssertionError(f"round {r['round']} receipt hash mismatch")
        receipt = load_json(receipt_path)
        if receipt["verdict"] != "PASS_CH11C__LIVE_READ_ONLY_SOURCE_REFRESH_3_OF_3__ZERO_WRITE_ZERO_ACTUATION":
            raise AssertionError(f"round {r['round']} was not CH11C PASS")

        manifest = load_json(manifest_path)
        if manifest.get("successful_fetch_count") != 3:
            raise AssertionError(f"round {r['round']} not 3/3 after retry")
        retry_policy = manifest.get("bounded_retry_policy", {})
        if retry_policy.get("max_attempts_per_source") != 3:
            raise AssertionError("retry bound changed")
        if retry_policy.get("transient_http_codes") != [429, 502, 503, 504]:
            raise AssertionError("transient HTTP allowlist changed")

    return rounds


def continuity_summary(rounds: list[dict[str, Any]]) -> dict[str, Any]:
    per_source: dict[str, list[dict[str, Any]]] = {
        "water": [],
        "electricity": [],
        "natural_gas": [],
    }

    for r in rounds:
        receipt = load_json(Path(r["receipt_path"]))
        rows = {x["source_id"]: x for x in receipt["live_source_refresh"]["rows"]}
        if set(rows) != set(per_source):
            raise AssertionError("source set changed between rounds")

        for source_id, row in rows.items():
            if row["provider_identity"] is not True:
                raise AssertionError(f"{source_id} provider identity failed")
            if row["schema_identity"] is not True:
                raise AssertionError(f"{source_id} schema identity failed")
            if row["semantic_identity"] is not True:
                raise AssertionError(f"{source_id} semantic identity failed")
            if row["admission_receipt"]["decision"] != "ADMIT_OBSERVED":
                raise AssertionError(f"{source_id} admission failed")
            if row["freshness_age_seconds"] > row["max_age_seconds"]:
                raise AssertionError(f"{source_id} stale input")
            per_source[source_id].append(row)

    summary: dict[str, Any] = {}
    for source_id, rows in per_source.items():
        times = [selected_time(source_id, row) for row in rows]
        for i in range(1, len(times)):
            if times[i] < times[i - 1]:
                raise AssertionError(
                    f"{source_id} selected record timestamp regressed: "
                    f"{times[i - 1].isoformat()} -> {times[i].isoformat()}"
                )

        providers = {row["provider"] for row in rows}
        roles = {row["role"] for row in rows}
        if len(providers) != 1 or len(roles) != 1:
            raise AssertionError(f"{source_id} provider/role drift")

        hashes = [row["live_raw_sha256"] for row in rows]
        summary[source_id] = {
            "provider": rows[0]["provider"],
            "role": rows[0]["role"],
            "selected_record_times": [
                t.isoformat().replace("+00:00", "Z") for t in times
            ],
            "non_regressing": True,
            "freshness_age_seconds": [
                row["freshness_age_seconds"] for row in rows
            ],
            "max_age_seconds": rows[0]["max_age_seconds"],
            "raw_sha256_timeline": hashes,
            "distinct_raw_sha256_count": len(set(hashes)),
            "schema_identity": "3/3",
            "semantic_identity": "3/3",
            "admission": "3/3 ADMIT_OBSERVED",
        }
    return summary


def transport_recovery_summary(index: dict[str, Any]) -> dict[str, Any]:
    attempts = []
    recovered = []

    for round_row in index["rounds"]:
        for source_id, history in round_row["attempt_history"].items():
            for item in history:
                attempts.append(
                    {
                        "round": round_row["round"],
                        "source_id": source_id,
                        **item,
                    }
                )
            if len(history) > 1 and history[-1]["result"] == "SUCCESS":
                recovered.append(
                    {
                        "round": round_row["round"],
                        "source_id": source_id,
                        "attempt_count": len(history),
                        "prior_errors": [
                            h for h in history[:-1] if h["result"] == "ERROR"
                        ],
                    }
                )

    transient_errors = [
        row
        for row in attempts
        if row["result"] == "ERROR" and row.get("transient") is True
    ]

    return {
        "current_run_total_attempts": len(attempts),
        "current_run_transient_error_count": len(transient_errors),
        "current_run_recovered_sources": recovered,
        "current_run_all_rounds_completed": index["transport_recovery"][
            "all_rounds_completed"
        ],
    }


def mutate_water_provider(round_no: int, round_row: dict[str, Any]) -> dict[str, Any]:
    FAILURE_DIR.mkdir(parents=True, exist_ok=True)
    original_manifest_path = Path(round_row["manifest_path"])
    original_manifest = load_json(original_manifest_path)
    mutant_manifest = deepcopy(original_manifest)

    water_row = next(
        row for row in mutant_manifest["rows"] if row["source_id"] == "water"
    )
    original_water_path = Path(water_row["local_capture"])
    payload = json.loads(original_water_path.read_text(encoding="utf-8"))
    if payload.get("meta", {}).get("publisher") != "Environment Agency":
        raise AssertionError("failure-control anchor publisher missing")

    payload["meta"]["publisher"] = "CH11D_MUTATED_PROVIDER"
    mutant_bytes = (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")

    mutant_water_path = FAILURE_DIR / f"round_{round_no}_water_provider_drift.bin"
    mutant_water_path.write_bytes(mutant_bytes)
    water_row["local_capture"] = str(mutant_water_path)
    water_row["sha256"] = sha256_bytes(mutant_bytes)
    water_row["byte_length"] = len(mutant_bytes)

    mutant_manifest_path = FAILURE_DIR / f"round_{round_no}_mutant_manifest.json"
    canonical_write(mutant_manifest_path, mutant_manifest)

    ch11c.FETCH_MANIFEST = mutant_manifest_path
    try:
        manifest, rows = ch11c.fetch_rows()
        ch11c.pass_receipt(manifest, rows)
    except ch11c.Ch11cHold as exc:
        if (
            exc.source_id != "water"
            or exc.code != "HOLD_PROVIDER_IDENTITY_MISMATCH"
        ):
            raise AssertionError(
                f"unexpected provider-drift hold: {exc.source_id}/{exc.code}"
            )
        return {
            "mutation": "water.meta.publisher",
            "expected": "HOLD_PROVIDER_IDENTITY_MISMATCH",
            "observed": exc.code,
            "detected": True,
            "mutant_manifest_sha256": sha256_file(mutant_manifest_path),
            "mutant_water_sha256": sha256_file(mutant_water_path),
        }
    raise AssertionError("provider identity mutation produced false PASS")


def mutate_water_schema(round_no: int, round_row: dict[str, Any]) -> dict[str, Any]:
    FAILURE_DIR.mkdir(parents=True, exist_ok=True)
    original_manifest = load_json(Path(round_row["manifest_path"]))
    mutant_manifest = deepcopy(original_manifest)

    water_row = next(
        row for row in mutant_manifest["rows"] if row["source_id"] == "water"
    )
    original_water_path = Path(water_row["local_capture"])
    payload = json.loads(original_water_path.read_text(encoding="utf-8"))
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise AssertionError("schema-drift anchor item missing")

    measure = items[0].get("measure")
    if not isinstance(measure, dict) or "unitName" not in measure:
        raise AssertionError("schema-drift anchor unitName missing")

    measure["unitName_v2"] = measure.pop("unitName")
    mutant_bytes = (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")

    mutant_water_path = FAILURE_DIR / f"round_{round_no}_water_schema_drift.bin"
    mutant_water_path.write_bytes(mutant_bytes)
    water_row["local_capture"] = str(mutant_water_path)
    water_row["sha256"] = sha256_bytes(mutant_bytes)
    water_row["byte_length"] = len(mutant_bytes)

    mutant_manifest_path = (
        FAILURE_DIR / f"round_{round_no}_schema_mutant_manifest.json"
    )
    canonical_write(mutant_manifest_path, mutant_manifest)

    ch11c.FETCH_MANIFEST = mutant_manifest_path
    try:
        manifest, rows = ch11c.fetch_rows()
        ch11c.pass_receipt(manifest, rows)
    except ch11c.Ch11cHold as exc:
        if (
            exc.source_id != "water"
            or exc.code != "HOLD_SCHEMA_OR_RECORD_IDENTITY_MISMATCH"
        ):
            raise AssertionError(
                f"unexpected schema-drift hold: {exc.source_id}/{exc.code}"
            )
        return {
            "mutation": "water.items[0].measure.unitName->unitName_v2",
            "expected": "HOLD_SCHEMA_OR_RECORD_IDENTITY_MISMATCH",
            "observed": exc.code,
            "detected": True,
            "mutant_manifest_sha256": sha256_file(mutant_manifest_path),
            "mutant_water_sha256": sha256_file(mutant_water_path),
        }
    raise AssertionError("schema mutation produced false PASS")


def recovery_check(round_row: dict[str, Any]) -> dict[str, Any]:
    original_manifest_path = Path(round_row["manifest_path"])
    ch11c.FETCH_MANIFEST = original_manifest_path
    manifest, rows = ch11c.fetch_rows()
    receipt = ch11c.pass_receipt(manifest, rows)

    if (
        receipt["verdict"]
        != "PASS_CH11C__LIVE_READ_ONLY_SOURCE_REFRESH_3_OF_3__ZERO_WRITE_ZERO_ACTUATION"
    ):
        raise AssertionError("recovery did not restore PASS")

    return {
        "restored_original_manifest_sha256": sha256_file(original_manifest_path),
        "verdict": receipt["verdict"],
        "recovered": True,
    }


def build_receipt() -> dict[str, Any]:
    if (
        sha256_file(Path("fetch_ch11c_live_readonly_sources_v1.py"))
        != EXPECTED_CH11C_FETCHER_SHA256
    ):
        raise AssertionError("CH11C fetcher source drifted")
    if (
        sha256_file(Path("run_ch11c_live_readonly_source_refresh_v1.py"))
        != EXPECTED_CH11C_VALIDATOR_SHA256
    ):
        raise AssertionError("CH11C validator source drifted")

    prior_failure = verify_prior_transport_failure()
    index = load_json(ROUND_INDEX)
    rounds = validate_round_index(index)
    continuity = continuity_summary(rounds)
    transport = transport_recovery_summary(index)

    control_round = rounds[1]
    provider_drift = mutate_water_provider(2, control_round)
    schema_drift = mutate_water_schema(2, control_round)
    recovery = recovery_check(control_round)

    return {
        "schema_version": "CH11D_REPEATED_LIVE_TEMPORAL_RECOVERY_RECEIPT_V2",
        "gate_id": GATE_ID,
        "predecessors": {
            "ch11c_receipt_sha256": CH11C_RECEIPT_SHA256,
            "ch11c_fetcher_sha256": EXPECTED_CH11C_FETCHER_SHA256,
            "ch11c_validator_sha256": EXPECTED_CH11C_VALIDATOR_SHA256,
            "prior_transport_failure_evidence_sha256": sha256_file(
                PRIOR_TRANSPORT_FAILURE
            ),
        },
        "prior_real_transport_failure": {
            "run_id": prior_failure["github"]["run_id"],
            "artifact_id": prior_failure["github"]["artifact_id"],
            "artifact_digest": prior_failure["github"]["artifact_digest"],
            "round": prior_failure["observed_failure"]["round"],
            "source_id": prior_failure["observed_failure"]["source_id"],
            "error": prior_failure["observed_failure"]["error"],
            "fail_closed": True,
        },
        "round_index_sha256": sha256_file(ROUND_INDEX),
        "round_count": 3,
        "minimum_round_separation_seconds": 60,
        "successful_round_source_slots": 9,
        "expected_round_source_slots": 9,
        "transport_recovery": transport,
        "continuity": continuity,
        "failure_recovery": {
            "provider_identity_drift": provider_drift,
            "schema_drift": schema_drift,
            "recovery": recovery,
        },
        "network_boundary": index["network_boundary"],
        "external_state_written": False,
        "external_actuation": False,
        "continuous_ingestion_enabled": False,
        "claim_ceiling": {
            "three_round_live_read_stability": True,
            "minute_scale_temporal_non_regression": True,
            "bounded_transient_read_retry": True,
            "real_transport_failure_observed_fail_closed": True,
            "local_schema_drift_detection": True,
            "local_failure_recovery": True,
            "long_horizon_stability": False,
            "unattended_continuous_ingestion": False,
            "live_network_runtime_admission": False,
            "runtime_admission": False,
            "production_readiness": False,
            "production_admission": False,
            "network_write": False,
            "external_actuation": False,
            "pointer_promotion": False,
            "global_bind": False,
            "certification": False,
            "deployment": False,
            "merge_authorization": False,
        },
        "verdict": "PASS_CH11D__THREE_ROUND_LIVE_TEMPORAL_CONTINUITY__BOUNDED_TRANSPORT_RECOVERY__DRIFT_DETECTED__RECOVERY_PASS__ZERO_WRITE_ZERO_ACTUATION",
    }


def main() -> None:
    receipt = build_receipt()
    sha = canonical_write(OUT_PATH, receipt)
    print(
        json.dumps(
            receipt,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    )
    print("CH11D_RECEIPT_SHA256=" + sha)


if __name__ == "__main__":
    main()
