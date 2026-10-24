# EQUILIBRIUM Planetary Resource Systems Core V1
## Process Coefficient Validity Interval V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__PROCESS_COEFFICIENT_VALIDITY_INTERVAL_V1`

This gate closes coefficient time-applicability while preserving the pinned process-coefficient uncertainty successor.

## Temporal model

Validity uses timezone-aware ISO-8601 half-open intervals:

- requested interval: `[requested_start, requested_end)`
- coefficient validity: `[valid_from, valid_to)`

A coefficient is admissible only when:

`valid_from <= requested_start AND valid_to >= requested_end`

All bounds are normalized to UTC for comparison.

## Fail-closed cases

Expired coefficient:

`valid_to <= requested_start`

→ `HOLD_PROCESS_COEFFICIENT_EXPIRED`

Not-yet-valid coefficient:

`valid_from >= requested_end`

→ `HOLD_PROCESS_COEFFICIENT_NOT_YET_VALID`

Partial overlap:

the two intervals overlap but the coefficient validity does not fully contain the requested interval.

→ `HOLD_PROCESS_COEFFICIENT_PARTIAL_INTERVAL_OVERLAP`

Missing validity while validity is required:

→ `HOLD_PROCESS_COEFFICIENT_VALIDITY_REQUIRED`

Malformed, timezone-naive, or non-positive temporal windows:

→ `HOLD_PROCESS_COEFFICIENT_VALIDITY_INVALID`

## Preservation

The successor delegates nominal process arithmetic and uncertainty propagation to the already-proven process-coefficient uncertainty path.

It therefore preserves:

- coefficient uncertainty;
- coefficient evidence ref;
- coefficient dimensional-unit checking;
- process source/method evidence;
- activity epistemic status;
- activity evidence refs;
- activity transform chain;
- hold codes;
- freshness;
- PHYSICAL value space.

The requested interval and coefficient validity windows are appended visibly to the transform chain.

## Scope ceiling

No provider work, new source ingest, multi-source fusion, aggregate EQ score, UI, runtime admission, pointer promotion, global binding, or merge is authorized.
