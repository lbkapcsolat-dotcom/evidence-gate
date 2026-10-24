from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import planetary_resource_generic_source_adapter_gate_v1 as generic_gate
import planetary_resource_generic_source_adapter_conformance_v1 as conformance


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__SOURCE_ADAPTER_SUBSYSTEM_FREEZE_AND_RETURN_TO_CORE_V1"
)
MANIFEST_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__SOURCE_ADAPTER_SUBSYSTEM_FREEZE.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__SOURCE_ADAPTER_SUBSYSTEM_FREEZE_AND_RETURN_TO_CORE_RECEIPT.json"
)


def sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha256(payload: dict[str, Any]) -> str:
    body=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load_manifest() -> dict[str, Any]:
    m=json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if m["gate_id"] != GATE_ID:
        raise AssertionError("freeze gate id mismatch")
    if m["subsystem_status"] != "FROZEN_BOUNDED_RETURN_TO_CORE":
        raise AssertionError("subsystem is not frozen")
    if m["future_provider_path"] != ["BINDING","CONFORMANCE","EMPIRICAL_ADMISSION"]:
        raise AssertionError("future provider path changed")
    if m["crude_oil"]["canary_status"] != "DEFERRED":
        raise AssertionError("crude-oil canary must remain deferred")
    if m["crude_oil"]["provider_implementation_now"] is not False:
        raise AssertionError("crude-oil provider implementation must be stopped")
    if m["return_to_core"]["provider_subsystem_work_now"] != "STOP":
        raise AssertionError("provider subsystem work must stop")
    if m["return_to_core"]["next_work_domain"] != "PLANETARY_RESOURCE_CORE":
        raise AssertionError("return target is not planetary resource core")
    if any(m["fences"].values()):
        raise AssertionError(f"scope fence enabled unexpectedly: {m['fences']!r}")
    return m


def verify_tested_interface_pins(m: dict[str, Any]) -> dict[str,str]:
    pins=m["tested_interface_pins"]
    files={
        "generic_adapter_contract_sha256":
            "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__GENERIC_SOURCE_ADAPTER_CONTRACT.json",
        "generic_adapter_implementation_sha256":
            "planetary_resource_generic_source_adapter_v1.py",
        "generic_bindings_sha256":
            "planetary_resource_generic_source_bindings_v1.py",
        "generic_gate_sha256":
            "planetary_resource_generic_source_adapter_gate_v1.py",
        "conformance_schema_sha256":
            "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__GENERIC_SOURCE_ADAPTER_CONFORMANCE_SCHEMA.json",
        "conformance_harness_sha256":
            "planetary_resource_generic_source_adapter_conformance_v1.py",
        "conformance_tests_sha256":
            "test_planetary_resource_generic_source_adapter_conformance_v1.py",
    }
    out={}
    for key,path in files.items():
        got=sha256_file(path)
        want=pins[key]
        if got != want:
            raise AssertionError(f"{key} changed: {got} != {want}")
        out[key]=got

    generic_receipt=generic_gate.run_gate()
    got_generic=canonical_sha256(generic_receipt)
    if got_generic != pins["generic_adapter_receipt_sha256"]:
        raise AssertionError(
            f"generic adapter receipt changed: {got_generic} != {pins['generic_adapter_receipt_sha256']}"
        )
    out["generic_adapter_receipt_sha256"]=got_generic

    conform_receipt=conformance.run_harness()
    got_conform=canonical_sha256(conform_receipt)
    if got_conform != pins["conformance_receipt_sha256"]:
        raise AssertionError(
            f"conformance receipt changed: {got_conform} != {pins['conformance_receipt_sha256']}"
        )
    out["conformance_receipt_sha256"]=got_conform
    return out


def verify_proven_bindings(m: dict[str, Any]) -> dict[str,Any]:
    raw_files={
        "water":"sources/environment_agency/1100TH_flow_mean_15min_2026-10-01T21-30Z.json",
        "electricity":"sources/elexon/INDO_2026-10-01T22-00Z.json",
        "natural_gas":"sources/entsog/DE-TSO-0005_ITP-00188_entry_physical_flow_2026-10-01T21-22Z.html",
    }
    generic_receipt=generic_gate.run_gate()
    conformance_receipt=conformance.run_harness()
    key_map={"water":"water","electricity":"electricity","natural_gas":"gas"}

    out={}
    for name,row in m["proven_bindings"].items():
        got_raw=sha256_file(raw_files[name])
        if got_raw != row["raw_sha256"]:
            raise AssertionError(f"{name} raw source changed")
        generic_name=key_map[name]
        if not generic_receipt["receipt_equality"][generic_name]["equal"]:
            raise AssertionError(f"{name} generic receipt equality lost")
        if not conformance_receipt["existing_binding_conformance"][generic_name]["conformant"]:
            raise AssertionError(f"{name} conformance lost")
        if not conformance_receipt["existing_binding_conformance"][generic_name]["receipt_equal_to_generic_contract_baseline"]:
            raise AssertionError(f"{name} conformance receipt equality lost")
        out[name]={
            "provider":row["provider"],
            "variable_id":row["variable_id"],
            "raw_sha256":got_raw,
            "status":row["status"],
            "generic_receipt_equal":True,
            "conformant":True,
        }
    return out


def run_freeze() -> dict[str,Any]:
    m=load_manifest()
    verified_pins=verify_tested_interface_pins(m)
    bindings=verify_proven_bindings(m)

    rules=m["future_provider_rules"]
    required_true=(
        "no_direct_empirical_admission_without_conformance",
        "no_provider_specific_domain_math",
        "no_provider_specific_physics_engine",
        "no_silent_unit_or_basis_conversion",
        "no_unpinned_raw_source_bytes",
    )
    for key in required_true:
        if rules[key] is not True:
            raise AssertionError(f"future provider rule disabled: {key}")

    return {
        "schema_version":"EQUILIBRIUM_PRS_SOURCE_ADAPTER_SUBSYSTEM_FREEZE_RECEIPT_V1",
        "gate_id":GATE_ID,
        "freeze_manifest_sha256":sha256_file(str(MANIFEST_PATH)),
        "subsystem_status":m["subsystem_status"],
        "verified_tested_interface_pins":verified_pins,
        "proven_bindings":bindings,
        "proven_binding_count":len(bindings),
        "future_provider_path":m["future_provider_path"],
        "future_provider_rules":rules,
        "crude_oil":m["crude_oil"],
        "return_to_core":m["return_to_core"],
        "new_source_ingest":False,
        "fences":m["fences"],
        "verdict":m["verdict_target"],
    }


def write_receipt() -> tuple[dict[str,Any],str]:
    receipt=run_freeze()
    canonical=json.dumps(receipt,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n"
    OUT_PATH.write_text(canonical,encoding="utf-8")
    sha=hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return receipt,sha


if __name__=="__main__":
    receipt,sha=write_receipt()
    print(json.dumps(receipt,sort_keys=True,separators=(",",":"),ensure_ascii=False))
    print("SOURCE_ADAPTER_SUBSYSTEM_FREEZE_RECEIPT_SHA256="+sha)
