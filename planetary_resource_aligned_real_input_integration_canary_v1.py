from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_bom_elexon_entsog_temporally_aligned_snapshot_set_v1 as aligned
import planetary_resource_empirical_admission_v1 as admission
import planetary_resource_end_to_end_uncertainty_v1 as e2e


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__ALIGNED_REAL_INPUT_INTEGRATION_CANARY_V1"
)
CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__ALIGNED_REAL_INPUT_INTEGRATION_CANARY.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__ALIGNED_REAL_INPUT_INTEGRATION_CANARY_RECEIPT.json"
)
MANIFEST_VERSION = "V1"


@dataclass(frozen=True)
class UnitInput:
    value: Fraction
    source_unit: str
    source_layer: str
    source_quantity_kind: str
    source_gas_basis: str = ""


def canonical_sha256(payload: dict[str, Any]) -> str:
    body = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def interval_id(prefix: str, start: str, end: str) -> str:
    return (
        prefix
        + "_"
        + dt(start).strftime("%Y%m%dT%H%M%SZ")
        + "_"
        + dt(end).strftime("%Y%m%dT%H%M%SZ")
    )


def qv_dict(v: core.QualifiedValue) -> dict[str, Any]:
    return {
        "value_n": None if v.value is None else v.value.numerator,
        "value_d": None if v.value is None else v.value.denominator,
        "unit": v.unit.symbol,
        "gas_basis": v.unit.gas_basis,
        "interval_id": v.interval_id,
        "status": v.status.value,
        "uncertainty_kind": v.uncertainty.kind.value,
        "evidence_refs": list(v.evidence_refs),
        "transform_chain": list(v.transform_chain),
    }


def zero(layer: core.ResourceLayer, iid: str) -> core.QualifiedValue:
    return core.QualifiedValue(
        value=Fraction(0),
        unit=core.canonical_unit(layer, core.QuantityKind.RATE),
        interval_id=iid,
        status=core.EpistemicStatus.DERIVED,
        uncertainty=core.ExactUncertainty(),
        evidence_refs=("INTEGRATION_FIXTURE:ZERO_BASELINE",),
        transform_chain=("integration_fixture:zero_baseline",),
        freshness="FROZEN_INTEGRATION_FIXTURE",
        space=core.ValueSpace.PHYSICAL,
    )


def observed_rate(
    *,
    value: Fraction,
    layer: core.ResourceLayer,
    iid: str,
    evidence_refs: tuple[str, ...],
    transform_chain: tuple[str, ...],
    gas_basis: str | None = None,
) -> core.QualifiedValue:
    return core.QualifiedValue(
        value=value,
        unit=core.canonical_unit(layer, core.QuantityKind.RATE, gas_basis),
        interval_id=iid,
        status=core.EpistemicStatus.OBSERVED,
        uncertainty=core.UnknownUncertainty(),
        evidence_refs=evidence_refs,
        transform_chain=transform_chain,
        freshness="PINNED_REAL_SOURCE",
        space=core.ValueSpace.PHYSICAL,
    )


def frozen_unit_convert(
    *,
    variable_id: str,
    value: Fraction,
    source_unit: str,
    source_layer: str,
    source_gas_basis: str = "",
) -> tuple[Fraction, str]:
    spec = admission.variable_spec(variable_id)
    candidate = UnitInput(
        value=value,
        source_unit=source_unit,
        source_layer=source_layer,
        source_quantity_kind="RATE",
        source_gas_basis=source_gas_basis,
    )
    return admission.unit_conversion(spec, candidate)  # frozen contract path


def exact_temporal_guard(
    *,
    variable_id: str,
    source_interval_id: str,
    target_interval_id: str,
) -> dict[str, Any]:
    spec = admission.variable_spec(variable_id)
    alignment = admission.TemporalAlignment(
        method=admission.TemporalMethod.EXACT_INTERVAL,
        source_interval_id=source_interval_id,
        target_interval_id=target_interval_id,
    )
    try:
        chain = admission.validate_temporal(spec, alignment)
        return {
            "decision": "READY_EXACT_INTERVAL",
            "hold_code": None,
            "transform_chain": list(chain),
        }
    except admission.AdmissionHold as exc:
        return {
            "decision": "HOLD",
            "hold_code": exc.code,
            "message": str(exc),
            "transform_chain": [],
        }


def run_gate() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract["gate_id"] != GATE_ID:
        raise AssertionError("gate id mismatch")
    if any(contract["fences"].values()):
        raise AssertionError("forbidden fence enabled")
    if not all(contract["requirements"].values()):
        raise AssertionError("required preservation disabled")

    pred = aligned.run_gate()
    pred_sha = canonical_sha256(pred)
    if pred_sha != contract["predecessor"]["receipt_sha256"]:
        raise AssertionError(
            f"aligned predecessor receipt changed: {pred_sha}"
        )

    common = contract["target_common_window"]
    pred_common = pred["three_way_intersection"]
    if (
        pred_common["start_utc"] != common["start_utc"]
        or pred_common["end_utc"] != common["end_utc"]
        or pred_common["duration_seconds"] != 1800
    ):
        raise AssertionError("common window changed")

    # Frozen source-unit mapping only. No temporal re-tagging occurs here.
    e_src = pred["sources"]["electricity"]
    e_value, e_unit = frozen_unit_convert(
        variable_id=contract["mappings"]["electricity"]["variable_id"],
        value=Fraction(e_src["record"]["initialDemandOutturn"]),
        source_unit="MW",
        source_layer="ELECTRICITY",
    )
    if e_unit != "W_e":
        raise AssertionError("electricity canonical unit changed")

    g_src = pred["sources"]["natural_gas"]
    # Reuse the already-proven gas semantic adapter:
    # kWh/h_GCV == kW_GCV numerically; frozen gas canary maps GCV terminology to HHV.
    g_value, g_unit = frozen_unit_convert(
        variable_id=contract["mappings"]["natural_gas"]["variable_id"],
        value=Fraction(g_src["value"]),
        source_unit="kW_HHV",
        source_layer="NATURAL_GAS",
        source_gas_basis="HHV",
    )
    if g_unit != "W_th":
        raise AssertionError("gas canonical unit changed")

    w_src = pred["sources"]["freshwater"]
    w_value, w_unit = frozen_unit_convert(
        variable_id=contract["mappings"]["freshwater"]["variable_id"],
        value=Fraction(w_src["published_value"]),
        source_unit="m3/s",
        source_layer="FRESHWATER",
    )
    if w_unit != "m3/s":
        raise AssertionError("freshwater canonical unit changed")

    target_iid = common["interval_id"]
    e_source_iid = interval_id(
        "ELEXON",
        e_src["interval_start"],
        e_src["interval_end"],
    )
    g_source_iid = interval_id(
        "ENTSOG",
        g_src["interval_start"],
        g_src["interval_end"],
    )
    w_source_iid = interval_id(
        "BOM",
        w_src["interval_start"],
        w_src["interval_end"],
    )

    # Because Elexon support equals the target support, its source interval
    # is exactly the target interval for frozen EXACT_INTERVAL admission.
    if (
        dt(e_src["interval_start"]) == dt(common["start_utc"])
        and dt(e_src["interval_end"]) == dt(common["end_utc"])
    ):
        e_source_iid = target_iid

    temporal = {
        "electricity": exact_temporal_guard(
            variable_id=contract["mappings"]["electricity"]["variable_id"],
            source_interval_id=e_source_iid,
            target_interval_id=target_iid,
        ),
        "natural_gas": exact_temporal_guard(
            variable_id=contract["mappings"]["natural_gas"]["variable_id"],
            source_interval_id=g_source_iid,
            target_interval_id=target_iid,
        ),
        "freshwater": exact_temporal_guard(
            variable_id=contract["mappings"]["freshwater"]["variable_id"],
            source_interval_id=w_source_iid,
            target_interval_id=target_iid,
        ),
    }

    if temporal["electricity"]["decision"] != "READY_EXACT_INTERVAL":
        raise AssertionError("Elexon exact support unexpectedly blocked")
    for layer in ("natural_gas", "freshwater"):
        if temporal[layer]["hold_code"] != "HOLD_TEMPORAL_METHOD_INVALID":
            raise AssertionError(f"{layer} did not fail closed on exact support")

    e_nodes = core.nodes_for(
        core.ResourceLayer.ELECTRICITY, ["E0"], version=MANIFEST_VERSION
    )
    g_nodes = core.nodes_for(
        core.ResourceLayer.NATURAL_GAS, ["G0"], version=MANIFEST_VERSION
    )
    w_nodes = core.nodes_for(
        core.ResourceLayer.FRESHWATER, ["W0", "W1"], version=MANIFEST_VERSION
    )
    w_edge = core.InternalEdgeManifest(
        edge_id=contract["mappings"]["freshwater"]["edge_id"],
        layer=core.ResourceLayer.FRESHWATER,
        source_node_id="W0",
        target_node_id="W1",
        manifest_version=MANIFEST_VERSION,
    )
    w_edges = [w_edge]
    w_B = core.build_internal_incidence(w_nodes, w_edges)
    core.validate_topology(
        w_nodes, w_edges, core.ResourceLayer.FRESHWATER, MANIFEST_VERSION
    )
    core.validate_internal_incidence(w_B, w_nodes, w_edges)

    e_qv = observed_rate(
        value=e_value,
        layer=core.ResourceLayer.ELECTRICITY,
        iid=target_iid,
        evidence_refs=(
            "RAW_SHA256:" + e_src["raw_sha256"],
            e_src["source_url"],
        ),
        transform_chain=(
            "source:elexon_indo",
            "unit:MW->W_e:frozen_empirical_contract",
            "slot:DEMAND",
            "temporal:EXACT_INTERVAL",
        ),
    )
    g_qv = observed_rate(
        value=g_value,
        layer=core.ResourceLayer.NATURAL_GAS,
        iid=g_source_iid,
        evidence_refs=(
            "RAW_SHA256:" + g_src["raw_sha256"],
            g_src["source_url"],
        ),
        transform_chain=(
            "source:entsog_physical_flow",
            "source_unit_adapter:kWh/h_GCV->kW_HHV:factor=1",
            "unit:kW_HHV->W_th:frozen_empirical_contract",
            "slot:BOUNDARY_IMPORT",
        ),
        gas_basis="HHV",
    )
    w_qv = observed_rate(
        value=w_value,
        layer=core.ResourceLayer.FRESHWATER,
        iid=w_source_iid,
        evidence_refs=(
            "RAW_SHA256:" + w_src["raw_sha256"],
            w_src["source_url"],
        ),
        transform_chain=(
            "source:bom_water_course_discharge",
            "unit:m3/s->m3/s:frozen_empirical_contract",
            "slot:INTERNAL_FLOW",
        ),
    )

    e_effect = e2e.resource_balance_with_uncertainty(
        layer=core.ResourceLayer.ELECTRICITY,
        interval_id=target_iid,
        nodes=e_nodes,
        internal_edges=[],
        B=[[]],
        production=[zero(core.ResourceLayer.ELECTRICITY, target_iid)],
        demand=[e_qv],
        loss=[zero(core.ResourceLayer.ELECTRICITY, target_iid)],
        internal_flow=[],
        manifest_version=MANIFEST_VERSION,
    )

    g_edge = core.BoundaryEdgeManifest(
        boundary_edge_id="G_REAL_IMPORT_0",
        layer=core.ResourceLayer.NATURAL_GAS,
        local_node_id="G0",
        direction="IMPORT",
        manifest_version=MANIFEST_VERSION,
    )
    g_effect = e2e.resource_balance_with_uncertainty(
        layer=core.ResourceLayer.NATURAL_GAS,
        interval_id=g_source_iid,
        nodes=g_nodes,
        internal_edges=[],
        B=[[]],
        production=[zero(core.ResourceLayer.NATURAL_GAS, g_source_iid)],
        demand=[zero(core.ResourceLayer.NATURAL_GAS, g_source_iid)],
        loss=[zero(core.ResourceLayer.NATURAL_GAS, g_source_iid)],
        internal_flow=[],
        boundary_edges=[g_edge],
        boundary_flow=[g_qv],
        manifest_version=MANIFEST_VERSION,
    )

    w_effect = e2e.resource_balance_with_uncertainty(
        layer=core.ResourceLayer.FRESHWATER,
        interval_id=w_source_iid,
        nodes=w_nodes,
        internal_edges=w_edges,
        B=w_B,
        production=[
            zero(core.ResourceLayer.FRESHWATER, w_source_iid),
            zero(core.ResourceLayer.FRESHWATER, w_source_iid),
        ],
        demand=[
            zero(core.ResourceLayer.FRESHWATER, w_source_iid),
            zero(core.ResourceLayer.FRESHWATER, w_source_iid),
        ],
        loss=[
            zero(core.ResourceLayer.FRESHWATER, w_source_iid),
            zero(core.ResourceLayer.FRESHWATER, w_source_iid),
        ],
        internal_flow=[w_qv],
        manifest_version=MANIFEST_VERSION,
    )

    if e_effect["E0"].value != -e_value:
        raise AssertionError("Elexon did not enter demand slot")
    if g_effect["G0"].value != g_value:
        raise AssertionError("ENTSOG did not enter boundary import slot")
    if w_effect["W0"].value != -w_value or w_effect["W1"].value != w_value:
        raise AssertionError("BOM did not enter directed internal edge")
    if any(
        x.uncertainty.kind is not core.UncertaintyKind.UNKNOWN
        for x in (
            e_effect["E0"],
            g_effect["G0"],
            w_effect["W0"],
            w_effect["W1"],
        )
    ):
        raise AssertionError("UNKNOWN uncertainty was lost")

    return {
        "schema_version":
            "EQUILIBRIUM_PRS_ALIGNED_REAL_INPUT_INTEGRATION_CANARY_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessor": {
            "receipt_sha256": pred_sha,
            "verdict": pred["verdict"],
            "head_sha": contract["predecessor"]["head_sha"],
        },
        "target_common_window": common,
        "slot_mappings": {
            "electricity": {
                "variable_id": contract["mappings"]["electricity"]["variable_id"],
                "slot": "DEMAND",
                "canonical_value_n": e_value.numerator,
                "canonical_value_d": e_value.denominator,
                "canonical_unit": e_unit,
                "source_interval_start": e_src["interval_start"],
                "source_interval_end": e_src["interval_end"],
                "raw_sha256": e_src["raw_sha256"],
                "source_url": e_src["source_url"],
                "uncertainty_kind": "UNKNOWN",
            },
            "natural_gas": {
                "variable_id": contract["mappings"]["natural_gas"]["variable_id"],
                "slot": "BOUNDARY_IMPORT",
                "canonical_value_n": g_value.numerator,
                "canonical_value_d": g_value.denominator,
                "canonical_unit": g_unit,
                "gas_basis": "HHV",
                "source_interval_start": g_src["interval_start"],
                "source_interval_end": g_src["interval_end"],
                "raw_sha256": g_src["raw_sha256"],
                "source_url": g_src["source_url"],
                "uncertainty_kind": "UNKNOWN",
            },
            "freshwater": {
                "variable_id": contract["mappings"]["freshwater"]["variable_id"],
                "slot": "INTERNAL_FLOW",
                "canonical_value_n": w_value.numerator,
                "canonical_value_d": w_value.denominator,
                "canonical_unit": w_unit,
                "source_interval_start": w_src["interval_start"],
                "source_interval_end": w_src["interval_end"],
                "raw_sha256": w_src["raw_sha256"],
                "source_url": w_src["source_url"],
                "uncertainty_kind": "UNKNOWN",
                "relabel_as_production_or_demand": False
            },
        },
        "topology_extension": {
            "integration_fixture_only": True,
            "core_patch": False,
            "nodes": ["W0", "W1"],
            "edge": {
                "edge_id": w_edge.edge_id,
                "source_node_id": w_edge.source_node_id,
                "target_node_id": w_edge.target_node_id,
            },
            "incidence_matrix": [
                [str(value) for value in row] for row in w_B
            ],
            "structurally_valid": True,
        },
        "source_native_core_effects": {
            "electricity": {"E0": qv_dict(e_effect["E0"])},
            "natural_gas": {"G0": qv_dict(g_effect["G0"])},
            "freshwater": {
                "W0": qv_dict(w_effect["W0"]),
                "W1": qv_dict(w_effect["W1"]),
            },
        },
        "temporal_support_guard": temporal,
        "common_window_integration": {
            "admitted": False,
            "ready_sources": ["electricity"],
            "blocked_sources": ["natural_gas", "freshwater"],
            "hold_code": "HOLD_TEMPORAL_METHOD_INVALID",
            "reason": (
                "Positive interval overlap is not exact temporal support. "
                "ENTSOG hourly and BOM daily-mean values cannot be re-tagged "
                "as the 30-minute target without a prohibited temporal transform."
            ),
        },
        "transforms": {
            "interpolation_performed": False,
            "imputation_performed": False,
            "cross_interval_aggregation_performed": False,
            "implicit_downscaling_performed": False,
            "cross_source_arithmetic_performed": False,
        },
        "raw_sha256_preserved": True,
        "source_provenance_preserved": True,
        "unknown_uncertainty_preserved": True,
        "version_validity_topology_guard_replay_required": True,
        "integrated_real_input_receipt_emitted": True,
        "core_patch_required": False,
        "new_domain_math_added": False,
        "fences": contract["fences"],
        "verdict": contract["verdict_target"],
        "claim_ceiling": (
            "Structural slot mapping and source-native core effects are proven. "
            "Common-window three-source integration is not admitted."
        ),
    }


def write_receipt() -> tuple[dict[str, Any], str]:
    receipt = run_gate()
    body = json.dumps(
        receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"
    OUT_PATH.write_text(body, encoding="utf-8")
    return receipt, hashlib.sha256(body.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    receipt, sha = write_receipt()
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    print("ALIGNED_REAL_INPUT_INTEGRATION_CANARY_RECEIPT_SHA256=" + sha)
