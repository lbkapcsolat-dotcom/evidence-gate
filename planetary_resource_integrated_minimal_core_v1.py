from __future__ import annotations

from fractions import Fraction
from typing import Any, Iterable

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_end_to_end_uncertainty_v1 as e2e
import planetary_resource_process_coefficient_validity_v1 as validity
import planetary_resource_process_manifest_version_v1 as process_version
import planetary_resource_storage_host_topology_bind_v1 as storage_topology


INTERVAL_ID = "T_INT_001"
INTERVAL_START = "2026-10-02T13:00:00Z"
INTERVAL_END = "2026-10-02T13:01:00Z"
MANIFEST_VERSION = "V1"


def _dedupe(items: Iterable[str]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return tuple(out)


def _uncertainty_dict(u: core.Uncertainty) -> dict[str, Any]:
    if isinstance(u, core.ExactUncertainty):
        return {"kind": "EXACT"}
    if isinstance(u, core.IntervalUncertainty):
        return {
            "kind": "INTERVAL",
            "lower": str(u.lower),
            "upper": str(u.upper),
        }
    if isinstance(u, core.MomentUncertainty):
        return {
            "kind": "MOMENT",
            "mean": str(u.mean),
            "variance": str(u.variance),
        }
    if isinstance(u, core.EmpiricalUncertainty):
        return {
            "kind": "EMPIRICAL",
            "samples": [str(x) for x in u.samples],
            "alignment_ref": u.alignment_ref,
        }
    return {"kind": "UNKNOWN"}


def _qv_dict(v: core.QualifiedValue) -> dict[str, Any]:
    return {
        "value": None if v.value is None else str(v.value),
        "unit": v.unit.symbol,
        "layer": v.unit.layer.value,
        "quantity_kind": v.unit.kind.value,
        "gas_basis": v.unit.gas_basis,
        "interval_id": v.interval_id,
        "status": v.status.value,
        "uncertainty": _uncertainty_dict(v.uncertainty),
        "evidence_refs": list(v.evidence_refs),
        "transform_chain": list(v.transform_chain),
        "hold_codes": list(v.hold_codes),
        "freshness": v.freshness,
        "space": v.space.value,
    }


def _rate(
    value: str | int | Fraction,
    layer: core.ResourceLayer,
    *,
    uncertainty: core.Uncertainty | None = None,
    evidence_ref: str,
    transform: str,
) -> core.QualifiedValue:
    return core.QualifiedValue(
        value=core.F(value),
        unit=core.canonical_unit(layer, core.QuantityKind.RATE),
        interval_id=INTERVAL_ID,
        status=core.EpistemicStatus.OBSERVED,
        uncertainty=uncertainty or core.ExactUncertainty(),
        evidence_refs=(evidence_ref,),
        transform_chain=(transform,),
        freshness="FROZEN_SYNTHETIC_FIXTURE",
        space=core.ValueSpace.PHYSICAL,
    )


def _stock(
    value: str | int | Fraction,
    layer: core.ResourceLayer,
    *,
    evidence_ref: str,
) -> core.QualifiedValue:
    return core.QualifiedValue(
        value=core.F(value),
        unit=core.canonical_unit(layer, core.QuantityKind.STOCK),
        interval_id=INTERVAL_ID,
        status=core.EpistemicStatus.OBSERVED,
        uncertainty=core.ExactUncertainty(),
        evidence_refs=(evidence_ref,),
        transform_chain=("fixture:synthetic_stock",),
        freshness="FROZEN_SYNTHETIC_FIXTURE",
        space=core.ValueSpace.PHYSICAL,
    )


def _storage_node_side_delta_rate(
    charge: core.QualifiedValue,
    discharge: core.QualifiedValue,
) -> core.QualifiedValue:
    # This is composition of the already-frozen balance convention A(w-u),
    # not a new storage equation.
    assert charge.value is not None and discharge.value is not None
    uncertainty = core.uncertainty_propagate(
        [Fraction(-1), Fraction(1)],
        [charge.uncertainty, discharge.uncertainty],
    )
    return core.QualifiedValue(
        value=discharge.value - charge.value,
        unit=core.canonical_unit(core.ResourceLayer.ELECTRICITY, core.QuantityKind.RATE),
        interval_id=INTERVAL_ID,
        status=core.EpistemicStatus.DERIVED,
        uncertainty=uncertainty,
        evidence_refs=_dedupe(charge.evidence_refs + discharge.evidence_refs),
        transform_chain=charge.transform_chain
        + discharge.transform_chain
        + ("frozen_balance_storage_convention:A(w-u)",),
        freshness="FROZEN_SYNTHETIC_FIXTURE",
        space=core.ValueSpace.PHYSICAL,
    )


def build_fixture() -> dict[str, Any]:
    electricity_nodes = core.nodes_for(
        core.ResourceLayer.ELECTRICITY, ["E0"], version=MANIFEST_VERSION
    )
    gas_nodes = core.nodes_for(
        core.ResourceLayer.NATURAL_GAS, ["G0"], version=MANIFEST_VERSION
    )
    water_nodes = core.nodes_for(
        core.ResourceLayer.FRESHWATER, ["W0"], version=MANIFEST_VERSION
    )

    time_basis = core.TimeBasis(INTERVAL_ID, Fraction(60))

    storage = core.StorageManifest(
        storage_id="ST_E0",
        layer=core.ResourceLayer.ELECTRICITY,
        host_node_id="E0",
        capacity=Fraction(1000),
        max_charge_rate=Fraction(10),
        max_discharge_rate=Fraction(10),
        eta_charge=Fraction(1),
        eta_discharge=Fraction(1),
        manifest_version=MANIFEST_VERSION,
    )
    active_topology = storage_topology.ActiveTopologySnapshot(
        layer=core.ResourceLayer.ELECTRICITY,
        manifest_version=MANIFEST_VERSION,
        nodes=tuple(electricity_nodes),
    )

    stock = _stock(500, core.ResourceLayer.ELECTRICITY, evidence_ref="SYNTH:STORAGE_STOCK")
    charge = _rate(
        1,
        core.ResourceLayer.ELECTRICITY,
        uncertainty=core.IntervalUncertainty(Fraction(-1, 20), Fraction(1, 20)),
        evidence_ref="SYNTH:STORAGE_CHARGE",
        transform="fixture:storage_charge",
    )
    discharge = _rate(
        Fraction(1, 2),
        core.ResourceLayer.ELECTRICITY,
        uncertainty=core.IntervalUncertainty(Fraction(-1, 50), Fraction(1, 50)),
        evidence_ref="SYNTH:STORAGE_DISCHARGE",
        transform="fixture:storage_discharge",
    )
    self_loss = _rate(
        Fraction(1, 10),
        core.ResourceLayer.ELECTRICITY,
        uncertainty=core.IntervalUncertainty(Fraction(-1, 100), Fraction(1, 100)),
        evidence_ref="SYNTH:STORAGE_SELF_LOSS",
        transform="fixture:storage_self_loss",
    )

    requested_interval = validity.RequestedInterval(
        INTERVAL_ID, INTERVAL_START, INTERVAL_END
    )
    activity = core.QualifiedValue(
        value=Fraction(2),
        unit=core.UnitTag(
            core.ResourceLayer.NATURAL_GAS,
            core.QuantityKind.DIMENSIONLESS,
            "process_activity",
        ),
        interval_id=INTERVAL_ID,
        status=core.EpistemicStatus.OBSERVED,
        uncertainty=core.IntervalUncertainty(Fraction(-1, 20), Fraction(1, 20)),
        evidence_refs=("SYNTH:PROCESS_ACTIVITY",),
        transform_chain=("fixture:cross_layer_process_activity",),
        freshness="FROZEN_SYNTHETIC_FIXTURE",
        space=core.ValueSpace.PHYSICAL,
    )
    process = validity.ValidityBoundedProcessManifest(
        process_id="P_GAS_TO_ELECTRICITY",
        process_class="PHYSICAL_CONVERSION",
        activity_unit="process_activity",
        coefficient_rows=(
            validity.ValidityBoundedProcessCoefficient(
                layer=core.ResourceLayer.ELECTRICITY,
                node_id="E0",
                coefficient=Fraction(2),
                uncertainty=core.IntervalUncertainty(Fraction(-1, 10), Fraction(1, 10)),
                evidence_ref="SYNTH:PROCESS_COEF_E",
                coefficient_unit="W_e/process_activity",
                valid_from="2026-10-02T00:00:00Z",
                valid_to="2026-10-03T00:00:00Z",
            ),
            validity.ValidityBoundedProcessCoefficient(
                layer=core.ResourceLayer.NATURAL_GAS,
                node_id="G0",
                coefficient=Fraction(-5),
                uncertainty=core.IntervalUncertainty(Fraction(-1, 5), Fraction(1, 5)),
                evidence_ref="SYNTH:PROCESS_COEF_G",
                coefficient_unit="W_th/process_activity",
                valid_from="2026-10-02T00:00:00Z",
                valid_to="2026-10-03T00:00:00Z",
            ),
        ),
        source_ref="SYNTH:PROCESS_SOURCE",
        method_ref="SYNTH:PROCESS_METHOD",
        manifest_version=MANIFEST_VERSION,
    )

    gas_boundary_edge = core.BoundaryEdgeManifest(
        boundary_edge_id="G_IMPORT_0",
        layer=core.ResourceLayer.NATURAL_GAS,
        local_node_id="G0",
        direction="IMPORT",
        manifest_version=MANIFEST_VERSION,
    )
    gas_boundary_flow = _rate(
        20,
        core.ResourceLayer.NATURAL_GAS,
        uncertainty=core.IntervalUncertainty(Fraction(-1, 2), Fraction(1, 2)),
        evidence_ref="SYNTH:GAS_BOUNDARY",
        transform="fixture:gas_boundary_import",
    )

    return {
        "electricity_nodes": electricity_nodes,
        "gas_nodes": gas_nodes,
        "water_nodes": water_nodes,
        "time_basis": time_basis,
        "storage": storage,
        "active_topology": active_topology,
        "stock": stock,
        "charge": charge,
        "discharge": discharge,
        "self_loss": self_loss,
        "requested_interval": requested_interval,
        "activity": activity,
        "process": process,
        "gas_boundary_edge": gas_boundary_edge,
        "gas_boundary_flow": gas_boundary_flow,
    }


def run_integrated_system() -> dict[str, Any]:
    fx = build_fixture()

    storage_next = storage_topology.storage_transition_with_topology_bind(
        fx["storage"],
        fx["active_topology"],
        fx["time_basis"],
        fx["stock"],
        fx["charge"],
        fx["discharge"],
        fx["self_loss"],
    )
    storage_delta_rate = _storage_node_side_delta_rate(
        fx["charge"], fx["discharge"]
    )

    electricity_process = process_version.process_coupling_with_manifest_version(
        fx["process"],
        fx["activity"],
        fx["electricity_nodes"],
        target_layer=core.ResourceLayer.ELECTRICITY,
        requested_interval=fx["requested_interval"],
        expected_process_manifest_version=MANIFEST_VERSION,
    )
    gas_process = process_version.process_coupling_with_manifest_version(
        fx["process"],
        fx["activity"],
        fx["gas_nodes"],
        target_layer=core.ResourceLayer.NATURAL_GAS,
        requested_interval=fx["requested_interval"],
        expected_process_manifest_version=MANIFEST_VERSION,
    )

    electricity_balance = e2e.resource_balance_with_uncertainty(
        layer=core.ResourceLayer.ELECTRICITY,
        interval_id=INTERVAL_ID,
        nodes=fx["electricity_nodes"],
        internal_edges=[],
        B=[[]],
        production=[
            _rate(
                Fraction(13, 2),
                core.ResourceLayer.ELECTRICITY,
                uncertainty=core.IntervalUncertainty(Fraction(-1, 10), Fraction(1, 10)),
                evidence_ref="SYNTH:ELEC_PRODUCTION",
                transform="fixture:electricity_production",
            )
        ],
        demand=[
            _rate(
                10,
                core.ResourceLayer.ELECTRICITY,
                evidence_ref="SYNTH:ELEC_DEMAND",
                transform="fixture:electricity_demand",
            )
        ],
        loss=[
            _rate(
                0,
                core.ResourceLayer.ELECTRICITY,
                evidence_ref="SYNTH:ELEC_LOSS",
                transform="fixture:electricity_loss",
            )
        ],
        internal_flow=[],
        storage_delta_rate=[storage_delta_rate],
        process_contribution=electricity_process,
        manifest_version=MANIFEST_VERSION,
    )

    gas_balance = e2e.resource_balance_with_uncertainty(
        layer=core.ResourceLayer.NATURAL_GAS,
        interval_id=INTERVAL_ID,
        nodes=fx["gas_nodes"],
        internal_edges=[],
        B=[[]],
        production=[
            _rate(
                0,
                core.ResourceLayer.NATURAL_GAS,
                evidence_ref="SYNTH:GAS_PRODUCTION",
                transform="fixture:gas_production",
            )
        ],
        demand=[
            _rate(
                10,
                core.ResourceLayer.NATURAL_GAS,
                evidence_ref="SYNTH:GAS_DEMAND",
                transform="fixture:gas_demand",
            )
        ],
        loss=[
            _rate(
                0,
                core.ResourceLayer.NATURAL_GAS,
                evidence_ref="SYNTH:GAS_LOSS",
                transform="fixture:gas_loss",
            )
        ],
        internal_flow=[],
        boundary_edges=[fx["gas_boundary_edge"]],
        boundary_flow=[fx["gas_boundary_flow"]],
        process_contribution=gas_process,
        manifest_version=MANIFEST_VERSION,
    )

    water_balance = e2e.resource_balance_with_uncertainty(
        layer=core.ResourceLayer.FRESHWATER,
        interval_id=INTERVAL_ID,
        nodes=fx["water_nodes"],
        internal_edges=[],
        B=[[]],
        production=[
            _rate(
                3,
                core.ResourceLayer.FRESHWATER,
                uncertainty=core.IntervalUncertainty(Fraction(-1, 5), Fraction(1, 5)),
                evidence_ref="SYNTH:WATER_PRODUCTION",
                transform="fixture:water_production",
            )
        ],
        demand=[
            _rate(
                3,
                core.ResourceLayer.FRESHWATER,
                evidence_ref="SYNTH:WATER_DEMAND",
                transform="fixture:water_demand",
            )
        ],
        loss=[
            _rate(
                0,
                core.ResourceLayer.FRESHWATER,
                evidence_ref="SYNTH:WATER_LOSS",
                transform="fixture:water_loss",
            )
        ],
        internal_flow=[],
        manifest_version=MANIFEST_VERSION,
    )

    balances = {
        "ELECTRICITY": electricity_balance["E0"],
        "NATURAL_GAS": gas_balance["G0"],
        "FRESHWATER": water_balance["W0"],
    }
    process_outputs = {
        "ELECTRICITY": electricity_process["E0"],
        "NATURAL_GAS": gas_process["G0"],
    }

    input_evidence = _dedupe(
        (
            "SYNTH:STORAGE_STOCK",
            "SYNTH:STORAGE_CHARGE",
            "SYNTH:STORAGE_DISCHARGE",
            "SYNTH:STORAGE_SELF_LOSS",
            "SYNTH:PROCESS_ACTIVITY",
            "SYNTH:PROCESS_COEF_E",
            "SYNTH:PROCESS_COEF_G",
            "SYNTH:PROCESS_SOURCE",
            "SYNTH:PROCESS_METHOD",
            "SYNTH:ELEC_PRODUCTION",
            "SYNTH:ELEC_DEMAND",
            "SYNTH:ELEC_LOSS",
            "SYNTH:GAS_PRODUCTION",
            "SYNTH:GAS_DEMAND",
            "SYNTH:GAS_LOSS",
            "SYNTH:GAS_BOUNDARY",
            "SYNTH:WATER_PRODUCTION",
            "SYNTH:WATER_DEMAND",
            "SYNTH:WATER_LOSS",
        )
    )
    output_evidence = _dedupe(
        tuple(storage_next.evidence_refs)
        + tuple(x for v in balances.values() for x in v.evidence_refs)
        + tuple(x for v in process_outputs.values() for x in v.evidence_refs)
    )

    state = {
        "schema_version": "EQUILIBRIUM_PRS_INTEGRATED_MINIMAL_STATE_V1",
        "integration_mode": "FROZEN_SYNTHETIC_PHYSICAL_FIXTURE",
        "interval": {
            "interval_id": INTERVAL_ID,
            "start": INTERVAL_START,
            "end": INTERVAL_END,
            "delta_t_seconds": "60",
        },
        "layers": ["ELECTRICITY", "NATURAL_GAS", "FRESHWATER"],
        "nodes": {
            "ELECTRICITY": ["E0"],
            "NATURAL_GAS": ["G0"],
            "FRESHWATER": ["W0"],
        },
        "counts": {
            "resource_layers": 3,
            "nodes": 3,
            "frozen_intervals": 1,
            "storages": 1,
            "boundary_edges": 1,
            "boundary_flows": 1,
            "cross_layer_processes": 1,
            "process_target_layers": 2,
        },
        "storage": {
            "storage_id": "ST_E0",
            "host_node_id": "E0",
            "next_stock": _qv_dict(storage_next),
            "node_side_delta_rate": _qv_dict(storage_delta_rate),
        },
        "boundary": {
            "boundary_edge_id": "G_IMPORT_0",
            "target_node_id": "G0",
            "direction": "IMPORT",
            "flow": _qv_dict(fx["gas_boundary_flow"]),
        },
        "process": {
            "process_id": "P_GAS_TO_ELECTRICITY",
            "manifest_version": MANIFEST_VERSION,
            "requested_interval": {
                "interval_id": INTERVAL_ID,
                "start": INTERVAL_START,
                "end": INTERVAL_END,
            },
            "target_layers": ["ELECTRICITY", "NATURAL_GAS"],
            "outputs": {k: _qv_dict(v) for k, v in process_outputs.items()},
        },
        "balances": {k: _qv_dict(v) for k, v in balances.items()},
        "input_evidence_refs": list(input_evidence),
        "output_evidence_refs": list(output_evidence),
        "full_evidence_lineage_preserved": set(input_evidence).issubset(set(output_evidence)),
        "real_source_bindings_consumed": False,
        "new_source_ingest": False,
        "real_multi_source_fusion": False,
        "core_patch_required": False,
        "new_domain_math_added": False,
    }
    state["state_sha256"] = core.canonical_sha256(state)
    return state
