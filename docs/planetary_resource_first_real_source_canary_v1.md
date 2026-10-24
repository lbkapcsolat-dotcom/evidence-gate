# EQUILIBRIUM Planetary Resource Systems Core V1
## First Real Source Single Variable Admission Canary V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__FIRST_REAL_SOURCE_SINGLE_VARIABLE_ADMISSION_CANARY_V1`

This canary admits exactly one real observation into the already frozen empirical admission contract.

## Frozen source snapshot

Provider: Environment Agency  
Dataset: Flood Monitoring Real Time API, version 0.9  
Station: Farmoor, stationReference 1100TH  
Parameter: flow  
Value type: mean  
Period: 900 seconds  
Observation timestamp: 2026-10-01T21:30:00Z  
Observed value: 0.832 m3/s

The exact retrieved JSON response is preserved byte-for-byte in the repository and pinned by SHA256.

## Model mapping

Variable:

`freshwater.internal_flow_rate`

Target node:

`EA_1100TH_FARMOOR_SOURCE_LOCAL_FLOW_ACCOUNTING_UNIT`

Target class:

`WATER_BASIN_OR_ACCOUNTING_UNIT`

Spatial method:

`NODE_LOOKUP`

This is a source-local gauge accounting unit only. The canary does **not** interpret the observation as a Thames-basin aggregate.

## Temporal semantics

The source reports a 900-second mean and a reading datetime. The canary uses one exact source/target interval identity:

`EA_1100TH_2026-10-01T21:30:00Z_MEAN_900S`

No start boundary is invented beyond the source's own period metadata.

## Uncertainty

The source snapshot does not provide a measurement-uncertainty model. Therefore uncertainty is preserved as:

`UNKNOWN`

It is not promoted to EXACT.

## Missingness

The value is present and status is OBSERVED. Zero remains distinct from missing.

## Freshness

Freshness is evaluated deterministically at the recorded retrieval timestamp:

2026-10-01T22:35:53Z

Age at admission: 3953 seconds.  
Allowed maximum: 7200 seconds.

This freshness result is a readback **at admission time**, not a claim that the frozen observation remains current forever.

## Claim ceiling

A PASS proves only one real source record was accepted by the frozen empirical admission gate with explicit provenance, unit, spatial, temporal, freshness, uncertainty, and missingness semantics.

It does not prove:
- Thames-basin-wide flow;
- global freshwater state;
- multi-source fusion;
- global dataset admission;
- calibrated stress;
- forecast;
- Equilibrium score;
- UI correctness;
- runtime admission;
- production readiness.
