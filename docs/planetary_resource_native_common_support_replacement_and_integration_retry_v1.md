# Native Common-Support Source Replacement and Integration Retry V1

Target interval is frozen at:

`2026-09-30T12:00:00Z -> 2026-09-30T12:30:00Z`

The Elexon INDO source remains pinned and exact for this window.

This successor gate performs bounded official-source discovery for replacement
natural-gas and freshwater inputs. The tested gas surfaces are National Gas
Transmission's public Instantaneous Flow REST API and the previously pinned
ENTSOG Physical Flow family. The tested freshwater surfaces are the Bureau of
Meteorology Water Data Online SOS2 capabilities surface and the previously
proven Environment Agency 15-minute mean family.

No exact native 30-minute replacement was proven in those tested official
surfaces.

The National Gas public Instantaneous Flow API documents two-minute captured
flow values published in twelve-minute sets. The tested ENTSOG family is hourly.
The BOM SOS2 capabilities advertise relevant AsStored, HourlyMean and DailyMean
series, but this bounded discovery did not prove a 30-minute Water Course
Discharge mean product. The previously proven Environment Agency family is
15-minute mean.

Therefore the integration retry is not executed. This is deliberate fail-closed
behavior, not a failed core computation.

Verdict:

`HOLD_EXACT_NATIVE_COMMON_SUPPORT_NOT_AVAILABLE`

The claim is bounded. It does not assert that an exact 30-minute gas or
freshwater source cannot exist elsewhere. It asserts only that no admissible
replacement was proven in the official surfaces tested by this gate.

No interpolation, imputation, aggregation, downscaling, inferred boundaries,
core patch, new domain math, score, UI, runtime admission, pointer promotion,
global bind, or merge.
