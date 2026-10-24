# EQUILIBRIUM Planetary Resource Systems Core V1
## Storage Host-Node Topology Bind V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__STORAGE_HOST_NODE_TOPOLOGY_BIND_V1`

This gate closes the storage host/topology binding gap over the pinned typed-self-loss path.

The successor introduces an explicit `ActiveTopologySnapshot` with:
- resource layer;
- manifest version;
- active nodes.

Admission requires:
- the active topology layer equals the storage layer;
- the storage manifest version equals the active topology version;
- every node in the snapshot matches the snapshot layer and version;
- `storage.host_node_id` exists in the active topology;
- the host node matches the storage layer and manifest version.

Fail-closed cases include:
- `HOLD_ACTIVE_TOPOLOGY_BIND_REQUIRED`;
- `HOLD_STORAGE_HOST_NODE_MISSING`;
- `HOLD_STORAGE_HOST_NODE_LAYER_MISMATCH`;
- `HOLD_STORAGE_HOST_NODE_VERSION_MISMATCH`;
- `HOLD_ACTIVE_TOPOLOGY_VERSION_MISMATCH`.

The successor delegates storage arithmetic and self-loss uncertainty propagation to the already-proven typed self-loss path. Storage uncertainty, self-loss evidence, epistemic status, freshness, transform chain and PHYSICAL value space remain preserved.

No provider work, source ingest, fusion, EQ score, UI, runtime admission, pointer promotion, global binding, or merge is authorized.
