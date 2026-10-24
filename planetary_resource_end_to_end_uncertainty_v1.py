from __future__ import annotations

from fractions import Fraction
from typing import Iterable, Mapping, Sequence

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_process_typed_dimensional_closure_v1 as typed


class EndToEndUncertaintyHold(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code=code
        super().__init__(f"{code}: {detail}" if detail else code)


def _dedupe(items: Iterable[str]) -> tuple[str,...]:
    seen=set()
    out=[]
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return tuple(out)


def _freshness_summary(values: Sequence[core.QualifiedValue]) -> str | None:
    vals=[v.freshness for v in values if v.freshness is not None]
    if not vals:
        return None
    uniq=_dedupe(vals)
    return uniq[0] if len(uniq)==1 else "MIXED"


def _derived_status(values: Sequence[core.QualifiedValue]) -> core.EpistemicStatus:
    return (
        core.EpistemicStatus.IMPUTED
        if any(v.status is core.EpistemicStatus.IMPUTED for v in values)
        else core.EpistemicStatus.DERIVED
    )


def _linear_uncertainty(
    coefficients: Sequence[Fraction],
    values: Sequence[core.QualifiedValue],
    *,
    covariance: Sequence[Sequence[Fraction]] | None = None,
    sample_alignment_ref: str | None = None,
) -> core.Uncertainty:
    if len(coefficients) != len(values):
        raise core.HoldError(core.HoldCode.HOLD_UNCERTAINTY_OPERATOR)

    uncertainties=[v.uncertainty for v in values]
    if any(isinstance(u,core.UnknownUncertainty) for u in uncertainties):
        return core.UnknownUncertainty()

    nonexact_types={
        type(u) for u in uncertainties
        if not isinstance(u,core.ExactUncertainty)
    }
    if not nonexact_types:
        return core.ExactUncertainty()

    if len(nonexact_types) > 1:
        raise core.HoldError(core.HoldCode.HOLD_UNCERTAINTY_OPERATOR)

    only=next(iter(nonexact_types))
    if only is core.IntervalUncertainty:
        out=core.uncertainty_propagate(coefficients,uncertainties)
    elif only is core.MomentUncertainty:
        idx=[i for i,u in enumerate(uncertainties) if isinstance(u,core.MomentUncertainty)]
        if covariance is None:
            raise core.HoldError(core.HoldCode.HOLD_COVARIANCE_REQUIRED)
        if len(covariance)!=len(idx) or any(len(row)!=len(idx) for row in covariance):
            raise core.HoldError(core.HoldCode.HOLD_COVARIANCE_REQUIRED)
        out=core.uncertainty_propagate(
            [coefficients[i] for i in idx],
            [uncertainties[i] for i in idx],
            covariance=covariance,
        )
    elif only is core.EmpiricalUncertainty:
        idx=[i for i,u in enumerate(uncertainties) if isinstance(u,core.EmpiricalUncertainty)]
        if not sample_alignment_ref:
            raise core.HoldError(core.HoldCode.HOLD_SAMPLE_ALIGNMENT_REQUIRED)
        out=core.uncertainty_propagate(
            [coefficients[i] for i in idx],
            [uncertainties[i] for i in idx],
            sample_alignment_ref=sample_alignment_ref,
        )
    else:
        raise core.HoldError(core.HoldCode.HOLD_UNCERTAINTY_OPERATOR)

    if any(not isinstance(u,core.ExactUncertainty) for u in uncertainties) and isinstance(out,core.ExactUncertainty):
        raise EndToEndUncertaintyHold("HOLD_RAW_UNCERTAINTY_LOSS")
    return out


def _metadata(values: Sequence[core.QualifiedValue], transform: str):
    evidence=_dedupe(x for v in values for x in v.evidence_refs)
    chains=tuple(x for v in values for x in v.transform_chain)
    holds=_dedupe(x for v in values for x in v.hold_codes)
    statuses="|".join(v.status.value for v in values)
    return {
        "status":_derived_status(values),
        "evidence_refs":evidence,
        "transform_chain":chains+(f"input_statuses:{statuses}",transform),
        "hold_codes":holds,
        "freshness":_freshness_summary(values),
        "space":core.ValueSpace.PHYSICAL,
    }


def resource_balance_with_uncertainty(
    *,
    layer: core.ResourceLayer,
    interval_id: str,
    nodes: Sequence[core.NodeManifest],
    internal_edges: Sequence[core.InternalEdgeManifest],
    B: Sequence[Sequence[Fraction]],
    production: Sequence[core.QualifiedValue],
    demand: Sequence[core.QualifiedValue],
    loss: Sequence[core.QualifiedValue],
    internal_flow: Sequence[core.QualifiedValue],
    boundary_edges: Sequence[core.BoundaryEdgeManifest]=(),
    boundary_flow: Sequence[core.QualifiedValue]=(),
    storage_delta_rate: Sequence[core.QualifiedValue] | None=None,
    process_contribution: Mapping[str,core.QualifiedValue] | None=None,
    manifest_version: str="V1",
    covariance_by_node: Mapping[str,Sequence[Sequence[Fraction]]] | None=None,
    sample_alignment_ref_by_node: Mapping[str,str] | None=None,
) -> dict[str,core.QualifiedValue]:
    numeric=typed.resource_balance_residual_typed(
        layer=layer,
        interval_id=interval_id,
        nodes=nodes,
        internal_edges=internal_edges,
        B=B,
        production=production,
        demand=demand,
        loss=loss,
        internal_flow=internal_flow,
        boundary_edges=boundary_edges,
        boundary_flow=boundary_flow,
        storage_delta_rate=storage_delta_rate,
        process_contribution=process_contribution,
        manifest_version=manifest_version,
    )

    node_index={n.node_id:i for i,n in enumerate(nodes)}
    boundary_by_node={n.node_id:[] for n in nodes}
    for edge,value in zip(boundary_edges,boundary_flow):
        sign=Fraction(1) if edge.direction=="IMPORT" else Fraction(-1)
        boundary_by_node[edge.local_node_id].append((sign,value))

    out={}
    for i,node in enumerate(nodes):
        coeffs=[]
        vals=[]
        def add(c,v):
            coeffs.append(Fraction(c))
            vals.append(v)

        add(1,production[i])
        add(-1,demand[i])
        add(-1,loss[i])
        for j,flow in enumerate(internal_flow):
            if B[i][j] != 0:
                add(Fraction(B[i][j]),flow)
        for sign,v in boundary_by_node[node.node_id]:
            add(sign,v)
        if storage_delta_rate is not None:
            add(1,storage_delta_rate[i])
        if process_contribution is not None and node.node_id in process_contribution:
            add(1,process_contribution[node.node_id])

        uncertainty=_linear_uncertainty(
            coeffs,
            vals,
            covariance=(covariance_by_node or {}).get(node.node_id),
            sample_alignment_ref=(sample_alignment_ref_by_node or {}).get(node.node_id),
        )
        meta=_metadata(vals,"balance:e2e_uncertainty")
        out[node.node_id]=core.QualifiedValue(
            value=numeric[node.node_id],
            unit=core.canonical_unit(layer,core.QuantityKind.RATE),
            interval_id=interval_id,
            uncertainty=uncertainty,
            **meta,
        )
    return out


def storage_transition_with_uncertainty(
    storage: core.StorageManifest,
    time_basis: core.TimeBasis,
    stock: core.QualifiedValue,
    charge: core.QualifiedValue,
    discharge: core.QualifiedValue,
    *,
    self_loss_rate: Fraction=Fraction(0),
    covariance: Sequence[Sequence[Fraction]] | None=None,
    sample_alignment_ref: str | None=None,
) -> core.QualifiedValue:
    numeric=core.storage_transition(
        storage,time_basis,stock,charge,discharge,self_loss_rate=self_loss_rate
    )
    values=[stock,charge,discharge]
    coefficients=[
        Fraction(1),
        time_basis.delta_t*storage.eta_charge,
        -time_basis.delta_t/storage.eta_discharge,
    ]
    uncertainty=_linear_uncertainty(
        coefficients,
        values,
        covariance=covariance,
        sample_alignment_ref=sample_alignment_ref,
    )
    meta=_metadata(values,"storage:e2e_uncertainty")
    return core.QualifiedValue(
        value=numeric.value,
        unit=stock.unit,
        interval_id=time_basis.interval_id,
        uncertainty=uncertainty,
        **meta,
    )
