from __future__ import annotations

from dataclasses import fields
import hashlib
import json
from pathlib import Path
from typing import Any

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_end_to_end_uncertainty_gate_v1 as e2e_gate
import planetary_resource_process_typed_dimensional_closure_gate_v1 as typed_gate
import planetary_resource_process_typed_dimensional_closure_v1 as typed
import planetary_resource_storage_self_loss_typed_gate_v1 as self_loss_gate
import planetary_resource_storage_self_loss_typed_v1 as typed_loss


GATE_ID=(
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__POST_SELF_LOSS_CORE_GAP_REVIEW_V1"
)
REVIEW_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__POST_SELF_LOSS_CORE_GAP_REVIEW.json"
)
OUT_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__POST_SELF_LOSS_CORE_GAP_REVIEW_RECEIPT.json"
)


def sha256_file(path:str)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha256(obj:Any)->str:
    body=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load_review()->dict[str,Any]:
    r=json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    if r["gate_id"] != GATE_ID:
        raise AssertionError("post-self-loss review gate mismatch")
    nxt=r["next_single_unproven_core_capability"]
    if nxt["id"] != "PROCESS_COEFFICIENT_UNCERTAINTY_PROPAGATION_V1":
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
    checks={
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
    out={}
    for key,path in checks.items():
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

    loss_sha=canonical_sha256(self_loss_gate.run_gate())
    if loss_sha != pins["typed_self_loss_receipt_sha256"]:
        raise AssertionError("typed self-loss receipt changed")
    out["typed_self_loss_receipt_sha256"]=loss_sha
    return out


def review_storage_host_node_scope()->dict[str,Any]:
    st,tb,stock,charge,discharge=core.fixture_f06_storage()
    bad=core.StorageManifest(
        st.storage_id,
        st.layer,
        "NODE_DOES_NOT_EXIST",
        st.capacity,
        st.max_charge_rate,
        st.max_discharge_rate,
        st.eta_charge,
        st.eta_discharge,
        st.manifest_version,
    )
    loss=core.qv(0,st.layer,interval_id=tb.interval_id)
    out=typed_loss.storage_transition_with_typed_self_loss(
        bad,tb,stock,charge,discharge,loss
    )
    return {
        "arbitrary_nonexistent_host_node_id_accepted":out.value==core.F(104),
        "transition_receives_topology_nodes":False,
        "status":"PASS_BOUNDED_LOCAL_TRANSITION_WITH_HOST_SCOPE_GAP",
    }


def review_storage_parameter_uncertainty()->dict[str,Any]:
    fs={f.name:f for f in fields(core.StorageManifest)}
    parameter_names=[
        "capacity","max_charge_rate","max_discharge_rate",
        "eta_charge","eta_discharge",
    ]
    annotations={name:str(fs[name].type) for name in parameter_names}
    all_raw_fraction=all("Fraction" in annotations[name] for name in parameter_names)

    st,tb,stock,charge,discharge=core.fixture_f06_storage()
    loss=core.qv(0,st.layer,interval_id=tb.interval_id)
    out=typed_loss.storage_transition_with_typed_self_loss(
        st,tb,stock,charge,discharge,loss
    )
    return {
        "parameter_annotations":annotations,
        "all_reviewed_parameters_raw_fraction":all_raw_fraction,
        "manifest_has_parameter_uncertainty_field":
            any("uncertainty" in f.name for f in fields(core.StorageManifest)),
        "exact_inputs_produce_exact_output_uncertainty":
            isinstance(out.uncertainty,core.ExactUncertainty),
        "status":"PASS_BOUNDED_EXACT_PARAMETER_MODEL_WITH_UNCERTAINTY_GAP",
    }


def review_process_coefficient_uncertainty()->dict[str,Any]:
    coeff_fields={f.name for f in fields(core.ProcessCoefficient)}
    layer=core.ResourceLayer.ELECTRICITY
    nodes=core.nodes_for(layer,["E0"])
    process=core.ProcessManifest(
        "P","PHYSICAL_CONVERSION","activity",
        (
            core.ProcessCoefficient(
                layer,"E0",core.F(2),"EV:coef","W_e/activity"
            ),
        ),
        "SRC","METHOD",
    )
    activity=core.QualifiedValue(
        core.F(3),
        core.UnitTag(layer,core.QuantityKind.DIMENSIONLESS,"activity"),
        "T0",
        core.EpistemicStatus.OBSERVED,
        core.ExactUncertainty(),
        ("EV:activity",),
        (),
        (),
        "fresh",
        core.ValueSpace.PHYSICAL,
    )
    out=typed.process_coupling_typed(
        process,activity,nodes,target_layer=layer,interval_id="T0"
    )["E0"]
    return {
        "coefficient_has_uncertainty_field":"uncertainty" in coeff_fields,
        "coefficient_is_raw_fraction_field":"coefficient" in coeff_fields,
        "exact_activity_output_uncertainty_is_exact":
            isinstance(out.uncertainty,core.ExactUncertainty),
        "output_value":str(out.value),
        "coefficient_evidence_preserved":"EV:coef" in out.evidence_refs,
        "status":"HOLD_UNREPRESENTED_PHYSICAL_COEFFICIENT_UNCERTAINTY",
    }


def review_process_coefficient_validity_interval()->dict[str,Any]:
    coeff_fields={f.name for f in fields(core.ProcessCoefficient)}
    return {
        "has_valid_from":"valid_from" in coeff_fields,
        "has_valid_to":"valid_to" in coeff_fields,
        "has_interval_id":"interval_id" in coeff_fields,
        "status":"HOLD_NO_COEFFICIENT_VALIDITY_INTERVAL",
    }


def review_process_manifest_version_enforcement()->dict[str,Any]:
    layer=core.ResourceLayer.ELECTRICITY
    nodes=core.nodes_for(layer,["E0"],version="V1")
    process=core.ProcessManifest(
        "P","PHYSICAL_CONVERSION","activity",
        (
            core.ProcessCoefficient(
                layer,"E0",core.F(2),"EV:coef","W_e/activity"
            ),
        ),
        "SRC","METHOD",
        manifest_version="V99",
    )
    activity=core.QualifiedValue(
        core.F(1),
        core.UnitTag(layer,core.QuantityKind.DIMENSIONLESS,"activity"),
        "T0",
    )
    out=typed.process_coupling_typed(
        process,activity,nodes,target_layer=layer,interval_id="T0"
    )["E0"]
    return {
        "process_manifest_version":"V99",
        "target_node_manifest_version":"V1",
        "mismatched_manifest_version_accepted":out.value==core.F(2),
        "status":"HOLD_UNENFORCED_TYPED_PROCESS_MANIFEST_VERSION",
    }


def review_audit_vector_provenance_typing()->dict[str,Any]:
    audit=core.audit_vector_l1_l4(
        core.F("0.1"),core.F("0.2"),core.F("0.3"),core.F("0.4")
    )
    aggregate_prohibited=False
    try:
        core.emit_aggregate_equilibrium_score(audit)
    except core.HoldError as exc:
        aggregate_prohibited=(
            exc.code is core.HoldCode.HOLD_AGGREGATE_SCORE_PROHIBITED
        )
    return {
        "returns_bare_tuple":isinstance(audit,tuple),
        "has_evidence_refs":hasattr(audit,"evidence_refs"),
        "has_uncertainty":hasattr(audit,"uncertainty"),
        "aggregate_score_prohibited":aggregate_prohibited,
        "status":"PASS_BOUNDED_SEPARATE_BUT_NOT_PROVENANCE_TYPED",
    }


def run_review()->dict[str,Any]:
    r=load_review()
    pins=verify_pins(r)

    observed={
        "storage_host_node_scope":review_storage_host_node_scope(),
        "storage_parameter_uncertainty":review_storage_parameter_uncertainty(),
        "process_coefficient_uncertainty":review_process_coefficient_uncertainty(),
        "process_coefficient_validity_interval":
            review_process_coefficient_validity_interval(),
        "process_manifest_version_enforcement":
            review_process_manifest_version_enforcement(),
        "audit_vector_provenance_typing":
            review_audit_vector_provenance_typing(),
    }

    if not observed["storage_host_node_scope"]["arbitrary_nonexistent_host_node_id_accepted"]:
        raise AssertionError("storage host-node scope gap is no longer observable")
    if observed["process_coefficient_uncertainty"]["coefficient_has_uncertainty_field"]:
        raise AssertionError("selected coefficient uncertainty gap is no longer observable")
    if not observed["process_coefficient_uncertainty"]["exact_activity_output_uncertainty_is_exact"]:
        raise AssertionError("coefficient-exactness probe changed")
    if not observed["process_manifest_version_enforcement"]["mismatched_manifest_version_accepted"]:
        raise AssertionError("manifest-version gap no longer observable")
    if not observed["audit_vector_provenance_typing"]["aggregate_score_prohibited"]:
        raise AssertionError("aggregate EQ score prohibition lost")

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_POST_SELF_LOSS_CORE_GAP_REVIEW_RECEIPT_V1",
        "gate_id":GATE_ID,
        "review_manifest_sha256":sha256_file(str(REVIEW_PATH)),
        "verified_predecessor_pins":pins,
        "observed_review":observed,
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
    print("POST_SELF_LOSS_CORE_GAP_REVIEW_RECEIPT_SHA256="+sha)
