from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Sequence

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_process_coefficient_uncertainty_v1 as pc


class ProcessCoefficientValidityHold(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code=code
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(frozen=True)
class RequestedInterval:
    interval_id: str
    start: str
    end: str


@dataclass(frozen=True)
class ValidityBoundedProcessCoefficient:
    layer: core.ResourceLayer
    node_id: str
    coefficient: core.Fraction
    uncertainty: core.Uncertainty
    evidence_ref: str
    coefficient_unit: str
    valid_from: str | None
    valid_to: str | None


@dataclass(frozen=True)
class ValidityBoundedProcessManifest:
    process_id: str
    process_class: str
    activity_unit: str
    coefficient_rows: tuple[ValidityBoundedProcessCoefficient, ...]
    source_ref: str
    method_ref: str
    manifest_version: str = "V1"


def _parse_aware_iso(value: str, *, field_name: str) -> datetime:
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except Exception as exc:
        raise ProcessCoefficientValidityHold(
            "HOLD_PROCESS_COEFFICIENT_VALIDITY_INVALID",
            f"{field_name}: {value}",
        ) from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ProcessCoefficientValidityHold(
            "HOLD_PROCESS_COEFFICIENT_VALIDITY_INVALID",
            f"{field_name} must be timezone-aware",
        )
    return dt.astimezone(timezone.utc)


def _validate_requested_interval(requested: RequestedInterval) -> tuple[datetime,datetime]:
    start=_parse_aware_iso(requested.start,field_name="requested_start")
    end=_parse_aware_iso(requested.end,field_name="requested_end")
    if not start < end:
        raise ProcessCoefficientValidityHold(
            "HOLD_PROCESS_COEFFICIENT_VALIDITY_INVALID",
            "requested interval must satisfy start < end",
        )
    return start,end


def _validate_row_validity(
    row: ValidityBoundedProcessCoefficient,
    requested_start: datetime,
    requested_end: datetime,
    *,
    validity_required: bool,
) -> tuple[datetime | None,datetime | None]:
    if row.valid_from is None or row.valid_to is None:
        if validity_required:
            raise ProcessCoefficientValidityHold(
                "HOLD_PROCESS_COEFFICIENT_VALIDITY_REQUIRED",
                f"{row.node_id} missing valid_from/valid_to",
            )
        return None,None

    valid_from=_parse_aware_iso(row.valid_from,field_name="valid_from")
    valid_to=_parse_aware_iso(row.valid_to,field_name="valid_to")
    if not valid_from < valid_to:
        raise ProcessCoefficientValidityHold(
            "HOLD_PROCESS_COEFFICIENT_VALIDITY_INVALID",
            f"{row.node_id}: valid_from must be before valid_to",
        )

    if valid_to <= requested_start:
        raise ProcessCoefficientValidityHold(
            "HOLD_PROCESS_COEFFICIENT_EXPIRED",
            row.node_id,
        )
    if valid_from >= requested_end:
        raise ProcessCoefficientValidityHold(
            "HOLD_PROCESS_COEFFICIENT_NOT_YET_VALID",
            row.node_id,
        )
    if valid_from > requested_start or valid_to < requested_end:
        raise ProcessCoefficientValidityHold(
            "HOLD_PROCESS_COEFFICIENT_PARTIAL_INTERVAL_OVERLAP",
            row.node_id,
        )
    return valid_from,valid_to


def _uncertain_manifest(
    process: ValidityBoundedProcessManifest,
) -> pc.UncertainProcessManifest:
    return pc.UncertainProcessManifest(
        process.process_id,
        process.process_class,
        process.activity_unit,
        tuple(
            pc.UncertainProcessCoefficient(
                row.layer,
                row.node_id,
                row.coefficient,
                row.uncertainty,
                row.evidence_ref,
                row.coefficient_unit,
            )
            for row in process.coefficient_rows
        ),
        process.source_ref,
        process.method_ref,
        process.manifest_version,
    )


def process_coupling_with_coefficient_validity(
    process: ValidityBoundedProcessManifest,
    activity: core.QualifiedValue,
    target_nodes: Sequence[core.NodeManifest],
    *,
    target_layer: core.ResourceLayer,
    requested_interval: RequestedInterval,
    validity_required: bool = True,
    joint_moment_by_node: Mapping[str,pc.JointMomentProductEvidence] | None = None,
    sample_alignment_ref_by_node: Mapping[str,str] | None = None,
) -> dict[str,core.QualifiedValue]:
    requested_start,requested_end=_validate_requested_interval(requested_interval)

    validated_windows={}
    for row in process.coefficient_rows:
        if row.layer is target_layer:
            validated_windows.setdefault(row.node_id,[]).append(
                _validate_row_validity(
                    row,
                    requested_start,
                    requested_end,
                    validity_required=validity_required,
                )
            )

    out=pc.process_coupling_with_coefficient_uncertainty(
        _uncertain_manifest(process),
        activity,
        target_nodes,
        target_layer=target_layer,
        interval_id=requested_interval.interval_id,
        joint_moment_by_node=joint_moment_by_node,
        sample_alignment_ref_by_node=sample_alignment_ref_by_node,
    )

    result={}
    for nid,qv in out.items():
        chain=qv.transform_chain+(
            f"requested_interval:[{requested_interval.start},{requested_interval.end})",
        )
        for valid_from,valid_to in validated_windows.get(nid,()):
            if valid_from is not None and valid_to is not None:
                chain=chain+(
                    "coefficient_validity:"
                    f"[{valid_from.isoformat()},{valid_to.isoformat()})",
                )
        result[nid]=core.QualifiedValue(
            value=qv.value,
            unit=qv.unit,
            interval_id=qv.interval_id,
            status=qv.status,
            uncertainty=qv.uncertainty,
            evidence_refs=qv.evidence_refs,
            transform_chain=chain,
            hold_codes=qv.hold_codes,
            freshness=qv.freshness,
            space=qv.space,
        )
    return result
