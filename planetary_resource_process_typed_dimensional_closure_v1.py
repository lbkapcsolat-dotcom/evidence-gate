from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from typing import Mapping, Sequence

import equilibrium_planetary_resource_core_v1 as core


class TypedProcessHold(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


def _dedupe(items):
    seen=set()
    out=[]
    for x in items:
        if x not in seen:
            seen.add(x); out.append(x)
    return tuple(out)


def _scale_uncertainty(u: core.Uncertainty, c: Fraction) -> core.Uncertainty:
    if isinstance(u, core.ExactUncertainty):
        return core.ExactUncertainty()
    if isinstance(u, core.IntervalUncertainty):
        vals=(c*u.lower,c*u.upper)
        return core.IntervalUncertainty(min(vals),max(vals))
    if isinstance(u, core.MomentUncertainty):
        return core.MomentUncertainty(c*u.mean,c*c*u.variance)
    if isinstance(u, core.EmpiricalUncertainty):
        return core.EmpiricalUncertainty(tuple(c*x for x in u.samples),u.alignment_ref)
    return core.UnknownUncertainty()


def _expected_coefficient_unit(target_layer: core.ResourceLayer, activity_unit: str) -> str:
    target=core.canonical_unit(target_layer,core.QuantityKind.RATE)
    return f"{target.symbol}/{activity_unit}"


def process_coupling_typed(
    process: core.ProcessManifest,
    activity: core.QualifiedValue,
    target_nodes: Sequence[core.NodeManifest],
    *,
    target_layer: core.ResourceLayer,
    interval_id: str,
) -> dict[str, core.QualifiedValue]:
    if process.process_class.upper() in {"CORRELATION","ASSOCIATION","EDITORIAL"}:
        raise core.HoldError(core.HoldCode.HOLD_CAUSALITY)
    if not process.source_ref or not process.method_ref:
        raise core.HoldError(core.HoldCode.HOLD_PROCESS_EVIDENCE)

    core.qualified_value_guard(activity, core.GuardPolicy.ALLOW_IMPUTED_WITH_FLAG)
    if activity.interval_id != interval_id:
        raise core.HoldError(core.HoldCode.HOLD_TIME_BASIS_MISMATCH)
    if activity.value is None:
        raise core.HoldError(core.HoldCode.HOLD_MISSING_INPUT)
    if activity.unit.symbol != process.activity_unit:
        raise TypedProcessHold(
            "HOLD_PROCESS_ACTIVITY_UNIT_MISMATCH",
            f"{activity.unit.symbol} != {process.activity_unit}",
        )

    node_ids={n.node_id for n in target_nodes if n.layer is target_layer}
    coeff_sum={nid:Fraction(0) for nid in node_ids}
    evidence={nid:[] for nid in node_ids}

    expected_unit=_expected_coefficient_unit(target_layer,process.activity_unit)
    for row in process.coefficient_rows:
        if not row.evidence_ref:
            raise core.HoldError(core.HoldCode.HOLD_PROCESS_EVIDENCE)
        if not row.coefficient_unit:
            raise core.HoldError(core.HoldCode.HOLD_PROCESS_UNIT)
        if row.layer is not target_layer:
            continue
        if row.node_id not in node_ids:
            raise core.HoldError(core.HoldCode.HOLD_PROCESS_SCOPE)
        if row.coefficient_unit != expected_unit:
            raise TypedProcessHold(
                "HOLD_PROCESS_COEFFICIENT_DIMENSION_MISMATCH",
                f"{row.coefficient_unit} != {expected_unit}",
            )
        coeff_sum[row.node_id] += row.coefficient
        evidence[row.node_id].append(row.evidence_ref)

    target_unit=core.canonical_unit(target_layer,core.QuantityKind.RATE)
    out={}
    for nid in node_ids:
        c=coeff_sum[nid]
        ev=_dedupe(activity.evidence_refs + (process.source_ref,process.method_ref) + tuple(evidence[nid]))
        chain=activity.transform_chain + (
            f"process:{process.process_id}",
            f"activity_unit:{process.activity_unit}",
            f"coefficient_unit:{expected_unit}",
            f"coefficient:{c}",
        )
        out[nid]=core.QualifiedValue(
            value=c*activity.value,
            unit=target_unit,
            interval_id=interval_id,
            status=activity.status,
            uncertainty=_scale_uncertainty(activity.uncertainty,c),
            evidence_refs=ev,
            transform_chain=chain,
            hold_codes=activity.hold_codes,
            freshness=activity.freshness,
            space=activity.space,
        )
    return out


def _validate_typed_process_map(
    process_contribution: Mapping[str, core.QualifiedValue],
    *,
    layer: core.ResourceLayer,
    interval_id: str,
    node_ids: set[str],
) -> dict[str,Fraction]:
    numeric={}
    expected=core.canonical_unit(layer,core.QuantityKind.RATE)
    for nid,v in process_contribution.items():
        if nid not in node_ids:
            raise core.HoldError(core.HoldCode.HOLD_PROCESS_SCOPE)
        if not isinstance(v,core.QualifiedValue):
            raise TypedProcessHold("HOLD_PROCESS_TYPED_VALUE_REQUIRED",nid)
        core.qualified_value_guard(v,core.GuardPolicy.ALLOW_IMPUTED_WITH_FLAG)
        if v.unit != expected:
            raise TypedProcessHold(
                "HOLD_PROCESS_TARGET_UNIT_MISMATCH",
                f"{v.unit} != {expected}",
            )
        if v.interval_id != interval_id:
            raise core.HoldError(core.HoldCode.HOLD_TIME_BASIS_MISMATCH)
        if v.space is not core.ValueSpace.PHYSICAL:
            raise core.HoldError(
                core.HoldCode.HOLD_AUDIT_PHYSICAL_MIX
                if v.space in (core.ValueSpace.AUDIT,core.ValueSpace.EVIDENCE)
                else core.HoldCode.HOLD_STRESS_PHYSICAL_MIX
            )
        if v.value is None:
            raise core.HoldError(core.HoldCode.HOLD_MISSING_INPUT)
        numeric[nid]=v.value
    return numeric


def resource_balance_residual_typed(*, process_contribution=None, **kwargs):
    nodes=kwargs["nodes"]
    layer=kwargs["layer"]
    interval_id=kwargs["interval_id"]
    numeric=None
    if process_contribution is not None:
        if not isinstance(process_contribution,Mapping):
            raise TypedProcessHold("HOLD_PROCESS_TYPED_VALUE_REQUIRED","not a mapping")
        numeric=_validate_typed_process_map(
            process_contribution,
            layer=layer,
            interval_id=interval_id,
            node_ids={n.node_id for n in nodes},
        )
    return core.resource_balance_residual(
        **kwargs,
        process_contribution=numeric,
    )
