# Source Interval Semantics Recovery V1

This gate uses official primary documentation only. It performs no new source
data ingest and no composition.

## Environment Agency

Primary source:
https://environment.data.gov.uk/flood-monitoring/doc/reference

The official reference establishes three facts:

1. readings carry a dateTime;
2. a measure period is the time between successive readings;
3. a mean value is a mean over the measurement period.

The same primary source does not define whether the reading dateTime anchors the
start, end, or center of that mean period. Therefore the previous
NO_INFERRED_START_BOUNDARY restriction remains binding.

Result: HOLD_UNPROVEN.

## Elexon

Primary sources:

- https://bscdocs.elexon.co.uk/interface-definition-documents/neta-interface-definition-and-design-document-part-1-interfaces-with-bsc-parties-and-their-agents
- https://www.elexon.co.uk/bsc/glossary/settlement-period/
- https://www.elexon.co.uk/bsc/glossary/spot-time/

The Digital BSC interface defines INDO as average demand in MW for each
Settlement Period and identifies the associated time as the Start Time of the
half-hour period. The BSC defines a Settlement Period as 30 minutes beginning on
the hour or half-hour, and the Spot Time definition states that the period ends
exactly 30 minutes after its starting spot time.

Therefore, for the already-pinned INDO record with startTime
2026-10-01T22:00:00Z, the authoritative end bound is
2026-10-01T22:30:00Z.

This is contract recovery from Elexon primary documentation, not an arbitrary
interval inference.

Result: PROVEN.

## Gate result

Elexon semantics are recovered; Environment Agency interval anchoring remains
unproven. ENTSOG was already satisfied by explicit periodFrom/periodTo.

Overall verdict:
HOLD_SOURCE_INTERVAL_SEMANTICS_RECOVERY_PARTIAL__ELEXON_PROVEN__EA_UNPROVEN

No new ingest, core patch, domain math, composition, score, UI, runtime
admission, pointer promotion, global bind, or merge.
