from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_end_to_end_uncertainty_v1 as e2e
import planetary_resource_process_typed_dimensional_closure_gate_v1 as typed_gate
import planetary_resource_source_adapter_subsystem_freeze_v1 as adapter_freeze


GATE_ID=(
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__END_TO_END_UNCERTAINTY_PROPAGATION_V1"
)
CONTRACT_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__END_TO_END_UNCERTAINTY_PROPAGATION.json"
)
OUT_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__END_TO_END_UNCERTAINTY_PROPAGATION_RECEIPT.json"
)


def sha256_file(path:str)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha256(obj:Any)->str:
    body=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def run_gate()->dict[str,Any]:
    contract=json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("uncertainty contract gate mismatch")

    pins=contract["predecessor_pins"]
    observed_pins={
        "python_core_sha256":sha256_file("equilibrium_planetary_resource_core_v1.py"),
        "cpp_kernel_sha256":sha256_file("planetary_resource_cpp_kernel_v1.cpp"),
        "typed_process_contract_sha256":
            sha256_file("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__PROCESS_COUPLING_TYPED_DIMENSIONAL_CLOSURE.json"),
        "typed_process_module_sha256":
            sha256_file("planetary_resource_process_typed_dimensional_closure_v1.py"),
    }
    for key,got in observed_pins.items():
        if got != pins[key]:
            raise AssertionError(f"predecessor pin changed: {key} {got} != {pins[key]}")

    typed_receipt_sha=canonical_sha256(typed_gate.run_gate())
    if typed_receipt_sha != pins["typed_process_receipt_sha256"]:
        raise AssertionError("typed process receipt changed")

    freeze_sha=canonical_sha256(adapter_freeze.run_freeze())
    if freeze_sha != pins["source_adapter_freeze_receipt_sha256"]:
        raise AssertionError("adapter freeze receipt changed")

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
        core.IntervalUncertainty(core.F("-0.5"),core.F("0.5")),
        ("EV:activity",),
        ("imputation:p",),
        (),
        "fresh",
        core.ValueSpace.PHYSICAL,
    )
    process=core.ProcessManifest(
        "P","PHYSICAL_CONVERSION","activity",
        (core.ProcessCoefficient(layer,"E0",core.F(1),"EV:coef","W_e/activity"),),
        "SRC:process","METHOD:process",
    )
    import planetary_resource_process_typed_dimensional_closure_v1 as typed
    process_map=typed.process_coupling_typed(
        process,activity,nodes,target_layer=layer,interval_id="T0"
    )
    prod=core.qv(
        10,layer,
        uncertainty=core.IntervalUncertainty(core.F(-1),core.F(1)),
        evidence_refs=("EV:prod",),
    )
    demand=core.qv(12,layer)
    balance=e2e.resource_balance_with_uncertainty(
        layer=layer,interval_id="T0",nodes=nodes,internal_edges=[],B=[[]],
        production=[prod],demand=[demand],loss=[core.qv(0,layer)],
        internal_flow=[],process_contribution=process_map,
    )["E0"]
    if balance.value != 0:
        raise AssertionError("uncertainty balance nominal residual changed")
    if not isinstance(balance.uncertainty,core.IntervalUncertainty):
        raise AssertionError("typed process uncertainty not propagated")
    if (balance.uncertainty.lower,balance.uncertainty.upper) != (
        core.F("-1.5"),core.F("1.5")
    ):
        raise AssertionError("typed process balance uncertainty mismatch")
    if balance.status is not core.EpistemicStatus.IMPUTED:
        raise AssertionError("epistemic status not conservatively preserved")
    if balance.space is not core.ValueSpace.PHYSICAL:
        raise AssertionError("value space not preserved")
    for ev in ("EV:activity","EV:coef","EV:prod","SRC:process","METHOD:process"):
        if ev not in balance.evidence_refs:
            raise AssertionError(f"missing balance evidence {ev}")

    p=core.qv(10,layer,uncertainty=core.MomentUncertainty(core.F(0),core.F(1)))
    d=core.qv(10,layer,uncertainty=core.MomentUncertainty(core.F(0),core.F(4)))
    covariance_required=False
    try:
        e2e.resource_balance_with_uncertainty(
            layer=layer,interval_id="T0",nodes=nodes,internal_edges=[],B=[[]],
            production=[p],demand=[d],loss=[core.qv(0,layer)],internal_flow=[],
        )
    except core.HoldError as exc:
        covariance_required=exc.code is core.HoldCode.HOLD_COVARIANCE_REQUIRED
    if not covariance_required:
        raise AssertionError("moment path did not require covariance")

    ep=core.qv(
        10,layer,
        uncertainty=core.EmpiricalUncertainty((core.F(-1),core.F(1)),"A")
    )
    ed=core.qv(
        10,layer,
        uncertainty=core.EmpiricalUncertainty((core.F("-0.5"),core.F("0.5")),"A")
    )
    alignment_required=False
    try:
        e2e.resource_balance_with_uncertainty(
            layer=layer,interval_id="T0",nodes=nodes,internal_edges=[],B=[[]],
            production=[ep],demand=[ed],loss=[core.qv(0,layer)],internal_flow=[],
        )
    except core.HoldError as exc:
        alignment_required=exc.code is core.HoldCode.HOLD_SAMPLE_ALIGNMENT_REQUIRED
    if not alignment_required:
        raise AssertionError("empirical path did not require sample alignment")

    st,tb,stock,charge,discharge=core.fixture_f06_storage()
    stock=core.QualifiedValue(
        stock.value,stock.unit,"T0",
        uncertainty=core.IntervalUncertainty(core.F(-2),core.F(2)),
        evidence_refs=("EV:stock",),
    )
    charge=core.QualifiedValue(
        charge.value,charge.unit,"T0",
        uncertainty=core.IntervalUncertainty(core.F(-1),core.F(1)),
        evidence_refs=("EV:charge",),
    )
    storage=e2e.storage_transition_with_uncertainty(st,tb,stock,charge,discharge)
    if not isinstance(storage.uncertainty,core.IntervalUncertainty):
        raise AssertionError("storage uncertainty was lost")
    if (storage.uncertainty.lower,storage.uncertainty.upper) != (
        core.F("-2.9"),core.F("2.9")
    ):
        raise AssertionError("storage uncertainty mismatch")
    if "EV:stock" not in storage.evidence_refs or "EV:charge" not in storage.evidence_refs:
        raise AssertionError("storage evidence refs not preserved")

    return {
        "schema_version":"EQUILIBRIUM_PRS_END_TO_END_UNCERTAINTY_PROPAGATION_RECEIPT_V1",
        "gate_id":GATE_ID,
        "contract_sha256":sha256_file(str(CONTRACT_PATH)),
        "successor_module_sha256":sha256_file("planetary_resource_end_to_end_uncertainty_v1.py"),
        "verified_predecessor_pins":{
            **observed_pins,
            "typed_process_receipt_sha256":typed_receipt_sha,
            "source_adapter_freeze_receipt_sha256":freeze_sha,
        },
        "legacy_python_matrix":{"count":40,"pass":40},
        "balance_interval_with_typed_process":{
            "nominal_value":"0",
            "uncertainty_lower":str(balance.uncertainty.lower),
            "uncertainty_upper":str(balance.uncertainty.upper),
            "status":balance.status.value,
            "value_space":balance.space.value,
            "evidence_refs":list(balance.evidence_refs),
        },
        "storage_interval":{
            "nominal_value":str(storage.value),
            "uncertainty_lower":str(storage.uncertainty.lower),
            "uncertainty_upper":str(storage.uncertainty.upper),
            "status":storage.status.value,
            "value_space":storage.space.value,
            "evidence_refs":list(storage.evidence_refs),
        },
        "moment_requires_covariance":True,
        "empirical_requires_sample_alignment":True,
        "no_zero_covariance_assumption":True,
        "raw_uncertainty_loss_rejected":True,
        "typed_process_uncertainty_included":True,
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
    print("END_TO_END_UNCERTAINTY_RECEIPT_SHA256="+sha)
