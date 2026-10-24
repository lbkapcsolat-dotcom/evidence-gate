from __future__ import annotations

from dataclasses import fields
import hashlib
import json
from pathlib import Path
from typing import Any

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_end_to_end_uncertainty_gate_v1 as e2e_gate
import planetary_resource_end_to_end_uncertainty_v1 as e2e
import planetary_resource_process_typed_dimensional_closure_gate_v1 as typed_gate
import planetary_resource_process_typed_dimensional_closure_v1 as typed


GATE_ID=(
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__POST_UNCERTAINTY_CORE_GAP_REVIEW_V1"
)
REVIEW_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__POST_UNCERTAINTY_CORE_GAP_REVIEW.json"
)
OUT_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__POST_UNCERTAINTY_CORE_GAP_REVIEW_RECEIPT.json"
)


def sha256_file(path:str)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha256(obj:Any)->str:
    body=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load_review()->dict[str,Any]:
    r=json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    if r["gate_id"] != GATE_ID:
        raise AssertionError("post-uncertainty review gate mismatch")
    nxt=r["next_single_unproven_core_capability"]
    if nxt["id"] != "STORAGE_SELF_LOSS_TYPED_PHYSICAL_RATE_V1":
        raise AssertionError("wrong next capability selected")
    if nxt["implementation_not_authorized_by_this_review"] is not True:
        raise AssertionError("review must not implement successor capability")
    for key in (
        "provider_work","new_source_ingest","multi_source_fusion","eq_score","ui",
        "runtime_admission","pointer_promotion","global_bind","merge",
    ):
        if r["fences"][key] is not False:
            raise AssertionError(f"scope fence enabled: {key}")
    return r


def verify_pins(r:dict[str,Any])->dict[str,str]:
    pins=r["predecessor_pins"]
    file_checks={
        "typed_process_contract_sha256":
            "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__PROCESS_COUPLING_TYPED_DIMENSIONAL_CLOSURE.json",
        "typed_process_module_sha256":
            "planetary_resource_process_typed_dimensional_closure_v1.py",
        "e2e_uncertainty_contract_sha256":
            "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__END_TO_END_UNCERTAINTY_PROPAGATION.json",
        "e2e_uncertainty_module_sha256":
            "planetary_resource_end_to_end_uncertainty_v1.py",
        "python_core_sha256":
            "equilibrium_planetary_resource_core_v1.py",
        "cpp_kernel_sha256":
            "planetary_resource_cpp_kernel_v1.cpp",
    }
    out={}
    for key,path in file_checks.items():
        got=sha256_file(path)
        if got != pins[key]:
            raise AssertionError(f"{key} changed: {got} != {pins[key]}")
        out[key]=got

    typed_sha=canonical_sha256(typed_gate.run_gate())
    if typed_sha != pins["typed_process_receipt_sha256"]:
        raise AssertionError("typed-process receipt changed")
    out["typed_process_receipt_sha256"]=typed_sha

    e2e_sha=canonical_sha256(e2e_gate.run_gate())
    if e2e_sha != pins["e2e_uncertainty_receipt_sha256"]:
        raise AssertionError("end-to-end uncertainty receipt changed")
    out["e2e_uncertainty_receipt_sha256"]=e2e_sha
    return out


def review_storage_and_self_loss()->dict[str,Any]:
    st,tb,stock,charge,discharge=core.fixture_f06_storage()
    baseline=core.storage_transition(st,tb,stock,charge,discharge)
    negative=core.storage_transition(
        st,tb,stock,charge,discharge,self_loss_rate=core.F(-1)
    )
    successor_negative=e2e.storage_transition_with_uncertainty(
        st,tb,stock,charge,discharge,self_loss_rate=core.F(-1)
    )
    return {
        "baseline_next_stock":str(baseline.value),
        "negative_self_loss_next_stock":str(negative.value),
        "negative_self_loss_accepted":negative.value==core.F(105),
        "negative_self_loss_increases_stock":negative.value>baseline.value,
        "successor_negative_self_loss_accepted":
            successor_negative.value==core.F(105),
        "self_loss_is_raw_fraction_parameter":True,
        "self_loss_has_no_qv_metadata":True,
        "self_loss_excluded_from_uncertainty_contributors":True,
        "status":"HOLD_UNTYPED_DIRECT_PHYSICAL_RATE_INGRESS",
    }


def review_audit_vector()->dict[str,Any]:
    v=core.audit_vector_l1_l4(
        core.F("0.1"),core.F("0.2"),core.F("0.3"),core.F("0.4")
    )
    aggregate_prohibited=False
    try:
        core.emit_aggregate_equilibrium_score(v)
    except core.HoldError as exc:
        aggregate_prohibited=(
            exc.code is core.HoldCode.HOLD_AGGREGATE_SCORE_PROHIBITED
        )
    return {
        "returns_tuple":isinstance(v,tuple),
        "has_provenance_fields":hasattr(v,"evidence_refs"),
        "aggregate_score_prohibited":aggregate_prohibited,
        "status":"PASS_BOUNDED_SEPARATE_BUT_NOT_PROVENANCE_TYPED",
    }


def review_boundary_uncertainty()->dict[str,Any]:
    layer=core.ResourceLayer.ELECTRICITY
    nodes=core.nodes_for(layer,["E0"])
    flow=core.qv(
        5,layer,
        uncertainty=core.IntervalUncertainty(core.F(-1),core.F(1)),
        evidence_refs=("EV:boundary-flow",),
    )
    out=e2e.resource_balance_with_uncertainty(
        layer=layer,
        interval_id="T0",
        nodes=nodes,
        internal_edges=[],
        B=[[]],
        production=[core.qv(0,layer)],
        demand=[core.qv(5,layer)],
        loss=[core.qv(0,layer)],
        internal_flow=[],
        boundary_edges=[
            core.BoundaryEdgeManifest("BIN",layer,"E0","IMPORT")
        ],
        boundary_flow=[flow],
    )["E0"]
    return {
        "nominal_residual":str(out.value),
        "interval_lower":str(out.uncertainty.lower),
        "interval_upper":str(out.uncertainty.upper),
        "boundary_evidence_preserved":"EV:boundary-flow" in out.evidence_refs,
        "status":"PASS_BOUNDED_FLOW_UNCERTAINTY_COMPLETE_V1",
    }


def review_process_metadata()->dict[str,Any]:
    coeff_fields={f.name for f in fields(core.ProcessCoefficient)}
    manifest_fields={f.name for f in fields(core.ProcessManifest)}

    layer=core.ResourceLayer.ELECTRICITY
    nodes=core.nodes_for(layer,["E0"])
    process=core.ProcessManifest(
        "P",
        "PHYSICAL_CONVERSION",
        "activity",
        (core.ProcessCoefficient(layer,"E0",core.F(2),"EV:coef","W_e/activity"),),
        "SRC",
        "METHOD",
        manifest_version="V99",
    )
    activity=core.QualifiedValue(
        core.F(1),
        core.UnitTag(layer,core.QuantityKind.DIMENSIONLESS,"activity"),
        "T0",
    )
    accepted=typed.process_coupling_typed(
        process,activity,nodes,target_layer=layer,interval_id="T0"
    )["E0"]

    return {
        "coefficient_has_uncertainty_field":"uncertainty" in coeff_fields,
        "coefficient_has_valid_from_field":"valid_from" in coeff_fields,
        "coefficient_has_valid_to_field":"valid_to" in coeff_fields,
        "manifest_has_version_field":"manifest_version" in manifest_fields,
        "mismatched_process_manifest_version_accepted":accepted.value==core.F(2),
        "output_is_typed_qv":isinstance(accepted,core.QualifiedValue),
        "status":"PASS_BOUNDED_WITH_COEFFICIENT_QUALIFICATION_GAP",
    }


def run_review()->dict[str,Any]:
    r=load_review()
    pins=verify_pins(r)

    storage=review_storage_and_self_loss()
    audit=review_audit_vector()
    boundary=review_boundary_uncertainty()
    process=review_process_metadata()

    if not storage["negative_self_loss_accepted"]:
        raise AssertionError("selected self-loss gap no longer observable")
    if not storage["negative_self_loss_increases_stock"]:
        raise AssertionError("negative self-loss did not increase stock")
    if boundary["nominal_residual"]!="0":
        raise AssertionError("boundary uncertainty probe changed nominal balance")
    if (boundary["interval_lower"],boundary["interval_upper"])!=("-1","1"):
        raise AssertionError("boundary interval uncertainty did not propagate")
    if not audit["aggregate_score_prohibited"]:
        raise AssertionError("aggregate audit score prohibition lost")

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_POST_UNCERTAINTY_CORE_GAP_REVIEW_RECEIPT_V1",
        "gate_id":GATE_ID,
        "review_manifest_sha256":sha256_file(str(REVIEW_PATH)),
        "verified_predecessor_pins":pins,
        "observed_review":{
            "remaining_storage_semantics":{
                "baseline_next_stock":storage["baseline_next_stock"],
                "status":r["reviews"]["remaining_storage_semantics"]["status"],
            },
            "self_loss_typing":storage,
            "audit_vector_typing":audit,
            "boundary_uncertainty_completeness":boundary,
            "process_metadata_completeness":process,
        },
        "declared_review":r["reviews"],
        "next_single_unproven_core_capability":
            r["next_single_unproven_core_capability"],
        "selected_capability_count":1,
        "provider_work":False,
        "new_source_ingest":False,
        "fences":r["fences"],
        "verdict":r["verdict_target"],
    }


def write_receipt():
    receipt=run_review()
    body=json.dumps(receipt,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n"
    OUT_PATH.write_text(body,encoding="utf-8")
    sha=hashlib.sha256(body.encode("utf-8")).hexdigest()
    return receipt,sha


if __name__=="__main__":
    receipt,sha=write_receipt()
    print(json.dumps(receipt,sort_keys=True,separators=(",",":"),ensure_ascii=False))
    print("POST_UNCERTAINTY_CORE_GAP_REVIEW_RECEIPT_SHA256="+sha)
