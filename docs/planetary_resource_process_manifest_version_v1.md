# EQUILIBRIUM Planetary Resource Systems Core V1
## Process Manifest Version Enforcement V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__PROCESS_MANIFEST_VERSION_ENFORCEMENT_V1`

This gate closes the process-manifest version gap while preserving the pinned coefficient-validity and coefficient-uncertainty successors.

## Version contract

The caller must supply an explicit non-empty `expected_process_manifest_version`.

Admission requires:

- `process.manifest_version == expected_process_manifest_version`;
- every target-layer node has `node.manifest_version == expected_process_manifest_version`.

There is no implicit fallback to the process version, node version, or a hard-coded default.

## Fail-closed cases

Missing or empty expected version:

`HOLD_PROCESS_MANIFEST_VERSION_REQUIRED`

Process manifest mismatch:

`HOLD_PROCESS_MANIFEST_VERSION_MISMATCH`

Target-layer node manifest mismatch:

`HOLD_TARGET_NODE_MANIFEST_VERSION_MISMATCH`

## Preservation

The successor delegates time applicability, coefficient uncertainty, dimensional unit checking, and typed process arithmetic to the already-proven predecessor path.

It preserves:

- coefficient validity intervals;
- coefficient uncertainty;
- coefficient evidence refs;
- process source/method evidence;
- activity epistemic status and evidence;
- transform chain;
- freshness;
- PHYSICAL value space.

Successful outputs append explicit process and target-node manifest-version entries to the transform chain.

## Scope ceiling

No provider work, new source ingest, multi-source fusion, aggregate EQ score, UI, runtime admission, pointer promotion, global binding, or merge is authorized.
