# EQUILIBRIUM Planetary Resource Systems Core V1
## Generic Source Adapter Conformance Harness V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__GENERIC_SOURCE_ADAPTER_CONFORMANCE_HARNESS_V1`

This gate freezes the proven generic source adapter as a tested interface and defines how future provider bindings must qualify before they may call it.

## Tested-interface pins

The conformance harness pins:
- the generic adapter contract;
- the generic adapter implementation;
- the three existing bindings;
- the generic 3-of-3 equality gate;
- the deterministic generic adapter receipt.

A hash mismatch fails before provider conformance is evaluated.

## Minimum binding contract

A provider binding must declare non-empty source identity, provenance, frozen raw file and SHA256, canonical variable mapping, layer and quantity kind, source-local spatial mapping, explicit interval semantics, deterministic freshness policy, uncertainty declaration, and an explicit transform chain.

A provider record must carry:
- value;
- source unit;
- record locator;
- observation/effective timestamp.

## Pre-contract transforms

Only two classes are allowed:

1. `NONE`
   - the source unit is already directly admitted by the frozen empirical contract.

2. `EVIDENCED_POSITIVE_RATIONAL_UNIT_OR_BASIS_ADAPTER`
   - exact positive rational scale;
   - source unit must match the record;
   - target unit must already be admitted by the empirical contract;
   - evidence reference required;
   - visible transform-chain tokens required;
   - natural-gas HHV-labelled targets require explicit HHV basis.

The harness does not permit additive offsets, nonlinear conversions, hidden interpolation, hidden imputation, temporal aggregation, spatial aggregation, provider-specific domain equations, or provider-specific physics engines.

## Fail-closed rejection matrix

The precommitted matrix contains twelve rejection cases:

- missing provider;
- missing record locator;
- malformed raw SHA256;
- raw SHA mismatch;
- negative freshness ceiling;
- empty transform chain;
- direct unit not admitted by the empirical contract;
- pre-contract source-unit mismatch;
- non-positive rational factor;
- missing transform evidence;
- target unit not admitted by the empirical contract;
- gas HHV target without explicit HHV basis.

Each must produce its specified HOLD code.

## Existing binding replay

The frozen Environment Agency freshwater, Elexon electricity, and ENTSOG natural-gas bindings must:

1. pass the conformance validator;
2. traverse the unchanged generic adapter;
3. reproduce the same empirical AdmissionReceipt hash as the proven generic-adapter baseline.

Acceptance is 3/3 conformance plus 3/3 exact receipt equality.

## Scope ceiling

No new source is fetched or ingested.

No provider-specific domain math, multi-source fusion, Equilibrium score, UI, runtime admission, pointer promotion, global bind, or merge is introduced.
