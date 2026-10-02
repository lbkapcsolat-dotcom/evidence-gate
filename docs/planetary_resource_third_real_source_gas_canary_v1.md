# EQUILIBRIUM Planetary Resource Systems Core V1
## Third Real Source Natural Gas Single Variable Admission Canary V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__THIRD_REAL_SOURCE_NATURAL_GAS_SINGLE_VARIABLE_ADMISSION_CANARY_V1`

This canary verifies the frozen empirical admission architecture on the natural-gas layer without using any volume-to-energy conversion.

## Measurement source

Provider: ENTSOG Transparency Platform

Indicator: Physical Flow

Operator: Gasunie Deutschland

Point: Dornum / NETRA (GUD)

Direction: entry

Source record interval:
- UTC start: 2026-10-01T21:00:00Z
- UTC end: 2026-10-01T22:00:00Z

Source value:
- 28,669,751 kWh/h

Source flow status:
- Provisional

Exactly one measurement row is frozen byte-for-byte.

## Energy basis

The source publishes Actual Physical Flow in an energy-rate unit, `kWh/h`.

Authoritative support evidence is frozen separately:

1. ENTSOG publication format: Actual Physical Flow is published in kWh/d or kWh/h.
2. Commission Regulation (EU) 2015/703, Article 13: gas energy is expressed in kWh based on Gross Calorific Value (GCV).
3. ISO 6976 terminology: gross calorific/heating value is synonymous with higher calorific/heating value.

Therefore the source adapter performs only:

`kWh/h_GCV -> kW_HHV`

with factor 1.

The unchanged empirical contract then performs:

`kW_HHV -> W_th`

with factor 1000.

No gas volume is converted into energy. No numeric calorific value is inserted or inferred.

## Model mapping

Variable:

`natural_gas.import_rate`

Target node:

`ENTSOG_DE_TSO_0005_ITP_00188_ENTRY_SOURCE_LOCAL_GAS_ZONE`

Target class:

`GAS_ZONE`

Spatial method:

`NODE_LOOKUP`

This is a source-local ENTSOG entry-flow accounting node. It is not a claim about total German gas imports.

## Temporal semantics

One exact hourly source interval is admitted.

No aggregation, interpolation, or imputation is performed.

For deterministic freshness, the completed interval end is used as the observation-effective timestamp.

## Uncertainty

No measurement-uncertainty model is provided with the frozen source row.

Uncertainty therefore remains:

`UNKNOWN`

It is not promoted to EXACT.

## Claim ceiling

A PASS proves one ENTSOG natural-gas physical-flow record passed the unchanged empirical admission boundary with explicit GCV/HHV basis handling.

It does not prove:
- total German gas imports;
- national gas balance;
- multi-source fusion;
- cross-layer coupling;
- physical calibration;
- stress;
- forecast;
- Equilibrium score;
- runtime admission;
- production readiness.
