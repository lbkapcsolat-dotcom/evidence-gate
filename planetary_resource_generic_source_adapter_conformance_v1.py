from __future__ import annotations

from dataclasses import asdict, fields, replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable

import planetary_resource_empirical_admission_v1 as admission
import planetary_resource_generic_source_adapter_v1 as generic
import planetary_resource_generic_source_bindings_v1 as bindings
import planetary_resource_generic_source_adapter_gate_v1 as generic_gate


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__GENERIC_SOURCE_ADAPTER_CONFORMANCE_HARNESS_V1"
)
SCHEMA_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__GENERIC_SOURCE_ADAPTER_CONFORMANCE_SCHEMA.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__GENERIC_SOURCE_ADAPTER_CONFORMANCE_HARNESS_RECEIPT.json"
)


class ConformanceHold(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


def sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_schema() -> dict[str, Any]:
    s = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if s["gate_id"] != GATE_ID:
        raise AssertionError("conformance schema gate mismatch")
    if s["acceptance"]["existing_bindings_conform"] != "3/3":
        raise AssertionError("conformance acceptance changed")
    if s["acceptance"]["rejection_matrix_fail_closed"] != "12/12":
        raise AssertionError("rejection acceptance changed")
    if s["acceptance"]["receipt_equality"] != "3/3 exact":
        raise AssertionError("receipt-equality acceptance changed")
    return s


SCHEMA = load_schema()
VARIABLES = admission.VARIABLES
EMPIRICAL_CONTRACT = admission.CONTRACT


def _required_nonempty_strings(spec: generic.GenericAdapterSpec) -> None:
    for name in SCHEMA["minimum_required_spec_fields"]:
        value = getattr(spec, name)
        if not isinstance(value, str) or not value.strip():
            raise ConformanceHold(
                "HOLD_BINDING_REQUIRED_FIELD_MISSING", name
            )


def _required_record_strings(record: generic.GenericSourceRecord) -> None:
    for name in SCHEMA["minimum_required_record_fields"]:
        value = getattr(record, name)
        if not isinstance(value, str) or not value.strip():
            raise ConformanceHold(
                "HOLD_BINDING_RECORD_FIELD_MISSING", name
            )


def _verify_sha(spec: generic.GenericAdapterSpec) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", spec.raw_sha256):
        raise ConformanceHold("HOLD_BINDING_RAW_SHA_INVALID")
    p = Path(spec.raw_file)
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    if got != spec.raw_sha256:
        raise ConformanceHold(
            "HOLD_BINDING_RAW_SHA_MISMATCH",
            f"{got} != {spec.raw_sha256}",
        )


def _variable_rule(spec: generic.GenericAdapterSpec) -> dict[str, Any]:
    row = VARIABLES.get(spec.variable_id)
    if row is None:
        raise ConformanceHold(
            "HOLD_BINDING_REQUIRED_FIELD_MISSING",
            "variable_id not in frozen dictionary",
        )
    if row["layer"] != spec.source_layer or row["quantity_kind"] != spec.source_quantity_kind:
        raise ConformanceHold(
            "HOLD_BINDING_REQUIRED_FIELD_MISSING",
            "variable layer/quantity mismatch",
        )
    return row


def _accepted_units(spec: generic.GenericAdapterSpec) -> dict[str, Any]:
    return (
        EMPIRICAL_CONTRACT["accepted_source_units"]
        .get(spec.source_layer, {})
        .get(spec.source_quantity_kind, {})
    )


def _verify_pre_contract(
    spec: generic.GenericAdapterSpec,
    record: generic.GenericSourceRecord,
) -> None:
    t = spec.pre_contract_transform
    accepted = _accepted_units(spec)

    if not t.enabled:
        if record.source_unit not in accepted:
            raise ConformanceHold(
                "HOLD_BINDING_SOURCE_UNIT_NOT_ADMISSIBLE",
                record.source_unit,
            )
        return

    if record.source_unit != t.from_unit:
        raise ConformanceHold("HOLD_PRECONTRACT_SOURCE_UNIT_MISMATCH")
    if t.factor_n <= 0 or t.factor_d <= 0:
        raise ConformanceHold("HOLD_PRECONTRACT_FACTOR_INVALID")
    if not t.evidence_ref.strip() or not t.chain_tokens:
        raise ConformanceHold("HOLD_PRECONTRACT_EVIDENCE_REQUIRED")
    if t.to_unit not in accepted:
        raise ConformanceHold(
            "HOLD_PRECONTRACT_TARGET_UNIT_NOT_ADMISSIBLE",
            t.to_unit,
        )

    target_rule = accepted[t.to_unit]
    target_basis = target_rule.get("gas_basis")
    if spec.source_layer == "NATURAL_GAS" and target_basis == "HHV":
        if t.to_gas_basis != "HHV":
            raise ConformanceHold("HOLD_PRECONTRACT_GAS_BASIS_REQUIRED")


def validate_binding(
    spec: generic.GenericAdapterSpec,
    record: generic.GenericSourceRecord,
) -> dict[str, Any]:
    _required_nonempty_strings(spec)
    _required_record_strings(record)
    _verify_sha(spec)
    _variable_rule(spec)

    if spec.max_age_seconds < 0:
        raise ConformanceHold("HOLD_BINDING_MAX_AGE_INVALID")
    if not spec.base_transform_chain:
        raise ConformanceHold("HOLD_BINDING_BASE_CHAIN_MISSING")
    if spec.sign_semantics_declared is not True:
        raise ConformanceHold(
            "HOLD_BINDING_REQUIRED_FIELD_MISSING",
            "sign_semantics_declared",
        )

    if spec.spatial_method not in EMPIRICAL_CONTRACT["spatial_mapping"]["allowed_methods"]:
        raise ConformanceHold(
            "HOLD_BINDING_REQUIRED_FIELD_MISSING",
            "spatial_method",
        )
    if spec.temporal_method not in EMPIRICAL_CONTRACT["temporal_alignment"]["allowed_methods"]:
        raise ConformanceHold(
            "HOLD_BINDING_REQUIRED_FIELD_MISSING",
            "temporal_method",
        )

    _verify_pre_contract(spec, record)

    return {
        "provider": spec.provider,
        "variable_id": spec.variable_id,
        "source_layer": spec.source_layer,
        "source_quantity_kind": spec.source_quantity_kind,
        "source_unit": record.source_unit,
        "pre_contract_transform_enabled": spec.pre_contract_transform.enabled,
        "raw_sha256": spec.raw_sha256,
        "conformant": True,
    }


def conform_and_adapt(
    spec: generic.GenericAdapterSpec,
    record: generic.GenericSourceRecord,
) -> admission.AdmissionReceipt:
    validate_binding(spec, record)
    return generic.adapt(spec, record)


def _expect_hold(
    case_id: str,
    expected: str,
    fn: Callable[[], Any],
) -> dict[str, Any]:
    try:
        fn()
    except ConformanceHold as exc:
        if exc.code != expected:
            raise AssertionError(
                f"{case_id}: expected {expected}, got {exc.code}"
            )
        return {
            "id": case_id,
            "expected": expected,
            "observed": exc.code,
            "passed": True,
        }
    raise AssertionError(f"{case_id}: expected HOLD, got PASS")


def run_rejection_matrix() -> list[dict[str, Any]]:
    water_spec, water_record = bindings.water_binding()
    gas_spec, gas_record = bindings.gas_binding()

    def bad_sha_same_length() -> str:
        return "0" * 64 if water_spec.raw_sha256 != "0" * 64 else "1" * 64

    cases = [
        ("R01", "HOLD_BINDING_REQUIRED_FIELD_MISSING",
         lambda: validate_binding(replace(water_spec, provider=""), water_record)),
        ("R02", "HOLD_BINDING_RECORD_FIELD_MISSING",
         lambda: validate_binding(water_spec, replace(water_record, record_locator=""))),
        ("R03", "HOLD_BINDING_RAW_SHA_INVALID",
         lambda: validate_binding(replace(water_spec, raw_sha256="abc"), water_record)),
        ("R04", "HOLD_BINDING_RAW_SHA_MISMATCH",
         lambda: validate_binding(replace(water_spec, raw_sha256=bad_sha_same_length()), water_record)),
        ("R05", "HOLD_BINDING_MAX_AGE_INVALID",
         lambda: validate_binding(replace(water_spec, max_age_seconds=-1), water_record)),
        ("R06", "HOLD_BINDING_BASE_CHAIN_MISSING",
         lambda: validate_binding(replace(water_spec, base_transform_chain=()), water_record)),
        ("R07", "HOLD_BINDING_SOURCE_UNIT_NOT_ADMISSIBLE",
         lambda: validate_binding(water_spec, replace(water_record, source_unit="barrel/day"))),
        ("R08", "HOLD_PRECONTRACT_SOURCE_UNIT_MISMATCH",
         lambda: validate_binding(
             gas_spec,
             replace(gas_record, source_unit="MWh/h"),
         )),
        ("R09", "HOLD_PRECONTRACT_FACTOR_INVALID",
         lambda: validate_binding(
             replace(
                 gas_spec,
                 pre_contract_transform=replace(
                     gas_spec.pre_contract_transform,
                     factor_n=0,
                 ),
             ),
             gas_record,
         )),
        ("R10", "HOLD_PRECONTRACT_EVIDENCE_REQUIRED",
         lambda: validate_binding(
             replace(
                 gas_spec,
                 pre_contract_transform=replace(
                     gas_spec.pre_contract_transform,
                     evidence_ref="",
                 ),
             ),
             gas_record,
         )),
        ("R11", "HOLD_PRECONTRACT_TARGET_UNIT_NOT_ADMISSIBLE",
         lambda: validate_binding(
             replace(
                 gas_spec,
                 pre_contract_transform=replace(
                     gas_spec.pre_contract_transform,
                     to_unit="m3/s",
                 ),
             ),
             gas_record,
         )),
        ("R12", "HOLD_PRECONTRACT_GAS_BASIS_REQUIRED",
         lambda: validate_binding(
             replace(
                 gas_spec,
                 pre_contract_transform=replace(
                     gas_spec.pre_contract_transform,
                     to_gas_basis="",
                 ),
             ),
             gas_record,
         )),
    ]

    return [_expect_hold(case_id, expected, fn) for case_id, expected, fn in cases]


def run_harness() -> dict[str, Any]:
    pins = SCHEMA["tested_interface_pins"]
    pin_files = {
        "generic_adapter_contract_sha256":
            "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__GENERIC_SOURCE_ADAPTER_CONTRACT.json",
        "generic_adapter_implementation_sha256":
            "planetary_resource_generic_source_adapter_v1.py",
        "generic_bindings_sha256":
            "planetary_resource_generic_source_bindings_v1.py",
        "generic_gate_sha256":
            "planetary_resource_generic_source_adapter_gate_v1.py",
    }
    verified_pins: dict[str, str] = {}
    for key, path in pin_files.items():
        got = sha256_file(path)
        if got != pins[key]:
            raise AssertionError(f"tested interface changed: {key} {got} != {pins[key]}")
        verified_pins[key] = got

    previous = generic_gate.run_gate()
    previous_canonical = (
        json.dumps(previous, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    )
    previous_sha = hashlib.sha256(previous_canonical.encode("utf-8")).hexdigest()
    if previous_sha != pins["generic_adapter_receipt_sha256"]:
        raise AssertionError("generic adapter predecessor receipt changed")

    builders = {
        "water": bindings.water_binding,
        "electricity": bindings.electricity_binding,
        "gas": bindings.gas_binding,
    }
    conformance: dict[str, Any] = {}
    for name, builder in builders.items():
        spec, record = builder()
        certificate = validate_binding(spec, record)
        adapted = conform_and_adapt(spec, record)
        existing_hash = previous["receipt_equality"][name]["generic_empirical_receipt_sha256"]
        adapted_hash = hashlib.sha256(
            json.dumps(
                asdict(adapted),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        if adapted_hash != existing_hash:
            raise AssertionError(f"{name} conformance replay receipt mismatch")
        conformance[name] = {
            **certificate,
            "empirical_receipt_sha256": adapted_hash,
            "receipt_equal_to_generic_contract_baseline": True,
        }

    rejection = run_rejection_matrix()
    if sum(1 for x in rejection if x["passed"]) != 12:
        raise AssertionError("rejection matrix not 12/12")

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_GENERIC_SOURCE_ADAPTER_CONFORMANCE_HARNESS_RECEIPT_V1",
        "gate_id": GATE_ID,
        "conformance_schema_sha256": sha256_file(str(SCHEMA_PATH)),
        "verified_tested_interface_pins": verified_pins,
        "generic_adapter_predecessor_receipt_sha256": previous_sha,
        "existing_binding_conformance": conformance,
        "three_of_three_conformant": all(x["conformant"] for x in conformance.values()),
        "three_of_three_receipt_equal": all(
            x["receipt_equal_to_generic_contract_baseline"]
            for x in conformance.values()
        ),
        "rejection_matrix": {
            "count": len(rejection),
            "pass": sum(1 for x in rejection if x["passed"]),
            "rows": rejection,
        },
        "provider_specific_domain_math": False,
        "new_source_ingest": False,
        "fences": SCHEMA["fences"],
        "verdict":
            "PASS_BOUNDED_GENERIC_SOURCE_ADAPTER_CONFORMANCE_3_OF_3__REJECT_12_OF_12",
    }


def write_receipt() -> tuple[dict[str, Any], str]:
    receipt = run_harness()
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    OUT_PATH.write_text(canonical, encoding="utf-8")
    sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return receipt, sha


if __name__ == "__main__":
    receipt, sha = write_receipt()
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    print("GENERIC_SOURCE_ADAPTER_CONFORMANCE_RECEIPT_SHA256=" + sha)
