from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_end_to_end_uncertainty_gate_v1 as e2e_gate
import planetary_resource_end_to_end_uncertainty_v1 as e2e
import planetary_resource_post_self_loss_core_gap_review_v1 as post_review
import planetary_resource_process_coefficient_uncertainty_v1 as pc
import planetary_resource_process_typed_dimensional_closure_gate_v1 as typed_gate
import planetary_resource_storage_self_loss_typed_gate_v1 as self_loss_gate


GATE_ID=(
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PROCESS_COEFFICIENT_UNCERTAINTY_PROPAGATION_V1"
)
CONTRACT_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PROCESS_COEFFICIENT_UNCERTAINTY_PROPAGATION.json"
)
OUT_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__PROCESS_COEFFICIENT_UNCERTAINTY_PROPAGATION_RECEIPT.json"
)


def sha256_file(path:str)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha256(obj:Any)->str:
    body=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def run_gate()->dict[str,Any]:
    contract=json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("coefficient uncertainty contract mismatch")

    pins=contract["predecessor_pins"]
    file_checks={
        "python_core_sha256":"equilibrium_planetary_resource_core_v1.py",
        "cpp_kernel_sha256":"planetary_resource_cpp_kernel_v1.cpp",
        "typed_process_contract_sha256":
            "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__PROCESS_COUPLING_TYPED_DIMENSIONAL_CLOSURE.json",
        "typed_process_module_sha256":
            "planetary_resource_process_typed_dimensional_closure_v1.py",
        "e2e_uncertainty_contract_sha256":
            "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__END_TO_END_UNCERTAINTY_PROPAGATION.json",
        "e2e_uncertainty_module_sha256":
            "planetary_resource_end_to_end_uncertainty_v1.py",
        "typed_self_loss_contract_sha256":
            "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__STORAGE_SELF_LOSS_TYPED_PHYSICAL_RATE.json",
        "typed_self_loss_module_sha256":
            "planetary_resource_storage_self_loss_typed_v1.py",
    }
    observed_pins={}
    for key,path in file_checks.items():
        got=sha256_file(path)
        if got != pins[key]:
            raise AssertionError(f"predecessor pin changed: {key} {got} != {pins[key]}")
        observed_pins[key]=got

    typed_sha=canonical_sha256(typed_gate.run_gate())
    if typed_sha != pins["typed_process_receipt_sha256"]:
        raise AssertionError("typed-process receipt changed")
    observed_pins["typed_process_receipt_sha256"]=typed_sha

    e2e_sha=canonical_sha256(e2e_gate.run_gate())
    if e2e_sha != pins["e2e_uncertainty_receipt_sha256"]:
        raise AssertionError("end-to-end uncertainty receipt changed")
    observed_pins["e2e_uncertainty_receipt_sha256"]=e2e_sha

    self_loss_sha=canonical_sha256(self_loss_gate.run_gate())
    if self_loss_sha != pins["typed_self_loss_receipt_sha256"]:
        raise AssertionError("typed self-loss receipt changed")
    observed_pins["typed_self_loss_receipt_sha256"]=self_loss_sha

    post_sha=canonical_sha256(post_review.run_review())
    if post_sha != pins["post_self_loss_review_receipt_sha256"]:
        raise AssertionError("post-self-loss review receipt changed")
    observed_pins["post_self_loss_review_receipt_sha256"]=post_sha

    matrix=core.run_validation_matrix()
    if len(matrix)!=40 or sum(1 for x in matrix if x.passed)!=40:
        raise AssertionError("legacy Python core no longer 40/40")

    layer=core.ResourceLayer.ELECTRICITY
    nodes=core.nodes_for(layer,["E0"])
    exact_activity=core.QualifiedValue(
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
    interval_coeff=pc.UncertainProcessManifest(
        "P","PHYSICAL_CONVERSION","activity",
        (
            pc.UncertainProcessCoefficient(
                layer,"E0",core.F(3),
                core.IntervalUncertainty(core.F(-1),core.F(1)),
                "EV:coef","W_e/activity",
            ),
        ),
        "SRC","METHOD",
    )
    interval_out=pc.process_coupling_with_coefficient_uncertainty(
        interval_coeff,exact_activity,nodes,target_layer=layer,interval_id="T0"
    )["E0"]
    if interval_out.value != core.F(6):
        raise AssertionError("coefficient uncertainty nominal output mismatch")
    if not isinstance(interval_out.uncertainty,core.IntervalUncertainty):
        raise AssertionError("coefficient interval uncertainty lost")
    if (interval_out.uncertainty.lower,interval_out.uncertainty.upper) != (
        core.F(-2),core.F(2)
    ):
        raise AssertionError("coefficient interval uncertainty mismatch")
    if interval_out.status is not core.EpistemicStatus.IMPUTED:
        raise AssertionError("activity epistemic status not preserved")
    if interval_out.space is not core.ValueSpace.PHYSICAL:
        raise AssertionError("value space not preserved")
    for ev in ("EV:activity","EV:coef","SRC","METHOD"):
        if ev not in interval_out.evidence_refs:
            raise AssertionError(f"missing preserved evidence {ev}")

    balance=e2e.resource_balance_with_uncertainty(
        layer=layer,interval_id="T0",nodes=nodes,internal_edges=[],B=[[]],
        production=[core.qv(0,layer)],demand=[core.qv(6,layer)],
        loss=[core.qv(0,layer)],internal_flow=[],
        process_contribution={"E0":interval_out},
    )["E0"]
    if balance.value != 0:
        raise AssertionError("coefficient uncertainty changed nominal balance")
    if not isinstance(balance.uncertainty,core.IntervalUncertainty):
        raise AssertionError("coefficient uncertainty did not reach E2E balance")
    if (balance.uncertainty.lower,balance.uncertainty.upper) != (
        core.F(-2),core.F(2)
    ):
        raise AssertionError("E2E coefficient uncertainty mismatch")

    moment_coeff=pc.UncertainProcessManifest(
        "PM","PHYSICAL_CONVERSION","activity",
        (
            pc.UncertainProcessCoefficient(
                layer,"E0",core.F(3),
                core.MomentUncertainty(core.F(0),core.F(4)),
                "EV:coef-moment","W_e/activity",
            ),
        ),
        "SRC","METHOD",
    )
    moment_out=pc.process_coupling_with_coefficient_uncertainty(
        moment_coeff,exact_activity,nodes,target_layer=layer,interval_id="T0"
    )["E0"]
    if moment_out.uncertainty.variance != core.F(16):
        raise AssertionError("coefficient variance was silently zeroed")

    uncertain_activity=core.QualifiedValue(
        core.F(2),
        core.UnitTag(layer,core.QuantityKind.DIMENSIONLESS,"activity"),
        "T0",
        core.EpistemicStatus.OBSERVED,
        core.MomentUncertainty(core.F(0),core.F(1)),
    )
    covariance_required=False
    try:
        pc.process_coupling_with_coefficient_uncertainty(
            moment_coeff,uncertain_activity,nodes,
            target_layer=layer,interval_id="T0"
        )
    except core.HoldError as exc:
        covariance_required=exc.code is core.HoldCode.HOLD_COVARIANCE_REQUIRED
    if not covariance_required:
        raise AssertionError("dual-moment coefficient path did not require joint evidence")

    empirical_coeff=pc.UncertainProcessManifest(
        "PE","PHYSICAL_CONVERSION","activity",
        (
            pc.UncertainProcessCoefficient(
                layer,"E0",core.F(3),
                core.EmpiricalUncertainty(
                    (core.F("-0.5"),core.F("0.5")),"A"
                ),
                "EV:coef-emp","W_e/activity",
            ),
        ),
        "SRC","METHOD",
    )
    empirical_activity=core.QualifiedValue(
        core.F(2),
        core.UnitTag(layer,core.QuantityKind.DIMENSIONLESS,"activity"),
        "T0",
        uncertainty=core.EmpiricalUncertainty((core.F(-1),core.F(1)),"A"),
    )
    alignment_required=False
    try:
        pc.process_coupling_with_coefficient_uncertainty(
            empirical_coeff,empirical_activity,nodes,
            target_layer=layer,interval_id="T0"
        )
    except core.HoldError as exc:
        alignment_required=exc.code is core.HoldCode.HOLD_SAMPLE_ALIGNMENT_REQUIRED
    if not alignment_required:
        raise AssertionError("dual empirical coefficient path did not require alignment")

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_PROCESS_COEFFICIENT_UNCERTAINTY_PROPAGATION_RECEIPT_V1",
        "gate_id":GATE_ID,
        "contract_sha256":sha256_file(str(CONTRACT_PATH)),
        "successor_module_sha256":
            sha256_file("planetary_resource_process_coefficient_uncertainty_v1.py"),
        "verified_predecessor_pins":observed_pins,
        "legacy_python_matrix":{"count":40,"pass":40},
        "coefficient_interval_example":{
            "nominal_value":str(interval_out.value),
            "uncertainty_lower":str(interval_out.uncertainty.lower),
            "uncertainty_upper":str(interval_out.uncertainty.upper),
            "status":interval_out.status.value,
            "value_space":interval_out.space.value,
            "evidence_refs":list(interval_out.evidence_refs),
        },
        "e2e_balance_example":{
            "nominal_residual":str(balance.value),
            "uncertainty_lower":str(balance.uncertainty.lower),
            "uncertainty_upper":str(balance.uncertainty.upper),
        },
        "coefficient_moment_variance_preserved":str(moment_out.uncertainty.variance),
        "no_zero_coefficient_variance_assumption":True,
        "dual_moment_requires_covariance_and_joint_moments":True,
        "empirical_requires_sample_alignment":True,
        "silent_coefficient_uncertainty_loss_rejected":True,
        "coefficient_evidence_preserved":True,
        "dimensional_unit_check_preserved":True,
        "activity_metadata_preserved":True,
        "value_space_preserved":True,
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
    print("PROCESS_COEFFICIENT_UNCERTAINTY_RECEIPT_SHA256="+sha)
