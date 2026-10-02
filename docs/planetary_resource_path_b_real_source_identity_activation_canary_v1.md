# PATH B Real-Source Identity Activation Canary V1

This gate performs the first bounded real-source execution through the proven
temporal-support kernel.

Pinned executable-kernel receipt:

`3383f715a41126f7218b79e52d1ca7bcd6946effa9b70fa5a1af237b2f38e18b`

Operator:

- `TEMPORAL_SUPPORT_TO_TARGET_WINDOW_OPERATOR_V1`
- version `V1`
- support relation allowed in this gate: `EXACT_TARGET_SUPPORT` only

## Real input

Provider: Elexon Insights Solution  
Dataset: INDO  
Variable: `electricity.consumption_rate`

Raw repository object:

`sources/elexon/INDO_outturn_alignment_window_2026-09-30.json`

Pinned raw evidence:

- bytes: `278348`
- SHA256:
  `2a91d6b47379b47e4d8cfdb220d90c890ce416ebcd094b9810de70d47db12564`

The selected source record begins at
`2026-09-30T12:00:00Z`. Its already-proven settlement-period semantics give
an end bound of `2026-09-30T12:30:00Z`, exactly equal to the canary target.

The real record carries `initialDemandOutturn = 21575 MW`.

## Identity canary

The source-derived value and interval are passed into the executable kernel as
one UNKNOWN-uncertainty cell.

Required result:

- decision `PASS_IDENTITY`
- support relation `EXACT_TARGET_SUPPORT`
- formula `IDENTITY_V1`
- output value exactly `21575`
- output uncertainty remains `UNKNOWN`

No partition aggregation is permitted.

## Real provenance

The canary emits a separate real-source operator transform record that binds
the kernel result to the actual Elexon raw SHA256, URL, path, source record,
source and target support, operator spec/version, input/output value and
uncertainty, and the identity formula.

The executable kernel's synthetic internal reference provenance is not used as
real-source authority.

## Activation boundary

PATH_B is activated only inside this one canary:

`CANARY_LOCAL_IDENTITY_ONLY`

It is not globally activated and receives no runtime admission. After the
canary the global state remains:

`LOCKED_NOT_GLOBALLY_ACTIVATED`

No gas, freshwater, cross-source composition, coarse-to-fine transform,
interpolation, imputation, core patch, EQ score, UI, pointer promotion, global
bind, or merge occurs.

Verdict target:

`PASS_BOUNDED_PATH_B_REAL_SOURCE_IDENTITY_ACTIVATION_CANARY`
