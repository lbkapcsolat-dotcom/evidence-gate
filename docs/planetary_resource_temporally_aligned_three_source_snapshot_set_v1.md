# Temporally Aligned Three-Source Snapshot Set V1

This successor gate is deliberately split into a source-semantics preflight
before any new external record ingest.

Pinned predecessor:
`REAL_THREE_LAYER_INPUT_COMPOSITION_CANARY_V1`
receipt SHA256
`eb28b3eb2a495497a53fe416e30dda9c72a090b3766f955f926c6a4616ee9e26`.

## Why ingest did not start

The strict requirement is source-explicit interval bounds for Environment
Agency, Elexon and ENTSOG before constructing a positive-duration common
window.

### Environment Agency

Official reference:
https://environment.data.gov.uk/flood-monitoring/doc/reference

The API documents a reading `dateTime`, a `period` between successive
readings, and `mean` as a mean over the measurement period. It does not
document whether the reading timestamp anchors the start, end or center of that
mean period. The already-proven binding therefore retains
`NO_INFERRED_START_BOUNDARY`.

### Elexon INDO

Official developer portal:
https://developer.data.elexon.co.uk/

The proven record carries `startTime`, settlement period and half-hour-average
semantics. The pinned source record does not carry an explicit end-time field.
Under this gate's deliberately strict "both bounds source-explicit" rule, this
is not yet sufficient.

### ENTSOG

Official API manual:
https://transparency.entsog.eu/api/archiveDirectories/8/api-manual/ENTSOG_TP_API_UserManual_v3.0.pdf

The operational-data schema exposes `periodFrom` and `periodTo`, so the
existing ENTSOG source surface satisfies the strict-bound shape.

## Result

The gate fails closed before new network ingest. Existing proven raw bytes,
SHA256 values, provenance and UNKNOWN uncertainty are revalidated unchanged.
No interpolation, imputation, cross-interval aggregation, composition, core
patch or new domain math occurs.

Verdict:
`HOLD_SOURCE_INTERVAL_SEMANTICS_UNPROVEN`.

Minimum unblock: authoritative Environment Agency interval anchoring plus a
source-explicit Elexon end bound (or authoritative contract-equivalent end
semantics). Only then ingest one aligned snapshot per source and prove a
positive-duration three-way intersection.
