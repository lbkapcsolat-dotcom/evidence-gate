from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_process_coefficient_uncertainty_gate_v1 as coefficient_gate
import planetary_resource_process_coefficient_validity_gate_v1 as validity_gate
import planetary_resource_process_coefficient_validity_v1 as pv
import planetary_resource_process_manifest_version_v1 as mv


GATE_ID=(
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PROCESS_MANIFEST_VERSION_ENFORCEMENT_V1"
)
CONTRACT_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PROCESS_MANIFEST_VERSION_ENFORCEMENT.json"
)
OUT_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PROCESS_MANIFEST_VERSION_ENFORCEMENT_RECEIPT.json"
)


def sha256_file(path:str)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha256(obj:Any)->str:
    body=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _expect_hold(code:str,fn)->dict[str,Any]:
    try:
        fn()
    except mv.ProcessManifestVersionHold as exc:
        if exc.code != code:
            raise AssertionError(f"expected {code}, got {exc.code}")
        return {"expected":code,"observed":exc.code,"passed":True}
    raise AssertionError(f"expected {code}, got PASS")


def run_gate()->dict[str,Any]:
    contract=json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("manifest-version contract mismatch")

    pins=contract["predecessor_pins"]
    observed={
        "python_core_sha256":sha256_file("equilibrium_planetary_resource_core_v1.py"),
        "cpp_kernel_sha256":sha256_file("planetary_resource_cpp_kernel_v1.cpp"),
        "coefficient_uncertainty_contract_sha256":
            sha256_file("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__PROCESS_COEFFICIENT_UNCERTAINTY_PROPAGATION.json"),
        "coefficient_uncertainty_module_sha256":
            sha256_file("planetary_resource_process_coefficient_uncertainty_v1.py"),
        "coefficient_validity_contract_sha256":
            sha256_file("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__PROCESS_COEFFICIENT_VALIDITY_INTERVAL.json"),
        "coefficient_validity_module_sha256":
            sha256_file("planetary_resource_process_coefficient_validity_v1.py"),
        "coefficient_validity_gate_sha256":
            sha256_file("planetary_resource_process_coefficient_validity_gate_v1.py"),
    }
    for key,got in observed.items():
        if got != pins[key]:
            raise AssertionError(f"predecessor pin changed: {key} {got} != {pins[key]}")

    coefficient_receipt_sha=canonical_sha256(coefficient_gate.run_gate())
    if coefficient_receipt_sha != pins["coefficient_uncertainty_receipt_sha256"]:
        raise AssertionError("coefficient uncertainty receipt changed")
    observed["coefficient_uncertainty_receipt_sha256"]=coefficient_receipt_sha

    validity_receipt_sha=canonical_sha256(validity_gate.run_gate())
    if validity_receipt_sha != pins["coefficient_validity_receipt_sha256"]:
        raise AssertionError("coefficient validity receipt changed")
    observed["coefficient_validity_receipt_sha256"]=validity_receipt_sha

    matrix=core.run_validation_matrix()
    if len(matrix)!=40 or sum(1 for x in matrix if x.passed)!=40:
        raise AssertionError("legacy Python core no longer 40/40")

    layer=core.ResourceLayer.ELECTRICITY
    nodes=core.nodes_for(layer,["E0"],version="V1")
    activity=core.QualifiedValue(
        core.F(2),
        core.UnitTag(layer,core.QuantityKind.DIMENSIONLESS,"activity"),
        "T0",
        core.EpistemicStatus.IMPUTED,
        core.ExactUncertainty(),
        ("EV:activity",),
        ("activity:source",),
        (),
        "fresh",
        core.ValueSpace.PHYSICAL,
    )
    row=pv.ValidityBoundedProcessCoefficient(
        layer,"E0",core.F(3),
        core.IntervalUncertainty(core.F(-1),core.F(1)),
        "EV:coef","W_e/activity",
        "2026-10-01T00:00:00Z","2026-10-03T00:00:00Z",
    )
    process=pv.ValidityBoundedProcessManifest(
        "P","PHYSICAL_CONVERSION","activity",(row,),"SRC","METHOD","V1"
    )
    requested=pv.RequestedInterval(
        "T0","2026-10-02T10:00:00Z","2026-10-02T11:00:00Z"
    )
    admitted=mv.process_coupling_with_manifest_version(
        process,activity,nodes,
        target_layer=layer,
        requested_interval=requested,
        expected_process_manifest_version="V1",
    )["E0"]

    if admitted.value != core.F(6):
        raise AssertionError("manifest-version successor changed nominal output")
    if not isinstance(admitted.uncertainty,core.IntervalUncertainty):
        raise AssertionError("coefficient uncertainty lost")
    if (admitted.uncertainty.lower,admitted.uncertainty.upper) != (
        core.F(-2),core.F(2)
    ):
        raise AssertionError("coefficient uncertainty changed")
    if admitted.status is not core.EpistemicStatus.IMPUTED:
        raise AssertionError("activity status not preserved")
    if admitted.space is not core.ValueSpace.PHYSICAL:
        raise AssertionError("value space not preserved")
    for ev in ("EV:activity","EV:coef","SRC","METHOD"):
        if ev not in admitted.evidence_refs:
            raise AssertionError(f"missing evidence {ev}")
    if not any(x.startswith("coefficient_validity:") for x in admitted.transform_chain):
        raise AssertionError("coefficient validity chain lost")

    process_v99=pv.ValidityBoundedProcessManifest(
        "P","PHYSICAL_CONVERSION","activity",(row,),"SRC","METHOD","V99"
    )
    process_mismatch=_expect_hold(
        "HOLD_PROCESS_MANIFEST_VERSION_MISMATCH",
        lambda:mv.process_coupling_with_manifest_version(
            process_v99,activity,nodes,
            target_layer=layer,
            requested_interval=requested,
            expected_process_manifest_version="V1",
        ),
    )

    nodes_v2=core.nodes_for(layer,["E0"],version="V2")
    node_mismatch=_expect_hold(
        "HOLD_TARGET_NODE_MANIFEST_VERSION_MISMATCH",
        lambda:mv.process_coupling_with_manifest_version(
            process,activity,nodes_v2,
            target_layer=layer,
            requested_interval=requested,
            expected_process_manifest_version="V1",
        ),
    )

    missing_expected=_expect_hold(
        "HOLD_PROCESS_MANIFEST_VERSION_REQUIRED",
        lambda:mv.process_coupling_with_manifest_version(
            process,activity,nodes,
            target_layer=layer,
            requested_interval=requested,
            expected_process_manifest_version="",
        ),
    )

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_PROCESS_MANIFEST_VERSION_ENFORCEMENT_RECEIPT_V1",
        "gate_id":GATE_ID,
        "contract_sha256":sha256_file(str(CONTRACT_PATH)),
        "successor_module_sha256":
            sha256_file("planetary_resource_process_manifest_version_v1.py"),
        "verified_predecessor_pins":observed,
        "legacy_python_matrix":{"count":40,"pass":40},
        "admitted_example":{
            "process_manifest_version":"V1",
            "expected_process_manifest_version":"V1",
            "target_node_manifest_version":"V1",
            "nominal_value":str(admitted.value),
            "uncertainty_lower":str(admitted.uncertainty.lower),
            "uncertainty_upper":str(admitted.uncertainty.upper),
            "status":admitted.status.value,
            "value_space":admitted.space.value,
            "evidence_refs":list(admitted.evidence_refs),
        },
        "rejections":{
            "process_manifest_version_mismatch":process_mismatch,
            "target_node_manifest_version_mismatch":node_mismatch,
            "missing_expected_version":missing_expected,
        },
        "no_implicit_version_fallback":True,
        "coefficient_validity_preserved":True,
        "coefficient_uncertainty_preserved":True,
        "dimensional_unit_check_preserved":True,
        "evidence_and_activity_metadata_preserved":True,
        "provider_work":False,
        "new_source_ingest":False,
        "fences":contract["fences"],
        "implementation_mode":contract["implementation_mode"],
        "verdict":contract["verdict_target"],
    }


def write_receipt():
    receipt=run_gate()
    body=json.dumps(receipt,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n"
    OUT_PATH.write_text(body,encoding="utf-8")
    sha=hashlib.sha256(body.encode("utf-8")).hexdigest()
    return receipt,sha


if __name__=="__main__":
    receipt,sha=write_receipt()
    print(json.dumps(receipt,sort_keys=True,separators=(",",":"),ensure_ascii=False))
    print("PROCESS_MANIFEST_VERSION_RECEIPT_SHA256="+sha)
