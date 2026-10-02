from __future__ import annotations

from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any

import planetary_resource_formal_temporal_support_operator_spec_v1 as predecessor


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__TEMPORAL_SUPPORT_OPERATOR_REFERENCE_VALIDATOR_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__TEMPORAL_SUPPORT_OPERATOR_REFERENCE_VALIDATOR.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__TEMPORAL_SUPPORT_OPERATOR_REFERENCE_VALIDATOR_RECEIPT.json"
)


def canonical_sha256(payload: dict[str, Any]) -> str:
    body = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def frac(n: int, d: int) -> Fraction:
    return Fraction(int(n), int(d))


def hold(code: str) -> dict[str, Any]:
    return {
        "decision": "HOLD",
        "hold_code": code,
        "value_n": None,
        "value_d": None,
        "uncertainty_kind": None,
        "conservation_lhs_n": None,
        "conservation_lhs_d": None,
        "conservation_rhs_n": None,
        "conservation_rhs_d": None,
    }


def validate_fixture(
    fixture: dict[str, Any],
    *,
    target_start: datetime,
    target_end: datetime,
    spec: dict[str, Any],
) -> dict[str, Any]:
    if fixture["operator_version"] != spec["operator_version"]:
        return hold("HOLD_TEMPORAL_OPERATOR_VERSION_UNPINNED")
    if not fixture["provenance_complete"]:
        return hold("HOLD_TEMPORAL_PROVENANCE_INCOMPLETE")

    uncertainty_kind = fixture["uncertainty_kind"]
    uncertainty_spec = spec["uncertainty_propagation"]
    if uncertainty_kind == "MOMENT" and not fixture["covariance_provided"]:
        if uncertainty_spec["MOMENT"] != "REQUIRE_COVARIANCE_OR_HOLD":
            raise AssertionError("predecessor moment uncertainty rule changed")
        return hold("HOLD_TEMPORAL_UNCERTAINTY_OPERATOR")

    cells = []
    for row in fixture["cells"]:
        start = dt(row["start_utc"])
        end = dt(row["end_utc"])
        if end <= start:
            return hold("HOLD_TEMPORAL_SOURCE_BOUNDARY_MISSING")
        cells.append(
            {
                "start": start,
                "end": end,
                "value": frac(row["value_n"], row["value_d"]),
                "native_time_mean": bool(row["native_time_mean"]),
            }
        )
    cells.sort(key=lambda x: (x["start"], x["end"]))

    # Exact identity support is the only admissible single-cell case.
    if len(cells) == 1:
        cell = cells[0]
        if cell["start"] == target_start and cell["end"] == target_end:
            out_uncertainty = (
                "UNKNOWN"
                if uncertainty_kind == "UNKNOWN"
                else uncertainty_kind
            )
            return {
                "decision": "PASS_IDENTITY",
                "hold_code": None,
                "value_n": cell["value"].numerator,
                "value_d": cell["value"].denominator,
                "uncertainty_kind": out_uncertainty,
                "support_relation": "EXACT_TARGET_SUPPORT",
                "formula_id": "IDENTITY_V1",
                "conservation_lhs_n": None,
                "conservation_lhs_d": None,
                "conservation_rhs_n": None,
                "conservation_rhs_d": None,
            }
        if cell["start"] <= target_start and cell["end"] >= target_end:
            return hold("HOLD_TEMPORAL_INFORMATION_INSUFFICIENT")
        return hold("HOLD_TEMPORAL_TARGET_NOT_EXACT_UNION")

    # Conservative partition requires source-native mean cells wholly inside
    # the target and an exact non-overlapping, gap-free partition.
    if any(not c["native_time_mean"] for c in cells):
        return hold("HOLD_TEMPORAL_INFORMATION_INSUFFICIENT")
    if any(c["start"] < target_start or c["end"] > target_end for c in cells):
        return hold("HOLD_TEMPORAL_TARGET_NOT_EXACT_UNION")
    if cells[0]["start"] != target_start or cells[-1]["end"] != target_end:
        return hold("HOLD_TEMPORAL_TARGET_NOT_EXACT_UNION")
    for left, right in zip(cells, cells[1:]):
        if left["end"] != right["start"]:
            return hold("HOLD_TEMPORAL_PARTITION_OVERLAP_OR_GAP")

    target_seconds = Fraction(int((target_end - target_start).total_seconds()))
    if target_seconds <= 0:
        return hold("HOLD_TEMPORAL_TARGET_BOUNDARY_INVALID")

    rhs = Fraction(0)
    for cell in cells:
        seconds = Fraction(int((cell["end"] - cell["start"]).total_seconds()))
        rhs += cell["value"] * seconds

    target_value = rhs / target_seconds
    lhs = target_value * target_seconds
    if lhs != rhs:
        raise AssertionError("conservation identity failed")

    if uncertainty_kind == "UNKNOWN":
        output_uncertainty = "UNKNOWN"
    elif uncertainty_kind == "EXACT":
        output_uncertainty = "EXACT"
    else:
        output_uncertainty = uncertainty_kind

    return {
        "decision": "PASS_CONSERVATIVE",
        "hold_code": None,
        "value_n": target_value.numerator,
        "value_d": target_value.denominator,
        "uncertainty_kind": output_uncertainty,
        "support_relation": "FINER_NATIVE_MEAN_PARTITION_EXACTLY_COVERS_TARGET",
        "formula_id": "TIME_MEAN_PARTITION_WEIGHTED_BY_EXPLICIT_DURATION_V1",
        "conservation_lhs_n": lhs.numerator,
        "conservation_lhs_d": lhs.denominator,
        "conservation_rhs_n": rhs.numerator,
        "conservation_rhs_d": rhs.denominator,
    }


def run_gate() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("gate id mismatch")
    if contract["target_path"] != "PATH_B":
        raise AssertionError("validator may target PATH_B only")
    if any(contract["fences"].values()):
        raise AssertionError("forbidden fence enabled")
    if not all(contract["requirements"].values()):
        raise AssertionError("validator requirement disabled")

    pred = predecessor.run_gate()
    expected = contract["predecessor"]
    pred_sha = canonical_sha256(pred)
    if pred_sha != expected["receipt_sha256"]:
        raise AssertionError(
            f"predecessor receipt changed: {pred_sha} != {expected['receipt_sha256']}"
        )
    if pred["verdict"] != expected["verdict"]:
        raise AssertionError("predecessor verdict changed")
    if pred["path_b_status"] != "DECLARED_LOCKED_NOT_ACTIVATED":
        raise AssertionError("PATH_B predecessor lock changed")

    execution = contract["execution_policy"]
    if not execution["path_b_remains_locked"]:
        raise AssertionError("PATH_B lock disabled")
    if not execution["reference_validator_only"]:
        raise AssertionError("reference-validator-only scope disabled")
    for key in (
        "real_source_transformation",
        "operator_activation",
        "real_value_composition",
    ):
        if execution[key]:
            raise AssertionError(f"forbidden execution enabled: {key}")

    target = contract["target_interval"]
    target_start = dt(target["start_utc"])
    target_end = dt(target["end_utc"])
    if int((target_end - target_start).total_seconds()) != target["duration_seconds"]:
        raise AssertionError("target duration changed")

    spec = pred["operator_spec"]
    results: dict[str, dict[str, Any]] = {}
    for fixture in contract["fixtures"]:
        observed = validate_fixture(
            fixture,
            target_start=target_start,
            target_end=target_end,
            spec=spec,
        )
        fixture_id = fixture["fixture_id"]
        if observed["decision"] != fixture["expected_decision"]:
            raise AssertionError(
                f"{fixture_id}: {observed['decision']} != "
                f"{fixture['expected_decision']}"
            )
        if fixture["expected_decision"] == "HOLD":
            if observed["hold_code"] != fixture["expected_hold_code"]:
                raise AssertionError(
                    f"{fixture_id}: {observed['hold_code']} != "
                    f"{fixture['expected_hold_code']}"
                )
        else:
            for field in (
                "expected_value_n",
                "expected_value_d",
                "expected_uncertainty_kind",
            ):
                observed_field = field.replace("expected_", "")
                if observed[observed_field] != fixture[field]:
                    raise AssertionError(
                        f"{fixture_id}: {observed_field} mismatch"
                    )
            if "expected_conservation_lhs_n" in fixture:
                for field in (
                    "expected_conservation_lhs_n",
                    "expected_conservation_lhs_d",
                    "expected_conservation_rhs_n",
                    "expected_conservation_rhs_d",
                ):
                    observed_field = field.replace("expected_", "")
                    if observed[observed_field] != fixture[field]:
                        raise AssertionError(
                            f"{fixture_id}: {observed_field} mismatch"
                        )
        results[fixture_id] = observed

    required_ids = {
        "EXACT_SUPPORT_IDENTITY",
        "TWO_15MIN_NATIVE_MEANS_TO_ONE_30MIN_TARGET",
        "ONE_60MIN_MEAN_TO_30MIN_TARGET",
        "PARTITION_WITH_GAP",
        "PARTITION_WITH_OVERLAP",
        "UNKNOWN_UNCERTAINTY",
        "MOMENT_WITHOUT_COVARIANCE",
        "INCOMPLETE_PROVENANCE",
        "UNPINNED_OPERATOR_VERSION",
    }
    if set(results) != required_ids:
        raise AssertionError("required fixture matrix changed")

    conservative = results["TWO_15MIN_NATIVE_MEANS_TO_ONE_30MIN_TARGET"]
    if (
        frac(conservative["conservation_lhs_n"], conservative["conservation_lhs_d"])
        != frac(conservative["conservation_rhs_n"], conservative["conservation_rhs_d"])
    ):
        raise AssertionError("conservation receipt identity failed")

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_TEMPORAL_SUPPORT_OPERATOR_REFERENCE_VALIDATOR_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessor": {
            "receipt_sha256": pred_sha,
            "head_sha": expected["head_sha"],
            "verdict": pred["verdict"],
        },
        "target_path": "PATH_B",
        "execution_policy": execution,
        "target_interval": target,
        "fixture_count": len(results),
        "fixtures": results,
        "conservation_identity_exact": True,
        "deterministic_replay_required": True,
        "path_b_status": "LOCKED_NOT_ACTIVATED",
        "operator_execution_status": "REFERENCE_VALIDATOR_ONLY",
        "real_source_transformation_performed": False,
        "real_value_composition_performed": False,
        "core_patch_required": False,
        "fences": contract["fences"],
        "verdict": contract["verdict_target"],
        "claim_ceiling": (
            "Synthetic reference validation only. No real source was transformed, "
            "no PATH_B activation occurred, and no production temporal operator ran."
        ),
    }


def write_receipt() -> tuple[dict[str, Any], str]:
    receipt = run_gate()
    body = json.dumps(
        receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"
    OUT_PATH.write_text(body, encoding="utf-8")
    return receipt, hashlib.sha256(body.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    receipt, sha = write_receipt()
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    print("TEMPORAL_SUPPORT_REFERENCE_VALIDATOR_RECEIPT_SHA256=" + sha)
