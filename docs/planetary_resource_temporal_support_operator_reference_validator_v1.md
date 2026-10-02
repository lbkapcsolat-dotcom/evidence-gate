# Temporal Support Operator Reference Validator V1

This gate validates the frozen formal temporal-support specification using
synthetic fixtures only.

Pinned formal specification receipt:

`f8c9d8eebacd3fbc19111fe4d9e5600eb6555ce58709666652e06b6beff5ca5a`

PATH_B remains locked. No real source is transformed and no production temporal
operator is activated.

## Reference fixtures

The validator executes nine synthetic cases.

`EXACT_SUPPORT_IDENTITY` passes with the identity relation.

`TWO_15MIN_NATIVE_MEANS_TO_ONE_30MIN_TARGET` passes conservatively. For
synthetic native means 10 and 20 over two adjacent 900-second cells:

`x_target = (10*900 + 20*900) / 1800 = 15`

and the conservation identity is exact:

`15*1800 = 10*900 + 20*900 = 27000`

All arithmetic is rational rather than floating-point.

A single 60-minute mean cannot determine a strict 30-minute target and holds
with `HOLD_TEMPORAL_INFORMATION_INSUFFICIENT`.

A partition with either a gap or overlap holds with
`HOLD_TEMPORAL_PARTITION_OVERLAP_OR_GAP`.

UNKNOWN uncertainty remains UNKNOWN.

MOMENT uncertainty without covariance holds with
`HOLD_TEMPORAL_UNCERTAINTY_OPERATOR`.

Incomplete provenance holds with
`HOLD_TEMPORAL_PROVENANCE_INCOMPLETE`.

An unpinned operator version holds with
`HOLD_TEMPORAL_OPERATOR_VERSION_UNPINNED`.

## Scope boundary

This validator is an executable reference checker for the specification, not
the PATH_B production operator. Its fixtures are synthetic. It performs no real
source transformation, no PATH_B activation, no real value composition, and no
core patch.

Verdict target:

`PASS_BOUNDED_TEMPORAL_SUPPORT_OPERATOR_REFERENCE_VALIDATOR`
