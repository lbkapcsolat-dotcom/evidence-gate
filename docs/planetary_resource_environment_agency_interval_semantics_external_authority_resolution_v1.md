# Environment Agency Interval Semantics External Authority Resolution V1

This gate is the final authority-resolution step for the Environment Agency
freshwater flow-mean source family.

Pinned predecessor receipt SHA256:

`b06b7a528c4f32631f116b92b8cb11387c066608ea68c3fae1b8fda7f3902f4f`

Accepted evidence classes are restricted to:

1. official Environment Agency primary documentation;
2. official Environment Agency schema semantics;
3. official Environment Agency written clarification.

No empirical timing inference is permitted.

## Flood Monitoring primary documentation

Official reference:
https://environment.data.gov.uk/flood-monitoring/doc/reference

The reference establishes that:

- a reading has a `dateTime` for when the reading occurred/applies;
- measure `period` is the period between successive readings;
- `mean` is a mean value over the measurement period.

It does not classify the reading `dateTime` as the START, END, CENTER, or any
other explicit boundary of a positive-duration mean period.

## Hydrology primary documentation

Official reference:
https://environment.data.gov.uk/hydrology/doc/reference

The Hydrology API classifies 15-minute Flow as instantaneous and daily Flow as
mean/min/max. It exposes reading date/dateTime fields but does not supply an
authoritative timestamp-to-boundary rule for positive-duration flow means.

Official OpenAPI surface:
https://environment.data.gov.uk/hydrology/doc/oas

No accepted flow-mean start/end/center boundary rule was identified there.

## Written clarification

No official EA written clarification classifying flow-mean `dateTime` as
period START, END, CENTER, or another explicit boundary is present in the
audited evidence set.

## Final source-family verdict

`FINAL_HOLD_FOR_EA_SOURCE_FAMILY__NO_AUTHORITATIVE_INTERVAL_BOUNDARY_RULE`

This is not a claim that no unpublished internal EA rule can exist. It is a
fail-closed statement about the accepted authority surfaces currently available
to this gate. Re-entry is allowed only if new official EA primary documentation,
official schema semantics, or written EA clarification explicitly classifies
the flow-mean timestamp boundary.

No new source ingest, assumption, empirical inference, core patch, domain math,
composition, EQ score, UI, runtime admission, pointer promotion, global bind,
or merge is performed.
