# BOM + Elexon + ENTSOG Temporally Aligned Snapshot Set V1

This gate proves temporal compatibility only. It does not compose values.

Pinned predecessor receipt:

`236dcdcf8669a9a64251722af55c31eda04cee9f7bd30383cdafe883bdfea42a`

## Freshwater

Australian Bureau of Meteorology Water Data Online, station 410713, daily mean
Water Course Discharge. The WaterML2 response carries explicit
`gml:beginPosition` and `gml:endPosition`:

- start: `2026-09-30T00:00:00.000+10:00`
- end: `2026-10-01T00:00:00.000+10:00`

## Electricity

Elexon Insights Solution demand outturn. The exact selected INDO row is:

- start: `2026-09-30T12:00:00Z`
- settlement period: 27
- initial demand outturn: `21575 MW`

The end bound `12:30:00Z` is the already-frozen authoritative Elexon
Settlement Period rule: start plus 30 minutes.

## Natural gas

ENTSOG Transparency Platform, Gasunie Deutschland, Dornum / NETRA (GUD),
entry Physical Flow. The exact selected raw CSV row embeds UTC bounds in its
record id:

- start: `2026-09-30T12:00:00Z`
- end: `2026-09-30T13:00:00Z`
- value: `26823568 kWh/h`
- status: `Provisional`

## Exact three-way intersection

`2026-09-30T12:00:00Z → 2026-09-30T12:30:00Z`

Duration: 1800 seconds.

No interpolation, imputation, cross-interval aggregation, or inferred boundary
is used. Elexon's end bound is an authoritative source-contract rule frozen by
the earlier semantics-recovery gate, not a numerical inference from the present
record. Source-native values are not combined.

Verdict target:

`PASS_BOUNDED_BOM_ELEXON_ENTSOG_TEMPORALLY_ALIGNED_SNAPSHOT_SET`

Claim ceiling: temporal alignment only. No composition, score, UI, runtime
admission, production admission, pointer promotion, global bind, or merge.
