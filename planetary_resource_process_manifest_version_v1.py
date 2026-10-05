from __future__ import annotations

from typing import Mapping, Sequence

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_process_coefficient_uncertainty_v1 as pc
import planetary_resource_process_coefficient_validity_v1 as pv


class ProcessManifestVersionHold(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code=code
        super().__init__(f"{code}: {detail}" if detail else code)


def _validate_versions(
    process: pv.ValidityBoundedProcessManifest,
    target_nodes: Sequence[core.NodeManifest],
    *,
    target_layer: core.ResourceLayer,
    expected_process_manifest_version: str,
) -> None:
    if not isinstance(expected_process_manifest_version,str) or not expected_process_manifest_version.strip():
        raise ProcessManifestVersionHold(
            "HOLD_PROCESS_MANIFEST_VERSION_REQUIRED"
        )
    expected=expected_process_manifest_version.strip()

    if process.manifest_version != expected:
        raise ProcessManifestVersionHold(
            "HOLD_PROCESS_MANIFEST_VERSION_MISMATCH",
            f"process={process.manifest_version}, expected={expected}",
        )

    target_layer_nodes=[n for n in target_nodes if n.layer is target_layer]
    for node in target_layer_nodes:
        if node.manifest_version != expected:
            raise ProcessManifestVersionHold(
                "HOLD_TARGET_NODE_MANIFEST_VERSION_MISMATCH",
                f"{node.node_id}: node={node.manifest_version}, expected={expected}",
            )


def process_coupling_with_manifest_version(
    process: pv.ValidityBoundedProcessManifest,
    activity: core.QualifiedValue,
    target_nodes: Sequence[core.NodeManifest],
    *,
    target_layer: core.ResourceLayer,
    requested_interval: pv.RequestedInterval,
    expected_process_manifest_version: str,
    validity_required: bool = True,
    joint_moment_by_node: Mapping[str,pc.JointMomentProductEvidence] | None = None,
    sample_alignment_ref_by_node: Mapping[str,str] | None = None,
) -> dict[str,core.QualifiedValue]:
    _validate_versions(
        process,
        target_nodes,
        target_layer=target_layer,
        expected_process_manifest_version=expected_process_manifest_version,
    )

    out=pv.process_coupling_with_coefficient_validity(
        process,
        activity,
        target_nodes,
        target_layer=target_layer,
        requested_interval=requested_interval,
        validity_required=validity_required,
        joint_moment_by_node=joint_moment_by_node,
        sample_alignment_ref_by_node=sample_alignment_ref_by_node,
    )

    expected=expected_process_manifest_version.strip()
    result={}
    for nid,qv in out.items():
        result[nid]=core.QualifiedValue(
            value=qv.value,
            unit=qv.unit,
            interval_id=qv.interval_id,
            status=qv.status,
            uncertainty=qv.uncertainty,
            evidence_refs=qv.evidence_refs,
            transform_chain=qv.transform_chain+(
                f"process_manifest_version:{expected}",
                f"target_node_manifest_version:{expected}",
            ),
            hold_codes=qv.hold_codes,
            freshness=qv.freshness,
            space=qv.space,
        )
    return result
