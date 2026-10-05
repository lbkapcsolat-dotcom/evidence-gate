from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_end_to_end_uncertainty_gate_v1 as e2e_gate
import planetary_resource_post_uncertainty_core_gap_review_v1 as post_review
import planetary_resource_process_typed_dimensional_closure_gate_v1 as typed_gate
import planetary_resource_storage_self_loss_typed_v1 as typed_loss


GATE_ID=(
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__STORAGE_SELF_LOSS_TYPED_PHYSICAL_RATE_V1"
)
CONTRACT_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__STORAGE_SELF_LOSS_TYPED_PHYSICAL_RATE.json"
)
OUT_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__STORAGE_SELF_LOSS_TYPED_PHYSICAL_RATE_RECEIPT.json"
)


def sha256_file(path:str)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha256(obj:Any)->str:
    body=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _expect_typed_hold(code:str,fn)->dict[str,Any]:
    try:
        fn()
    except typed_loss.TypedSelfLossHold as exc:
        if exc.code != code:
            raise AssertionError(f"expected {code}, got {exc.code}")
        return {"expected":code,"observed":exc.code,"passed":True}
    raise AssertionError(f"expected {code}, got PASS")


def _expect_core_hold(code:core.HoldCode,fn)->dict[str,Any]:
    try:
        fn()
    except core.HoldError as exc:
        if exc.code is not code:
            raise AssertionError(f"expected {code.value}, got {exc.code.value}")
        return {"expected":code.value,"observed":exc.code.value,"passed":True}
    raise AssertionError(f"expected {code.value}, got PASS")


def run_gate()->dict[str,Any]:
    contract=json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("typed self-loss contract mismatch")

    pins=contract["predecessor_pins"]
    observed_pins={
        "python_core_sha256":sha256_file("equilibrium_planetary_resource_core_v1.py"),
        "cpp_kernel_sha256":sha256_file("planetary_resource_cpp_kernel_v1.cpp"),
        "typed_process_module_sha256":
            sha256_file("planetary_resource_process_typed_dimensional_closure_v1.py"),
        "e2e_uncertainty_module_sha256":
            sha256_file("planetary_resource_end_to_end_uncertainty_v1.py"),
    }
    for key,got in observed_pins.items():
        if got != pins[key]:
            raise AssertionError(f"predecessor pin changed: {key} {got} != {pins[key]}")

    typed_receipt_sha=canonical_sha256(typed_gate.run_gate())
    if typed_receipt_sha != pins["typed_process_receipt_sha256"]:
        raise AssertionError("typed-process receipt changed")
    e2e_receipt_sha=canonical_sha256(e2e_gate.run_gate())
    if e2e_receipt_sha != pins["e2e_uncertainty_receipt_sha256"]:
        raise AssertionError("end-to-end uncertainty receipt changed")
    review_receipt_sha=canonical_sha256(post_review.run_review())
    if review_receipt_sha != pins["post_uncertainty_review_receipt_sha256"]:
        raise AssertionError("post-uncertainty review receipt changed")

    matrix=core.run_validation_matrix()
    if len(matrix)!=40 or sum(1 for x in matrix if x.passed)!=40:
        raise AssertionError("legacy Python matrix is not 40/40")

    st,tb,stock,charge,discharge=core.fixture_f06_storage()
    self_loss=core.qv(
        1,
        st.layer,
        interval_id=tb.interval_id,
        status=core.EpistemicStatus.IMPUTED,
        uncertainty=core.IntervalUncertainty(core.F("-0.5"),core.F("0.5")),
        evidence_refs=("EV:self-loss",),
        transform_chain=("imputation:self-loss",),
    )
    out=typed_loss.storage_transition_with_typed_self_loss(
        st,tb,stock,charge,discharge,self_loss
    )
    if out.value != core.F(103):
        raise AssertionError("typed self-loss nominal storage value mismatch")
    if not isinstance(out.uncertainty,core.IntervalUncertainty):
        raise AssertionError("self-loss uncertainty not propagated")
    if (out.uncertainty.lower,out.uncertainty.upper) != (
        core.F("-0.5"),core.F("0.5")
    ):
        raise AssertionError("self-loss interval uncertainty mismatch")
    if out.status is not core.EpistemicStatus.IMPUTED:
        raise AssertionError("self-loss epistemic status not preserved conservatively")
    if "EV:self-loss" not in out.evidence_refs:
        raise AssertionError("self-loss evidence ref not preserved")
    if "imputation:self-loss" not in out.transform_chain:
        raise AssertionError("self-loss transform chain not preserved")
    if out.space is not core.ValueSpace.PHYSICAL:
        raise AssertionError("self-loss value space not preserved")

    raw_rejection=_expect_typed_hold(
        "HOLD_SELF_LOSS_TYPED_VALUE_REQUIRED",
        lambda:typed_loss.storage_transition_with_typed_self_loss(
            st,tb,stock,charge,discharge,core.F(1)
        ),
    )
    negative_rejection=_expect_typed_hold(
        "HOLD_NEGATIVE_SELF_LOSS",
        lambda:typed_loss.storage_transition_with_typed_self_loss(
            st,tb,stock,charge,discharge,
            core.qv(-1,st.layer,interval_id=tb.interval_id),
        ),
    )
    wrong_layer_rejection=_expect_core_hold(
        core.HoldCode.HOLD_UNIT_MISMATCH,
        lambda:typed_loss.storage_transition_with_typed_self_loss(
            st,tb,stock,charge,discharge,
            core.qv(
                1,core.ResourceLayer.FRESHWATER,interval_id=tb.interval_id
            ),
        ),
    )
    interval_rejection=_expect_core_hold(
        core.HoldCode.HOLD_TIME_BASIS_MISMATCH,
        lambda:typed_loss.storage_transition_with_typed_self_loss(
            st,tb,stock,charge,discharge,
            core.qv(1,st.layer,interval_id="T1"),
        ),
    )

    moment_loss=core.qv(
        1,st.layer,interval_id=tb.interval_id,
        uncertainty=core.MomentUncertainty(core.F(0),core.F(4)),
    )
    covariance_required=False
    try:
        typed_loss.storage_transition_with_typed_self_loss(
            st,tb,stock,charge,discharge,moment_loss
        )
    except core.HoldError as exc:
        covariance_required=exc.code is core.HoldCode.HOLD_COVARIANCE_REQUIRED
    if not covariance_required:
        raise AssertionError("typed self-loss moment path did not require covariance")

    empirical_loss=core.qv(
        1,st.layer,interval_id=tb.interval_id,
        uncertainty=core.EmpiricalUncertainty(
            (core.F("-0.5"),core.F("0.5")),"A"
        ),
    )
    alignment_required=False
    try:
        typed_loss.storage_transition_with_typed_self_loss(
            st,tb,stock,charge,discharge,empirical_loss
        )
    except core.HoldError as exc:
        alignment_required=exc.code is core.HoldCode.HOLD_SAMPLE_ALIGNMENT_REQUIRED
    if not alignment_required:
        raise AssertionError("typed self-loss empirical path did not require alignment")

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_STORAGE_SELF_LOSS_TYPED_PHYSICAL_RATE_RECEIPT_V1",
        "gate_id":GATE_ID,
        "contract_sha256":sha256_file(str(CONTRACT_PATH)),
        "successor_module_sha256":
            sha256_file("planetary_resource_storage_self_loss_typed_v1.py"),
        "verified_predecessor_pins":{
            **observed_pins,
            "typed_process_receipt_sha256":typed_receipt_sha,
            "e2e_uncertainty_receipt_sha256":e2e_receipt_sha,
            "post_uncertainty_review_receipt_sha256":review_receipt_sha,
        },
        "legacy_python_matrix":{"count":40,"pass":40},
        "typed_self_loss_example":{
            "nominal_next_stock":str(out.value),
            "uncertainty_lower":str(out.uncertainty.lower),
            "uncertainty_upper":str(out.uncertainty.upper),
            "status":out.status.value,
            "evidence_refs":list(out.evidence_refs),
            "value_space":out.space.value,
        },
        "rejections":{
            "raw_fraction":raw_rejection,
            "negative_self_loss":negative_rejection,
            "wrong_layer_or_unit":wrong_layer_rejection,
            "interval_mismatch":interval_rejection,
        },
        "moment_requires_covariance":True,
        "empirical_requires_sample_alignment":True,
        "self_loss_uncertainty_included":True,
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
    print("STORAGE_SELF_LOSS_TYPED_RATE_RECEIPT_SHA256="+sha)
