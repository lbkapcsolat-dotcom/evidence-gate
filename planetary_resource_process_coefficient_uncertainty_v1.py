from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping, Sequence

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_process_typed_dimensional_closure_v1 as typed


class ProcessCoefficientUncertaintyHold(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code=code
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(frozen=True)
class UncertainProcessCoefficient:
    layer: core.ResourceLayer
    node_id: str
    coefficient: Fraction
    uncertainty: core.Uncertainty
    evidence_ref: str
    coefficient_unit: str


@dataclass(frozen=True)
class UncertainProcessManifest:
    process_id: str
    process_class: str
    activity_unit: str
    coefficient_rows: tuple[UncertainProcessCoefficient, ...]
    source_ref: str
    method_ref: str
    manifest_version: str = "V1"


@dataclass(frozen=True)
class JointMomentProductEvidence:
    covariance_delta_activity_coefficient: Fraction
    e_delta_activity_sq_delta_coefficient: Fraction
    e_delta_activity_delta_coefficient_sq: Fraction
    e_delta_activity_sq_delta_coefficient_sq: Fraction
    evidence_ref: str


def _base_manifest(process: UncertainProcessManifest) -> core.ProcessManifest:
    return core.ProcessManifest(
        process.process_id,
        process.process_class,
        process.activity_unit,
        tuple(
            core.ProcessCoefficient(
                row.layer,
                row.node_id,
                row.coefficient,
                row.evidence_ref,
                row.coefficient_unit,
            )
            for row in process.coefficient_rows
        ),
        process.source_ref,
        process.method_ref,
        process.manifest_version,
    )


def _nonexact(u: core.Uncertainty) -> bool:
    return not isinstance(u, core.ExactUncertainty)


def _interval_product_perturbation(
    a0: Fraction,
    ua: core.IntervalUncertainty,
    c0: Fraction,
    uc: core.IntervalUncertainty,
) -> core.IntervalUncertainty:
    vals=[
        (a0+da)*(c0+dc)-a0*c0
        for da in (ua.lower,ua.upper)
        for dc in (uc.lower,uc.upper)
    ]
    return core.IntervalUncertainty(min(vals),max(vals))


def _empirical_product_perturbation(
    a0: Fraction,
    ua: core.EmpiricalUncertainty,
    c0: Fraction,
    uc: core.EmpiricalUncertainty,
    *,
    sample_alignment_ref: str | None,
) -> core.EmpiricalUncertainty:
    if (
        not sample_alignment_ref
        or ua.alignment_ref != sample_alignment_ref
        or uc.alignment_ref != sample_alignment_ref
        or len(ua.samples) != len(uc.samples)
    ):
        raise core.HoldError(core.HoldCode.HOLD_SAMPLE_ALIGNMENT_REQUIRED)
    vals=tuple(
        (a0+da)*(c0+dc)-a0*c0
        for da,dc in zip(ua.samples,uc.samples)
    )
    return core.EmpiricalUncertainty(vals,sample_alignment_ref)


def _moment_product_perturbation(
    a0: Fraction,
    ua: core.MomentUncertainty,
    c0: Fraction,
    uc: core.MomentUncertainty,
    *,
    joint: JointMomentProductEvidence | None,
) -> core.MomentUncertainty:
    if joint is None:
        raise core.HoldError(core.HoldCode.HOLD_COVARIANCE_REQUIRED)
    if not joint.evidence_ref:
        raise core.HoldError(core.HoldCode.HOLD_COVARIANCE_REQUIRED)

    mu_a=ua.mean
    mu_c=uc.mean
    e_a2=ua.variance+mu_a*mu_a
    e_c2=uc.variance+mu_c*mu_c
    e_ac=joint.covariance_delta_activity_coefficient+mu_a*mu_c

    mean_z=c0*mu_a+a0*mu_c+e_ac
    e_z2=(
        c0*c0*e_a2
        + a0*a0*e_c2
        + joint.e_delta_activity_sq_delta_coefficient_sq
        + 2*c0*a0*e_ac
        + 2*c0*joint.e_delta_activity_sq_delta_coefficient
        + 2*a0*joint.e_delta_activity_delta_coefficient_sq
    )
    var_z=e_z2-mean_z*mean_z
    if var_z < 0:
        raise core.HoldError(core.HoldCode.HOLD_UNCERTAINTY_OPERATOR)
    return core.MomentUncertainty(mean_z,var_z)


def _product_uncertainty(
    a0: Fraction,
    ua: core.Uncertainty,
    c0: Fraction,
    uc: core.Uncertainty,
    *,
    joint_moment: JointMomentProductEvidence | None = None,
    sample_alignment_ref: str | None = None,
) -> core.Uncertainty:
    if isinstance(ua,core.UnknownUncertainty) or isinstance(uc,core.UnknownUncertainty):
        return core.UnknownUncertainty()

    if isinstance(ua,core.ExactUncertainty) and isinstance(uc,core.ExactUncertainty):
        return core.ExactUncertainty()

    if isinstance(ua,core.ExactUncertainty):
        out=typed._scale_uncertainty(uc,a0)
    elif isinstance(uc,core.ExactUncertainty):
        out=typed._scale_uncertainty(ua,c0)
    elif isinstance(ua,core.IntervalUncertainty) and isinstance(uc,core.IntervalUncertainty):
        out=_interval_product_perturbation(a0,ua,c0,uc)
    elif isinstance(ua,core.EmpiricalUncertainty) and isinstance(uc,core.EmpiricalUncertainty):
        out=_empirical_product_perturbation(
            a0,ua,c0,uc,sample_alignment_ref=sample_alignment_ref
        )
    elif isinstance(ua,core.MomentUncertainty) and isinstance(uc,core.MomentUncertainty):
        out=_moment_product_perturbation(
            a0,ua,c0,uc,joint=joint_moment
        )
    else:
        raise core.HoldError(core.HoldCode.HOLD_UNCERTAINTY_OPERATOR)

    if (_nonexact(ua) or _nonexact(uc)) and isinstance(out,core.ExactUncertainty):
        raise ProcessCoefficientUncertaintyHold(
            "HOLD_SILENT_COEFFICIENT_UNCERTAINTY_LOSS"
        )
    return out


def process_coupling_with_coefficient_uncertainty(
    process: UncertainProcessManifest,
    activity: core.QualifiedValue,
    target_nodes: Sequence[core.NodeManifest],
    *,
    target_layer: core.ResourceLayer,
    interval_id: str,
    joint_moment_by_node: Mapping[str,JointMomentProductEvidence] | None = None,
    sample_alignment_ref_by_node: Mapping[str,str] | None = None,
) -> dict[str,core.QualifiedValue]:
    base=_base_manifest(process)
    nominal=typed.process_coupling_typed(
        base,
        activity,
        target_nodes,
        target_layer=target_layer,
        interval_id=interval_id,
    )

    rows_by_node={
        n.node_id:[
            row for row in process.coefficient_rows
            if row.layer is target_layer and row.node_id==n.node_id
        ]
        for n in target_nodes if n.layer is target_layer
    }

    out={}
    for nid,base_qv in nominal.items():
        rows=rows_by_node[nid]
        uncertain=[row for row in rows if _nonexact(row.uncertainty)]
        if len(uncertain)>1:
            raise ProcessCoefficientUncertaintyHold(
                "HOLD_PROCESS_COEFFICIENT_CROSS_COVARIANCE_REQUIRED",
                nid,
            )

        c0=sum((row.coefficient for row in rows),Fraction(0))
        coeff_uncertainty=(
            core.ExactUncertainty()
            if not uncertain
            else uncertain[0].uncertainty
        )
        joint=(joint_moment_by_node or {}).get(nid)
        alignment=(sample_alignment_ref_by_node or {}).get(nid)

        output_uncertainty=_product_uncertainty(
            activity.value,
            activity.uncertainty,
            c0,
            coeff_uncertainty,
            joint_moment=joint,
            sample_alignment_ref=alignment,
        )

        evidence=base_qv.evidence_refs
        if joint is not None and joint.evidence_ref not in evidence:
            evidence=evidence+(joint.evidence_ref,)

        chain=base_qv.transform_chain+(
            f"coefficient_uncertainty:{type(coeff_uncertainty).__name__}",
        )
        if joint is not None:
            chain=chain+("coefficient_joint_moments:explicit",)

        out[nid]=core.QualifiedValue(
            value=base_qv.value,
            unit=base_qv.unit,
            interval_id=base_qv.interval_id,
            status=base_qv.status,
            uncertainty=output_uncertainty,
            evidence_refs=evidence,
            transform_chain=chain,
            hold_codes=base_qv.hold_codes,
            freshness=base_qv.freshness,
            space=base_qv.space,
        )
    return out
