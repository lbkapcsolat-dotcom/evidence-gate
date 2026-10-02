from __future__ import annotations

from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any

import planetary_resource_formal_temporal_support_operator_spec_v1 as formal_spec
import planetary_resource_temporal_support_operator_reference_validator_v1 as reference_validator


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__TEMPORAL_SUPPORT_OPERATOR_EXECUTABLE_KERNEL_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__TEMPORAL_SUPPORT_OPERATOR_EXECUTABLE_KERNEL.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__TEMPORAL_SUPPORT_OPERATOR_EXECUTABLE_KERNEL_RECEIPT.json"
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


def fraction_fields(prefix: str, value: Fraction) -> dict[str, int]:
    return {
        f"{prefix}_n": value.numerator,
        f"{prefix}_d": value.denominator,
    }


def synthetic_hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _hold(
    code: str,
    *,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = dict(provenance or {})
    record["hold_codes"] = [code]
    record.setdefault("support_relation", "UNRESOLVED")
    record.setdefault("conservation_mode", "HOLD")
    record.setdefault("formula_id", None)
    record.setdefault("output_uncertainty_kind", None)
    return {
        "decision": "HOLD",
        "hold_code": code,
        "value_n": None,
        "value_d": None,
        "uncertainty": None,
        "support_relation": None,
        "formula_id": None,
        "conservation_lhs_n": None,
        "conservation_lhs_d": None,
        "conservation_rhs_n": None,
        "conservation_rhs_d": None,
        "provenance_transform_record": record,
    }


def _complete_base_provenance(
    *,
    fixture_id: str,
    fixture: dict[str, Any],
    formal_receipt: dict[str, Any],
) -> dict[str, Any]:
    cells = fixture["cells"]
    complete = bool(fixture.get("provenance_complete", True))
    record = {
        "operator_spec_id": formal_receipt["operator_spec"]["operator_spec_id"],
        "operator_version": fixture["operator_version"],
        "policy_receipt_sha256": formal_receipt["predecessor"]["receipt_sha256"],
        "variable_id": "synthetic.reference.rate",
        "resource_layer": "FRESHWATER",
        "quantity_kind": "RATE",
        "source_raw_sha256_set": [
            synthetic_hash(f"SYNTHETIC:{fixture_id}:{i}") for i, _ in enumerate(cells)
        ],
        "source_url_set": [
            f"synthetic://temporal-support/{fixture_id}/{i}" for i, _ in enumerate(cells)
        ],
        "source_cell_intervals": [
            {"start_utc": row["start_utc"], "end_utc": row["end_utc"]}
            for row in cells
        ],
        "unit_transform_chain": ["synthetic:canonical-unit:no-op"],
        "input_uncertainty_kinds": [
            fixture.get("uncertainty_kind", "EXACT") for _ in cells
        ],
        "input_evidence_refs": [
            f"SYNTHETIC_EVIDENCE:{fixture_id}:{i}" for i, _ in enumerate(cells)
        ],
    }
    if not complete:
        record["source_raw_sha256_set"] = []
        record["input_evidence_refs"] = []
    return record


def _provenance_ready(
    record: dict[str, Any],
    *,
    spec: dict[str, Any],
) -> bool:
    required_input_fields = {
        "operator_spec_id",
        "operator_version",
        "policy_receipt_sha256",
        "variable_id",
        "resource_layer",
        "quantity_kind",
        "source_raw_sha256_set",
        "source_url_set",
        "source_cell_intervals",
        "unit_transform_chain",
        "input_uncertainty_kinds",
        "input_evidence_refs",
    }
    if not required_input_fields.issubset(record):
        return False
    for key in ("source_raw_sha256_set", "source_url_set", "input_evidence_refs"):
        if not record[key]:
            return False
    if record["operator_spec_id"] != spec["operator_spec_id"]:
        return False
    return True


def _normalize_uncertainty(
    cell: dict[str, Any],
    default_kind: str,
) -> dict[str, Any]:
    payload = cell.get("uncertainty")
    if payload is None:
        if default_kind == "EXACT":
            return {"kind": "EXACT"}
        if default_kind == "UNKNOWN":
            return {"kind": "UNKNOWN"}
        if default_kind == "MOMENT":
            return {"kind": "MOMENT"}
        if default_kind == "EMPIRICAL":
            return {"kind": "EMPIRICAL"}
        raise AssertionError(f"unsupported synthetic uncertainty kind: {default_kind}")
    return dict(payload)


def _propagate_uncertainty(
    cells: list[dict[str, Any]],
    weights: list[Fraction],
    *,
    fixture: dict[str, Any],
    spec: dict[str, Any],
    provenance: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    uncertainties = [
        _normalize_uncertainty(cell["raw"], fixture.get("uncertainty_kind", "EXACT"))
        for cell in cells
    ]
    kinds = [u["kind"] for u in uncertainties]
    provenance["input_uncertainty_kinds"] = kinds

    if "UNKNOWN" in kinds:
        provenance["output_uncertainty_kind"] = "UNKNOWN"
        return {"kind": "UNKNOWN"}, None

    if "MOMENT" in kinds:
        if not fixture.get("covariance_provided", False):
            return None, _hold(
                "HOLD_TEMPORAL_UNCERTAINTY_OPERATOR",
                provenance=provenance,
            )
        return None, _hold(
            "HOLD_TEMPORAL_UNCERTAINTY_OPERATOR",
            provenance=provenance,
        )

    if "EMPIRICAL" in kinds:
        return None, _hold(
            "HOLD_TEMPORAL_UNCERTAINTY_OPERATOR",
            provenance=provenance,
        )

    if all(kind == "EXACT" for kind in kinds):
        provenance["output_uncertainty_kind"] = "EXACT"
        return {"kind": "EXACT"}, None

    if all(kind in ("EXACT", "INTERVAL") for kind in kinds):
        lower = Fraction(0)
        upper = Fraction(0)
        for cell, weight, uncertainty in zip(cells, weights, uncertainties):
            value = cell["value"]
            if uncertainty["kind"] == "EXACT":
                lo = hi = value
            else:
                lo = frac(uncertainty["lower_n"], uncertainty["lower_d"])
                hi = frac(uncertainty["upper_n"], uncertainty["upper_d"])
                if lo > hi:
                    return None, _hold(
                        "HOLD_TEMPORAL_UNCERTAINTY_OPERATOR",
                        provenance=provenance,
                    )
            lower += weight * lo
            upper += weight * hi
        provenance["output_uncertainty_kind"] = "INTERVAL"
        return {
            "kind": "INTERVAL",
            **fraction_fields("lower", lower),
            **fraction_fields("upper", upper),
        }, None

    return None, _hold(
        "HOLD_TEMPORAL_UNCERTAINTY_OPERATOR",
        provenance=provenance,
    )


def execute_kernel(
    fixture: dict[str, Any],
    *,
    target_start: datetime,
    target_end: datetime,
    formal_receipt: dict[str, Any],
) -> dict[str, Any]:
    spec = formal_receipt["operator_spec"]
    provenance = _complete_base_provenance(
        fixture_id=fixture["fixture_id"],
        fixture=fixture,
        formal_receipt=formal_receipt,
    )

    if fixture["operator_version"] != spec["operator_version"]:
        return _hold(
            "HOLD_TEMPORAL_OPERATOR_VERSION_UNPINNED",
            provenance=provenance,
        )
    if not _provenance_ready(provenance, spec=spec):
        return _hold(
            "HOLD_TEMPORAL_PROVENANCE_INCOMPLETE",
            provenance=provenance,
        )
    if target_end <= target_start:
        return _hold(
            "HOLD_TEMPORAL_TARGET_BOUNDARY_INVALID",
            provenance=provenance,
        )

    cells: list[dict[str, Any]] = []
    for row in fixture["cells"]:
        start = dt(row["start_utc"])
        end = dt(row["end_utc"])
        if end <= start:
            return _hold(
                "HOLD_TEMPORAL_SOURCE_BOUNDARY_MISSING",
                provenance=provenance,
            )
        cells.append(
            {
                "start": start,
                "end": end,
                "value": frac(row["value_n"], row["value_d"]),
                "native_time_mean": bool(row["native_time_mean"]),
                "raw": row,
            }
        )
    cells.sort(key=lambda c: (c["start"], c["end"]))

    target_seconds = Fraction(int((target_end - target_start).total_seconds()))
    target_interval = {
        "start_utc": target_start.isoformat().replace("+00:00", "Z"),
        "end_utc": target_end.isoformat().replace("+00:00", "Z"),
    }
    provenance["target_interval"] = target_interval

    if len(cells) == 1:
        cell = cells[0]
        if cell["start"] == target_start and cell["end"] == target_end:
            relation = "EXACT_TARGET_SUPPORT"
            if relation not in spec["source_support_domain"]["allowed_support_relations"]:
                return _hold(
                    "HOLD_TEMPORAL_CONSERVATION_UNDECLARED",
                    provenance=provenance,
                )
            provenance["support_relation"] = relation
            provenance["conservation_mode"] = "IDENTITY_EXACT_SUPPORT"
            provenance["formula_id"] = "IDENTITY_V1"
            uncertainty, uncertainty_hold = _propagate_uncertainty(
                cells,
                [Fraction(1)],
                fixture=fixture,
                spec=spec,
                provenance=provenance,
            )
            if uncertainty_hold:
                return uncertainty_hold
            provenance["hold_codes"] = []
            return {
                "decision": "PASS_IDENTITY",
                "hold_code": None,
                **fraction_fields("value", cell["value"]),
                "uncertainty": uncertainty,
                "support_relation": relation,
                "formula_id": "IDENTITY_V1",
                "conservation_lhs_n": None,
                "conservation_lhs_d": None,
                "conservation_rhs_n": None,
                "conservation_rhs_d": None,
                "provenance_transform_record": provenance,
            }
        if cell["start"] <= target_start and cell["end"] >= target_end:
            return _hold(
                "HOLD_TEMPORAL_INFORMATION_INSUFFICIENT",
                provenance=provenance,
            )
        return _hold(
            "HOLD_TEMPORAL_TARGET_NOT_EXACT_UNION",
            provenance=provenance,
        )

    if any(not cell["native_time_mean"] for cell in cells):
        return _hold(
            "HOLD_TEMPORAL_INFORMATION_INSUFFICIENT",
            provenance=provenance,
        )
    if any(
        cell["start"] < target_start or cell["end"] > target_end
        for cell in cells
    ):
        return _hold(
            "HOLD_TEMPORAL_TARGET_NOT_EXACT_UNION",
            provenance=provenance,
        )
    if cells[0]["start"] != target_start or cells[-1]["end"] != target_end:
        return _hold(
            "HOLD_TEMPORAL_TARGET_NOT_EXACT_UNION",
            provenance=provenance,
        )
    for left, right in zip(cells, cells[1:]):
        if left["end"] != right["start"]:
            return _hold(
                "HOLD_TEMPORAL_PARTITION_OVERLAP_OR_GAP",
                provenance=provenance,
            )

    relation = "FINER_NATIVE_MEAN_PARTITION_EXACTLY_COVERS_TARGET"
    if relation not in spec["source_support_domain"]["allowed_support_relations"]:
        return _hold(
            "HOLD_TEMPORAL_CONSERVATION_UNDECLARED",
            provenance=provenance,
        )
    provenance["support_relation"] = relation
    provenance["conservation_mode"] = "CONSERVATIVE_TIME_MEAN_PARTITION"
    provenance["formula_id"] = (
        "TIME_MEAN_PARTITION_WEIGHTED_BY_EXPLICIT_DURATION_V1"
    )

    durations = [
        Fraction(int((cell["end"] - cell["start"]).total_seconds()))
        for cell in cells
    ]
    if sum(durations, Fraction(0)) != target_seconds:
        return _hold(
            "HOLD_TEMPORAL_TARGET_NOT_EXACT_UNION",
            provenance=provenance,
        )
    weights = [duration / target_seconds for duration in durations]
    rhs = sum(
        (cell["value"] * duration for cell, duration in zip(cells, durations)),
        Fraction(0),
    )
    target_value = rhs / target_seconds
    lhs = target_value * target_seconds
    if lhs != rhs:
        raise AssertionError("exact rational conservation identity failed")

    uncertainty, uncertainty_hold = _propagate_uncertainty(
        cells,
        weights,
        fixture=fixture,
        spec=spec,
        provenance=provenance,
    )
    if uncertainty_hold:
        return uncertainty_hold
    provenance["hold_codes"] = []

    return {
        "decision": "PASS_CONSERVATIVE",
        "hold_code": None,
        **fraction_fields("value", target_value),
        "uncertainty": uncertainty,
        "support_relation": relation,
        "formula_id": (
            "TIME_MEAN_PARTITION_WEIGHTED_BY_EXPLICIT_DURATION_V1"
        ),
        **fraction_fields("conservation_lhs", lhs),
        **fraction_fields("conservation_rhs", rhs),
        "provenance_transform_record": provenance,
    }


def _adapt_reference_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(fixture))


def _check_reference_expected(
    fixture: dict[str, Any],
    result: dict[str, Any],
) -> None:
    if result["decision"] != fixture["expected_decision"]:
        raise AssertionError(
            f"{fixture['fixture_id']}: {result['decision']} != "
            f"{fixture['expected_decision']}"
        )
    if fixture["expected_decision"] == "HOLD":
        if result["hold_code"] != fixture["expected_hold_code"]:
            raise AssertionError(
                f"{fixture['fixture_id']}: {result['hold_code']} != "
                f"{fixture['expected_hold_code']}"
            )
        return
    if (result["value_n"], result["value_d"]) != (
        fixture["expected_value_n"],
        fixture["expected_value_d"],
    ):
        raise AssertionError(f"{fixture['fixture_id']}: value mismatch")
    expected_uncertainty = fixture["expected_uncertainty_kind"]
    if result["uncertainty"]["kind"] != expected_uncertainty:
        raise AssertionError(
            f"{fixture['fixture_id']}: uncertainty kind mismatch"
        )
    if "expected_conservation_lhs_n" in fixture:
        fields = (
            "conservation_lhs_n",
            "conservation_lhs_d",
            "conservation_rhs_n",
            "conservation_rhs_d",
        )
        for field in fields:
            if result[field] != fixture[f"expected_{field}"]:
                raise AssertionError(
                    f"{fixture['fixture_id']}: {field} mismatch"
                )


def _run_uncertainty_probe(
    probe: dict[str, Any],
    *,
    formal_receipt: dict[str, Any],
) -> dict[str, Any]:
    fixture = {
        "fixture_id": probe["probe_id"],
        "operator_version": "V1",
        "provenance_complete": True,
        "uncertainty_kind": "INTERVAL",
        "covariance_provided": False,
        "cells": probe["cells"],
    }
    result = execute_kernel(
        fixture,
        target_start=dt(probe["target_start_utc"]),
        target_end=dt(probe["target_end_utc"]),
        formal_receipt=formal_receipt,
    )
    if result["decision"] != "PASS_CONSERVATIVE":
        raise AssertionError("interval uncertainty probe did not pass")
    if (result["value_n"], result["value_d"]) != (
        probe["expected_value_n"],
        probe["expected_value_d"],
    ):
        raise AssertionError("interval uncertainty probe value mismatch")
    interval = result["uncertainty"]
    if interval["kind"] != "INTERVAL":
        raise AssertionError("interval uncertainty kind was not preserved")
    expected = (
        probe["expected_lower_n"],
        probe["expected_lower_d"],
        probe["expected_upper_n"],
        probe["expected_upper_d"],
    )
    observed = (
        interval["lower_n"],
        interval["lower_d"],
        interval["upper_n"],
        interval["upper_d"],
    )
    if observed != expected:
        raise AssertionError(f"interval uncertainty mismatch: {observed} != {expected}")
    return result


def run_gate() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("gate id mismatch")
    if any(contract["fences"].values()):
        raise AssertionError("forbidden fence enabled")
    if not all(contract["requirements"].values()):
        raise AssertionError("kernel requirement disabled")

    pred = reference_validator.run_gate()
    expected = contract["predecessor"]
    pred_sha = canonical_sha256(pred)
    if pred_sha != expected["receipt_sha256"]:
        raise AssertionError(
            f"reference-validator receipt changed: {pred_sha} != "
            f"{expected['receipt_sha256']}"
        )
    if pred["verdict"] != expected["verdict"]:
        raise AssertionError("reference-validator verdict changed")
    if pred["path_b_status"] != "LOCKED_NOT_ACTIVATED":
        raise AssertionError("PATH_B predecessor lock changed")

    formal = formal_spec.run_gate()
    formal_pin = contract["formal_spec"]
    formal_sha = canonical_sha256(formal)
    if formal_sha != formal_pin["receipt_sha256"]:
        raise AssertionError("formal spec receipt changed")
    spec = formal["operator_spec"]
    if spec["operator_spec_id"] != formal_pin["operator_spec_id"]:
        raise AssertionError("operator spec id changed")
    if spec["operator_version"] != formal_pin["operator_version"]:
        raise AssertionError("operator version changed")
    if formal["predecessor"]["receipt_sha256"] != formal_pin["policy_receipt_sha256"]:
        raise AssertionError("policy receipt pin changed")

    kernel = contract["kernel"]
    if kernel["implementation_basis"] != "FROZEN_FORMAL_SPEC_ONLY":
        raise AssertionError("kernel implementation basis changed")
    if kernel["arithmetic"] != "EXACT_RATIONAL_FRACTION":
        raise AssertionError("kernel arithmetic changed")
    if kernel["supported_relations"] != spec["source_support_domain"]["allowed_support_relations"]:
        raise AssertionError("kernel support relation registry diverged")
    if not kernel["path_b_remains_locked"]:
        raise AssertionError("PATH_B lock disabled")
    if not kernel["synthetic_fixture_execution_only"]:
        raise AssertionError("synthetic-only gate scope disabled")
    if kernel["real_source_input_allowed"] or kernel["real_value_composition_allowed"]:
        raise AssertionError("real execution enabled")

    ref_contract = json.loads(
        reference_validator.CONTRACT_PATH.read_text(encoding="utf-8")
    )
    target = ref_contract["target_interval"]
    target_start = dt(target["start_utc"])
    target_end = dt(target["end_utc"])

    replay: dict[str, dict[str, Any]] = {}
    for source_fixture in ref_contract["fixtures"]:
        fixture = _adapt_reference_fixture(source_fixture)
        result = execute_kernel(
            fixture,
            target_start=target_start,
            target_end=target_end,
            formal_receipt=formal,
        )
        _check_reference_expected(fixture, result)
        replay[fixture["fixture_id"]] = result

    if len(replay) != 9:
        raise AssertionError("reference fixture replay count changed")

    interval_probe = _run_uncertainty_probe(
        contract["uncertainty_probe"],
        formal_receipt=formal,
    )

    mutation_checks = {
        "GAP": {
            "passed": replay["PARTITION_WITH_GAP"]["hold_code"]
            == "HOLD_TEMPORAL_PARTITION_OVERLAP_OR_GAP",
            "observed": replay["PARTITION_WITH_GAP"]["hold_code"],
        },
        "OVERLAP": {
            "passed": replay["PARTITION_WITH_OVERLAP"]["hold_code"]
            == "HOLD_TEMPORAL_PARTITION_OVERLAP_OR_GAP",
            "observed": replay["PARTITION_WITH_OVERLAP"]["hold_code"],
        },
        "COARSE_TO_FINE": {
            "passed": replay["ONE_60MIN_MEAN_TO_30MIN_TARGET"]["hold_code"]
            == "HOLD_TEMPORAL_INFORMATION_INSUFFICIENT",
            "observed": replay["ONE_60MIN_MEAN_TO_30MIN_TARGET"]["hold_code"],
        },
        "UNKNOWN_TO_EXACT": {
            "passed": replay["UNKNOWN_UNCERTAINTY"]["uncertainty"]["kind"]
            == "UNKNOWN",
            "observed": replay["UNKNOWN_UNCERTAINTY"]["uncertainty"]["kind"],
        },
        "MISSING_COVARIANCE": {
            "passed": replay["MOMENT_WITHOUT_COVARIANCE"]["hold_code"]
            == "HOLD_TEMPORAL_UNCERTAINTY_OPERATOR",
            "observed": replay["MOMENT_WITHOUT_COVARIANCE"]["hold_code"],
        },
        "MISSING_PROVENANCE": {
            "passed": replay["INCOMPLETE_PROVENANCE"]["hold_code"]
            == "HOLD_TEMPORAL_PROVENANCE_INCOMPLETE",
            "observed": replay["INCOMPLETE_PROVENANCE"]["hold_code"],
        },
        "UNPINNED_VERSION": {
            "passed": replay["UNPINNED_OPERATOR_VERSION"]["hold_code"]
            == "HOLD_TEMPORAL_OPERATOR_VERSION_UNPINNED",
            "observed": replay["UNPINNED_OPERATOR_VERSION"]["hold_code"],
        },
    }
    if set(mutation_checks) != set(contract["required_mutations"]):
        raise AssertionError("mutation registry changed")
    if not all(item["passed"] for item in mutation_checks.values()):
        raise AssertionError("one or more mutation checks failed")

    conservative = replay["TWO_15MIN_NATIVE_MEANS_TO_ONE_30MIN_TARGET"]
    lhs = frac(
        conservative["conservation_lhs_n"],
        conservative["conservation_lhs_d"],
    )
    rhs = frac(
        conservative["conservation_rhs_n"],
        conservative["conservation_rhs_d"],
    )
    if lhs != rhs:
        raise AssertionError("replayed conservation identity failed")

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_TEMPORAL_SUPPORT_OPERATOR_EXECUTABLE_KERNEL_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessor": {
            "receipt_sha256": pred_sha,
            "head_sha": expected["head_sha"],
            "verdict": pred["verdict"],
        },
        "formal_spec": {
            "receipt_sha256": formal_sha,
            "operator_spec_id": spec["operator_spec_id"],
            "operator_version": spec["operator_version"],
            "policy_receipt_sha256": formal["predecessor"]["receipt_sha256"],
        },
        "kernel": {
            **kernel,
            "status": "EXECUTABLE_ISOLATED_SYNTHETIC_ONLY",
        },
        "reference_replay_count": len(replay),
        "reference_replay": replay,
        "reference_replay_9_of_9": True,
        "mutation_checks": mutation_checks,
        "mutation_checks_7_of_7": True,
        "interval_uncertainty_probe": interval_probe,
        "conservation_identity_exact": True,
        "provenance_transform_record_emitted": True,
        "fail_closed_hold_codes_enforced": True,
        "path_b_status": "LOCKED_NOT_ACTIVATED",
        "real_source_input_used": False,
        "real_value_composition_performed": False,
        "core_patch_required": False,
        "fences": contract["fences"],
        "verdict": contract["verdict_target"],
        "claim_ceiling": (
            "Executable temporal-support kernel proven on synthetic fixtures only. "
            "PATH_B remains locked; no real-source admission or real value composition occurred."
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
    print("TEMPORAL_SUPPORT_EXECUTABLE_KERNEL_RECEIPT_SHA256=" + sha)
