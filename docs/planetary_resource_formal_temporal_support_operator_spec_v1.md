# Formal Temporal Support Operator Spec V1

This gate specifies PATH_B without activating or executing it.

Pinned temporal-support policy receipt:

`5cfbb2feb2b7485e5f791f062794929e134981277d6c29679b7cbc12219fb6b9`

## Formal signature

`T_spec(Q_source_set, S_source_partition, S_target, support_semantics_ref, uncertainty_bundle, provenance_bundle) -> Q_target_candidate OR HOLD`

The signature is a specification only. No executable operator is defined in
this gate.

Both source and target supports use explicit positive-duration half-open UTC
intervals `[start,end)`.

## Admissible support relations

Only two support relations are admitted by the spec:

1. `EXACT_TARGET_SUPPORT`
2. `FINER_NATIVE_MEAN_PARTITION_EXACTLY_COVERS_TARGET`

Containment alone is insufficient. Coarse-to-fine temporal projection is not
admissible. An instantaneous sample cannot silently become an interval mean.

## Conservation semantics

For exact support, the identity operator preserves the source value.

For a target that is exactly partitioned by non-overlapping source-native
time-mean cells, the formal conservative relation is:

`x_target = SUM_i(x_i * delta_t_i) / delta_t_target`

with conservation identity:

`x_target * delta_t_target = SUM_i(x_i * delta_t_i)`

This is an exact duration-weighted aggregation of declared native means, not
interpolation, downscaling, imputation, or an assumption that a coarse value is
constant inside a subinterval.

If a coarse mean is asked to determine a strict subinterval, or if support
information is otherwise insufficient, the physical action is HOLD.

## Uncertainty

- UNKNOWN remains UNKNOWN.
- EXACT remains exact only when all required inputs are exact.
- INTERVAL uses positive-duration weighted linear propagation.
- MOMENT requires covariance or HOLD.
- EMPIRICAL requires a sample-alignment reference or HOLD.
- uncertainty may not be narrowed without evidence.
- UNKNOWN may not be promoted to EXACT.

## Provenance

Every future operator result must carry an auditable transform record including
the pinned operator spec/version, policy receipt SHA, source raw hashes and
URLs, source cell intervals, target interval, support relation, conservation
mode, formula id, unit transform chain, uncertainty kinds, input evidence refs,
and hold codes. Raw evidence refs must survive the transform chain.

## Fail-closed behavior

The formal registry includes explicit holds for insufficient temporal
information, non-exact target partitions, overlap/gaps, variable/layer mismatch,
unit/kind mismatch, undeclared conservation semantics, nonconservative physical
admission, uncertainty failure, incomplete provenance, unpinned operator
version, and PATH_B not being activated.

Verdict:

`PASS_BOUNDED_FORMAL_TEMPORAL_SUPPORT_OPERATOR_SPEC`

This PASS is specification-only. The operator is not executed, PATH_B is not
activated, and no value composition occurs.
