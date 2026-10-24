from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_storage_self_loss_typed_v1 as typed_loss


class StorageTopologyHold(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(frozen=True)
class ActiveTopologySnapshot:
    layer: core.ResourceLayer
    manifest_version: str
    nodes: tuple[core.NodeManifest, ...]


def _validate_active_topology(
    storage: core.StorageManifest,
    active_topology: ActiveTopologySnapshot | None,
) -> core.NodeManifest:
    if not isinstance(active_topology, ActiveTopologySnapshot):
        raise StorageTopologyHold("HOLD_ACTIVE_TOPOLOGY_BIND_REQUIRED")

    if active_topology.layer is not storage.layer:
        raise StorageTopologyHold(
            "HOLD_STORAGE_HOST_NODE_LAYER_MISMATCH",
            f"storage={storage.layer.value}, topology={active_topology.layer.value}",
        )
    if not active_topology.manifest_version:
        raise StorageTopologyHold("HOLD_ACTIVE_TOPOLOGY_VERSION_MISMATCH")

    for node in active_topology.nodes:
        if node.layer is not active_topology.layer:
            raise StorageTopologyHold(
                "HOLD_STORAGE_HOST_NODE_LAYER_MISMATCH",
                f"{node.node_id}: node={node.layer.value}, topology={active_topology.layer.value}",
            )
        if node.manifest_version != active_topology.manifest_version:
            raise StorageTopologyHold(
                "HOLD_ACTIVE_TOPOLOGY_VERSION_MISMATCH",
                f"{node.node_id}: node={node.manifest_version}, topology={active_topology.manifest_version}",
            )

    if storage.manifest_version != active_topology.manifest_version:
        raise StorageTopologyHold(
            "HOLD_STORAGE_HOST_NODE_VERSION_MISMATCH",
            f"storage={storage.manifest_version}, topology={active_topology.manifest_version}",
        )

    candidates = [n for n in active_topology.nodes if n.node_id == storage.host_node_id]
    if not candidates:
        raise StorageTopologyHold(
            "HOLD_STORAGE_HOST_NODE_MISSING",
            storage.host_node_id,
        )

    host = candidates[0]
    if host.layer is not storage.layer:
        raise StorageTopologyHold(
            "HOLD_STORAGE_HOST_NODE_LAYER_MISMATCH",
            storage.host_node_id,
        )
    if host.manifest_version != storage.manifest_version:
        raise StorageTopologyHold(
            "HOLD_STORAGE_HOST_NODE_VERSION_MISMATCH",
            f"host={host.manifest_version}, storage={storage.manifest_version}",
        )
    return host


def storage_transition_with_topology_bind(
    storage: core.StorageManifest,
    active_topology: ActiveTopologySnapshot | None,
    time_basis: core.TimeBasis,
    stock: core.QualifiedValue,
    charge: core.QualifiedValue,
    discharge: core.QualifiedValue,
    self_loss: core.QualifiedValue,
    *,
    covariance: Sequence[Sequence[Fraction]] | None = None,
    sample_alignment_ref: str | None = None,
) -> core.QualifiedValue:
    host = _validate_active_topology(storage, active_topology)

    out = typed_loss.storage_transition_with_typed_self_loss(
        storage,
        time_basis,
        stock,
        charge,
        discharge,
        self_loss,
        covariance=covariance,
        sample_alignment_ref=sample_alignment_ref,
    )

    return core.QualifiedValue(
        value=out.value,
        unit=out.unit,
        interval_id=out.interval_id,
        status=out.status,
        uncertainty=out.uncertainty,
        evidence_refs=out.evidence_refs,
        transform_chain=out.transform_chain + (
            f"storage_host_node:{host.node_id}",
            f"active_topology_layer:{active_topology.layer.value}",
            f"active_topology_manifest_version:{active_topology.manifest_version}",
        ),
        hold_codes=out.hold_codes,
        freshness=out.freshness,
        space=out.space,
    )
