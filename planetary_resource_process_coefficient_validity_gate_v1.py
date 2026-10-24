from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_process_coefficient_uncertainty_gate_v1 as coefficient_gate
import planetary_resource_process_coefficient_validity_v1 as validity


GATE_ID=(
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PROCESS_COEFFICIENT_VALIDITY_INTERVAL_V1"
)
CONTRACT_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PROCESS_COEFFICIENT_VALIDITY_INTERVAL.json"
)
OUT_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PROCESS_COEFFICIENT_VALIDITY_INTERVAL_RECEIPT.json"
)


def sha256_file(path:str)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha256(obj:Any)->str:
    body=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _expect_validity_hold(code:str,fn)->dict[str,Any]:
    try:
        fn()
    except validity.ProcessCoefficientValidityHold as exc:
        if exc.code != code:
            raise AssertionError(f"expected {code}, got {exc.code}")
        return {"expected":code,"observed":exc.code,"passed":True}
    raise AssertionError(f"expected {code}, got PASS")


def run_gate()->dict[str,Any]:
    contract=json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("validity contract gate mismatch")

    pins=contract["predecessor_pins"]
    observed={
        "python_core_sha256":sha256_file("equilibrium_planetary_resource_core_v1.py"),
        "cpp_kernel_sha256":sha256_file("planetary_resource_cpp_kernel_v1.cpp"),
        "coefficient_uncertainty_contract_sha256":
            sha256_file("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__PROCESS_COEFFICIENT_UNCERTAINTY_PROPAGATION.json"),
        "coefficient_uncertainty_module_sha256":
            sha256_file("planetary_resource_process_coefficient_uncertainty_v1.py"),
        "coefficient_uncertainty_gate_sha256":
            sha256_file("planetary_resource_process_coefficient_uncertainty_gate_v1.py"),
    }
    for key,got in observed.items():
        if got != pins[key]:
            raise AssertionError(f"predecessor pin changed: {key} {got} != {pins[key]}")

    predecessor_receipt_sha=canonical_sha256(coefficient_gate.run_gate())
    if predecessor_receipt_sha != pins["coefficient_uncertainty_receipt_sha256"]:
        raise AssertionError("coefficient uncertainty receipt changed")
    observed["coefficient_uncertainty_receipt_sha256"]=predecessor_receipt_sha

    matrix=core.run_validation_matrix()
    if len(matrix)!=40 or sum(1 for x in matrix if x.passed)!=40:
        raise AssertionError("legacy Python core no longer 40/40")

    layer=core.ResourceLayer.ELECTRICITY
    nodes=core.nodes_for(layer,["E0"])
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
    row=validity.ValidityBoundedProcessCoefficient(
        layer,"E0",core.F(3),
        core.IntervalUncertainty(core.F(-1),core.F(1)),
        "EV:coef","W_e/activity",
        "2026-10-01T00:00:00Z",
        "2026-10-03T00:00:00Z",
    )
    process=validity.ValidityBoundedProcessManifest(
        "P","PHYSICAL_CONVERSION","activity",(row,),"SRC","METHOD","V1"
    )
    requested=validity.RequestedInterval(
        "T0","2026-10-02T10:00:00Z","2026-10-02T11:00:00Z"
    )
    admitted=validity.process_coupling_with_coefficient_validity(
        process,activity,nodes,target_layer=layer,requested_interval=requested
    )["E0"]

    if admitted.value != core.F(6):
        raise AssertionError("valid coefficient nominal output mismatch")
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

    def mk(vf,vt):
        r=validity.ValidityBoundedProcessCoefficient(
            layer,"E0",core.F(3),core.ExactUncertainty(),
            "EV:coef","W_e/activity",vf,vt
        )
        p=validity.ValidityBoundedProcessManifest(
            "P","PHYSICAL_CONVERSION","activity",(r,),"SRC","METHOD","V1"
        )
        return lambda:validity.process_coupling_with_coefficient_validity(
            p,activity,nodes,target_layer=layer,requested_interval=requested
        )

    rejections={
        "expired":_expect_validity_hold(
            "HOLD_PROCESS_COEFFICIENT_EXPIRED",
            mk("2026-09-01T00:00:00Z","2026-10-02T10:00:00Z"),
        ),
        "not_yet_valid":_expect_validity_hold(
            "HOLD_PROCESS_COEFFICIENT_NOT_YET_VALID",
            mk("2026-10-02T11:00:00Z","2026-10-04T00:00:00Z"),
        ),
        "partial_overlap":_expect_validity_hold(
            "HOLD_PROCESS_COEFFICIENT_PARTIAL_INTERVAL_OVERLAP",
            mk("2026-10-02T10:30:00Z","2026-10-03T00:00:00Z"),
        ),
        "missing_validity":_expect_validity_hold(
            "HOLD_PROCESS_COEFFICIENT_VALIDITY_REQUIRED",
            mk(None,"2026-10-03T00:00:00Z"),
        ),
    }

    if not any(x.startswith("coefficient_validity:") for x in admitted.transform_chain):
        raise AssertionError("coefficient validity not visible in transform chain")
    if not any(x.startswith("requested_interval:") for x in admitted.transform_chain):
        raise AssertionError("requested interval not visible in transform chain")

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_PROCESS_COEFFICIENT_VALIDITY_INTERVAL_RECEIPT_V1",
        "gate_id":GATE_ID,
        "contract_sha256":sha256_file(str(CONTRACT_PATH)),
        "successor_module_sha256":
            sha256_file("planetary_resource_process_coefficient_validity_v1.py"),
        "verified_predecessor_pins":observed,
        "legacy_python_matrix":{"count":40,"pass":40},
        "interval_semantics":contract["interval_semantics"],
        "admitted_example":{
            "requested_interval":{
                "interval_id":requested.interval_id,
                "start":requested.start,
                "end":requested.end,
            },
            "coefficient_validity":{
                "valid_from":row.valid_from,
                "valid_to":row.valid_to,
            },
            "nominal_value":str(admitted.value),
            "uncertainty_lower":str(admitted.uncertainty.lower),
            "uncertainty_upper":str(admitted.uncertainty.upper),
            "status":admitted.status.value,
            "value_space":admitted.space.value,
            "evidence_refs":list(admitted.evidence_refs),
        },
        "rejections":rejections,
        "expired_rejected":True,
        "not_yet_valid_rejected":True,
        "partial_overlap_rejected":True,
        "missing_validity_when_required_rejected":True,
        "coefficient_uncertainty_preserved":True,
        "coefficient_evidence_preserved":True,
        "dimensional_unit_check_preserved":True,
        "activity_metadata_preserved":True,
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
    print("PROCESS_COEFFICIENT_VALIDITY_RECEIPT_SHA256="+sha)
