# Environment Agency Explicit Interval Source Surface Recovery V1

This gate searches only official Environment Agency / Defra primary
documentation for an Environment Agency freshwater-flow source surface that can
satisfy the strict temporal-composition requirement.

Pinned predecessor receipt SHA256:

`1094ac15a21253b6e867bfd783cdd8daa27750e3a57c821440e624efa36da70b`

No new source data is ingested.

## Candidate 1 — Flood Monitoring flow mean

Primary documentation:
https://environment.data.gov.uk/flood-monitoring/doc/reference

The surface provides reading `dateTime`, measure `period`, and
`valueType=mean`. The documentation defines period as the interval between
successive readings and mean as a value over the measurement period, but does
not bind the reading timestamp to the start, end, or center boundary of that
period.

Result: not eligible.

## Candidate 2 — Hydrology API 15-minute flow

Primary documentation:
https://environment.data.gov.uk/hydrology/doc/reference

The revised Hydrology API explicitly identifies 15-minute Flow as
`valueType=instantaneous`, unit `m3/s`.

This gives a source-defined observation timestamp but not a positive-duration
flow interval. It therefore cannot satisfy the later common-window requirement.

Result: not eligible.

## Candidate 3 — Hydrology API daily mean flow

The Hydrology API exposes daily mean flow time series and identifies
`valueStatistic` as statistics over a measurement interval. Reading records
contain `date` and `dateTime`, but the official reference does not define
that timestamp as the start or end boundary of the daily mean interval and does
not expose explicit start/end fields.

Result: not eligible under the strict no-inference rule.

## Candidate 4 — Tide Gauge API

Primary documentation:
https://environment.data.gov.uk/flood-monitoring/doc/tidegauge

The Tide Gauge API states that measurements provide mean sea level within each
15-minute window. This is a tidal water-level variable, not freshwater flow.
Substituting it would change the physical variable and violate the frozen
binding scope.

Result: not eligible.

## Verdict

No official Environment Agency freshwater-flow surface located in the audited
primary documentation provides either explicit start/end bounds or an
authoritative timestamp-to-boundary rule for a positive-duration flow aggregate.

`HOLD_NO_ELIGIBLE_ENVIRONMENT_AGENCY_FRESHWATER_FLOW_INTERVAL_SURFACE`

Elexon remains recovered and ENTSOG remains satisfied. No timestamp-minus-period
inference, center-window inference, assumed 15-minute window, new source ingest,
composition, core patch, new domain math, EQ score, UI, runtime admission,
pointer promotion, global bind, or merge is performed.
