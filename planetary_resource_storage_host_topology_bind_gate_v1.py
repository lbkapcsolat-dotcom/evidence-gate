from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_process_manifest_version_gate_v1 as pmv_gate
import planetary_resource_storage_host_topology_bind_v1 as sh
import planetary_resource_storage_self_loss_typed_gate_v1 as self_loss_gate


GATE_ID=(
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__STORAGE_HOST_NODE_TOPOLOGY_BIND_V1"
)
CONTRACT_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__STORAGE_HOST_NODE_TOPOLOGY_BIND.json"
)
OUT_PATH=Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__STORAGE_HOST_NODE_TOPOLOGY_BIND_RECEIPT.json"
)


def sha256_file(path:str)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha256(obj:Any)->str:
    body=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _expect_hold(code:str,fn)->dict[str,Any]:
    try:
        fn()
    except sh.StorageTopologyHold as exc:
        if exc.code != code:
            raise AssertionError(f"expected {code}, got {exc.code}")
        return {"expected":code,"observed":exc.code,"passed":True}
    raise AssertionError(f"expected {code}, got PASS")


def run_gate()->dict[str,Any]:
    contract=json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("storage topology contract mismatch")

    pins=contract["predecessor_pins"]
    observed={
        "python_core_sha256":sha256_file("equilibrium_planetary_resource_core_v1.py"),
        "cpp_kernel_sha256":sha256_file("planetary_resource_cpp_kernel_v1.cpp"),
        "typed_self_loss_contract_sha256":
            sha256_file("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__STORAGE_SELF_LOSS_TYPED_PHYSICAL_RATE.json"),
        "typed_self_loss_module_sha256":
            sha256_file("planetary_resource_storage_self_loss_typed_v1.py"),
        "typed_self_loss_gate_sha256":
            sha256_file("planetary_resource_storage_self_loss_typed_gate_v1.py"),
        "process_manifest_version_contract_sha256":
            sha256_file("EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__PROCESS_MANIFEST_VERSION_ENFORCEMENT.json"),
        "process_manifest_version_module_sha256":
            sha256_file("planetary_resource_process_manifest_version_v1.py"),
        "process_manifest_version_gate_sha256":
            sha256_file("planetary_resource_process_manifest_version_gate_v1.py"),
    }
    for key,got in observed.items():
        if got != pins[key]:
            raise AssertionError(f"predecessor pin changed: {key} {got} != {pins[key]}")

    self_loss_sha=canonical_sha256(self_loss_gate.run_gate())
    if self_loss_sha != pins["typed_self_loss_receipt_sha256"]:
        raise AssertionError("typed self-loss receipt changed")
    observed["typed_self_loss_receipt_sha256"]=self_loss_sha

    pmv_sha=canonical_sha256(pmv_gate.run_gate())
    if pmv_sha != pins["process_manifest_version_receipt_sha256"]:
        raise AssertionError("process manifest version receipt changed")
    observed["process_manifest_version_receipt_sha256"]=pmv_sha

    matrix=core.run_validation_matrix()
    if len(matrix)!=40 or sum(1 for x in matrix if x.passed)!=40:
        raise AssertionError("legacy Python core no longer 40/40")

    st,tb,stock,charge,discharge=core.fixture_f06_storage()
    topology=sh.ActiveTopologySnapshot(
        st.layer,"V1",(core.NodeManifest("E0",st.layer,"ELECTRICITY_ZONE","V1"),)
    )
    self_loss=core.qv(
        1,st.layer,interval_id=tb.interval_id,
        status=core.EpistemicStatus.IMPUTED,
        uncertainty=core.IntervalUncertainty(core.F("-0.5"),core.F("0.5")),
        evidence_refs=("EV:self-loss",),
        transform_chain=("imputation:self-loss",),
    )
    admitted=sh.storage_transition_with_topology_bind(
        st,topology,tb,stock,charge,discharge,self_loss
    )
    if admitted.value != core.F(103):
        raise AssertionError("topology bind changed nominal storage result")
    if not isinstance(admitted.uncertainty,core.IntervalUncertainty):
        raise AssertionError("storage uncertainty lost")
    if (admitted.uncertainty.lower,admitted.uncertainty.upper) != (
        core.F("-0.5"),core.F("0.5")
    ):
        raise AssertionError("storage uncertainty changed")
    if admitted.status is not core.EpistemicStatus.IMPUTED:
        raise AssertionError("storage metadata status lost")
    if "EV:self-loss" not in admitted.evidence_refs:
        raise AssertionError("self-loss evidence lost")
    if admitted.space is not core.ValueSpace.PHYSICAL:
        raise AssertionError("storage value space changed")

    missing=_expect_hold(
        "HOLD_STORAGE_HOST_NODE_MISSING",
        lambda:sh.storage_transition_with_topology_bind(
            st,
            sh.ActiveTopologySnapshot(
                st.layer,"V1",(core.NodeManifest("E9",st.layer,"ELECTRICITY_ZONE","V1"),)
            ),
            tb,stock,charge,discharge,self_loss,
        ),
    )
    wrong_layer=_expect_hold(
        "HOLD_STORAGE_HOST_NODE_LAYER_MISMATCH",
        lambda:sh.storage_transition_with_topology_bind(
            st,
            sh.ActiveTopologySnapshot(
                core.ResourceLayer.FRESHWATER,"V1",
                (core.NodeManifest("E0",core.ResourceLayer.FRESHWATER,"WATER_BASIN_OR_ACCOUNTING_UNIT","V1"),)
            ),
            tb,stock,charge,discharge,self_loss,
        ),
    )
    version=_expect_hold(
        "HOLD_STORAGE_HOST_NODE_VERSION_MISMATCH",
        lambda:sh.storage_transition_with_topology_bind(
            core.StorageManifest(
                st.storage_id,st.layer,st.host_node_id,st.capacity,
                st.max_charge_rate,st.max_discharge_rate,st.eta_charge,st.eta_discharge,"V2"
            ),
            topology,tb,stock,charge,discharge,self_loss,
        ),
    )

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_STORAGE_HOST_NODE_TOPOLOGY_BIND_RECEIPT_V1",
        "gate_id":GATE_ID,
        "contract_sha256":sha256_file(str(CONTRACT_PATH)),
        "successor_module_sha256":
            sha256_file("planetary_resource_storage_host_topology_bind_v1.py"),
        "verified_predecessor_pins":observed,
        "legacy_python_matrix":{"count":40,"pass":40},
        "admitted_example":{
            "host_node_id":"E0",
            "active_topology_layer":st.layer.value,
            "active_topology_manifest_version":"V1",
            "nominal_next_stock":str(admitted.value),
            "uncertainty_lower":str(admitted.uncertainty.lower),
            "uncertainty_upper":str(admitted.uncertainty.upper),
            "status":admitted.status.value,
            "value_space":admitted.space.value,
            "evidence_refs":list(admitted.evidence_refs),
        },
        "rejections":{
            "missing_host":missing,
            "wrong_layer_host":wrong_layer,
            "host_version_mismatch":version,
        },
        "storage_uncertainty_preserved":True,
        "typed_self_loss_preserved":True,
        "evidence_and_metadata_preserved":True,
        "active_topology_bind_required":True,
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
    print("STORAGE_HOST_TOPOLOGY_BIND_RECEIPT_SHA256="+sha)
