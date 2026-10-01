# EQUILIBRIUM Planetary Resource Systems Core V1
## Empirical Data Contract and Source Admission V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__EMPIRICAL_DATA_CONTRACT_AND_SOURCE_ADMISSION_V1`

This gate defines the boundary between the frozen synthetic mathematical core and any future external observations. It does **not** ingest a dataset.

## 1. Frozen variable dictionary

The V1 empirical surface contains 36 primitive balance-input variables:

- 4 resource layers: electricity, natural gas, crude oil, freshwater.
- 9 roles per layer: stock, production, consumption, loss, internal flow, import, export, storage charge, storage discharge.

Process-activity variables are intentionally excluded from this primitive dictionary because process coefficients and activity units require their own evidence-bearing contract.

## 2. Canonical units

The contract reuses the mathematical core's canonical physical units:

| Layer | Stock | Rate | Basis |
| --- | --- | --- | --- |
| Electricity | J_e | W_e | physical electricity |
| Natural gas | J_gas | W_th | HHV |
| Crude oil | kg_crude | kg/s | mass |
| Freshwater | m3 | m3/s | volume |

Only explicit dimension-preserving conversions in the machine-readable contract are admitted. Gas volume to energy requires calorific-value and HHV/LHV evidence. Oil volume to mass requires density and temperature-basis evidence. Those context-dependent conversions are HOLD by default.

## 3. Provenance contract

Every candidate observation must carry:

source ID, provider, dataset ID, dataset version, record locator, observation time, retrieval time, raw SHA256, citation, license or terms reference, and access class.

A missing or malformed provenance field fails closed.

## 4. Spatial mapping contract

Permitted mapping methods are frozen in the JSON contract. Every mapping names the target node, the target node class, and a method reference. Area-weighted mappings must provide weights summing exactly to one.

There is no implicit nearest-neighbour assignment.

## 5. Temporal alignment contract

Permitted methods:

`EXACT_INTERVAL`, `TIME_WEIGHTED_MEAN`, `END_OF_INTERVAL_STOCK`, `SUM_SUBINTERVALS`, `INTEGRATE_RATE`.

Non-exact alignment requires an explicit method reference. Interpolation and imputation are OFF by default. If used, each requires an explicit method reference and remains visible in the transform chain.

## 6. Freshness contract

Freshness is evaluated against an explicit deterministic `as_of` timestamp and a declared maximum age. It never depends on hidden wall-clock state.

Stale input is HOLD by default.

## 7. Uncertainty admission

Supported states are EXACT, INTERVAL, MOMENT, EMPIRICAL, and UNKNOWN.

UNKNOWN cannot be silently upgraded to EXACT. Aggregated MOMENT uncertainty requires covariance evidence. Aggregated EMPIRICAL uncertainty requires sample-alignment evidence.

## 8. Missingness semantics

Zero is a valid physical value and is never synonymous with missing.

A missing value requires one explicit reason from the frozen missingness vocabulary. Missing observations may be preserved as evidence records, but are not admitted as physical state values.

## 9. Source-to-model receipt

Every admitted candidate yields a deterministic receipt containing:

- source and raw digest,
- variable ID,
- canonical value and unit,
- layer and quantity kind,
- target node,
- spatial and temporal transforms,
- interpolation/imputation visibility,
- uncertainty state,
- freshness age,
- output epistemic status,
- claim ceiling.

## 10. Separation rules

This gate does not merge:

- physical state with evidence confidence,
- physical state with stress,
- physical state with L1-L4 audit,
- missing with zero,
- observed with imputed,
- HHV with LHV,
- source-native units with canonical units without a declared transform.

## Claim ceiling

A PASS proves only that the **admission contract itself** is frozen, executable, fail-closed, and internally consistent against synthetic candidates.

It does not prove:

- validity of any NASA, GISS, Stockholm Resilience Centre, Rockström, IEA, World Bank, UN, national, commercial, or other external dataset,
- empirical calibration,
- planetary-boundary integration,
- forecasting,
- policy conclusions,
- aggregate Equilibrium scoring,
- runtime admission,
- production readiness.

Real data must enter through a separate source-specific admission gate after this contract is frozen.
