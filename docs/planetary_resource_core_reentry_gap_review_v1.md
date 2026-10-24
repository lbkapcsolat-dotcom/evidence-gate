# EQUILIBRIUM Planetary Resource Systems Core V1
## Core Reentry and Unresolved Kernel Gap Review V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__CORE_REENTRY_AND_UNRESOLVED_KERNEL_GAP_REVIEW_V1`

The source-adapter subsystem is pinned frozen. This review performs no provider work and changes no core implementation.

## Reviewed core areas

### Balance kernel

Bounded proof remains in place for incidence conservation, production-demand-loss arithmetic, internal directed flow, boundary net flow, storage delta-rate input, typed primitive layer/rate/time checks, topology versioning, and double-loss protection.

Unresolved: `process_contribution` enters `resource_balance_residual` as `Mapping[str, Fraction]`. It therefore carries no `UnitTag`, `ValueSpace`, epistemic status, uncertainty, or evidence refs.

### Storage kernel

The deterministic transition path remains proven for capacity, rate limits, charge/discharge efficiency domain, stock/rate separation, time basis, and deterministic next-state arithmetic.

Unresolved but not selected first: uncertain stock/flow inputs do not propagate through the storage result. The current result returns `ExactUncertainty`.

### Process coupling

Existing guards prove evidence presence, source/method presence, target-node scope, causal-class rejection, and interval consistency.

The dimensional contract is incomplete:

- `coefficient_unit` is only required to be nonempty;
- it is not checked against the target canonical rate divided by `process.activity_unit`;
- the runtime activity `UnitTag.symbol` is not checked against `process.activity_unit`;
- the output is an untyped numeric mapping.

Executable review probes demonstrate both a deliberately mismatched coefficient unit and a mismatched activity-unit symbol survive the current process path.

### Boundary flow

The bounded typed directional path remains proven for IMPORT/EXPORT direction, nonnegative directed flows, layer/rate/time signature checks, topology scope, and deterministic import-export-net decomposition.

### Uncertainty path

The standalone affine uncertainty operator remains proven for:

- exact;
- interval;
- moment with covariance;
- empirical with sample alignment.

It is not yet an end-to-end property of the balance kernel because balance output is a raw numeric mapping.

### Audit vector

L1-L4 remain four separate bounded components. Aggregate Equilibrium scoring remains prohibited. Audit/evidence/stress primitive inputs remain excluded from physical balance arithmetic.

The audit vector is still a bare tuple, but this is not the selected next blocker because it does not currently enter the physical balance residual.

## Next single unproven capability

Selected:

`PROCESS_COUPLING_TYPED_DIMENSIONAL_CLOSURE_V1`

Reason:

The process path is currently the only reviewed physical-balance ingress that can bypass the typed physical-value boundary with a raw numeric mapping. Closing that path restores a uniform fail-closed unit/evidence boundary across all physical contributions.

This review does not implement the successor gate.
