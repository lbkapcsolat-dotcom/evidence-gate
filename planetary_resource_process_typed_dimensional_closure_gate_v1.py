from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Any

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_core_reentry_gap_review_v1 as gap_review
import planetary_resource_process_typed_dimensional_closure_v1 as typed
import planetary_resource_source_adapter_subsystem_freeze_v1 as adapter_freeze


GATE_ID=(
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PROCESS_COUPLING_TYPED_DIMENSIONAL_CLOSURE_V1"
)
CONTRACT_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PROCESS_COUPLING_TYPED_DIMENSIONAL_CLOSURE.json"
)
OUT_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PROCESS_COUPLING_TYPED_DIMENSIONAL_CLOSURE_RECEIPT.json"
)


def sha256_file(path:str)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha256(obj:Any)->str:
    body=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _expect_typed_hold(code:str,fn)->dict[str,Any]:
    try:
        fn()
    except typed.TypedProcessHold as exc:
        if exc.code != code:
            raise AssertionError(f"expected {code}, got {exc.code}")
        return {"expected":code,"observed":exc.code,"passed":True}
    raise AssertionError(f"expected {code}, got PASS")


def run_gate()->dict[str,Any]:
    contract=json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("typed closure contract mismatch")

    pins=contract["predecessor_pins"]
    frozen={
        "python_core_sha256":sha256_file("equilibrium_planetary_resource_core_v1.py"),
        "cpp_kernel_sha256":sha256_file("planetary_resource_cpp_kernel_v1.cpp"),
    }
    if frozen["python_core_sha256"] != pins["python_core_sha256"]:
        raise AssertionError("pinned Python core mutated")
    if frozen["cpp_kernel_sha256"] != pins["cpp_kernel_sha256"]:
        raise AssertionError("pinned C++ kernel mutated")

    review_sha=canonical_sha256(gap_review.run_review())
    if review_sha != pins["core_reentry_review_receipt_sha256"]:
        raise AssertionError("core reentry review receipt changed")
    freeze_sha=canonical_sha256(adapter_freeze.run_freeze())
    if freeze_sha != pins["source_adapter_freeze_receipt_sha256"]:
        raise AssertionError("source adapter freeze receipt changed")

    matrix=core.run_validation_matrix()
    if len(matrix) != 40 or sum(1 for x in matrix if x.passed) != 40:
        raise AssertionError("legacy Python matrix is not 40/40")

    layer=core.ResourceLayer.ELECTRICITY
    nodes=core.nodes_for(layer,["E0"])
    activity=core.QualifiedValue(
        core.F(2),
        core.UnitTag(layer,core.QuantityKind.DIMENSIONLESS,"activity"),
        "T0",
        core.EpistemicStatus.IMPUTED,
        core.IntervalUncertainty(core.F(1),core.F(3)),
        ("EV:activity",),
        ("imputation:model-x",),
        ("HOLD:carry",),
        "fresh",
        core.ValueSpace.PHYSICAL,
    )
    process=core.ProcessManifest(
        "P",
        "PHYSICAL_CONVERSION",
        "activity",
        (core.ProcessCoefficient(layer,"E0",core.F(3),"EV:coef","W_e/activity"),),
        "SRC:process",
        "METHOD:process",
    )
    contribution=typed.process_coupling_typed(
        process,activity,nodes,target_layer=layer,interval_id="T0"
    )["E0"]

    preserved={
        "value":str(contribution.value),
        "unit_symbol":contribution.unit.symbol,
        "status":contribution.status.value,
        "uncertainty_type":type(contribution.uncertainty).__name__,
        "uncertainty_lower":str(contribution.uncertainty.lower),
        "uncertainty_upper":str(contribution.uncertainty.upper),
        "evidence_refs":list(contribution.evidence_refs),
        "hold_codes":list(contribution.hold_codes),
        "freshness":contribution.freshness,
        "value_space":contribution.space.value,
    }
    if preserved["value"] != "6":
        raise AssertionError("typed contribution value mismatch")
    if preserved["unit_symbol"] != "W_e":
        raise AssertionError("target canonical unit mismatch")
    if preserved["status"] != "IMPUTED":
        raise AssertionError("epistemic status not preserved")
    if preserved["value_space"] != "PHYSICAL":
        raise AssertionError("value space not preserved")
    if preserved["uncertainty_type"] != "IntervalUncertainty":
        raise AssertionError("uncertainty not preserved/scaled")
    for ev in ("EV:activity","EV:coef","SRC:process","METHOD:process"):
        if ev not in contribution.evidence_refs:
            raise AssertionError(f"missing evidence ref {ev}")

    wrong_activity=core.ProcessManifest(
        "P","PHYSICAL_CONVERSION","declared",
        (core.ProcessCoefficient(layer,"E0",core.F(1),"EV","W_e/declared"),),
        "SRC","METHOD",
    )
    wrong_coeff=core.ProcessManifest(
        "P","PHYSICAL_CONVERSION","activity",
        (core.ProcessCoefficient(layer,"E0",core.F(1),"EV","m3/s/activity"),),
        "SRC","METHOD",
    )
    observed_rejections={
        "activity_unit_mismatch":_expect_typed_hold(
            "HOLD_PROCESS_ACTIVITY_UNIT_MISMATCH",
            lambda:typed.process_coupling_typed(
                wrong_activity,activity,nodes,target_layer=layer,interval_id="T0"
            ),
        ),
        "coefficient_unit_mismatch":_expect_typed_hold(
            "HOLD_PROCESS_COEFFICIENT_DIMENSION_MISMATCH",
            lambda:typed.process_coupling_typed(
                wrong_coeff,activity,nodes,target_layer=layer,interval_id="T0"
            ),
        ),
        "raw_fraction_injection":_expect_typed_hold(
            "HOLD_PROCESS_TYPED_VALUE_REQUIRED",
            lambda:typed.resource_balance_residual_typed(
                **core.fixture_f01(),process_contribution={"E0":core.F(1)}
            ),
        ),
    }

    balance_args=dict(
        layer=layer,interval_id="T0",nodes=nodes,internal_edges=[],B=[[]],
        production=[core.qv(0,layer)],
        demand=[core.qv(6,layer)],
        loss=[core.qv(0,layer)],
        internal_flow=[],
    )
    closed=typed.resource_balance_residual_typed(
        **balance_args,process_contribution={"E0":contribution}
    )
    if closed != {"E0":core.F(0)}:
        raise AssertionError("typed process balance did not close")

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_PROCESS_COUPLING_TYPED_DIMENSIONAL_CLOSURE_RECEIPT_V1",
        "gate_id":GATE_ID,
        "contract_sha256":sha256_file(str(CONTRACT_PATH)),
        "successor_module_sha256":
            sha256_file("planetary_resource_process_typed_dimensional_closure_v1.py"),
        "verified_predecessor_pins":{
            **frozen,
            "core_reentry_review_receipt_sha256":review_sha,
            "source_adapter_freeze_receipt_sha256":freeze_sha,
        },
        "legacy_python_matrix":{"count":40,"pass":40},
        "typed_contribution_metadata":preserved,
        "typed_balance_zero_residual":True,
        "rejections":observed_rejections,
        "raw_fraction_process_injection_rejected":True,
        "coefficient_unit_mismatch_rejected":True,
        "activity_unit_mismatch_rejected":True,
        "target_canonical_rate_compatibility":True,
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
    print("PROCESS_TYPED_DIMENSIONAL_CLOSURE_RECEIPT_SHA256="+sha)
