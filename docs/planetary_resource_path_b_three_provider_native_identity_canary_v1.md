# PATH B Three-Provider Native Identity Canary V1

This gate proves that the same executable temporal-support kernel can admit
three already-pinned real providers independently under native exact-support
identity semantics.

Pinned predecessor receipt:

`9a0c62c606a8c688ea535b02f2a6ba390e4a6d4f61fe7698ff7a09546d3c70af`

## Providers

### Elexon

- layer: ELECTRICITY
- raw SHA256:
  `2a91d6b47379b47e4d8cfdb220d90c890ce416ebcd094b9810de70d47db12564`
- native interval:
  `2026-09-30T12:00:00Z -> 2026-09-30T12:30:00Z`
- input: `21575 MW`
- uncertainty: UNKNOWN

### ENTSOG

- layer: NATURAL_GAS
- raw SHA256:
  `889e9bf2e6365893bfed18a50291a0d130559fa1e38484c71d8e278e82f64be5`
- native interval:
  `2026-09-30T12:00:00Z -> 2026-09-30T13:00:00Z`
- input: `26823568 kWh/h`
- uncertainty: UNKNOWN

The native UTC interval is recovered from the already-proven explicit bounds
embedded in the ENTSOG record id. No display-time reinterpretation is added.

### Australian Bureau of Meteorology

- layer: FRESHWATER
- raw SHA256:
  `1fe8f1416b69377160ed6c9fced011785a46e7cb52eac46ce783a424c3e7ee14`
- explicit native interval:
  `2026-09-29T14:00:00Z -> 2026-09-30T14:00:00Z`
- published input: `0.378 cumec = 189/500 cumec`
- uncertainty: UNKNOWN

The interval comes directly from WaterML
`gml:beginPosition` / `gml:endPosition`.

## Identity contract

Each provider is executed separately through:

`TEMPORAL_SUPPORT_TO_TARGET_WINDOW_OPERATOR_V1 / V1`

with:

`EXACT_TARGET_SUPPORT -> IDENTITY_V1`

Each provider's target is exactly its own native source interval.

Required:

- 3/3 `PASS_IDENTITY`
- output equals input exactly
- UNKNOWN remains UNKNOWN
- raw SHA256 bound into a real-source transform record per provider

## Temporal boundary

No common window is calculated in this gate.

`common_window_computed = false`

The three native intervals stay distinct. There is no cross-provider temporal
alignment, resampling, partition aggregation, interpolation, imputation,
coarse-to-fine transform, or cross-source value composition.

PATH_B activation is local to this canary only. Global PATH_B remains locked,
and no runtime or production admission is granted.

Verdict target:

`PASS_BOUNDED_PATH_B_THREE_PROVIDER_NATIVE_IDENTITY_CANARY`
