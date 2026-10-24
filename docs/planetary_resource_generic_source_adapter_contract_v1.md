# EQUILIBRIUM Planetary Resource Systems Core V1
## Generic Source Adapter Contract V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__GENERIC_SOURCE_ADAPTER_CONTRACT_V1`

This gate extracts one provider-neutral source-adapter interface from the already-proven freshwater, electricity, and natural-gas canaries. It ingests no new source.

## Shared interface

The adapter accepts two immutable objects:

1. `GenericSourceRecord`
   - source value
   - source unit
   - exact record locator
   - observation/effective timestamp

2. `GenericAdapterSpec`
   - provenance
   - canonical variable mapping
   - source layer and quantity kind
   - source-local spatial mapping
   - explicit temporal interval
   - deterministic freshness policy
   - uncertainty and missingness declarations
   - transform-chain evidence
   - optional pre-contract unit/basis transform

The adapter returns the unchanged empirical-admission `AdmissionReceipt`.

## Provider binding boundary

Provider bindings may only:

- parse already-frozen raw bytes;
- extract source fields;
- declare source semantics;
- declare unit/basis evidence;
- declare source-local spatial mapping;
- declare source interval metadata.

Provider bindings may not implement:

- resource balance equations;
- storage equations;
- cross-resource process mathematics;
- stress models;
- aggregate Equilibrium scores;
- provider-specific physics engines.

## Pre-contract transform

A pre-contract transform is declarative:

`source value × rational factor → contract-recognized source unit`

It requires:
- explicit source and target units;
- exact rational factor;
- evidence reference;
- visible transform-chain tokens.

For the current natural-gas canary:

`kWh/h_GCV → kW_HHV`

has factor 1 and evidence-backed GCV/HHV semantics. The frozen empirical contract then performs `kW_HHV → W_th`.

Freshwater and electricity need no pre-contract transform.

## Receipt equality

The decisive acceptance rule is not merely “same result”.

For each of the three canaries:

`generic_adapter_empirical_receipt == existing_canary_empirical_receipt`

field-for-field.

The legacy canary path remains the comparison oracle. The generic interface must reproduce it without changing source bytes, canary semantics, claim ceilings, or the empirical-admission validator.

## Scope ceiling

This gate does not:
- fetch or ingest a new source;
- fuse providers;
- aggregate resources;
- compute an Equilibrium score;
- add UI;
- admit runtime use;
- promote pointers;
- globally bind;
- merge.
