# EQUILIBRIUM Planetary Resource Systems Core V1
## Process Coupling Typed Dimensional Closure V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__PROCESS_COUPLING_TYPED_DIMENSIONAL_CLOSURE_V1`

This gate closes the process-coupling ingress identified by the core reentry review.

The pinned predecessor core is not rewritten. The closure is implemented as an additive successor typed boundary over the frozen core so prior receipts and 40/40 baselines remain byte-valid.

## Typed process contribution

A process contribution is now represented as a `QualifiedValue` physical rate rather than a raw `Fraction`.

For every target-layer contribution the successor path preserves:

- canonical target-layer rate unit;
- activity epistemic status;
- scaled activity uncertainty;
- activity evidence refs plus process source/method/coefficient evidence;
- activity transform chain plus explicit process and coefficient transforms;
- activity hold codes;
- freshness;
- physical value space.

## Dimensional closure

The runtime activity unit symbol must equal `process.activity_unit`.

Each process coefficient unit must equal:

`<canonical target rate symbol>/<process.activity_unit>`

Examples:

- electricity: `W_e/activity`
- natural gas: `W_th/activity`
- crude oil: `kg/s/activity`
- freshwater: `m3/s/activity`

Natural-gas output uses the canonical HHV-tagged `W_th` UnitTag.

## Typed balance ingress

The successor balance wrapper accepts only:

`Mapping[node_id, QualifiedValue]`

for process contributions.

Raw numeric process maps are rejected before entering the frozen balance kernel.

Typed contributions are checked for:

- target node scope;
- exact canonical target-layer rate unit;
- interval equality;
- physical value space;
- non-missing value.

Only after these checks are numeric values projected into the pinned predecessor residual calculation.

## Uncertainty preservation

Scalar process coefficients propagate uncertainty exactly for the supported V1 uncertainty forms:

- EXACT remains EXACT;
- INTERVAL endpoints scale with sign-safe ordering;
- MOMENT mean scales by `c` and variance by `c²`;
- EMPIRICAL samples scale pointwise and preserve alignment ref;
- UNKNOWN remains UNKNOWN.

## Claim ceiling

This gate proves a typed successor process-coupling and balance-ingress path.

It does not mutate or supersede the pinned predecessor core bytes.

It does not add provider work, source ingestion, multi-source fusion, Equilibrium scoring, UI, runtime admission, pointer promotion, global binding, or merge.
