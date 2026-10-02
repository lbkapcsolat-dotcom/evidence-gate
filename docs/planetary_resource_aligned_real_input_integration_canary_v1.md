# Aligned Real Input Integration Canary V1

This gate deliberately ends in a bounded HOLD.

The predecessor proves that BOM freshwater, Elexon electricity, and ENTSOG gas
have a positive-duration three-way intersection from
`2026-09-30T12:00:00Z` to `2026-09-30T12:30:00Z`.

That overlap is not sufficient to claim exact temporal support for all three
published rate values.

## Structural mappings proven

- Elexon INDO `21575 MW` maps through the frozen empirical contract to
  `21,575,000,000 W_e` and enters the electricity **DEMAND** slot.
- ENTSOG Physical Flow `26823568 kWh/h` reuses the previously proven
  `kWh/h_GCV -> kW_HHV` semantic adapter and frozen contract conversion to
  `26,823,568,000 W_th`; structurally it enters the gas **BOUNDARY_IMPORT**
  slot.
- BOM Water Course Discharge `0.378 m3/s` remains
  `freshwater.internal_flow_rate`. It is not relabeled as production or
  demand. The integration fixture adds `W1` and one frozen-core internal edge
  `W0 -> W1`; the incidence effect is `W0=-0.378`, `W1=+0.378`.

No core patch and no new domain equation are introduced.

## Why the common-window integration is HOLD

The frozen empirical contract's `EXACT_INTERVAL` rule requires the source
interval identity to equal the target interval identity.

- Elexon support: `12:00 -> 12:30 UTC`, exact target match.
- ENTSOG support: `12:00 -> 13:00 UTC`, contains the target but is not equal.
- BOM daily-mean support: `2026-09-29 14:00 -> 2026-09-30 14:00 UTC`,
  contains the target but is not equal.

Treating the hourly gas value or daily freshwater mean as a 30-minute value
would require an additional temporal assumption or transform. This gate
forbids interpolation, imputation, cross-interval aggregation, and implicit
downscaling, so the system fails closed.

Verdict:

`HOLD_BOUNDED_ALIGNED_REAL_INPUT_INTEGRATION_TEMPORAL_SUPPORT_MISMATCH`

Claim ceiling: structural slot mapping, unit mapping, source-native core
effects, and topology compatibility are proven. A three-source 30-minute
physical composition is not proven or admitted.
