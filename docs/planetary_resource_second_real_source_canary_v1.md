# EQUILIBRIUM Planetary Resource Systems Core V1
## Second Real Source Single Variable Admission Canary V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__SECOND_REAL_SOURCE_SINGLE_VARIABLE_ADMISSION_CANARY_V1`

This successor canary verifies that the frozen empirical admission architecture works on a different physical layer from the first freshwater canary.

## Source

Provider:
Elexon Insights Solution

Underlying source:
National Energy System Operator (NESO)

Dataset:
INDO — Initial National Demand outturn

Record:
- startTime: 2026-10-01T22:00:00Z
- publishTime: 2026-10-01T22:30:00Z
- settlementDate: 2026-10-01
- settlementPeriod: 47
- demand: 22557 MW

The exact API response is frozen byte-for-byte and pinned by SHA256.

## Model mapping

Variable:

`electricity.consumption_rate`

Target node:

`ELEXON_INDO_NATIONAL_SOURCE_LOCAL_ELECTRICITY_ZONE`

Target class:

`ELECTRICITY_ZONE`

Spatial mapping:

`NODE_LOOKUP`

The target is a source-local accounting node for the INDO national-demand series. It is not asserted to equal all final electricity consumption in Great Britain.

## Temporal semantics

The source is treated as one half-hour mean demand interval corresponding to the INDO settlement-period record.

No aggregation, interpolation, or imputation occurs in this canary.

## Units

Source:
MW

Canonical:
W_e

Transform:
MW × 1,000,000 = W_e

For the frozen record:

22557 MW = 22557000000 W_e

## Freshness

Admission timestamp:
2026-10-01T22:45:14Z

Observed interval start:
2026-10-01T22:00:00Z

Age at admission:
2714 seconds

Maximum allowed:
7200 seconds

This is a freshness readback at admission time only.

## Uncertainty

No measurement-uncertainty model is supplied with the frozen source record, therefore the empirical contract preserves uncertainty as:

`UNKNOWN`

No promotion to EXACT is allowed.

## Claim ceiling

This gate proves one electricity-demand record can pass the same empirical source-admission boundary used by the freshwater canary.

It does not prove:
- total final electricity consumption;
- multi-source fusion;
- cross-layer integration;
- aggregation;
- calibrated stress;
- Equilibrium score;
- forecast;
- UI correctness;
- runtime admission;
- global bind;
- production readiness.
