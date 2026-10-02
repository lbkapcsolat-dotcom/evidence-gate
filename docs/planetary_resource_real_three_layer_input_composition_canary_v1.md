# Real Three-Layer Input Composition Canary V1

This gate attempts to reuse only the three already-proven real-source admissions
(Environment Agency freshwater, Elexon electricity, ENTSOG natural gas) and map
them into the frozen integrated minimal planetary core.

The gate is intentionally fail-closed on temporal composition. A real-value
mapping is permitted only after a positive-duration common source window is
proven without interpolation, imputation, aggregation, inferred interval
boundaries, or new source ingest.

For the pinned evidence set:

- ENTSOG natural-gas Physical Flow is explicit on `[2026-10-01T21:00Z, 22:00Z)`.
- Elexon INDO starts at `2026-10-01T22:00Z` and is a half-hour average.
- Therefore the gas/electricity pair has zero positive-duration overlap. They
  only touch at the `22:00Z` boundary.
- The Environment Agency freshwater record is a 15-minute mean observed at
  `21:30Z`, but its proven admission contract explicitly says
  `NO_INFERRED_START_BOUNDARY`.

Result: no exact positive-duration common three-layer window is proven. The
canary revalidates all three admission receipts and the integrated predecessor,
preserves uncertainty/provenance and all predecessor guards, performs no
real-value mapping, and emits a deterministic HOLD receipt.

No new source ingest, interpolation, imputation, aggregation, core patch, new
domain math, EQ score, UI, runtime admission, pointer promotion, global bind, or
merge is performed.

Minimum unblock: acquire a new explicitly bounded three-layer snapshot set with
a shared positive-duration source window while keeping the frozen core and
composition math unchanged.
