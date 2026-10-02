# Temporal Support Operator Executable Kernel V1

This gate implements the frozen temporal-support specification as an executable
pure kernel while keeping PATH_B locked.

Pinned reference-validator receipt:

`152ecba00cfcb9e22f767b654bd04631222fb73a3d4666d9ce4e635647267973`

Pinned formal operator spec:

- id: `TEMPORAL_SUPPORT_TO_TARGET_WINDOW_OPERATOR_V1`
- version: `V1`
- receipt:
  `f8c9d8eebacd3fbc19111fe4d9e5600eb6555ce58709666652e06b6beff5ca5a`

## Executable support relations

The kernel implements only the two relations frozen by the formal spec:

1. `EXACT_TARGET_SUPPORT`
2. `FINER_NATIVE_MEAN_PARTITION_EXACTLY_COVERS_TARGET`

Arithmetic uses Python `Fraction` throughout. The conservative operator
therefore verifies:

`x_target * delta_t_target = SUM_i(x_i * delta_t_i)`

as an exact rational equality.

## Reference replay

All nine frozen reference fixtures are replayed by the new kernel rather than
delegated back to the reference validator. The expected outcomes are reproduced
9/9.

## Uncertainty

- EXACT remains EXACT when every required input is exact.
- UNKNOWN propagates as UNKNOWN and cannot be promoted to EXACT.
- INTERVAL uses the frozen positive-duration weighted linear rule.
- MOMENT without the required covariance information fails closed.
- No new covariance formula is invented in V1 because the frozen formal spec
  did not define one.

A separate synthetic interval probe maps two adjacent 15-minute interval inputs
to one 30-minute interval result with exact bounds
`[27/2, 33/2]`.

## Provenance

Every successful result emits the frozen provenance transform record fields:
operator spec/version, policy receipt, variable/layer/kind, synthetic source
hashes and URLs, source intervals, target interval, support relation,
conservation mode, formula id, unit transform chain, input/output uncertainty
kinds, evidence refs and hold codes.

## Mutation guards

The gate requires seven safe outcomes:

- GAP -> HOLD
- OVERLAP -> HOLD
- COARSE_TO_FINE -> HOLD
- UNKNOWN_TO_EXACT -> UNKNOWN remains UNKNOWN
- MISSING_COVARIANCE -> HOLD
- MISSING_PROVENANCE -> HOLD
- UNPINNED_VERSION -> HOLD

## Scope boundary

This is an executable isolated kernel, not PATH_B activation. Only synthetic
fixtures are executed. No real source enters the kernel, no real value
composition occurs, and no runtime admission is granted.

Verdict target:

`PASS_BOUNDED_TEMPORAL_SUPPORT_OPERATOR_EXECUTABLE_KERNEL`
